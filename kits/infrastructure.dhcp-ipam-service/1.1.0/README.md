# DHCP / IPAM service

Reusable dhcp / ipam service authoring content using the RAES module `infrastructure/dhcp-ipam-service` and declared `kea` source.

The module exports `nodes.dhcp` and `content.seed_inventory`. Its `address_pool` parameter varies the declared inventory without changing those identities.

Declared service surface:

- dhcp4: 67/udp — DHCPv4 server endpoint.

The seed inventory names subnet, address_pool, reservations, lease_policy. Attach this DHCP service to a suitable pack network and connect clients at the pack composition root.

This release is static authoring content. The consuming pack and backend own relationships, credential delivery, launch, configuration, and any runtime evidence.
