# Firewall / NAT integration material

Author parameter: `ruleset_name` (default `edge-filter`).

## Exported RAES declarations

- `nodes.firewall`
- `content.seed_inventory`

## Composition notes

- Attach the firewall node to protected networks and specify policy relationships at the pack root.
- Keep credentials, private keys, and runtime-selected endpoints outside kit parameters and seed assets.
- Validate the completed ordinary pack after adding pack-level relationships.
