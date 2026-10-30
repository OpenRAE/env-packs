# RAES 10 dependency design

Issue #526 moves the package to RAES 10.0.0.
RAES 10.0.0 adds dependent-declaration variation targets (OpenRAE/rae#1733).
It also adds one exception hierarchy (OpenRAE/rae#1716, RAES ADR-116).
See the [preflight](dependent-declaration-variation-preflight.md) for the binding guardrails.

## Components and contracts

`pyproject.toml` and `requirements/runtime.in` declare `raes>=10.0.0`.
[ADR 0043](../decisions/adrs/0043-require-a-minimum-raes-version.md) sets the floor rule.
The package imports RAES 10 exception classes, so 10.0.0 is the oldest release that supplies every API it uses.
`uv.lock` and `requirements/runtime.txt` lock RAES 10.0.0 with SHA-256 hashes.

RAES owns the new targets.
They are `declaration-presence` and `resource-consumers` alternatives, coupled to `nodes.presence` with `requires` and `excludes`.
The package adds no target schema, dependency graph, or pruning logic.
`validate_pack` and `admit_experiment_set` pass the SDL and the selections to RAES without change.

## Exception contract

RAES 10 derives every RAES exception from `raes_contracts.errors.RaesError`.
A RAES domain failure is no longer a `ValueError`, `KeyError`, or `RuntimeError`.
Value-object validation still raises `ValueError`, and a RAES invariant defect still raises a built-in exception.

Each handler that wraps a RAES call catches the RAES class that the call documents:

| Call | RAES 10 failure | Handler |
| --- | --- | --- |
| Experiment selection and binding-target checks | `SDLSelectionError`, `ExperimentBindingTargetError` | `_experiment_set._check_family` |
| `load_associated_artifact_manifest_json` | `StrictJsonIngressError` | `digest._load_manifest`, `kits` manifest loaders |
| `load_lockfile` | `SDLError` | `component_boundary._load_lockfile`, `release` lock summary |
| `load_backend_profile` | `BackendProfileIdentityError` | `publication._is_trusted_backend_profile` |

Each handler keeps its existing diagnostic code or domain error.
No handler catches `RaesError` or `Exception` to hide a RAES failure.
A programming defect is not converted into a pack diagnostic.

## Data flows and trust boundaries

```text
External package index
  -- RAES 10.0.0 metadata and wheel bytes --> dependency resolver
Local dependency declarations
  -- raes>=10.0.0 --> dependency resolver
Dependency resolver
  -- versions, artifact locations, hashes --> local lock files
Local lock files and package index
  -- hash-checked dependencies --> isolated Python environment
Untrusted pack files
  -- bounded file reads --> pack validator
Pack validator
  -- SDL, experiment documents, manifests, lockfile --> RAES
RAES
  -- admitted models, or RaesError categories --> pack validator
Pack validator
  -- bounded diagnostics --> consumer or author CI
```

The package index, untrusted pack content, and the RAES library form separate trust boundaries.
The RAES boundary now returns typed failure categories.
No new network destination, runtime store, process, or deployment component is required.
This data flow also shows the component interfaces; no other diagram is needed.

## Security controls and verification

The protected assets are package integrity, validation correctness, and diagnostic confidentiality.

| Threat | Control | Verification |
| --- | --- | --- |
| A substituted RAES artifact changes validation | Minimum-version declaration, exact SHA-256 locks | Dependency policy tests, hash-checked CI install |
| Malformed pack input crashes a consumer check | Catch the documented RAES class at each RAES call | Tests for invalid selections, duplicate JSON members, malformed lockfiles |
| A broad handler hides a programming defect | Catch named RAES classes only | Code review; no new `Exception` handler |
| A diagnostic leaks pack content | Keep existing fixed codes; do not render RAES messages | Existing diagnostic tests |

Hash checks do not prove that upstream code is safe.
Vulnerability audits and the compatibility tests address that residual risk.
The change grants no new execution authority, credential, or host access.
ADRs 0011, 0036, 0042, and 0043 govern these choices.
No new ADR, policy check, or infrastructure declaration is needed.

## Reference basis

- [RAES release](https://github.com/OpenRAE/rae/releases/tag/v10.0.0), version 10.0.0: released capabilities and the breaking change.
- [PyPI metadata](https://pypi.org/pypi/raes/10.0.0/json), version 10.0.0: wheel SHA-256 `b2c1bd909618443ade49732413ebf16bf09f1f8e8bbd49a6d60049367d5ad73f`, Python `>=3.14,<3.15`.
- [RAES exceptions and logging](https://github.com/OpenRAE/rae/blob/v10.0.0/docs/develop/exceptions-and-logging.md), version 10.0.0, rules E3, H1, H5: catch the RAES class, not a broad built-in.
- [RAES variation points](https://github.com/OpenRAE/rae/blob/v10.0.0/specs/sdl/variation-points.md), version 10.0.0: dependent-declaration target shapes.
- [Python exception handling](https://docs.python.org/3.14/tutorial/errors.html), Python 3.14, "Handling Exceptions": exception class matching.
- [uv locking](https://docs.astral.sh/uv/pip/compile/), uv 0.11.8: generate hash locks and keep compatible pins.
- [Official STE guidance](https://asd-ste100.org/about_STE.html), Issue 9: short sentences and one meaning per term.

The writing review checks brevity, active verbs, consistent terms, and document purpose.
Implementation tasks and verification results belong in the issue record.
