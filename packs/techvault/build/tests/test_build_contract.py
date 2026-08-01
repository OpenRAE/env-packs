import importlib.util
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

import yaml


PACK_ROOT = Path(__file__).resolve().parents[2]
BUILD_ROOT = PACK_ROOT / "build"
RUNTIME_ROOT = BUILD_ROOT / "aptl-runtime"
VALIDATOR_PATH = BUILD_ROOT / "validate_build.py"
RENDER_PATH = BUILD_ROOT / "render_runtime.py"


def _load_validator():
    spec = importlib.util.spec_from_file_location("techvault_build_validator", VALIDATOR_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _load_render_runtime():
    spec = importlib.util.spec_from_file_location("techvault_render_runtime", RENDER_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _copy_pack_for_test(destination: Path) -> None:
    generated_roots = {
        (PACK_ROOT / "build" / "aptl-runtime").resolve(): {".aptl", "keys", "runs"},
        (PACK_ROOT / "build" / "aptl-runtime" / "config").resolve(): {
            "lab-ssh",
            "soc_certs",
            "wazuh_indexer_ssl_certs",
        },
    }

    def ignore(directory, names):
        ignored = {"__pycache__"}
        try:
            ignored.update(generated_roots.get(Path(directory).resolve(), set()))
        except OSError:
            pass
        return ignored & set(names)

    shutil.copytree(PACK_ROOT, destination, ignore=ignore)


class TechVaultBuildContractTest(unittest.TestCase):
    def setUp(self):
        self.validator = _load_validator()

    def test_build_contract_passes_for_committed_pack(self):
        self.assertEqual([], self.validator.validate_pack(PACK_ROOT))

    def test_every_aces_node_has_compose_service_or_alias(self):
        index = self.validator.build_contract(PACK_ROOT)
        missing = sorted(set(index.aces_nodes) - set(index.node_to_service))
        self.assertEqual([], missing)
        self.assertEqual("kali", index.node_to_service["kali"])
        self.assertEqual("wazuh.manager", index.node_to_service["wazuh-manager"])
        self.assertEqual("wazuh.indexer", index.node_to_service["wazuh-indexer"])

    def test_active_profile_bind_mounts_are_checked_in_or_generated(self):
        issues = self.validator.validate_pack(PACK_ROOT)
        self.assertFalse(
            [issue for issue in issues if "bind mount source must be committed or generated" in issue],
            "\n".join(issues),
        )
        generated = self.validator.build_contract(PACK_ROOT).generated_runtime_paths
        self.assertIn("aptl-runtime/config/wazuh_indexer_ssl_certs/root-ca.pem", generated)
        self.assertIn("aptl-runtime/config/soc_certs/lab-ca.pem", generated)
        self.assertIn("aptl-runtime/config/lab-ssh/kali_pivot_key", generated)

    def test_runtime_does_not_require_repo_root_env(self):
        contract = self.validator.build_contract(PACK_ROOT)
        self.assertEqual("operator-defaults.env", contract.default_env_file)
        self.assertFalse((PACK_ROOT / ".env").exists())
        required = contract.required_env_names
        self.assertIn("MISP_API_KEY", required)
        self.assertLessEqual(required, contract.default_env_names)

    def test_default_dns_publish_avoids_host_mdns_port(self):
        env_values = self.validator._env_values(BUILD_ROOT / "operator-defaults.env")
        self.assertEqual("55353", env_values["APTL_DNS_HOST_PORT"])
        self.assertNotEqual("5353", env_values["APTL_DNS_HOST_PORT"])

    def test_wazuh_api_password_policy_is_enforced_for_defaults(self):
        self.assertTrue(self.validator._wazuh_api_password_strong("TechVaultWazuhApiPass2026!"))
        for value in (
            "techvault-wazuh-api-pass-2026",
            "TechVaultWazuhApiPass",
            "TechVaultWazuhApiPass2026",
            "Short1!",
        ):
            with self.subTest(value=value):
                self.assertFalse(self.validator._wazuh_api_password_strong(value))

    def test_insecure_wazuh_api_password_is_reported(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_root = Path(tmp) / "techvault"
            _copy_pack_for_test(tmp_root)
            env_path = tmp_root / "build" / "operator-defaults.env"
            env_text = env_path.read_text(encoding="utf-8")
            env_path.write_text(
                env_text.replace(
                    "API_PASSWORD=TechVaultWazuhApiPass2026!",
                    "API_PASSWORD=techvault-wazuh-api-pass-2026",
                ),
                encoding="utf-8",
            )

            issues = self.validator.validate_pack(tmp_root)

        self.assertTrue(
            any(
                "env:operator-defaults.env.API_PASSWORD: Wazuh API password policy required" == issue
                for issue in issues
            ),
            "\n".join(issues),
        )

    def test_operator_env_override_must_be_pack_contained_regular_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_root = Path(tmp) / "techvault"
            _copy_pack_for_test(tmp_root)
            inside = tmp_root / "build" / "operator-defaults.env"
            outside = Path(tmp) / "outside.env"
            outside.write_text("INDEXER_USERNAME=admin\n", encoding="utf-8")
            symlink = tmp_root / "build" / "linked.env"
            symlink.symlink_to(inside)

            self.assertEqual(
                inside.resolve(),
                self.validator.resolve_operator_env(
                    "build/operator-defaults.env",
                    pack_root=tmp_root,
                ),
            )
            with self.assertRaises(ValueError):
                self.validator.resolve_operator_env(outside, pack_root=tmp_root)
            with self.assertRaises(ValueError):
                self.validator.resolve_operator_env("build/linked.env", pack_root=tmp_root)

    def test_compose_project_override_is_validated_before_docker_use(self):
        self.assertEqual("techvault_golden", self.validator.validate_compose_project("techvault_golden"))
        for value in ("../escape", "TechVault", "techvault.golden", "-bad", "bad$name"):
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    self.validator.validate_compose_project(value)

    def test_missing_compose_node_mapping_is_reported(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_root = Path(tmp) / "techvault"
            _copy_pack_for_test(tmp_root)
            compose_path = tmp_root / "build" / "aptl-runtime" / "docker-compose.yml"
            compose = yaml.safe_load(compose_path.read_text(encoding="utf-8"))
            compose["services"].pop("kali")
            compose_path.write_text(yaml.safe_dump(compose, sort_keys=False), encoding="utf-8")

            issues = self.validator.validate_pack(tmp_root)

        self.assertTrue(
            any("node:kali.service: compose realization required" == issue for issue in issues),
            "\n".join(issues),
        )

    def test_generated_state_paths_are_gitignored(self):
        contract = self.validator.build_contract(PACK_ROOT)
        ignored = contract.gitignored_paths
        self.assertIn("aptl-runtime/.aptl/", ignored)
        self.assertIn("aptl-runtime/config/soc_certs/", ignored)
        self.assertIn("aptl-runtime/config/wazuh_indexer_ssl_certs/", ignored)
        self.assertIn("aptl-runtime/keys/", ignored)

    def test_mutable_latest_images_are_rejected_for_active_profiles(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_root = Path(tmp) / "techvault"
            _copy_pack_for_test(tmp_root)
            compose_path = tmp_root / "build" / "aptl-runtime" / "docker-compose.yml"
            compose = yaml.safe_load(compose_path.read_text(encoding="utf-8"))
            compose["services"]["misp"]["image"] = "ghcr.io/misp/misp-docker/misp-core:latest"
            compose_path.write_text(yaml.safe_dump(compose, sort_keys=False), encoding="utf-8")

            issues = self.validator.validate_pack(tmp_root)

        self.assertTrue(
            any("service:misp.image: active profile image must not use latest" == issue for issue in issues),
            "\n".join(issues),
        )

    def test_mutable_latest_image_env_values_are_rejected_for_active_profiles(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_root = Path(tmp) / "techvault"
            _copy_pack_for_test(tmp_root)
            compose_path = tmp_root / "build" / "aptl-runtime" / "docker-compose.yml"
            compose = yaml.safe_load(compose_path.read_text(encoding="utf-8"))
            environment = compose["services"]["shuffle-orborus"]["environment"]
            compose["services"]["shuffle-orborus"]["environment"] = [
                "SHUFFLE_WORKER_IMAGE=ghcr.io/shuffle/shuffle-worker:latest"
                if row.startswith("SHUFFLE_WORKER_IMAGE=")
                else row
                for row in environment
            ]
            compose_path.write_text(yaml.safe_dump(compose, sort_keys=False), encoding="utf-8")

            issues = self.validator.validate_pack(tmp_root)

        self.assertTrue(
            any(
                "service:shuffle-orborus.environment.SHUFFLE_WORKER_IMAGE: "
                "active profile image must not use latest" == issue
                for issue in issues
            ),
            "\n".join(issues),
        )

    def test_default_webapp_publish_is_loopback_only(self):
        compose = yaml.safe_load((RUNTIME_ROOT / "docker-compose.yml").read_text(encoding="utf-8"))
        ports = compose["services"]["webapp"]["ports"]
        self.assertEqual(["127.0.0.1:${APTL_HP_WEBAPP_8080:-8080}:8080"], ports)

    def test_health_check_targets_live_kali_marker_and_victim_ip(self):
        health_check = (BUILD_ROOT / "health-check.sh").read_text(encoding="utf-8")
        self.assertIn("test -f /run/aptl-kali-ready", health_check)
        self.assertIn("labadmin@172.20.2.20 true", health_check)
        self.assertNotIn("/tmp/aptl-kali-ready", health_check)
        self.assertNotIn("labadmin@172.20.2.22", health_check)

    def test_wildcard_webapp_publish_is_reported(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_root = Path(tmp) / "techvault"
            _copy_pack_for_test(tmp_root)
            compose_path = tmp_root / "build" / "aptl-runtime" / "docker-compose.yml"
            compose = yaml.safe_load(compose_path.read_text(encoding="utf-8"))
            compose["services"]["webapp"]["ports"] = ["${APTL_HP_WEBAPP_8080:-8080}:8080"]
            compose_path.write_text(yaml.safe_dump(compose, sort_keys=False), encoding="utf-8")

            issues = self.validator.validate_pack(tmp_root)

        self.assertTrue(
            any("service:webapp.ports: host publish must bind loopback" == issue for issue in issues),
            "\n".join(issues),
        )

    def test_reverse_tools_bootstrap_uses_verified_radare2_source(self):
        script = (
            RUNTIME_ROOT
            / "containers"
            / "reverse"
            / "setup-reverse-tools.sh"
        ).read_text(encoding="utf-8")
        self.assertIn('RADARE2_COMMIT="4eb49d5ad8c99eaecc8850a2f10bad407067c898"', script)
        self.assertIn('RADARE2_TREE_SHA="5832bce065b40f209ece377b61d51aed7bdf052b"', script)
        self.assertIn('git fetch --depth=1 origin "${RADARE2_COMMIT}"', script)
        self.assertIn("actual_tree=", script)
        self.assertNotIn("git clone https://github.com/radareorg/radare2", script)

    def test_mutable_radare2_bootstrap_is_reported(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_root = Path(tmp) / "techvault"
            _copy_pack_for_test(tmp_root)
            script_path = (
                tmp_root
                / "build"
                / "aptl-runtime"
                / "containers"
                / "reverse"
                / "setup-reverse-tools.sh"
            )
            script_path.write_text(
                "#!/bin/bash\n"
                "git clone https://github.com/radareorg/radare2\n"
                "bash sys/install.sh\n",
                encoding="utf-8",
            )

            issues = self.validator.validate_pack(tmp_root)

        self.assertTrue(
            any("script:reverse/setup-reverse-tools.sh.radare2: mutable branch clone forbidden" == issue for issue in issues),
            "\n".join(issues),
        )

    def test_service_keystore_password_is_not_passed_in_openssl_argv(self):
        renderer = _load_render_runtime()
        calls = []

        def fake_run(args, **kwargs):
            calls.append((args, kwargs))
            if args[:2] == ["openssl", "genrsa"]:
                Path(args[args.index("-out") + 1]).write_text("key", encoding="utf-8")
            elif args[:3] == ["openssl", "req", "-new"]:
                Path(args[args.index("-out") + 1]).write_text("csr", encoding="utf-8")
            elif args[:3] == ["openssl", "x509", "-req"]:
                Path(args[args.index("-out") + 1]).write_text("cert", encoding="utf-8")
            elif args[:3] == ["openssl", "pkcs12", "-export"]:
                Path(args[args.index("-out") + 1]).write_text("p12", encoding="utf-8")

        with tempfile.TemporaryDirectory() as tmp:
            ca_dir = Path(tmp) / "ca"
            ca_dir.mkdir()
            (ca_dir / "lab-ca.key").write_text("ca-key", encoding="utf-8")
            (ca_dir / "lab-ca.pem").write_text("ca-cert", encoding="utf-8")
            old_run = renderer._run
            old_token = renderer.secrets.token_urlsafe
            renderer._run = fake_run
            renderer.secrets.token_urlsafe = lambda _size: "generated-test-password"
            try:
                renderer._generate_service_cert(ca_dir, "svc", "svc", ("svc",), True)
            finally:
                renderer._run = old_run
                renderer.secrets.token_urlsafe = old_token

        pkcs12_calls = [call for call in calls if call[0][:3] == ["openssl", "pkcs12", "-export"]]
        self.assertEqual(1, len(pkcs12_calls))
        args, kwargs = pkcs12_calls[0]
        self.assertIn("stdin", args)
        self.assertNotIn("pass:generated-test-password", args)
        self.assertEqual("generated-test-password\n", kwargs["input_text"])

    def test_wazuh_certificate_generation_preserves_generator_permissions(self):
        renderer = _load_render_runtime()

        with tempfile.TemporaryDirectory() as tmp:
            runtime_root = Path(tmp) / "runtime"
            certs_dir = runtime_root / "config" / "wazuh_indexer_ssl_certs"

            def fake_run(args, **_kwargs):
                if "run" not in args:
                    return
                certs_dir.mkdir(parents=True, exist_ok=True)
                for name in ("root-ca.pem", "root-ca-manager.pem"):
                    path = certs_dir / name
                    path.write_text(name, encoding="utf-8")
                    path.chmod(0o400)
                certs_dir.chmod(0o500)

            old_root = renderer.RUNTIME_ROOT
            old_run = renderer._run
            renderer.RUNTIME_ROOT = runtime_root
            renderer._run = fake_run
            try:
                renderer._generate_wazuh_certs()
            finally:
                certs_dir.chmod(0o700)
                renderer.RUNTIME_ROOT = old_root
                renderer._run = old_run

            self.assertEqual(0o400, (certs_dir / "root-ca.pem").stat().st_mode & 0o777)
            self.assertEqual(0o400, (certs_dir / "root-ca-manager.pem").stat().st_mode & 0o777)

    def test_metadata_indexes_build_lifecycle_and_provenance(self):
        compatibility = yaml.safe_load((PACK_ROOT / "pack.compatibility.yaml").read_text(encoding="utf-8"))
        runtime = next(row for row in compatibility["runtime_profiles"] if row["profile_id"] == "operational")
        self.assertEqual("supported", runtime["status"])
        self.assertEqual("docker-compose", runtime["provider"])
        self.assertIn({"path": "build/"}, runtime["build"])
        self.assertIn({"path": "build/tests/"}, runtime["tests"])
        self.assertIn(391, compatibility["pack"]["source"]["issues"])
        surface_paths = {row["path"] for row in compatibility["operator_surfaces"]}
        for path in ("build/launch.sh", "build/health-check.sh", "build/reset.sh", "build/cleanup.sh"):
            self.assertIn(path, surface_paths)

    def test_manual_walkthrough_report_contract_and_catalog_index(self):
        guide_path = "docs/walkthroughs/manual-participant-walkthrough.md"
        report_path = "docs/manual-participant-walkthrough-report-393.md"
        guide = (PACK_ROOT / guide_path).read_text(encoding="utf-8")
        report = (PACK_ROOT / report_path).read_text(encoding="utf-8")

        for heading in (
            "## Run boundary",
            "## Participant evidence",
            "## Observer evidence",
            "## Reset and freshness",
            "## Automated follow-up",
            "## Teardown",
            "## Run-specific golden-readiness checklist",
            "## Limitations",
        ):
            self.assertIn(heading, report)
        for check_id in (
            "portal_reachable",
            "negative_invalid_login_rejected",
            "sqli_login_accepted",
            "dashboard_reachable",
            "admin_surface_reachable",
            "web_upload_created",
            "public_share_content",
            "shared_marker_created",
            "telemetry_negative_ssh_generated",
            "portal_reachable_after_reset",
            "sqli_login_after_reset",
            "shared_marker_removed",
            "public_share_content_after_reset",
        ):
            self.assertIn(f"`{check_id}`", report)
            self.assertIn(check_id, guide)
        for forbidden in (
            "BEGIN " + "OPENSSH PRIVATE KEY",
            "BEGIN " + "PRIVATE KEY",
            "Set-Cookie:",
            "AWS_SECRET_ACCESS_KEY=",
            "INDEXER_PASSWORD=",
            "APTL_EXPERIMENT_NO_REDACT=1",
        ):
            self.assertNotIn(forbidden, report)

        compatibility = yaml.safe_load((PACK_ROOT / "pack.compatibility.yaml").read_text(encoding="utf-8"))
        runtime = next(row for row in compatibility["runtime_profiles"] if row["profile_id"] == "operational")
        self.assertIn({"path": guide_path}, runtime["walkthroughs"])
        asset_paths = {row["path"] for row in compatibility["assets"]}
        self.assertTrue({guide_path, report_path} <= asset_paths)
        surface_paths = {row["path"] for row in compatibility["operator_surfaces"]}
        self.assertTrue({guide_path, report_path} <= surface_paths)
        manual_gate = next(row for row in compatibility["validation"]["gates"] if row["id"] == "manual-walkthrough")
        self.assertEqual("manual-walkthrough", manual_gate["kind"])
        self.assertEqual({guide_path, report_path}, {row["path"] for row in manual_gate["paths"]})
        self.assertIn(393, compatibility["pack"]["source"]["issues"])

    def test_golden_metadata_requires_complete_reference_triangle(self):
        pack = yaml.safe_load((PACK_ROOT / "pack.yaml").read_text(encoding="utf-8"))
        compatibility = yaml.safe_load((PACK_ROOT / "pack.compatibility.yaml").read_text(encoding="utf-8"))
        provenance = yaml.safe_load((PACK_ROOT / "docs" / "provenance-ledger.yaml").read_text(encoding="utf-8"))

        self.assertEqual("golden", pack["status"])
        self.assertTrue(pack["contents"]["reference_triangle"])
        self.assertEqual(pack["version"], compatibility["pack"]["version"])
        self.assertEqual(pack["version"], provenance["pack"]["version"])
        self.assertEqual("golden", compatibility["pack"]["status"])
        self.assertEqual(
            "approved",
            next(
                gate["status"]
                for gate in provenance["review"]["gates"]
                if gate["gate_id"] == "offensive-tooling"
            ),
        )
        command_ids = {row["id"] for row in compatibility["validation"]["commands"]}
        self.assertIn("techvault-build", command_ids)
        self.assertIn("techvault-web-ui", command_ids)

        provenance = yaml.safe_load((PACK_ROOT / "docs" / "provenance-ledger.yaml").read_text(encoding="utf-8"))
        artifacts = {row["artifact_id"]: row["path"] for row in provenance["artifacts"]}
        self.assertEqual("build/aptl-runtime/", artifacts["aptl-runtime-build-source"])
        self.assertEqual("build/", artifacts["techvault-build-lifecycle"])


if __name__ == "__main__":
    unittest.main()
