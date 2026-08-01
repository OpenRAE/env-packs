# TechVault delivery bundles

These bundles select audience-specific documentation for the one scenario in
[`../sdl/techvault.sdl.yaml`](../sdl/techvault.sdl.yaml). They do not select a
different topology, modify ACES resources, or define objectives and scoring.

The shipped projections are guided, unguided, purple-team facilitation, and
demo. An agent-benchmark bundle is intentionally absent because the migrated
APTL scenario does not yet author an ACES objective/evidence/scoring contract.

Validate the joins and participant/operator split with:

```bash
python3 scenarios/techvault/profiles/validate_profiles.py validate
```
