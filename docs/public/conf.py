"""Sphinx configuration for the public documentation site (ADR 0030, issue #154).

``docs/public/`` is the sole Sphinx source root. Everything else under ``docs/``
-- ADRs, CI and release notes, and other maintainer records -- lives outside this
directory and is never built, indexed, sitemapped, or previewed. Adding a page
here publishes it; adding a record elsewhere cannot publish it by accident.

The pages are plain CommonMark, cross-linked with relative ``.md`` paths so they
stay readable on GitHub too. MyST parses that markdown directly, and
``myst_heading_anchors`` keeps intra-page anchor links working.

The package is deliberately **not** installed for the docs build. These pages are
narrative -- there is no autodoc -- and installing would drag in the whole pinned
``raes`` runtime closure to render markdown. The version is read straight from
``pyproject.toml`` instead, which keeps the build fast, hermetic, and independent
of the runtime stack.
"""

from __future__ import annotations

import pathlib
import tomllib

# docs/public/conf.py -> parents[2] is the repository root.
_ROOT = pathlib.Path(__file__).resolve().parents[2]
_PYPROJECT = tomllib.loads((_ROOT / "pyproject.toml").read_text(encoding="utf-8"))

# -- Project information -----------------------------------------------------

project = "RAES Environment Packs"
author = _PYPROJECT["project"]["authors"][0]["name"]
copyright = f"{author}, MIT licensed"  # noqa: A001 - Sphinx requires this name.

# release-please owns [project].version (ADR 0008); never hand-edit it here.
release = _PYPROJECT["project"]["version"]
version = release

# -- General configuration ---------------------------------------------------

extensions = [
    "myst_parser",
]

# Anchors are generated down to h3 so intra-page links resolve.
myst_heading_anchors = 3

myst_enable_extensions = [
    "colon_fence",
    "deflist",
]

source_suffix = {
    ".md": "markdown",
}

exclude_patterns = [
    "_build",
]

# A missing cross-reference should fail the build rather than silently publish a
# broken link. Read the Docs surfaces the failure on the PR preview.
nitpicky = True

# -- HTML output -------------------------------------------------------------

html_theme = "furo"
html_title = f"{project} {release}"

# The "Edit this page" links point back into the public source root only, so a
# reader never lands on an internal record from the published site (ADR 0030).
html_theme_options = {
    "source_repository": "https://github.com/RAESystem/env-packs",
    "source_branch": "main",
    "source_directory": "docs/public/",
}

# No custom static assets yet; declaring the (empty) list keeps Sphinx from
# warning about a missing _static directory.
html_static_path = []
