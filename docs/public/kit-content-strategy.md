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

## Choose the reusable unit

Start with the author task and a working example. Record what you repeatedly
assemble, what changes between uses, and which files need to travel together.
Separate demonstrated composition from expected demand: a valid module and a
useful name do not establish that another reusable family is needed.

| What you need to reuse | Start with |
| --- | --- |
| Static infrastructure plus supporting assets and safe add/update/removal | An infrastructure kit over a RAES module. |
| A coherent semantic unit already expressed by RAES | An ordinary RAES module, with parameters and exports owned by RAES. |
| Different participant and facilitator material for the same scenario | The existing delivery bundles under `profiles/`. |
| A purpose, its environment, behavior, and evidence that belong together | A complete pack. |
| Instructions for connecting existing components | A worked composition guide. |
| A repeated shape without a demonstrated reusable boundary | Keep it local until a working example establishes the boundary. |

Delivery bundles select content exposure; they do not change scenario meaning,
topology or backend setup. See the [pack reference](environment-packs.md).
Behavioral modules and complete packs can use RAES concepts that infrastructure
kit admission excludes. Choosing one of those carriers does not make that
content eligible for the infrastructure collection.

## Show what reuse preserves

An admission proposal should include the original author task, a concrete source
revision, and a second materially different use. Identify the RAES-owned
parameters and exports that support the variation. Connect exported surfaces at
the consuming pack root so each kit remains independently replaceable.

Exercise the [authoring workflow](kits.md): inspect the exact release, preview
ordinary file and lock changes, add it to a valid pack, change a meaningful
parameter, and update, replace or remove it while preserving author edits.
Record what the checks actually establish. Declared seed objects are not proof
that a service implements a workflow, that telemetry flows, or that an experiment
produces valid results. Review source and realization constraints during
inspection before making a portability claim.

Keep the assets, redistribution terms, component inventory, visibility rules,
tests and limitations with the proposed unit. A composition example must retain
those facts for its constituent releases. If reuse needs new portable semantics,
resolve that need in RAES. If it needs a different kit carrier, evaluate the
manifest, catalog, ownership and validation implications before changing the
existing infrastructure contract.

## Scope discipline

Kits describe static infrastructure and seeded environment state using public
RAES concepts. They do not introduce objectives, participant behavior, injects,
events, narrative, or runtime control. They make no claim that a particular
backend can launch, configure, attach, or observe the declared infrastructure.
Those realization decisions belong to backend projects.

Credentials and other secrets are never kit parameters or bundled seed data.
When two kits need a relationship, the consuming pack declares it at the
composition root; the kits remain independently useful and replaceable.
