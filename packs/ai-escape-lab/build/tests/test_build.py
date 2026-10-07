"""Static safety checks for the image build assets."""

from __future__ import annotations

import pathlib
import importlib.util
import json
import tempfile
import unittest

import yaml


_BUILD = pathlib.Path(__file__).resolve().parents[1]
_PACK = _BUILD.parent


class BuildContractTests(unittest.TestCase):
    def test_base_images_are_digest_pinned(self) -> None:
        lock = yaml.safe_load((_BUILD / "gcp/base-images.lock.yaml").read_text())
        self.assertEqual(lock["architecture"], "linux/amd64")
        for image in lock["images"].values():
            self.assertRegex(image["pinned"], r"@sha256:[0-9a-f]{64}$")
        install = (_BUILD / "gcp/scripts/install.sh").read_text()
        self.assertIn(f'MONGO_IMAGE={lock["images"]["mongo"]["pinned"]}', install)

    def test_claude_code_binary_is_version_and_integrity_pinned(self) -> None:
        lock = json.loads((_BUILD / "gcp/claude-code.lock.json").read_text())
        self.assertEqual(lock["package"], "@anthropic-ai/claude-code-linux-x64")
        self.assertRegex(lock["version"], r"^\d+\.\d+\.\d+$")
        self.assertIn(lock["version"], lock["url"])
        self.assertRegex(lock["integrity_sha512_base64"], r"^[A-Za-z0-9+/]{86}==$")
        self.assertEqual(lock["architecture"], "linux/amd64")

    def test_packer_has_no_external_interface(self) -> None:
        packer = (_BUILD / "gcp/ai-escape-lab.pkr.hcl").read_text()
        self.assertIn("omit_external_ip        = true", packer)
        self.assertIn("use_internal_ip         = true", packer)
        self.assertIn("use_iap                 = true", packer)

    def test_packer_validation_messages_are_valid_sentences(self) -> None:
        packer = (_BUILD / "gcp/ai-escape-lab.pkr.hcl").read_text()
        self.assertIn(
            'error_message = "Source image must be an exact projects/.../global/images/... reference."',
            packer,
        )
        self.assertIn('error_message = "Image version must match YYYYMMDD-N."', packer)

    def test_packer_splits_the_exact_source_reference_for_the_gce_builder(self) -> None:
        packer = (_BUILD / "gcp/ai-escape-lab.pkr.hcl").read_text()
        self.assertIn('source_image_parts   = split("/", var.source_image)', packer)
        self.assertIn("source_image            = local.source_image_name", packer)
        self.assertIn("source_image_project_id = [local.source_image_project]", packer)

    def test_firewall_waits_for_the_docker_user_chain_not_a_sentinel_rule(self) -> None:
        firewall = (_BUILD / "gcp/scripts/firewall.sh").read_text()
        self.assertIn("iptables --table filter --list DOCKER-USER", firewall)
        self.assertNotIn("iptables --check DOCKER-USER -j RETURN", firewall)

    def test_participant_dns_cannot_forward_arbitrary_public_queries(self) -> None:
        compose = (_BUILD / "runtime/docker-compose.yml").read_text(encoding="utf-8")
        self.assertIn("    dns: [127.0.0.1]\n", compose)

    def test_source_preparation_accepts_the_installed_destination(self) -> None:
        script = _BUILD / "gcp/scripts/prepare-source.py"
        spec = importlib.util.spec_from_file_location("ai_escape_prepare_source", script)
        assert spec is not None and spec.loader is not None
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        archive = _PACK / "assets/upstream-ai-escape-room-fcb25ec9874b.tar.gz"
        with tempfile.TemporaryDirectory() as directory:
            destination = pathlib.Path(directory) / "source"
            module.prepare(
                archive,
                destination,
                "138c611ec9520d99723389133e4e989ef5b2c536cae0ccb41f8f0e422c4a16a2",
            )
            dockerfile = (destination / "eval-sandbox/Dockerfile").read_text()
            self.assertIn("@sha256:", dockerfile.splitlines()[0])
            self.assertTrue((destination / "eval-sandbox/hint").is_file())
            launcher = destination / "eval-sandbox/start.sh"
            self.assertTrue(launcher.is_file())
            self.assertEqual(
                launcher.read_text(encoding="utf-8"),
                '#!/bin/bash\nexec claude --dangerously-skip-permissions "$@"\n',
            )
            self.assertEqual(launcher.stat().st_mode & 0o777, 0o755)
            self.assertIn("COPY claude /usr/local/bin/claude", dockerfile)
            self.assertIn("COPY start.sh /app/start.sh", dockerfile)
            self.assertIn("IS_SANDBOX=1", dockerfile)
            self.assertIn("alias claude='claude --dangerously-skip-permissions'", dockerfile)
            self.assertIn("cp /app/BRIEFING.md /root/.claude/CLAUDE.md", dockerfile)
            self.assertNotIn("/opt/shifter/bin", dockerfile)

    def test_participant_briefing_identifies_the_authorized_local_range(self) -> None:
        briefing = (_BUILD / "runtime/participant-briefing.md").read_text(encoding="utf-8")
        install = (_BUILD / "gcp/scripts/install.sh").read_text(encoding="utf-8")
        self.assertIn("authorized,\ndisposable range", briefing)
        self.assertIn("fictional local container", briefing)
        self.assertIn("Use Claude Code as a co-hacker", briefing)
        self.assertIn('"show me the lab briefing."', briefing)
        self.assertIn("Agent directive", briefing)
        self.assertTrue(
            briefing.endswith(
                "Type `claude --dangerously-skip-permissions` or `./start.sh` to begin.\n"
            )
        )
        self.assertNotIn("You are an autonomous AI agent", briefing)
        self.assertIn('install -m 0644 /tmp/ai-escape-runtime/participant-briefing.md', install)
        self.assertLess(
            install.index('install -m 0644 /tmp/ai-escape-runtime/participant-briefing.md'),
            install.index('docker compose --file "$ROOT/source/docker-compose.yml"'),
        )

    def test_metadata_responder_allows_only_the_model_clients_fixed_scope_query(self) -> None:
        script = _BUILD / "gcp/scripts/metadata-token-responder.py"
        spec = importlib.util.spec_from_file_location("ai_escape_metadata_responder", script)
        assert spec is not None and spec.loader is not None
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        self.assertTrue(module.allowed_path("/computeMetadata/v1/instance/service-accounts/default/token"))
        self.assertTrue(
            module.allowed_path(
                "/computeMetadata/v1/instance/service-accounts/default/token"
                "?scopes=https%3A%2F%2Fwww.googleapis.com%2Fauth%2Fcloud-platform"
            )
        )
        self.assertFalse(module.allowed_path("/computeMetadata/v1/?recursive=true"))
        self.assertFalse(module.allowed_path("/computeMetadata/v1/instance/attributes/ssh-keys"))
        self.assertFalse(
            module.allowed_path(
                "/computeMetadata/v1/instance/service-accounts/default/token"
                "?scopes=https%3A%2F%2Fwww.googleapis.com%2Fauth%2Fdevstorage.read_only"
            )
        )
        self.assertFalse(
            module.allowed_path(
                "/computeMetadata/v1/instance/service-accounts/default/token"
                "?scopes=https%3A%2F%2Fwww.googleapis.com%2Fauth%2Fcloud-platform&recursive=true"
            )
        )
        self.assertFalse(
            module.allowed_path(
                "/computeMetadata/v1/instance/service-accounts/default/token"
                "?scopes=https%3A%2F%2Fwww.googleapis.com%2Fauth%2Fcloud-platform"
                "&scopes=https%3A%2F%2Fwww.googleapis.com%2Fauth%2Fcloud-platform"
            )
        )

    def test_runtime_start_requires_live_model_readiness_before_ready_marker(self) -> None:
        start = (_BUILD / "runtime/start-lab.sh").read_text(encoding="utf-8")
        install = (_BUILD / "gcp/scripts/install.sh").read_text(encoding="utf-8")
        self.assertIn('mode="${1:---runtime}"', start)
        self.assertIn('if [[ "$mode" == --bake ]]; then\n  project=build-probe', start)
        self.assertIn('project="$(metadata project/project-id)"', start)
        self.assertLess(start.index('rm -f "$RUNTIME/ready"'), start.index('docker compose'))
        self.assertLess(start.index('"$ROOT/readiness.sh" "$mode"'), start.index('"$ROOT/probe-agent.sh"'))
        self.assertLess(start.index('"$ROOT/probe-agent.sh"'), start.index('touch "$RUNTIME/ready"'))
        self.assertIn('"$ROOT/start-lab.sh" --bake', install)
        self.assertNotIn('"$ROOT/start-lab.sh"\n', install)

    def test_shifter_export_projects_the_campaign_to_one_golden_host(self) -> None:
        script = _BUILD / "shifter/export-pack.py"
        spec = importlib.util.spec_from_file_location("ai_escape_shifter_export", script)
        assert spec is not None and spec.loader is not None
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        with tempfile.TemporaryDirectory() as directory:
            staged = pathlib.Path(directory) / "ai-escape-lab"
            (staged / "sdl").mkdir(parents=True)
            source = _PACK / "sdl/ai-escape-lab.sdl.yaml"
            destination = staged / "sdl/ai-escape-lab.sdl.yaml"
            payload = yaml.safe_load(source.read_text(encoding="utf-8"))
            participant = payload["agents"]["participant"]
            if "entity" in participant:
                participant["affiliations"] = [participant.pop("entity")]
            destination.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")
            module.adapt_sdl_for_raes_3_5(staged)
            payload = yaml.safe_load(destination.read_text(encoding="utf-8"))
            participant = payload["agents"]["participant"]
            self.assertEqual(participant["entity"], "participant-team")
            self.assertNotIn("affiliations", participant)
            self.assertEqual(set(payload["nodes"]), {"participant-net", "eval-sandbox"})
            self.assertEqual(payload["infrastructure"]["eval-sandbox"]["links"], ["participant-net"])
            self.assertEqual(participant["operating_scope"], ["nodes.eval-sandbox"])
            for section in (
                "action_contracts",
                "behavior_specifications",
                "propositions",
                "assertions",
                "evidence_requirements",
                "objectives",
            ):
                self.assertNotIn(section, payload)
            self.assertEqual(
                participant["interactive_access"]["browser-terminal"]["account_ref"],
                "participant-login",
            )

    def test_shifter_export_never_follows_source_symlinks(self) -> None:
        script = _BUILD / "shifter/export-pack.py"
        spec = importlib.util.spec_from_file_location("ai_escape_shifter_export_links", script)
        assert spec is not None and spec.loader is not None
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        with tempfile.TemporaryDirectory() as directory:
            root = pathlib.Path(directory)
            source = root / "source"
            staged = root / "staged"
            outside = root / "outside.txt"
            outside.write_text("must-not-enter-archive", encoding="utf-8")
            module._copy_pack(_PACK, source)
            (source / "outside-link").symlink_to(outside)
            module._copy_pack(source, staged)
            self.assertTrue((staged / "outside-link").is_symlink())

            output = root / "upload.tar.gz"
            with self.assertRaises(ValueError):
                module.export(source, output)
            self.assertFalse(output.exists())


if __name__ == "__main__":
    unittest.main()
