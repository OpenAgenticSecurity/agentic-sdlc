from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys


REPO = Path(__file__).resolve().parents[1]
AGENT_CLAIM = REPO / "scripts" / "agent-claim.py"
EXAMPLE_CLAIM = REPO / "profiles" / "L1-team" / "issue-claim.example.md"


def _run_claim(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(AGENT_CLAIM), *args],
        cwd=REPO,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )


def _render_to(
    path: Path,
    *,
    issue: str = "org/service#42",
    task: str = "task-a",
    status: str = "running",
    repo: str = "service",
    owned_paths: list[str] | None = None,
) -> Path:
    paths = owned_paths or ["src/auth/guard.py"]
    cmd = [
        "render",
        "--issue",
        issue,
        "--task",
        task,
        "--status",
        status,
        "--identity",
        "Claude Code",
        "--actor",
        "alice",
        "--agent",
        "claude-code",
        "--session",
        "sess-1",
        "--repo",
        repo,
        "--branch",
        f"fix/{task}",
        "--worktree",
        f".claude/worktrees/{task}",
        "--lease-expires",
        "2026-11-20T18:00:00Z",
        "--updated",
        "2026-11-20T16:00:00Z",
        "--summary",
        "Working on scoped change.",
        "--next-action",
        "Run targeted tests.",
        "--output",
        str(path),
    ]
    for item in paths:
        cmd.extend(["--owned-path", item])
    proc = _run_claim(*cmd)
    assert proc.returncode == 0, proc.stderr
    return path


def test_validate_committed_profile_example() -> None:
    proc = _run_claim("validate", str(EXAMPLE_CLAIM), "--json")
    assert proc.returncode == 0, proc.stderr
    data = json.loads(proc.stdout)
    assert len(data) == 1
    assert data[0]["status"] == "running"
    assert data[0]["repo"] == "service"
    assert data[0]["owned_paths"] == ["src/auth/guard.py", "tests/test_auth_guard.py"]


def test_render_and_validate_round_trip(tmp_path: Path) -> None:
    claim_file = _render_to(tmp_path / "claim.md", owned_paths=["scripts/tool.py", "tests/test_tool.py"])
    text = claim_file.read_text(encoding="utf-8")
    assert text.startswith("<!-- agent-claim:org/service#42:task-a -->")

    proc = _run_claim("validate", str(claim_file))
    assert proc.returncode == 0, proc.stderr


def test_rejects_invalid_status_marker_and_unsafe_paths(tmp_path: Path) -> None:
    bad_status = tmp_path / "bad-status.md"
    bad_status.write_text(
        EXAMPLE_CLAIM.read_text(encoding="utf-8").replace("`running`", "`almost_done`"),
        encoding="utf-8",
    )
    assert _run_claim("validate", str(bad_status)).returncode == 1

    bad_marker = tmp_path / "bad-marker.md"
    bad_marker.write_text("### Agent Claim\n- Status: `running`\n", encoding="utf-8")
    assert _run_claim("validate", str(bad_marker)).returncode == 1

    bad_path = tmp_path / "bad-path.md"
    bad_path.write_text(
        EXAMPLE_CLAIM.read_text(encoding="utf-8").replace("`src/auth/guard.py`", "`../outside.py`"),
        encoding="utf-8",
    )
    proc = _run_claim("validate", str(bad_path))
    assert proc.returncode == 1
    assert ".." in proc.stderr

    abs_path = tmp_path / "abs-path.md"
    abs_path.write_text(
        EXAMPLE_CLAIM.read_text(encoding="utf-8").replace("`src/auth/guard.py`", "`/etc/passwd`"),
        encoding="utf-8",
    )
    assert _run_claim("validate", str(abs_path)).returncode == 1


def test_check_overlap_catches_identical_and_nested_paths(tmp_path: Path) -> None:
    c1 = _render_to(tmp_path / "c1.md", issue="org/service#10", task="task-1", owned_paths=["src/auth/"])
    c2 = _render_to(tmp_path / "c2.md", issue="org/service#11", task="task-2", owned_paths=["src/auth/guard.py"])

    nested = _run_claim("check-overlap", "--now", "2026-11-20T17:00:00Z", str(c1), str(c2), "--json")
    assert nested.returncode == 2
    overlaps = json.loads(nested.stdout)["overlaps"]
    assert len(overlaps) == 1
    assert overlaps[0]["path_a"] == "src/auth/"
    assert overlaps[0]["path_b"] == "src/auth/guard.py"

    c3 = _render_to(tmp_path / "c3.md", issue="org/service#12", task="task-3", owned_paths=["src/auth/guard.py"])
    exact = _run_claim("check-overlap", "--now", "2026-11-20T17:00:00Z", str(c2), str(c3))
    assert exact.returncode == 2


def test_check_overlap_normalizes_repo_name_case_and_respects_lease_expiry(tmp_path: Path) -> None:
    # Repo spelling variants ("service" vs "org/service") and path case variants must overlap.
    c1 = _render_to(tmp_path / "c1.md", issue="org/service#10", task="task-1", repo="service", owned_paths=["src/Auth/"])
    c2 = _render_to(tmp_path / "c2.md", issue="org/service#11", task="task-2", repo="org/service", owned_paths=["src/auth/guard.py"])
    hit = _run_claim("check-overlap", "--now", "2026-11-20T17:00:00Z", str(c1), str(c2))
    assert hit.returncode == 2, hit.stdout + hit.stderr

    # After lease_expires (2026-11-20T18:00:00Z), expired claim no longer blocks a fresh claim.
    fresh = _render_to(tmp_path / "fresh.md", issue="org/service#12", task="task-3", repo="service", owned_paths=["src/auth/guard.py"])
    # Give fresh a later lease so only c1 is expired at 19:00:00Z.
    fresh.write_text(
        fresh.read_text(encoding="utf-8").replace("2026-11-20T18:00:00Z", "2026-11-21T18:00:00Z"),
        encoding="utf-8",
    )
    after_expiry = _run_claim("check-overlap", "--now", "2026-11-20T19:00:00Z", str(c1), str(fresh))
    assert after_expiry.returncode == 0, after_expiry.stdout + after_expiry.stderr


def test_check_overlap_allows_disjoint_and_terminal_claims(tmp_path: Path) -> None:
    c1 = _render_to(tmp_path / "c1.md", issue="org/service#10", task="task-1", owned_paths=["src/auth/guard.py"])
    c2 = _render_to(tmp_path / "c2.md", issue="org/service#11", task="task-2", owned_paths=["src/billing/invoice.py"])
    c3 = _render_to(
        tmp_path / "c3.md",
        issue="org/service#12",
        task="task-3",
        status="completed",
        owned_paths=["src/auth/guard.py"],
    )
    c4 = _render_to(
        tmp_path / "c4.md",
        issue="org/service#13",
        task="task-4",
        status="released",
        owned_paths=["src/auth/"],
    )

    proc = _run_claim("check-overlap", "--now", "2026-11-20T17:00:00Z", str(c1), str(c2), str(c3), str(c4))
    assert proc.returncode == 0, proc.stderr


def _write_fake_gh(path: Path, body: str) -> Path:
    path.write_text(body, encoding="utf-8")
    path.chmod(0o755)
    return path


def test_publish_blocks_hijack_checks_overlap_handles_bad_json_and_timeout(tmp_path: Path) -> None:
    alice_claim = _render_to(tmp_path / "alice.md", issue="org/service#42", task="auth-20261121", owned_paths=["src/auth/"])
    bob_same_task = tmp_path / "bob.md"
    bob_same_task.write_text(
        alice_claim.read_text(encoding="utf-8")
        .replace("- GitHub actor: `alice`", "- GitHub actor: `bob`")
        .replace("- Session: `sess-1`", "- Session: `sess-2`")
        .replace("`src/auth/`", "`src/billing/`"),
        encoding="utf-8",
    )
    existing_comments = [
        [
            {
                "id": 9001,
                "user": {"login": "alice"},
                "body": alice_claim.read_text(encoding="utf-8"),
            },
            {
                "id": 9002,
                "user": {"login": "reviewer"},
                "body": "Quoting marker in prose should never be matched:\n"
                + "<!-- agent-claim:org/service#42:quoted-task -->\n",
            },
        ]
    ]
    comments_json = tmp_path / "comments.json"
    comments_json.write_text(json.dumps(existing_comments), encoding="utf-8")
    call_log = tmp_path / "gh-calls.log"
    fake_gh = _write_fake_gh(
        tmp_path / "fake-gh",
        f"""#!/bin/sh
echo "$@" >> {str(call_log)!r}
case "$*" in
  *--paginate*) cat {str(comments_json)!r} ;;
  *) echo '{{"id": 9001}}' ;;
esac
""",
    )

    # 1. Different actor/session on an active claim must be refused without --takeover.
    hijack = _run_claim(
        "publish",
        str(bob_same_task),
        "--gh-bin",
        str(fake_gh),
        "--now",
        "2026-11-20T17:00:00Z",
    )
    assert hijack.returncode == 1
    assert "takeover" in hijack.stderr.lower()
    assert "PATCH" not in call_log.read_text(encoding="utf-8")

    # 2. Explicit --takeover permits replacing the existing comment.
    takeover = _run_claim(
        "publish",
        str(bob_same_task),
        "--gh-bin",
        str(fake_gh),
        "--now",
        "2026-11-20T17:00:00Z",
        "--takeover",
    )
    assert takeover.returncode == 0, takeover.stderr
    assert "PATCH repos/org/service/issues/comments/9001" in call_log.read_text(encoding="utf-8")

    # 3. Same owner updating own active claim succeeds via PATCH.
    call_log.write_text("", encoding="utf-8")
    self_update = _run_claim(
        "publish",
        str(alice_claim),
        "--gh-bin",
        str(fake_gh),
        "--now",
        "2026-11-20T17:00:00Z",
    )
    assert self_update.returncode == 0, self_update.stderr
    assert "PATCH repos/org/service/issues/comments/9001" in call_log.read_text(encoding="utf-8")

    # 4. Publishing a different task whose Owned paths overlap an existing active claim fails with exit 2.
    call_log.write_text("", encoding="utf-8")
    overlap_claim = _render_to(
        tmp_path / "overlap.md",
        issue="org/service#42",
        task="other-task-20261121",
        owned_paths=["src/auth/guard.py"],
    )
    blocked = _run_claim(
        "publish",
        str(overlap_claim),
        "--gh-bin",
        str(fake_gh),
        "--now",
        "2026-11-20T17:00:00Z",
    )
    assert blocked.returncode == 2, blocked.stdout + blocked.stderr
    assert "OVERLAP" in blocked.stderr
    assert "POST" not in call_log.read_text(encoding="utf-8")

    # 5. Marker quoted inside prose must NOT be matched as an existing claim comment (must POST new comment).
    call_log.write_text("", encoding="utf-8")
    quoted_task = _render_to(
        tmp_path / "quoted.md",
        issue="org/service#42",
        task="quoted-task",
        owned_paths=["docs/guide.md"],
    )
    posted = _run_claim(
        "publish",
        str(quoted_task),
        "--gh-bin",
        str(fake_gh),
        "--now",
        "2026-11-20T17:00:00Z",
    )
    assert posted.returncode == 0, posted.stderr
    assert "POST repos/org/service/issues/42/comments" in call_log.read_text(encoding="utf-8")

    # 6. Malformed JSON from gh fails cleanly without raw Python traceback.
    bad_gh = _write_fake_gh(tmp_path / "bad-gh", "#!/bin/sh\necho '<html>rate limited</html>'\n")
    malformed = _run_claim("publish", str(alice_claim), "--gh-bin", str(bad_gh), "--now", "2026-11-20T17:00:00Z")
    assert malformed.returncode == 1
    assert "Traceback" not in malformed.stderr
    assert "invalid JSON" in malformed.stderr

    # 7. Slow gh times out cleanly with NOT_RUN.
    slow_gh = _write_fake_gh(tmp_path / "slow-gh", "#!/bin/sh\nsleep 5\n")
    timed_out = _run_claim(
        "publish",
        str(alice_claim),
        "--gh-bin",
        str(slow_gh),
        "--timeout",
        "1",
        "--now",
        "2026-11-20T17:00:00Z",
    )
    assert timed_out.returncode == 1
    assert "NOT_RUN" in timed_out.stderr and "timed out" in timed_out.stderr


def test_parse_claim_handles_leading_blank_lines_and_rejects_symlink_output(tmp_path: Path) -> None:
    padded = tmp_path / "padded.md"
    padded.write_text("\n\n" + EXAMPLE_CLAIM.read_text(encoding="utf-8"), encoding="utf-8")
    proc = _run_claim("validate", str(padded))
    assert proc.returncode == 0, proc.stderr

    outside = tmp_path / "outside.md"
    outside.write_text("keep\n", encoding="utf-8")
    out_link = tmp_path / "out-link.md"
    out_link.symlink_to(outside)
    res = _run_claim(
        "render",
        "--issue",
        "org/service#42",
        "--task",
        "task-sym",
        "--status",
        "running",
        "--identity",
        "Claude Code",
        "--actor",
        "alice",
        "--agent",
        "claude-code",
        "--session",
        "sess-1",
        "--repo",
        "service",
        "--branch",
        "fix/sym",
        "--worktree",
        ".worktrees/sym",
        "--lease-expires",
        "2026-11-20T18:00:00Z",
        "--owned-path",
        "src/app.py",
        "--output",
        str(out_link),
    )
    assert res.returncode == 1
    assert outside.read_text(encoding="utf-8") == "keep\n"


def test_publish_ignores_spoofed_comment_author_and_blocks_author_mismatch(tmp_path: Path) -> None:
    # Mallory posts a comment claiming `- GitHub actor: alice` on `src/auth/`
    forged_alice = _render_to(
        tmp_path / "forged.md",
        issue="org/service#42",
        task="spoof-task",
        owned_paths=["src/auth/"],
    )
    bob_legit = _render_to(
        tmp_path / "bob-legit.md",
        issue="org/service#42",
        task="bob-auth",
        owned_paths=["src/auth/guard.py"],
    )
    bob_legit.write_text(
        bob_legit.read_text(encoding="utf-8").replace("- GitHub actor: `alice`", "- GitHub actor: `bob`"),
        encoding="utf-8",
    )
    comments_json = tmp_path / "spoof-comments.json"
    comments_json.write_text(
        json.dumps(
            [
                [
                    {
                        "id": 7001,
                        "user": {"login": "mallory"},
                        "body": forged_alice.read_text(encoding="utf-8"),
                    }
                ]
            ]
        ),
        encoding="utf-8",
    )
    fake_gh = _write_fake_gh(
        tmp_path / "fake-gh-spoof",
        f"""#!/bin/sh
case "$*" in
  *--paginate*) cat {str(comments_json)!r} ;;
  *) echo '{{"id": 7002}}' ;;
esac
""",
    )

    # Spoofed comment (author mallory != declared actor alice) must NOT block bob's legitimate claim
    proc = _run_claim("publish", str(bob_legit), "--gh-bin", str(fake_gh), "--now", "2026-11-20T17:00:00Z")
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "spoofed" in proc.stderr.lower() or "mismatch" in proc.stderr.lower()

    # And even if a claim file matches the marker of comment #7001 (`alice`), refusing to PATCH a comment authored by `mallory` without --takeover
    refuse_patch = _run_claim("publish", str(forged_alice), "--gh-bin", str(fake_gh), "--now", "2026-11-20T17:00:00Z")
    assert refuse_patch.returncode == 1
