# Secrets store integration material

Author parameter: `mount_path` (default `kv`).

## Exported RAES declarations

- `nodes.secrets_store`
- `content.seed_inventory`

## Composition notes

- Bind applications and identities at the pack root; provide unseal material and credentials outside this kit.
- Keep credentials, private keys, and runtime-selected endpoints outside kit parameters and seed assets.
- Validate the completed ordinary pack after adding pack-level relationships.
