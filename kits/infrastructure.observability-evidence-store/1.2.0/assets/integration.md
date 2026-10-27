# Observability/evidence store integration material

Author parameter: `retention_profile` (default `standard`).

## Exported RAES declarations

- `nodes.metrics`
- `nodes.traces`
- `content.seed_inventory`
- `accounts.observability_operator`

## Composition notes

- No mandatory external authoring prerequisite; connect exported surfaces at the pack composition root as needed.
- Keep credentials and runtime-selected endpoints outside kit parameters and seed assets.
- Validate the completed ordinary pack after adding pack-level relationships.

## Internal topology

- `nodes.internal_network` is the module-local switch.
- `infrastructure.metrics` links the node to `internal_network`.
- `infrastructure.traces` links the node to `internal_network`.
- `relationships.metrics_depends_on_traces` declares an internal service dependency.
- Addressing, access control, readiness, and backend realization remain external.

## Internal topology

- `nodes.internal_network` is the module-local switch.
- `infrastructure.metrics` links the node to `internal_network`.
- `infrastructure.traces` links the node to `internal_network`.
- `relationships.metrics_depends_on_traces` declares an internal service dependency.
- Addressing, access control, readiness, and backend realization remain external.
