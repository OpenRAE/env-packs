# Build environments from infrastructure kits

An infrastructure kit is a reusable piece of environment source. It is a RAES
SDL module plus its pack-local assets, documentation, tests, provenance,
resource estimates, and software-component inventory inputs. You do not have to
recreate it each time that you need a domain controller, workstation, database,
mail system, model service, or observability stack.

Kits do not add a runtime layer. After composition, the result is an ordinary
environment pack containing editable RAES SDL, ordinary assets,
`sdl/raes.lock.json`, its RAES associated-artifact manifest, and an inert
`kit.materializations.json` ownership record. A backend sees the resulting RAES
scenario; it does not call a kit API.

This repository publishes the complete first-party collection under `kits/`.
The [kit content strategy](kit-content-strategy.md) defines its scope and
release quality bar.

## What an author gets

For each release, inspection shows:

- the kit identity, author value, infrastructure concern, release terms,
  limitations, and planning estimates;
- the module identity, parameters, defaults, exports, and topology derived from
  the installed RAES library;
- pack-local assets and visibility;
- kit prerequisites and declared software-component inputs; and
- validation, parameter-variation, and multi-kit test declarations.

The kit manifest does not copy the RAES module descriptor, source identity,
artifact identity, trust policy, or dependency lock. Those facts remain RAES
facts.

The CLI is an adapter over the importable `raes_env_packs` library. Applications
use `build_kit_catalog`, `search_catalog`, `inspect_kit`, `propose_add`,
`propose_update`, `propose_replace`, `propose_remove`, `proposal_document`, and
`apply_proposal`; they do not shell out or implement a second composer. Proposal
and discovery functions print and log nothing.

## When a kit requires a virtual machine

A kit lets the backend choose the compute substrate unless the kit can't work
without a particular one. Each node states this in the kit's `module.sdl.yaml`
as a RAES compute-substrate constraint. A Linux kit leaves the choice open:

```yaml
realization:
  constraints:
  - field_pointer: /nodes/endpoint
    concern: compute-substrate
    posture: open
```

The backend then realizes the node as a container, a virtual machine, or any
other substrate it supports. A kit that needs a virtual machine names it
exactly:

```yaml
realization:
  constraints:
  - field_pointer: /nodes/domain_member
    concern: compute-substrate
    posture: exact
    domain:
      kind: exact
      value: virtual-machine
```

Only the three Windows kits need a virtual machine, because their nodes run a
`windows-server` source: `infrastructure.rdp-accessible-windows-host`,
`infrastructure.windows-active-directory-domain-controller`, and
`infrastructure.windows-domain-member`. RAES planning rejects them when the
backend offers no virtual machine.

Every Linux kit leaves the substrate open from release 1.1.0. The 1.0.0
releases still require a virtual machine. Releases are immutable, so 1.0.0
stays published. Select the newer release to leave the choice to the backend.
The examples on this page pin 1.0.0 releases.

Six open kits run software that needs more access to the host than many
containers get:

- `infrastructure.container-orchestration` (k3s)
- `infrastructure.firewall-nat` (nftables)
- `infrastructure.suricata-network-intrusion-detection-sensor` (packet capture)
- `infrastructure.samba-active-directory-domain-controller` (Samba domain
  services)
- `infrastructure.linux-domain-member` (domain join)
- `infrastructure.owlbear-protected-target` (kernel module and BPF LSM)

They stay open, so the backend decides whether it can realize them.

## Owlbear protected target

Follow the [Owlbear composition guide](owlbear-composition.md) for a synthetic
study scaffold, a daemon-state update, and the independent runtime-adapter
qualification boundary.

`infrastructure.owlbear-protected-target` version `1.0.0` exports one ARM64 Ubuntu target and four Owlbear input-file declarations.
It also exports a benign seed inventory.
The `daemon_active_state` parameter selects `active` or `inactive` typed service state.
The backend supplies the service binding, kernel-compatible artifacts, target PID, and enforcement arguments.
The kit bundles no upstream service unit or executable.
Service activity alone does not establish effective protection.

The compute substrate remains open.
Kernel access, BTF, BPF LSM, and module compatibility require backend admission.
The kit grants no host privileges and configures no network listener or external telemetry destination.
The two deployment profile labels use the same resource requirements.
Copied seed assets describe defaults; parameters do not render those files.
See the release's [integration material](https://github.com/OpenRAE/env-packs/blob/dev/kits/infrastructure.owlbear-protected-target/1.0.0/assets/integration.md) and [provenance](https://github.com/OpenRAE/env-packs/blob/dev/kits/infrastructure.owlbear-protected-target/1.0.0/assets/provenance.md).

## Discover and inspect

### Use a pinned package release

Install an exact package release to obtain the complete first-party kit
collection without a Git checkout:

```sh
python -m pip install "raes-env-packs==<release>"
```

Replace `<release>` with a published package version that includes bundled
kits. The wheel and source distribution contain every kit release from that
package's source tree, including historical kit versions.

Use the installed collection through the existing library APIs:

```python
from raes_env_packs import (
    build_kit_catalog, bundled_kit_source, source_release,
)

source = bundled_kit_source()
catalog = build_kit_catalog((source,))
release = source_release(source, "infrastructure.postgresql-database", "1.2.0")
print(release.id, release.version)
print(release.associated_artifacts.set_digest)
```

```text
infrastructure.postgresql-database 1.2.0
sha256:b0842f0e5ea56b2f82c90f7d0eb242de5450177434f1478690436f36daca14eb
```

The source id is `openrae-env-packs`. Its revision is
`raes-env-packs==<installed-version>`. The package version pins the collection;
each kit retains its own version and RAES associated-artifact set digest.
`source_release()` verifies the digest against the kit's exact files and SDL
parent before returning. It rejects missing, changed, or undeclared files.

Pass this same `source` to the kit proposal APIs when composing a pack.
Discovery and inspection read the installed resources without changing them,
running kit code, or contacting the network. The source root contains `kits/`;
it is also usable with the CLI's existing source arguments.

The helper requires filesystem-backed installed resources. If they are absent,
or if Python loads the package from a ZIP file, it raises `KitError` without
extracting files or searching a checkout. Editable installations should use an
explicit checkout source as shown below.

A kit digest proves content integrity, not authenticity. Admit the acquired
Python distribution through your supply-chain policy. The existing release
workflow supplies distribution build attestations. See
[ADR 0041](https://github.com/OpenRAE/env-packs/blob/main/docs/decisions/adrs/0041-distribute-kits-as-package-resources.md).

### Use an explicit checkout source

You can also use an `env-packs` checkout. Identify the exact revision you
admitted. The CLI performs no acquisition and no network access.

```sh
catalog_revision=$(git rev-parse HEAD)

raes-pack-kit list . \
  --source-id openrae-env-packs \
  --source-revision "$catalog_revision"

raes-pack-kit search . "domain controller" \
  --source-id openrae-env-packs \
  --source-revision "$catalog_revision"

raes-pack-kit inspect . \
  --source-id openrae-env-packs \
  --source-revision "$catalog_revision" \
  infrastructure.windows-active-directory-domain-controller 1.0.0 \
  --json
```

The source id and revision become materialization provenance. They are not a
second dependency lock; RAES still resolves the selected module into
`sdl/raes.lock.json`.

## Preview and add

Creating the pack and changing its kits need Linux. `raes-pack-new` and each
kit add, update, replace, and remove commit with the Linux `renameat2` system
call, which macOS does not provide. A `--preview` run writes nothing, so it does
not use `renameat2`.

Start from any valid minimal pack. The first add initializes the existing RAES
associated-artifact identity if the pack has not opted into it yet.

```sh
raes-pack-new realistic-lab --route minimal --yes

printf '%s\n' '{"deployment_profile":"standard","service_label":"directory"}' |
  raes-pack-kit add environments/realistic-lab . \
    --source-id openrae-env-packs \
    --source-revision "$catalog_revision" \
    infrastructure.windows-active-directory-domain-controller 1.0.0 \
    --namespace directory \
    --target-sdl sdl/realistic-lab.sdl.yaml \
    --parameters - \
    --preview --json
```

Preview constructs and validates the complete successor in private staging. It
does not change the pack, write its lock, create a RAES cache in it, execute
content, or contact a registry. Remove `--preview` to commit the exact proposal.
The command reads parameter values from stdin, and the preview output does not
repeat them.

Repeat the operation with distinct namespaces to add endpoints, DNS,
application, data, and observability services. Namespace, export, version,
dependency, path, visibility, parameter, source, and author-modification
conflicts are blocking diagnostics.

For a complete security-operations example, follow the verified
[defensive-tooling composition](defensive-tooling-composition.md) walkthrough.
It composes the published Wazuh and Suricata releases, and it declares one
supported relationship at the pack root. It keeps static environment state
separate from runtime telemetry and backend realization.

## Update, replace, and remove

The materialization id is the namespace selected during add. Update keeps the
same kit identity and changes its exact release or bounded parameters:

```sh
printf '%s\n' '{"deployment_profile":"compact","service_label":"directory"}' |
  raes-pack-kit update environments/realistic-lab . \
    --source-id openrae-env-packs \
    --source-revision "$catalog_revision" \
    infrastructure.windows-active-directory-domain-controller 1.0.0 \
    directory --parameters - --preview --json
```

Replacement is one remove-plus-add transaction. The pack never passes through
an intermediate state:

```sh
printf '%s\n' '{"deployment_profile":"standard","service_label":"front-door"}' |
  raes-pack-kit replace environments/realistic-lab . \
    --source-id openrae-env-packs \
    --source-revision "$catalog_revision" \
    infrastructure.reverse-proxy-api-gateway 1.0.0 \
    web --namespace gateway \
    --target-sdl sdl/realistic-lab.sdl.yaml \
    --parameters - --preview --json
```

Removal selects files only from explicit ownership metadata:

```sh
raes-pack-kit remove environments/realistic-lab gateway --preview --json
```

If an author changed an owned file after materialization, update, replacement,
and removal stop with `kit.author-modification.conflict`. Filename or byte
similarity does not select an unowned file. Shared SDL and lock files carry
explicit multi-owner state. Kit composition rewrites them only as part of a
fully validated successor.

A kit can place assets only below `assets/briefing/`, `assets/content/`,
`assets/kits/`, or `docs/kits/`. Kit assets cannot add pack validators, tests,
hooks, or workflows. Kit tooling also treats catalog titles as untrusted
terminal text.

Release inspection parses the kit module in memory and denies imports. Local
composition resolves imports through RAES with an empty registry policy. It
refuses a `raes-trust.yaml` file before it reads content.
An MCP host uses [separate preparation and review steps](mcp.md) before applying
a kit proposal.

An exceptionally rare failed recovery exchange returns a tool failure and a
`recovery:` path. That directory contains the preserved original pack. Do not
delete it until you inspect the target and the recovery copy.

## Validate the ordinary result

```sh
raes-pack-validate --pack environments/realistic-lab
raes-pack-release check --pack environments/realistic-lab
```

You can edit and validate the resulting pack without the CLI or the interface
that originally presented it. The kit ledger is authoring provenance and
ownership only; deleting the UI does not change the RAES scenario.
Canonical pack validation enforces the ledger whenever it is present, including
its exact dependency, member, artifact-id, and ownership joins.

The executable multi-service version of this walkthrough lives in the
[kit integration runbook](https://github.com/OpenRAE/env-packs/blob/main/docs/development/kits-integration-runbook.md).

## Supply-chain boundary

Every kit release binds its exact files through a RAES associated-artifact
manifest. A completed pack does the same for its new exact inventory and
authored semantic parent. Shipped or immutably pinned software must point to the
finest RAES source/artifact or preserved upstream SPDX/CycloneDX identity the
author actually has. Mutable or runtime-selected software remains explicitly
`external` or `unresolved`; the kit tool does not guess a dependency closure.

Component inventory is an input to pack SBOM publication. It is not an SBOM
format, signature, attestation, safety result, or proof that a backend realized
the service.
