#!/usr/bin/env python3
"""Zero-dependency deterministic PR-diff referee for the inner-to-outer loop boundary.

Evaluates an exact `base..head` Git diff using Python 3.11+ standard library
only (strictly read-only, never mutates the target repository):
  - OAS-DIFF-01 (Non-Self-Attestation Banner): Flags PRs touching workflows,
    CODEOWNERS, agent instructions/configs, schemas, scripts, or tests so human
    reviewers see immediately that candidate CI cannot self-attest.
  - OAS-DIFF-02 (Anti-Reward-Hacking Gate): Fails closed when a diff injects new
    gate-suppression directives (`# noqa`, `eslint-disable`, `@ts-ignore`,
    `@ts-nocheck`, `pytest.mark.skip`, `.skip(`, `--no-verify`,
    `--passWithNoTests`) or weakens/deletes assertions in existing test files
    without replacement (unless explicitly waived with an auditable reason).
  - OAS-DIFF-03 (Coupled Artifact Closure): Automatically runs
    `check-change-sync.py` when `.agentic-sync.json` (or `--sync-config`) is
    present.

All output is explicitly `authority: "candidate"` / `trusted: false`.

Exit codes:
  0  No FAIL findings (PASS / WARN / WAIVED / NOT_APPLICABLE)
  1  Input error, symlink violation, or Git diff NOT_RUN error
  2  One or more FAIL findings detected
"""

from __future__ import annotations

import argparse
from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass
import importlib.util
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys


SAFE_REF_RE = re.compile(r"^[A-Za-z0-9._/~^@:{}-]{1,200}$")
RULE_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$")
HUNK_RE = re.compile(r"^@@ -\d+(?:,\d+)? \+(?P<new_start>\d+)(?:,\d+)? @@")

ENFORCEMENT_GLOBS = (
    ".github/**",
    "action.yml",
    "CODEOWNERS",
    "Makefile",
    "AGENTS.md",
    "CLAUDE.md",
    "llms.txt",
    ".claude/**",
    ".cursor/**",
    ".vscode/**",
    ".mcp.json",
    ".claude-plugin/**",
    ".cursor-plugin/**",
    ".codex-plugin/**",
    "skills/**",
    "scripts/**",
    "tests/**",
    "standards/**/schema/**",
    "pyproject.toml",
    "requirements-test*",
    ".agentic-sync.json",
)
PROSE_SUFFIXES = frozenset({".md", ".txt", ".html", ".css", ".svg", ".rst"})
BYPASS_FLAG_FILES = frozenset({".yml", ".yaml", ".sh", ".json"})

PY_HASH_SUPPRESS_RE = re.compile(r"#[^\n]*?\b(?:noqa|type:\s*ignore(?!\[)|pragma:\s*no\s*cover)\b")
C_COMMENT_SUPPRESS_RE = re.compile(r"(?://|/\*)[^\n]*?(?:\b(?:eslint-disable|nolint)|@ts-ignore|@ts-nocheck)\b")
RUST_CHAR_LITERAL_RE = re.compile(r"^'(?:\\(?:x[0-9a-fA-F]{2}|u\{[0-9a-fA-F_]{1,6}\}|.)|[^'\\\s])'")
HASH_COMMENT_SUFFIXES = frozenset({".py", ".pyi", ".sh", ".bash", ".zsh", ".yml", ".yaml", ".toml", ".rb"})
SLASH_COMMENT_SUFFIXES = frozenset({".js", ".jsx", ".ts", ".tsx", ".mjs", ".cjs", ".go", ".rs", ".java", ".kt", ".c", ".cc", ".cpp", ".h"})
RUST_ALLOW_RE = re.compile(r"^\s*#\[allow\(")
SKIP_TEST_RE = re.compile(
    r"^\s*@(?:pytest\.mark\.skip|unittest\.skip)\b"
    r"|\b(?:it|test|describe)\.skip\s*\("
    r"|\bt\.Skip(?:f|Now)?\s*\("
)
CLI_BYPASS_RE = re.compile(r"(?<!\w)(?:--no-verify|--passWithNoTests)\b")
ASSERT_LINE_RE = re.compile(
    r"\b(?:assert(?:_[a-z0-9_]+|[A-Z]\w*)?|pytest\.raises|expect)\b"
    r"|\b(?:require|assert)\.(?:NoError|Equal|True|False|Nil|NotNil)\s*\("
    r"|\bt\.(?:Fatal|Error)(?:f)?\s*\("
)

DOES_NOT_PROVE = (
    "Semantic quality of newly written assertions (tautological tests still require human/mutation review)",
    "Runtime behavior, business-logic authorization, or production scale",
    "Trusted merge authority (candidate PR-diff referee only; not self-attesting)",
)


class DiffAuditInputError(ValueError):
    """Fail-closed error for invalid arguments, symlinks, or config schema."""


class DiffAuditNotRunError(RuntimeError):
    """Fail-closed NOT_RUN error when Git diff observation cannot execute."""


@dataclass(frozen=True)
class DiffFinding:
    rule_id: str
    status: str  # PASS | WARN | FAIL | WAIVED | NOT_APPLICABLE
    title: str
    detail: str
    items: list[str]
    waiver_reason: str = ""


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise DiffAuditInputError(message)


def _strip_dot_slash(value: str) -> str:
    res = value.strip()
    while res.startswith("./"):
        res = res[2:]
    return res.lstrip("/")


def _compile_glob(pattern: str) -> re.Pattern[str]:
    pat = _strip_dot_slash(pattern)
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


ENFORCEMENT_PATTERNS = tuple(_compile_glob(g) for g in ENFORCEMENT_GLOBS)


def _parse_waivers(raw_waivers: Sequence[str]) -> dict[str, str]:
    waivers: dict[str, str] = {}
    for entry in raw_waivers:
        if not entry.strip():
            continue
        _require(":" in entry, f"waiver must use 'RULE_ID: non-empty reason' format: {entry!r}")
        rule_id, reason = entry.split(":", 1)
        rule_id = rule_id.strip()
        reason = reason.strip()
        _require(bool(RULE_ID_RE.fullmatch(rule_id)), f"invalid waiver rule_id: {rule_id!r}")
        _require(len(reason) >= 5, f"waiver reason for {rule_id!r} must be at least 5 characters")
        waivers[rule_id] = reason
    return waivers


def _validate_repo_and_refs(repo: Path, base: str, head: str) -> Path:
    if repo.is_symlink() or not repo.is_dir():
        raise DiffAuditInputError(f"repo must be an existing non-symlink directory: {repo}")
    for label, ref in (("base", base), ("head", head)):
        _require(
            bool(SAFE_REF_RE.fullmatch(ref)) and not ref.startswith("-"),
            f"unsafe Git {label} ref: {ref!r}",
        )
    return repo.resolve()


def _run_git(repo: Path, args: Sequence[str], *, git_bin: str, timeout: int) -> bytes:
    resolved_git = shutil.which(git_bin)
    if not resolved_git:
        raise DiffAuditNotRunError(f"NOT_RUN: git binary ({git_bin!r}) not found on PATH")
    try:
        proc = subprocess.run(
            [resolved_git, "-C", str(repo), *args],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=timeout,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        raise DiffAuditNotRunError(f"NOT_RUN: git {' '.join(args[:2])} timed out after {timeout}s") from exc
    if proc.returncode != 0:
        err = proc.stderr.decode("utf-8", errors="replace").strip()
        raise DiffAuditNotRunError(f"NOT_RUN: git {' '.join(args[:2])} failed (exit {proc.returncode}): {err}")
    return proc.stdout


def _has_closing_quote(line: str, start: int, quote_ch: str) -> bool:
    i = start
    n = len(line)
    while i < n:
        ch = line[i]
        if ch == "\\" and i + 1 < n:
            i += 2
            continue
        if ch == quote_ch:
            return True
        i += 1
    return False


def _strip_quoted_strings(line: str, *, rel_path: str = "") -> str:
    """Replace string literal interiors with spaces while preserving comments and Rust lifetimes."""
    suffix = Path(rel_path).suffix.lower() if rel_path else ""
    is_rust = suffix == ".rs"
    stop_hash = suffix in HASH_COMMENT_SUFFIXES or Path(rel_path).name in {"Makefile", "makefile", "GNUmakefile"}
    stop_slash = suffix in SLASH_COMMENT_SUFFIXES

    out: list[str] = []
    quote: str | None = None
    i = 0
    n = len(line)
    while i < n:
        ch = line[i]
        if quote is not None:
            if ch == "\\" and i + 1 < n:
                out.append("  ")
                i += 2
                continue
            if ch == quote:
                out.append(ch)
                quote = None
            else:
                out.append(" ")
            i += 1
            continue
        if stop_hash and ch == "#":
            out.append(line[i:])
            break
        if stop_slash and ch == "/" and i + 1 < n and line[i + 1] in {"/", "*"}:
            out.append(line[i:])
            break
        if ch == "'":
            if is_rust:
                m = RUST_CHAR_LITERAL_RE.match(line[i:])
                if m is not None:
                    span = len(m.group(0))
                    out.append("'" + (" " * (span - 2)) + "'")
                    i += span
                    continue
                # Rust lifetime ('a, 'static, '_): not a string literal
                out.append(ch)
                i += 1
                continue
            if _has_closing_quote(line, i + 1, "'"):
                quote = "'"
            out.append(ch)
            i += 1
            continue
        if ch in {'"', "`"}:
            if _has_closing_quote(line, i + 1, ch):
                quote = ch
            out.append(ch)
            i += 1
            continue
        out.append(ch)
        i += 1
    return "".join(out)


def _strip_line_comments(unquoted: str) -> str:
    for marker in ("#", "//"):
        idx = unquoted.find(marker)
        if idx != -1:
            unquoted = unquoted[:idx]
    return unquoted


def _is_skipped_fixture_or_prose(rel_path: str) -> bool:
    p = Path(rel_path)
    if p.name == "LICENSE" or p.suffix.lower() in PROSE_SUFFIXES:
        return True
    parts = set(p.parts)
    return bool(parts & {"fixtures", "evals", "examples"})


def _is_test_file(rel_path: str) -> bool:
    p = Path(rel_path)
    parts = set(p.parts)
    if parts & {"fixtures", "evals", "examples"}:
        return False
    name = p.name
    if parts & {"tests", "test", "__tests__"}:
        return True
    return (
        name.startswith("test_")
        or "_test." in name
        or ".test." in name
        or ".spec." in name
        or name.endswith(("Test.java", "Tests.java"))
    )


def _check_suppression_on_added_line(rel_path: str, raw_line: str) -> str | None:
    if _is_skipped_fixture_or_prose(rel_path):
        return None
    unquoted = _strip_quoted_strings(raw_line, rel_path=rel_path)
    hit = PY_HASH_SUPPRESS_RE.search(unquoted) or C_COMMENT_SUPPRESS_RE.search(unquoted)
    if hit:
        return hit.group(0).strip()
    if RUST_ALLOW_RE.search(unquoted):
        return "#[allow(...)]"
    skip_hit = SKIP_TEST_RE.search(unquoted)
    if skip_hit:
        return skip_hit.group(0).strip()
    p = Path(rel_path)
    if p.suffix.lower() in BYPASS_FLAG_FILES or p.name in {"Makefile", "makefile", "GNUmakefile"}:
        # In workflow/config files, CLI flags may sit inside YAML string quotes, so scan raw_line excluding comments.
        if not raw_line.lstrip().startswith("#"):
            cli_hit = CLI_BYPASS_RE.search(raw_line)
            if cli_hit:
                return cli_hit.group(0)
    return None


def _is_assertion_line(raw_line: str, *, rel_path: str = "") -> bool:
    stripped = raw_line.strip()
    if not stripped or stripped.startswith(("#", "//", "/*", "*")):
        return False
    code_only = _strip_line_comments(_strip_quoted_strings(raw_line, rel_path=rel_path))
    return ASSERT_LINE_RE.search(code_only) is not None


def _evaluate_reward_hacking_diff(
    unified_diff_text: str,
    *,
    waivers: Mapping[str, str],
) -> DiffFinding:
    suppression_hits: list[str] = []
    assert_counts: dict[str, list[int]] = {}  # rel_path -> [removed, added]

    current_file: str | None = None
    old_file: str | None = None
    new_lineno = 0

    for line in unified_diff_text.splitlines():
        if line.startswith("diff --git "):
            current_file = None
            old_file = None
            new_lineno = 0
            continue
        if line.startswith("--- "):
            raw_old = line[4:].strip()
            old_file = raw_old[2:] if raw_old.startswith("a/") else None
            continue
        if line.startswith("+++ "):
            raw_new = line[4:].strip()
            if raw_new == "/dev/null":
                current_file = old_file
            elif raw_new.startswith("b/"):
                current_file = raw_new[2:]
            else:
                current_file = None
            continue
        hunk_match = HUNK_RE.match(line)
        if hunk_match:
            new_lineno = int(hunk_match.group("new_start"))
            continue
        if current_file is None:
            continue

        if line.startswith("+") and not line.startswith("+++"):
            added_body = line[1:]
            sup = _check_suppression_on_added_line(current_file, added_body)
            if sup is not None:
                suppression_hits.append(f"{current_file}:{new_lineno} (added `{sup}`)")
            if _is_test_file(current_file) and _is_assertion_line(added_body, rel_path=current_file):
                assert_counts.setdefault(current_file, [0, 0])[1] += 1
            new_lineno += 1
        elif line.startswith("-") and not line.startswith("---"):
            removed_body = line[1:]
            if _is_test_file(current_file) and _is_assertion_line(removed_body, rel_path=current_file):
                assert_counts.setdefault(current_file, [0, 0])[0] += 1

    weakened_tests = [
        f"{rel} (removed {rem} assertion line(s), added {add})"
        for rel, (rem, add) in sorted(assert_counts.items())
        if rem > add
    ]
    violations = [*suppression_hits, *weakened_tests]

    if not violations:
        return DiffFinding(
            rule_id="OAS-DIFF-02",
            status="PASS",
            title="Zero reward-hacking suppressions or net test-assertion deletions",
            detail="Inspected added lines for gate-bypass directives and verified test assertion counts did not shrink.",
            items=[],
        )

    if "OAS-DIFF-02" in waivers:
        return DiffFinding(
            rule_id="OAS-DIFF-02",
            status="WAIVED",
            title=f"Reward-hacking / test-shrinkage check explicitly waived ({len(violations)} item(s))",
            detail="Waived with explicit reason; human reviewer must verify intent.",
            items=violations[:20],
            waiver_reason=waivers["OAS-DIFF-02"],
        )

    return DiffFinding(
        rule_id="OAS-DIFF-02",
        status="FAIL",
        title=f"Candidate reward-hacking or test-weakening detected ({len(violations)} item(s))",
        detail="Diff adds gate-suppression/skip directives or reduces assertions in existing test files.",
        items=violations[:20],
    )


def _evaluate_enforcement_surface(changed_files: Sequence[str]) -> DiffFinding:
    touched = [
        rel
        for rel in changed_files
        if any(rx.match(rel) is not None for rx in ENFORCEMENT_PATTERNS)
    ]
    if not touched:
        return DiffFinding(
            rule_id="OAS-DIFF-01",
            status="PASS",
            title="No enforcement or specification surface modified",
            detail="Diff stays outside workflows, CODEOWNERS, agent instructions/settings, scripts, schemas, and tests.",
            items=[],
        )
    return DiffFinding(
        rule_id="OAS-DIFF-01",
        status="WARN",
        title=f"Enforcement surface modified ({len(touched)} file(s) — NOT SELF-ATTESTING)",
        detail="Candidate CI runs from PR-controlled sources and cannot approve changes to its own gates, tests, or agent instructions. Require independent human mechanism review.",
        items=touched[:25],
    )


def _evaluate_coupled_sync(
    repo: Path,
    changed_files: Sequence[str],
    *,
    sync_config: Path | None,
    waivers: Mapping[str, str],
) -> DiffFinding:
    cfg_path = sync_config
    if cfg_path is None:
        default_cfg = repo / ".agentic-sync.json"
        if default_cfg.exists():
            cfg_path = default_cfg
    if cfg_path is None:
        return DiffFinding(
            rule_id="OAS-DIFF-03",
            status="NOT_APPLICABLE",
            title="No .agentic-sync.json coupled-change config in repository",
            detail="Optional: add .agentic-sync.json (see profiles/L1-team/agentic-sync.example.json) to enforce code/test/doc sync.",
            items=[],
        )

    sync_script = Path(__file__).resolve().parent / "check-change-sync.py"
    if sync_script.is_symlink() or not sync_script.is_file():
        raise DiffAuditInputError(f"missing sibling checker: {sync_script}")
    spec = importlib.util.spec_from_file_location("check_change_sync", sync_script)
    if spec is None or spec.loader is None:
        raise DiffAuditInputError(f"unable to load {sync_script}")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)

    try:
        cfg_obj = mod._load_strict_json(cfg_path, "sync config")
        sync_report = mod.evaluate_sync(cfg_obj, changed_files, waivers=waivers)
    except mod.SyncInputError as exc:
        raise DiffAuditInputError(str(exc)) from exc

    derived = str(sync_report["derived_status"])
    failed_items = [
        f"{o['rule_id']}: missing {', '.join(o['missing'])} (triggered by {', '.join(o['triggered_by'][:3])})"
        for o in sync_report["outcomes"]
        if o["status"] == "FAIL"
    ]
    waived_items = [
        f"{o['rule_id']}: {o['waiver_reason']}"
        for o in sync_report["outcomes"]
        if o["status"] == "WAIVED"
    ]
    if derived == "FAIL":
        return DiffFinding(
            rule_id="OAS-DIFF-03",
            status="FAIL",
            title=f"Coupled artifact closure unsatisfied ({len(failed_items)} rule(s))",
            detail="Primary artifacts changed without required coupled tests, docs, or mirrors.",
            items=failed_items,
        )
    if derived == "WAIVED":
        return DiffFinding(
            rule_id="OAS-DIFF-03",
            status="WAIVED",
            title="Coupled artifact closure satisfied via explicit waiver",
            detail="Review waiver justification(s) before merge.",
            items=waived_items,
            waiver_reason="; ".join(waived_items),
        )
    return DiffFinding(
        rule_id="OAS-DIFF-03",
        status="PASS",
        title="All declared coupled artifact sync rules satisfied",
        detail=f"Verified against {cfg_path.name}.",
        items=[],
    )


def audit_pr_diff(
    repo: Path,
    *,
    base: str,
    head: str,
    sync_config: Path | None = None,
    waivers: Mapping[str, str] | None = None,
    git_bin: str = "git",
    timeout: int = 30,
) -> dict[str, object]:
    resolved_repo = _validate_repo_and_refs(repo, base, head)
    waiver_map = dict(waivers or {})

    raw_names = _run_git(
        resolved_repo,
        ["diff", "--name-only", "-z", "--no-renames", f"{base}..{head}"],
        git_bin=git_bin,
        timeout=timeout,
    )
    changed_files = sorted(
        {
            _strip_dot_slash(chunk.decode("utf-8", errors="strict"))
            for chunk in raw_names.split(b"\x00")
            if chunk.strip()
        }
    )

    raw_patch = _run_git(
        resolved_repo,
        ["diff", "-U0", "--no-color", "--no-ext-diff", "--no-renames", f"{base}..{head}"],
        git_bin=git_bin,
        timeout=timeout,
    )
    patch_text = raw_patch.decode("utf-8", errors="replace")

    findings = [
        _evaluate_enforcement_surface(changed_files),
        _evaluate_reward_hacking_diff(patch_text, waivers=waiver_map),
        _evaluate_coupled_sync(resolved_repo, changed_files, sync_config=sync_config, waivers=waiver_map),
    ]
    counts = {
        st: sum(1 for item in findings if item.status == st)
        for st in ("PASS", "WARN", "FAIL", "WAIVED", "NOT_APPLICABLE")
    }
    derived = "FAIL" if counts["FAIL"] > 0 else ("REVIEW_REQUIRED" if counts["WARN"] > 0 or counts["WAIVED"] > 0 else "PASS")
    return {
        "schema_version": "openagenticsecurity.audit.pr-diff-referee.v1",
        "authority": "candidate",
        "trusted": False,
        "base": base,
        "head": head,
        "changed_file_count": len(changed_files),
        "derived_status": derived,
        "counts": counts,
        "findings": [asdict(f) for f in findings],
        "does_not_prove": list(DOES_NOT_PROVE),
    }


def _render_text(report: Mapping[str, object]) -> str:
    counts = report["counts"]
    assert isinstance(counts, Mapping)
    lines = [
        f"=== OpenAgenticSecurity PR-Diff Referee ({report['base']}..{report['head']}) ===",
        f"Authority : {report['authority']} (trusted={str(report['trusted']).lower()}; not self-attesting)",
        (
            f"Summary   : derived={report['derived_status']} | changed_files={report['changed_file_count']} | "
            f"FAIL={counts['FAIL']}  WARN={counts['WARN']}  WAIVED={counts['WAIVED']}  PASS={counts['PASS']}"
        ),
        "",
    ]
    for item in report["findings"]:  # type: ignore[union-attr]
        lines.append(f"  {item['status']:<14} {item['rule_id']:<13} {item['title']}")
        if item["status"] in {"FAIL", "WARN", "WAIVED"}:
            lines.append(f"                 -> {item['detail']}")
            for sub in item["items"][:10]:
                lines.append(f"                    * {sub}")
            if item["waiver_reason"]:
                lines.append(f"                    waiver: {item['waiver_reason']}")
    return "\n".join(lines) + "\n"


def _render_markdown(report: Mapping[str, object]) -> str:
    lines = [
        "### OpenAgenticSecurity PR-Diff Referee (Candidate / Non-Self-Attesting)",
        "",
        f"- **Range**: `{report['base']}..{report['head']}` (`{report['changed_file_count']}` changed file(s))",
        f"- **Derived status**: `{report['derived_status']}` (`authority: candidate`, `trusted: false`)",
        "",
        "| Rule | Status | Summary |",
        "|---|---|---|",
    ]
    for item in report["findings"]:  # type: ignore[union-attr]
        lines.append(f"| `{item['rule_id']}` | **{item['status']}** | {item['title']} |")

    for item in report["findings"]:  # type: ignore[union-attr]
        if item["rule_id"] == "OAS-DIFF-01" and item["status"] == "WARN":
            lines.extend(
                [
                    "",
                    "> **Non-Self-Attestation Notice (`OAS-DIFF-01`)**: This PR modifies enforcement, gate, test, or agent-instruction surfaces. Candidate CI **cannot approve itself** — require independent mechanism review under protected GitHub Rulesets.",
                    "",
                    "Touched enforcement paths: " + ", ".join(f"`{p}`" for p in item["items"][:15]),
                ]
            )
        elif item["status"] in {"FAIL", "WAIVED"} and item["items"]:
            lines.append("")
            lines.append(f"**{item['rule_id']} details**:")
            for sub in item["items"][:12]:
                lines.append(f"- `{sub}`")
            if item["waiver_reason"]:
                lines.append(f"- Waiver reason: `{item['waiver_reason']}`")
    return "\n".join(lines) + "\n"


def _append_summary_file(summary_path: Path, markdown: str) -> None:
    if summary_path.is_symlink():
        raise DiffAuditInputError(f"refusing to write summary to symlink: {summary_path}")
    flags = os.O_WRONLY | os.O_CREAT | os.O_APPEND | getattr(os, "O_NOFOLLOW", 0)
    fd = os.open(summary_path, flags, 0o644)
    with os.fdopen(fd, "w", encoding="utf-8") as handle:
        handle.write(markdown + "\n")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, default=Path("."), help="Target Git repository root (default: .).")
    parser.add_argument("--base", required=True, help="Base Git commit SHA or ref.")
    parser.add_argument("--head", required=True, help="Head Git commit SHA or ref.")
    parser.add_argument("--sync-config", type=Path, help="Optional path to .agentic-sync.json.")
    parser.add_argument(
        "--waiver",
        action="append",
        default=[],
        help="Explicit auditable waiver in 'RULE_ID: reason' format (repeatable).",
    )
    parser.add_argument("--format", choices=("text", "json", "markdown"), default="text")
    parser.add_argument("--summary-file", type=Path, help="Optional file to append Markdown summary (e.g. $GITHUB_STEP_SUMMARY).")
    parser.add_argument("--git-bin", default="git")
    parser.add_argument("--timeout", type=int, default=30)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.timeout < 1:
        print("audit-pr-diff input error: --timeout must be >= 1", file=sys.stderr)
        return 1
    try:
        waivers = _parse_waivers(args.waiver)
        report = audit_pr_diff(
            args.repo,
            base=args.base,
            head=args.head,
            sync_config=args.sync_config,
            waivers=waivers,
            git_bin=args.git_bin,
            timeout=args.timeout,
        )
        if args.summary_file is not None:
            _append_summary_file(args.summary_file, _render_markdown(report))
    except DiffAuditNotRunError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    except (DiffAuditInputError, OSError) as exc:
        print(f"audit-pr-diff input error: {exc}", file=sys.stderr)
        return 1

    if args.format == "json":
        sys.stdout.write(json.dumps(report, indent=2, ensure_ascii=True, sort_keys=True) + "\n")
    elif args.format == "markdown":
        sys.stdout.write(_render_markdown(report))
    else:
        sys.stdout.write(_render_text(report))

    counts = report["counts"]
    assert isinstance(counts, Mapping)
    return 2 if int(counts["FAIL"]) > 0 else 0


if __name__ == "__main__":
    raise SystemExit(main())
