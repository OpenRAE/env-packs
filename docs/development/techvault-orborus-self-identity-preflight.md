# TechVault Orborus self-identity boundary

Issue #331 reports that a realization of the TechVault scenario could not
start Shuffle workers because Orborus did not receive the native identity of
its own holder. The missing value is real, but it is not portable scenario
content.

This note applies the ownership test established by issue #337: a scenario
declares what participants encounter, the experiment to run, and the data or
evidence it requires. A realizer chooses and operates the apparatus used to
produce that environment. The portable pack must not describe the realizer's
own naming or bootstrap machinery.

## Decision

TechVault does not declare `ORBORUS_CONTAINER_NAME`, a native holder name, or
a `value_from` selector for either one. RAES does not need a new environment
value-source semantic for this case.

The responsibilities remain:

| Concern | Owner |
| --- | --- |
| Orborus, the Shuffle services, their in-world relationships, workflow content, and required evidence | The TechVault scenario, expressed with RAES SDL |
| The meaning and validation of those portable declarations | RAES |
| Allocation of native process or container identities and any realization-only bootstrap configuration needed by the selected implementation | The realizing backend |
| Observation that the realized environment met the admitted scenario and evidence requirements | The realizing backend, reported through RAES-owned contracts |

The native identity is not an authored fact about the game world. It is an
address chosen by one realization so its own components can find each other.
Another conforming backend may use a different name, a different isolation
mechanism, or no container holder at all. Requiring the pack to carry that
choice would make the scenario select runtime implementation.

The same distinction applies even though `ORBORUS_CONTAINER_NAME` is a
product-recognized environment key. A backend may use that key while realizing
the selected Orborus image, but its need to do so does not turn the resolved
native value or its injection mechanism into scenario content. Product-specific
bootstrap handling belongs behind the backend's implementation boundary.

## Existing portable contract

The TechVault SDL already declares the parts that affect the scenario:

- the Orborus node and its exact image;
- the in-world Shuffle backend relationship;
- exact worker and application image inventory;
- workflow execution and cleanup settings;
- the in-world Docker control endpoint and its RAES orchestration-authority
  classification; and
- the scenario assertions and evidence requirements used to judge the exercise.

It deliberately declares an open realization below those authored facts. The
pack therefore does not promise a complete operating-system, process,
namespace, or bootstrap description. A backend may add machinery below the
portable contract, but it may not contradict the declared content or treat
backend-added state as authored SDL.

The existing `_assert_shuffle_orborus_contract()` test keeps the Orborus
environment set closed. Issue #331 adds an explicit regression assertion that
the native-holder environment key and runtime-derived binding remain absent.
That is the correct static test in this repository: adding the binding would be
the regression.

## Runtime acceptance boundary

Pack validation can prove that TechVault:

- contains no backend-native name or self-identity binding;
- preserves its exact in-game Orborus and Shuffle content;
- carries no predicted child observations; and
- remains valid under the pinned RAES release.

It cannot prove how a backend allocates a native name, joins a worker to an
isolation namespace, selects a daemon, or injects implementation bootstrap
configuration. Nor can this repository's static checks prove that a live
workflow completed or produced a correlated case. Those are realization and
live-conformance observations.

A backend claiming support for this scenario must either realize the selected
Orborus image successfully using its own machinery or reject the scenario
before side effects with a bounded diagnostic. It must not ask the pack to
choose a native name, encode a backend naming convention, or pretend that a
portable node id is the observed native identity.

## Security and reliability guardrails

- A native identity is not a credential or authority grant. The existing RAES
  orchestration-authority and control-interface declarations remain the only
  portable authority claims.
- Native allocation, collision handling, namespace selection, and stale-name
  detection remain backend responsibilities and fail closed.
- Runtime diagnostics must not dump complete environment maps, credentials,
  host paths, or raw engine responses.
- A runtime may record its resolved native identity in realization evidence,
  but it must not write that value back into the authored pack.
- Static validation performs no host, daemon, namespace, or backend lookup.

## Rejected alternatives

- Hardcoding a native name in the TechVault SDL.
- Adding a RAES self-identity value source solely to transport a realization
  choice through the scenario.
- Reusing generated artifacts for a transient native allocation.
- Treating the portable node id, hostname, container id, or network alias as an
  interchangeable native identity.
- Adding predicted workers or application containers to authored
  `realized_children`.
- Making live backend behavior an env-pack release claim.

## Consequences

Issue #331 requires no TechVault SDL change, dependency update, pack schema, or
RAES semantic extension. The portable contract was already correct to omit the
value; this record and its regression guards prevent the reported runtime
failure from reversing the dependency direction.

No ADR is required. ADR 0009, ADR 0036, the public ownership boundary, and the
issue-337 precedent already establish the governing rule.
