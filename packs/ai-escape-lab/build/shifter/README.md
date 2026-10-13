# Current Shifter upload archive

The deployed Shifter contract uses `raes==3.5.0` and
`raes-env-packs==5.2.0`. The canonical SDL declares the eleven container nodes,
their five challenge boundaries, and the seven-stage participant campaign. The
current Shifter compiler would otherwise treat each compute node as a separate
GCE resource, even though the reference profile bakes the complete topology
into one image. `export-pack.py` therefore creates a deployment projection with
one `eval-sandbox` GCE node and its participant network. It also translates the
current participant affiliation to RAES 3.5's singular `agent.entity` field.

The projection removes campaign-only action, behavior, objective, assertion,
and evidence declarations from the upload SDL; CTFd carries that progression at
runtime. It does not change the canonical pack. The exporter regenerates the
associated-artifact manifest, validates the staged projection, and writes a
deterministic upload archive.

Run the exporter in an environment containing the same pinned RAES packages as
the deployed Shifter instance:

```sh
python build/shifter/export-pack.py \
  --pack-root . \
  --output /secure/operator-path/ai-escape-lab-0.1.0-shifter.tar.gz
```

The source pack is never modified. The command refuses to overwrite an existing
archive and prints its SHA-256 digest for the installation record.
