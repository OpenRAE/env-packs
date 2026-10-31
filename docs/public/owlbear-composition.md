# Compose an Owlbear study environment

Use the Owlbear kit to add a synthetic protected-target scaffold to an ordinary
environment pack. This guide covers discovery, inspection, composition, update,
and validation. Runtime installation is a separate backend operation.

The example uses the benign `owlbear-game` seed and synthetic study labels.
It contains no participant records, attack corpus, credentials, or trial results.
It makes no runtime protection or study-outcome claim.

## Select tooling and kit content

Run the commands on Linux with CPython 3.14 in an authoring virtual environment.
Pack creation and kit changes require Linux `renameat2`.
The declared target's ARM64 requirement does not apply to the authoring host.

Install these released tools:

```sh
python -m pip install "raes-env-packs==7.0.0" "raes==10.0.0"
```

Use an admitted `OpenRAE/env-packs` checkout containing
`kits/infrastructure.owlbear-protected-target/1.0.0/` as the source.
That kit first appears in commit `a5a423bed99215b639ae10a0465ce238f3d35226`.
The 7.0.0 package's bundled collection does not contain it.
The released CLI can compose this separately admitted content.
Recording a source revision does not establish trust in that source.

From that checkout, run the remaining blocks in the same shell:

```sh
catalog_root=$(pwd -P)
catalog_revision=$(git rev-parse HEAD)
kit=infrastructure.owlbear-protected-target

raes-pack-kit search "$catalog_root" owlbear \
  --source-id openrae-env-packs --source-revision "$catalog_revision"
```

The search returns:

```text
infrastructure.owlbear-protected-target@1.0.0 — Owlbear protected target
```

Inspect that exact release:

```sh
raes-pack-kit inspect "$catalog_root" \
  --source-id openrae-env-packs --source-revision "$catalog_revision" \
  "$kit" 1.0.0 --json
```

Review the parameters, exports, external prerequisites, component inventory,
and limitations. The selected release declares:

| Surface | Declaration |
| --- | --- |
| Node export | `target`: ARM64 Ubuntu 24.04, two CPU cores, 4 GiB RAM; open compute substrate |
| File exports | `kernel_module`, `daemon_binary`, `game_binary`, `signature_database` |
| Seed export | `seed_inventory`: benign workload, component paths, and reference defaults |
| Parameters | `deployment_profile`, `service_label`, `daemon_active_state` |
| Service state | Portable unit ID `owlbear_protection`; `active` by default or `inactive` |
| Supporting assets | Operator-visible integration, seed, and provenance files under `assets/kits/owlbear-protected-target/` |

The file selectors name build outputs from upstream revision
`fa4497f3273517611e2d62f5fb32c620a00a9681`.
They do not identify admitted binary bytes or promise published binaries.
Review the immutable release's
[integration material](https://github.com/OpenRAE/env-packs/blob/a5a423bed99215b639ae10a0465ce238f3d35226/kits/infrastructure.owlbear-protected-target/1.0.0/assets/integration.md)
and [provenance](https://github.com/OpenRAE/env-packs/blob/a5a423bed99215b639ae10a0465ce238f3d35226/kits/infrastructure.owlbear-protected-target/1.0.0/assets/provenance.md).

## Create a synthetic pack

Create a disposable local authoring repository:

```sh
tutorial_root=$(mktemp -d)
author_repo="$tutorial_root/catalog"
git init --quiet "$author_repo"
mkdir -p "$author_repo/environments"

raes-pack-new owlbear-study --route minimal --repo "$author_repo" --yes
pack="$author_repo/environments/owlbear-study"
```

The wizard reports:

```text
created environments/owlbear-study
validated with the static pack check (minimal route)
```

Record the static study purpose and incomplete runtime readiness before adding
the kit. The composer will include these files in the pack's content identity.

```sh
mkdir -p "$pack/docs"
cat >"$pack/docs/study.md" <<'EOF'
# Synthetic Owlbear study scaffold

Use the benign game seed to author a repeatable target environment.
This scaffold contains no participant data or observed runtime results.
Daemon activity is a declared requirement, not evidence of protection.
EOF

cat >"$pack/docs/golden-readiness-checklist.md" <<'EOF'
# Golden readiness checklist

This static authoring pack makes no golden-runtime claim.

## Golden Definition Of Done

- [ ] Qualify runtime realization independently.

## Final Manual Participant Walkthrough Protocol

- [ ] Record a real walkthrough before claiming participant readiness.
EOF
```

## Preview, compose, and validate

First, preview a target whose daemon is required to be inactive:

```sh
printf '%s\n' \
  '{"deployment_profile":"compact","service_label":"synthetic-study","daemon_active_state":"inactive"}' |
  raes-pack-kit add "$pack" "$catalog_root" \
    --source-id openrae-env-packs --source-revision "$catalog_revision" \
    "$kit" 1.0.0 --namespace protected \
    --target-sdl sdl/owlbear-study.sdl.yaml --parameters - --preview --json
```

Preview validates a complete successor without changing the pack or running
kit content. Parameters enter through stdin. Use only non-secret authoring values.

Apply the same choices:

```sh
printf '%s\n' \
  '{"deployment_profile":"compact","service_label":"synthetic-study","daemon_active_state":"inactive"}' |
  raes-pack-kit add "$pack" "$catalog_root" \
    --source-id openrae-env-packs --source-revision "$catalog_revision" \
    "$kit" 1.0.0 --namespace protected \
    --target-sdl sdl/owlbear-study.sdl.yaml --parameters - --json

raes-pack-validate --pack "$pack"
raes-pack-release check --pack "$pack"
```

The author validator ends with:

```text
ENVIRONMENT-PACK CONTENT CI: PASS
```

The release check reports the minimal pack's limit:

```text
  [skip] owlbear-study: not releasable (no compatibility manifest with artifact_boundaries)
  [warn] no releasable packs found
PACK RELEASE GATE: PASS
```

This pack has no releasable artifact declarations. The skipped checks do not
establish artifact-release readiness.

The result contains namespaced declarations such as `protected.target` and
`protected.daemon_binary`. Its ordinary files include:

- `sdl/owlbear-study.sdl.yaml` and `sdl/raes.lock.json`;
- `associated-artifacts.json` for pack content identity;
- `kit.materializations.json` for authoring provenance and ownership; and
- the kit's supporting assets under `assets/kits/owlbear-protected-target/`.

The ownership ledger is not a runtime installer or a second dependency lock.
The commands do not acquire Owlbear binaries, start a service, or load kernel code.

## Update the declared daemon state

The materialization ID is the namespace `protected` selected during add.
Keep the kit version at `1.0.0` and change its bounded parameters:

```sh
printf '%s\n' \
  '{"deployment_profile":"compact","service_label":"synthetic-study","daemon_active_state":"active"}' |
  raes-pack-kit update "$pack" "$catalog_root" \
    --source-id openrae-env-packs --source-revision "$catalog_revision" \
    "$kit" 1.0.0 protected --parameters - --preview --json
```

Apply the reviewed update and validate again:

```sh
printf '%s\n' \
  '{"deployment_profile":"compact","service_label":"synthetic-study","daemon_active_state":"active"}' |
  raes-pack-kit update "$pack" "$catalog_root" \
    --source-id openrae-env-packs --source-revision "$catalog_revision" \
    "$kit" 1.0.0 protected --parameters - --json

raes-pack-validate --pack "$pack"
raes-pack-release check --pack "$pack"
```

The update changes the typed service-manager requirement from `inactive` to
`active`. It does not change any running system. Supply the complete intended
parameter set on each update.

These author checks may execute pack-local checks. Use them on this trusted
synthetic pack. Their success establishes static pack validity, not runtime
readiness or backend qualification.

## Install and qualify the runtime separately

The consuming backend needs an independently installed runtime adapter capable
of realizing these RAES declarations. The kit supplies no adapter package,
installation command, native service unit, or qualified backend.
Use the selected backend's own installation and admission procedure.

| Kit requirement | Runtime adapter and backend responsibility |
| --- | --- |
| ARM64 Linux target with open substrate | Admit an isolated target with compatible hardware, kernel build, and resources. An open substrate grants no host privileges. |
| Four artifact input files and declared paths | Admit the module, daemon with embedded eBPF skeletons, game, signatures, and runtime libraries. Preserve binary digests, build provenance, and dependency identity. |
| `owlbear_protection` service state | Bind the portable unit ID to the actual `owlbeard`. Select the workload PID and native arguments, including enforcement mode. |
| Static source and runtime declarations | Verify kernel ABI compatibility, module policy, BTF, BPF LSM availability, and successful loading and attachment. Refuse unsupported targets before privileged preparation. |
| Requested activity | Observe actual service and process state. Verify enforcement independently; activity alone does not establish protection. |
| Isolated study environment | Verify containment and teardown, including daemon and kernel state. Retain backend/adapter versions, target configuration, and observed qualification results. |

The upstream reference is a non-production prototype on Ubuntu 24.04 with
kernel 6.17. Other kernel builds have no compatibility claim here.
A container with insufficient kernel access cannot satisfy the target requirements.
A privileged container alone does not establish isolation or backend suitability.

Local logging belongs to backend preparation. External telemetry needs separate
authorization and declarations. The kit configures no listener, cloud account,
external telemetry destination, or attacker program.

## Keep the limitations visible

- `active` does not prove effective enforcement. `inactive` does not prove
  that kernel protection is absent or removed.
- `compact` and `standard` are planning labels with the same resource requirements.
- Copied seed files describe reference defaults. Parameter updates do not render
  those files; default text can still say `active` after an `inactive` composition.
- Fixed asset paths permit one materialization per pack. A second namespace
  does not avoid asset collisions.
- Author edits to owned files can block updates with
  `kit.author-modification.conflict`. Keep those diagnostics; do not rewrite
  ownership records, locks, or digests to force an update.
- Independent services and relationships belong at the consuming pack root.
  Formal study artifacts use the existing [RAES experiment carrier](environment-packs.md#experiments),
  rather than a new Owlbear-specific study format.

For other lifecycle operations, see [update, replace, and remove](kits.md#update-replace-and-remove).
