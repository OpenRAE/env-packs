# LDAP directory

Reusable ldap directory authoring content using the RAES module `infrastructure/ldap-directory` and declared `openldap` source.

The module exports `nodes.directory` and `content.seed_inventory`. Its `directory_suffix` parameter varies the declared inventory without changing those identities.

Declared service surface:

- ldap: 389/tcp — LDAP client endpoint.

The seed inventory names base_dn, organizational_units, groups, entries. Connect non-AD directory consumers at the pack root and provide bind credentials separately.

This release is static authoring content. The consuming pack and backend own relationships, credential delivery, launch, configuration, and any runtime evidence.
