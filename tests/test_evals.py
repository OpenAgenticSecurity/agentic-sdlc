from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys

import yaml


REPO = Path(__file__).resolve().parents[1]


def test_deterministic_eval_suite_runs_stdlib_only_and_passes_all_cases() -> None:
    proc = subprocess.run(
        [sys.executable, "-S", str(REPO / "scripts/run-evals.py"), "--format", "json"],
        cwd=REPO,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    summary = json.loads(proc.stdout)
    assert summary["schema_version"] == "openagenticsecurity.eval.deterministic-suite.v1"
    assert summary["authority"] == "candidate"
    assert summary["trusted"] is False
    assert summary["all_passed"] is True
    assert summary["traps_caught"] == summary["traps_total"] >= 17
    assert summary["control_false_positives"] == 0
    assert summary["controls_total"] >= 2


def test_starter_backend_contract_gate_example_is_runnable() -> None:
    proc = subprocess.run(
        [sys.executable, "-m", "pytest", "-q", str(REPO / "examples/backend-contract-gates.py")],
        cwd=REPO,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "4 passed" in proc.stdout


def test_skill_eval_cases_have_prompts_and_rubrics() -> None:
    skill_eval_root = REPO / "evals/skills"
    cases = sorted(p for p in skill_eval_root.iterdir() if p.is_dir())
    assert len(cases) >= 3, [c.name for c in cases]
    for case_dir in cases:
        prompt = case_dir / "prompt.md"
        rubric = case_dir / "graders/rubric.md"
        assert prompt.is_file() and prompt.read_text(encoding="utf-8").strip(), f"missing prompt: {case_dir.name}"
        assert rubric.is_file() and rubric.read_text(encoding="utf-8").strip(), f"missing rubric: {case_dir.name}"


def test_composite_github_action_manifest_is_valid_and_safe() -> None:
    action_path = REPO / "action.yml"
    assert action_path.is_file(), "missing root action.yml"
    raw = action_path.read_text(encoding="utf-8")
    parsed = yaml.safe_load(raw)
    assert isinstance(parsed, dict)
    assert parsed["runs"]["using"] == "composite"
    steps = parsed["runs"]["steps"]
    assert steps and isinstance(steps, list)
    # Inputs must be passed via env:, never directly interpolated into `run:` shell code.
    for step in steps:
        run_block = str(step.get("run", ""))
        assert "${{ inputs." not in run_block, "action.yml must pass inputs via env:, not raw shell interpolation"


def test_static_pages_site_has_zero_external_trackers_or_unsafe_dom_sinks() -> None:
    html = (REPO / "site/index.html").read_text(encoding="utf-8")
    css = (REPO / "site/styles.css").read_text(encoding="utf-8")
    js = (REPO / "site/app.js").read_text(encoding="utf-8")
    assert "<!DOCTYPE html>" in html
    assert "styles.css" in html and "app.js" in html
    assert ":root" in css
    # Zero external CDN scripts/stylesheets or unsafe DOM sinks
    assert 'src="http' not in html and 'href="http' not in html.split("<body", 1)[0]
    for sink in ("innerHTML", "outerHTML", "document.write", "eval(", "new Function("):
        assert sink not in js, f"site/app.js must not use unsafe sink {sink!r}"
