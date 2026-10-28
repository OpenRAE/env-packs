# RAES 9.1 compatibility

Issue #519 updates the exact runtime dependency to the published RAES 9.1.0
release. The package supports CPython `>=3.14,<3.15`, matching RAES.
Release Please owns the package version and changelog; the dependency update
uses a patch-producing `fix(deps):` title.

## Dependency artifacts

`pyproject.toml` and `requirements/runtime.in` declare `raes==9.1.0`.
`uv.lock` and `requirements/runtime.txt` were regenerated against the existing
PyPI source. RAES now requires `rpds-py==0.30.0`; the locks replace the previous
calendar-versioned rpds-py releases with that exact version.
Other dependency versions are retained.

The published RAES wheel SHA-256 is
`4ccbd167ff39f9a7550c9c5794d22fc16e555100d7795ea5c34be0da9ad92af2`.
The sdist SHA-256 is
`ffac8e2b931f791bbd138925118fe3106703840b40fa60aa406a6ccc897b9d95`.
The runtime closure installs with hash verification on CPython 3.14.4.
No local source override appears in the package metadata or locks.

## Compatibility scope

RAES 9 adds runtime lifetime ownership changes, participant opacity evidence,
control runtime conformance, typed factorial treatments, participant tool
profiles and control-context references, and cloud SDL declarations. RAES 9.1
also adds shared-engine experiment execution and executable mixed-backend
capability conformance checks.

Those semantics belong to RAES. This package consumes its parser, language
service, compiler, planner, module registry, artifact requirements, and public
contract models. No runtime implementation or compatibility adapter is added.

The existing runtime inventory/materialization archive round-trip and host
authoring tests exercise the public contract and compile/plan boundary.
The distribution test builds wheel and sdist artifacts, installs the wheel,
and loads bundled kits outside the checkout. First-party pack validation and
release checks exercise the shipped content against the published runtime.
Hosted CI verifies the full suite, dependency audit, content, and analysis
checks for the exact PR head.

## References

- [RAES 9.1.0 release](https://github.com/OpenRAE/rae/releases/tag/v9.1.0)
- [Published package](https://pypi.org/project/raes/9.1.0/)
- [Dependency authority](../decisions/adrs/0011-require-pinned-aces-sdl-validation.md)
