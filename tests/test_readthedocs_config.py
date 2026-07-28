"""Static contract for the public documentation boundary (ADR 0030, issue #154).

``docs/public/`` is the sole Sphinx source root: only pages under it are built,
indexed, sitemapped, and previewed. ADRs and other maintainer records live
elsewhere under ``docs/`` and must never enter the published site. The site
itself can only be observed on a real build, but the configuration and structure
that produce the boundary are guarded here so a regression -- a source root that
drifts back over the whole tree, an internal record linked into the public
navigation, a warning-tolerant build, a dropped requirements pin -- fails locally
and in CI instead of quietly shipping.

Mirrors the existing config-contract tests (tests/test_ci_topology.py,
tests/test_scorecard_workflow.py) and reuses the same unittest + PyYAML stack.
"""

from __future__ import annotations

import pathlib
import re
import tomllib
import unittest

import yaml

_ROOT = pathlib.Path(__file__).resolve().parents[1]
_CONFIG = _ROOT / ".readthedocs.yaml"
_PUBLIC = _ROOT / "docs" / "public"
_CONF_PY = _PUBLIC / "conf.py"
_DOCS_LOCK = _ROOT / "requirements" / "docs.txt"
_INDEX = _PUBLIC / "index.md"
_DEV_INDEX = _ROOT / "docs" / "README.md"
_README = _ROOT / "README.md"

# The interpreter every other automated surface in this repo uses. Docs drifting
# onto a different one is how "works locally, breaks on RTD" starts.
_EXPECTED_PYTHON = "3.12"

# Every markdown link target: the "x" in [text](x).
_LINK = re.compile(r"\]\(([^)]+)\)")


def _load() -> dict:
    return yaml.safe_load(_CONFIG.read_text(encoding="utf-8"))


def _public_pages() -> set[str]:
    """Every public page name relative to docs/public/, without the .md suffix."""
    return {
        str(p.relative_to(_PUBLIC)).removesuffix(".md")
        for p in _PUBLIC.rglob("*.md")
    }


def _link_targets(text: str) -> list[str]:
    return [m.group(1).strip() for m in _LINK.finditer(text)]


class ReadTheDocsConfigTests(unittest.TestCase):
    def setUp(self) -> None:
        self.data = _load()

    def test_uses_config_version_two(self) -> None:
        # v1 is long unsupported; RTD silently ignores keys it cannot parse.
        self.assertEqual(self.data.get("version"), 2)

    def test_build_image_and_python_are_declared(self) -> None:
        build = self.data.get("build")
        self.assertIsInstance(build, dict, ".readthedocs.yaml must declare `build`")
        self.assertTrue(build.get("os"), "build.os must be pinned, not left to RTD's default")
        self.assertEqual(
            build.get("tools", {}).get("python"),
            _EXPECTED_PYTHON,
            "the docs build must use the same Python as CI, SonarCloud, and the "
            "release build (#142)",
        )

    def test_sphinx_configuration_points_at_public_conf_py(self) -> None:
        sphinx = self.data.get("sphinx")
        self.assertIsInstance(sphinx, dict, ".readthedocs.yaml must declare `sphinx`")
        self.assertEqual(
            sphinx.get("configuration"),
            "docs/public/conf.py",
            "the build must be rooted at docs/public/, the sole public source "
            "root (ADR 0030)",
        )
        self.assertTrue(_CONF_PY.is_file(), "docs/public/conf.py must exist")

    def test_build_fails_on_warning(self) -> None:
        # A broken cross-reference is a defect, not a note. Without this, RTD
        # publishes dead links and nothing reports it.
        self.assertIs(
            self.data["sphinx"].get("fail_on_warning"),
            True,
            "sphinx.fail_on_warning must be true so broken references fail the "
            "build instead of publishing (#142)",
        )

    def test_docs_requirements_are_hash_locked(self) -> None:
        install = self.data.get("python", {}).get("install")
        self.assertTrue(install, "the docs build must install its requirements")
        targets = [entry.get("requirements") for entry in install if isinstance(entry, dict)]
        self.assertIn(
            "requirements/docs.txt",
            targets,
            "the docs build must install the hash-locked requirements/docs.txt "
            "so it resolves the same artifacts as every other install (#142)",
        )
        self.assertTrue(_DOCS_LOCK.is_file(), "requirements/docs.txt must exist")
        text = _DOCS_LOCK.read_text(encoding="utf-8")
        self.assertIn("--hash=sha256:", text, "requirements/docs.txt must carry hashes")

    def test_package_itself_is_not_installed_for_docs(self) -> None:
        # Deliberate: the pages are narrative markdown with no autodoc, so
        # installing would pull the whole pinned raes runtime closure just to
        # render text. docs/public/conf.py reads the version from pyproject.toml.
        install = self.data.get("python", {}).get("install", [])
        self.assertNotIn(
            ".",
            [entry.get("path") for entry in install if isinstance(entry, dict)],
            "the docs build should not install the package; see docs/public/conf.py",
        )


class SphinxConfTests(unittest.TestCase):
    def test_conf_py_does_not_hardcode_the_version(self) -> None:
        # release-please owns [project].version (ADR 0008). A literal here would
        # go stale at the next release and nothing would catch it.
        text = _CONF_PY.read_text(encoding="utf-8")
        declared = tomllib.loads(
            (_ROOT / "pyproject.toml").read_text(encoding="utf-8")
        )["project"]["version"]
        self.assertNotIn(
            f'"{declared}"', text,
            "docs/public/conf.py must derive the version from pyproject.toml, not "
            "restate it (ADR 0008)",
        )
        self.assertIn("pyproject.toml", text)

    def test_markdown_is_parsed_by_myst(self) -> None:
        text = _CONF_PY.read_text(encoding="utf-8")
        self.assertIn("myst_parser", text, "the docs are markdown; MyST must parse them")

    def test_theme_edit_links_stay_in_the_public_root(self) -> None:
        # The Furo "edit this page" links must point back into docs/public/ only,
        # so a reader never reaches an internal record from the published site.
        text = _CONF_PY.read_text(encoding="utf-8")
        self.assertIn(
            '"docs/public/"', text,
            "conf.py must set source_directory to docs/public/ (ADR 0030)",
        )


class PublicationBoundaryTests(unittest.TestCase):
    """docs/public/ is the whole published surface; internal records stay out."""

    def test_no_decision_records_under_the_public_root(self) -> None:
        # ADRs are internal records. If one lived under docs/public/ it would be
        # published; the boundary is the directory, not a toctree (ADR 0030).
        self.assertFalse(
            (_PUBLIC / "decisions").exists(),
            "decision records must not live under docs/public/ (ADR 0030)",
        )
        stray = [
            str(p.relative_to(_PUBLIC))
            for p in _PUBLIC.rglob("*.md")
            if re.match(r"\d{4}-", p.name)
        ]
        self.assertEqual(
            stray, [],
            f"ADR-shaped pages must not live under docs/public/: {stray} (ADR 0030)",
        )

    def test_internal_records_live_outside_the_public_root(self) -> None:
        for record in (
            _ROOT / "docs" / "decisions" / "adrs" / "README.md",
            _ROOT / "docs" / "development" / "ci.md",
            _ROOT / "docs" / "development" / "scrub-policy.md",
        ):
            with self.subTest(record=record.relative_to(_ROOT)):
                self.assertTrue(record.is_file(), f"{record} must exist in the repo")
                self.assertNotIn(
                    _PUBLIC, record.parents,
                    f"{record} is a developer record and must stay out of "
                    "docs/public/ (ADR 0030)",
                )

    def test_public_pages_do_not_relative_link_outside_the_root(self) -> None:
        # A relative link that escapes docs/public/ (e.g. ../decisions/...) both
        # breaks the warning-strict build and points a reader at an internal
        # record. Reference repo files from a public page by absolute URL instead.
        for page in sorted(_PUBLIC.rglob("*.md")):
            for target in _link_targets(page.read_text(encoding="utf-8")):
                if target.startswith(("http://", "https://", "#", "mailto:")):
                    continue
                with self.subTest(page=page.relative_to(_ROOT), target=target):
                    self.assertFalse(
                        target.startswith("../") or target.startswith("/"),
                        f"{page.relative_to(_ROOT)} links '{target}', which "
                        "escapes docs/public/; use an absolute URL for repo files "
                        "(ADR 0030)",
                    )


class DeveloperIndexTests(unittest.TestCase):
    """The developer index is the entry point to the internal records."""

    def test_developer_index_exists_and_reaches_the_records(self) -> None:
        self.assertTrue(_DEV_INDEX.is_file(), "docs/README.md (developer index) must exist")
        text = _DEV_INDEX.read_text(encoding="utf-8")
        for record in (
            "decisions/adrs/README.md",
            "development/ci.md",
            "development/scrub-policy.md",
        ):
            with self.subTest(record=record):
                self.assertIn(
                    record, text,
                    f"the developer index must link {record} so internal records "
                    "stay reachable (ADR 0030)",
                )

    def test_contributing_reaches_the_developer_index(self) -> None:
        contributing = (_ROOT / "CONTRIBUTING.md").read_text(encoding="utf-8")
        self.assertIn(
            "docs/README.md", contributing,
            "CONTRIBUTING.md must link the developer index (ADR 0030)",
        )


class DocsNavigationTests(unittest.TestCase):
    def test_public_index_declares_a_toctree(self) -> None:
        self.assertIn(
            "{toctree}",
            _INDEX.read_text(encoding="utf-8"),
            "docs/public/index.md must declare a toctree so pages are navigable",
        )

    def test_every_public_page_is_reachable(self) -> None:
        # Every published page must sit in a toctree; with fail_on_warning an
        # orphan page breaks the build.
        toctrees = "\n".join(
            p.read_text(encoding="utf-8")
            for p in _PUBLIC.rglob("*.md")
            if "{toctree}" in p.read_text(encoding="utf-8")
        )
        for page in sorted(_public_pages()):
            if page == "index":
                continue
            with self.subTest(page=page):
                self.assertIn(
                    page, toctrees,
                    f"docs/public/{page}.md is not referenced by any toctree; with "
                    "fail_on_warning an unreachable page fails the build",
                )


class DocsBadgeTests(unittest.TestCase):
    def test_readme_links_the_documentation(self) -> None:
        self.assertIn(
            "readthedocs",
            _README.read_text(encoding="utf-8").lower(),
            "README must advertise the published documentation (#142)",
        )


if __name__ == "__main__":
    unittest.main()
