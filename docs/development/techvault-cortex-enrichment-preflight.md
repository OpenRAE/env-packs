# TechVault Cortex enrichment preflight

Issue #286 began with a healthy Cortex API but an empty analyzer inventory and
a failed TheHive connector. The gap was not liveness: TechVault had no analyzer
bytes, organization enablement, connector identity, or executable enrichment
proof. It also declared Cortex's internal Elasticsearch mapping as portable
service state. That mapping forced the heterogeneous `relations` join field to
a scalar type and made analyzer enablement fail.

## Implemented boundary

- TechVault declares the provider-neutral facts: analysis capability, exact
  offline analyzer content, a dedicated least-privilege connector principal,
  TheHive-to-Cortex relationship, and observed enrichment readiness.
- No API key, initializer, or credential-delivery route is authored in portable
  content. A backend chooses how to establish the declared in-world state.
- Cortex owns its native job-index schema. The SDL no longer names or attempts
  to reproduce the `cortex_6` mapping.
- TheHive's service account has only `read` and `analyze`.
- The analyzer is dependency-free Python content. It has no network dependency,
  external catalog, responder capability, or private service credential.

## Proof

Static tests verify the RAES application, authorization, and integration
contracts; exact analyzer artifact bindings; least privilege; and the absence
of a portable Cortex index mapping or initializer. The dependency-free analyzer
test executes `TechVaultScenarioContext_1_0` for both the scenario attacker and
an unclassified address. Runtime connector health remains a required evidence
readback from a realized environment.
