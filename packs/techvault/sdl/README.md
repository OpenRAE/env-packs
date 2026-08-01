# TechVault ACES authority

`techvault.sdl.yaml` is the scenario's canonical authored truth. It is adapted
from APTL's operational TechVault SDL, captured from its `aces-sdl` 0.23.1
consumer and validated by the repository's isolated ACES 0.23 toolchain.

Use ACES standard fields whenever the schema can express a fact. Do not add a
pack-local scenario contract, duplicate parser, topology ledger, objective
mapping, or provider selector keyed by the `techvault` name. A genuine schema
gap belongs upstream in ACES; generic provider mechanics belong in a provider
binding.

The SDL currently authors topology, dependencies, services, generated Wazuh
artifacts, persistent volumes, content placement, one webapp vulnerability,
and representative AD identity. It does not author scored objectives, flags,
or an evaluation contract, and the pack must not infer those from metadata.

Referenced file sources are relative to the pack root:

- `assets/runtime/wazuh/certs.yml`
- `assets/runtime/wazuh/wazuh_manager.conf`
- `assets/content/onboarding`

Validate through the delivery validator or the central pack gate; both parse
the SDL through `aces_sdl`, not a TechVault-specific adapter.
