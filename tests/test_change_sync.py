from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys


REPO = Path(__file__).resolve().parents[1]
CHECKER = REPO / "scripts" / "check-change-sync.py"
EXAMPLE_CFG = REPO / "profiles" / "L1-team" / "agentic-sync.example.json"


def _run_sync(*args: str, isolated: bool = False) -> subprocess.CompletedProcess[str]:
    cmd = [sys.executable]
    if isolated:
        cmd.append("-S")
    cmd.extend([str(CHECKER), *args])
    return subprocess.run(
        cmd,
        cwd=REPO,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )


def test_sync_fails_when_code_or_api_changes_lack_tests_or_docs() -> None:
    proc = _run_sync(
        "--config",
        str(EXAMPLE_CFG),
        "--changed",
        "src/api/orders.py",
        "--format",
        "json",
        isolated=True,
    )
    assert proc.returncode == 2, proc.stdout + proc.stderr
    report = json.loads(proc.stdout)
    assert report["schema_version"] == "openagenticsecurity.sync.change-sync-report.v1"
    assert report["authority"] == "candidate"
    assert report["trusted"] is False
    assert report["derived_status"] == "FAIL"
    by_id = {o["rule_id"]: o for o in report["outcomes"]}
    assert by_id["SYNC-TESTS"]["status"] == "FAIL"
    assert by_id["SYNC-CONTRACT-DOCS"]["status"] == "FAIL"
    assert by_id["SYNC-BILINGUAL-DOCS"]["status"] == "NOT_APPLICABLE"


def test_sync_passes_when_coupled_tests_and_docs_are_updated() -> None:
    proc = _run_sync(
        "--config",
        str(EXAMPLE_CFG),
        "--changed",
        "src/api/orders.py",
        "--changed",
        "tests/test_orders.py",
        "--changed",
        "docs/architecture/STATUS.md",
        "--format",
        "json",
        isolated=True,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    report = json.loads(proc.stdout)
    assert report["derived_status"] == "PASS"
    assert report["counts"]["FAIL"] == 0


def test_bidirectional_mirror_catches_missing_translation_and_accepts_pair() -> None:
    fail_proc = _run_sync(
        "--config",
        str(EXAMPLE_CFG),
        "--changed",
        "docs/guide.md",
        "--format",
        "json",
    )
    assert fail_proc.returncode == 2
    by_id = {o["rule_id"]: o for o in json.loads(fail_proc.stdout)["outcomes"]}
    assert by_id["SYNC-BILINGUAL-DOCS"]["status"] == "FAIL"
    assert by_id["SYNC-BILINGUAL-DOCS"]["missing"] == ["docs/guide.zh.md"]

    pass_proc = _run_sync(
        "--config",
        str(EXAMPLE_CFG),
        "--changed",
        "docs/guide.md",
        "--changed",
        "docs/guide.zh.md",
        "--format",
        "json",
    )
    assert pass_proc.returncode == 0


def test_explicit_waiver_records_waived_never_pass_and_rejects_blank_reason() -> None:
    waived = _run_sync(
        "--config",
        str(EXAMPLE_CFG),
        "--changed",
        "src/core.py",
        "--waiver",
        "SYNC-TESTS: pure comment refactor verified by existing suite",
        "--format",
        "json",
    )
    assert waived.returncode == 0, waived.stdout + waived.stderr
    report = json.loads(waived.stdout)
    assert report["derived_status"] == "WAIVED"
    by_id = {o["rule_id"]: o for o in report["outcomes"]}
    assert by_id["SYNC-TESTS"]["status"] == "WAIVED"
    assert "comment refactor" in by_id["SYNC-TESTS"]["waiver_reason"]

    bad_waiver = _run_sync(
        "--config",
        str(EXAMPLE_CFG),
        "--changed",
        "src/core.py",
        "--waiver",
        "SYNC-TESTS: ok",
    )
    assert bad_waiver.returncode == 1
    assert "at least 5 characters" in bad_waiver.stderr


def test_git_diff_mode_detects_missing_and_satisfied_sync(tmp_path: Path) -> None:
    subprocess.run(["git", "init", "-b", "main", str(tmp_path)], check=True, stdout=subprocess.DEVNULL)
    subprocess.run(["git", "-C", str(tmp_path), "config", "user.email", "example@example.com"], check=True)
    subprocess.run(["git", "-C", str(tmp_path), "config", "user.name", "Example"], check=True)
    (tmp_path / "src").mkdir()
    (tmp_path / "src/app.py").write_text("x = 1\n", encoding="utf-8")
    subprocess.run(["git", "-C", str(tmp_path), "add", "."], check=True)
    subprocess.run(["git", "-C", str(tmp_path), "commit", "-m", "base"], check=True, stdout=subprocess.DEVNULL)

    (tmp_path / "src/app.py").write_text("x = 2\n", encoding="utf-8")
    subprocess.run(["git", "-C", str(tmp_path), "add", "."], check=True)
    subprocess.run(["git", "-C", str(tmp_path), "commit", "-m", "code only"], check=True, stdout=subprocess.DEVNULL)

    missing = _run_sync("--config", str(EXAMPLE_CFG), "--repo", str(tmp_path), "--base", "HEAD~1", "--head", "HEAD")
    assert missing.returncode == 2, missing.stdout + missing.stderr
    assert "SYNC-TESTS" in missing.stdout

    (tmp_path / "tests").mkdir()
    (tmp_path / "tests/test_app.py").write_text("assert True\n", encoding="utf-8")
    subprocess.run(["git", "-C", str(tmp_path), "add", "."], check=True)
    subprocess.run(["git", "-C", str(tmp_path), "commit", "-m", "add test"], check=True, stdout=subprocess.DEVNULL)

    ok = _run_sync("--config", str(EXAMPLE_CFG), "--repo", str(tmp_path), "--base", "HEAD~2", "--head", "HEAD")
    assert ok.returncode == 0, ok.stdout + ok.stderr


def test_rejects_symlinks_duplicate_keys_and_unsafe_git_refs(tmp_path: Path) -> None:
    dup = tmp_path / "dup.json"
    dup.write_text('{"rules": [], "rules": []}', encoding="utf-8")
    p1 = _run_sync("--config", str(dup), "--changed", "src/a.py")
    assert p1.returncode == 1
    assert "duplicate JSON key" in p1.stderr

    sym = tmp_path / "sym.json"
    sym.symlink_to(EXAMPLE_CFG)
    p2 = _run_sync("--config", str(sym), "--changed", "src/a.py")
    assert p2.returncode == 1
    assert "non-symlink" in p2.stderr

    p3 = _run_sync("--config", str(EXAMPLE_CFG), "--repo", str(tmp_path), "--base=--exec=evil", "--head", "HEAD")
    assert p3.returncode == 1
    assert "unsafe Git base ref" in p3.stderr

    p4 = _run_sync("--config", str(EXAMPLE_CFG), "--repo", str(tmp_path), "--base", "main;id", "--head", "HEAD")
    assert p4.returncode == 1
    assert "unsafe Git base ref" in p4.stderr
