"""TechVault forwarding agents declare only values that a backend can prove (#604)."""

from __future__ import annotations

import pathlib
import unittest

import yaml

_ROOT = pathlib.Path(__file__).resolve().parents[1]
_PACKS = ("techvault", "techvault-participant-study")
_SENTINELS = frozenset({"other", "unknown"})


def _agents(pack: str) -> list[tuple[str, dict]]:
    sdl = yaml.safe_load((_ROOT / "packs" / pack / "sdl" / f"{pack}.sdl.yaml").read_text(encoding="utf-8"))
    return [
        (node_name, agent)
        for node_name, node in sdl["nodes"].items()
        for agent in ((node or {}).get("runtime") or {}).get("forwarding_agents") or []
    ]


def _sentinel_provenances(pack: str) -> list[str]:
    return [
        f"{node_name}.{agent['forwarding_agent_id']}.{setting['setting_id']}"
        for node_name, agent in _agents(pack)
        for setting in agent.get("settings") or []
        if setting.get("provenance") in _SENTINELS
    ]


def _sentinel_source_kinds(pack: str) -> list[str]:
    return [
        f"{node_name}.{agent['forwarding_agent_id']}.{source['source_id']}"
        for node_name, agent in _agents(pack)
        for source in agent.get("sources") or []
        if source.get("kind") in _SENTINELS
    ]


class TechVaultForwardingAgentTests(unittest.TestCase):
    def test_no_forwarding_setting_declares_a_provenance_sentinel(self) -> None:
        for pack in _PACKS:
            with self.subTest(pack=pack):
                self.assertEqual(_sentinel_provenances(pack), [])

    def test_no_forwarding_source_declares_a_kind_sentinel(self) -> None:
        for pack in _PACKS:
            with self.subTest(pack=pack):
                self.assertEqual(_sentinel_source_kinds(pack), [])


if __name__ == "__main__":
    unittest.main()
