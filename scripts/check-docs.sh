#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)"
PYTHON="${PYTHON:-python3}"

"$PYTHON" - "$ROOT" <<'PY'
from __future__ import annotations

import json
from pathlib import Path
import re
import sys

root = Path(sys.argv[1]).resolve()
errors: list[str] = []

# 1. Required repository files
required_files = [
    "README.md",
    "README.zh.md",
    "llms.txt",
    "BOOTSTRAP.md",
    "BOOTSTRAP.zh.md",
    "AGENTS.md",
    "CLAUDE.md",
    "MATURITY.md",
    "MATURITY.zh.md",
    "LICENSE",
    "CODE_OF_CONDUCT.md",
    "CONTRIBUTING.md",
    "SECURITY.md",
    "Makefile",
    "pyproject.toml",
    "action.yml",
    ".github/workflows/ci.yml",
    ".github/workflows/release.yml",
    ".github/workflows/scorecard.yml",
    ".github/workflows/pages.yml",
    ".github/release.yml",
    ".github/dependabot.yml",
    ".github/ISSUE_TEMPLATE/config.yml",
    ".github/ISSUE_TEMPLATE/bug-report.yml",
    ".github/ISSUE_TEMPLATE/proposal.yml",
    ".gitattributes",
    ".agentic-sync.json",
    "requirements-test.in",
    "requirements-test.txt",
    ".github/CODEOWNERS",
    ".github/pull_request_template.md",
    ".claude-plugin/plugin.json",
    ".claude-plugin/marketplace.json",
    ".cursor-plugin/plugin.json",
    ".codex-plugin/plugin.json",
    "docs/manifesto.md",
    "docs/manifesto.zh.md",
    "docs/ontology.md",
    "docs/ontology.zh.md",
    "docs/empirical-findings.md",
    "docs/empirical-findings.zh.md",
    "docs/workflow-integration.md",
    "docs/workflow-integration.zh.md",
    "standards/README.md",
    "standards/README.zh.md",
    "checklists/README.md",
    "checklists/README.zh.md",
    "profiles/README.md",
    "profiles/README.zh.md",
    "skills/README.md",
    "skills/README.zh.md",
    "examples/README.md",
    "examples/README.zh.md",
    "evals/README.md",
    "evals/README.zh.md",
    "scripts/bootstrap.sh",
    "scripts/audit-repo.py",
    "scripts/audit-pr-diff.py",
    "scripts/check-change-sync.py",
    "scripts/run-evals.py",
    "site/index.html",
    "site/styles.css",
    "site/app.js",
]
for rel in required_files:
    if not (root / rel).is_file():
        errors.append(f"missing required file: {rel}")

# 2. Scan Markdown files for unresolved placeholders and broken local links
fence_re = re.compile(r"```[\s\S]*?```")
inline_code_re = re.compile(r"`[^`\n]+`")
link_re = re.compile(r"!?\[[^\]]*\]\(([^)]+)\)")
placeholder_patterns = [
    (re.compile(r"\b(?:TODO|FIXME|XXX)\b"), "TODO/FIXME/XXX"),
    (re.compile(r"\[TBD\]", re.IGNORECASE), "[TBD]"),
    (re.compile(r"(?<!\$)\{\{[^}\n]+\}\}"), "unresolved template {{...}}"),
]

def is_ignored(rel_path: Path) -> bool:
    return any(
        part in {"__pycache__", ".pytest_cache", ".git", ".venv", "node_modules"}
        for part in rel_path.parts
    )

for md in sorted(root.rglob("*.md")):
    rel = md.relative_to(root)
    if is_ignored(rel):
        continue
    text = md.read_text(encoding="utf-8")
    stripped = fence_re.sub("", text)
    stripped_no_inline = inline_code_re.sub("", stripped)

    for rx, label in placeholder_patterns:
        for match in rx.finditer(stripped_no_inline):
            errors.append(f"placeholder ({label}) in {rel.as_posix()}: {match.group(0)!r}")

    for match in link_re.finditer(stripped):
        raw_href = match.group(1).strip()
        if not raw_href:
            continue
        href = raw_href.split()[0].strip("<>")
        if href.startswith(("http://", "https://", "mailto:", "#")):
            continue
        target_part = href.split("#", 1)[0]
        if not target_part:
            continue
        target = (md.parent / target_part).resolve()
        try:
            target.relative_to(root)
        except ValueError:
            errors.append(f"link escapes repository root in {rel.as_posix()}: {href}")
            continue
        if not target.exists():
            errors.append(f"broken relative link in {rel.as_posix()}: {href}")

# 3. Verify ZERO host-specific /Users/<name> paths (allowing only /Users/example)
user_path_re = re.compile(r"/Users/([A-Za-z0-9._-]+)")
for path in sorted(root.rglob("*")):
    if not path.is_file() or path.is_symlink():
        continue
    rel = path.relative_to(root)
    if is_ignored(rel):
        continue
    try:
        content = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        continue
    for match in user_path_re.finditer(content):
        if match.group(1) != "example":
            errors.append(f"host-specific personal path in {rel.as_posix()}: {match.group(0)}")

# 4. Verify all non-invalid JSON files parse cleanly
for json_file in sorted(root.rglob("*.json")):
    rel = json_file.relative_to(root)
    if is_ignored(rel):
        continue
    if "invalid" in rel.parts:
        continue
    try:
        json.loads(json_file.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        errors.append(f"invalid JSON in {rel.as_posix()}: {exc}")

if errors:
    for err in errors:
        print(f"check-docs FAIL: {err}", file=sys.stderr)
    print(f"check-docs failed with {len(errors)} error(s)", file=sys.stderr)
    sys.exit(1)

print("check-docs passed: required files, links, placeholders, paths, and JSON are clean")
PY
