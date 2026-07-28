"""Sphinx configuration for the Read the Docs build (issue #142).

The documentation in this directory is plain CommonMark, cross-linked with
relative ``.md`` paths so it stays readable on GitHub. MyST parses that markdown
directly, and ``myst_heading_anchors`` keeps the existing intra-page anchor links
working, so publishing to Read the Docs needs no rewriting of the source files.

The package is deliberately **not** installed for the docs build. These pages are
narrative -- there is no autodoc -- and installing would drag in the whole pinned
``raes`` runtime closure (FastAPI, uvicorn, cryptography, ...) to render
markdown. The version below is read straight from ``pyproject.toml`` instead,
which keeps the build fast, hermetic, and independent of the runtime stack.
"""

from __future__ import annotations

import pathlib
import tomllib

_ROOT = pathlib.Path(__file__).resolve().parents[1]
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

# The ADR set is the bulk of these docs and is heavily cross-linked; anchors are
# generated down to h3 so those links resolve.
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

# No custom static assets yet; declaring the (empty) list keeps Sphinx from
# warning about a missing _static directory.
html_static_path = []
