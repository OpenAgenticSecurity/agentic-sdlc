from __future__ import annotations

import importlib.util
from pathlib import Path
import socket
import subprocess
import sys
import threading


REPO = Path(__file__).resolve().parents[1]
WORKSPACE_GIT_PATH = REPO / "scripts" / "workspace-git.py"


def _load_workspace_git():
    spec = importlib.util.spec_from_file_location("workspace_git", WORKSPACE_GIT_PATH)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _git(path: Path, *args: str, input_text: str | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", "-C", str(path), *args],
        text=True,
        input=input_text,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )


def _init_repo_with_remote(ws: Path, name: str) -> tuple[Path, Path]:
    repo = ws / name
    remote = ws / f"{name}.git"
    repo.mkdir(parents=True)
    assert _git(repo, "init", "-b", "main").returncode == 0
    (repo / "tracked.txt").write_text("initial\n", encoding="utf-8")
    assert _git(repo, "add", "tracked.txt").returncode == 0
    assert _git(repo, "commit", "-m", "initial").returncode == 0
    assert _git(ws, "init", "--bare", "-b", "main", str(remote)).returncode == 0
    assert _git(repo, "remote", "add", "origin", str(remote)).returncode == 0
    assert _git(repo, "push", "-u", "origin", "main").returncode == 0
    assert _git(repo, "remote", "set-head", "origin", "main").returncode == 0
    return repo, remote


def test_managed_guardrails_block_primary_and_main_but_allow_topic_worktree(tmp_path: Path) -> None:
    workspace_git = _load_workspace_git()
    repo, _remote = _init_repo_with_remote(tmp_path, "repo")
    worktree = tmp_path / "task-worktree"

    changes = workspace_git.install_guardrails(repo)
    assert changes
    assert workspace_git.guardrails_ok(repo)

    (repo / "tracked.txt").write_text("primary edit\n", encoding="utf-8")
    assert _git(repo, "add", "tracked.txt").returncode == 0
    blocked_main = _git(repo, "commit", "-m", "must fail")
    assert blocked_main.returncode != 0
    assert "agentic-sdlc guardrail: commits on main are blocked" in blocked_main.stderr
    assert _git(repo, "restore", "--staged", "tracked.txt").returncode == 0
    assert _git(repo, "restore", "tracked.txt").returncode == 0

    assert _git(repo, "worktree", "add", "-b", "feat/task", str(worktree), "origin/main").returncode == 0
    (worktree / "tracked.txt").write_text("topic edit\n", encoding="utf-8")
    assert _git(worktree, "add", "tracked.txt").returncode == 0
    assert _git(worktree, "commit", "-m", "topic commit").returncode == 0
    assert _git(worktree, "push", "-u", "origin", "feat/task").returncode == 0

    blocked_push = _git(worktree, "push", "origin", "HEAD:main")
    assert blocked_push.returncode != 0
    assert "agentic-sdlc guardrail: direct push to main is blocked" in blocked_push.stderr


def test_managed_guardrails_chain_pre_commit_and_forward_other_hooks_and_remove_cleanly(tmp_path: Path) -> None:
    workspace_git = _load_workspace_git()
    repo, _remote = _init_repo_with_remote(tmp_path, "repo")
    hooks = repo / ".custom-hooks"
    hooks.mkdir()
    # Prior pre-commit, commit-msg, and post-checkout hooks must all keep running!
    prior_pre = hooks / "pre-commit"
    prior_pre.write_text("#!/bin/sh\necho prior-pre-commit >&2\nexit 0\n", encoding="utf-8")
    prior_pre.chmod(0o755)

    commit_msg = hooks / "commit-msg"
    commit_msg.write_text(
        '#!/bin/sh\ngrep -q "^feat:" "$1" || { echo "commit-msg-rejected" >&2; exit 1; }\n',
        encoding="utf-8",
    )
    commit_msg.chmod(0o755)

    checkout_marker = tmp_path / "post-checkout-ran.txt"
    post_checkout = hooks / "post-checkout"
    post_checkout.write_text(f"#!/bin/sh\necho ran >> {str(checkout_marker)!r}\n", encoding="utf-8")
    post_checkout.chmod(0o755)

    assert _git(repo, "config", "core.hooksPath", ".custom-hooks").returncode == 0

    assert workspace_git.main(["guardrails", "--root", str(tmp_path), "--repo", "repo", "--apply"]) == 0
    assert Path(
        _git(repo, "config", "--get", workspace_git.PREVIOUS_HOOKS_PATH_KEY).stdout.strip()
    ) == hooks.resolve()

    wt = tmp_path / "wt-hooks"
    assert _git(repo, "worktree", "add", "-b", "feat/hooks", str(wt), "origin/main").returncode == 0
    assert checkout_marker.is_file(), "post-checkout hook must still execute after guardrails are installed"

    (wt / "file.txt").write_text("content\n", encoding="utf-8")
    assert _git(wt, "add", "file.txt").returncode == 0
    bad_msg = _git(wt, "commit", "-m", "missing prefix")
    assert bad_msg.returncode != 0
    assert "commit-msg-rejected" in bad_msg.stderr

    good_msg = _git(wt, "commit", "-m", "feat: valid prefix")
    assert good_msg.returncode == 0, good_msg.stderr
    assert "prior-pre-commit" in good_msg.stderr

    # Removing guardrails restores the original core.hooksPath and cleans up managed hooks.
    assert workspace_git.main(["guardrails", "--root", str(tmp_path), "--repo", "repo", "--remove"]) == 0
    assert not workspace_git.guardrails_ok(repo)
    assert Path(_git(repo, "config", "--get", "core.hooksPath").stdout.strip()) == hooks.resolve()
    assert _git(repo, "config", "--get", workspace_git.PREVIOUS_HOOKS_PATH_KEY).returncode != 0
    managed_dir = workspace_git.managed_hooks_dir(repo)
    assert managed_dir is not None and not managed_dir.exists()


def test_guardrails_allow_unborn_first_commit_interactive_rebase_amend_and_optional_primary_topic(
    tmp_path: Path,
) -> None:
    workspace_git = _load_workspace_git()

    # 1. Empty repo (unborn HEAD) must allow the very first commit so worktrees become possible.
    fresh = tmp_path / "fresh"
    fresh.mkdir()
    assert _git(fresh, "init", "-b", "main").returncode == 0
    workspace_git.install_guardrails(fresh)
    (fresh / "init.txt").write_text("hello\n", encoding="utf-8")
    assert _git(fresh, "add", "init.txt").returncode == 0
    first = _git(fresh, "commit", "-m", "initial commit")
    assert first.returncode == 0, first.stderr
    # Subsequent commit directly on main is blocked now that HEAD exists.
    (fresh / "init.txt").write_text("second\n", encoding="utf-8")
    assert _git(fresh, "add", "init.txt").returncode == 0
    second = _git(fresh, "commit", "-m", "should block")
    assert second.returncode != 0
    assert "commits on main are blocked" in second.stderr

    # 2. Interactive rebase stopped for edit allows `git commit --amend` in a topic worktree.
    repo, _remote = _init_repo_with_remote(tmp_path, "rebase-repo")
    workspace_git.install_guardrails(repo)
    wt = tmp_path / "wt-rebase"
    assert _git(repo, "worktree", "add", "-b", "feat/rb", str(wt), "origin/main").returncode == 0
    (wt / "a.txt").write_text("1\n", encoding="utf-8")
    assert _git(wt, "add", "a.txt").returncode == 0
    assert _git(wt, "commit", "-m", "step 1").returncode == 0
    (wt / "b.txt").write_text("2\n", encoding="utf-8")
    assert _git(wt, "add", "b.txt").returncode == 0
    assert _git(wt, "commit", "-m", "step 2").returncode == 0

    seq_editor = tmp_path / "edit-first.sh"
    seq_editor.write_text("#!/bin/sh\nsed -i.bak '1s/^pick/edit/' \"$1\"\n", encoding="utf-8")
    seq_editor.chmod(0o755)
    rebase_start = subprocess.run(
        ["git", "-C", str(wt), "rebase", "-i", "HEAD~2"],
        env={
            "PATH": "/usr/bin:/bin:/usr/local/bin:/opt/homebrew/bin",
            "GIT_SEQUENCE_EDITOR": str(seq_editor),
            "GIT_EDITOR": "true",
            "GIT_AUTHOR_NAME": "Test Author",
            "GIT_AUTHOR_EMAIL": "author@example.invalid",
            "GIT_COMMITTER_NAME": "Test Committer",
            "GIT_COMMITTER_EMAIL": "committer@example.invalid",
        },
        text=True,
        capture_output=True,
        check=False,
    )
    assert rebase_start.returncode == 0, rebase_start.stderr
    (wt / "a.txt").write_text("1-amended\n", encoding="utf-8")
    assert _git(wt, "add", "a.txt").returncode == 0
    amend = _git(wt, "commit", "--amend", "--no-edit")
    assert amend.returncode == 0, amend.stderr
    assert _git(wt, "rebase", "--continue").returncode == 0

    # 3. --allow-primary-topic permits topic branches in the primary checkout while still blocking main.
    single, _r = _init_repo_with_remote(tmp_path, "single-clone")
    assert workspace_git.main(["guardrails", "--root", str(tmp_path), "--repo", "single-clone", "--apply", "--allow-primary-topic"]) == 0
    assert workspace_git.guardrails_ok(single)
    assert _git(single, "checkout", "-b", "feat/local").returncode == 0
    (single / "tracked.txt").write_text("topic in primary\n", encoding="utf-8")
    assert _git(single, "add", "tracked.txt").returncode == 0
    ok_topic = _git(single, "commit", "-m", "topic ok")
    assert ok_topic.returncode == 0, ok_topic.stderr


def test_guardrail_audit_detects_content_and_mode_drift(tmp_path: Path) -> None:
    workspace_git = _load_workspace_git()
    repo = tmp_path / "repo"
    repo.mkdir()
    assert _git(repo, "init", "-b", "main").returncode == 0
    workspace_git.install_guardrails(repo)
    hooks = workspace_git.managed_hooks_dir(repo)
    assert hooks is not None
    pre_push = hooks / "pre-push"
    pre_push.write_text(
        pre_push.read_text(encoding="utf-8") + "# drift\n",
        encoding="utf-8",
    )
    assert not workspace_git.guardrails_ok(repo)
    workspace_git.install_guardrails(repo)
    assert workspace_git.guardrails_ok(repo)

    pre_push.chmod(0o644)
    assert not workspace_git.guardrails_ok(repo)
    changes = workspace_git.install_guardrails(repo)
    assert "made pre-push executable" in changes
    assert workspace_git.guardrails_ok(repo)


def test_guardrails_without_root_scopes_only_to_current_repo_never_siblings(tmp_path: Path, monkeypatch) -> None:
    workspace_git = _load_workspace_git()
    svc_a, _ = _init_repo_with_remote(tmp_path, "svc-a")
    svc_b, _ = _init_repo_with_remote(tmp_path, "svc-b")
    monkeypatch.delenv("OPENAGENTIC_ROOT", raising=False)
    monkeypatch.chdir(svc_a)

    # Running without --root inside svc-a must ONLY affect svc-a, never sibling svc-b.
    rc = workspace_git.main(["guardrails", "--apply"])
    assert rc == 0
    assert workspace_git.guardrails_ok(svc_a)
    assert not workspace_git.guardrails_ok(svc_b)

    # Outside any Git repo and with no workspace manifest, refusing without --root fails closed.
    empty = tmp_path / "not-a-repo"
    empty.mkdir()
    monkeypatch.chdir(empty)
    rc_outside = workspace_git.main(["guardrails"])
    assert rc_outside == 2


def test_discover_repos_supports_generic_workspaces_and_manifest(tmp_path: Path) -> None:
    workspace_git = _load_workspace_git()

    generic = tmp_path / "generic-org"
    generic.mkdir()
    for name in ("alpha-service", "beta-lib"):
        repo = generic / name
        repo.mkdir()
        assert _git(repo, "init", "-b", "main").returncode == 0
    (generic / "plain-notes").mkdir()

    assert [p.name for p in workspace_git.discover_repos(generic)] == ["alpha-service", "beta-lib"]

    mixed = tmp_path / "mixed-org"
    mixed.mkdir()
    for name in ("xray-core", "agentic-sdlc", "mcp-guard"):
        repo = mixed / name
        repo.mkdir()
        assert _git(repo, "init", "-b", "main").returncode == 0

    assert [p.name for p in workspace_git.discover_repos(mixed)] == [
        "agentic-sdlc",
        "mcp-guard",
        "xray-core",
    ]

    (mixed / ".openagenticsecurity.yaml").write_text(
        "repos:\n  - mcp-guard\n  - agentic-sdlc\n",
        encoding="utf-8",
    )
    assert [p.name for p in workspace_git.discover_repos(mixed)] == [
        "agentic-sdlc",
        "mcp-guard",
    ]


def test_agent_start_clean_defaults_and_audit_end_to_end_and_fetch_timeout(tmp_path: Path) -> None:
    workspace_git = _load_workspace_git()
    ws = tmp_path / "ws"
    ws.mkdir()
    repo, remote = _init_repo_with_remote(ws, "service")

    # Happy path: audit, clean-defaults, and agent-start --create-worktree
    assert workspace_git.main(["audit", "--root", str(ws), "--tsv"]) == 0
    assert workspace_git.main(["clean-defaults", "--root", str(ws), "--fetch"]) == 0
    assert (
        workspace_git.main(
            [
                "agent-start",
                "--root",
                str(ws),
                "--repo",
                "service",
                "--task",
                "happy-path",
                "--branch",
                "feat/happy-path",
                "--fetch",
                "--create-worktree",
            ]
        )
        == 0
    )
    assert (repo / ".worktrees" / "happy-path").is_dir()

    # Clean-defaults fast-forwards a behind clean default checkout safely.
    other = tmp_path / "other-clone"
    assert _git(tmp_path, "clone", str(remote), str(other)).returncode == 0
    (other / "tracked.txt").write_text("from remote\n", encoding="utf-8")
    assert _git(other, "add", "tracked.txt").returncode == 0
    assert _git(other, "commit", "-m", "remote advance").returncode == 0
    assert _git(other, "push", "origin", "main").returncode == 0
    assert workspace_git.main(["clean-defaults", "--root", str(ws), "--fetch", "--apply"]) == 0
    assert (repo / "tracked.txt").read_text(encoding="utf-8") == "from remote\n"

    # Fetch error fails closed in both agent-start and clean-defaults.
    bad_repo = ws / "broken"
    bad_repo.mkdir()
    assert _git(bad_repo, "init", "-b", "main").returncode == 0
    (bad_repo / "README.md").write_text("hi\n", encoding="utf-8")
    assert _git(bad_repo, "add", "README.md").returncode == 0
    assert _git(bad_repo, "commit", "-m", "init").returncode == 0
    assert _git(bad_repo, "remote", "add", "origin", str(tmp_path / "missing-remote.git")).returncode == 0
    assert _git(bad_repo, "update-ref", "refs/remotes/origin/main", "HEAD").returncode == 0
    assert _git(bad_repo, "symbolic-ref", "refs/remotes/origin/HEAD", "refs/remotes/origin/main").returncode == 0

    rc_start = workspace_git.main(
        [
            "agent-start",
            "--root",
            str(ws),
            "--repo",
            "broken",
            "--task",
            "stale-test",
            "--branch",
            "fix/stale-test",
            "--fetch",
            "--create-worktree",
        ]
    )
    assert rc_start == 2
    assert not (bad_repo / ".worktrees" / "stale-test").exists()
    assert workspace_git.main(["clean-defaults", "--root", str(ws), "--fetch"]) == 1

    # Unresponsive remote times out cleanly instead of hanging forever.
    srv = socket.socket()
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.bind(("127.0.0.1", 0))
    port = srv.getsockname()[1]
    srv.listen(2)
    accepted: list[socket.socket] = []

    def _hold_conn() -> None:
        srv.settimeout(3.0)
        try:
            conn, _addr = srv.accept()
            accepted.append(conn)
        except OSError:
            pass

    t = threading.Thread(target=_hold_conn, daemon=True)
    t.start()
    try:
        hang_repo = tmp_path / "hang-ws" / "slow"
        hang_repo.mkdir(parents=True)
        assert _git(hang_repo, "init", "-b", "main").returncode == 0
        (hang_repo / "a").write_text("a\n", encoding="utf-8")
        assert _git(hang_repo, "add", "a").returncode == 0
        assert _git(hang_repo, "commit", "-m", "init").returncode == 0
        assert _git(hang_repo, "remote", "add", "origin", f"git://127.0.0.1:{port}/none.git").returncode == 0

        res = workspace_git.run_git(hang_repo, "fetch", "--prune", "origin", timeout=1)
        assert res.returncode == 124
        assert "timed out" in res.stderr
    finally:
        for conn in accepted:
            conn.close()
        srv.close()
        t.join(timeout=1.0)


def test_removed_internal_subcommands_are_absent() -> None:
    workspace_git = _load_workspace_git()
    assert not hasattr(workspace_git, "install_entrypoint_block")
    assert not hasattr(workspace_git, "cmd_entrypoints")
    assert not hasattr(workspace_git, "cmd_configure")
