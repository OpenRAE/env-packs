# OIDC identity provider integration material

Author parameter: `realm_name` (default `workforce`).

## Exported RAES declarations

- `nodes.identity_provider`
- `identity_facades.oidc`
- `content.seed_inventory`
- `accounts.identity_operator`

## Composition notes

- No mandatory external authoring prerequisite; connect exported surfaces at the pack composition root as needed.
- Keep credentials and runtime-selected endpoints outside kit parameters and seed assets.
- Validate the completed ordinary pack after adding pack-level relationships.
