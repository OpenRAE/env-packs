# Python package resolver integration material

Author parameter: `index_name` (default `packages`).

## Exported RAES declarations

- `nodes.resolver`
- `content.seed_inventory`
- `accounts.resolver_operator`

## Composition notes

- No mandatory external authoring prerequisite; connect exported surfaces at the pack composition root as needed.
- Keep credentials and runtime-selected endpoints outside kit parameters and seed assets.
- Validate the completed ordinary pack after adding pack-level relationships.
