from __future__ import annotations

import json
from pathlib import Path
import re

import yaml


REPO = Path(__file__).resolve().parents[1]


def test_excluded_internal_and_heavy_contract_artifacts_are_absent() -> None:
    for forbidden in (
        "contracts",
        "products",
        "architecture",
        "sales",
        "audits",
        "roadmap",
        "adr",
        "templates",
        "CHANGELOG.md",
        "INDEX.md",
        "INDEX.zh.md",
        "catalog.json",
    ):
        assert not (REPO / forbidden).exists(), f"excluded artifact must not exist: {forbidden}"
    for split_out in (
        "standards/ui-assurance",
        "standards/code-health",
        "tests/ui_assurance",
        "tests/code_health",
        "tests/assurance",
        "tests/architecture",
        "tests/uml",
        "docs/superpowers",
        "docs/reference",
        "docs/specs",
        "scripts/build-catalog.py",
        "scripts/check-ui-assurance.py",
        "scripts/check-code-health.py",
    ):
        assert not (REPO / split_out).exists(), f"split/excluded path must not exist in lean agentic-sdlc: {split_out}"


def test_bootstrap_guides_and_plugin_manifests_exist() -> None:
    for rel in ("BOOTSTRAP.md", "BOOTSTRAP.zh.md", "llms.txt", "scripts/bootstrap.sh"):
        assert (REPO / rel).is_file(), f"missing bootstrap/agent-native asset: {rel}"

    for rel in (
        ".claude-plugin/plugin.json",
        ".claude-plugin/marketplace.json",
        ".cursor-plugin/plugin.json",
        ".codex-plugin/plugin.json",
    ):
        path = REPO / rel
        assert path.is_file(), f"missing plugin manifest: {rel}"
        parsed = json.loads(path.read_text(encoding="utf-8"))
        assert isinstance(parsed, dict)
        if "skills" in parsed:
            assert parsed["skills"] == "./skills/"


def test_agents_and_claude_behavioral_parity() -> None:
    agents = (REPO / "AGENTS.md").read_text(encoding="utf-8")
    claude = (REPO / "CLAUDE.md").read_text(encoding="utf-8")
    for token in (
        "make check",
        "make verify-all",
        "standards/testing-strategy/**",
        "scripts/**",
        "skills/**",
        ".claude-plugin/**",
        ".cursor-plugin/**",
        ".codex-plugin/**",
        "llms.txt",
        "not self-attesting",
    ):
        assert token in agents, f"AGENTS.md missing {token!r}"
        assert token in claude, f"CLAUDE.md missing {token!r}"


def test_zero_personal_user_paths() -> None:
    user_path_re = re.compile(r"/Users/([A-Za-z0-9._-]+)")
    offenders: list[str] = []
    for path in sorted(REPO.rglob("*")):
        if not path.is_file() or path.is_symlink():
            continue
        rel = path.relative_to(REPO)
        if any(part in {"__pycache__", ".pytest_cache", ".git"} for part in rel.parts):
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        for match in user_path_re.finditer(text):
            if match.group(1) != "example":
                offenders.append(f"{rel.as_posix()}: {match.group(0)}")
    assert not offenders, "host-specific user paths found: " + "; ".join(offenders)


def test_empirical_checklists_and_done_claim_templates_exist() -> None:
    for rel in (
        "checklists/README.md",
        "checklists/README.zh.md",
        "checklists/vibe-coding-seven-sins.md",
        "checklists/vibe-coding-seven-sins.zh.md",
        "checklists/secure-vibe-coding-review.md",
        "checklists/secure-vibe-coding-review.zh.md",
        "checklists/multi-agent-git-gates.md",
        "checklists/multi-agent-git-gates.zh.md",
        "checklists/fake-done-dereference.md",
        "checklists/fake-done-dereference.zh.md",
        "checklists/frontend-vibe-coding-review.md",
        "checklists/frontend-vibe-coding-review.zh.md",
        "checklists/backend-performance-review.md",
        "checklists/backend-performance-review.zh.md",
        "checklists/agent-ops-and-workspace-hygiene.md",
        "checklists/agent-ops-and-workspace-hygiene.zh.md",
        "checklists/production-readiness-audit.md",
        "checklists/production-readiness-audit.zh.md",
        "checklists/done-claim.template.md",
        "checklists/done-claim.example.json",
        "checklists/handoff.template.md",
    ):
        assert (REPO / rel).is_file(), f"missing checklist/template asset: {rel}"
    assert (REPO / "scripts/link-shared-node-deps.mjs").is_file()

    done_claim = json.loads((REPO / "checklists/done-claim.example.json").read_text(encoding="utf-8"))
    for key in (
        "subject",
        "revision",
        "environment",
        "predicate",
        "evidence_locator",
        "independent_observer",
        "dereference_checks",
        "derived_status",
        "does_not_prove",
    ):
        assert key in done_claim, f"done-claim.example.json missing {key!r}"
    assert done_claim["does_not_prove"], "does_not_prove must be non-empty"


def test_progressive_profiles_and_five_standalone_skills_exist() -> None:
    for rel in (
        "profiles/L0-solo/README.md",
        "profiles/L0-solo/AGENTS.md",
        "profiles/L0-solo/CLAUDE.md",
        "profiles/L0-solo/STATUS.md",
        "profiles/L0-solo/VIBE_CODING_CONTEXT.md",
        "profiles/L0-solo/pull_request_template.md",
        "profiles/L0-solo/.gitignore.snippet",
        "profiles/L0-solo/Makefile.agent-check.snippet",
        "profiles/L1-team/README.md",
        "profiles/L1-team/ISSUE_TEMPLATE/config.yml",
        "profiles/L1-team/ISSUE_TEMPLATE/issue.md",
        "profiles/L1-team/ISSUE_TEMPLATE/epic.md",
        "profiles/L1-team/workflows/ci-python.yml",
        "profiles/L1-team/workflows/ci-node-ts.yml",
        "profiles/L1-team/workflows/ci-rust.yml",
        "profiles/L1-team/workflows/ci-go.yml",
        "profiles/L1-team/workflows/ci-java.yml",
        "profiles/L1-team/issue-claim.example.md",
        "profiles/L1-team/suite-catalog.example.json",
        "profiles/L1-team/candidate-gates.workflow.yml",
        "profiles/L2-governed/README.md",
        "profiles/L2-governed/CODEOWNERS.example",
        "profiles/L2-governed/github-ruleset.import.json",
        "profiles/L2-governed/ruleset-policy.example.json",
        "profiles/L2-governed/mechanism-review-checklist.md",
    ):
        assert (REPO / rel).is_file(), f"missing profile asset: {rel}"

    assert (REPO / ".github/dependabot.yml").is_file()
    issue_cfg = (REPO / ".github/ISSUE_TEMPLATE/config.yml").read_text(encoding="utf-8")
    assert "INDEX.md" not in issue_cfg

    contrib = (REPO / "CONTRIBUTING.md").read_text(encoding="utf-8")
    for stale in ("catalog.json", "catalog-generate", "architecture/policy", "check-ui-assurance.py"):
        assert stale not in contrib, f"stale reference {stale!r} in CONTRIBUTING.md"

    pr_template = (REPO / ".github/pull_request_template.md").read_text(encoding="utf-8")
    for stale in ("product-architecture", "architecture-core-test", "uml-test", "catalog.json", "ui-assurance-test"):
        assert stale not in pr_template, f"stale reference {stale!r} in .github/pull_request_template.md"

    expected_skills = {
        "bootstrap-agentic-sdlc",
        "secure-vibe-coding",
        "audit-pr-diff",
        "audit-production-readiness",
        "done-claim-verify",
        "multi-agent-git-flow",
    }
    actual_skills = {p.parent.name for p in (REPO / "skills").glob("*/SKILL.md")}
    assert actual_skills == expected_skills, f"expected 6 consolidated skills, found {actual_skills}"
    assert not (REPO / "projections").exists(), "redundant global projections/ directory must stay removed (use unified AGENTS.md + skills/)"

    for rel in (
        "skills/README.md",
        *[f"skills/{name}/SKILL.md" for name in sorted(expected_skills)],
    ):
        path = REPO / rel
        assert path.is_file(), f"missing projection/skill asset: {rel}"
        lower = path.read_text(encoding="utf-8").lower()
        assert "non-authoritative" in lower or "not authoritative" in lower, (
            f"{rel} must explicitly declare non-authoritative status"
        )

    for rel in ("standards/secure-vibe-coding.md", "standards/secure-vibe-coding.zh.md"):
        assert (REPO / rel).is_file(), f"missing secure vibe coding standard: {rel}"


def test_ci_workflows_security_and_non_self_attestation_contract() -> None:
    workflow_text = (REPO / ".github/workflows/ci.yml").read_text(encoding="utf-8")
    assert "candidate" in workflow_text.lower()
    assert "not self-attesting" in workflow_text
    assert "--require-hashes --only-binary=:all:" in workflow_text
    assert "persist-credentials: false" in workflow_text
    assert "github.event.pull_request.head.sha || github.sha" in workflow_text

    parsed = yaml.safe_load(workflow_text)
    assert isinstance(parsed, dict)
    jobs = parsed["jobs"]
    assert "verify-agentic-sdlc" in jobs
    for job_name, job in jobs.items():
        assert "timeout-minutes" in job, f"ci.yml/{job_name}: every job needs an explicit timeout"


OWN_WORKFLOWS = sorted((REPO / ".github/workflows").glob("*.yml"))
TEMPLATE_WORKFLOWS = [
    REPO / "profiles/L1-team/candidate-gates.workflow.yml",
    *sorted((REPO / "profiles/L1-team/workflows").glob("*.yml")),
]


def _workflow_steps(wf_path: Path):
    parsed = yaml.safe_load(wf_path.read_text(encoding="utf-8"))
    assert isinstance(parsed, dict), f"{wf_path}: workflow must be a YAML mapping"
    for job_name, job in parsed["jobs"].items():
        for step in job["steps"]:
            yield job_name, step


def test_every_shipped_workflow_pins_actions_to_full_commit_sha() -> None:
    assert {p.name for p in OWN_WORKFLOWS} >= {"ci.yml", "release.yml"}
    assert len(TEMPLATE_WORKFLOWS) == 6
    sha_pin_re = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_./-]+@[0-9a-f]{40}$")
    for wf_path in (*OWN_WORKFLOWS, *TEMPLATE_WORKFLOWS):
        for job_name, step in _workflow_steps(wf_path):
            if "uses" in step:
                assert sha_pin_re.fullmatch(step["uses"]), (
                    f"{wf_path.name}/{job_name}: action must be pinned to 40-char SHA: {step['uses']}"
                )


def test_own_workflows_only_call_existing_make_targets_and_input_files() -> None:
    makefile_text = (REPO / "Makefile").read_text(encoding="utf-8")
    make_target_re = re.compile(r"\bmake\s+([a-z0-9-]+)\b")
    # A repo-relative input file named in a run step. Redirect targets (`> file`)
    # and anything under dist/ are produced by the workflow itself.
    input_file_re = re.compile(r"(?<![\w./>-])(?<!> )([A-Za-z0-9_][\w./-]*\.(?:json|txt|toml|py|sh|mjs|md))\b")
    for wf_path in OWN_WORKFLOWS:
        for job_name, step in _workflow_steps(wf_path):
            run = step.get("run")
            if not isinstance(run, str):
                continue
            for match in make_target_re.finditer(run):
                target = match.group(1)
                assert re.search(rf"^{re.escape(target)}:", makefile_text, re.MULTILINE), (
                    f"{wf_path.name}/{job_name}: calls missing Makefile target {target!r}"
                )
            for match in input_file_re.finditer(run):
                rel = match.group(1)
                if rel.startswith("dist/"):
                    continue
                assert (REPO / rel).is_file(), (
                    f"{wf_path.name}/{job_name}: run step reads {rel!r}, which does not exist in the repository"
                )


def test_no_internal_workspace_branding_leaks_into_published_files() -> None:
    # Built by concatenation so this file does not match its own patterns.
    ws = "x" + "2"
    forbidden = re.compile(
        rf"(?i)(?<![A-Za-z0-9]){ws}(?![A-Za-z0-9])"
        + r"|\bx-(?:pul" + r"sar|neb" + r"ula|super" + r"nova|hori" + r"zon)\b"
        + r"|\bpul" + r"sar-"
        + r"|meta" + r"brain"
        + r"|agentica" + r"soc"
        + r"|\bbli" + r"nds\b"
        + r"|\bup-" + r"cli\b"
        + r"|@compet" + r"ition|@content-ser" + r"ies"
    )
    offenders: list[str] = []
    for path in sorted(REPO.rglob("*")):
        if not path.is_file() or path.is_symlink():
            continue
        rel = path.relative_to(REPO)
        if any(part in {"__pycache__", ".pytest_cache", ".ruff_cache", ".git"} for part in rel.parts):
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        for lineno, line in enumerate(text.splitlines(), start=1):
            hit = forbidden.search(line)
            if hit:
                offenders.append(f"{rel.as_posix()}:{lineno}: {hit.group(0)}")
    assert not offenders, "internal workspace branding found:\n" + "\n".join(offenders[:40])


WIRE_NAMESPACE = "openagenticsecurity."
SCHEMA_ID_BASE = "https://openagenticsecurity.github.io/schemas/"


def test_wire_contract_identifiers_share_one_public_namespace() -> None:
    schemas = sorted((REPO / "standards").rglob("*.schema.json"))
    assert len(schemas) == 2, [p.name for p in schemas]
    versions: set[str] = set()
    for schema_path in schemas:
        schema = json.loads(schema_path.read_text(encoding="utf-8"))
        assert schema["$id"].startswith(SCHEMA_ID_BASE), f"{schema_path.name}: $id {schema['$id']!r}"
        version = schema["properties"]["schema_version"]["const"]
        assert version.startswith(WIRE_NAMESPACE) and version.endswith(".v1"), f"{schema_path.name}: {version!r}"
        versions.add(version)
        # openagenticsecurity.<domain>.<slug>.v1  <->  <base><domain>/<slug>.v1.json
        domain, slug = version.removeprefix(WIRE_NAMESPACE).removesuffix(".v1").split(".", 1)
        assert schema["$id"] == f"{SCHEMA_ID_BASE}{domain}/{slug}.v1.json", (
            f"{schema_path.name}: $id {schema['$id']!r} does not match schema_version {version!r}"
        )

    # Every committed document and every producer uses an identifier from that namespace.
    seen: set[str] = set()
    version_re = re.compile(r'"schema_version"\s*:\s*"([^"]+)"')
    for path in sorted([*(REPO / "standards").rglob("*.json"), *(REPO / "profiles").rglob("*.json"), *(REPO / "scripts").glob("*.py")]):
        for value in version_re.findall(path.read_text(encoding="utf-8")):
            if value == "tampered":
                continue  # deliberate negative fixture
            assert value.startswith(WIRE_NAMESPACE), f"{path.relative_to(REPO)}: {value!r}"
            seen.add(value)
    assert versions <= seen, f"schema versions never used by a fixture or producer: {versions - seen}"


def test_llms_txt_stays_within_its_documented_budget() -> None:
    # README advertises llms.txt as a ~1K-token routing map; 4,000 bytes of
    # mostly-ASCII Markdown is a conservative ceiling for that.
    size = len((REPO / "llms.txt").read_bytes())
    assert size <= 4000, f"llms.txt is {size} bytes; keep the routing map within the documented ~1K-token budget"
    for rel in ("README.md", "README.zh.md"):
        text = (REPO / rel).read_text(encoding="utf-8")
        assert "<500" not in text, f"{rel} still advertises llms.txt as a <500-token file"
        assert "1K-token" in text, f"{rel} must state the llms.txt size budget"


def test_plugin_manifest_versions_agree() -> None:
    versions: dict[str, str] = {}
    for rel in (".claude-plugin/plugin.json", ".cursor-plugin/plugin.json", ".codex-plugin/plugin.json"):
        versions[rel] = json.loads((REPO / rel).read_text(encoding="utf-8"))["version"]
    marketplace = json.loads((REPO / ".claude-plugin/marketplace.json").read_text(encoding="utf-8"))
    for plugin in marketplace["plugins"]:
        versions[f".claude-plugin/marketplace.json#{plugin['name']}"] = plugin["version"]
    assert len(set(versions.values())) == 1, f"plugin manifest versions disagree: {versions}"
    version = next(iter(versions.values()))
    assert re.fullmatch(r"\d+\.\d+\.\d+", version), f"version must be plain SemVer: {version!r}"
    for rel in (
        "skills/README.md",
        "skills/README.zh.md",
    ):
        assert f"`v{version}`" in (REPO / rel).read_text(encoding="utf-8"), f"{rel} must reference v{version}"


def test_repository_does_not_declare_an_installable_python_package() -> None:
    # README promises "no CLI package to install": pyproject.toml carries tool
    # configuration only, and scripts/ are run in place.
    import tomllib

    pyproject = tomllib.loads((REPO / "pyproject.toml").read_text(encoding="utf-8"))
    assert "project" not in pyproject, "pyproject.toml must not declare an installable [project]"
    assert "build-system" not in pyproject, "pyproject.toml must not declare a [build-system]"


def test_issue_forms_are_valid_and_route_vulnerabilities_privately() -> None:
    template_dir = REPO / ".github/ISSUE_TEMPLATE"
    forms = sorted(p for p in template_dir.glob("*.yml") if p.name != "config.yml")
    assert {p.name for p in forms} == {"bug-report.yml", "proposal.yml"}
    for form in forms:
        parsed = yaml.safe_load(form.read_text(encoding="utf-8"))
        for key in ("name", "description", "body"):
            assert parsed.get(key), f"{form.name}: issue form needs {key!r}"
        ids = [item["id"] for item in parsed["body"] if "id" in item]
        assert len(ids) == len(set(ids)), f"{form.name}: duplicate field ids {ids}"
        for item in parsed["body"]:
            assert item["type"] in {"markdown", "textarea", "input", "dropdown", "checkboxes"}, item
            if item["type"] != "markdown":
                assert item["attributes"].get("label"), f"{form.name}: field {item.get('id')} needs a label"
        required = [
            item["id"]
            for item in parsed["body"]
            if item.get("validations", {}).get("required")
            or any(opt.get("required") for opt in item.get("attributes", {}).get("options", []) if isinstance(opt, dict))
        ]
        assert "no-secrets" in required, f"{form.name}: reporters must confirm the report contains no secrets"

    config = yaml.safe_load((template_dir / "config.yml").read_text(encoding="utf-8"))
    urls = [link["url"] for link in config["contact_links"]]
    assert any(url.endswith("/security/advisories/new") for url in urls), (
        "issue chooser must point vulnerability reports at private advisories"
    )
    assert any(url.endswith("/discussions") for url in urls), (
        "issue chooser must provide a GitHub Discussions link for adoption Q&A"
    )
    assert (REPO / "CODE_OF_CONDUCT.md").is_file(), "missing CODE_OF_CONDUCT.md"


def test_core_invariants_stay_aligned_across_standards_checklists_and_skills() -> None:
    # Standalone skills must stay self-contained for `npx skills add`, so this
    # test guards against silent drift between authoritative standards and skills.
    security_surfaces = (
        "standards/secure-vibe-coding.md",
        "checklists/secure-vibe-coding-review.md",
        "skills/secure-vibe-coding/SKILL.md",
        "skills/audit-pr-diff/SKILL.md",
    )
    for rel in security_surfaces:
        text = (REPO / rel).read_text(encoding="utf-8")
        for token in ("169.254.169.254", "hmac.compare_digest", "slopsquat"):
            assert token in text, f"{rel} drifted: missing core security invariant {token!r}"

    for rel in (
        "standards/testing-strategy.md",
        "checklists/fake-done-dereference.md",
        "skills/done-claim-verify/SKILL.md",
    ):
        text = (REPO / rel).read_text(encoding="utf-8")
        for token in ("NOT_RUN", "ERROR"):
            assert token in text, f"{rel} drifted: missing core verification invariant {token!r}"

    for rel in (
        "checklists/fake-done-dereference.md",
        "checklists/done-claim.template.md",
        "skills/done-claim-verify/SKILL.md",
    ):
        text = (REPO / rel).read_text(encoding="utf-8")
        assert "does_not_prove" in text, f"{rel} drifted: missing 'does_not_prove'"


def test_bilingual_standards_and_checklists_keep_structural_parity() -> None:
    def heading_count(path: Path) -> int:
        text = path.read_text(encoding="utf-8")
        body = re.sub(r"```.*?```", "", text, flags=re.S)
        return len(re.findall(r"^#{1,6} ", body, re.M))

    pairs = 0
    for directory in ("standards", "checklists"):
        for en in sorted((REPO / directory).rglob("*.md")):
            if en.name.endswith(".zh.md"):
                continue
            zh = en.with_name(en.name[:-3] + ".zh.md")
            if not zh.exists():
                continue
            pairs += 1
            assert heading_count(en) == heading_count(zh), (
                f"bilingual heading drift between {en.relative_to(REPO)} ({heading_count(en)}) "
                f"and {zh.relative_to(REPO)} ({heading_count(zh)})"
            )
    assert pairs >= 18, f"expected >=18 bilingual standards/checklists pairs, found {pairs}"

    for pair_base in ("docs/empirical-findings", "docs/workflow-integration", "examples/README", "evals/README"):
        en = REPO / f"{pair_base}.md"
        zh = REPO / f"{pair_base}.zh.md"
        assert en.is_file() and zh.is_file(), f"missing bilingual pair: {pair_base}"
        assert heading_count(en) == heading_count(zh), (
            f"bilingual heading drift between {en.relative_to(REPO)} ({heading_count(en)}) "
            f"and {zh.relative_to(REPO)} ({heading_count(zh)})"
        )


def test_text_files_have_no_trailing_whitespace_or_eof_blank_lines() -> None:
    # `git diff --check` is part of the L1 CI baseline we ship; our own templates,
    # checklists, docs, and tests must never fail it.
    offenders: list[str] = []
    for path in sorted(REPO.rglob("*")):
        if not path.is_file() or path.is_symlink():
            continue
        rel = path.relative_to(REPO)
        if any(part in {"__pycache__", ".pytest_cache", ".ruff_cache", ".git"} for part in rel.parts):
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        if not text:
            continue
        if not text.endswith("\n"):
            offenders.append(f"{rel.as_posix()}: missing trailing newline")
        if text.endswith("\n\n"):
            offenders.append(f"{rel.as_posix()}: trailing blank line at EOF")
        for lineno, line in enumerate(text.splitlines(), start=1):
            if line.endswith((" ", "\t")):
                offenders.append(f"{rel.as_posix()}:{lineno}: trailing whitespace")
    assert not offenders, "whitespace errors (would fail `git diff --check`):\n" + "\n".join(offenders[:30])


def test_shebang_scripts_are_executable() -> None:
    import os

    non_exec = []
    for path in sorted((REPO / "scripts").iterdir()):
        if not path.is_file():
            continue
        if path.read_bytes().startswith(b"#!") and not os.access(path, os.X_OK):
            non_exec.append(path.relative_to(REPO).as_posix())
    assert not non_exec, f"shebang scripts missing executable bit: {non_exec}"


def test_release_provenance_scorecard_and_release_notes_config() -> None:
    release_cfg = yaml.safe_load((REPO / ".github/release.yml").read_text(encoding="utf-8"))
    assert isinstance(release_cfg, dict)
    assert release_cfg.get("changelog", {}).get("categories"), ".github/release.yml must define changelog categories"

    release_wf = yaml.safe_load((REPO / ".github/workflows/release.yml").read_text(encoding="utf-8"))
    job = release_wf["jobs"]["verify-and-release"]
    assert job["permissions"].get("id-token") == "write"
    assert job["permissions"].get("attestations") == "write"
    uses = [step.get("uses", "") for step in job["steps"]]
    assert any(u.startswith("actions/attest-build-provenance@") for u in uses), (
        "release.yml must attest build provenance for release artifacts"
    )

    scorecard_path = REPO / ".github/workflows/scorecard.yml"
    assert scorecard_path.is_file(), "missing .github/workflows/scorecard.yml"
    scorecard_wf = yaml.safe_load(scorecard_path.read_text(encoding="utf-8"))
    sc_steps = [
        step
        for j in scorecard_wf["jobs"].values()
        for step in j["steps"]
    ]
    assert any(str(s.get("uses", "")).startswith("ossf/scorecard-action@") for s in sc_steps)
    checkout_steps = [s for s in sc_steps if str(s.get("uses", "")).startswith("actions/checkout@")]
    assert checkout_steps and all(s.get("with", {}).get("persist-credentials") is False for s in checkout_steps)
