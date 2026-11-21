#!/usr/bin/env python3
"""Read-only GitHub Ruleset observer emitting candidate enforcement evidence.

This CLI normalizes either:
  - an offline raw GitHub Ruleset REST API payload (`--input-file`), or
  - a live read-only query (`--live`) via `gh api --method GET repos/<repo>/rulesets/<id>`.

It computes a SHA-256 digest over the exact raw response bytes, emits a
deterministic `openagenticsecurity.governance.enforcement-evidence.v1` JSON document with
`authority: "candidate"` and `trusted: false`, and optionally validates it
against `scripts/check-enforcement-evidence.py` (`--validate`, exiting 2 on
contract/policy failure).

It never modifies repository settings, never grants merge authority, and fails
closed on malformed input, symlinks, duplicate JSON keys, unsafe identifiers,
or missing `gh`.
"""

from __future__ import annotations

import argparse
from collections.abc import Mapping, Sequence
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys


REPO_RE = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")
BRANCH_RE = re.compile(r"^[A-Za-z0-9._/-]+$")
ISO_UTC_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")
ALLOWED_ACTOR_TYPES = frozenset(
    {
        "DeployKey",
        "EnterpriseTeam",
        "Integration",
        "OrganizationAdmin",
        "RepositoryRole",
        "Team",
        "User",
    }
)
ALLOWED_BYPASS_MODES = frozenset({"always", "exempt", "pull_request"})


class ObserverInputError(ValueError):
    """Fail-closed error for unsafe CLI arguments or malformed inputs."""


class ObserverNotRunError(RuntimeError):
    """Fail-closed NOT_RUN error when an external observer dependency is absent."""


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ObserverInputError(message)


def _reject_duplicate_keys(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise ObserverInputError(f"duplicate JSON key {key!r}")
        result[key] = value
    return result


def strict_json_loads_bytes(raw_bytes: bytes, label: str) -> object:
    try:
        text = raw_bytes.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ObserverInputError(f"{label}: invalid UTF-8") from exc
    try:
        return json.loads(text, object_pairs_hook=_reject_duplicate_keys)
    except json.JSONDecodeError as exc:
        raise ObserverInputError(f"{label}: invalid JSON ({exc.msg})") from exc


def read_regular_file_bytes(path: Path, label: str) -> bytes:
    if path.is_symlink() or not path.is_file():
        raise ObserverInputError(f"{label}: regular non-symlink file required ({path})")
    try:
        return path.read_bytes()
    except OSError as exc:
        raise ObserverInputError(f"{label}: unable to read file ({exc})") from exc


def validate_repo(repository: str) -> str:
    _require(
        bool(REPO_RE.fullmatch(repository)) and len(repository) <= 200,
        f"unsafe repository identifier: {repository!r}",
    )
    owner, name = repository.split("/", 1)
    _require(owner not in {".", ".."} and name not in {".", ".."}, f"unsafe repository identifier: {repository!r}")
    return repository


def validate_branch(branch: str) -> str:
    _require(
        bool(BRANCH_RE.fullmatch(branch))
        and len(branch) <= 255
        and ".." not in branch
        and not branch.startswith("/")
        and not branch.endswith("/"),
        f"unsafe branch name: {branch!r}",
    )
    return branch


def validate_observed_at(observed_at: str | None) -> str:
    if observed_at is None:
        return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    _require(
        bool(ISO_UTC_RE.fullmatch(observed_at)),
        f"observed_at must be UTC ISO-8601 (YYYY-MM-DDTHH:MM:SSZ): {observed_at!r}",
    )
    try:
        datetime.strptime(observed_at, "%Y-%m-%dT%H:%M:%SZ")
    except ValueError as exc:
        raise ObserverInputError(f"invalid observed_at timestamp: {observed_at!r}") from exc
    return observed_at


def _normalize_policy(raw_policy: object) -> dict[str, object]:
    _require(isinstance(raw_policy, Mapping), "policy must be a JSON object")
    assert isinstance(raw_policy, Mapping)
    policy = dict(raw_policy)
    contexts = policy.get("required_status_contexts")
    _require(
        isinstance(contexts, list) and all(isinstance(item, str) for item in contexts),
        "policy.required_status_contexts must be a list of strings",
    )
    assert isinstance(contexts, list)
    policy["required_status_contexts"] = sorted(set(contexts))

    allowed_pr_raw = policy.get("allowed_pull_request_bypass_actors")
    if allowed_pr_raw is not None:
        _require(
            isinstance(allowed_pr_raw, list),
            "policy.allowed_pull_request_bypass_actors must be a list",
        )
        assert isinstance(allowed_pr_raw, list)
        dedup: dict[tuple[str, int], dict[str, object]] = {}
        for actor in allowed_pr_raw:
            _require(isinstance(actor, Mapping), "allowed bypass actor entry must be an object")
            assert isinstance(actor, Mapping)
            actor_type = actor.get("actor_type")
            actor_id = actor.get("actor_id")
            _require(
                isinstance(actor_type, str) and actor_type in ALLOWED_ACTOR_TYPES,
                f"unsupported allowed bypass actor_type: {actor_type!r}",
            )
            _require(
                actor_id is None
                or (isinstance(actor_id, int) and not isinstance(actor_id, bool) and actor_id >= 1),
                f"allowed bypass actor_id must be a positive integer or null: {actor_id!r}",
            )
            assert isinstance(actor_type, str)
            sort_id = -1 if actor_id is None else int(actor_id)
            dedup[(actor_type, sort_id)] = {"actor_id": actor_id, "actor_type": actor_type}
        policy["allowed_pull_request_bypass_actors"] = [dedup[key] for key in sorted(dedup)]
    return policy


def _extract_conditions(raw_ruleset: Mapping[str, object]) -> dict[str, list[str]]:
    conditions = raw_ruleset.get("conditions")
    if conditions is None:
        return {"ref_name_include": [], "ref_name_exclude": []}
    _require(isinstance(conditions, Mapping), "ruleset.conditions must be an object")
    assert isinstance(conditions, Mapping)
    ref_name = conditions.get("ref_name", {})
    _require(isinstance(ref_name, Mapping), "ruleset.conditions.ref_name must be an object")
    assert isinstance(ref_name, Mapping)
    include_raw = ref_name.get("include", [])
    exclude_raw = ref_name.get("exclude", [])
    _require(
        isinstance(include_raw, list) and all(isinstance(x, str) for x in include_raw),
        "ruleset.conditions.ref_name.include must be a list of strings",
    )
    _require(
        isinstance(exclude_raw, list) and all(isinstance(x, str) for x in exclude_raw),
        "ruleset.conditions.ref_name.exclude must be a list of strings",
    )
    return {
        "ref_name_include": sorted(set(include_raw)),
        "ref_name_exclude": sorted(set(exclude_raw)),
    }


def _extract_pull_request(raw_ruleset: Mapping[str, object]) -> dict[str, object]:
    rules = raw_ruleset.get("rules", [])
    _require(isinstance(rules, list), "ruleset.rules must be a list")
    assert isinstance(rules, list)

    pr_params: Mapping[str, object] = {}
    status_checks_by_context: dict[str, int | None] = {}

    for rule in rules:
        _require(isinstance(rule, Mapping), "each ruleset rule must be an object")
        assert isinstance(rule, Mapping)
        rule_type = rule.get("type")
        params = rule.get("parameters")
        if rule_type == "pull_request":
            _require(isinstance(params, Mapping), "pull_request rule parameters must be an object")
            assert isinstance(params, Mapping)
            pr_params = params
        elif rule_type == "required_status_checks":
            _require(isinstance(params, Mapping), "required_status_checks rule parameters must be an object")
            assert isinstance(params, Mapping)
            checks = params.get("required_status_checks", [])
            _require(isinstance(checks, list), "required_status_checks list must be an array")
            assert isinstance(checks, list)
            for check in checks:
                _require(isinstance(check, Mapping), "status check entry must be an object")
                assert isinstance(check, Mapping)
                context = check.get("context")
                _require(isinstance(context, str) and bool(context), "status check context must be a non-empty string")
                assert isinstance(context, str)
                integration_id = check.get("integration_id")
                if integration_id is not None:
                    _require(
                        isinstance(integration_id, int) and not isinstance(integration_id, bool) and integration_id >= 1,
                        f"status check integration_id must be a positive integer or null for {context!r}",
                    )
                if context in status_checks_by_context and status_checks_by_context[context] != integration_id:
                    raise ObserverInputError(f"conflicting integration_id for status check context {context!r}")
                status_checks_by_context[context] = integration_id

    review_count = pr_params.get("required_approving_review_count", 0)
    _require(
        isinstance(review_count, int) and not isinstance(review_count, bool) and review_count >= 0,
        "pull_request.required_approving_review_count must be a non-negative integer",
    )
    require_code_owner = pr_params.get("require_code_owner_review", False)
    dismiss_stale = pr_params.get("dismiss_stale_reviews_on_push", False)
    require_last_push = pr_params.get("require_last_push_approval", False)
    for field_name, val in (
        ("require_code_owner_review", require_code_owner),
        ("dismiss_stale_reviews_on_push", dismiss_stale),
        ("require_last_push_approval", require_last_push),
    ):
        _require(isinstance(val, bool), f"pull_request.{field_name} must be a boolean")

    sorted_checks = [
        {"context": context, "integration_id": status_checks_by_context[context]}
        for context in sorted(status_checks_by_context)
    ]
    return {
        "required_status_checks": sorted_checks,
        "required_approving_review_count": review_count,
        "require_code_owner_review": require_code_owner,
        "dismiss_stale_reviews_on_push": dismiss_stale,
        "require_last_push_approval": require_last_push,
    }


def _extract_bypass_actors(raw_ruleset: Mapping[str, object]) -> list[dict[str, object]]:
    actors_raw = raw_ruleset.get("bypass_actors", [])
    if actors_raw is None:
        return []
    _require(isinstance(actors_raw, list), "ruleset.bypass_actors must be a list")
    assert isinstance(actors_raw, list)
    dedup: dict[tuple[str, int, str], dict[str, object]] = {}
    for actor in actors_raw:
        _require(isinstance(actor, Mapping), "bypass actor entry must be an object")
        assert isinstance(actor, Mapping)
        actor_type = actor.get("actor_type")
        actor_id = actor.get("actor_id")
        bypass_mode = actor.get("bypass_mode")
        _require(
            isinstance(actor_type, str) and actor_type in ALLOWED_ACTOR_TYPES,
            f"unsupported bypass actor_type: {actor_type!r}",
        )
        _require(
            actor_id is None
            or (isinstance(actor_id, int) and not isinstance(actor_id, bool) and actor_id >= 1),
            f"bypass actor_id must be a positive integer or null: {actor_id!r}",
        )
        _require(
            isinstance(bypass_mode, str) and bypass_mode in ALLOWED_BYPASS_MODES,
            f"unsupported bypass_mode: {bypass_mode!r}",
        )
        assert isinstance(actor_type, str) and isinstance(bypass_mode, str)
        sort_id = -1 if actor_id is None else int(actor_id)
        key = (actor_type, sort_id, bypass_mode)
        dedup[key] = {
            "actor_id": actor_id,
            "actor_type": actor_type,
            "bypass_mode": bypass_mode,
        }
    return [dedup[key] for key in sorted(dedup)]


def normalize_ruleset_bytes(
    *,
    raw_bytes: bytes,
    repository: str,
    default_branch: str,
    policy: Mapping[str, object],
    ruleset_id: int | None = None,
    observed_at: str | None = None,
) -> dict[str, object]:
    repository = validate_repo(repository)
    default_branch = validate_branch(default_branch)
    observed_ts = validate_observed_at(observed_at)
    normalized_policy = _normalize_policy(policy)

    raw_payload = strict_json_loads_bytes(raw_bytes, "ruleset payload")
    _require(isinstance(raw_payload, Mapping), "ruleset payload root must be an object")
    assert isinstance(raw_payload, Mapping)

    payload_id = raw_payload.get("id")
    _require(
        isinstance(payload_id, int) and not isinstance(payload_id, bool) and payload_id >= 1,
        "ruleset payload must include positive integer 'id'",
    )
    assert isinstance(payload_id, int)
    if ruleset_id is not None:
        _require(
            ruleset_id >= 1 and ruleset_id == payload_id,
            f"requested ruleset_id ({ruleset_id}) does not match payload id ({payload_id})",
        )
    effective_ruleset_id = payload_id

    ruleset_name = raw_payload.get("name")
    _require(
        isinstance(ruleset_name, str) and 1 <= len(ruleset_name) <= 255,
        "ruleset payload must include non-empty string 'name'",
    )
    target = raw_payload.get("target")
    _require(isinstance(target, str), "ruleset payload must include string 'target'")
    enforcement = raw_payload.get("enforcement")
    _require(isinstance(enforcement, str), "ruleset payload must include string 'enforcement'")

    digest = "sha256:" + hashlib.sha256(raw_bytes).hexdigest()
    reference = f"repos/{repository}/rulesets/{effective_ruleset_id}"

    return {
        "schema_version": "openagenticsecurity.governance.enforcement-evidence.v1",
        "authority": "candidate",
        "trusted": False,
        "repository": repository,
        "default_branch": default_branch,
        "observed_at": observed_ts,
        "source": {
            "kind": "github_ruleset_api",
            "reference": reference,
            "response_digest": digest,
        },
        "policy": normalized_policy,
        "observation": {
            "ruleset_id": effective_ruleset_id,
            "ruleset_name": ruleset_name,
            "target": target,
            "enforcement": enforcement,
            "conditions": _extract_conditions(raw_payload),
            "pull_request": _extract_pull_request(raw_payload),
            "bypass_actors": _extract_bypass_actors(raw_payload),
        },
    }


def fetch_live_ruleset_bytes(
    repository: str,
    ruleset_id: int,
    gh_bin: str = "gh",
    timeout: int = 30,
) -> bytes:
    repository = validate_repo(repository)
    _require(ruleset_id >= 1, f"ruleset_id must be >= 1, got {ruleset_id}")
    _require(timeout >= 1, f"timeout must be >= 1 second, got {timeout}")
    resolved_gh = shutil.which(gh_bin)
    if not resolved_gh:
        raise ObserverNotRunError(
            f"NOT_RUN: GitHub CLI ({gh_bin!r}) is not installed or not on PATH"
        )
    endpoint = f"repos/{repository}/rulesets/{ruleset_id}"
    try:
        proc = subprocess.run(
            [resolved_gh, "api", "--method", "GET", endpoint],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=timeout,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        raise ObserverNotRunError(
            f"NOT_RUN: gh api GET {endpoint} timed out after {timeout}s"
        ) from exc
    if proc.returncode != 0:
        stderr_text = proc.stderr.decode("utf-8", errors="replace").strip()
        raise ObserverNotRunError(
            f"NOT_RUN: gh api GET {endpoint} failed (exit {proc.returncode}): {stderr_text}"
        )
    return proc.stdout


def load_enforcement_checker(root: Path):
    checker_path = root / "scripts" / "check-enforcement-evidence.py"
    if checker_path.is_symlink() or not checker_path.is_file():
        raise ObserverInputError(f"missing enforcement checker: {checker_path}")
    spec = importlib.util.spec_from_file_location("check_enforcement_evidence", checker_path)
    if spec is None or spec.loader is None:
        raise ObserverInputError(f"unable to load enforcement checker: {checker_path}")
    module = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(module)
    except ImportError as exc:
        raise ObserverNotRunError(
            f"NOT_RUN: unable to import validation dependency ({exc}); "
            "install requirements-test.txt to use --validate"
        ) from exc
    return module


def validate_normalized_report(report: Mapping[str, object], root: Path) -> None:
    checker = load_enforcement_checker(root)
    schema = checker._schema(root)
    checker.validate_report(report, schema=schema)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    source_group = parser.add_mutually_exclusive_group(required=True)
    source_group.add_argument(
        "--input-file",
        type=Path,
        help="Path to an offline raw GitHub Ruleset REST API JSON payload.",
    )
    source_group.add_argument(
        "--live",
        action="store_true",
        help="Query GitHub read-only via `gh api --method GET repos/<repo>/rulesets/<id>`.",
    )
    parser.add_argument(
        "--repo",
        required=True,
        help="GitHub repository in owner/name format.",
    )
    parser.add_argument(
        "--ruleset-id",
        type=int,
        help="Positive integer ruleset ID (required with --live; cross-checked with --input-file).",
    )
    parser.add_argument(
        "--default-branch",
        default="main",
        help="Expected default branch name (default: main).",
    )
    parser.add_argument(
        "--policy",
        type=Path,
        required=True,
        help="Path to JSON policy document matching enforcement-evidence.v1 $defs/policy.",
    )
    parser.add_argument(
        "--observed-at",
        help="Explicit UTC timestamp (YYYY-MM-DDTHH:MM:SSZ). Defaults to current UTC time.",
    )
    parser.add_argument(
        "--root",
        type=Path,
        default=Path(__file__).resolve().parents[1],
        help="Repository root containing standards/ and scripts/check-enforcement-evidence.py.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="Optional output file path for normalized JSON report (default: stdout).",
    )
    parser.add_argument(
        "--validate",
        action="store_true",
        help="Validate normalized report against schema and policy rules; exit 2 on failure.",
    )
    parser.add_argument(
        "--gh-bin",
        default="gh",
        help="GitHub CLI executable name/path for --live mode (default: gh).",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=30,
        help="Timeout in seconds for live GitHub CLI calls (default: 30).",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    root = args.root.resolve()
    try:
        checker = load_enforcement_checker(root) if args.validate else None
        policy_bytes = read_regular_file_bytes(args.policy, "policy file")
        policy_obj = strict_json_loads_bytes(policy_bytes, "policy file")
        _require(isinstance(policy_obj, Mapping), "policy file root must be a JSON object")
        assert isinstance(policy_obj, Mapping)

        if args.live:
            _require(args.ruleset_id is not None and args.ruleset_id >= 1, "--ruleset-id is required with --live")
            raw_bytes = fetch_live_ruleset_bytes(
                args.repo,
                args.ruleset_id,
                gh_bin=args.gh_bin,
                timeout=args.timeout,
            )
        else:
            raw_bytes = read_regular_file_bytes(args.input_file, "input ruleset file")

        report = normalize_ruleset_bytes(
            raw_bytes=raw_bytes,
            repository=args.repo,
            default_branch=args.default_branch,
            policy=policy_obj,
            ruleset_id=args.ruleset_id,
            observed_at=args.observed_at,
        )
    except ObserverNotRunError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    except ObserverInputError as exc:
        print(f"observe-github-ruleset input error: {exc}", file=sys.stderr)
        return 1

    rendered = json.dumps(report, indent=2, ensure_ascii=True) + "\n"
    if args.output is not None:
        if args.output.is_symlink():
            print(f"observe-github-ruleset input error: refusing to write to symlink path: {args.output}", file=sys.stderr)
            return 1
        args.output.parent.mkdir(parents=True, exist_ok=True)
        flags = os.O_WRONLY | os.O_CREAT | os.O_TRUNC | getattr(os, "O_NOFOLLOW", 0)
        try:
            fd = os.open(args.output, flags, 0o644)
        except OSError as exc:
            print(f"observe-github-ruleset input error: refusing to write output ({exc})", file=sys.stderr)
            return 1
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(rendered)
    else:
        sys.stdout.write(rendered)

    if checker is not None:
        try:
            schema = checker._schema(root)
            checker.validate_report(report, schema=schema)
        except checker.EnforcementEvidenceError as exc:
            print(f"observe-github-ruleset validation failed: {exc}", file=sys.stderr)
            return 2
        except Exception as exc:
            print(f"NOT_RUN: validation runtime error: {exc}", file=sys.stderr)
            return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
