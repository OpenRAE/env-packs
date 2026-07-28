"""Static contract for the Read the Docs build (issue #142).

The published site can only be observed on a real Read the Docs build, but the
configuration that produces it is guarded here so a silent regression -- a
dropped requirements pin, a warning-tolerant build, an interpreter that drifts
away from the rest of CI -- fails locally and in CI instead of quietly shipping
broken or stale documentation.

Mirrors the existing workflow-contract tests (tests/test_scorecard_workflow.py,
tests/test_codeql_workflow.py) and reuses the same unittest + PyYAML stack rather
than introducing another config-validation framework.
"""

from __future__ import annotations

import pathlib
import tomllib
import unittest

import yaml

_ROOT = pathlib.Path(__file__).resolve().parents[1]
_CONFIG = _ROOT / ".readthedocs.yaml"
_CONF_PY = _ROOT / "docs" / "conf.py"
_DOCS_LOCK = _ROOT / "requirements" / "docs.txt"
_INDEX = _ROOT / "docs" / "index.md"
_README = _ROOT / "README.md"

# The interpreter every other automated surface in this repo uses. Docs drifting
# onto a different one is how "works locally, breaks on RTD" starts.
_EXPECTED_PYTHON = "3.12"


def _load() -> dict:
    return yaml.safe_load(_CONFIG.read_text(encoding="utf-8"))


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

    def test_sphinx_configuration_points_at_conf_py(self) -> None:
        sphinx = self.data.get("sphinx")
        self.assertIsInstance(sphinx, dict, ".readthedocs.yaml must declare `sphinx`")
        self.assertEqual(sphinx.get("configuration"), "docs/conf.py")
        self.assertTrue(_CONF_PY.is_file(), "docs/conf.py must exist")

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
        # render text. docs/conf.py reads the version from pyproject.toml.
        install = self.data.get("python", {}).get("install", [])
        self.assertNotIn(
            ".",
            [entry.get("path") for entry in install if isinstance(entry, dict)],
            "the docs build should not install the package; see docs/conf.py",
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
            "docs/conf.py must derive the version from pyproject.toml, not "
            "restate it (ADR 0008)",
        )
        self.assertIn("pyproject.toml", text)

    def test_markdown_is_parsed_by_myst(self) -> None:
        text = _CONF_PY.read_text(encoding="utf-8")
        self.assertIn("myst_parser", text, "the docs are markdown; MyST must parse them")


class DocsNavigationTests(unittest.TestCase):
    def test_index_declares_a_toctree(self) -> None:
        # Every page must be reachable; with fail_on_warning an orphan page
        # breaks the build, so this catches it before RTD does.
        self.assertIn(
            "{toctree}",
            _INDEX.read_text(encoding="utf-8"),
            "docs/index.md must declare a toctree so pages are navigable",
        )

    def test_every_docs_page_is_reachable(self) -> None:
        pages = {
            str(p.relative_to(_ROOT / "docs")).removesuffix(".md")
            for p in (_ROOT / "docs").rglob("*.md")
        }
        # The ADR set is pulled in by a glob toctree in its own README.
        adr_readme = "decisions/adrs/README"
        toctrees = "\n".join(
            p.read_text(encoding="utf-8")
            for p in (_ROOT / "docs").rglob("*.md")
            if "{toctree}" in p.read_text(encoding="utf-8")
        )
        for page in sorted(pages):
            if page == "index" or page.startswith("decisions/adrs/0"):
                continue
            with self.subTest(page=page):
                name = page.rsplit("/", 1)[-1] if page == adr_readme else page
                self.assertIn(
                    name, toctrees,
                    f"docs/{page}.md is not referenced by any toctree; with "
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
