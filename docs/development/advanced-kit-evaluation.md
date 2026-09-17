# Advanced reusable-content evaluation

Issue [#224](https://github.com/OpenRAE/env-packs/issues/224) evaluates which
reusable content belongs in a kit, a RAES module, a delivery profile, a complete
pack, or documentation. It does not implement candidate families.

Evaluation baseline: 2026-09-17, repository commit
`6dd6ae0117079ab8881a9bdb2bb8f540b4fdeaf1`, pinned `raes==5.0.0`. Follow the
[preflight guardrails](advanced-kit-evaluation-preflight.md). Candidate names
are descriptions, not new schema fields or controlled vocabulary.

## Evidence and limits

Author feedback is not yet available. This is an engineering evaluation of
concrete author tasks against the shipped kit and RAES contracts. It identifies
reuse opportunities and ownership boundaries without claiming adoption,
measured savings or backend qualification. The task probes below are design
questions, not usage findings.

| Evidence | Observation | Limit |
| --- | --- | --- |
| E1: [infrastructure issue #190](https://github.com/OpenRAE/env-packs/issues/190), #226, #232 and [ADR 0036](../decisions/adrs/0036-publish-first-party-content-with-env-packs.md) | Tooling and the complete 38-release collection are available in the evaluated repository revision; #190 closed on 2026-08-01. | Availability is the repository source, not a separate registry or backend claim. |
| E2: [author walkthrough](../../tests_integration/kit_author_walkthrough.py), run through the [runbook](kits-integration-runbook.md) | All 25 checks passed: discovery, inspection, preview, five-kit composition, parameter update, replacement, removal, ordinary-pack validation and release checking. | Controlled author-workflow exercise, not feedback from independent authors. |
| E3: [published-kit tests](../../tests/test_published_kits.py) | All four tests passed, including default/variation composition for all 38 releases and a representative seven-kit environment. | Static composition and packaged-content checks, not proof of connected services. |
| E4: [TechVault](../../packs/techvault/README.md) and authoring corrections [#354](https://github.com/OpenRAE/env-packs/issues/354), [#373](https://github.com/OpenRAE/env-packs/issues/373) | Concrete scenario content requires in-world service relationships while leaving realization methods and host exposure to the backend. | Complete-pack experience; not evidence that TechVault was assembled using the kit workflow. |
| E5: [delivery-bundle contract](../../src/raes_env_packs/resources/contract/pack-layout.md#e-delivery-profiles-optional) and [release tests](../../tests/test_release.py) | An existing carrier and checks separate audience exposure, participant material and restricted operator content. | Not a demonstrated demand for new reusable teaching material. |

### Author task probes

Evaluate the smallest useful unit against these independently framed tasks.
Each task separates what an author wants to express from how a backend runs it.

| Task | Potential reusable unit | What stays with the scenario |
| --- | --- | --- |
| Give an assistant a bounded role in an ordinary business process | RAES agent, authority and behavior references | Its instructions, goals, permitted actions and success meaning |
| Require identity verification before approving a service request | A coherent RAES action contract with refusal cases | The verification policy, actors and consequences of approval |
| Schedule routine work and notify a second role of its result | Linked RAES events/workflow with explicit inputs and outputs | Purpose, timing, branches and narrative |
| Establish that a declared artifact reached the intended recipient | A claim joined to RAES conditions and evidence requirements | Which artifact, recipient and observations satisfy the claim |
| Assess service continuity across a disturbance and restoration | A complete pack with baseline, disturbance and recovery claim | Impact bounds, safety, restoration method and participant purpose |
| Compare two processing methods over controlled input data | A composition of worker, notebook, registry and storage infrastructure | Trial design, dataset meaning, evaluation method and conclusions |
| Assemble an order-processing or records-exchange environment | Static service modules, data assets and explicit relationships | Domain workflow, records vocabulary, roles and intended outcome |
| Describe a sensor/gateway boundary with constrained writes | A protocol-specific component once its contract is demonstrated | Physical dynamics, safety assumptions and operating context |
| Connect monitoring and case-handling services | A documented composition over independently replaceable kits | Incident, detection meaning and response decisions |
| Present one task with hints to one audience and without hints to another | Existing delivery bundles with separated participant/operator material | The same RAES scenario and objective meaning |

### What the kits actually contain

All 38 inspected 1.0.0 releases have a RAES module, two materialized supporting
assets (seed inventory and integration notes), parameter cases, a README and
associated-artifact byte binding. Each exports nodes and content; most export
accounts, and the identity kits add identity/relationship declarations. All have
`deployment_profile`, `service_label`, and one concern-specific parameter.

For example, the [evaluation worker](../../kits/infrastructure.python-evaluation-worker/1.0.0/module.sdl.yaml)
declares `queue_name`, a Python service node, an operator account and seed objects
named input/result contract. It does not implement an evaluation method. The
[workflow orchestrator](../../kits/infrastructure.workflow-orchestrator/1.0.0/module.sdl.yaml)
declares a service and seed inventory; it is not a reusable RAES story or workflow.
The [Suricata seed](../../kits/infrastructure.suricata-network-intrusion-detection-sensor/1.0.0/assets/seed.yaml)
names capture/rules/output objects without proving sensor attachment or traffic.

The inspected modules also carry explicit realization constraints, such as the
evaluation worker's exact virtual-machine substrate, and component inventory
marks immutable software selection unresolved. A future example must preserve
and disclose those facts. A kit label, product name, seed count or passing parse
does not establish a new behavioral capability or unrestricted portability.

## Candidate ranking

Scores are engineering judgments about the narrow task in each row.
They are not measured demand. Use four ordinal dimensions, each from 1 to 3:

- **A, author value:** 3 for a composition need shared by several task probes;
  2 for one concrete task; 1 for a task whose usable boundary is unresolved.
- **P, portability:** 3 for existing source/packaging reuse without new
  realization assumptions; 2 for scenario or substrate constraints; 1 for
  unproven domain/physical constraints.
- **C, cohesion:** 3 for one separable task and existing authority; 2 for a unit
  needing an explicit infrastructure/purpose split; 1 for no demonstrated seam.
- **M, maintenance cost:** 1 for guidance over existing contracts; 2 for maintained
  examples/assets; 3 for coupled behavior, evidence, domain or platform work.

Priority is `A + P + C + (4 - M)`, with equal scores sharing a rank. Evidence and
ownership decide admission independently of that score.

| Rank | Candidate | A | P | C | M | Score | Disposition and status |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | Teaching, exercise, or assessment overlays | 3 | 3 | 3 | 2 | 11 | `profile`: approve a minimal two-audience example over existing bundles; no generic assessment overlay (E5). |
| 2 | Security operations and defensive-tooling assemblies | 3 | 2 | 3 | 2 | 10 | `documentation`: a narrow composition guide over existing kits; no assembly kit (E2–E4). |
| 3 | Research and evaluation apparatus | 2 | 2 | 2 | 2 | 8 | `documentation`: infrastructure recipe prospect; standard apparatus deferred (E3). |
| 3 | Agents and behavior specifications | 2 | 2 | 3 | 3 | 8 | `module-only`: retain RAES ownership; no behavioral kit approval (E4). |
| 3 | Objectives, conditions, assertions, and evidence requirements | 2 | 2 | 3 | 3 | 8 | `module-only`: preserve the coherent claim and its evidence; no generic objective kit (E4). |
| 6 | Action contracts and participant interaction | 2 | 2 | 2 | 3 | 7 | `module-only`: role/action boundary; reusable family deferred (E4). |
| 6 | Failure, recovery, continuity, and resilience patterns | 2 | 2 | 2 | 3 | 7 | `complete-pack`: preserve purpose and recovery evidence; new reference pack deferred. |
| 8 | Injects, events, stories, and workflows | 2 | 1 | 2 | 3 | 6 | `module-only`: coherent RAES content; reject a universal narrative template. |
| 8 | Domain-specific environment assemblies | 2 | 1 | 2 | 3 | 6 | `complete-pack`: retain domain context; no canonical domain-kit layer (E4). |
| 10 | Operational-technology and cyber-physical components | 1 | 1 | 1 | 3 | 4 | `do-not-standardize`: defer admission without a portable component and qualification evidence. |

`kit` remains appropriate for proven, purpose-neutral static infrastructure that
needs supporting pack assets and lifecycle operations beyond a RAES module.
None of these broader families currently justifies changing that carrier.
`module-only`, `profile` and `complete-pack` route content to existing authorities;
they do not approve publication of a new reusable family. Deferral is a decision
status, not a seventh carrier.

## Candidate boundaries and evidence needed

| Candidate | Task, parameters and exports | Assets, tests and limitations that travel with it | Decision rationale and reconsideration |
| --- | --- | --- | --- |
| Defensive tooling | Connect existing Wazuh, Suricata and TheHive infrastructure. Parameters include `enrollment_group`, `ruleset_name`, `organization_name`; RAES exports nodes, accounts and seed content. | Existing seed/integration assets, provenance, component scope, constraints and variation tests; a guide adds a checked pack-root relationship and lifecycle example. | Documentation avoids coupling independently versioned kits. No flowing telemetry, case creation, incident or backend-readiness claim. Reconsider a kit only after distinct packs demonstrate the same separable capability and constituent replacement. |
| Teaching/assessment | Select audience material for one unchanged scenario. `profile` specifically means `profiles/bundles.yaml` plus the thin `pack.yaml` index; no new SDL exports. | Shared briefs, hints, facilitator notes, rights, boundary declarations and release/leak checks. | Approve a minimal guided/unguided example over the current contract, validating distinct exposure and restricted separation. A reusable assessment overlay still needs two demonstrated uses. Objectives, scoring and scenario behavior are not profile selection. Publication and backend profiles are different contracts. |
| Research/evaluation | Compose notebook, worker, registry and storage infrastructure. Module parameters include `workspace_name`, `queue_name`, `registry_namespace`, `bucket_name`; bind exported service nodes/accounts/content. | Seed assets, dataset rights, inventory/provenance, component limits and static composition tests. | Experiment design, trials, evidence and interpretation remain RAES/pack-owner content. A recipe needs two concrete author tasks with shared inputs/outputs; the worker name does not establish a reusable evaluation method. |
| Agents/behavior | Reuse a role-bound behavior where RAES permits it. Potential parameters bind roles, targets and bounded task inputs; exports remain exact RAES agent/behavior symbols. | Prompts/tool assets, permissions, provenance, restricted instructions, behavior tests and execution limits. | Actor renaming does not remove purpose. Require two validated consuming scenarios and explicit authority/access boundaries before approving a reusable module family. No agent runtime or prompt dialect here. |
| Objectives/conditions/assertions/evidence | Reuse a coherent claim with its conditions and evidence. Potential parameters bind subjects/thresholds; keep the related RAES symbols together. | Participant-safe descriptions, restricted examples, positive/negative semantic cases, provenance and evidence limitations. | Do not detach an objective label from its meaning or turn an implementation observation into success. Require the same claim in distinct scenarios; no pack-owned scoring/oracle vocabulary. |
| Action/interaction | Reuse actor authority, target, inputs, preconditions and outcomes together. Potential module parameters bind actors/targets; export RAES action symbols. | Tool assets, rights, access assumptions, acceptance/refusal cases and visibility constraints. | Standardization needs two consumers preserving the same action contract under changed bindings. Credentials/session brokering are not author parameters; semantic gaps go upstream. |
| Resilience | Keep disturbance, continuity and recovery claim in a complete RAES pack. Target/load/time variation is scenario-owned; no proven generic exports. | Disturbance assets, safety limits, recovery criteria, evidence, provenance and normal/failed recovery cases. | Runner/observability infrastructure does not prove a recovery experiment. Require a working scenario and repeated task; backend fault injection/rollback are not this carrier. |
| Injects/events/stories/workflows | Preserve linked actors, timing and ordering in ordinary RAES modules. Potential parameters bind roles/targets/time; export actual linked RAES symbols. | Narrative assets, timing assumptions, branch/order tests, evidence and rights. | Reject universal templates based on superficial structure. Reconsider a narrow module after two examples preserve meaning under substitution. External playbook translation remains [#207](https://github.com/OpenRAE/env-packs/issues/207). |
| Domain assemblies | Keep a concrete purpose and environment together. Scenario-owned RAES parameters; no generic kit exports. Static records, transaction or message-exchange services may be independently reusable. | Domain assets, rights, concept bindings, tests, limitations and participant proof. | Separate a useful service from a full domain topology. Before a service becomes a kit, require a redistributable implementation, meaningful input/output variation and composition evidence. Complete assemblies need a concrete purpose and maintenance owner; classifications remain RAES-owned under ADR 0038. |
| OT/cyber-physical | No demonstrated reusable seam yet; protocol, topology, timing and sensor/actuator parameters/exports remain hypotheses. | Exact assets/provenance, redistribution rights, conformance/negative tests and physical/safety limits would be required. | Defer until a concrete component and two materially different uses establish a portable RAES boundary. Simulation is not physical equivalence; neither backend drivers nor a domain ontology are approved. |

## Approved implementation issues

[Issue #378](https://github.com/OpenRAE/env-packs/issues/378) specifies the narrow
defensive-tooling documentation slice. It names three existing releases, the
walkthrough/test basis, pack-root relationships, lifecycle checks, visibility
constraints and static-evidence limits. It creates no new kit family and is
separate from #190.

[Issue #379](https://github.com/OpenRAE/env-packs/issues/379) specifies a minimal
guided/unguided example over the existing delivery-bundle contract. It requires
one unchanged RAES scenario, independently authored synthetic content, distinct
participant views, restricted facilitator material, actual release-view
inspection and negative exposure checks. It introduces no profile vocabulary,
assessment semantics or runtime behavior.

These approve examples of existing contracts, not new behavioral or domain kit
standards. No implementation issues are opened for the deferred families until
their named working basis is available. Missing general infrastructure
primitives remain the separate qualification scope in
[#225](https://github.com/OpenRAE/env-packs/issues/225).

## Admission guidance

The [public content strategy](../public/kit-content-strategy.md) now explains
carrier choice, a task/source/variation admission record, explicit exports,
ordinary-source lifecycle checks and the limits of static evidence. E2 supports
the lifecycle guidance; E3 supports composition and packaged material; E4
supports purpose and realization separation; E5 identifies the audience carrier.
These changes are prose guidance, not new executable admission rules.
