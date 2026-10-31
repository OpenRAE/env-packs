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
#
# The Go checks of the port (ADR 0047) are the exception. CI runs `make
# go-check`, so this target is their one definition, and the other lists call it.

# Substitutable so the contract test in tests/test_makefile.py can drive the
# promotion target without touching GitHub.
GH ?= gh

# Substitutable so a caller can select a specific Go toolchain binary.
GO ?= go

# Substitutable so a caller can use a mise binary that is not on PATH. mise
# installs the tool versions that mise.toml pins and mise.lock verifies.
MISE ?= mise

.DEFAULT_GOAL := help

.PHONY: help devmain go-check go-lint

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

# Builds, vets, and tests every Go package with the toolchain that go.mod pins.
go-check: ## Build, vet, and test the Go code
	$(GO) build ./...
	$(GO) vet ./...
	$(GO) test ./...

# Lints the Go code with the pinned golangci-lint, checks the formatting, and
# checks that go.mod and go.sum are tidy (docs/development/go-style-map.md).
go-lint: ## Lint the Go code and check formatting and tidiness
	$(MISE) exec -- golangci-lint run ./...
	$(MISE) exec -- golangci-lint fmt --diff ./...
	$(GO) mod tidy -diff
