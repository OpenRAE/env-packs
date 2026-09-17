# Build a defensive-tooling environment pack from kits

Use this authoring tutorial to create a versioned, validated starting
environment with network sensing, security monitoring, and case-management
surfaces. Instead of rewriting those infrastructure declarations for each
environment, you compose three released kits into an ordinary pack, retain
their provenance, and keep each kit independently replaceable.

The completed pack gives authors a concrete scaffold to extend with
scenario-specific RAES source and gives runtime backends a portable input to
consume. The tutorial also shows how to declare the one supported relationship
between exported nodes without turning the releases into a new bundle or
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

## Follow the authoring tutorial

This tutorial creates a disposable catalog repository so you can run the full
workflow without modifying the `env-packs` checkout. When you are ready to use
the composition in a real pack, run the same kit commands against that pack's
root instead.

From an `env-packs` checkout with the package installed, capture the admitted
kit source and create a temporary authoring repository:

```sh
catalog_root=$(pwd -P)
catalog_revision=$(git rev-parse HEAD)
tutorial_root=$(mktemp -d)
author_repo="$tutorial_root/catalog"

git init --quiet "$author_repo"
mkdir -p "$author_repo/environments"

raes-pack-new defensive-tooling \
  --route minimal \
  --repo "$author_repo" \
  --yes

pack="$author_repo/environments/defensive-tooling"
```

The wizard creates and statically validates an ordinary minimal pack. The
remaining commands add reusable infrastructure to its root SDL; no special
defensive-tooling pack type is introduced.

### 1. Record the static readiness boundary

Repository content CI requires every pack to carry a golden-readiness record.
This tutorial creates the record without claiming that the static scaffold has
been deployed or rehearsed:

```sh
mkdir -p "$pack/docs"
cat >"$pack/docs/golden-readiness-checklist.md" <<'EOF'
# Golden readiness checklist

This static authoring pack makes no golden-runtime claim.

## Golden Definition Of Done

- [ ] Runtime realization is intentionally outside this tutorial.

## Final Manual Participant Walkthrough Protocol

- [ ] No runtime or participant walkthrough is claimed.
EOF
```

Replace this record with real build, rehearsal, participant, and teardown
evidence if the pack later advances toward `built` or `golden` status. Never
mark these items complete based on the static checks in this tutorial.

### 2. Inspect the releases

Inspect all three exact releases before accepting their files or limitations:

```sh
for kit in \
  infrastructure.wazuh-security-monitoring-stack \
  infrastructure.suricata-network-intrusion-detection-sensor \
  infrastructure.thehive-case-management-service
do
  raes-pack-kit inspect "$catalog_root" \
    --source-id openrae-env-packs \
    --source-revision "$catalog_revision" \
    "$kit" 1.0.0 --json
done
```

Review the output against the release table above. In particular, confirm the
parameter names, exports, operator-visible assets, unresolved component scope,
and absence of kit prerequisites.

### 3. Preview and add Wazuh

Parameter documents go through stdin so values are not exposed in process
arguments. Preview constructs and validates the full successor without writing
it:

```sh
printf '%s\n' \
  '{"deployment_profile":"compact","service_label":"soc-monitoring","enrollment_group":"blue-team"}' |
  raes-pack-kit add "$pack" "$catalog_root" \
    --source-id openrae-env-packs \
    --source-revision "$catalog_revision" \
    infrastructure.wazuh-security-monitoring-stack 1.0.0 \
    --namespace wazuh \
    --target-sdl sdl/defensive-tooling.sdl.yaml \
    --parameters - --preview --json
```

Review the proposed files, topology, assumptions, and lock changes. Apply the
same proposal by removing only `--preview`:

```sh
printf '%s\n' \
  '{"deployment_profile":"compact","service_label":"soc-monitoring","enrollment_group":"blue-team"}' |
  raes-pack-kit add "$pack" "$catalog_root" \
    --source-id openrae-env-packs \
    --source-revision "$catalog_revision" \
    infrastructure.wazuh-security-monitoring-stack 1.0.0 \
    --namespace wazuh \
    --target-sdl sdl/defensive-tooling.sdl.yaml \
    --parameters - --json
```

### 4. Add Suricata and TheHive

Use distinct namespaces so every exported declaration has an unambiguous RAES
address:

```sh
printf '%s\n' \
  '{"deployment_profile":"compact","service_label":"network-sensor","ruleset_name":"community"}' |
  raes-pack-kit add "$pack" "$catalog_root" \
    --source-id openrae-env-packs \
    --source-revision "$catalog_revision" \
    infrastructure.suricata-network-intrusion-detection-sensor 1.0.0 \
    --namespace suricata \
    --target-sdl sdl/defensive-tooling.sdl.yaml \
    --parameters - --json

printf '%s\n' \
  '{"deployment_profile":"compact","service_label":"case-management","organization_name":"blue-team"}' |
  raes-pack-kit add "$pack" "$catalog_root" \
    --source-id openrae-env-packs \
    --source-revision "$catalog_revision" \
    infrastructure.thehive-case-management-service 1.0.0 \
    --namespace thehive \
    --target-sdl sdl/defensive-tooling.sdl.yaml \
    --parameters - --json
```

Validate the three-kit intermediate result:

```sh
raes-pack-validate --pack "$pack"
```

At this point the pack contains three exact materializations, their ordinary
module files and assets, a RAES-owned `sdl/raes.lock.json`, and a byte-bound
associated-artifact set.

### 5. Update a meaningful parameter

Perform updates before adding an author-owned relationship to the shared root
SDL. This changes Suricata's ruleset name while preserving the Wazuh and
TheHive materializations:

```sh
printf '%s\n' \
  '{"deployment_profile":"compact","service_label":"network-sensor","ruleset_name":"curated-soc"}' |
  raes-pack-kit update "$pack" "$catalog_root" \
    --source-id openrae-env-packs \
    --source-revision "$catalog_revision" \
    infrastructure.suricata-network-intrusion-detection-sensor 1.0.0 \
    suricata --parameters - --json
```

You can also confirm that ownership-driven removal is currently available
without changing the pack:

```sh
raes-pack-kit remove "$pack" suricata --preview --json
```

The three selected releases have no kit prerequisites, so this preview cannot
demonstrate a kit-dependency conflict. Its safety comes from explicit file
ownership and full-successor validation.

### 6. Author the supported relationship

The relationship is ordinary RAES source owned by the pack author, not by any
kit. The following public APIs add it, perform file-backed RAES validation, and
refresh the pack's associated-artifact identity:

```sh
python - "$pack" <<'PY'
from pathlib import Path
import sys

from raes import parse_sdl_file
from raes.language_service import apply_structured_edit
from raes_env_packs.digest import (
    derive_pack_content_manifest,
    validate_pack_content_manifest,
)

pack = Path(sys.argv[1]).resolve()
root = pack / "sdl" / "defensive-tooling.sdl.yaml"
edited = apply_structured_edit(
    root.read_text(encoding="utf-8"),
    operation="set",
    pointer="/relationships",
    value={
        "suricata-can-reach-wazuh": {
            "type": "connects_to",
            "source": "suricata.sensor",
            "target": "wazuh.manager",
            "description": (
                "Static in-world connectivity only; no telemetry-flow or "
                "backend readiness claim."
            ),
        }
    },
)
if edited.get("status") not in {"edited", "edited_with_diagnostics"}:
    raise SystemExit("RAES rejected the relationship edit")

root.write_text(str(edited["content"]), encoding="utf-8")
parse_sdl_file(root, migration_policy="accept")

manifest = derive_pack_content_manifest(pack)
(pack / "associated-artifacts.json").write_text(
    manifest.model_dump_json(indent=2) + "\n",
    encoding="utf-8",
)
validate_pack_content_manifest(pack)
PY
```

The resulting root declaration is:

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

### 7. Validate the completed pack

Run both author validation and the release gate against the completed ordinary
pack:

```sh
raes-pack-validate --pack "$pack"
raes-pack-release check --pack "$pack"
printf 'tutorial pack: %s\n' "$pack"
```

Passing these commands establishes static composition, exact lock and artifact
identity, visibility separation, and release-contract validity. It does not
establish service execution or runtime integration.

### 8. Observe safe removal after the author edit

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

Preview the same removal again:

```sh
raes-pack-kit remove "$pack" suricata --preview --json
```

The expected nonzero result contains
`kit.author-modification.conflict` for the shared root SDL and leaves the pack
unchanged. This is the tool protecting the relationship you authored, not a
failed dependency check.

## Verify the tutorial implementation

Repository maintainers can execute the complete tutorial as a regression:

```sh
.venv/bin/python tests_integration/defensive_tooling_composition.py \
  --catalog .
```

The [executable walkthrough](https://github.com/OpenRAE/env-packs/blob/main/tests_integration/defensive_tooling_composition.py)
creates a temporary pack, follows the same lifecycle through the shipped
command modules and public APIs, and checks the exact materializations, lock,
artifact coverage, relationship, validation results, and removal refusal. Exit
status is zero only when every check passes.

For the general proposal, preview, update, replace, and removal contract, see
[build environments from infrastructure kits](kits.md). For the ownership
boundary between RAES, environment packs, and backends, see [what an environment
pack owns](ownership-boundary.md).
