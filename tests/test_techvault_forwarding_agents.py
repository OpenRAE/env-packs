"""TechVault forwarding agents declare only values that a backend can prove (#604)."""

from __future__ import annotations

import pathlib
import unittest

import yaml

_ROOT = pathlib.Path(__file__).resolve().parents[1]
_PACKS = ("techvault", "techvault-participant-study")
_CHILDREN = ("sources", "transforms", "ship_targets", "reload_channels", "settings")
_SENTINELS = frozenset({"other", "unknown"})


def _sentinel_fields(pack: str) -> list[str]:
    sdl = yaml.safe_load((_ROOT / "packs" / pack / "sdl" / f"{pack}.sdl.yaml").read_text(encoding="utf-8"))
    found = []
    for node_name, node in sdl["nodes"].items():
        for agent in ((node or {}).get("runtime") or {}).get("forwarding_agents") or []:
            for field in _CHILDREN:
                for child in agent.get(field) or []:
                    found += [
                        f"{node_name}.{agent['forwarding_agent_id']}.{field}.{key}"
                        for key, value in child.items()
                        if isinstance(value, str) and value in _SENTINELS
                    ]
            found += [
                f"{node_name}.{agent['forwarding_agent_id']}.{key}"
                for key, value in agent.items()
                if isinstance(value, str) and value in _SENTINELS
            ]
    return found


class TechVaultForwardingAgentTests(unittest.TestCase):
    def test_no_forwarding_agent_declares_a_knowledge_sentinel(self) -> None:
        for pack in _PACKS:
            with self.subTest(pack=pack):
                self.assertEqual(_sentinel_fields(pack), [])

    def test_local_syslog_names_its_socket_input(self) -> None:
        for pack in _PACKS:
            with self.subTest(pack=pack):
                sdl = yaml.safe_load(
                    (_ROOT / "packs" / pack / "sdl" / f"{pack}.sdl.yaml").read_text(encoding="utf-8")
                )
                agents = {
                    agent["forwarding_agent_id"]: agent for agent in sdl["nodes"]["ad"]["runtime"]["forwarding_agents"]
                }
                (source,) = agents["ad-syslog-forwarder"]["sources"]
                self.assertEqual(source["kind"], "socket")


if __name__ == "__main__":
    unittest.main()
