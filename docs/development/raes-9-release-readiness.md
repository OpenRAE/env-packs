# RAES 9 release readiness

Issue #519 remains a patch dependency update through the quickfix lane.
Release Please owns the package version and changelog.

## Candidate under test

The candidate is OpenRAE/rae `origin/dev` at
`0184ce6ade585e33d0569097d236a88c53674e1d`, fetched on 2026-10-28.
The source still reports version 8.1.0; this is a development snapshot,
not the published 8.1.0 wheel or a released 9.0.0 artifact.
Build it from `implementations/python` in a full repository archive so its
metadata hook can read the repository README and bundled contract resources.

RAES now requires `>=3.14,<3.15`. The prepared package metadata and project
lock use that range. Existing CI and documentation builds already use 3.14.
The published RAES dependency stays at 8.1.0 until 9.0.0 can be resolved with
real artifact hashes.

## Compatibility scope

Changes since 8.1.0 include runtime lifetime ownership, participant opacity
evidence, control runtime conformance, typed factorial treatments, participant
tool profiles and control-context references, and cloud SDL declarations.
Those semantics belong to RAES. This package consumes its parser, language
service, compiler, planner, module registry, artifact requirements, and public
contract models; it does not implement a runtime or duplicate those contracts.

The dev snapshot also adds an exact `rpds-py==0.30.0` dependency. Both current
locks select newer calendar-versioned rpds-py releases, which will conflict
with that requirement. Regeneration for 9.0.0 must select 0.30.0. A temporary
candidate lock using the local source override resolved and installed that
closure successfully on CPython 3.14.4. Local paths stay outside repository
locks and package metadata.

The existing runtime inventory/materialization archive round-trip and host
authoring tests exercise the public contract and compile/plan boundary.
First-party pack validation and installed-wheel content tests must also pass:
import success alone does not establish compatibility.

On CPython 3.14.4, the candidate passed 58 focused tests covering authoring,
runtime contracts, package identity, provenance alignment, dependency pinning,
and package metadata. Six distribution/runtime/metadata tests also passed,
including building the wheel and sdist, installing the wheel, and loading its
bundled kits outside the checkout. Repository validation, both release checks,
and byte compilation passed. Explicit first-party pack validation also passed.

The full unit run did not complete and was interrupted. The isolated
`test_mcp_server.StdioTests.test_frame_reader_stops_before_reading_an_unbounded_line`
also exceeded a 20-second diagnostic limit, with the event loop waiting and
an AnyIO worker idle. The same test stall was documented in the
[8.1 preflight](raes-8-1-consumer-compatibility-preflight.md).
This is an unresolved verification blocker, not evidence of a RAES 9
regression. The interrupted run also emitted one failure before reaching the
stall; it did not reach the final traceback report. The focused tests were
rerun after the Python-range test updates and passed. Hosted full-suite checks
remain required; do not skip the stalled test or claim a green full suite.

## Publication steps

When 9.0.0 appears on the existing PyPI source:

1. Change only the exact RAES requirement in `pyproject.toml` and
   `requirements/runtime.in` to `raes==9.0.0`.
2. Run `uv lock` and
   `uv pip compile --generate-hashes --python-version 3.14 requirements/runtime.in -o requirements/runtime.txt`.
   Retain compatible transitive pins; inspect any resolver changes.
3. Install the released dependency closure on CPython 3.14 and run the full
   verification commands in `AGENTS.md`, plus
   `python -m unittest tests.test_distribution_contents` to build, install,
   and load the packaged first-party content outside the checkout.
4. Publish through quickfix with a `fix(deps):` title and pass hosted checks.
   Merge and release remain maintainer actions.

No source adapter is planned. Any difference between the tested commit and
the released wheel needs review and repeat compatibility verification.
Published artifact resolution and hashes cannot be certified before release.
