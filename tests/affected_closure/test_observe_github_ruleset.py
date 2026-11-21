from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess
import sys


REPO = Path(__file__).resolve().parents[2]
OBSERVER = REPO / "scripts" / "observe-github-ruleset.py"
POLICY_EXAMPLE = REPO / "profiles" / "L2-governed" / "ruleset-policy.example.json"


def _strong_raw_ruleset(
    *,
    ruleset_id: int = 4242,
    required_contexts: list[str] | None = None,
    integration_id: int | None = 15368,
    require_last_push: bool = True,
    bypass_actors: list[dict[str, object]] | None = None,
) -> dict[str, object]:
    contexts = (
        required_contexts
        if required_contexts is not None
        else [
            "security-scan",
            "agent-check",
        ]
    )
    return {
        "id": ruleset_id,
        "name": "Protect main",
        "target": "branch",
        "enforcement": "active",
        "conditions": {
            "ref_name": {
                "include": ["~DEFAULT_BRANCH"],
                "exclude": [],
            }
        },
        "bypass_actors": bypass_actors if bypass_actors is not None else [],
        "rules": [
            {
                "type": "pull_request",
                "parameters": {
                    "required_approving_review_count": 2,
                    "require_code_owner_review": True,
                    "dismiss_stale_reviews_on_push": True,
                    "require_last_push_approval": require_last_push,
                },
            },
            {
                "type": "required_status_checks",
                "parameters": {
                    "required_status_checks": [
                        {"context": ctx, "integration_id": integration_id} for ctx in contexts
                    ]
                },
            },
        ],
    }


def _run_observer(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(OBSERVER), *args],
        cwd=REPO,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )


def test_offline_strong_ruleset_passes_validate_and_computes_exact_digest(tmp_path: Path) -> None:
    raw_bytes = (json.dumps(_strong_raw_ruleset(), indent=2) + "\n").encode("utf-8")
    raw_file = tmp_path / "ruleset.json"
    raw_file.write_bytes(raw_bytes)
    expected_digest = "sha256:" + hashlib.sha256(raw_bytes).hexdigest()

    proc = _run_observer(
        "--input-file",
        str(raw_file),
        "--repo",
        "OpenAgenticSecurity/agentic-sdlc",
        "--ruleset-id",
        "4242",
        "--default-branch",
        "main",
        "--policy",
        str(POLICY_EXAMPLE),
        "--observed-at",
        "2026-11-20T12:00:00Z",
        "--validate",
    )
    assert proc.returncode == 0, proc.stderr
    report = json.loads(proc.stdout)
    assert report["schema_version"] == "openagenticsecurity.governance.enforcement-evidence.v1"
    assert report["authority"] == "candidate"
    assert report["trusted"] is False
    assert report["source"]["reference"] == "repos/OpenAgenticSecurity/agentic-sdlc/rulesets/4242"
    assert report["source"]["response_digest"] == expected_digest
    observed_contexts = [
        item["context"] for item in report["observation"]["pull_request"]["required_status_checks"]
    ]
    assert observed_contexts == [
        "agent-check",
        "security-scan",
    ]


def test_weak_rulesets_fail_validate_with_exit_code_2(tmp_path: Path) -> None:
    cases = [
        (
            "missing-status",
            _strong_raw_ruleset(required_contexts=["agent-check"]),
            "required status",
        ),
        (
            "last-push-disabled",
            _strong_raw_ruleset(require_last_push=False),
            "last-push approval",
        ),
        (
            "unconditional-bypass",
            _strong_raw_ruleset(
                bypass_actors=[
                    {
                        "actor_id": 5,
                        "actor_type": "RepositoryRole",
                        "bypass_mode": "always",
                    }
                ]
            ),
            "unconditional bypass",
        ),
        (
            "unbound-status-source",
            _strong_raw_ruleset(integration_id=None),
            "status check source",
        ),
        (
            "unapproved-pr-bypass",
            _strong_raw_ruleset(
                bypass_actors=[
                    {
                        "actor_id": 987654,
                        "actor_type": "Integration",
                        "bypass_mode": "pull_request",
                    }
                ]
            ),
            "pull_request bypass",
        ),
    ]
    for name, payload, expected_err in cases:
        raw_file = tmp_path / f"{name}.json"
        raw_file.write_text(json.dumps(payload), encoding="utf-8")
        proc = _run_observer(
            "--input-file",
            str(raw_file),
            "--repo",
            "OpenAgenticSecurity/agentic-sdlc",
            "--policy",
            str(POLICY_EXAMPLE),
            "--observed-at",
            "2026-11-20T12:00:00Z",
            "--validate",
        )
        assert proc.returncode == 2, f"{name}: expected exit 2, got {proc.returncode} ({proc.stderr})"
        assert expected_err in proc.stderr, f"{name}: {proc.stderr}"


def test_duplicate_json_key_in_raw_ruleset_is_rejected(tmp_path: Path) -> None:
    raw_file = tmp_path / "dup.json"
    raw_file.write_text('{"id": 1, "id": 2, "name": "dup", "target": "branch", "enforcement": "active"}', encoding="utf-8")
    proc = _run_observer(
        "--input-file",
        str(raw_file),
        "--repo",
        "OpenAgenticSecurity/agentic-sdlc",
        "--policy",
        str(POLICY_EXAMPLE),
    )
    assert proc.returncode == 1
    assert "duplicate JSON key" in proc.stderr


def test_unsafe_repo_identifier_is_rejected(tmp_path: Path) -> None:
    raw_file = tmp_path / "ok.json"
    raw_file.write_text(json.dumps(_strong_raw_ruleset()), encoding="utf-8")
    proc = _run_observer(
        "--input-file",
        str(raw_file),
        "--repo",
        "../escape/repo",
        "--policy",
        str(POLICY_EXAMPLE),
    )
    assert proc.returncode == 1
    assert "unsafe repository identifier" in proc.stderr


def test_missing_gh_binary_fails_closed_with_not_run(tmp_path: Path) -> None:
    proc = _run_observer(
        "--live",
        "--repo",
        "OpenAgenticSecurity/agentic-sdlc",
        "--ruleset-id",
        "4242",
        "--policy",
        str(POLICY_EXAMPLE),
        "--gh-bin",
        "nonexistent-gh-binary-for-test-only",
    )
    assert proc.returncode == 1
    assert "NOT_RUN" in proc.stderr


def test_symlink_input_file_is_rejected(tmp_path: Path) -> None:
    target = tmp_path / "real.json"
    target.write_text(json.dumps(_strong_raw_ruleset()), encoding="utf-8")
    link = tmp_path / "link.json"
    link.symlink_to(target)
    proc = _run_observer(
        "--input-file",
        str(link),
        "--repo",
        "OpenAgenticSecurity/agentic-sdlc",
        "--policy",
        str(POLICY_EXAMPLE),
    )
    assert proc.returncode == 1
    assert "regular non-symlink file required" in proc.stderr


def test_live_api_null_actor_id_deploy_key_exempt_and_evaluate_fail_policy_cleanly(tmp_path: Path) -> None:
    # Real GitHub API returns actor_id=null for OrganizationAdmin/DeployKey, bypass_mode="exempt",
    # and enforcement="evaluate". Observer must normalize cleanly and fail --validate with exit 2.
    exempt_payload = _strong_raw_ruleset(
        bypass_actors=[
            {"actor_id": None, "actor_type": "OrganizationAdmin", "bypass_mode": "exempt"},
            {"actor_id": None, "actor_type": "DeployKey", "bypass_mode": "pull_request"},
        ]
    )
    f1 = tmp_path / "exempt.json"
    f1.write_text(json.dumps(exempt_payload), encoding="utf-8")
    p1 = _run_observer(
        "--input-file",
        str(f1),
        "--repo",
        "OpenAgenticSecurity/agentic-sdlc",
        "--policy",
        str(POLICY_EXAMPLE),
        "--observed-at",
        "2026-11-20T12:00:00Z",
        "--validate",
    )
    assert p1.returncode == 2, p1.stderr
    assert "unconditional bypass" in p1.stderr

    eval_payload = _strong_raw_ruleset()
    eval_payload["enforcement"] = "evaluate"
    f2 = tmp_path / "evaluate.json"
    f2.write_text(json.dumps(eval_payload), encoding="utf-8")
    p2 = _run_observer(
        "--input-file",
        str(f2),
        "--repo",
        "OpenAgenticSecurity/agentic-sdlc",
        "--policy",
        str(POLICY_EXAMPLE),
        "--observed-at",
        "2026-11-20T12:00:00Z",
        "--validate",
    )
    assert p2.returncode == 2, p2.stderr
    assert "not active" in p2.stderr


def test_importable_github_ruleset_template_passes_validate(tmp_path: Path) -> None:
    template = json.loads(
        (REPO / "profiles/L2-governed/github-ruleset.import.json").read_text(encoding="utf-8")
    )
    template["id"] = 999
    raw = tmp_path / "imported.json"
    raw.write_text(json.dumps(template), encoding="utf-8")
    proc = _run_observer(
        "--input-file",
        str(raw),
        "--repo",
        "OpenAgenticSecurity/agentic-sdlc",
        "--policy",
        str(POLICY_EXAMPLE),
        "--observed-at",
        "2026-11-20T12:00:00Z",
        "--validate",
    )
    assert proc.returncode == 0, proc.stderr


def test_symlink_output_path_is_rejected(tmp_path: Path) -> None:
    raw = tmp_path / "ok.json"
    raw.write_text(json.dumps(_strong_raw_ruleset()), encoding="utf-8")
    outside = tmp_path / "outside.json"
    outside.write_text("keep\n", encoding="utf-8")
    out_link = tmp_path / "out-link.json"
    out_link.symlink_to(outside)
    proc = _run_observer(
        "--input-file",
        str(raw),
        "--repo",
        "OpenAgenticSecurity/agentic-sdlc",
        "--policy",
        str(POLICY_EXAMPLE),
        "--output",
        str(out_link),
    )
    assert proc.returncode == 1
    assert outside.read_text(encoding="utf-8") == "keep\n"

    # Writing through a symlinked ancestor directory (like macOS /tmp -> /private/tmp) must still work
    real_dir = tmp_path / "real-tmp"
    real_dir.mkdir()
    sym_dir = tmp_path / "sym-tmp"
    sym_dir.symlink_to(real_dir)
    ok_out = sym_dir / "evidence.json"
    ok_proc = _run_observer(
        "--input-file",
        str(raw),
        "--repo",
        "OpenAgenticSecurity/agentic-sdlc",
        "--policy",
        str(POLICY_EXAMPLE),
        "--output",
        str(ok_out),
    )
    assert ok_proc.returncode == 0, ok_proc.stderr
    assert ok_out.is_file()


def test_importable_ruleset_pins_status_check_integration_id() -> None:
    template = json.loads(
        (REPO / "profiles/L2-governed/github-ruleset.import.json").read_text(encoding="utf-8")
    )
    status_rules = [r for r in template["rules"] if r["type"] == "required_status_checks"]
    assert len(status_rules) == 1
    checks = status_rules[0]["parameters"]["required_status_checks"]
    assert checks
    for check in checks:
        assert isinstance(check["integration_id"], int) and check["integration_id"] >= 1, (
            f"status check {check['context']!r} must bind an explicit integration_id, not null"
        )


def test_missing_jsonschema_exits_1_not_run_instead_of_policy_failure_2(tmp_path: Path) -> None:
    raw = tmp_path / "ok.json"
    raw.write_text(json.dumps(_strong_raw_ruleset()), encoding="utf-8")
    out = tmp_path / "out.json"
    proc = subprocess.run(
        [
            sys.executable,
            "-S",
            str(OBSERVER),
            "--input-file",
            str(raw),
            "--repo",
            "OpenAgenticSecurity/agentic-sdlc",
            "--policy",
            str(POLICY_EXAMPLE),
            "--observed-at",
            "2026-11-20T12:00:00Z",
            "--output",
            str(out),
            "--validate",
        ],
        cwd=REPO,
        text=True,
        capture_output=True,
        check=False,
    )
    assert proc.returncode == 1, f"missing jsonschema must exit 1 (NOT_RUN), got {proc.returncode}: {proc.stderr}"
    assert "NOT_RUN" in proc.stderr


def test_live_gh_timeout_fails_closed_with_not_run(tmp_path: Path) -> None:
    slow_gh = tmp_path / "slow-gh"
    slow_gh.write_text("#!/bin/sh\nsleep 5\n", encoding="utf-8")
    slow_gh.chmod(0o755)
    proc = _run_observer(
        "--live",
        "--repo",
        "OpenAgenticSecurity/agentic-sdlc",
        "--ruleset-id",
        "4242",
        "--policy",
        str(POLICY_EXAMPLE),
        "--gh-bin",
        str(slow_gh),
        "--timeout",
        "1",
    )
    assert proc.returncode == 1
    assert "NOT_RUN" in proc.stderr and "timed out" in proc.stderr
