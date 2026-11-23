.PHONY: check lint static-analysis affected-test-closure-check governance-enforcement-evidence-check agent-governance-test eval-deterministic verify-all agent-check demo-catch-bugs audit-repo audit-pr-diff product-compliance

PYTHON ?= python3
PROFILE ?= L1

# Digest-pinned linters used by `make static-analysis` (requires Docker):
# ShellCheck v0.11.0 and actionlint 1.7.12.
SHELLCHECK_IMAGE ?= koalaman/shellcheck@sha256:bb596a0d169b85ddd81d8b6d3a2ff6d5baf5fca10b97f575ebc647c3dff62b3d
ACTIONLINT_IMAGE ?= rhysd/actionlint@sha256:b1934ee5f1c509618f2508e6eb47ee0d3520686341fec936f3b79331f9315667
SHELL_SCRIPTS := $(wildcard scripts/*.sh)
WORKFLOW_FILES := $(wildcard .github/workflows/*.yml) profiles/L1-team/candidate-gates.workflow.yml $(wildcard profiles/L1-team/workflows/*.yml)

check: affected-test-closure-check governance-enforcement-evidence-check
	bash scripts/check-docs.sh

affected-test-closure-check:
	$(PYTHON) scripts/check-affected-closure.py --root "$(CURDIR)" check
	$(PYTHON) -m pytest -q tests/affected_closure/test_contract.py

governance-enforcement-evidence-check:
	$(PYTHON) scripts/check-enforcement-evidence.py --root "$(CURDIR)" check
	$(PYTHON) -m pytest -q tests/affected_closure/test_enforcement_evidence.py tests/affected_closure/test_observe_github_ruleset.py

agent-governance-test:
	$(PYTHON) -m pytest -q tests --ignore=tests/affected_closure

lint:
	$(PYTHON) -m ruff check --no-cache .

static-analysis:
	docker run --rm -v "$(CURDIR):/mnt:ro" -w /mnt $(SHELLCHECK_IMAGE) $(SHELL_SCRIPTS)
	docker run --rm -v "$(CURDIR):/repo:ro" -w /repo $(ACTIONLINT_IMAGE) -no-color $(WORKFLOW_FILES)

eval-deterministic:
	$(PYTHON) -S scripts/run-evals.py

verify-all: check lint agent-governance-test eval-deterministic

agent-check: verify-all

demo-catch-bugs:
	@echo "=== Demo 1: Catching a GitHub Ruleset where an AI agent can push after approval (expected FAIL) ==="
	@$(PYTHON) scripts/check-enforcement-evidence.py --root "$(CURDIR)" --report standards/testing-strategy/enforcement-evidence/fixtures/invalid/last-push-disabled.json check 2>&1 && exit 1 || echo "Caught as expected (fail-closed)."
	@echo ""
	@echo "=== Demo 2: Catching an unconditional bypass actor in GitHub Rulesets (expected FAIL) ==="
	@$(PYTHON) scripts/check-enforcement-evidence.py --root "$(CURDIR)" --report standards/testing-strategy/enforcement-evidence/fixtures/invalid/unconditional-bypass.json check 2>&1 && exit 1 || echo "Caught as expected (fail-closed)."
	@echo ""
	@echo "=== Demo 3: Catching an unbound status-check source (integration_id: null; spoofable by write token) ==="
	@$(PYTHON) scripts/check-enforcement-evidence.py --root "$(CURDIR)" --report standards/testing-strategy/enforcement-evidence/fixtures/invalid/unbound-status-source.json check 2>&1 && exit 1 || echo "Caught as expected (fail-closed)."
	@echo ""
	@echo "=== Demo 4: Catching an unapproved pull_request bypass actor (expected FAIL) ==="
	@$(PYTHON) scripts/check-enforcement-evidence.py --root "$(CURDIR)" --report standards/testing-strategy/enforcement-evidence/fixtures/invalid/unapproved-pr-bypass.json check 2>&1 && exit 1 || echo "Caught as expected (fail-closed)."
	@echo ""
	@echo "=== Demo 5: Validating a strong ruleset (expected PASS) ==="
	@$(PYTHON) scripts/check-enforcement-evidence.py --root "$(CURDIR)" --report standards/testing-strategy/enforcement-evidence/fixtures/valid/strong-ruleset.json check 2>&1

audit-repo:
	@test -n "$(REPO)" || (echo "Usage: make audit-repo REPO=/path/to/repo [AUDIT_ARGS='--github']" && exit 1)
	$(PYTHON) scripts/audit-repo.py "$(REPO)" $(AUDIT_ARGS)

audit-pr-diff:
	@test -n "$(BASE)" -a -n "$(HEAD)" || (echo "Usage: make audit-pr-diff BASE=origin/main HEAD=HEAD [REPO=.]" && exit 1)
	$(PYTHON) -S scripts/audit-pr-diff.py --repo "$${REPO:-.}" --base "$(BASE)" --head "$(HEAD)" $(DIFF_ARGS)

product-compliance:
	@test -n "$(REPO)" || (echo "Usage: make product-compliance REPO=/path/to/repo [PROFILE=L0|L1|L2]" && exit 1)
	bash scripts/check-product-compliance.sh --profile "$(PROFILE)" "$(REPO)"
