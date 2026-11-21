from __future__ import annotations

from pathlib import Path
import subprocess


REPO = Path(__file__).resolve().parents[1]
BOOTSTRAP = REPO / "scripts" / "bootstrap.sh"
COMPLIANCE = REPO / "scripts" / "check-product-compliance.sh"


def _run_bootstrap(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["bash", str(BOOTSTRAP), *args],
        cwd=REPO,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )


def test_bootstrap_dry_run_writes_nothing(tmp_path: Path) -> None:
    target = tmp_path / "empty-repo"
    target.mkdir()
    proc = _run_bootstrap("--profile", "L2", "--target", str(target), "--with-skills", "--dry-run")
    assert proc.returncode == 0, proc.stderr
    assert "Dry-run complete (profile=L2)" in proc.stdout
    assert list(target.iterdir()) == []


def test_bootstrap_l0_safe_non_overwrite_and_idempotent_gitignore(tmp_path: Path) -> None:
    target = tmp_path / "solo-repo"
    target.mkdir()
    (target / "AGENTS.md").write_text("# My Existing Custom AGENTS\n", encoding="utf-8")
    (target / ".gitignore").write_text("*.pyc\n", encoding="utf-8")

    first = _run_bootstrap("--profile", "L0", "--target", str(target))
    assert first.returncode == 0, first.stderr
    assert "SKIP (exists): AGENTS.md" in first.stdout
    assert (target / "AGENTS.md").read_text(encoding="utf-8") == "# My Existing Custom AGENTS\n"
    assert (target / "CLAUDE.md").is_file()
    assert (target / "docs/architecture/STATUS.md").is_file()
    assert (target / "docs/VIBE_CODING_CONTEXT.md").is_file()
    assert (target / ".github/pull_request_template.md").is_file()
    gitignore_once = (target / ".gitignore").read_text(encoding="utf-8")
    assert "*.pyc" in gitignore_once
    assert ".worktrees/" in gitignore_once

    # Running a second time skips everything idempotently
    second = _run_bootstrap("--profile", "L0", "--target", str(target))
    assert second.returncode == 0, second.stderr
    assert (target / ".gitignore").read_text(encoding="utf-8") == gitignore_once
    assert "SKIP (already present): .gitignore worktree snippet" in second.stdout

    # Explicit --force overwrites existing file
    forced = _run_bootstrap("--profile", "L0", "--target", str(target), "--force")
    assert forced.returncode == 0, forced.stderr
    assert "L0 Solo Baseline" in (target / "AGENTS.md").read_text(encoding="utf-8")


def test_bootstrap_l2_with_skills_and_checklists_passes_compliance(tmp_path: Path) -> None:
    target = tmp_path / "team-repo"
    target.mkdir()
    assert subprocess.run(["git", "-C", str(target), "init", "-b", "main"], check=False).returncode == 0

    proc = _run_bootstrap(
        "--profile",
        "L2",
        "--target",
        str(target),
        "--with-skills",
        "--with-checklists",
    )
    assert proc.returncode == 0, proc.stderr
    assert not (target / ".cursor/rules/openagenticsecurity.mdc").exists()
    for skill in (
        "bootstrap-agentic-sdlc",
        "secure-vibe-coding",
        "audit-pr-diff",
        "audit-production-readiness",
        "done-claim-verify",
        "multi-agent-git-flow",
    ):
        assert (target / ".agents/skills" / skill / "SKILL.md").is_file(), f"missing installed skill: {skill}"
    assert (target / "docs/checklists/done-claim.template.md").is_file()
    assert (target / "docs/checklists/secure-vibe-coding-review.md").is_file()
    assert (target / ".github/CODEOWNERS").is_file()
    assert (target / ".github/ruleset-policy.json").is_file()
    assert (target / "docs/github-ruleset.import.json").is_file()
    assert (target / ".github/workflows/candidate-gates.yml").is_file()
    assert "<owner>/<repo>" in (target / ".github/ISSUE_TEMPLATE/issue.md").read_text(encoding="utf-8")
    assert "OpenAgenticSecurity/agentic-sdlc" not in (target / ".github/ISSUE_TEMPLATE/issue.md").read_text(encoding="utf-8")
    assert "Use [AGENTS.md](AGENTS.md)" in (target / "CLAUDE.md").read_text(encoding="utf-8")

    # Fresh L2 bootstrap leaves @org/... placeholders in CODEOWNERS; compliance
    # must fail closed until real team/user handles are configured (GitHub skips
    # invalid owners silently).
    before_edit = _run_compliance("--profile", "L2", str(target))
    assert before_edit.returncode == 1, before_edit.stdout + before_edit.stderr
    assert "@org/" in before_edit.stderr

    # Once real owners are written into .github/CODEOWNERS, L2 compliance passes.
    codeowners = target / ".github/CODEOWNERS"
    codeowners.write_text(
        codeowners.read_text(encoding="utf-8").replace("@org/", "@acme-eng/"),
        encoding="utf-8",
    )
    comp = _run_compliance("--profile", "L2", str(target))
    assert comp.returncode == 0, comp.stdout + comp.stderr
    assert "PASS:" in comp.stdout


def _run_compliance(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["bash", str(COMPLIANCE), *args],
        cwd=REPO,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )


def _git_init(target: Path) -> None:
    target.mkdir()
    assert subprocess.run(["git", "-C", str(target), "init", "-q", "-b", "main"], check=False).returncode == 0


def _make(target: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["make", "-C", str(target), *args],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )


def test_bootstrap_fresh_repo_passes_matching_profile_compliance(tmp_path: Path) -> None:
    for profile in ("L0", "L1", "L2"):
        target = tmp_path / f"fresh-{profile}"
        _git_init(target)
        proc = _run_bootstrap("--profile", profile, "--target", str(target))
        assert proc.returncode == 0, proc.stderr
        # The script tells the adopter the exact, profile-matching follow-up check.
        assert f"check-product-compliance.sh --profile {profile} " in proc.stdout

        if profile == "L2":
            # L2 CODEOWNERS ships with @org/... placeholders and must fail closed until edited.
            unconfigured = _run_compliance("--profile", "L2", str(target))
            assert unconfigured.returncode == 1, unconfigured.stdout + unconfigured.stderr
            assert "@org/" in unconfigured.stderr
            co = target / ".github/CODEOWNERS"
            co.write_text(co.read_text(encoding="utf-8").replace("@org/", "@acme/"), encoding="utf-8")

        comp = _run_compliance("--profile", profile, str(target))
        assert comp.returncode == 0, f"{profile}: " + comp.stdout + comp.stderr
        assert "PASS:" in comp.stdout


def test_bootstrap_follow_up_command_is_copy_pasteable_for_paths_with_spaces(tmp_path: Path) -> None:
    target = tmp_path / "my repo with spaces"
    _git_init(target)
    proc = _run_bootstrap("--profile", "L0", "--target", str(target))
    assert proc.returncode == 0, proc.stderr

    follow_up = proc.stdout.rstrip().splitlines()[-1].strip()
    assert "check-product-compliance.sh --profile L0 " in follow_up
    # Run the printed line exactly as a user would paste it into a shell.
    pasted = subprocess.run(["bash", "-c", follow_up], text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
    assert pasted.returncode == 0, pasted.stdout + pasted.stderr
    assert "PASS:" in pasted.stdout


def test_bootstrap_installs_fail_closed_agent_check_entrypoint(tmp_path: Path) -> None:
    # AGENTS.md, CLAUDE.md and the L1 workflow all name `make agent-check`; after
    # bootstrap that command must exist and must not be green before it is configured.
    target = tmp_path / "entrypoint-repo"
    _git_init(target)
    proc = _run_bootstrap("--profile", "L0", "--target", str(target))
    assert proc.returncode == 0, proc.stderr
    assert "COPIED: Makefile" in proc.stdout
    assert "make agent-check" in (target / "AGENTS.md").read_text(encoding="utf-8")

    dry = _make(target, "-n", "agent-check")
    assert dry.returncode == 0, dry.stderr

    real = _make(target, "agent-check")
    assert real.returncode != 0, "unconfigured agent-check must fail closed, not report green"
    assert "not configured" in real.stderr


def test_bootstrap_never_modifies_an_existing_makefile(tmp_path: Path) -> None:
    target = tmp_path / "has-makefile"
    _git_init(target)
    original = "build:\n\t@echo build\n"
    (target / "Makefile").write_text(original, encoding="utf-8")

    proc = _run_bootstrap("--profile", "L1", "--target", str(target), "--force")
    assert proc.returncode == 0, proc.stderr
    assert (target / "Makefile").read_text(encoding="utf-8") == original
    assert (target / "Makefile.agent-check.snippet").is_file()
    assert "Merge Makefile.agent-check.snippet into your existing Makefile" in proc.stdout

    comp = _run_compliance("--profile", "L1", str(target))
    assert "no agent-check target" in comp.stderr

    # Once the adopter owns an agent-check target, bootstrap leaves it alone.
    (target / "Makefile").write_text(original + "\nagent-check:\n\t@echo ok\n", encoding="utf-8")
    (target / "Makefile.agent-check.snippet").unlink()
    again = _run_bootstrap("--profile", "L1", "--target", str(target))
    assert again.returncode == 0, again.stderr
    assert "SKIP (already present): agent-check target in Makefile" in again.stdout
    assert not (target / "Makefile.agent-check.snippet").exists()


def test_bootstrap_reads_but_never_writes_through_a_symlinked_makefile(tmp_path: Path) -> None:
    shared = tmp_path / "shared.mk"
    shared.write_text("build:\n\t@echo build\n", encoding="utf-8")
    target = tmp_path / "symlinked-makefile"
    _git_init(target)
    (target / "Makefile").symlink_to(shared)

    proc = _run_bootstrap("--profile", "L0", "--target", str(target), "--force")
    assert proc.returncode == 0, proc.stderr
    assert shared.read_text(encoding="utf-8") == "build:\n\t@echo build\n"
    assert (target / "Makefile").is_symlink()
    assert (target / "Makefile.agent-check.snippet").is_file()


def test_compliance_warns_when_documented_check_command_does_not_exist(tmp_path: Path) -> None:
    target = tmp_path / "l0-no-target"
    _git_init(target)
    (target / "Makefile").write_text("build:\n\t@echo build\n", encoding="utf-8")
    assert _run_bootstrap("--profile", "L0", "--target", str(target)).returncode == 0

    comp = _run_compliance("--profile", "L0", str(target))
    assert comp.returncode == 0, comp.stdout + comp.stderr
    assert "AGENTS.md names `make agent-check`" in comp.stderr


def test_compliance_without_profile_flag_says_which_profile_it_assumed(tmp_path: Path) -> None:
    target = tmp_path / "l0-default-profile"
    _git_init(target)
    assert _run_bootstrap("--profile", "L0", "--target", str(target)).returncode == 0

    comp = _run_compliance(str(target))
    assert comp.returncode == 1
    assert "no --profile given; checked against L1" in comp.stderr
    assert "--profile L0" in comp.stderr

    explicit = _run_compliance("--profile", "L1", str(target))
    assert explicit.returncode == 1
    assert "no --profile given" not in explicit.stderr


def test_bootstrap_ci_flag_installs_language_workflow_template(tmp_path: Path) -> None:
    for stack in ("python", "node-ts", "rust", "go", "java"):
        target = tmp_path / f"ci-{stack}"
        _git_init(target)
        proc = _run_bootstrap("--profile", "L1", "--target", str(target), "--ci", stack)
        assert proc.returncode == 0, proc.stderr
        installed = (target / ".github/workflows/candidate-gates.yml").read_text(encoding="utf-8")
        template = (REPO / "profiles/L1-team/workflows" / f"ci-{stack}.yml").read_text(encoding="utf-8")
        assert installed == template

    generic = tmp_path / "ci-generic"
    _git_init(generic)
    assert _run_bootstrap("--profile", "L1", "--target", str(generic)).returncode == 0
    assert "make agent-check" in (generic / ".github/workflows/candidate-gates.yml").read_text(encoding="utf-8")

    rejected = tmp_path / "ci-rejected"
    _git_init(rejected)
    bad_value = _run_bootstrap("--profile", "L1", "--target", str(rejected), "--ci", "cobol")
    assert bad_value.returncode == 1
    assert "--ci must be" in bad_value.stderr
    # L0 installs no CI workflow, so asking for one is an error rather than a silent no-op.
    l0_with_ci = _run_bootstrap("--profile", "L0", "--target", str(rejected), "--ci", "python")
    assert l0_with_ci.returncode == 1
    assert "--ci requires --profile L1 or L2" in l0_with_ci.stderr
    assert list(rejected.iterdir()) == [rejected / ".git"]


def test_bootstrap_reports_where_skills_were_installed(tmp_path: Path) -> None:
    target = tmp_path / "skills-repo"
    _git_init(target)
    default = _run_bootstrap("--profile", "L0", "--target", str(target), "--with-skills")
    assert default.returncode == 0, default.stderr
    assert "--skills-dir .claude/skills" in default.stdout

    claude = _run_bootstrap(
        "--profile", "L0", "--target", str(target), "--with-skills", "--skills-dir", ".claude/skills"
    )
    assert claude.returncode == 0, claude.stderr
    assert (target / ".claude/skills/secure-vibe-coding/SKILL.md").is_file()


def test_bootstrap_rejects_symlinks_empty_skills_dir_and_missing_flag_values(tmp_path: Path) -> None:
    outside = tmp_path / "outside-secret.txt"
    outside.write_text("do-not-touch\n", encoding="utf-8")

    # 1. Dangling symlink at destination
    t1 = tmp_path / "dangling"
    t1.mkdir()
    (t1 / "AGENTS.md").symlink_to(tmp_path / "outside-new.txt")
    res1 = _run_bootstrap("--target", str(t1))
    assert res1.returncode == 1
    assert "symlink" in res1.stderr
    assert not (tmp_path / "outside-new.txt").exists()

    # 2. Symlinked parent directory
    t2 = tmp_path / "symparent"
    t2.mkdir()
    outside_dir = tmp_path / "outside-dir"
    outside_dir.mkdir()
    (t2 / "docs").symlink_to(outside_dir)
    res2 = _run_bootstrap("--target", str(t2))
    assert res2.returncode == 1
    assert "symlink" in res2.stderr
    assert list(outside_dir.iterdir()) == []

    # 3. Symlinked .gitignore
    t3 = tmp_path / "symgitignore"
    t3.mkdir()
    (t3 / ".gitignore").symlink_to(outside)
    res3 = _run_bootstrap("--target", str(t3))
    assert res3.returncode == 1
    assert outside.read_text(encoding="utf-8") == "do-not-touch\n"

    # 4. Unsafe/empty --skills-dir, bad profile, missing option values
    t4 = tmp_path / "repo"
    t4.mkdir()
    assert _run_bootstrap("--target", str(t4), "--skills-dir", "../escape").returncode == 1
    assert _run_bootstrap("--target", str(t4), "--skills-dir", "").returncode == 1
    assert _run_bootstrap("--target", str(t4), "--profile", "L9").returncode == 1
    assert _run_bootstrap("--target").returncode == 1
    assert _run_bootstrap("--target", str(t4), "--profile").returncode == 1
