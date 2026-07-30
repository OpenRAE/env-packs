"""Environment-pack catalog projection (issue #188, ADR 0032).

The catalog is one generated read model over existing authorities. These tests
exercise the projection, the explicit state families, deterministic
collision-safe aggregation, the safe-for-untrusted-input boundary, and the CLI
process contract — plus synthetic fixtures for the five required scenario
families (they vary authority *combinations*, never a new category enum).
"""

from __future__ import annotations

import io
import json
import os
import shutil
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

import yaml
from unittest import mock

from raes_env_packs import catalog, publication
from raes_env_packs.validation import validate_pack

_ROOT = Path(__file__).resolve().parents[1]
_TEMPLATE = _ROOT / "src" / "raes_env_packs" / "resources" / "template"
_VALID_SDL = "name: {name}\nnodes:\n  target:\n    type: vm\n"


def _load(path: Path) -> dict:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def _dump(path: Path, value: object) -> None:
    path.write_text(yaml.safe_dump(value, sort_keys=False), encoding="utf-8")


def _valid_pack(parent: Path, name: str) -> Path:
    """A pack that passes ``validate_pack`` — the canonical quickstart shape."""

    root = parent / name
    shutil.copytree(_TEMPLATE, root)
    for rel in ("pack.yaml", "pack.compatibility.yaml", "docs/provenance-ledger.yaml"):
        path = root / rel
        path.write_text(
            path.read_text(encoding="utf-8").replace("<name>", name), encoding="utf-8"
        )
    (root / "sdl" / "example.sdl.yaml").write_text(
        _VALID_SDL.format(name=name), encoding="utf-8"
    )
    return root


def _set_manifest(root: Path, **fields: object) -> None:
    manifest = _load(root / "pack.yaml")
    manifest.update(fields)
    _dump(root / "pack.yaml", manifest)


def _set_compat(root: Path, **fields: object) -> None:
    compat = _load(root / "pack.compatibility.yaml")
    compat.update(fields)
    _dump(root / "pack.compatibility.yaml", compat)


def _set_provenance(root: Path, **fields: object) -> None:
    ledger = _load(root / "docs" / "provenance-ledger.yaml")
    ledger.update(fields)
    _dump(root / "docs" / "provenance-ledger.yaml", ledger)


def _write(root: Path, rel: str, content: str = "x") -> None:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _minimal_pack(parent: Path, name: str = "minimal-pack") -> Path:
    """A valid pack that declares no compatibility surfaces (many unknowns)."""

    root = _valid_pack(parent, name)
    _set_manifest(root, compatibility_manifest=None, description="")
    (root / "pack.compatibility.yaml").unlink()
    manifest = _load(root / "pack.yaml")
    manifest.pop("compatibility_manifest", None)
    _dump(root / "pack.yaml", manifest)
    return root


def _run(*argv: str) -> tuple[int, str, str]:
    out, err = io.StringIO(), io.StringIO()
    with redirect_stdout(out), redirect_stderr(err):
        try:
            code = catalog.main(list(argv))
        except SystemExit as exc:
            # argparse usage errors exit via SystemExit; its code is the status.
            code = int(exc.code) if isinstance(exc.code, int) else catalog.EXIT_USAGE
    return code, out.getvalue(), err.getvalue()


# --------------------------------------------------------------------------
# Synthetic fixtures for the five required scenario families (AC5). Each varies
# the authority combination, not a scenario-category enum.
# --------------------------------------------------------------------------
def _ai_research_pack(parent: Path) -> Path:
    root = _valid_pack(parent, "ai-research-pack")
    _set_manifest(
        root,
        title="Agentic red-team research range",
        description="Benchmark an autonomous agent against a scored objective.",
        status="golden",
        difficulty="advanced",
        participant_time="2-4 hours",
    )
    _set_compat(
        root,
        runtime_profiles=[
            {"profile_id": "local_minimal", "status": "supported", "provider": "docker", "description": "single-host docker"},
            {"profile_id": "aws_full", "status": "planned", "description": "full AWS estate"},
        ],
        delivery_bundles=[
            {"bundle_id": "bench", "status": "supported", "audience": "agent-benchmark"}
        ],
        assets=[
            {"asset_id": "diagram", "path": "assets/topology.svg", "visibility": "public", "status": "shipped"}
        ],
    )
    _write(root, "assets/topology.svg")
    _set_provenance(
        root,
        artifacts=[
            {"artifact_id": "media", "path": "assets/topology.svg", "classification": "open"},
            {"artifact_id": "docs", "path": "docs/", "classification": "commercial-only"},
        ],
    )
    return root


def _security_pack(parent: Path) -> Path:
    root = _valid_pack(parent, "security-pack")
    _set_manifest(
        root,
        title="Purple-team AD intrusion",
        description="Emulated intrusion across an Active Directory estate.",
        status="built",
    )
    _set_compat(
        root,
        runtime_profiles=[{"profile_id": "aws_minimal", "status": "required", "description": "minimal AWS estate"}],
        delivery_bundles=[
            {"bundle_id": "pt", "status": "supported", "audience": "purple-team"}
        ],
    )
    return root


def _resilience_pack(parent: Path) -> Path:
    root = _valid_pack(parent, "resilience-dr-pack")
    _set_manifest(
        root,
        title="Regional failover drill",
        description="Exercise disaster-recovery runbooks under a region loss.",
        status="draft",
    )
    # Minimal compatibility: no runtimes/bundles → mostly unknown/unsupported.
    return root


def _product_testing_pack(parent: Path) -> Path:
    root = _valid_pack(parent, "product-testing-pack")
    _set_manifest(
        root,
        title="Checkout flow product test",
        description="Validate a checkout flow against seeded fixtures.",
        status="built",
    )
    _set_compat(
        root,
        delivery_bundles=[
            {"bundle_id": "demo", "status": "supported", "audience": "demo"},
            {"bundle_id": "guided", "status": "planned", "audience": "guided"},
        ],
    )
    return root


def _simulator_pack(parent: Path) -> Path:
    root = _valid_pack(parent, "simulator-backed-pack")
    _set_manifest(
        root,
        title="OT plant simulator",
        description="Operate against a simulated industrial control plant.",
        status="golden",
    )
    _set_compat(
        root,
        runtime_profiles=[
            {"profile_id": "sim_local", "status": "supported", "provider": "plant-sim", "description": "local plant simulator"}
        ],
        platform_features=[
            {"feature_id": "ot-plc", "status": "required", "description": "simulated PLC network", "runtime_profiles": ["sim_local"]}
        ],
    )
    return root


_FIXTURES = (
    _ai_research_pack,
    _security_pack,
    _resilience_pack,
    _product_testing_pack,
    _simulator_pack,
)


class CatalogFixture(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)

    def _source(self, root: Path, sid: str = "local", rev: str = "r1") -> catalog.Source:
        return catalog.Source(id=sid, revision=rev, root=str(root))

    def _build(self, *sources: catalog.Source, as_of: str = "2026-07-30") -> tuple:
        return catalog.build_catalog(list(sources), as_of=as_of)


class SinglePackCliTests(CatalogFixture):
    def test_single_valid_pack_generates_a_one_entry_document(self) -> None:
        root = _ai_research_pack(self.tmp)
        code, out, err = _run(str(root), "--as-of", "2026-07-30")
        self.assertEqual(code, catalog.EXIT_OK, err)
        document = json.loads(out)
        self.assertEqual(document["schema_version"], catalog.SCHEMA_VERSION)
        self.assertEqual(len(document["entries"]), 1)
        self.assertEqual(document["entries"][0]["name"], "ai-research-pack")
        self.assertEqual(document["entries"][0]["maturity"], "golden")

    def test_generated_document_validates_against_the_packaged_schema(self) -> None:
        root = _ai_research_pack(self.tmp)
        doc, _diags = self._build(self._source(root))
        self.assertEqual(catalog.validate_document(doc), [])

    def test_preview_mode_renders_a_card_and_writes_nothing_to_stderr(self) -> None:
        root = _security_pack(self.tmp)
        code, out, err = _run(str(root), "--preview")
        self.assertEqual(code, catalog.EXIT_OK, err)
        self.assertIn("security-pack", out)
        self.assertIn("purpose:", out)
        self.assertEqual(err, "")

    def test_json_mode_stdout_is_only_the_document(self) -> None:
        root = _security_pack(self.tmp)
        code, out, err = _run(str(root))
        self.assertEqual(code, catalog.EXIT_OK)
        json.loads(out)  # parses cleanly; nothing else on stdout
        self.assertEqual(err, "")


class StateFamilyTests(CatalogFixture):
    def _entry(self, root: Path) -> dict:
        doc, _diags = self._build(self._source(root))
        return doc.entries[0]

    def test_known_and_unknown_discovery_states(self) -> None:
        entry = self._entry(_ai_research_pack(self.tmp))
        self.assertEqual(entry["purpose"]["state"], "known")
        self.assertIn("value", entry["purpose"])
        self.assertEqual(entry["difficulty"]["state"], "known")  # declared
        self.assertEqual(entry["resource_cost"]["state"], "unknown")
        self.assertNotIn("value", entry["resource_cost"])

    def test_minimal_pack_is_truthfully_unknown_with_completeness_notes(self) -> None:
        root = _minimal_pack(self.tmp)
        doc, diags = self._build(self._source(root))
        entry = doc.entries[0]
        self.assertEqual(entry["purpose"]["state"], "unknown")
        self.assertEqual(entry["audiences"]["state"], "unknown")
        codes = {note["code"] for note in entry["completeness"]}
        self.assertIn("catalog.purpose.undeclared", codes)
        self.assertIn("catalog.difficulty.undeclared", codes)
        # Completeness is non-blocking: the pack is still catalogued and valid.
        self.assertTrue(validate_pack(str(root)).ok)
        self.assertFalse(any(d.blocking for d in diags))

    def test_supported_and_unsupported_capability_states(self) -> None:
        entry = self._entry(_ai_research_pack(self.tmp))
        support = {r["profile_id"]: r["support"] for r in entry["runtimes"]}
        self.assertEqual(support["local_minimal"], "supported")
        self.assertEqual(support["aws_full"], "unsupported")  # status: planned

    def test_trust_is_unverified_and_rehearsal_is_unknown(self) -> None:
        entry = self._entry(_simulator_pack(self.tmp))
        self.assertEqual(entry["trust"]["state"], "unverified")
        self.assertEqual(entry["last_rehearsal"]["state"], "unknown")
        # golden maturity is never upgraded into trust or rehearsal evidence.
        self.assertEqual(entry["maturity"], "golden")

    def test_safety_and_provenance_are_leak_safe_counts(self) -> None:
        entry = self._entry(_security_pack(self.tmp))
        # The template ledger this fixture uses has content_safety all-true and
        # exactly one source row, so assert the concrete projected values — a
        # type-only check would pass even if the projection inverted its logic.
        self.assertEqual(entry["safety"]["state"], "known")
        self.assertIs(entry["safety"]["attestations_satisfied"], True)
        self.assertEqual(entry["provenance"]["state"], "known")
        self.assertEqual(entry["provenance"]["sources"], 1)


class ReleaseProjectionTests(CatalogFixture):
    def test_absent_publication_is_unknown(self) -> None:
        entry = self._build(self._source(_security_pack(self.tmp)))[0].entries[0]
        self.assertEqual(entry["release"]["state"], "unknown")

    def test_present_but_invalid_publication_is_unverified_not_a_crash(self) -> None:
        root = _valid_pack(self.tmp, "pub-pack")
        _set_manifest(root, publication_supply="publication-supply.yaml")
        # A structurally incomplete publication profile must project as a
        # truthful `unverified`, never crash the generator (foreign input).
        _dump(root / "publication-supply.yaml", {"schema_version": "environment-pack-publication/v1"})
        entry = self._build(self._source(root))[0].entries[0]
        self.assertEqual(entry["release"]["state"], "unverified")

    def test_declared_but_unreadable_publication_is_unverified_not_unknown(self) -> None:
        # A declared pointer whose document did not load is *present*, not
        # absent — it must not collapse to `unknown`.
        result = catalog._project_release(None, True, ())
        self.assertEqual(result["state"], "unverified")

    def test_valid_publication_projects_known_identity(self) -> None:
        with mock.patch.object(publication, "validate_publication_document", return_value=[]):
            with mock.patch.object(
                publication,
                "release_identity",
                return_value={"pack": {"name": "mine", "version": "1.0.0"}},
            ):
                projected = catalog._project_release({"x": 1}, True, ())
        self.assertEqual(projected["state"], "known")
        self.assertEqual(projected["name"], "mine")

    def test_unexpected_publication_failure_propagates_not_masked(self) -> None:
        # An unexpected exception is a tool failure, never mislabeled as a
        # foreign-input `unverified` (ADR 0032).
        with mock.patch.object(
            publication, "validate_publication_document", side_effect=RuntimeError("boom")
        ):
            with self.assertRaises(RuntimeError):
                catalog._project_release({"x": 1}, True, ())


class StateInvariantTests(unittest.TestCase):
    """The relational state/value contract is enforced, not just schema shape."""

    def _entry(self, **overrides: object) -> dict:
        # A minimally shaped entry with every field in a valid `unknown` state,
        # then apply the contradiction under test.
        base: dict[str, object] = {
            field: {"state": "unknown"}
            for field in catalog._STATE_FIELDS
        }
        base.update(overrides)
        return base

    def _violations(self, entry: dict) -> list[str]:
        return catalog._state_invariant_violations({"entries": [entry]})

    def test_known_discovery_without_value_is_flagged(self) -> None:
        v = self._violations(self._entry(purpose={"state": "known"}))
        self.assertTrue(any("purpose.value" in x and "state-requires-field" in x for x in v))

    def test_unknown_discovery_with_value_is_flagged(self) -> None:
        v = self._violations(self._entry(license={"state": "unknown", "value": "x"}))
        self.assertTrue(any("license.value" in x and "state-forbids-field" in x for x in v))

    def test_unknown_list_with_values_is_flagged(self) -> None:
        v = self._violations(self._entry(audiences={"state": "unknown", "values": ["a"]}))
        self.assertTrue(any("audiences.values" in x and "state-forbids-field" in x for x in v))

    def test_verified_rehearsal_without_evidence_is_flagged(self) -> None:
        v = self._violations(self._entry(last_rehearsal={"state": "verified"}))
        self.assertTrue(any("last_rehearsal.as_of" in x and "state-requires-field" in x for x in v))

    def test_non_known_release_with_identity_is_flagged(self) -> None:
        v = self._violations(self._entry(release={"state": "unverified", "name": "p"}))
        self.assertTrue(any("release.name" in x and "state-forbids-field" in x for x in v))

    def test_a_well_formed_entry_has_no_state_violations(self) -> None:
        entry = self._entry(
            purpose={"state": "known", "value": "p"},
            audiences={"state": "known", "values": ["a"]},
            last_rehearsal={"state": "verified", "as_of": "2026-07-30", "profile": "x"},
            release={"state": "known", "name": "p", "version": "1.0.0"},
        )
        self.assertEqual(self._violations(entry), [])


class MediaBoundaryTests(CatalogFixture):
    def test_media_is_bound_to_inventory_and_provenance_authorities(self) -> None:
        root = _valid_pack(self.tmp, "media-pack")
        # Files that actually exist (existence of shipped assets is a
        # validate_pack invariant; see ValidationSeamTests).
        _write(root, "assets/pub.svg")
        _write(root, "operator/secret.md")
        _write(root, "assets/planned.svg")
        _write(root, "assets/commercial.svg")
        _set_compat(
            root,
            assets=[
                # eligible: public, shipped, in inventory, provenance = open
                {"asset_id": "pub", "path": "assets/pub.svg", "visibility": "public", "status": "shipped"},
                # excluded: restricted visibility
                {"asset_id": "sec", "path": "operator/secret.md", "visibility": "operator", "status": "shipped"},
                # excluded: not shipped
                {"asset_id": "plan", "path": "assets/planned.svg", "visibility": "public", "status": "planned"},
                # excluded: provenance classifies it commercial-only, not publishable
                {"asset_id": "comm", "path": "assets/commercial.svg", "visibility": "public", "status": "shipped"},
            ],
        )
        _set_provenance(
            root,
            artifacts=[
                {"artifact_id": "media", "path": "assets/pub.svg", "classification": "open"},
                {"artifact_id": "commercial", "path": "assets/commercial.svg", "classification": "commercial-only"},
                {"artifact_id": "docs", "path": "docs/", "classification": "commercial-only"},
            ],
        )
        doc, _diags = self._build(self._source(root))
        entry = doc.entries[0]
        refs = {m["reference"] for m in entry["media"]}
        # Only the asset that satisfies EVERY authority is surfaced.
        self.assertEqual(refs, {"assets/pub.svg"})
        rendered = catalog.render_json(doc)
        self.assertNotIn("operator/secret.md", rendered)
        self.assertNotIn("assets/commercial.svg", rendered)
        # The non-distributable exclusion is diagnosed, not silent.
        codes = {note["code"] for note in entry["completeness"]}
        self.assertIn("catalog.media.not-distributable", codes)


class ValidationSeamTests(CatalogFixture):
    """Catalog-critical relational joins live in the shared static authority."""

    def test_shipped_asset_missing_from_inventory_fails_validate_pack(self) -> None:
        root = _valid_pack(self.tmp, "missing-asset-pack")
        _set_compat(
            root,
            assets=[
                {"asset_id": "ghost", "path": "assets/ghost.svg", "visibility": "public", "status": "shipped"}
            ],
        )
        result = validate_pack(str(root))
        self.assertFalse(result.ok)
        self.assertIn("compatibility.asset.missing", {d.code for d in result.diagnostics})
        # A blocking pack produces no catalog entry.
        doc, diags = self._build(self._source(root))
        self.assertEqual(len(doc.entries), 0)
        self.assertTrue(any(d.blocking for d in diags))

    def test_publication_identity_mismatch_fails_validate_pack(self) -> None:
        root = _valid_pack(self.tmp, "pub-identity-pack")
        _set_manifest(root, publication_supply="publication-supply.yaml")
        _dump(
            root / "publication-supply.yaml",
            {"release": {"pack": {"name": "someone-else", "version": "9.9.9"}}},
        )
        result = validate_pack(str(root))
        self.assertFalse(result.ok)
        self.assertIn("publication.identity-mismatch", {d.code for d in result.diagnostics})

    def test_matching_publication_identity_does_not_add_a_diagnostic(self) -> None:
        root = _valid_pack(self.tmp, "pub-ok-pack")
        _set_manifest(root, publication_supply="publication-supply.yaml")
        manifest = _load(root / "pack.yaml")
        _dump(
            root / "publication-supply.yaml",
            {"release": {"pack": {"name": manifest["name"], "version": manifest["version"]}}},
        )
        self.assertNotIn(
            "publication.identity-mismatch",
            {d.code for d in validate_pack(str(root)).diagnostics},
        )


class DeterminismTests(CatalogFixture):
    def test_same_inputs_produce_byte_identical_json(self) -> None:
        root = _ai_research_pack(self.tmp)
        first, _ = self._build(self._source(root))
        second, _ = self._build(self._source(root))
        self.assertEqual(catalog.render_json(first), catalog.render_json(second))

    def test_aggregation_is_independent_of_source_order(self) -> None:
        a = self._source(_security_pack(self.tmp), sid="repo-a")
        b = self._source(_simulator_pack(self.tmp), sid="repo-b")
        forward, _ = self._build(a, b)
        reverse, _ = self._build(b, a)
        self.assertEqual(catalog.render_json(forward), catalog.render_json(reverse))

    def test_entries_sorted_by_composite_key(self) -> None:
        b = self._source(_simulator_pack(self.tmp), sid="repo-b")
        a = self._source(_security_pack(self.tmp), sid="repo-a")
        doc, _ = self._build(b, a)
        ids = [e["source"]["id"] for e in doc.entries]
        self.assertEqual(ids, ["repo-a", "repo-b"])

    def test_freshness_policy_is_echoed(self) -> None:
        root = _security_pack(self.tmp)
        doc, _ = catalog.build_catalog(
            [self._source(root)], as_of="2026-07-30", rehearsal_max_age_days=30
        )
        mapping = json.loads(catalog.render_json(doc))
        self.assertEqual(mapping["freshness"]["rehearsal_max_age_days"], 30)


class AggregationFailClosedTests(CatalogFixture):
    def test_duplicate_composite_identity_fails_closed(self) -> None:
        root = _security_pack(self.tmp)
        # Two sources with the same id AND same pack identity collide.
        s1 = self._source(root, sid="dup")
        s2 = self._source(root, sid="dup")
        doc, diags = self._build(s1, s2)
        self.assertEqual(len(doc.entries), 1)
        blocking = [d for d in diags if d.blocking]
        self.assertTrue(any(d.code == "catalog.identity.duplicate" for d in blocking))

    def test_unsafe_source_id_fails_closed(self) -> None:
        root = _security_pack(self.tmp)
        doc, diags = self._build(self._source(root, sid="../evil"))
        self.assertEqual(len(doc.entries), 0)
        self.assertTrue(any(d.code == "catalog.source.unsafe" and d.blocking for d in diags))

    def test_invalid_pack_is_blocking_and_produces_no_entry(self) -> None:
        root = _valid_pack(self.tmp, "broken-pack")
        # Break the provenance name so the pack fails static validation.
        ledger = _load(root / "docs" / "provenance-ledger.yaml")
        ledger["pack"]["name"] = "someone-else"
        _dump(root / "docs" / "provenance-ledger.yaml", ledger)
        self.assertFalse(validate_pack(str(root)).ok)
        doc, diags = self._build(self._source(root))
        self.assertEqual(len(doc.entries), 0)
        self.assertTrue(any(d.blocking and d.code.startswith("catalog.pack.invalid") for d in diags))

    def test_cli_blocking_writes_stderr_and_no_stdout(self) -> None:
        root = _valid_pack(self.tmp, "broken2")
        ledger = _load(root / "docs" / "provenance-ledger.yaml")
        ledger["pack"]["name"] = "mismatch"
        _dump(root / "docs" / "provenance-ledger.yaml", ledger)
        code, out, err = _run(str(root))
        self.assertEqual(code, catalog.EXIT_BLOCKING)
        self.assertEqual(out, "")
        self.assertIn("catalog.pack.invalid", err)


class SafeInputTests(CatalogFixture):
    def test_unsafe_pack_member_is_blocking_not_a_crash(self) -> None:
        root = _valid_pack(self.tmp, "symlink-pack")
        # A symlink escaping the pack is rejected by the safe filesystem layer.
        os.symlink("/etc/passwd", root / "assets" / "escape.txt")
        doc, diags = self._build(self._source(root))
        self.assertEqual(len(doc.entries), 0)
        self.assertTrue(any(d.blocking for d in diags))

    def test_authored_terminal_control_is_escaped_in_preview(self) -> None:
        root = _valid_pack(self.tmp, "escape-title")
        _set_manifest(root, title="evil\r\x1b[2Ktitle")
        code, out, _ = _run(str(root), "--preview")
        self.assertEqual(code, catalog.EXIT_OK)
        self.assertNotIn("\x1b", out)
        self.assertIn("\\x1b", out)


class UsageContractTests(CatalogFixture):
    def test_no_arguments_is_usage_error(self) -> None:
        code, _out, _err = _run()
        self.assertEqual(code, catalog.EXIT_USAGE)

    def test_both_pack_and_sources_is_usage_error(self) -> None:
        root = _security_pack(self.tmp)
        manifest = self.tmp / "sources.yaml"
        _dump(manifest, [{"id": "x", "revision": "r", "root": str(root)}])
        code, _out, _err = _run(str(root), "--sources", str(manifest))
        self.assertEqual(code, catalog.EXIT_USAGE)

    def test_missing_directory_is_usage_error(self) -> None:
        code, _out, _err = _run(str(self.tmp / "nope"))
        self.assertEqual(code, catalog.EXIT_USAGE)

    def test_bad_rehearsal_age_is_usage_error(self) -> None:
        root = _security_pack(self.tmp)
        code, _out, _err = _run(str(root), "--rehearsal-max-age-days", "0")
        self.assertEqual(code, catalog.EXIT_USAGE)


class SourcesManifestTests(CatalogFixture):
    def _chdir_tmp(self) -> None:
        # The sources manifest must live within the working directory (S8707
        # containment), so run these from the temp workspace.
        old = os.getcwd()
        os.chdir(self.tmp)
        self.addCleanup(os.chdir, old)

    def test_sources_manifest_aggregates_many_packs(self) -> None:
        a = _security_pack(self.tmp)
        b = _simulator_pack(self.tmp)
        self._chdir_tmp()
        _dump(
            self.tmp / "sources.yaml",
            [
                {"id": "repo-a", "revision": "1", "root": str(a)},
                {"id": "repo-b", "revision": "2", "root": str(b)},
            ],
        )
        code, out, err = _run("--sources", "sources.yaml", "--as-of", "2026-07-30")
        self.assertEqual(code, catalog.EXIT_OK, err)
        document = json.loads(out)
        names = {e["name"] for e in document["entries"]}
        self.assertEqual(names, {"security-pack", "simulator-backed-pack"})

    def test_manifest_outside_working_dir_is_usage_error(self) -> None:
        a = _security_pack(self.tmp)
        outside = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, outside, ignore_errors=True)
        self._chdir_tmp()
        _dump(outside / "sources.yaml", [{"id": "x", "revision": "1", "root": str(a)}])
        code, _out, _err = _run("--sources", str(outside / "sources.yaml"))
        self.assertEqual(code, catalog.EXIT_USAGE)

    def test_malformed_sources_manifest_is_usage_error(self) -> None:
        self._chdir_tmp()
        (self.tmp / "bad.yaml").write_text("just a string\n", encoding="utf-8")
        code, _out, _err = _run("--sources", "bad.yaml")
        self.assertEqual(code, catalog.EXIT_USAGE)


class FixtureCoverageTests(CatalogFixture):
    def test_every_required_scenario_family_catalogs_cleanly(self) -> None:
        # AC5: fixture coverage across AI research, security, resilience/DR,
        # product testing, and simulator-backed packs. Each fixture has a
        # distinct pack name, so they coexist under one temp parent.
        for build in _FIXTURES:
            with self.subTest(fixture=build.__name__):
                root = build(self.tmp)
                doc, diags = self._build(self._source(root))
                self.assertEqual(len(doc.entries), 1)
                self.assertEqual(catalog.validate_document(doc), [])
                self.assertFalse([d for d in diags if d.blocking])

    def test_hub_can_build_from_the_projection_alone(self) -> None:
        # AC6: a downstream client reads every fact it needs from the published
        # entry without reparsing pack YAML or RAES SDL.
        doc, _ = self._build(self._source(_security_pack(self.tmp), sid="cat-a"))
        document = json.loads(catalog.render_json(doc))
        entry = document["entries"][0]
        for field in (
            "name", "title", "version", "maturity", "purpose", "audiences",
            "runtimes", "launch_modes", "safety", "provenance", "trust",
            "last_rehearsal", "media", "license",
        ):
            self.assertIn(field, entry)


if __name__ == "__main__":
    unittest.main()
