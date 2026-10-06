"""Contract tests for the AI Escape Lab environment pack."""

from __future__ import annotations

import hashlib
import json
import os
import pathlib
import subprocess
import tarfile
import tempfile
import unittest

import yaml
from raes import parse_sdl_file

from raes_env_packs import validate_pack


_ROOT = pathlib.Path(__file__).resolve().parents[1]
_PACK = _ROOT / "packs" / "ai-escape-lab"
_UPSTREAM_REVISION = "fcb25ec9874b0676706b9aca650f22efc90f711e"
_SERVICES = {
    "eval-sandbox",
    "registry-cache",
    "cybergym",
    "request-capture",
    "pastebin",
    "hf-api",
    "dataset-worker",
    "k8s-api",
    "internal-db",
    "mesh-gateway",
    "source-control",
}
_NETWORKS = {"eval-net", "internet-net", "hf-prod-net", "hf-cluster-net", "corp-net"}
_MODEL_NETWORK = "model-egress-net"


def _yaml(relative: str) -> dict:
    return yaml.safe_load((_PACK / relative).read_text(encoding="utf-8"))


class AiEscapeLabPackTests(unittest.TestCase):
    def test_pack_and_sdl_are_valid(self) -> None:
        result = validate_pack(_PACK)
        self.assertTrue(result.ok, result.errors)
        scenario = parse_sdl_file(_PACK / "sdl" / "ai-escape-lab.sdl.yaml")
        self.assertEqual(scenario.name, "ai-escape-lab")

        raw = _yaml("sdl/ai-escape-lab.sdl.yaml")
        host = raw["nodes"]["eval-sandbox"]
        self.assertEqual(host["source"], "ai-escape-lab/gce")
        self.assertEqual(host["roles"]["participant"]["username"], "participant")
        self.assertNotIn("features", host)
        self.assertNotIn("features", raw)
        access = raw["agents"]["participant"]["interactive_access"]["browser-terminal"]
        self.assertEqual(
            access,
            {
                "target_ref": "eval-sandbox",
                "channel": "ssh",
                "account_ref": "participant-login",
            },
        )
        self.assertEqual(raw["accounts"]["participant-login"]["username"], "participant")
        compute = {name for name, node in raw["nodes"].items() if node["type"] == "compute"}
        self.assertEqual(compute, _SERVICES)
        self.assertEqual(_NETWORKS | {_MODEL_NETWORK, "participant-net"}, set(raw["nodes"]) - compute)
        self.assertEqual(set(raw["objectives"]), {f"recover-flag-{number}" for number in range(1, 8)})
        behavior = raw["behavior_specifications"]["participant-agent-cohacking"]
        self.assertEqual(behavior["behavior_mode"], "human-supervised")
        self.assertEqual(set(behavior["action_contract_refs"]), set(raw["action_contracts"]))

    def test_upstream_source_is_pinned_and_safe_to_extract(self) -> None:
        provenance = _yaml("docs/provenance-ledger.yaml")
        upstream = provenance["sources"][0]
        self.assertEqual(upstream["ref"], _UPSTREAM_REVISION)
        lock = _yaml("assets/upstream-source.lock.yaml")
        self.assertEqual(lock["revision"], _UPSTREAM_REVISION)
        archive = _PACK / lock["path"]
        self.assertEqual(hashlib.sha256(archive.read_bytes()).hexdigest(), lock["sha256"])
        self.assertTrue((_PACK / "assets" / "upstream-LICENSE").is_file())

        with tarfile.open(archive, "r:gz") as bundle:
            names = set()
            for member in bundle.getmembers():
                path = pathlib.PurePosixPath(member.name)
                self.assertFalse(path.is_absolute())
                self.assertNotIn("..", path.parts)
                self.assertFalse(member.issym() or member.islnk())
                names.add(path.as_posix())
        self.assertIn("ai-escape-room/docker-compose.yml", names)
        self.assertIn("ai-escape-room/LICENSE", names)

    def test_runtime_compose_is_an_offline_isolated_closure(self) -> None:
        compose = _yaml("build/runtime/docker-compose.yml")
        self.assertEqual(set(compose["services"]), _SERVICES)
        self.assertEqual(set(compose["networks"]), _NETWORKS | {_MODEL_NETWORK})
        self.assertTrue(all(compose["networks"][name].get("internal") is True for name in _NETWORKS))
        self.assertFalse(compose["networks"][_MODEL_NETWORK].get("internal", False))

        for name, service in compose["services"].items():
            with self.subTest(service=name):
                self.assertNotIn("build", service)
                self.assertRegex(service["image"], r"^ai-escape-lab/[a-z0-9-]+:fcb25ec9874b$")
                self.assertNotIn("privileged", service)
                self.assertNotEqual(service.get("network_mode"), "host")
                self.assertNotEqual(service.get("pid"), "host")
                self.assertNotEqual(service.get("ipc"), "host")
                mounts = service.get("volumes", [])
                self.assertFalse(any("/var/run/docker.sock" in str(mount) for mount in mounts))

        sandbox = compose["services"]["eval-sandbox"]
        self.assertEqual(sandbox["networks"], ["eval-net", _MODEL_NETWORK])
        self.assertNotIn("volumes", sandbox)
        self.assertIn("ALL", sandbox["cap_drop"])
        self.assertIn("no-new-privileges:true", sandbox["security_opt"])

        database = compose["services"]["internal-db"]
        self.assertNotIn("MONGO_INITDB_ROOT_PASSWORD", database["environment"])
        self.assertEqual(
            database["environment"]["MONGO_INITDB_ROOT_PASSWORD_FILE"],
            "/run/secrets/mongo-password",
        )
        self.assertNotIn("environment", compose["services"]["mesh-gateway"])

        start = (_PACK / "build" / "runtime" / "start-lab.sh").read_text(encoding="utf-8")
        self.assertIn("--pull never", start)
        self.assertIn("--no-build", start)
        self.assertIn('model_region="${AI_ESCAPE_MODEL_REGION:-us-east5}"', start)
        self.assertNotIn('region="${zone%-*}"', start)

        firewall = (_PACK / "build" / "gcp" / "scripts" / "firewall.sh").read_text(encoding="utf-8")
        self.assertIn('-s "$MODEL_SUBNET" -d "$GOOGLE_PRIVATE" -p tcp --dport 443 -j RETURN', firewall)
        self.assertIn('DOCKER-USER 1 -s "$MODEL_SUBNET" -j DROP', firewall)
        self.assertIn('INPUT -s "$subnet" -j REJECT', firewall)

    def test_challenges_cover_seven_flags_and_twelve_hints(self) -> None:
        source = _yaml("challenges/challenges.yaml")
        challenges = source["challenges"]
        placements = _yaml("flags/placement.yaml")["flags"]
        self.assertEqual(len(challenges), 7)
        self.assertEqual([item["flag_id"] for item in challenges], [f"flag-{number}" for number in range(1, 8)])
        self.assertEqual([item["flag_id"] for item in placements], [f"flag-{number}" for number in range(1, 8)])
        self.assertEqual(len({item["value"] for item in placements}), 7)
        self.assertEqual(sum(len(item["hints"]) for item in challenges), 12)

        with tempfile.TemporaryDirectory() as directory:
            output = pathlib.Path(directory) / "ctfd.json"
            subprocess.run(
                [
                    "python3",
                    str(_PACK / "ctfd" / "export_shifter_challenge_pack.py"),
                    "--output",
                    str(output),
                ],
                cwd=_PACK,
                check=True,
                capture_output=True,
                text=True,
            )
            exported = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual(exported["format"], "ctfd")
            self.assertEqual(len(exported["challenges"]), 7)
            self.assertEqual([len(item["flags"]) for item in exported["challenges"]], [1] * 7)
            self.assertEqual(sum(len(item["hints"]) for item in exported["challenges"]), 12)
            self.assertEqual(os.stat(output).st_mode & 0o777, 0o600)

    def test_readiness_proves_the_participant_surface_and_full_chain(self) -> None:
        readiness = json.loads((_PACK / "build" / "runtime" / "readiness.json").read_text(encoding="utf-8"))
        self.assertEqual(set(readiness["required_containers"]), _SERVICES)
        self.assertEqual(readiness["participant_container"], "eval-sandbox")
        self.assertEqual(readiness["flag_count"], 7)
        self.assertEqual(readiness["hint_count"], 12)
        probes = {probe["id"] for probe in readiness["probes"]}
        self.assertLessEqual(
            {"compose-health", "participant-shell", "claude-client", "challenge-path"},
            probes,
        )


if __name__ == "__main__":
    unittest.main()
