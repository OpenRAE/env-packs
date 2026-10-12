"""Atomic directory transactions on a C library without renameat2 (issue #443).

macOS libc has no ``renameat2``. These tests hand the transactions a real C
library handle that hides that one symbol, which is how ``ctypes`` sees macOS,
and check that each transaction refuses with the missing platform capability
named and both trees left untouched. The wizard, kit, and distribution CLI
tests reuse ``without_renameat2`` to check what each command prints.
"""

from __future__ import annotations

import ctypes
import tempfile
import unittest
from contextlib import AbstractContextManager
from pathlib import Path
from unittest import mock

from raes_env_packs import _transactions

_REAL_CDLL = ctypes.CDLL


class _LibcWithoutRenameat2:
    """A real C library handle that hides renameat2, as macOS libc lacks it."""

    def __init__(self, *args: object, **kwargs: object) -> None:
        self._libc = _REAL_CDLL(*args, **kwargs)

    def __getattr__(self, name: str) -> object:
        if name == "renameat2":
            raise AttributeError(name)
        return getattr(self._libc, name)


def without_renameat2() -> AbstractContextManager[object]:
    """Patch the C library lookup so it has no renameat2 symbol."""

    return mock.patch.object(ctypes, "CDLL", _LibcWithoutRenameat2)


class MissingRenameat2Tests(unittest.TestCase):
    def setUp(self) -> None:
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)

    def _tree(self, name: str, content: str) -> Path:
        tree = self.root / name
        tree.mkdir()
        (tree / "pack.yaml").write_text(content, encoding="utf-8")
        return tree

    def test_each_transaction_names_the_missing_platform_capability(self) -> None:
        cases = (
            (_transactions.publish_noreplace, False),
            (_transactions.exchange, True),
        )
        for transaction, target_exists in cases:
            with self.subTest(transaction=transaction.__name__):
                staged = self._tree(f"{transaction.__name__}-staged", "successor\n")
                target = self.root / f"{transaction.__name__}-target"
                if target_exists:
                    self._tree(target.name, "live\n")
                with without_renameat2(), self.assertRaises(
                    _transactions.UnsupportedPlatformError
                ) as caught:
                    transaction(staged, target)
                message = str(caught.exception)
                self.assertIn("renameat2", message)
                self.assertIn("Linux", message)
                self.assertEqual(
                    (staged / "pack.yaml").read_text(encoding="utf-8"), "successor\n"
                )
                if target_exists:
                    self.assertEqual(
                        (target / "pack.yaml").read_text(encoding="utf-8"), "live\n"
                    )
                else:
                    self.assertFalse(target.exists())

    def test_other_failures_keep_only_the_bounded_summary(self) -> None:
        summary = _transactions.failure_message(
            "could not publish pack",
            _transactions.TransactionError("staged tree could not be published"),
        )
        self.assertEqual(summary, "could not publish pack")


if __name__ == "__main__":
    unittest.main()
