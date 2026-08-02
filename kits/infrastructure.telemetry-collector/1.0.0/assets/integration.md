# Telemetry collector integration material

Author parameter: `pipeline_name` (default `default`).

## Exported RAES declarations

- `nodes.collector`
- `content.seed_inventory`

## Composition notes

- No mandatory external authoring prerequisite; connect exported surfaces at the pack composition root as needed.
- Keep credentials and runtime-selected endpoints outside kit parameters and seed assets.
- Validate the completed ordinary pack after adding pack-level relationships.
