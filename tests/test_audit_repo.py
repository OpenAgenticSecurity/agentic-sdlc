from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys


REPO = Path(__file__).resolve().parents[1]
AUDIT = REPO / "scripts" / "audit-repo.py"
STRONG_RULESET = REPO / "profiles" / "L2-governed" / "github-ruleset.import.json"


def _run_audit(*args: str, isolated: bool = False) -> subprocess.CompletedProcess[str]:
    cmd = [sys.executable]
    if isolated:
        cmd.append("-S")
    cmd.extend([str(AUDIT), *args])
    return subprocess.run(
        cmd,
        cwd=REPO,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )


def _write_clean_repo(root: Path) -> None:
    (root / "AGENTS.md").write_text("# AGENTS\nRun make agent-check.\n", encoding="utf-8")
    (root / "CLAUDE.md").write_text("# CLAUDE\nSee AGENTS.md.\n", encoding="utf-8")
    (root / ".gitignore").write_text(
        ".worktrees/\n.claude/worktrees/\n.cursor/worktrees/\n.codex/worktrees/\n",
        encoding="utf-8",
    )
    (root / "docs/architecture").mkdir(parents=True)
    (root / "docs/architecture/STATUS.md").write_text("# Status\n", encoding="utf-8")
    (root / ".github/workflows").mkdir(parents=True)
    (root / ".github/pull_request_template.md").write_text(
        "## Verification\n- exact command and exit code\n",
        encoding="utf-8",
    )
    (root / ".github/CODEOWNERS").write_text("* @acme/security-maintainers\n", encoding="utf-8")
    (root / ".github/workflows/ci.yml").write_text(
        "name: CI\n"
        "on: [pull_request]\n"
        "permissions:\n"
        "  contents: read\n"
        "jobs:\n"
        "  test:\n"
        "    runs-on: ubuntu-24.04\n"
        "    timeout-minutes: 10\n"
        "    steps:\n"
        "      - uses: actions/checkout@11bd71901bbe5b1630ceea73d27597364c9af683\n"
        "        with:\n"
        "          persist-credentials: false\n"
        "      - run: echo ok\n",
        encoding="utf-8",
    )
    (root / "src").mkdir()
    (root / "src/app.py").write_text(
        "import os\n\n\ndef read_setting() -> str:\n    return os.getenv('APP_MODE', 'strict')\n",
        encoding="utf-8",
    )


def test_audit_repo_runs_pure_stdlib_isolated_on_self() -> None:
    # Must work under `python3 -S` (no third-party packages) and report zero FAILs on this repo.
    proc = _run_audit(str(REPO), "--format", "json", isolated=True)
    assert proc.returncode == 0, proc.stderr
    report = json.loads(proc.stdout)
    assert report["schema_version"] == "openagenticsecurity.audit.repo-self-check.v1"
    assert report["authority"] == "candidate"
    assert report["trusted"] is False
    assert report["counts"]["FAIL"] == 0
    assert report["counts"]["NOT_RUN"] == 1
    assert report["derived_status"] == "PARTIAL"
    assert report["does_not_prove"], "does_not_prove must be non-empty"


def test_clean_repo_with_strong_ruleset_passes_all_layers(tmp_path: Path) -> None:
    _write_clean_repo(tmp_path)
    proc = _run_audit(
        str(tmp_path),
        "--github-ruleset-file",
        str(STRONG_RULESET),
        "--format",
        "json",
        isolated=True,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    report = json.loads(proc.stdout)
    assert report["derived_status"] == "PASS"
    assert report["counts"]["FAIL"] == 0
    assert report["counts"]["NOT_RUN"] == 0


def test_catches_unpinned_action_missing_permissions_and_persist_credentials(tmp_path: Path) -> None:
    _write_clean_repo(tmp_path)
    (tmp_path / ".github/workflows/ci.yml").write_text(
        "name: Unsafe CI\n"
        "on: [pull_request]\n"
        "jobs:\n"
        "  test:\n"
        "    runs-on: ubuntu-24.04\n"
        "    steps:\n"
        "      - uses: actions/checkout@v4\n"
        "      - run: echo ok\n",
        encoding="utf-8",
    )
    proc = _run_audit(str(tmp_path), "--format", "json")
    assert proc.returncode == 2, proc.stdout + proc.stderr
    by_rule = {item["rule_id"]: item for item in json.loads(proc.stdout)["findings"]}
    assert by_rule["OAS-CI-01"]["status"] == "FAIL"
    assert "actions/checkout@v4" in by_rule["OAS-CI-01"]["detail"]
    assert by_rule["OAS-CI-02"]["status"] == "FAIL"
    assert "permissions" in by_rule["OAS-CI-02"]["detail"]
    assert "persist-credentials: false" in by_rule["OAS-CI-02"]["detail"]
    assert by_rule["OAS-CI-03"]["status"] == "WARN"


def test_catches_all_six_python_ast_security_traps_and_ignores_tests(tmp_path: Path) -> None:
    _write_clean_repo(tmp_path)
    (tmp_path / "src/bad.py").write_text(
        "import os\n"
        "import pickle\n"
        "import subprocess\n"
        "import yaml\n\n"
        "SECRET = os.getenv('JWT_SECRET_KEY', 'dev-fallback')\n\n"
        "def bad(x, client):\n"
        "    try:\n"
        "        subprocess.run(x, shell=True)\n"
        "    except Exception:\n"
        "        pass\n"
        "    eval(x)\n"
        "    client.get('https://example.com', verify=False)\n"
        "    yaml.load(x)\n"
        "    pickle.loads(b'')\n",
        encoding="utf-8",
    )
    # Planted patterns inside tests/ must not trigger production source findings.
    (tmp_path / "tests").mkdir()
    (tmp_path / "tests/test_sample.py").write_text("eval('1+1')\n", encoding="utf-8")

    proc = _run_audit(str(tmp_path), "--format", "json")
    assert proc.returncode == 2, proc.stdout + proc.stderr
    by_rule = {item["rule_id"]: item for item in json.loads(proc.stdout)["findings"]}
    for rule_id in (
        "OAS-SVC-01",
        "OAS-SVC-02",
        "OAS-SVC-03",
        "OAS-SVC-04",
        "OAS-SVC-05",
        "OAS-SVC-06",
    ):
        assert by_rule[rule_id]["status"] == "FAIL", f"expected {rule_id} to FAIL: {by_rule}"
        assert "tests/test_sample.py" not in by_rule[rule_id]["detail"]


def test_catches_codeowners_placeholder_and_missing_context(tmp_path: Path) -> None:
    (tmp_path / ".github").mkdir()
    (tmp_path / ".github/CODEOWNERS").write_text("* @org/security\n", encoding="utf-8")
    proc = _run_audit(str(tmp_path), "--format", "json")
    assert proc.returncode == 2
    by_rule = {item["rule_id"]: item for item in json.loads(proc.stdout)["findings"]}
    assert by_rule["OAS-CTX-01"]["status"] == "FAIL"
    assert by_rule["OAS-CTX-02"]["status"] == "FAIL"
    assert by_rule["OAS-CI-04"]["status"] == "FAIL"


def test_catches_weak_github_ruleset_vulnerabilities(tmp_path: Path) -> None:
    _write_clean_repo(tmp_path)
    weak = {
        "id": 77,
        "name": "Weak main ruleset",
        "target": "branch",
        "enforcement": "active",
        "conditions": {"ref_name": {"include": ["~DEFAULT_BRANCH"], "exclude": []}},
        "bypass_actors": [{"actor_id": 5, "actor_type": "RepositoryRole", "bypass_mode": "always"}],
        "rules": [
            {
                "type": "pull_request",
                "parameters": {
                    "required_approving_review_count": 1,
                    "require_code_owner_review": False,
                    "dismiss_stale_reviews_on_push": True,
                    "require_last_push_approval": False,
                },
            },
            {
                "type": "required_status_checks",
                "parameters": {
                    "required_status_checks": [{"context": "agent-check", "integration_id": None}]
                },
            },
        ],
    }
    rs_file = tmp_path / "weak-ruleset.json"
    rs_file.write_text(json.dumps(weak), encoding="utf-8")

    proc = _run_audit(str(tmp_path), "--github-ruleset-file", str(rs_file), "--format", "json")
    assert proc.returncode == 2, proc.stdout + proc.stderr
    by_rule = {item["rule_id"]: item for item in json.loads(proc.stdout)["findings"]}
    assert by_rule["OAS-GH-01"]["status"] == "PASS"
    assert by_rule["OAS-GH-02"]["status"] == "FAIL"
    assert by_rule["OAS-GH-03"]["status"] == "FAIL"
    assert by_rule["OAS-GH-04"]["status"] == "FAIL"
    assert by_rule["OAS-GH-05"]["status"] == "FAIL"


def test_empty_rulesets_fails_closed_on_layer3(tmp_path: Path) -> None:
    _write_clean_repo(tmp_path)
    rs_file = tmp_path / "empty.json"
    rs_file.write_text("[]\n", encoding="utf-8")

    proc = _run_audit(str(tmp_path), "--github-ruleset-file", str(rs_file), "--format", "json")
    assert proc.returncode == 2
    by_rule = {item["rule_id"]: item for item in json.loads(proc.stdout)["findings"]}
    assert by_rule["OAS-GH-01"]["status"] == "FAIL"


def test_rejects_symlink_target_and_duplicate_json_keys(tmp_path: Path) -> None:
    real_dir = tmp_path / "real"
    real_dir.mkdir()
    sym_dir = tmp_path / "sym"
    sym_dir.symlink_to(real_dir)
    p1 = _run_audit(str(sym_dir))
    assert p1.returncode == 1
    assert "non-symlink directory" in p1.stderr

    _write_clean_repo(real_dir)
    dup_file = tmp_path / "dup.json"
    dup_file.write_text('{"id": 1, "id": 2}', encoding="utf-8")
    p2 = _run_audit(str(real_dir), "--github-ruleset-file", str(dup_file))
    assert p2.returncode == 1
    assert "duplicate JSON key" in p2.stderr


def test_github_mode_fails_closed_not_run_when_gh_missing(tmp_path: Path) -> None:
    _write_clean_repo(tmp_path)
    proc = _run_audit(
        str(tmp_path),
        "--github",
        "--repo",
        "OpenAgenticSecurity/agentic-sdlc",
        "--gh-bin",
        "nonexistent-gh-binary-for-audit-test",
    )
    assert proc.returncode == 1
    assert "NOT_RUN" in proc.stderr


def test_catches_js_ts_go_rust_and_java_security_and_gate_traps(tmp_path: Path) -> None:
    _write_clean_repo(tmp_path)
    (tmp_path / "package.json").write_text(
        json.dumps({"name": "demo", "scripts": {"test": "vitest run --passWithNoTests"}}),
        encoding="utf-8",
    )
    (tmp_path / "tsconfig.json").write_text('{"compilerOptions": {"target": "ES2022"}}\n', encoding="utf-8")
    (tmp_path / "src/view.tsx").write_text(
        "// eval('comment-ignored')\nexport const x = <div dangerouslySetInnerHTML={{ __html: user }} />;\n",
        encoding="utf-8",
    )
    (tmp_path / "src/main.go").write_text(
        'package main\nvar tlsCfg = &tls.Config{InsecureSkipVerify: true}\n'
        'func run(x string) { exec.Command("sh", "-c", x) }\n',
        encoding="utf-8",
    )
    (tmp_path / "src/lib.rs").write_text(
        'fn bad() { let _ = Client::builder().danger_accept_invalid_certs(true); Command::new("sh").arg("-c"); }\n',
        encoding="utf-8",
    )
    (tmp_path / "src/App.java").write_text(
        "class App { void f(String c) throws Exception { Runtime.getRuntime().exec(c); new ObjectInputStream(null); } }\n",
        encoding="utf-8",
    )
    # Test files must not trigger production source findings.
    (tmp_path / "src/view.spec.tsx").write_text("eval('ok')\n", encoding="utf-8")
    (tmp_path / "src/main_test.go").write_text("var c = &tls.Config{InsecureSkipVerify: true}\n", encoding="utf-8")

    proc = _run_audit(str(tmp_path), "--format", "json", isolated=True)
    assert proc.returncode == 2, proc.stdout + proc.stderr
    by_rule = {item["rule_id"]: item for item in json.loads(proc.stdout)["findings"]}
    assert by_rule["OAS-JS-01"]["status"] == "FAIL"
    assert "view.spec.tsx" not in by_rule["OAS-JS-01"]["detail"]
    assert by_rule["OAS-JS-02"]["status"] == "FAIL"
    assert by_rule["OAS-JS-03"]["status"] == "WARN"
    assert by_rule["OAS-GO-01"]["status"] == "FAIL"
    assert "main_test.go" not in by_rule["OAS-GO-01"]["detail"]
    assert by_rule["OAS-RS-01"]["status"] == "FAIL"
    assert by_rule["OAS-JV-01"]["status"] == "FAIL"


def test_clean_polyglot_repo_passes_all_language_scans(tmp_path: Path) -> None:
    _write_clean_repo(tmp_path)
    (tmp_path / "package.json").write_text(
        json.dumps({"name": "demo", "scripts": {"test": "vitest run"}}),
        encoding="utf-8",
    )
    (tmp_path / "tsconfig.json").write_text('{"compilerOptions": {"strict": true}}\n', encoding="utf-8")
    (tmp_path / "src/view.tsx").write_text("export const View = () => <p>safe</p>;\n", encoding="utf-8")
    (tmp_path / "src/main.go").write_text('package main\nfunc main() {}\n', encoding="utf-8")
    (tmp_path / "src/lib.rs").write_text("pub fn add(a: i32, b: i32) -> i32 { a + b }\n", encoding="utf-8")
    (tmp_path / "src/App.java").write_text("class App { int add(int a, int b) { return a + b; } }\n", encoding="utf-8")

    proc = _run_audit(str(tmp_path), "--format", "json", isolated=True)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    by_rule = {item["rule_id"]: item for item in json.loads(proc.stdout)["findings"]}
    for rule_id in ("OAS-SVC-00", "OAS-JS-00", "OAS-GO-00", "OAS-RS-00", "OAS-JV-00"):
        assert by_rule[rule_id]["status"] == "PASS", f"expected {rule_id} PASS: {by_rule}"
