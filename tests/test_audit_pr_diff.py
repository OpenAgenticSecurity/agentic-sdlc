from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys


REPO = Path(__file__).resolve().parents[1]
REFEREE = REPO / "scripts" / "audit-pr-diff.py"
SYNC_EXAMPLE = REPO / "profiles" / "L1-team" / "agentic-sync.example.json"


def _git(repo: Path, *args: str) -> None:
    subprocess.run(["git", "-C", str(repo), *args], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def _init_repo(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init", "-b", "main")
    _git(repo, "config", "user.email", "example@example.com")
    _git(repo, "config", "user.name", "Example")
    (repo / "src").mkdir()
    (repo / "tests").mkdir()
    (repo / "src/calc.py").write_text("def add(a: int, b: int) -> int:\n    return a + b\n", encoding="utf-8")
    (repo / "tests/test_calc.py").write_text(
        "from src.calc import add\n\n\ndef test_add() -> None:\n    assert add(1, 2) == 3\n    assert add(0, 0) == 0\n",
        encoding="utf-8",
    )
    _git(repo, "add", ".")
    _git(repo, "commit", "-m", "initial")
    return repo


def _run_referee(*args: str, isolated: bool = True) -> subprocess.CompletedProcess[str]:
    cmd = [sys.executable]
    if isolated:
        cmd.append("-S")
    cmd.extend([str(REFEREE), *args])
    return subprocess.run(cmd, cwd=REPO, text=True, capture_output=True, check=False)


def test_clean_feature_and_test_diff_passes(tmp_path: Path) -> None:
    repo = _init_repo(tmp_path)
    (repo / "src/calc.py").write_text(
        "def add(a: int, b: int) -> int:\n    return a + b\n\n\ndef sub(a: int, b: int) -> int:\n    return a - b\n",
        encoding="utf-8",
    )
    (repo / "tests/test_calc.py").write_text(
        "from src.calc import add, sub\n\n\ndef test_ops() -> None:\n    assert add(1, 2) == 3\n    assert add(0, 0) == 0\n    assert sub(5, 2) == 3\n",
        encoding="utf-8",
    )
    _git(repo, "add", ".")
    _git(repo, "commit", "-m", "add sub with test")

    summary = tmp_path / "step-summary.md"
    proc = _run_referee("--repo", str(repo), "--base", "HEAD~1", "--head", "HEAD", "--format", "json", "--summary-file", str(summary))
    assert proc.returncode == 0, proc.stdout + proc.stderr
    report = json.loads(proc.stdout)
    assert report["authority"] == "candidate"
    assert report["trusted"] is False
    by_rule = {f["rule_id"]: f for f in report["findings"]}
    # Touching tests/ flags OAS-DIFF-01 WARN (non-self-attesting), while OAS-DIFF-02 is PASS (exit 0).
    assert by_rule["OAS-DIFF-01"]["status"] == "WARN"
    assert by_rule["OAS-DIFF-02"]["status"] == "PASS"
    assert "Non-Self-Attestation Notice" in summary.read_text(encoding="utf-8")


def test_catches_suppression_injection_and_assertion_deletion(tmp_path: Path) -> None:
    repo = _init_repo(tmp_path)
    # 1. Inject inline noqa and ts-ignore suppressions + 2. Delete one existing assertion
    noqa_tag = "#" + " noqa: S307"
    (repo / "src/calc.py").write_text(
        f"def add(a: int, b: int) -> int:\n    return eval('a + b')  {noqa_tag}\n",
        encoding="utf-8",
    )
    (repo / "src/ui.ts").write_text("// @ts-ignore\nexport const x: number = 'bad';\n", encoding="utf-8")
    (repo / "tests/test_calc.py").write_text(
        "from src.calc import add\n\n\ndef test_add() -> None:\n    assert add(1, 2) == 3\n",
        encoding="utf-8",
    )
    (repo / ".github/workflows").mkdir(parents=True)
    (repo / ".github/workflows/ci.yml").write_text("name: CI\n", encoding="utf-8")
    # Prose docs mentioning suppression tokens must NOT trigger false positives
    noqa_str = "#" + " noqa"
    (repo / "README.md").write_text(f"Never add `{noqa_str}` to silence gates.\n", encoding="utf-8")
    _git(repo, "add", ".")
    _git(repo, "commit", "-m", "reward hack")

    proc = _run_referee("--repo", str(repo), "--base", "HEAD~1", "--head", "HEAD", "--format", "json")
    assert proc.returncode == 2, proc.stdout + proc.stderr
    by_rule = {f["rule_id"]: f for f in json.loads(proc.stdout)["findings"]}
    assert ".github/workflows/ci.yml" in by_rule["OAS-DIFF-01"]["items"]
    assert by_rule["OAS-DIFF-02"]["status"] == "FAIL"
    joined = "\n".join(by_rule["OAS-DIFF-02"]["items"])
    assert "src/calc.py" in joined
    assert "src/ui.ts" in joined
    assert "tests/test_calc.py (removed 1 assertion line(s), added 0)" in joined
    assert "README.md" not in joined

    # Explicit auditable waiver turns FAIL into WAIVED (exit 0) without pretending PASS
    waived = _run_referee(
        "--repo",
        str(repo),
        "--base",
        "HEAD~1",
        "--head",
        "HEAD",
        "--waiver",
        "OAS-DIFF-02: consolidated duplicate assertion reviewed by @owner",
        "--format",
        "json",
    )
    assert waived.returncode == 0, waived.stderr
    w_rule = {f["rule_id"]: f for f in json.loads(waived.stdout)["findings"]}
    assert w_rule["OAS-DIFF-02"]["status"] == "WAIVED"


def test_quoted_strings_mentioning_suppressions_do_not_false_positive(tmp_path: Path) -> None:
    repo = _init_repo(tmp_path)
    src_line = 'FORBIDDEN = ["#' + ' noqa", "// eslint-disable", "// @ts-ignore"]\n'
    (repo / "src/checker.py").write_text(src_line, encoding="utf-8")
    _git(repo, "add", ".")
    _git(repo, "commit", "-m", "string literals only")

    proc = _run_referee("--repo", str(repo), "--base", "HEAD~1", "--head", "HEAD", "--format", "json")
    assert proc.returncode == 0, proc.stdout + proc.stderr
    by_rule = {f["rule_id"]: f for f in json.loads(proc.stdout)["findings"]}
    assert by_rule["OAS-DIFF-01"]["status"] == "PASS"
    assert by_rule["OAS-DIFF-02"]["status"] == "PASS"


def test_auto_runs_coupled_change_sync_when_config_present(tmp_path: Path) -> None:
    repo = _init_repo(tmp_path)
    (repo / ".agentic-sync.json").write_text(SYNC_EXAMPLE.read_text(encoding="utf-8"), encoding="utf-8")
    _git(repo, "add", ".")
    _git(repo, "commit", "-m", "add sync config")

    # Edit src/calc.py without touching tests/ -> OAS-DIFF-03 must FAIL
    (repo / "src/calc.py").write_text("def add(a: int, b: int) -> int:\n    return a + b + 0\n", encoding="utf-8")
    _git(repo, "add", ".")
    _git(repo, "commit", "-m", "code without test")

    proc = _run_referee("--repo", str(repo), "--base", "HEAD~1", "--head", "HEAD", "--format", "json")
    assert proc.returncode == 2
    by_rule = {f["rule_id"]: f for f in json.loads(proc.stdout)["findings"]}
    assert by_rule["OAS-DIFF-03"]["status"] == "FAIL"


def test_rejects_unsafe_refs_and_missing_git(tmp_path: Path) -> None:
    repo = _init_repo(tmp_path)
    bad = _run_referee("--repo", str(repo), "--base=--exec=evil", "--head", "HEAD")
    assert bad.returncode == 1
    assert "unsafe Git base ref" in bad.stderr

    no_git = _run_referee("--repo", str(repo), "--base", "HEAD", "--head", "HEAD", "--git-bin", "nonexistent-git-bin")
    assert no_git.returncode == 1
    assert "NOT_RUN" in no_git.stderr
