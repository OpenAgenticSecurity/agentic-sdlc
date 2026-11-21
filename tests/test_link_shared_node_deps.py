from __future__ import annotations

import json
from pathlib import Path
import shutil
import subprocess

import pytest


REPO = Path(__file__).resolve().parents[1]
SCRIPT = REPO / "scripts" / "link-shared-node-deps.mjs"
NODE = shutil.which("node")


def _write_pkg(project_dir: Path, *, version: str = "1.0.0", dep_ver: str = "1.0.0") -> None:
    project_dir.mkdir(parents=True, exist_ok=True)
    (project_dir / "package.json").write_text(
        json.dumps(
            {
                "name": "demo-app",
                "version": version,
                "dependencies": {"demo-pkg": dep_ver},
            }
        )
        + "\n",
        encoding="utf-8",
    )
    (project_dir / "package-lock.json").write_text(
        json.dumps(
            {
                "name": "demo-app",
                "version": version,
                "lockfileVersion": 3,
                "packages": {
                    "": {"name": "demo-app", "version": version},
                    "node_modules/demo-pkg": {"version": dep_ver},
                },
            }
        )
        + "\n",
        encoding="utf-8",
    )


@pytest.mark.skipif(NODE is None, reason="node runtime not available")
def test_link_shared_node_deps_dry_run_and_missing_lockfile(tmp_path: Path) -> None:
    assert NODE is not None
    project = tmp_path / "app"
    _write_pkg(project)
    store = tmp_path / "store"

    dry = subprocess.run(
        [NODE, str(SCRIPT), "--project-dir", str(project), "--store-dir", str(store), "--dry-run"],
        text=True,
        capture_output=True,
        check=False,
    )
    assert dry.returncode == 0, dry.stderr
    assert "Dry-run: key=" in dry.stdout
    assert "would-install" in dry.stdout
    assert not (project / "node_modules").exists()

    empty = tmp_path / "empty"
    empty.mkdir()
    missing = subprocess.run(
        [NODE, str(SCRIPT), "--project-dir", str(empty), "--store-dir", str(store)],
        text=True,
        capture_output=True,
        check=False,
    )
    assert missing.returncode == 1
    assert "package-lock.json" in missing.stderr


@pytest.mark.skipif(NODE is None, reason="node runtime not available")
def test_link_shared_node_deps_links_entries_copies_lock_and_preserves_local_cache(tmp_path: Path) -> None:
    assert NODE is not None
    wt_a = tmp_path / "wt-a"
    wt_b = tmp_path / "wt-b"
    # Distinct root versions (1.0.0 vs 2.0.0) with identical locked deps must share the exact same store key
    _write_pkg(wt_a, version="1.0.0")
    _write_pkg(wt_b, version="2.0.0")
    # Pre-existing local .vite cache inside wt_a must survive linking
    vite_cache = wt_a / "node_modules" / ".vite"
    vite_cache.mkdir(parents=True)
    (vite_cache / "marker.txt").write_text("keep-local\n", encoding="utf-8")

    store = tmp_path / "store"
    js_driver = f"""
import fs from 'node:fs';
import path from 'node:path';
import {{ pathToFileURL }} from 'node:url';
const mod = await import({json.dumps(SCRIPT.as_uri())});

let installCalls = 0;
function fakeInstall(buildDir) {{
  installCalls += 1;
  const nm = path.join(buildDir, 'node_modules');
  fs.mkdirSync(path.join(nm, 'demo-pkg'), {{ recursive: true }});
  fs.mkdirSync(path.join(nm, '.bin'), {{ recursive: true }});
  fs.writeFileSync(path.join(nm, 'demo-pkg', 'index.js'), 'export const ok = true;\\n');
  fs.writeFileSync(path.join(nm, '.bin', 'demo'), '#!/bin/sh\\n');
  fs.writeFileSync(path.join(nm, '.package-lock.json'), '{{"lockfileVersion":3}}\\n');
}}

const rc1 = mod.main(['--project-dir', {json.dumps(str(wt_a))}, '--store-dir', {json.dumps(str(store))}], {{ install: fakeInstall, log: () => {{}} }});
const rc2 = mod.main(['--project-dir', {json.dumps(str(wt_b))}, '--store-dir', {json.dumps(str(store))}], {{ install: fakeInstall, log: () => {{}} }});
console.log(JSON.stringify({{ rc1, rc2, installCalls }}));
"""
    proc = subprocess.run(
        [NODE, "--input-type=module", "-e", js_driver],
        text=True,
        capture_output=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr
    result = json.loads(proc.stdout.strip())
    assert result == {"rc1": 0, "rc2": 0, "installCalls": 1}

    # Package entries are symlinks into store; .package-lock.json is copied (NOT a symlink); .vite cache survived
    assert (wt_a / "node_modules" / "demo-pkg").is_symlink()
    assert (wt_a / "node_modules" / ".bin").is_symlink()
    assert (wt_a / "node_modules" / ".package-lock.json").is_file()
    assert not (wt_a / "node_modules" / ".package-lock.json").is_symlink()
    assert (wt_a / "node_modules" / ".vite" / "marker.txt").read_text(encoding="utf-8") == "keep-local\n"
    assert (wt_b / "node_modules" / "demo-pkg").is_symlink()
    assert not (wt_b / "node_modules" / ".package-lock.json").is_symlink()

    # Real npm install must never be clobbered
    real_repo = tmp_path / "real-install"
    _write_pkg(real_repo)
    (real_repo / "node_modules" / "demo-pkg").mkdir(parents=True)
    (real_repo / "node_modules" / "demo-pkg" / "local.txt").write_text("real\n", encoding="utf-8")
    keep = subprocess.run(
        [NODE, str(SCRIPT), "--project-dir", str(real_repo), "--store-dir", str(store)],
        text=True,
        capture_output=True,
        check=False,
    )
    assert keep.returncode == 0, keep.stderr
    assert "left unchanged" in keep.stdout
    assert not (real_repo / "node_modules" / "demo-pkg").is_symlink()


@pytest.mark.skipif(NODE is None, reason="node runtime not available")
def test_link_shared_node_deps_handles_zero_dependencies_and_ignore_scripts_flag(tmp_path: Path) -> None:
    assert NODE is not None
    zero = tmp_path / "zero-deps"
    zero.mkdir()
    (zero / "package.json").write_text(json.dumps({"name": "zero", "version": "1.0.0"}) + "\n", encoding="utf-8")
    (zero / "package-lock.json").write_text(
        json.dumps({"name": "zero", "version": "1.0.0", "lockfileVersion": 3, "packages": {"": {"name": "zero", "version": "1.0.0"}}})
        + "\n",
        encoding="utf-8",
    )
    store = tmp_path / "store"
    js_driver = f"""
import {{ pathToFileURL }} from 'node:url';
const mod = await import({json.dumps(SCRIPT.as_uri())});

const seenFlags = [];
function zeroInstall(_buildDir, opts) {{
  seenFlags.push(Boolean(opts?.ignoreScripts));
  // Real `npm ci` on a zero-dependency project succeeds without creating node_modules/.package-lock.json
}}

const rc1 = mod.main(
  ['--project-dir', {json.dumps(str(zero))}, '--store-dir', {json.dumps(str(store))}, '--ignore-scripts'],
  {{ install: zeroInstall, log: () => {{}} }},
);
const rc2 = mod.main(
  ['--project-dir', {json.dumps(str(zero))}, '--store-dir', {json.dumps(str(store))}],
  {{ install: zeroInstall, log: () => {{}} }},
);
console.log(JSON.stringify({{ rc1, rc2, seenFlags }}));
"""
    proc = subprocess.run(
        [NODE, "--input-type=module", "-e", js_driver],
        text=True,
        capture_output=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr
    assert json.loads(proc.stdout.strip()) == {"rc1": 0, "rc2": 0, "seenFlags": [True]}
    assert (zero / "node_modules").is_dir()


@pytest.mark.skipif(NODE is None, reason="node runtime not available")
def test_read_only_store_blocks_cross_worktree_tampering(tmp_path: Path) -> None:
    assert NODE is not None
    import os

    if hasattr(os, "geteuid") and os.geteuid() == 0:
        pytest.skip("root ignores POSIX read-only file modes")

    wt = tmp_path / "wt-ro"
    _write_pkg(wt)
    store = tmp_path / "ro-store"
    js_driver = f"""
import fs from 'node:fs';
import path from 'node:path';
const mod = await import({json.dumps(SCRIPT.as_uri())});

function fakeInstall(buildDir) {{
  const nm = path.join(buildDir, 'node_modules');
  fs.mkdirSync(path.join(nm, 'demo-pkg'), {{ recursive: true }});
  fs.writeFileSync(path.join(nm, 'demo-pkg', 'index.js'), 'export const ok = true;\\n');
}}

const rc = mod.main(
  ['--project-dir', {json.dumps(str(wt))}, '--store-dir', {json.dumps(str(store))}, '--read-only-store'],
  {{ install: fakeInstall, log: () => {{}} }},
);
console.log(JSON.stringify({{ rc }}));
"""
    try:
        proc = subprocess.run(
            [NODE, "--input-type=module", "-e", js_driver],
            text=True,
            capture_output=True,
            check=False,
        )
        assert proc.returncode == 0, proc.stderr
        assert json.loads(proc.stdout.strip()) == {"rc": 0}

        linked_file = wt / "node_modules" / "demo-pkg" / "index.js"
        assert linked_file.is_file()
        with pytest.raises(PermissionError):
            linked_file.write_text("tampered\n", encoding="utf-8")
    finally:
        # Restore write bits so pytest tmp_path teardown can remove the store cleanly.
        for path in sorted(store.rglob("*"), reverse=True):
            if not path.is_symlink():
                path.chmod(0o700 if path.is_dir() else 0o600)
        if store.exists():
            store.chmod(0o700)
