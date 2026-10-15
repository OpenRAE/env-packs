"""SMTP/IMAP mailbox addresses follow the selected mail domain (#435).

The 1.0.0 and 1.1.0 releases substitute ``mail_domain`` into the domain name
but hard-code both mailbox addresses to ``environment.test``. The 1.2.0
release derives each address from ``mail_domain``. This test composes the
release through RAES with the default, the declared variation, and a custom
domain, and checks each composed address and domain reference.

RAES 6.0.1 already reports ``realization.authority-bound-unavailable`` for
the domain name (OpenRAE/rae#1481). The derived addresses must not add a
planning diagnostic to the set that the 1.1.0 release reports.
"""

from __future__ import annotations

import shutil
import tempfile
import unittest
from pathlib import Path

import yaml
from raes import parse_sdl_file
from raes_processor.compiler import compile_scenario_runtime_model
from raes_processor.planner import plan

from tests.test_kit_compute_substrate import MANIFEST


KIT = Path(__file__).resolve().parents[1] / "kits/infrastructure.smtp-imap-mail-service"
CORRECTED = KIT / "1.2.0"
PREVIOUS = KIT / "1.1.0"


def _compose(release: Path, parameters: dict) -> tuple[object, set[str]]:
    """Return the composed mail service and its planning diagnostic codes."""

    version = yaml.safe_load((release / "kit.yaml").read_text(encoding="utf-8"))["version"]
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        shutil.copy2(release / "module.sdl.yaml", root / "module.sdl.yaml")
        document = {
            "name": "composition",
            "imports": [
                {
                    "source": "local:module.sdl.yaml",
                    "namespace": "subject",
                    "version": version,
                    "parameters": parameters,
                }
            ],
        }
        (root / "scenario.sdl.yaml").write_text(
            yaml.safe_dump(document, sort_keys=False), encoding="utf-8"
        )
        scenario = parse_sdl_file(root / "scenario.sdl.yaml", migration_policy="accept")
        model = compile_scenario_runtime_model(scenario, parameters={})
        execution = plan(model, MANIFEST)
    codes = {diagnostic.code for diagnostic in (*model.diagnostics, *execution.diagnostics)}
    return scenario.nodes["subject.mail"].runtime.mail_services[0], codes


def _cases() -> dict[str, tuple[dict, str]]:
    cases = yaml.safe_load(
        (CORRECTED / "tests/composition.yaml").read_text(encoding="utf-8")
    )
    return {
        "default": (cases["default"], "environment.test"),
        "variation": (cases["variation"], "alternate.test"),
        "custom": ({**cases["default"], "mail_domain": "example.test"}, "example.test"),
    }


class SmtpImapMailboxDomainTests(unittest.TestCase):
    def test_mailbox_addresses_follow_the_selected_domain(self) -> None:
        for case, (parameters, domain) in _cases().items():
            with self.subTest(case=case):
                service, _ = _compose(CORRECTED, parameters)
                self.assertEqual(
                    [(entry.domain_id, entry.name) for entry in service.domains],
                    [("primary_domain", domain)],
                )
                self.assertEqual(
                    [
                        (mailbox.mailbox_id, mailbox.address, mailbox.domain_ref)
                        for mailbox in service.mailboxes
                    ],
                    [
                        ("operator_mailbox", f"operator@{domain}", "primary_domain"),
                        ("service_mailbox", f"service@{domain}", "primary_domain"),
                    ],
                )

    def test_derived_addresses_add_no_planning_diagnostic(self) -> None:
        for case, (parameters, _) in _cases().items():
            with self.subTest(case=case):
                _, corrected = _compose(CORRECTED, parameters)
                _, previous = _compose(PREVIOUS, parameters)
                self.assertLessEqual(corrected, previous)


if __name__ == "__main__":
    unittest.main()
