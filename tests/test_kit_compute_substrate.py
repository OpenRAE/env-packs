"""Kits require a virtual-machine substrate only where they need one (#413).

The newest release of every Linux kit declares an open compute-substrate
constraint on each compute node, so the backend chooses the substrate. Planning
it against a manifest whose realization envelope offers in-process emulation,
not a virtual machine, therefore reports no ``realization.compute-substrate-*``
diagnostic; an exact virtual-machine constraint fails there with
``realization.compute-substrate-not-admitted``. The Windows kits keep an exact
virtual-machine substrate on each node, as the kit documentation states.

The manifest is the RAES stub manifest with its in-process realization
envelope, plus exact and constrained support, with an observation capability,
for every RAES realization concern. RAES's own planner tests declare support the
same way (``_fixture`` in ``test_issue_1200_mixed_runtime_constraints.py``). The
manifest judges what the kit demands, not what a particular backend supports,
and claims no backend behavior.

Every Linux kit plans valid there except the four in
``RUNTIME_COLLECTION_KITS``, which put a ``${parameter}`` inside a node runtime
collection. RAES 6.0.1 cannot retain typed authority for a configurable string
parameter there (OpenRAE/rae#1481), so planning them still reports
``realization.authority-bound-unavailable`` (#414). The planning test asserts
that their plans are not valid and that this is their only diagnostic.
"""

from __future__ import annotations

import shutil
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path

import yaml
from packaging.version import Version
from raes import parse_sdl_file
from raes_backend_protocols.capabilities import BackendManifest
from raes_backend_stubs.stubs import create_stub_manifest
from raes_contracts.apparatus import RealizationObservationCapability
from raes_contracts.vocabulary import ObservationStrength, RealizationVerificationScope
from raes_processor.compiler import compile_scenario_runtime_model
from raes_processor.planner import plan
from raes_processor.semantics.realization_concerns import realization_concern_descriptors


ROOT = Path(__file__).resolve().parents[1]
VIRTUAL_MACHINE_KITS = frozenset(
    {
        "infrastructure.rdp-accessible-windows-host",
        "infrastructure.windows-active-directory-domain-controller",
        "infrastructure.windows-domain-member",
    }
)
RUNTIME_COLLECTION_KITS = frozenset(
    {
        "infrastructure.application-api-service",
        "infrastructure.postgresql-database",
        "infrastructure.reverse-proxy-api-gateway",
        "infrastructure.smtp-imap-mail-service",
    }
)
OPEN = {"concern": "compute-substrate", "posture": "open"}
EXACT_VIRTUAL_MACHINE = {
    "concern": "compute-substrate",
    "posture": "exact",
    "domain": {"kind": "exact", "value": "virtual-machine"},
}
COMPUTE_SUBSTRATE_CODE_PREFIX = "realization.compute-substrate-"
AUTHORITY_BOUND_UNAVAILABLE = "realization.authority-bound-unavailable"


def _declaring_manifest() -> BackendManifest:
    """Return the stub manifest declaring every RAES realization concern."""

    stub = create_stub_manifest(with_realization_envelope=True)
    kinds = frozenset(
        descriptor.concern_kind for descriptor in realization_concern_descriptors()
    )
    observed = RealizationObservationCapability(
        verification_scope=RealizationVerificationScope.CONFIGURATION,
        observation_strength=ObservationStrength.GUEST_OBSERVED,
    )
    return replace(
        stub,
        realization_support=tuple(
            replace(
                declaration,
                supported_exact_requirement_kinds=(
                    declaration.supported_exact_requirement_kinds | kinds
                ),
                supported_constraint_kinds=declaration.supported_constraint_kinds | kinds,
                observation_capabilities={
                    **declaration.observation_capabilities,
                    **dict.fromkeys(kinds, observed),
                },
            )
            for declaration in stub.realization_support
        ),
    )


MANIFEST = _declaring_manifest()


def _newest_releases() -> list[Path]:
    """Return the newest release directory of every published kit."""

    newest: dict[str, Path] = {}
    for manifest in ROOT.glob("kits/*/*/kit.yaml"):
        release = manifest.parent
        current = newest.get(release.parent.name)
        if current is None or Version(release.name) > Version(current.name):
            newest[release.parent.name] = release
    return [newest[kit] for kit in sorted(newest)]


def _releases(*, windows: bool) -> list[Path]:
    return [
        release
        for release in _newest_releases()
        if (release.parent.name in VIRTUAL_MACHINE_KITS) is windows
    ]


def _module(release: Path) -> dict:
    return yaml.safe_load((release / "module.sdl.yaml").read_text(encoding="utf-8"))


def _substrates(module: dict) -> dict[str, dict]:
    """Map each node pointer to its compute-substrate constraint."""

    return {
        constraint["field_pointer"]: {
            key: value for key, value in constraint.items() if key != "field_pointer"
        }
        for constraint in module.get("realization", {}).get("constraints", [])
        if constraint["concern"] == "compute-substrate"
    }


def _on_every_compute_node(module: dict, constraint: dict) -> dict[str, dict]:
    return {
        f"/nodes/{name}": constraint
        for name, node in module["nodes"].items()
        if node["type"] != "switch"
    }


def _plan_release(release: Path, version: str, parameters: dict) -> tuple[bool, set[str]]:
    """Compose one release with ``parameters``, plan it, and return the result."""

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        shutil.copy2(release / "module.sdl.yaml", root / "module.sdl.yaml")
        document = {
            "name": "composition",
            "imports": [
                {
                    "source": "local:module.sdl.yaml",
                    "namespace": "subject",
                    "version": version,
                    "parameters": parameters,
                }
            ],
        }
        (root / "scenario.sdl.yaml").write_text(
            yaml.safe_dump(document, sort_keys=False), encoding="utf-8"
        )
        scenario = parse_sdl_file(root / "scenario.sdl.yaml", migration_policy="accept")
        model = compile_scenario_runtime_model(scenario, parameters={})
        execution = plan(model, MANIFEST)
    codes = {diagnostic.code for diagnostic in (*model.diagnostics, *execution.diagnostics)}
    return execution.is_valid, codes


def _compute_substrate_codes(codes: set[str]) -> set[str]:
    return {code for code in codes if code.startswith(COMPUTE_SUBSTRATE_CODE_PREFIX)}


class KitComputeSubstrateTests(unittest.TestCase):
    def test_linux_kits_leave_the_compute_substrate_open(self) -> None:
        releases = _releases(windows=False)
        self.assertLessEqual(
            RUNTIME_COLLECTION_KITS, {release.parent.name for release in releases}
        )
        for release in releases:
            module = _module(release)
            with self.subTest(kit=release.parent.name, version=release.name):
                self.assertEqual(_substrates(module), _on_every_compute_node(module, OPEN))

    def test_linux_kits_plan_where_no_virtual_machine_is_offered(self) -> None:
        for release in _releases(windows=False):
            module = _module(release)
            cases = yaml.safe_load(
                (release / "tests/composition.yaml").read_text(encoding="utf-8")
            )
            for case in ("default", "variation"):
                with self.subTest(kit=release.parent.name, version=release.name, case=case):
                    is_valid, codes = _plan_release(
                        release, module["module"]["version"], cases[case]
                    )
                    self.assertFalse(_compute_substrate_codes(codes))
                    if release.parent.name in RUNTIME_COLLECTION_KITS:
                        # OpenRAE/rae#1481: the runtime-collection parameter has
                        # no authority bound under RAES 6.0.1.
                        self.assertFalse(is_valid)
                        self.assertEqual(codes, {AUTHORITY_BOUND_UNAVAILABLE})
                    else:
                        self.assertTrue(is_valid, sorted(codes))

    def test_windows_kits_keep_an_exact_virtual_machine_substrate(self) -> None:
        releases = _releases(windows=True)
        self.assertEqual({release.parent.name for release in releases}, VIRTUAL_MACHINE_KITS)
        for release in releases:
            module = _module(release)
            with self.subTest(kit=release.parent.name, version=release.name):
                self.assertEqual(
                    _substrates(module),
                    _on_every_compute_node(module, EXACT_VIRTUAL_MACHINE),
                )


if __name__ == "__main__":
    unittest.main()
