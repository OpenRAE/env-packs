"""First-party TechVault pack contract.

These checks guard the portable in-world declarations and immutable content
bindings without becoming a second source of RAES scenario semantics.
"""

from __future__ import annotations

import copy
import hashlib
import io
import json
import os
import pathlib
import re
import shutil
import subprocess
import tarfile
import tempfile
import types
import unittest
from typing import NamedTuple
from unittest import mock

import yaml
from raes import SDLInstantiationError, instantiate_scenario, parse_sdl_file
from raes.realization_designation import (
    designation_records,
    resolve_realization_designation,
)
from raes_contracts.apparatus import (
    RealizationObservationCapability,
    RealizationSupportDeclaration,
)
from raes_contracts.vocabulary import (
    ObservationStrength,
    RealizationSupportMode,
    RealizationVerificationScope,
)
from raes_processor.compiler import compile_scenario_runtime_model
from raes_processor.semantics.realization_observation_admission import (
    has_required_observation_support,
)

from raes_env_packs import PackDigestError, resolve_pack_artifact, validate_pack
from raes_env_packs.digest import validate_pack_content_manifest
from tools import build_techvault_mcp_artifacts as mcp_builder


_ROOT = pathlib.Path(__file__).resolve().parents[1]
_PACK = _ROOT / "packs" / "techvault"
_SDL = _PACK / "sdl" / "techvault.sdl.yaml"
_BINDINGS = _PACK / "sdl" / "techvault.bindings.json"
_SCHEMES = _PACK / "sdl" / "techvault.schemes.json"
_BINDINGS_ARTIFACT = "techvault-pack-sdl-techvault-bindings-json"
_PORTAL_ROUTES = "nodes.webapp.runtime.applications.techvault-portal.routes."


class _Weakness(NamedTuple):
    route: str
    concept: str


# The portal's intentional weaknesses, keyed by binding id.
_WEBAPP_WEAKNESSES = {
    "webapp-sqli-login": _Weakness(route="login", concept="CWE-89"),
    "webapp-verbose-errors": _Weakness(route="login", concept="CWE-209"),
    "webapp-sqli-search": _Weakness(route="search", concept="CWE-89"),
    "webapp-xss-reflected": _Weakness(route="search", concept="CWE-79"),
    "webapp-cmdi-ping": _Weakness(route="ping-tool", concept="CWE-78"),
    "webapp-xss-stored": _Weakness(route="comment", concept="CWE-79"),
    "webapp-idor-files": _Weakness(route="api-file", concept="CWE-639"),
    "webapp-idor-users": _Weakness(route="api-user", concept="CWE-639"),
    "webapp-missing-authz-admin": _Weakness(route="admin", concept="CWE-862"),
    "webapp-weak-jwt": _Weakness(route="api-token", concept="CWE-330"),
    "webapp-hardcoded-secrets": _Weakness(route="api-token", concept="CWE-798"),
    "webapp-unrestricted-upload": _Weakness(route="upload", concept="CWE-434"),
    "webapp-debug-endpoint": _Weakness(route="debug", concept="CWE-489"),
    "webapp-env-disclosure": _Weakness(route="debug", concept="CWE-538"),
}
_CWE_SCHEME = {
    "scheme_id": "mitre-cwe",
    "authority": "MITRE Common Weakness Enumeration",
    "revision": "4.20",
    "source_locator": "https://cwe.mitre.org/data/xml/cwec_v4.20.xml.zip",
    "source_digest": "sha256:3976f599e5e5200219a3108bb896d06e2a88fbb293369e1883cb423a5e9d7d50",
}
_PROFILE = _PACK / "profiles" / "exact-artifact-copy-v1.json"
_VALIDATOR = _PACK / "validation" / "validate_techvault.py"


def _load_pack_validator() -> types.ModuleType:
    module = types.ModuleType("techvault_pack_validator")
    module.__file__ = str(_VALIDATOR)
    source = _VALIDATOR.read_text(encoding="utf-8")
    exec(compile(source, str(_VALIDATOR), "exec"), module.__dict__)
    return module


_PACK_VALIDATOR = _load_pack_validator()

_PACK_ARTIFACT_CONTENT_IDS = frozenset(
    {
        "webapp-rules",
        "suricata-rules",
        "ad-rules",
        "database-rules",
        "falco-rules",
        "postgresql-decoders",
        "samba-decoders",
        "wazuh-integrations",
        "misp-suricata-sync-pyproject",
        "misp-suricata-sync-readme",
        "misp-suricata-sync-hatch-build",
        "misp-suricata-sync-src",
        "cortex-analyzer-executable",
        "cortex-analyzer-definition",
        "mcp-red-sources",
        "mcp-blue-sources",
        "suricata-config",
        "suricata-local-rules",
        "suricata-misp-ioc-rules-seed",
        "suricata-misp-md5-seed",
        "suricata-misp-sha1-seed",
        "suricata-misp-sha256-seed",
        "webapp-app-code",
        "dns-named-conf",
        "dns-zone-fwd",
        "dns-zone-rev",
        "fileshare-smb-conf",
        "fileshare-shares",
        "workstation-dev-user-home",
        "db-init-schema",
        "db-init-seed",
    }
)

_GENERATED_SSH_CONTENT_IDS = frozenset(
    {
        "workstation-dev-user-privkey",
        "workstation-dev-user-pubkey",
        "victim-authorized-keys",
        "workstation-authorized-keys",
        "workstation-pivot-key",
        "kali-authorized-keys",
        "kali-pivot-key",
    }
)

_UNDERDECLARED_RUNTIME_NODES = frozenset(
    {
        "thehive",
        "cortex",
        "misp",
        "misp-db",
        "misp-redis",
        "wazuh-dashboard",
        "shuffle-backend",
        "shuffle-frontend",
        "ad",
    }
)


def _load_sdl() -> dict:
    return yaml.safe_load(_SDL.read_text(encoding="utf-8"))


def _canonical_json_digest(document: object) -> str:
    payload = json.dumps(
        document, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    ).encode("utf-8")
    return "sha256:" + hashlib.sha256(payload).hexdigest()


def _assert_shuffle_runtime_contract(test: unittest.TestCase, sdl: dict) -> None:
    """Assert Shuffle's typed in-world application and datastore state."""
    backend = sdl["nodes"]["shuffle-backend"]
    opensearch = sdl["nodes"]["shuffle-opensearch"]
    for node in (backend, opensearch):
        test.assertNotIn("environment", node["runtime"])
        test.assertNotIn("container", node["runtime"])

    (application,) = backend["runtime"]["platform_applications"]
    test.assertEqual(application["platform_application_id"], "shuffle-soar")
    test.assertEqual(application["product"], "Shuffle")
    test.assertEqual(application["version"], "unversioned")
    test.assertEqual(
        application["upstream_bindings"][0]["target_node_ref"],
        "shuffle-opensearch",
    )

    (datastore,) = opensearch["runtime"]["datastore_services"]
    test.assertEqual(datastore["engine"], "opensearch")
    test.assertEqual(datastore["version"], "2.14.0")
    test.assertEqual(datastore["protocol"], "https")
    test.assertFalse(datastore["transport_security"]["client_verification"])
    test.assertEqual(sdl["persistent_volumes"]["shuffle_data"]["lifecycle"], "retain")


def _assert_shuffle_orborus_contract(test: unittest.TestCase, sdl: dict) -> None:
    """Assert Orborus is an in-world component without a launch method."""
    runtime = sdl["nodes"]["shuffle-orborus"]["runtime"]
    (component,) = runtime["software_components"]
    test.assertEqual(component["component_id"], "shuffle-orborus")
    test.assertEqual(component["version"], "unversioned")
    for field in (
        "environment",
        "local_control_interfaces",
        "orchestration_authorities",
    ):
        test.assertNotIn(field, runtime)


class TechVaultPackTests(unittest.TestCase):
    def test_pack_and_byte_manifest_validate(self) -> None:
        result = validate_pack(_PACK)
        self.assertTrue(result.ok, result.errors)
        validate_pack_content_manifest(_PACK)

    def test_real_pack_manifest_fails_closed_on_inventory_drift(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            staged = pathlib.Path(directory) / "techvault"
            shutil.copytree(_PACK, staged)
            asset = staged / "assets" / "content" / "dns-named.conf"
            original = asset.read_bytes()

            asset.write_bytes(original + b"\n")
            with self.assertRaises(PackDigestError):
                validate_pack_content_manifest(staged)

            asset.write_bytes(original)
            extra = staged / "assets" / "content" / "undeclared.txt"
            extra.write_text("not in manifest\n", encoding="utf-8")
            with self.assertRaises(PackDigestError):
                validate_pack_content_manifest(staged)

            extra.unlink()
            asset.unlink()
            with self.assertRaises(PackDigestError):
                validate_pack_content_manifest(staged)

    def test_full_sdl_topology_is_preserved(self) -> None:
        sdl = _load_sdl()
        self.assertEqual(sdl["name"], "techvault")
        expected_counts = {
            "nodes": 29,
            "infrastructure": 29,
            "persistent_volumes": 19,
            "propositions": 3,
            "assertions": 3,
            "observation_boundaries": 1,
            "evidence_requirements": 4,
            "identity_domains": 1,
            "relationships": 2,
            "accounts": 14,
            "variables": 10,
            "entities": 2,
            "agents": 2,
        }
        for section, expected in expected_counts.items():
            with self.subTest(section=section):
                self.assertEqual(len(sdl[section]), expected)

        self.assertNotIn("features", sdl)
        self.assertNotIn("source", sdl["nodes"]["kali"])

    def test_realization_is_open_below_the_declared_contract(self) -> None:
        sdl = _load_sdl()
        scenario = parse_sdl_file(_SDL)

        # This pack is authoritative over substrate, topology, declared
        # services, declared content and the runtime families it states -- not
        # over the operating system. Closed-world means the SDL is total
        # authority, so anything undeclared must not exist; asserting that over
        # a real Debian or Kali image would claim a completeness this pack does
        # not have, and no honest backend could admit it.
        self.assertEqual(sdl["realization"].get("default"), "open")
        self.assertEqual(scenario.realization.default.value, "open")

        records = designation_records(scenario.realization)
        for pointer in (
            "/nodes/kali/runtime/packages",
            "/nodes/kali/runtime/forwarding_agents",
            "/nodes/kali/runtime/filesystem_inventory",
            "/nodes/kali/runtime/processes",
            "/nodes/wazuh-manager/runtime/environment",
        ):
            with self.subTest(field_pointer=pointer):
                self.assertEqual(
                    resolve_realization_designation(
                        records, field_pointer=pointer
                    ).closure.value,
                    "open-world",
                )

        self.assertEqual(scenario.realization.constraints, ())

    def test_redteam_activity_is_declared_as_a_need_not_a_collector(self) -> None:
        requirement = _load_sdl()["evidence_requirements"]["redteam-session-transcript"]

        # The research need is what the red team did: the commands issued and
        # the responses returned. The pack states the need and names no
        # collector, so the backend answers it with its own capture offer.
        self.assertEqual(requirement["source_class"], "apparatus")
        self.assertNotIn("source_refs", requirement)
        self.assertEqual(requirement["scope_refs"], ["nodes.kali"])
        self.assertEqual(requirement["channel"], "participant_output")
        self.assertEqual(requirement["retention"], "run_lifetime")
        self.assertEqual(requirement["loss_disclosure"], "required")

        # The removed sidecar held its evidence where the participant could not
        # reach it. That intent survives as a stated expectation rather than as
        # a mechanism the pack ships.
        self.assertEqual(requirement["integrity"], "chain_of_custody")
        self.assertEqual(requirement["redaction"], "redact_secrets")

        for field in ("scope", "description"):
            with self.subTest(field=field):
                self.assertNotRegex(
                    requirement[field].lower(),
                    r"tcpdump|grafana|tempo|otel|opentelemetry|sidecar|collector agent",
                )

    def test_backend_measurement_apparatus_is_excised(self) -> None:
        sdl = _load_sdl()
        removed = {
            "aptl-otel-collector",
            "aptl-tempo",
            "aptl-grafana-otel",
            "kali-capture",
        }

        self.assertEqual(removed & set(sdl["nodes"]), set())
        self.assertEqual(removed & set(sdl["infrastructure"]), set())
        for name, entry in sdl["infrastructure"].items():
            with self.subTest(infrastructure=name):
                self.assertEqual(removed & set(entry.get("dependencies", [])), set())

        self.assertNotIn("constraints", sdl["realization"])

        for section in ("persistent_volumes", "generated_artifacts"):
            for name, entry in sdl[section].items():
                with self.subTest(section=section, entry=name):
                    consumers = {item["node"] for item in entry.get("consumers", [])}
                    self.assertEqual(removed & consumers, set())

        self.assertEqual(
            removed & {content.get("target") for content in sdl["content"].values()},
            set(),
        )

        # Nothing may survive by name: a stray dependency, upstream binding, or
        # config body would reintroduce the backend coupling the excision removes.
        raw = _SDL.read_text(encoding="utf-8")
        for node_id in removed:
            with self.subTest(node=node_id):
                self.assertNotIn(node_id, raw)

        # The pack declares WHAT must be captured, never the apparatus that
        # captures it. In-world security tooling (Suricata, Wazuh and the rest
        # of the SOC stack) is scenario content and stays; anything whose only
        # job is feeding evidence capture belongs to the realizing backend,
        # which answers an evidence requirement with its own capture offer.
        for node_id, node in sdl["nodes"].items():
            runtime = node.get("runtime") or {}
            for sensor in runtime.get("network_sensors", []) or []:
                with self.subTest(node=node_id, sensor=sensor["network_sensor_id"]):
                    self.assertNotIn("evidence_refs", sensor)
            for agent in runtime.get("forwarding_agents", []) or []:
                with self.subTest(node=node_id, agent=agent["forwarding_agent_id"]):
                    self.assertNotEqual(
                        agent.get("ownership_role", "system_under_test"),
                        "measurement_apparatus",
                    )
        for agent in sdl.get("forwarding_agents", []) or []:
            with self.subTest(agent=agent["forwarding_agent_id"]):
                self.assertNotEqual(
                    agent.get("ownership_role", "system_under_test"),
                    "measurement_apparatus",
                )

    def test_shuffle_runtime_contract_is_complete_and_consistent(self) -> None:
        _assert_shuffle_runtime_contract(self, _load_sdl())

    def test_shuffle_orborus_contract_is_complete_and_consistent(self) -> None:
        _assert_shuffle_orborus_contract(self, _load_sdl())

    def test_shuffle_contract_omits_backend_launch_controls(self) -> None:
        sdl = _load_sdl()
        for node_id in (
            "shuffle-backend",
            "shuffle-frontend",
            "shuffle-opensearch",
            "shuffle-orborus",
        ):
            with self.subTest(node=node_id):
                runtime = sdl["nodes"][node_id]["runtime"]
                self.assertNotIn("environment", runtime)
                self.assertNotIn("container", runtime)
                self.assertNotIn("orchestration_authorities", runtime)

    def test_all_original_content_obligations_are_accounted_for(self) -> None:
        content = _load_sdl()["content"]
        self.assertLessEqual(_PACK_ARTIFACT_CONTENT_IDS, set(content))
        self.assertTrue(_GENERATED_SSH_CONTENT_IDS.isdisjoint(content))
        inline = {name for name, item in content.items() if "text" in item}
        sourced = {name for name, item in content.items() if "source" in item}
        materialized = {
            name
            for name, item in content.items()
            if "service_materialization" in item
        }
        self.assertEqual(inline & sourced, set())
        self.assertEqual(inline & materialized, set())
        self.assertEqual(sourced & materialized, set())
        self.assertEqual(inline | sourced | materialized, set(content))
        self.assertEqual(len(inline), 15)
        self.assertEqual(sourced, _PACK_ARTIFACT_CONTENT_IDS)
        self.assertEqual(materialized, set())
        self.assertEqual(len(content) + len(_GENERATED_SSH_CONTENT_IDS), 53)

    def test_loaded_wazuh_content_sets_have_real_placements(self) -> None:
        sdl = _load_sdl()
        manager = sdl["nodes"]["wazuh-manager"]
        (monitoring_manager,) = manager["runtime"]["security_monitoring_managers"]
        content = sdl["content"]

        for content_set in monitoring_manager["content_sets"]:
            with self.subTest(content_id=content_set["content_id"]):
                self.assertTrue(content_set["loaded"])
                placement = content[content_set["content_id"]]
                self.assertEqual(placement["target"], "wazuh-manager")
                self.assertEqual(
                    pathlib.PurePosixPath(placement["path"]).name,
                    content_set["name"],
                )
                # file_count counts files, not the rules or decoders in them
                # (#343): each corpus ships as exactly its one placed file.
                self.assertEqual(content_set["file_refs"], [placement["path"]])
                self.assertEqual(content_set["file_count"], 1)

    def test_pack_validator_rejects_wazuh_definition_counts_as_file_counts(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            staged = pathlib.Path(directory) / "techvault"
            shutil.copytree(_PACK, staged)
            sdl_path = staged / "sdl" / "techvault.sdl.yaml"
            text = sdl_path.read_text(encoding="utf-8")
            webapp = (
                "name: webapp_rules.xml\n"
                "              file_count: 1\n"
            )
            self.assertEqual(text.count(webapp), 1)
            sdl_path.write_text(
                text.replace(webapp, webapp.replace("file_count: 1", "file_count: 11")),
                encoding="utf-8",
            )
            self.assertIn(
                "content-set.file-count-mismatch: sdl/techvault.sdl.yaml:"
                "nodes.wazuh-manager.runtime.security_monitoring_managers[0]"
                ".content_sets[0].file_count",
                validate_pack(staged).errors,
            )

    def test_suricata_content_contract_is_complete(self) -> None:
        errors = _PACK_VALIDATOR.validate_suricata_contract(_PACK, _load_sdl())
        self.assertEqual(errors, [])

        local = resolve_pack_artifact(
            _PACK, "techvault-suricata-local-rules"
        ).data.decode("utf-8")
        active = [
            line
            for line in local.splitlines()
            if line.strip() and not line.lstrip().startswith("#")
        ]
        self.assertEqual(len(active), 16)
        self.assertEqual(
            tuple(int(value) for value in re.findall(r"\bsid:(\d+);", local)),
            (
                1000001,
                1000002,
                1000010,
                1000011,
                1000012,
                1000020,
                1000030,
                1000031,
                1000040,
                1000050,
                1000060,
                1000061,
                1000070,
                1000080,
                1000090,
                1000091,
            ),
        )
        self.assertIn(
            'content:"UNION"; nocase; content:"SELECT"',
            next(line for line in active if "sid:1000010;" in line),
        )

        manifest = json.loads(
            (_PACK / "associated-artifacts.json").read_text(encoding="utf-8")
        )["artifacts"]
        pinned_source = "aptl@3db5171f3e4add842efd1d81fa0d4fe078511b7e"
        for artifact_id in (
            "techvault-suricata-local-rules",
            "techvault-suricata-misp-ioc-rules-seed",
            "techvault-suricata-misp-md5-seed",
            "techvault-suricata-misp-sha1-seed",
            "techvault-suricata-misp-sha256-seed",
        ):
            self.assertEqual(manifest[artifact_id]["source"], pinned_source)
        self.assertIn(pinned_source, manifest["techvault-suricata-config"]["source"])

    def test_suricata_content_contract_rejects_broken_variants(self) -> None:
        original = _load_sdl()
        local_artifact = "techvault-suricata-local-rules"
        config_artifact = "techvault-suricata-config"
        wazuh_artifact = "techvault-wazuh-suricata-rules"

        def resolve_path(sdl, path):
            target = sdl
            for key in path:
                target = target[key]
            return target

        def set_path(path, value):
            def mutate(sdl, assets):
                target = resolve_path(sdl, path[:-1])
                target[path[-1]] = value

            return mutate

        def update_named(path, identity_key, identity, updates):
            def mutate(sdl, assets):
                item = next(
                    candidate
                    for candidate in resolve_path(sdl, path)
                    if candidate.get(identity_key) == identity
                )
                item.update(updates)

            return mutate

        def replace_artifact(artifact_id, before, after):
            return lambda sdl, assets: assets.update(
                {artifact_id: assets[artifact_id].replace(before, after)}
            )

        def replace_local(before: bytes, after: bytes):
            return replace_artifact(local_artifact, before, after)

        def null_rule_files(sdl, assets):
            config = yaml.safe_load(assets[config_artifact].decode("utf-8"))
            config["rule-files"] = None
            assets[config_artifact] = yaml.safe_dump(config).encode("utf-8")

        cases = {
            "empty local corpus": (
                lambda sdl, assets: assets.update({local_artifact: b""}),
                "suricata.local-rules-empty",
            ),
            "header-only local corpus": (
                lambda sdl, assets: assets.update(
                    {local_artifact: b"# no active local rules\n"}
                ),
                "suricata.local-rules-zero-effective",
            ),
            "undefined rule variable": (
                replace_local(b"$HTTP_SERVERS", b"$UNDEFINED_SERVERS"),
                "suricata.rule-variable-undefined",
            ),
            "selected rule file missing": (
                lambda sdl, assets: assets.update(
                    {
                        config_artifact: assets[config_artifact].replace(
                            b"/etc/suricata/rules/local.rules",
                            b"/etc/suricata/rules/missing.rules",
                        )
                    }
                ),
                "suricata.rule-file-unresolved",
            ),
            "malformed rule file list": (
                null_rule_files,
                "suricata.rule-files-invalid",
            ),
            "content provenance mismatch": (
                lambda sdl, assets: sdl["content"]["suricata-local-rules"][
                    "source"
                ]["artifact_requirement"]["exact_artifact"].update(
                    {"digest": "sha256:" + "0" * 64}
                ),
                "suricata.content-identity-mismatch",
            ),
            "declared zero effective rules": (
                lambda sdl, assets: next(
                    source
                    for source in sdl["nodes"]["suricata"]["runtime"][
                        "network_detection_engines"
                    ][0]["rule_sources"]
                    if source["source_id"] == "techvault-local"
                ).update({"rule_count": 0}),
                "suricata.local-rule-count-mismatch",
            ),
            "reload target mismatch": (
                lambda sdl, assets: sdl["nodes"]["misp-suricata-sync"][
                    "runtime"
                ]["forwarding_agents"][0]["reload_channels"][0].update(
                    {"target_ref": "suricata"}
                ),
                "suricata.reload-target-mismatch",
            ),
            "content placement mismatch": (
                set_path(("content", "suricata-config", "path"), "/tmp/suricata.yaml"),
                "suricata.content-placement-mismatch: suricata-config",
            ),
            "invalid configuration bytes": (
                lambda sdl, assets: assets.update({config_artifact: b"["}),
                "suricata.config-invalid: suricata-config",
            ),
            "invalid local rule encoding": (
                lambda sdl, assets: assets.update({local_artifact: b"\xff"}),
                "suricata.local-rules-invalid: suricata-local-rules",
            ),
            "non-alert local action": (
                replace_local(b"alert http", b"drop http"),
                "suricata.local-rule-action-invalid: all local rules must be alert rules",
            ),
            "local SID corpus mismatch": (
                replace_local(b"sid:1000091;", b"sid:1000092;"),
                "suricata.local-rule-sids-mismatch: expected the authoritative 16-SID corpus",
            ),
            "nonzero MISP seed": (
                replace_artifact(
                    "techvault-suricata-misp-ioc-rules-seed",
                    b"# ioc_count=0",
                    b"# ioc_count=1",
                ),
                "suricata.misp-seed-invalid: the initial generated source must declare zero indicators",
            ),
            "missing engine identity": (
                set_path(
                    (
                        "nodes",
                        "suricata",
                        "runtime",
                        "network_detection_engines",
                        0,
                        "network_detection_engine_id",
                    ),
                    "other-engine",
                ),
                "suricata.engine-missing: suricata-engine",
            ),
            "configuration reference mismatch": (
                set_path(
                    (
                        "nodes",
                        "suricata",
                        "runtime",
                        "network_detection_engines",
                        0,
                        "configuration_file_refs",
                    ),
                    [],
                ),
                "suricata.configuration-ref-mismatch: suricata-engine",
            ),
            "log reference mismatch": (
                set_path(
                    (
                        "nodes",
                        "suricata",
                        "runtime",
                        "network_detection_engines",
                        0,
                        "log_file_refs",
                    ),
                    [],
                ),
                "suricata.output-ref-mismatch: suricata-engine",
            ),
            "rule source mismatch": (
                update_named(
                    (
                        "nodes",
                        "suricata",
                        "runtime",
                        "network_detection_engines",
                        0,
                        "rule_sources",
                    ),
                    "source_id",
                    "techvault-local",
                    {"loaded": False},
                ),
                "suricata.rule-source-mismatch: techvault-local",
            ),
            "EVE output mismatch": (
                update_named(
                    (
                        "nodes",
                        "suricata",
                        "runtime",
                        "network_detection_engines",
                        0,
                        "output_streams",
                    ),
                    "stream_id",
                    "eve-json",
                    {"path": "/tmp/eve.json"},
                ),
                "suricata.output-ref-mismatch: eve-json",
            ),
            "generated source mismatch": (
                update_named(
                    (
                        "nodes",
                        "suricata",
                        "runtime",
                        "network_detection_engines",
                        0,
                        "rule_sources",
                    ),
                    "source_id",
                    "misp-iocs",
                    {"generated_by": "other"},
                ),
                "suricata.generated-source-mismatch: misp-iocs",
            ),
            "SID namespace mismatch": (
                update_named(
                    (
                        "nodes",
                        "misp-suricata-sync",
                        "runtime",
                        "forwarding_agents",
                        0,
                        "transforms",
                    ),
                    "transform_id",
                    "ioc-to-suricata-rules",
                    {"sid_namespace": "98000000"},
                ),
                "suricata.sid-namespace-mismatch: ioc-to-suricata-rules",
            ),
            "control channel path mismatch": (
                update_named(
                    (
                        "nodes",
                        "suricata",
                        "runtime",
                        "network_detection_engines",
                        0,
                        "control_channels",
                    ),
                    "channel_id",
                    "command-socket",
                    {"path": "/tmp/suricata-command.socket"},
                ),
                "suricata.control-channel-mismatch: command-socket",
            ),
            "control channel capability mismatch": (
                update_named(
                    (
                        "nodes",
                        "suricata",
                        "runtime",
                        "network_detection_engines",
                        0,
                        "control_channels",
                    ),
                    "channel_id",
                    "command-socket",
                    {"capabilities": []},
                ),
                "suricata.control-channel-mismatch: command-socket",
            ),
            "duplicate shared runtime mount": (
                lambda sdl, assets: sdl["nodes"]["suricata"]["runtime"].setdefault(
                    "mounts", []
                ).append(
                    {
                        "source": "suricata_command_socket",
                        "destination": "/var/run/suricata",
                    }
                ),
                "suricata.shared-volume-mismatch: duplicate runtime mount on suricata",
            ),
            "stale config seed": (
                lambda sdl, assets: sdl["persistent_volumes"].update(
                    {"suricata_config_seed": {}}
                ),
                "suricata.stale-config-seed: suricata_config_seed",
            ),
            "shared volume access mismatch": (
                set_path(
                    ("persistent_volumes", "suricata_command_socket", "access_mode"),
                    "read_write_once",
                ),
                "suricata.shared-volume-mismatch: suricata_command_socket",
            ),
            "shared volume consumers mismatch": (
                set_path(
                    ("persistent_volumes", "suricata_misp_rules", "consumers"),
                    [],
                ),
                "suricata.shared-volume-mismatch: suricata_misp_rules",
            ),
            "readiness proposition mismatch": (
                set_path(
                    ("propositions", "suricata-local-rules-ready", "subjects"), []
                ),
                "suricata.readiness-evidence-mismatch: suricata-local-rules-ready",
            ),
            "detection proposition mismatch": (
                set_path(
                    (
                        "propositions",
                        "suricata-login-sqli-detected",
                        "evidence_requirements",
                    ),
                    [],
                ),
                "suricata.detection-evidence-mismatch: suricata-login-sqli-detected",
            ),
            "detection assertion mismatch": (
                set_path(
                    ("assertions", "suricata-login-sqli-detected", "role"),
                    "invariant",
                ),
                "suricata.detection-evidence-mismatch: suricata-login-sqli-detected",
            ),
            "readiness evidence sources mismatch": (
                set_path(
                    (
                        "evidence_requirements",
                        "suricata-local-rule-readiness",
                        "source_refs",
                    ),
                    [],
                ),
                "suricata.readiness-evidence-mismatch: suricata-local-rule-readiness",
            ),
            "readiness evidence scope mismatch": (
                set_path(
                    (
                        "evidence_requirements",
                        "suricata-local-rule-readiness",
                        "scope_refs",
                    ),
                    [],
                ),
                "suricata.readiness-evidence-mismatch: suricata-local-rule-readiness",
            ),
            "alert evidence sources mismatch": (
                set_path(
                    (
                        "evidence_requirements",
                        "suricata-login-sqli-alert",
                        "source_refs",
                    ),
                    [],
                ),
                "suricata.detection-evidence-mismatch: suricata-login-sqli-alert sources",
            ),
            "alert trigger mismatch": (
                set_path(
                    (
                        "evidence_requirements",
                        "suricata-login-sqli-alert",
                        "trigger_ref",
                    ),
                    "nodes.other",
                ),
                "suricata.detection-evidence-mismatch: suricata-login-sqli-alert path",
            ),
            "alert scope refs mismatch": (
                set_path(
                    (
                        "evidence_requirements",
                        "suricata-login-sqli-alert",
                        "scope_refs",
                    ),
                    [],
                ),
                "suricata.detection-evidence-mismatch: suricata-login-sqli-alert path",
            ),
            "alert identity scope mismatch": (
                set_path(
                    (
                        "evidence_requirements",
                        "suricata-login-sqli-alert",
                        "scope",
                    ),
                    "unrelated alert",
                ),
                "suricata.detection-evidence-mismatch: expected alert identities",
            ),
            "login route weakness mismatch": (
                lambda sdl, assets: assets.update(
                    {
                        _BINDINGS_ARTIFACT: json.dumps(
                            {
                                **json.loads(assets[_BINDINGS_ARTIFACT]),
                                "bindings": {
                                    binding_id: binding
                                    for binding_id, binding in json.loads(
                                        assets[_BINDINGS_ARTIFACT]
                                    )["bindings"].items()
                                    if binding_id != "webapp-sqli-login"
                                },
                            }
                        ).encode("utf-8")
                    }
                ),
                "suricata.detection-path-mismatch: webapp login weakness",
            ),
            "Wazuh detection rule mismatch": (
                lambda sdl, assets: assets.update({wazuh_artifact: b"<group/>"}),
                "suricata.detection-path-mismatch: Wazuh rule 303020",
            ),
        }

        artifact_ids = (
            local_artifact,
            config_artifact,
            "techvault-suricata-misp-ioc-rules-seed",
            "techvault-suricata-misp-md5-seed",
            "techvault-suricata-misp-sha1-seed",
            "techvault-suricata-misp-sha256-seed",
            wazuh_artifact,
            _BINDINGS_ARTIFACT,
        )
        resolved_artifacts = {
            artifact_id: resolve_pack_artifact(_PACK, artifact_id)
            for artifact_id in artifact_ids
        }
        base_assets = {
            artifact_id: resolved.data
            for artifact_id, resolved in resolved_artifacts.items()
        }

        # The canonical resolver is tested independently and above supplies
        # real byte-bound results. Reuse those immutable results so this
        # mutation matrix isolates every validator branch without revalidating
        # the complete pack artifact set hundreds of times.
        with mock.patch.object(
            _PACK_VALIDATOR,
            "resolve_pack_artifact",
            side_effect=lambda pack_root, artifact_id: resolved_artifacts[artifact_id],
        ):
            for name, (mutate, expected_code) in cases.items():
                with self.subTest(mutation=name):
                    candidate = copy.deepcopy(original)
                    assets = dict(base_assets)
                    mutate(candidate, assets)
                    errors = _PACK_VALIDATOR.validate_suricata_contract(
                        _PACK,
                        candidate,
                        artifact_overrides=assets,
                    )
                    self.assertTrue(
                        any(expected_code in error for error in errors),
                        errors,
                    )

    def test_underdeclared_nodes_have_complete_runtime_contracts(self) -> None:
        nodes = _load_sdl()["nodes"]
        expected_runtime_keys = {
            "thehive": {"applications", "platform_applications", "service_listeners"},
            "cortex": {"applications", "platform_applications", "service_listeners"},
            "misp": {"applications", "platform_applications", "service_listeners"},
            "misp-db": {"database_services", "service_listeners"},
            "misp-redis": {"datastore_services", "service_listeners"},
            "wazuh-dashboard": {
                "applications",
                "platform_applications",
                "service_listeners",
            },
            "shuffle-backend": {
                "applications",
                "platform_applications",
                "service_listeners",
            },
            "shuffle-frontend": {"applications", "service_listeners"},
            "ad": {"identity_authorities", "service_listeners"},
        }
        self.assertEqual(set(expected_runtime_keys), _UNDERDECLARED_RUNTIME_NODES)

        for node_name, required_keys in expected_runtime_keys.items():
            with self.subTest(node=node_name):
                runtime = nodes[node_name]["runtime"]
                self.assertLessEqual(required_keys, set(runtime))
                for method_field in (
                    "container",
                    "environment",
                    "mounts",
                    "operational_policy",
                ):
                    self.assertNotIn(method_field, runtime)

                listeners = {
                    listener["service"]: listener
                    for listener in runtime.get("service_listeners", [])
                }
                for service in nodes[node_name]["services"]:
                    listener = listeners[service["name"]]
                    self.assertEqual(listener["port"], service["port"])
                    self.assertEqual(listener["protocol"], service["protocol"])
                    self.assertNotIn("role", listener)

    def test_underdeclared_runtime_joins_are_explicit_and_portable(self) -> None:
        sdl = _load_sdl()
        nodes = sdl["nodes"]
        infrastructure = sdl["infrastructure"]

        expected_application_services = {
            "thehive": "thehive-api",
            "cortex": "cortex-api",
            "misp": "https",
            "wazuh-dashboard": "dashboard",
            "shuffle-backend": "shuffle-api",
            "shuffle-frontend": "https",
        }
        for node_name, service in expected_application_services.items():
            with self.subTest(application=node_name):
                (application,) = nodes[node_name]["runtime"]["applications"]
                self.assertEqual(application["service"], service)
                self.assertTrue(application["routes"])

        thehive_bindings = {
            item["role"]: (item["target_node_ref"], item["target_service_ref"])
            for item in nodes["thehive"]["runtime"]["platform_applications"][0][
                "upstream_bindings"
            ]
        }
        self.assertEqual(
            thehive_bindings,
            {
                "cql_backend": ("thehive-cassandra", "cassandra"),
                "index_backend": ("thehive-es", "elasticsearch"),
                "backend_api": ("cortex", "cortex-api"),
            },
        )
        self.assertEqual(
            infrastructure["thehive"]["dependencies"],
            ["thehive-cassandra", "thehive-es", "cortex"],
        )

        misp_runtime = nodes["misp"]["runtime"]
        self.assertEqual(
            misp_runtime["platform_applications"][0]["platform_kind"],
            "threat_intel",
        )
        self.assertEqual(
            infrastructure["misp"]["dependencies"], ["misp-db", "misp-redis"]
        )
        (database,) = nodes["misp-db"]["runtime"]["database_services"]
        self.assertEqual(
            (database["service"], database["engine"], database["protocol"]),
            ("mysql", "mariadb", "mysql"),
        )
        self.assertEqual(database["databases"][0]["name"], "misp")

        (redis,) = nodes["misp-redis"]["runtime"]["datastore_services"]
        self.assertEqual(
            (redis["service"], redis["engine"], redis["data_model"]),
            ("redis", "redis", "key_value"),
        )
        self.assertEqual(redis["persistence"]["eviction"], "noeviction")

        (authority,) = nodes["ad"]["runtime"]["identity_authorities"]
        self.assertEqual(authority["kind"], "domain")
        self.assertEqual(authority["domain_name"], "techvault.local")
        self.assertEqual(
            {item["protocol"] for item in authority["services"]},
            {"ldap", "kerberos", "ad_ds_rpc"},
        )

        mount_owned_nodes = {
            "thehive",
            "cortex",
            "misp",
            "misp-suricata-sync",
            "misp-db",
            "wazuh-dashboard",
            "shuffle-backend",
            "shuffle-frontend",
            "ad",
        }
        for node_name in mount_owned_nodes:
            self.assertNotIn("mounts", nodes[node_name]["runtime"])

        declared_destinations: dict[str, set[str]] = {}
        for content in sdl["content"].values():
            if path := content.get("path"):
                declared_destinations.setdefault(content["target"], set()).add(path)
        for volume in sdl["persistent_volumes"].values():
            for consumer in volume.get("consumers", []):
                declared_destinations.setdefault(consumer["node"], set()).add(
                    consumer["mount_destination"]
                )
        for artifact in sdl["generated_artifacts"].values():
            for consumer in artifact.get("consumers", []):
                declared_destinations.setdefault(consumer["node"], set()).add(
                    consumer["mount_destination"]
                )
        expected_destinations = {
            "thehive": "/opt/thp/thehive/data",
            "cortex": "/opt/cortex/jobs",
            "misp": "/var/www/MISP/app/Config",
            "misp-suricata-sync": "/opt/techvault/soc-certs",
            "misp-db": "/var/lib/mysql",
            "wazuh-dashboard": "/usr/share/wazuh-dashboard/data/wazuh/config",
            "shuffle-backend": "/shuffle-database",
            "shuffle-frontend": "/opt/techvault/soc-certs",
            "ad": "/var/lib/samba",
        }
        self.assertEqual(set(expected_destinations), mount_owned_nodes)
        for node_name, destination in expected_destinations.items():
            self.assertIn(destination, declared_destinations[node_name])

        for node_name in _UNDERDECLARED_RUNTIME_NODES:
            self.assertNotIn("environment", nodes[node_name]["runtime"])

    def test_internal_services_have_no_host_publication_contract(self) -> None:
        for node_name, node in _load_sdl()["nodes"].items():
            with self.subTest(node=node_name):
                runtime = node.get("runtime", {})
                self.assertNotIn("network", runtime)
                for listener in runtime.get("service_listeners", []):
                    self.assertNotIn("published_port_refs", listener)

    def test_cortex_provides_case_driven_offline_enrichment(self) -> None:
        sdl = _load_sdl()
        thehive = sdl["nodes"]["thehive"]
        thehive_app = thehive["runtime"]["platform_applications"][0]
        cortex_binding = next(
            item
            for item in thehive_app["upstream_bindings"]
            if item["role"] == "backend_api"
        )
        self.assertEqual(cortex_binding["target_node_ref"], "cortex")
        self.assertEqual(cortex_binding["target_service_ref"], "cortex-api")
        (connector_declaration,) = thehive_app["connectors"]
        self.assertEqual(connector_declaration["kind"], "analyzer_engine")
        self.assertEqual(
            connector_declaration["credential_classification"], "redacted"
        )

        cortex = sdl["nodes"]["cortex"]
        self.assertEqual(
            cortex["services"],
            [{"name": "cortex-api", "port": 9001, "protocol": "tcp"}],
        )
        cortex_config = sdl["content"]["cortex-app-config"]["text"]
        self.assertIn('job.runners = ["process"]', cortex_config)
        self.assertIn(
            'analyzer.urls = ["/opt/techvault/cortex-analyzers"]', cortex_config
        )
        self.assertNotIn("docker.sock", yaml.safe_dump(cortex))
        cortex_app = cortex["runtime"]["platform_applications"][0]
        self.assertEqual(cortex_app["platform_application_id"], "cortex-enrichment")
        self.assertEqual(cortex_app["authorization_ref"], "cortex-rbac")
        self.assertEqual(
            {item["kind"] for item in cortex_app["capabilities"]},
            {"analysis_execution"},
        )
        analyzers = {
            item["content_object_id"]: item
            for item in cortex_app["content_objects"]
            if item["kind"] == "analyzer"
        }
        self.assertIn("techvault-scenario-context", analyzers)
        self.assertEqual(
            analyzers["techvault-scenario-context"]["attributes"]["data_types"],
            ["ip"],
        )

        authorization = cortex["runtime"]["app_authorizations"][0]
        self.assertEqual(authorization["app_authorization_id"], "cortex-rbac")
        principals = {
            item["principal_id"]: item for item in authorization["principals"]
        }
        connector = principals["thehive-cortex-connector"]
        self.assertEqual(connector["kind"], "service_account")
        self.assertEqual(connector["credential_classification"], "redacted")
        self.assertEqual(connector["backend_roles"], ["read", "analyze"])
        self.assertNotIn("orgadmin", connector["backend_roles"])
        self.assertEqual(set(principals), {"thehive-cortex-connector"})
        self.assertNotIn("cortex-initializer", sdl["nodes"])
        self.assertNotIn("cortex-initializer", sdl["infrastructure"])

        integrations = [
            relationship["service_integration"]
            for relationship in sdl["relationships"].values()
            if relationship.get("service_integration", {}).get("engine_ref")
            == "cortex-enrichment"
        ]
        self.assertEqual(len(integrations), 1)
        integration = integrations[0]
        self.assertEqual(integration["consumer_ref"], "thehive-case-management")
        self.assertEqual(integration["integration_kind"], "enrichment")
        self.assertEqual(integration["auth_principal_ref"], "thehive-cortex-connector")
        self.assertTrue(integration["enabled"])

        for content_id in (
            "cortex-analyzer-definition",
            "cortex-analyzer-executable",
        ):
            content = sdl["content"][content_id]
            requirement = content["source"]["artifact_requirement"]
            self.assertEqual(requirement["explicitness"], "exact")
            self.assertEqual(
                resolve_pack_artifact(_PACK, content["source"]["name"]).identity.digest,
                requirement["exact_artifact"]["digest"],
            )

        proposition = sdl["propositions"]["cortex-enrichment-ready"]
        self.assertEqual(proposition["basis"], "observed_state")
        self.assertIn("cortex-enrichment-readback", proposition["evidence_requirements"])
        evidence = sdl["evidence_requirements"]["cortex-enrichment-readback"]
        self.assertIn("nodes.cortex", evidence["scope_refs"])
        self.assertIn("nodes.thehive", evidence["scope_refs"])

    def test_cortex_owns_its_native_job_index_schema(self) -> None:
        sdl = _load_sdl()

        self.assertNotIn("cortex-index-init", sdl["nodes"])
        self.assertNotIn("cortex-index-init", sdl["infrastructure"])
        self.assertNotIn("cortex-index-init-script", sdl["content"])
        self.assertNotIn("cortex-job-index-schema", sdl["content"])

        (datastore,) = sdl["nodes"]["thehive-es"]["runtime"]["datastore_services"]
        self.assertEqual(datastore["engine"], "elasticsearch")
        self.assertEqual(datastore["version"], "7.17.28")

        self.assertFalse(
            (_PACK / "assets" / "content" / "cortex-initializer.py").exists()
        )

    def test_cortex_pack_validator_rejects_contract_mutations(self) -> None:
        original = _load_sdl()
        self.assertEqual(
            _PACK_VALIDATOR.validate_cortex_contract(_PACK, original), []
        )

        def principals(candidate):
            return {
                item["principal_id"]: item
                for item in candidate["nodes"]["cortex"]["runtime"]
                ["app_authorizations"][0]["principals"]
            }

        def mutate(candidate, code):
            cortex_runtime = candidate["nodes"]["cortex"]["runtime"]
            if code == "connector-key-mismatch":
                candidate["nodes"]["thehive"]["runtime"]["platform_applications"][
                    0
                ]["connectors"][0]["credential_classification"] = "plain"
            elif code == "connector-binding-invalid":
                candidate["nodes"]["thehive"]["runtime"]["platform_applications"][0]["upstream_bindings"] = []
            elif code == "application-missing":
                cortex_runtime["platform_applications"][0]["platform_application_id"] = "other"
            elif code == "capability-missing":
                cortex_runtime["platform_applications"][0]["capabilities"] = []
            elif code == "connector-principal-invalid":
                principals(candidate)["thehive-cortex-connector"]["backend_roles"].append("orgadmin")
            elif code == "unexpected-principal":
                cortex_runtime["app_authorizations"][0]["principals"].append(
                    {"principal_id": "initializer", "kind": "service_account"}
                )
            elif code == "native-schema-leaked":
                candidate["content"]["cortex-job-index-schema"] = {}
            elif code == "content-placement-mismatch":
                candidate["content"]["cortex-analyzer-definition"]["path"] = "/tmp/analyzer.json"
            elif code == "content-identity-mismatch":
                candidate["content"]["cortex-analyzer-definition"]["source"][
                    "artifact_requirement"
                ]["exact_artifact"]["digest"] = "sha256:" + "0" * 64

        codes = (
            "connector-key-mismatch",
            "connector-binding-invalid",
            "application-missing",
            "capability-missing",
            "connector-principal-invalid",
            "unexpected-principal",
            "native-schema-leaked",
            "content-placement-mismatch",
            "content-identity-mismatch",
        )
        for code in codes:
            with self.subTest(code=code):
                candidate = copy.deepcopy(original)
                mutate(candidate, code)
                errors = _PACK_VALIDATOR.validate_cortex_contract(_PACK, candidate)
                self.assertTrue(
                    any(f"cortex.{code}" in error for error in errors), errors
                )

        real_resolve = _PACK_VALIDATOR.resolve_pack_artifact

        def invalid_definition(pack_root, artifact_id):
            artifact = real_resolve(pack_root, artifact_id)
            if artifact_id == "techvault-cortex-analyzer-definition":
                return types.SimpleNamespace(identity=artifact.identity, data=b"{}")
            return artifact

        with mock.patch.object(
            _PACK_VALIDATOR, "resolve_pack_artifact", side_effect=invalid_definition
        ):
            errors = _PACK_VALIDATOR.validate_cortex_contract(_PACK, original)
        self.assertTrue(
            any("cortex.analyzer-definition-invalid" in error for error in errors),
            errors,
        )

    def test_content_sources_are_exact_resolvable_pack_artifacts(self) -> None:
        profile = json.loads(_PROFILE.read_text(encoding="utf-8"))
        profile_digest = _canonical_json_digest(profile)
        content = _load_sdl()["content"]

        for content_id in sorted(_PACK_ARTIFACT_CONTENT_IDS):
            with self.subTest(content_id=content_id):
                source = content[content_id]["source"]
                artifact_id = source["name"]
                self.assertNotIn("/", artifact_id)
                self.assertNotIn("\\", artifact_id)
                requirement = source["artifact_requirement"]
                self.assertEqual(requirement["explicitness"], "exact")
                exact = requirement["exact_artifact"]
                self.assertEqual(exact["artifact_id"], artifact_id)
                self.assertEqual(exact["version"], "0.1.0")

                route = requirement["permitted_routes"]
                self.assertEqual(len(route), 1)
                self.assertEqual(route[0]["acquisition"], "copy")
                self.assertEqual(route[0]["timing"], "pack-ingestion")
                self.assertEqual(route[0]["mechanism"]["mechanism"], "exact-artifact")
                self.assertEqual(route[0]["mechanism"]["profile"], profile["profile"])
                self.assertEqual(route[0]["mechanism"]["version"], profile["version"])
                self.assertEqual(route[0]["mechanism"]["digest"], profile_digest)

                resolved = resolve_pack_artifact(_PACK, artifact_id)
                self.assertEqual(resolved.identity.artifact_id, artifact_id)
                self.assertEqual(resolved.identity.version, exact["version"])
                self.assertEqual(resolved.identity.media_type, exact["media_type"])
                self.assertEqual(resolved.identity.digest, exact["digest"])

    def test_directory_artifacts_are_safe_complete_tar_carriers(self) -> None:
        required_members = {
            "techvault-misp-sync-src": "aptl/services/misp_suricata_sync/main.py",
            "techvault-webapp-app": "app.py",
            "techvault-fileshare-shares": "engineering/deployments/deploy.sh",
            "techvault-workstation-dev-user-home": ".bash_history",
            "techvault-wazuh-integrations": "custom-shuffle",
        }
        for artifact_id, required_member in required_members.items():
            with self.subTest(artifact_id=artifact_id):
                data = resolve_pack_artifact(_PACK, artifact_id).data
                with tarfile.open(fileobj=io.BytesIO(data), mode="r:") as archive:
                    members = archive.getmembers()
                self.assertIn(required_member, {member.name for member in members})
                self.assertTrue(members)
                for member in members:
                    path = pathlib.PurePosixPath(member.name)
                    self.assertFalse(path.is_absolute())
                    self.assertNotIn("..", path.parts)
                    self.assertFalse(member.issym() or member.islnk())
                    self.assertTrue(member.isfile() or member.isdir())

        integrations = resolve_pack_artifact(
            _PACK, "techvault-wazuh-integrations"
        ).data
        with tarfile.open(fileobj=io.BytesIO(integrations), mode="r:") as archive:
            integration = archive.getmember("custom-shuffle")
            self.assertEqual(integration.mode & 0o111, 0o111)

        workstation = resolve_pack_artifact(
            _PACK, "techvault-workstation-dev-user-home"
        ).data
        with tarfile.open(fileobj=io.BytesIO(workstation), mode="r:") as archive:
            env = archive.extractfile("projects/techvault-portal/.env")
            self.assertIsNotNone(env)
            assert env is not None
            self.assertEqual(
                env.read(),
                b"DB_PASSWORD=techvault_db_pass\nJWT_SECRET=techvault-jwt-weak\n",
            )

    def test_generated_keys_and_certificates_enforce_output_boundaries(self) -> None:
        generated = _load_sdl()["generated_artifacts"]
        self.assertEqual(len(generated), 6)

        ssh = generated["techvault-ssh-keys"]
        self.assertEqual(ssh["generator"], "ssh_key_bundle")
        private = {
            output["name"]
            for output in ssh["outputs"]
            if output.get("disposition") == "producer_private"
        }
        self.assertEqual(private, {"operator-private-key"})
        for consumer in ssh["consumers"]:
            self.assertTrue(consumer["selected_outputs"])
            self.assertTrue(private.isdisjoint(consumer["selected_outputs"]))

        soc = generated["techvault-soc-certificates"]
        self.assertEqual(soc["generator"], "certificate_bundle")
        ca_private = next(
            output for output in soc["outputs"] if output["name"] == "ca-private-key"
        )
        self.assertEqual(ca_private["disposition"], "producer_private")
        for consumer in soc["consumers"]:
            self.assertNotIn("ca-private-key", consumer["selected_outputs"])


# The TechVault domain's in-world roster: username -> (groups, password
# strength, SPN). Only the SPN each account is Kerberoastable through is listed.
_AD_ACCOUNT_ROSTER = {
    "Administrator": ({"Domain Admins"}, "weak", ""),
    "sarah.mitchell": ({"Executives"}, "strong", ""),
    "james.rodriguez": ({"Executives", "IT-Admins"}, "strong", ""),
    "lisa.chang": ({"Executives", "Sales"}, "medium", ""),
    "emily.chen": ({"Engineering", "IT-Admins", "Domain Admins"}, "medium", ""),
    "michael.thompson": ({"Engineering"}, "weak", ""),
    "david.kim": ({"Engineering", "IT-Admins"}, "strong", ""),
    "jessica.williams": ({"Sales", "VPN-Users"}, "weak", ""),
    "robert.martinez": ({"Sales"}, "medium", ""),
    "svc-sql": (set(), "weak", "MSSQLSvc/db.techvault.local:1433"),
    "svc-web": (set(), "weak", "HTTP/webapp.techvault.local"),
    "svc-backup": ({"Domain Admins"}, "medium", ""),
    "contractor.temp": ({"VPN-Users", "Remote-Desktop", "Engineering"}, "weak", ""),
    "former.employee": (set(), "weak", ""),
}


class TechVaultInWorldDeclarationTests(unittest.TestCase):
    """The pack states what exists in the scenario, never how it is built."""

    def test_checked_in_sdl_contains_no_realization_method(self) -> None:
        self.assertEqual(
            _PACK_VALIDATOR.validate_realization_method_contract(_load_sdl()), []
        )

    def test_compiled_verification_leaves_authoritative_source_open(self) -> None:
        sdl = _load_sdl()
        model = compile_scenario_runtime_model(
            parse_sdl_file(_SDL),
            parameters={name: f"test-{name}" for name in sdl["variables"]},
        )
        by_field = {
            requirement.field_path: requirement
            for requirement in model.realization_requirements
        }
        expected_scopes = {
            "nodes.wazuh-manager.os": RealizationVerificationScope.PRESENCE,
            (
                "nodes.misp-suricata-sync.runtime.forwarding_agents"
            ): RealizationVerificationScope.CONFIGURATION,
            (
                "nodes.wazuh-dashboard.runtime.applications"
            ): RealizationVerificationScope.CONFIGURATION,
            (
                "nodes.suricata.runtime.network_sensors"
            ): RealizationVerificationScope.CONFIGURATION,
        }

        for field_path, expected_scope in expected_scopes.items():
            with self.subTest(field_path=field_path):
                requirement = by_field[field_path]
                self.assertEqual(requirement.verification_scope, expected_scope)
                self.assertIsNone(requirement.required_observation_strength)

    def test_unconstrained_source_requires_authoritative_observation(self) -> None:
        model = compile_scenario_runtime_model(
            parse_sdl_file(_SDL),
            parameters={
                name: f"test-{name}" for name in _load_sdl()["variables"]
            },
        )
        requirement = next(
            requirement
            for requirement in model.realization_requirements
            if requirement.field_path
            == "nodes.wazuh-dashboard.runtime.applications"
        )
        for source, admitted in (
            (ObservationStrength.DRIVER_REPORTED, False),
            (ObservationStrength.DAEMON_OBSERVED, True),
            (ObservationStrength.GUEST_OBSERVED, True),
        ):
            declaration = RealizationSupportDeclaration(
                domain=requirement.domain,
                support_mode=RealizationSupportMode.OPEN_REALIZATION,
                supported_constraint_kinds=frozenset(
                    {requirement.requirement_kind}
                ),
                disclosure_kinds=frozenset({"runtime-snapshot-v1"}),
                observation_capabilities={
                    requirement.requirement_kind: RealizationObservationCapability(
                        verification_scope=RealizationVerificationScope.CONFIGURATION,
                        observation_strength=source,
                    )
                },
            )
            with self.subTest(source=source.value):
                self.assertEqual(
                    has_required_observation_support(
                        requirement,
                        [declaration],
                        observation_kind=requirement.requirement_kind,
                    ),
                    admitted,
                )

        self.assertFalse(
            has_required_observation_support(
                requirement,
                [],
                observation_kind=requirement.requirement_kind,
            )
        )

    def test_misp_sync_preserves_authentication_and_ca_trust_as_typed_state(
        self,
    ) -> None:
        sdl = _load_sdl()
        misp_runtime = sdl["nodes"]["misp"]["runtime"]
        (misp_application,) = misp_runtime["platform_applications"]
        self.assertEqual(
            misp_application["authorization_ref"], "misp-api-authorization"
        )
        (authorization,) = misp_runtime["app_authorizations"]
        self.assertEqual(
            authorization["app_authorization_id"], "misp-api-authorization"
        )
        (principal,) = authorization["principals"]
        self.assertEqual(principal["principal_id"], "misp-suricata-sync-api-key")
        self.assertEqual(principal["kind"], "api_key")
        self.assertEqual(principal["credential_classification"], "operator_secret")

        sync_runtime = sdl["nodes"]["misp-suricata-sync"]["runtime"]
        (sync_agent,) = sync_runtime["forwarding_agents"]
        settings = {item["setting_id"]: item for item in sync_agent["settings"]}
        self.assertEqual(
            settings["misp-api-authentication"]["classification"],
            "operator_secret",
        )
        self.assertEqual(
            settings["misp-tls-verification"]["value"], "required"
        )
        self.assertEqual(
            settings["misp-ca-trust-anchor"]["value"],
            "/opt/techvault/soc-certs/lab-ca.pem",
        )

        consumers = {
            consumer["node"]: consumer
            for consumer in sdl["generated_artifacts"][
                "techvault-soc-certificates"
            ]["consumers"]
        }
        self.assertEqual(
            consumers["misp-suricata-sync"]["selected_outputs"],
            ["ca-certificate"],
        )
        inventory = {
            item["path"]: item for item in sync_runtime["filesystem_inventory"]
        }
        self.assertEqual(
            inventory["/opt/techvault/soc-certs/lab-ca.pem"]["mode"], "0644"
        )

    def test_workstation_loot_permissions_are_backend_neutral_state(self) -> None:
        runtime = _load_sdl()["nodes"]["workstation"]["runtime"]
        inventory = {item["path"]: item for item in runtime["filesystem_inventory"]}
        expected = {
            "/home/dev-user/.bash_history": "secret_fixture",
            "/home/dev-user/.config/credentials.json": "secret_fixture",
            "/home/dev-user/.pgpass": "secret_fixture",
            "/home/dev-user/.ssh/id_rsa": "operator_secret",
            "/home/dev-user/projects/techvault-portal/.env": "secret_fixture",
        }
        for path, sensitivity in expected.items():
            with self.subTest(path=path):
                entry = inventory[path]
                self.assertEqual(entry["entry_type"], "file")
                self.assertEqual(entry["owner_user"], "dev-user")
                self.assertEqual(entry["owner_group"], "dev-user")
                self.assertEqual(entry["mode"], "0600")
                self.assertEqual(entry["sensitivity"], sensitivity)

    def test_image_identities_are_replaced_by_product_versions(self) -> None:
        sdl = _load_sdl()
        self.assertTrue(all("source" not in node for node in sdl["nodes"].values()))
        self.assertNotIn("features", sdl)

        expected = {
            "wazuh-manager": ("security_monitoring_managers", "4.12.0"),
            "wazuh-indexer": ("datastore_services", "4.12.0"),
            "wazuh-dashboard": ("platform_applications", "4.12.0"),
            "suricata": ("network_detection_engines", "7.0"),
            "misp": ("platform_applications", "2.5.44"),
            "misp-db": ("database_services", "10.11"),
            "misp-redis": ("datastore_services", "7"),
            "thehive": ("platform_applications", "5.4"),
            "thehive-cassandra": ("datastore_services", "4.1"),
            "thehive-es": ("datastore_services", "7.17.28"),
            "cortex": ("platform_applications", "3.1.8"),
            "shuffle-backend": ("platform_applications", "unversioned"),
            "shuffle-opensearch": ("datastore_services", "2.14.0"),
        }
        for node_id, (family, version) in expected.items():
            with self.subTest(node=node_id):
                self.assertEqual(
                    sdl["nodes"][node_id]["runtime"][family][0]["version"],
                    version,
                )

        software = {
            component["component_id"]: component
            for node_id in ("shuffle-frontend", "shuffle-orborus")
            for component in sdl["nodes"][node_id]["runtime"][
                "software_components"
            ]
        }
        self.assertEqual(software["shuffle-frontend"]["version"], "unversioned")
        self.assertEqual(software["shuffle-orborus"]["version"], "unversioned")

    def test_wazuh_agents_are_declared_on_every_watched_host(self) -> None:
        sdl = _load_sdl()
        expected_sources = {
            "ad": {
                "/var/log/samba/log.samba",
                "/var/log/samba/log.smbd",
                "/var/log/samba/log.winbindd",
            },
            "db": {"/var/log/postgresql/postgresql-15-main.log"},
            "suricata": {"/var/log/suricata/eve.json"},
            "webapp": {"/var/log/gunicorn/access.log"},
            "dns": {"/var/log/named/query.log", "/var/log/named/default.log"},
            "fileshare": {
                "/var/log/samba/log.samba",
                "/var/log/samba/log.smbd",
            },
            "victim": {"/var/log/secure", "/var/log/messages"},
        }
        for node_id, paths in expected_sources.items():
            with self.subTest(node=node_id):
                agents = sdl["nodes"][node_id]["runtime"]["forwarding_agents"]
                declared = {
                    source["location"]
                    for agent in agents
                    if agent["implementation"] == "wazuh_agent"
                    for source in agent["sources"]
                    if source["kind"] == "tailed_path"
                }
                self.assertEqual(declared, paths)
                self.assertTrue(
                    all(
                        target["target_node_ref"] == "wazuh-manager"
                        for agent in agents
                        if agent["implementation"] == "wazuh_agent"
                        for target in agent["ship_targets"]
                    )
                )

        manager_agents = {
            agent["node_ref"]
            for agent in sdl["nodes"]["wazuh-manager"]["runtime"][
                "security_monitoring_managers"
            ][0]["agents"]
        }
        self.assertEqual(manager_agents, set(expected_sources))

    def test_victim_has_one_typed_log_handoff(self) -> None:
        sdl = _load_sdl()
        runtime = sdl["nodes"]["victim"]["runtime"]
        self.assertNotIn("victim-rsyslog-forward", sdl["content"])
        self.assertIn(
            ("rsyslog", "rsyslog.service", "enabled", "active"),
            {
                (
                    unit["unit_id"],
                    unit["unit_name"],
                    unit["enabled_state"],
                    unit["active_state"],
                )
                for unit in runtime["service_manager_units"]
            },
        )
        (agent,) = runtime["forwarding_agents"]
        self.assertEqual(agent["implementation"], "wazuh_agent")
        self.assertEqual(
            {source["location"] for source in agent["sources"]},
            {"/var/log/secure", "/var/log/messages"},
        )
        self.assertEqual(
            {target["target_node_ref"] for target in agent["ship_targets"]},
            {"wazuh-manager"},
        )

    def test_webapp_has_one_log_handoff_and_no_launch_recipe(self) -> None:
        sdl = _load_sdl()
        runtime = sdl["nodes"]["webapp"]["runtime"]
        self.assertNotIn("service_manager_units", runtime)
        self.assertNotIn("rsyslog", {item["name"] for item in runtime["packages"]})
        for content_id in (
            "webapp-rsyslog-forward",
            "webapp-rsyslog-unit",
            "webapp-service-unit",
        ):
            with self.subTest(content=content_id):
                self.assertNotIn(content_id, sdl["content"])
        self.assertEqual(
            [
                source["location"]
                for agent in runtime["forwarding_agents"]
                for source in agent["sources"]
                if source["location"] == "/var/log/gunicorn/access.log"
            ],
            ["/var/log/gunicorn/access.log"],
        )

    def test_participant_mcp_sources_are_split_and_byte_bound(self) -> None:
        sdl = _load_sdl()
        declarations = {
            "techvault-red-mcp-sources": (
                "mcp-red-sources",
                "kali",
                {"aptl-mcp-common", "mcp-red"},
            ),
            "techvault-blue-mcp-sources": (
                "mcp-blue-sources",
                "soc-workstation",
                {
                    "aptl-mcp-common",
                    "mcp-casemgmt",
                    "mcp-indexer",
                    "mcp-network",
                    "mcp-reverse",
                    "mcp-soar",
                    "mcp-threatintel",
                    "mcp-wazuh",
                },
            ),
        }
        for artifact_id, (content_id, target, roots) in declarations.items():
            with self.subTest(artifact=artifact_id):
                content = sdl["content"][content_id]
                self.assertEqual(content["target"], target)
                self.assertEqual(content["destination"], "/opt/techvault/mcp")
                self.assertEqual(content["source"]["name"], artifact_id)
                data = resolve_pack_artifact(_PACK, artifact_id).data
                with tarfile.open(fileobj=io.BytesIO(data), mode="r:") as archive:
                    members = archive.getmembers()
                    names = {member.name for member in members}
                    source_metadata = json.loads(
                        archive.extractfile("SOURCE.json").read()
                    )
                    telemetry = archive.extractfile(
                        "aptl-mcp-common/src/telemetry.ts"
                    ).read().decode("utf-8")
                self.assertIn("LICENSE", names)
                self.assertIn("SOURCE.json", names)
                self.assertEqual(
                    {pathlib.PurePosixPath(name).parts[0] for name in names}
                    - {"LICENSE", "SOURCE.json"},
                    roots,
                )
                self.assertFalse(
                    any(
                        part in {"build", "node_modules", "tests"}
                        or part == "docker-lab-config.json"
                        for name in names
                        for part in pathlib.PurePosixPath(name).parts
                    )
                )
                self.assertTrue(
                    all(
                        member.isfile() or member.isdir()
                        for member in members
                    )
                )
                self.assertEqual(
                    source_metadata["revision"],
                    "7c673a19f9fb6a3eb1d17305104196b600bd59cc",
                )
                self.assertEqual(
                    source_metadata["adaptations"][0]["path"],
                    "aptl-mcp-common/src/telemetry.ts",
                )
                self.assertIn("'aptl.tool.payload.recorded': false", telemetry)
                for content_attribute in (
                    "aptl.tool.arguments",
                    "aptl.tool.response",
                    "exception.message",
                    "exception.stacktrace",
                ):
                    self.assertNotIn(content_attribute, telemetry)
                self.assertEqual([member.name for member in members], sorted(names))
                for member in members:
                    self.assertEqual((member.uid, member.gid, member.mtime), (0, 0, 0))
                    self.assertEqual(member.mode, 0o644)

    def test_mcp_builder_pins_commit_and_disables_git_replacements(self) -> None:
        revision = mcp_builder.SOURCE_REVISION
        completed = mcp_builder.subprocess.CompletedProcess(
            args=[], returncode=0, stdout=f"{revision}\n".encode(), stderr=b""
        )
        hostile_environment = {
            "GIT_DIR": "/tmp/untrusted-git-dir",
            "GIT_OBJECT_DIRECTORY": "/tmp/untrusted-objects",
        }
        with mock.patch.dict(
            mcp_builder.os.environ, hostile_environment, clear=False
        ), mock.patch.object(
            mcp_builder.subprocess, "run", return_value=completed
        ) as run:
            mcp_builder._validate_revision(pathlib.Path("/tmp/source"), revision)

        command = run.call_args.args[0]
        environment = run.call_args.kwargs["env"]
        self.assertIn("--no-replace-objects", command)
        self.assertEqual(environment["GIT_NO_REPLACE_OBJECTS"], "1")
        self.assertEqual(environment["GIT_CONFIG_GLOBAL"], os.devnull)
        self.assertNotIn("GIT_DIR", environment)
        self.assertNotIn("GIT_OBJECT_DIRECTORY", environment)

        with self.assertRaisesRegex(ValueError, "reviewed immutable commit"):
            mcp_builder._validate_revision(
                pathlib.Path("/tmp/source"), "0" * 40
            )

    def test_mcp_builder_builds_archive_end_to_end_from_stubbed_git(self) -> None:
        revision = mcp_builder.SOURCE_REVISION
        members = {
            "mcp/mcp-red/package.json": b'{"name":"mcp-red"}\n',
            "mcp/mcp-red/src/index.ts": b"export const ready = true;\n",
        }

        def read_git(_repo: pathlib.Path, *args: str) -> bytes:
            if args[0] == "rev-parse":
                return f"{revision}\n".encode()
            if args == ("show", f"{revision}:LICENSE"):
                return b"MIT License\n"
            if args[0] == "ls-tree":
                prefix = args[-1]
                return "".join(
                    f"{name}\n" for name in members if name.startswith(prefix)
                ).encode()
            if args[0] == "show":
                return members[args[1].split(":", 1)[1]]
            raise AssertionError(f"unexpected git request: {args}")

        with tempfile.TemporaryDirectory() as directory:
            repository_root = pathlib.Path(directory) / "repo"
            asset_root = (
                repository_root / "packs" / "techvault" / "assets" / "content"
            )
            asset_root.mkdir(parents=True)
            destination = asset_root / "mcp-red-sources.tar"
            with mock.patch.object(
                mcp_builder, "_REPOSITORY_ROOT", repository_root
            ), mock.patch.object(
                mcp_builder, "_ASSET_ROOT", asset_root
            ), mock.patch.object(
                mcp_builder, "_git", side_effect=read_git
            ):
                mcp_builder.build_archive(
                    pathlib.Path(directory) / "source",
                    revision,
                    ("mcp-red",),
                    destination,
                )

            with tarfile.open(destination, mode="r:") as archive:
                self.assertEqual(
                    archive.getnames(),
                    [
                        "LICENSE",
                        "SOURCE.json",
                        "mcp-red/package.json",
                        "mcp-red/src/index.ts",
                    ],
                )
                metadata = json.load(archive.extractfile("SOURCE.json"))
                self.assertEqual(metadata["revision"], revision)
                self.assertEqual(metadata["packages"], ["mcp-red"])

    def test_mcp_builder_rejects_unsafe_destination_paths(self) -> None:
        revision = mcp_builder.SOURCE_REVISION

        def resolve_revision(_repo: pathlib.Path, *args: str) -> bytes:
            if args[0] == "rev-parse":
                return f"{revision}\n".encode()
            raise AssertionError(f"unexpected git request: {args}")

        with tempfile.TemporaryDirectory() as directory:
            temporary = pathlib.Path(directory)
            repository_root = temporary / "repo"
            asset_root = (
                repository_root / "packs" / "techvault" / "assets" / "content"
            )
            asset_root.mkdir(parents=True)
            patches = (
                mock.patch.object(mcp_builder, "_REPOSITORY_ROOT", repository_root),
                mock.patch.object(mcp_builder, "_ASSET_ROOT", asset_root),
                mock.patch.object(mcp_builder, "_git", side_effect=resolve_revision),
            )
            with patches[0], patches[1], patches[2]:
                with self.subTest(destination="outside asset root"), self.assertRaisesRegex(
                    ValueError, "outside the TechVault asset root"
                ):
                    mcp_builder.build_archive(
                        temporary / "source",
                        revision,
                        ("mcp-red",),
                        temporary / "mcp-red-sources.tar",
                    )

                symlink_destination = asset_root / "mcp-red-sources.tar"
                symlink_destination.symlink_to(temporary / "outside.tar")
                with self.subTest(destination="symlink"), self.assertRaisesRegex(
                    ValueError, "must not be a symbolic link"
                ):
                    mcp_builder.build_archive(
                        temporary / "source",
                        revision,
                        ("mcp-red",),
                        symlink_destination,
                    )

            linked_asset_root = repository_root / "linked-content"
            real_asset_root = temporary / "real-content"
            real_asset_root.mkdir()
            linked_asset_root.symlink_to(real_asset_root, target_is_directory=True)
            with mock.patch.object(
                mcp_builder, "_REPOSITORY_ROOT", repository_root
            ), mock.patch.object(
                mcp_builder, "_ASSET_ROOT", linked_asset_root
            ), mock.patch.object(
                mcp_builder, "_git", side_effect=resolve_revision
            ), self.subTest(destination="symlinked parent"), self.assertRaisesRegex(
                ValueError, "must not contain symbolic links"
            ):
                mcp_builder.build_archive(
                    temporary / "source",
                    revision,
                    ("mcp-red",),
                    linked_asset_root / "mcp-red-sources.tar",
                )

    def test_mcp_builder_rejects_incomplete_packages(self) -> None:
        revision = mcp_builder.SOURCE_REVISION
        incomplete_trees = {
            "missing package manifest": "mcp/mcp-red/src/index.ts\n",
            "missing source": "mcp/mcp-red/package.json\n",
        }

        with tempfile.TemporaryDirectory() as directory:
            repository_root = pathlib.Path(directory) / "repo"
            asset_root = (
                repository_root / "packs" / "techvault" / "assets" / "content"
            )
            asset_root.mkdir(parents=True)
            destination = asset_root / "mcp-red-sources.tar"
            for condition, tree in incomplete_trees.items():
                def read_git(_repo: pathlib.Path, *args: str) -> bytes:
                    if args[0] == "rev-parse":
                        return f"{revision}\n".encode()
                    if args == ("show", f"{revision}:LICENSE"):
                        return b"MIT License\n"
                    if args[0] == "ls-tree":
                        return tree.encode()
                    raise AssertionError(f"unexpected git request: {args}")

                with self.subTest(condition=condition), mock.patch.object(
                    mcp_builder, "_REPOSITORY_ROOT", repository_root
                ), mock.patch.object(
                    mcp_builder, "_ASSET_ROOT", asset_root
                ), mock.patch.object(
                    mcp_builder, "_git", side_effect=read_git
                ), self.assertRaisesRegex(RuntimeError, "package is incomplete"):
                    mcp_builder.build_archive(
                        pathlib.Path(directory) / "source",
                        revision,
                        ("mcp-red",),
                        destination,
                    )

    def test_mcp_builder_rejects_telemetry_adaptation_drift(self) -> None:
        with self.subTest(condition="source hash"), self.assertRaisesRegex(
            RuntimeError, "source changed unexpectedly"
        ):
            mcp_builder._adapt_source(
                mcp_builder.COMMON_PACKAGE,
                mcp_builder._TELEMETRY_PATH,
                b"changed telemetry source\n",
            )

        duplicate_replacement = (
            b"import { redact } from './redaction.js';\n\n"
            b"import { redact } from './redaction.js';\n\n"
        )
        expected_hash = hashlib.sha256(duplicate_replacement).hexdigest()
        with mock.patch.object(
            mcp_builder, "_TELEMETRY_SOURCE_SHA256", expected_hash
        ), self.subTest(condition="replacement count"), self.assertRaisesRegex(
            RuntimeError, "adaptation no longer applies"
        ):
            mcp_builder._adapt_source(
                mcp_builder.COMMON_PACKAGE,
                mcp_builder._TELEMETRY_PATH,
                duplicate_replacement,
            )

    def test_red_and_blue_agents_have_separate_workstations(self) -> None:
        scenario = parse_sdl_file(_SDL)
        self.assertEqual(scenario.entities["red-team"].role.value, "red")
        self.assertEqual(scenario.entities["blue-team"].role.value, "blue")
        expected = {
            "red-team-operator": ("red-team", "kali"),
            "blue-team-operator": ("blue-team", "soc-workstation"),
        }
        for agent_id, (entity_id, target) in expected.items():
            with self.subTest(agent=agent_id):
                agent = scenario.agents[agent_id]
                self.assertEqual(agent.entity, entity_id)
                self.assertEqual(
                    {(item.target_ref, item.channel.value) for item in agent.interactive_access.values()},
                    {(target, "ssh")},
                )

        for node_id, packages in {
            "kali": {"aptl-mcp-common", "aptl-kali-mcp-server"},
            "soc-workstation": {
                "aptl-mcp-common",
                "aptl-casemgmt-mcp-server",
                "aptl-indexer-mcp-server",
                "aptl-network-mcp-server",
                "aptl-reverse-mcp-server",
                "aptl-soar-mcp-server",
                "aptl-threatintel-mcp-server",
                "aptl-wazuh-mcp-server",
            },
        }.items():
            with self.subTest(node=node_id):
                components = scenario.nodes[node_id].runtime.software_components
                self.assertIn(
                    "nodejs",
                    {component.component_id for component in components},
                )
                self.assertEqual(
                    {
                        component.name
                        for component in components
                        if component.component_id != "nodejs"
                    },
                    packages,
                )

    def test_pack_validator_rejects_every_realization_method_family(self) -> None:
        sdl = _load_sdl()
        mutations = {
            "/realization/constraints/0": lambda candidate: candidate[
                "realization"
            ].update(
                constraints=[
                    {
                        "field_pointer": "/nodes/kali",
                        "concern": "compute-substrate",
                        "posture": "exact",
                        "domain": {
                            "kind": "exact",
                            "value": "operating-system-container",
                        },
                    }
                ]
            ),
            "/nodes/kali/source": lambda candidate: candidate["nodes"][
                "kali"
            ].update(source={"name": "backend-image", "version": "latest"}),
            "/features/example/source": lambda candidate: candidate.setdefault(
                "features", {}
            ).update(
                example={
                    "type": "service",
                    "source": {"name": "backend-feature", "version": "local"},
                }
            ),
            "/nodes/kali/runtime/environment": lambda candidate: candidate[
                "nodes"
            ]["kali"]["runtime"].update(
                environment=[{"name": "DELIVERY_SETTING", "value": "value"}]
            ),
            "/nodes/kali/runtime/network/published_ports": lambda candidate: candidate[
                "nodes"
            ]["kali"]["runtime"].update(
                network={
                    "published_ports": [
                        {
                            "container_port": 22,
                            "host_port": 2022,
                            "protocol": "tcp",
                        }
                    ]
                }
            ),
            "/nodes/kali/runtime/service_listeners/0/published_port_refs": lambda candidate: candidate[
                "nodes"
            ]["kali"]["runtime"].update(
                service_listeners=[
                    {
                        "listener_id": "ssh",
                        "service": "ssh",
                        "published_port_refs": [{"host_port": 2022}],
                    }
                ]
            ),
            "/nodes/kali/runtime/container": lambda candidate: candidate["nodes"][
                "kali"
            ]["runtime"].update(container={"entrypoint": ["/bin/sh"]}),
            "/nodes/kali/runtime/linux_capabilities": lambda candidate: candidate[
                "nodes"
            ]["kali"]["runtime"].update(
                linux_capabilities={"add": ["CAP_NET_ADMIN"]}
            ),
            "/nodes/kali/runtime/mounts": lambda candidate: candidate["nodes"][
                "kali"
            ]["runtime"].update(
                mounts=[
                    {
                        "target": "/work",
                        "source": "backend-volume",
                        "source_kind": "volume",
                    }
                ]
            ),
            "/nodes/kali/runtime/operational_policy": lambda candidate: candidate[
                "nodes"
            ]["kali"]["runtime"].update(
                operational_policy={"restart": "always"}
            ),
            "/nodes/kali/runtime/orchestration_authorities": lambda candidate: candidate[
                "nodes"
            ]["kali"]["runtime"].update(
                orchestration_authorities=[
                    {
                        "orchestration_authority_id": "backend-engine",
                        "engine": "docker",
                        "privilege_class": "host_root_equivalent",
                    }
                ]
            ),
            "/nodes/kali/runtime/local_control_interfaces": lambda candidate: candidate[
                "nodes"
            ]["kali"]["runtime"].update(
                local_control_interfaces=[
                    {
                        "control_interface_id": "backend-socket",
                        "path": "/var/run/docker.sock",
                        "kind": "unix_socket",
                        "access": "read_write",
                    }
                ]
            ),
            "/nodes/suricata/runtime/network_sensors/0/capture_mode": lambda candidate: candidate[
                "nodes"
            ]["suricata"]["runtime"]["network_sensors"][0].update(
                capture_mode="af_packet"
            ),
            "/content/renamed-web-launch": lambda candidate: (
                candidate["nodes"]["webapp"]["runtime"].update(
                    service_manager_units=[
                        {
                            "unit_id": "renamed-web-launch",
                            "unit_name": "renamed-web.service",
                            "enabled_state": "enabled",
                            "active_state": "active",
                        }
                    ]
                ),
                candidate["content"].update(
                    {
                        "renamed-web-launch": {
                            "type": "file",
                            "target": "webapp",
                            "path": "/etc/systemd/system/renamed-web.service",
                            "text": "[Service]\nExecStart=/opt/web/start\n",
                        }
                    }
                ),
            ),
            "/content/renamed-web-drop-in": lambda candidate: candidate[
                "content"
            ].update(
                {
                    "renamed-web-drop-in": {
                        "type": "file",
                        "target": "webapp",
                        "path": (
                            "/etc/systemd/system/renamed-web.service.d/"
                            "override.conf"
                        ),
                        "text": "[Service]\nExecStart=/opt/web/start\n",
                    }
                }
            ),
            "/content/renamed-unit-directory": lambda candidate: candidate[
                "content"
            ].update(
                {
                    "renamed-unit-directory": {
                        "type": "directory",
                        "target": "webapp",
                        "destination": "/etc/systemd/system/generated-units",
                        "source": {
                            "name": "unit-directory",
                            "version": "1",
                        },
                    }
                }
            ),
        }
        for pointer, mutate in mutations.items():
            with self.subTest(pointer=pointer):
                candidate = copy.deepcopy(sdl)
                # Start from the intended clean policy surface so each mutation
                # proves one diagnostic rather than inheriting the current SDL.
                candidate["realization"] = {"default": "open"}
                for node in candidate["nodes"].values():
                    node.pop("source", None)
                    runtime = node.get("runtime") or {}
                    for field in (
                        "environment",
                        "network",
                        "container",
                        "linux_capabilities",
                        "mounts",
                        "operational_policy",
                        "orchestration_authorities",
                        "local_control_interfaces",
                    ):
                        runtime.pop(field, None)
                    for listener in runtime.get("service_listeners", []):
                        listener.pop("published_port_refs", None)
                    for sensor in runtime.get("network_sensors", []):
                        sensor.pop("capture_mode", None)
                        sensor.pop("capture_interfaces", None)
                    runtime["service_manager_units"] = [
                        unit
                        for unit in runtime.get("service_manager_units", [])
                        if not unit.get("unit_id", "").startswith("aptl-")
                        and not unit.get("unit_id", "").endswith("-bootstrap")
                    ]
                candidate["features"] = {}
                mutate(candidate)
                errors = _PACK_VALIDATOR.validate_realization_method_contract(
                    candidate
                )
                self.assertTrue(
                    any(error.endswith(pointer) for error in errors), errors
                )

    def test_realization_validator_does_not_classify_historical_identifiers(
        self,
    ) -> None:
        candidate = copy.deepcopy(_load_sdl())
        candidate["nodes"]["cortex-initializer"] = {
            "type": "compute",
            "os": "linux",
            "services": [],
        }
        candidate["content"]["db-bootstrap-unit"] = {
            "type": "file",
            "target": "db",
            "path": "/opt/techvault/bootstrap-notes.txt",
            "text": "Scenario documentation, not a launch unit.\n",
        }
        self.assertEqual(
            _PACK_VALIDATOR.validate_realization_method_contract(candidate), []
        )

    def test_pack_validator_rejects_build_recipes(self) -> None:
        sdl = _load_sdl()
        self.assertEqual(
            _PACK_VALIDATOR.validate_realization_method_contract(sdl), []
        )

        build_route = {
            "mechanism": {
                "mechanism": "materialization-specification",
                "profile": "some-build",
                "version": "1",
                "digest": "sha256:" + "0" * 64,
            },
            "acquisition": "none",
            "timing": "backend-preparation",
        }
        mutations = {
            "/nodes/kali/source/artifact_requirement": lambda candidate: candidate[
                "nodes"
            ]["kali"].update(
                source={
                    "name": "kali",
                    "version": "local",
                    "artifact_requirement": {
                        "requirement_id": "kali-image",
                        "explicitness": "constrained",
                        "materialization_specifications": [
                            {
                                "specification_id": "kali",
                                "profile": build_route["mechanism"],
                                "digest": "sha256:" + "1" * 64,
                            }
                        ],
                        "permitted_routes": [build_route],
                    },
                }
            ),
            "/content/webapp-app-code/source/artifact_requirement": lambda candidate: candidate[
                "content"
            ]["webapp-app-code"]["source"]["artifact_requirement"][
                "permitted_routes"
            ].append(build_route),
        }
        for pointer, mutate in mutations.items():
            with self.subTest(pointer=pointer):
                candidate = copy.deepcopy(sdl)
                mutate(candidate)
                self.assertEqual(
                    _PACK_VALIDATOR.validate_realization_method_contract(candidate),
                    [f"realization.build-recipe: {pointer}"],
                )

    def test_ad_declares_its_domain_without_a_build_source(self) -> None:
        sdl = _load_sdl()
        ad = sdl["nodes"]["ad"]

        self.assertNotIn("source", ad)
        environment = {item["name"] for item in ad["runtime"].get("environment", [])}
        for name in (
            "SAMBA_DOMAIN",
            "SAMBA_REALM",
            "SAMBA_ADMIN_PASSWORD",
            "DNS_FORWARDER",
            "SIEM_IP",
            "WAZUH_MANAGER",
            "AGENT_NAME",
            "LOG_PATHS",
            "LOG_FORMAT",
        ):
            with self.subTest(environment=name):
                self.assertNotIn(name, environment)

        scenario = parse_sdl_file(_SDL)
        domain_accounts = {
            account.username: account
            for account in scenario.accounts.values()
            if account.node == "ad"
        }
        self.assertEqual(set(domain_accounts), set(_AD_ACCOUNT_ROSTER))
        for username, (groups, strength, spn) in _AD_ACCOUNT_ROSTER.items():
            with self.subTest(account=username):
                account = domain_accounts[username]
                self.assertEqual(set(account.groups), groups)
                self.assertEqual(account.password_strength.value, strength)
                self.assertEqual(account.spn, spn)
                self.assertEqual(account.domain_ref, "techvault")
                self.assertFalse(account.disabled)

    def test_wazuh_agents_are_declared_on_the_hosts_they_watch(self) -> None:
        sdl = _load_sdl()
        removed = {"wazuh-sidecar-db", "wazuh-sidecar-suricata"}

        self.assertEqual(removed & set(sdl["nodes"]), set())
        self.assertEqual(removed & set(sdl["infrastructure"]), set())
        for volume, entry in sdl["persistent_volumes"].items():
            with self.subTest(volume=volume):
                consumers = {item["node"] for item in entry.get("consumers", [])}
                self.assertEqual(removed & consumers, set())
        self.assertNotIn("wazuh-sidecar", _SDL.read_text(encoding="utf-8"))

        expected = {
            "ad": {
                (
                    "wazuh_agent",
                    frozenset(
                        {
                            "/var/log/samba/log.samba",
                            "/var/log/samba/log.smbd",
                            "/var/log/samba/log.winbindd",
                        }
                    ),
                    ("wazuh-manager", 1514, "tcp"),
                ),
                ("rsyslog", frozenset(), ("wazuh-manager", 514, "udp")),
            },
            "db": {
                (
                    "wazuh_agent",
                    frozenset({"/var/log/postgresql/postgresql-15-main.log"}),
                    ("wazuh-manager", 1514, "tcp"),
                )
            },
            "suricata": {
                (
                    "wazuh_agent",
                    frozenset({"/var/log/suricata/eve.json"}),
                    ("wazuh-manager", 1514, "tcp"),
                )
            },
        }
        for node_id, agents in expected.items():
            with self.subTest(node=node_id):
                declared = {
                    (
                        agent["implementation"],
                        frozenset(
                            source["location"]
                            for source in agent["sources"]
                            if source.get("kind") == "tailed_path"
                        ),
                        (
                            target["target_node_ref"],
                            target["ingestion_port"],
                            target["protocol"],
                        ),
                    )
                    for agent in sdl["nodes"][node_id]["runtime"]["forwarding_agents"]
                    for target in agent["ship_targets"]
                }
                self.assertEqual(declared, agents)

    def test_red_team_ssh_access_is_declared_not_proxied(self) -> None:
        sdl = _load_sdl()
        removed = {"kali-ssh-proxy", "webapp-proxy", "control-net"}

        self.assertEqual(removed & set(sdl["nodes"]), set())
        self.assertEqual(removed & set(sdl["infrastructure"]), set())
        raw = _SDL.read_text(encoding="utf-8")
        for name in removed:
            with self.subTest(name=name):
                self.assertNotIn(name, raw)

        scenario = parse_sdl_file(_SDL)
        self.assertEqual(scenario.entities["red-team"].role.value, "red")
        operator = scenario.agents["red-team-operator"]
        self.assertEqual(operator.entity, "red-team")
        self.assertEqual(
            {
                (access.target_ref, access.channel.value)
                for access in operator.interactive_access.values()
            },
            {("kali", "ssh")},
        )

    def test_webapp_weaknesses_are_cwe_bindings_on_their_routes(self) -> None:
        raw = _SDL.read_text(encoding="utf-8")
        self.assertNotIn("vulnerabilities", _load_sdl())
        self.assertNotIn("vulnerability_refs", raw)

        bindings = json.loads(_BINDINGS.read_text(encoding="utf-8"))["bindings"]
        self.assertEqual(
            {
                binding_id: (
                    binding["subject"]["canonical_ref"],
                    binding["scheme"]["concept_id"],
                )
                for binding_id, binding in bindings.items()
            },
            {
                binding_id: (_PORTAL_ROUTES + weakness.route, weakness.concept)
                for binding_id, weakness in _WEBAPP_WEAKNESSES.items()
            },
        )
        for binding_id, binding in bindings.items():
            with self.subTest(binding=binding_id):
                self.assertEqual(
                    {key: binding["scheme"][key] for key in _CWE_SCHEME}, _CWE_SCHEME
                )

        (snapshot,) = json.loads(_SCHEMES.read_text(encoding="utf-8"))
        self.assertEqual({key: snapshot[key] for key in _CWE_SCHEME}, _CWE_SCHEME)
        self.assertLessEqual(
            {weakness.concept for weakness in _WEBAPP_WEAKNESSES.values()},
            {term["concept_id"] for term in snapshot["concepts"]},
        )

        self.assertEqual(
            [error for error in validate_pack(_PACK).errors if error.startswith("sdl.bindings")],
            [],
        )

    def test_ad_flags_are_backend_provided_values(self) -> None:
        sdl = _load_sdl()
        scenario = parse_sdl_file(_SDL)
        inventory = {
            entry["path"]: entry
            for entry in sdl["nodes"]["ad"]["runtime"]["filesystem_inventory"]
        }
        placed = {
            item["path"]: item
            for item in sdl["content"].values()
            if item.get("target") == "ad" and item.get("type") == "file"
        }

        for variable, path, mode in (
            ("flag_ad_user", "/opt/flags/user.txt", "0644"),
            ("flag_ad_root", "/root/root.txt", "0600"),
        ):
            with self.subTest(flag=variable):
                declared = scenario.variables[variable]
                self.assertEqual(declared.type.value, "string")
                self.assertTrue(declared.required)
                self.assertIsNone(declared.default)

                self.assertEqual(placed[path]["text"], "${" + variable + "}")
                self.assertIs(placed[path]["sensitive"], True)

                entry = inventory[path]
                self.assertEqual(
                    (
                        entry["entry_type"],
                        entry["owner_user"],
                        entry["owner_group"],
                        entry["mode"],
                    ),
                    ("file", "root", "root", mode),
                )


def _load_refresh_tool() -> types.ModuleType:
    path = _ROOT / "tools" / "refresh_pack_sdl_binding.py"
    module = types.ModuleType("techvault_refresh_pack_sdl_binding")
    module.__file__ = str(path)
    exec(compile(path.read_text(encoding="utf-8"), str(path), "exec"), module.__dict__)
    return module


class TechVaultFlagDeclarationTests(unittest.TestCase):
    """Flag values bind through RAES; the pack preserves their in-world access."""

    USER_FLAGS = {
        "victim": ("/home/labadmin/user.txt", "labadmin"),
        "workstation": ("/home/dev-user/user.txt", "dev-user"),
        "webapp": ("/app/user.txt", "root"),
        "fileshare": ("/srv/shares/shared/user-flag.txt", "root"),
    }

    def test_flags_preserve_paths_owners_and_sensitive_required_values(self) -> None:
        scenario = parse_sdl_file(_SDL)
        for host, (user_path, user_owner) in self.USER_FLAGS.items():
            for level, path, owner, mode in (
                ("user", user_path, user_owner, "0644"),
                ("root", "/root/root.txt", "root", "0600"),
            ):
                with self.subTest(host=host, level=level):
                    variable = f"flag_{host}_{level}"
                    self.assertIn(variable, set(scenario.variables))
                    declaration = scenario.variables[variable]
                    self.assertEqual(declaration.type.value, "string")
                    self.assertTrue(declaration.required)
                    self.assertIsNone(declaration.default)
                    placed = [
                        item for item in scenario.content.values()
                        if item.target == host and item.path == path
                    ]
                    self.assertEqual(len(placed), 1)
                    self.assertEqual(placed[0].type.value, "file")
                    self.assertEqual(placed[0].text, "${" + variable + "}")
                    self.assertTrue(placed[0].sensitive)
                    self.assertIsNone(placed[0].source)
                    inventory = [
                        item for item in scenario.nodes[host].runtime.filesystem_inventory
                        if item.path == path
                    ]
                    self.assertEqual(len(inventory), 1)
                    entry = inventory[0]
                    self.assertEqual(entry.entry_type.value, "file")
                    self.assertEqual((entry.owner_user, entry.owner_group), (owner, owner))
                    self.assertEqual(entry.mode, mode)
                    self.assertEqual(entry.sensitivity.value, "operator_secret")

    def test_instantiation_places_each_run_value_and_rejects_missing_flags(self) -> None:
        scenario = parse_sdl_file(_SDL)
        parameters = {name: f"test-run-one-{name}" for name in scenario.variables}
        for host in self.USER_FLAGS:
            for level in ("user", "root"):
                parameters[f"flag_{host}_{level}"] = f"test-run-one-{host}-{level}"

        for run in ("first", "second"):
            values = {name: f"{run}-{value}" for name, value in parameters.items()}
            concrete = instantiate_scenario(scenario, values)
            for host, (user_path, _) in self.USER_FLAGS.items():
                for level, path in (("user", user_path), ("root", "/root/root.txt")):
                    with self.subTest(run=run, host=host, level=level):
                        placed = [
                            item for item in concrete.content.values()
                            if item.target == host and item.path == path
                        ]
                        self.assertEqual(len(placed), 1)
                        self.assertEqual(placed[0].text, values[f"flag_{host}_{level}"])
                        self.assertTrue(placed[0].sensitive)

        for host in self.USER_FLAGS:
            for level in ("user", "root"):
                variable = f"flag_{host}_{level}"
                with self.subTest(missing=variable):
                    supplied = {name: value for name, value in parameters.items() if name != variable}
                    with self.assertRaisesRegex(
                        SDLInstantiationError, f"Variable '{variable}' is required"
                    ):
                        instantiate_scenario(scenario, supplied)

    def test_pack_has_no_flag_delivery_machinery(self) -> None:
        # Report the diagnostic without dumping the SDL into test output.
        self.longMessage = False
        self.assertNotIn(
            "flaggen",
            _SDL.read_text(encoding="utf-8").lower(),
            "SDL retains a flag-generation reference",
        )
        scenario = parse_sdl_file(_SDL)
        with self.subTest(surface="generated artifacts"):
            self.assertNotIn("techvault-flag-signing-keys", set(scenario.generated_artifacts))
        for host in self.USER_FLAGS:
            with self.subTest(surface="service units", host=host):
                units = scenario.nodes[host].runtime.service_manager_units
                self.assertNotIn("aptl-flaggen", {unit.unit_id for unit in units})
                self.assertNotIn("aptl-flaggen.service", {unit.unit_name for unit in units})
            with self.subTest(surface="content", host=host):
                self.assertNotIn(f"{host}-flaggen-script", set(scenario.content))
                self.assertNotIn(f"{host}-flaggen-unit", set(scenario.content))
                paths = {item.path for item in scenario.content.values() if item.target == host}
                self.assertNotIn("/usr/local/sbin/aptl-flaggen.sh", paths)
                self.assertNotIn("/etc/systemd/system/aptl-flaggen.service", paths)
        with self.subTest(surface="published inventory"):
            manifest = json.loads((_PACK / "associated-artifacts.json").read_text(encoding="utf-8"))
            self.assertNotIn("techvault-flaggen-script", set(manifest["artifacts"]))
        with self.subTest(surface="bundled script"):
            self.assertFalse((_PACK / "assets/content/flaggen.sh").exists())


class TechVaultValidatorEntrypointTests(unittest.TestCase):
    """``validate()`` is what CI runs; every pack contract must be wired into it."""

    def test_validate_reports_each_contract_violation(self) -> None:
        refresh = _load_refresh_tool().refresh
        build_route = {
            "mechanism": {
                "mechanism": "materialization-specification",
                "profile": "some-build",
                "version": "1",
                "digest": "sha256:" + "0" * 64,
            },
            "acquisition": "none",
            "timing": "backend-preparation",
        }

        def add_substrate_constraint(sdl: dict) -> None:
            sdl["realization"]["constraints"] = [
                {
                    "field_pointer": "/nodes/kali",
                    "concern": "compute-substrate",
                    "posture": "exact",
                    "domain": {
                        "kind": "exact",
                        "value": "operating-system-container",
                    },
                }
            ]

        def add_build_recipe(sdl: dict) -> None:
            sdl["nodes"]["kali"]["source"] = {
                "name": "kali",
                "version": "local",
                "artifact_requirement": {
                    "requirement_id": "kali-image",
                    "explicitness": "constrained",
                    "materialization_specifications": [
                        {
                            "specification_id": "kali",
                            "profile": build_route["mechanism"],
                            "digest": "sha256:" + "1" * 64,
                        }
                    ],
                    "permitted_routes": [build_route],
                },
            }

        def publish_on_every_interface(sdl: dict) -> None:
            sdl["nodes"]["dns"]["runtime"]["network"] = {
                "published_ports": [
                    {
                        "container_port": 53,
                        "host_port": 5353,
                        "host_ip": "0.0.0.0",
                        "protocol": "tcp",
                    }
                ]
            }

        def unrelated_suricata_alert(sdl: dict) -> None:
            sdl["evidence_requirements"]["suricata-login-sqli-alert"][
                "scope"
            ] = "unrelated alert"

        def add_delivery_content(sdl: dict) -> None:
            sdl["content"]["renamed-db-launch"] = {
                "type": "file",
                "target": "db",
                "path": "/etc/systemd/system/renamed-db.service",
                "text": "delivery recipe",
            }

        cases = {
            "realization.constraint": add_substrate_constraint,
            "realization.build-recipe": add_build_recipe,
            "realization.host-publication": publish_on_every_interface,
            "suricata.detection-evidence-mismatch": unrelated_suricata_alert,
            "realization.service-unit-content": add_delivery_content,
        }
        for code, mutate in cases.items():
            with self.subTest(code=code), tempfile.TemporaryDirectory() as directory:
                pack = pathlib.Path(directory) / "techvault"
                shutil.copytree(_PACK, pack)
                sdl_path = pack / "sdl" / "techvault.sdl.yaml"
                sdl = yaml.safe_load(sdl_path.read_text(encoding="utf-8"))
                mutate(sdl)
                sdl_path.write_text(yaml.safe_dump(sdl, sort_keys=False), encoding="utf-8")
                refresh(pack)

                validator_path = pack / "validation" / "validate_techvault.py"
                validator = types.ModuleType("techvault_pack_validator_copy")
                validator.__file__ = str(validator_path)
                exec(
                    compile(validator_path.read_text(encoding="utf-8"), str(validator_path), "exec"),
                    validator.__dict__,
                )
                errors = validator.validate()

                self.assertTrue(
                    any(error.startswith(code) for error in errors), errors
                )


class TechVaultCiContractTests(unittest.TestCase):
    def test_first_party_pack_is_on_canonical_ci_surfaces(self) -> None:
        surfaces = {
            ".github/workflows/ci.yml": (_ROOT / ".github/workflows/ci.yml").read_text(),
            ".ground-control.yaml": (_ROOT / ".ground-control.yaml").read_text(),
            ".github/PULL_REQUEST_TEMPLATE.md": (
                _ROOT / ".github/PULL_REQUEST_TEMPLATE.md"
            ).read_text(),
        }
        for name, body in surfaces.items():
            with self.subTest(surface=name):
                self.assertIn("raes-pack-validate --packs-root packs", body)
                self.assertIn("raes-pack-release check --packs-root packs", body)


if __name__ == "__main__":
    unittest.main()
