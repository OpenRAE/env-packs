# Package one scenario for guided and unguided audiences

Create one temporary environment pack, then expose different participant
material to guided and unguided audiences. Both bundles keep the same hydrated
RAES scenario and the same participant objective. Facilitator notes stay on the
operator release tier.

This example changes content exposure only. RAES owns the SDL language,
processor, and runtime. Your environment pack owns the concrete scenario it
authors with that language.

## Before you start

Use an `env-packs` checkout with the package installed in its virtual
environment:

```sh
python -m pip install -e .
```

The walkthrough writes only to an empty directory you provide. Its malformed
and leak cases use separate temporary copies and are deleted automatically.

## Create and verify the example

Create a scratch directory and run the executable walkthrough:

```sh
tutorial_root=$(mktemp -d)
python tests_integration/two_audience_bundles.py \
  --workspace "$tutorial_root"
pack="$tutorial_root/catalog/environments/two-audience-example"
```

The command starts with `raes-pack-new --route minimal`, snapshots the generated
SDL, adds the existing delivery-bundle layer, and runs author validation plus
the release checks. It also builds the boundary-split release tree and exercises
two invalid disposable copies.

```text
Two audiences — static content-exposure evidence only
  [PASS] ordinary minimal pack created
  [PASS] minimal SDL remains byte-for-byte unchanged
  [PASS] trusted author validation passes
  [PASS] release lint and smoke checks pass
  [PASS] both audience bundles reuse one shared participant objective
  [PASS] guided and unguided participant content differs
  [PASS] facilitator material stays operator-only
  [PASS] boundary-split release builds
  [PASS] participant release contains only participant bundle material
  [PASS] operator release contains both facilitator surfaces
  [PASS] restricted participant content is rejected
  [PASS] malformed bundle selection is rejected

12 passed, 0 failed
```

## Inspect the bundle contract

`profiles/bundles.yaml` is the authoritative bundle declaration. The example
factors the common objective once and adds one audience-specific participant
entrypoint to each bundle:

```yaml
schema_version: environment-pack-profile-bundles/v1
bundles:
- id: guided
  audience: participant
  runtime_profiles: []
  shared_includes:
  - _shared/objective.md
  participant_entrypoints:
  - guided/participant/hint.md
  operator_entrypoints:
  - guided/operator/facilitator.md
- id: unguided
  audience: participant
  runtime_profiles: []
  shared_includes:
  - _shared/objective.md
  participant_entrypoints:
  - unguided/participant/briefing.md
  operator_entrypoints:
  - unguided/operator/facilitator.md
```

`pack.yaml` carries only the presence flag and thin index:

```yaml
contents:
  profile_bundles: true
profile_bundles:
  manifest: profiles/bundles.yaml
  bundles:
  - id: guided
  - id: unguided
```

The matching `pack.compatibility.yaml` rows declare both bundles as supported.
They also place `_shared/` and each `participant/` directory on participant
paths, and each `operator/` directory on an operator path. No whole
`profiles/` directory is participant-visible.

## Inspect each audience exposure

Use the existing release helper to derive the files each participant receives:

```sh
python - "$pack" <<'PY'
from pathlib import Path
import sys

from raes_env_packs.release import bundle_participant_views

pack = Path(sys.argv[1])
for bundle_id, paths in sorted(bundle_participant_views(str(pack)).items()):
    print(f"{bundle_id}:")
    for path in paths:
        print(f"  {path}")
PY
```

```text
guided:
  profiles/_shared/objective.md
  profiles/guided/participant/hint.md
unguided:
  profiles/_shared/objective.md
  profiles/unguided/participant/briefing.md
```

The shared objective has one authored copy. The guided overlay suggests a first
investigation step. The unguided briefing states the task without that hint.
Neither exposure set contains an `operator/` path.

## Inspect the release tiers

Guided and unguided are delivery bundles. Participant and operator are release
tiers. `build_release()` separates the latter; it does not create one output
directory per bundle.

The walkthrough already built the release under `$tutorial_root/release`.
Inspect its file placement without printing the facilitator content:

```sh
release="$tutorial_root/release/two-audience-example-0.1.0"
find "$release" -type f | sed "s|$release/||" | sort
```

```text
operator/profiles/guided/operator/facilitator.md
operator/profiles/unguided/operator/facilitator.md
participant/README.md
participant/profiles/_shared/objective.md
participant/profiles/guided/participant/hint.md
participant/profiles/unguided/participant/briefing.md
release.yaml
```

The participant tier contains both safe audience overlays because it is the
boundary-split pack release, not a selected bundle. A consumer selects one
bundle from the manifest and exposes only its shared and participant
entrypoints. Facilitator files exist only in the operator tier.

## What the negative checks prove

The executable walkthrough makes two disposable copies of the valid pack:

- It adds restricted vocabulary to each participant overlay in turn. The
  existing release smoke check rejects both copies through its redacted leak
  report.
- It removes the `unguided` row from `profiles/bundles.yaml` while leaving the
  supported compatibility row intact. Existing release lint and smoke checks
  reject the inconsistent selection contract.

These checks do not add a bundle schema or a second selector. The pack-local
validator is a thin adapter over `validate_pack`, `lint_pack`, and `smoke_pack`.

## What you have not done

You have not changed the RAES SDL, started a runtime, changed topology or
participant behavior, added scoring, or measured whether either audience
learned more. You have demonstrated only that one concrete environment-pack
scenario can expose different safe guidance while keeping facilitator material
restricted.

Continue with the [pack reference](environment-packs.md) for the complete
layout and validation contract.
