#!/usr/bin/env python3
"""Assert the built documentation site contains only public pages (ADR 0030).

``docs/public/`` is the sole Sphinx source root, so a correct build can only
generate pages from it. This check proves that on the *generated artifact*: it
walks the built HTML tree and fails if any page does not correspond to a
``docs/public/`` source page, or if any path looks like an internal record (a
decision record, a ``development/`` note). It is the build-time half of the
publication boundary; ``tests/test_readthedocs_config.py`` guards the source-side
contract without a build.

Usage:
    python tools/check_docs_publication_boundary.py <built-html-dir>
"""

from __future__ import annotations

import pathlib
import sys

_ROOT = pathlib.Path(__file__).resolve().parents[1]
_PUBLIC = _ROOT / "docs" / "public"

# Sphinx generates these helper pages regardless of the source set.
_HELPER_PAGES = {"genindex", "search", "py-modindex"}

# Directory names that only ever hold internal records. If one appears in the
# built output, an internal tree leaked into the published site.
_INTERNAL_DIRS = {"decisions", "adrs", "development"}


def _public_page_stems() -> set[str]:
    return {
        str(p.relative_to(_PUBLIC).with_suffix("")).replace("\\", "/")
        for p in _PUBLIC.rglob("*.md")
    }


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print("usage: check_docs_publication_boundary.py <built-html-dir>", file=sys.stderr)
        return 2

    html_dir = pathlib.Path(argv[1]).resolve()
    if not html_dir.is_dir():
        print(f"error: built HTML directory not found: {html_dir}", file=sys.stderr)
        return 2

    allowed = _public_page_stems() | _HELPER_PAGES
    violations: list[str] = []

    for page in sorted(html_dir.rglob("*.html")):
        rel = page.relative_to(html_dir)
        parts = rel.with_suffix("").parts

        # Sphinx's own asset/source directories are not content pages.
        if parts and parts[0] in {"_static", "_sources", "_images", "_downloads"}:
            continue

        if _INTERNAL_DIRS.intersection(parts):
            violations.append(f"internal record published: {rel}")
            continue

        stem = "/".join(parts)
        if stem not in allowed:
            violations.append(f"page not sourced from docs/public/: {rel}")

    if violations:
        print("PUBLICATION BOUNDARY VIOLATION (ADR 0030):", file=sys.stderr)
        for line in violations:
            print(f" - {line}", file=sys.stderr)
        return 1

    print("publication boundary OK: every built page is sourced from docs/public/")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
