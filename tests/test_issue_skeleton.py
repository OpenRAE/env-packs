"""Tests for the environment-pack issue skeleton helper."""

from __future__ import annotations

import importlib.util
import os
import sys
import unittest

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
