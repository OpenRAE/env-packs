# Certificate authority integration material

Author parameter: `authority_name` (default `lab-ca`).

## Exported RAES declarations

- `nodes.ca`
- `content.seed_inventory`

## Composition notes

- Connect consuming services to this authority at the pack root and supply private signing material through the backend.
- Keep credentials, private keys, and runtime-selected endpoints outside kit parameters and seed assets.
- Validate the completed ordinary pack after adding pack-level relationships.
