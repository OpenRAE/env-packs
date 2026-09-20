# Firewall / NAT

Reusable firewall / nat authoring content using the RAES module `infrastructure/firewall-nat` and declared `nftables` source.

The module exports `nodes.firewall` and `content.seed_inventory`. Its `ruleset_name` parameter varies the declared inventory without changing those identities.

Declared service surface:

- No node listener. The selected policy ports are seed inventory, not nftables service endpoints.

The seed inventory names filter_chains, allowed_ports, nat_policy, forwarding_rules. Attach the firewall node to protected networks and specify policy relationships at the pack root.

This release is static authoring content. The consuming pack and backend own relationships, credential delivery, launch, configuration, and any runtime evidence.
