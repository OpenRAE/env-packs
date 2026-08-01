"""CLI coverage for the shared infrastructure-kit workflow."""

from __future__ import annotations

import io
import json
import tempfile
import unittest
from pathlib import Path

from raes_env_packs import kit_cli, kits
from tests.test_kit_materialization import _write_content_identified_pack
from tests.test_kits import KIT_ID, KIT_VERSION, _write_synthetic_kit


class KitCliTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        base = Path(self.temp.name)
        self.pack = _write_content_identified_pack(base)
        self.catalog = base / "catalog"
        _write_synthetic_kit(self.catalog / "kits" / KIT_ID / KIT_VERSION)
        self.source_args = [
            str(self.catalog),
            "--source-id",
            "reference",
            "--source-revision",
            "sha256:catalog",
        ]

    def _main(self, arguments: list[str], stdin: str = "") -> tuple[int, str, str]:
        stdout = io.StringIO()
        stderr = io.StringIO()
        result = kit_cli.main(
            arguments,
            stdin=io.StringIO(stdin),
            stdout=stdout,
            stderr=stderr,
        )
        return result, stdout.getvalue(), stderr.getvalue()

    def test_list_search_and_inspect_share_the_catalog_projection(self) -> None:
        result, listed, _error = self._main(["list", *self.source_args, "--json"])
        self.assertEqual(result, kit_cli.EXIT_OK)
        self.assertEqual(json.loads(listed)[0]["id"], KIT_ID)

        result, searched, _error = self._main(
            ["search", *self.source_args, "static web", "--json"]
        )
        self.assertEqual(result, kit_cli.EXIT_OK)
        self.assertEqual(json.loads(searched)[0]["module"]["parameter_defaults"], {"hostname": "web"})

        result, inspected, _error = self._main(
            ["inspect", *self.source_args, KIT_ID, KIT_VERSION, "--json"]
        )
        self.assertEqual(result, kit_cli.EXIT_OK)
        self.assertEqual(json.loads(inspected)["topology"], ["nodes.web"])

    def test_preview_and_mutation_consume_the_same_value_free_proposal(self) -> None:
        arguments = [
            "add",
            str(self.pack),
            *self.source_args,
            KIT_ID,
            KIT_VERSION,
            "--namespace",
            "web",
            "--target-sdl",
            "sdl/example-pack.sdl.yaml",
            "--parameters",
            "-",
            "--json",
        ]
        parameters = json.dumps({"hostname": "web.example.test"})
        result, preview, _error = self._main([*arguments, "--preview"], parameters)
        self.assertEqual(result, kit_cli.EXIT_OK)
        self.assertNotIn("web.example.test", preview)
        self.assertFalse((self.pack / kits.KIT_MATERIALIZATIONS_PATH).exists())

        result, applied, _error = self._main(arguments, parameters)
        self.assertEqual(result, kit_cli.EXIT_OK)
        self.assertEqual(json.loads(applied), json.loads(preview))
        self.assertTrue((self.pack / kits.KIT_MATERIALIZATIONS_PATH).is_file())

        result, _removed, _error = self._main(
            ["remove", str(self.pack), "web", "--json"]
        )
        self.assertEqual(result, kit_cli.EXIT_OK)

    def test_update_and_replace_cli_wiring_mutates_the_exact_materialization(self) -> None:
        add_arguments = [
            "add",
            str(self.pack),
            *self.source_args,
            KIT_ID,
            KIT_VERSION,
            "--namespace",
            "web",
            "--target-sdl",
            "sdl/example-pack.sdl.yaml",
            "--parameters",
            "-",
            "--json",
        ]
        result, _output, _error = self._main(
            add_arguments, json.dumps({"hostname": "web.example.test"})
        )
        self.assertEqual(result, kit_cli.EXIT_OK)

        result, _output, _error = self._main(
            [
                "update",
                str(self.pack),
                *self.source_args,
                KIT_ID,
                KIT_VERSION,
                "web",
                "--parameters",
                "-",
                "--json",
            ],
            json.dumps({"hostname": "updated.example.test"}),
        )
        self.assertEqual(result, kit_cli.EXIT_OK)
        ledger = json.loads(
            (self.pack / kits.KIT_MATERIALIZATIONS_PATH).read_text(
                encoding="utf-8"
            )
        )
        self.assertEqual(
            ledger["materializations"][0]["parameters"]["hostname"],
            "updated.example.test",
        )

        replacement_id = "infrastructure.reverse-proxy"
        _write_synthetic_kit(
            self.catalog / "kits" / replacement_id / KIT_VERSION,
            kit_id=replacement_id,
            module_id="infrastructure/reverse-proxy",
            node_name="proxy",
            parameter="route",
        )
        result, _output, _error = self._main(
            [
                "replace",
                str(self.pack),
                *self.source_args,
                replacement_id,
                KIT_VERSION,
                "web",
                "--namespace",
                "front",
                "--target-sdl",
                "sdl/example-pack.sdl.yaml",
                "--parameters",
                "-",
                "--json",
            ],
            json.dumps({"route": "app.example.test"}),
        )
        self.assertEqual(result, kit_cli.EXIT_OK)
        ledger = json.loads(
            (self.pack / kits.KIT_MATERIALIZATIONS_PATH).read_text(
                encoding="utf-8"
            )
        )
        self.assertEqual(ledger["materializations"][0]["id"], "front")
        self.assertEqual(
            ledger["materializations"][0]["kit_id"], replacement_id
        )

    def test_parameter_document_is_bounded_duplicate_safe_and_finite(self) -> None:
        base = [
            "add",
            str(self.pack),
            *self.source_args,
            KIT_ID,
            KIT_VERSION,
            "--namespace",
            "web",
            "--target-sdl",
            "sdl/example-pack.sdl.yaml",
            "--parameters",
            "-",
            "--preview",
            "--json",
        ]
        for payload in (
            '{"hostname":"first","hostname":"second"}',
            '{"hostname":NaN}',
            " " * (64 * 1024 + 1),
        ):
            with self.subTest(payload=payload[:20]):
                result, output, error = self._main(base, payload)
                self.assertEqual(result, kit_cli.EXIT_BLOCKING)
                self.assertEqual(output, "")
                self.assertNotIn(payload[:20], error)

    def test_secret_shaped_parameter_is_rejected_without_echoing_the_value(self) -> None:
        arguments = [
            "add",
            str(self.pack),
            *self.source_args,
            KIT_ID,
            KIT_VERSION,
            "--namespace",
            "web",
            "--target-sdl",
            "sdl/example-pack.sdl.yaml",
            "--parameters",
            "-",
            "--preview",
            "--json",
        ]
        value = "${SOME_VAR}"
        result, output, error = self._main(
            arguments, json.dumps({"hostname": value})
        )

        self.assertEqual(result, kit_cli.EXIT_BLOCKING)
        self.assertIn("kit.parameter.secret", output)
        self.assertNotIn(value, output)
        self.assertEqual(error, "")

    def test_human_catalog_output_escapes_terminal_controls(self) -> None:
        output = io.StringIO()
        kit_cli._emit(
            [
                {
                    "id": KIT_ID,
                    "version": KIT_VERSION,
                    "title": "safe\nforged\x1b]52;c;Zm9yZ2Vk\x07",
                }
            ],
            as_json=False,
            stdout=output,
        )

        rendered = output.getvalue()
        self.assertNotIn("\x1b", rendered)
        self.assertNotIn("\x07", rendered)
        self.assertNotIn("\nforged", rendered)
        self.assertIn(r"safe\u000aforged\u001b", rendered)


if __name__ == "__main__":
    unittest.main()
