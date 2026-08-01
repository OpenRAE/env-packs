# Samba Active Directory-compatible domain controller integration material

Author parameter: `domain_name` (default `directory.example.test`).

## Exported RAES declarations

- `nodes.domain_controller`
- `accounts.directory_administrator`
- `identity_domains.directory`
- `identity_forests.forest`
- `relationships.directory_controller`
- `content.seed_inventory`

## Composition notes

- No mandatory external authoring prerequisite; connect exported surfaces at the pack composition root as needed.
- Keep credentials and runtime-selected endpoints outside kit parameters and seed assets.
- Validate the completed ordinary pack after adding pack-level relationships.
