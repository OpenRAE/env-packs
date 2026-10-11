"""Four runtime-collection kits leave the compute substrate open (#413).

The newest release of each kit in ``RUNTIME_COLLECTION_KITS`` declares an open
compute-substrate constraint on every compute node, so the backend chooses the
substrate. Planning it against a manifest whose realization envelope offers
in-process emulation, not a virtual machine, therefore reports no
``realization.compute-substrate-*`` diagnostic. The 1.0.0 releases declare an
exact virtual-machine substrate and fail there with
``realization.compute-substrate-not-admitted``.

The manifest is the RAES stub manifest with its in-process realization
envelope, plus exact and constrained support, with an observation capability,
for every RAES realization concern. RAES's own planner tests declare support the
same way (``_fixture`` in ``test_issue_1200_mixed_runtime_constraints.py``). The
manifest judges what the kit demands, not what a particular backend supports,
and claims no backend behavior.

Each of these kits puts a ``${parameter}`` inside a node runtime collection.
RAES 6.0.1 cannot retain typed authority for a configurable string parameter
there (OpenRAE/rae#1481), so planning still reports
``realization.authority-bound-unavailable`` and the plan is not valid (#414).
The planning test permits this known diagnostic. It rejects all other
diagnostics and does not require the upstream failure to persist. Each kit is
also composed with a custom value outside its default and variation values.
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
RUNTIME_COLLECTION_KITS = frozenset(
    {
        "infrastructure.application-api-service",
        "infrastructure.postgresql-database",
        "infrastructure.reverse-proxy-api-gateway",
        "infrastructure.smtp-imap-mail-service",
    }
)
OPEN = {"concern": "compute-substrate", "posture": "open"}
AUTHORITY_BOUND_UNAVAILABLE = "realization.authority-bound-unavailable"
CUSTOM_PARAMETERS = {
    "infrastructure.application-api-service": {"api_base_path": "/custom/v3"},
    "infrastructure.postgresql-database": {"database_name": "customer_data"},
    "infrastructure.reverse-proxy-api-gateway": {"route_prefix": "/team/api"},
    "infrastructure.smtp-imap-mail-service": {"mail_domain": "example.test"},
}


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


def _runtime_collection_releases() -> list[Path]:
    return [
        release
        for release in _newest_releases()
        if release.parent.name in RUNTIME_COLLECTION_KITS
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


def _plan_release(release: Path, version: str, parameters: dict) -> set[str]:
    """Compose one release with ``parameters`` and return planning diagnostics."""

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
    return codes


class KitComputeSubstrateTests(unittest.TestCase):
    def test_runtime_collection_kits_leave_the_compute_substrate_open(self) -> None:
        releases = _runtime_collection_releases()
        self.assertEqual(
            {release.parent.name for release in releases}, RUNTIME_COLLECTION_KITS
        )
        for release in releases:
            module = _module(release)
            with self.subTest(kit=release.parent.name, version=release.name):
                self.assertEqual(_substrates(module), _on_every_compute_node(module, OPEN))

    def test_runtime_collection_kits_plan_without_a_compute_substrate_diagnostic(
        self,
    ) -> None:
        for release in _runtime_collection_releases():
            module = _module(release)
            cases = yaml.safe_load(
                (release / "tests/composition.yaml").read_text(encoding="utf-8")
            )
            cases["custom"] = {
                **cases["default"],
                **CUSTOM_PARAMETERS[release.parent.name],
            }
            for case in ("default", "variation", "custom"):
                with self.subTest(kit=release.parent.name, version=release.name, case=case):
                    codes = _plan_release(
                        release, module["module"]["version"], cases[case]
                    )
                    # OpenRAE/rae#1481: the runtime-collection parameter has no
                    # authority bound under RAES 6.0.1. Permit that diagnostic
                    # without requiring the upstream failure to persist.
                    self.assertFalse(codes - {AUTHORITY_BOUND_UNAVAILABLE}, codes)


if __name__ == "__main__":
    unittest.main()
