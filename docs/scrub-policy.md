# Migration Scrub Policy

Use this policy when adapting material from another source into this canonical
environment-pack definition and tooling repository.

This repository is subordinate to RAES core and must remain free of
downstream-catalog vocabulary, private operational details, and source-specific
product assumptions. Preserve only material that is needed for the shared
environment-pack layout, schemas, templates, or authoring and validation tools.

## Before opening a migration task

- Keep source-specific terms in a private, caller-supplied scanner denylist;
  do not paste that denylist into an issue or a canonical document.
- Identify material that belongs to RAES core semantics and consume it from
  RAES instead of redefining it here.

## Review the proposed material

Remove or generalize:

- downstream catalog and product names, branding, and customer assumptions;
- private repository paths, directory layouts, labels, milestones, and
  workflow conventions;
- private deployment details, including hostnames, addresses, environment
  names, and infrastructure identifiers; and
- private or unrelated issue and pull-request references.

Then run the applicable leak or scrub scanner against the private denylist and
resolve its findings before the material is accepted.
