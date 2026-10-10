# SMB file service integration material

Author parameter: `share_name` (default `shared`).

## Exported RAES declarations

- `nodes.file_service`
- `content.seed_inventory`
- `accounts.file_operator`

## Composition notes

- No mandatory external authoring prerequisite; connect exported surfaces at the pack composition root as needed.
- Keep credentials and runtime-selected endpoints outside kit parameters and seed assets.
- Validate the completed ordinary pack after adding pack-level relationships.
