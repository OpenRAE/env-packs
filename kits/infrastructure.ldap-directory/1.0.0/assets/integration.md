# LDAP directory integration material

Author parameter: `directory_suffix` (default `dc=example,dc=test`).

## Exported RAES declarations

- `nodes.directory`
- `content.seed_inventory`

## Composition notes

- Connect non-AD directory consumers at the pack root and provide bind credentials separately.
- Keep credentials, private keys, and runtime-selected endpoints outside kit parameters and seed assets.
- Validate the completed ordinary pack after adding pack-level relationships.
