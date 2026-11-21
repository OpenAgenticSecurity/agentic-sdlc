#!/usr/bin/env python3
"""Check the candidate contract for externally observed GitHub enforcement.

This command validates a normalized, read-only ruleset observation.  It does
not call GitHub, change a ruleset, select a test, or grant merge/release
authority.  A separately authorized observer (for example, a future Guardian)
must supply the observation and its response digest.
"""

from __future__ import annotations

import argparse
from collections.abc import Mapping, Sequence
from datetime import datetime
import json
from pathlib import Path
import re
import sys

from jsonschema import Draft202012Validator, FormatChecker
from jsonschema.exceptions import SchemaError


SCHEMA_RELATIVE = Path(
    "standards/testing-strategy/enforcement-evidence/schema/"
    "enforcement-evidence.v1.schema.json"
)
FIXTURE_ROOT = Path(
    "standards/testing-strategy/enforcement-evidence/fixtures"
)
SHA256_RE = re.compile(r"^sha256:[0-9a-f]{64}$")
RFC3339_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2}[Tt ]\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:[Zz]|[+-]\d{2}:\d{2})$"
)
REFERENCE_RE = re.compile(
    r"^repos/(?P<owner>[A-Za-z0-9_.-]+)/(?P<repo>[A-Za-z0-9_.-]+)/rulesets/"
    r"(?P<ruleset>[0-9]+)$"
)
INVALID_FIXTURE_EXPECTATIONS = {
    "duplicate-key.json": "duplicate JSON key",
    "missing-required-status.json": "required status",
    "unconditional-bypass.json": "unconditional bypass",
    "last-push-disabled.json": "last-push approval",
    "source-mismatch.json": "source reference",
    "unbound-status-source.json": "status check source",
    "unapproved-pr-bypass.json": "pull_request bypass",
}


class EnforcementEvidenceError(ValueError):
    """A bounded candidate evidence contract failure."""


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise EnforcementEvidenceError(message)


def _strict_load(path: Path) -> object:
    if path.is_symlink() or not path.is_file():
        raise EnforcementEvidenceError(f"{path}: regular JSON file required")

    def reject_duplicates(
        pairs: list[tuple[str, object]],
    ) -> dict[str, object]:
        value: dict[str, object] = {}
        for key, item in pairs:
            if key in value:
                raise EnforcementEvidenceError(
                    f"{path}: duplicate JSON key {key!r}"
                )
            value[key] = item
        return value

    try:
        return json.loads(
            path.read_text(encoding="utf-8"),
            object_pairs_hook=reject_duplicates,
        )
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise EnforcementEvidenceError(f"{path}: invalid JSON") from exc


def _schema(root: Path) -> Mapping[str, object]:
    value = _strict_load(root / SCHEMA_RELATIVE)
    _require(
        isinstance(value, Mapping),
        "enforcement-evidence schema root is not an object",
    )
    try:
        Draft202012Validator.check_schema(value)
    except SchemaError as exc:
        raise EnforcementEvidenceError(
            "enforcement-evidence schema is invalid"
        ) from exc
    return value


def _schema_errors(
    value: Mapping[str, object],
    schema: Mapping[str, object],
) -> list[str]:
    validator = Draft202012Validator(schema, format_checker=FormatChecker())
    return [
        error.message
        for error in sorted(
            validator.iter_errors(value),
            key=lambda item: tuple(
                (type(part).__name__, str(part)) for part in item.absolute_path
            ),
        )
    ]


def _sorted_unique_strings(value: object, field: str) -> list[str]:
    _require(isinstance(value, list), f"{field} must be an array")
    _require(all(isinstance(item, str) for item in value), f"{field} has non-string item")
    result = list(value)
    _require(result == sorted(set(result)), f"{field} must be sorted and unique")
    return result


def _status_checks_by_context(pull_request: Mapping[str, object]) -> dict[str, int | None]:
    checks = pull_request.get("required_status_checks")
    _require(isinstance(checks, list), "required status checks must be an array")
    contexts: list[str] = []
    by_context: dict[str, int | None] = {}
    for check in checks:
        _require(isinstance(check, Mapping), "status check must be an object")
        context = check.get("context")
        _require(isinstance(context, str), "status check context must be a string")
        integration_id = check.get("integration_id")
        _require(
            integration_id is None
            or (isinstance(integration_id, int) and not isinstance(integration_id, bool) and integration_id >= 1),
            "status check integration_id must be a positive integer or null",
        )
        contexts.append(context)
        by_context[context] = integration_id
    _require(contexts == sorted(set(contexts)), "observed status checks must be sorted and unique")
    return by_context


def _allowed_pr_bypass_keys(value: object) -> set[tuple[str, int]]:
    _require(isinstance(value, list), "allowed_pull_request_bypass_actors must be an array")
    keys: list[tuple[str, int]] = []
    for actor in value:
        _require(isinstance(actor, Mapping), "allowed bypass actor must be an object")
        actor_type = actor.get("actor_type")
        actor_id = actor.get("actor_id")
        _require(isinstance(actor_type, str), "allowed bypass actor type must be a string")
        _require(
            actor_id is None or (isinstance(actor_id, int) and not isinstance(actor_id, bool)),
            "allowed bypass actor id must be an integer or null",
        )
        keys.append((actor_type, -1 if actor_id is None else actor_id))
    _require(keys == sorted(set(keys)), "allowed_pull_request_bypass_actors must be sorted and unique")
    return set(keys)


def _validate_rfc3339_timestamp(value: object, field: str) -> None:
    _require(isinstance(value, str) and bool(RFC3339_RE.fullmatch(value)), f"{field} must be a valid RFC 3339 date-time")
    assert isinstance(value, str)
    normalized = value[:-1] + "+00:00" if value[-1] in {"Z", "z"} else value
    try:
        datetime.fromisoformat(normalized)
    except ValueError as exc:
        raise EnforcementEvidenceError(f"{field} is not a valid calendar date-time: {value!r}") from exc


def _bypass_actor_keys(value: object) -> list[tuple[str, int, str]]:
    _require(isinstance(value, list), "bypass_actors must be an array")
    keys: list[tuple[str, int, str]] = []
    for actor in value:
        _require(isinstance(actor, Mapping), "bypass actor must be an object")
        actor_type = actor.get("actor_type")
        actor_id = actor.get("actor_id")
        bypass_mode = actor.get("bypass_mode")
        _require(isinstance(actor_type, str), "bypass actor type must be a string")
        _require(
            actor_id is None or (isinstance(actor_id, int) and not isinstance(actor_id, bool)),
            "bypass actor id must be an integer or null",
        )
        _require(isinstance(bypass_mode, str), "bypass mode must be a string")
        keys.append((actor_type, -1 if actor_id is None else actor_id, bypass_mode))
    _require(keys == sorted(set(keys)), "bypass actors must be sorted and unique")
    return keys


def _validate_semantics(value: Mapping[str, object]) -> None:
    repository = value["repository"]
    default_branch = value["default_branch"]
    _validate_rfc3339_timestamp(value.get("observed_at"), "observed_at")
    source = value["source"]
    policy = value["policy"]
    observation = value["observation"]
    _require(isinstance(repository, str), "repository must be a string")
    _require(isinstance(default_branch, str), "default_branch must be a string")
    _require(isinstance(source, Mapping), "source must be an object")
    _require(isinstance(policy, Mapping), "policy must be an object")
    _require(isinstance(observation, Mapping), "observation must be an object")

    reference = source.get("reference")
    _require(isinstance(reference, str), "source reference must be a string")
    reference_match = REFERENCE_RE.fullmatch(reference)
    _require(reference_match is not None, "source reference is unsafe")
    assert reference_match is not None
    observed_repo = f"{reference_match['owner']}/{reference_match['repo']}"
    _require(
        observed_repo == repository,
        "source reference does not match repository",
    )
    observed_ruleset_id = int(reference_match["ruleset"])
    response_digest = source.get("response_digest")
    _require(
        isinstance(response_digest, str)
        and SHA256_RE.fullmatch(response_digest) is not None,
        "source response digest is invalid",
    )

    ruleset_id = observation.get("ruleset_id")
    _require(
        ruleset_id == observed_ruleset_id,
        "source reference does not match observed ruleset",
    )
    _require(observation.get("enforcement") == "active", "ruleset is not active")
    _require(observation.get("target") == "branch", "ruleset target is not branch")

    conditions = observation.get("conditions")
    _require(isinstance(conditions, Mapping), "ruleset conditions are missing")
    includes = _sorted_unique_strings(
        conditions.get("ref_name_include"),
        "ref_name_include",
    )
    excludes = _sorted_unique_strings(
        conditions.get("ref_name_exclude"),
        "ref_name_exclude",
    )
    branch_ref = f"refs/heads/{default_branch}"
    _require(
        "~DEFAULT_BRANCH" in includes or branch_ref in includes,
        "ruleset does not cover the default branch",
    )
    _require(
        "~DEFAULT_BRANCH" not in excludes and branch_ref not in excludes,
        "ruleset excludes the default branch",
    )

    policy_contexts = _sorted_unique_strings(
        policy.get("required_status_contexts"),
        "policy required_status_contexts",
    )
    observed_pull_request = observation.get("pull_request")
    _require(
        isinstance(observed_pull_request, Mapping),
        "pull-request rule is missing",
    )
    observed_checks = _status_checks_by_context(observed_pull_request)
    missing_contexts = sorted(set(policy_contexts) - set(observed_checks))
    _require(
        not missing_contexts,
        "required status context is missing: " + ", ".join(missing_contexts),
    )
    if policy.get("require_status_check_source_binding") is True:
        unbound = [
            context
            for context in policy_contexts
            if observed_checks.get(context) is None
        ]
        _require(
            not unbound,
            "required status check source (integration_id) is unbound for: " + ", ".join(unbound),
        )

    minimum_reviews = policy.get("minimum_approving_review_count")
    observed_reviews = observed_pull_request.get("required_approving_review_count")
    _require(
        isinstance(minimum_reviews, int) and isinstance(observed_reviews, int),
        "review count is not an integer",
    )
    _require(
        observed_reviews >= minimum_reviews,
        "required approving review count is below policy",
    )
    _require(
        observed_pull_request.get("require_code_owner_review") is True,
        "code-owner review is not required",
    )
    _require(
        observed_pull_request.get("dismiss_stale_reviews_on_push") is True,
        "stale review dismissal is not required",
    )
    _require(
        observed_pull_request.get("require_last_push_approval") is True,
        "last-push approval is not required",
    )

    bypass_actors = _bypass_actor_keys(observation.get("bypass_actors"))
    if policy.get("forbid_unconditional_bypass") is True:
        unconditional = [
            actor
            for actor in bypass_actors
            if actor[2] in {"always", "exempt"}
        ]
        _require(
            not unconditional,
            "unconditional bypass actor is present",
        )
    allowed_pr_bypass = _allowed_pr_bypass_keys(policy.get("allowed_pull_request_bypass_actors"))
    unapproved_pr_bypass = [
        actor
        for actor in bypass_actors
        if actor[2] == "pull_request" and (actor[0], actor[1]) not in allowed_pr_bypass
    ]
    _require(
        not unapproved_pr_bypass,
        "unapproved pull_request bypass actor is present",
    )


def validate_report(
    value: object,
    *,
    schema: Mapping[str, object],
) -> None:
    _require(isinstance(value, Mapping), "report root must be an object")
    errors = _schema_errors(value, schema)
    if errors:
        raise EnforcementEvidenceError("schema: " + "; ".join(errors))
    _validate_semantics(value)


def check_fixtures(root: Path) -> None:
    schema = _schema(root)
    valid_root = root / FIXTURE_ROOT / "valid"
    invalid_root = root / FIXTURE_ROOT / "invalid"
    valid_paths = sorted(valid_root.glob("*.json"))
    invalid_paths = sorted(invalid_root.glob("*.json"))
    _require(valid_paths, "no valid enforcement-evidence fixtures found")
    _require(invalid_paths, "no invalid enforcement-evidence fixtures found")
    _require(
        {path.name for path in invalid_paths}
        == set(INVALID_FIXTURE_EXPECTATIONS),
        "invalid enforcement-evidence fixture expectation set drifted",
    )
    for path in valid_paths:
        validate_report(_strict_load(path), schema=schema)
    for path in invalid_paths:
        try:
            validate_report(_strict_load(path), schema=schema)
        except EnforcementEvidenceError as exc:
            expected = INVALID_FIXTURE_EXPECTATIONS[path.name]
            _require(
                expected in str(exc),
                f"invalid fixture failed for the wrong reason: {path.name}",
            )
            continue
        raise EnforcementEvidenceError(f"invalid fixture was accepted: {path}")


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument(
        "--report",
        type=Path,
        help="validate one normalized report instead of the committed fixtures",
    )
    parser.add_argument("command", choices=("check",))
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    arguments = _parser().parse_args(argv)
    root = arguments.root.resolve()
    try:
        schema = _schema(root)
        if arguments.report is None:
            check_fixtures(root)
        else:
            report_path = arguments.report
            if not report_path.is_absolute():
                report_path = root / report_path
            validate_report(_strict_load(report_path), schema=schema)
    except EnforcementEvidenceError as exc:
        print(f"enforcement-evidence check failed: {exc}", file=sys.stderr)
        return 1
    print("governance enforcement-evidence fixtures passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
