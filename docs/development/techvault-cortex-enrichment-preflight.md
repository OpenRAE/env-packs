# TechVault Cortex enrichment preflight

Issue #286 began with a healthy Cortex API but an empty analyzer inventory and
a failed TheHive connector. The gap was not liveness: TechVault had no analyzer
bytes, organization enablement, connector identity, or executable enrichment
proof. It also declared Cortex's internal Elasticsearch mapping as portable
service state. That mapping forced the heterogeneous `relations` join field to
a scalar type and made analyzer enablement fail.

## Implemented boundary

- TechVault declares the provider-neutral facts: analysis capability, exact
  offline analyzer content, dedicated connector principal, TheHive-to-Cortex
  relationship, one-shot initialization, and observed enrichment readiness.
- Backend-generated secret artifact outputs are injected into the initializer
  and TheHive through RAES `value_from` references; no API key is authored in
  portable content.
- The pack-local initializer performs Cortex-native operations through its API:
  clean database migration, organization and identity creation, analyzer scan,
  organization enablement, and readback. Re-running it accepts matching state
  and rejects conflicting connector ownership.
- Cortex owns its native job-index schema. The SDL no longer names or attempts
  to reproduce the `cortex_6` mapping.
- TheHive uses a separate generated key for a service account with only `read` and
  `analyze`; the initializer's `orgadmin` key is not supplied to TheHive.
- The analyzer is pure Python already present in the exact Cortex image. It has
  no package installation, network dependency, external catalog, Docker socket,
  responder capability, or private service credential.

## Proof

Static tests verify the RAES application/authorization/integration contracts,
exact artifact bindings, key separation, least privilege, idempotence, and the
absence of a portable Cortex index mapping. The native gate starts clean exact
Elasticsearch, Cortex, Cassandra, and TheHive images; runs
`TechVaultScenarioContext_1_0` for `172.20.1.30`; requires a successful report
classifying it as the scenario attacker; and requires authenticated TheHive
connector status `OK`.

```sh
TECHVAULT_NATIVE_CORTEX=1 .venv/bin/python -m unittest \
  tests.test_techvault_cortex_native.NativeCortexContractTests.test_exact_images_execute_enrichment_and_connect_thehive
```
