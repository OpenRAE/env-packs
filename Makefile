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

.PHONY: help devmain prose conformance conformance-go go-check go-lint go-audit go-fuzz go-arch \
	go-arch-design go-arch-dsl go-mutation go-mutation-all go-regression

help: ## List the available targets
	@grep -hE '^[a-zA-Z0-9_-]+:.*?## ' $(MAKEFILE_LIST) \
	  | awk 'BEGIN {FS = ":.*?## "}; {printf "  %-15s %s\n", $$1, $$2}'

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
# The tests run with the race detector and in shuffled order, and write the
# coverage profile that CI sends to SonarCloud (docs/development/go-test-standard.md).
go-check: ## Build, vet, and test the Go code
	$(GO) build ./...
	$(GO) vet ./...
	$(GO) test -race -shuffle=on -coverprofile=coverage-go.out ./...

# Lints the Go code with the pinned golangci-lint once for each release
# platform of the architecture model, so that each build-constrained file is
# linted. Then it checks the formatting, and checks that go.mod and go.sum are
# tidy (docs/development/go-style-map.md).
go-lint: ## Lint the Go code and check formatting and tidiness
	@set -eu; \
	for platform in $$($(GO) run ./tools/archcheck platforms); do \
	  echo "go-lint: $$platform"; \
	  GOOS=$${platform%/*} GOARCH=$${platform#*/} CGO_ENABLED=0 \
	    $(MISE) exec -- golangci-lint run ./...; \
	done
	$(MISE) exec -- golangci-lint fmt --diff ./...
	$(GO) mod tidy -diff

# Checks the downloaded modules against go.sum, and reports each known
# vulnerability that the code can reach, with the govulncheck version that
# mise.toml pins. govulncheck reads the Go vulnerability database on the
# network.
go-audit: ## Verify the Go modules and check them for known vulnerabilities
	$(GO) mod verify
	$(MISE) exec -- govulncheck ./...

# The fuzz time for each target. The weekly CI schedule raises it.
FUZZTIME ?= 30s

# Runs every native fuzz target in the module, one target at a time, for
# FUZZTIME each (docs/development/go-test-standard.md). The package list and
# each target list are captured first, so a failed command stops the run
# instead of leaving a loop with nothing to fuzz.
go-fuzz: ## Run every Go fuzz target for FUZZTIME (default 30s)
	@set -eu; \
	pkgs=$$($(GO) list ./...); \
	for pkg in $$pkgs; do \
	  listing=$$($(GO) test -list '^Fuzz' "$$pkg"); \
	  for target in $$(printf '%s\n' "$$listing" | grep '^Fuzz' || true); do \
	    echo "go-fuzz: $$pkg $$target"; \
	    $(GO) test -run '^$$' -fuzz "^$$target$$" -fuzztime "$(FUZZTIME)" "$$pkg"; \
	  done; \
	done

# Checks the code, the design records, and the C4 view against the
# architecture model (docs/development/designs/README.md).
go-arch: ## Check the code and design records against the architecture model
	$(GO) run ./tools/archcheck check

# The design step: checks the model and the design records before the code
# exists.
go-arch-design: ## Check the design records against the architecture model
	$(GO) run ./tools/archcheck design

# Renders architecture/workspace.dsl from the architecture model.
go-arch-dsl: ## Render the C4 view of the architecture model
	$(GO) run ./tools/archcheck dsl -write

# The base commit of the gates on the changed lines: the integration branch of
# the Go port (ADR 0047). The cutover changes it to origin/dev. The gates read
# only committed code, so commit the work before you run them.
BASE ?= origin/go-cutover

# Runs the conformance corpus against the Python console scripts on PATH
# (docs/development/designs/0003-conformance-corpus.md). The corpus starts the
# commands, so the test results do not come from the cache.
conformance: ## Run the conformance corpus against the Python implementation
	$(GO) test ./conformance -count=1 -args -impl=python

# Builds each Go command under cmd/ and runs its conformance cases against it.
# The other commands have no Go implementation yet (design 0008).
conformance-go: ## Run the conformance cases of the Go commands against Go
	@set -eu; bin=$$(mktemp -d); trap 'rm -rf "$$bin"' EXIT; \
	$(GO) build -o "$$bin/" ./cmd/...; \
	commands=$$(ls cmd | paste -sd '|' -); \
	$(GO) test ./conformance -count=1 -run "TestCorpus/^($$commands)$$/" -args -impl=go -bin "$$bin"

# Checks the prose of each Markdown file that HEAD adds or changes since BASE,
# with the Vale version that mise.toml pins and the rules in .vale/styles/STE
# (docs/development/documentation-style-guide.md). It skips CHANGELOG.md, test
# fixtures, and the assets of packs and kits.
prose: ## Check the prose of the Markdown files changed since BASE
	@set -eu; \
	files=$$(git diff --name-only --diff-filter=d --merge-base "$(BASE)" HEAD -- '*.md' \
	  ':(exclude)CHANGELOG.md' ':(exclude,glob)**/testdata/**' ':(exclude)tests/fixtures' \
	  ':(exclude,glob)packs/*/assets/**' ':(exclude,glob)kits/*/*/assets/**'); \
	if [ -z "$$files" ]; then echo "prose: no changed Markdown file"; exit 0; fi; \
	$(MISE) exec -- vale $$files

# Mutation testing on the Go lines that HEAD changes since BASE, with the
# go-mutesting version that mise.toml pins
# (docs/development/go-test-standard.md).
go-mutation: ## Mutation testing on the Go lines changed since BASE
	$(MISE) exec -- $(GO) run ./tools/testgate mutation -base "$(BASE)"

# Mutation testing on each Go file. A weekly workflow runs it.
go-mutation-all: ## Mutation testing on each Go file
	$(MISE) exec -- $(GO) run ./tools/testgate mutation -all

# Proves that each regression test that HEAD adds or changes since BASE fails
# on the merge base.
go-regression: ## Prove that each new regression test fails before its fix
	$(GO) run ./tools/testgate regression -base "$(BASE)"
