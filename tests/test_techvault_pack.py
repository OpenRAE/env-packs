"""First-party TechVault pack contract (issue #234).

The checks in this module deliberately preserve the complete upstream SDL while
moving its repository-local content dependencies behind immutable pack artifact
identities.  They are regression guards for the migration, not a second source
of RAES scenario semantics.
"""

from __future__ import annotations

import copy
import hashlib
import hmac
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
from unittest import mock

import yaml

from raes_env_packs import PackDigestError, resolve_pack_artifact, validate_pack
from raes_env_packs.digest import validate_pack_content_manifest


_ROOT = pathlib.Path(__file__).resolve().parents[1]
_PACK = _ROOT / "packs" / "techvault"
_SDL = _PACK / "sdl" / "techvault.sdl.yaml"
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
        "cortex-initializer-script",
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
        "kali-wrap-shell-script",
        "kali-capture-client",
        "victim-flaggen-script",
        "workstation-flaggen-script",
        "webapp-flaggen-script",
        "fileshare-flaggen-script",
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


def _load_sdl() -> dict:
    return yaml.safe_load(_SDL.read_text(encoding="utf-8"))


def _canonical_json_digest(document: object) -> str:
    payload = json.dumps(
        document, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    ).encode("utf-8")
    return "sha256:" + hashlib.sha256(payload).hexdigest()


def _assert_shuffle_runtime_contract(test: unittest.TestCase, sdl: dict) -> None:
    """Assert the exact closed Shuffle-to-OpenSearch authored contract."""
    nodes = sdl["nodes"]
    backend = nodes["shuffle-backend"]
    opensearch = nodes["shuffle-opensearch"]

    environment = {
        item["name"]: item for item in backend["runtime"]["environment"]
    }
    expected_environment = {
        "SHUFFLE_APP_SDK_TIMEOUT": {
            "name": "SHUFFLE_APP_SDK_TIMEOUT",
            "value": "120",
            "value_classification": "plain",
            "provenance": "compose",
        },
        "SHUFFLE_DEFAULT_APIKEY": {
            "name": "SHUFFLE_DEFAULT_APIKEY",
            "value": "31a211c4-ea5c-4a49-b022-5e2434e758a7",
            "value_classification": "secret_fixture",
            "provenance": "compose",
        },
        "SHUFFLE_DEFAULT_PASSWORD": {
            "name": "SHUFFLE_DEFAULT_PASSWORD",
            "value": "ShuffleAdmin2024!",
            "value_classification": "secret_fixture",
            "provenance": "compose",
        },
        "SHUFFLE_DEFAULT_USERNAME": {
            "name": "SHUFFLE_DEFAULT_USERNAME",
            "value": "admin",
            "value_classification": "plain",
            "provenance": "compose",
        },
        "SHUFFLE_OPENSEARCH_PASSWORD": {
            "name": "SHUFFLE_OPENSEARCH_PASSWORD",
            "value": "StrongPassword123!",
            "value_classification": "secret_fixture",
            "provenance": "compose",
        },
        "SHUFFLE_OPENSEARCH_SKIPSSL_VERIFY": {
            "name": "SHUFFLE_OPENSEARCH_SKIPSSL_VERIFY",
            "value": "true",
            "value_classification": "plain",
            "provenance": "compose",
        },
        "SHUFFLE_OPENSEARCH_URL": {
            "name": "SHUFFLE_OPENSEARCH_URL",
            "value": "https://shuffle-opensearch:9200",
            "value_classification": "plain",
            "provenance": "compose",
        },
        "SHUFFLE_OPENSEARCH_USERNAME": {
            "name": "SHUFFLE_OPENSEARCH_USERNAME",
            "value": "admin",
            "value_classification": "plain",
            "provenance": "compose",
        },
    }
    test.assertEqual(environment, expected_environment)

    opensearch_environment = {
        item["name"]: item for item in opensearch["runtime"]["environment"]
    }
    bootstrap_password = opensearch_environment[
        "OPENSEARCH_INITIAL_ADMIN_PASSWORD"
    ]
    test.assertEqual(bootstrap_password["value_classification"], "secret_fixture")
    test.assertEqual(bootstrap_password["provenance"], "compose")
    test.assertEqual(
        environment["SHUFFLE_OPENSEARCH_PASSWORD"]["value"],
        bootstrap_password["value"],
    )

    (datastore,) = opensearch["runtime"]["datastore_services"]
    test.assertEqual(datastore["service"], "opensearch-rest")
    test.assertEqual(datastore["protocol"], "https")
    test.assertEqual(
        datastore["nodes"],
        [
            {
                "node_id": "shuffle-opensearch-node",
                "name": "shuffle-opensearch",
                "roles": ["data", "cluster_manager"],
                "is_coordinator": True,
                "endpoints": [
                    {
                        "endpoint_id": "shuffle-opensearch-client",
                        "role": "client",
                        "protocol": "https",
                        "address": "shuffle-opensearch",
                        "port": 9200,
                    }
                ],
            }
        ],
    )
    test.assertEqual(
        datastore["transport_security"],
        {
            "transport_security_id": "shuffle-opensearch-tls",
            "mode": "tls",
            "client_verification": False,
            "node_verification": False,
            "description": (
                "The disposable single-node datastore uses the selected image's "
                "demo TLS material; Shuffle deliberately does not verify that "
                "certificate on this internal hop."
            ),
        },
    )

    endpoint = datastore["nodes"][0]["endpoints"][0]
    expected_url = f'{endpoint["protocol"]}://{endpoint["address"]}:{endpoint["port"]}'
    test.assertEqual(environment["SHUFFLE_OPENSEARCH_URL"]["value"], expected_url)
    test.assertEqual(
        environment["SHUFFLE_OPENSEARCH_SKIPSSL_VERIFY"]["value"],
        str(not datastore["transport_security"]["client_verification"]).lower(),
    )

    (application,) = backend["runtime"]["platform_applications"]
    test.assertEqual(application["platform_application_id"], "shuffle-soar")
    test.assertEqual(application["service"], "shuffle-api")
    test.assertEqual(application["product"], "Shuffle")
    test.assertEqual(
        application["capabilities"],
        [
            {
                "capability_id": "workflow-automation",
                "kind": "workflow_automation",
            }
        ],
    )
    test.assertEqual(
        application["upstream_bindings"],
        [
            {
                "binding_id": "shuffle-index-backend",
                "role": "index_backend",
                "target_node_ref": "shuffle-opensearch",
                "target_service_ref": "opensearch-rest",
            }
        ],
    )

    (listener,) = backend["runtime"]["service_listeners"]
    test.assertEqual(listener["service"], "shuffle-api")
    test.assertEqual(listener["address"], "0.0.0.0")
    test.assertEqual(listener["port"], 5001)
    test.assertEqual(listener["protocol"], "tcp")
    test.assertEqual(listener["scope"], "wildcard")
    test.assertEqual(listener["provenance"], "operator")
    readiness = listener["readiness"]
    test.assertIn("authenticated Shuffle API", readiness["criteria"])
    test.assertIn("write", readiness["criteria"])
    test.assertIn("read", readiness["criteria"])
    test.assertIn("OpenSearch", readiness["criteria"])

    volumes = sdl["persistent_volumes"]
    test.assertEqual(volumes["shuffle_data"]["lifecycle"], "retain")
    test.assertEqual(volumes["shuffle_opensearch_data"]["lifecycle"], "retain")
    test.assertEqual(
        volumes["shuffle_data"]["consumers"],
        [
            {
                "node": "shuffle-backend",
                "mount_destination": "/shuffle-database",
                "access_mode": "read_write",
            }
        ],
    )
    test.assertEqual(
        volumes["shuffle_opensearch_data"]["consumers"],
        [
            {
                "node": "shuffle-opensearch",
                "mount_destination": "/usr/share/opensearch/data",
                "access_mode": "read_write",
            }
        ],
    )


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
            "nodes": 38,
            "infrastructure": 38,
            "persistent_volumes": 24,
            "features": 2,
            "vulnerabilities": 14,
            "propositions": 3,
            "assertions": 3,
            "observation_boundaries": 1,
            "evidence_requirements": 3,
            "identity_domains": 1,
            "relationships": 2,
            "accounts": 4,
        }
        for section, expected in expected_counts.items():
            with self.subTest(section=section):
                self.assertEqual(len(sdl[section]), expected)

        # This runtime-authority declaration is intentionally not a content
        # acquisition path and must survive the pack migration.
        self.assertIn("/var/run/docker.sock", _SDL.read_text(encoding="utf-8"))

    def test_shuffle_runtime_contract_is_complete_and_consistent(self) -> None:
        _assert_shuffle_runtime_contract(self, _load_sdl())

    def test_shuffle_runtime_contract_rejects_closed_state_drift(self) -> None:
        mutations = {
            "missing environment": lambda sdl: sdl["nodes"]["shuffle-backend"][
                "runtime"
            ]["environment"].pop(),
            "excess environment": lambda sdl: sdl["nodes"]["shuffle-backend"][
                "runtime"
            ]["environment"].append({"name": "UNDECLARED", "value": "true"}),
            "substituted endpoint": lambda sdl: sdl["nodes"]["shuffle-backend"][
                "runtime"
            ]["environment"][0].update({"value": "https://other:9200"}),
            "credential mismatch": lambda sdl: next(
                item
                for item in sdl["nodes"]["shuffle-opensearch"]["runtime"][
                    "environment"
                ]
                if item["name"] == "OPENSEARCH_INITIAL_ADMIN_PASSWORD"
            ).update({"value": "different-fixture"}),
            "verification mismatch": lambda sdl: sdl["nodes"][
                "shuffle-opensearch"
            ]["runtime"]["datastore_services"][0]["transport_security"].update(
                {"client_verification": True}
            ),
        }

        original = _load_sdl()
        for name, mutate in mutations.items():
            with self.subTest(mutation=name):
                candidate = copy.deepcopy(original)
                mutate(candidate)
                with self.assertRaises((AssertionError, KeyError)):
                    _assert_shuffle_runtime_contract(self, candidate)

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
        self.assertEqual(len(inline), 23)
        self.assertEqual(sourced, _PACK_ARTIFACT_CONTENT_IDS)
        self.assertEqual(materialized, set())
        self.assertEqual(len(content) + len(_GENERATED_SSH_CONTENT_IDS), 66)

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
            "generated output mismatch": (
                update_named(
                    ("nodes", "misp-suricata-sync", "runtime", "environment"),
                    "name",
                    "RULES_OUT_PATH",
                    {"value": "/tmp/misp.rules"},
                ),
                "suricata.generated-output-mismatch: RULES_OUT_PATH",
            ),
            "SID namespace mismatch": (
                update_named(
                    ("nodes", "misp-suricata-sync", "runtime", "environment"),
                    "name",
                    "SID_BASE",
                    {"value": "98000000"},
                ),
                "suricata.sid-namespace-mismatch: SID_BASE",
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
            "forwarder socket mismatch": (
                update_named(
                    ("nodes", "misp-suricata-sync", "runtime", "environment"),
                    "name",
                    "SURICATA_SOCKET_PATH",
                    {"value": "/tmp/suricata-command.socket"},
                ),
                "suricata.control-channel-mismatch: SURICATA_SOCKET_PATH",
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
            "login route vulnerability mismatch": (
                set_path(
                    (
                        "nodes",
                        "webapp",
                        "runtime",
                        "applications",
                        0,
                        "routes",
                        1,
                        "vulnerability_refs",
                    ),
                    [],
                ),
                "suricata.detection-path-mismatch: webapp login vulnerability",
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

    def test_operator_soc_surfaces_are_loopback_published(self) -> None:
        nodes = _load_sdl()["nodes"]
        expected = {
            "misp": {(443, 8443)},
            "thehive": {(9000, 9000)},
            "cortex": {(9001, 9001)},
            "shuffle-frontend": {(443, 3443), (80, 3001)},
        }

        for node_name, expected_ports in expected.items():
            with self.subTest(node=node_name):
                published = nodes[node_name]["runtime"]["network"][
                    "published_ports"
                ]
                self.assertEqual(
                    {(item["container_port"], item["host_port"]) for item in published},
                    expected_ports,
                )
                self.assertTrue(
                    all(item["host_ip"] == "127.0.0.1" for item in published)
                )

    def test_cortex_provides_case_driven_offline_enrichment(self) -> None:
        sdl = _load_sdl()
        thehive = sdl["nodes"]["thehive"]
        command = thehive["runtime"]["container"]["command"]
        self.assertEqual(
            command[command.index("--cortex-proto") + 1], "http"
        )
        self.assertEqual(
            command[command.index("--cortex-hostnames") + 1], "cortex"
        )
        self.assertEqual(command[command.index("--cortex-port") + 1], "9001")

        thehive_environment = {
            item["name"]: item for item in thehive["runtime"]["environment"]
        }
        connector_key = thehive_environment["TH_CORTEX_KEYS"]
        self.assertEqual(connector_key["value_classification"], "redacted")
        self.assertNotIn("value", connector_key)
        self.assertEqual(
            connector_key["value_from"],
            {
                "generated_artifact": "cortex-service-credentials",
                "output": "connector-api-key",
            },
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
        initializer_principal = principals["cortex-initializer-admin"]
        self.assertEqual(initializer_principal["credential_classification"], "redacted")
        self.assertEqual(
            initializer_principal["backend_roles"], ["read", "analyze", "orgadmin"]
        )

        initializer = sdl["nodes"]["cortex-initializer"]
        self.assertTrue(initializer["runtime"]["container"]["autoremove"])
        initializer_environment = {
            item["name"]: item for item in initializer["runtime"]["environment"]
        }
        self.assertEqual(
            initializer_environment["CORTEX_CONNECTOR_KEY"]["value_from"],
            connector_key["value_from"],
        )
        self.assertEqual(
            initializer_environment["CORTEX_CONNECTOR_KEY"]["value_classification"],
            "redacted",
        )
        self.assertNotEqual(
            initializer_environment["CORTEX_ADMIN_KEY"]["value_from"],
            connector_key["value_from"],
        )
        self.assertNotIn("value", initializer_environment["CORTEX_ADMIN_KEY"])

        credential_artifact = sdl["generated_artifacts"][
            "cortex-service-credentials"
        ]
        self.assertEqual(credential_artifact["generator"], "rendered_config")
        self.assertEqual(credential_artifact["lifecycle"], "reuse_valid")
        self.assertEqual(
            {output["name"] for output in credential_artifact["outputs"]},
            {"initializer-api-key", "connector-api-key"},
        )
        self.assertTrue(
            all(
                output["sensitivity"] == "secret"
                for output in credential_artifact["outputs"]
            )
        )

        self.assertIn(
            "cortex-initializer", sdl["infrastructure"]["thehive"]["dependencies"]
        )
        self.assertEqual(
            sdl["infrastructure"]["cortex-initializer"]["dependencies"],
            ["cortex"],
        )

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
            "cortex-initializer-script",
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

        self.assertNotIn(
            "datastore_services", sdl["nodes"]["thehive-es"]["runtime"]
        )

        initializer = (
            _PACK / "assets" / "content" / "cortex-initializer.py"
        ).read_text(encoding="utf-8")
        self.assertIn("/api/maintenance/migrate", initializer)
        self.assertNotIn("cortex_6", initializer)
        self.assertNotIn("_mapping", initializer)

    def test_cortex_pack_validator_rejects_contract_mutations(self) -> None:
        original = _load_sdl()
        self.assertEqual(
            _PACK_VALIDATOR.validate_cortex_contract(_PACK, original), []
        )

        def environments(candidate):
            return {
                node: {
                    item["name"]: item
                    for item in candidate["nodes"][node]["runtime"]["environment"]
                }
                for node in ("thehive", "cortex-initializer")
            }

        def principals(candidate):
            return {
                item["principal_id"]: item
                for item in candidate["nodes"]["cortex"]["runtime"]
                ["app_authorizations"][0]["principals"]
            }

        def mutate(candidate, code):
            env = environments(candidate)
            cortex_runtime = candidate["nodes"]["cortex"]["runtime"]
            if code == "connector-key-mismatch":
                env["thehive"]["TH_CORTEX_KEYS"]["value_from"]["output"] = "initializer-api-key"
            elif code == "initializer-key-invalid":
                env["cortex-initializer"]["CORTEX_ADMIN_KEY"]["value_from"]["output"] = "connector-api-key"
            elif code == "generated-credentials-invalid":
                candidate["generated_artifacts"]["cortex-service-credentials"]["outputs"][0]["sensitivity"] = "public"
            elif code == "application-missing":
                cortex_runtime["platform_applications"][0]["platform_application_id"] = "other"
            elif code == "capability-missing":
                cortex_runtime["platform_applications"][0]["capabilities"] = []
            elif code == "connector-principal-invalid":
                principals(candidate)["thehive-cortex-connector"]["backend_roles"].append("orgadmin")
            elif code == "initializer-principal-invalid":
                principals(candidate)["cortex-initializer-admin"]["backend_roles"] = ["read"]
            elif code == "initializer-not-oneshot":
                candidate["nodes"]["cortex-initializer"]["runtime"]["container"]["autoremove"] = False
            elif code == "docker-socket-forbidden":
                candidate["nodes"]["cortex-initializer"]["runtime"]["container"]["mounts"] = ["/var/run/docker.sock"]
            elif code == "native-schema-leaked":
                candidate["content"]["cortex-job-index-schema"] = {}
            elif code == "content-placement-mismatch":
                candidate["content"]["cortex-initializer-script"]["path"] = "/tmp/initializer.py"
            elif code == "content-identity-mismatch":
                candidate["content"]["cortex-initializer-script"]["source"]["artifact_requirement"]["exact_artifact"]["digest"] = "sha256:" + "0" * 64

        codes = (
            "connector-key-mismatch",
            "initializer-key-invalid",
            "generated-credentials-invalid",
            "application-missing",
            "capability-missing",
            "connector-principal-invalid",
            "initializer-principal-invalid",
            "initializer-not-oneshot",
            "docker-socket-forbidden",
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
        self.assertEqual(len(generated), 8)

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

        signing = generated["techvault-flag-signing-keys"]
        self.assertEqual(signing["generator"], "rendered_config")
        seed = next(
            output for output in signing["outputs"] if output["name"] == "signing-seed"
        )
        self.assertEqual(seed["disposition"], "producer_private")
        selected = {
            name
            for consumer in signing["consumers"]
            for name in consumer["selected_outputs"]
        }
        self.assertNotIn("signing-seed", selected)
        self.assertEqual(
            selected,
            {
                "victim-signing-key",
                "workstation-signing-key",
                "webapp-signing-key",
                "fileshare-signing-key",
            },
        )

    def test_security_assets_drop_legacy_unsafe_primitives(self) -> None:
        capture = resolve_pack_artifact(_PACK, "techvault-kali-wrap-shell").data
        self.assertNotIn(b"run_unwrapped", capture)
        self.assertNotIn(b"running unwrapped", capture)

        flaggen = resolve_pack_artifact(_PACK, "techvault-flaggen-script").data
        self.assertNotIn(b"aptl-flag-key-2024", flaggen)
        self.assertNotIn(b"md5sum", flaggen)

    def test_capture_wrapper_rejects_missing_capability_and_unreachable_sidecar(
        self,
    ) -> None:
        wrapper = _PACK / "assets" / "content" / "kali-wrap-shell.sh"
        env = os.environ.copy()
        env.pop("APTL_CAPTURE_CAPABILITY", None)
        missing = subprocess.run(
            ["/bin/bash", str(wrapper)],
            env=env,
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
        self.assertEqual(missing.returncode, 70)
        self.assertIn("capture capability missing; access denied", missing.stderr)

        with tempfile.TemporaryDirectory() as directory:
            tools = pathlib.Path(directory)
            client = tools / "aptl-capture-client"
            client.write_text("#!/bin/sh\nexit 1\n", encoding="utf-8")
            client.chmod(0o755)
            env.update(
                {
                    "PATH": f"{tools}:/usr/bin:/bin",
                    "APTL_CAPTURE_CAPABILITY": "opaque-one-use-capability",
                }
            )
            unavailable = subprocess.run(
                ["/bin/bash", str(wrapper)],
                env=env,
                capture_output=True,
                text=True,
                timeout=10,
                check=False,
            )
        self.assertEqual(unavailable.returncode, 70)
        self.assertIn("capture sidecar unavailable; access denied", unavailable.stderr)

    def test_capture_client_sends_and_validates_authenticated_protocol(self) -> None:
        path = _PACK / "assets" / "content" / "kali-capture-client"
        module = types.ModuleType("techvault_capture_client_protocol_test")
        module.__file__ = str(path)
        exec(compile(path.read_bytes(), str(path), "exec"), module.__dict__)

        class AcknowledgingSocket:
            def __init__(self) -> None:
                self.frames: list[dict] = []
                self.response = bytearray()

            def settimeout(self, _timeout: float) -> None:
                pass

            def sendall(self, data: bytes) -> None:
                frame = json.loads(data)
                self.frames.append(frame)
                if frame["type"] == "session_start":
                    response_type = "session_accepted"
                elif frame["type"] == "session_end":
                    response_type = "session_finalized"
                else:
                    return
                self.response.extend(
                    json.dumps(
                        {
                            "version": 2,
                            "type": response_type,
                            "run_id": "run-1",
                            "session_id": "session-1",
                        },
                        separators=(",", ":"),
                    ).encode("utf-8")
                    + b"\n"
                )

            def recv(self, size: int) -> bytes:
                chunk = bytes(self.response[:size])
                del self.response[:size]
                return chunk

            def close(self) -> None:
                pass

        source = io.BytesIO(b"terminal bytes")
        fake_socket = AcknowledgingSocket()
        with (
            mock.patch.object(module, "_connect", return_value=fake_socket),
            mock.patch.object(module.sys, "stdin", types.SimpleNamespace(buffer=source)),
            mock.patch.dict(
                module.os.environ,
                {"APTL_CAPTURE_CAPABILITY": "opaque-one-use-capability"},
            ),
        ):
            module.cmd_stream("run-1", "session-1")

        self.assertEqual(
            [frame["type"] for frame in fake_socket.frames],
            ["session_start", "pty_chunk", "session_end"],
        )
        start = fake_socket.frames[0]
        self.assertEqual(start["version"], 2)
        self.assertEqual(start["capability"], "opaque-one-use-capability")
        self.assertEqual((start["run_id"], start["session_id"]), ("run-1", "session-1"))

    def test_capture_client_drains_after_midstream_failure_and_exits_nonzero(self) -> None:
        path = _PACK / "assets" / "content" / "kali-capture-client"
        module = types.ModuleType("techvault_capture_client_test")
        module.__file__ = str(path)
        exec(compile(path.read_bytes(), str(path), "exec"), module.__dict__)

        class FailingSocket:
            def __init__(self) -> None:
                self.send_count = 0
                self.response = bytearray(
                    b'{"version":2,"type":"session_accepted",'
                    b'"run_id":"run-1","session_id":"session-1"}\n'
                )

            def settimeout(self, _timeout: float) -> None:
                pass

            def sendall(self, _data: bytes) -> None:
                self.send_count += 1
                if self.send_count == 3:
                    raise BrokenPipeError("injected mid-stream failure")

            def recv(self, size: int) -> bytes:
                chunk = bytes(self.response[:size])
                del self.response[:size]
                return chunk

            def close(self) -> None:
                pass

        source = io.BytesIO(b"x" * (module._CHUNK_SIZE * 3))
        fake_socket = FailingSocket()
        with (
            mock.patch.object(module, "_connect", return_value=fake_socket),
            mock.patch.object(module.sys, "stdin", types.SimpleNamespace(buffer=source)),
            mock.patch.dict(
                module.os.environ,
                {"APTL_CAPTURE_CAPABILITY": "opaque-one-use-capability"},
            ),
            self.assertRaises(SystemExit) as raised,
        ):
            module.cmd_stream("run-1", "session-1")

        self.assertEqual(raised.exception.code, 1)
        self.assertEqual(source.tell(), len(source.getvalue()))

    def test_capture_wrapper_rejects_failed_stream_after_fifo_is_drained(self) -> None:
        wrapper = _PACK / "assets" / "content" / "kali-wrap-shell.sh"
        with tempfile.TemporaryDirectory() as directory:
            tools = pathlib.Path(directory)
            client = tools / "aptl-capture-client"
            script = tools / "script"
            client.write_text(
                "#!/bin/sh\n"
                "if [ \"${1:-}\" = ping ]; then exit 0; fi\n"
                "cat >/dev/null\n"
                "exit 1\n",
                encoding="utf-8",
            )
            script.write_text(
                "#!/bin/sh\n"
                "spool=\n"
                "while [ \"$#\" -gt 0 ]; do\n"
                "  if [ \"$1\" = --log-io ]; then shift; spool=$1; fi\n"
                "  shift\n"
                "done\n"
                "printf 'fully drained transcript' >\"$spool\"\n"
                "exit 0\n",
                encoding="utf-8",
            )
            client.chmod(0o755)
            script.chmod(0o755)
            env = os.environ.copy()
            env.update(
                {
                    "PATH": f"{tools}:/usr/bin:/bin",
                    "APTL_CAPTURE_CAPABILITY": "opaque-one-use-capability",
                    "APTL_RUN_ID": "run-1",
                    "APTL_SESSION_ID": "session-1",
                    "SSH_ORIGINAL_COMMAND": "true",
                }
            )
            result = subprocess.run(
                ["/bin/bash", str(wrapper)],
                env=env,
                capture_output=True,
                text=True,
                timeout=10,
                check=False,
            )

        self.assertEqual(result.returncode, 70)
        self.assertIn("capture stream failed; session invalid", result.stderr)

    def test_flag_generator_requires_key_and_emits_verifiable_hmac_tokens(self) -> None:
        flaggen = _PACK / "assets" / "content" / "flaggen.sh"
        with tempfile.TemporaryDirectory() as directory:
            root = pathlib.Path(directory)
            tools = root / "bin"
            tools.mkdir()
            chown = tools / "chown"
            chown.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
            chown.chmod(0o755)
            key = root / "signing.key"
            key.write_text("test-only-signing-key", encoding="utf-8")
            user_flag = root / "user.txt"
            root_flag = root / "root.txt"
            base_env = os.environ.copy()
            base_env.update(
                {
                    "PATH": f"{tools}:/usr/bin:/bin",
                    "APTL_FLAG_NODE": "victim",
                    "APTL_FLAG_USER_PATH": str(user_flag),
                    "APTL_FLAG_USER_OWNER": "nobody:nogroup",
                    "APTL_FLAG_ROOT_PATH": str(root_flag),
                }
            )

            missing = subprocess.run(
                ["/bin/bash", str(flaggen)],
                env=base_env,
                capture_output=True,
                text=True,
                timeout=10,
                check=False,
            )
            self.assertEqual(missing.returncode, 78)

            empty_key = root / "empty.key"
            empty_key.touch()
            empty_env = base_env | {"APTL_FLAG_KEY_FILE": str(empty_key)}
            empty = subprocess.run(
                ["/bin/bash", str(flaggen)],
                env=empty_env,
                capture_output=True,
                text=True,
                timeout=10,
                check=False,
            )
            self.assertEqual(empty.returncode, 78)

            signed_env = base_env | {"APTL_FLAG_KEY_FILE": str(key)}
            signed = subprocess.run(
                ["/bin/bash", str(flaggen)],
                env=signed_env,
                capture_output=True,
                text=True,
                timeout=10,
                check=False,
            )
            self.assertEqual(signed.returncode, 0, signed.stderr)

            for level, path in (("user", user_flag), ("root", root_flag)):
                token_line = next(
                    line for line in path.read_text(encoding="utf-8").splitlines()
                    if line.startswith("Token: ")
                )
                token = token_line.removeprefix("Token: ")
                prefix, version, node, actual_level, nonce, signature = token.split(":")
                self.assertEqual((prefix, version, node, actual_level), ("aptl", "v2", "victim", level))
                expected = hmac.new(
                    b"test-only-signing-key",
                    f"victim:{level}:{nonce}".encode("utf-8"),
                    hashlib.sha256,
                ).hexdigest()
                self.assertTrue(hmac.compare_digest(signature, expected))


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
