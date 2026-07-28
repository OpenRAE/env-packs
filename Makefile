# Repository task shortcuts.
#
# `devmain` is the only target that acts on anything. The default goal is
# deliberately `help`: Make runs the *first* target when invoked with no goal,
# and the acting target here opens a pull request against `main`. A bare `make`
# must never do that, so the default goal is pinned rather than left to file
# order (ADR 0019).
#
# The local verification loop -- unittest, raes-pack-validate,
# raes-pack-release, compileall -- is intentionally NOT restated here. AGENTS.md,
# .ground-control.yaml, and .github/workflows/ci.yml already each hold that list;
# a fourth copy would drift out of step with them.

# Substitutable so the contract test in tests/test_makefile.py can drive the
# promotion target without touching GitHub.
GH ?= gh

.DEFAULT_GOAL := help

.PHONY: help devmain

help: ## List the available targets
	@grep -hE '^[a-zA-Z0-9_-]+:.*?## ' $(MAKEFILE_LIST) \
	  | awk 'BEGIN {FS = ":.*?## "}; {printf "  %-8s %s\n", $$1, $$2}'

# The promotion PR body, kept in an exported variable so the recipe passes it as
# one literal argument: no shell metacharacters, no interpolation, and no editor
# or --fill, which would let .github/PULL_REQUEST_TEMPLATE.md supply the blank
# sections and unticked boxes that the hand-opened promotions carried.
define DEVMAIN_BODY
Promotes dev to main.

Merge this with a merge commit. Do not squash it and do not rebase it.

main is where release-please reads Conventional Commit history to decide the
version bump and build CHANGELOG.md (ADR 0008, ADR 0019). Squashing or rebasing
collapses every promoted subject into a single one, and the next release loses
both its changelog entries and its version decision.
endef
export DEVMAIN_BODY

# Opens the PR and stops there. GitHub stays the authority on everything else:
# it rejects a second open PR for the same head/base pair, and branch protection
# on `main` still requires an approving review plus `verify`. That refusal is a
# visible nonzero error and is deliberately left to propagate.
devmain: ## Open the dev -> main promotion PR
	@$(GH) pr create --base main --head dev \
	  --title "chore: promote dev to main" \
	  --body "$$DEVMAIN_BODY"
