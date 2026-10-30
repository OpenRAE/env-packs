"""Repository gates for the published first-party infrastructure kits."""

from __future__ import annotations

import json
import math
import shutil
import tempfile
import unittest
from pathlib import Path

import yaml
from packaging.version import Version
from raes import parse_sdl_file

from raes_env_packs.kits import KitSource, build_kit_catalog, load_kit_release


ROOT = Path(__file__).resolve().parents[1]
EXPECTED_RELEASE_COUNT = 133

MULTI_NODE_DEPENDENCIES = {
    "infrastructure.observability-evidence-store": {
        ("metrics", "traces"),
    },
    "infrastructure.shuffle-automation-service": {
        ("automation", "storage"),
    },
    "infrastructure.wazuh-security-monitoring-stack": {
        ("manager", "indexer"),
        ("dashboard", "manager"),
        ("dashboard", "indexer"),
    },
}

MEANINGLESS_SEED_STRINGS = {
    "configured",
    "default",
    "example",
    "none",
    "placeholder",
    "tbd",
    "todo",
    "unknown",
    "value",
}

ISSUE_225_KITS = {
    "certificate-authority": (
        "ca", "step-ca", "authority_name", ("https", 9000, "tcp"), "provisioner"
    ),
    "dhcp-ipam-service": (
        "dhcp", "kea", "address_pool", ("dhcp4", 67, "udp"), "address_pool"
    ),
    "secrets-store": (
        "secrets_store", "openbao", "mount_path", ("api", 8200, "tcp"),
        "secret_engine_mount",
    ),
    "message-broker": (
        "broker", "rabbitmq", "virtual_host", ("amqp", 5672, "tcp"), "exchange"
    ),
    "cache-key-value-store": (
        "cache", "valkey", "key_prefix", ("resp", 6379, "tcp"),
        "eviction_policy",
    ),
    "firewall-nat": ("firewall", "nftables", "ruleset_name", None, "allowed_ports"),
    "ldap-directory": (
        "directory", "openldap", "directory_suffix", ("ldap", 389, "tcp"),
        "organizational_units",
    ),
    "container-orchestration": (
        "orchestrator", "k3s", "cluster_name", ("api", 6443, "tcp"),
        "namespace",
    ),
}


def _newest_releases() -> list[Path]:
    """Return the newest release directory for every published kit."""

    newest: dict[str, Path] = {}
    for manifest in ROOT.glob("kits/*/*/kit.yaml"):
        release = manifest.parent
        current = newest.get(release.parent.name)
        if current is None or Version(release.name) > Version(current.name):
            newest[release.parent.name] = release
    return [newest[kit] for kit in sorted(newest)]


def _reject_non_finite(value: str) -> None:
    """Reject JSON extensions that are not finite JSON values."""

    raise ValueError(f"non-finite JSON value: {value}")


def _seed_value_is_meaningful(value: object) -> bool:
    """Return whether a seed value carries concrete, non-placeholder state."""

    if value is None:
        return False
    if isinstance(value, bool):
        return True
    if isinstance(value, int):
        return True
    if isinstance(value, float):
        return math.isfinite(value)
    if isinstance(value, str):
        normalized = value.strip().lower()
        return bool(normalized) and normalized not in MEANINGLESS_SEED_STRINGS
    if isinstance(value, list):
        return bool(value) and all(_seed_value_is_meaningful(item) for item in value)
    if isinstance(value, dict):
        return bool(value) and all(
            isinstance(key, str)
            and bool(key.strip())
            and _seed_value_is_meaningful(item)
            for key, item in value.items()
        )
    return False


class PublishedKitTests(unittest.TestCase):
    def test_issue_225_kits_have_accurate_static_surfaces(self) -> None:
        for slug, facts in ISSUE_225_KITS.items():
            node_id, source, parameter, listener, seed_item = facts
            kit_id = f"infrastructure.{slug}"
            with self.subTest(kit=kit_id):
                root = ROOT / "kits" / kit_id / "1.0.0"
                release = load_kit_release(root)
                module = yaml.safe_load(
                    (root / "module.sdl.yaml").read_text(encoding="utf-8")
                )
                self.assertEqual(release.id, kit_id)
                self.assertEqual(module["nodes"][node_id]["source"]["name"], source)
                self.assertIn(parameter, module["module"]["parameters"])
                self.assertEqual(module["content"]["seed_inventory"]["target"], node_id)
                self.assertIn(
                    seed_item,
                    {item["name"] for item in module["content"]["seed_inventory"]["items"]},
                )
                services = module["nodes"][node_id].get("services", [])
                actual = {(item["name"], item["port"], item["protocol"]) for item in services}
                if listener is None:
                    self.assertFalse(actual, "nftables policy ports are not daemon listeners")
                    seed = yaml.safe_load(
                        (root / "assets/seed.yaml").read_text(encoding="utf-8")
                    )
                    self.assertEqual(seed["configuration"]["policy_ports"], [80, 443])
                else:
                    self.assertIn(listener, actual)

        proxy = yaml.safe_load(
            (ROOT / "kits/infrastructure.reverse-proxy-api-gateway/1.0.0/module.sdl.yaml")
            .read_text(encoding="utf-8")
        )
        self.assertEqual(proxy["nodes"]["gateway"]["source"]["name"], "traefik")
        self.assertEqual(
            {item["port"] for item in proxy["nodes"]["gateway"]["services"]},
            {80, 443},
        )
        self.assertIn(
            "upstream_bindings",
            {item["name"] for item in proxy["content"]["seed_inventory"]["items"]},
        )

    def test_all_releases_are_discoverable_and_deterministic(self) -> None:
        source = KitSource(
            id="openrae-env-packs",
            revision="test-revision",
            root=str(ROOT),
        )
        first = build_kit_catalog((source,))
        second = build_kit_catalog((source,))
        self.assertEqual(first, second)
        self.assertEqual(len(first["entries"]), EXPECTED_RELEASE_COUNT)

    def test_collection_offers_no_thehive_case_management_kit(self) -> None:
        source = KitSource(
            id="openrae-env-packs",
            revision="test-revision",
            root=str(ROOT),
        )
        for entry in build_kit_catalog((source,))["entries"]:
            with self.subTest(kit=entry["id"], version=entry["version"]):
                self.assertNotRegex(json.dumps(entry), "(?i)thehive")
        for path in sorted((ROOT / "kits").rglob("*")):
            if not path.is_file() or "__pycache__" in path.parts:
                continue
            relative = path.relative_to(ROOT).as_posix()
            with self.subTest(path=relative):
                self.assertNotRegex(relative, "(?i)thehive")
                self.assertNotRegex(path.read_bytes(), rb"(?i)thehive")

    def test_newest_releases_have_actionable_seed_content(self) -> None:
        for release_root in _newest_releases():
            release = load_kit_release(release_root)
            module = yaml.safe_load(
                (release_root / "module.sdl.yaml").read_text(encoding="utf-8")
            )
            dataset = module["content"]["seed_inventory"]
            with self.subTest(kit=release.id, version=release.version):
                self.assertTrue(dataset.get("text") or dataset.get("source"))
                if dataset.get("text") is None:
                    continue
                self.assertEqual(dataset.get("format"), "application/json")
                payload = json.loads(
                    dataset["text"], parse_constant=_reject_non_finite
                )
                item_names = {item["name"] for item in dataset["items"]}
                self.assertEqual(set(payload), item_names)
                for item_name, value in payload.items():
                    self.assertTrue(
                        _seed_value_is_meaningful(value),
                        f"{release.id} seed item {item_name} needs concrete state",
                    )
                if release.id == "infrastructure.firewall-nat":
                    seed_asset = yaml.safe_load(
                        (release_root / "assets/seed.yaml").read_text(
                            encoding="utf-8"
                        )
                    )
                    self.assertEqual(
                        [entry["port"] for entry in payload["allowed_ports"]],
                        seed_asset["configuration"]["policy_ports"],
                    )
                    self.assertEqual(
                        {entry["protocol"] for entry in payload["allowed_ports"]},
                        {"tcp"},
                    )

            cases = yaml.safe_load(
                (release_root / "tests/composition.yaml").read_text(encoding="utf-8")
            )
            with tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                shutil.copy2(
                    release_root / "module.sdl.yaml", root / "module.sdl.yaml"
                )
                imports = [
                    {
                        "source": "local:module.sdl.yaml",
                        "namespace": name,
                        "version": module["module"]["version"],
                        "parameters": cases[name],
                    }
                    for name in ("default", "variation")
                ]
                (root / "scenario.sdl.yaml").write_text(
                    yaml.safe_dump(
                        {"name": "seed-composition", "imports": imports},
                        sort_keys=False,
                    ),
                    encoding="utf-8",
                )
                scenario = parse_sdl_file(
                    root / "scenario.sdl.yaml", migration_policy="accept"
                )
                for namespace in ("default", "variation"):
                    composed = scenario.content[f"{namespace}.seed_inventory"]
                    if composed.text is not None:
                        payload = json.loads(
                            composed.text, parse_constant=_reject_non_finite
                        )
                        self.assertEqual(
                            set(payload), {item.name for item in composed.items}
                        )
                        if release.id == "infrastructure.cache-key-value-store":
                            prefix = cases[namespace]["key_prefix"]
                            key_binding = payload["seed_keys"][0]["key"]
                            self.assertEqual(
                                payload["keyspace"]["prefix_parameter"],
                                "key_prefix",
                            )
                            self.assertEqual(
                                key_binding["prefix_parameter"], "key_prefix"
                            )
                            self.assertEqual(
                                prefix + key_binding["suffix"], prefix + "status"
                            )
                            self.assertIn(prefix, composed.description)
                        if release.id == "infrastructure.postgresql-database":
                            service = scenario.nodes[
                                f"{namespace}.database"
                            ].model_dump(mode="json")["runtime"][
                                "database_services"
                            ][0]
                            database = service["databases"][0]
                            self.assertEqual(
                                payload["database"]["name_parameter"],
                                "database_name",
                            )
                            self.assertEqual(
                                database["name"], cases[namespace]["database_name"]
                            )
                            self.assertIn(database["name"], composed.description)
                            typed_schemas = {
                                schema["name"] for schema in database["schemas"]
                            }
                            self.assertEqual(
                                {schema["name"] for schema in payload["schemas"]},
                                typed_schemas,
                            )
                            typed_tables = {
                                (schema["name"], table["name"])
                                for schema in database["schemas"]
                                for table in schema["tables"]
                            }
                            self.assertEqual(
                                {
                                    (table["schema"], table["name"])
                                    for table in payload["tables"]
                                },
                                typed_tables,
                            )
                            self.assertEqual(
                                {role["name"] for role in payload["roles"]},
                                {role["name"] for role in service["roles"]},
                            )
                            self.assertLessEqual(
                                {
                                    tuple(row["table"].split(".", maxsplit=1))
                                    for row in payload["seed_rows"]
                                },
                                typed_tables,
                            )

    def test_newest_multi_node_releases_declare_internal_topology(self) -> None:
        observed_multi_node: set[str] = set()
        for release_root in _newest_releases():
            release = load_kit_release(release_root)
            module = yaml.safe_load(
                (release_root / "module.sdl.yaml").read_text(encoding="utf-8")
            )
            compute_nodes = {
                name
                for name, node in module["nodes"].items()
                if node["type"].lower() != "switch"
            }
            if len(compute_nodes) < 2:
                continue
            observed_multi_node.add(release.id)
            with self.subTest(kit=release.id, version=release.version):
                switch_nodes = {
                    name
                    for name, node in module["nodes"].items()
                    if node["type"].lower() == "switch"
                }
                self.assertTrue(switch_nodes)
                infrastructure = module.get("infrastructure", {})
                exported = module["module"]["exports"]
                self.assertLessEqual(
                    set(infrastructure), set(exported.get("infrastructure", []))
                )
                self.assertLessEqual(switch_nodes, set(infrastructure))
                for node_name in compute_nodes:
                    self.assertIn(node_name, infrastructure)
                    self.assertTrue(
                        switch_nodes.intersection(
                            infrastructure[node_name].get("links", [])
                        ),
                        f"{release.id} node {node_name} has no internal network",
                    )

                relationships = module.get("relationships", {})
                self.assertLessEqual(
                    set(relationships), set(exported.get("relationships", []))
                )
                actual_dependencies = {
                    (relationship["source"], relationship["target"])
                    for relationship in relationships.values()
                    if relationship["type"] == "depends_on"
                }
                self.assertEqual(
                    actual_dependencies, MULTI_NODE_DEPENDENCIES[release.id]
                )

                cases = yaml.safe_load(
                    (release_root / "tests/composition.yaml").read_text(
                        encoding="utf-8"
                    )
                )
                with tempfile.TemporaryDirectory() as tmp:
                    root = Path(tmp)
                    shutil.copy2(
                        release_root / "module.sdl.yaml", root / "module.sdl.yaml"
                    )
                    document = {
                        "name": "topology-composition",
                        "imports": [
                            {
                                "source": "local:module.sdl.yaml",
                                "namespace": "subject",
                                "version": module["module"]["version"],
                                "parameters": cases["default"],
                            }
                        ],
                    }
                    (root / "scenario.sdl.yaml").write_text(
                        yaml.safe_dump(document, sort_keys=False), encoding="utf-8"
                    )
                    scenario = parse_sdl_file(
                        root / "scenario.sdl.yaml", migration_policy="accept"
                    )
                    for node_name in compute_nodes:
                        links = scenario.infrastructure[
                            f"subject.{node_name}"
                        ].links
                        self.assertTrue(
                            any(link.startswith("subject.") for link in links)
                        )
                    composed_dependencies = {
                        (relationship.source, relationship.target)
                        for relationship in scenario.relationships.values()
                        if relationship.type.value == "depends_on"
                    }
                    self.assertEqual(
                        composed_dependencies,
                        {
                            (f"subject.{source}", f"subject.{target}")
                            for source, target in MULTI_NODE_DEPENDENCIES[
                                release.id
                            ]
                        },
                    )

        self.assertEqual(observed_multi_node, set(MULTI_NODE_DEPENDENCIES))

    def test_every_release_composes_with_two_parameter_sets(self) -> None:
        for manifest in sorted(ROOT.glob("kits/*/*/kit.yaml")):
            release = load_kit_release(manifest.parent)
            module = yaml.safe_load(
                (manifest.parent / "module.sdl.yaml").read_text(encoding="utf-8")
            )
            cases = yaml.safe_load(
                (manifest.parent / "tests/composition.yaml").read_text(
                    encoding="utf-8"
                )
            )
            domain_parameters = set(module["module"]["parameters"]) - {
                "deployment_profile",
                "service_label",
            }
            self.assertGreaterEqual(len(domain_parameters), 1, release.id)
            self.assertIn("seed_inventory", module["module"]["exports"]["content"])
            self.assertGreaterEqual(
                len(module["content"]["seed_inventory"]["items"]), 3, release.id
            )
            self.assertTrue(
                any(
                    cases["default"].get(parameter)
                    != cases["variation"].get(parameter)
                    for parameter in domain_parameters
                ),
                release.id,
            )
            for name in ("default", "variation"):
                with self.subTest(kit=release.id, case=name), tempfile.TemporaryDirectory() as tmp:
                    root = Path(tmp)
                    shutil.copy2(
                        manifest.parent / "module.sdl.yaml", root / "module.sdl.yaml"
                    )
                    document = {
                        "name": "composition",
                        "imports": [
                            {
                                "source": "local:module.sdl.yaml",
                                "namespace": "subject",
                                "version": module["module"]["version"],
                                "parameters": cases[name],
                            }
                        ],
                    }
                    (root / "scenario.sdl.yaml").write_text(
                        yaml.safe_dump(document, sort_keys=False), encoding="utf-8"
                    )
                    parse_sdl_file(
                        root / "scenario.sdl.yaml", migration_policy="accept"
                    )

    def test_every_release_has_substantive_authoring_material(self) -> None:
        for manifest in sorted(ROOT.glob("kits/*/*/kit.yaml")):
            release = load_kit_release(manifest.parent)
            readme = (manifest.parent / "README.md").read_text(encoding="utf-8")
            integration = (manifest.parent / "assets/integration.md").read_text(
                encoding="utf-8"
            )
            seed = yaml.safe_load(
                (manifest.parent / "assets/seed.yaml").read_text(encoding="utf-8")
            )
            self.assertIn("authoring content", readme.lower(), release.id)
            self.assertIn("## Exported RAES declarations", integration, release.id)
            self.assertIn("## Composition notes", integration, release.id)
            self.assertGreaterEqual(len(seed["declared_objects"]), 3, release.id)
            self.assertTrue(seed["integration_requirements"], release.id)

    def test_representative_multi_kit_environment_composes(self) -> None:
        selected = [
            "infrastructure.windows-active-directory-domain-controller",
            "infrastructure.browser-workstation",
            "infrastructure.authoritative-dns-service",
            "infrastructure.application-api-service",
            "infrastructure.postgresql-database",
            "infrastructure.wazuh-security-monitoring-stack",
            "infrastructure.telemetry-collector",
            *(f"infrastructure.{slug}" for slug in ISSUE_225_KITS),
        ]
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            imports = []
            for index, kit_id in enumerate(selected):
                source = ROOT / "kits" / kit_id / "1.0.0" / "module.sdl.yaml"
                target = root / f"module-{index}.sdl.yaml"
                shutil.copy2(source, target)
                imports.append(
                    {
                        "source": f"local:{target.name}",
                        "namespace": f"kit{index}",
                        "version": "1.0.0",
                        "parameters": {
                            "deployment_profile": "compact",
                            "service_label": f"service-{index}",
                        },
                    }
                )
            (root / "scenario.sdl.yaml").write_text(
                yaml.safe_dump(
                    {"name": "realistic-environment", "imports": imports},
                    sort_keys=False,
                ),
                encoding="utf-8",
            )
            scenario = parse_sdl_file(
                root / "scenario.sdl.yaml", migration_policy="accept"
            )
            self.assertGreaterEqual(len(scenario.nodes), 17)


if __name__ == "__main__":
    unittest.main()
