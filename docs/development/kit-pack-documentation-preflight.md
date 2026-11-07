# Kit and example-pack documentation preflight

This explanation records design guardrails for issue #659. It does not implement the documentation rewrite.
The inspected source revision is `7bc2ec6b78c684e4fae2d1ab4e63124632122370`.
The supplied issue is the delivery contract.

## Existing authorities

Use the [documentation style guide](documentation-style-guide.md) and the existing `documentation` skill.
They already define Diataxis purpose, STE review, source verification, writing checks, and narrow exclusions.
Add no new ADR, prose schema, page registry, checker, or migration framework.

This work follows the RAES-subordinate pack tooling pattern.
[ADR 0036](../decisions/adrs/0036-publish-first-party-content-with-env-packs.md) places first-party content here; RAES owns scenario semantics.
Link to RAES contracts rather than creating local rules for SDL, objectives, evidence, or runtime behavior.
Keep downstream deployment vocabulary in its existing integration context.

The base uses Python 3.14 and declares `raes>=11.0.0` in `pyproject.toml`.
The runtime lock records the tested dependency version.
Check the implementation base again; historical preflights contain older pins.
Issues #581 and #582 own Go instruction migration and cutover.

## Reader purpose and preserved sources

The inspected tree contains 269 kit Markdown files and 24 pack Markdown files.
These counts exclude prose inside structured data, scripts, templates, and archives.
They are inspection evidence, not a permanent coverage threshold.

The implementation PR needs an inventory of every maintained page and preserved artifact in scope.
Record its consumer, purpose, source revision, treatment, and reason for any exclusion.
Keep that evidence in the PR; do not create a persistent content registry.
Classify by use rather than suffix or location.
Entry pages can route readers to tutorials, how-to guides, reference, and explanation.
Split mixed material only when that helps the reader, and preserve useful paths and heading links.

Archive member inspection found nested READMEs and text in the TechVault fileshare and workstation archives.
The web application archive also contains HTML templates.
Some of this text is scenario evidence or application content, rather than documentation.
The AI Escape Lab upstream archive contains third-party instructions, hints, and solutions.

Review ownership and purpose for each artifact; neither an archive nor an asset directory justifies a blanket exclusion.
Preserve upstream text, licenses, exact fixtures, and captured output.
Review maintained descriptions inside YAML, JSON, and generator strings as well as Markdown.

`tools/build_techvault_mcp_artifacts.py` owns deterministic MCP archive adaptations and source metadata.
It requires an external source checkout; this repository-only review does not acquire or inspect that checkout.
Do not invoke a generator merely to inspect prose or replace a pinned source with its current upstream state.
If a maintained source revision is unavailable, record that limit rather than asserting historical verification.

Edit maintained generator prose at its source; preserve deterministic archive membership, modes, attribution, and provenance.
The two TechVault packs have separate manifests and evidence obligations, even where their assets match.

## Release identity is a documentation boundary

Versioned kit directories are immutable releases, including their READMEs and `assets/integration.md`.
`load_kit_release()` verifies the exact payload inventory against the RAES associated-artifact manifest.
Keep admitted release bytes, independent kit versions, and their digests unchanged.

For current explanations of an exact release, use maintained pages outside its versioned directory and link to the historical reference.
For example, a README for a kit family can sit above its version directories without becoming a release member.
Keep such guidance explicit about the kit version it describes.
Do not create successor kit releases just to make historical prose pass a checker.

Current pack documentation is also bound content, but it can change through the normal pack authoring process.
Reuse `tools/refresh_pack_sdl_binding.py` for changed existing members.
It refreshes declared members; it does not add descriptors for new pages or remove descriptors for deleted pages.
A split or move therefore needs the existing RAES descriptor contract and exact-inventory validation as well.
Review descriptor metadata and preserve artifact ids and locators where possible.

Do not introduce a second checksum tool or silently repair manifests during consumer verification.

The style guide's general instruction to leave digests alone cannot permit stale bindings after an authorized pack-content edit.
Refresh only affected working pack bindings; preserve published artifacts and historical kit bindings.
Release Please owns package versions and `CHANGELOG.md`.
[ADR 0045](../decisions/adrs/0045-version-packs-with-the-package.md) assigns pack-version synchronization to the existing release job.
Do not hand-edit pack versions or run version synchronization as part of a prose rewrite.

A `docs:` change does not itself trigger a package release.
Do not claim that merged guidance has shipped before the normal release process publishes it.

Keep the AI Escape Lab qualification record dated 2026-10-06 exact.
Its accepted image, hashes, source revisions, uncommitted-input gap, and limited qualification are historical facts.
Current guidance must distinguish those observations from current static checks and untested runtime behavior.
Rewriting the participant briefing does not qualify a new image or update the briefing baked into the accepted image.

## Cross-cutting layers to reuse

Paths in this table are repository-relative; package modules are under `src/raes_env_packs/`.

| Layer and canonical incumbent | Guardrail for this work |
| --- | --- |
| Source admission: `_pack_fs`, `_authoring_safety.admit_members`, `KitLimits`, `PackValidationLimits` | Keep canonical contained paths, bounded reads, regular-file admission, and link rejection. Inspect archive members without executing them or extracting to uncontrolled paths. Add no bypass for documentation. |
| Shape and semantics: `validation`, packaged `resources/schemas/`, `kits.load_kit_release`, public RAES parsers | Preserve strict YAML/JSON, closed fields, materialization ownership joins, compatibility declarations, and provenance references. A documentation purpose does not require a schema field. Keep executable examples and runtime configuration unchanged. |
| Content identity: `digest`, `tools/refresh_pack_sdl_binding.py`, `release`, RAES associated-artifact validation | Check exact inventory, semantic parent, checksums, sizes, and set digest. Static validity, byte identity, release eligibility, authenticity, and runtime qualification are separate claims. |
| Audience and visibility: `pack.compatibility.yaml`, kit asset visibility, `validation._boundary_overlaps`, `content_ci.check_visibility` | Preserve participant, operator, oracle, and restricted boundaries when moving text or adding links. Kit integration prose remains operator material. The token scan covers selected text roots and extensions; it does not prove archive or linked-page safety. Review those surfaces separately. |
| Secrets, authentication, and OS exposure: existing runtime scripts, source locks, kit parameter checks, `publication` availability policy | Preserve documented identity, authorization, TLS, and containment prerequisites. Add no credential values, signed URLs, secret-bearing environment shapes, or tokens in command arguments or logs. Retain synthetic scenario fixtures without presenting them as real credentials. Do not read local secret stores, deploy infrastructure, or call live services to verify prose. |
| Publication: `pyproject.toml` Hatch mappings, `docs/public/conf.py`, `.readthedocs.yaml`, `tools/check_docs_publication_boundary.py` | Keep `docs/public/` the sole Sphinx source root. Do not include operator solutions or developer records there. Kits and packs already ship in wheel/sdist data: operator visibility is an audience label, not package encryption or access control. Add no publisher or external processing. |
| Execution and persistence: `validation.validate_pack`, `content_ci`, kit proposals, `_transactions` | Consumer validation remains inert; trusted author CI owns pack-local test execution. Add no database, cache, migration, controller, or service. Documentation work does not change proposal approval, atomic materialization, or recovery behavior. |
| Errors and observability: `validation.Diagnostic`, `KitError`, `PackDigestError`, `content_ci._token_leaks`, existing CLI envelopes | Preserve bounded diagnostics and existing exit status. Visibility failures report class and location, not matched values. Do not paste raw secrets or restricted output into PR evidence. Add no logger, exception hierarchy, or new error envelope. |
| Writing and workflow: `mise.toml`, `mise.lock`, `.vale.ini`, `.ste.yml`, `.github/workflows/ci.yml`, `.ground-control.yaml` | Reuse locked Vale and STE tools on explicit changed paths. Keep dictionary and remote analyzer features off. Preserve the fail-closed `verify` gate, targeted local checks, full CI validation, and fast pre-commit checks. |

## Evidence and extension seam

The extension seam is ordinary linked guidance outside immutable release directories.
Its inputs are the reader's task, audience, exact kit or pack revision, and actual evidence status.
Future releases can add version-specific guidance without editing historical artifacts or changing a canonical schema.
Do not turn these distinctions into a new registry or content framework.

Reuse `tests/test_published_kits.py`, `test_bundled_kits.py`, and `test_distribution_contents.py` for kit admission and packaged bytes.
Kit gates are separate from ordinary pack gates; a pack check alone does not validate the kit collection.
Existing tests also assert some README wording and integration headings.
Preserve useful heading anchors; do not weaken integrity tests to accommodate a rewrite.

Reuse `test_hosted_pack_content_binding.py`, `test_hosted_pack_byte_binding.py`, and `test_pack_versions.py` for pack identity.
Use `test_content_ci.py`, `test_validation.py`, and the affected pack tests for content, visibility, and template contracts.
The AI Escape Lab also has build and CTFd tests; these are static evidence, not a live rehearsal.

For each rewritten section, record source paths, revision, commands, results, corrected differences, and unresolved claims in the PR.
Run configured writing gates on explicit changed Markdown paths, including nested asset pages.
Check unsupported formats and preserved evidence separately.
Review reader purpose and STE meaning independently; linter success proves neither.
Check rendered heading order, descriptive links, diagram alternatives, and preserved anchors.
Check keyboard access when navigation changes, and do not use color alone for meaning.

The Sphinx build does not render kit or pack pages outside `docs/public/`.
Do not claim that it checked their rendering or links.

## Non-goals

No implementation, release publication, infrastructure deployment, runtime qualification, or Go migration is part of this preflight.
The implementation must not add RAES semantics, duplicate validation, a custom tool or skill, a dictionary pipeline, or a new hosting destination.
It must not repair runtime behavior under a documentation-only claim, rewrite provenance as current evidence, or publish restricted content.
Deliver issue #659 through one implementation PR using the existing release and CI workflows.

## Documentation design

The developer kit reference routes authors to maintained integration guidance and exact release references.
The integration guide explains composition without changing an immutable release.
Each release reference retains its original README, integration material, seed, module, and manifest.
The maintained reference identifies the available versions and their distinct parameter behavior.
It lives outside `kits/` because the distribution gate admits only versioned release members there.

Pack entry pages route readers to explanations, operating procedures, and historical references.
The participant entry contains no solution route or operator credentials.
Operator instructions retain their existing compatibility boundaries.
The current source explains preserved upstream text without changing that text.
Lineage and qualification records retain their original revisions and uncertainty.

### Data flows and security

The following diagram names the existing processes, stores, and audience boundaries.
It describes documentation handling, not scenario execution.

```text
[Versioned kits / pack sources / pinned archives]
             | source facts and exact historical bytes
             v
       [Local author review] <--- purpose rules --- [Style guide]
             | maintained prose
             v
       [Working source tree] ---> explicit paths ---> [Local writing checks]
             | affected pack members
             v
       [Existing digest refresh] ---> bindings ---> [Pack manifests]
             | source and bindings
             v
       [Existing CI and package build] ---> released content ---> [Pack consumer]

Participant boundary: participant-visible text contains no operator solutions.
Operator boundary: runbooks, solutions, and captured evidence retain their declared audiences.
Publication boundary: only docs/public/ enters the Sphinx site.
External boundary: no source text goes to a new service or remote analyzer.
```

Incorrect links can expose solution guidance to participants.
Check each new link against the compatibility manifest and the destination's content.

Changed exact assets can invalidate evidence or release identity.
Preserve those bytes and check the existing manifests against the resulting tree.
Historical evidence can mislead readers about current runtime behavior.
Label it by date and revision; keep current static results separate.
Audience labels do not encrypt package content or enforce access control.

The existing CI configuration and typed manifests remain the policy and architecture models.
No new policy, architecture schema, deployment model, or ADR is necessary.
This change modifies prose and derived pack checksums through their existing interfaces.
No executable interface, dependency, or trust boundary changes.
Mutation tests do not apply to static prose; existing integrity and visibility tests check the affected boundaries.

### Design references and review

[Diataxis application guidance](https://diataxis.fr/how-to-use-diataxis/) supports incremental changes in existing pages.
The [Diataxis compass](https://diataxis.fr/compass/) distinguishes tasks, learning, exact facts, and explanations.
This review used those references on 2026-11-07.
The [official ASD-STE100 site](https://www.asd-ste100.org/) returned HTTP 403 during this review.
The local style guide supplies the established sentence, paragraph, and meaning-preservation rules.

The rewrite requires a separate purpose and meaning review; passing local checks cannot establish full STE conformance.
Preserve technical vocabulary when a simpler replacement changes its meaning.
Review instructions against the 20-word limit and descriptions against the 25-word limit.
