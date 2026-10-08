#!/usr/bin/env python3
"""Verify, safely extract, and pin the vendored upstream build tree."""

from __future__ import annotations

import argparse
import hashlib
import os
import shutil
import tarfile
import tempfile
from pathlib import Path, PurePosixPath


PYTHON_IMAGE = "python:3.11-slim@sha256:9534e5a8e315485d4061ed659af0fd78a284c015f9b73661b41d6bab25604534"
DEBIAN_IMAGE = "debian:bookworm-slim@sha256:3783cc01769c7b2b1b83a5c5ad96c815348e28ed7da68e2e3687004faa906251"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def _safe_members(archive: tarfile.TarFile) -> list[tarfile.TarInfo]:
    members = archive.getmembers()
    for member in members:
        path = PurePosixPath(member.name)
        if (
            path.is_absolute()
            or ".." in path.parts
            or not path.parts
            or path.parts[0] != "ai-escape-room"
            or member.issym()
            or member.islnk()
            or not (member.isfile() or member.isdir())
        ):
            raise ValueError("upstream archive has an unsafe member")
    return members


def _replace_from(path: Path, source: str, pinned: str) -> None:
    text = path.read_text(encoding="utf-8")
    needle = f"FROM {source}\n"
    if text.count(needle) != 1:
        raise ValueError(f"unexpected base image declaration in {path}")
    path.write_text(text.replace(needle, f"FROM {pinned}\n"), encoding="utf-8")


def prepare(archive_path: Path, destination: Path, expected_sha256: str) -> None:
    if _sha256(archive_path) != expected_sha256:
        raise ValueError("upstream archive checksum mismatch")
    if destination.exists():
        shutil.rmtree(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix=".ai-escape-room-", dir=destination.parent))
    try:
        with tarfile.open(archive_path, "r:gz") as archive:
            archive.extractall(staging, members=_safe_members(archive), filter="data")
        extracted = staging / "ai-escape-room"
        if not (extracted / "docker-compose.yml").is_file():
            raise ValueError("upstream archive root is missing")
        os.replace(extracted, destination)
    finally:
        shutil.rmtree(staging, ignore_errors=True)

    for dockerfile in destination.rglob("Dockerfile"):
        first = dockerfile.read_text(encoding="utf-8").splitlines()[0]
        if first == "FROM python:3.11-slim":
            _replace_from(dockerfile, "python:3.11-slim", PYTHON_IMAGE)
        elif first == "FROM debian:bookworm-slim":
            _replace_from(dockerfile, "debian:bookworm-slim", DEBIAN_IMAGE)
        else:
            raise ValueError(f"unrecognized upstream base image in {dockerfile}")

    hints = destination / "eval-sandbox" / "hints"
    if hints.exists():
        shutil.rmtree(hints)

    launcher = destination / "eval-sandbox" / "start.sh"
    launcher.write_text(
        "#!/bin/bash\n"
        'exec claude --dangerously-skip-permissions "$@"\n',
        encoding="utf-8",
    )
    os.chmod(launcher, 0o755)
    sandbox = destination / "eval-sandbox" / "Dockerfile"
    sandbox_text = sandbox.read_text(encoding="utf-8")
    hint_copy = "COPY hints/hints.txt /opt/lab/hints.txt\n"
    hint_alias = (
        "RUN echo 'cat /app/BRIEFING.md' >> /etc/bash.bashrc \\\n"
        "    && echo 'alias hint=\"cat /opt/lab/hints.txt\"' >> /etc/bash.bashrc\n"
    )
    briefing_only = "RUN echo 'cat /app/BRIEFING.md' >> /etc/bash.bashrc\n"
    welcome_hint = "    Type hint to see hints"
    for fragment in (hint_copy, hint_alias, welcome_hint):
        if sandbox_text.count(fragment) != 1:
            raise ValueError(f"unexpected upstream shell-hint fragment: {fragment!r}")
    sandbox_text = sandbox_text.replace(hint_copy, "")
    sandbox_text = sandbox_text.replace(hint_alias, briefing_only)
    sandbox_text = sandbox_text.replace(welcome_hint, "")
    sandbox.write_text(sandbox_text, encoding="utf-8")
    with sandbox.open("a", encoding="utf-8") as handle:
        handle.write(
            "\nCOPY claude /usr/local/bin/claude\n"
            "COPY start.sh /app/start.sh\n"
            "ENV CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC=1 DISABLE_AUTOUPDATER=1 IS_SANDBOX=1\n"
            "RUN chmod 0755 /usr/local/bin/claude \\\n"
            "    && chmod 0755 /app/start.sh \\\n"
            "    && mkdir -p /root/.claude \\\n"
            "    && cp /app/BRIEFING.md /root/.claude/CLAUDE.md \\\n"
            "    && printf \\\"\\nexport IS_SANDBOX=1\\nalias "
            "claude='claude --dangerously-skip-permissions'\\n\\\" >> /etc/bash.bashrc \\\n"
            "    && /usr/local/bin/claude --version\n"
        )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--archive", required=True, type=Path)
    parser.add_argument("--destination", required=True, type=Path)
    parser.add_argument("--sha256", required=True)
    args = parser.parse_args()
    prepare(args.archive, args.destination, args.sha256)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
