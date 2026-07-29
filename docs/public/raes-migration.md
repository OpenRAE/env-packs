# Migrating to RAES Environment Packs

The maintained project is now `raes-env-packs`, imported as
`raes_env_packs`. The previous `aces-scenario-packs` distribution and
`aces_scenario_packs` import package are retired; there is no compatibility
shim or legacy console-script alias.

Update consumers together:

| Previous | Current |
| --- | --- |
| `pip install aces-scenario-packs` | `pip install raes-env-packs` |
| `from aces_scenario_packs import …` | `from raes_env_packs import …` |
| `aces-pack-validate` | `raes-pack-validate` |
| `aces-pack-release` | `raes-pack-release` |
| `aces-new-pack` | `raes-new-pack` |
| `aces-pack-issue-skeleton` | `raes-pack-issue-skeleton` |
| `scenarios/<pack-id>/` | `environments/<pack-id>/` |

Pack-owned identifiers also make a hard cut: compatibility
`environment-pack-compatibility/v2`, provenance
`environment-pack-provenance/v3`, layout contract version 4, and
`raes-environment-pack:/` locators. Existing manifests are not rewritten or
accepted through aliases.

SDL still describes a RAES `Scenario`, so `sdl/`, `*.sdl.yaml`,
`reusable_scenario`, and the identifiers published by the exact `raes==2.0.0`
contract corpus keep their upstream spellings. RAES 2 uses the
`https://raes.dev/schemas/` namespace, `raes.lock.json`, and
`sdl/.raes/module-cache`.

The retired distribution receives one final metadata-only notice directing
users here and is then frozen. It does not depend on the new distribution or
install placeholder modules.
