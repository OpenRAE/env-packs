"""Tests for proposal-first pack distribution (ADR 0037, ASP-0004)."""

from __future__ import annotations

import os
import tempfile
import unittest

from raes_env_packs import distribution as dist
from raes_env_packs import release

_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO = os.path.dirname(_HERE)
_TECHVAULT = os.path.join(_REPO, "packs", "techvault")


def _read_set_digest(evidence_dir: str) -> str:
    import yaml
    with open(os.path.join(evidence_dir, "release.yaml"), encoding="utf-8") as fh:
        profile = yaml.safe_load(fh)
    return profile["release"]["source_set"]["set_digest"]


_STATE: dict = {}


def setUpModule() -> None:
    """Publish TechVault once for the whole module (a publish is ~14s)."""

    _STATE["out"] = tempfile.TemporaryDirectory()
    _meta, failures = release.build_release(_TECHVAULT, _STATE["out"].name, publish=True)
    assert not failures, failures
    _STATE["evidence"] = os.path.join(_STATE["out"].name, "techvault-0.1.0")


def tearDownModule() -> None:
    _STATE["out"].cleanup()


class _Fixture(unittest.TestCase):
    """Expose the module-level published TechVault release evidence directory."""

    @property
    def evidence(self) -> str:
        return _STATE["evidence"]


class ReadOnlyPlanTests(_Fixture):
    def test_verify_plan_is_read_only_and_applicable(self) -> None:
        plan = dist.plan_verify(_TECHVAULT, self.evidence)
        self.assertEqual(plan.operation, "verify")
        self.assertEqual(plan.effects, ())
        self.assertTrue(plan.applicable)

    def test_lock_plan_surfaces_the_reproducible_subject(self) -> None:
        plan = dist.plan_lock(_TECHVAULT, self.evidence)
        self.assertEqual(plan.effects, ())
        self.assertRegex(plan.resolved["subject"], r"^sha256:[0-9a-f]{64}$")
        self.assertIn("lock_digest", plan.resolved)

    def test_publish_plan_classifies_signing_and_registry_effects(self) -> None:
        selector = dist.Selector(repository="ghcr.io/openrae/env-packs/techvault", reference="0.1.0")
        plan = dist.plan_publish(self.evidence, selector=selector)
        kinds = {effect.kind for effect in plan.effects}
        self.assertIn(dist.EFFECT_SIGNING, kinds)
        self.assertIn(dist.EFFECT_REGISTRY_WRITE, kinds)
        self.assertIn(dist.EFFECT_NETWORK, kinds)
        self.assertIn(dist.EFFECT_CREDENTIAL, kinds)


class InstallTests(_Fixture):
    def test_install_plan_verifies_and_classifies_the_write(self) -> None:
        with tempfile.TemporaryDirectory() as root:
            target = os.path.join(root, "techvault")
            plan = dist.plan_install(_TECHVAULT, self.evidence, target)
            self.assertTrue(plan.applicable)
            self.assertEqual([e.kind for e in plan.effects], [dist.EFFECT_FILESYSTEM_WRITE])
            self.assertTrue(plan.verification.accepted)

    def test_apply_requires_authorization(self) -> None:
        with tempfile.TemporaryDirectory() as root:
            target = os.path.join(root, "techvault")
            plan = dist.plan_install(_TECHVAULT, self.evidence, target)
            policy = dist.PromotionPolicy(require_signature=False)
            with self.assertRaises(dist.DistributionError):
                dist.apply_install(plan, _TECHVAULT, self.evidence, target,
                                   authorized=False, policy=policy)
            self.assertFalse(os.path.exists(target))

    def test_apply_installs_and_writes_a_receipt_beside_the_pack(self) -> None:
        with tempfile.TemporaryDirectory() as root:
            target = os.path.join(root, "techvault")
            plan = dist.plan_install(_TECHVAULT, self.evidence, target)
            receipt = dist.apply_install(plan, _TECHVAULT, self.evidence, target,
                                         authorized=True,
                                         policy=dist.PromotionPolicy(require_signature=False))
            self.assertTrue(os.path.isfile(os.path.join(target, "pack.yaml")))
            self.assertEqual(receipt["schema_version"], "environment-pack-install-receipt/v1")
            self.assertEqual(dist.read_receipt(target)["subject"]["domain"],
                             dist.DIGEST_DOMAIN_SET)

    def test_apply_fails_closed_on_unauthenticated_release(self) -> None:
        # A published release with no signature verifier is `unavailable`, not
        # verified; promotion must refuse by default (F3).
        with tempfile.TemporaryDirectory() as root:
            target = os.path.join(root, "techvault")
            plan = dist.plan_install(_TECHVAULT, self.evidence, target)
            with self.assertRaises(dist.DistributionError):
                dist.apply_install(plan, _TECHVAULT, self.evidence, target, authorized=True)
            self.assertFalse(os.path.exists(target))

    def test_apply_accepts_a_verified_signature(self) -> None:
        set_digest = _read_set_digest(self.evidence)

        def verifier(subject: str, _prov: object) -> bool:
            return subject == set_digest

        with tempfile.TemporaryDirectory() as root:
            target = os.path.join(root, "techvault")
            plan = dist.plan_install(_TECHVAULT, self.evidence, target,
                                     signature_verifier=verifier)
            self.assertTrue(plan.verification.authenticated)
            dist.apply_install(plan, _TECHVAULT, self.evidence, target,
                               authorized=True,
                               policy=dist.PromotionPolicy(signature_verifier=verifier))
            self.assertTrue(os.path.isfile(os.path.join(target, "pack.yaml")))

    def test_apply_refuses_a_non_install_plan(self) -> None:
        with tempfile.TemporaryDirectory() as root:
            target = os.path.join(root, "techvault")
            verify_plan = dist.plan_verify(_TECHVAULT, self.evidence)
            policy = dist.PromotionPolicy(require_signature=False)
            with self.assertRaises(dist.DistributionError):
                dist.apply_install(verify_plan, _TECHVAULT, self.evidence, target,
                                   authorized=True, policy=policy)

    def test_apply_refuses_a_target_other_than_the_planned_one(self) -> None:
        with tempfile.TemporaryDirectory() as root:
            planned = os.path.join(root, "techvault")
            plan = dist.plan_install(_TECHVAULT, self.evidence, planned)
            elsewhere = os.path.join(root, "elsewhere", "techvault")
            os.makedirs(os.path.dirname(elsewhere))
            policy = dist.PromotionPolicy(require_signature=False)
            with self.assertRaises(dist.DistributionError):
                dist.apply_install(plan, _TECHVAULT, self.evidence, elsewhere,
                                   authorized=True, policy=policy)

    def test_update_replaces_atomically_over_an_existing_target(self) -> None:
        with tempfile.TemporaryDirectory() as root:
            target = os.path.join(root, "techvault")
            first = dist.plan_install(_TECHVAULT, self.evidence, target)
            dist.apply_install(first, _TECHVAULT, self.evidence, target,
                               authorized=True,
                               policy=dist.PromotionPolicy(require_signature=False))
            update = dist.plan_update(target, _TECHVAULT, self.evidence)
            categories = {c.category for c in update.changes}
            self.assertIn(dist.CHANGE_VERSION, categories)
            dist.apply_install(update, _TECHVAULT, self.evidence, target,
                               authorized=True,
                               policy=dist.PromotionPolicy(require_signature=False))
            self.assertTrue(os.path.isfile(os.path.join(target, "pack.yaml")))


class ArchiveRouteTests(_Fixture):
    def test_install_via_deterministic_archive_route(self) -> None:
        with tempfile.TemporaryDirectory() as root:
            archive = os.path.join(root, "techvault.tar.gz")
            digest = dist.export_pack_archive(_TECHVAULT, archive)
            selector = dist.Selector(
                repository="local", reference=archive,
                digest_domain=dist.DIGEST_DOMAIN_ARCHIVE)
            transport = dist.ArchiveTransport()
            target = os.path.join(root, "techvault")
            plan = dist.plan_install(
                _TECHVAULT, self.evidence, target,
                selector=selector, transport=transport)
            self.assertEqual(plan.resolved["transport_digest"], digest)
            self.assertIn(dist.EFFECT_NETWORK, {e.kind for e in plan.effects})
            self.assertTrue(plan.applicable)
            receipt = dist.apply_install(
                plan, _TECHVAULT, self.evidence, target,
                authorized=True,
                policy=dist.PromotionPolicy(selector=selector, transport=transport,
                                            require_signature=False))
            self.assertEqual(receipt["transport"]["digest"], digest)
            self.assertEqual(receipt["transport"]["domain"], dist.DIGEST_DOMAIN_ARCHIVE)


class RenderTests(_Fixture):
    def test_plan_renders_json_and_human(self) -> None:
        import json
        plan = dist.plan_verify(_TECHVAULT, self.evidence)
        document = json.loads(plan.render_json())
        self.assertEqual(document["version"], "raes-pack-dist/v1")
        self.assertEqual(document["operation"], "verify")
        self.assertIn("APPLICABLE", plan.render_human())


class CliTests(_Fixture):
    def _run(self, argv):
        import io
        out, err = io.StringIO(), io.StringIO()
        code = dist.main(argv, stdout=out, stderr=err)
        return code, out.getvalue(), err.getvalue()

    def test_verify_cli(self) -> None:
        code, text, _ = self._run(["verify", "--pack", _TECHVAULT, "--release", self.evidence])
        self.assertEqual(code, dist.EXIT_OK)
        self.assertIn("APPLICABLE", text)

    def test_install_plan_without_apply_writes_nothing(self) -> None:
        with tempfile.TemporaryDirectory() as root:
            target = os.path.join(root, "techvault")
            code, _text, _ = self._run(
                ["install", "--pack", _TECHVAULT, "--release", self.evidence, "--target", target])
            self.assertEqual(code, dist.EXIT_OK)
            self.assertFalse(os.path.exists(target))

    def test_install_apply_writes_the_target(self) -> None:
        with tempfile.TemporaryDirectory() as root:
            target = os.path.join(root, "techvault")
            code, _text, _ = self._run(
                ["install", "--pack", _TECHVAULT, "--release", self.evidence,
                 "--target", target, "--apply", "--allow-unsigned", "--json"])
            self.assertEqual(code, dist.EXIT_OK)
            self.assertTrue(os.path.isfile(os.path.join(target, "pack.yaml")))

    def test_publish_cli_shows_the_plan(self) -> None:
        code, text, _ = self._run(
            ["publish", "--release", self.evidence,
             "--repository", "ghcr.io/openrae/env-packs/techvault", "--reference", "0.1.0"])
        self.assertEqual(code, dist.EXIT_OK)
        self.assertIn("signing", text)


if __name__ == "__main__":
    unittest.main()
