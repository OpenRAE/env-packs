# Two-audience delivery-bundle preflight

Issue #379 is a public walkthrough and executable, synthetic authoring example
over the existing delivery-bundle contract. It does not add a profile type,
schema, selector, template engine, scenario semantic, checked-in example pack,
or runtime feature. ADRs
[0009](../decisions/adrs/0009-scenario-packs-subordinate-to-aces.md),
[0030](../decisions/adrs/0030-separate-public-and-developer-documentation.md),
[0031](../decisions/adrs/0031-compose-beginner-safe-pack-checks-from-existing-authorities.md),
and [0036](../decisions/adrs/0036-publish-first-party-content-with-env-packs.md)
already decide the architecture; no new ADR is needed.

## Contract and authority boundary

Start from the shipped `raes-pack-new --route minimal` result in a temporary
catalog and add an ordinary compatibility projection plus the existing profile
layer. The minimal route's one RAES start-state document remains byte-for-byte
unchanged. Shared participant prose may explain the task in safe language, but
it is not another objective contract. RAES owns the SDL language, processor,
and runtime; the environment pack owns its particular hydrated scenario,
including the objectives, conditions, evidence, and participant behaviour it
authors with that language. Bundle selection changes neither layer.

The authoritative profile declaration is `profiles/bundles.yaml`. Use the
wizard-emitted `environment-pack-profile-bundles/v1` version and only the
existing `id`, `audience`, `runtime_profiles`, `shared_includes`,
`participant_entrypoints`, and `operator_entrypoints` vocabulary needed by the
contract. `pack.yaml.contents.profile_bundles` and its `profile_bundles` block
are a thin presence/index projection. `pack.compatibility.yaml` is the existing
release/visibility projection. Neither projection becomes a second bundle
manifest.

The example has one shared participant-safe objective and observation sheet, a
guided-only participant hint, an unguided participant brief without next-step
guidance, and facilitator-only resolution material under each bundle's
`operator/` root. Participant and operator paths must be disjoint in both the profile tree and
`artifact_boundaries`. The provenance ledger classifies the new authored roots
and records them against the existing original-design source; it does not make
an authenticity, safety-at-runtime, or educational-effectiveness claim.

There is intentionally no packaged schema for `profiles/bundles.yaml` today.
Do not create one for this example or treat the loose historical fixture shape
in `tests/test_release.py` as a schema. The current contract is the layout
document plus release joins. A malformed-selection negative case should be a
bounded contract mismatch already rejected by `raes-pack-release` -- for
example, a supported compatibility bundle absent from the canonical manifest
or an entrypoint that is missing -- not a new parser or validation dialect.

## Do not conflate the two view axes

`release.bundle_participant_views()` derives each selected audience's exposure
set: shared includes plus that bundle's participant entrypoints.
`release.build_release()` separately stages the compatibility manifest's
participant, operator, restricted, and commercial boundary tiers. Guided and
unguided are delivery bundles; participant and operator are release views.

The walkthrough must inspect the real files named by both derived bundle
exposure sets, then build and inspect the boundary-split release tree. It must
show that the facilitator file is absent from both participant exposure sets
and from the staged participant tier, while present only in the staged operator
tier. It must not imply that `build_release()` materializes one directory per
bundle, call guided/unguided publication views, or implement a second copy
engine to make the wording convenient.

## Existing cross-cutting authorities

| Concern | Canonical incumbent and guardrail |
| --- | --- |
| Scenario authority | The exact `raes` pin in `pyproject.toml` and the public RAES parser used by `validation.py` and `wizard.py` own the SDL language and its processing/runtime semantics. The generated environment pack owns its concrete hydrated scenario. Snapshot those SDL bytes and prove profile authoring and selection do not change them. Do not add objectives, nodes, topology, scoring, oracle, telemetry, or behaviour fields for this exposure-only example. |
| Starter workflow | `wizard.py`, its `minimal` route, and `raes-pack-new`. Exercise the shipped generator in a temporary catalog; do not copy the generated base pack into a fixture or add a special two-audience route. |
| Bundle contract | Section E of `resources/contract/pack-layout.md`, `release.PackContracts`, `lint_pack`, `bundle_participant_views`, and `smoke_pack`. Reuse these joins and exposure rules; a pack-local `profiles/validate_*.py` may only be a thin adapter over the existing release checks. |
| Config shape | `pack.yaml`, `pack-compatibility.schema.yaml`, `profiles/bundles.yaml`, and the provenance schema. Keep the bundle manifest canonical, the pack index thin, and compatibility rows synchronized. Do not add an example-only DTO, schema, or vocabulary. |
| Static validation | `validation.validate_pack` / `_validate_pack_for_author_ci`, `content_ci`, and the exact RAES parser. Preserve bounded strict metadata parsing, duplicate-key rejection where the shared validator provides it, full compatibility/provenance schema checks, and the anti-extension gate. |
| Visibility and release | `validation._boundary_overlaps`, `content_ci._participant_roots` and its redacted token scan, `release.smoke_pack`, `_stage_views`, and `build_release`. Shared and per-bundle participant roots are scanned; operator content is excluded from bundle exposure and staged under the operator boundary. |
| Filesystem and persistence | `_pack_fs` for untrusted static reads and the release gate's containment/no-follow staging, fixed `0600` staged-file mode, scratch tree, and atomic promotion. The example and every negative mutation live under a temporary directory and leave no repository or external state. |
| Errors and observability | `Diagnostic`/`ValidationResult`, author-CI's bounded subprocess envelope, release CLI exit status, and the redacted leak messages. Print safe assertion labels and bounded command failures only; add no logger, exception hierarchy, raw token echo, or authored-body dump on a failure path. |
| Documentation | `docs/public/` as the sole published source, its style guide, the warning-strict Sphinx build, `test_readthedocs_config.py`, and `tools/check_docs_publication_boundary.py`. Commands need real output and the public page must be reachable from a toctree. |

The pack-local profile validator and tests run only through trusted author CI.
They must not reimplement the manifest joins, path rules, or leak patterns. The
consumer-facing `validate_pack()` remains the non-executing, descriptor-anchored
ingest boundary; a documentation example must not blur these two trust models.

## Security path through the example

The example adds no authentication or authorization surface. It is a local,
single-user author workflow over content the author just generated. A future
hosted presentation still inherits `AuthoringSession` and MCP host authorization,
controlled-root, proposal-review, persistence, and redacted-audit requirements;
bundle ids grant no actor access.

Every authored document still passes the applicable gates:

- `pack.yaml`, provenance, compatibility, and SDL pass the shared static
  validator; compatibility also passes the packaged closed schema and
  participant/restricted overlap check.
- The canonical bundle/index/compatibility joins pass release lint and smoke;
  distinctness is proven from exposure sets, not merely claimed in prose.
- `_shared/` and each `<bundle>/participant/` tree pass the existing redacted
  participant leak scan. The staged participant tier is scanned again after
  path-safe copying.
- Release staging rejects absolute paths, traversal, links, hardlinks, special
  files, and unsafe output components, writes owner-only files, validates the
  generated publication profile, and promotes only a complete tree.
- Pack-local validators/tests run with the existing timeout and retained-output
  bounds. Negative copies assert nonzero, redacted failures without printing
  facilitator answers or token values.

The material is independently written and synthetic: no credentials, secret
coordinates, environment bindings, live targets, customer data, signed URLs,
or backend settings belong in files, environment variables, process arguments,
stdout, or test fixtures. Pack and output paths are non-secret CLI arguments;
there is no sensitive parameter payload that needs a new stdin channel. The
walkthrough may display participant prose because it is deliberately public,
but should inspect restricted placement by filename and tier rather than echoing
facilitator content.

`PackContracts` is a trusted-author release reader, not the untrusted consumer
parser: it uses the fixed `profiles/bundles.yaml` path and does not supply a
standalone strict bundle schema. Keep the example small and bounded, and do not
widen this issue into parser hardening or advertise release selection as an
untrusted ingest API. Such hardening would be separate contract work.

## Verification and maintenance seam

Follow the existing `tests_integration/defensive_tooling_composition.py` pattern:
drive installed command modules against a temporary catalog and keep the safe
authored example data together. The one extension seam is the bundle table in
`profiles/bundles.yaml`; `pack.yaml` and compatibility stay projections of it.
A future third audience should require another manifest row, its explicit
content roots, and matching projection rows -- not branches in release logic or
edits to the shared scenario. Keep the integration harness's expected bundle
ids and unique/shared entrypoints in one bounded data constant so contract
version changes have one obvious maintenance point. That constant is test data,
not a new model.

Positive coverage must establish the unchanged SDL bytes, exactly two supported
bundle ids, one shared include, distinct guided/unguided participant sets,
meaningfully different authored content, no operator entrypoint in either set,
successful author validation and release checks, and correct participant versus
operator staged contents. Negative coverage mutates disposable copies to prove
that each participant view rejects restricted vocabulary and that an existing
bundle/index/compatibility mismatch fails. Existing release unit tests remain
the authority for generic identical-view, boundary-overlap, containment, and
redacted-leak behavior; do not duplicate that matrix in the walkthrough test.

## Non-goals and prohibited shortcuts

Do not add a checked-in pack under `packs/`, a reusable profile or kit family, a
new wizard route, a bundle schema, a selector service, a template engine, a
publication profile, a backend capability profile, runtime execution, grading,
scoring, benchmark results, topology, behavior, objectives, evidence semantics,
or an educational-effectiveness claim. Do not adapt a named scenario or source,
duplicate shared participant prose, place facilitator material under `_shared/`
or `participant/`, use the whole `profiles/` root as a participant boundary,
compare only filenames while claiming content differs, or infer safety merely
because the operator file was omitted from `participant_entrypoints`.

Do not hand-parse YAML in the walkthrough, copy release validation into a
pack-local script, inspect a raw facilitator answer in expected command output,
turn an expected negative case into a committed invalid pack, or weaken the
warning-strict documentation, ordinary unit-suite, pack-validation, release,
and compile gates.
