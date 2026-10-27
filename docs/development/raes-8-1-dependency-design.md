# RAES 8.1 dependency design

The package consumes the published RAES 8.1.0 wheel through one exact dependency.
The existing parser, consumer APIs, pack fixtures, and release process remain the integration points.
See the [compatibility preflight](raes-8-1-consumer-compatibility-preflight.md) for the repository assessment and binding constraints.

## Components and contracts

`pyproject.toml` defines the runtime dependency.
`requirements/runtime.in` mirrors this declaration for dependency updates.
`uv.lock` and `requirements/runtime.txt` record the resolved dependency artifacts.
The resolver generates their versions, locations, and hashes.
The existing hash checks detect inconsistent locks.

`validation.validate_pack` passes scenario content to RAES.
RAES owns parsing, semantic validation, runtime inventory, and materialization attestations.
Public consumer APIs retain their existing results and bounded diagnostics.
Invalid content continues to fail validation.
Existing first-party packs retain their content identities.

## Data flows and trust boundaries

```text
External package index
  -- release metadata and wheel bytes --> dependency resolver
Local dependency declarations
  -- exact requirements --> dependency resolver
Dependency resolver
  -- versions, artifact locations, hashes --> local lock files
Local lock files and package index
  -- hash-checked dependencies --> isolated Python environment
Untrusted pack files
  -- bounded file reads --> pack validator
Pack validator
  -- scenario content --> RAES parser
RAES parser
  -- validated models or errors --> pack validator
Pack validator
  -- bounded diagnostics --> consumer
Reviewed source and dependency locks
  -- build inputs --> existing release workflow
Existing release workflow
  -- distribution, SBOM, provenance --> existing PyPI and GitHub destinations
```

The package index, untrusted pack content, and release credentials form separate trust boundaries.
No new network destination, runtime store, or deployment component is required.
This data flow also shows the component interfaces; no additional deployment diagram is needed.

## Security controls and verification

The protected assets are package integrity, pack content, and release credentials.
An incorrect dependency artifact can change validation behavior.
Exact requirements and SHA-256 lock hashes bind the dependency artifact.
Dependency tests and ordinary wheel resolution check those controls.
Hash checks do not prove that upstream code is safe.
Existing vulnerability audits and compatibility tests address that remaining risk.

Untrusted pack content can attempt path escapes, resource exhaustion, or code execution.
Existing bounded reads, import denial, and consumer tests protect that boundary.
Trusted author CI retains its separate execution policy.
This dependency update grants no additional execution authority.

Release credentials remain inside the existing publication workflow.
Its permissions, provenance, and trusted publication controls remain applicable.
ADRs 0004, 0008, 0011, 0018, 0036, and 0041 already govern these choices.
No new ADR, policy check, infrastructure declaration, or service is needed.
Existing policy tests verify the retained dependency and workflow rules.

## Reference basis

- [RAES release](https://github.com/OpenRAE/rae/releases/tag/v8.1.0), version 8.1.0: released contract capabilities.
- [PyPI metadata](https://pypi.org/pypi/raes/8.1.0/json), version 8.1.0: wheel SHA-256, Python range, and dependencies.
- [uv locking](https://docs.astral.sh/uv/pip/compile/), uv 0.11.8: generate hash locks and retain compatible existing pins.
- [uv project locks](https://docs.astral.sh/uv/concepts/projects/sync/), uv 0.11.8: refresh project metadata without dependency overrides.
- [SLSA build requirements](https://slsa.dev/spec/v1.2/build-requirements), version 1.2: retain the consistent build and provenance process.
- [Official STE guidance](https://asd-ste100.org/about_STE.html), Issue 9: short sentences, consistent technical terms, and one meaning per term.

The writing review checks brevity, active verbs, consistent terms, and document purpose.
It uses the public STE guidance; it does not claim a complete dictionary compliance assessment.
Implementation tasks and verification results belong in the issue record.
