"""First-party TechVault pack contract (issue #234).

The checks in this module deliberately preserve the complete upstream SDL while
moving its repository-local content dependencies behind immutable pack artifact
identities.  They are regression guards for the migration, not a second source
of RAES scenario semantics.
"""

from __future__ import annotations

import hashlib
import hmac
import io
import json
import os
import pathlib
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

_PACK_ARTIFACT_CONTENT_IDS = frozenset(
    {
        "misp-suricata-sync-pyproject",
        "misp-suricata-sync-readme",
        "misp-suricata-sync-hatch-build",
        "misp-suricata-sync-src",
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
            "nodes": 37,
            "infrastructure": 37,
            "persistent_volumes": 23,
            "features": 2,
            "vulnerabilities": 14,
            "propositions": 1,
            "assertions": 1,
            "observation_boundaries": 1,
            "evidence_requirements": 1,
            "identity_domains": 1,
            "relationships": 1,
            "accounts": 4,
        }
        for section, expected in expected_counts.items():
            with self.subTest(section=section):
                self.assertEqual(len(sdl[section]), expected)

        # This runtime-authority declaration is intentionally not a content
        # acquisition path and must survive the pack migration.
        self.assertIn("/var/run/docker.sock", _SDL.read_text(encoding="utf-8"))

    def test_all_original_content_obligations_are_accounted_for(self) -> None:
        content = _load_sdl()["content"]
        self.assertLessEqual(_PACK_ARTIFACT_CONTENT_IDS, set(content))
        self.assertTrue(_GENERATED_SSH_CONTENT_IDS.isdisjoint(content))
        inline = {name for name, item in content.items() if "text" in item}
        sourced = {name for name, item in content.items() if "source" in item}
        # ADR-088 service-materialized content declares desired service state and
        # carries neither an inline `text` body nor a `source` package.
        materialized = {
            name
            for name, item in content.items()
            if "service_materialization" in item
        }
        self.assertEqual(inline & sourced, set())
        self.assertEqual(inline & materialized, set())
        self.assertEqual(sourced & materialized, set())
        self.assertEqual(inline | sourced | materialized, set(content))
        self.assertEqual(len(inline), 25)
        self.assertEqual(sourced, _PACK_ARTIFACT_CONTENT_IDS)
        self.assertEqual(materialized, {"cortex-job-index-schema"})
        self.assertEqual(len(content) + len(_GENERATED_SSH_CONTENT_IDS), 52)

    def test_cortex_job_index_schema_is_adr088_initial_service_state(self) -> None:
        sdl = _load_sdl()

        # The one-shot init node, its inline script, and its topology row are gone.
        self.assertNotIn("cortex-index-init", sdl["nodes"])
        self.assertNotIn("cortex-index-init", sdl["infrastructure"])
        self.assertNotIn("cortex-index-init-script", sdl["content"])

        entry = sdl["content"]["cortex-job-index-schema"]
        self.assertEqual(entry["type"], "dataset")
        self.assertEqual(entry["target"], "thehive-es")
        # Materialization-only: no inline body, source package, or item list.
        self.assertNotIn("text", entry)
        self.assertNotIn("source", entry)
        self.assertNotIn("items", entry)

        materialization = entry["service_materialization"]
        self.assertEqual(
            materialization["interface_profile"], "service-search-index-schema"
        )
        self.assertEqual(materialization["profile_version"], "1")
        self.assertEqual(
            materialization["target_service_ref"],
            "nodes.thehive-es.services.elasticsearch",
        )
        requirements = materialization["requirements"]
        self.assertEqual(requirements["operation"], "ensure-search-index-field-schema")
        self.assertEqual(requirements["conflict_policy"], "reject-unowned-collision")
        self.assertEqual(
            requirements["readback"], "canonical-portable-field-schema-digest"
        )
        self.assertEqual(
            requirements["field_semantics"],
            {
                "key": "exact-token",
                "status": "exact-token",
                "relations": "exact-token",
            },
        )

        # The readback scaffolding cross-refs resolve to a postcondition assertion
        # over an observed-state proposition whose subject is this content, plus a
        # bound evidence requirement and an observation boundary that exposes it.
        (assertion_ref,) = materialization["readback_assertion_refs"]
        (evidence_ref,) = materialization["evidence_requirement_refs"]
        (boundary_ref,) = materialization["observation_boundary_refs"]

        assertion = sdl["assertions"][assertion_ref]
        self.assertEqual(assertion["role"], "postcondition")
        proposition = sdl["propositions"][assertion["proposition"]]
        self.assertEqual(proposition["basis"], "observed_state")
        self.assertIn("content.cortex-job-index-schema", proposition["subjects"])
        self.assertIn(evidence_ref, proposition["evidence_requirements"])

        evidence = sdl["evidence_requirements"][evidence_ref]
        self.assertIn("content.cortex-job-index-schema", evidence["source_refs"])

        boundary = sdl["observation_boundaries"][boundary_ref]
        self.assertIn("content.cortex-job-index-schema", boundary["observable_refs"])

        # ADR-088 forbids leaking the backend index name or vendor ES literals into
        # the portable declaration; only portable field semantics belong here.
        declaration = yaml.safe_dump(entry)
        for forbidden in ("cortex_6", "keyword", "_mapping", "http://", "https://"):
            self.assertNotIn(forbidden, declaration)

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
        self.assertEqual(len(generated), 7)

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
