# Cache / key-value store

Reusable cache / key-value store authoring content using the RAES module `infrastructure/cache-key-value-store` and declared `valkey` source.

The module exports `nodes.cache` and `content.seed_inventory`. Its `key_prefix` parameter varies the declared inventory without changing those identities.

Declared service surface:

- resp: 6379/tcp — RESP client endpoint.

The seed inventory names keyspace, seed_keys, eviction_policy, persistence_policy. Connect clients at the pack root and choose persistence and access controls in the consuming environment.

The JSON seed data identifies `key_prefix` as the prefix source and supplies concrete key suffixes. This keeps arbitrary author-selected prefixes out of JSON interpolation while still telling a consuming pack how to form each key.

This release is static authoring content. The consuming pack and backend own relationships, credential delivery, launch, configuration, and any runtime evidence.
