# PostgreSQL database integration material

Author parameter: `database_name` (default `environment`).

## Exported RAES declarations

- `nodes.database`
- `content.seed_inventory`
- `accounts.database_operator`

## Composition notes

- No mandatory external authoring prerequisite; connect exported surfaces at the pack composition root as needed.
- Keep credentials and runtime-selected endpoints outside kit parameters and seed assets.
- Validate the completed ordinary pack after adding pack-level relationships.
