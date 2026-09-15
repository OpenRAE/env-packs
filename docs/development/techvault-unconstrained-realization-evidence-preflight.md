# TechVault unconstrained realization-evidence preflight

Issue #365 is an observation-method defect, not permission to remove TechVault
state or evidence. TechVault requires its declared state to be realized and
authoritatively evidenced, but does not choose whether that evidence is read
from a guest, a daemon, or another native control plane. The realizing backend
chooses the least intrusive valid method within the authored realization scope.

The checked-in SDL already expresses the correct author intent: it has an open
realization default, no realization constraints, no module imports/composition,
and no guest- or daemon-observation declaration. Its evidence `source_refs`,
`source_class`, observation boundary, channels, and artifact roles describe what
evidence is needed and what it concerns; none is an observer-location selector and none
should be removed to simulate an unconstrained method.

## RAES contract resolution and governing decision

RAES 5.0.0 includes the upstream resolution from rae#1285. When the author does
not select an observation source, the processor now retains the applicable
presence or configuration verification scope while compiling
`CompiledRealizationRequirement.required_observation_strength` as `None`.
Admission therefore accepts any authoritative observation strength that
satisfies the scope instead of deriving a guest- or daemon-observed floor from
the concern kind.

This is consumed here by advancing the exact RAES pin and adding regression
coverage against the actual TechVault compilation. No SDL field or pack-local
compatibility setting is necessary: the checked-in omission already expresses
the intended author choice. An absent required strength is distinct from
`ObservationStrength.NONE`; verification scope remains present, missing
observation support still fails admission, and driver-reported state alone is
not promoted to authoritative corroboration.

No new ADR is required. [ADR 0009](../decisions/adrs/0009-scenario-packs-subordinate-to-aces.md)
already requires RAES-owned semantics to be fixed upstream and consumed here,
while [ADR 0036](../decisions/adrs/0036-publish-first-party-content-with-env-packs.md)
permits TechVault to publish here without gaining special semantics or backend
privileges. Older TechVault preflights describing mandatory containers are
historical context, not authority to restore a substrate constraint.

## Boundaries that must remain distinct

| Concern | Authority and guardrail |
| --- | --- |
| Declared state and evidence need | TechVault authors existing RAES SDL runtime facts, propositions, assertions, observation boundaries, and evidence requirements. Keep their coverage, redaction, integrity, retention, and loss-disclosure requirements intact. |
| Realization verification | RAES owns `CompiledRealizationRequirement`, verification scope, observation strength, strength satisfaction, and admission diagnostics. Env-packs must not copy or override that policy. |
| Observation offer and selection | The backend declares the actual source/provenance and selects the least intrusive authoritative offer that completely covers the claim. Native readback must corroborate realized state at the required scope; echoed desired configuration, a successful write, or presence alone does not prove configuration. A pack-local source label is not a backend capability. |
| Realization closure | RAES realization designation decides whether additional apparatus may exist. An unconstrained observation method does not open a closed scope. In an open scope, apparatus is added only when needed and is included in realized-form reporting. |
| Experimental evidence | The four TechVault evidence requirements remain scenario obligations. In particular, `redteam-session-transcript.source_class: apparatus` identifies an evidence-source class; it is not the realization-verification strength at issue. |

## Canonical repository surfaces

- `pyproject.toml`, `requirements/runtime.txt`, and `uv.lock` are the exact RAES
  dependency authorities. Keep them aligned through the existing lock
  workflow; `requirements/runtime.txt` records its hash-generation command.
  `tests/test_dependency_pinning.py` also requires agreement across locks
  co-installed by CI. Preserve hash-locked installs, audit/SBOM controls and the
  upstream Python floor; do not vendor or patch RAES processor code here.
- `raes.parse_sdl`, `raes.parse_sdl_file`, `validate_pack()`, and the author-CI
  composition in `content_ci.py` remain the SDL shape and semantic gates. Do
  not add a copied SDL schema, parser, enum, DTO, or exception hierarchy.
- `packs/techvault/validation/validate_techvault.py` and
  `tests/test_techvault_pack.py` are the existing TechVault-specific contract
  guards. Keep observation-method assertions narrow and based on RAES-owned
  fields; do not turn the validator into a second operational-verification
  policy engine or conflate its realization-method guard with evidence method.
  The existing guard rejects all realization constraints and runtime environment
  overrides: reconcile any future upstream carrier narrowly without weakening
  the prohibition on backend implementation details.
- `raes_processor.compiler.compile_scenario_runtime_model` is the existing
  repository integration seam that exposes the derived realization
  requirements. Compatibility proof should inspect the actual TechVault
  compilation rather than infer behavior from YAML key absence or duplicate
  the upstream concern-kind table. Preserve verification scope and assert the
  accepted unconstrained representation, not brittle totals for open-world
  generated requirements.
- SDL bytes bind pack content identity; semantic SDL changes also stale external
  concept subject bindings (ADR 0038). Use `tools/refresh_pack_sdl_binding.py` to
  retarget surviving subjects and derive the associated-artifact checksum, size,
  and set digest. Validate bindings after a RAES upgrade too, since canonical
  model changes can affect subject identity. `digest.py` owns
  `validate_pack_content_manifest()`, `derive_pack_content_manifest()` and
  `PackDigestError`; changed membership needs full manifest derivation, not an
  SDL-only refresh. Never hand-edit coupled identity values.
- The normal `raes-pack-validate --packs-root packs`,
  `raes-pack-release check --packs-root packs`, distribution-content, and full
  repository gates remain the publication proof. `release.py`, `publication.py`,
  `verify.py`, and `distribution.py` own release evidence and verification; pack
  signatures/SBOM provenance are distinct from runtime realization evidence.
  Backend admission with native readback needs a downstream integration test
  because this repository carries no affected backend manifest or runtime.

## Cross-cutting security and reliability gates

| Layer | Required behavior |
| --- | --- |
| RAES shape and semantic validation | Use only the pinned RAES representation. Preserve closed model shapes, realization designation, concern scope, evidence references, and semantic diagnostics. An unknown convenience key must fail rather than be ignored. If composition is later introduced, inspect the resolved policy through RAES rather than relying on root-key absence. |
| Backend admission and runtime corroboration | Reuse RAES `RealizationObservationCapabilityModel`, `has_required_observation_support()`, scope/strength satisfaction and runtime corroboration. Keep verification scope mandatory where currently required. Check both compiled requirements and projected authority: clearing both scope and strength would bypass corroboration. No monkeypatch or diagnostic suppression. |
| Consumer validation and imports | `validate_pack()` uses bounded text parsing and denies imports; it executes no pack code. The author lane admits file-backed parsing and RAES-owned import resolution. Preserve parser limits, import containment, registry/trust/lock controls and cache/network restrictions when advancing RAES (ADR 0011/0013). |
| Pack schemas, provenance and visibility | Reuse `resources/schemas/`, `validation.py` identity/visibility checks, provenance secret-shape checks, and `content_ci.py` leak/anti-extension gates. Keep compatibility runtime profiles empty; they cannot carry an observation policy. Operator evidence/configuration must not become participant-visible release content. |
| Author validator process | Reuse `content_ci._run_pack_process()` and its admitted roots, literal argv, process-group timeout and output caps. This is trusted author execution, not a sandbox: it inherits the environment. Run without production credentials and emit only value-free diagnostic details. |
| Artifact and filesystem safety | Reuse `_pack_fs` descriptor-anchored, bounded, no-follow reads and full associated-artifact byte binding. The same admitted SDL bytes must be parsed, bound, packaged, and released. |
| Authentication, secrets and environment shapes | No new credential or environment binding is required. Preserve generated-secret references, per-run flag variables and current TechVault auth contracts; use synthetic flags for compilation tests. Do not add runtime environment keys to encode this policy. Observation capability records carry no credentials; native responses and secrets must not enter argv, diagnostic output or unredacted portable evidence. |
| Authoring/MCP, if exercised | Reuse host-granted `AuthoringSession` operations, `_authoring_tools` closed request shapes, `_bounded()`, `_authoring_safety.admit_members()` and `_safe_diagnostics()`. No new endpoint, grant or transport is needed. Its existing SDL preview uses a reference stub manifest and has a 64 KiB input limit; it is not a full-TechVault backend admission test. |
| OS and network exposure | Add no process, guest probe, daemon, sidecar, socket, host path, port publication, capability, mount, Docker requirement, or observability stack. A compatibility choice is data in an RAES-owned contract, not apparatus shipped by the pack. |
| Error and logging envelopes | Keep libraries silent and diagnostics bounded and payload-free. Reuse `Diagnostic`/`ValidationResult`, RAES `SDLError` classification and the existing transport envelopes; unexpected library defects remain failures, not invalid-input success paths. Do not add exception-prose parsing or report absolute paths, native readback bodies, or backend exceptions. |
| Persistence and reporting | This repository adds no runtime persistence. A backend may persist its existing evidence/result records, and any apparatus admitted under open scope must appear in its existing realized-form report rather than mutate the authored SDL. |

The extensibility seam remains in RAES realization verification, independently
of verification scope and realization closure. RAES defines the omission
semantics and any supported author-selected floor, including precedence through
composition; this repository prescribes no new field or schema. TechVault does
not need edits when another authoritative observation method becomes available.
A concern-kind switch, TechVault special case, or backend name in the pack
would foreclose that variation.

## Acceptance evidence boundary

The existing TechVault tests should exercise actual compiled requirements using
synthetic flag parameters. The full repository suite also covers templates,
first-party kit composition, authoring and release consumers affected by a
global RAES pin change. Absence-of-YAML-key assertions and a reference stub plan
are insufficient evidence of native-readback admission.

Integration evidence must identify the released pack digest and the RAES and
backend versions used. A package dependency bump alone cannot update the RAES
processor in an independently deployed backend. Acceptance requires complete
authoritative native readback to pass while missing, partial, wrongly scoped
or uncorroborated evidence still fails. Verify closed-scope apparatus rejection,
selection of existing valid native observation under open scope, and disclosure
of any necessary added apparatus in realized-form reporting. Exercise these
scope variations in upstream/backend tests without changing TechVault's authored
open default. Static release checks do not establish live realization or
upgrade the pack's readiness status.

## Non-goals and rejected shortcuts

- Do not remove or relax runtime facts, propositions, assertions, evidence
  requirements, source/scope references, redaction, integrity, retention, or
  loss disclosure to avoid a provenance mismatch.
- Do not remove forwarding agents or other authored runtime concerns merely
  because current RAES derives a floor from their kinds.
- Do not use `observation_demand`, `source_refs`, `source_class`, channels,
  artifact roles, prose, compatibility-manifest runtime profiles, or a magic
  backend capability name as a realization-observation override.
- Do not change `realization.default: open` as a proxy for evidence strength,
  and do not interpret open realization as permission to add unnecessary
  observation apparatus.
- Do not add a local schema, planner rule, concern-kind table, compatibility
  shim, Docker substrate, guest probe, daemon, sidecar, or observability stack.
- Do not teach a backend to special-case `techvault`; it should consume the
  generic RAES requirement and report its actual authoritative observation.
- Do not hand-edit the project version, `CHANGELOG.md`, binding digests, member
  checksums, sizes, or associated-artifact set digest.

RAES 5.0.0 supplies the required unconstrained-collection semantics while
keeping verification mandatory. The environment pack consumes that authority;
it does not encode a local exception or duplicate the upstream admission rule.
