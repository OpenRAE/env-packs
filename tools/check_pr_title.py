#!/usr/bin/env python3
"""Repository-side PR title guard.

Single source of truth for this repo's pull-request title policy. The
`.github/workflows/pr-title.yml` CI workflow and `tests/test_pr_title_guard.py`
both call ``validate_pr_title`` here, so the policy cannot drift between the
workflow YAML and local enforcement.

Policy:
  * Reject agent/tool advertising bracketed prefixes such as ``[codex] ...``,
    ``[claude] ...``, ``[openai] ...``, ``[chatgpt] ...`` (case-insensitive), on
    every target branch including ``dev`` — no ``dev`` exemption.
  * Enforce the Conventional Commit shape ``<type>(<optional-scope>): <subject>``
    with a single allowed type. The type drives the release-please version bump
    (ADR 0008).
  * Require the subject to start lowercase (``^[a-z].*$``).
  * Reject breaking-change markers (ADR 0039). A ``!`` after the type, a
    ``BREAKING CHANGE:`` or ``BREAKING-CHANGE:`` footer, or a ``<type>!:`` footer
    line makes release-please bump the major version. A breaking change uses
    ``feat:`` and gets a minor release. A ``Release-As:`` footer is the only
    path to a major release. The guard checks the title, the PR body, and every
    PR commit message, because the squash commit carries the commit messages.

Security: the PR title is untrusted GitHub event data. The CLI reads it from
``$GITHUB_EVENT_PATH`` (parsed as JSON) or the ``PR_TITLE`` env var, never from a
shell-interpolated argument, and never dumps the event payload or environment. It
is intentionally stdlib-only so the CI job runs on a bare ``python`` interpreter
with no third-party dependencies.

NOTE: keep ``CONVENTIONAL_TYPES`` below in sync with
``.ground-control.yaml`` ``workflow.pr_title.types`` (the agent-side /implement
Step 9 check), so titles /implement produces always pass this guard.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from collections.abc import Sequence
from dataclasses import dataclass

# --- Policy data (the extensibility seam: parameterize, do not hard-fork) ---

#: Agent/tool advertising prefixes banned as a bracketed title prefix.
BRANDED_PREFIXES: tuple[str, ...] = ("codex", "claude", "openai", "chatgpt")

#: Conventional Commit types accepted in PR titles (history hygiene; ADR 0007).
CONVENTIONAL_TYPES: tuple[str, ...] = (
    "feat",
    "fix",
    "docs",
    "style",
    "refactor",
    "perf",
    "test",
    "build",
    "ci",
    "chore",
    "revert",
)

#: Subject must start lowercase.
SUBJECT_PATTERN: str = r"^[a-z].*$"

RULE_AGENT_BRAND = "pr-title-agent-brand"
RULE_CONVENTIONAL = "pr-title-conventional"
RULE_SUBJECT_LOWERCASE = "pr-title-subject-lowercase"
RULE_EMPTY = "pr-title-empty"
RULE_BREAKING_MARKER = "pr-breaking-marker"

#: Body tokens that release-please reads as a breaking change.
_BREAKING_FOOTER_RE = re.compile(r"BREAKING[ -]CHANGE")

#: Message that tells the author how to ship a breaking change (ADR 0039).
_BREAKING_GUIDANCE = (
    "Breaking changes get a minor release (ADR 0039): use 'feat:' and describe "
    "the break in prose. Only a 'Release-As: X.0.0' footer makes a major release."
)


@dataclass(frozen=True)
class TitleViolation:
    """A single policy violation."""

    rule_id: str
    message: str

    def render(self) -> str:
        return f"[{self.rule_id}] {self.message}"


def _branded_prefix_re(branded_prefixes: Sequence[str]) -> re.Pattern[str]:
    alternation = "|".join(re.escape(p) for p in branded_prefixes)
    # Bracketed prefix only (with optional surrounding whitespace); NOT a
    # substring ban, so a subject that mentions a tool name later is fine.
    return re.compile(rf"^\s*\[\s*(?:{alternation})\s*\]", re.IGNORECASE)


def _conventional_re(types: Sequence[str]) -> re.Pattern[str]:
    alternation = "|".join(re.escape(t) for t in types)
    # <type>(<optional-scope>)<optional breaking !>: <subject>
    return re.compile(rf"^(?:{alternation})(?:\([^()\n]+\))?(?:!)?: (?P<subject>.+)$")


def _breaking_footer_line_re(types: Sequence[str]) -> re.Pattern[str]:
    alternation = "|".join(re.escape(t) for t in types)
    # A body line that release-please can parse as a breaking footer commit,
    # with an optional list bullet (GitHub squash bodies list commits as "* ").
    return re.compile(
        rf"^\s*(?:[*-]\s+)?(?:{alternation})(?:\([^()\n]+\))?!:",
        re.MULTILINE,
    )


def validate_pr_title(
    title: str | None,
    *,
    branded_prefixes: Sequence[str] = BRANDED_PREFIXES,
    types: Sequence[str] = CONVENTIONAL_TYPES,
    subject_pattern: str = SUBJECT_PATTERN,
    require_scope: bool = False,
) -> list[TitleViolation]:
    """Validate ``title`` against the PR title policy and return violations.

    An empty list means the title is acceptable.
    """
    violations: list[TitleViolation] = []
    stripped = (title or "").strip()

    if not stripped:
        violations.append(TitleViolation(RULE_EMPTY, "PR title is empty."))
        return violations

    # Rule 1: agent/tool advertising bracketed prefix ban. Checked first so the
    # failure message is unambiguous (a branded title also fails Rule 2).
    if _branded_prefix_re(branded_prefixes).match(stripped):
        banned = ", ".join(f"[{p}]" for p in branded_prefixes)
        violations.append(
            TitleViolation(
                RULE_AGENT_BRAND,
                "PR title must not start with an agent/tool advertising prefix "
                f"such as {banned}. Use a project-native conventional title "
                "instead.",
            )
        )
        return violations

    # Rule 2: conventional-commit shape with a single allowed type.
    match = _conventional_re(types).match(stripped)
    if match is not None and stripped.split(":", 1)[0].endswith("!"):
        violations.append(
            TitleViolation(
                RULE_BREAKING_MARKER,
                f"PR title must not use the '!' breaking marker. {_BREAKING_GUIDANCE}",
            )
        )
    if match is None:
        allowed = ", ".join(types)
        violations.append(
            TitleViolation(
                RULE_CONVENTIONAL,
                "PR title must match '<type>(<optional-scope>): <subject>' with a "
                f"single type from: {allowed}. Compound type prefixes "
                "(e.g. 'fix/refactor:') are rejected.",
            )
        )
        return violations

    if require_scope and "(" not in stripped.split(":", 1)[0]:
        violations.append(
            TitleViolation(
                RULE_CONVENTIONAL,
                "PR title must include a scope: '<type>(<scope>): <subject>'.",
            )
        )

    # Rule 3: subject starts lowercase.
    subject = match.group("subject")
    if re.match(subject_pattern, subject) is None:
        violations.append(
            TitleViolation(
                RULE_SUBJECT_LOWERCASE,
                "PR title subject must start lowercase "
                f"(match {subject_pattern!r}); got subject {subject!r}.",
            )
        )

    return violations


def validate_merge_text(
    text: str | None,
    *,
    source: str,
    types: Sequence[str] = CONVENTIONAL_TYPES,
) -> list[TitleViolation]:
    """Reject breaking-change markers in text that can reach the squash commit.

    ``source`` names the text (for example ``"PR body"``) in the message.
    """
    body = text or ""
    if _BREAKING_FOOTER_RE.search(body) or _breaking_footer_line_re(types).search(body):
        return [
            TitleViolation(
                RULE_BREAKING_MARKER,
                f"{source} must not contain a 'BREAKING CHANGE' token or a "
                f"'<type>!:' line. {_BREAKING_GUIDANCE}",
            )
        ]
    return []


def _load_event(args: argparse.Namespace) -> dict | None:
    """Parse the GitHub event JSON, or return ``None`` when it is unavailable."""
    event_path = args.event_path or os.environ.get("GITHUB_EVENT_PATH")
    if not event_path:
        return None
    try:
        with open(event_path, encoding="utf-8") as handle:
            return json.load(handle)
    except (OSError, json.JSONDecodeError):
        return None


def _load_commit_messages(path: str) -> list[str] | None:
    """Read PR commit messages from ``gh api --paginate --slurp`` output.

    The file holds a list of pages; each page is a list of commit objects.
    Returns ``None`` when the file is unreadable or malformed (fail closed).
    """
    try:
        with open(path, encoding="utf-8") as handle:
            pages = json.load(handle)
        return [str(item["commit"]["message"]) for page in pages for item in page]
    except (OSError, json.JSONDecodeError, KeyError, TypeError) as exc:
        print(
            f"pr-title-guard: could not read commit messages from {path}: {exc}",
            file=sys.stderr,
        )
        return None


def _resolve_title(args: argparse.Namespace) -> str | None:
    """Resolve the PR title without ever shell-interpolating untrusted data.

    Priority: explicit ``--title`` (local/testing) -> ``$GITHUB_EVENT_PATH``
    JSON (the CI path) -> ``PR_TITLE`` env var.
    """
    if args.title is not None:
        return args.title

    event_path = args.event_path or os.environ.get("GITHUB_EVENT_PATH")
    if event_path:
        try:
            with open(event_path, encoding="utf-8") as handle:
                event = json.load(handle)
        except (OSError, json.JSONDecodeError) as exc:
            print(
                f"pr-title-guard: could not read event JSON from {event_path}: {exc}",
                file=sys.stderr,
            )
            return None
        title = (event.get("pull_request") or {}).get("title")
        if title is None:
            print(
                "pr-title-guard: no pull_request.title in event payload.",
                file=sys.stderr,
            )
        return title

    return os.environ.get("PR_TITLE")


def _resolve_author(args: argparse.Namespace) -> str | None:
    """Best-effort PR author login from the event JSON (CI path only).

    The event payload is runner-provided (trusted), not PR-controllable, so a PR
    cannot spoof its author to dodge the guard.
    """
    event = _load_event(args) or {}
    return ((event.get("pull_request") or {}).get("user") or {}).get("login")


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Repository-side PR title guard.",
    )
    parser.add_argument(
        "--title",
        default=None,
        help="PR title to validate directly (local/testing only).",
    )
    parser.add_argument(
        "--event-path",
        default=None,
        help="Path to the GitHub event JSON (defaults to $GITHUB_EVENT_PATH).",
    )
    parser.add_argument(
        "--commit-messages-file",
        default=None,
        help=(
            "JSON from `gh api --paginate --slurp .../pulls/N/commits` "
            "(defaults to $PR_COMMIT_MESSAGES_FILE)."
        ),
    )
    args = parser.parse_args(argv)

    # Automated authors (e.g. dependabot[bot]) use controlled title formats;
    # exempt them so dependency PRs are not blocked by the human title policy.
    author = _resolve_author(args)
    if author and author.endswith("[bot]"):
        print(f"pr-title-guard: skipping automated author {author!r}.")
        return 0

    title = _resolve_title(args)
    if title is None:
        # Fail closed: a pull_request event should always carry a title.
        print(
            "pr-title-guard: could not resolve a PR title to validate.",
            file=sys.stderr,
        )
        return 2

    violations = validate_pr_title(title)
    event = _load_event(args) or {}
    violations += validate_merge_text(
        (event.get("pull_request") or {}).get("body"), source="PR body"
    )
    commits_path = args.commit_messages_file or os.environ.get("PR_COMMIT_MESSAGES_FILE")
    if commits_path:
        messages = _load_commit_messages(commits_path)
        if messages is None:
            return 2
        for index, message in enumerate(messages, start=1):
            violations += validate_merge_text(message, source=f"PR commit {index}")
    if violations:
        print(f"pr-title-guard: rejected PR {title!r}:", file=sys.stderr)
        for violation in violations:
            print(f"  {violation.render()}", file=sys.stderr)
        return 1

    print(f"pr-title-guard: OK: {title!r}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
