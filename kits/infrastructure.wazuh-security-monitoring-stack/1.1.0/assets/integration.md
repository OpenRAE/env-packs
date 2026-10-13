# Wazuh security monitoring stack integration material

Author parameter: `enrollment_group` (default `lab`).

## Exported RAES declarations

- `nodes.manager`
- `nodes.indexer`
- `nodes.dashboard`
- `content.seed_inventory`
- `accounts.monitoring_operator`

## Composition notes

- No mandatory external authoring prerequisite; connect exported surfaces at the pack composition root as needed.
- Keep credentials and runtime-selected endpoints outside kit parameters and seed assets.
- Validate the completed ordinary pack after adding pack-level relationships.
