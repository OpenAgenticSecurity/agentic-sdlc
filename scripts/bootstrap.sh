#!/usr/bin/env bash
# Zero-dependency bootstrap helper for adopting OpenAgenticSecurity/agentic-sdlc
# into an existing repository. Safe by default: never overwrites existing files
# unless --force is explicitly passed, and rejects symlink escapes.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd -P)"

PROFILE="L0"
TARGET=""
WITH_SKILLS=0
WITH_CHECKLISTS=0
SKILLS_DIR=".agents/skills"
SKILLS_DIR_SET=0
CI_TEMPLATE=""
DRY_RUN=0
FORCE=0

usage() {
  cat <<'EOF'
Usage: bootstrap.sh --target <repo-dir> [options]

Options:
  --target <dir>       Target repository directory (required)
  --profile <L0|L1|L2> Adoption profile (cumulative; default: L0)
  --ci <template>      L1/L2 CI workflow installed as .github/workflows/candidate-gates.yml:
                       generic (default; runs `make agent-check`), python, node-ts, rust, go, or java
  --with-skills        Install 6 Agent Skills into --skills-dir (default: .agents/skills)
  --skills-dir <rel>   Relative directory for skills: .agents/skills (Codex and the
                       cross-agent convention), .claude/skills (Claude Code), or
                       .cursor/skills (Cursor)
  --with-checklists    Copy empirical & security checklists into docs/checklists/
  --dry-run            Print planned changes without writing files
  --force              Overwrite files this script installs (default: skip existing files).
                       An existing Makefile is never modified.
  -h, --help           Show this help message
EOF
}

require_value() {
  local opt="$1"
  local argc="$2"
  if [[ "$argc" -lt 2 ]]; then
    echo "bootstrap.sh error: $opt requires a value" >&2
    usage >&2
    exit 1
  fi
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --target)
      require_value "$1" "$#"
      TARGET="$2"
      shift 2
      ;;
    --profile)
      require_value "$1" "$#"
      PROFILE="$2"
      shift 2
      ;;
    --with-skills)
      WITH_SKILLS=1
      shift
      ;;
    --skills-dir)
      require_value "$1" "$#"
      SKILLS_DIR="$2"
      SKILLS_DIR_SET=1
      shift 2
      ;;
    --ci)
      require_value "$1" "$#"
      CI_TEMPLATE="$2"
      shift 2
      ;;
    --with-checklists)
      WITH_CHECKLISTS=1
      shift
      ;;
    --dry-run)
      DRY_RUN=1
      shift
      ;;
    --force)
      FORCE=1
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "bootstrap.sh error: unknown option: $1" >&2
      usage >&2
      exit 1
      ;;
  esac
done

if [[ -z "$TARGET" ]]; then
  echo "bootstrap.sh error: --target is required" >&2
  usage >&2
  exit 1
fi

case "$PROFILE" in
  L0|L1|L2) ;;
  *)
    echo "bootstrap.sh error: --profile must be L0, L1, or L2 (got: $PROFILE)" >&2
    exit 1
    ;;
esac

case "$CI_TEMPLATE" in
  "") ;;
  generic|python|node-ts|rust|go|java)
    if [[ "$PROFILE" == "L0" ]]; then
      echo "bootstrap.sh error: --ci requires --profile L1 or L2 (L0 installs no CI workflow)" >&2
      exit 1
    fi
    ;;
  *)
    echo "bootstrap.sh error: --ci must be generic, python, node-ts, rust, go, or java (got: $CI_TEMPLATE)" >&2
    exit 1
    ;;
esac

case "${CI_TEMPLATE:-generic}" in
  python|node-ts|rust|go|java) CI_WORKFLOW_SRC="$REPO_ROOT/profiles/L1-team/workflows/ci-$CI_TEMPLATE.yml" ;;
  *) CI_WORKFLOW_SRC="$REPO_ROOT/profiles/L1-team/candidate-gates.workflow.yml" ;;
esac

if [[ -L "$TARGET" ]] || [[ ! -d "$TARGET" ]]; then
  echo "bootstrap.sh error: --target must be an existing non-symlink directory: $TARGET" >&2
  exit 1
fi

TARGET="$(cd "$TARGET" && pwd -P)"

# Strip trailing slashes from SKILLS_DIR and validate strictly
SKILLS_DIR="${SKILLS_DIR%/}"
if [[ -z "$SKILLS_DIR" ]] || [[ "$SKILLS_DIR" == /* ]] || [[ "$SKILLS_DIR" == "." ]] || [[ "$SKILLS_DIR" == *".."* ]] || [[ "$SKILLS_DIR" == *"\\"* ]] || [[ "$SKILLS_DIR" =~ [[:space:]] ]]; then
  echo "bootstrap.sh error: --skills-dir must be a non-empty safe repo-relative path: '$SKILLS_DIR'" >&2
  exit 1
fi

# Reject any symlink at destination or along any intermediate path component under $TARGET
assert_no_symlink_components() {
  local rel="$1"
  local current="$TARGET"
  local IFS='/'
  local parts
  read -r -a parts <<< "$rel"
  for part in "${parts[@]}"; do
    [[ -z "$part" ]] && continue
    current="$current/$part"
    if [[ -L "$current" ]]; then
      echo "bootstrap.sh error: refusing to traverse or overwrite symlink path: $current" >&2
      exit 1
    fi
  done
}

copied=0
skipped=0

copy_file() {
  local src="$1"
  local rel_dst="$2"
  local dst="$TARGET/$rel_dst"

  if [[ -L "$src" ]] || [[ ! -f "$src" ]]; then
    echo "bootstrap.sh error: missing regular source template: $src" >&2
    exit 1
  fi

  assert_no_symlink_components "$rel_dst"

  if [[ -e "$dst" ]] && [[ "$FORCE" -ne 1 ]]; then
    echo "SKIP (exists): $rel_dst"
    skipped=$((skipped + 1))
    return 0
  fi

  if [[ "$DRY_RUN" -eq 1 ]]; then
    echo "WOULD COPY: $rel_dst"
    copied=$((copied + 1))
    return 0
  fi

  mkdir -p "$(dirname "$dst")"
  cp "$src" "$dst"
  echo "COPIED: $rel_dst"
  copied=$((copied + 1))
}

append_gitignore_snippet() {
  local snippet="$REPO_ROOT/profiles/L0-solo/.gitignore.snippet"
  local dst="$TARGET/.gitignore"
  local marker="# Agentic SDLC multi-tool worktree namespaces"

  assert_no_symlink_components ".gitignore"

  if [[ -f "$dst" ]] && grep -Fq "$marker" "$dst"; then
    echo "SKIP (already present): .gitignore worktree snippet"
    skipped=$((skipped + 1))
    return 0
  fi

  if [[ "$DRY_RUN" -eq 1 ]]; then
    echo "WOULD APPEND: .gitignore worktree snippet"
    copied=$((copied + 1))
    return 0
  fi

  if [[ -f "$dst" ]] && [[ -s "$dst" ]]; then
    printf '\n' >> "$dst"
  fi
  cat "$snippet" >> "$dst"
  echo "APPENDED: .gitignore worktree snippet"
  copied=$((copied + 1))
}

# Install the `make agent-check` entrypoint that AGENTS.md, CLAUDE.md and the L1
# workflow refer to. An existing Makefile is never modified, even with --force:
# the snippet is placed next to it for the adopter to merge.
MAKEFILE_STATE="none"

install_agent_check_entrypoint() {
  local snippet="$REPO_ROOT/profiles/L0-solo/Makefile.agent-check.snippet"
  local existing=""
  local name

  for name in Makefile makefile GNUmakefile; do
    if [[ -e "$TARGET/$name" ]] || [[ -L "$TARGET/$name" ]]; then
      existing="$name"
      break
    fi
  done

  if [[ -z "$existing" ]]; then
    copy_file "$snippet" "Makefile"
    MAKEFILE_STATE="created"
    return 0
  fi

  # Read-only inspection: the existing Makefile (even a symlinked one) is never written.
  if grep -Eq '^agent-check[[:space:]]*:' "$TARGET/$existing" 2>/dev/null; then
    echo "SKIP (already present): agent-check target in $existing"
    skipped=$((skipped + 1))
    MAKEFILE_STATE="present"
    return 0
  fi

  copy_file "$snippet" "Makefile.agent-check.snippet"
  MAKEFILE_STATE="merge"
}

# --- L0 Solo Baseline (always included) ---
copy_file "$REPO_ROOT/profiles/L0-solo/AGENTS.md" "AGENTS.md"
copy_file "$REPO_ROOT/profiles/L0-solo/CLAUDE.md" "CLAUDE.md"
copy_file "$REPO_ROOT/profiles/L0-solo/STATUS.md" "docs/architecture/STATUS.md"
copy_file "$REPO_ROOT/profiles/L0-solo/VIBE_CODING_CONTEXT.md" "docs/VIBE_CODING_CONTEXT.md"
copy_file "$REPO_ROOT/profiles/L0-solo/pull_request_template.md" ".github/pull_request_template.md"
append_gitignore_snippet
install_agent_check_entrypoint

# --- L1 Team Additions ---
if [[ "$PROFILE" == "L1" || "$PROFILE" == "L2" ]]; then
  copy_file "$REPO_ROOT/profiles/L1-team/ISSUE_TEMPLATE/config.yml" ".github/ISSUE_TEMPLATE/config.yml"
  copy_file "$REPO_ROOT/profiles/L1-team/ISSUE_TEMPLATE/issue.md" ".github/ISSUE_TEMPLATE/issue.md"
  copy_file "$REPO_ROOT/profiles/L1-team/ISSUE_TEMPLATE/epic.md" ".github/ISSUE_TEMPLATE/epic.md"
  copy_file "$CI_WORKFLOW_SRC" ".github/workflows/candidate-gates.yml"
  copy_file "$REPO_ROOT/profiles/L1-team/suite-catalog.example.json" "docs/suite-catalog.example.json"
fi

# --- L2 Governed Additions ---
if [[ "$PROFILE" == "L2" ]]; then
  copy_file "$REPO_ROOT/profiles/L2-governed/CODEOWNERS.example" ".github/CODEOWNERS"
  copy_file "$REPO_ROOT/profiles/L2-governed/ruleset-policy.example.json" ".github/ruleset-policy.json"
  copy_file "$REPO_ROOT/profiles/L2-governed/github-ruleset.import.json" "docs/github-ruleset.import.json"
  copy_file "$REPO_ROOT/profiles/L2-governed/mechanism-review-checklist.md" "docs/mechanism-review-checklist.md"
fi

# --- Optional Agent Skills ---
if [[ "$WITH_SKILLS" -eq 1 ]]; then
  for skill_dir in "$REPO_ROOT"/skills/*; do
    if [[ -f "$skill_dir/SKILL.md" ]]; then
      skill_name="$(basename "$skill_dir")"
      copy_file "$skill_dir/SKILL.md" "$SKILLS_DIR/$skill_name/SKILL.md"
    fi
  done
fi

# --- Optional Empirical & Security Checklists ---
if [[ "$WITH_CHECKLISTS" -eq 1 ]]; then
  for f in "$REPO_ROOT"/checklists/*; do
    if [[ -f "$f" ]]; then
      copy_file "$f" "docs/checklists/$(basename "$f")"
    fi
  done
fi

echo "---"
if [[ "$DRY_RUN" -eq 1 ]]; then
  echo "Dry-run complete (profile=$PROFILE): $copied planned, $skipped skipped"
  exit 0
fi

echo "Bootstrap complete (profile=$PROFILE): $copied applied, $skipped skipped"
echo "Next steps before committing:"
step=1
case "$MAKEFILE_STATE" in
  created)
    echo "  $step. Edit the agent-check recipe in Makefile to run your real lint, typecheck and test commands. It fails closed until you do."
    ;;
  merge)
    echo "  $step. Merge Makefile.agent-check.snippet into your existing Makefile (it was left untouched), then delete the snippet."
    ;;
  *)
    echo "  $step. Confirm your existing agent-check target runs your real lint, typecheck and test commands."
    ;;
esac
step=$((step + 1))
echo "  $step. Fill docs/architecture/STATUS.md and docs/VIBE_CODING_CONTEXT.md with this repository's real modules and entrypoints."
step=$((step + 1))
if [[ "$PROFILE" == "L1" || "$PROFILE" == "L2" ]]; then
  echo "  $step. Replace <owner>/<repo> in .github/ISSUE_TEMPLATE/{config.yml,issue.md,epic.md}."
  step=$((step + 1))
  if [[ "${CI_TEMPLATE:-generic}" == "generic" ]]; then
    echo "  $step. Add your language runtime setup step to .github/workflows/candidate-gates.yml (or delete that file and re-run with --ci python|node-ts|rust|go|java)."
  else
    echo "  $step. Review the $CI_TEMPLATE commands in .github/workflows/candidate-gates.yml against your real lint, typecheck and test setup."
  fi
  step=$((step + 1))
fi
if [[ "$PROFILE" == "L2" ]]; then
  echo "  $step. Replace @org/... handles in .github/CODEOWNERS with verified team/user handles and align required_status_contexts in .github/ruleset-policy.json."
  step=$((step + 1))
fi
if [[ "$WITH_SKILLS" -eq 1 ]] && [[ "$SKILLS_DIR_SET" -eq 0 ]]; then
  echo "Skills were installed to $SKILLS_DIR (read by Codex and other .agents-aware tools)."
  echo "  For Claude Code re-run with --skills-dir .claude/skills; for Cursor use --skills-dir .cursor/skills."
fi
echo "Verify adoption signals (read-only):"
# %q keeps the printed command copy-pasteable when a path contains spaces.
printf '  python3 %q --profile %s %q\n' "$SCRIPT_DIR/audit-repo.py" "$PROFILE" "$TARGET"
