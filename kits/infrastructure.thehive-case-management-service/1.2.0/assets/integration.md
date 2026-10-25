# TheHive case-management service integration material

Author parameter: `organization_name` (default `operations`).

## Exported RAES declarations

- `nodes.case_manager`
- `nodes.storage`
- `content.seed_inventory`
- `accounts.case_analyst`

## Composition notes

- No mandatory external authoring prerequisite; connect exported surfaces at the pack composition root as needed.
- Keep credentials and runtime-selected endpoints outside kit parameters and seed assets.
- Validate the completed ordinary pack after adding pack-level relationships.

## Internal topology

- `nodes.internal_network` is the module-local switch.
- `infrastructure.case_manager` links the node to `internal_network`.
- `infrastructure.storage` links the node to `internal_network`.
- `relationships.case_manager_depends_on_storage` declares an internal service dependency.
- Addressing, access control, readiness, and backend realization remain external.
