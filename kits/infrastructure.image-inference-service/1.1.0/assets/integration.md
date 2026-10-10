# Image-inference service integration material

Author parameter: `model_name` (default `local-image`).

## Exported RAES declarations

- `nodes.inference`
- `content.seed_inventory`
- `accounts.model_operator`

## Composition notes

- No mandatory external authoring prerequisite; connect exported surfaces at the pack composition root as needed.
- Keep credentials and runtime-selected endpoints outside kit parameters and seed assets.
- Validate the completed ordinary pack after adding pack-level relationships.
