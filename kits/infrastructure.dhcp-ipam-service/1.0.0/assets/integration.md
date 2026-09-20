# DHCP / IPAM service integration material

Author parameter: `address_pool` (default `10.42.0.0/24`).

## Exported RAES declarations

- `nodes.dhcp`
- `content.seed_inventory`

## Composition notes

- Attach this DHCP service to a suitable pack network and connect clients at the pack composition root.
- Keep credentials, private keys, and runtime-selected endpoints outside kit parameters and seed assets.
- Validate the completed ordinary pack after adding pack-level relationships.
