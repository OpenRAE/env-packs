#!/usr/bin/env python3
"""Build deterministic TechVault participant MCP source archives.

The archives contain only source and build manifests from one immutable Git
revision. Backend configuration, generated output, tests, and dependency trees
are deliberately excluded from the portable scenario content.
"""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
import pathlib
import re
import subprocess
import tarfile


SOURCE_REPOSITORY = "https://github.com/Brad-Edwards/aptl"
SOURCE_REVISION = "7c673a19f9fb6a3eb1d17305104196b600bd59cc"
COMMON_PACKAGE = "aptl-mcp-common"
RED_PACKAGES = (COMMON_PACKAGE, "mcp-red")
BLUE_PACKAGES = (
    COMMON_PACKAGE,
    "mcp-indexer",
    "mcp-network",
    "mcp-reverse",
    "mcp-soar",
    "mcp-threatintel",
    "mcp-wazuh",
)
_ROOT_FILES = frozenset({"package.json", "package-lock.json", "tsconfig.json", "tsconfig.build.json"})
_REPOSITORY_ROOT = pathlib.Path(__file__).resolve().parents[1]
_ASSET_ROOT = _REPOSITORY_ROOT / "packs" / "techvault" / "assets" / "content"
_TELEMETRY_PATH = "src/telemetry.ts"
_TELEMETRY_SOURCE_SHA256 = "dc6b5c9c39a5818c6bd690d4e86bf14f9cb1eefc889c5db9744c5ae97867da51"


def _git(repo: pathlib.Path, *args: str) -> bytes:
    environment = {
        "GIT_CONFIG_GLOBAL": os.devnull,
        "GIT_CONFIG_NOSYSTEM": "1",
        "GIT_NO_REPLACE_OBJECTS": "1",
        "LC_ALL": "C",
    }
    if path := os.environ.get("PATH"):
        environment["PATH"] = path
    result = subprocess.run(
        ["git", "--no-replace-objects", "-C", str(repo), *args],
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=environment,
        timeout=30,
    )
    if result.returncode:
        raise RuntimeError("immutable MCP source could not be read")
    return result.stdout


def _validate_revision(repo: pathlib.Path, revision: str) -> None:
    if revision != SOURCE_REVISION or re.fullmatch(r"[0-9a-f]{40}", revision) is None:
        raise ValueError("MCP source revision must be the reviewed immutable commit")
    resolved = _git(repo, "rev-parse", "--verify", f"{revision}^{{commit}}").decode(
        "ascii"
    ).strip()
    if resolved != revision:
        raise RuntimeError("MCP source revision did not resolve to the reviewed commit")


_TELEMETRY_REPLACEMENTS = (
    (
        "import { redact } from './redaction.js';\n\n",
        "",
    ),
    (
        "const MAX_ATTR_SIZE = 50_000;\n\n"
        "/**\n"
        " * Truncate a value to a string suitable for a span attribute.\n"
        " */\n"
        "function truncateAttr(value: unknown): string {\n"
        "  const serialized = JSON.stringify(value);\n"
        "  if (serialized && serialized.length > MAX_ATTR_SIZE) {\n"
        "    return serialized.slice(0, 2000) + `... [truncated from ${serialized.length} bytes]`;\n"
        "  }\n"
        "  return serialized;\n"
        "}\n\n",
        "",
    ),
    (
        " * Creates a span with GenAI SIG conventions, records timing, errors,\n"
        " * and truncated arguments/responses as attributes.\n",
        " * Creates a span with GenAI SIG conventions and records only tool identity\n"
        " * and content-free completion status metadata.\n",
    ),
    (
        "  args: Record<string, unknown>,\n",
        "  _args: Record<string, unknown>,\n",
    ),
    (
        "        // Redact before truncating so the marker is never split mid-token.\n"
        "        'aptl.tool.arguments': truncateAttr(redact(args)),\n",
        "        'aptl.tool.payload.recorded': false,\n",
    ),
    (
        "        span.setAttribute('aptl.tool.response', truncateAttr(redact(result)));\n",
        "",
    ),
    (
        "        const rawMessage = err instanceof Error ? err.message : String(err);\n"
        "        // Error messages and stack traces from MCP tools regularly carry\n"
        "        // the offending command line / response body / token verbatim.\n"
        "        // Redact via the same boundary helper before they land in span\n"
        "        // status, recordException event, or exported attributes.\n"
        "        const safeMessage = String(redact(rawMessage));\n"
        "        span.setStatus({ code: SpanStatusCode.ERROR, message: safeMessage });\n"
        "        if (err instanceof Error) {\n"
        "          // Build the OTel `exception` event manually rather than calling\n"
        "          // `span.recordException(err)` so the auto-populated\n"
        "          // `exception.message` / `exception.stacktrace` attributes go\n"
        "          // through the same redactor.\n"
        "          const safeStack = err.stack ? String(redact(err.stack)) : undefined;\n"
        "          const eventAttrs: Record<string, string> = {\n"
        "            'exception.type': err.name || 'Error',\n"
        "            'exception.message': safeMessage,\n"
        "          };\n"
        "          if (safeStack !== undefined) {\n"
        "            eventAttrs['exception.stacktrace'] = safeStack;\n"
        "          }\n"
        "          span.addEvent('exception', eventAttrs);\n"
        "        }\n",
        "        span.setStatus({ code: SpanStatusCode.ERROR });\n"
        "        span.addEvent('exception', {\n"
        "          'exception.type': err instanceof Error ? err.name || 'Error' : 'Error',\n"
        "        });\n",
    ),
)
_TELEMETRY_PURPOSE = (
    "export tool identity and status metadata without request, response, or error content"
)
# The reviewed correction from aptl@1838b7fd89d78951f555aff69229e7f227ba78b8:
# rule-writing tools send raw XML request bodies.
_RULE_SCHEMA_PATH = "src/tools/api-definitions.ts"
_RULE_SCHEMA_SOURCE_SHA256 = "a78b9a41dcfb6d40fde2d3c1abf6fb86ab89a7280097543f715ff9b0dba86c18"
_RULE_SCHEMA_REPLACEMENTS = (
    (
        "            type: 'object',\n"
        "            description: 'Request body for POST/PUT requests',\n",
        "            anyOf: [{ type: 'object' }, { type: 'string' }],\n"
        "            description: 'Request body for POST/PUT requests. Use a string for raw payloads such as XML.',\n",
    ),
    (
        "              type: 'object',\n"
        "              description: 'Override or add request body data',\n",
        "              anyOf: [{ type: 'object' }, { type: 'string' }],\n"
        "              description: 'Override request body data. Use a string for raw payloads such as XML.',\n",
    ),
)
_RULE_SCHEMA_PURPOSES = {
    "mcp-red-sources.tar": "keep the shared MCP request schema consistent with raw-payload handlers",
    "mcp-blue-sources.tar": "accept raw XML payloads for declared rule-writing tools",
}


def _adapt_source(package: str, relative: str, data: bytes) -> bytes:
    """Apply the reviewed telemetry and rule-schema adaptations to the shared MCP source."""

    if package != COMMON_PACKAGE:
        return data
    if relative == _TELEMETRY_PATH:
        name, reviewed_sha256, replacements = (
            "telemetry", _TELEMETRY_SOURCE_SHA256, _TELEMETRY_REPLACEMENTS
        )
    elif relative == _RULE_SCHEMA_PATH:
        name, reviewed_sha256, replacements = (
            "rule schema", _RULE_SCHEMA_SOURCE_SHA256, _RULE_SCHEMA_REPLACEMENTS
        )
    else:
        return data
    if hashlib.sha256(data).hexdigest() != reviewed_sha256:
        raise RuntimeError(f"reviewed MCP {name} source changed unexpectedly")

    text = data.decode("utf-8")
    for before, after in replacements:
        if text.count(before) != 1:
            raise RuntimeError(f"reviewed MCP {name} adaptation no longer applies")
        text = text.replace(before, after)
    return text.encode("utf-8")


def _package_members(repo: pathlib.Path, revision: str, package: str) -> tuple[str, ...]:
    prefix = f"mcp/{package}/"
    names = _git(repo, "ls-tree", "-r", "--name-only", revision, "--", prefix).decode(
        "utf-8"
    )
    selected: list[str] = []
    for source_path in names.splitlines():
        relative = source_path.removeprefix(prefix)
        if relative in _ROOT_FILES or relative.startswith("src/"):
            selected.append(relative)
    if not selected or "package.json" not in selected or not any(
        item.startswith("src/") for item in selected
    ):
        raise RuntimeError(f"MCP source package is incomplete: {package}")
    return tuple(sorted(selected))


def _add_file(archive: tarfile.TarFile, name: str, data: bytes) -> None:
    info = tarfile.TarInfo(name)
    info.size = len(data)
    info.mode = 0o644
    info.uid = 0
    info.gid = 0
    info.uname = ""
    info.gname = ""
    info.mtime = 0
    archive.addfile(info, io.BytesIO(data))


def _source_metadata(revision: str, packages: tuple[str, ...], archive_name: str) -> bytes:
    metadata = {
        "license": "MIT",
        "packages": list(packages),
        "repository": SOURCE_REPOSITORY,
        "revision": revision,
        "adaptations": [
            {
                "path": f"{COMMON_PACKAGE}/{_TELEMETRY_PATH}",
                "purpose": _TELEMETRY_PURPOSE,
            },
            {
                "path": f"{COMMON_PACKAGE}/{_RULE_SCHEMA_PATH}",
                "purpose": _RULE_SCHEMA_PURPOSES[archive_name],
            },
        ],
    }
    return (json.dumps(metadata, indent=2, sort_keys=True) + "\n").encode("utf-8")


def build_archive(
    source_repo: pathlib.Path,
    revision: str,
    packages: tuple[str, ...],
    destination: pathlib.Path,
) -> None:
    _validate_revision(source_repo, revision)
    expected_parent = _ASSET_ROOT
    if destination.parent != expected_parent or destination.name not in {
        "mcp-red-sources.tar",
        "mcp-blue-sources.tar",
    }:
        raise ValueError("MCP archive destination is outside the TechVault asset root")
    for parent in (expected_parent, *expected_parent.parents):
        if parent == _REPOSITORY_ROOT.parent:
            break
        if parent.is_symlink():
            raise ValueError("TechVault asset path must not contain symbolic links")
    if destination.is_symlink():
        raise ValueError("MCP archive destination must not be a symbolic link")

    payload = io.BytesIO()
    with tarfile.open(fileobj=payload, mode="w", format=tarfile.USTAR_FORMAT) as archive:
        _add_file(archive, "LICENSE", _git(source_repo, "show", f"{revision}:LICENSE"))
        _add_file(
            archive,
            "SOURCE.json",
            _source_metadata(revision, packages, destination.name),
        )
        for package in packages:
            for relative in _package_members(source_repo, revision, package):
                source_path = f"mcp/{package}/{relative}"
                _add_file(
                    archive,
                    f"{package}/{relative}",
                    _adapt_source(
                        package,
                        relative,
                        _git(source_repo, "show", f"{revision}:{source_path}"),
                    ),
                )

    destination.parent.mkdir(parents=True, exist_ok=True)
    staged = destination.with_name(f".{destination.name}.{os.getpid()}.tmp")
    try:
        staged.write_bytes(payload.getvalue())
        os.replace(staged, destination)
    finally:
        staged.unlink(missing_ok=True)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-repo", required=True, type=pathlib.Path)
    parser.add_argument("--revision", default=SOURCE_REVISION)
    args = parser.parse_args()

    build_archive(
        args.source_repo.resolve(),
        args.revision,
        RED_PACKAGES,
        _ASSET_ROOT / "mcp-red-sources.tar",
    )
    build_archive(
        args.source_repo.resolve(),
        args.revision,
        BLUE_PACKAGES,
        _ASSET_ROOT / "mcp-blue-sources.tar",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
