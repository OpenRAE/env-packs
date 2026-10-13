# Workflow orchestrator integration material

Author parameter: `workflow_name` (default `daily_ingest`).

## Exported RAES declarations

- `nodes.orchestrator`
- `content.seed_inventory`
- `accounts.workflow_operator`

## Composition notes

- No mandatory external authoring prerequisite; connect exported surfaces at the pack composition root as needed.
- Keep credentials and runtime-selected endpoints outside kit parameters and seed assets.
- Validate the completed ordinary pack after adding pack-level relationships.
