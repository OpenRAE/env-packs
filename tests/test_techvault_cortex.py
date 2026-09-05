"""Executable tests for TechVault's pack-local Cortex state and analyzer."""

from __future__ import annotations

import http.server
import json
import os
import pathlib
import subprocess
import tempfile
import threading
import types
import unittest
import urllib.parse

from tools import verify_techvault_cortex


_ROOT = pathlib.Path(__file__).resolve().parents[1]
_CONTENT = _ROOT / "packs" / "techvault" / "assets" / "content"
_ANALYZER = _CONTENT / "cortex-techvault-analyzer.py"
_INITIALIZER = _CONTENT / "cortex-initializer.py"


def _load_initializer():
    module = types.ModuleType("techvault_cortex_initializer")
    module.__file__ = str(_INITIALIZER)
    source = _INITIALIZER.read_text(encoding="utf-8")
    exec(compile(source, str(_INITIALIZER), "exec"), module.__dict__)
    return module


class _CortexState:
    admin_key = "admin-fixture-key"
    connector_key = "connector-fixture-key"

    def __init__(self) -> None:
        self.users: dict[str, dict[str, object]] = {}
        self.enabled: list[dict[str, object]] = []
        self.organization_posts = 0
        self.user_posts = 0
        self.enable_posts = 0


def _handler(state: _CortexState):
    class Handler(http.server.BaseHTTPRequestHandler):
        def log_message(self, _format: str, *_args: object) -> None:
            return

        def _key(self) -> str:
            value = self.headers.get("Authorization", "")
            return value.removeprefix("Bearer ")

        def _reply(self, status: int, payload: object | None = None) -> None:
            body = b"" if payload is None else json.dumps(payload).encode("utf-8")
            self.send_response(status)
            if body:
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            if body:
                self.wfile.write(body)

        def do_GET(self) -> None:  # noqa: N802 - HTTP handler API
            path = urllib.parse.unquote(self.path)
            if path == "/api/status":
                self._reply(200, {"status": "ok"})
            elif path == "/api/user/current":
                user = state.users.get(self._key())
                self._reply(200, user) if user else self._reply(401)
            elif path.startswith("/api/user/"):
                login = path.removeprefix("/api/user/")
                users = [item for item in state.users.values() if item["_id"] == login]
                self._reply(200, users[0]) if users else self._reply(404)
            elif path == "/api/analyzerdefinition":
                self._reply(
                    200,
                    [
                        {
                            "id": "TechVaultScenarioContext_1_0",
                            "name": "TechVaultScenarioContext",
                        }
                    ],
                )
            elif path == "/api/analyzer":
                self._reply(200, state.enabled)
            else:
                self._reply(404)

        def do_POST(self) -> None:  # noqa: N802 - HTTP handler API
            length = int(self.headers.get("Content-Length", "0"))
            payload = json.loads(self.rfile.read(length) or b"{}")
            if self.path == "/api/organization":
                state.organization_posts += 1
                self._reply(201, {"name": payload["name"]})
            elif self.path == "/api/user":
                state.user_posts += 1
                key = payload["key"]
                state.users[key] = {
                    "_id": payload["login"],
                    "organization": payload["organization"],
                    "roles": payload["roles"],
                }
                self._reply(201, state.users[key])
            elif self.path == "/api/analyzerdefinition/scan":
                self._reply(204)
            elif self.path == "/api/organization/analyzer/TechVaultScenarioContext_1_0":
                state.enable_posts += 1
                state.enabled.append(
                    {
                        "id": "enabled-techvault-analyzer",
                        "analyzerDefinitionId": "TechVaultScenarioContext_1_0",
                    }
                )
                self._reply(201, state.enabled[0])
            else:
                self._reply(404)

    return Handler


class TechVaultCortexTests(unittest.TestCase):
    def test_offline_analyzer_emits_the_expected_bounded_report(self) -> None:
        self.assertTrue(os.access(_ANALYZER, os.X_OK))
        cases = (
            ("172.20.1.30", "attacker", "malicious", "malicious"),
            ("172.20.1.31", "unclassified", "unknown", "info"),
        )
        for observable, role, verdict, level in cases:
            with self.subTest(observable=observable), tempfile.TemporaryDirectory() as directory:
                job = pathlib.Path(directory)
                (job / "input").mkdir()
                (job / "output").mkdir()
                (job / "input" / "input.json").write_text(
                    json.dumps({"data": observable, "dataType": "ip"}),
                    encoding="utf-8",
                )
                result = subprocess.run(
                    [str(_ANALYZER), str(job)],
                    capture_output=True,
                    text=True,
                    timeout=10,
                    check=False,
                )
                report = json.loads(
                    (job / "output" / "output.json").read_text(encoding="utf-8")
                )

                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(result.stdout, "")
                self.assertTrue(report["success"])
                self.assertEqual(report["full"]["scenario_role"], role)
                self.assertEqual(report["full"]["verdict"], verdict)
                self.assertTrue(report["full"]["offline"])
                self.assertEqual(report["summary"]["taxonomies"][0]["level"], level)

    def test_native_verifier_requires_cortex_specific_ok_status(self) -> None:
        self.assertFalse(
            verify_techvault_cortex._cortex_connector_is_ok(
                {"database": {"status": "OK"}}
            )
        )
        self.assertTrue(
            verify_techvault_cortex._cortex_connector_is_ok(
                {"connectors": [{"name": "Cortex", "status": "OK"}]}
            )
        )
        self.assertFalse(
            verify_techvault_cortex._cortex_connector_is_ok(
                {"connectors": [{"name": "Cortex", "status": "ERROR"}]}
            )
        )

    def test_native_verifier_rejects_invalid_analyzer_results(self) -> None:
        analyzer = {
            "id": "enabled-techvault-analyzer",
            "analyzerDefinitionId": "TechVaultScenarioContext_1_0",
        }
        valid = [
            [analyzer],
            {"id": "job-1"},
            {
                "status": "Success",
                "report": {"full": {"scenario_role": "attacker"}},
            },
        ]

        cases = (
            ("inventory", ({"unexpected": "shape"},), "invalid analyzer inventory"),
            ("not-enabled", [[], *valid[1:]], "not enabled"),
            ("no-job", [valid[0], {}, valid[2]], "did not create"),
            (
                "failed-report",
                [valid[0], valid[1], {"status": "Failure"}],
                "did not succeed",
            ),
            (
                "wrong-context",
                [
                    valid[0],
                    valid[1],
                    {
                        "status": "Success",
                        "report": {"full": {"scenario_role": "unclassified"}},
                    },
                ],
                "lacks attacker context",
            ),
        )
        for name, responses, message in cases:
            with self.subTest(name=name):
                pending = iter(responses)

                def requester(*_args, **_kwargs):
                    return next(pending)

                with self.assertRaisesRegex(
                    verify_techvault_cortex.VerificationError, message
                ):
                    verify_techvault_cortex._verify_analyzer_execution(
                        requester, "http://cortex", "connector-key"
                    )

        successful = iter(valid)
        verify_techvault_cortex._verify_analyzer_execution(
            lambda *_args, **_kwargs: next(successful),
            "http://cortex",
            "connector-key",
        )

    def test_initializer_is_idempotent_and_connector_is_least_privilege(self) -> None:
        module = _load_initializer()
        state = _CortexState()
        server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), _handler(state))
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        environment = {
            "CORTEX_URL": f"http://127.0.0.1:{server.server_port}",
            "CORTEX_ADMIN_KEY": state.admin_key,
            "CORTEX_CONNECTOR_KEY": state.connector_key,
            "CORTEX_ORGANIZATION": "TechVault",
            "CORTEX_ANALYZER_DEFINITION_ID": "TechVaultScenarioContext_1_0",
            "CORTEX_READY_TIMEOUT": "2",
        }
        try:
            module.initialize(environment)
            module.initialize(environment)
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=2)

        self.assertEqual(state.organization_posts, 1)
        self.assertEqual(state.user_posts, 2)
        self.assertEqual(state.enable_posts, 1)
        connector = state.users[state.connector_key]
        self.assertEqual(connector["roles"], ["read", "analyze"])
        self.assertNotIn("orgadmin", connector["roles"])

    def test_initializer_rejects_shared_admin_and_connector_key(self) -> None:
        module = _load_initializer()
        environment = {
            "CORTEX_URL": "http://127.0.0.1:1",
            "CORTEX_ADMIN_KEY": "same",
            "CORTEX_CONNECTOR_KEY": "same",
            "CORTEX_ORGANIZATION": "TechVault",
            "CORTEX_ANALYZER_DEFINITION_ID": "TechVaultScenarioContext_1_0",
        }
        with self.assertRaisesRegex(module.CortexError, "must differ"):
            module.initialize(environment)


if __name__ == "__main__":
    unittest.main()
