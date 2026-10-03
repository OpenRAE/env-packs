# Defensive-tooling composition preflight

Issue #378 is a documentation and static-authoring example over three existing
kit releases. It does not add a kit, schema, composer, runtime integration, or
backend promise. ADRs
[0009](../decisions/adrs/0009-scenario-packs-subordinate-to-aces.md),
[0035](../decisions/adrs/0035-compose-catalog-kits-through-raes-and-transactional-pack-projections.md),
and [0036](../decisions/adrs/0036-publish-first-party-content-with-env-packs.md)
already decide the architecture; no new ADR is needed.

## Composition boundary

The example composes these exact releases through `raes-pack-kit` and the
shared library behind it:

- `infrastructure.wazuh-security-monitoring-stack@1.0.0`, namespace `wazuh`;
- `infrastructure.suricata-network-intrusion-detection-sensor@1.0.0`, namespace
  `suricata`; and
- `infrastructure.thehive-case-management-service@1.0.0`, namespace `thehive`.

The public guide must derive and display parameters, exports, source identities,
component scope, realization constraints, and limitations from those releases.
It must not copy their module descriptors into another fixture or describe the
three releases as an assembly kit.

The pinned `raes==5.0.0` public parser accepts one deliberately narrow pack-root
relationship:

```yaml
relationships:
  suricata-can-reach-wazuh:
    type: connects_to
    source: suricata.sensor
    target: wazuh.manager
    description: Static in-world connectivity only; no telemetry-flow claim.
```

This proves that the two exported nodes have an authored in-world connectivity
edge. It does not prove that Suricata emits compatible events, Wazuh receives or
indexes them, an alert exists, TheHive receives a case, or a backend can realize
the topology. The current releases export no RAES declaration supporting a
Wazuh-to-TheHive alert/case mapping, so that mapping must remain explicitly
unsupported. A stronger relationship requires an upstream RAES contract and
updated kit exports, not local prose or a pack-owned schema.

Use RAES's public structured edit for the relationship and then file-backed RAES
validation. An in-memory edit can return `edited_with_diagnostics` because it
cannot resolve local imports; do not parse that diagnostic prose or treat the
in-memory result as composition proof. Re-derive the pack's associated-artifact
manifest through `derive_pack_content_manifest()` after the ordinary author
edit. Do not call the private kit manifest refresher or hand-edit checksums,
sizes, parent references, lock records, or set digests.

## Lifecycle ordering is a contract constraint

Kit materialization records the root SDL baseline as explicitly shared owned
state. A later pack-root relationship is therefore an author modification to a
kit-owned file. Current `propose_update()`, `propose_replace()`, and
`propose_remove()` correctly stop with `kit.author-modification.conflict`; there
is no supported operation that adopts or rebaselines arbitrary author edits.
Adding and then deleting the relationship through RAES structured edits is not
guaranteed to restore byte-identical YAML and does not clear that conflict.

Consequently, the example may demonstrate a successful parameter update and a
successful ownership-driven removal only before the pack-root relationship is
authored. It can then re-add the removed release, author and validate the
relationship, and demonstrate that a removal preview is blocked without changing
the pack. That refusal is the truthful reference/author-modification behavior.
The three releases declare no kit prerequisites, so the example must disclose
that there is no `kit.dependency.conflict` case to exercise rather than invent a
dependency. General adoption or merge of modified owned files is separate
tooling scope.

## Existing cross-cutting authorities

| Concern | Canonical incumbent and guardrail |
| --- | --- |
| RAES semantics | The exact pin in `pyproject.toml`; public parser, structured edit, resolver and lock models used by `kits.py`. Namespaces, imports, exports, relationships and `sdl/raes.lock.json` remain RAES-owned. |
| Kit discovery and composition | `KitSource`, `source_release`, `inspect_kit`, `propose_add`, `propose_update`, `propose_remove`, `proposal_document`, and `apply_proposal`. Preview and mutation consume the same proposal; do not duplicate workflow decisions in the walkthrough. |
| Config and validation shapes | Closed kit and materialization schemas, strict bounded YAML/JSON loaders, `KitLimits`, `PackValidationLimits`, `_validate_pack_for_author_ci`, and `content_ci`. Do not add an example schema or a second relationship validator. |
| Filesystem and persistence | `_pack_fs`, `_transactions`, the materialization ledger, RAES lock, and RAES associated-artifact manifest. Use a temporary pack, bounded regular files, explicit ownership, full-successor validation and atomic kit operations. The ledger is provenance/ownership, not a second lock. |
| Secrets and process exposure | `_authoring_safety.admit_members`, kit secret-shape checks, and `kit_cli._parameters`. Pass bounded parameter JSON on stdin via `--parameters -`; never put credentials, environment-variable coordinates, host bindings, signed URLs, backend settings, or JSON parameter payloads in argv, output, or fixtures. |
| Errors and observability | `Diagnostic`, `ValidationResult`, `KitError`/`KitRecoveryError`, value-free proposal documents, and CLI outcomes `0`/`1`/`2`/`3`. The library stays silent; the walkthrough may print safe check labels and bounded command failures, but adds no logger or exception taxonomy. |
| Identity and publication | `derive_pack_content_manifest`, `validate_pack_content_manifest`, component-boundary checks, `raes-pack-validate`, and `raes-pack-release check`. Assert the exact three lock imports and exact associated-artifact coverage; do not turn provenance or inventory into authenticity or readiness claims. |
| Visibility | Existing kit assets remain on their declared operator surfaces under `assets/kits/`; public/restricted separation continues through content CI and release checks. The guide contains synthetic, non-secret authoring data only. |
| Documentation | `docs/public/` is the only published root, its style guide requires real commands and output, and Sphinx plus `tools/check_docs_publication_boundary.py` enforce warning-strict links and separation from maintainer records. |

The local CLI is a trusted single-user author workflow and adds no authentication
or authorization surface. If a hosted adapter later presents the example,
`AuthoringSession` and the MCP host retain actor authorization, admitted-source,
tenant/path, proposal-review, persistence, redacted-audit, and apply-time checks;
none of those controls may be inferred from a source revision or pack lock.

## Verification and maintenance seam

The reproducible walkthrough should follow the existing
`tests_integration/kit_author_walkthrough.py` conventions and operate only in a
temporary directory. Keep the three kit ids, versions, namespaces, safe
parameters, and expected exports in one bounded input table so a future release
or RAES-pin update changes one obvious seam. This is test input, not a new
catalog or descriptor abstraction.

The checked observations are static: side-effect-free preview; exact
materializations and lock imports; preservation of the other two
materializations during one meaningful parameter update; ownership-driven
removal and re-add; the exact pack-root relationship after expansion; refusal to
remove an author-modified referenced materialization; associated-artifact set
validation; trusted author validation; and release checking. The ordinary
repository suite, pack validation/release gates, compile check, warning-strict
Sphinx build, and publication-boundary scan remain authoritative.

## Non-goals and prohibited shortcuts

Do not add or modify kit releases, kit identifiers, schemas, admission rules,
module descriptors, runtime profiles, backend probes, launch settings, service
execution, credentials, incidents, detections, alerts, cases, response
playbooks, objectives, scoring, participant behavior, or compatibility verdicts.
Do not infer a relationship from matching service names or ports; concatenate
SDL as YAML; use private RAES APIs; patch the lock or artifact manifest by hand;
silently rebaseline author edits; claim successful removal after a blocking
preview; or interpret static validation as telemetry, case creation, backend
readiness, or runtime qualification.
