"""Beginner-safe static pack check CLI (issue #187, ADR 0031).

``raes-pack-check`` is the consumer-facing adapter over the ``validate_pack()``
static authority. It never executes pack code, never touches the network, reads
only through the descriptor-anchored pack filesystem, and renders one structured
result as plain language or a versioned JSON envelope.

Running a pack's own validators or tests is the *trusted-author* capability and
stays with ``raes-pack-validate``; this command is deliberately inert. Every
diagnostic is a stable code plus a bounded, pack-relative location — never an
authored value, an absolute path, or raw upstream prose (ADR 0013, ADR 0031).
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from dataclasses import dataclass, replace

from .validation import Diagnostic, ValidationResult, validate_pack

# JSON envelope identity. Bump when the machine contract changes shape.
ENVELOPE_VERSION = "raes-pack-check/v1"

# Durable documentation target. Diagnostics point at a stable per-domain anchor
# in this page; the anchor set is enforced by a test so moving a heading fails
# closed rather than silently breaking the link (ADR 0031).
DOC_PAGE = "docs/public/checking.md"

# Stable process contract (ADR 0031). Suitable for scripts, editors, CI, Hub,
# and MCP delegation.
EXIT_OK = 0
EXIT_BLOCKING = 1
EXIT_USAGE = 2
EXIT_TOOL_FAILURE = 3

_SEVERITY_ERROR = "error"

# The two owning authorities the SDL-vs-pack boundary distinguishes (ADR 0009,
# ADR 0013). Everything in this package's pack contract is owned by env-packs;
# SDL syntax and meaning are owned by RAES.
_OWNER_ENV_PACKS = "env-packs"
_OWNER_RAES = "raes"

# Domain -> stable heading anchor in DOC_PAGE.
_DOMAIN_DOC_ANCHOR = {
    "pack": "pack-layout",
    "sdl": "sdl-and-raes",
    "compatibility": "compatibility",
    "trust": "trust-and-provenance",
}


@dataclass(frozen=True)
class Presentation(object):
    """Beginner-safe presentation metadata for one diagnostic code family.

    This is presentation only — it explains a finding the static authority
    already produced. It is not a validator and adds no new checks.
    """

    severity: str
    domain: str
    owner: str
    explanation: str
    reason: str
    suggestion: str


def _pack(explanation: str, reason: str, suggestion: str) -> Presentation:
    return Presentation(
        _SEVERITY_ERROR, "pack", _OWNER_ENV_PACKS, explanation, reason, suggestion
    )


def _trust(explanation: str, reason: str, suggestion: str) -> Presentation:
    return Presentation(
        _SEVERITY_ERROR, "trust", _OWNER_ENV_PACKS, explanation, reason, suggestion
    )


def _compat(explanation: str, reason: str, suggestion: str) -> Presentation:
    return Presentation(
        _SEVERITY_ERROR,
        "compatibility",
        _OWNER_ENV_PACKS,
        explanation,
        reason,
        suggestion,
    )


def _sdl(explanation: str, reason: str, suggestion: str) -> Presentation:
    return Presentation(
        _SEVERITY_ERROR, "sdl", _OWNER_RAES, explanation, reason, suggestion
    )


# Presentation catalog, keyed by a diagnostic-code prefix. A code resolves to the
# entry whose key is its longest dotted prefix, so specific codes win and every
# namespace has a family fallback. ``*.schema.<subcode>`` codes additionally pick
# up a subcode hint (see ``_SCHEMA_SUBCODE_HINT``).
_CATALOG: dict[str, Presentation] = {
    # -- pack layout / identity -------------------------------------------------
    "pack": _pack(
        "The pack manifest (pack.yaml) is missing or malformed.",
        "pack.yaml is the pack's identity entrypoint; nothing else can be trusted without it.",
        "Add a valid pack.yaml at the top of the pack directory.",
    ),
    "pack.missing": _pack(
        "pack.yaml is missing from the pack root.",
        "Every pack must declare its identity in pack.yaml.",
        "Add a pack.yaml at the top of the pack directory (see the template).",
    ),
    "pack.type": _pack(
        "pack.yaml did not parse to a mapping.",
        "The manifest must be a YAML mapping of identity fields.",
        "Make pack.yaml a top-level mapping (key: value pairs), not a list or scalar.",
    ),
    "pack.identity.missing": _pack(
        "A required identity field (name, title, or version) is missing or empty.",
        "Consumers key on a pack's name, title, and version.",
        "Set name, title, and version in pack.yaml to non-empty strings.",
    ),
    "pack.identity.name-mismatch": _pack(
        "The name in pack.yaml does not match the pack directory name.",
        "The manifest name is the pack's identity and must match its folder.",
        "Set name in pack.yaml to the directory name, or rename the directory to match.",
    ),
    # -- YAML / filesystem / resource (all pack-domain) -------------------------
    "yaml": _pack(
        "A pack file is not valid YAML.",
        "The check reads pack metadata as strict YAML.",
        "Fix the YAML syntax in the reported file.",
    ),
    "yaml.invalid": _pack(
        "A pack file is not valid YAML.",
        "The check reads pack metadata as strict YAML.",
        "Fix the YAML syntax in the reported file.",
    ),
    "yaml.invalid-utf8": _pack(
        "A pack file is not valid UTF-8 text.",
        "Pack metadata must be UTF-8 so it reads deterministically.",
        "Re-save the reported file as UTF-8 text.",
    ),
    "yaml.duplicate-key": _pack(
        "A YAML mapping in the pack has a duplicate key.",
        "Duplicate keys are ambiguous, so the strict loader rejects them.",
        "Remove the duplicated key from the reported file.",
    ),
    "filesystem": _pack(
        "The pack filesystem could not be read safely.",
        "The check reads only through a no-follow, descriptor-anchored boundary.",
        "Point the check at the pack's top-level directory and remove unsafe members.",
    ),
    "filesystem.invalid-root": _pack(
        "The pack root could not be opened as a directory.",
        "The check needs a real directory to inventory the pack.",
        "Point the check at the pack's top-level directory.",
    ),
    "filesystem.unsafe-member": _pack(
        "The pack contains an unsafe member (symlink, hardlink, special file, or escaping path).",
        "The check refuses to follow these so foreign input cannot escape the pack root.",
        "Replace the unsafe member with a regular file inside the pack.",
    ),
    "filesystem.changed": _pack(
        "A pack file changed or disappeared while the check was running.",
        "The check needs a stable, immutable pack snapshot to be deterministic.",
        "Stage the pack immutably, then re-run the check over the staged bytes.",
    ),
    "resource": _pack(
        "The pack exceeded a check resource limit.",
        "Bounds protect the consumer from oversized or adversarial input.",
        "Reduce the input, or raise the bound via PackValidationLimits.",
    ),
    "resource.metadata-limit": _pack(
        "A metadata file is larger than the check allows.",
        "Metadata size is bounded so a pack cannot exhaust the consumer.",
        "Shrink the reported file, or raise max_metadata_bytes via PackValidationLimits.",
    ),
    "resource.sdl-limit": _pack(
        "An SDL document is larger than the check allows.",
        "SDL size is bounded so a pack cannot exhaust the consumer.",
        "Shrink the reported document, or raise max_sdl_bytes via PackValidationLimits.",
    ),
    "resource.member-limit": _pack(
        "The pack has more files than the check allows.",
        "Member count is bounded so a pack cannot exhaust the consumer.",
        "Reduce the file count, or raise max_members via PackValidationLimits.",
    ),
    "challenges": _pack(
        "The challenges document uses a removed pack field.",
        "Challenge grouping and classification are not pack semantics.",
        "Remove the offending field from the challenge entry.",
    ),
    "challenges.category.forbidden": _pack(
        "challenges[].category is a removed pack field.",
        "Tactic/technique classification lives in RAES SDL, not a pack field (ADR 0014).",
        "Remove the category field from the reported challenge entry.",
    ),
    # -- trust / provenance -----------------------------------------------------
    "provenance": _trust(
        "The provenance ledger is missing or does not meet the pack contract.",
        "The ledger is the pack's origin, licensing, safety, and review record.",
        "Add or correct docs/provenance-ledger.yaml (see the template).",
    ),
    "provenance.pointer": _trust(
        "pack.yaml's provenance_ledger pointer is missing or is not the canonical path.",
        "The ledger is required and must live at docs/provenance-ledger.yaml.",
        "Set provenance_ledger: docs/provenance-ledger.yaml in pack.yaml.",
    ),
    "provenance.missing": _trust(
        "The referenced provenance ledger file was not found.",
        "The ledger the manifest points at must actually exist in the pack.",
        "Add docs/provenance-ledger.yaml, or fix the pointer to the real file.",
    ),
    "provenance.type": _trust(
        "The provenance ledger did not parse to a mapping.",
        "The ledger must be a YAML mapping for the schema to apply.",
        "Make docs/provenance-ledger.yaml a top-level YAML mapping.",
    ),
    "provenance.name-mismatch": _trust(
        "The ledger's pack.name does not match the pack's name.",
        "The ledger must describe this pack, not another one.",
        "Set pack.name in the ledger to match name in pack.yaml.",
    ),
    "provenance.safety.required": _trust(
        "A required content-safety attestation is missing or is not true.",
        "Packs must attest they carry no real malware, live targets, credentials, or sensitive data.",
        "Set the reported content_safety flag to true in the ledger — only if it is actually true.",
    ),
    "provenance.review-gate.missing": _trust(
        "A required publication review gate is missing.",
        "Licensing, attribution, sensitive-data, and offensive-tooling must each be reviewed before publication.",
        "Add the missing gate under review.gates in the ledger.",
    ),
    "provenance.schema": _trust(
        "The provenance ledger does not match its packaged schema.",
        "The ledger must match provenance.schema.yaml so tools can read it.",
        "Correct the field at the reported location to match the schema.",
    ),
    # -- compatibility ----------------------------------------------------------
    "compatibility": _compat(
        "The compatibility manifest does not meet the pack contract.",
        "The manifest is how a pack declares the runtime and delivery surfaces a consumer can rely on.",
        "Correct pack.compatibility.yaml, or remove the pointer if the pack has no manifest.",
    ),
    "compatibility.pointer": _compat(
        "pack.yaml's compatibility_manifest pointer is invalid.",
        "The pointer must name a real pack-relative file.",
        "Point compatibility_manifest at an existing file, or remove it.",
    ),
    "compatibility.missing": _compat(
        "The referenced compatibility manifest file was not found.",
        "The manifest the manifest points at must exist in the pack.",
        "Add the compatibility file the pointer names, or remove the pointer.",
    ),
    "compatibility.type": _compat(
        "The compatibility manifest did not parse to a mapping.",
        "The manifest must be a YAML mapping for the schema to apply.",
        "Make the compatibility file a top-level YAML mapping.",
    ),
    "compatibility.boundary-overlap": _compat(
        "A participant-visible path overlaps a restricted (operator, oracle, or private) path.",
        "Hidden-tier content must never be reachable from a participant export.",
        "Move the participant path so it is disjoint from every restricted root.",
    ),
    "compatibility.schema": _compat(
        "The compatibility manifest does not match its packaged schema.",
        "The manifest must match pack-compatibility.schema.yaml so tools can read it.",
        "Correct the field at the reported location to match the schema.",
    ),
    # -- SDL (RAES-owned) -------------------------------------------------------
    "sdl": _sdl(
        "An SDL start-state document did not pass RAES validation.",
        "The start state must be valid under the pinned raes.",
        "Fix the SDL document; RAES owns its syntax and meaning.",
    ),
    "sdl.missing": _sdl(
        "The pack has no direct sdl/*.sdl.yaml start-state document.",
        "Every pack must ship at least one SDL start state.",
        "Add an sdl/<name>.sdl.yaml document describing the environment start state.",
    ),
    "sdl.invalid": _sdl(
        "The SDL start state failed RAES validation.",
        "The start state must parse and validate under the pinned raes.",
        "Validate the document with raes and fix the reported SDL error.",
    ),
    "sdl.invalid-utf8": _sdl(
        "An SDL document is not valid UTF-8 text.",
        "SDL documents must be UTF-8 so RAES can parse them.",
        "Re-save the reported SDL document as UTF-8 text.",
    ),
    "sdl.imports-denied": _sdl(
        "The SDL document uses imports, which the consumer check denies.",
        "Import resolution can reach the network, so it is refused for untrusted input.",
        "Inline the imported content, or validate as the trusted author with raes-pack-validate.",
    ),
}

# Appended to a schema-violation suggestion, keyed by the JSON-Schema subcode the
# static authority reports (``provenance.schema.required`` -> ``required``).
_SCHEMA_SUBCODE_HINT: dict[str, str] = {
    "required": "A required field is missing — add it.",
    "enum": "The value is not one of the allowed choices — use an allowed value.",
    "pattern": "The value does not match the required format — correct its format.",
    "type": "The value has the wrong type — use the type the schema expects.",
    "unknown": "An unrecognized field is present — remove it.",
    "min-items": "The list needs more entries — add the required minimum.",
    "const": "The value must equal the fixed required value — set it exactly.",
    "ref": "An internal schema reference did not resolve — please report this upstream.",
}

# Fail-closed fallback for an unknown code (a code from a future authority the
# catalog has not learned yet). It stays bounded and never echoes upstream prose.
_GENERIC = _pack(
    "The check reported a problem with this pack.",
    "See the diagnostic code and location for the specific contract it failed.",
    "Consult the pack contract documentation for this code.",
)


def presentation_for(code: str) -> Presentation:
    """Resolve one code to its presentation via longest-prefix + subcode hint."""

    parts = code.split(".")
    base = _GENERIC
    for cut in range(len(parts), 0, -1):
        key = ".".join(parts[:cut])
        entry = _CATALOG.get(key)
        if entry is not None:
            base = entry
            break
    return _enrich_schema(code, base)


def _enrich_schema(code: str, base: Presentation) -> Presentation:
    """Append a subcode hint to a ``*.schema.<subcode>`` suggestion."""

    marker = ".schema."
    index = code.find(marker)
    if index == -1:
        return base
    subcode = code[index + len(marker):]
    hint = _SCHEMA_SUBCODE_HINT.get(subcode)
    if hint is None:
        return base
    return replace(base, suggestion=f"{base.suggestion} {hint}")


def _location(diagnostic: Diagnostic) -> str | None:
    """Bounded pack-relative member and field pointer, or None."""

    if diagnostic.path and diagnostic.field_path:
        return f"{diagnostic.path}:{diagnostic.field_path}"
    return diagnostic.path or diagnostic.field_path or None


def _enriched(diagnostic: Diagnostic) -> dict[str, object]:
    """Combine a canonical diagnostic with its presentation metadata."""

    presentation = presentation_for(diagnostic.code)
    return {
        "code": diagnostic.code,
        "severity": presentation.severity,
        "domain": presentation.domain,
        "owner": presentation.owner,
        "location": _location(diagnostic),
        "file": diagnostic.path,
        "field": diagnostic.field_path,
        "explanation": presentation.explanation,
        "reason": presentation.reason,
        "suggestion": presentation.suggestion,
        "doc": f"{DOC_PAGE}#{_DOMAIN_DOC_ANCHOR[presentation.domain]}",
    }


@dataclass(frozen=True)
class Report(object):
    """The one canonical result every renderer serializes (ADR 0031)."""

    ok: bool
    pack: str
    diagnostics: tuple[dict[str, object], ...]


def build_report(result: ValidationResult, pack_name: str) -> Report:
    """Build the shared report from a validation result. Order is preserved."""

    return Report(
        ok=result.ok,
        pack=pack_name,
        diagnostics=tuple(_enriched(diagnostic) for diagnostic in result.diagnostics),
    )


def _summary(diagnostics: tuple[dict[str, object], ...]) -> dict[str, object]:
    by_domain: dict[str, int] = {}
    for diagnostic in diagnostics:
        domain = str(diagnostic["domain"])
        by_domain[domain] = by_domain.get(domain, 0) + 1
    return {"total": len(diagnostics), "by_domain": by_domain}


def render_json(report: Report) -> str:
    """Serialize the canonical result as the versioned JSON envelope."""

    document = {
        "version": ENVELOPE_VERSION,
        "ok": report.ok,
        "pack": report.pack,
        "summary": _summary(report.diagnostics),
        "diagnostics": [dict(diagnostic) for diagnostic in report.diagnostics],
    }
    return json.dumps(document, indent=2, sort_keys=True)


def _terminal_safe(text: str) -> str:
    """Escape an untrusted, filesystem-derived label for terminal display.

    A crafted pack directory or member name can carry newlines or ANSI/OSC
    escape sequences. Printed raw into the trust report they could spoof a
    verdict line, erase findings, or drive the terminal. Control characters and
    line/paragraph separators are rendered in a visible ``\\xNN``/``\\uNNNN``
    form. JSON output is intentionally left as the real value — ``json.dumps``
    already escapes these safely for machine consumers.
    """

    return "".join(
        character
        if character.isprintable()
        else (
            f"\\x{ord(character):02x}"
            if ord(character) < 0x100
            else f"\\u{ord(character):04x}"
        )
        for character in text
    )


def render_human(report: Report) -> str:
    """Render the same canonical result as plain language."""

    lines = [f"pack: {_terminal_safe(report.pack)}"]
    if report.ok:
        lines.append("OK — no blocking problems found.")
        return "\n".join(lines) + "\n"
    count = len(report.diagnostics)
    lines.append(f"FOUND {count} blocking problem{'' if count == 1 else 's'}:")
    lines.append("")
    for diagnostic in report.diagnostics:
        raw_location = diagnostic["location"]
        location = _terminal_safe(str(raw_location)) if raw_location else "(whole pack)"
        lines.append(f"[{diagnostic['domain']}] {diagnostic['code']}  (owner: {diagnostic['owner']})")
        lines.append(f"  where: {location}")
        lines.append(f"  what:  {diagnostic['explanation']}")
        lines.append(f"  why:   {diagnostic['reason']}")
        lines.append(f"  fix:   {diagnostic['suggestion']}")
        lines.append(f"  docs:  {diagnostic['doc']}")
        lines.append("")
    return "\n".join(lines) + "\n"


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="raes-pack-check",
        description=(
            "Statically check one environment pack and explain any problems in "
            "plain language. Networkless and non-executing by default: it never "
            "runs the pack's own validators, tests, or code. Running those is the "
            "trusted-author job of raes-pack-validate."
        ),
        epilog=(
            "exit codes: 0 valid; 1 blocking problems found; "
            "2 invalid invocation; 3 checker/upstream failure."
        ),
    )
    parser.add_argument("pack_root", help="path to the staged pack directory")
    parser.add_argument(
        "--json",
        action="store_true",
        help="emit the JSON envelope on stdout instead of plain text",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    """Command-line entry point. Returns the process exit status."""

    parser = _parser()
    args = parser.parse_args(argv)  # invalid invocation -> SystemExit(2)

    if not os.path.isdir(args.pack_root):
        # Escape the echoed argument: it may be an attacker-supplied directory
        # name carrying terminal control sequences.
        parser.error(f"not a directory: {_terminal_safe(args.pack_root)}")  # -> SystemExit(2)

    try:
        result = validate_pack(args.pack_root)
    except Exception as exc:  # noqa: BLE001 - bounded, payload-free tool-failure path
        # An unexpected package/RAES defect is a checker failure, never
        # mislabeled as invalid pack content (ADR 0031). Report only the
        # exception type so no path, body, or value leaks.
        print(
            f"raes-pack-check: internal error ({type(exc).__name__})",
            file=sys.stderr,
        )
        return EXIT_TOOL_FAILURE

    report = build_report(result, os.path.basename(os.path.normpath(args.pack_root)))
    if args.json:
        print(render_json(report))
    else:
        sys.stdout.write(render_human(report))
    return EXIT_OK if report.ok else EXIT_BLOCKING


if __name__ == "__main__":
    raise SystemExit(main())
