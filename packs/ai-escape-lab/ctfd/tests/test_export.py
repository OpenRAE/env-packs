"""Pack-local tests for the CTFd projection."""

from __future__ import annotations

import importlib.util
import pathlib
import unittest


_SCRIPT = pathlib.Path(__file__).resolve().parents[1] / "export_shifter_challenge_pack.py"
_SPEC = importlib.util.spec_from_file_location("ai_escape_ctfd_export", _SCRIPT)
assert _SPEC is not None and _SPEC.loader is not None
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)


class ChallengeExportTests(unittest.TestCase):
    def test_complete_projection(self) -> None:
        payload = _MODULE.build_import_pack()
        self.assertEqual(payload["format"], "ctfd")
        self.assertEqual(len(payload["challenges"]), 7)
        self.assertEqual(sum(len(row["hints"]) for row in payload["challenges"]), 12)


if __name__ == "__main__":
    unittest.main()
