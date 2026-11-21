from __future__ import annotations

import copy
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import sys

import pytest


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "check-affected-closure.py"
FIXTURE_ROOT = ROOT / "standards/testing-strategy/fixtures/affected-closure"


def _load_checker():
    spec = importlib.util.spec_from_file_location("affected_closure_checker", SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def checker():
    return _load_checker()


def _load(relative: str) -> dict[str, object]:
    return json.loads((FIXTURE_ROOT / relative).read_text(encoding="utf-8"))


def _catalog() -> dict[str, object]:
    value = _load("suite-catalog.json")
    entries = value["entries"]
    assert isinstance(entries, dict)
    return entries


def test_valid_reports_are_closed_and_semantically_valid(checker) -> None:
    schema = checker._schema(ROOT)
    for relative in (
        "valid/docs-only-shadow.json",
        "valid/shared-fast-path.json",
        "valid/git-error-shadow.json",
    ):
        checker.validate_report(_load(relative), schema=schema, suite_catalog=_catalog())


def test_invalid_fixture_proves_docs_only_cannot_expand_to_backend(checker) -> None:
    schema = checker._schema(ROOT)
    with pytest.raises(checker.AffectedClosureContractError):
        checker.validate_report(
            _load("invalid/docs-recommends-backend.json"),
            schema=schema,
            suite_catalog=_catalog(),
        )


@pytest.mark.parametrize(
    ("mutation", "message"),
    [
        (lambda report: report.update({"trusted": True}), "schema"),
        (lambda report: report.update({"shadow_only": False}), "schema"),
        (
            lambda report: report.update({"policy_mode": "pull_request_fast_path"}),
            "schema",
        ),
        (
            lambda report: report.update({"changes": [{"path": "../secret", "status": "M"}]}),
            "schema",
        ),
        (
            lambda report: report.update({"changes": [{"path": "docs/guides/testing.md", "status": "X"}]}),
            "schema",
        ),
        (
            lambda report: report.update({"base_sha": None, "head_sha": None}),
            "schema",
        ),
        (
            lambda report: report.update({"recommended_suites": ["full-suite"]}),
            "docs_only",
        ),
        (
            lambda report: report.update({"hostname": "builder-1"}),
            "schema",
        ),
    ],
)
def test_negative_mutations_never_become_green(checker, mutation, message: str) -> None:
    report = copy.deepcopy(_load("valid/docs-only-shadow.json"))
    mutation(report)
    with pytest.raises(checker.AffectedClosureContractError, match=message):
        checker.validate_report(report, schema=checker._schema(ROOT), suite_catalog=_catalog())


def test_empty_diff_is_explicitly_full_and_not_a_docs_only_shortcut(checker) -> None:
    report = copy.deepcopy(_load("valid/docs-only-shadow.json"))
    report["changes"] = []
    report["classification"] = "full"
    report["recommended_suites"] = ["full-suite"]
    report["reasons"] = ["full_boundary:empty_diff"]
    checker.validate_report(report, schema=checker._schema(ROOT), suite_catalog=_catalog())

    report["reasons"] = ["docs_local"]
    with pytest.raises(checker.AffectedClosureContractError, match="empty diff"):
        checker.validate_report(report, schema=checker._schema(ROOT), suite_catalog=_catalog())


def test_changes_must_be_ordered_by_path_and_status(checker) -> None:
    report = copy.deepcopy(_load("valid/shared-fast-path.json"))
    report["changes"] = list(reversed(report["changes"]))
    with pytest.raises(
        checker.AffectedClosureContractError,
        match="changes must be deterministically ordered",
    ):
        checker.validate_report(report, schema=checker._schema(ROOT), suite_catalog=_catalog())


def test_unknown_status_is_fail_closed(checker) -> None:
    report = copy.deepcopy(_load("valid/docs-only-shadow.json"))
    report["changes"] = [{"path": "docs/guides/testing.md", "status": "U"}]
    report["classification"] = "full"
    report["reasons"] = ["full_boundary:unknown_status"]
    report["recommended_suites"] = ["full-suite"]
    checker.validate_report(report, schema=checker._schema(ROOT), suite_catalog=_catalog())


def test_suite_catalog_is_an_explicit_product_entrypoint_boundary(checker) -> None:
    report = _load("valid/docs-only-shadow.json")
    with pytest.raises(checker.AffectedClosureContractError, match="catalogue"):
        checker.validate_report(
            report,
            schema=checker._schema(ROOT),
            suite_catalog={},
        )


@pytest.mark.parametrize(
    "catalog",
    [
        {},
        {"docs-check": ""},
        {"../docs-check": "product:docs-check"},
        {"docs-check": None},
    ],
)
def test_suite_catalog_cannot_be_empty_or_unresolvable(checker, catalog) -> None:
    with pytest.raises(checker.AffectedClosureContractError, match="catalogue"):
        checker._validate_suite_catalog(catalog)


def test_duplicate_json_key_is_rejected_by_strict_loader(checker, tmp_path: Path) -> None:
    duplicate = tmp_path / "duplicate.json"
    duplicate.write_text(
        '{"schema_version":"one","schema_version":"two"}\n',
        encoding="utf-8",
    )
    with pytest.raises(checker.AffectedClosureContractError, match="duplicate JSON key"):
        checker._strict_load(duplicate)


def test_cli_accepts_syntax_negative_fixture_and_does_not_normalize_duplicates(
    checker, tmp_path: Path
) -> None:
    # Copy only the contract tree and checker dependencies needed by the real
    # CLI.  This proves the committed invalid fixture is exercised through the
    # command-line wiring without mutating the checkout.
    shutil.copytree(ROOT / "standards", tmp_path / "standards")
    shutil.copy2(SCRIPT, tmp_path / "scripts-check.py")
    completed = subprocess.run(
        [sys.executable, str(tmp_path / "scripts-check.py"), "--root", str(tmp_path), "check"],
        cwd=tmp_path,
        check=False,
        capture_output=True,
        text=True,
    )
    assert completed.returncode == 0, completed.stderr


def test_invalid_fixture_cannot_pass_for_the_wrong_reason(
    checker, tmp_path: Path
) -> None:
    shutil.copytree(ROOT / "standards", tmp_path / "standards")
    invalid = (
        tmp_path
        / "standards/testing-strategy/fixtures/affected-closure/invalid/docs-recommends-backend.json"
    )
    invalid.write_text('{"schema_version":"truncated"}\n', encoding="utf-8")
    with pytest.raises(
        checker.AffectedClosureContractError,
        match="failed for the wrong reason",
    ):
        checker.check_fixtures(tmp_path)


def test_cli_checks_real_committed_fixture_set() -> None:
    completed = subprocess.run(
        [sys.executable, str(SCRIPT), "--root", str(ROOT), "check"],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    assert completed.returncode == 0, completed.stderr
    assert "contract fixtures passed" in completed.stdout


def test_report_is_stable_and_has_no_machine_identity_fields() -> None:
    report = _load("valid/docs-only-shadow.json")
    encoded = json.dumps(report, sort_keys=True, separators=(",", ":"))
    assert "timestamp" not in encoded
    assert "hostname" not in encoded
    assert "username" not in encoded
    assert str(ROOT) not in encoded


def test_cli_validates_adopter_report_and_custom_catalog(tmp_path: Path) -> None:
    valid_report = FIXTURE_ROOT / "valid/shared-fast-path.json"
    invalid_report = FIXTURE_ROOT / "invalid/docs-recommends-backend.json"
    catalog = FIXTURE_ROOT / "suite-catalog.json"

    ok = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--root",
            str(ROOT),
            "--report",
            str(valid_report),
            "--catalog",
            str(catalog),
            "check",
        ],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    assert ok.returncode == 0, ok.stderr
    assert "passed" in ok.stdout

    bad = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--root",
            str(ROOT),
            "--report",
            str(invalid_report),
            "check",
        ],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    assert bad.returncode != 0
    assert "docs_only cannot recommend" in bad.stderr
