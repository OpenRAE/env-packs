# Linux domain member integration material

Author parameter: `computer_name` (default `linux-member-01`).

## Exported RAES declarations

- `nodes.domain_member`
- `content.seed_inventory`
- `accounts.member_operator`

## Composition notes

- Compose with one exported RAES identity domain and add the pack-level domain-join relationship.
- Keep credentials and runtime-selected endpoints outside kit parameters and seed assets.
- Validate the completed ordinary pack after adding pack-level relationships.
