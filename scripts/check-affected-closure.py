#!/usr/bin/env python3
"""Validate the platform affected-test-closure candidate report contract.

This checker validates report shape and fail-closed semantics only.  It does
not collect a Git diff, run a product test command, choose a CI job, or grant
merge/release authority.  Product repositories own their exact-revision
classifier and suite catalogue; this package gives them one stable wire and
negative-test contract to conform to.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import sys
from typing import Mapping, Sequence

from jsonschema import Draft202012Validator, FormatChecker
from jsonschema.exceptions import SchemaError, ValidationError


SCHEMA_RELATIVE = Path(
    "standards/testing-strategy/schema/affected-closure-report.v1.schema.json"
)
FIXTURE_ROOT = Path("standards/testing-strategy/fixtures/affected-closure")
SHA_RE = re.compile(r"^[0-9a-f]{40}$")
PATH_RE = re.compile(
    r"^(?!/)(?![A-Za-z]:/)(?!.*(?:^|/)\.{1,2}(?:/|$))"
    r"(?!.*\\)(?!.*//)(?!.*[\x00-\x1f\x7f])"
    r"[A-Za-z0-9_.@+:-]+(?:/[A-Za-z0-9_.@+:-]+)*$"
)
CLASSIFICATIONS = frozenset(
    {"docs_only", "frontend_only", "backend_only", "shared_boundary", "full"}
)
STATUSES = frozenset({"A", "D", "M", "T", "U", "B"})
SUITE_ID_RE = re.compile(r"^[a-z0-9][a-z0-9._:-]{1,127}$")
INVALID_FIXTURE_EXPECTATIONS = {
    "docs-recommends-backend.json": "docs_only cannot recommend",
    "duplicate-key.json": "duplicate JSON key",
}


class AffectedClosureContractError(ValueError):
    """A bounded, human-readable contract failure."""


def _strict_load(path: Path) -> object:
    def reject_duplicates(pairs: list[tuple[str, object]]) -> dict[str, object]:
        value: dict[str, object] = {}
        for key, item in pairs:
            if key in value:
                raise AffectedClosureContractError(
                    f"{path}: duplicate JSON key {key!r}"
                )
            value[key] = item
        return value

    try:
        return json.loads(
            path.read_text(encoding="utf-8"), object_pairs_hook=reject_duplicates
        )
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise AffectedClosureContractError(f"{path}: invalid JSON") from exc


def _schema(root: Path) -> Mapping[str, object]:
    value = _strict_load(root / SCHEMA_RELATIVE)
    if not isinstance(value, Mapping):
        raise AffectedClosureContractError("affected-closure schema root is not an object")
    try:
        Draft202012Validator.check_schema(value)
    except SchemaError as exc:
        raise AffectedClosureContractError("affected-closure schema is invalid") from exc
    return value


def _schema_errors(value: Mapping[str, object], schema: Mapping[str, object]) -> list[str]:
    validator = Draft202012Validator(schema, format_checker=FormatChecker())
    return [
        error.message
        for error in sorted(
            validator.iter_errors(value), key=lambda item: list(item.absolute_path)
        )
    ]


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise AffectedClosureContractError(message)


def _as_list(value: object, field: str) -> list[object]:
    _require(isinstance(value, list), f"{field} must be an array")
    return value


def _validate_suite_catalog(suite_catalog: Mapping[str, object]) -> None:
    """Validate the deliberately small platform-side suite catalogue shape.

    The catalogue maps opaque, stable suite IDs to product-owned entrypoint
    descriptors.  It does not interpret or execute those descriptors, but an
    empty or malformed catalogue would make membership validation vacuous and
    could turn a report into unresolvable advice.
    """

    _require(bool(suite_catalog), "suite catalogue must contain at least one entry")
    for suite_id, entrypoint in suite_catalog.items():
        _require(
            isinstance(suite_id, str) and SUITE_ID_RE.fullmatch(suite_id) is not None,
            f"suite catalogue ID is unsafe: {suite_id!r}",
        )
        _require(
            isinstance(entrypoint, str) and entrypoint.strip(),
            f"suite catalogue entrypoint is empty: {suite_id!r}",
        )


def _validate_semantics(
    value: Mapping[str, object],
    *,
    suite_catalog: Mapping[str, object] | None = None,
) -> None:
    # The schema is checked by validate_report; keeping semantic validation
    # independent makes mutation tests identify which boundary rejected input.
    if suite_catalog is not None:
        _validate_suite_catalog(suite_catalog)
    _require(value.get("authority") == "candidate", "authority must remain candidate")
    _require(value.get("trusted") is False, "candidate report cannot be trusted")
    policy_mode = value.get("policy_mode")
    shadow_only = value.get("shadow_only")
    _require(
        (policy_mode == "shadow" and shadow_only is True)
        or (policy_mode == "pull_request_fast_path" and shadow_only is False),
        "shadow_only must match policy_mode",
    )

    changes = _as_list(value.get("changes"), "changes")
    reasons = _as_list(value.get("reasons"), "reasons")
    suites = _as_list(value.get("recommended_suites"), "recommended_suites")
    _require(reasons == sorted(reasons), "reasons must be deterministically ordered")
    change_keys: list[tuple[str, str]] = []
    for item in changes:
        _require(isinstance(item, Mapping), "each change must be an object")
        path = item.get("path")
        status = item.get("status")
        _require(isinstance(path, str) and PATH_RE.fullmatch(path) is not None, "change path is unsafe")
        _require(isinstance(status, str) and status in STATUSES, "change status is unknown")
        change_keys.append((path, status))
    _require(change_keys == sorted(change_keys), "changes must be deterministically ordered")

    error_code = value.get("error_code")
    classification = value.get("classification")
    _require(classification in CLASSIFICATIONS, "classification is unknown")
    if error_code is not None:
        _require(isinstance(error_code, str) and error_code, "error_code must be non-empty")
        _require(value.get("base_sha") is None, "error report cannot claim a base SHA")
        _require(value.get("head_sha") is None, "error report cannot claim a head SHA")
        _require(not changes, "error report cannot claim changed paths")
        _require(classification == "full", "error report must fail closed to full")
        _require("full_boundary:git_error" in reasons, "error report must expose git_error")
    else:
        _require(isinstance(value.get("base_sha"), str) and SHA_RE.fullmatch(value["base_sha"]) is not None, "base_sha must be a full SHA")
        _require(isinstance(value.get("head_sha"), str) and SHA_RE.fullmatch(value["head_sha"]) is not None, "head_sha must be a full SHA")
        if not changes:
            _require(classification == "full", "empty diff must fail closed")
            _require("full_boundary:empty_diff" in reasons, "empty diff reason is required")
        if any(item[1] in {"U", "B"} for item in change_keys):
            _require(classification == "full", "unknown or unmerged status must fail closed")
            _require("full_boundary:unknown_status" in reasons, "unknown status reason is required")

    if classification == "docs_only":
        forbidden = ("backend", "frontend", "integration", "browser", "e2e", "full", "agent")
        _require(
            all(
                isinstance(suite, str)
                and not any(token in suite.casefold() for token in forbidden)
                for suite in suites
            ),
            "docs_only cannot recommend execution suites",
        )

    if suite_catalog is not None:
        for suite in suites:
            _require(isinstance(suite, str) and suite in suite_catalog, f"suite is not in catalogue: {suite}")


def validate_report(
    value: object,
    *,
    schema: Mapping[str, object],
    suite_catalog: Mapping[str, object] | None = None,
) -> None:
    """Validate one report against the closed schema and semantic rules."""

    _require(isinstance(value, Mapping), "report root must be an object")
    errors = _schema_errors(value, schema)
    if errors:
        raise AffectedClosureContractError("schema: " + "; ".join(errors))
    _validate_semantics(value, suite_catalog=suite_catalog)


def _load_catalog(root: Path, catalog_path: Path | None = None) -> Mapping[str, object]:
    resolved = catalog_path if catalog_path is not None else (root / FIXTURE_ROOT / "suite-catalog.json")
    value = _strict_load(resolved)
    _require(isinstance(value, Mapping), "suite catalogue root must be an object")
    _require(
        value.get("schema_version") == "openagenticsecurity.testing.affected-suite-catalog.v1",
        "suite catalogue schema_version is unsupported",
    )
    _require(
        set(value) == {"schema_version", "entries"},
        "suite catalogue has unknown fields",
    )
    entries = value.get("entries")
    _require(isinstance(entries, Mapping), "suite catalogue entries must be an object")
    _validate_suite_catalog(entries)
    return entries


def check_fixtures(root: Path) -> None:
    schema = _schema(root)
    catalog = _load_catalog(root)
    valid_root = root / FIXTURE_ROOT / "valid"
    invalid_root = root / FIXTURE_ROOT / "invalid"
    valid_paths = sorted(valid_root.glob("*.json"))
    invalid_paths = sorted(invalid_root.glob("*.json"))
    _require(valid_paths, "no valid affected-closure fixtures found")
    _require(invalid_paths, "no invalid affected-closure fixtures found")
    invalid_names = {path.name for path in invalid_paths}
    _require(
        invalid_names == set(INVALID_FIXTURE_EXPECTATIONS),
        "invalid fixture expectation set drifted",
    )
    for path in valid_paths:
        value = _strict_load(path)
        validate_report(value, schema=schema, suite_catalog=catalog)
    for path in invalid_paths:
        try:
            value = _strict_load(path)
            validate_report(value, schema=schema, suite_catalog=catalog)
        except AffectedClosureContractError as exc:
            expected = INVALID_FIXTURE_EXPECTATIONS[path.name]
            _require(
                expected in str(exc),
                f"invalid fixture failed for the wrong reason: {path.name}",
            )
            continue
        raise AffectedClosureContractError(f"invalid fixture was accepted: {path}")


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument(
        "--report",
        type=Path,
        help="validate one affected-closure report instead of the committed fixtures",
    )
    parser.add_argument(
        "--catalog",
        type=Path,
        help="optional suite catalogue JSON path used with --report (default: repo fixture catalogue)",
    )
    parser.add_argument("command", choices=("check",))
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    root = args.root.resolve()
    try:
        if args.report is None:
            check_fixtures(root)
        else:
            schema = _schema(root)
            catalog_path = args.catalog
            if catalog_path is not None and not catalog_path.is_absolute():
                catalog_path = root / catalog_path
            catalog = _load_catalog(root, catalog_path)
            report_path = args.report
            if not report_path.is_absolute():
                report_path = root / report_path
            validate_report(_strict_load(report_path), schema=schema, suite_catalog=catalog)
    except (AffectedClosureContractError, OSError, ValidationError) as exc:
        print(f"affected-closure contract check failed: {exc}", file=sys.stderr)
        return 1
    if args.report is None:
        print("affected-test-closure contract fixtures passed")
    else:
        print("affected-test-closure report passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
