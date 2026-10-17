"""The pinned RAES enforces purpose-specific reference eligibility (#478).

RAES 7.0.0 (OpenRAE/rae#1446) narrows what an objective subject, an action
target, an effect target, shared state, and an authority scope can name. This
repository does not restate those rules. These tests parse the AI Escape Lab
SDL through RAES, change one reference at a time, and check that the pinned
RAES admits an eligible declaration and refuses an ineligible one.
"""

from __future__ import annotations

import pathlib
import unittest

import yaml
from raes import SDLError, parse_sdl


_SDL = (
    pathlib.Path(__file__).resolve().parents[1]
    / "packs/ai-escape-lab/sdl/ai-escape-lab.sdl.yaml"
)
_CONTRACT = "relay-through-registry"
_NODE = "nodes.registry-cache"
_PROPOSITION = "propositions.flag-1-accepted"
_ASSERTION = "assertions.flag-1-accepted"
_AGENT = "agents.participant"
_ACTION_CONTRACT = f"action_contracts.{_CONTRACT}"


def _document() -> dict:
    return yaml.safe_load(_SDL.read_text(encoding="utf-8"))


def _parse(document: dict) -> object:
    return parse_sdl(
        yaml.safe_dump(document, sort_keys=False), migration_policy="accept"
    )


def _with_interaction(target: str, shared_state: str) -> dict:
    document = _document()
    document["action_contracts"][_CONTRACT]["interactions"] = [
        {
            "interaction_class": "contention",
            "target": target,
            "rationale": "Participants contend for the package cache relay.",
            "shared_state_refs": [shared_state],
        }
    ]
    return document


def _with_objective_subject(subject: str) -> dict:
    document = _document()
    document["objectives"]["recover-flag-1"]["targets"] = [subject]
    return document


def _with_effect_target(target: str) -> dict:
    document = _document()
    document["action_contracts"][_CONTRACT]["effects"][0]["target_refs"] = [target]
    return document


def _with_authority_scope(scope: str) -> dict:
    document = _document()
    specification = document["behavior_specifications"]["participant-agent-cohacking"]
    specification["authority_scope_refs"] = [scope]
    return document


class ReferenceEligibilityTests(unittest.TestCase):
    def assert_refused(self, document: dict, reference: str, purpose: str) -> None:
        with self.assertRaises(SDLError) as raised:
            _parse(document)
        message = str(raised.exception)
        self.assertIn(f"eligible as {purpose}", message)
        self.assertIn(f"it names {reference}", message)

    def test_authored_pack_references_are_eligible(self) -> None:
        document = _document()
        self.assertNotIn("interactions", document["action_contracts"][_CONTRACT])
        scenario = _parse(document)
        self.assertEqual(scenario.objectives["recover-flag-1"].targets, ["registry-cache"])

    def test_objective_subject_names_a_resource_not_an_action_contract(self) -> None:
        _parse(_with_objective_subject(_NODE))
        self.assert_refused(
            _with_objective_subject(_ACTION_CONTRACT),
            _ACTION_CONTRACT,
            "an objective subject",
        )

    def test_effect_target_names_a_resource_not_an_assertion(self) -> None:
        _parse(_with_effect_target(_NODE))
        self.assert_refused(_with_effect_target(_ASSERTION), _ASSERTION, "an action target")

    def test_authority_scope_names_a_resource_not_a_proposition(self) -> None:
        _parse(_with_authority_scope(_NODE))
        self.assert_refused(
            _with_authority_scope(_PROPOSITION), _PROPOSITION, "an authority scope"
        )

    def test_interaction_target_names_a_resource_not_an_assertion(self) -> None:
        _parse(_with_interaction(_NODE, _NODE))
        self.assert_refused(
            _with_interaction(_ASSERTION, _NODE), _ASSERTION, "an action target"
        )

    def test_shared_state_names_a_resource_not_a_participant(self) -> None:
        self.assert_refused(_with_interaction(_NODE, _AGENT), _AGENT, "shared state")


if __name__ == "__main__":
    unittest.main()
