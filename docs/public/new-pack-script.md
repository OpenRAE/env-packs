# New Pack Script

`raes-new-pack` scaffolds a new pack from the template bundled in the package,
into the `environments/` tree of your catalog repo. Run it from the catalog root.

```sh
raes-new-pack blind-example \
  --title "Blind Example" \
  --description "One line: what the scenario is and what the player does." \
  --issue 123
```

If you track packs against an upstream requirement id, pass it too:

```sh
raes-new-pack example-range \
  --title "Example Range" \
  --requirement EXR-0001
```

The script:

- validates the pack id as lowercase kebab-case;
- copies the bundled template into `environments/<pack-id>`;
- patches `pack.yaml`, `pack.compatibility.yaml` when present, and the first
  README placeholders;
- preserves the build doctrine and `docs/golden-readiness-checklist.md`;
- refuses to overwrite an existing pack.

After scaffolding, edit the generated `pack.yaml` and `pack.compatibility.yaml`,
replace the README with scenario-specific prose, fill in `sdl/` and `docs/`, and
plan the milestone using the generated golden-readiness checklist.
