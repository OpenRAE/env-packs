# Infrastructure kit content strategy

The first-party kit collection turns recurring environment infrastructure into
independently versioned RAES modules that an environment-pack author can
discover, inspect, parameterize, and compose. The collection covers eight broad
concerns:

1. identity and domain services;
2. access hosts and workstations;
3. network and shared services;
4. collaboration and developer services;
5. data and workflow services;
6. AI and model-serving services;
7. security operations services; and
8. policy and operational services.

The concerns are discovery aids, not coupled release trains. Each kit has its
own identity and version so authors can select and update only the infrastructure
their pack needs.

## Minimum release content

Every kit release must provide all of these layers:

- a valid, composable RAES module with explicit exports;
- a domain-specific parameter in addition to shared sizing and naming
  parameters;
- declared service, identity, data, or integration surfaces appropriate to the
  infrastructure;
- at least three benign seed-inventory items describing useful environment
  state;
- pack-local seed and integration assets;
- planning estimates, limitations, external authoring prerequisites where
  applicable, and component-inventory inputs;
- default and materially different parameter-variation composition tests; and
- an associated-artifact manifest binding every release file to the exact
  module snapshot.

The repository test suite applies these requirements to every released module
and composes a representative multi-kit environment. A kit that only renames a
generic node does not meet the bar.

## Scope discipline

Kits describe static infrastructure and seeded environment state using public
RAES concepts. They do not introduce objectives, participant behavior, injects,
events, narrative, or runtime control. They make no claim that a particular
backend can launch, configure, attach, or observe the declared infrastructure.
Those realization decisions belong to backend projects.

Credentials and other secrets are never kit parameters or bundled seed data.
When two kits need a relationship, the consuming pack declares it at the
composition root; the kits remain independently useful and replaceable.
