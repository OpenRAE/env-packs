# Observability/evidence store integration material

Author parameter: `retention_profile` (default `standard`).

## Exported RAES declarations

- `nodes.metrics`
- `nodes.traces`
- `content.seed_inventory`
- `accounts.observability_operator`

## Composition notes

- No mandatory external authoring prerequisite; connect exported surfaces at the pack composition root as needed.
- Keep credentials and runtime-selected endpoints outside kit parameters and seed assets.
- Validate the completed ordinary pack after adding pack-level relationships.
