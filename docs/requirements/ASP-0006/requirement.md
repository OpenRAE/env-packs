---
id: ASP-0006
title: "Repository governance checks through the Go cutover"
status: ACTIVE
type: FUNCTIONAL
priority: MUST
created_at: 2026-11-09T00:00:00Z
updated_at: 2026-11-09T00:00:00Z
---

# ASP-0006 — Repository governance checks through the Go cutover

## Statement

The repository shall check its governance invariants with policy as code or
standard linters. An inventory shall map every check named in issue #577 to
its replacement or a stated retirement reason. Each policy shall have passing
and failing tests. CI and Ground Control shall run the same policy gate.

Go tests shall check the identity, concept-authority, and provenance contracts.
The concept check shall read governed terms through the RAES Go adapter.
The migration shall preserve each invariant that applies after the cutover.
Checks specific to the current Python product shall remain active until that
cutover removes that product. The documentation toolchain shall retain its supply-chain
and publication checks after the cutover.

## Rationale

Issue #577 changes the enforcement of existing repository rules.
This requirement binds the replacement gate and its tests to that contract.
It adds no pack semantics or release path.

## Traceability

- IMPLEMENTS → GITHUB_ISSUE `577`
- IMPLEMENTS → CODE `tools/policyinput/main.go`
- IMPLEMENTS → CODE `policy/governance.rego`
- IMPLEMENTS → CODE `policy/dependencies.rego`
- IMPLEMENTS → CODE `policy/release.rego`
- IMPLEMENTS → CODE `policy/ci.rego`
- IMPLEMENTS → CODE `policy/ownership.rego`
- IMPLEMENTS → CODE `internal/raesadapter/vocabulary.go`
- IMPLEMENTS → CODE `Makefile`
- IMPLEMENTS → CODE `.github/workflows/ci.yml`
- IMPLEMENTS → DOCUMENTATION `docs/development/repository-policy-inventory.md`
- TESTS → TEST `policy/main_test.rego`
- TESTS → TEST `tools/policyinput/behavior_test.go`
- TESTS → TEST `tools/policyinput/boundary_test.go`
- TESTS → TEST `tools/policyinput/gate_test.go`
- TESTS → TEST `internal/contractalignment/alignment_test.go`
- TESTS → TEST `internal/contractalignment/identity_test.go`
- TESTS → TEST `internal/raesadapter/vocabulary_test.go`
- TESTS → TEST `internal/architecture/adapter_boundary_test.go`
- TESTS → TEST `conformance/testdata/raes-pack-check/concept-authority.txtar`
