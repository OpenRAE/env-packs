"""Host-scoped, session-local authoring over the canonical pack libraries.

Sources are immutable admitted trees, not user-supplied arbitrary paths. The
launching host owns the principal, source visibility, trusted parent directories
and operation grants. One instance is one principal/session. This module does
not listen on a network, acquire credentials, execute pack code or log payloads.
"""
from __future__ import annotations

import copy
import dataclasses
import json
import os
import re
import shutil
import threading
import uuid
from datetime import date
from collections.abc import Mapping
from functools import partial
from pathlib import Path
from typing import Any, TypeVar

from jsonschema import Draft202012Validator
from raes import SDLError

from . import _pack_fs, catalog, check, distribution, kits, validation, wizard
from ._authoring_safety import admit_members, sensitive_member
from ._authoring_tools import TOOLS
from .digest import PackDigestError

VERSION = "raes-pack-authoring/v1"
_MAX_INPUT = 65536
_MAX_OUTPUT = 2 * 1024 * 1024
_MAX_PROPOSALS = 32
_CODE = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9._-]{0,127}$")
_SDL_INVALID = "sdl.invalid"
Json = dict[str, Any]
_Value = TypeVar("_Value")
_Preparation = tuple[Json, kits._PackSnapshot, tuple[kits.KitSource, kits._PackSnapshot, str, str] | None, str, str]


class _InvalidInput(ValueError):
    """An explicitly identified boundary refusal, not an internal failure."""


def _envelope(status: int, result: object = None, *, code: str | None = None,
              authority: str = "raes-env-packs") -> Json:
    """Wrap a shared result with a bounded transport status and authority."""
    return {"version": VERSION, "status": status, "authority": authority,
            "result": result, "diagnostics": [{"code": code}] if code else []}


def _admit_scalar(item: object, max_bytes: int) -> None:
    """Reject unsupported scalars, oversized strings and secret-shaped values."""
    if isinstance(item, str):
        if len(item.encode("utf-8")) > max_bytes or validation._secret_value(item):
            raise _InvalidInput("document value")
    elif item is not None and not isinstance(item, (bool, int, float)):
        raise _InvalidInput("document type")


def _document_children(item: object, max_bytes: int) -> list[object]:
    """Validate one JSON-like node and expose its children for bounded traversal."""
    children = []
    if isinstance(item, dict):
        if not all(isinstance(key, str) for key in item):
            raise _InvalidInput("document keys")
        children = [part for pair in item.items() for part in pair]
    elif isinstance(item, (list, tuple)):
        children = list(item)
    else:
        _admit_scalar(item, max_bytes)
    return children


def _bounded(value: object, *, max_bytes: int) -> None:
    """Bound recursive shape before serialization, and reject secret-shaped values."""
    pending = [(value, 0)]
    count = 0
    while pending:
        item, depth = pending.pop()
        count += 1
        if depth > 32 or count > 32768:
            raise _InvalidInput("document limit")
        pending.extend((part, depth + 1) for part in _document_children(item, max_bytes))
    try:
        size = len(json.dumps(value, ensure_ascii=True, allow_nan=False).encode("utf-8"))
    except ValueError as exc:
        raise _InvalidInput("document encoding") from exc
    if size > max_bytes:
        raise _InvalidInput("document bytes")


def _trusted_root(path: str | Path) -> Path:
    """Admit a host-selected root without following symlink ancestors."""
    absolute = Path(os.path.abspath(path))
    if sensitive_member(absolute.as_posix()):
        raise _InvalidInput("root not admitted")
    current = Path(absolute.anchor)
    for part in absolute.parts[1:]:
        current /= part
        if current.is_symlink():
            raise _InvalidInput("root link")
    if not absolute.is_dir():
        raise _InvalidInput("root unavailable")
    return absolute


def _admit_tree(path: str | Path, *, max_members: int = 16384) -> None:
    """Reject unsafe members before opening content in a host-selected tree."""
    root = _trusted_root(path)
    _real, fd = _pack_fs.open_root(root)
    try:
        members = _pack_fs.inventory(fd, max_members=max_members)
        admit_members(members)
    finally:
        os.close(fd)


@dataclasses.dataclass
class _Pending(object):
    """An exact session-bound proposal and its retained review/result bytes."""

    kind: str
    value: wizard.Proposal | kits.KitProposal | _Preparation
    review: Json
    size: int
    result: Json | None = None


def _retained_bytes(value: object) -> int:
    """Count retained proposal payload recursively without serializing it."""
    size = 0
    if isinstance(value, (str, bytes)):
        size = len(value.encode("utf-8") if isinstance(value, str) else value)
    elif dataclasses.is_dataclass(value):
        size = sum(_retained_bytes(getattr(value, f.name)) for f in dataclasses.fields(value))
    elif isinstance(value, dict):
        size = sum(_retained_bytes(k) + _retained_bytes(v) for k, v in value.items())
    elif isinstance(value, (list, tuple)):
        size = sum(map(_retained_bytes, value))
    return size


def _lookup(mapping: Mapping[str, _Value], key: str) -> _Value:
    """Resolve a host- or session-owned handle without exposing its value."""
    if key not in mapping:
        raise _InvalidInput("unknown handle")
    return mapping[key]


def _validate_sources(mapping: Mapping[str, catalog.Source | kits.KitSource | str]) -> None:
    """Admit each host-supplied handle and root before session use."""
    for key, source in mapping.items():
        if not isinstance(key, str) or not _CODE.fullmatch(key):
            raise ValueError("source handle")
        _trusted_root(source if isinstance(source, str) else source.root)
        if not isinstance(source, str):
            _bounded({"id": source.id, "revision": source.revision}, max_bytes=1024)


class AuthoringSession(object):
    """A host-owned scope; only explicit operation grants enable mutations.

    ``packs`` and ``kit_sources`` map opaque handles to admitted source records.
    ``releases`` maps handles to built release evidence directories. A write root
    must be dedicated author storage with parents controlled by the host. Default
    grants expose proposals only. Handles are not evidence of human approval:
    the MCP host must enforce its confirmation policy when invoking apply.
    """

    def __init__(self, *, packs: Mapping[str, catalog.Source] | None = None,
                 kit_sources: Mapping[str, kits.KitSource] | None = None,
                 releases: Mapping[str, str] | None = None,
                 write_root: str | Path | None = None,
                 allow_writes: bool = False, allow_prepare: bool = False) -> None:
        self._packs = dict(packs or {})
        self._kits = dict(kit_sources or {})
        self._releases = dict(releases or {})
        if sum(map(len, (self._packs, self._kits, self._releases))) > 32:
            raise ValueError("source limit")
        for mapping in (self._packs, self._kits, self._releases):
            _validate_sources(mapping)
        self._write_root = _trusted_root(write_root) if write_root is not None else None
        self._allow_writes = allow_writes
        self._allow_prepare = allow_prepare
        self._pending: dict[str, _Pending] = {}
        self._lock = threading.RLock()
        self._closed = False

    def close(self) -> None:
        """Revoke retained proposals and prevent further session operations."""
        with self._lock:
            self._pending.clear()
            self._closed = True

    def __enter__(self) -> AuthoringSession:
        return self

    def __exit__(self, *_exc: object) -> None:
        self.close()

    def call(self, name: str, arguments: Json) -> Json:
        """Dispatch a bounded closed request without exposing exception prose."""
        with self._lock:
            if self._closed or not isinstance(name, str) or name not in TOOLS:
                return _envelope(2, code="authoring.operation-denied")
            try:
                _bounded(arguments, max_bytes=_MAX_INPUT)
                if not Draft202012Validator(TOOLS[name][1]).is_valid(arguments):
                    raise _InvalidInput("request schema")
                if kits._secret_shape_violations(arguments.get("parameters", {})):
                    raise _InvalidInput("secret parameters")
                if self._write_root is not None:
                    _trusted_root(self._write_root)
                result = self._dispatch(name, copy.deepcopy(arguments))
                _bounded(result, max_bytes=_MAX_OUTPUT)
            except kits.KitRecoveryError as exc:
                # The shared transaction preserves the original recovery tree.
                recovery = {"recovery_path": exc.recovery_path}
                try:
                    _bounded(recovery, max_bytes=4096)
                except _InvalidInput:
                    recovery = None
                result = _envelope(3, recovery, code="authoring.recovery-required")
            except (kits.KitError, wizard.WizardError, PackDigestError, SDLError,
                    _pack_fs.PackFilesystemError):
                result = _envelope(1, code="authoring.input-or-conflict")
            except _InvalidInput:
                result = _envelope(2, code="authoring.invalid-input")
            except OSError:
                result = _envelope(3, code="authoring.filesystem-unavailable")
            except Exception:
                result = _envelope(3, code="authoring.tool-failure")
            return result

    def _source(self, key: str) -> catalog.Source:
        """Look up and statically admit one configured pack source."""
        source = _lookup(self._packs, key)
        _admit_tree(source.root)
        return source

    def _dispatch(self, name: str, args: Json) -> Json:
        """Dispatch only the explicitly registered pack operations."""
        handlers = {
            "pack_search": partial(self._catalog, "pack_search"),
            "pack_inspect": partial(self._catalog, "pack_inspect"),
            "pack_compatibility_card": partial(self._catalog, "pack_compatibility_card"),
            "pack_validate": self._validate,
            "pack_explain": self._explain,
            "pack_examples": self._examples,
            "pack_scaffold": lambda arguments: self._scaffold(arguments["inputs"]),
            "pack_kits": partial(self._kit_discovery, "pack_kits"),
            "pack_kit_inspect": partial(self._kit_discovery, "pack_kit_inspect"),
            "pack_compose": self._compose,
            "pack_prepare": lambda arguments: self._execute("pack_prepare", arguments["proposal"]),
            "pack_apply": lambda arguments: self._execute("pack_apply", arguments["proposal"]),
            "pack_sdl": _sdl,
            "pack_publication_plan": self._publication,
        }
        return handlers[name](args)

    def _validate(self, args: Json) -> Json:
        """Return the same static validation report as the CLI."""
        source = self._source(args["source"])
        result = validation.validate_pack(source.root)
        document = json.loads(check.render_json(check.build_report(result, Path(source.root).name)))
        return _envelope(0 if result.ok else 1, document)

    @staticmethod
    def _explain(args: Json) -> Json:
        """Present a stable diagnostic code without authored exception prose."""
        if not _CODE.fullmatch(args["code"]):
            raise _InvalidInput("diagnostic code")
        return _envelope(0, dataclasses.asdict(check.presentation_for(args["code"])))

    @staticmethod
    def _examples(args: Json) -> Json:
        """Preview the shared starter and its optional layers without writes."""
        inputs = {"version": wizard.WIZARD_INPUT_VERSION, "pack_id": "example-pack",
                  "route": args.get("route", "minimal")}
        proposal = wizard.build_proposal(wizard.normalize_inputs(inputs))
        return _envelope(0, {"inputs": inputs, "routes": list(wizard.ROUTES),
                             "preview": wizard.review_document(proposal, "example-pack")})

    def _catalog(self, name: str, args: Json) -> Json:
        """Project admitted pack records with the shared catalog authority."""
        try:
            date.fromisoformat(args["as_of"])
        except ValueError as exc:
            raise _InvalidInput("catalog date") from exc
        keys = sorted(self._packs) if name == "pack_search" else [args["source"]]
        sources = [self._source(key) for key in keys]
        document, diagnostics = catalog.build_catalog(sources, as_of=args["as_of"])
        if catalog.validate_document(document):
            raise _InvalidInput("catalog inputs")
        if name == "pack_search":
            query = args.get("query", "").casefold()
            entries = tuple(entry for entry in document.entries
                            if query in json.dumps(entry, ensure_ascii=False).casefold())
            document = dataclasses.replace(document, entries=entries)
        return _envelope(1 if any(d.blocking for d in diagnostics) else 0,
                         {"catalog": json.loads(catalog.render_json(document)),
                          "sources": [{"handle": key, "id": source.id, "revision": source.revision}
                                      for key, source in zip(keys, sources)],
                          "diagnostics": [dataclasses.asdict(d) for d in diagnostics]})

    def _save(self, kind: str, value: wizard.Proposal | kits.KitProposal | _Preparation, review: Json) -> Json:
        """Retain an immutable, bounded proposal only after its review is admitted."""
        if len(self._pending) >= _MAX_PROPOSALS:
            raise _InvalidInput("proposal limit")
        token = uuid.uuid4().hex
        document = {**review, "proposal": token}
        # Refuse oversized/secret output before making its handle actionable.
        _bounded(document, max_bytes=_MAX_OUTPUT - 1024)
        size = _retained_bytes(value) + _retained_bytes(document)
        if size + sum(item.size for item in self._pending.values()) > 64 * 1024 * 1024:
            raise _InvalidInput("session storage limit")
        self._pending[token] = _Pending(kind, copy.deepcopy(value), copy.deepcopy(document), size)
        return _envelope(0, document)

    def _scaffold(self, inputs: Json) -> Json:
        """Capture the shared wizard proposal and disclose its create-only target."""
        if self._write_root is None:
            raise _InvalidInput("write root required for a target proposal")
        proposal = wizard.build_proposal(wizard.normalize_inputs(inputs))
        target = self._write_root / proposal.pack_id
        review = wizard.review_document(proposal, str(target))
        review["effects"] = [{"kind": "filesystem-write", "target": str(target)}]
        return self._save("scaffold", proposal, review)

    def _kit_discovery(self, name: str, args: Json) -> Json:
        """Discover already admitted local kits without acquisition or execution."""
        source = _lookup(self._kits, args["source"])
        _admit_tree(Path(source.root) / "kits")
        if name == "pack_kits":
            document = kits.build_kit_catalog((source,))
            return _envelope(0, {"catalog": document,
                                 "matches": kits.search_catalog(document, args.get("query", ""))})
        release = kits.source_release(source, args["kit"], args["version"])
        return _envelope(0, kits.inspect_kit(release))

    def _compose(self, args: Json) -> Json:
        """Capture composition inputs and disclose preparation before any write."""
        if self._write_root is None:
            raise _InvalidInput("preparation root required")
        required = {"kit_source", "kit", "version"} if args["operation"] != "remove" else set()
        if args["operation"] in {"add", "replace"}:
            required.update({"namespace", "target_sdl"})
        if args["operation"] != "add":
            required.add("materialization")
        if not required.issubset(args):
            raise _InvalidInput("operation fields")
        source = self._source(args["source"])
        target = Path(source.root)
        if target.parent != self._write_root:
            raise _InvalidInput("target not writable")
        base = kits._capture_pack(target)
        release_data = None
        if args["operation"] != "remove":
            source_kit = _lookup(self._kits, args["kit_source"])
            _admit_tree(Path(source_kit.root) / "kits")
            release = kits.source_release(source_kit, args["kit"], args["version"])
            release_data = (source_kit, kits._capture_pack(release.root), release.id, release.version)
        scratch = self._write_root / (".prepare-" + uuid.uuid4().hex)
        value = (args, base, release_data, str(scratch), str(target))
        review = {"target": str(target), "preparation_target": str(scratch),
                  "operation": args["operation"],
                  "assumptions": ["Local imports only; no registry policy files.",
                                  "Preparation changes only the private scratch tree; review its result before apply."],
                  "effects": [{"kind": "filesystem-write", "target": str(scratch),
                               "change": "Copy admitted inputs, compose through RAES, and remove temporary files."}],
                  "input_files": [{"path": f.path, "sha256": f.digest, "size": len(f.content)}
                                  for f in base.files]}
        if release_data:
            review["kit_input_files"] = [{"path": f.path, "sha256": f.digest, "size": len(f.content)}
                                         for f in release_data[1].files]
        return self._save("prepare", value, review)

    def _execute(self, name: str, token: str) -> Json:
        """Consume an exact proposal only within its session's operation grant."""
        pending = _lookup(self._pending, token)
        needed = "prepare" if name == "pack_prepare" else "apply"
        permitted = {"prepare": self._allow_prepare, "apply": self._allow_writes}
        if not permitted[needed]:
            return _envelope(2, code="authoring.operation-denied")
        if (pending.kind == "prepare") != (needed == "prepare"):
            raise _InvalidInput("proposal kind")
        if pending.result is not None:
            return copy.deepcopy(pending.result)
        if needed == "prepare":
            result = self._prepare(pending.value)
        else:
            result = self._apply(pending, token)
        if needed == "prepare" or result["status"] == 0:
            pending.result = copy.deepcopy(result)
        return result

    def _apply(self, pending: _Pending, token: str) -> Json:
        """Apply text-reviewed bytes through the existing guarded transactions."""
        if any((change.get(side) or {}).get("binary") for change in pending.review.get("changes", [])
               for side in ("before", "after")):
            return _envelope(2, code="authoring.binary-review-required")
        if pending.kind == "scaffold":
            target = wizard.write_proposal(pending.value, str(self._write_root))
        else:
            _admit_tree(pending.value.pack_root)
            target = kits.apply_proposal(pending.value)
        return _envelope(0, {"target": target, "operation": "applied", "proposal": token})

    def _prepare(self, value: _Preparation) -> Json:
        """Compose captured inputs in private scratch, then retain the exact review."""
        args, base, release_data, scratch_path, target = value
        _admit_tree(target)
        if kits._capture_pack(target).digest != base.digest:
            raise kits.KitError("input changed")
        scratch = Path(scratch_path)
        scratch.mkdir(mode=0o700)
        try:
            pack = scratch / Path(target).name
            kits._write_snapshot(pack, {f.path: f.content for f in base.files})
            common = {"pack_root": pack}
            operation = args["operation"]
            if operation != "remove":
                original_source, snapshot, kit_id, version = release_data
                kit_root = scratch / "catalog" / "kits" / kit_id / version
                kit_root.parent.mkdir(parents=True, mode=0o700)
                kits._write_snapshot(kit_root, {f.path: f.content for f in snapshot.files})
                source = dataclasses.replace(original_source, root=str(scratch / "catalog"))
                common.update(release=kits.load_kit_release(kit_root), source=source,
                              parameters=args.get("parameters", {}))
            if operation in {"add", "replace"}:
                common.update(namespace=args["namespace"], target_sdl=args["target_sdl"])
            if operation in {"remove", "update", "replace"}:
                common["materialization_id"] = args["materialization"]
            functions = {"add": kits.propose_add, "remove": kits.propose_remove,
                         "update": kits.propose_update, "replace": kits.propose_replace}
            proposal = dataclasses.replace(functions[operation](**common), pack_root=target)
            if proposal.diagnostics:
                return _envelope(1, kits.proposal_document(proposal))
            review = kits.review_document(proposal)
            review["effects"] = [{"kind": "filesystem-write", "target": target}]
            return self._save("kit", proposal, review)
        finally:
            # Only the exact private directory just created by this call.
            shutil.rmtree(scratch)

    def _publication(self, args: Json) -> Json:
        """Plan shared publication effects without assessing or mutating a registry."""
        root = _lookup(self._releases, args["source"])
        _admit_tree(root)
        # OCI repository names, not URLs, credentials, filesystem paths or queries.
        if not re.fullmatch(r"[a-z0-9][a-z0-9.:-]*/[a-z0-9][a-z0-9._/-]*", args["repository"]):
            raise _InvalidInput("repository")
        if ".." in args["repository"] or not re.fullmatch(r"\w[\w.-]{0,127}", args["reference"], re.ASCII):
            raise _InvalidInput("reference")
        selector = distribution.Selector(repository=args["repository"], reference=args["reference"])
        plan = distribution.plan_publish(root, selector=selector)
        document = json.loads(plan.render_json())
        # A plan observes effects; it is never a publication verification verdict.
        document["publication_verified"] = False
        document["readiness"] = "not-assessed"
        for diagnostic in document["diagnostics"]:
            diagnostic["path"] = None
        return _envelope(0 if not plan.diagnostics else 1, document)


def _safe_diagnostics(items: list[Any]) -> list[Json]:
    """Keep upstream identity/severity/ranges; omit authored exception prose."""
    result = []
    for item in items[:100]:
        row = item if isinstance(item, dict) else dataclasses.asdict(item)
        code = row.get("code", _SDL_INVALID)
        if not isinstance(code, str) or not _CODE.fullmatch(code):
            code = _SDL_INVALID
        severity = row.get("severity", "error")
        severity = getattr(severity, "value", severity)
        result.append({"code": code, "severity": severity if severity in {"error", "warning", "info"} else "error",
                       "explanation": check.presentation_for(code).explanation})
        location = row.get("range")
        if isinstance(location, dict) and all(
            isinstance(location.get(end), dict)
            and all(type(location[end].get(axis)) is int and 0 <= location[end][axis] <= _MAX_INPUT
                    for axis in ("line", "column")) for end in ("start", "end")
        ):
            result[-1]["range"] = {end: {axis: location[end][axis] for axis in ("line", "column")}
                                   for end in ("start", "end")}
    return result


def _sdl(args: Json) -> Json:
    """Delegate language, compilation and planning semantics to public RAES APIs."""
    from raes import parse_sdl
    from raes.language_service import language_completions, language_diagnostics, language_format
    from raes_processor.compiler import compile_scenario_runtime_model
    from raes_processor.planner import plan
    from raes_backend_stubs.stubs import create_stub_manifest

    operation, content = args["operation"], args["content"]
    try:
        if operation == "completion":
            document = language_completions(
                content, cursor_path=args.get("cursor_path", ""), prefix=args.get("prefix", ""),
            )
        elif operation in {"diagnostics", "format"}:
            document = (language_diagnostics if operation == "diagnostics" else language_format)(content)
        else:
            scenario = parse_sdl(content)
            document = {"stage": "parse", "diagnostics": [], "status": "parsed"}
            if operation in {"compile", "plan"}:
                model = compile_scenario_runtime_model(scenario, parameters=args.get("parameters", {}))
                document.update(stage="compile", status="compiled", nodes=len(model.node_deployments),
                                networks=len(model.networks), diagnostics=list(model.diagnostics))
                if operation == "plan":
                    execution = plan(model, create_stub_manifest())
                    document.update(stage="plan", status="planned", is_valid=execution.is_valid,
                                    diagnostics=list(execution.diagnostics),
                                    resources={name: len(getattr(execution, name).resources)
                                               for name in ("provisioning", "orchestration", "evaluation")},
                                    basis="RAES reference stub manifest; no runtime execution")
        document["diagnostics"] = _safe_diagnostics(document.get("diagnostics", []))
        blocking = document.get("status") == "invalid" or any(d["severity"] == "error" for d in document["diagnostics"])
        return _envelope(1 if blocking else 0, document, authority="raes")
    except SDLError as exc:
        diagnostics = _safe_diagnostics([d.as_dict() for d in getattr(exc, "diagnostics", ())])
        return _envelope(
            1, {"diagnostics": diagnostics or [{"code": _SDL_INVALID, "severity": "error"}]}, authority="raes",
        )
