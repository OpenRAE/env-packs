# Message broker

Reusable message broker authoring content using the RAES module `infrastructure/message-broker` and declared `rabbitmq` source.

The module exports `nodes.broker` and `content.seed_inventory`. Its `virtual_host` parameter varies the declared inventory without changing those identities.

Declared service surface:

- amqp: 5672/tcp — AMQP client endpoint.

The seed inventory names virtual_host, exchange, queue, binding. Connect publishers and consumers to the broker at the pack root; provide credentials separately.

This release is static authoring content. The consuming pack and backend own relationships, credential delivery, launch, configuration, and any runtime evidence.
