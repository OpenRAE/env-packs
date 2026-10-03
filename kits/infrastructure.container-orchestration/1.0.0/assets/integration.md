# Container orchestration integration material

Author parameter: `cluster_name` (default `lab-cluster`).

## Exported RAES declarations

- `nodes.orchestrator`
- `content.seed_inventory`

## Composition notes

- Connect workloads and network services at the pack root; deliver join material outside this kit.
- Keep credentials, private keys, and runtime-selected endpoints outside kit parameters and seed assets.
- Validate the completed ordinary pack after adding pack-level relationships.
