# Reverse proxy/API gateway integration material

Author parameter: `route_prefix` (default `/`).

## Exported RAES declarations

- `nodes.gateway`
- `content.seed_inventory`
- `accounts.gateway_operator`

## Composition notes

- Add pack-level proxy-upstream relationships to imported application services.
- Keep credentials and runtime-selected endpoints outside kit parameters and seed assets.
- Validate the completed ordinary pack after adding pack-level relationships.
