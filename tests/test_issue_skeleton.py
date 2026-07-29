"""Tests for the environment-pack issue skeleton helper."""

from __future__ import annotations

import importlib.util
import os
import sys
import unittest
from unittest import mock

_HERE = os.path.dirname(os.path.abspath(__file__))
_SCRIPT = os.path.join(os.path.dirname(_HERE), "src", "raes_env_packs",
                       "issue_skeleton.py")


def _load_module():
    spec = importlib.util.spec_from_file_location("pack_issue_skeleton_undertest", _SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


SKELETON = _load_module()


def _issue(number: int, milestone: int, title: str):
    return {
        "number": number,
        "title": title,
        "milestone": {"number": milestone},
        "labels": [],
    }


class SkeletonTemplateTests(unittest.TestCase):
    def plan(self):
        return SKELETON.PackPlan(
            pack_id="example-pack",
            title="Example Pack",
            focus="A focused example scenario.",
            sources=("Source: https://example.invalid/source",),
            labels=("scenario:example-pack",),
            milestone_number=42,
        )

    def test_has_nine_standard_issue_templates(self):
        self.assertEqual(len(SKELETON.ISSUE_TEMPLATES), 9)
        self.assertEqual(
            [template.key for template in SKELETON.ISSUE_TEMPLATES],
            ["contract", "topology", "behavior", "flags", "profiles",
             "build", "rehearsal", "manual", "final"])

    def test_behavior_slice_uses_aces_participant_semantics(self):
        template = next(
            template for template in SKELETON.ISSUE_TEMPLATES
            if template.key == "behavior"
        )

        body = template.renderer(self.plan())

        self.assertIn("RAES participant behavior", body)
        self.assertIn("behavior_specifications", body)
        self.assertIn("action_contracts", body)
        self.assertNotIn("Pack-local oracle", body)

    def test_rendered_bodies_are_markdown_not_code_blocks(self):
        plan = self.plan()
        for template in SKELETON.ISSUE_TEMPLATES:
            with self.subTest(template=template.key):
                body = template.renderer(plan)
                self.assertTrue(body.startswith("## Goal\n"), body[:40])
                self.assertIn("## Child Issue Guidance", body)
                self.assertNotIn("\n    ##", body)

    def test_missing_templates_create_issues(self):
        ops = SKELETON.build_operations(
            self.plan(),
            existing_issues=[],
            available_labels={"area:content", "documentation", "scenario:example-pack"},
        )
        creates = [op for op in ops if op.action == "create_issue"]
        self.assertEqual(len(creates), 9)
        self.assertEqual(creates[0].title,
                         "example-pack: create scenario contract and pack skeleton")
        self.assertIn("scenario:example-pack", creates[0].labels)
        self.assertIn("documentation", creates[0].labels)
        self.assertNotIn("tier:raes", creates[0].labels)

    def test_existing_templates_are_skipped_by_default(self):
        plan = self.plan()
        existing = [
            _issue(100 + index, 42, SKELETON.issue_title(plan, template))
            for index, template in enumerate(SKELETON.ISSUE_TEMPLATES)
        ]
        ops = SKELETON.build_operations(plan, existing_issues=existing)
        self.assertEqual({op.action for op in ops}, {"skip_issue"})
        self.assertEqual(len(ops), 9)

    def test_legacy_oracle_issue_title_is_reused(self):
        plan = self.plan()
        existing = [
            _issue(
                102,
                42,
                "example-pack: define hidden path, oracle, and validation model",
            )
        ]

        operations = SKELETON.build_operations(plan, existing_issues=existing)
        behavior = next(
            operation for operation in operations
            if operation.title.endswith("specify participant attacker behavior in RAES")
        )

        self.assertEqual(behavior.action, "skip_issue")
        self.assertEqual(behavior.issue_number, 102)

    def test_refresh_existing_updates_existing_templates(self):
        plan = self.plan()
        existing = [
            _issue(100 + index, 42, SKELETON.issue_title(plan, template))
            for index, template in enumerate(SKELETON.ISSUE_TEMPLATES)
        ]
        ops = SKELETON.build_operations(
            plan, existing_issues=existing, refresh_existing=True)
        self.assertEqual({op.action for op in ops}, {"update_issue"})
        self.assertEqual(len(ops), 9)

    def test_can_plan_missing_milestone_creation(self):
        plan = self.plan()
        plan = SKELETON.PackPlan(
            pack_id=plan.pack_id,
            title=plan.title,
            focus=plan.focus,
            sources=plan.sources,
            labels=plan.labels,
            milestone_title="Environment pack: Example Pack",
        )
        ops = SKELETON.build_operations(plan, [], milestone_exists=False)
        self.assertEqual(ops[0].action, "create_milestone")
        self.assertEqual(len([op for op in ops if op.action == "create_issue"]), 9)


class RepoTargetTests(unittest.TestCase):
    """The catalog repository must be named explicitly (issue #194).

    The skeleton creates pack-implementation issues, which belong in a catalog
    repository. This tooling repo (``RAESystem/env-packs``) owns the pack
    format, not pack content, so it must never be a silent or explicit target.
    """

    def test_repo_has_no_argparse_default(self):
        args = SKELETON.parse_args(
            ["--pack-id", "example-pack", "--milestone-number", "1"])
        self.assertIsNone(args.repo)

    def test_missing_repo_selector_is_rejected(self):
        for missing in (None, ""):
            with self.subTest(missing=missing):
                with self.assertRaises(SystemExit):
                    SKELETON.validate_target_selector(missing)

    def test_malformed_repo_selectors_are_rejected(self):
        for bad in ("notaslug", "https://github.com/o/r", "owner/repo/extra",
                    "owner/repo?tab=issues", "owner /repo", "owner/re po",
                    "owner/", "/repo", "owner/repo\n"):
            with self.subTest(bad=bad):
                with self.assertRaises(SystemExit):
                    SKELETON.validate_target_selector(bad)

    def test_first_party_and_community_targets_pass(self):
        # Arbitrary catalogs — first-party, community, private — share one route.
        for target in ("example-org/first-party-packs", "some-org/community-packs",
                       "acme-internal/private-packs"):
            with self.subTest(target=target):
                self.assertEqual(
                    SKELETON.validate_target_selector(target), target)

    def test_format_tooling_repo_is_rejected_case_insensitively(self):
        for forbidden in ("RAESystem/env-packs", "raesystem/ENV-PACKS"):
            with self.subTest(forbidden=forbidden):
                with self.assertRaises(SystemExit):
                    SKELETON.validate_target_selector(forbidden)

    def test_ensure_not_tooling_repo_allows_catalogs(self):
        SKELETON.ensure_not_tooling_repo("some-org/ok")
        SKELETON.ensure_not_tooling_repo("example-org/first-party-packs")
        with self.assertRaises(SystemExit):
            SKELETON.ensure_not_tooling_repo("RAESystem/env-packs")

    def test_example_catalog_is_a_neutral_placeholder(self):
        # Canonical tooling must stay catalog-neutral (issue #194 codex class
        # finding): the only GitHub identity it embeds is this repo's own name
        # (to reject it). The catalog example fed to help and error text must be
        # an obvious placeholder, never a concrete downstream/first-party
        # catalog such as one under the RAESystem org.
        self.assertRegex(SKELETON.EXAMPLE_CATALOG,
                         r"^[A-Za-z0-9._-]+/[A-Za-z0-9._-]+$")
        self.assertNotIn("raesystem", SKELETON.EXAMPLE_CATALOG.lower())

    def test_main_rejects_locally_without_subprocess(self):
        base = ["--pack-id", "example-pack", "--milestone-number", "1"]
        with mock.patch.object(SKELETON.subprocess, "run") as run:
            for argv in (
                base,  # missing --repo
                base + ["--repo", "RAESystem/env-packs"],  # forbidden tooling repo
                base + ["--repo", "notaslug"],  # malformed
            ):
                with self.subTest(argv=argv):
                    with self.assertRaises(SystemExit):
                        SKELETON.main(argv)
            run.assert_not_called()

    def test_main_rejects_canonical_alias_to_tooling_repo(self):
        # gh resolves a redirected/renamed slug back to the tooling repo.
        resolved = mock.Mock(
            returncode=0,
            stdout='{"nameWithOwner": "RAESystem/env-packs"}',
            stderr="",
        )
        with mock.patch.object(SKELETON.subprocess, "run", return_value=resolved):
            with self.assertRaises(SystemExit):
                SKELETON.main(["--pack-id", "example-pack",
                               "--milestone-number", "1",
                               "--repo", "RAESystem/old-packs-alias"])
