# Webmail service integration material

Author parameter: `site_name` (default `mail`).

## Exported RAES declarations

- `nodes.webmail`
- `content.seed_inventory`
- `accounts.webmail_user`

## Composition notes

- Bind the browser client to an imported SMTP/IMAP service.
- Keep credentials and runtime-selected endpoints outside kit parameters and seed assets.
- Validate the completed ordinary pack after adding pack-level relationships.
