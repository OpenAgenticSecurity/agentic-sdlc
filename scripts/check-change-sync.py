#!/usr/bin/env python3
"""Zero-dependency deterministic coupled-change gate (Axiom 2: ArtifactGraph).

Verifies that when a coding agent or engineer edits a primary artifact (code,
API routes, migrations, standards, or CI), every declared coupled artifact
(tests, docs, STATUS.md, or bilingual mirrors) is updated in the same change
set — or explicitly waived with a non-empty auditable reason.

Pure Python 3.11+ standard library, strictly read-only, fail-closed on
symlinks, duplicate JSON keys, unsafe Git refs, or Git execution errors.

Exit codes:
  0  All triggered sync rules satisfied (or explicitly waived with a reason)
  1  Input error, malformed config, symlink violation, or Git NOT_RUN error
  2  One or more coupled-change obligations unsatisfied (FAIL)
"""

from __future__ import annotations

import argparse
from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys


SAFE_REF_RE = re.compile(r"^[A-Za-z0-9._/~^@:{}-]{1,200}$")
RULE_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$")
DOES_NOT_PROVE = (
    "Semantic correctness of the updated tests, docs, or mirrors",
    "Runtime behavior or coverage of undeclared implicit couplings",
    "Trusted merge authority (candidate read-only check only; not self-attesting)",
)


class SyncInputError(ValueError):
    """Fail-closed error for invalid CLI arguments, paths, or config schema."""


class SyncNotRunError(RuntimeError):
    """Fail-closed NOT_RUN error when Git diff observation cannot execute."""


@dataclass(frozen=True)
class RuleOutcome:
    rule_id: str
    status: str  # PASS | FAIL | WAIVED | NOT_APPLICABLE
    description: str
    triggered_by: list[str]
    missing: list[str]
    waiver_reason: str = ""


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise SyncInputError(message)


def _reject_duplicate_keys(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise SyncInputError(f"duplicate JSON key {key!r}")
        result[key] = value
    return result


def _load_strict_json(path: Path, label: str) -> object:
    if path.is_symlink() or not path.is_file():
        raise SyncInputError(f"{label}: regular non-symlink JSON file required ({path})")
    try:
        raw = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        raise SyncInputError(f"{label}: unable to read UTF-8 file ({exc})") from exc
    try:
        return json.loads(raw, object_pairs_hook=_reject_duplicate_keys)
    except json.JSONDecodeError as exc:
        raise SyncInputError(f"{label}: invalid JSON ({exc.msg})") from exc


def _strip_dot_slash(value: str) -> str:
    res = value.strip().replace("\\", "/")
    while res.startswith("./"):
        res = res[2:]
    return res


def _compile_glob(pattern: str) -> re.Pattern[str]:
    """Compile a POSIX glob supporting `*`, `?`, and `**` deterministically."""
    _require(isinstance(pattern, str) and bool(pattern.strip()), "glob pattern must be a non-empty string")
    pat = _strip_dot_slash(pattern).lstrip("/")
    out: list[str] = ["^"]
    i = 0
    n = len(pat)
    while i < n:
        ch = pat[i]
        if ch == "*":
            if i + 1 < n and pat[i + 1] == "*":
                if i + 2 < n and pat[i + 2] == "/":
                    out.append("(?:.*/)?")
                    i += 3
                else:
                    out.append(".*")
                    i += 2
            else:
                out.append("[^/]*")
                i += 1
        elif ch == "?":
            out.append("[^/]")
            i += 1
        else:
            out.append(re.escape(ch))
            i += 1
    out.append("$")
    return re.compile("".join(out))


def _matches_any(rel_path: str, compiled: Sequence[re.Pattern[str]]) -> bool:
    return any(rx.match(rel_path) is not None for rx in compiled)


def _normalize_changed_paths(raw_paths: Sequence[str]) -> list[str]:
    cleaned: set[str] = set()
    for item in raw_paths:
        raw = item.strip().replace("\\", "/")
        if not raw:
            continue
        _require(not raw.startswith("/"), f"unsafe changed path: {item!r}")
        norm = _strip_dot_slash(raw)
        if not norm:
            continue
        _require(".." not in norm.split("/"), f"unsafe changed path: {item!r}")
        cleaned.add(norm)
    return sorted(cleaned)


def _git_changed_files(repo: Path, *, base: str, head: str, git_bin: str = "git", timeout: int = 30) -> list[str]:
    if repo.is_symlink() or not repo.is_dir():
        raise SyncInputError(f"repo must be an existing non-symlink directory: {repo}")
    for label, ref in (("base", base), ("head", head)):
        _require(
            bool(SAFE_REF_RE.fullmatch(ref)) and not ref.startswith("-"),
            f"unsafe Git {label} ref: {ref!r}",
        )
    resolved_git = shutil.which(git_bin)
    if not resolved_git:
        raise SyncNotRunError(f"NOT_RUN: git binary ({git_bin!r}) not found on PATH")
    try:
        proc = subprocess.run(
            [resolved_git, "-C", str(repo.resolve()), "diff", "--name-only", "-z", "--no-renames", f"{base}..{head}"],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=timeout,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        raise SyncNotRunError(f"NOT_RUN: git diff timed out after {timeout}s") from exc
    if proc.returncode != 0:
        err = proc.stderr.decode("utf-8", errors="replace").strip()
        raise SyncNotRunError(f"NOT_RUN: git diff failed (exit {proc.returncode}): {err}")
    raw_items = [chunk.decode("utf-8", errors="strict") for chunk in proc.stdout.split(b"\x00") if chunk]
    return _normalize_changed_paths(raw_items)


def _parse_waivers(raw_waivers: Sequence[str]) -> dict[str, str]:
    waivers: dict[str, str] = {}
    for entry in raw_waivers:
        _require(":" in entry, f"waiver must use 'RULE_ID: non-empty reason' format: {entry!r}")
        rule_id, reason = entry.split(":", 1)
        rule_id = rule_id.strip()
        reason = reason.strip()
        _require(bool(RULE_ID_RE.fullmatch(rule_id)), f"invalid waiver rule_id: {rule_id!r}")
        _require(len(reason) >= 5, f"waiver reason for {rule_id!r} must be at least 5 characters")
        waivers[rule_id] = reason
    return waivers


def _validate_glob_list(value: object, label: str) -> list[re.Pattern[str]]:
    _require(isinstance(value, list) and bool(value), f"{label} must be a non-empty list of glob patterns")
    assert isinstance(value, list)
    return [_compile_glob(pat) for pat in value]


def evaluate_sync(
    config_obj: object,
    changed_files: Sequence[str],
    *,
    waivers: Mapping[str, str] | None = None,
) -> dict[str, object]:
    _require(isinstance(config_obj, Mapping), "config root must be a JSON object")
    assert isinstance(config_obj, Mapping)
    rules_raw = config_obj.get("rules")
    _require(isinstance(rules_raw, list) and bool(rules_raw), "config.rules must be a non-empty list")
    assert isinstance(rules_raw, list)

    normalized_files = _normalize_changed_paths(changed_files)
    changed_set = set(normalized_files)
    waiver_map = dict(waivers or {})
    seen_ids: set[str] = set()
    outcomes: list[RuleOutcome] = []

    for rule in rules_raw:
        _require(isinstance(rule, Mapping), "each rule must be a JSON object")
        assert isinstance(rule, Mapping)
        rule_id = rule.get("id")
        _require(isinstance(rule_id, str) and bool(RULE_ID_RE.fullmatch(rule_id)), f"invalid rule id: {rule_id!r}")
        assert isinstance(rule_id, str)
        _require(rule_id not in seen_ids, f"duplicate rule id: {rule_id!r}")
        seen_ids.add(rule_id)

        description = rule.get("description")
        _require(isinstance(description, str) and bool(description.strip()), f"{rule_id}: description required")
        assert isinstance(description, str)

        when_patterns = _validate_glob_list(rule.get("when_changed"), f"{rule_id}.when_changed")
        exclude_raw = rule.get("exclude", [])
        _require(isinstance(exclude_raw, list), f"{rule_id}.exclude must be a list")
        assert isinstance(exclude_raw, list)
        exclude_patterns = [_compile_glob(pat) for pat in exclude_raw]

        require_any_raw = rule.get("require_any")
        require_mirror_raw = rule.get("require_mirror")
        _require(
            (require_any_raw is not None) ^ (require_mirror_raw is not None),
            f"{rule_id}: declare exactly one of 'require_any' or 'require_mirror'",
        )

        triggered = [
            f
            for f in normalized_files
            if _matches_any(f, when_patterns) and not _matches_any(f, exclude_patterns)
        ]

        if not triggered:
            outcomes.append(
                RuleOutcome(
                    rule_id=rule_id,
                    status="NOT_APPLICABLE",
                    description=description,
                    triggered_by=[],
                    missing=[],
                )
            )
            continue

        missing: list[str] = []
        if require_any_raw is not None:
            req_patterns = _validate_glob_list(require_any_raw, f"{rule_id}.require_any")
            satisfied = any(_matches_any(f, req_patterns) for f in normalized_files)
            if not satisfied:
                missing = [str(p) for p in require_any_raw]
        else:
            _require(isinstance(require_mirror_raw, Mapping), f"{rule_id}.require_mirror must be an object")
            assert isinstance(require_mirror_raw, Mapping)
            from_sfx = require_mirror_raw.get("from_suffix")
            to_sfx = require_mirror_raw.get("to_suffix")
            bidirectional = require_mirror_raw.get("bidirectional", False)
            _require(
                isinstance(from_sfx, str) and bool(from_sfx) and isinstance(to_sfx, str) and bool(to_sfx),
                f"{rule_id}.require_mirror needs non-empty string 'from_suffix' and 'to_suffix'",
            )
            _require(isinstance(bidirectional, bool), f"{rule_id}.require_mirror.bidirectional must be boolean")
            assert isinstance(from_sfx, str) and isinstance(to_sfx, str)
            missing_set: set[str] = set()
            for f in triggered:
                if f.endswith(to_sfx):
                    if bidirectional:
                        partner = f[: -len(to_sfx)] + from_sfx
                        if partner not in changed_set:
                            missing_set.add(partner)
                elif f.endswith(from_sfx):
                    partner = f[: -len(from_sfx)] + to_sfx
                    if partner not in changed_set:
                        missing_set.add(partner)
            missing = sorted(missing_set)

        if not missing:
            status = "PASS"
            waiver_reason = ""
        elif rule_id in waiver_map:
            status = "WAIVED"
            waiver_reason = waiver_map[rule_id]
        else:
            status = "FAIL"
            waiver_reason = ""

        outcomes.append(
            RuleOutcome(
                rule_id=rule_id,
                status=status,
                description=description,
                triggered_by=triggered,
                missing=missing,
                waiver_reason=waiver_reason,
            )
        )

    counts = {
        state: sum(1 for item in outcomes if item.status == state)
        for state in ("PASS", "FAIL", "WAIVED", "NOT_APPLICABLE")
    }
    derived = "FAIL" if counts["FAIL"] > 0 else ("WAIVED" if counts["WAIVED"] > 0 else "PASS")
    return {
        "schema_version": "openagenticsecurity.sync.change-sync-report.v1",
        "authority": "candidate",
        "trusted": False,
        "changed_file_count": len(normalized_files),
        "derived_status": derived,
        "counts": counts,
        "outcomes": [asdict(item) for item in outcomes],
        "does_not_prove": list(DOES_NOT_PROVE),
    }


def _render_text(report: Mapping[str, object]) -> str:
    counts = report["counts"]
    assert isinstance(counts, Mapping)
    outcomes = report["outcomes"]
    assert isinstance(outcomes, list)
    lines = [
        "=== OpenAgenticSecurity Coupled-Change Sync Check ===",
        f"Authority : {report['authority']} (trusted={str(report['trusted']).lower()}; read-only)",
        (
            f"Summary   : derived={report['derived_status']} | changed_files={report['changed_file_count']} | "
            f"FAIL={counts['FAIL']}  WAIVED={counts['WAIVED']}  PASS={counts['PASS']}  N/A={counts['NOT_APPLICABLE']}"
        ),
        "",
    ]
    for item in outcomes:
        lines.append(f"  {item['status']:<14} {item['rule_id']:<20} {item['description']}")
        if item["status"] == "FAIL":
            lines.append(f"                 triggered by: {', '.join(item['triggered_by'][:5])}")
            lines.append(f"                 missing sync: {', '.join(item['missing'][:5])}")
            lines.append(
                f"                 fix: update coupled artifact(s) above or pass --waiver \"{item['rule_id']}: <reason>\""
            )
        elif item["status"] == "WAIVED":
            lines.append(f"                 waiver: {item['waiver_reason']}")
    return "\n".join(lines) + "\n"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True, help="Path to declarative sync config JSON.")
    parser.add_argument("--repo", type=Path, default=Path("."), help="Git repository root for --base/--head mode.")
    parser.add_argument("--base", help="Base Git revision (used with --head).")
    parser.add_argument("--head", help="Head Git revision (used with --base).")
    parser.add_argument(
        "--changed",
        action="append",
        default=[],
        help="Explicit repo-relative changed file path (repeatable; skips Git diff).",
    )
    parser.add_argument(
        "--changed-files-file",
        type=Path,
        help="Path to newline-delimited list of changed files (skips Git diff).",
    )
    parser.add_argument(
        "--waiver",
        action="append",
        default=[],
        help="Explicit auditable waiver in 'RULE_ID: reason' format (repeatable).",
    )
    parser.add_argument("--format", choices=("text", "json"), default="text")
    parser.add_argument("--git-bin", default="git")
    parser.add_argument("--timeout", type=int, default=30)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        config_obj = _load_strict_json(args.config, "sync config")
        waivers = _parse_waivers(args.waiver)

        if args.changed or args.changed_files_file is not None:
            _require(not args.base and not args.head, "do not combine --base/--head with --changed/--changed-files-file")
            changed = list(args.changed)
            if args.changed_files_file is not None:
                if args.changed_files_file.is_symlink() or not args.changed_files_file.is_file():
                    raise SyncInputError(f"regular non-symlink file required: {args.changed_files_file}")
                changed.extend(args.changed_files_file.read_text(encoding="utf-8").splitlines())
        else:
            _require(bool(args.base) and bool(args.head), "provide either --base and --head, or --changed / --changed-files-file")
            changed = _git_changed_files(
                args.repo,
                base=args.base,
                head=args.head,
                git_bin=args.git_bin,
                timeout=args.timeout,
            )

        report = evaluate_sync(config_obj, changed, waivers=waivers)
    except SyncNotRunError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    except SyncInputError as exc:
        print(f"check-change-sync input error: {exc}", file=sys.stderr)
        return 1

    if args.format == "json":
        sys.stdout.write(json.dumps(report, indent=2, ensure_ascii=True, sort_keys=True) + "\n")
    else:
        sys.stdout.write(_render_text(report))

    counts = report["counts"]
    assert isinstance(counts, Mapping)
    return 2 if int(counts["FAIL"]) > 0 else 0


if __name__ == "__main__":
    raise SystemExit(main())
