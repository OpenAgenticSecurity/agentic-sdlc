#!/usr/bin/env node
/**
 * Point a Git worktree's `node_modules` at a shared, lockfile-keyed install.
 *
 * Why: `NODE_PATH` does NOT work for Vite, `tsc`, or ESLint — they resolve
 * packages strictly from local `node_modules`. Installing `npm ci` inside
 * every Git worktree wastes gigabytes of disk and minutes per task.
 *
 * How it works:
 * - Computes a canonical SHA-256 key over `package-lock.json` locked packages
 *   (excluding the root package version so release bumps do not force reinstalls),
 *   `package.json` dependency fields, OS platform, CPU arch, and Node ABI.
 * - Installs once atomically (`npm ci`) into an external store outside the repo.
 * - Creates a real `node_modules/` in the worktree whose package entries symlink
 *   into that store, while keeping tool caches (`.vite`, `.cache`, `.tmp`,
 *   `.turbo`, `.next`) local per worktree.
 * - Copies `.package-lock.json` instead of symlinking it so `npm` never edits
 *   the shared store in place.
 * - Leaves any existing real `node_modules/` install untouched.
 *
 * Trust boundary & limitations:
 * - The shared store is a same-user disk/speed optimization across trusted
 *   worktrees, NOT an OS adversarial isolation boundary between agents.
 * - Pass `--ignore-scripts` to prevent dependency lifecycle scripts during
 *   `npm ci` (when packages do not require native postinstall build steps).
 * - Projects whose root `package.json` `postinstall`/`prepare` scripts read
 *   files outside `package.json`/`package-lock.json` cannot build inside the
 *   isolated store directory without `--ignore-scripts`.
 *
 * Usage:
 *   node scripts/link-shared-node-deps.mjs --project-dir ./frontend [--store-dir <dir>] [--ignore-scripts] [--dry-run]
 *
 * Store root precedence:
 *   1. --store-dir <dir>
 *   2. $SHARED_NODE_DEPS_STORE
 *   3. ${XDG_CACHE_HOME:-~/.cache}/shared-node-deps
 */
import { execFileSync } from 'node:child_process';
import { createHash } from 'node:crypto';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { parseArgs } from 'node:util';

const DEPENDENCY_FIELDS = [
  'dependencies',
  'devDependencies',
  'optionalDependencies',
  'peerDependencies',
  'peerDependenciesMeta',
  'bundleDependencies',
  'bundledDependencies',
  'overrides',
];
const LINKED_DOT_ENTRIES = new Set(['.bin']);
const INSTALL_RECORD = '.package-lock.json';
const STORE_COMPLETE_MARKER = '.store-complete';
const LOCAL_CACHE_ENTRIES = new Set(['.cache', '.tmp', '.vite', '.vite-temp', '.turbo', '.next']);

function canonical(value) {
  if (Array.isArray(value)) return value.map(canonical);
  if (value && typeof value === 'object') {
    return Object.fromEntries(
      Object.keys(value)
        .sort()
        .map((key) => [key, canonical(value[key])]),
    );
  }
  return value;
}

export function depsKey({ lockfileText, packageJsonText, platform, arch, abi }) {
  const lockfile = JSON.parse(lockfileText);
  const { '': _root, ...lockedPackages } = lockfile.packages ?? {};
  const manifest = JSON.parse(packageJsonText);
  const dependencyFields = Object.fromEntries(
    DEPENDENCY_FIELDS.filter((field) => field in manifest).map((field) => [field, manifest[field]]),
  );
  const hash = createHash('sha256');
  for (const part of [
    JSON.stringify(canonical({ lockfileVersion: lockfile.lockfileVersion, lockedPackages })),
    JSON.stringify(canonical(dependencyFields)),
    `${platform}-${arch}-abi${abi}`,
  ]) {
    hash.update(part);
    hash.update('\0');
  }
  return hash.digest('hex').slice(0, 16);
}

export function resolveStoreRoot(env, homedir, explicitStoreDir) {
  if (explicitStoreDir) return path.resolve(explicitStoreDir);
  if (env.SHARED_NODE_DEPS_STORE) return path.resolve(env.SHARED_NODE_DEPS_STORE);
  return path.join(env.XDG_CACHE_HOME || path.join(homedir, '.cache'), 'shared-node-deps');
}

function npmCi(buildDir, { ignoreScripts = false } = {}) {
  const args = ['ci', '--no-audit', '--no-fund'];
  if (ignoreScripts) args.push('--ignore-scripts');
  execFileSync('npm', args, {
    cwd: buildDir,
    stdio: 'inherit',
    env: { ...process.env, HUSKY: '0' },
  });
}

function isStoreComplete(storeDir) {
  const nodeModules = path.join(storeDir, 'node_modules');
  return (
    fs.existsSync(path.join(storeDir, STORE_COMPLETE_MARKER)) ||
    fs.existsSync(path.join(nodeModules, INSTALL_RECORD))
  );
}

function completeStore(storeDir) {
  const nodeModules = path.join(storeDir, 'node_modules');
  if (!isStoreComplete(storeDir)) {
    throw new Error(
      `Shared node deps store is incomplete: ${storeDir}. Delete that directory and rerun.`,
    );
  }
  fs.mkdirSync(nodeModules, { recursive: true });
  return nodeModules;
}

function lockTreeReadOnly(rootDir) {
  const stack = [rootDir];
  const dirs = [];
  while (stack.length > 0) {
    const current = stack.pop();
    const st = fs.lstatSync(current);
    if (st.isSymbolicLink()) continue;
    if (st.isDirectory()) {
      dirs.push(current);
      for (const entry of fs.readdirSync(current)) {
        stack.push(path.join(current, entry));
      }
    } else {
      fs.chmodSync(current, st.mode & ~0o222);
    }
  }
  for (let i = dirs.length - 1; i >= 0; i -= 1) {
    const st = fs.lstatSync(dirs[i]);
    fs.chmodSync(dirs[i], st.mode & ~0o222);
  }
}

export function ensureStore({
  storeRoot,
  key,
  projectDir,
  ignoreScripts = false,
  readOnlyStore = false,
  install = npmCi,
}) {
  const storeDir = path.join(storeRoot, key);
  if (fs.existsSync(storeDir)) {
    const existing = completeStore(storeDir);
    if (readOnlyStore) lockTreeReadOnly(storeDir);
    return existing;
  }

  fs.mkdirSync(storeRoot, { recursive: true });
  const buildDir = fs.mkdtempSync(path.join(storeRoot, `.build-${key}-`));
  try {
    for (const file of ['package.json', 'package-lock.json']) {
      fs.copyFileSync(path.join(projectDir, file), path.join(buildDir, file));
    }
    install(buildDir, { ignoreScripts });
    fs.mkdirSync(path.join(buildDir, 'node_modules'), { recursive: true });
    fs.writeFileSync(path.join(buildDir, STORE_COMPLETE_MARKER), 'ok\n');
    if (readOnlyStore) lockTreeReadOnly(buildDir);
    try {
      fs.renameSync(buildDir, storeDir);
    } catch (error) {
      if (error.code !== 'ENOTEMPTY' && error.code !== 'EEXIST') throw error;
    }
  } finally {
    if (fs.existsSync(buildDir)) {
      if (readOnlyStore) {
        // Restore write bit on temp dir only when cleaning up an aborted/raced build.
        fs.chmodSync(buildDir, 0o700);
      }
      fs.rmSync(buildDir, { recursive: true, force: true });
    }
  }
  return completeStore(storeDir);
}

function lstatOrNull(target) {
  try {
    return fs.lstatSync(target);
  } catch (error) {
    if (error.code === 'ENOENT') return null;
    throw error;
  }
}

function isRealInstall(nodeModules) {
  if (!lstatOrNull(nodeModules)?.isDirectory()) return false;
  return fs
    .readdirSync(nodeModules)
    .some(
      (entry) =>
        !LOCAL_CACHE_ENTRIES.has(entry) &&
        entry !== INSTALL_RECORD &&
        !fs.lstatSync(path.join(nodeModules, entry)).isSymbolicLink(),
    );
}

export function linkNodeModules({ projectDir, storeNodeModules }) {
  const nodeModules = path.join(projectDir, 'node_modules');
  if (isRealInstall(nodeModules)) return { status: 'kept-real-install', nodeModules };

  let replacedLegacyLink;
  const stat = lstatOrNull(nodeModules);
  if (stat?.isSymbolicLink()) {
    replacedLegacyLink = path.resolve(projectDir, fs.readlinkSync(nodeModules));
    fs.unlinkSync(nodeModules);
  } else if (stat) {
    for (const entry of fs.readdirSync(nodeModules)) {
      if (!LOCAL_CACHE_ENTRIES.has(entry)) {
        fs.rmSync(path.join(nodeModules, entry), { recursive: true, force: true });
      }
    }
  }
  fs.mkdirSync(nodeModules, { recursive: true });
  for (const entry of fs.readdirSync(storeNodeModules)) {
    const source = path.join(storeNodeModules, entry);
    const target = path.join(nodeModules, entry);
    if (entry === INSTALL_RECORD) fs.copyFileSync(source, target);
    else if (!entry.startsWith('.') || LINKED_DOT_ENTRIES.has(entry)) fs.symlinkSync(source, target);
  }
  return { status: 'linked', nodeModules, replacedLegacyLink };
}

function usageText() {
  return [
    'Usage: node scripts/link-shared-node-deps.mjs [options]',
    '',
    'Options:',
    '  --project-dir <dir>   Directory containing package.json & package-lock.json (default: cwd)',
    '  --frontend-dir <dir>  Alias for --project-dir',
    '  --store-dir <dir>     External shared store root (default: $SHARED_NODE_DEPS_STORE or ~/.cache/shared-node-deps)',
    '  --ignore-scripts      Pass --ignore-scripts to npm ci when building the store (recommended for untrusted lockfiles)',
    '  --read-only-store     Remove write bits on the finalized shared store to block cross-worktree tampering',
    '  --dry-run             Compute store key and print planned action without writing',
    '  -h, --help            Show this help message',
    '',
    'Trust boundary: share stores only across same-trust-domain local worktrees.',
    'Never share a writable store across mutually untrusted tasks or protected verifiers.',
  ].join('\n');
}

export function main(argv, { env = process.env, install, log = console.log } = {}) {
  const { values } = parseArgs({
    args: argv,
    options: {
      'project-dir': { type: 'string' },
      'frontend-dir': { type: 'string' },
      'store-dir': { type: 'string' },
      'ignore-scripts': { type: 'boolean', default: false },
      'read-only-store': { type: 'boolean', default: false },
      'dry-run': { type: 'boolean', default: false },
      help: { type: 'boolean', short: 'h', default: false },
    },
  });

  if (values.help) {
    log(usageText());
    return 0;
  }

  const projectDir = path.resolve(values['project-dir'] ?? values['frontend-dir'] ?? process.cwd());
  const pkgPath = path.join(projectDir, 'package.json');
  const lockPath = path.join(projectDir, 'package-lock.json');
  if (!fs.existsSync(pkgPath) || !fs.existsSync(lockPath)) {
    throw new Error(`Both package.json and package-lock.json are required in ${projectDir}`);
  }

  const nodeModules = path.join(projectDir, 'node_modules');
  if (isRealInstall(nodeModules)) {
    log(
      `${nodeModules} is a real npm install; left unchanged. ` +
        'Delete it and rerun to switch to the shared store.',
    );
    return 0;
  }

  const key = depsKey({
    lockfileText: fs.readFileSync(lockPath, 'utf8'),
    packageJsonText: fs.readFileSync(pkgPath, 'utf8'),
    platform: process.platform,
    arch: process.arch,
    abi: process.versions.modules,
  });
  const storeRoot = resolveStoreRoot(env, os.homedir(), values['store-dir']);
  const storeDir = path.join(storeRoot, key);

  if (values['dry-run']) {
    const exists = isStoreComplete(storeDir);
    log(`Dry-run: key=${key} store=${storeDir} (${exists ? 'cache-hit' : 'would-install'}) -> ${nodeModules}`);
    return 0;
  }

  const storeNodeModules = ensureStore({
    storeRoot,
    key,
    projectDir,
    ignoreScripts: values['ignore-scripts'],
    readOnlyStore: values['read-only-store'],
    install,
  });
  const result = linkNodeModules({ projectDir, storeNodeModules });
  if (result.replacedLegacyLink) {
    log(`Replaced whole-directory link to ${result.replacedLegacyLink} (target left untouched).`);
  }
  log(`Linked ${nodeModules} -> ${path.dirname(storeNodeModules)}`);
  return 0;
}

const isMain = process.argv[1] && fileURLToPath(import.meta.url) === path.resolve(process.argv[1]);
if (isMain) {
  try {
    process.exit(main(process.argv.slice(2)));
  } catch (error) {
    console.error(`link-shared-node-deps: ${error.message}`);
    process.exit(1);
  }
}
