# TechVault Wazuh endpoint-agent contract

Issue #312 consumes RAE 5.0.0 and its progressive SDL semantics. RAE owns the
models and their meaning; this repository authors the TechVault scenario and
validates its joins; backends acquire software, realize processes and storage,
and observe readiness. ADR 0009 and ADR 0036 remain binding. No new schema or
backend adapter is introduced.

## Current baseline and recovered work

The original September 3 work targeted RAE 3.3.0, dedicated forwarding sidecars
and an unresolved package-acquisition contract. The September 5 issue correction
and subsequent dev changes supersede that approach. Current dev declares DB
and Suricata forwarding on their scenario owners and delegates sidecar/process
placement. Preserve that separation; do not restore retired sidecar nodes,
source images, package repositories, environment bindings or launch recipes.

RAE 5.0.0 is the latest release checked on September 16. Required software can
be expressed independently from acquisition through RuntimeSoftwareComponent.
An omitted acquisition refinement under the existing open realization policy is
delegation, not a missing package-install recipe. Wazuh 4.12.0 remains the
selected software version; no Wazuh package manager, repository, distribution
version or trust override is selected.

## Authored outcomes

The required graph has eight owners: webapp, ad, dns, fileshare, victim,
workstation, db and suricata. Each has one Wazuh forwarder, required software,
a stable techvault-<owner>-agent enrollment name, and one active manager member
whose node_ref resolves to that owner. Declaration IDs and manager agent IDs
remain distinct from enrollment names.

The six endpoint owners carry host telemetry. DB owns PostgreSQL logs and
Suricata owns its EVE network evidence. Generic syslog and Suricata alerts do
not prove another host's endpoint enrollment. Existing current-dev source
paths and logical IDs are preserved.

Separate targets reference the manager's agent-events and agent-enrollment
services, with matching listener role, port and protocol. Enrollment material
is classified operator_secret; no credential value is authored. Dependencies
state manager ordering, not live service health.

One retained, single-writer volume per owner carries /var/ossec/etc. This is
scenario-visible enrollment state, not a host storage location or storage
driver choice. Compatible enrollment must survive restart/recreation without
creating another manager identity. Manager inventory retains its existing
volume. Log sources name required files; Suricata's existing EVE output stream
owns its log. Backends must make those sources readable by their realized agent
and protect client keys; the pack adds no user, capability or launch recipe.

## Readiness and evidence

RAE deliberately excludes observed connection status from configuration
comparison. Therefore active manager membership alone is not a readiness gate.
The observed-state proposition wazuh-agents-ready and its precondition assertion
require all eight node subjects to satisfy the Boolean observable
urn:techvault:observable:wazuh-agent-ready. This is a scenario-authored property
carried by RAE's existing proposition contract, not a new RAE vocabulary enum
or an implemented evaluator.

For each subject, that observable means exactly one matching active enrollment,
readable declared sources and fresh telemetry attributed to that identity,
including after restart/recreation. Missing, duplicate, stale or disconnected
required identities fail. The linked evidence requirement scopes the manager
and all eight forwarding declarations, requires redaction and loss disclosure,
and retains bounded identity/status/correlation results as a JSON report
artifact for the run. The artifact channel gives evaluator admission a concrete
output modality while leaving observation method open. It does
not select a collector, transport, probe or API implementation.

Backend/evaluator capability admission must support that observable before
claiming readiness. The reference compiler proves carriage and required
configuration; it does not deploy Wazuh or produce live truth. Open realization
still permits compatible backend additions: an exact authored baseline is not
a global prohibition on unmentioned runtime resources.

## Validation and security

Reuse validate_pack(), the pinned RAE parser, the existing author-only pack
validator and its bounded code/id diagnostics. The Wazuh table is only the
TechVault baseline policy: eight authored owners, stable names, source paths,
manager joins, software version and retained state. Generic semantic
validation stays upstream. Readiness validation protects the proposition,
assertion and evidence links, never evaluates live observations locally.

Tests exercise the real parser/compiler, upstream recursive software
constraint evaluation, observed-state assertion carriage and independent
mutations of membership, identity, targets, sources, software, persistence and
readiness. Existing realization-method tests protect backend delegation.
No raw keys, environment secrets, host paths or event payloads enter test
fixtures or diagnostics.

Refresh external concept subjects with tools/refresh_pack_sdl_binding.py, then
derive the complete associated-artifact manifest because validator content also
changes. Run focused tests and all repository completion, policy, review,
content and release gates. Release Please owns the package version and changelog.

## Acceptance boundary

Static evidence proves declarations, references and required constraints. Live
readiness requires a backend to consume the released pack digest and report the
per-host observations above. It must also verify enrollment compatibility after
restart/recreation. This work does not claim that a deployment is golden, that
a stub proves readiness, or that a static manifest revokes old credentials.
A deployment migrating older sidecar identities needs backend reconciliation;
this change preserves the identities already on current dev.
