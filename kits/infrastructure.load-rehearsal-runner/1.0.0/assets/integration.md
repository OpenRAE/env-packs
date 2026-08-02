# Load/rehearsal runner integration material

Author parameter: `workload_profile` (default `smoke`).

## Exported RAES declarations

- `nodes.runner`
- `content.seed_inventory`
- `accounts.runner_operator`

## Composition notes

- Select imported services as bounded workload targets.
- Keep credentials and runtime-selected endpoints outside kit parameters and seed assets.
- Validate the completed ordinary pack after adding pack-level relationships.
