# SMTP/IMAP mail service integration material

Author parameter: `mail_domain` (default `environment.test`).

## Exported RAES declarations

- `nodes.mail`
- `content.seed_inventory`
- `accounts.mail_operator`

## Composition notes

- No mandatory external authoring prerequisite; connect exported surfaces at the pack composition root as needed.
- Keep credentials and runtime-selected endpoints outside kit parameters and seed assets.
- Validate the completed ordinary pack after adding pack-level relationships.
