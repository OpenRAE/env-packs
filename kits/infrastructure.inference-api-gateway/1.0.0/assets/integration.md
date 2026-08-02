# Inference API gateway integration material

Author parameter: `route_name` (default `inference`).

## Exported RAES declarations

- `nodes.gateway`
- `content.seed_inventory`
- `accounts.gateway_operator`

## Composition notes

- Bind routes to one or more imported model-serving services.
- Keep credentials and runtime-selected endpoints outside kit parameters and seed assets.
- Validate the completed ordinary pack after adding pack-level relationships.
