"""Static contract guard for the pack-distribution rehearsal workflow.

The real acceptance criterion — a signed release a clean consumer can install and
verify — can only be met by an actual run of ``pack-distribution.yml`` (a
registry service + a keyless Sigstore OIDC identity). The workflow *shape* that
produces it is guarded here so a reorder, an unpinned action, a dropped
permission, or a lost registry service fails CI. Reuses the repo's unittest +
PyYAML stack (issue #191, ADR 0037).
"""

from __future__ import annotations

import pathlib
import re
import unittest

import yaml

_ROOT = pathlib.Path(__file__).resolve().parents[1]
_WORKFLOW = _ROOT / ".github" / "workflows" / "pack-distribution.yml"

_SHA_RE = re.compile(r"^[0-9a-f]{40}$")
_COSIGN = "sigstore/cosign-installer@"
_ORAS = "oras-project/setup-oras@"


def _load() -> dict:
    return yaml.safe_load(_WORKFLOW.read_text(encoding="utf-8"))


def _triggers(data: dict) -> dict:
    # PyYAML parses the bare `on:` key as the boolean True (YAML 1.1).
    value = data.get("on", data.get(True))
    return value if isinstance(value, dict) else {}


class DistributionWorkflowContractTests(unittest.TestCase):
    def setUp(self) -> None:
        self.data = _load()
        self.job = self.data["jobs"]["rehearse"]
        self.steps = self.job["steps"]

    def _uses(self) -> list[str]:
        return [str(step["uses"]) for step in self.steps if "uses" in step]

    def test_manually_triggered_only(self) -> None:
        triggers = _triggers(self.data)
        self.assertIn("workflow_dispatch", triggers,
                      "the rehearsal must be a manually triggered integration run")

    def test_top_level_permissions_are_read_only(self) -> None:
        self.assertEqual(self.data.get("permissions"), "read-all")

    def test_job_keeps_oidc_and_stays_least_privilege(self) -> None:
        permissions = self.job.get("permissions", {})
        self.assertEqual(permissions.get("id-token"), "write",
                         "keyless Sigstore signing needs id-token: write")
        self.assertEqual(permissions.get("contents"), "read",
                         "a rehearsal reads the source; it must not request write")

    def test_registry_service_is_present(self) -> None:
        registry = self.job.get("services", {}).get("registry", {})
        self.assertTrue(str(registry.get("image", "")).startswith("registry:"),
                        "the ephemeral OCI registry:2 service must be declared")

    def test_signing_and_transport_tools_are_sha_pinned(self) -> None:
        for prefix, tool in ((_COSIGN, "cosign"), (_ORAS, "oras")):
            match = next((u for u in self._uses() if u.startswith(prefix)), None)
            self.assertIsNotNone(match, f"the workflow must install {tool}")
            ref = match.split("@", 1)[1].split()[0]
            self.assertRegex(ref, _SHA_RE, f"{tool} installer must be SHA-pinned: {match!r}")

    def test_every_action_is_sha_pinned(self) -> None:
        for uses in self._uses():
            ref = uses.split("@", 1)[1].split()[0]
            self.assertRegex(ref, _SHA_RE, f"action must be SHA-pinned: {uses!r}")

    def test_pip_installs_are_pinned(self) -> None:
        runs = "\n".join(str(step.get("run", "")) for step in self.steps)
        for line in runs.splitlines():
            stripped = line.strip()
            if "pip install" in stripped:
                self.assertTrue(
                    "--require-hashes" in stripped or "--no-deps -e" in stripped,
                    f"pip install must be pinned (require-hashes or --no-deps -e): {stripped!r}")

    def test_rehearsal_runs_after_tools_are_installed(self) -> None:
        def index(predicate) -> int:
            for i, step in enumerate(self.steps):
                if predicate(step):
                    return i
            return -1

        cosign = index(lambda s: str(s.get("uses", "")).startswith(_COSIGN))
        oras = index(lambda s: str(s.get("uses", "")).startswith(_ORAS))
        rehearsal = index(lambda s: "distribution_rehearsal.py" in str(s.get("run", "")))
        for name, idx in (("cosign", cosign), ("oras", oras), ("rehearsal", rehearsal)):
            self.assertGreaterEqual(idx, 0, f"missing the {name} step")
        self.assertLess(cosign, rehearsal, "cosign must be installed before the rehearsal")
        self.assertLess(oras, rehearsal, "oras must be installed before the rehearsal")


if __name__ == "__main__":
    unittest.main()
