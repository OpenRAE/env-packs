# Secrets store

Reusable secrets store authoring content using the RAES module `infrastructure/secrets-store` and declared `openbao` source.

The module exports `nodes.secrets_store` and `content.seed_inventory`. Its `mount_path` parameter varies the declared inventory without changing those identities.

Declared service surface:

- api: 8200/tcp — OpenBao client API endpoint.

The seed inventory names secret_engine_mount, access_policy, auth_method, audit_profile. Bind applications and identities at the pack root; provide unseal material and credentials outside this kit.

This release is static authoring content. The consuming pack and backend own relationships, credential delivery, launch, configuration, and any runtime evidence.
