"""Networkless CLI over the shared infrastructure-kit proposal contracts."""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Mapping
from typing import TextIO

from . import kits

EXIT_OK = 0
EXIT_BLOCKING = 1
EXIT_USAGE = 2
EXIT_TOOL_FAILURE = 3
_MAX_PARAMETER_DOCUMENT_BYTES = 64 * 1024


def _terminal_text(value: object) -> str:
    """Render untrusted catalog text without terminal control characters."""

    return "".join(
        character
        if ord(character) >= 0xA0 or 0x20 <= ord(character) < 0x7F
        else f"\\u{ord(character):04x}"
        for character in str(value)
    )


def _source(args: argparse.Namespace) -> kits.KitSource:
    """Build the immutable staged-source descriptor from parsed arguments."""

    return kits.KitSource(
        id=args.source_id, revision=args.source_revision, root=args.source_root
    )


def _source_arguments(parser: argparse.ArgumentParser) -> None:
    """Add the shared staged-source arguments to one command parser."""

    parser.add_argument("source_root", help="staged local catalog source root")
    parser.add_argument("--source-id", required=True, help="stable catalog source id")
    parser.add_argument(
        "--source-revision", required=True, help="immutable catalog source revision"
    )


def _format_argument(parser: argparse.ArgumentParser) -> None:
    """Add the stable machine-output switch to one command parser."""

    parser.add_argument("--json", action="store_true", help="emit stable JSON")


def _mutation_arguments(
    parser: argparse.ArgumentParser,
    *,
    release: bool,
    namespace: bool,
    target: bool,
    materialization: bool,
) -> None:
    """Add the arguments shared by pack mutation commands."""

    parser.add_argument("pack_root", help="existing environment-pack root")
    if release:
        _source_arguments(parser)
        parser.add_argument("kit_id")
        parser.add_argument("kit_version")
    if materialization:
        parser.add_argument("materialization_id")
    if namespace:
        parser.add_argument("--namespace", required=True)
    if target:
        parser.add_argument("--target-sdl", required=True)
    if release:
        parser.add_argument(
            "--parameters",
            choices=("-",),
            help="read a JSON parameter mapping from stdin; values are never accepted in argv",
        )
    parser.add_argument("--preview", action="store_true", help="write nothing")
    _format_argument(parser)


def _parser() -> argparse.ArgumentParser:
    """Build the complete command parser without reading process state."""

    parser = argparse.ArgumentParser(
        prog="raes-pack-kit",
        description="Discover and compose catalog-owned infrastructure kits.",
    )
    commands = parser.add_subparsers(dest="command", required=True)
    listing = commands.add_parser("list", help="list validated kit releases")
    _source_arguments(listing)
    _format_argument(listing)
    searching = commands.add_parser("search", help="search validated kit releases")
    _source_arguments(searching)
    searching.add_argument("query")
    _format_argument(searching)
    inspecting = commands.add_parser("inspect", help="inspect one exact kit release")
    _source_arguments(inspecting)
    inspecting.add_argument("kit_id")
    inspecting.add_argument("kit_version")
    _format_argument(inspecting)
    add = commands.add_parser("add", help="preview or add one kit")
    _mutation_arguments(
        add, release=True, namespace=True, target=True, materialization=False
    )
    update = commands.add_parser("update", help="preview or update one kit")
    _mutation_arguments(
        update, release=True, namespace=False, target=False, materialization=True
    )
    replace = commands.add_parser("replace", help="preview or replace one kit")
    _mutation_arguments(
        replace, release=True, namespace=True, target=True, materialization=True
    )
    remove = commands.add_parser("remove", help="preview or remove one kit")
    _mutation_arguments(
        remove, release=False, namespace=False, target=False, materialization=True
    )
    return parser


def _parameters(args: argparse.Namespace, stdin: TextIO) -> Mapping[str, object]:
    """Read a bounded duplicate-free JSON parameter mapping from stdin."""

    if not getattr(args, "parameters", None):
        return {}

    def object_pairs(pairs: list[tuple[str, object]]) -> dict[str, object]:
        """Reject duplicate JSON object members while decoding."""

        document: dict[str, object] = {}
        for key, value in pairs:
            if key in document:
                raise ValueError("duplicate JSON member")
            document[key] = value
        return document

    def invalid_constant(_value: str) -> object:
        """Reject JSON extensions for non-finite numeric values."""

        raise ValueError("non-finite JSON number")

    try:
        payload = stdin.read(_MAX_PARAMETER_DOCUMENT_BYTES + 1)
        if len(payload.encode("utf-8")) > _MAX_PARAMETER_DOCUMENT_BYTES:
            raise ValueError("parameter document is too large")
        document = json.loads(
            payload,
            object_pairs_hook=object_pairs,
            parse_constant=invalid_constant,
        )
    except ValueError as exc:
        raise kits.KitError("parameter input is not valid JSON") from exc
    if not isinstance(document, dict):
        raise kits.KitError("parameter input must be a JSON mapping")
    return document


def _emit(value: object, *, as_json: bool, stdout: TextIO) -> None:
    """Render one bounded discovery or proposal document."""

    if as_json:
        print(json.dumps(value, indent=2, sort_keys=True), file=stdout)
        return
    if isinstance(value, list):
        for item in value:
            if isinstance(item, dict):
                print(
                    f"{item.get('id')}@{item.get('version')} — "
                    f"{_terminal_text(item.get('title'))}",
                    file=stdout,
                )
        return
    if isinstance(value, dict) and "operation" in value:
        print(
            f"{value['operation']} {value['kit']['id']}@{value['kit']['version']}",
            file=stdout,
        )
        print("files:", file=stdout)
        for rel in value["files"]:
            print(f"  {rel}", file=stdout)
        for item in value["diagnostics"]:
            print(f"blocking: {item['code']}", file=stdout)
        return
    print(json.dumps(value, indent=2, sort_keys=True), file=stdout)


def _discovery(args: argparse.Namespace, stdout: TextIO) -> int:
    """Run one catalog discovery command."""

    source = _source(args)
    catalog = kits.build_kit_catalog((source,))
    if args.command == "list":
        entries = catalog["entries"]
    elif args.command == "search":
        entries = list(kits.search_catalog(catalog, args.query))
    else:
        release = kits.source_release(source, args.kit_id, args.kit_version)
        _emit(kits.inspect_kit(release), as_json=args.json, stdout=stdout)
        return EXIT_OK
    _emit(entries, as_json=args.json, stdout=stdout)
    return EXIT_OK


def _proposal(
    args: argparse.Namespace, stdin: TextIO
) -> kits.KitProposal:
    """Build one mutation proposal from parsed command arguments."""

    if args.command == "remove":
        proposal = kits.propose_remove(
            args.pack_root, materialization_id=args.materialization_id
        )
    else:
        source = _source(args)
        release = kits.source_release(source, args.kit_id, args.kit_version)
        parameters = _parameters(args, stdin)
        if args.command == "add":
            proposal = kits.propose_add(
                args.pack_root,
                release,
                source,
                namespace=args.namespace,
                target_sdl=args.target_sdl,
                parameters=parameters,
            )
        elif args.command == "update":
            proposal = kits.propose_update(
                args.pack_root,
                release,
                source,
                materialization_id=args.materialization_id,
                parameters=parameters,
            )
        else:
            proposal = kits.propose_replace(
                args.pack_root,
                release,
                source,
                materialization_id=args.materialization_id,
                namespace=args.namespace,
                target_sdl=args.target_sdl,
                parameters=parameters,
            )
    return proposal


def main(
    argv: list[str] | None = None,
    *,
    stdin: TextIO | None = None,
    stdout: TextIO | None = None,
    stderr: TextIO | None = None,
) -> int:
    """Run one discovery or mutation command with the shared exit contract."""

    stdin = stdin or sys.stdin
    stdout = stdout or sys.stdout
    stderr = stderr or sys.stderr
    exit_code = EXIT_OK
    try:
        args = _parser().parse_args(argv)
        if args.command in {"list", "search", "inspect"}:
            exit_code = _discovery(args, stdout)
        else:
            proposal = _proposal(args, stdin)
            document = kits.proposal_document(proposal)
            _emit(document, as_json=args.json, stdout=stdout)
            if proposal.diagnostics:
                exit_code = EXIT_BLOCKING
            elif not args.preview:
                kits.apply_proposal(proposal)
    except kits.KitRecoveryError as exc:
        print(f"error: {exc}", file=stderr)
        print(f"recovery: {_terminal_text(exc.recovery_path)}", file=stderr)
        exit_code = EXIT_TOOL_FAILURE
    except kits.KitError as exc:
        # KitError messages are bounded and value-free by contract.
        print(f"error: {exc}", file=stderr)
        exit_code = EXIT_BLOCKING
    except (OSError, RuntimeError):
        print("error: kit tool failure", file=stderr)
        exit_code = EXIT_TOOL_FAILURE
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
