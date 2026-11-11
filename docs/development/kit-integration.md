# Integrate a released infrastructure kit

Use this how-to guide to select kit inputs before composition.
The result is an ordinary pack with RAES declarations and copied assets.

## Prerequisites

Use the supported Python package and an admitted kit source.
Keep the source revision immutable during inspection and composition.
Select an exact kit ID and version from the [release reference](kit-release-reference.md#release-references).
Read that release's README, `assets/integration.md`, `kit.yaml`, and `module.sdl.yaml`.
For Owlbear, also read the selected release's source provenance: [1.0.0](../../kits/infrastructure.owlbear-protected-target/1.0.0/assets/provenance.md) or [1.1.0](../../kits/infrastructure.owlbear-protected-target/1.1.0/assets/provenance.md).

Kit inspection and proposals do not qualify a runtime backend.
Only use trusted author content when a later author check executes pack-local validators or tests.
Consumer validation remains inert.

## Inspect and compose

1. Inspect the exact release through the existing kit CLI or library.
2. Check its exported surfaces, prerequisite kit versions, component-inventory inputs, license, visibility, and limitations.
3. Select the module parameters for your task.
4. Keep real credentials and runtime-selected endpoints outside kit parameters and seed files.
5. Preview the proposal before application.
6. Check the resulting SDL and copied assets for default values that need separate review.
7. Connect independent networks, storage, and observation services at the pack root.
8. Apply the reviewed proposal through the existing composition interface.
9. Validate the resulting ordinary pack and its content bindings.

Use the [kit composition guide](../public/kits.md) for exact CLI and library examples.
It describes source selection, inspection, preview, application, update, replacement, and removal.
Use the [checking guide](../public/checking.md) to select the correct validation interface.

## Check the result

Confirm that `sdl/raes.lock.json`, `kit.materializations.json`, the copied files, and the associated-artifact manifest agree.
Preserve the asset visibility from the kit manifest.
Integration material remains operator guidance after copying.
Do not place operator solutions in participant guidance.

Resolve namespace or owned-path conflicts through the proposal workflow.
Do not overwrite another materialization's files to bypass a conflict.
Copied files do not prove that a service starts or that a backend satisfies its constraints.

## Runtime admission

Select a backend that can satisfy the resulting RAES declarations.
An open compute substrate does not waive kernel, host-access, service-binding, or evidence requirements.
For Owlbear, active daemon state does not prove enforcement; inactive state does not prove an unprotected kernel.
Its backend must supply compatible artifacts, a service binding, process identity, and enforcement arguments.
The kit provides no executable or host privilege.

Retain runtime evidence separately from static composition results.
Keep historical releases exact; add maintained explanations outside their versioned directories.
