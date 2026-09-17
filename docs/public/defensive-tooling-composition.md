# Compose defensive tooling at the pack root

This walkthrough assembles three existing infrastructure kits into an ordinary
environment pack. It shows how to declare a supported relationship between
exported nodes without turning the three releases into a new bundle or
duplicating their module descriptors.

The result is static authoring evidence. It does not show that services start,
telemetry moves, alerts are generated, cases are created, or a backend can
realize the environment.

## Use these exact releases

Admit an immutable revision of the `OpenRAE/env-packs` repository and inspect
each release before composing it. The source revision becomes materialization
provenance; it is not a substitute for independently admitting the source.

| Release and namespace | Parameters | Exported RAES declarations | Declared software sources |
| --- | --- | --- | --- |
| `infrastructure.wazuh-security-monitoring-stack@1.0.0` as `wazuh` | `deployment_profile`, `service_label`, `enrollment_group` | nodes `manager`, `indexer`, `dashboard`; content `seed_inventory`; account `monitoring_operator` | Wazuh manager, indexer, and dashboard 4 |
| `infrastructure.suricata-network-intrusion-detection-sensor@1.0.0` as `suricata` | `deployment_profile`, `service_label`, `ruleset_name` | node `sensor`; content `seed_inventory` | Suricata 8 |
| `infrastructure.thehive-case-management-service@1.0.0` as `thehive` | `deployment_profile`, `service_label`, `organization_name` | nodes `case_manager`, `storage`; content `seed_inventory`; account `case_analyst` | TheHive 5 and Cassandra 5 |

All three releases have the same important limitations:

- they declare static infrastructure, seeded state, and integration surfaces;
- they do not claim launch, readiness, traffic attachment, credential delivery,
  or runtime evidence;
- their component inventory remains unresolved until pack publication; and
- they declare no kit prerequisites. There is therefore no truthful
  `kit.dependency.conflict` case to demonstrate in this composition.

Their two pack-local assets retain `operator` visibility under `assets/kits/`.
The example does not move them onto a public surface, add restricted material,
or include credentials, secret coordinates, host bindings, or backend launch
settings.

Inspect the authoritative release records rather than relying on this summary:

```sh
catalog_revision=$(git rev-parse HEAD)

raes-pack-kit inspect . \
  --source-id openrae-env-packs \
  --source-revision "$catalog_revision" \
  infrastructure.wazuh-security-monitoring-stack 1.0.0 --json
```

Repeat `inspect` for the Suricata and TheHive identifiers in the table. The
machine document provides the parameters, defaults, exports, assets,
limitations, prerequisites, resource estimates, and unresolved component
scope derived from the released content and the pinned RAES library.

## Run the verified walkthrough

From an `env-packs` checkout with its development environment installed, run:

```sh
.venv/bin/python tests_integration/defensive_tooling_composition.py \
  --catalog .
```

The [executable walkthrough](https://github.com/OpenRAE/env-packs/blob/main/tests_integration/defensive_tooling_composition.py)
uses a temporary pack and the same shipped command modules as the public CLI.
It performs this sequence:

1. inspect the three exact releases and their exported surfaces;
2. preview the first add and verify that preview writes nothing;
3. add all three releases through bounded parameter documents on stdin;
4. verify the three materializations, exact RAES lock records, and complete
   associated-artifact set;
5. update Suricata's `ruleset_name` while preserving Wazuh and TheHive;
6. remove Suricata through explicit ownership, then re-add it;
7. add and validate the supported pack-root relationship below; and
8. prove that a later Suricata removal preview refuses the author-modified root
   SDL and writes nothing.

Exit status is zero only when every check passes. The final pack also passes
trusted author validation and release checking. Those checks establish a valid,
byte-bound static pack; they do not qualify a deployment.

## Declare only the supported relationship

After parameter updates and successful ownership-driven removals are complete,
add this relationship to the consuming pack's root SDL:

```yaml
relationships:
  suricata-can-reach-wazuh:
    type: connects_to
    source: suricata.sensor
    target: wazuh.manager
    description: Static in-world connectivity only; no telemetry-flow or backend readiness claim.
```

The namespace-qualified endpoints are RAES exports from two independently
replaceable kits. File-backed RAES parsing verifies that both resolve. The
relationship says only that the authored nodes have a static connectivity edge.
Matching `events` service names or ports do not establish event compatibility,
delivery, indexing, alert creation, or detection behavior.

The current releases expose no RAES declaration that supports a
Wazuh-to-TheHive alert or case mapping. Do not invent one in prose or encode a
deployment-specific setup as a portable relationship. A portable mapping needs
an upstream RAES contract and corresponding exported surfaces first.

## Respect author edits during removal

Kit materialization records the root SDL as shared owned state. Adding the
relationship is an ordinary author edit to that file, so later update,
replacement, and removal proposals stop with
`kit.author-modification.conflict`. That refusal prevents the kit tool from
silently deleting the relationship or overwriting other authored changes.

Perform successful updates and removals before adding the relationship. Once
the relationship exists, review and remove the author-owned reference yourself
before deciding how to change the materialization. Do not patch the ownership
baseline, `sdl/raes.lock.json`, checksums, parent identity, or artifact-set
digest by hand.

For the general proposal, preview, update, replace, and removal contract, see
[build environments from infrastructure kits](kits.md). For the ownership
boundary between RAES, environment packs, and backends, see [what an environment
pack owns](ownership-boundary.md).
