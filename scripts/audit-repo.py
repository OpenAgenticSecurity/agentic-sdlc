#!/usr/bin/env python3
"""Zero-dependency, read-only Agentic SDLC self-audit for any local repository.

Inspects a repository across three defense layers using Python 3.11+ standard
library only (no `pip install` required, never writes to the target repository):
  - Layer 1 (Agent Context): AGENTS.md / CLAUDE.md, worktree .gitignore hygiene,
    reality anchor (STATUS.md / MATURITY.md), and PR evidence template.
  - Layer 2 (Local & Supply-Chain Guardrails): Git hook guardrails, Agent
    instruction-file & IDE/MCP poisoning checks (hidden Unicode, `folderOpen`,
    endpoint hijacks), GitHub Actions 40-char SHA pinning, workflow permissions
    / persist-credentials / Comment-and-Control injection / dedicated SAST
    presence, CODEOWNERS placeholder checks, and Day-0 multi-language static
    smoke checks (Python AST + JS/TS, Go, Rust, Java).
  - Layer 3 (GitHub Merge Boundary, opt-in via `--github` or
    `--github-ruleset-file`): live read-only GitHub Ruleset check against AI
    post-approval pushes, spoofable unbound status checks, and unconditional
    bypass actors.

All output is explicitly `authority: "candidate"` / `trusted: false` and never
collapses `NOT_RUN`, `WARN`, or `FAIL` into `PASS`.

Exit codes:
  0  No FAIL findings (and requested external observations ran cleanly)
  1  Input error, symlink violation, or requested check could not run (NOT_RUN)
  2  One or more FAIL findings detected
"""

from __future__ import annotations

import argparse
import ast
from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys


REPO_RE = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")
SHA_PIN_RE = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_./-]+@[0-9a-f]{40}$")
DOCKER_DIGEST_RE = re.compile(r"^docker://[^\s@]+@sha256:[0-9a-f]{64}$")
USES_LINE_RE = re.compile(r"^(?P<indent>\s*)(?:-\s+)?uses\s*:\s*(?P<val>[^#\n]+?)(?:\s+#.*)?$")
JOB_HEADER_RE = re.compile(r"^  (?P<name>[A-Za-z0-9_.-]+)\s*:\s*(?:#.*)?$")
SECRET_ENV_RE = re.compile(
    r"(?:SECRET|TOKEN|PASSWORD|PASSWD|API_KEY|APIKEY|PRIVATE_KEY|JWT_KEY|SIGNING_KEY|AUTH_KEY)",
    re.IGNORECASE,
)

SKIP_DIRS = frozenset(
    {
        ".git",
        ".venv",
        "venv",
        "env",
        "node_modules",
        "__pycache__",
        ".pytest_cache",
        ".mypy_cache",
        ".ruff_cache",
        ".worktrees",
        "worktrees",
        ".claude",
        ".cursor",
        ".codex",
        "dist",
        "build",
        "target",
        "vendor",
    }
)
TEST_DIR_NAMES = frozenset({"tests", "test", "__tests__", "fixtures", "examples", "evals", "benches"})
WORKTREE_IGNORES = (
    ".worktrees/",
    ".claude/worktrees/",
    ".cursor/worktrees/",
    ".codex/worktrees/",
)
MAX_PY_FILE_BYTES = 2 * 1024 * 1024
MAX_PY_FILES = 2000
SAFE_YAML_LOADERS = frozenset({"SafeLoader", "CSafeLoader", "BaseLoader", "CBaseLoader"})
UNSAFE_SUBPROCESS_FUNCS = frozenset(
    {"run", "Popen", "call", "check_call", "check_output", "getoutput", "getstatusoutput"}
)
JS_TS_SUFFIXES = frozenset({".js", ".jsx", ".ts", ".tsx", ".mjs", ".cjs"})
JS_SINK_RE = re.compile(r"\bdangerouslySetInnerHTML\b|\beval\s*\(|\bnew\s+Function\s*\(")
GO_TLS_RE = re.compile(r"\bInsecureSkipVerify\s*:\s*true\b")
GO_SHELL_RE = re.compile(r"""\bexec\.Command(?:Context)?\s*\([^)\n]*["'](?:sh|bash|/bin/sh|/bin/bash)["']\s*,\s*["']-c["']""")
RUST_TLS_RE = re.compile(r"\bdanger_accept_invalid_certs\s*\(\s*true\s*\)")
RUST_SHELL_RE = re.compile(r"""\bCommand::new\s*\(\s*"(?:sh|bash|/bin/sh|/bin/bash)"\s*\)\s*\.arg\s*\(\s*"-c"\s*\)""")
JAVA_EXEC_RE = re.compile(r"\bRuntime\.getRuntime\(\)\.exec\s*\(")
JAVA_DESER_RE = re.compile(r"\bnew\s+ObjectInputStream\s*\(")
UNTRUSTED_GH_EXPR_RE = re.compile(
    r"\$\{\{\s*github\.(?:event\.(?:issue|pull_request|comment|discussion|review|review_comment)\.(?:title|body)"
    r"|event\.commits\[[^\]]*\]\.message|head_ref)\b"
)
PR_TARGET_RE = re.compile(r"^\s*pull_request_target\s*:")
PR_HEAD_CHECKOUT_RE = re.compile(r"^\s*ref\s*:.*github\.event\.pull_request\.head\.")
DEDICATED_SAST_RE = re.compile(
    r"\b(?:ruff|bandit|semgrep|codeql|gitleaks|trufflehog|govulncheck|golangci-lint"
    r"|cargo\s+audit|clippy|eslint|tsc|scorecard|shellcheck|actionlint|pip-audit|npm\s+audit"
    r"|deps\s+security-audit|verify-all)\b",
    re.IGNORECASE,
)
API_ENDPOINT_HIJACK_RE = re.compile(
    r"""\b(?:ANTHROPIC_BASE_URL|OPENAI_BASE_URL)\s*[:=]\s*['"]?https?://""",
    re.IGNORECASE,
)
SILENT_HIDE_RE = re.compile(
    r"\bdo\s+not\s+(?:read|display|show|inspect|quote)\b",
    re.IGNORECASE,
)
SILENT_RUN_RE = re.compile(
    r"\b(?:run|execute)\b[^\n]{0,80}\b(?:without\s+(?:asking|confirmation|displaying)|automatically\s+without)\b",
    re.IGNORECASE,
)
MCP_SHELL_EXEC_RE = re.compile(
    r"(?:curl\s+[^|]+\|\s*(?:sh|bash)|wget\s+[^|]+\|\s*(?:sh|bash)|\b(?:sh|bash)\s+-c\b)",
    re.IGNORECASE,
)
ROOT_INSTRUCTION_FILES = (
    "AGENTS.md",
    "CLAUDE.md",
    "llms.txt",
    ".cursorrules",
    ".github/copilot-instructions.md",
)
INSTRUCTION_SCAN_DIRS = (
    ".cursor/rules",
    "skills",
    ".agents/skills",
    ".claude/skills",
    ".cursor/skills",
)
DOES_NOT_PROVE = (
    "Runtime behavior, business-logic authorization, or production scale (P99 load)",
    "Deep inter-procedural dataflow/taint SAST (source checks here are Day-0 smoke checks only; wire Ruff S / Semgrep / CodeQL / Bandit / gitleaks / deps)",
    "Trusted merge authority (candidate read-only audit only; not self-attesting)",
)


class AuditInputError(ValueError):
    """Fail-closed error for invalid arguments, paths, or malformed inputs."""


class AuditNotRunError(RuntimeError):
    """Fail-closed NOT_RUN error when an explicitly requested check cannot run."""


@dataclass(frozen=True)
class Finding:
    rule_id: str
    layer: str
    status: str  # PASS | WARN | FAIL | NOT_RUN | NOT_APPLICABLE
    title: str
    detail: str
    location: str = ""
    remediation: str = ""


def _reject_duplicate_keys(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise AuditInputError(f"duplicate JSON key {key!r}")
        result[key] = value
    return result


def _strict_json_loads(raw_bytes: bytes, label: str) -> object:
    try:
        text = raw_bytes.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise AuditInputError(f"{label}: invalid UTF-8") from exc
    try:
        return json.loads(text, object_pairs_hook=_reject_duplicate_keys)
    except json.JSONDecodeError as exc:
        raise AuditInputError(f"{label}: invalid JSON ({exc.msg})") from exc


def _validate_repo_slug(slug: str) -> str:
    if not REPO_RE.fullmatch(slug) or len(slug) > 200:
        raise AuditInputError(f"unsafe GitHub repository identifier: {slug!r}")
    owner, name = slug.split("/", 1)
    if owner in {".", ".."} or name in {".", ".."}:
        raise AuditInputError(f"unsafe GitHub repository identifier: {slug!r}")
    return slug


def _read_regular_text(root: Path, rel: str) -> str | None:
    candidate = root / rel
    if not candidate.exists():
        return None
    if candidate.is_symlink() or not candidate.is_file():
        return None
    try:
        resolved = candidate.resolve()
        resolved.relative_to(root)
    except (OSError, ValueError):
        return None
    try:
        return resolved.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return None


def _run_cmd(argv: Sequence[str], *, cwd: Path | None = None, timeout: int = 15) -> subprocess.CompletedProcess[bytes]:
    return subprocess.run(
        list(argv),
        cwd=str(cwd) if cwd is not None else None,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=timeout,
        check=False,
    )


def _infer_github_repo(target: Path) -> str | None:
    git_bin = shutil.which("git")
    if not git_bin or not (target / ".git").exists():
        return None
    try:
        proc = _run_cmd([git_bin, "-C", str(target), "remote", "get-url", "origin"], timeout=10)
    except subprocess.TimeoutExpired:
        return None
    if proc.returncode != 0:
        return None
    url = proc.stdout.decode("utf-8", errors="replace").strip()
    patterns = (
        re.compile(r"^https?://github\.com/(?P<slug>[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+?)(?:\.git)?/?$"),
        re.compile(r"^git@github\.com:(?P<slug>[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+?)(?:\.git)?$"),
        re.compile(r"^ssh://git@github\.com/(?P<slug>[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+?)(?:\.git)?/?$"),
    )
    for rx in patterns:
        match = rx.fullmatch(url)
        if match:
            slug = match.group("slug")
            try:
                return _validate_repo_slug(slug)
            except AuditInputError:
                return None
    return None


def _audit_layer1_context(target: Path) -> list[Finding]:
    findings: list[Finding] = []

    agents_txt = _read_regular_text(target, "AGENTS.md")
    claude_txt = _read_regular_text(target, "CLAUDE.md")
    has_agents = bool(agents_txt and agents_txt.strip())
    has_claude = bool(claude_txt and claude_txt.strip())
    if has_agents and has_claude:
        findings.append(
            Finding(
                rule_id="OAS-CTX-01",
                layer="L1",
                status="PASS",
                title="Agent instruction files present",
                detail="Both AGENTS.md and CLAUDE.md are present and non-empty.",
                location="AGENTS.md, CLAUDE.md",
            )
        )
    elif has_agents or has_claude:
        present = "AGENTS.md" if has_agents else "CLAUDE.md"
        missing = "CLAUDE.md" if has_agents else "AGENTS.md"
        findings.append(
            Finding(
                rule_id="OAS-CTX-01",
                layer="L1",
                status="WARN",
                title="Only one agent instruction file present",
                detail=f"{present} exists, but {missing} is missing (tools like Claude Code / Codex / Cursor read different files).",
                location=present,
                remediation="Run bootstrap.sh --profile L0 --target <repo> (never overwrites existing files).",
            )
        )
    else:
        findings.append(
            Finding(
                rule_id="OAS-CTX-01",
                layer="L1",
                status="FAIL",
                title="Missing AGENTS.md and CLAUDE.md",
                detail="Coding agents have no repository-level scope, security, or verification instructions.",
                location="AGENTS.md",
                remediation="Run: bash scripts/bootstrap.sh --profile L0 --target <repo>",
            )
        )

    gitignore_txt = _read_regular_text(target, ".gitignore") or ""
    missing_wt = [pat for pat in WORKTREE_IGNORES if pat not in gitignore_txt]
    if ".worktrees/" in missing_wt:
        findings.append(
            Finding(
                rule_id="OAS-CTX-02",
                layer="L1",
                status="FAIL",
                title="Worktree directories not ignored in .gitignore",
                detail="Multi-agent worktrees (.worktrees/, .claude/worktrees/, .cursor/worktrees/, .codex/worktrees/) can be accidentally staged and committed.",
                location=".gitignore",
                remediation="Append profiles/L0-solo/.gitignore.snippet or run bootstrap.sh --profile L0.",
            )
        )
    elif missing_wt:
        findings.append(
            Finding(
                rule_id="OAS-CTX-02",
                layer="L1",
                status="WARN",
                title="Partial multi-tool worktree .gitignore coverage",
                detail="Missing worktree ignore pattern(s): " + ", ".join(missing_wt),
                location=".gitignore",
                remediation="Append the missing tool worktree patterns to .gitignore.",
            )
        )
    else:
        findings.append(
            Finding(
                rule_id="OAS-CTX-02",
                layer="L1",
                status="PASS",
                title="Multi-tool worktree namespaces ignored",
                detail="All standard worktree directories are excluded in .gitignore.",
                location=".gitignore",
            )
        )

    reality_candidates = ("docs/architecture/STATUS.md", "STATUS.md", "MATURITY.md")
    found_reality = next((rel for rel in reality_candidates if (_read_regular_text(target, rel) or "").strip()), "")
    if found_reality:
        findings.append(
            Finding(
                rule_id="OAS-CTX-03",
                layer="L1",
                status="PASS",
                title="Implementation reality anchor present",
                detail=f"Found reality/maturity ledger at {found_reality}.",
                location=found_reality,
            )
        )
    else:
        findings.append(
            Finding(
                rule_id="OAS-CTX-03",
                layer="L1",
                status="WARN",
                title="No STATUS.md / implementation reality ledger",
                detail="Without STATUS.md, agents treat stale design docs as implemented code and hallucinate deleted or planned modules.",
                location="docs/architecture/STATUS.md",
                remediation="Create docs/architecture/STATUS.md from profiles/L0-solo/STATUS.md.",
            )
        )

    pr_tmpl = _read_regular_text(target, ".github/pull_request_template.md")
    if pr_tmpl and re.search(r"Verification|Validation|Test Plan|Tests|验证|测试", pr_tmpl):
        findings.append(
            Finding(
                rule_id="OAS-CTX-04",
                layer="L1",
                status="PASS",
                title="PR template requires verification evidence",
                detail="Pull request template asks contributors and agents for verification evidence.",
                location=".github/pull_request_template.md",
            )
        )
    else:
        findings.append(
            Finding(
                rule_id="OAS-CTX-04",
                layer="L1",
                status="WARN",
                title="Missing evidence-first PR template",
                detail="PRs do not prompt for exact verification commands, exit codes, NOT_RUN disclosure, or negative security tests.",
                location=".github/pull_request_template.md",
                remediation="Copy profiles/L0-solo/pull_request_template.md to .github/pull_request_template.md.",
            )
        )

    return findings


def _audit_layer2_git_guardrails(target: Path) -> Finding:
    if not (target / ".git").exists():
        return Finding(
            rule_id="OAS-GIT-01",
            layer="L2",
            status="NOT_APPLICABLE",
            title="Local Git hook guardrails",
            detail="Target directory has no .git entry; local Git hook inspection is not applicable.",
            location=".git",
        )
    git_bin = shutil.which("git")
    if not git_bin:
        return Finding(
            rule_id="OAS-GIT-01",
            layer="L2",
            status="NOT_RUN",
            title="Local Git hook guardrails",
            detail="git binary not found on PATH; unable to inspect core.hooksPath.",
            location=".git",
        )
    try:
        proc = _run_cmd([git_bin, "-C", str(target), "config", "--get", "core.hooksPath"], timeout=10)
    except subprocess.TimeoutExpired:
        return Finding(
            rule_id="OAS-GIT-01",
            layer="L2",
            status="NOT_RUN",
            title="Local Git hook guardrails",
            detail="git config timed out while checking core.hooksPath.",
            location=".git",
        )
    hooks_path = proc.stdout.decode("utf-8", errors="replace").strip() if proc.returncode == 0 else ""
    if "agentic-sdlc-managed-hooks" in hooks_path:
        return Finding(
            rule_id="OAS-GIT-01",
            layer="L2",
            status="PASS",
            title="Managed local Git guardrails installed",
            detail=f"core.hooksPath points to {hooks_path} (blocks direct commits/pushes on main).",
            location=".git/config",
        )
    return Finding(
        rule_id="OAS-GIT-01",
        layer="L2",
        status="WARN",
        title="No local Git guardrail preventing direct commits/pushes to main",
        detail="Coding agents can accidentally commit directly on main or in a dirty primary checkout.",
        location=".git/config",
        remediation="Run: python3 scripts/workspace-git.py guardrails --apply (inside target repo)",
    )


def _strip_quotes(val: str) -> str:
    val = val.strip()
    if len(val) >= 2 and val[0] == val[-1] and val[0] in {"'", '"'}:
        return val[1:-1].strip()
    return val


def _is_pinned_action_ref(ref: str) -> bool:
    if ref.startswith("./") or ref.startswith(".\\"):
        return True
    if ref.startswith("docker://"):
        return bool(DOCKER_DIGEST_RE.fullmatch(ref))
    return bool(SHA_PIN_RE.fullmatch(ref))


def _audit_layer2_workflows(target: Path) -> list[Finding]:
    wf_dir = target / ".github" / "workflows"
    if not wf_dir.is_dir() or wf_dir.is_symlink():
        return [
            Finding(
                rule_id="OAS-CI-01",
                layer="L2",
                status="WARN",
                title="No GitHub Actions workflows found",
                detail="Repository has no .github/workflows/ directory to enforce fail-closed CI checks.",
                location=".github/workflows/",
                remediation="Install a fail-closed L1 workflow: bash scripts/bootstrap.sh --profile L1 --ci <python|node-ts|rust|generic> --target <repo>",
            )
        ]

    workflows = sorted(
        p
        for p in wf_dir.iterdir()
        if p.is_file() and not p.is_symlink() and p.suffix in {".yml", ".yaml"}
    )
    if not workflows:
        return [
            Finding(
                rule_id="OAS-CI-01",
                layer="L2",
                status="WARN",
                title="No GitHub Actions workflow YAML files found",
                detail=".github/workflows/ exists but contains no .yml or .yaml files.",
                location=".github/workflows/",
                remediation="Install a fail-closed L1 workflow via scripts/bootstrap.sh --profile L1.",
            )
        ]

    unpinned: list[tuple[str, int, str]] = []
    missing_perms: list[str] = []
    missing_persist_false: list[tuple[str, int]] = []
    missing_timeouts: list[tuple[str, int, str]] = []
    ci_injections: list[tuple[str, int, str]] = []
    has_dedicated_sast = False
    calls_make = False

    for wf in workflows:
        rel = wf.relative_to(target).as_posix()
        try:
            wf_text = wf.read_text(encoding="utf-8")
            lines = wf_text.splitlines()
        except (OSError, UnicodeDecodeError):
            continue

        if DEDICATED_SAST_RE.search(wf_text):
            has_dedicated_sast = True
        if re.search(r"\bmake\s+[a-z0-9_-]+", wf_text):
            calls_make = True

        has_pr_target = False
        pr_head_line: int | None = None
        has_top_permissions = False
        in_jobs = False
        current_job: tuple[str, int] | None = None
        current_job_has_timeout = False
        block_scalar_indent: int | None = None

        for idx, line in enumerate(lines, start=1):
            stripped = line.strip()
            indent = len(line) - len(line.lstrip(" "))

            # Inspect raw shell/expression lines for Comment-and-Control injection before skipping block scalars
            if stripped and not stripped.startswith("#"):
                expr_hit = UNTRUSTED_GH_EXPR_RE.search(line)
                if expr_hit:
                    ci_injections.append((rel, idx, expr_hit.group(0).strip()))
                if PR_TARGET_RE.match(line):
                    has_pr_target = True
                if PR_HEAD_CHECKOUT_RE.match(line) and pr_head_line is None:
                    pr_head_line = idx

            if block_scalar_indent is not None:
                if stripped and indent <= block_scalar_indent:
                    block_scalar_indent = None
                else:
                    continue

            if not stripped or stripped.startswith("#"):
                continue

            if indent == 0:
                if re.match(r"^permissions\s*:", line):
                    has_top_permissions = True
                if re.match(r"^jobs\s*:\s*(?:#.*)?$", line):
                    in_jobs = True
                else:
                    if in_jobs and current_job is not None and not current_job_has_timeout:
                        missing_timeouts.append((rel, current_job[1], current_job[0]))
                    in_jobs = False
                    current_job = None
                    current_job_has_timeout = False
            elif in_jobs:
                job_match = JOB_HEADER_RE.match(line)
                if job_match:
                    if current_job is not None and not current_job_has_timeout:
                        missing_timeouts.append((rel, current_job[1], current_job[0]))
                    current_job = (job_match.group("name"), idx)
                    current_job_has_timeout = False
                elif current_job is not None and indent == 4 and re.match(r"^    timeout-minutes\s*:", line):
                    current_job_has_timeout = True

            uses_match = USES_LINE_RE.match(line)
            if uses_match:
                ref = _strip_quotes(uses_match.group("val"))
                if not _is_pinned_action_ref(ref):
                    unpinned.append((rel, idx, ref))
                if ref.startswith("actions/checkout@"):
                    step_indent = len(uses_match.group("indent"))
                    has_persist_false = False
                    for look in range(idx, min(len(lines), idx + 20)):
                        nxt = lines[look]
                        nxt_stripped = nxt.strip()
                        if not nxt_stripped or nxt_stripped.startswith("#"):
                            continue
                        nxt_indent = len(nxt) - len(nxt.lstrip(" "))
                        if nxt_indent <= step_indent and nxt_stripped.startswith("- "):
                            break
                        if nxt_indent < step_indent:
                            break
                        if re.match(r"^\s*persist-credentials\s*:\s*false\b", nxt, re.IGNORECASE):
                            has_persist_false = True
                            break
                    if not has_persist_false:
                        missing_persist_false.append((rel, idx))

            # Track YAML block scalars (e.g. `run: |` or `run: >-`) so shell snippets are not parsed as YAML keys
            if re.search(r":\s*[|>][+-]?\d*\s*(?:#.*)?$", line):
                block_scalar_indent = indent

        if in_jobs and current_job is not None and not current_job_has_timeout:
            missing_timeouts.append((rel, current_job[1], current_job[0]))

        if has_pr_target and pr_head_line is not None:
            ci_injections.append((rel, pr_head_line, "pull_request_target + PR head checkout"))

        if not has_top_permissions:
            missing_perms.append(rel)

    if not has_dedicated_sast and calls_make:
        makefile_txt = _read_regular_text(target, "Makefile") or ""
        if DEDICATED_SAST_RE.search(makefile_txt):
            has_dedicated_sast = True

    findings: list[Finding] = []
    if unpinned:
        preview = "; ".join(f"{rel}:{ln} ({ref})" for rel, ln, ref in unpinned[:5])
        extra = f" (+{len(unpinned) - 5} more)" if len(unpinned) > 5 else ""
        findings.append(
            Finding(
                rule_id="OAS-CI-01",
                layer="L2",
                status="FAIL",
                title=f"Unpinned GitHub Actions ({len(unpinned)} occurrence(s))",
                detail=f"Mutable tags/branches can be silently retargeted in supply-chain attacks: {preview}{extra}",
                location=f"{unpinned[0][0]}:{unpinned[0][1]}",
                remediation="Pin every external Action to a full 40-char commit SHA (see profiles/L1-team/workflows/).",
            )
        )
    else:
        findings.append(
            Finding(
                rule_id="OAS-CI-01",
                layer="L2",
                status="PASS",
                title="All GitHub Actions pinned to immutable digests",
                detail=f"Checked {len(workflows)} workflow file(s); zero mutable Action tag/branch refs found.",
                location=".github/workflows/",
            )
        )

    if missing_perms or missing_persist_false:
        parts: list[str] = []
        first_loc = ".github/workflows/"
        if missing_perms:
            parts.append("missing top-level `permissions:` in " + ", ".join(missing_perms[:4]))
            first_loc = f"{missing_perms[0]}:1"
        if missing_persist_false:
            loc_str = ", ".join(f"{rel}:{ln}" for rel, ln in missing_persist_false[:4])
            parts.append(f"`actions/checkout` missing `persist-credentials: false` at {loc_str}")
            if first_loc == ".github/workflows/":
                first_loc = f"{missing_persist_false[0][0]}:{missing_persist_false[0][1]}"
        findings.append(
            Finding(
                rule_id="OAS-CI-02",
                layer="L2",
                status="FAIL",
                title="GitHub Actions token/credential hardening gap",
                detail="; ".join(parts) + ".",
                location=first_loc,
                remediation="Declare least-privilege top-level `permissions: contents: read` and `persist-credentials: false` on actions/checkout.",
            )
        )
    else:
        findings.append(
            Finding(
                rule_id="OAS-CI-02",
                layer="L2",
                status="PASS",
                title="Workflow permissions and checkout credential hygiene hardened",
                detail=f"All {len(workflows)} workflow(s) declare top-level permissions and disable persisted checkout credentials.",
                location=".github/workflows/",
            )
        )

    if missing_timeouts:
        preview = ", ".join(f"{rel}:{ln} ({job})" for rel, ln, job in missing_timeouts[:4])
        findings.append(
            Finding(
                rule_id="OAS-CI-03",
                layer="L2",
                status="WARN",
                title=f"CI job(s) missing explicit timeout-minutes ({len(missing_timeouts)})",
                detail=f"Jobs without `timeout-minutes` default to 360 minutes on hung agent loops: {preview}",
                location=f"{missing_timeouts[0][0]}:{missing_timeouts[0][1]}",
                remediation="Set bounded `timeout-minutes` (e.g., 10–20) on every CI job.",
            )
        )
    else:
        findings.append(
            Finding(
                rule_id="OAS-CI-03",
                layer="L2",
                status="PASS",
                title="All CI jobs declare explicit timeout-minutes",
                detail=f"Checked {len(workflows)} workflow file(s); every job defines a bounded timeout.",
                location=".github/workflows/",
            )
        )

    if ci_injections:
        preview = "; ".join(f"{rel}:{ln} ({desc})" for rel, ln, desc in ci_injections[:4])
        extra = f" (+{len(ci_injections) - 4} more)" if len(ci_injections) > 4 else ""
        findings.append(
            Finding(
                rule_id="OAS-CI-05",
                layer="L2",
                status="FAIL",
                title=f"GitHub Actions prompt/script injection or pull_request_target hazard ({len(ci_injections)})",
                detail=f"Untrusted PR/issue content can hijack CI or AI review agents: {preview}{extra}",
                location=f"{ci_injections[0][0]}:{ci_injections[0][1]}",
                remediation="Pass untrusted fields only via env: with strict validation; never combine pull_request_target with PR head checkout or secrets.",
            )
        )
    else:
        findings.append(
            Finding(
                rule_id="OAS-CI-05",
                layer="L2",
                status="PASS",
                title="No Comment-and-Control CI injection or unsafe pull_request_target patterns",
                detail=f"Checked {len(workflows)} workflow file(s); zero untrusted title/body interpolations or pull_request_target head checkouts.",
                location=".github/workflows/",
            )
        )

    if has_dedicated_sast:
        findings.append(
            Finding(
                rule_id="OAS-CI-06",
                layer="L2",
                status="PASS",
                title="Dedicated static/security linter or scanner wired in CI",
                detail="Detected dedicated security/static analysis tooling referenced by CI workflows.",
                location=".github/workflows/",
            )
        )
    else:
        findings.append(
            Finding(
                rule_id="OAS-CI-06",
                layer="L2",
                status="WARN",
                title="No dedicated SAST / security linter detected in CI",
                detail="audit-repo.py source checks are Day-0 smoke checks only (no cross-file taint/dataflow).",
                location=".github/workflows/",
                remediation="Wire dedicated tooling into CI (e.g., Ruff S / Bandit / Semgrep / CodeQL / gitleaks / govulncheck / Clippy -D warnings).",
            )
        )

    return findings


def _is_hidden_deceptive_char(ch: str, *, is_file_start: bool) -> bool:
    cp = ord(ch)
    if cp == 0xFEFF:
        return not is_file_start
    if 0x200B <= cp <= 0x200F:
        return True
    if 0x202A <= cp <= 0x202E:
        return True
    if 0x2066 <= cp <= 0x2069:
        return True
    if cp == 0x2060:
        return True
    if 0xE0000 <= cp <= 0xE007F:
        return True
    return False


def _iter_instruction_files(target: Path) -> list[Path]:
    found: list[Path] = []
    seen: set[Path] = set()
    for rel in ROOT_INSTRUCTION_FILES:
        p = target / rel
        if p.is_file() and not p.is_symlink():
            rp = p.resolve()
            if rp not in seen:
                seen.add(rp)
                found.append(p)
    for rel_dir in INSTRUCTION_SCAN_DIRS:
        base = target / rel_dir
        if not base.is_dir() or base.is_symlink():
            continue
        for p in sorted(base.rglob("*")):
            if p.is_symlink() or not p.is_file():
                continue
            if p.suffix not in {".md", ".mdc", ".txt"}:
                continue
            rp = p.resolve()
            if rp not in seen:
                seen.add(rp)
                found.append(p)
    return found


def _audit_layer2_agent_surfaces(target: Path) -> list[Finding]:
    """Audit Agent instruction files & repo-committed IDE/MCP settings (OAS-AGT-01..03)."""
    findings: list[Finding] = []
    instr_files = _iter_instruction_files(target)

    hidden_hits: list[tuple[str, int, str]] = []
    hijack_hits: list[tuple[str, int, str]] = []

    for path in instr_files:
        rel = path.relative_to(target).as_posix()
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue

        for lineno, line in enumerate(text.splitlines(), start=1):
            for col, ch in enumerate(line):
                if _is_hidden_deceptive_char(ch, is_file_start=(lineno == 1 and col == 0)):
                    hidden_hits.append((rel, lineno, f"U+{ord(ch):04X}"))
                    break

        # Strip fenced code blocks before checking social-engineering / endpoint-hijack directives
        in_fence = False
        unquoted_lines: list[tuple[int, str]] = []
        for lineno, line in enumerate(text.splitlines(), start=1):
            if line.lstrip().startswith("```"):
                in_fence = not in_fence
                continue
            if not in_fence:
                unquoted_lines.append((lineno, line))

        has_hide_line: int | None = None
        has_silent_run_line: int | None = None
        for lineno, line in unquoted_lines:
            if API_ENDPOINT_HIJACK_RE.search(line):
                hijack_hits.append((rel, lineno, "model API base URL override in instruction file"))
            if has_hide_line is None and SILENT_HIDE_RE.search(line):
                has_hide_line = lineno
            if has_silent_run_line is None and SILENT_RUN_RE.search(line):
                has_silent_run_line = lineno
        if has_hide_line is not None and has_silent_run_line is not None:
            hijack_hits.append((rel, has_silent_run_line, "silent unconfirmed execution + do-not-inspect directive"))

    if hidden_hits:
        preview = "; ".join(f"{rel}:{ln} ({cp})" for rel, ln, cp in hidden_hits[:5])
        extra = f" (+{len(hidden_hits) - 5} more)" if len(hidden_hits) > 5 else ""
        findings.append(
            Finding(
                rule_id="OAS-AGT-01",
                layer="L2",
                status="FAIL",
                title=f"Hidden/deceptive Unicode detected in agent instruction file(s) ({len(hidden_hits)})",
                detail=f"Zero-width, BiDi, or Unicode Tag characters can smuggle invisible instructions: {preview}{extra}",
                location=f"{hidden_hits[0][0]}:{hidden_hits[0][1]}",
                remediation="Inspect raw bytes, strip invisible Unicode controls, and protect instruction files under CODEOWNERS.",
            )
        )
    elif instr_files:
        findings.append(
            Finding(
                rule_id="OAS-AGT-01",
                layer="L2",
                status="PASS",
                title="Agent instruction files free of hidden Unicode controls",
                detail=f"Scanned {len(instr_files)} instruction/skill file(s); zero zero-width, BiDi, or Tag-block characters.",
            )
        )

    # OAS-AGT-02: Dangerous repo-committed IDE / Agent executable configs
    cfg_fails: list[tuple[str, str]] = []
    cfg_warns: list[tuple[str, str]] = []

    vscode_tasks = _read_regular_text(target, ".vscode/tasks.json")
    if vscode_tasks is not None:
        cleaned = _strip_c_style_comments(vscode_tasks)
        if re.search(r'"runOn"\s*:\s*"folderOpen"', cleaned):
            cfg_fails.append((".vscode/tasks.json", 'auto-executing `"runOn": "folderOpen"` task'))

    for claude_cfg_rel in (".claude/settings.json", ".claude/settings.local.json"):
        cfg_txt = _read_regular_text(target, claude_cfg_rel)
        if cfg_txt is None:
            continue
        try:
            cfg_obj = json.loads(cfg_txt)
        except json.JSONDecodeError:
            cfg_warns.append((claude_cfg_rel, "invalid JSON in repo-committed Claude settings"))
            continue
        if isinstance(cfg_obj, Mapping):
            perms = cfg_obj.get("permissions")
            if isinstance(perms, Mapping):
                if perms.get("defaultMode") == "bypassPermissions":
                    cfg_fails.append((claude_cfg_rel, 'sets `permissions.defaultMode: "bypassPermissions"`'))
                allow_list = perms.get("allow")
                if isinstance(allow_list, list) and any(
                    isinstance(x, str) and x.strip() in {"Bash", "Bash(*)", "Bash(*:*)"} for x in allow_list
                ):
                    cfg_fails.append((claude_cfg_rel, "allows unrestricted shell wildcard `Bash(*)`"))
            if cfg_obj.get("hooks"):
                cfg_warns.append((claude_cfg_rel, "commits executable Claude lifecycle `hooks` into repo"))
            if cfg_obj.get("apiKeyHelper"):
                cfg_fails.append((claude_cfg_rel, "commits executable `apiKeyHelper` command into repo"))
            env_map = cfg_obj.get("env")
            if isinstance(env_map, Mapping) and (
                "ANTHROPIC_BASE_URL" in env_map or "OPENAI_BASE_URL" in env_map
            ):
                cfg_fails.append((claude_cfg_rel, "overrides model API base URL inside repo-committed settings"))

    for mcp_rel in (".mcp.json", ".cursor/mcp.json"):
        mcp_txt = _read_regular_text(target, mcp_rel)
        if mcp_txt is None:
            continue
        if MCP_SHELL_EXEC_RE.search(mcp_txt):
            cfg_fails.append((mcp_rel, "MCP config invokes shell `-c` or `curl|sh` command"))
        else:
            cfg_warns.append((mcp_rel, "repo-committed MCP server configuration (review under CODEOWNERS)"))

    if cfg_fails:
        preview = "; ".join(f"{rel} ({msg})" for rel, msg in cfg_fails[:4])
        findings.append(
            Finding(
                rule_id="OAS-AGT-02",
                layer="L2",
                status="FAIL",
                title=f"Dangerous executable IDE/agent config committed to repo ({len(cfg_fails)})",
                detail=preview,
                location=cfg_fails[0][0],
                remediation="Remove folderOpen auto-tasks, bypassPermissions, shell wildcards, apiKeyHelper, and API URL overrides from repo configs.",
            )
        )
    elif cfg_warns:
        preview = "; ".join(f"{rel} ({msg})" for rel, msg in cfg_warns[:4])
        findings.append(
            Finding(
                rule_id="OAS-AGT-02",
                layer="L2",
                status="WARN",
                title=f"Repo-committed executable agent/MCP settings require review ({len(cfg_warns)})",
                detail=preview,
                location=cfg_warns[0][0],
                remediation="Protect .claude/, .cursor/, .vscode/, and .mcp.json under CODEOWNERS and audit every command.",
            )
        )
    else:
        findings.append(
            Finding(
                rule_id="OAS-AGT-02",
                layer="L2",
                status="PASS",
                title="No dangerous executable IDE/agent settings committed",
                detail="No folderOpen auto-tasks, bypassPermissions, apiKeyHelper, or risky repo MCP configs found.",
            )
        )

    if hijack_hits:
        preview = "; ".join(f"{rel}:{ln} ({desc})" for rel, ln, desc in hijack_hits[:4])
        findings.append(
            Finding(
                rule_id="OAS-AGT-03",
                layer="L2",
                status="FAIL",
                title=f"Instruction-file endpoint hijack or silent-execution directive ({len(hijack_hits)})",
                detail=preview,
                location=f"{hijack_hits[0][0]}:{hijack_hits[0][1]}",
                remediation="Audit instruction files like executable code; remove API endpoint redirects and unconfirmed silent-run directives.",
            )
        )
    elif instr_files:
        findings.append(
            Finding(
                rule_id="OAS-AGT-03",
                layer="L2",
                status="PASS",
                title="No instruction-file endpoint hijack or silent-execution directives",
                detail=f"Checked {len(instr_files)} instruction/skill file(s); clean.",
            )
        )

    return findings


def _audit_layer2_codeowners(target: Path) -> Finding:
    text = _read_regular_text(target, ".github/CODEOWNERS")
    if text is None:
        return Finding(
            rule_id="OAS-CI-04",
            layer="L2",
            status="WARN",
            title="No .github/CODEOWNERS protecting enforcement surfaces",
            detail="Without CODEOWNERS on .github/, Makefile, scripts/, and AGENTS.md, an agent PR can weaken its own gates without designated owner review.",
            location=".github/CODEOWNERS",
            remediation="Add .github/CODEOWNERS from profiles/L2-governed/CODEOWNERS.example using verified team/user handles.",
        )
    if re.search(r"(^|\s)@org/", text, re.MULTILINE):
        return Finding(
            rule_id="OAS-CI-04",
            layer="L2",
            status="FAIL",
            title="CODEOWNERS contains unresolved @org/ placeholder",
            detail="GitHub silently ignores unknown CODEOWNER handles, leaving enforcement surfaces unprotected.",
            location=".github/CODEOWNERS",
            remediation="Replace @org/... handles with real GitHub team/user handles that have Write access.",
        )
    return Finding(
        rule_id="OAS-CI-04",
        layer="L2",
        status="PASS",
        title="CODEOWNERS configured without template placeholders",
        detail=".github/CODEOWNERS is present and contains no @org/ placeholders.",
        location=".github/CODEOWNERS",
    )


def _iter_non_test_python_files(target: Path) -> list[Path]:
    files: list[Path] = []
    stack: list[Path] = [target]
    while stack and len(files) < MAX_PY_FILES:
        current = stack.pop()
        try:
            entries = sorted(current.iterdir(), reverse=True)
        except OSError:
            continue
        for entry in entries:
            if entry.is_symlink():
                continue
            name = entry.name
            if entry.is_dir():
                if name in SKIP_DIRS or name in TEST_DIR_NAMES:
                    continue
                stack.append(entry)
            elif entry.is_file() and name.endswith(".py"):
                if name.startswith("test_") or name.endswith("_test.py") or name == "conftest.py":
                    continue
                try:
                    if entry.stat().st_size <= MAX_PY_FILE_BYTES:
                        files.append(entry)
                except OSError:
                    continue
                if len(files) >= MAX_PY_FILES:
                    break
    return sorted(files)


def _attr_chain(node: ast.AST) -> list[str]:
    parts: list[str] = []
    cur: ast.AST | None = node
    while isinstance(cur, ast.Attribute):
        parts.append(cur.attr)
        cur = cur.value
    if isinstance(cur, ast.Name):
        parts.append(cur.id)
    parts.reverse()
    return parts


def _is_noop_body(stmts: Sequence[ast.stmt]) -> bool:
    if not stmts:
        return True
    for stmt in stmts:
        if isinstance(stmt, ast.Pass):
            continue
        if isinstance(stmt, ast.Expr) and isinstance(stmt.value, ast.Constant) and stmt.value.value is Ellipsis:
            continue
        return False
    return True


def _is_broad_exception(handler: ast.ExceptHandler) -> bool:
    if handler.type is None:
        return True
    if isinstance(handler.type, ast.Name) and handler.type.id in {"Exception", "BaseException"}:
        return True
    if isinstance(handler.type, ast.Tuple):
        return any(isinstance(elt, ast.Name) and elt.id in {"Exception", "BaseException"} for elt in handler.type.elts)
    return False


def _scan_python_ast(target: Path) -> list[Finding]:
    py_files = _iter_non_test_python_files(target)
    if not py_files:
        return []

    hits: dict[str, list[tuple[str, int, str]]] = {
        "OAS-SVC-01": [],
        "OAS-SVC-02": [],
        "OAS-SVC-03": [],
        "OAS-SVC-04": [],
        "OAS-SVC-05": [],
        "OAS-SVC-06": [],
    }
    parse_errors: list[str] = []

    for py_path in py_files:
        rel = py_path.relative_to(target).as_posix()
        try:
            source = py_path.read_text(encoding="utf-8")
            tree = ast.parse(source, filename=rel)
        except (OSError, UnicodeDecodeError, SyntaxError) as exc:
            parse_errors.append(f"{rel} ({type(exc).__name__})")
            continue

        for node in ast.walk(tree):
            if isinstance(node, ast.ExceptHandler):
                if _is_broad_exception(node) and _is_noop_body(node.body):
                    hits["OAS-SVC-01"].append((rel, node.lineno, "broad except with pass/..."))
            elif isinstance(node, ast.Call):
                chain = _attr_chain(node.func)
                # OAS-SVC-02: shell=True or os.system / os.popen
                if len(chain) >= 2 and chain[-2] == "subprocess" and chain[-1] in UNSAFE_SUBPROCESS_FUNCS:
                    for kw in node.keywords:
                        if kw.arg == "shell" and isinstance(kw.value, ast.Constant) and kw.value.value is True:
                            hits["OAS-SVC-02"].append((rel, node.lineno, f"subprocess.{chain[-1]}(..., shell=True)"))
                elif chain in (["os", "system"], ["os", "popen"]):
                    hits["OAS-SVC-02"].append((rel, node.lineno, ".".join(chain) + "(...)"))

                # OAS-SVC-03: eval / exec
                if chain in (["eval"], ["exec"]):
                    hits["OAS-SVC-03"].append((rel, node.lineno, f"{chain[0]}(...)"))

                # OAS-SVC-04: verify=False (TLS verification disabled)
                for kw in node.keywords:
                    if kw.arg == "verify" and isinstance(kw.value, ast.Constant) and kw.value.value is False:
                        hits["OAS-SVC-04"].append((rel, node.lineno, "verify=False"))

                # OAS-SVC-05: hardcoded fallback secret in os.getenv / os.environ.get
                if chain in (["os", "getenv"], ["os", "environ", "get"]):
                    key_arg = node.args[0] if len(node.args) >= 1 else None
                    default_arg = node.args[1] if len(node.args) >= 2 else None
                    if default_arg is None:
                        for kw in node.keywords:
                            if kw.arg == "default":
                                default_arg = kw.value
                                break
                    if (
                        isinstance(key_arg, ast.Constant)
                        and isinstance(key_arg.value, str)
                        and SECRET_ENV_RE.search(key_arg.value)
                        and isinstance(default_arg, ast.Constant)
                        and isinstance(default_arg.value, str)
                        and default_arg.value.strip() != ""
                    ):
                        hits["OAS-SVC-05"].append((rel, node.lineno, f"hardcoded fallback for env var {key_arg.value!r}"))

                # OAS-SVC-06: unsafe yaml.load / pickle.load(s)
                if chain == ["yaml", "load"]:
                    loader_kw = next((kw for kw in node.keywords if kw.arg == "Loader"), None)
                    loader_name = ""
                    if loader_kw is not None:
                        lchain = _attr_chain(loader_kw.value)
                        loader_name = lchain[-1] if lchain else ""
                    if loader_name not in SAFE_YAML_LOADERS:
                        hits["OAS-SVC-06"].append((rel, node.lineno, "yaml.load without SafeLoader"))
                elif chain in (["pickle", "load"], ["pickle", "loads"], ["_pickle", "load"], ["_pickle", "loads"]):
                    hits["OAS-SVC-06"].append((rel, node.lineno, ".".join(chain) + "(...)"))

    meta = {
        "OAS-SVC-01": (
            "Fail-open silent exception swallowing (`except: pass`)",
            "Replace silent swallowing with explicit fail-closed handling or scoped error logging (see skills/secure-vibe-coding).",
        ),
        "OAS-SVC-02": (
            "Shell command injection sink (`shell=True` / `os.system`)",
            "Use subprocess.run([...], shell=False) with an explicit argument list.",
        ),
        "OAS-SVC-03": (
            "Dynamic code execution sink (`eval` / `exec`)",
            "Replace eval/exec with explicit parsing (e.g. ast.literal_eval or structured dispatch).",
        ),
        "OAS-SVC-04": (
            "TLS certificate verification disabled (`verify=False`)",
            "Remove verify=False and configure trusted CA certificates explicitly.",
        ),
        "OAS-SVC-05": (
            "Hardcoded fallback secret on environment variable",
            "Fail startup cleanly when a required secret env var is unset instead of falling back to a default literal.",
        ),
        "OAS-SVC-06": (
            "Unsafe deserialization (`yaml.load` / `pickle`)",
            "Use yaml.safe_load or strict JSON schema validation instead of pickle or unsafe yaml.load.",
        ),
    }

    findings: list[Finding] = []
    any_hit = False
    for rule_id, (title, remediation) in meta.items():
        rule_hits = hits[rule_id]
        if rule_hits:
            any_hit = True
            preview = "; ".join(f"{rel}:{ln} ({desc})" for rel, ln, desc in rule_hits[:4])
            extra = f" (+{len(rule_hits) - 4} more)" if len(rule_hits) > 4 else ""
            findings.append(
                Finding(
                    rule_id=rule_id,
                    layer="L2",
                    status="FAIL",
                    title=f"{title} ({len(rule_hits)} candidate hit(s))",
                    detail=preview + extra,
                    location=f"{rule_hits[0][0]}:{rule_hits[0][1]}",
                    remediation=remediation,
                )
            )

    if not any_hit:
        findings.append(
            Finding(
                rule_id="OAS-SVC-00",
                layer="L2",
                status="PASS",
                title="Python AST high-signal security traps clean",
                detail=f"Scanned {len(py_files)} non-test Python file(s); zero hits across OAS-SVC-01..06.",
            )
        )
    if parse_errors:
        findings.append(
            Finding(
                rule_id="OAS-SVC-PARSE",
                layer="L2",
                status="WARN",
                title=f"Skipped unparseable Python file(s) ({len(parse_errors)})",
                detail="Could not parse: " + ", ".join(parse_errors[:5]),
                remediation="Verify syntax/encoding of skipped Python files so static scans do not silently miss them.",
            )
        )
    return findings


def _strip_c_style_comments(source: str) -> str:
    """Remove // and /* */ comments while preserving newline count for exact line numbers."""
    out: list[str] = []
    i = 0
    n = len(source)
    in_quote: str | None = None
    while i < n:
        ch = source[i]
        nxt = source[i + 1] if i + 1 < n else ""
        if in_quote is not None:
            out.append(ch)
            if ch == "\\" and i + 1 < n:
                out.append(nxt)
                i += 2
                continue
            if ch == in_quote:
                in_quote = None
            i += 1
            continue
        if ch in {'"', "'", "`"}:
            in_quote = ch
            out.append(ch)
            i += 1
            continue
        if ch == "/" and nxt == "/":
            i += 2
            while i < n and source[i] != "\n":
                i += 1
            continue
        if ch == "/" and nxt == "*":
            i += 2
            while i + 1 < n and not (source[i] == "*" and source[i + 1] == "/"):
                if source[i] == "\n":
                    out.append("\n")
                i += 1
            i = min(n, i + 2)
            continue
        out.append(ch)
        i += 1
    return "".join(out)


def _iter_source_files(target: Path, suffixes: frozenset[str], *, skip_file_fn) -> list[Path]:
    files: list[Path] = []
    stack: list[Path] = [target]
    while stack and len(files) < MAX_PY_FILES:
        current = stack.pop()
        try:
            entries = sorted(current.iterdir(), reverse=True)
        except OSError:
            continue
        for entry in entries:
            if entry.is_symlink():
                continue
            name = entry.name
            if entry.is_dir():
                if name in SKIP_DIRS or name in TEST_DIR_NAMES:
                    continue
                stack.append(entry)
            elif entry.is_file() and entry.suffix in suffixes:
                if skip_file_fn(name):
                    continue
                try:
                    if entry.stat().st_size <= MAX_PY_FILE_BYTES:
                        files.append(entry)
                except OSError:
                    continue
                if len(files) >= MAX_PY_FILES:
                    break
    return sorted(files)


def _scan_js_ts(target: Path) -> list[Finding]:
    def _is_js_test(name: str) -> bool:
        return (
            name.endswith(".d.ts")
            or ".test." in name
            or ".spec." in name
            or name.startswith("test_")
        )

    js_files = _iter_source_files(target, JS_TS_SUFFIXES, skip_file_fn=_is_js_test)
    pkg_text = _read_regular_text(target, "package.json")
    tsconfig_text = _read_regular_text(target, "tsconfig.json")
    if not js_files and pkg_text is None and tsconfig_text is None:
        return []

    findings: list[Finding] = []
    sink_hits: list[tuple[str, int, str]] = []
    for path in js_files:
        rel = path.relative_to(target).as_posix()
        try:
            cleaned = _strip_c_style_comments(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError):
            continue
        for lineno, line in enumerate(cleaned.splitlines(), start=1):
            match = JS_SINK_RE.search(line)
            if match:
                sink_hits.append((rel, lineno, match.group(0).strip()))

    if sink_hits:
        preview = "; ".join(f"{rel}:{ln} ({desc})" for rel, ln, desc in sink_hits[:4])
        extra = f" (+{len(sink_hits) - 4} more)" if len(sink_hits) > 4 else ""
        findings.append(
            Finding(
                rule_id="OAS-JS-01",
                layer="L2",
                status="FAIL",
                title=f"JS/TS unsafe HTML/code execution sink ({len(sink_hits)} candidate hit(s))",
                detail=preview + extra,
                location=f"{sink_hits[0][0]}:{sink_hits[0][1]}",
                remediation="Avoid dangerouslySetInnerHTML, eval(), and new Function() on dynamic inputs; sanitize or use structured rendering.",
            )
        )

    if pkg_text is not None:
        try:
            pkg_obj = json.loads(pkg_text)
        except json.JSONDecodeError:
            pkg_obj = None
        if isinstance(pkg_obj, Mapping) and isinstance(pkg_obj.get("scripts"), Mapping):
            bad_scripts = [
                str(name)
                for name, cmd in pkg_obj["scripts"].items()
                if isinstance(cmd, str) and "--passWithNoTests" in cmd
            ]
            if bad_scripts:
                findings.append(
                    Finding(
                        rule_id="OAS-JS-02",
                        layer="L2",
                        status="FAIL",
                        title="Test script allows 0 tests collected to pass (--passWithNoTests)",
                        detail="package.json script(s) mask missing tests as green: " + ", ".join(sorted(bad_scripts)),
                        location="package.json",
                        remediation="Remove --passWithNoTests so 0 tests collected fails closed.",
                    )
                )

    if tsconfig_text is not None:
        cleaned_ts = _strip_c_style_comments(tsconfig_text)
        if not re.search(r'"strict"\s*:\s*true\b', cleaned_ts):
            findings.append(
                Finding(
                    rule_id="OAS-JS-03",
                    layer="L2",
                    status="WARN",
                    title="TypeScript strict mode not enabled in tsconfig.json",
                    detail='tsconfig.json does not explicitly set `"strict": true`, weakening null/undefined and type-boundary checks.',
                    location="tsconfig.json",
                    remediation='Enable `"strict": true` under compilerOptions in tsconfig.json.',
                )
            )

    if not findings:
        findings.append(
            Finding(
                rule_id="OAS-JS-00",
                layer="L2",
                status="PASS",
                title="JS/TS high-signal security & gate traps clean",
                detail=f"Scanned {len(js_files)} non-test JS/TS file(s) and Node/TS config; zero hits across OAS-JS-01..03.",
            )
        )
    return findings


def _scan_go(target: Path) -> list[Finding]:
    go_files = _iter_source_files(target, frozenset({".go"}), skip_file_fn=lambda name: name.endswith("_test.go"))
    if not go_files:
        return []
    hits: list[tuple[str, int, str]] = []
    for path in go_files:
        rel = path.relative_to(target).as_posix()
        try:
            cleaned = _strip_c_style_comments(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError):
            continue
        for lineno, line in enumerate(cleaned.splitlines(), start=1):
            if GO_TLS_RE.search(line):
                hits.append((rel, lineno, "InsecureSkipVerify: true"))
            if GO_SHELL_RE.search(line):
                hits.append((rel, lineno, "exec.Command shell -c"))
    if hits:
        preview = "; ".join(f"{rel}:{ln} ({desc})" for rel, ln, desc in hits[:4])
        extra = f" (+{len(hits) - 4} more)" if len(hits) > 4 else ""
        return [
            Finding(
                rule_id="OAS-GO-01",
                layer="L2",
                status="FAIL",
                title=f"Go TLS-disable or shell-interpolation sink ({len(hits)} candidate hit(s))",
                detail=preview + extra,
                location=f"{hits[0][0]}:{hits[0][1]}",
                remediation="Keep TLS verification enabled and pass explicit argv slices to exec.Command without sh -c.",
            )
        ]
    return [
        Finding(
            rule_id="OAS-GO-00",
            layer="L2",
            status="PASS",
            title="Go high-signal security traps clean",
            detail=f"Scanned {len(go_files)} non-test Go file(s); zero hits on OAS-GO-01.",
        )
    ]


def _scan_rust(target: Path) -> list[Finding]:
    rs_files = _iter_source_files(target, frozenset({".rs"}), skip_file_fn=lambda name: name.endswith("_test.rs"))
    if not rs_files:
        return []
    hits: list[tuple[str, int, str]] = []
    for path in rs_files:
        rel = path.relative_to(target).as_posix()
        try:
            cleaned = _strip_c_style_comments(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError):
            continue
        for lineno, line in enumerate(cleaned.splitlines(), start=1):
            if RUST_TLS_RE.search(line):
                hits.append((rel, lineno, "danger_accept_invalid_certs(true)"))
            if RUST_SHELL_RE.search(line):
                hits.append((rel, lineno, 'Command::new("sh").arg("-c")'))
    if hits:
        preview = "; ".join(f"{rel}:{ln} ({desc})" for rel, ln, desc in hits[:4])
        extra = f" (+{len(hits) - 4} more)" if len(hits) > 4 else ""
        return [
            Finding(
                rule_id="OAS-RS-01",
                layer="L2",
                status="FAIL",
                title=f"Rust TLS-disable or shell-interpolation sink ({len(hits)} candidate hit(s))",
                detail=preview + extra,
                location=f"{hits[0][0]}:{hits[0][1]}",
                remediation="Do not disable TLS certificate checks and pass explicit args to Command::new without sh -c.",
            )
        ]
    return [
        Finding(
            rule_id="OAS-RS-00",
            layer="L2",
            status="PASS",
            title="Rust high-signal security traps clean",
            detail=f"Scanned {len(rs_files)} non-test Rust file(s); zero hits on OAS-RS-01.",
        )
    ]


def _scan_java(target: Path) -> list[Finding]:
    java_files = _iter_source_files(
        target,
        frozenset({".java"}),
        skip_file_fn=lambda name: name.endswith("Test.java") or name.endswith("Tests.java"),
    )
    if not java_files:
        return []
    hits: list[tuple[str, int, str]] = []
    for path in java_files:
        rel = path.relative_to(target).as_posix()
        try:
            cleaned = _strip_c_style_comments(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError):
            continue
        for lineno, line in enumerate(cleaned.splitlines(), start=1):
            if JAVA_EXEC_RE.search(line):
                hits.append((rel, lineno, "Runtime.getRuntime().exec(...)"))
            if JAVA_DESER_RE.search(line):
                hits.append((rel, lineno, "new ObjectInputStream(...)"))
    if hits:
        preview = "; ".join(f"{rel}:{ln} ({desc})" for rel, ln, desc in hits[:4])
        extra = f" (+{len(hits) - 4} more)" if len(hits) > 4 else ""
        return [
            Finding(
                rule_id="OAS-JV-01",
                layer="L2",
                status="FAIL",
                title=f"Java command-exec or unsafe deserialization sink ({len(hits)} candidate hit(s))",
                detail=preview + extra,
                location=f"{hits[0][0]}:{hits[0][1]}",
                remediation="Use ProcessBuilder with explicit argument lists and safe JSON/Protobuf serialization instead of ObjectInputStream.",
            )
        ]
    return [
        Finding(
            rule_id="OAS-JV-00",
            layer="L2",
            status="PASS",
            title="Java high-signal security traps clean",
            detail=f"Scanned {len(java_files)} non-test Java file(s); zero hits on OAS-JV-01.",
        )
    ]


def _scan_multi_language_traps(target: Path) -> list[Finding]:
    findings: list[Finding] = []
    findings.extend(_scan_python_ast(target))
    findings.extend(_scan_js_ts(target))
    findings.extend(_scan_go(target))
    findings.extend(_scan_rust(target))
    findings.extend(_scan_java(target))
    if not findings:
        return [
            Finding(
                rule_id="OAS-SVC-00",
                layer="L2",
                status="NOT_APPLICABLE",
                title="Multi-language static security trap scan",
                detail="No non-test Python, JS/TS, Go, Rust, or Java source files found.",
            )
        ]
    return findings


def _fetch_gh_json(endpoint: str, *, gh_bin: str, timeout: int) -> object:
    resolved = shutil.which(gh_bin)
    if not resolved:
        raise AuditNotRunError(f"NOT_RUN: GitHub CLI ({gh_bin!r}) not found on PATH")
    try:
        proc = _run_cmd([resolved, "api", "--method", "GET", endpoint], timeout=timeout)
    except subprocess.TimeoutExpired as exc:
        raise AuditNotRunError(f"NOT_RUN: gh api GET {endpoint} timed out after {timeout}s") from exc
    if proc.returncode != 0:
        err = proc.stderr.decode("utf-8", errors="replace").strip()
        raise AuditNotRunError(f"NOT_RUN: gh api GET {endpoint} failed (exit {proc.returncode}): {err}")
    return _strict_json_loads(proc.stdout, f"gh api {endpoint}")


def _ruleset_covers_default_branch(ruleset: Mapping[str, object], default_branch: str) -> bool:
    if ruleset.get("target") != "branch" or ruleset.get("enforcement") != "active":
        return False
    conditions = ruleset.get("conditions")
    if not isinstance(conditions, Mapping):
        return False
    ref_name = conditions.get("ref_name")
    if not isinstance(ref_name, Mapping):
        return False
    include = ref_name.get("include") or []
    exclude = ref_name.get("exclude") or []
    if not isinstance(include, list) or not isinstance(exclude, list):
        return False
    branch_ref = f"refs/heads/{default_branch}"
    covered = "~DEFAULT_BRANCH" in include or branch_ref in include
    excluded = "~DEFAULT_BRANCH" in exclude or branch_ref in exclude
    return covered and not excluded


def _evaluate_rulesets(
    rulesets: Sequence[Mapping[str, object]],
    *,
    repository: str,
    default_branch: str,
) -> list[Finding]:
    covering = [rs for rs in rulesets if _ruleset_covers_default_branch(rs, default_branch)]
    if not covering:
        return [
            Finding(
                rule_id="OAS-GH-01",
                layer="L3",
                status="FAIL",
                title="No active GitHub Branch Ruleset covers the default branch",
                detail=f"Checked {len(rulesets)} ruleset(s) on {repository}; none actively enforce protection on {default_branch!r} (~DEFAULT_BRANCH). Coding agents or write tokens are not blocked by a ruleset merge boundary.",
                location=f"repos/{repository}/rulesets",
                remediation="Import profiles/L2-governed/github-ruleset.import.json in GitHub Settings -> Rules -> Rulesets.",
            )
        ]

    # Aggregate protections across all active rulesets covering the default branch
    max_reviews = 0
    any_codeowner = False
    any_dismiss_stale = False
    any_last_push = False
    status_checks: list[tuple[str, int | None]] = []
    unconditional_bypasses: list[str] = []
    pr_bypasses: list[str] = []
    ruleset_refs: list[str] = []

    for rs in covering:
        rs_id = rs.get("id")
        rs_name = rs.get("name", "unnamed")
        ruleset_refs.append(f"#{rs_id} ({rs_name})" if rs_id is not None else str(rs_name))
        for actor in rs.get("bypass_actors") or []:
            if not isinstance(actor, Mapping):
                continue
            mode = actor.get("bypass_mode")
            label = f"{actor.get('actor_type')}:{actor.get('actor_id')} ({mode})"
            if mode in {"always", "exempt"}:
                unconditional_bypasses.append(label)
            elif mode == "pull_request":
                pr_bypasses.append(label)

        for rule in rs.get("rules") or []:
            if not isinstance(rule, Mapping):
                continue
            rtype = rule.get("type")
            params = rule.get("parameters")
            if not isinstance(params, Mapping):
                continue
            if rtype == "pull_request":
                rc = params.get("required_approving_review_count", 0)
                if isinstance(rc, int) and not isinstance(rc, bool):
                    max_reviews = max(max_reviews, rc)
                if params.get("require_code_owner_review") is True:
                    any_codeowner = True
                if params.get("dismiss_stale_reviews_on_push") is True:
                    any_dismiss_stale = True
                if params.get("require_last_push_approval") is True:
                    any_last_push = True
            elif rtype == "required_status_checks":
                for chk in params.get("required_status_checks") or []:
                    if not isinstance(chk, Mapping):
                        continue
                    ctx = chk.get("context")
                    iid = chk.get("integration_id")
                    if isinstance(ctx, str) and ctx:
                        status_checks.append((ctx, iid if isinstance(iid, int) and not isinstance(iid, bool) else None))

    loc = f"repos/{repository}/rulesets [{', '.join(ruleset_refs)}]"
    findings: list[Finding] = [
        Finding(
            rule_id="OAS-GH-01",
            layer="L3",
            status="PASS",
            title="Active GitHub Branch Ruleset covers default branch",
            detail=f"Found {len(covering)} active ruleset(s) covering {default_branch!r}: {', '.join(ruleset_refs)}.",
            location=loc,
        )
    ]

    # OAS-GH-02: Post-approval push protection
    if any_last_push and any_dismiss_stale:
        findings.append(
            Finding(
                rule_id="OAS-GH-02",
                layer="L3",
                status="PASS",
                title="Post-approval pushes are blocked",
                detail="Both require_last_push_approval and dismiss_stale_reviews_on_push are enabled.",
                location=loc,
            )
        )
    else:
        missing_flags = [
            flag
            for flag, ok in (
                ("require_last_push_approval", any_last_push),
                ("dismiss_stale_reviews_on_push", any_dismiss_stale),
            )
            if not ok
        ]
        findings.append(
            Finding(
                rule_id="OAS-GH-02",
                layer="L3",
                status="FAIL",
                title="AI agent can push new commits after human approval",
                detail="Missing PR review protection(s): " + ", ".join(missing_flags) + ".",
                location=loc,
                remediation="Enable both 'Dismiss stale pull request approvals when new commits are pushed' and 'Require approval of the most recent reviewable push'.",
            )
        )

    # OAS-GH-03: Required status checks bound to integration_id
    if not status_checks:
        findings.append(
            Finding(
                rule_id="OAS-GH-03",
                layer="L3",
                status="FAIL",
                title="No required status checks configured on default branch",
                detail="PRs can be merged without passing CI checks.",
                location=loc,
                remediation="Require your CI check context(s) and bind them explicitly to GitHub Actions (integration_id: 15368) or your CI App.",
            )
        )
    else:
        unbound = sorted({ctx for ctx, iid in status_checks if iid is None})
        if unbound:
            findings.append(
                Finding(
                    rule_id="OAS-GH-03",
                    layer="L3",
                    status="FAIL",
                    title="Required status check source is unbound (spoofable by write token)",
                    detail="Status check(s) accept 'Any source' (integration_id: null): " + ", ".join(unbound),
                    location=loc,
                    remediation="Bind each required status check to its exact CI GitHub App (e.g. GitHub Actions = 15368) in the Ruleset.",
                )
            )
        else:
            findings.append(
                Finding(
                    rule_id="OAS-GH-03",
                    layer="L3",
                    status="PASS",
                    title="Required status checks bound to explicit CI App source",
                    detail=f"{len(status_checks)} required status check(s) bind an explicit integration_id.",
                    location=loc,
                )
            )

    # OAS-GH-04: Review count + CODEOWNER review
    if max_reviews < 1 or not any_codeowner:
        findings.append(
            Finding(
                rule_id="OAS-GH-04",
                layer="L3",
                status="FAIL",
                title="Weak PR approval / CODEOWNERS enforcement",
                detail=f"Observed required_approving_review_count={max_reviews}, require_code_owner_review={any_codeowner}.",
                location=loc,
                remediation="Require at least 1 approving review (2 for enforcement surfaces) and enable require_code_owner_review.",
            )
        )
    elif max_reviews < 2:
        findings.append(
            Finding(
                rule_id="OAS-GH-04",
                layer="L3",
                status="WARN",
                title="Single-reviewer PR threshold (recommend >= 2 on enforcement surfaces)",
                detail=f"Observed required_approving_review_count={max_reviews} with require_code_owner_review=True.",
                location=loc,
                remediation="Raise required_approving_review_count to 2 for L2 non-self-attesting enforcement surfaces.",
            )
        )
    else:
        findings.append(
            Finding(
                rule_id="OAS-GH-04",
                layer="L3",
                status="PASS",
                title="Multi-reviewer and CODEOWNERS approval enforced",
                detail=f"Observed required_approving_review_count={max_reviews} with require_code_owner_review=True.",
                location=loc,
            )
        )

    # OAS-GH-05: Bypass actors
    if unconditional_bypasses:
        findings.append(
            Finding(
                rule_id="OAS-GH-05",
                layer="L3",
                status="FAIL",
                title="Unconditional ruleset bypass actor present",
                detail="Actors can bypass PR/CI rules unconditionally: " + ", ".join(sorted(set(unconditional_bypasses))),
                location=loc,
                remediation="Remove always/exempt bypass actors from the branch ruleset (see profiles/L2-governed/github-ruleset.import.json).",
            )
        )
    elif pr_bypasses:
        findings.append(
            Finding(
                rule_id="OAS-GH-05",
                layer="L3",
                status="WARN",
                title="Pull-request bypass actor(s) configured (verify allowlist)",
                detail="Verify these break-glass actors are explicitly approved: " + ", ".join(sorted(set(pr_bypasses))),
                location=loc,
                remediation="Audit against an explicit policy allowlist via scripts/observe-github-ruleset.py --live --validate.",
            )
        )
    else:
        findings.append(
            Finding(
                rule_id="OAS-GH-05",
                layer="L3",
                status="PASS",
                title="Zero ruleset bypass actors configured",
                detail="No unconditional or pull_request bypass actors present on covering ruleset(s).",
                location=loc,
            )
        )

    return findings


def _audit_layer3_github(
    *,
    target: Path,
    use_github: bool,
    ruleset_file: Path | None,
    repo_arg: str | None,
    default_branch: str | None,
    gh_bin: str,
    timeout: int,
) -> list[Finding]:
    if not use_github and ruleset_file is None:
        return [
            Finding(
                rule_id="OAS-GH-00",
                layer="L3",
                status="NOT_RUN",
                title="Live GitHub Branch Ruleset audit not run",
                detail="Local checks alone cannot verify the external GitHub merge boundary (non-self-attesting).",
                remediation="Re-run with `--github` (requires authenticated `gh` CLI) or `--github-ruleset-file <json>`.",
            )
        ]

    if ruleset_file is not None:
        if ruleset_file.is_symlink() or not ruleset_file.is_file():
            raise AuditInputError(f"regular non-symlink JSON file required for --github-ruleset-file: {ruleset_file}")
        raw_obj = _strict_json_loads(ruleset_file.read_bytes(), "github ruleset file")
        rulesets: list[Mapping[str, object]]
        if isinstance(raw_obj, Mapping):
            rulesets = [raw_obj]
        elif isinstance(raw_obj, list) and all(isinstance(item, Mapping) for item in raw_obj):
            rulesets = list(raw_obj)
        else:
            raise AuditInputError("--github-ruleset-file must contain a ruleset JSON object or array of ruleset objects")
        repo_label = _validate_repo_slug(repo_arg) if repo_arg else "offline/ruleset-file"
        branch = default_branch or "main"
        return _evaluate_rulesets(rulesets, repository=repo_label, default_branch=branch)

    # Live read-only GitHub inspection via `gh api`
    repo_slug = _validate_repo_slug(repo_arg) if repo_arg else _infer_github_repo(target)
    if not repo_slug:
        raise AuditNotRunError(
            "NOT_RUN: unable to infer GitHub owner/repo from `git remote get-url origin`; pass `--repo owner/name`"
        )

    branch = default_branch
    if not branch:
        repo_meta = _fetch_gh_json(f"repos/{repo_slug}", gh_bin=gh_bin, timeout=timeout)
        if not isinstance(repo_meta, Mapping) or not isinstance(repo_meta.get("default_branch"), str):
            raise AuditNotRunError(f"NOT_RUN: unexpected GitHub repo metadata for {repo_slug}")
        branch = str(repo_meta["default_branch"])

    listing = _fetch_gh_json(f"repos/{repo_slug}/rulesets", gh_bin=gh_bin, timeout=timeout)
    if not isinstance(listing, list):
        raise AuditNotRunError(f"NOT_RUN: unexpected GitHub rulesets list payload for {repo_slug}")

    detailed_rulesets: list[Mapping[str, object]] = []
    for entry in listing:
        if not isinstance(entry, Mapping):
            continue
        if entry.get("target") != "branch" or entry.get("enforcement") != "active":
            continue
        rs_id = entry.get("id")
        if not isinstance(rs_id, int) or isinstance(rs_id, bool) or rs_id < 1:
            continue
        detail_obj = _fetch_gh_json(f"repos/{repo_slug}/rulesets/{rs_id}", gh_bin=gh_bin, timeout=timeout)
        if isinstance(detail_obj, Mapping):
            detailed_rulesets.append(detail_obj)

    return _evaluate_rulesets(detailed_rulesets, repository=repo_slug, default_branch=branch)


def audit_repository(
    target: Path,
    *,
    use_github: bool = False,
    ruleset_file: Path | None = None,
    repo_arg: str | None = None,
    default_branch: str | None = None,
    gh_bin: str = "gh",
    timeout: int = 30,
) -> dict[str, object]:
    if target.is_symlink() or not target.is_dir():
        raise AuditInputError(f"target must be an existing non-symlink directory: {target}")
    resolved = target.resolve()

    findings: list[Finding] = []
    findings.extend(_audit_layer1_context(resolved))
    findings.append(_audit_layer2_git_guardrails(resolved))
    findings.extend(_audit_layer2_agent_surfaces(resolved))
    findings.extend(_audit_layer2_workflows(resolved))
    findings.append(_audit_layer2_codeowners(resolved))
    findings.extend(_scan_multi_language_traps(resolved))
    findings.extend(
        _audit_layer3_github(
            target=resolved,
            use_github=use_github,
            ruleset_file=ruleset_file,
            repo_arg=repo_arg,
            default_branch=default_branch,
            gh_bin=gh_bin,
            timeout=timeout,
        )
    )

    counts = {
        status: sum(1 for item in findings if item.status == status)
        for status in ("PASS", "WARN", "FAIL", "NOT_RUN", "NOT_APPLICABLE")
    }
    derived_status = "FAIL" if counts["FAIL"] > 0 else ("PARTIAL" if counts["NOT_RUN"] > 0 else "PASS")

    return {
        "schema_version": "openagenticsecurity.audit.repo-self-check.v1",
        "authority": "candidate",
        "trusted": False,
        "target_name": resolved.name,
        "derived_status": derived_status,
        "counts": counts,
        "findings": [asdict(item) for item in findings],
        "does_not_prove": list(DOES_NOT_PROVE),
    }


def _render_text(report: Mapping[str, object]) -> str:
    counts = report["counts"]
    assert isinstance(counts, Mapping)
    findings = report["findings"]
    assert isinstance(findings, list)

    lines = [
        f"=== OpenAgenticSecurity Self-Audit: {report['target_name']} ===",
        f"Authority : {report['authority']} (trusted={str(report['trusted']).lower()}; read-only, not self-attesting)",
        (
            f"Summary   : derived={report['derived_status']} | "
            f"FAIL={counts['FAIL']}  WARN={counts['WARN']}  PASS={counts['PASS']}  "
            f"NOT_RUN={counts['NOT_RUN']}  N/A={counts['NOT_APPLICABLE']}"
        ),
        "",
    ]

    for layer_code, layer_label in (
        ("L1", "Layer 1 — Agent Context & Truth Boundary"),
        ("L2", "Layer 2 — Local Git, CI Supply Chain & Static Code Traps"),
        ("L3", "Layer 3 — GitHub Merge Boundary (External Enforcement)"),
    ):
        layer_items = [item for item in findings if item["layer"] == layer_code]
        if not layer_items:
            continue
        lines.append(f"[{layer_label}]")
        for item in layer_items:
            loc = f" ({item['location']})" if item["location"] else ""
            lines.append(f"  {item['status']:<14} {item['rule_id']:<13} {item['title']}{loc}")
            if item["status"] in {"FAIL", "WARN", "NOT_RUN"}:
                lines.append(f"                 -> {item['detail']}")
                if item["remediation"]:
                    lines.append(f"                 fix: {item['remediation']}")
        lines.append("")

    lines.append("Does NOT prove:")
    for limit in report["does_not_prove"]:  # type: ignore[union-attr]
        lines.append(f"  - {limit}")

    if counts["FAIL"] > 0:
        lines.append("")
        lines.append("Next step: fix FAIL items above, or run scripts/bootstrap.sh --dry-run --profile L1 --target <repo>.")
    return "\n".join(lines) + "\n"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "target",
        type=Path,
        help="Path to the local repository directory to inspect (strictly read-only).",
    )
    parser.add_argument(
        "--github",
        action="store_true",
        help="Also query live GitHub Branch Rulesets read-only via `gh api` (zero pip install).",
    )
    parser.add_argument(
        "--github-ruleset-file",
        type=Path,
        help="Evaluate an offline raw GitHub Ruleset JSON object or array instead of calling `gh`.",
    )
    parser.add_argument(
        "--repo",
        help="Explicit GitHub owner/repo slug for --github (default: inferred from origin remote).",
    )
    parser.add_argument(
        "--default-branch",
        help="Expected default branch name (default: queried from GitHub in --github mode, or 'main').",
    )
    parser.add_argument(
        "--format",
        choices=("text", "json"),
        default="text",
        help="Output format (default: text).",
    )
    parser.add_argument(
        "--gh-bin",
        default="gh",
        help="GitHub CLI binary name/path for --github mode (default: gh).",
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
    if args.github and args.github_ruleset_file is not None:
        print("audit-repo input error: pass either --github or --github-ruleset-file, not both", file=sys.stderr)
        return 1
    if args.timeout < 1:
        print("audit-repo input error: --timeout must be >= 1", file=sys.stderr)
        return 1

    try:
        report = audit_repository(
            args.target,
            use_github=args.github,
            ruleset_file=args.github_ruleset_file,
            repo_arg=args.repo,
            default_branch=args.default_branch,
            gh_bin=args.gh_bin,
            timeout=args.timeout,
        )
    except AuditNotRunError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    except AuditInputError as exc:
        print(f"audit-repo input error: {exc}", file=sys.stderr)
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
