#!/usr/bin/env python3
"""Coverage-guided fuzzing of the untrusted-pack-input boundary (issue #142).

``validate_pack()`` is this package's contract with foreign input. A consumer
points it at a pack directory that some other party authored, and its docstring
promises:

    Invalid foreign input is returned as stable, bounded error codes. Unexpected
    package defects still raise normally so they cannot be mislabeled as input
    failures.

That is a precise, falsifiable property, and it is exactly what this harness
tests. The oracle is:

* ``validate_pack()`` returns a ``ValidationResult`` for *any* directory content
  -- a hostile pack must never escape as an exception;
* the diagnostics stay bounded by the caller's ``PackValidationLimits``, so a
  malicious pack cannot turn an error report into a memory-exhaustion vector;
* the result is deterministic in shape (sorted, deduplicated).

Deliberate scope, per the #142 architecture preflight:

* Only ``validate_pack()`` -- the *consumer* boundary (ADR 0013) -- is fuzzed.
  ``content_ci.main()`` and the author-side validators are **not**, because they
  intentionally resolve imports and execute catalog-controlled code; fuzzing
  those would be running attacker input through a path designed to trust it.
* Exceptions from ``validate_pack()`` are **not** swallowed. Only the harness's
  own corpus-materialization is guarded, and only against errors the *harness*
  causes (an OS rejecting a filename it was told to create). Catching everything
  around the call would convert real defects into silent passes.

Run it locally::

    pip install --require-hashes -r requirements/fuzz.txt
    pip install --require-hashes -r requirements/runtime.txt
    pip install --no-deps -e .
    python fuzz/fuzz_validate_pack.py -atheris_runs=20000

``.github/workflows/fuzz.yml`` runs a bounded session on pull requests. A
findings-free run proves nothing on its own; a crash is a real bug report.
"""

from __future__ import annotations

import pathlib
import shutil
import sys
import tempfile

import atheris

# Instrumented so libFuzzer can steer on the validator's real branches; without
# this the run degrades to blind random input.
with atheris.instrument_imports():
    from aces_scenario_packs import PackValidationLimits, validate_pack

_TEMPLATE = (
    pathlib.Path(__file__).resolve().parents[1]
    / "src" / "aces_scenario_packs" / "resources" / "template"
)

# The pack directory name is load-bearing: validate_pack cross-checks it against
# the manifest's `name`, so the seed uses the name the template declares.
_PACK_NAME = "example-pack"

# Small limits keep each iteration cheap and make the bounds easy to assert
# against. They stay well inside the defaults so the limit paths get exercised
# rather than being unreachable.
_LIMITS = PackValidationLimits(
    max_metadata_bytes=64 * 1024,
    max_sdl_bytes=64 * 1024,
    max_members=64,
    max_errors=25,
    max_error_chars=120,
)


def _build_workspace() -> tuple[pathlib.Path, dict[str, bytes]]:
    """Materialize the pristine pack once and cache its contents.

    Copying the whole template per iteration costs far more than the validation
    being measured -- it held the loop to ~3 exec/s, which is not enough
    throughput for libFuzzer to explore anything. Instead the pack is built once
    and each iteration restores only the files it touched, from memory.
    """
    workspace = pathlib.Path(tempfile.mkdtemp(prefix="fuzz-pack-"))
    root = workspace / _PACK_NAME
    shutil.copytree(_TEMPLATE, root)
    # The template ships placeholders that a real pack fills in; substituting the
    # pack name makes the seed pass identity validation, so the fuzzer starts
    # from a structurally valid pack and reaches deep validation immediately.
    for rel in ("pack.yaml", "pack.compatibility.yaml", "docs/provenance-ledger.yaml"):
        path = root / rel
        if path.is_file():
            path.write_text(
                path.read_text(encoding="utf-8").replace("<name>", _PACK_NAME),
                encoding="utf-8",
            )
    pristine = {
        str(p.relative_to(root)): p.read_bytes()
        for p in root.rglob("*")
        if p.is_file()
    }
    return root, pristine


_ROOT_DIR, _PRISTINE = _build_workspace()
_SEED_FILES = sorted(_PRISTINE)


def _apply(mutations: list[tuple[str, bytes]]) -> bool:
    """Overwrite the chosen files. False if the harness itself could not.

    Only failures this function *causes* are tolerated -- e.g. the OS refusing a
    path. Validator behaviour is never guarded.
    """
    try:
        for rel, blob in mutations:
            (_ROOT_DIR / rel).write_bytes(blob)
    except (OSError, ValueError):
        return False
    return True


def _restore(mutations: list[tuple[str, bytes]]) -> None:
    """Return the workspace to its pristine state for the next iteration."""
    for rel, _ in mutations:
        (_ROOT_DIR / rel).write_bytes(_PRISTINE[rel])
    # Validation must not create anything; if it ever does, drop it rather than
    # letting state leak across iterations and make a crash unreproducible.
    for path in sorted(_ROOT_DIR.rglob("*"), reverse=True):
        rel = str(path.relative_to(_ROOT_DIR))
        if path.is_file() and rel not in _PRISTINE:
            path.unlink()
        elif path.is_dir() and not any(path.iterdir()):
            path.rmdir()


def _check(result: object) -> None:
    """Assert the documented output contract."""
    errors = getattr(result, "errors", None)
    assert isinstance(errors, list), f"validate_pack returned {type(result)!r}"
    assert len(errors) <= _LIMITS.max_errors, (
        f"error list exceeded max_errors: {len(errors)} > {_LIMITS.max_errors}"
    )
    for item in errors:
        assert isinstance(item, str), f"non-string diagnostic: {item!r}"
        assert len(item) <= _LIMITS.max_error_chars, (
            f"diagnostic exceeded max_error_chars ({len(item)}): {item!r}"
        )
    assert errors == sorted(set(errors)), "diagnostics must be sorted and deduplicated"
    assert getattr(result, "ok") == (not errors), "`ok` must be derived from `errors`"


def test_one_input(data: bytes) -> None:
    fdp = atheris.FuzzedDataProvider(data)

    # Mutate between one and three template files per iteration; the rest stay
    # structurally valid so the fuzzer reaches deep validation rather than
    # bouncing off the first missing-file check.
    chosen: dict[str, bytes] = {}
    for _ in range(fdp.ConsumeIntInRange(1, 3)):
        rel = _SEED_FILES[fdp.ConsumeIntInRange(0, len(_SEED_FILES) - 1)]
        # Deduplicated: mutating one path twice would restore only the last
        # write, and the dict keeps the restore list exact.
        chosen[rel] = fdp.ConsumeBytes(fdp.ConsumeIntInRange(0, 2048))
    mutations = list(chosen.items())

    try:
        if not _apply(mutations):
            return
        # Intentionally unguarded: any exception escaping here is a finding.
        _check(validate_pack(_ROOT_DIR, limits=_LIMITS))
    finally:
        _restore(mutations)


def main() -> None:
    atheris.Setup(sys.argv, test_one_input)
    atheris.Fuzz()


if __name__ == "__main__":
    main()
