#!/usr/bin/env python3
"""Multi-repository workspace Git governance utilities.

Local-first guardrails and preflight helpers for coding-agent Git workflows:
- guardrails audits, installs, or removes managed pre-commit/pre-push hooks
  while forwarding all other Git client hooks to the original hooks directory;
- agent-start fails closed on fetch errors and creates clean latest worktrees
  from `origin/<default>` without touching dirty/occupied primary checkouts;
- audit reports multi-repo Git, worktree, and guardrail health read-only;
- clean-defaults dry-runs or applies safe fast-forwards on clean default
  checkouts while skipping occupied, dirty, ahead, or non-default checkouts.
"""

from __future__ import annotations

import argparse
from collections.abc import Iterable
import dataclasses
import os
from pathlib import Path
import re
import shutil
import stat
import subprocess
import sys


WORKSPACE_CONFIG_FILE = ".openagenticsecurity.yaml"
WORKTREE_PATTERNS = (
    ".worktrees/",
    "worktrees/",
    ".claude/worktrees/",
    ".cursor/worktrees/",
    ".codex/worktrees/",
)
GUARDRAIL_DIR = "agentic-sdlc-managed-hooks"
GUARDRAIL_MARKER_PREFIX = "AGENTIC-SDLC-MANAGED-GIT-GUARDRAIL:"
GUARDRAIL_MARKER = f"{GUARDRAIL_MARKER_PREFIX}v2"
PREVIOUS_HOOKS_PATH_KEY = "agentic-sdlc.guardrails.previousHooksPath"
ALLOW_PRIMARY_TOPIC_KEY = "agentic-sdlc.guardrails.allowPrimaryTopic"
NETWORK_GIT_SUBCOMMANDS = frozenset({"fetch", "push", "pull", "ls-remote", "clone"})
DEFAULT_LOCAL_GIT_TIMEOUT = 30
DEFAULT_NETWORK_GIT_TIMEOUT = 60

# Standard client-side Git hooks forwarded to the preserved hooks directory so
# commit-msg linters, git-lfs (post-checkout/post-merge), and user hooks keep
# running transparently after core.hooksPath is switched to GUARDRAIL_DIR.
FORWARDED_CLIENT_HOOKS = (
    "applypatch-msg",
    "pre-applypatch",
    "post-applypatch",
    "prepare-commit-msg",
    "commit-msg",
    "post-commit",
    "pre-rebase",
    "post-checkout",
    "post-merge",
    "pre-merge-commit",
    "post-rewrite",
    "reference-transaction",
)


def _render_pre_commit_hook(*, allow_primary_topic: bool = False) -> str:
    primary_block = (
        ""
        if allow_primary_topic
        else """if [ "$top" = "$primary" ]; then
  echo "agentic-sdlc guardrail: commits from the primary checkout are blocked. Use a task worktree." >&2
  exit 1
fi
"""
    )
    return f'''#!/bin/sh
# {GUARDRAIL_MARKER}
set -eu

top=$(git rev-parse --show-toplevel)
git_dir=$(git rev-parse --git-dir)
branch=$(git symbolic-ref --quiet --short HEAD || true)
default_ref=$(git symbolic-ref --quiet --short refs/remotes/origin/HEAD || true)
default_branch=${{default_ref#origin/}}
[ -n "$default_branch" ] || default_branch=main
primary=$(git worktree list --porcelain | sed -n 's/^worktree //p' | sed -n '1p')

# Allow the very first commit in an empty repository (unborn HEAD), because Git
# cannot create a task worktree until at least one commit exists.
if git rev-parse --verify --quiet HEAD >/dev/null 2>&1; then
  in_rebase=0
  if [ -d "$git_dir/rebase-merge" ] || [ -d "$git_dir/rebase-apply" ]; then
    in_rebase=1
  fi

  if [ -z "$branch" ] && [ "$in_rebase" -eq 0 ]; then
    echo "agentic-sdlc guardrail: commits on detached HEAD are blocked. Use a topic branch in a task worktree." >&2
    exit 1
  fi
  if [ "$branch" = "$default_branch" ]; then
    echo "agentic-sdlc guardrail: commits on $default_branch are blocked. Use a topic branch in a task worktree." >&2
    exit 1
  fi
  {primary_block.rstrip()}
fi

previous=$(git config --get {PREVIOUS_HOOKS_PATH_KEY} || true)
if [ -n "$previous" ]; then
  case "$previous" in
    /*) previous_hook="$previous/pre-commit" ;;
    *) previous_hook="$top/$previous/pre-commit" ;;
  esac
  if [ -x "$previous_hook" ]; then
    exec "$previous_hook" "$@"
  fi
fi
exit 0
'''


PRE_PUSH_HOOK = f'''#!/bin/sh
# {GUARDRAIL_MARKER}
set -eu

remote_name=${{1:-origin}}
top=$(git rev-parse --show-toplevel)
default_ref=$(git symbolic-ref --quiet --short "refs/remotes/$remote_name/HEAD" || true)
default_branch=${{default_ref#${{remote_name}}/}}
[ -n "$default_branch" ] || default_branch=main
input=$(mktemp "${{TMPDIR:-/tmp}}/agentic-sdlc-pre-push.XXXXXX")
trap 'rm -f "$input"' EXIT HUP INT TERM
cat > "$input"

while read -r local_ref local_sha remote_ref remote_sha; do
  if [ "${{remote_ref:-}}" = "refs/heads/$default_branch" ]; then
    echo "agentic-sdlc guardrail: direct push to $default_branch is blocked. Push a topic branch and merge by PR." >&2
    exit 1
  fi
done < "$input"

previous=$(git config --get {PREVIOUS_HOOKS_PATH_KEY} || true)
if [ -n "$previous" ]; then
  case "$previous" in
    /*) previous_hook="$previous/pre-push" ;;
    *) previous_hook="$top/$previous/pre-push" ;;
  esac
  if [ -x "$previous_hook" ]; then
    "$previous_hook" "$@" < "$input"
  fi
fi
exit 0
'''


def _render_forward_hook(hook_name: str) -> str:
    return f'''#!/bin/sh
# {GUARDRAIL_MARKER}
set -eu

top=$(git rev-parse --show-toplevel)
previous=$(git config --get {PREVIOUS_HOOKS_PATH_KEY} || true)
if [ -n "$previous" ]; then
  case "$previous" in
    /*) previous_hook="$previous/{hook_name}" ;;
    *) previous_hook="$top/$previous/{hook_name}" ;;
  esac
  if [ -x "$previous_hook" ]; then
    exec "$previous_hook" "$@"
  fi
fi
exit 0
'''


@dataclasses.dataclass
class RepoState:
    name: str
    path: Path
    is_git: bool
    branch: str = "not-git"
    upstream: str = "none"
    ahead: str = "NA"
    behind: str = "NA"
    default_branch: str = "NA"
    default_ref: str = "NA"
    default_ahead: str = "NA"
    default_behind: str = "NA"
    dirty: int = 0
    tracked_dirty: int = 0
    untracked: int = 0
    pull_ff: str = "unset"
    pull_rebase: str = "unset"
    default_rebase: str = "unset"
    has_worktree_ignore: bool = False
    worktree_count: int = 0
    guardrails_ok: bool = False
    fetch_error: str = ""

    @property
    def config_ok(self) -> bool:
        return (
            self.pull_ff == "only"
            and self.pull_rebase == "true"
            and self.default_rebase == "false"
        )

    def high_risks(self) -> list[str]:
        risks: list[str] = []
        if not self.is_git:
            return risks
        if self.branch == "DETACHED":
            risks.append("detached HEAD")
        if (
            self.branch == self.default_branch
            and _to_int(self.default_behind) > 0
            and self.dirty > 0
        ):
            risks.append(f"dirty default behind {self.default_behind}")
        if self.branch == self.default_branch and _to_int(self.default_ahead) > 0:
            risks.append(f"default ahead {self.default_ahead}")
        return risks

    def warnings(self) -> list[str]:
        warnings: list[str] = []
        if not self.is_git:
            warnings.append("not a Git repository")
            return warnings
        if self.fetch_error:
            warnings.append(f"fetch failed: {self.fetch_error}")
        if self.dirty > 0:
            warnings.append(
                f"dirty {self.dirty} ({self.tracked_dirty} tracked, {self.untracked} untracked)"
            )
        if not self.guardrails_ok:
            warnings.append("missing or drifted managed main guardrails")
        if _to_int(self.default_behind) > 0:
            warnings.append(f"behind default {self.default_behind}")
        if not self.config_ok:
            warnings.append(
                "git config drift "
                f"(pull.ff={self.pull_ff}, pull.rebase={self.pull_rebase}, "
                f"branch.{self.default_branch}.rebase={self.default_rebase})"
            )
        if not self.has_worktree_ignore:
            warnings.append("missing worktree ignore")
        return warnings


def _to_int(value: str) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def _git_timeout_for(args: tuple[str, ...], override: int | None = None) -> int:
    if override is not None:
        return max(1, override)
    env_timeout = os.environ.get("OPENAGENTIC_GIT_TIMEOUT", "").strip()
    if env_timeout.isdigit() and int(env_timeout) >= 1:
        return int(env_timeout)
    subcmd = next((arg for arg in args if not arg.startswith("-")), "")
    if subcmd in NETWORK_GIT_SUBCOMMANDS:
        return DEFAULT_NETWORK_GIT_TIMEOUT
    return DEFAULT_LOCAL_GIT_TIMEOUT


def run_git(repo: Path, *args: str, timeout: int | None = None) -> subprocess.CompletedProcess[str]:
    effective_timeout = _git_timeout_for(args, timeout)
    cmd = ["git", "-C", str(repo), *args]
    env = {
        **os.environ,
        "GIT_TERMINAL_PROMPT": "0",
        "GCM_INTERACTIVE": "never",
    }
    try:
        return subprocess.run(
            cmd,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            env=env,
            timeout=effective_timeout,
            check=False,
        )
    except subprocess.TimeoutExpired:
        subcmd = next((arg for arg in args if not arg.startswith("-")), "git")
        return subprocess.CompletedProcess(
            cmd,
            124,
            stdout="",
            stderr=f"git {subcmd} timed out after {effective_timeout}s",
        )


def git_stdout(repo: Path, *args: str, timeout: int | None = None) -> str:
    result = run_git(repo, *args, timeout=timeout)
    if result.returncode != 0:
        return ""
    return result.stdout.strip()


def _load_workspace_config(root: Path) -> dict[str, object] | None:
    cfg_path = root / WORKSPACE_CONFIG_FILE
    if not cfg_path.is_file() or cfg_path.is_symlink():
        return None
    try:
        import yaml  # type: ignore[import-untyped]
        loaded = yaml.safe_load(cfg_path.read_text(encoding="utf-8"))
        return loaded if isinstance(loaded, dict) else {}
    except Exception:
        repos: list[str] = []
        in_repos = False
        for line in cfg_path.read_text(encoding="utf-8", errors="ignore").splitlines():
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue
            if stripped.startswith("repos:"):
                in_repos = True
                continue
            if in_repos and stripped.startswith("- "):
                repos.append(stripped[2:].strip().strip("'\""))
            elif ":" in stripped:
                in_repos = False
        return {"repos": repos} if repos else {}


def _find_git_toplevel(start: Path) -> Path | None:
    result = run_git(start, "rev-parse", "--show-toplevel")
    if result.returncode == 0 and result.stdout.strip():
        return Path(result.stdout.strip()).resolve()
    return None


def discover_workspace_root(explicit: str | None = None) -> Path | None:
    """Resolve an explicit or declared multi-repo workspace root.

    Returns None when no --root, OPENAGENTIC_ROOT, or .openagenticsecurity.yaml
    manifest is present — callers never silently scan the parent of where
    agentic-sdlc happens to be cloned.
    """
    if explicit:
        return Path(explicit).expanduser().resolve()
    if os.environ.get("OPENAGENTIC_ROOT"):
        return Path(os.environ["OPENAGENTIC_ROOT"]).expanduser().resolve()
    cwd = Path.cwd().resolve()
    for candidate in (cwd, *cwd.parents):
        if (candidate / WORKSPACE_CONFIG_FILE).is_file():
            return candidate
    return None


def discover_repos(root: Path) -> list[Path]:
    config = _load_workspace_config(root)
    if config is not None:
        raw_exclude = config.get("exclude")
        excluded: set[str] = set()
        if isinstance(raw_exclude, list):
            excluded.update(str(item) for item in raw_exclude)
        raw_repos = config.get("repos")
        if isinstance(raw_repos, list) and raw_repos:
            configured: list[Path] = []
            for entry in raw_repos:
                name = str(entry).strip()
                if not name or name in excluded:
                    continue
                candidate = (root / name).resolve()
                if candidate.is_dir():
                    configured.append(candidate)
            return sorted(configured, key=lambda item: item.name.lower())

    children = [
        child
        for child in sorted(root.iterdir(), key=lambda item: item.name.lower())
        if child.is_dir() and not child.name.startswith(".")
    ]
    return [
        child
        for child in children
        if (child / ".git").exists() or is_git_repo(child)
    ]


def _resolve_target_repos(
    explicit_root: str | None,
    requested_repos: list[str] | None = None,
) -> tuple[Path, list[Path]] | None:
    """Resolve target repositories safely without accidental sibling-repo scope.

    Precedence:
      1. Explicit --root / OPENAGENTIC_ROOT / .openagenticsecurity.yaml -> workspace repos
      2. Explicit --repo paths -> those repositories only
      3. Current working directory inside a Git repo -> that single repository only
      4. Otherwise -> None (caller fails closed asking for --root or --repo)
    """
    root = discover_workspace_root(explicit_root)
    if root is not None:
        return root, discover_repos(root)

    if requested_repos:
        resolved: list[Path] = []
        for raw in requested_repos:
            candidate = Path(raw).expanduser().resolve()
            if candidate.is_dir():
                resolved.append(candidate)
        if resolved:
            return Path.cwd().resolve(), resolved

    current_repo = _find_git_toplevel(Path.cwd().resolve())
    if current_repo is not None:
        return current_repo, [current_repo]
    return None


def is_git_repo(path: Path) -> bool:
    result = run_git(path, "rev-parse", "--is-inside-work-tree")
    return result.returncode == 0 and result.stdout.strip() == "true"


def current_branch(repo: Path) -> str:
    branch = git_stdout(repo, "branch", "--show-current")
    return branch if branch else "DETACHED"


def default_ref(repo: Path) -> tuple[str, str]:
    ref = git_stdout(repo, "symbolic-ref", "--quiet", "--short", "refs/remotes/origin/HEAD")
    if not ref:
        for candidate in ("origin/main", "origin/master"):
            if run_git(repo, "rev-parse", "--verify", "--quiet", candidate).returncode == 0:
                ref = candidate
                break
    if not ref:
        return "NA", "NA"
    return ref, ref.removeprefix("origin/")


def ahead_behind(repo: Path, left: str, right: str) -> tuple[str, str]:
    output = git_stdout(repo, "rev-list", "--left-right", "--count", f"{left}...{right}")
    if not output:
        return "NA", "NA"
    parts = output.split()
    if len(parts) != 2:
        return "NA", "NA"
    return parts[0], parts[1]


def status_counts(repo: Path) -> tuple[int, int, int]:
    result = run_git(repo, "status", "--porcelain")
    if result.returncode != 0:
        return 0, 0, 0
    lines = [line for line in result.stdout.splitlines() if line]
    tracked = sum(1 for line in lines if not line.startswith("??"))
    untracked = sum(1 for line in lines if line.startswith("??"))
    return len(lines), tracked, untracked


def config_value(repo: Path, *keys: str) -> str:
    for key in keys:
        value = git_stdout(repo, "config", "--get", key)
        if value:
            return value
    return "unset"


def read_git_path(repo: Path, git_path: str) -> Path:
    value = git_stdout(repo, "rev-parse", "--git-path", git_path)
    if not value:
        return repo / ".git" / git_path
    path = Path(value)
    if path.is_absolute():
        return path
    return (repo / path).resolve()


def git_common_dir(repo: Path) -> Path | None:
    result = run_git(repo, "rev-parse", "--path-format=absolute", "--git-common-dir")
    if result.returncode == 0 and result.stdout.strip():
        return Path(result.stdout.strip()).resolve()

    value = git_stdout(repo, "rev-parse", "--git-common-dir")
    if not value:
        return None
    path = Path(value)
    if path.is_absolute():
        return path.resolve()
    return (repo / path).resolve()


def managed_hooks_dir(repo: Path) -> Path | None:
    common_dir = git_common_dir(repo)
    if common_dir is None:
        return None
    return common_dir / GUARDRAIL_DIR


def _expected_managed_hooks(repo: Path, *, allow_primary_topic: bool | None = None) -> dict[str, str]:
    if allow_primary_topic is None:
        allow_primary_topic = git_stdout(repo, "config", "--get", ALLOW_PRIMARY_TOPIC_KEY) == "true"
    hooks: dict[str, str] = {
        "pre-commit": _render_pre_commit_hook(allow_primary_topic=allow_primary_topic),
        "pre-push": PRE_PUSH_HOOK,
    }
    for name in FORWARDED_CLIENT_HOOKS:
        hooks[name] = _render_forward_hook(name)
    return hooks


def guardrails_ok(repo: Path) -> bool:
    hooks_dir = managed_hooks_dir(repo)
    if hooks_dir is None:
        return False
    configured = git_stdout(repo, "config", "--path", "--get", "core.hooksPath")
    if not configured:
        return False
    try:
        configured_path = Path(configured).expanduser().resolve()
    except (OSError, RuntimeError):
        return False
    if configured_path != hooks_dir.resolve():
        return False
    expected = _expected_managed_hooks(repo)
    for name, content in expected.items():
        path = hooks_dir / name
        if not path.is_file() or not os.access(path, os.X_OK):
            return False
        if path.read_text(encoding="utf-8", errors="ignore") != content:
            return False
    return True


def _existing_hooks_path(repo: Path) -> str:
    configured = git_stdout(repo, "config", "--get", "core.hooksPath")
    if configured:
        path = Path(configured).expanduser()
        if not path.is_absolute():
            path = repo / path
        return str(path.resolve())
    common_dir = git_common_dir(repo)
    if common_dir is None:
        raise RuntimeError(f"{repo.name}: cannot determine Git common dir")
    return str(common_dir / "hooks")


def install_guardrails(repo: Path, *, allow_primary_topic: bool = False) -> list[str]:
    if not is_git_repo(repo):
        return []
    hooks_dir = managed_hooks_dir(repo)
    if hooks_dir is None:
        raise RuntimeError(f"{repo.name}: cannot determine managed hooks directory")

    changes: list[str] = []
    previous = git_stdout(repo, "config", "--get", PREVIOUS_HOOKS_PATH_KEY)
    current_hooks = git_stdout(repo, "config", "--get", "core.hooksPath")
    if not previous and (not current_hooks or Path(current_hooks).expanduser() != hooks_dir):
        previous = _existing_hooks_path(repo)
        result = run_git(repo, "config", PREVIOUS_HOOKS_PATH_KEY, previous)
        if result.returncode != 0:
            raise RuntimeError(result.stderr.strip() or result.stdout.strip())
        changes.append(f"preserved hooksPath={previous}")

    allow_str = "true" if allow_primary_topic else "false"
    if git_stdout(repo, "config", "--get", ALLOW_PRIMARY_TOPIC_KEY) != allow_str:
        res = run_git(repo, "config", ALLOW_PRIMARY_TOPIC_KEY, allow_str)
        if res.returncode != 0:
            raise RuntimeError(res.stderr.strip() or res.stdout.strip())

    hooks_dir.mkdir(parents=True, exist_ok=True)
    expected = _expected_managed_hooks(repo, allow_primary_topic=allow_primary_topic)
    # Also forward any additional executable hook files found in the preserved hooks dir.
    if previous:
        prev_dir = Path(previous)
        if prev_dir.is_dir():
            for item in sorted(prev_dir.iterdir()):
                if (
                    item.is_file()
                    and not item.name.endswith(".sample")
                    and item.name not in expected
                    and os.access(item, os.X_OK)
                ):
                    expected[item.name] = _render_forward_hook(item.name)

    for name, content in expected.items():
        path = hooks_dir / name
        existing = path.read_text(encoding="utf-8", errors="ignore") if path.exists() else ""
        if existing != content:
            path.write_text(content, encoding="utf-8")
            changes.append(f"installed {name}")
        executable_mode = path.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH
        if path.stat().st_mode != executable_mode:
            path.chmod(executable_mode)
            changes.append(f"made {name} executable")

    result = run_git(repo, "config", "core.hooksPath", str(hooks_dir))
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or result.stdout.strip())
    if current_hooks != str(hooks_dir):
        changes.append(f"core.hooksPath={hooks_dir}")
    return changes


def remove_guardrails(repo: Path) -> list[str]:
    if not is_git_repo(repo):
        return []
    hooks_dir = managed_hooks_dir(repo)
    common_dir = git_common_dir(repo)
    if hooks_dir is None or common_dir is None:
        raise RuntimeError(f"{repo.name}: cannot determine managed hooks directory")

    changes: list[str] = []
    current_hooks = git_stdout(repo, "config", "--get", "core.hooksPath")
    previous = git_stdout(repo, "config", "--get", PREVIOUS_HOOKS_PATH_KEY)
    default_hooks = str((common_dir / "hooks").resolve())

    if current_hooks and Path(current_hooks).expanduser().resolve() == hooks_dir.resolve():
        if previous and Path(previous).expanduser().resolve() != Path(default_hooks):
            res = run_git(repo, "config", "core.hooksPath", previous)
            if res.returncode != 0:
                raise RuntimeError(res.stderr.strip() or res.stdout.strip())
            changes.append(f"restored core.hooksPath={previous}")
        else:
            run_git(repo, "config", "--unset", "core.hooksPath")
            changes.append("unset core.hooksPath")

    if previous:
        run_git(repo, "config", "--unset", PREVIOUS_HOOKS_PATH_KEY)
        changes.append("cleared saved hooksPath")
    if git_stdout(repo, "config", "--get", ALLOW_PRIMARY_TOPIC_KEY):
        run_git(repo, "config", "--unset", ALLOW_PRIMARY_TOPIC_KEY)

    if hooks_dir.is_dir():
        unmanaged = [
            item
            for item in hooks_dir.iterdir()
            if not item.is_file()
            or GUARDRAIL_MARKER_PREFIX not in item.read_text(encoding="utf-8", errors="ignore")
        ]
        if unmanaged:
            raise RuntimeError(
                f"refusing to delete {hooks_dir}: contains unmanaged entries "
                f"({', '.join(p.name for p in unmanaged)})"
            )
        shutil.rmtree(hooks_dir)
        changes.append(f"removed {hooks_dir.name}")
    return changes


def file_contains_worktree_patterns(path: Path) -> bool:
    if not path.exists() or not path.is_file():
        return False
    lines = {
        line.strip()
        for line in path.read_text(encoding="utf-8", errors="ignore").splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    }
    return any(pattern in lines for pattern in WORKTREE_PATTERNS)


def has_worktree_ignore(repo: Path) -> bool:
    return file_contains_worktree_patterns(repo / ".gitignore") or file_contains_worktree_patterns(
        read_git_path(repo, "info/exclude")
    )


def worktree_count(repo: Path) -> int:
    result = run_git(repo, "worktree", "list", "--porcelain")
    if result.returncode != 0:
        return 0
    return sum(1 for line in result.stdout.splitlines() if line.startswith("worktree "))


def collect_state(repo: Path, fetch: bool = False) -> RepoState:
    state = RepoState(name=repo.name, path=repo, is_git=is_git_repo(repo))
    if not state.is_git:
        return state

    if fetch:
        fetched = run_git(repo, "fetch", "--prune", "origin")
        if fetched.returncode != 0:
            state.fetch_error = fetched.stderr.strip() or fetched.stdout.strip()

    state.branch = current_branch(repo)
    state.upstream = git_stdout(repo, "rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{u}") or "none"
    if state.upstream != "none":
        state.ahead, state.behind = ahead_behind(repo, "HEAD", "@{u}")
    state.default_ref, state.default_branch = default_ref(repo)
    if state.default_ref != "NA":
        state.default_ahead, state.default_behind = ahead_behind(repo, "HEAD", state.default_ref)
    state.dirty, state.tracked_dirty, state.untracked = status_counts(repo)
    state.pull_ff = config_value(repo, "pull.ff")
    state.pull_rebase = config_value(repo, "pull.rebase")
    state.default_rebase = config_value(repo, f"branch.{state.default_branch}.rebase")
    state.has_worktree_ignore = has_worktree_ignore(repo)
    state.worktree_count = worktree_count(repo)
    state.guardrails_ok = guardrails_ok(repo)
    return state


def print_audit(states: Iterable[RepoState], root: Path, fetch: bool, tsv: bool = False) -> tuple[int, int]:
    states = list(states)
    high_count = sum(1 for state in states for _ in state.high_risks())
    warning_count = sum(1 for state in states for _ in state.warnings())
    if tsv:
        print(
            "\t".join(
                (
                    "repo",
                    "branch",
                    "upstream",
                    "ahead",
                    "behind",
                    "dirty",
                    "tracked_dirty",
                    "untracked",
                    "worktrees",
                    "default_branch",
                    "default_ahead",
                    "default_behind",
                    "config_ok",
                    "guardrails_ok",
                    "high_risks",
                    "warnings",
                )
            )
        )
        for state in states:
            print(
                "\t".join(
                    (
                        state.name,
                        state.branch,
                        state.upstream,
                        state.ahead,
                        state.behind,
                        str(state.dirty),
                        str(state.tracked_dirty),
                        str(state.untracked),
                        str(state.worktree_count),
                        state.default_branch,
                        state.default_ahead,
                        state.default_behind,
                        "yes" if state.config_ok else "no",
                        "yes" if state.guardrails_ok else "no",
                        "; ".join(state.high_risks()),
                        "; ".join(state.warnings()),
                    )
                )
            )
        return high_count, warning_count

    print("Workspace Git audit")
    print(f"Root: {root}")
    print(f"Fetch: {'yes' if fetch else 'no'}")
    print("---")
    for state in states:
        if not state.is_git:
            print(f"{state.name}: SKIP not a Git repository")
            continue
        sync = f"{state.default_branch} +{state.default_ahead}/-{state.default_behind}"
        dirty = (
            "clean"
            if state.dirty == 0
            else f"dirty {state.dirty} ({state.tracked_dirty} tracked, {state.untracked} untracked)"
        )
        print(
            f"{state.name}: branch={state.branch} upstream={state.upstream} "
            f"default_sync={sync} {dirty} worktrees={state.worktree_count}"
        )
        risks = state.high_risks()
        warnings = state.warnings()
        if risks:
            print("  HIGH: " + "; ".join(risks))
        if warnings:
            print("  WARN: " + "; ".join(warnings))
    print("---")
    print(f"Summary: {high_count} high risks, {warning_count} warnings across {len(states)} entries")
    return high_count, warning_count


def configure_repo(repo: Path, add_excludes: bool = True) -> list[str]:
    changed: list[str] = []
    if not is_git_repo(repo):
        return changed

    default_remote_ref, default_branch_name = default_ref(repo)
    settings = (
        ("pull.ff", "only"),
        ("pull.rebase", "true"),
        (f"branch.{default_branch_name}.rebase", "false"),
    )
    for key, value in settings:
        if default_remote_ref == "NA" and key.startswith("branch."):
            continue
        current = git_stdout(repo, "config", "--get", key)
        if current != value:
            result = run_git(repo, "config", key, value)
            if result.returncode != 0:
                raise RuntimeError(f"{repo.name}: failed to set {key}: {result.stderr.strip()}")
            changed.append(f"{key}={value}")

    if add_excludes:
        exclude_path = read_git_path(repo, "info/exclude")
        exclude_path.parent.mkdir(parents=True, exist_ok=True)
        existing = exclude_path.read_text(encoding="utf-8", errors="ignore") if exclude_path.exists() else ""
        existing_lines = {line.strip() for line in existing.splitlines()}
        missing = [pattern for pattern in WORKTREE_PATTERNS if pattern not in existing_lines]
        if missing:
            with exclude_path.open("a", encoding="utf-8") as handle:
                if existing and not existing.endswith("\n"):
                    handle.write("\n")
                handle.write("\n# Local AI/worktree state (agentic-sdlc)\n")
                for pattern in missing:
                    handle.write(f"{pattern}\n")
            changed.append("info/exclude worktree patterns")
    return changed


def slugify(value: str) -> str:
    slug = re.sub(r"[^A-Za-z0-9._-]+", "-", value.strip().lower()).strip("-")
    return slug or "agent-task"


def parse_occupied(values: list[str] | None = None) -> set[str]:
    occupied: set[str] = set()
    raw_values = list(values or [])
    env_value = os.environ.get("OPENAGENTIC_OCCUPIED_REPOS", "")
    if env_value:
        raw_values.append(env_value)
    for raw in raw_values:
        for item in re.split(r"[\s,]+", raw):
            if item.strip():
                occupied.add(item.strip())
    return occupied


def ensure_branch_available(repo: Path, branch: str) -> None:
    if run_git(repo, "show-ref", "--verify", "--quiet", f"refs/heads/{branch}").returncode == 0:
        raise RuntimeError(f"local branch already exists: {branch}")


def create_clean_worktree(repo: Path, task: str, branch: str, base_ref: str) -> Path:
    configure_repo(repo, add_excludes=True)
    ensure_branch_available(repo, branch)
    path = repo / ".worktrees" / slugify(task)
    if path.exists():
        raise RuntimeError(f"worktree path already exists: {path}")
    result = run_git(repo, "worktree", "add", str(path), "-b", branch, base_ref)
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or result.stdout.strip())
    return path


def cmd_audit(args: argparse.Namespace) -> int:
    resolved = _resolve_target_repos(args.root)
    if resolved is None:
        print(
            "ERROR: cannot determine workspace root; pass --root <workspace-dir> or run inside a Git repository.",
            file=sys.stderr,
        )
        return 2
    root, repos = resolved
    states = [collect_state(repo, fetch=args.fetch) for repo in repos]
    high_count, warning_count = print_audit(states, root=root, fetch=args.fetch, tsv=args.tsv)
    if args.strict and (high_count > 0 or warning_count > 0):
        return 1
    return 0


def cmd_guardrails(args: argparse.Namespace) -> int:
    resolved = _resolve_target_repos(args.root, args.repo)
    if resolved is None:
        print(
            "ERROR: refusing to guess a workspace root; pass --root <workspace-dir>, --repo <path>, "
            "or run inside a Git repository.",
            file=sys.stderr,
        )
        return 2
    root, repos = resolved
    requested = {Path(item).name for item in (args.repo or [])}
    seen: set[Path] = set()
    failed = 0
    changed = 0
    mode = "remove" if args.remove else ("apply" if args.apply else "audit")
    print(f"Managed main-branch guardrails ({mode})")
    print(f"Root: {root}")
    print("---")
    for repo in repos:
        if not is_git_repo(repo):
            continue
        common_dir = git_common_dir(repo)
        if common_dir is None or common_dir in seen:
            continue
        seen.add(common_dir)
        canonical_name = common_dir.parent.name if common_dir.name == ".git" else repo.name
        if requested and repo.name not in requested and canonical_name not in requested:
            continue
        if args.remove:
            try:
                changes = remove_guardrails(repo)
            except (OSError, RuntimeError) as exc:
                print(f"{canonical_name}: FAIL {exc}")
                failed += 1
                continue
            if changes:
                print(f"{canonical_name}: REMOVED " + ", ".join(changes))
                changed += 1
            else:
                print(f"{canonical_name}: OK not installed")
            continue
        if not args.apply:
            ok = guardrails_ok(repo)
            print(f"{canonical_name}: {'OK' if ok else 'MISSING'}")
            if not ok:
                failed += 1
            continue
        try:
            changes = install_guardrails(repo, allow_primary_topic=args.allow_primary_topic)
        except (OSError, RuntimeError) as exc:
            print(f"{canonical_name}: FAIL {exc}")
            failed += 1
            continue
        if not guardrails_ok(repo):
            print(f"{canonical_name}: FAIL post-install verification")
            failed += 1
        elif changes:
            print(f"{canonical_name}: UPDATED " + ", ".join(changes))
            changed += 1
        else:
            print(f"{canonical_name}: OK already installed")
    print("---")
    verb = "removed" if args.remove else "updated"
    print(f"Summary: {changed} {verb}, {failed} missing/failed")
    return 1 if failed else 0


def cmd_clean_defaults(args: argparse.Namespace) -> int:
    root = discover_workspace_root(args.root)
    if root is None:
        print(
            "ERROR: clean-defaults requires --root <workspace-dir>, OPENAGENTIC_ROOT, or .openagenticsecurity.yaml.",
            file=sys.stderr,
        )
        return 2
    occupied = parse_occupied(args.occupied)
    skipped = 0
    changed = 0
    failed = 0
    mode = "apply" if args.apply else "dry-run"

    print(f"Default checkout cleanup ({mode})")
    print(f"Root: {root}")
    if occupied:
        print("Occupied repos: " + ", ".join(sorted(occupied)))
    print("---")

    for repo in discover_repos(root):
        if not is_git_repo(repo):
            print(f"{repo.name}: SKIP not a Git repository")
            continue

        if args.configure:
            try:
                configure_repo(repo, add_excludes=True)
            except RuntimeError as exc:
                print(f"{repo.name}: FAIL {exc}")
                failed += 1
                continue

        state = collect_state(repo, fetch=args.fetch)

        if args.fetch and state.fetch_error:
            print(f"{repo.name}: FAIL fetch failed ({state.fetch_error}); refusing stale sync")
            failed += 1
            continue

        if repo.name in occupied:
            print(f"{repo.name}: SKIP occupied by active agent at {repo}")
            skipped += 1
            continue

        if state.default_ref == "NA":
            print(f"{repo.name}: SKIP cannot determine origin default branch")
            skipped += 1
            continue

        if state.branch != state.default_branch:
            print(
                f"{repo.name}: SKIP current branch is {state.branch}, "
                f"default is {state.default_branch}; do not switch active checkouts"
            )
            skipped += 1
            continue

        if state.dirty > 0:
            print(
                f"{repo.name}: SKIP dirty default checkout "
                f"({state.tracked_dirty} tracked, {state.untracked} untracked)"
            )
            skipped += 1
            continue

        if _to_int(state.default_ahead) > 0:
            print(f"{repo.name}: SKIP default ahead of remote by {state.default_ahead} commits")
            skipped += 1
            continue

        if _to_int(state.default_behind) == 0:
            print(f"{repo.name}: OK clean latest {state.default_branch}")
            continue

        if not args.apply:
            print(
                f"{repo.name}: WOULD fast-forward {state.default_branch} "
                f"by {state.default_behind} commits from {state.default_ref}"
            )
            changed += 1
            continue

        result = run_git(repo, "merge", "--ff-only", state.default_ref)
        if result.returncode != 0:
            print(f"{repo.name}: FAIL {result.stderr.strip() or result.stdout.strip()}")
            failed += 1
            continue
        after = collect_state(repo, fetch=False)
        print(
            f"{repo.name}: UPDATED {after.default_branch} "
            f"+{after.default_ahead}/-{after.default_behind} dirty={after.dirty}"
        )
        changed += 1

    print("---")
    print(f"Summary: {changed} {'updated' if args.apply else 'would update'}, {skipped} skipped, {failed} failed")
    if failed > 0 or (args.strict and skipped > 0):
        return 1
    return 0


def cmd_agent_start(args: argparse.Namespace) -> int:
    repo = Path(args.repo).expanduser()
    if not repo.is_absolute():
        root = discover_workspace_root(args.root)
        repo = (root / repo) if root is not None else (Path.cwd() / repo)
    repo = repo.resolve()
    if not repo.exists():
        print(f"ERROR: repo does not exist: {repo}", file=sys.stderr)
        return 2
    if not is_git_repo(repo):
        print(f"ERROR: not a Git repository: {repo}", file=sys.stderr)
        return 2

    if args.configure:
        changes = configure_repo(repo, add_excludes=True)
        if changes:
            print(f"{repo.name}: configured " + ", ".join(changes))

    state = collect_state(repo, fetch=args.fetch)
    print(
        f"{repo.name}: branch={state.branch} default={state.default_branch} "
        f"default +{state.default_ahead}/-{state.default_behind} dirty={state.dirty}"
    )

    if args.fetch and state.fetch_error:
        print(
            f"ERROR: git fetch failed ({state.fetch_error}); refusing to start from stale remote ref.",
            file=sys.stderr,
        )
        return 2

    if state.default_ref == "NA":
        print("ERROR: cannot determine origin default branch", file=sys.stderr)
        return 2

    if state.branch == state.default_branch and state.dirty == 0 and _to_int(state.default_behind) > 0:
        if args.update_default:
            result = run_git(repo, "merge", "--ff-only", state.default_ref)
            if result.returncode != 0:
                print(result.stderr.strip() or result.stdout.strip(), file=sys.stderr)
                return 2
            state = collect_state(repo, fetch=False)
            print(f"{repo.name}: fast-forwarded {state.default_branch} to {state.default_ref}")
        else:
            print("BLOCKED: clean default checkout is behind; rerun with --update-default")
            return 2

    unsafe_default = (
        state.branch == state.default_branch
        and state.dirty > 0
        and _to_int(state.default_behind) > 0
    )
    detached = state.branch == "DETACHED"

    if unsafe_default or detached:
        reason = "detached HEAD" if detached else "dirty default checkout is behind remote"
        if not args.create_worktree:
            print(f"BLOCKED: {reason}.")
            print(
                "Use --create-worktree --branch <type/topic> to start from "
                f"{state.default_ref} without touching local WIP."
            )
            return 2

    if args.create_worktree:
        branch = args.branch or f"chore/{slugify(args.task)}"
        try:
            path = create_clean_worktree(repo, args.task, branch, state.default_ref)
        except RuntimeError as exc:
            print(f"ERROR: {exc}", file=sys.stderr)
            return 2
        print(f"Worktree ready: {path}")
        print(f"Branch: {branch}")
        print(f"Base: {state.default_ref}")
        return 0

    if state.dirty > 0:
        print("WARN: checkout has local changes; confirm ownership before editing.")
    else:
        print("OK: checkout is clean for preflight.")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Multi-repository workspace Git governance utility")
    subparsers = parser.add_subparsers(dest="command", required=True)

    audit = subparsers.add_parser("audit", help="Audit Git, worktree, and guardrail state")
    audit.add_argument("--root", help="Workspace root directory (default: current Git repo or OPENAGENTIC_ROOT).")
    audit.add_argument("--all-repos", action="store_true", help=argparse.SUPPRESS)
    audit.add_argument("--fetch", dest="fetch", action="store_true", help="Run git fetch --prune origin first.")
    audit.add_argument("--no-fetch", dest="fetch", action="store_false", help="Do not fetch before auditing.")
    audit.set_defaults(fetch=False)
    audit.add_argument("--strict", action="store_true", help="Exit non-zero when risks or warnings exist.")
    audit.add_argument("--tsv", action="store_true", help="Print machine-readable TSV.")
    audit.set_defaults(func=cmd_audit)

    guardrails = subparsers.add_parser(
        "guardrails",
        help="Audit, install (--apply), or uninstall (--remove) managed main-branch Git hooks",
    )
    guardrails.add_argument("--root", help="Workspace root directory (default: current Git repo or OPENAGENTIC_ROOT).")
    guardrails.add_argument("--all-repos", action="store_true", help=argparse.SUPPRESS)
    guardrails.add_argument(
        "--repo",
        action="append",
        default=[],
        help="Limit to a repository name or path. Can be repeated.",
    )
    action_group = guardrails.add_mutually_exclusive_group()
    action_group.add_argument("--apply", action="store_true", help="Install or refresh managed hooks.")
    action_group.add_argument("--remove", action="store_true", help="Uninstall managed hooks and restore core.hooksPath.")
    guardrails.add_argument(
        "--allow-primary-topic",
        action="store_true",
        help="Allow commits on non-default branches in the primary checkout (still blocks default branch & detached HEAD).",
    )
    guardrails.set_defaults(func=cmd_guardrails)

    clean_defaults = subparsers.add_parser(
        "clean-defaults",
        help="Dry-run or apply safe default-checkout fast-forwards",
    )
    clean_defaults.add_argument("--root", help="Workspace root directory (or OPENAGENTIC_ROOT).")
    clean_defaults.add_argument("--all-repos", action="store_true", help=argparse.SUPPRESS)
    clean_defaults.add_argument("--fetch", dest="fetch", action="store_true", help="Fetch before cleanup.")
    clean_defaults.add_argument("--no-fetch", dest="fetch", action="store_false", help="Do not fetch before cleanup.")
    clean_defaults.set_defaults(fetch=True)
    clean_defaults.add_argument("--apply", action="store_true", help="Apply safe fast-forwards.")
    clean_defaults.add_argument("--configure", action="store_true", help="Apply local Git safety config first.")
    clean_defaults.add_argument(
        "--occupied",
        action="append",
        default=[],
        help="Repo name occupied by an active agent. Can be repeated or comma-separated.",
    )
    clean_defaults.add_argument("--strict", action="store_true", help="Exit non-zero when any repo is skipped.")
    clean_defaults.set_defaults(func=cmd_clean_defaults)

    agent_start = subparsers.add_parser("agent-start", help="Preflight an agent task in one repo")
    agent_start.add_argument("--root", help="Workspace root directory (or OPENAGENTIC_ROOT).")
    agent_start.add_argument("--repo", required=True, help="Repo name under root or path.")
    agent_start.add_argument("--task", required=True, help="Human-readable task name.")
    agent_start.add_argument("--branch", help="Branch name to create when --create-worktree is used.")
    agent_start.add_argument("--fetch", dest="fetch", action="store_true", help="Fetch before preflight.")
    agent_start.add_argument("--no-fetch", dest="fetch", action="store_false", help="Do not fetch before preflight.")
    agent_start.set_defaults(fetch=True)
    agent_start.add_argument("--configure", action="store_true", help="Apply local Git safety config first.")
    agent_start.add_argument("--update-default", action="store_true", help="Fast-forward clean default checkout.")
    agent_start.add_argument("--create-worktree", action="store_true", help="Create clean latest worktree from origin default.")
    agent_start.set_defaults(func=cmd_agent_start)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
