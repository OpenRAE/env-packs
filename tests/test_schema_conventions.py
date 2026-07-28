"""RAES schema-convention conformance guard (issue #86).

Every schema this repository ships is subordinate to RAES (ADR 0009/0010) and
must follow RAES's governed schema-authoring conventions, not a placeholder:

  * ``$schema`` is JSON Schema draft 2020-12 (the RAES corpus draft).
  * ``$id`` lives under the governed ``https://aces.dev/schemas/`` namespace as
    ``<name>-v<n>.json`` -- never an ``example.com`` placeholder.
  * ``schema_version`` is the RAES string form
    ``{type: string, const: "<name>/v<n>"}``, with ``<name>``/``<n>`` derived
    from the ``$id``.

The guard loads *every* packaged schema, so a future ``v2`` or a newly added
schema is covered without editing scattered literals (the extensibility seam
called out by the architecture preflight).
"""

from __future__ import annotations

import re
import unittest
from pathlib import Path

import yaml

_SCHEMAS_DIR = (
    Path(__file__).parents[1]
    / "src"
    / "raes_env_packs"
    / "resources"
    / "schemas"
)
_DRAFT_2020_12 = "https://json-schema.org/draft/2020-12/schema"
_ID_RE = re.compile(
    r"^https://aces\.dev/schemas/"
    r"(?P<name>[a-z0-9]+(?:-[a-z0-9]+)*)-v(?P<version>\d+)\.json$"
)


def _packaged_schemas() -> list[Path]:
    return sorted(_SCHEMAS_DIR.glob("*.schema.yaml"))


class SchemaConventionTests(unittest.TestCase):
    def test_packaged_schemas_are_present(self) -> None:
        # The guard is only meaningful if it actually finds the shipped schemas.
        self.assertTrue(
            _packaged_schemas(), f"no packaged schemas under {_SCHEMAS_DIR}"
        )

    def test_every_schema_follows_aces_conventions(self) -> None:
        for path in _packaged_schemas():
            with self.subTest(schema=path.name):
                schema = yaml.safe_load(path.read_text(encoding="utf-8"))
                self.assertIsInstance(schema, dict)

                self.assertEqual(schema.get("$schema"), _DRAFT_2020_12)

                schema_id = schema.get("$id")
                self.assertIsInstance(schema_id, str)
                self.assertNotIn("example.com", schema_id)
                match = _ID_RE.fullmatch(schema_id)
                self.assertIsNotNone(
                    match,
                    f"$id {schema_id!r} is not a governed aces.dev schema id",
                )

                expected_version = f"{match.group('name')}/v{match.group('version')}"
                version_prop = (schema.get("properties") or {}).get("schema_version")
                self.assertIsInstance(version_prop, dict)
                self.assertEqual(version_prop.get("type"), "string")
                self.assertEqual(version_prop.get("const"), expected_version)


if __name__ == "__main__":
    unittest.main()
