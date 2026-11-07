# Current Shifter upload archive

Use this how-to guide to export the supplied single-host deployment projection.
It targets the recorded Shifter profile with `raes==3.5.0` and `raes-env-packs==5.2.0`.
Confirm that the receiving deployment still uses that contract before export.
This page makes no claim about a current Shifter installation.

The canonical SDL declares eleven container nodes, five challenge boundaries, and a seven-stage participant campaign.
The referenced Shifter compiler treats compute nodes as separate GCE resources.
The reference image contains the complete topology on one host.
The exporter therefore retains one `eval-sandbox` GCE node and its participant network.
It translates the participant affiliation to RAES 3.5's singular `agent.entity` field.

The projection removes campaign-only action, behavior, objective, assertion, and evidence declarations from its upload SDL.
CTFd carries that progression at runtime.
The exporter preserves the canonical source pack.
It regenerates the staged associated-artifact manifest, validates the projection, and writes a deterministic archive.

Use an environment with the receiving deployment's pinned RAES packages.
Run from the `packs/ai-escape-lab/` directory:

```sh
python build/shifter/export-pack.py \
  --pack-root . \
  --output /secure/operator-path/ai-escape-lab-0.1.0-shifter.tar.gz
```

Choose a protected output path outside the source pack.
The example filename does not set the pack version.
The command refuses an existing archive and prints its SHA-256 digest.
It writes the archive with mode `0600`.
Retain the digest in the installation record.
Continue with the [operator runbook](../../docs/operator-runbook.md#3-register-the-scenario-and-ctfd-content) after deployment approval.
