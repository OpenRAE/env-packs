# Application/API service integration material

Author parameter: `api_base_path` (default `/api`).

## Exported RAES declarations

- `nodes.application`
- `content.seed_inventory`
- `accounts.application_service`

## Composition notes

- No mandatory external authoring prerequisite; connect exported surfaces at the pack composition root as needed.
- Keep credentials and runtime-selected endpoints outside kit parameters and seed assets.
- Validate the completed ordinary pack after adding pack-level relationships.
