# Repository policy

This guide explains the repository policy gate and its input boundary.
[Design 0012](designs/0012-repository-policy.md) records the architecture.
The [invariant inventory](repository-policy-inventory.md) records the replacement for each old Python assertion.

## Run the gate

Install the tool versions that `mise.toml` pins:

```sh
mise install
make policy
```

CI and `workflow.policy_command` in `.ground-control.yaml` call `make policy`.
The gate runs the policy tests, evaluates the local Rego rules, and checks workflows with actionlint.
It also runs the targeted Go tests of contract alignment and gate behavior.
It does not run the full product suite.
Any failed stage stops the gate with a nonzero exit status.

Conftest evaluates local policy files. It does not pull or update policy bundles.
Actionlint checks workflow syntax and expressions.
The gate explicitly disables its optional ShellCheck and pyflakes integrations.
The existing language-specific CI jobs retain their analysis responsibilities.

## Add or change a rule

1. Identify the invariant and its governing decision.
2. Add the Rego rule under `policy/`.
3. Add a passing fixture and a failing fixture for its rule identifier.
4. Run the policy tests before changing the checked configuration.
5. Update the invariant inventory when the change replaces an existing check.
6. Run `make policy`.

Check missing fields and wrong value types as well as incorrect values.
An empty discovery result must fail when the rule requires a population.
Do not put exceptions in evaluated input. Exceptions belong in reviewed policy.
Do not replace executable failure tests with text matches.

## Inputs and effects

The collector reads named configuration, workflows, public pages, and selected maintained text from the checkout.
It rejects missing required files, malformed structured input, and paths that escape the checkout.
Shell parsing extracts commands and arguments without executing them.
The resulting JSON stays on the local machine or CI runner.
Temporary input files have cleanup on success and failure.

The behavior tests use disposable fixtures and fake external commands.
They run the actual Makefile and aggregate script without credentials or GitHub writes.
They check successful results and each failed, cancelled, skipped, or empty mandatory result.
The tests also check command failures and discovery failures.
Collector tests distinguish each malformed workflow shape and reject non-string commands.
They check the read budget, missing required files, inaccessible roots, and JSON encoding failures.
`mutation.yaml` records only equivalent changes that no parsed input can observe.
Each record states the exact pinned-library or owned-resource reason.

The RAES vocabulary test uses the public Go catalog through the sole adapter.
The module revision and sums select the corpus; a network vocabulary lookup does not.
Unknown or empty governed vocabularies fail the check.
The test does not maintain a local copy of governed terms.

## Cutover responsibilities

ADR 0047 keeps the Python product until the final cutover in issue #582.
Python-only checks remain active while their subjects still exist.
Their inventory rows name the reason and the Go equivalent where one applies.
Removal of a file does not automatically retire its policy.

The Go equivalents use the existing module, lint, security, and architecture gates.
Module checksums establish integrity; they do not establish vulnerability freedom.
Dependency update ownership remains a separate policy.

Sphinx, Read the Docs, and the documentation requirements remain after cutover.
Their supply-chain and publication controls therefore remain applicable.
Signing identity, release authorization, immutable tags, recovery, and attestation also remain applicable.
The distribution port must adapt artifact-specific checks to the new release subjects.
