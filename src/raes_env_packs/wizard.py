"""Progressive environment-pack scaffold wizard (issue #189, ADR 0034).

This replaces the monolithic ``raes-new-pack`` copy-the-whole-template scaffold.
It selects the smallest pack shape that satisfies an author's stated goal,
previews it, writes it as one guarded transaction, and immediately runs the same
static check (:func:`raes_env_packs.validate_pack`) consumers run later.

Boundary (ADR 0009 / 0011 / 0034): this module owns pack **structure** and
pack-aware optional layers only. SDL construction, choices, and diagnostics are
delegated to the public RAES pin — ``raes.language_service.apply_structured_edit``
builds the start-state document and ``raes.parse_sdl`` (through ``validate_pack``)
decides validity. The wizard hard-codes no SDL semantics, defines no second
schema, and never labels parse validation as completion or compilation. RAES-owned
completion and compilation are not approximated here; they remain unavailable
until RAES publishes those contracts and this repo advances its exact pin.

Both front ends — interactive prompts and non-interactive replay for Hub/MCP —
produce one immutable :class:`Proposal`; preview, human render, machine render,
the writer, and the tests all consume that single proposal.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import sys
import tempfile
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import TextIO

import yaml

from . import _transactions
from .validation import validate_pack

# Versioned wire identities. Bump when the machine contract changes shape.
WIZARD_INPUT_VERSION = "raes-pack-wizard-input/v1"
WIZARD_OUTPUT_VERSION = "raes-pack-wizard/v1"

# Sentinel for a deliberate "not sure" answer. It stays visible in the proposal
# and never becomes a silent semantic claim (ADR 0034).
NOT_SURE = "not-sure"

_PACK_ID_RE = re.compile(r"^[a-z0-9][a-z0-9-]*[a-z0-9]$|^[a-z0-9]$")
_MISSING = object()

_RESOURCES = Path(__file__).with_name("resources")
_TEMPLATE = _RESOURCES / "template"

# Canonical pack-relative pointers the generated manifest references.
_PROVENANCE_LEDGER_REL = "docs/provenance-ledger.yaml"
_COMPATIBILITY_REL = "pack.compatibility.yaml"
_GOLDEN_CHECKLIST_REL = "docs/golden-readiness-checklist.md"

# Exit statuses (mirrors the raes-pack-check process contract).
EXIT_OK = 0
EXIT_BLOCKING = 1
EXIT_USAGE = 2


class WizardError(Exception):
    """A bounded, author-facing wizard failure (invalid input or conflict)."""


def validate_pack_id(pack_id: str) -> None:
    """Reject a pack id that is not lowercase kebab-case (matches new_pack)."""

    if not isinstance(pack_id, str) or not _PACK_ID_RE.fullmatch(pack_id):
        raise SystemExit(
            "pack id must be lowercase kebab-case, start/end with a letter or "
            "digit, and contain only a-z, 0-9, and '-'")


def title_from_pack_id(pack_id: str) -> str:
    """Derive a human-readable title from a pack id."""

    return " ".join(part.capitalize() for part in pack_id.split("-"))


def repo_root(start: str | None = None) -> str:
    """Walk up to the checkout root holding ``.git`` and ``environments/``.

    ``.git`` may be a directory or a git-worktree gitfile, so this works from a
    linked worktree as well as a primary checkout.
    """

    here = os.path.abspath(start or os.getcwd())
    while True:
        if (os.path.exists(os.path.join(here, ".git"))
                and os.path.isdir(os.path.join(here, "environments"))):
            return here
        parent = os.path.dirname(here)
        if parent == here:
            raise WizardError(
                "could not find a repo root containing .git and environments/")
        here = parent


# --------------------------------------------------------------------------- #
# Questions
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class Question(object):
    """One ordinary-language question with its stated consequence.

    Every question either carries a safe ``default`` or offers an explicit
    ``allow_not_sure`` route (ADR 0034). A ``required`` question whose answer is
    left not-sure or unanswered blocks the write rather than inventing a value.
    """

    key: str
    prompt: str
    consequence: str
    default: str | None = None
    allow_not_sure: bool = False
    choices: tuple[str, ...] | None = None
    required: bool = False
    # When set, a required question is satisfied ONLY by this exact answer; any
    # other resolved value (e.g. an affirmative gate answered "no") still blocks
    # the write rather than counting as satisfied.
    required_value: str | None = None


_CORE_QUESTIONS: tuple[Question, ...] = (
    Question(
        key="title",
        prompt="What should the pack be called?",
        consequence="Sets the human-readable title in pack.yaml and the catalog.",
        default="",
    ),
    Question(
        key="description",
        prompt="Describe the scenario in one line.",
        consequence="Sets the one-line description in pack.yaml.",
        default="",
    ),
)

_PUBLICATION_CLEARED = Question(
    key="publication_cleared",
    prompt="Is this pack's content cleared for publication?",
    consequence=(
        "A publication-ready pack asserts a release claim. Leave this not-sure "
        "if unsure — it blocks writing rather than asserting a false clearance."),
    default=None,
    allow_not_sure=True,
    required=True,
    required_value="yes",
    choices=("yes", "no"),
)


# --------------------------------------------------------------------------- #
# Capability inventory (the closed, declarative extension seam — ADR 0034)
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class Capability(object):
    """One optional pack layer: its owning contents flag / pointer + generator."""

    key: str
    label: str
    contents_flag: str | None
    manifest_pointer: tuple[str, str] | None
    generate: Callable[["_Context"], dict[str, str]]


@dataclass(frozen=True)
class Route(object):
    """A named, versioned presentation profile over capability selection."""

    key: str
    label: str
    description: str
    default_capabilities: tuple[str, ...]
    extra_questions: tuple[Question, ...] = ()


@dataclass(frozen=True)
class _Context(object):
    """Resolved, normalized inputs a generator reads. No I/O, no secrets."""

    pack_id: str
    title: str
    description: str


# --------------------------------------------------------------------------- #
# File-body generators
# --------------------------------------------------------------------------- #
def _template_text(rel: str, replacements: Mapping[str, str]) -> str:
    """Read one packaged template resource and apply literal replacements."""

    body = (_TEMPLATE / rel).read_text(encoding="utf-8")
    for old, new in replacements.items():
        body = body.replace(old, new)
    return body


def _build_sdl(context: _Context) -> str:
    """Emit a minimal, RAES-valid start-state document carrying only identity.

    The wizard owns pack identity, not scenario semantics (ADR 0009 / 0034). It
    supplies only the identity *value* (the pack id) and the identity *pointer*
    (``/name``) to RAES's public structured-edit API, which constructs and
    serialises the document; the wizard never hand-writes an SDL fragment or
    node/type/topology. RAES decides validity, and any diagnostic fails closed.
    Node authoring is RAES's, done later with the RAES SDL tools.
    """

    from raes.language_service import apply_structured_edit

    result = apply_structured_edit(
        "{}\n", operation="set", pointer="/name", value=context.pack_id)
    if result.get("status") != "edited" or result.get("diagnostics"):
        raise WizardError(
            "RAES rejected the scenario identity; the wizard does not emit SDL "
            "it cannot validate")
    return result["content"]


def _pack_manifest(
    context: _Context,
    contents: Mapping[str, bool],
    pointers: Mapping[str, str],
) -> str:
    """Render pack.yaml with only the pointers the selected layers add."""

    manifest: dict[str, object] = {
        "name": context.pack_id,
        "title": context.title,
        "version": "0.1.0",
        "status": "draft",
        "description": context.description,
        "authors": ["Your Name <you@example.com>"],
        "license": "© 2026 Your Org. All rights reserved.",
        "requirement": None,
        "contents": {
            "flag_layer": contents.get("flag_layer", False),
            "reference_triangle": contents.get("reference_triangle", False),
            "profile_bundles": contents.get("profile_bundles", False),
        },
        "provenance_ledger": _PROVENANCE_LEDGER_REL,
    }
    for key, value in pointers.items():
        manifest[key] = value
    return yaml.safe_dump(manifest, sort_keys=False, allow_unicode=True)


def _concepts_doc(context: _Context) -> str:
    """Neutral starter body for docs/concepts.md."""

    return (
        f"# {context.title} — concepts\n\n"
        f"{context.description}\n\n"
        "Explain the ideas a participant needs to understand this scenario: the\n"
        "systems involved, the objective, and the reasoning the environment is\n"
        "meant to exercise. Keep it participant-safe.\n"
    )


def _attack_path_doc(context: _Context) -> str:
    """Neutral starter body for docs/attack-path.md."""

    return (
        f"# {context.title} — path model\n\n"
        "Describe the intended route a participant takes through the environment,\n"
        "step by step. This is explanatory design prose, not machine-readable\n"
        "state: the hydrated RAES SDL remains the authority for what is reachable.\n"
    )


def _golden_checklist() -> str:
    """Neutral golden-readiness checklist body."""

    return (
        "# Golden-readiness checklist\n\n"
        "Copy this into a rehearsal report and check what you actually proved.\n\n"
        "- [ ] The range applies from a clean checkout using committed pack content.\n"
        "- [ ] The participant entry surface exists, is documented, and is reachable.\n"
        "- [ ] The happy path is completed by hand from the participant surface.\n"
        "- [ ] Every required RAES objective and success condition is reached.\n"
        "- [ ] Automated rehearsal passes against the same build profile.\n"
        "- [ ] Teardown is run and verified; no live resources remain.\n"
        "- [ ] pack.yaml.status: golden is set only after the above proof exists.\n"
    )


def _participant_readme(context: _Context) -> str:
    """Neutral participant-safe README body."""

    return (
        f"# {context.title}\n\n"
        f"{context.description}\n\n"
        "Participant-safe overview of the scenario. Replace this with the brief a\n"
        "participant should see; keep restricted material out of this file.\n"
    )


def _required_files(context: _Context) -> dict[str, str]:
    """The minimum-complete required tier every generated pack ships."""

    # pack.yaml is filled by build_proposal once the selected pointers are known.
    return {
        "pack.yaml": "",
        f"sdl/{context.pack_id}.sdl.yaml": _build_sdl(context),
        "docs/concepts.md": _concepts_doc(context),
        "docs/attack-path.md": _attack_path_doc(context),
        _PROVENANCE_LEDGER_REL: _template_text(
            _PROVENANCE_LEDGER_REL, {"<name>": context.pack_id}),
    }


def _gen_flag_layer(context: _Context) -> dict[str, str]:
    """Flag/challenge layer: flags, challenges, and a reference CTFd loader."""

    return {
        "flags/placement.yaml": _template_text("flags/placement.yaml", {}),
        "challenges/challenges.yaml": _template_text(
            "challenges/challenges.yaml", {}),
        "ctfd/README.md": _template_text("ctfd/README.md", {}),
    }


def _gen_reference_triangle(context: _Context) -> dict[str, str]:
    """Reference triangle: golden build, tests, and matching walkthrough."""

    return {
        "build/README.md": _template_text("build/README.md", {}),
        "tests/README.md": _template_text("tests/README.md", {}),
        "docs/walkthroughs/README.md": _template_text(
            "docs/walkthroughs/README.md", {}),
        _GOLDEN_CHECKLIST_REL: _golden_checklist(),
    }


def _gen_compatibility(context: _Context) -> dict[str, str]:
    """Compatibility projection plus the participant README and checklist it references."""

    return {
        _COMPATIBILITY_REL: _template_text(
            _COMPATIBILITY_REL,
            {"<name>": context.pack_id, "Human-readable title": context.title}),
        "README.md": _participant_readme(context),
        _GOLDEN_CHECKLIST_REL: _golden_checklist(),
    }


def _gen_profile_bundles(context: _Context) -> dict[str, str]:
    """Delivery/audience profile-bundle layer (manifest + shared content)."""

    bundles = yaml.safe_dump(
        {"schema_version": "environment-pack-profile-bundles/v1", "bundles": []},
        sort_keys=False)
    return {
        "profiles/bundles.yaml": bundles,
        "profiles/_shared/README.md": (
            "# Shared profile content\n\n"
            "Participant-safe content factored once across delivery bundles.\n"),
    }


CAPABILITIES: dict[str, Capability] = {
    "flag_layer": Capability(
        "flag_layer", "CTF flags, challenges, and a reference loader",
        "flag_layer", None, _gen_flag_layer),
    "reference_triangle": Capability(
        "reference_triangle", "Golden build, tests, and matching walkthrough",
        "reference_triangle", None, _gen_reference_triangle),
    "compatibility": Capability(
        "compatibility", "Product/backend compatibility projection",
        None, ("compatibility_manifest", _COMPATIBILITY_REL),
        _gen_compatibility),
    "profile_bundles": Capability(
        "profile_bundles", "Delivery/audience profile bundles",
        "profile_bundles", None, _gen_profile_bundles),
}


ROUTES: dict[str, Route] = {
    "minimal": Route(
        "minimal", "Minimal authored scenario",
        "A paper design: identity, start state, and the docs to understand it.",
        ()),
    "runnable-local": Route(
        "runnable-local", "Runnable local environment",
        "Adds the reference triangle so the scenario can be stood up and tested.",
        ("reference_triangle",)),
    "ai-agent-eval": Route(
        "ai-agent-eval", "AI-agent evaluation",
        "Adds delivery bundles for an agent-benchmark contract.",
        ("profile_bundles",)),
    "security-exercise": Route(
        "security-exercise", "Security exercise",
        "Adds the flag/challenge layer for a capture-the-flag style exercise.",
        ("flag_layer",)),
    "dr-recovery": Route(
        "dr-recovery", "DR / recovery exercise",
        "Adds the reference triangle to build and rehearse a recovery drill.",
        ("reference_triangle",)),
    "product-integration": Route(
        "product-integration", "Product integration test",
        "Adds a compatibility projection for product/backend consumers.",
        ("compatibility",)),
    "publication-ready": Route(
        "publication-ready", "Publication-ready pack",
        "Adds the compatibility projection required to package a release.",
        ("compatibility",), (_PUBLICATION_CLEARED,)),
}


def route_questions(route_id: str) -> tuple[Question, ...]:
    """Return the ordered question set for one route (core + route-specific)."""

    route = ROUTES.get(route_id)
    if route is None:
        raise WizardError(f"unknown route: {route_id}")
    return (*_CORE_QUESTIONS, *route.extra_questions)


# --------------------------------------------------------------------------- #
# Inputs / proposal
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class WizardInputs(object):
    """Normalized, validated authoring inputs — the replay DTO's parsed form."""

    pack_id: str
    route: str
    title: str
    description: str
    capabilities: tuple[str, ...]
    answers: tuple[tuple[str, str], ...]


# title/description are question answers, so they belong in `answers`, not at
# the top level; a top-level one is rejected rather than silently ignored.
_ALLOWED_INPUT_KEYS = frozenset(
    {"version", "pack_id", "route", "answers", "capabilities"})
_DEFAULT_DESCRIPTION = "One line describing the scenario and what a participant does."


def _require_envelope(raw: Mapping[str, object]) -> None:
    """Reject a wizard-input document with a bad version or unknown keys."""

    if raw.get("version") != WIZARD_INPUT_VERSION:
        raise WizardError(
            f"unsupported wizard input version: {raw.get('version')!r}")
    unknown = {key for key in raw if key not in _ALLOWED_INPUT_KEYS}
    if unknown:
        raise WizardError(f"unknown wizard input keys: {sorted(unknown)}")


def _require_pack_id(raw: Mapping[str, object]) -> str:
    """Return a validated pack id or fail with the bounded contract."""

    pack_id = raw.get("pack_id")
    if not isinstance(pack_id, str) or not _PACK_ID_RE.fullmatch(pack_id):
        raise WizardError(
            "pack_id must be a lowercase kebab-case string (a-z, 0-9, '-')")
    return pack_id


def _require_route(raw: Mapping[str, object]) -> str:
    """Return a validated route id or fail closed on anything else."""

    route = raw.get("route", "minimal")
    if not isinstance(route, str) or route not in ROUTES:
        raise WizardError(f"unknown route: {route!r}")
    return route


def normalize_inputs(raw: Mapping[str, object]) -> WizardInputs:
    """Validate an untrusted wizard-input document; fail closed on anything odd."""

    if not isinstance(raw, Mapping):
        raise WizardError("wizard input must be a mapping")
    _require_envelope(raw)
    pack_id = _require_pack_id(raw)
    route = _require_route(raw)
    answers = _normalize_answers(route, raw.get("answers", {}))
    capabilities = _normalize_capabilities(raw.get("capabilities", ()))

    title = _answer_or(answers, "title", "") or title_from_pack_id(pack_id)
    description = _answer_or(answers, "description", "") or _DEFAULT_DESCRIPTION

    return WizardInputs(
        pack_id=pack_id,
        route=route,
        title=title,
        description=description,
        capabilities=capabilities,
        answers=tuple(sorted(answers.items())),
    )


def _answer_or(answers: Mapping[str, str], key: str, fallback: str) -> str:
    """Return the answer for ``key``, treating not-sure as absent."""

    value = answers.get(key, fallback)
    return fallback if value == NOT_SURE else value


def _normalize_answers(route: str, raw: object) -> dict[str, str]:
    """Validate the answers map against the route's questions; fail closed."""

    if not isinstance(raw, Mapping):
        raise WizardError("answers must be a mapping")
    questions = {q.key: q for q in route_questions(route)}
    normalized: dict[str, str] = {}
    for key, value in raw.items():
        question = questions.get(key)
        if question is None:
            raise WizardError(f"unknown answer key for route {route!r}: {key!r}")
        if not isinstance(value, str):
            raise WizardError(f"answer {key!r} must be a string")
        if value == NOT_SURE:
            if not question.allow_not_sure:
                raise WizardError(f"answer {key!r} may not be not-sure")
        elif question.choices is not None and value not in question.choices:
            raise WizardError(
                f"answer {key!r} must be one of {question.choices}")
        normalized[key] = value
    return normalized


def _normalize_capabilities(raw: object) -> tuple[str, ...]:
    """Validate and de-duplicate the selected optional-layer ids; fail closed."""

    if not isinstance(raw, (list, tuple)):
        raise WizardError("capabilities must be a list")
    result: list[str] = []
    for item in raw:
        if not isinstance(item, str) or item not in CAPABILITIES:
            raise WizardError(f"unknown capability: {item!r}")
        if item not in result:
            result.append(item)
    return tuple(result)


@dataclass(frozen=True)
class Proposal(object):
    """The one immutable proposal every renderer, the writer, and tests read."""

    pack_id: str
    route: str
    title: str
    description: str
    capabilities: tuple[str, ...]
    files: dict[str, str]
    assumptions: tuple[tuple[str, str], ...]
    unresolved: tuple[tuple[str, str], ...]
    _blocking: frozenset[str]

    def manifest(self) -> tuple[str, ...]:
        """The sorted set of pack-relative files this proposal would write."""

        return tuple(sorted(self.files))

    def blocking_unresolved(self) -> tuple[tuple[str, str], ...]:
        """Unresolved answers whose owning question requires a resolved value."""

        return tuple((k, r) for k, r in self.unresolved if k in self._blocking)


def build_proposal(inputs: WizardInputs) -> Proposal:
    """Deterministically build the immutable proposal. Pure: no filesystem I/O."""

    context = _Context(
        pack_id=inputs.pack_id,
        title=inputs.title,
        description=inputs.description,
    )
    route = ROUTES[inputs.route]
    selected = tuple(dict.fromkeys((*route.default_capabilities,
                                    *inputs.capabilities)))

    files = _required_files(context)
    contents: dict[str, bool] = {}
    pointers: dict[str, str] = {}
    for key in selected:
        capability = CAPABILITIES[key]
        _merge_files(files, capability.generate(context))
        if capability.contents_flag is not None:
            contents[capability.contents_flag] = True
        if capability.manifest_pointer is not None:
            pointers[capability.manifest_pointer[0]] = capability.manifest_pointer[1]
    files["pack.yaml"] = _pack_manifest(context, contents, pointers)

    unresolved, blocking = _resolve_answer_state(inputs)
    assumptions = (
        ("route", route.label),
        ("optional_layers", ", ".join(selected) or "none"),
    )
    return Proposal(
        pack_id=inputs.pack_id,
        route=inputs.route,
        title=inputs.title,
        description=inputs.description,
        capabilities=selected,
        files=files,
        assumptions=assumptions,
        unresolved=unresolved,
        _blocking=blocking,
    )


def _merge_files(base: dict[str, str], extra: Mapping[str, str]) -> None:
    """Merge generated files, rejecting a conflicting duplicate path."""

    for rel, content in extra.items():
        if rel in base and base[rel] != content:
            raise WizardError(f"capability file conflict at {rel!r}")
        base[rel] = content


def _resolve_answer_state(
    inputs: WizardInputs,
) -> tuple[tuple[tuple[str, str], ...], frozenset[str]]:
    """Compute unresolved answers and which of them block the write."""

    answers = dict(inputs.answers)
    unresolved: list[tuple[str, str]] = []
    blocking: set[str] = set()
    for question in route_questions(inputs.route):
        value = answers.get(question.key, _MISSING)
        reason = _unresolved_reason(question, value)
        if reason is None:
            continue
        unresolved.append((question.key, reason))
        if question.required:
            blocking.add(question.key)
    return tuple(unresolved), frozenset(blocking)


def _unresolved_reason(question: Question, value: object) -> str | None:
    """Why an answer leaves a question unresolved, or None when it is resolved.

    A required affirmative gate (``required_value`` set) is satisfied ONLY by
    that exact value; answering it "no" is a resolved answer but still leaves the
    gate unsatisfied, so it must block the write rather than silently pass.
    """

    if value == NOT_SURE:
        reason: str | None = "not-sure"
    elif value is _MISSING:
        reason = "unanswered" if question.required else None
    elif question.required_value is not None and value != question.required_value:
        reason = f"requires '{question.required_value}'"
    else:
        reason = None
    return reason


# --------------------------------------------------------------------------- #
# Rendering
# --------------------------------------------------------------------------- #
def render_human_preview(proposal: Proposal) -> str:
    """Plain-language preview of the file set and assumptions. No side effects."""

    lines = [
        f"pack: {proposal.pack_id}",
        f"route: {proposal.route}",
        "",
        "assumptions:",
    ]
    lines.extend(f"  - {key}: {value}" for key, value in proposal.assumptions)
    lines.append("")
    lines.append("files to write:")
    lines.extend(f"  {rel}" for rel in proposal.manifest())
    if proposal.unresolved:
        lines.append("")
        lines.append("unresolved (left not-sure / unanswered):")
        lines.extend(f"  - {key}: {reason}" for key, reason in proposal.unresolved)
    blocking = proposal.blocking_unresolved()
    if blocking:
        lines.append("")
        lines.append(
            "NOTE: writing is blocked until these are answered: "
            + ", ".join(key for key, _ in blocking))
    return "\n".join(lines) + "\n"


def machine_document(proposal: Proposal) -> dict[str, object]:
    """The versioned machine document (stdout-only in machine mode)."""

    return {
        "version": WIZARD_OUTPUT_VERSION,
        "pack": proposal.pack_id,
        "route": proposal.route,
        "files": list(proposal.manifest()),
        "assumptions": dict(proposal.assumptions),
        "unresolved": [
            {"key": key, "reason": reason} for key, reason in proposal.unresolved],
        "blocking": [key for key, _ in proposal.blocking_unresolved()],
    }


# --------------------------------------------------------------------------- #
# Writing (one guarded, atomic transaction)
# --------------------------------------------------------------------------- #
def _write_member(pack_root: Path, rel: str, content: str) -> None:
    """Write one canonical regular member under a fresh private pack root."""

    try:
        _transactions.write_member(pack_root, rel, content)
    except _transactions.TransactionError as exc:
        raise WizardError("generated member is not safe to stage") from exc


def write_proposal(proposal: Proposal, environments_root: str) -> str:
    """Validate then atomically publish the pack into an absent target.

    Renders into a private staging tree, runs ``validate_pack`` on the completed
    pack, and only then atomically renames it into place. An existing target is a
    deterministic conflict — never overlaid, replaced, or merged (ADR 0034). A
    failed render or validation removes only the staging tree.
    """

    blocking = proposal.blocking_unresolved()
    if blocking:
        raise WizardError(
            "cannot write: unresolved required answers: "
            + ", ".join(key for key, _ in blocking))

    validate_pack_id(proposal.pack_id)
    environments = Path(environments_root).resolve(strict=True)
    target = (environments / proposal.pack_id).resolve()
    if target.parent != environments:
        raise WizardError(f"target escapes environments root: {proposal.pack_id}")
    # Fast, friendly pre-check; the atomic claim below is the real guarantee.
    if target.exists():
        raise WizardError(f"target already exists: environments/{proposal.pack_id}")

    staging_parent = Path(tempfile.mkdtemp(prefix=".wizard-", dir=environments))
    try:
        staged = staging_parent / proposal.pack_id
        staged.mkdir(mode=0o755)
        staged.chmod(0o755)
        for rel, content in sorted(proposal.files.items()):
            _write_member(staged, rel, content)
        result = validate_pack(str(staged))
        if not result.ok:
            raise WizardError(
                "generated pack did not pass validation: "
                + "; ".join(result.errors))
        _publish(staged, target, proposal.pack_id)
    finally:
        shutil.rmtree(staging_parent, ignore_errors=True)
    return str(target)


def _rename_noreplace(src: str, dst: str) -> None:
    """Compatibility wrapper over the shared no-replace transaction primitive."""

    try:
        _transactions.publish_noreplace(Path(src), Path(dst))
    except _transactions.TransactionError as exc:
        raise WizardError(str(exc)) from exc


def _publish(staged: Path, target: Path, pack_id: str) -> None:
    """Publish the validated staging tree into an absent target in one operation.

    ``renameat2(RENAME_NOREPLACE)`` moves the complete, already-validated pack
    into place atomically and fails closed (``EEXIST``) if anything occupies the
    target — so a concurrent reader never observes a partial pack and an existing
    pack is never replaced (ADR 0034). Both paths sit under ``environments/`` on
    one filesystem, which the primitive requires.
    """

    try:
        _transactions.publish_noreplace(staged, target)
    except _transactions.TargetExistsError as exc:
        raise WizardError(
            f"target already exists: environments/{pack_id}") from exc
    except _transactions.TransactionError as exc:
        raise WizardError("could not publish pack") from exc


# --------------------------------------------------------------------------- #
# Interactive question flow
# --------------------------------------------------------------------------- #
def ask_questions(
    questions: tuple[Question, ...],
    ask: Callable[[Question], str | None],
) -> dict[str, str]:
    """Drive a question set through an injected ``ask`` callback.

    ``ask`` returns the raw answer, or ``NOT_SURE`` for a deliberate not-sure.
    Empty answers fall back to the question default. The interactive CLI and the
    tests share this one flow so a non-developer path is exactly what is tested.
    """

    answers: dict[str, str] = {}
    for question in questions:
        raw = ask(question)
        if raw == NOT_SURE:
            if not question.allow_not_sure:
                raise WizardError(f"{question.key} may not be not-sure")
            answers[question.key] = NOT_SURE
        elif raw:
            answers[question.key] = raw
        elif question.default:
            answers[question.key] = question.default
    return answers


def _terminal_ask(
    stdin: TextIO, out: TextIO,
) -> Callable[[Question], str | None]:
    """Build a stdin/out ``ask`` that prints each prompt and its consequence."""

    def ask(question: Question) -> str | None:
        """Prompt for one question and return the raw answer or not-sure."""

        print(question.prompt, file=out)
        print(f"  why: {question.consequence}", file=out)
        if question.choices:
            print(f"  choices: {', '.join(question.choices)}", file=out)
        if question.default:
            print(f"  default: {question.default}", file=out)
        if question.allow_not_sure:
            print("  (enter '?' if you are not sure)", file=out)
        out.flush()
        raw = stdin.readline().strip()
        return NOT_SURE if raw == "?" and question.allow_not_sure else raw

    return ask


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #
def _parser() -> argparse.ArgumentParser:
    """Build the ``raes-pack-new`` argument parser."""

    parser = argparse.ArgumentParser(
        prog="raes-pack-new",
        description=(
            "Scaffold a new environment pack through a progressive wizard. "
            "Generates only the files your goal needs, previews them, and runs "
            "the same static check consumers run later."),
    )
    parser.add_argument("pack_id", nargs="?", help="lowercase kebab-case pack id")
    parser.add_argument("--repo", default=None,
                        help="repository root; defaults to the current directory")
    parser.add_argument("--route", choices=sorted(ROUTES), default="minimal",
                        help="starter route (default: minimal)")
    parser.add_argument("--title", help="human-readable title")
    parser.add_argument("--description", help="one-line pack description")
    parser.add_argument("--with", dest="layers", action="append", default=[],
                        choices=sorted(CAPABILITIES),
                        help="add an optional layer (repeatable)")
    parser.add_argument("--answer", dest="answers", action="append", default=[],
                        metavar="KEY=VALUE",
                        help="answer a route question non-interactively (repeatable)")
    parser.add_argument("--preview", action="store_true",
                        help="show the proposed file set and assumptions; write nothing")
    parser.add_argument("--json", action="store_true",
                        help="emit the versioned machine document on stdout")
    parser.add_argument("--replay", metavar="-",
                        help="read a wizard-input document from stdin (pass '-')")
    parser.add_argument("--yes", action="store_true",
                        help="non-interactive: accept defaults, no prompts")
    return parser


def _load_replay(path: str, stdin: TextIO) -> Mapping[str, object]:
    """Read and parse the wizard-input document from stdin.

    The replay document is read only from stdin (``--replay -``); the wizard
    never opens a caller-named file path, so a faulty CLI argument cannot direct
    it at an arbitrary filesystem location. Pipe a saved file in with a shell
    redirect: ``--replay - < input.json``.
    """

    if path != "-":
        raise WizardError(
            "read the replay document from stdin: --replay - < input.json")
    try:
        document = json.loads(stdin.read())
    except json.JSONDecodeError as exc:
        raise WizardError(f"replay input is not valid JSON: {exc}") from exc
    return document


def _cli_answers(
    args: argparse.Namespace, stdin: TextIO, prompt_out: TextIO,
) -> dict[str, str]:
    """Assemble answers from flags, ``--answer`` pairs, and interactive prompts.

    Explicit flags stay authoritative; prompts (shown on ``prompt_out``/stderr so
    a machine channel on stdout stays uncontaminated, ADR 0034) only fill answers
    not already supplied.
    """

    answers: dict[str, str] = {}
    if args.title:
        answers["title"] = args.title
    if args.description:
        answers["description"] = args.description
    for pair in args.answers:
        key, sep, value = pair.partition("=")
        if not sep or not key:
            raise WizardError(f"--answer must be KEY=VALUE, got {pair!r}")
        answers[key] = value
    if not args.yes and stdin is not None and getattr(stdin, "isatty", bool)():
        asked = ask_questions(
            route_questions(args.route), _terminal_ask(stdin, prompt_out))
        for key, value in asked.items():
            answers.setdefault(key, value)
    return answers


def _inputs_from_args(
    args: argparse.Namespace, stdin: TextIO, prompt_out: TextIO,
) -> WizardInputs:
    """Build validated inputs from replay stdin, or from CLI flags and prompts."""

    if args.replay:
        return normalize_inputs(_load_replay(args.replay, stdin))
    if not args.pack_id:
        raise WizardError("a pack id is required (or use --replay -)")
    raw = {
        "version": WIZARD_INPUT_VERSION,
        "pack_id": args.pack_id,
        "route": args.route,
        "answers": _cli_answers(args, stdin, prompt_out),
        "capabilities": list(args.layers),
    }
    return normalize_inputs(raw)


def _report_error(exc: WizardError, stderr: TextIO) -> None:
    """Print one bounded error line to stderr."""

    print(f"error: {exc}", file=stderr)


def _emit_preview(proposal: Proposal, as_json: bool, stdout: TextIO) -> None:
    """Render the side-effect-free preview (machine or human)."""

    if as_json:
        print(json.dumps(machine_document(proposal), indent=2, sort_keys=True),
              file=stdout)
    else:
        print(render_human_preview(proposal), file=stdout, end="")


def _create_and_report(
    args: argparse.Namespace, proposal: Proposal, stdout: TextIO, stderr: TextIO,
) -> int:
    """Resolve the repo, write the pack, and report; returns the exit status."""

    try:
        repo = os.path.abspath(args.repo) if args.repo else repo_root()
    except WizardError as exc:
        _report_error(exc, stderr)
        return EXIT_USAGE
    try:
        created = write_proposal(proposal, os.path.join(repo, "environments"))
    except WizardError as exc:
        _report_error(exc, stderr)
        return EXIT_BLOCKING
    relative = os.path.relpath(created, repo)
    if args.json:
        document = machine_document(proposal)
        document["created"] = relative
        print(json.dumps(document, indent=2, sort_keys=True), file=stdout)
    else:
        print(f"created {relative}", file=stdout)
        print(f"validated with the static pack check ({proposal.route} route)",
              file=stdout)
    return EXIT_OK


def main(
    argv: list[str] | None = None,
    *,
    stdin: TextIO | None = None,
    stdout: TextIO | None = None,
    stderr: TextIO | None = None,
) -> int:
    """Command-line entry point. Returns the process exit status."""

    stdin = stdin if stdin is not None else sys.stdin
    stdout = stdout if stdout is not None else sys.stdout
    stderr = stderr if stderr is not None else sys.stderr

    args = _parser().parse_args(argv)
    try:
        inputs = _inputs_from_args(args, stdin, stderr)
        proposal = build_proposal(inputs)
    except WizardError as exc:
        _report_error(exc, stderr)
        return EXIT_USAGE

    if args.preview:
        _emit_preview(proposal, args.json, stdout)
        return EXIT_OK
    return _create_and_report(args, proposal, stdout, stderr)


if __name__ == "__main__":
    raise SystemExit(main())
