# S3-compatible object store integration material

Author parameter: `bucket_name` (default `artifacts`).

## Exported RAES declarations

- `nodes.object_store`
- `content.seed_inventory`
- `accounts.object_store_operator`

## Composition notes

- No mandatory external authoring prerequisite; connect exported surfaces at the pack composition root as needed.
- Keep credentials and runtime-selected endpoints outside kit parameters and seed assets.
- Validate the completed ordinary pack after adding pack-level relationships.
