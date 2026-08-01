# Model registry integration material

Author parameter: `registry_namespace` (default `baseline`).

## Exported RAES declarations

- `nodes.registry`
- `content.seed_inventory`
- `accounts.registry_operator`

## Composition notes

- No mandatory external authoring prerequisite; connect exported surfaces at the pack composition root as needed.
- Keep credentials and runtime-selected endpoints outside kit parameters and seed assets.
- Validate the completed ordinary pack after adding pack-level relationships.
