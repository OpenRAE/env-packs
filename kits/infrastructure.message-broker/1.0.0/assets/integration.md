# Message broker integration material

Author parameter: `virtual_host` (default `lab`).

## Exported RAES declarations

- `nodes.broker`
- `content.seed_inventory`

## Composition notes

- Connect publishers and consumers to the broker at the pack root; provide credentials separately.
- Keep credentials, private keys, and runtime-selected endpoints outside kit parameters and seed assets.
- Validate the completed ordinary pack after adding pack-level relationships.
