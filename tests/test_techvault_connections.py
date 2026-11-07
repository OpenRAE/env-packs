"""Read TechVault software connections through the public RAES model."""

from copy import deepcopy
from pathlib import Path
import unittest

import yaml
from raes import SDLError, instantiate_scenario, parse_sdl, parse_sdl_file
from raes_processor.compiler import compile_runtime_model

_PACKS = Path(__file__).resolve().parents[1] / "packs"
_APPLICATIONS = {
    "kali": {"aptl-red"},
    "soc-workstation": {
        "aptl-indexer", "aptl-wazuh", "aptl-network", "aptl-soar", "aptl-threatintel",
    },
}
_EXPECTED = {
    "aptl-red": {("connects_to", "nodes.kali.services.ssh", 22, "tcp")},
    "aptl-indexer": {
        ("connects_to", "nodes.wazuh-indexer.services.indexer-api", 9200, "tcp"),
        ("connects_to", "nodes.wazuh-manager.services.wazuh-api", 55000, "tcp"),
    },
    "aptl-wazuh": {
        ("connects_to", "nodes.wazuh-indexer.services.indexer-api", 9200, "tcp"),
        ("connects_to", "nodes.wazuh-manager.services.wazuh-api", 55000, "tcp"),
    },
    "aptl-network": {
        ("connects_to", "nodes.wazuh-indexer.services.indexer-api", 9200, "tcp"),
        ("depends_on", "nodes.suricata", None, None),
    },
    "aptl-soar": {("connects_to", "nodes.shuffle-frontend.services.https", 443, "tcp")},
    "aptl-threatintel": {("connects_to", "nodes.misp.services.https", 443, "tcp")},
}


class TechVaultConnectionTests(unittest.TestCase):
    def assert_connections(self, scenario):
        applications = {}
        for host, expected in _APPLICATIONS.items():
            inventory = scenario.nodes[host].runtime.platform_applications
            self.assertEqual({app.platform_application_id for app in inventory}, expected)
            for app in inventory:
                self.assertFalse(app.service, "stdio tools need no invented listener")
                applications[
                    f"nodes.{host}.runtime.platform_applications.{app.platform_application_id}"
                ] = app.platform_application_id
        targets = {f"nodes.{name}": (None, None) for name in scenario.nodes}
        targets.update({
            f"nodes.{name}.services.{service.name}": (service.port, service.protocol)
            for name, node in scenario.nodes.items()
            for service in node.services
        })
        actual = {application: set() for application in applications.values()}
        edges = {}
        for name, edge in scenario.relationships.items():
            if edge.source in applications:
                actual[applications[edge.source]].add(
                    (edge.type.value, edge.target, *targets[edge.target])
                )
                edges[name] = edge
        self.assertEqual(actual, _EXPECTED)
        self.assertEqual(len(edges), 9)
        self.assertEqual(scenario.nodes["suricata"].services, [])
        return edges

    def test_both_packs_declare_and_compile_every_connection(self):
        for name in ("techvault", "techvault-participant-study"):
            with self.subTest(pack=name):
                scenario = parse_sdl_file(_PACKS / name / "sdl" / f"{name}.sdl.yaml")
                edges = self.assert_connections(scenario)
                concrete = instantiate_scenario(
                    scenario, parameters={key: "FLAG{synthetic}" for key in scenario.variables},
                )
                model = compile_runtime_model(concrete)
                self.assertFalse(model.diagnostics)
                for key, edge in edges.items():
                    self.assertEqual(model.relationship_specs[key]["source"], edge.source)
                    self.assertEqual(model.relationship_specs[key]["target"], edge.target)

    def test_connection_targets_use_raes_reference_validation(self):
        path = _PACKS / "techvault/sdl/techvault.sdl.yaml"
        original = yaml.safe_load(path.read_text())
        for label, source, target in (
            ("missing application", "nodes.kali.runtime.platform_applications.missing", "nodes.kali.services.ssh"),
            ("missing service", "nodes.kali.runtime.platform_applications.aptl-red", "nodes.kali.services.missing"),
            ("missing node", "nodes.kali.runtime.platform_applications.aptl-red", "nodes.missing"),
        ):
            with self.subTest(mutation=label):
                changed = deepcopy(original)
                changed["relationships"]["probe"] = {
                    "type": "connects_to", "source": source, "target": target,
                }
                source_text = yaml.safe_dump(changed, sort_keys=False)
                with self.assertRaises(SDLError):
                    parse_sdl(source_text)

    def test_regression_detects_omitted_edges_and_wrong_ports(self):
        scenario = parse_sdl_file(_PACKS / "techvault/sdl/techvault.sdl.yaml")
        edges = self.assert_connections(scenario)
        changed = scenario.model_copy(deep=True)
        del changed.relationships[next(iter(edges))]
        with self.assertRaises(AssertionError):
            self.assert_connections(changed)
        changed = scenario.model_copy(deep=True)
        api = next(service for service in changed.nodes["wazuh-indexer"].services if service.name == "indexer-api")
        api.port = 9201
        with self.assertRaises(AssertionError):
            self.assert_connections(changed)
