# Authoritative DNS service integration material

Author parameter: `zone_name` (default `environment.test`).

## Exported RAES declarations

- `nodes.dns`
- `content.seed_inventory`

## Composition notes

- No mandatory external authoring prerequisite; connect exported surfaces at the pack composition root as needed.
- Keep credentials and runtime-selected endpoints outside kit parameters and seed assets.
- Validate the completed ordinary pack after adding pack-level relationships.
