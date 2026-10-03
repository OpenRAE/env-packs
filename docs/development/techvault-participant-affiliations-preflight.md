# TechVault participant affiliations preflight

Issue #401 is a compatibility correction to first-party RAES content. RAES owns
the agent affiliation shape and the parse, compile, and admission rules. This
repository owns the two TechVault pack copies, their byte-bound associated
artifacts, and the release that makes the corrected study pack consumable. No
pack-owned participant schema, migration alias, or admission policy is needed.

## Contract and scope

Use one compatible **published** RAES release as the exactly pinned dependency
and as the authority in the regression. The study pack's three agent
declarations must use its `affiliations` contract. The base TechVault pack also
declares `entity` on its two agents; a pin change that rejects that field must
bring those declarations forward as well, because hosted-pack and package tests
validate both packs. Compare the final parsed agent affiliations with the
intended `study-control`, `red-team`, and `blue-team` entities. Do not treat a
syntactic rename as proof that authority or audience is unchanged.

Affiliation identifies an agent's relation to an entity. It does not grant the
controller authority or participant access. Preserve the separate
`authority_anchors`, `operating_scope`, `interactive_access`,
`observation_boundaries`, inject source and recipients, delivery policies,
mixed-control transitions, evidence requirements, and the authored red-start,
red-stop, blue-start, blue-stop order. The existing study regression checks the
compiled addresses and ticks; it needs a RAES-owned admission check of the
participant delivery bindings and their authority and exposure boundaries.
That admission test should use a deterministic, non-secret compatible fixture,
not backend credentials or a live provider session. A passing `validate_pack`
or successful compile alone does not establish admission.

## Cross-cutting guardrails

| Layer | Existing authority and constraint |
| --- | --- |
| SDL shape and semantics | `raes.parse_sdl_file`, `instantiate_scenario`, `raes_processor.compiler.compile_runtime_model`, and the published RAES admission contract. Use their public models and diagnostics; add no local SDL DTO, validator, exception hierarchy, or fallback for `entity`. |
| Pack validation | `validation.validate_pack` is the silent consumer result. `content_ci` adds trusted author checks. Keep their bounded, payload-free diagnostic and logging behavior; do not route foreign packs through pack-local executable tests. |
| Filesystem and content identity | `_pack_fs`, `digest.validate_pack_content_manifest`, and `digest.pack_content_digest` guard contained reads and exact inventory. `tools/refresh_pack_sdl_binding.py` is the SDL-only authoring path that retargets surviving external-concept subjects and rebinds their manifest members. Use `derive_pack_content_manifest` when another member's bytes or inventory change. Verify the resulting digest from the final tree; never hand-edit hashes or claim a digest from unvalidated bytes. |
| Concepts and schemes | ADR 0038 and RAES `admit_external_concept_bindings` own concept admission. The scheme snapshot is an independently pinned source, not a digest of agent affiliations. Preserve its bytes when its source and concepts are unchanged; revalidate it and its manifest member after rebinding. |
| Exposure and secrets | Keep `pack.compatibility.yaml` artifact boundaries, release participant-view and leak gates, RAES observation boundaries, and existing generated-secret references. The SDL has no provider credential, host path, environment binding, or executable launch command. Test fixtures, CLI argv, logs, and errors must contain no secret values or instruction payload dumps. |
| Publication | `pyproject.toml` includes both packs in wheel and sdist. Use the hosted-pack validation and release checks plus packaged-content tests. Release Please owns the project version and `CHANGELOG.md`; the `dev` to `main` promotion and release workflow own publication. |

The extensibility seam is the pinned RAES public contract and its admission
fixture: a later participant profile or affiliation variation should change
authored RAES data and the fixture, not introduce a TechVault-specific parser or
hard-code Claude Code into a generic pack validator. Preserve the
`participant-implementation-manifest:claude-code` reference as authored study
data. Backend mapping of that reference and provider session lifecycle remain
outside this repository.

## Published RAES 6.0.1 compatibility

RAES 6.0.1 admits participant delivery addresses as temporal subjects and
requires agent affiliations. It also accepts required evidence media types only
when a registered output contract can validate their content. The two TechVault
packs previously required `text/plain` or `application/x-ndjson` for three
evidence needs without a matching RAES output contract. Leave their encodings
unspecified while preserving each requirement's source, scope, channel,
redaction, integrity, retention, and loss-disclosure intent. Do not relabel a
plain-text transcript as JSON merely to satisfy the parser.

## Boundaries

No changes to the four-inject study design, evidence meaning, scoring, telemetry,
backend admission policy, runtime controller, credential delivery, or live
qualification are implied. Do not conflate affiliation with authorization,
observation with instruction delivery, the pack set digest with an SDL or scheme
digest, or a validated local checkout with a published package. Do not encode
APTL-specific catalog paths or backend commands into canonical pack metadata.
