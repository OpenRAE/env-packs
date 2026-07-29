# ADR 0030 — Separate public and developer documentation

- Status: Accepted
- Date: 2026-07-28
- Extends: [ADR 0002](0002-distribute-as-installable-package.md) and
  [ADR 0029](0029-parallel-pr-feedback-with-a-complete-merge-gate.md)

## Context

Read the Docs currently treats all of `docs/` as one Sphinx source tree. A
toctree controls navigation, not publication: source pages outside the toctree
can still enter HTML, search indexes, sitemaps, PDFs, and pull-request previews.
The same tree contains user guidance and internal decision and release records,
so removing the ADR toctree would not establish a reliable publication
boundary.

The public documentation also describes security-sensitive trust boundaries.
In particular, the author CLI may execute pack-local validators and tests,
whereas the in-process consumer validator is silent and never executes pack
code. A rewrite that improves tone but blurs those interfaces would make the
documentation less safe.

## Decision

`docs/public/` is the sole Sphinx source root. Public pages keep their existing
relative names where practical so their rendered URLs remain stable. Published
HTML, search indexes, sitemaps, PDFs, and pull-request previews are built only
from that root; an exclusion blacklist over the mixed `docs/` tree is not an
acceptable substitute.

Developer material remains in the repository outside `docs/public/`. A
developer index, also outside the public source root and linked from
`CONTRIBUTING.md`, is the entry point to ADRs, CI and release mechanics, and
other maintainer records. Public explanations may summarize decisions that
users need, but they do not link raw ADRs into the public navigation.

The existing documentation supply-chain and merge controls remain canonical:

- Read the Docs and local/CI builds use `requirements/docs.txt`, with hashes;
- Sphinx remains warning-strict and derives the package version from
  `pyproject.toml`;
- the documentation build and link check join the existing fail-closed `verify`
  aggregate from ADR 0029, with its topology contract tests; and
- publication-boundary tests assert that internal source paths and their
  content do not appear in any generated public artifact.

Public examples exercise the installed package and the exactly pinned RAES
dependency. They reuse the bundled template, schemas, public APIs, and existing
validation entry points rather than defining a documentation-only pack shape or
validator. Synthetic examples are created in temporary directories, as the test
suite already does; this repository does not acquire a catalog or checked-in
environment pack.

Interface documentation states each command's inputs, output and exit behavior,
side effects, and trust preconditions. It keeps these existing boundaries
explicit:

- `validate_pack()` is the untrusted single-pack ingest boundary and returns
  bounded, body-free diagnostics without logging, subprocesses, network access,
  or persistence;
- `raes-pack-validate` is trusted author CI and may execute pack-local
  validators and tests under its existing process and output limits;
- `raes-pack-release` reuses the shared author-static gate and existing
  containment, identity, provenance, visibility, and leak checks; and
- `raes-pack-issue-skeleton` remains dry-run by default, delegates
  authentication to `gh`, and sends mutation bodies on stdin rather than
  placing them or credentials in process arguments.

Public prose explains the pack layout but treats the packaged layout contract,
schemas, template, and exact RAES pin as normative. It does not copy their
field definitions, RAES semantics, validation rules, diagnostic hierarchy, or
release workflow into a second documentation-owned contract.

## Consequences

- Adding a file beneath `docs/public/` deliberately makes it publishable;
  adding a developer record elsewhere cannot publish it accidentally.
- Existing public page URLs can remain stable even though their repository
  source paths move. Pages that must change URLs use explicit redirects rather
  than duplicate compatibility pages.
- Documentation verification becomes part of the protected merge result, not
  an advisory workflow or a production-only surprise.
- README and community files remain GitHub-facing entry points. They link to the
  public site for users and to the developer index for contributors without
  being copied into the Sphinx source tree.

## Non-goals

This decision does not rewrite the documentation, delete or revise historical
ADRs, change pack schemas or tooling behavior, host an environment pack, alter
RAES semantics, perform another naming migration, add authentication or
persistence, or claim community capacity or badge criteria the project does
not meet.
