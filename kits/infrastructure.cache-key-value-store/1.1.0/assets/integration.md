# Cache / key-value store integration material

Author parameter: `key_prefix` (default `lab:`).

## Exported RAES declarations

- `nodes.cache`
- `content.seed_inventory`

## Composition notes

- Connect clients at the pack root and choose persistence and access controls in the consuming environment.
- Keep credentials, private keys, and runtime-selected endpoints outside kit parameters and seed assets.
- Validate the completed ordinary pack after adding pack-level relationships.
