#!/usr/bin/env python3
"""Standalone CLI for the Managed Issue Claim Comment protocol.

Implements deterministic rendering, validation, path-overlap detection, and
optional GitHub comment publication for multi-agent issue claims defined in
`standards/agent-issue-pr-loop.md`.

Marker format:
    <!-- agent-claim:<owner/repo#number>:<task-id> -->
"""

from __future__ import annotations

import argparse
from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import datetime, timezone
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import subprocess
import sys


VALID_STATUSES = frozenset(
    {
        "claimed",
        "running",
        "waiting_review",
        "blocked",
        "completed",
        "released",
        "failed",
    }
)
ACTIVE_STATUSES = frozenset({"claimed", "running", "waiting_review", "blocked"})
TERMINAL_STATUSES = frozenset({"completed", "released", "failed"})

MARKER_RE = re.compile(
    r"^<!--\s*agent-claim:(?P<issue>[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+#[1-9][0-9]*):"
    r"(?P<task>[A-Za-z0-9][A-Za-z0-9._-]{0,127})\s*-->$"
)
ISSUE_REF_RE = re.compile(
    r"^(?P<repo>[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+)#(?P<number>[1-9][0-9]*)$"
)
TASK_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
UTC_TS_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")
FIELD_LINE_RE = re.compile(r"^- (?P<key>[A-Za-z][A-Za-z0-9 ]+):\s*`(?P<val>[^`]+)`\s*$")
LIST_ITEM_RE = re.compile(r"^- `(?P<val>[^`]+)`\s*$")

REQUIRED_SCALAR_FIELDS = (
    "Status",
    "Automation identity",
    "GitHub actor",
    "Agent",
    "Session",
    "Task",
    "Repo",
    "Branch",
    "Worktree",
    "Claim issue",
    "PR",
    "Lease expires",
    "Updated",
)


class ClaimProtocolError(ValueError):
    """Fail-closed validation error for a managed issue claim."""


@dataclass(frozen=True)
class AgentClaimRecord:
    issue_ref: str
    task_id: str
    status: str
    automation_identity: str
    github_actor: str
    agent: str
    session: str
    repo: str
    branch: str
    worktree: str
    pr: str
    lease_expires: str
    updated: str
    owned_paths: tuple[str, ...]
    out_of_scope: tuple[str, ...] = field(default_factory=tuple)
    dependencies: tuple[str, ...] = field(default_factory=tuple)
    current_summary: str = ""
    next_action: str = ""
    source: str = ""

    @property
    def marker(self) -> str:
        return f"<!-- agent-claim:{self.issue_ref}:{self.task_id} -->"

    @property
    def is_active(self) -> bool:
        return self.status in ACTIVE_STATUSES

    def is_active_at(self, now: datetime | None = None) -> bool:
        if self.status not in ACTIVE_STATUSES:
            return False
        if now is None:
            return True
        lease_dt = datetime.strptime(self.lease_expires, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
        return lease_dt > now

    @property
    def canonical_repo(self) -> str:
        raw = self.repo.strip().lower()
        if "/" in raw:
            return raw
        issue_owner = self.issue_ref.split("/", 1)[0].lower()
        return f"{issue_owner}/{raw}"


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ClaimProtocolError(message)


def validate_utc_timestamp(value: str, field_name: str) -> str:
    _require(
        bool(UTC_TS_RE.fullmatch(value)),
        f"{field_name} must be UTC ISO-8601 (YYYY-MM-DDTHH:MM:SSZ), got {value!r}",
    )
    try:
        datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ")
    except ValueError as exc:
        raise ClaimProtocolError(f"{field_name} is not a valid calendar timestamp: {value!r}") from exc
    return value


def normalize_owned_path(raw: str, *, allow_none: bool = False) -> str:
    text = raw.strip()
    if allow_none and text == "none":
        return "none"
    _require(bool(text), "owned path must not be empty")
    _require("\\" not in text, f"owned path must use POSIX forward slashes: {raw!r}")
    _require(not text.startswith("/"), f"owned path must be repo-relative (no leading '/'): {raw!r}")
    _require(not any(ord(ch) < 32 or ord(ch) == 127 for ch in text), f"owned path contains control characters: {raw!r}")
    _require(not re.match(r"^[A-Za-z]:", text), f"owned path must not contain a drive prefix: {raw!r}")

    had_trailing_slash = text.endswith("/")
    parts = text.rstrip("/").split("/")
    _require(bool(parts) and all(part != "" for part in parts), f"owned path contains empty segments: {raw!r}")
    _require(all(part not in {".", ".."} for part in parts), f"owned path must not contain '.' or '..': {raw!r}")

    normalized = PurePosixPath(*parts).as_posix()
    return f"{normalized}/" if had_trailing_slash else normalized


def validate_claim_record(record: AgentClaimRecord) -> AgentClaimRecord:
    _require(bool(ISSUE_REF_RE.fullmatch(record.issue_ref)), f"invalid Claim issue: {record.issue_ref!r}")
    _require(bool(TASK_ID_RE.fullmatch(record.task_id)), f"invalid Task ID: {record.task_id!r}")
    _require(record.status in VALID_STATUSES, f"invalid Status: {record.status!r} (allowed: {sorted(VALID_STATUSES)})")
    for label, val in (
        ("Automation identity", record.automation_identity),
        ("GitHub actor", record.github_actor),
        ("Agent", record.agent),
        ("Session", record.session),
        ("Repo", record.repo),
        ("Branch", record.branch),
        ("Worktree", record.worktree),
        ("PR", record.pr),
    ):
        _require(bool(val.strip()), f"{label} must be non-empty")
    validate_utc_timestamp(record.lease_expires, "Lease expires")
    validate_utc_timestamp(record.updated, "Updated")
    _require(bool(record.owned_paths), "Owned paths must contain at least one path")
    normalized_owned = tuple(normalize_owned_path(p) for p in record.owned_paths)
    _require(len(set(normalized_owned)) == len(normalized_owned), "Owned paths must not contain duplicates")
    normalized_out = tuple(normalize_owned_path(p, allow_none=True) for p in record.out_of_scope)
    return AgentClaimRecord(
        issue_ref=record.issue_ref,
        task_id=record.task_id,
        status=record.status,
        automation_identity=record.automation_identity,
        github_actor=record.github_actor,
        agent=record.agent,
        session=record.session,
        repo=record.repo,
        branch=record.branch,
        worktree=record.worktree,
        pr=record.pr,
        lease_expires=record.lease_expires,
        updated=record.updated,
        owned_paths=normalized_owned,
        out_of_scope=normalized_out,
        dependencies=tuple(d.strip() for d in record.dependencies if d.strip()),
        current_summary=record.current_summary.strip(),
        next_action=record.next_action.strip(),
        source=record.source,
    )


def render_claim(record: AgentClaimRecord) -> str:
    validated = validate_claim_record(record)
    out_items = validated.out_of_scope or ("none",)
    dep_items = validated.dependencies or ("none",)

    lines = [
        validated.marker,
        "",
        "### Agent Claim",
        "",
        f"- Status: `{validated.status}`",
        f"- Automation identity: `{validated.automation_identity}`",
        f"- GitHub actor: `{validated.github_actor}`",
        f"- Agent: `{validated.agent}`",
        f"- Session: `{validated.session}`",
        f"- Task: `{validated.task_id}`",
        f"- Repo: `{validated.repo}`",
        f"- Branch: `{validated.branch}`",
        f"- Worktree: `{validated.worktree}`",
        f"- Claim issue: `{validated.issue_ref}`",
        f"- PR: `{validated.pr}`",
        f"- Lease expires: `{validated.lease_expires}`",
        f"- Updated: `{validated.updated}`",
        "",
        "Owned paths:",
        *[f"- `{path}`" for path in validated.owned_paths],
        "",
        "Out of scope:",
        *[f"- `{item}`" for item in out_items],
        "",
        "Dependencies:",
        *[f"- `{item}`" for item in dep_items],
        "",
        "Current summary:",
        validated.current_summary or "none",
        "",
        "Next action:",
        validated.next_action or "none",
        "",
    ]
    return "\n".join(lines)


def parse_claim(markdown_text: str, *, source: str = "<memory>") -> AgentClaimRecord:
    lines = markdown_text.splitlines()
    marker_idx: int | None = None
    for idx, raw_line in enumerate(lines):
        if raw_line.strip():
            marker_idx = idx
            break
    _require(marker_idx is not None, f"{source}: claim comment is empty")
    assert marker_idx is not None

    marker_match = MARKER_RE.fullmatch(lines[marker_idx].strip())
    _require(
        marker_match is not None,
        f"{source}: first non-empty line must be a valid <!-- agent-claim:<owner/repo#number>:<task-id> --> marker",
    )
    assert marker_match is not None
    marker_issue = marker_match.group("issue")
    marker_task = marker_match.group("task")

    scalars: dict[str, str] = {}
    section: str | None = None
    sections_list: dict[str, list[str]] = {
        "Owned paths": [],
        "Out of scope": [],
        "Dependencies": [],
    }
    sections_text: dict[str, list[str]] = {
        "Current summary": [],
        "Next action": [],
    }

    for raw_line in lines[marker_idx + 1 :]:
        stripped = raw_line.strip()
        if not stripped:
            continue
        if stripped == "### Agent Claim":
            section = "header"
            continue
        if stripped in ("Owned paths:", "Out of scope:", "Dependencies:"):
            section = stripped[:-1]
            continue
        if stripped in ("Current summary:", "Next action:"):
            section = stripped[:-1]
            continue

        if section in (None, "header"):
            fm = FIELD_LINE_RE.fullmatch(stripped)
            _require(fm is not None, f"{source}: unexpected header line: {stripped!r}")
            assert fm is not None
            key = fm.group("key")
            _require(key not in scalars, f"{source}: duplicate claim field {key!r}")
            scalars[key] = fm.group("val")
        elif section in sections_list:
            lm = LIST_ITEM_RE.fullmatch(stripped)
            _require(lm is not None, f"{source}: invalid list item under {section}: {stripped!r}")
            assert lm is not None
            sections_list[section].append(lm.group("val"))
        elif section in sections_text:
            sections_text[section].append(stripped)

    missing = [key for key in REQUIRED_SCALAR_FIELDS if key not in scalars]
    _require(not missing, f"{source}: missing required claim fields: {', '.join(missing)}")
    _require(
        scalars["Claim issue"] == marker_issue,
        f"{source}: Claim issue ({scalars['Claim issue']!r}) does not match marker ({marker_issue!r})",
    )
    _require(
        scalars["Task"] == marker_task,
        f"{source}: Task ({scalars['Task']!r}) does not match marker ({marker_task!r})",
    )

    record = AgentClaimRecord(
        issue_ref=scalars["Claim issue"],
        task_id=scalars["Task"],
        status=scalars["Status"],
        automation_identity=scalars["Automation identity"],
        github_actor=scalars["GitHub actor"],
        agent=scalars["Agent"],
        session=scalars["Session"],
        repo=scalars["Repo"],
        branch=scalars["Branch"],
        worktree=scalars["Worktree"],
        pr=scalars["PR"],
        lease_expires=scalars["Lease expires"],
        updated=scalars["Updated"],
        owned_paths=tuple(sections_list["Owned paths"]),
        out_of_scope=tuple(sections_list["Out of scope"]),
        dependencies=tuple(sections_list["Dependencies"]),
        current_summary="\n".join(sections_text["Current summary"]),
        next_action="\n".join(sections_text["Next action"]),
        source=source,
    )
    return validate_claim_record(record)


def paths_overlap(path_a: str, path_b: str) -> bool:
    # Compare case-insensitively so macOS/Windows case-variant spellings cannot slip past overlap checks.
    a_parts = normalize_owned_path(path_a).rstrip("/").lower().split("/")
    b_parts = normalize_owned_path(path_b).rstrip("/").lower().split("/")
    prefix_len = min(len(a_parts), len(b_parts))
    return a_parts[:prefix_len] == b_parts[:prefix_len]


def _parse_now(raw: str | None) -> datetime:
    if raw is None:
        return datetime.now(timezone.utc)
    validate_utc_timestamp(raw, "--now")
    return datetime.strptime(raw, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)


def _first_non_empty_line(text: str) -> str:
    for line in text.splitlines():
        stripped = line.strip()
        if stripped:
            return stripped
    return ""


def find_overlaps(
    claims: Sequence[AgentClaimRecord],
    *,
    now: datetime | None = None,
) -> list[dict[str, str]]:
    active = [claim for claim in claims if claim.is_active_at(now)]
    overlaps: list[dict[str, str]] = []
    for idx, left in enumerate(active):
        for right in active[idx + 1 :]:
            if left.canonical_repo != right.canonical_repo:
                continue
            if left.issue_ref == right.issue_ref and left.task_id == right.task_id:
                continue
            for lp in left.owned_paths:
                for rp in right.owned_paths:
                    if paths_overlap(lp, rp):
                        overlaps.append(
                            {
                                "repo": left.canonical_repo,
                                "claim_a": f"{left.issue_ref}:{left.task_id}",
                                "path_a": lp,
                                "claim_b": f"{right.issue_ref}:{right.task_id}",
                                "path_b": rp,
                            }
                        )
    return overlaps


def _read_claim_file(path_str: str) -> tuple[str, str]:
    if path_str == "-":
        return "<stdin>", sys.stdin.read()
    path = Path(path_str)
    if path.is_symlink() or not path.is_file():
        raise ClaimProtocolError(f"claim file must be a regular non-symlink file: {path}")
    return str(path), path.read_text(encoding="utf-8")


def _cmd_render(args: argparse.Namespace) -> int:
    now_utc = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    record = AgentClaimRecord(
        issue_ref=args.issue,
        task_id=args.task,
        status=args.status,
        automation_identity=args.identity,
        github_actor=args.actor,
        agent=args.agent,
        session=args.session,
        repo=args.repo,
        branch=args.branch,
        worktree=args.worktree,
        pr=args.pr,
        lease_expires=args.lease_expires,
        updated=args.updated or now_utc,
        owned_paths=tuple(args.owned_path),
        out_of_scope=tuple(args.out_of_scope or ()),
        dependencies=tuple(args.dependency or ()),
        current_summary=args.summary,
        next_action=args.next_action,
    )
    rendered = render_claim(record)
    if args.output is not None:
        if args.output.is_symlink():
            raise ClaimProtocolError(f"refusing to write to symlink output path: {args.output}")
        args.output.parent.mkdir(parents=True, exist_ok=True)
        flags = os.O_WRONLY | os.O_CREAT | os.O_TRUNC | getattr(os, "O_NOFOLLOW", 0)
        try:
            fd = os.open(args.output, flags, 0o644)
        except OSError as exc:
            raise ClaimProtocolError(f"refusing to write output path ({exc})") from exc
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(rendered)
    else:
        sys.stdout.write(rendered)
    return 0


def _cmd_validate(args: argparse.Namespace) -> int:
    parsed: list[AgentClaimRecord] = []
    for file_arg in args.files:
        src, text = _read_claim_file(file_arg)
        parsed.append(parse_claim(text, source=src))
    if args.json:
        payload = [
            {
                "source": item.source,
                "marker": item.marker,
                "status": item.status,
                "repo": item.repo,
                "owned_paths": list(item.owned_paths),
                "active": item.is_active,
            }
            for item in parsed
        ]
        print(json.dumps(payload, indent=2, ensure_ascii=True))
    else:
        print(f"OK: validated {len(parsed)} claim file(s)")
    return 0


def _cmd_check_overlap(args: argparse.Namespace) -> int:
    now = _parse_now(args.now)
    parsed: list[AgentClaimRecord] = []
    for file_arg in args.files:
        src, text = _read_claim_file(file_arg)
        parsed.append(parse_claim(text, source=src))
    overlaps = find_overlaps(parsed, now=now)
    if args.json:
        print(json.dumps({"overlaps": overlaps}, indent=2, ensure_ascii=True))
    elif overlaps:
        for item in overlaps:
            print(
                f"OVERLAP repo={item['repo']} {item['claim_a']} ({item['path_a']}) "
                f"<-> {item['claim_b']} ({item['path_b']})",
                file=sys.stderr,
            )
    else:
        print(f"OK: no overlapping active claims across {len(parsed)} claim(s)")
    return 2 if overlaps else 0


def _run_gh(cmd: list[str], *, timeout: int) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        cmd,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        timeout=timeout,
        check=False,
    )


def _cmd_publish(args: argparse.Namespace) -> int:
    _require(args.timeout >= 1, f"--timeout must be >= 1 second, got {args.timeout}")
    now = _parse_now(args.now)
    src, text = _read_claim_file(args.file)
    claim = parse_claim(text, source=src)
    match = ISSUE_REF_RE.fullmatch(claim.issue_ref)
    assert match is not None
    repo_slug = match.group("repo")
    issue_num = match.group("number")

    resolved_gh = shutil.which(args.gh_bin)
    if not resolved_gh:
        print(
            f"NOT_RUN: GitHub CLI ({args.gh_bin!r}) is not installed or not on PATH",
            file=sys.stderr,
        )
        return 1

    canonical_body = render_claim(claim)
    if args.dry_run:
        sys.stdout.write(canonical_body)
        return 0

    try:
        list_proc = _run_gh(
            [resolved_gh, "api", "--paginate", "--slurp", f"repos/{repo_slug}/issues/{issue_num}/comments"],
            timeout=args.timeout,
        )
    except subprocess.TimeoutExpired:
        print(f"NOT_RUN: gh api timed out after {args.timeout}s while listing issue comments", file=sys.stderr)
        return 1
    if list_proc.returncode != 0:
        print(f"NOT_RUN: failed to list issue comments: {list_proc.stderr.strip()}", file=sys.stderr)
        return 1

    try:
        raw_pages = json.loads(list_proc.stdout or "[]")
    except json.JSONDecodeError as exc:
        print(f"ERROR: invalid JSON response from gh api ({exc.msg})", file=sys.stderr)
        return 1
    if not isinstance(raw_pages, list):
        print("ERROR: invalid JSON response from gh api (expected comment array)", file=sys.stderr)
        return 1

    comments: list[dict[str, object]] = []
    for entry in raw_pages:
        if isinstance(entry, list):
            comments.extend(item for item in entry if isinstance(item, dict))
        elif isinstance(entry, dict):
            comments.append(entry)

    existing_comment: dict[str, object] | None = None
    existing_id: int | None = None
    other_claims: list[AgentClaimRecord] = []
    for comment in comments:
        body = str(comment.get("body", ""))
        user_obj = comment.get("user")
        comment_author = str(user_obj.get("login", "")) if isinstance(user_obj, dict) else ""
        first_line = _first_non_empty_line(body)
        if first_line == claim.marker and existing_id is None:
            raw_id = comment.get("id")
            if isinstance(raw_id, int) and not isinstance(raw_id, bool):
                existing_id = raw_id
                existing_comment = comment
            continue
        if MARKER_RE.fullmatch(first_line):
            try:
                parsed_other = parse_claim(body, source=f"comment#{comment.get('id', '?')}")
            except ClaimProtocolError:
                continue
            if comment_author and comment_author.lower() != parsed_other.github_actor.lower():
                print(
                    f"WARN: ignoring spoofed claim comment #{comment.get('id', '?')} "
                    f"(comment author {comment_author!r} != declared GitHub actor {parsed_other.github_actor!r})",
                    file=sys.stderr,
                )
                continue
            other_claims.append(parsed_other)

    if existing_comment is not None:
        user_obj = existing_comment.get("user")
        comment_author = str(user_obj.get("login", "")) if isinstance(user_obj, dict) else ""
        if comment_author and comment_author.lower() != claim.github_actor.lower() and not args.takeover:
            print(
                f"agent-claim error: refusing to overwrite comment #{existing_id} authored by "
                f"{comment_author!r} (claim declares {claim.github_actor!r}); pass --takeover to reassign",
                file=sys.stderr,
            )
            return 1
        existing_body = str(existing_comment.get("body", ""))
        try:
            existing_parsed = parse_claim(existing_body, source=f"comment#{existing_id}")
        except ClaimProtocolError:
            existing_parsed = None
        if existing_parsed is not None:
            same_owner = (
                existing_parsed.github_actor.lower() == claim.github_actor.lower()
                and existing_parsed.session == claim.session
            )
            if existing_parsed.is_active_at(now) and not same_owner and not args.takeover:
                print(
                    f"agent-claim error: refusing to overwrite active claim comment #{existing_id} "
                    f"owned by {existing_parsed.github_actor!r} (session {existing_parsed.session!r}); "
                    "use a distinct --task or pass --takeover to reassign",
                    file=sys.stderr,
                )
                return 1

    overlaps = find_overlaps([*other_claims, claim], now=now)
    if overlaps:
        for item in overlaps:
            print(
                f"OVERLAP repo={item['repo']} {item['claim_a']} ({item['path_a']}) "
                f"<-> {item['claim_b']} ({item['path_b']})",
                file=sys.stderr,
            )
        return 2

    if existing_id is not None:
        endpoint = f"repos/{repo_slug}/issues/comments/{existing_id}"
        method = "PATCH"
    else:
        endpoint = f"repos/{repo_slug}/issues/{issue_num}/comments"
        method = "POST"

    try:
        write_proc = _run_gh(
            [resolved_gh, "api", "--method", method, endpoint, "-f", f"body={canonical_body}"],
            timeout=args.timeout,
        )
    except subprocess.TimeoutExpired:
        print(f"NOT_RUN: gh api {method} {endpoint} timed out after {args.timeout}s", file=sys.stderr)
        return 1
    if write_proc.returncode != 0:
        print(f"ERROR: failed to {method} {endpoint}: {write_proc.stderr.strip()}", file=sys.stderr)
        return 1
    sys.stdout.write(write_proc.stdout)
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    render_p = subparsers.add_parser("render", help="Render a canonical managed issue claim comment.")
    render_p.add_argument("--issue", required=True, help="owner/repo#number")
    render_p.add_argument("--task", required=True, help="Task ID")
    render_p.add_argument("--status", required=True, choices=sorted(VALID_STATUSES))
    render_p.add_argument("--identity", required=True, help="Automation identity (e.g. 'Claude Code')")
    render_p.add_argument("--actor", required=True, help="GitHub actor login")
    render_p.add_argument("--agent", required=True, help="Agent slug (e.g. claude-code)")
    render_p.add_argument("--session", required=True, help="Session identifier")
    render_p.add_argument("--repo", required=True, help="Target repository name")
    render_p.add_argument("--branch", required=True, help="Topic branch name")
    render_p.add_argument("--worktree", required=True, help="Isolated worktree path")
    render_p.add_argument("--pr", default="none", help="PR reference or 'none'")
    render_p.add_argument("--lease-expires", required=True, help="UTC ISO-8601 lease expiry")
    render_p.add_argument("--updated", help="UTC ISO-8601 updated timestamp (default: now UTC)")
    render_p.add_argument("--owned-path", action="append", required=True, help="Repo-relative POSIX path (repeatable)")
    render_p.add_argument("--out-of-scope", action="append", default=[], help="Out-of-scope path (repeatable)")
    render_p.add_argument("--dependency", action="append", default=[], help="Dependency reference (repeatable)")
    render_p.add_argument("--summary", default="none", help="Current summary text")
    render_p.add_argument("--next-action", default="none", help="Next action text")
    render_p.add_argument("--output", type=Path, help="Optional file path to write rendered Markdown")
    render_p.set_defaults(func=_cmd_render)

    validate_p = subparsers.add_parser("validate", help="Validate one or more managed claim comments.")
    validate_p.add_argument("files", nargs="+", help="Claim Markdown file path(s), or '-' for stdin")
    validate_p.add_argument("--json", action="store_true", help="Emit structured JSON summary")
    validate_p.set_defaults(func=_cmd_validate)

    overlap_p = subparsers.add_parser("check-overlap", help="Check active claims for equal or nested Owned paths.")
    overlap_p.add_argument("files", nargs="+", help="Claim Markdown file path(s)")
    overlap_p.add_argument("--now", help="UTC ISO-8601 timestamp for lease-expiry evaluation (default: now UTC)")
    overlap_p.add_argument("--json", action="store_true", help="Emit JSON report")
    overlap_p.set_defaults(func=_cmd_check_overlap)

    publish_p = subparsers.add_parser("publish", help="Idempotently publish or update a claim comment via gh.")
    publish_p.add_argument("file", help="Claim Markdown file path (or '-' for stdin)")
    publish_p.add_argument("--gh-bin", default="gh", help="GitHub CLI binary (default: gh)")
    publish_p.add_argument("--now", help="UTC ISO-8601 timestamp for lease-expiry evaluation (default: now UTC)")
    publish_p.add_argument("--timeout", type=int, default=30, help="Timeout in seconds for gh calls (default: 30)")
    publish_p.add_argument(
        "--takeover",
        action="store_true",
        help="Allow overwriting an active claim owned by another actor/session with the same marker",
    )
    publish_p.add_argument("--dry-run", action="store_true", help="Validate and print body without calling GitHub")
    publish_p.set_defaults(func=_cmd_publish)

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        return args.func(args)
    except ClaimProtocolError as exc:
        print(f"agent-claim error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
