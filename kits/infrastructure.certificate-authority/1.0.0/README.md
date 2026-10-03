# Certificate authority

Reusable certificate authority authoring content using the RAES module `infrastructure/certificate-authority` and declared `step-ca` source.

The module exports `nodes.ca` and `content.seed_inventory`. Its `authority_name` parameter varies the declared inventory without changing those identities.

Declared service surface:

- https: 9000/tcp — Certificate authority API.

The seed inventory names trust_anchor, provisioner, certificate_profile, issuance_policy. Connect consuming services to this authority at the pack root and supply private signing material through the backend.

This release is static authoring content. The consuming pack and backend own relationships, credential delivery, launch, configuration, and any runtime evidence.
