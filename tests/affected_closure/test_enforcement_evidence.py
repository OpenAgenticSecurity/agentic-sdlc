from __future__ import annotations

import copy
import importlib.util
import json
from pathlib import Path
import subprocess
import sys

import pytest


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts/check-enforcement-evidence.py"
FIXTURE_ROOT = (
    ROOT
    / "standards/testing-strategy/enforcement-evidence/fixtures"
)
CONTRACT_EN = ROOT / "standards/testing-strategy/enforcement-evidence-contract.md"
CONTRACT_ZH = ROOT / "standards/testing-strategy/enforcement-evidence-contract.zh.md"


def _load_checker():
    spec = importlib.util.spec_from_file_location(
        "enforcement_evidence_checker",
        SCRIPT,
    )
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _load(relative: str) -> dict[str, object]:
    return json.loads((FIXTURE_ROOT / relative).read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def checker():
    return _load_checker()


def test_committed_fixture_set_is_checked_by_the_real_cli(checker) -> None:
    completed = subprocess.run(
        [sys.executable, str(SCRIPT), "--root", str(ROOT), "check"],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    assert completed.returncode == 0, completed.stderr
    assert "fixtures passed" in completed.stdout


def test_valid_report_passes_semantic_validation(checker) -> None:
    checker.validate_report(
        _load("valid/strong-ruleset.json"),
        schema=checker._schema(ROOT),
    )


@pytest.mark.parametrize(
    ("mutation", "message"),
    [
        (lambda value: value.update({"trusted": True}), "schema"),
        (
            lambda value: value["observation"]["pull_request"].update(
                {"required_status_checks": []}
            ),
            "required status",
        ),
        (
            lambda value: value["observation"].update(
                {
                    "bypass_actors": [
                        {
                            "actor_id": 9,
                            "actor_type": "RepositoryRole",
                            "bypass_mode": "always",
                        }
                    ]
                }
            ),
            "unconditional bypass",
        ),
        (
            lambda value: value["observation"]["pull_request"].update(
                {"require_last_push_approval": False}
            ),
            "last-push approval",
        ),
        (
            lambda value: value["source"].update(
                {"reference": "repos/example-org/other-repo/rulesets/12345"}
            ),
            "source reference",
        ),
        (
            lambda value: value["observation"]["conditions"].update(
                {
                    "ref_name_include": ["refs/heads/other"],
                    "ref_name_exclude": [],
                }
            ),
            "default branch",
        ),
        (
            lambda value: value["observation"].update({"enforcement": "disabled"}),
            "not active",
        ),
        (
            lambda value: value["observation"]["pull_request"].update(
                {"required_approving_review_count": 1}
            ),
            "review count",
        ),
        (
            lambda value: value["observation"].update(
                {
                    "bypass_actors": [
                        {
                            "actor_id": 9,
                            "actor_type": "RepositoryRole",
                            "bypass_mode": "pull_request",
                        },
                        {
                            "actor_id": 7,
                            "actor_type": "RepositoryRole",
                            "bypass_mode": "pull_request",
                        },
                    ]
                }
            ),
            "sorted and unique",
        ),
        (
            lambda value: value["source"].update(
                {"response_digest": "not-a-digest"}
            ),
            "schema",
        ),
        (
            lambda value: value["observation"]["pull_request"].update(
                {
                    "required_status_checks": [
                        {"context": "architecture-model", "integration_id": None},
                        {"context": "check-docs", "integration_id": 15368},
                    ]
                }
            ),
            "status check source",
        ),
        (
            lambda value: value["observation"].update(
                {
                    "bypass_actors": [
                        {
                            "actor_id": 987654,
                            "actor_type": "Integration",
                            "bypass_mode": "pull_request",
                        }
                    ]
                }
            ),
            "pull_request bypass",
        ),
    ],
)
def test_mutations_never_turn_into_a_green_report(
    checker,
    mutation,
    message: str,
) -> None:
    report = copy.deepcopy(_load("valid/strong-ruleset.json"))
    mutation(report)
    with pytest.raises(checker.EnforcementEvidenceError, match=message):
        checker.validate_report(report, schema=checker._schema(ROOT))


def test_explicit_pr_bypass_allowlist_and_optional_source_binding(checker) -> None:
    schema = checker._schema(ROOT)
    # Explicitly allowlisting one break-glass pull_request actor permits ONLY that actor.
    allowed = copy.deepcopy(_load("valid/strong-ruleset.json"))
    allowed["policy"]["allowed_pull_request_bypass_actors"] = [
        {"actor_id": 42, "actor_type": "Team"}
    ]
    allowed["observation"]["bypass_actors"] = [
        {"actor_id": 42, "actor_type": "Team", "bypass_mode": "pull_request"}
    ]
    checker.validate_report(allowed, schema=schema)

    # An unlisted actor is still rejected even when another actor is allowlisted.
    sneaky = copy.deepcopy(allowed)
    sneaky["observation"]["bypass_actors"].append(
        {"actor_id": 99, "actor_type": "Integration", "bypass_mode": "pull_request"}
    )
    sneaky["observation"]["bypass_actors"].sort(
        key=lambda a: (a["actor_type"], -1 if a["actor_id"] is None else a["actor_id"], a["bypass_mode"])
    )
    with pytest.raises(checker.EnforcementEvidenceError, match="pull_request bypass"):
        checker.validate_report(sneaky, schema=schema)

    # Disabling source binding explicitly allows integration_id=null for non-App status checks.
    unbound_ok = copy.deepcopy(_load("valid/strong-ruleset.json"))
    unbound_ok["policy"]["require_status_check_source_binding"] = False
    unbound_ok["observation"]["pull_request"]["required_status_checks"] = [
        {"context": "architecture-model", "integration_id": None},
        {"context": "check-docs", "integration_id": None},
    ]
    checker.validate_report(unbound_ok, schema=schema)


def test_invalid_observed_at_rejected_even_without_rfc3339_validator(tmp_path: Path) -> None:
    bad = copy.deepcopy(_load("valid/strong-ruleset.json"))
    bad["observed_at"] = "2026-13-45T99:99:99Z"
    bad_file = tmp_path / "bad-ts.json"
    bad_file.write_text(json.dumps(bad), encoding="utf-8")

    # Simulate an environment that has jsonschema installed but NOT rfc3339-validator.
    code = (
        "import sys, runpy; "
        "sys.modules['rfc3339_validator'] = None; "
        f"sys.argv = ['check-enforcement-evidence.py', '--root', {str(ROOT)!r}, '--report', {str(bad_file)!r}, 'check']; "
        f"runpy.run_path({str(SCRIPT)!r}, run_name='__main__')"
    )
    proc = subprocess.run(
        [sys.executable, "-c", code],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    assert proc.returncode != 0, "impossible timestamp must fail closed even without rfc3339-validator"
    assert "observed_at" in proc.stderr or "date-time" in proc.stderr


def test_invalid_fixtures_fail_for_the_declared_reason(checker) -> None:
    checker.check_fixtures(ROOT)


def test_duplicate_keys_are_not_normalized(checker, tmp_path: Path) -> None:
    duplicate = tmp_path / "duplicate.json"
    duplicate.write_text(
        '{"schema_version":"one","schema_version":"two"}\n',
        encoding="utf-8",
    )
    with pytest.raises(checker.EnforcementEvidenceError, match="duplicate JSON key"):
        checker._strict_load(duplicate)


def test_symlinked_evidence_is_not_read_as_committed_input(
    checker, tmp_path: Path
) -> None:
    target = tmp_path / "target.json"
    target.write_text('{"schema_version":"outside"}\n', encoding="utf-8")
    linked = tmp_path / "linked.json"
    linked.symlink_to(target)

    with pytest.raises(checker.EnforcementEvidenceError, match="regular JSON file"):
        checker._strict_load(linked)


def test_cli_report_option_uses_the_same_validator() -> None:
    valid = FIXTURE_ROOT / "valid/strong-ruleset.json"
    invalid = FIXTURE_ROOT / "invalid/last-push-disabled.json"

    accepted = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--root",
            str(ROOT),
            "--report",
            str(valid),
            "check",
        ],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    assert accepted.returncode == 0, accepted.stderr

    rejected = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--root",
            str(ROOT),
            "--report",
            str(invalid),
            "check",
        ],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    assert rejected.returncode != 0
    assert "last-push approval" in rejected.stderr


def test_bilingual_contract_docs_keep_the_same_candidate_boundary() -> None:
    english = CONTRACT_EN.read_text(encoding="utf-8")
    chinese = CONTRACT_ZH.read_text(encoding="utf-8")

    for document in (english, chinese):
        assert "authority=candidate" in document
        assert "trusted=false" in document
        assert "does not" in document or "不会" in document
        assert "make governance-enforcement-evidence-check" in document
        for fixture in (
            "missing-required-status.json",
            "last-push-disabled.json",
            "unconditional-bypass.json",
            "source-mismatch.json",
        ):
            assert fixture in document

    for phrase in (
        "does not fetch the API",
        "does not",
        "not trusted enforcement",
        "NOT_RUN",
        "architecture/contract owner",
        "independent mechanism reviewer",
    ):
        assert phrase in english
    for phrase in (
        "不请求 API",
        "不会",
        "不是 trusted enforcement",
        "NOT_RUN",
        "architecture/contract owner",
        "独立 mechanism reviewer",
    ):
        assert phrase in chinese
