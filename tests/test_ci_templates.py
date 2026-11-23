from __future__ import annotations

import importlib.util
from pathlib import Path
import shlex
import shutil
import subprocess
import sys

import yaml


REPO = Path(__file__).resolve().parents[1]
PYTHON_TEMPLATE = REPO / "profiles/L1-team/workflows/ci-python.yml"


def _ruff_cmd() -> list[str]:
    if importlib.util.find_spec("ruff") is not None:
        return [sys.executable, "-m", "ruff"]
    return [shutil.which("ruff") or "ruff"]


def _template_ruff_argv() -> list[str]:
    """Return the exact `ruff check ...` command the L1 Python template runs."""
    workflow = yaml.safe_load(PYTHON_TEMPLATE.read_text(encoding="utf-8"))
    commands = [
        line.strip()
        for job in workflow["jobs"].values()
        for step in job["steps"]
        for line in str(step.get("run", "")).splitlines()
        if line.strip().startswith("ruff check ")
    ]
    assert len(commands) == 1, f"expected exactly one ruff command in {PYTHON_TEMPLATE.name}: {commands}"
    argv = shlex.split(commands[0])
    return [*_ruff_cmd(), *argv[1:], "--no-cache"]


def _run(argv: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(argv, cwd=cwd, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)


def test_python_template_lint_accepts_an_ordinary_pytest_project(tmp_path: Path) -> None:
    # A first run must not be red merely because the tests use `assert`.
    (tmp_path / "app.py").write_text("def add(a, b):\n    return a + b\n", encoding="utf-8")
    (tmp_path / "tests").mkdir()
    (tmp_path / "tests/test_app.py").write_text(
        "from app import add\n\n\ndef test_add():\n    assert add(1, 2) == 3\n", encoding="utf-8"
    )
    (tmp_path / "test_top_level.py").write_text("def test_truth():\n    assert True\n", encoding="utf-8")

    proc = _run(_template_ruff_argv(), tmp_path)
    assert proc.returncode == 0, proc.stdout + proc.stderr


def test_python_template_lint_rejects_planted_security_bugs(tmp_path: Path) -> None:
    planted = {
        "shell_injection.py": ("import subprocess\n\n\ndef run(cmd):\n    return subprocess.run(cmd, shell=True)\n", "S602"),
        "eval_sink.py": ("def calc(expr):\n    return eval(expr)\n", "S307"),
        "fail_open.py": ("def allowed(check):\n    try:\n        return check()\n    except Exception:\n        pass\n", "S110"),
        "assert_auth.py": ("def guard(user):\n    assert user.is_admin\n", "S101"),
    }
    for name, (source, rule) in planted.items():
        case = tmp_path / name.removesuffix(".py")
        case.mkdir()
        (case / name).write_text(source, encoding="utf-8")
        proc = _run([*_template_ruff_argv(), "--output-format", "concise"], case)
        assert proc.returncode != 0, f"{name}: planted bug must fail the template lint"
        assert rule in proc.stdout, f"{name}: expected {rule}, got:\n{proc.stdout}"


def test_repository_passes_its_own_lint_baseline() -> None:
    proc = _run([*_ruff_cmd(), "check", "--no-cache", "."], REPO)
    assert proc.returncode == 0, proc.stdout + proc.stderr


def test_ruff_cmd_falls_back_to_path_binary_when_module_absent(monkeypatch) -> None:
    import importlib.util
    import shutil

    monkeypatch.setattr(importlib.util, "find_spec", lambda _name: None)
    monkeypatch.setattr(shutil, "which", lambda _name: "/usr/local/bin/ruff")
    assert _ruff_cmd() == ["/usr/local/bin/ruff"]
