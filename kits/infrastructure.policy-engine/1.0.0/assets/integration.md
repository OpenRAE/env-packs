# Policy engine integration material

Author parameter: `policy_bundle` (default `baseline`).

## Exported RAES declarations

- `nodes.policy`
- `content.seed_inventory`
- `accounts.policy_operator`

## Composition notes

- No mandatory external authoring prerequisite; connect exported surfaces at the pack composition root as needed.
- Keep credentials and runtime-selected endpoints outside kit parameters and seed assets.
- Validate the completed ordinary pack after adding pack-level relationships.
