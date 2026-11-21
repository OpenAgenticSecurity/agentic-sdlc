"""Runnable starter contract gates for backend performance & security invariants.

Graduates high-frequency checklist items from:
  - checklists/backend-performance-review.md
  - checklists/secure-vibe-coding-review.md

Run directly:
    pytest -q examples/backend-contract-gates.py

Replace the sample config dicts and helpers with imports from your real service.
"""

from __future__ import annotations

from dataclasses import dataclass
from itertools import pairwise
from pathlib import Path
import pytest


@dataclass(frozen=True)
class ProcessPoolBudget:
    name: str
    processes: int
    pool_size: int
    max_overflow: int

    @property
    def max_connections(self) -> int:
        return self.processes * (self.pool_size + self.max_overflow)


def assert_connection_pool_ledger(
    budgets: list[ProcessPoolBudget],
    *,
    rollout_factor: float,
    db_max_connections: int,
    safety_ratio: float = 0.7,
) -> None:
    """Enforce sum(processes * (pool_size + max_overflow)) * rollout <= 0.7 * max_conn."""
    total_peak = sum(item.max_connections for item in budgets) * rollout_factor
    ceiling = db_max_connections * safety_ratio
    if total_peak > ceiling:
        raise AssertionError(
            f"DB pool ledger overflow: peak={total_peak:.1f} > allowed={ceiling:.1f} "
            f"(db_max_connections={db_max_connections}, rollout_factor={rollout_factor})"
        )


def assert_timeout_chain_monotonic(chain: dict[str, int]) -> None:
    """Enforce queue_visibility > stale_cleanup > task_hard > task_soft > sub_agent > tool > llm."""
    order = (
        "queue_visibility_timeout",
        "stale_cleanup_threshold",
        "task_hard_limit",
        "task_soft_limit",
        "sub_agent_budget",
        "tool_or_sse_timeout",
        "llm_client_timeout",
    )
    for outer, inner in pairwise(order):
        if chain[outer] <= chain[inner]:
            raise AssertionError(
                f"Timeout chain inverted: {outer}={chain[outer]}s must be strictly greater than "
                f"{inner}={chain[inner]}s"
            )


def resolve_confined_path(base_dir: Path, untrusted_rel: str) -> Path:
    """Fail-closed canonical path containment rejecting `..`, absolute paths, and symlink escapes."""
    if not untrusted_rel or untrusted_rel.startswith(("/", "\\")) or "\x00" in untrusted_rel:
        raise ValueError("unsafe path input")
    root = base_dir.resolve()
    candidate = (root / untrusted_rel).resolve()
    try:
        candidate.relative_to(root)
    except ValueError as exc:
        raise ValueError(f"path escapes root: {untrusted_rel!r}") from exc
    return candidate


def test_connection_pool_ledger_accepts_safe_config_and_rejects_overflow() -> None:
    budgets = [
        ProcessPoolBudget("api-workers", processes=4, pool_size=5, max_overflow=5),
        ProcessPoolBudget("bg-workers", processes=2, pool_size=5, max_overflow=5),
    ]
    # 60 connections * 1.5 rolling deploy = 90 <= 0.7 * 200 (140)
    assert_connection_pool_ledger(budgets, rollout_factor=1.5, db_max_connections=200)

    # Negative mutation: raising worker count without raising DB ceiling must fail red.
    overloaded = [*budgets, ProcessPoolBudget("extra-workers", processes=6, pool_size=10, max_overflow=5)]
    with pytest.raises(AssertionError, match="DB pool ledger overflow"):
        assert_connection_pool_ledger(overloaded, rollout_factor=1.5, db_max_connections=200)


def test_timeout_chain_monotonicity_rejects_inverted_limits() -> None:
    valid_chain = {
        "queue_visibility_timeout": 3600,
        "stale_cleanup_threshold": 2400,
        "task_hard_limit": 1800,
        "task_soft_limit": 1500,
        "sub_agent_budget": 600,
        "tool_or_sse_timeout": 120,
        "llm_client_timeout": 60,
    }
    assert_timeout_chain_monotonic(valid_chain)

    # Negative mutation: soft limit exceeding hard limit silently breaks graceful cleanup.
    broken_chain = {**valid_chain, "task_soft_limit": 1900}
    with pytest.raises(AssertionError, match="Timeout chain inverted"):
        assert_timeout_chain_monotonic(broken_chain)


def test_query_budget_ceiling_catches_n_plus_one() -> None:
    max_queries_for_list_endpoint = 4
    executed_sql: list[str] = []

    def simulate_batched_list(item_count: int) -> None:
        executed_sql.append("SELECT * FROM items WHERE tenant_id = :tid LIMIT 20")
        if item_count > 0:
            executed_sql.append("SELECT * FROM owners WHERE tenant_id = :tid AND id IN (:ids)")

    simulate_batched_list(20)
    assert len(executed_sql) <= max_queries_for_list_endpoint

    # Negative mutation: N+1 per-row query blows past the ceiling.
    n_plus_one_sql = ["SELECT * FROM items LIMIT 20"] + [
        "SELECT * FROM owners WHERE id = :id" for _ in range(20)
    ]
    assert len(n_plus_one_sql) > max_queries_for_list_endpoint


def test_confined_path_rejects_traversal_and_escaping_symlinks(tmp_path: Path) -> None:
    sandbox = tmp_path / "sandbox"
    sandbox.mkdir()
    safe_file = sandbox / "report.json"
    safe_file.write_text("{}", encoding="utf-8")
    assert resolve_confined_path(sandbox, "report.json") == safe_file.resolve()

    # Negative security tests: parent traversal, absolute path, and symlink escape must fail closed.
    for bad in ("../etc/passwd", "/etc/passwd", "sub/../../outside.txt"):
        with pytest.raises(ValueError):
            resolve_confined_path(sandbox, bad)

    outside = tmp_path / "secret.txt"
    outside.write_text("do-not-read", encoding="utf-8")
    escape_link = sandbox / "link.txt"
    escape_link.symlink_to(outside)
    with pytest.raises(ValueError, match="path escapes root"):
        resolve_confined_path(sandbox, "link.txt")
