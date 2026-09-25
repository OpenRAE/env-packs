"""The study copy preserves TechVault's authored scenario and content."""

from __future__ import annotations

import hashlib
import pathlib
import unittest

import yaml
from raes import instantiate_scenario, parse_sdl_file
from raes_processor.compiler import compile_runtime_model

from raes_env_packs import validate_pack
from raes_env_packs.digest import pack_content_digest

_ROOT = pathlib.Path(__file__).resolve().parents[1] / "packs"
_BASE = _ROOT / "techvault"
_STUDY = _ROOT / "techvault-participant-study"


class StudyPackTests(unittest.TestCase):
    def test_study_pack_is_valid_and_has_distinct_identity(self) -> None:
        result = validate_pack(_STUDY)
        self.assertTrue(result.ok, result.errors)
        self.assertNotEqual(pack_content_digest(_BASE), pack_content_digest(_STUDY))

    def test_study_preserves_techvault_and_adds_participant_sequence(self) -> None:
        base = yaml.safe_load((_BASE / "sdl/techvault.sdl.yaml").read_text())
        study = yaml.safe_load(
            (_STUDY / "sdl/techvault-participant-study.sdl.yaml").read_text()
        )
        self.assertEqual(study.pop("name"), "techvault-participant-study")
        self.assertEqual(base.pop("name"), "techvault")

        additive = {
            "content": {
                "red-participant-start-instruction",
                "red-participant-stop-instruction",
                "blue-participant-start-instruction",
                "blue-participant-stop-instruction",
            },
            "observation_boundaries": {
                "red-participant-study-view",
                "blue-participant-study-view",
            },
            "evidence_requirements": {
                "red-participant-start-delivery",
                "red-participant-stop-delivery",
                "blue-participant-start-delivery",
                "blue-participant-stop-delivery",
            },
            "entities": {"study-control"},
        }
        for section, names in additive.items():
            for name in names:
                self.assertIn(name, study[section])
                study[section].pop(name)

        study_agents = study.pop("agents")
        base_agents = base.pop("agents")
        for name in ("red-team-operator", "blue-team-operator"):
            self.assertEqual(study_agents[name]["entity"], base_agents[name]["entity"])
            self.assertEqual(
                study_agents[name]["interactive_access"],
                base_agents[name]["interactive_access"],
            )
        self.assertEqual(study.pop("injects").keys(), {
            "red-participant-start",
            "red-participant-stop",
            "blue-participant-start",
            "blue-participant-stop",
        })
        self.assertEqual(set(study.pop("events")), {
            "red-participant-start",
            "red-participant-stop",
            "blue-participant-start",
            "blue-participant-stop",
        })
        self.assertEqual(set(study.pop("scripts")), {"participant-study-sequence"})
        self.assertEqual(set(study.pop("stories")), {"participant-study"})
        self.assertEqual(set(study.pop("time_domains")), {"participant-study-time"})
        self.assertEqual(set(study.pop("clocks")), {"participant-study-clock"})
        self.assertEqual(
            set(study.pop("time_progression_policies")),
            {"participant-study-progression"},
        )
        self.assertEqual(set(study.pop("temporal_constraints")), {
            "red-participant-start-window",
            "red-participant-stop-window",
            "blue-participant-start-window",
            "blue-participant-stop-window",
        })
        self.assertEqual(set(study.pop("behavior_specifications")), {
            "red-participant-study",
            "blue-participant-study",
        })
        self.assertEqual(study, base)

    def test_participant_injects_compile_in_authored_order_for_claude(self) -> None:
        scenario = parse_sdl_file(
            _STUDY / "sdl/techvault-participant-study.sdl.yaml"
        )
        concrete = instantiate_scenario(
            scenario,
            {name: f"study-{name}" for name in scenario.variables},
        )
        runtime = compile_runtime_model(concrete)

        expected = (
            ("red-participant-study", "start", "red-team-operator", "red-participant-start", 1),
            ("red-participant-study", "stop", "red-team-operator", "red-participant-stop", 3),
            ("blue-participant-study", "start", "blue-team-operator", "blue-participant-start", 5),
            ("blue-participant-study", "stop", "blue-team-operator", "blue-participant-stop", 7),
        )
        for spec, delivery, participant, inject, order in expected:
            with self.subTest(spec=spec, delivery=delivery):
                authored = scenario.behavior_specifications[spec]
                self.assertEqual(
                    authored.realization_profile_ref,
                    "participant-implementation-manifest:claude-code",
                )
                address = (
                    f"participant.behavior-specification.{spec}."
                    f"inject-delivery.{delivery}"
                )
                compiled = runtime.participant_inject_deliveries[address]
                self.assertEqual(
                    compiled.participant_address,
                    f"participant.behavior.{participant}",
                )
                self.assertEqual(
                    compiled.inject_address,
                    f"orchestration.inject.{inject}",
                )
                self.assertEqual(compiled.delivery_kind, "external-direction")
                self.assertEqual(compiled.control_effective_order, order)

        script = scenario.scripts["participant-study-sequence"]
        self.assertEqual(
            script.events,
            {
                "red-participant-start": 1,
                "red-participant-stop": 3,
                "blue-participant-start": 5,
                "blue-participant-stop": 7,
            },
        )
        progression = scenario.time_progression_policies[
            "participant-study-progression"
        ]
        self.assertEqual(progression.advancement_mode, "event_driven")
        self.assertEqual(progression.synchronization_mode, "barrier")

    def test_exact_content_assets_are_identical(self) -> None:
        for source in (_BASE / "assets/content").iterdir():
            if not source.is_file():
                continue
            with self.subTest(asset=source.name):
                target = _STUDY / "assets/content" / source.name
                self.assertEqual(
                    hashlib.sha256(target.read_bytes()).digest(),
                    hashlib.sha256(source.read_bytes()).digest(),
                )
