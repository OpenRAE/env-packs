#!/usr/bin/env python3
"""Executable defensive-tooling kit composition for issue #378.

The walkthrough exercises authoring-time composition only. It never acquires
content, calls a backend, starts a service, or claims telemetry or case flow.
"""

from __future__ import annotations

import argparse
import json
import tempfile
from pathlib import Path

from raes import parse_sdl_file
from raes.language_service import apply_structured_edit

from raes_env_packs.digest import (
    derive_pack_content_manifest,
    validate_pack_content_manifest,
)

from kit_author_walkthrough import Result, _json, _kit, _revision, _run, _source


_VERSION = "1.0.0"
_TARGET_SDL = "sdl/defensive-tooling.sdl.yaml"
_KITS = (
    {
        "id": "infrastructure.wazuh-security-monitoring-stack",
        "namespace": "wazuh",
        "parameters": {
            "deployment_profile": "compact",
            "service_label": "soc-monitoring",
            "enrollment_group": "blue-team",
        },
        "parameter_names": {
            "deployment_profile",
            "service_label",
            "enrollment_group",
        },
        "exports": {
            "nodes": {"manager", "indexer", "dashboard"},
            "content": {"seed_inventory"},
            "accounts": {"monitoring_operator"},
        },
        "component_refs": {
            "/nodes/manager/source",
            "/nodes/indexer/source",
            "/nodes/dashboard/source",
        },
    },
    {
        "id": "infrastructure.suricata-network-intrusion-detection-sensor",
        "namespace": "suricata",
        "parameters": {
            "deployment_profile": "compact",
            "service_label": "network-sensor",
            "ruleset_name": "community",
        },
        "updated_parameters": {
            "deployment_profile": "compact",
            "service_label": "network-sensor",
            "ruleset_name": "curated-soc",
        },
        "parameter_names": {
            "deployment_profile",
            "service_label",
            "ruleset_name",
        },
        "exports": {
            "nodes": {"sensor"},
            "content": {"seed_inventory"},
        },
        "component_refs": {"/nodes/sensor/source"},
    },
    {
        "id": "infrastructure.thehive-case-management-service",
        "namespace": "thehive",
        "parameters": {
            "deployment_profile": "compact",
            "service_label": "case-management",
            "organization_name": "blue-team",
        },
        "parameter_names": {
            "deployment_profile",
            "service_label",
            "organization_name",
        },
        "exports": {
            "nodes": {"case_manager", "storage"},
            "content": {"seed_inventory"},
            "accounts": {"case_analyst"},
        },
        "component_refs": {
            "/nodes/case_manager/source",
            "/nodes/storage/source",
        },
    },
)
_EXPECTED_LOCK = {
    "wazuh": ("infrastructure/wazuh-security-monitoring-stack", _VERSION),
    "suricata": (
        "infrastructure/suricata-network-intrusion-detection-sensor",
        _VERSION,
    ),
    "thehive": ("infrastructure/thehive-case-management-service", _VERSION),
}
_RELATIONSHIP = {
    "suricata-can-reach-wazuh": {
        "type": "connects_to",
        "source": "suricata.sensor",
        "target": "wazuh.manager",
        "description": (
            "Static in-world connectivity only; no telemetry-flow or backend "
            "readiness claim."
        ),
    }
}


def _snapshot(root: Path) -> dict[str, bytes]:
    return {
        path.relative_to(root).as_posix(): path.read_bytes()
        for path in root.rglob("*")
        if path.is_file()
    }


def _ledger(pack: Path) -> dict[str, object]:
    return json.loads((pack / "kit.materializations.json").read_text(encoding="utf-8"))


def _lock(pack: Path) -> dict[str, object]:
    return json.loads((pack / "sdl" / "raes.lock.json").read_text(encoding="utf-8"))


def _materializations(pack: Path) -> dict[str, dict[str, object]]:
    return {str(item["id"]): item for item in _ledger(pack)["materializations"]}


def _refresh_manifest(pack: Path) -> None:
    manifest = derive_pack_content_manifest(pack)
    (pack / "associated-artifacts.json").write_text(
        manifest.model_dump_json(indent=2) + "\n",
        encoding="utf-8",
    )


def _add(pack: Path, catalog: Path, revision: str, spec: dict[str, object]) -> object:
    return _kit(
        [
            "add",
            str(pack),
            *_source(catalog, revision),
            str(spec["id"]),
            _VERSION,
            "--namespace",
            str(spec["namespace"]),
            "--target-sdl",
            _TARGET_SDL,
            "--parameters",
            "-",
            "--json",
        ],
        parameters=dict(spec["parameters"]),
    )


def _inspect_releases(result: Result, catalog: Path, revision: str) -> None:
    print("\n== inspect the exact released surfaces ==")
    for spec in _KITS:
        inspected = _kit(
            [
                "inspect",
                *_source(catalog, revision),
                str(spec["id"]),
                _VERSION,
                "--json",
            ]
        )
        result.command(f"inspected {spec['namespace']}@{_VERSION}", inspected)
        document = _json(inspected)
        module = document.get("module", {}) if isinstance(document, dict) else {}
        exports = module.get("exports", {}) if isinstance(module, dict) else {}
        inventory = (
            document.get("component_inventory", [])
            if isinstance(document, dict)
            else []
        )
        result.check(
            f"{spec['namespace']} parameters and exports are exact",
            isinstance(document, dict)
            and set(module.get("parameters", [])) == spec["parameter_names"]
            and {kind: set(names) for kind, names in exports.items()}
            == spec["exports"],
        )
        result.check(
            f"{spec['namespace']} limitations and component scope are retained",
            isinstance(document, dict)
            and len(document.get("limitations", [])) == 3
            and document.get("prerequisites") == []
            and {item.get("ref") for item in inventory} == spec["component_refs"]
            and all(item.get("scope") == "unresolved" for item in inventory)
            and all(
                asset.get("visibility") == "operator"
                for asset in document.get("assets", [])
            ),
        )


def _create_pack(result: Result, workspace: Path) -> Path:
    author_repo = workspace / "catalog"
    (author_repo / ".git").mkdir(parents=True)
    (author_repo / "environments").mkdir()
    created = _run(
        "raes_env_packs.wizard",
        [
            "defensive-tooling",
            "--route",
            "minimal",
            "--repo",
            str(author_repo),
            "--yes",
        ],
    )
    result.command("minimal temporary pack created", created)
    pack = author_repo / "environments" / "defensive-tooling"
    checklist = pack / "docs" / "golden-readiness-checklist.md"
    checklist.parent.mkdir(parents=True, exist_ok=True)
    checklist.write_text(
        "# Golden readiness checklist\n\n"
        "This static authoring demonstration makes no golden-runtime claim.\n\n"
        "## Golden Definition Of Done\n\n"
        "- [ ] Runtime realization is intentionally outside this walkthrough.\n\n"
        "## Final Manual Participant Walkthrough Protocol\n\n"
        "- [ ] No runtime or participant walkthrough is claimed.\n",
        encoding="utf-8",
    )
    return pack


def _compose_and_update(
    result: Result, pack: Path, catalog: Path, revision: str
) -> None:
    print("\n== preview and compose three releases ==")
    before_preview = _snapshot(pack)
    previewed = _kit(
        [
            "add",
            str(pack),
            *_source(catalog, revision),
            str(_KITS[0]["id"]),
            _VERSION,
            "--namespace",
            str(_KITS[0]["namespace"]),
            "--target-sdl",
            _TARGET_SDL,
            "--parameters",
            "-",
            "--preview",
            "--json",
        ],
        parameters=dict(_KITS[0]["parameters"]),
    )
    result.command("first add previewed", previewed)
    result.check("preview is side-effect free", _snapshot(pack) == before_preview)

    for spec in _KITS:
        result.command(f"added {spec['namespace']}", _add(pack, catalog, revision, spec))

    initial = _materializations(pack)
    specs_by_namespace = {str(spec["namespace"]): spec for spec in _KITS}
    result.check(
        "three exact materializations and source coordinates are recorded",
        set(initial) == set(_EXPECTED_LOCK)
        and all(
            row["kit_id"] == specs_by_namespace[name]["id"]
            and row["kit_version"] == _VERSION
            and row["source"] == {"id": "reference", "revision": revision}
            and row["parameters"] == specs_by_namespace[name]["parameters"]
            and row["dependencies"] == []
            for name, row in initial.items()
        ),
    )
    before_other = {
        name: row for name, row in initial.items() if name != "suricata"
    }

    print("\n== update one meaningful parameter ==")
    suricata = _KITS[1]
    updated = _kit(
        [
            "update",
            str(pack),
            *_source(catalog, revision),
            str(suricata["id"]),
            _VERSION,
            "suricata",
            "--parameters",
            "-",
            "--json",
        ],
        parameters=dict(suricata["updated_parameters"]),
    )
    result.command("Suricata ruleset parameter updated", updated)
    after_update = _materializations(pack)
    result.check(
        "the other materializations are unchanged",
        {name: row for name, row in after_update.items() if name != "suricata"}
        == before_other,
    )
    scenario = parse_sdl_file(pack / _TARGET_SDL, migration_policy="accept")
    result.check(
        "the updated ruleset reaches the expanded sensor",
        "curated-soc" in scenario.nodes["suricata.sensor"].description,
    )


def _remove_and_readd(
    result: Result, pack: Path, catalog: Path, revision: str
) -> None:
    print("\n== remove safely before authoring a root relationship ==")
    removed = _kit(["remove", str(pack), "suricata", "--json"])
    result.command("Suricata removed through explicit ownership", removed)
    result.check(
        "Wazuh and TheHive remain materialized",
        set(_materializations(pack)) == {"wazuh", "thehive"},
    )
    result.command(
        "Suricata re-added for relationship authoring",
        _add(
            pack,
            catalog,
            revision,
            {**_KITS[1], "parameters": _KITS[1]["updated_parameters"]},
        ),
    )


def _assert_identity(result: Result, pack: Path) -> None:
    lock = _lock(pack)
    actual_lock = {
        str(item["namespace"]): (str(item["module_id"]), str(item["module_version"]))
        for item in lock["imports"]
    }
    result.check(
        "RAES lock contains the three exact module resolutions",
        actual_lock == _EXPECTED_LOCK,
    )
    result.check(
        "every lock record carries exact content and export identity",
        all(
            item.get("content_digest") and item.get("export_hash")
            for item in lock["imports"]
        ),
    )
    manifest = validate_pack_content_manifest(pack)
    result.check(
        "the complete associated-artifact set validates",
        manifest.set_digest.startswith("sha256:") and len(manifest.artifacts) == 17,
    )


def _author_relationship(result: Result, pack: Path) -> None:
    print("\n== author and validate the supported pack-root relationship ==")
    root = pack / _TARGET_SDL
    edited = apply_structured_edit(
        root.read_text(encoding="utf-8"),
        operation="set",
        pointer="/relationships",
        value=_RELATIONSHIP,
    )
    result.check(
        "RAES structured edit produced a successor",
        edited.get("status") in {"edited", "edited_with_diagnostics"},
    )
    if edited.get("status") not in {"edited", "edited_with_diagnostics"}:
        return
    root.write_text(str(edited["content"]), encoding="utf-8")
    _refresh_manifest(pack)

    scenario = parse_sdl_file(root, migration_policy="accept")
    relationship = scenario.relationships.get("suricata-can-reach-wazuh")
    result.check(
        "expanded relationship resolves the two exported nodes",
        relationship is not None
        and relationship.type.value == "connects_to"
        and relationship.source == "suricata.sensor"
        and relationship.target == "wazuh.manager",
    )
    result.check(
        "no unsupported Wazuh-to-TheHive mapping is asserted",
        set(scenario.relationships) == {"suricata-can-reach-wazuh"},
    )

    validated = _run("raes_env_packs.content_ci", ["--pack", str(pack)])
    result.command("composed pack passes trusted author validation", validated)
    released = _run("raes_env_packs.release", ["check", "--pack", str(pack)])
    result.command("composed pack passes release checks", released)
    _assert_identity(result, pack)

    before_preview = _snapshot(pack)
    removal = _kit(["remove", str(pack), "suricata", "--preview", "--json"])
    document = _json(removal)
    diagnostics = document.get("diagnostics", []) if isinstance(document, dict) else []
    result.check(
        "referenced author-modified materialization refuses removal",
        removal.returncode == 1
        and [item.get("code") for item in diagnostics]
        == ["kit.author-modification.conflict"],
        removal.stderr or removal.stdout,
    )
    result.check("blocked removal writes nothing", _snapshot(pack) == before_preview)


def _walk(result: Result, catalog: Path, revision: str, workspace: Path) -> None:
    _inspect_releases(result, catalog, revision)
    pack = _create_pack(result, workspace)
    _compose_and_update(result, pack, catalog, revision)
    _remove_and_readd(result, pack, catalog, revision)
    _author_relationship(result, pack)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--catalog",
        required=True,
        type=Path,
        help="staged local kit catalog root",
    )
    parser.add_argument("--source-revision", help="immutable admitted catalog revision")
    args = parser.parse_args(argv)
    catalog = args.catalog.resolve()
    revision = _revision(catalog, args.source_revision)
    print("Defensive tooling — static authoring evidence only")
    print(f"catalog revision: {revision}")
    result = Result()
    with tempfile.TemporaryDirectory(
        prefix="defensive-tooling-composition-"
    ) as temporary:
        _walk(result, catalog, revision, Path(temporary))
    print(f"\n{result.passed} passed, {result.failed} failed")
    return 0 if result.failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
