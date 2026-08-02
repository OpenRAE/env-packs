# Build environments from infrastructure kits

An infrastructure kit is a reusable piece of environment source: a RAES SDL
module plus its pack-local assets, documentation, tests, provenance, resource
estimates, and software-component inventory inputs. It is the part you should
not have to recreate each time you need a domain controller, workstation,
database, mail system, model service, or observability stack.

Kits do not add a runtime layer. After composition, the result is an ordinary
environment pack containing editable RAES SDL, ordinary assets,
`sdl/raes.lock.json`, its RAES associated-artifact manifest, and an inert
`kit.materializations.json` ownership record. A backend sees the resulting RAES
scenario; it does not call a kit API.

The complete first-party collection is published under `kits/`. Its scope and
release quality bar are defined by the [kit content strategy](kit-content-strategy.md).

## What an author gets

For each release, inspection shows:

- the kit identity, author value, infrastructure concern, release terms,
  limitations, and planning estimates;
- the module identity, parameters, defaults, exports, and topology derived from
  the pinned RAES library;
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

## Discover and inspect

Use an `env-packs` checkout and identify the exact revision you admitted. The
CLI performs no acquisition and no network access.

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

Preview constructs and validates the complete successor in private staging, but
does not change the pack, write its lock, create a RAES cache in it, execute
content, or contact a registry. Remove `--preview` to commit the exact proposal.
Parameter values are read from stdin and are not repeated in preview output.

Repeat the operation with distinct namespaces to add endpoints, DNS,
application, data, and observability services. Namespace, export, version,
dependency, path, visibility, parameter, source, and author-modification
conflicts are blocking diagnostics.

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
and removal stop with `kit.author-modification.conflict`. Unowned files are not
selected by filename or byte similarity. Shared SDL and lock files carry
explicit multi-owner state and are rewritten only as part of a fully validated
successor.

Kit assets can be placed only below `assets/briefing/`, `assets/content/`,
`assets/kits/`, or `docs/kits/`. They cannot add pack validators, tests, hooks,
or workflows. Catalog titles are also treated as untrusted terminal text.

An exceptionally rare failed recovery exchange returns a tool failure and a
`recovery:` path. That directory contains the preserved original pack; do not
delete it until the target and recovery copy have been inspected.

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
