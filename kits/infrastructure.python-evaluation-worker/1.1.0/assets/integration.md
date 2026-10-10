# Python evaluation worker integration material

Author parameter: `queue_name` (default `evaluation`).

## Exported RAES declarations

- `nodes.worker`
- `content.seed_inventory`
- `accounts.worker_operator`

## Composition notes

- No mandatory external authoring prerequisite; connect exported surfaces at the pack composition root as needed.
- Keep credentials and runtime-selected endpoints outside kit parameters and seed assets.
- Validate the completed ordinary pack after adding pack-level relationships.
