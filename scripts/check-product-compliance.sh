#!/usr/bin/env bash
# Read-only repository compliance checker for Agentic SDLC adoption signals.
# Usage: ./scripts/check-product-compliance.sh [--profile L0|L1|L2] [--fetch] /path/to/repo
# --profile defaults to L1; pass the profile you bootstrapped (bootstrap.sh prints the exact command).
# By default this script is strictly read-only (does NOT run git fetch unless --fetch is passed).
set -uo pipefail

PROFILE="L1"
PROFILE_SET=0
DO_FETCH=0
REPO_PATH=""

usage() {
  cat <<'EOF'
Usage: check-product-compliance.sh [--profile L0|L1|L2] [--fetch] <repo-path>

  --profile  Profile to check against (default: L1). Use the profile you bootstrapped.
  --fetch    Run `git fetch origin --prune` first (otherwise strictly read-only).
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --profile)
      if [[ $# -lt 2 ]]; then
        echo "check-product-compliance.sh error: --profile requires a value" >&2
        exit 1
      fi
      PROFILE="$2"
      PROFILE_SET=1
      shift 2
      ;;
    --fetch)
      DO_FETCH=1
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    -*)
      echo "check-product-compliance.sh error: unknown option: $1" >&2
      usage >&2
      exit 1
      ;;
    *)
      if [[ -n "$REPO_PATH" ]]; then
        echo "check-product-compliance.sh error: unexpected extra argument: $1" >&2
        exit 1
      fi
      REPO_PATH="$1"
      shift
      ;;
  esac
done

if [[ -z "$REPO_PATH" ]]; then
  usage >&2
  exit 1
fi

case "$PROFILE" in
  L0|L1|L2) ;;
  *)
    echo "check-product-compliance.sh error: --profile must be L0, L1, or L2 (got: $PROFILE)" >&2
    exit 1
    ;;
esac

REPO_NAME="$(basename "$REPO_PATH")"

if [[ ! -e "$REPO_PATH/.git" ]]; then
  echo "SKIP: $REPO_NAME is not a git repository" >&2
  exit 2
fi

pass=0
fail=0
warn=0

check_file() {
  local file="$1"
  local label="$2"
  if [[ -f "$REPO_PATH/$file" ]] && [[ -s "$REPO_PATH/$file" ]]; then
    pass=$((pass + 1))
  else
    echo "  FAIL: missing $label ($file)" >&2
    fail=$((fail + 1))
  fi
}

check_warn() {
  local file="$1"
  local label="$2"
  if [[ -f "$REPO_PATH/$file" ]] && [[ -s "$REPO_PATH/$file" ]]; then
    pass=$((pass + 1))
  else
    echo "  WARN: missing $label ($file)" >&2
    warn=$((warn + 1))
  fi
}

check_contains() {
  local file="$1"
  local pattern="$2"
  local label="$3"
  if [[ -f "$REPO_PATH/$file" ]] && grep -Eq "$pattern" "$REPO_PATH/$file"; then
    pass=$((pass + 1))
  else
    echo "  WARN: $label ($file)" >&2
    warn=$((warn + 1))
  fi
}

echo "=== $REPO_NAME (profile=$PROFILE) ==="

# --- L0 Required baseline ---
check_file "CLAUDE.md" "Agent instructions (CLAUDE.md)"
check_file "AGENTS.md" "Agent instructions (AGENTS.md)"
check_contains "AGENTS.md" 'issue|Issue|GitHub|PR|pull request|worktree|agent-issue-pr-loop' "AGENTS.md should reference PR/worktree workflow"
check_contains "CLAUDE.md" 'issue|Issue|GitHub|PR|pull request|worktree|agent-issue-pr-loop' "CLAUDE.md should reference PR/worktree workflow"
check_file "docs/VIBE_CODING_CONTEXT.md" "Vibe Coding context"
check_file "docs/architecture/STATUS.md" "Architecture status"
check_file ".github/pull_request_template.md" "PR template"
check_contains ".github/pull_request_template.md" 'Verification|Validation|Test Plan|Tests|验证|测试' "PR template should require verification evidence"
check_contains ".github/pull_request_template.md" 'Risk|Rollback|风险|回滚' "PR template should require risk/rollback"
check_contains ".github/pull_request_template.md" 'AI Assistance|agent|Agent|Tool' "PR template should capture AI assistance"
check_contains ".github/pull_request_template.md" 'Closes|Fixes|Related|issue|Issue|关联' "PR template should require issue linkage"
check_contains ".gitignore" '\.worktrees/' ".gitignore should ignore .worktrees/"

# The verification command agents are told to run must actually exist.
has_agent_check_target() {
  local name
  for name in Makefile makefile GNUmakefile; do
    if [[ -f "$REPO_PATH/$name" ]] && grep -Eq '^agent-check[[:space:]]*:' "$REPO_PATH/$name"; then
      return 0
    fi
  done
  return 1
}

entrypoint_warned=0
if [[ -f "$REPO_PATH/AGENTS.md" ]] && grep -q 'make agent-check' "$REPO_PATH/AGENTS.md"; then
  if has_agent_check_target; then
    pass=$((pass + 1))
  else
    echo "  WARN: AGENTS.md names \`make agent-check\` but there is no agent-check target in a Makefile (add one, or replace the command with your real check)" >&2
    warn=$((warn + 1))
    entrypoint_warned=1
  fi
fi

# --- L1 Team checks ---
if [[ "$PROFILE" == "L1" || "$PROFILE" == "L2" ]]; then
  check_warn ".github/ISSUE_TEMPLATE/issue.md" "Issue template"
  check_warn ".github/ISSUE_TEMPLATE/epic.md" "Epic issue template"
  check_warn ".github/ISSUE_TEMPLATE/config.yml" "Issue config"
  check_contains ".github/ISSUE_TEMPLATE/issue.md" '验收标准|Acceptance Criteria' "Issue template should require acceptance criteria"
  check_contains ".github/ISSUE_TEMPLATE/issue.md" '验证计划|Verification Plan' "Issue template should require verification plan"
  check_contains ".github/ISSUE_TEMPLATE/issue.md" '归属仓库|Owning [Rr]epository|Repository' "Issue template should require owning repository"
  check_contains ".github/ISSUE_TEMPLATE/issue.md" '依赖|Dependencies' "Issue template should require dependencies"
  for tmpl in ".github/ISSUE_TEMPLATE/issue.md" ".github/ISSUE_TEMPLATE/epic.md" ".github/ISSUE_TEMPLATE/config.yml"; do
    if [[ -f "$REPO_PATH/$tmpl" ]] && grep -Fq '<owner>/<repo>' "$REPO_PATH/$tmpl"; then
      echo "  WARN: $tmpl still contains placeholder '<owner>/<repo>'" >&2
      warn=$((warn + 1))
    fi
  done

  # Check for at least one .yml or .yaml workflow without SIGPIPE-prone ls|head
  workflow_found=0
  if [[ -d "$REPO_PATH/.github/workflows" ]]; then
    for wf in "$REPO_PATH/.github/workflows/"*.yml "$REPO_PATH/.github/workflows/"*.yaml; do
      if [[ -f "$wf" ]]; then
        workflow_found=1
        break
      fi
    done
  fi
  if [[ "$workflow_found" -eq 1 ]]; then
    pass=$((pass + 1))
  else
    echo "  FAIL: no CI workflow (.yml/.yaml) in .github/workflows/" >&2
    fail=$((fail + 1))
  fi

  if [[ -f "$REPO_PATH/Makefile" ]] || [[ -f "$REPO_PATH/makefile" ]] || [[ -f "$REPO_PATH/GNUmakefile" ]]; then
    if has_agent_check_target; then
      pass=$((pass + 1))
    elif [[ "$entrypoint_warned" -eq 0 ]]; then
      echo "  WARN: Makefile exists but has no agent-check target" >&2
      warn=$((warn + 1))
    fi
  else
    echo "  FAIL: no Makefile (L1 expects a single \`make agent-check\` entrypoint)" >&2
    fail=$((fail + 1))
  fi
fi

# --- L2 Governed checks ---
if [[ "$PROFILE" == "L2" ]]; then
  check_file ".github/CODEOWNERS" "Enforcement CODEOWNERS"
  if [[ -f "$REPO_PATH/.github/CODEOWNERS" ]] && grep -Eq '(^|[[:space:]])@org/' "$REPO_PATH/.github/CODEOWNERS"; then
    echo "  FAIL: .github/CODEOWNERS still contains template placeholder '@org/' (GitHub skips unknown owners; replace with real team or user handles)" >&2
    fail=$((fail + 1))
  fi
  check_warn ".github/ruleset-policy.json" "GitHub ruleset policy"
  if [[ -f "$REPO_PATH/.github/ruleset-policy.json" ]] && grep -Fq 'policy.example-repo.' "$REPO_PATH/.github/ruleset-policy.json"; then
    echo "  WARN: .github/ruleset-policy.json still contains placeholder 'policy.example-repo.*'" >&2
    warn=$((warn + 1))
  fi
fi

# --- Git status (strictly read-only unless --fetch) ---
cd "$REPO_PATH" || { echo "check-product-compliance.sh error: cannot enter $REPO_PATH" >&2; exit 2; }
if [[ "$DO_FETCH" -eq 1 ]]; then
  if ! git fetch origin --prune 2>/dev/null; then
    echo "  WARN: git fetch origin --prune failed" >&2
    warn=$((warn + 1))
  fi
fi

behind=$(git rev-list --left-right --count 'HEAD...@{u}' 2>/dev/null | awk '{print $2}' || true)
if [[ -n "$behind" ]] && [[ "$behind" -gt 0 ]]; then
  echo "  WARN: $REPO_NAME is $behind commits behind remote" >&2
  warn=$((warn + 1))
fi

dirty=$(git status --short 2>/dev/null | wc -l | tr -d ' ')
if [[ "$dirty" -gt 0 ]]; then
  echo "  WARN: $REPO_NAME has $dirty uncommitted changes" >&2
  warn=$((warn + 1))
fi

total=$((pass + fail))
if [[ "$fail" -eq 0 ]]; then
  echo "  PASS: $REPO_NAME ($pass/$total checks, $warn warnings)"
  exit 0
else
  echo "  FAIL: $REPO_NAME ($pass/$total checks passed, $fail failed, $warn warnings)"
  if [[ "$PROFILE_SET" -eq 0 ]]; then
    echo "  NOTE: no --profile given; checked against L1. If this repository adopted the solo baseline, re-run with --profile L0." >&2
  fi
  exit 1
fi
