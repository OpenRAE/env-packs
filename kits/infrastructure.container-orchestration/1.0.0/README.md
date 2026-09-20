# Container orchestration

Reusable container orchestration authoring content using the RAES module `infrastructure/container-orchestration` and declared `k3s` source.

The module exports `nodes.orchestrator` and `content.seed_inventory`. Its `cluster_name` parameter varies the declared inventory without changing those identities.

Declared service surface:

- api: 6443/tcp — K3s supervisor and Kubernetes API endpoint.

The seed inventory names namespace, workload_template, service_account, service_profile. Connect workloads and network services at the pack root; deliver join material outside this kit.

This release is static authoring content. The consuming pack and backend own relationships, credential delivery, launch, configuration, and any runtime evidence.
