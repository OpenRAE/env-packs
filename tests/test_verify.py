"""Tests for consumer verification and its five evidence states (ADR 0037)."""

from __future__ import annotations

import io
import json
import os
import tempfile
import unittest

from raes_env_packs import release, verify

_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO = os.path.dirname(_HERE)
_TECHVAULT = os.path.join(_REPO, "packs", "techvault")


_STATE: dict = {}


def setUpModule() -> None:
    """Publish TechVault once for the whole module (a publish is ~14s)."""

    _STATE["out"] = tempfile.TemporaryDirectory()
    metadata, failures = release.build_release(_TECHVAULT, _STATE["out"].name, publish=True)
    assert not failures, failures
    _STATE["release_dir"] = os.path.join(_STATE["out"].name, "techvault-0.1.0")
    _STATE["evidence"] = verify.load_release_evidence(_STATE["release_dir"])


def tearDownModule() -> None:
    _STATE["out"].cleanup()


class _PublishedFixture(unittest.TestCase):
    """Expose the module-level published TechVault release + evidence."""

    @property
    def release_dir(self) -> str:
        return _STATE["release_dir"]

    @property
    def profile(self):
        return _STATE["evidence"][0]

    @property
    def sbom(self):
        return _STATE["evidence"][1]

    @property
    def provenance(self):
        return _STATE["evidence"][2]

    def _verify(self, **overrides):
        kwargs = {
            "release_profile": self.profile,
            "sbom_document": self.sbom,
            "provenance_document": self.provenance,
        }
        kwargs.update(overrides)
        return verify.verify_pack_release(_TECHVAULT, **kwargs)


class HappyPathTests(_PublishedFixture):
    def test_core_gates_verify_and_release_is_accepted(self) -> None:
        result = self._verify()
        states = {e.gate: e.state for e in result.evidence}
        self.assertEqual(states[verify.GATE_STATIC], verify.STATE_VERIFIED)
        self.assertEqual(states[verify.GATE_CONTENT_BINDING], verify.STATE_VERIFIED)
        self.assertEqual(states[verify.GATE_SBOM], verify.STATE_VERIFIED)
        self.assertEqual(states[verify.GATE_PROVENANCE], verify.STATE_VERIFIED)
        self.assertTrue(result.accepted)

    def test_signature_is_unavailable_without_a_verifier(self) -> None:
        result = self._verify()
        states = {e.gate: e.state for e in result.evidence}
        self.assertEqual(states[verify.GATE_RELEASE_SIGNATURE], verify.STATE_UNAVAILABLE)
        self.assertFalse(result.authenticated)

    def test_injected_signature_verifier_authenticates(self) -> None:
        result = self._verify(signature_verifier=lambda subject, prov: subject == self.profile["release"]["source_set"]["set_digest"])
        self.assertTrue(result.authenticated)
        self.assertTrue(result.accepted)

    def test_lockless_pack_reports_lock_absent_not_failed(self) -> None:
        states = {e.gate: e.state for e in self._verify().evidence}
        self.assertEqual(states[verify.GATE_LOCK], verify.STATE_ABSENT)


class TamperTests(_PublishedFixture):
    def test_tampered_sbom_bytes_fail_the_sbom_gate(self) -> None:
        tampered = json.loads(json.dumps(self.sbom))
        tampered["components"].append({"type": "library", "bom-ref": "sneaked-in", "name": "evil"})
        result = self._verify(sbom_document=tampered)
        states = {e.gate: e.state for e in result.evidence}
        self.assertEqual(states[verify.GATE_SBOM], verify.STATE_FAILED)
        self.assertFalse(result.accepted)

    def test_tampered_provenance_bytes_fail_the_provenance_gate(self) -> None:
        tampered = json.loads(json.dumps(self.provenance))
        tampered["predicate"]["builder"]["id"] = "attacker"
        states = {e.gate: e.state for e in self._verify(provenance_document=tampered).evidence}
        self.assertEqual(states[verify.GATE_PROVENANCE], verify.STATE_FAILED)

    def test_missing_evidence_is_absent_and_not_accepted(self) -> None:
        # A local projection carries no evidence block.
        with tempfile.TemporaryDirectory() as out:
            release.build_release(_TECHVAULT, out)  # publish=False
            profile, sbom_doc, prov_doc = verify.load_release_evidence(
                os.path.join(out, "techvault-0.1.0"))
            result = verify.verify_pack_release(
                _TECHVAULT, release_profile=profile,
                sbom_document=sbom_doc, provenance_document=prov_doc)
        states = {e.gate: e.state for e in result.evidence}
        self.assertEqual(states[verify.GATE_SBOM], verify.STATE_ABSENT)
        self.assertEqual(states[verify.GATE_PROVENANCE], verify.STATE_ABSENT)
        self.assertFalse(result.accepted)


class NoContentIdentityTests(unittest.TestCase):
    def test_pack_without_content_identity_fails_binding(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            pack = os.path.join(tmp, "bare")
            os.makedirs(pack)
            with open(os.path.join(pack, "pack.yaml"), "w", encoding="utf-8") as fh:
                fh.write("name: bare\nversion: 0.1.0\n")
            result = verify.verify_pack_release(pack, release_profile=None)
        states = {e.gate: e.state for e in result.evidence}
        self.assertEqual(states[verify.GATE_CONTENT_BINDING], verify.STATE_FAILED)
        self.assertIsNone(result.subject)
        self.assertFalse(result.accepted)


class CliTests(_PublishedFixture):
    def _run(self, argv):
        out, err = io.StringIO(), io.StringIO()
        code = verify.main(argv, stdout=out, stderr=err)
        return code, out.getvalue(), err.getvalue()

    def test_cli_accepts_a_valid_release(self) -> None:
        code, text, _ = self._run(["--pack", _TECHVAULT, "--release", self.release_dir])
        self.assertEqual(code, verify.EXIT_OK)
        self.assertIn("ACCEPTED", text)

    def test_cli_json_envelope(self) -> None:
        code, text, _ = self._run(["--pack", _TECHVAULT, "--release", self.release_dir, "--json"])
        document = json.loads(text)
        self.assertEqual(document["version"], "raes-pack-verify/v1")
        self.assertTrue(document["content_accepted"])
        self.assertEqual(code, verify.EXIT_OK)

    def test_cli_require_signature_rejects_unauthenticated(self) -> None:
        code, text, _ = self._run(
            ["--pack", _TECHVAULT, "--release", self.release_dir, "--require-signature"])
        self.assertEqual(code, verify.EXIT_BLOCKING)
        self.assertIn("REJECTED", text)


if __name__ == "__main__":
    unittest.main()
