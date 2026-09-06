"""Exercise the actual SDK transport handshake and tool dispatch."""
import os
import asyncio
import io
import subprocess
import sys
import tempfile
from contextlib import asynccontextmanager
from pathlib import Path
from types import SimpleNamespace
from unittest import TestCase, mock
import anyio
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from mcp.shared.memory import create_client_server_memory_streams

from raes_env_packs import mcp_server, wizard
from raes_env_packs.authoring import AuthoringSession


class StdioTests(TestCase):
    def test_in_process_transport_observes_launch_grants_and_exact_apply(self):
        with tempfile.TemporaryDirectory() as directory:
            async def exchange():
                with AuthoringSession(write_root=directory, allow_writes=True, allow_prepare=True) as author:
                    server = mcp_server.create_server(author, allow_writes=True, allow_prepare=True)
                    async with create_client_server_memory_streams() as (client_streams, server_streams), anyio.create_task_group() as tasks:
                        tasks.start_soon(server.run, *server_streams, server.create_initialization_options())
                        async with ClientSession(*client_streams) as client:
                            await client.initialize()
                            listed = {tool.name: tool for tool in (await client.list_tools()).tools}
                            self.assertFalse(listed["pack_prepare"].annotations.read_only_hint)
                            self.assertTrue(listed["pack_apply"].annotations.destructive_hint)
                            preview = (await client.call_tool("pack_scaffold", {"inputs": {
                                "version": wizard.WIZARD_INPUT_VERSION, "pack_id": "wire-pack"}})).structured_content
                            self.assertFalse((Path(directory) / "wire-pack").exists())
                            applied = await client.call_tool("pack_apply", {"proposal": preview["result"]["proposal"]})
                            self.assertFalse(applied.is_error)
                            for change in preview["result"]["changes"]:
                                self.assertEqual((Path(directory) / "wire-pack" / change["path"]).read_text(), change["after"]["text"])
                        tasks.cancel_scope.cancel()
            asyncio.run(exchange())

    def test_frame_reader_stops_before_reading_an_unbounded_line(self):
        valid = b'{"jsonrpc":"2.0","method":"notifications/initialized"}\n'
        for content, expected in ((valid, 1), (b'\xff\n', 0), (b'x' * 300000, 0)):
            stream = io.BytesIO(content)
            async def collect():
                return [line async for line in mcp_server._BoundedStdin()]
            with mock.patch.object(mcp_server.sys, "stdin", SimpleNamespace(buffer=stream)), \
                 mock.patch.object(mcp_server.sys, "stderr", io.StringIO()):
                self.assertEqual(len(asyncio.run(collect())), expected)
            self.assertLessEqual(stream.tell(), mcp_server._MAX_FRAME + 1)

    def test_main_wires_independent_grants_and_closes_the_real_session(self):
        for allow_writes, allow_prepare in ((False, False), (True, False), (False, True), (True, True)):
            with self.subTest(writes=allow_writes, prepare=allow_prepare), tempfile.TemporaryDirectory() as directory:
                async def exchange(streams):
                    async with ClientSession(*streams) as client:
                        await client.initialize()
                        names = {tool.name for tool in (await client.list_tools()).tools}
                        self.assertEqual("pack_apply" in names, allow_writes)
                        self.assertEqual("pack_prepare" in names, allow_prepare)
                        preview = (await client.call_tool("pack_scaffold", {"inputs": {
                            "version": wizard.WIZARD_INPUT_VERSION, "pack_id": "launch-pack",
                        }})).structured_content
                        self.assertEqual(preview["status"], 0, preview)
                        target = Path(directory) / "launch-pack"
                        self.assertEqual(preview["result"]["target"], str(target))
                        self.assertFalse(target.exists())
                        applied = await client.call_tool("pack_apply", {"proposal": preview["result"]["proposal"]})
                        self.assertEqual(applied.is_error, not allow_writes)
                        self.assertEqual(target.exists(), allow_writes)
                    await streams[1].aclose()

                @asynccontextmanager
                async def memory_stdio(**_kwargs):
                    with anyio.fail_after(15):
                        async with create_client_server_memory_streams() as (client, server), anyio.create_task_group() as tasks:
                            tasks.start_soon(exchange, client)
                            yield server

                arguments = ["--pack", "sample", "examples", "revision-1", directory,
                             "--write-root", directory]
                if allow_writes:
                    arguments.append("--allow-writes")
                if allow_prepare:
                    arguments.append("--allow-prepare")
                with mock.patch.object(mcp_server, "stdio_server", new=memory_stdio), \
                     mock.patch.object(mcp_server, "AuthoringSession", wraps=AuthoringSession) as sessions, \
                     mock.patch.object(mcp_server, "create_server", wraps=mcp_server.create_server) as servers:
                    self.assertEqual(mcp_server.main(arguments), 0)
                sessions.assert_called_once_with(
                    packs={"sample": mcp_server.catalog.Source("examples", "revision-1", directory)},
                    kit_sources={}, releases={}, write_root=directory,
                    allow_writes=allow_writes, allow_prepare=allow_prepare)
                session = servers.call_args.args[0]
                servers.assert_called_once_with(session, allow_writes=allow_writes, allow_prepare=allow_prepare)
                self.assertEqual(session.call("pack_examples", {})["status"], 2)

    def test_main_rejects_duplicate_handles_without_payload_logging(self):
        with tempfile.TemporaryDirectory() as directory:
            duplicate = ["--release", "release", directory, "--release", "release", directory]
            with mock.patch.object(mcp_server.sys, "stderr", io.StringIO()) as stderr:
                self.assertEqual(mcp_server.main(duplicate), 2)
                self.assertEqual(stderr.getvalue(), "authoring.invalid-host-configuration\n")
            with self.assertRaises(ValueError):
                mcp_server._sources([["same", "a", "1", directory]] * 2, mcp_server.catalog.Source)

    def test_invalid_transport_frames_are_bounded_and_never_echoed(self):
        for frame in ('{"invalid":"SENSITIVE-SENTINEL"}\n',
                      'SENSITIVE-SENTINEL' + 'x' * 262144 + '\n'):
            process = subprocess.run([sys.executable, "-m", "raes_env_packs.mcp_server"],
                                     input=frame, text=True, capture_output=True, timeout=15)
            self.assertNotIn("SENSITIVE-SENTINEL", process.stdout + process.stderr)
            self.assertIn("authoring.invalid-frame", process.stderr)

    def test_installed_module_serves_discovery_and_shared_example_without_writes(self):
        with tempfile.TemporaryDirectory() as directory:
            async def exchange():
                parameters = StdioServerParameters(command=sys.executable,
                    args=["-m", "raes_env_packs.mcp_server"], cwd=directory,
                    env={"PATH": os.defpath, "PYTHONDONTWRITEBYTECODE": "1"})
                with anyio.fail_after(30):
                    async with stdio_client(parameters) as (reader, writer):
                        async with ClientSession(reader, writer) as client:
                            await client.initialize()
                            listed = await client.list_tools()
                            called = await client.call_tool("pack_examples", {})
                            refused = await client.call_tool("pack_validate", {"source": "SENSITIVE-SENTINEL", "approved": True})
                            self.assertTrue(refused.is_error)
                            self.assertEqual(refused.structured_content["status"], 2)
                            self.assertNotIn("SENSITIVE-SENTINEL", refused.content[0].text)
                            return listed, called
            listed, called = asyncio.run(exchange())
            names = {tool.name for tool in listed.tools}
            self.assertIn("pack_validate", names)
            self.assertIn("pack_compose", names)
            self.assertNotIn("pack_apply", names)
            self.assertNotIn("pack_prepare", names)
            result = called.structured_content
            self.assertEqual(result["status"], 0)
            self.assertEqual(result["result"]["preview"]["pack"], "example-pack")
            self.assertEqual(list(Path(directory).iterdir()), [])
