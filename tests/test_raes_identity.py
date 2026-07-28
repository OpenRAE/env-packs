"""Structural contract for the RAES environment-pack hard cut (ADR 0021)."""

from __future__ import annotations

import json
import pathlib
import re
import subprocess
import tomllib
import unittest

import yaml
from raes.module_registry import LOCKFILE_NAME


_ROOT = pathlib.Path(__file__).resolve().parents[1]
_PYPROJECT = _ROOT / "pyproject.toml"
_NEW_PACKAGE = _ROOT / "src" / "raes_env_packs"
_RETIRED_PREFIX = "a" + "ces"
_RETIRED_DISTRIBUTION = f"{_RETIRED_PREFIX}-scenario-packs"
_RETIRED_IMPORT = f"{_RETIRED_PREFIX}_scenario_packs"
_OLD_PACKAGE = _ROOT / "src" / _RETIRED_IMPORT
_GROUND_CONTROL_PROJECT = _RETIRED_DISTRIBUTION
_SONAR_PROJECT_KEY = f"Brad-Edwards_{_RETIRED_DISTRIBUTION}"

_RETIRED_TOKENS = (
    f"{_RETIRED_PREFIX}-sdl",
    f"{_RETIRED_PREFIX}_sdl",
    _RETIRED_DISTRIBUTION,
    _RETIRED_IMPORT,
    f"Brad-Edwards/{_RETIRED_PREFIX}",
)
_HISTORICAL_ALLOWLIST = {
    "CHANGELOG.md",
    "SECURITY.md",
    "docs/decisions/adrs/README.md",
    "docs/decisions/adrs/0021-adopt-raes-environment-pack-identity.md",
    "docs/raes-migration.md",
}
_IMMUTABLE_ADR_ALLOWLIST = {
    f"docs/decisions/adrs/{name}"
    for name in (
        "0001-repository-purpose-and-boundary.md",
        "0002-distribute-as-installable-package.md",
        "0003-build-and-release-model.md",
        "0004-sbom-and-supply-chain.md",
        "0005-automatic-release-on-merge-to-main.md",
        "0006-conventional-commit-releases.md",
        "0007-changelog-driven-versioning.md",
        "0008-adopt-release-please.md",
        "0009-scenario-packs-subordinate-to-aces.md",
        "0010-consume-aces-reusable-asset-trust-policy.md",
        f"0011-require-pinned-{_RETIRED_PREFIX}-sdl-validation.md",
        "0012-pack-content-identity-and-trust-boundary.md",
        "0013-separate-consumer-static-validation-from-author-ci.md",
        "0014-consume-aces-concept-authority.md",
        "0015-attest-python-distribution-build-provenance.md",
        "0016-automate-dependency-updates.md",
        "0017-sign-release-tags-with-keyless-sigstore.md",
        "0018-openssf-scorecard-posture.md",
        "0019-preserve-history-in-dev-main-promotions.md",
        "0020-no-auto-merge.md",
    )
}
_BOUND_IDENTITY_LINES = {
    ".ground-control.yaml": (
        f"project: {_GROUND_CONTROL_PROJECT}",
        f"project_key: {_SONAR_PROJECT_KEY}",
    ),
    "sonar-project.properties": (
        f"https://sonarcloud.io/project/overview?id={_SONAR_PROJECT_KEY}",
        f"sonar.projectKey={_SONAR_PROJECT_KEY}",
    ),
}


def _project() -> dict:
    with _PYPROJECT.open("rb") as handle:
        return tomllib.load(handle)["project"]


def _tracked_files() -> list[pathlib.Path]:
    output = subprocess.run(
        ["git", "ls-files", "-z"],
        cwd=_ROOT,
        check=True,
        stdout=subprocess.PIPE,
    ).stdout
    return [
        _ROOT / path.decode("utf-8")
        for path in output.split(b"\0")
        if path
    ]


class PackageIdentityTests(unittest.TestCase):
    def test_distribution_import_tree_and_scripts_use_one_identity(self) -> None:
        project = _project()
        self.assertEqual(project["name"], "raes-env-packs")
        self.assertTrue(_NEW_PACKAGE.is_dir())
        self.assertFalse(_OLD_PACKAGE.exists())
        self.assertEqual(
            project["scripts"],
            {
                "raes-pack-validate": "raes_env_packs.content_ci:main",
                "raes-pack-release": "raes_env_packs.release:main",
                "raes-new-pack": "raes_env_packs.new_pack:main",
                "raes-pack-issue-skeleton": "raes_env_packs.issue_skeleton:main",
            },
        )

    def test_raes_is_the_single_exact_upstream_pin(self) -> None:
        dependencies = _project()["dependencies"]
        specs = [
            dependency.replace(" ", "")
            for dependency in dependencies
            if re.match(r"raes(?![\w-])", dependency.strip())
        ]
        self.assertEqual(len(specs), 1)
        self.assertRegex(specs[0], r"\Araes==[^=<>!~;,\s]+\Z")
        self.assertFalse(
            any(
                dependency.startswith(
                    (f"{_RETIRED_PREFIX}-sdl", _RETIRED_DISTRIBUTION)
                )
                for dependency in dependencies
            )
        )
        self.assertEqual(_project()["requires-python"], ">=3.11")


class PackContractIdentityTests(unittest.TestCase):
    def test_pack_owned_contracts_advance_together(self) -> None:
        schemas = _NEW_PACKAGE / "resources" / "schemas"
        compatibility = yaml.safe_load(
            (schemas / "pack-compatibility.schema.yaml").read_text(encoding="utf-8")
        )
        provenance = yaml.safe_load(
            (schemas / "provenance.schema.yaml").read_text(encoding="utf-8")
        )
        self.assertEqual(
            compatibility["$id"],
            "https://raes.dev/schemas/environment-pack-compatibility-v2.json",
        )
        self.assertEqual(
            compatibility["properties"]["schema_version"]["const"],
            "environment-pack-compatibility/v2",
        )
        self.assertEqual(
            provenance["$id"],
            "https://raes.dev/schemas/environment-pack-provenance-v3.json",
        )
        self.assertEqual(
            provenance["properties"]["schema_version"]["const"],
            "environment-pack-provenance/v3",
        )

        layout = (
            _NEW_PACKAGE / "resources" / "contract" / "pack-layout.md"
        ).read_text(encoding="utf-8")
        self.assertIn("Environment-pack contract version:** `4`", layout)

        digest = (_NEW_PACKAGE / "digest.py").read_text(encoding="utf-8")
        self.assertIn('_PACK_URI_SCHEME = "raes-environment-pack"', digest)

    def test_current_surfaces_use_the_raes_lockfile_name(self) -> None:
        self.assertEqual(LOCKFILE_NAME, "raes.lock.json")
        current_surfaces = (
            _ROOT / "docs" / "environment-packs.md",
            _ROOT / "docs" / "raes-migration.md",
            _NEW_PACKAGE / "resources" / "contract" / "pack-layout.md",
            _NEW_PACKAGE / "resources" / "schemas" / "provenance.schema.yaml",
        )
        for path in current_surfaces:
            with self.subTest(path=path.relative_to(_ROOT)):
                text = path.read_text(encoding="utf-8")
                self.assertIn(LOCKFILE_NAME, text)
                self.assertNotIn("aces.lock.json", text)

    def test_release_please_tracks_the_new_distribution(self) -> None:
        config = json.loads(
            (_ROOT / "release-please-config.json").read_text(encoding="utf-8")
        )
        self.assertEqual(config["packages"]["."]["package-name"], "raes-env-packs")


class RepositoryIdentityTests(unittest.TestCase):
    def test_current_surfaces_do_not_reintroduce_retired_names(self) -> None:
        violations: list[str] = []
        for path in _tracked_files():
            relative = path.relative_to(_ROOT).as_posix()
            if (
                relative in _HISTORICAL_ALLOWLIST
                or relative in _IMMUTABLE_ADR_ALLOWLIST
                or not path.is_file()
            ):
                continue
            try:
                text = path.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                continue
            for allowed_line in _BOUND_IDENTITY_LINES.get(relative, ()):
                self.assertEqual(
                    text.count(allowed_line),
                    1,
                    f"{relative} must retain exactly one bound external identity "
                    f"line: {allowed_line}",
                )
                text = text.replace(allowed_line, "", 1)
            for token in _RETIRED_TOKENS:
                if token in text:
                    violations.append(f"{relative}: {token}")
        self.assertEqual(
            violations,
            [],
            "retired identities may survive only in the narrow historical "
            f"allowlist: {violations}",
        )

    def test_ground_control_and_sonar_use_their_bound_project_identities(self) -> None:
        ground_control = yaml.safe_load(
            (_ROOT / ".ground-control.yaml").read_text(encoding="utf-8")
        )
        self.assertEqual(ground_control["project"], _GROUND_CONTROL_PROJECT)
        self.assertEqual(ground_control["short_code"], "ASP")
        self.assertEqual(
            ground_control["docs"]["workflow_reference"],
            "docs/environment-packs.md",
        )
        self.assertEqual(
            ground_control["example_paths"]["source"],
            "src/raes_env_packs/",
        )
        self.assertEqual(
            ground_control["sonarcloud"],
            {
                "project_key": _SONAR_PROJECT_KEY,
                "organization": "brad-edwards",
            },
        )

        sonar = (_ROOT / "sonar-project.properties").read_text(encoding="utf-8")
        self.assertIn(f"sonar.projectKey={_SONAR_PROJECT_KEY}", sonar)
        self.assertIn("sonar.organization=brad-edwards", sonar)


if __name__ == "__main__":
    unittest.main()
