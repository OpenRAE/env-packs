"""Tests for the environment-pack publication profile (issue #141, ADR 0028).

The publication profile turns one validated pack release into distributable,
verifiable release views. It *consumes* the RAES artifact-requirement contract
shipped in the exactly pinned ``raes`` release and defines no RAES semantics of
its own: author posture, mechanism vocabulary, acquisition, timing, and trust
references all remain RAES-owned.

These tests lock the authority invariants that make publication a *claim* about
release assets rather than an override of RAES author intent:

  * an exact required artifact stays exact and is never relabeled a substitute;
  * a constrained requirement may advertise several conforming candidates
    without that set becoming exhaustive;
  * an open requirement may lean on a declared backend capability without a
    fabricated image or recipe;
  * a requirement may be published with nothing at all;
  * immutable release identity is separate from mutable channel/availability
    metadata, so distribution can evolve without re-identifying a release.
"""

from __future__ import annotations

import unittest

from raes.artifact_requirements import (
    ArtifactCandidate,
    ArtifactIdentity,
    ArtifactMechanismProfile,
    ArtifactRequirement,
    ArtifactSatisfactionRoute,
)

from raes_env_packs import publication

_MEDIA = "application/vnd.oci.image.manifest.v1+json"


def _digest(seed: str) -> str:
    return "sha256:" + (seed * 64)[:64]


def _mechanism(name: str = "exact-artifact") -> ArtifactMechanismProfile:
    return ArtifactMechanismProfile(
        mechanism=name,
        profile="raes-artifact-satisfaction",
        version="1",
        digest=_digest("c"),
    )


def _route(name: str = "exact-artifact") -> ArtifactSatisfactionRoute:
    return ArtifactSatisfactionRoute(
        mechanism=_mechanism(name), acquisition="pull", timing="realization"
    )


def _identity(artifact_id: str, seed: str, version: str = "1.0.0") -> ArtifactIdentity:
    return ArtifactIdentity(
        artifact_id=artifact_id,
        version=version,
        digest=_digest(seed),
        media_type=_MEDIA,
    )


def exact_requirement() -> ArtifactRequirement:
    """An exact requirement naming exactly one immutable artifact."""
    return ArtifactRequirement(
        requirement_id="web-image",
        explicitness="exact",
        exact_artifact=_identity("web-image", "a"),
        permitted_routes=[_route()],
    )


def constrained_requirement() -> ArtifactRequirement:
    """A constrained requirement admitting two immutable candidates."""
    return ArtifactRequirement(
        requirement_id="db-image",
        explicitness="constrained",
        candidates=[
            ArtifactCandidate(candidate_id="pg-15", artifact=_identity("db-image", "b")),
            ArtifactCandidate(candidate_id="pg-16", artifact=_identity("db-image", "d")),
        ],
        permitted_routes=[_route("published-candidate")],
    )


def open_requirement() -> ArtifactRequirement:
    """An open requirement delegating output selection to the backend."""
    return ArtifactRequirement(
        requirement_id="cache-image",
        explicitness="open",
        permitted_routes=[_route("backend-owned-artifact")],
    )


def _publication(**overrides: object) -> dict[str, object]:
    row: dict[str, object] = {
        "publication_id": "pub-1",
        "requirement_id": "web-image",
        "requirement_address": "provision.nodes.web-image.source-artifact",
        "artifact": {
            "artifact_id": "web-image",
            "version": "1.0.0",
            "digest": _digest("a"),
            "media_type": _MEDIA,
        },
        "mechanism": {
            "mechanism": "exact-artifact",
            "profile": "raes-artifact-satisfaction",
            "version": "1",
            "digest": _digest("c"),
        },
    }
    row.update(overrides)
    return row


def _profile(publications: list[dict[str, object]], **overrides: object) -> dict[str, object]:
    profile: dict[str, object] = {
        "schema_version": publication.PUBLICATION_SCHEMA_VERSION,
        "summary": {
            "contract": {
                "version": "5",
                "source": "contract/pack-layout.md",
                "digest": _digest("2"),
            },
            "supported_profiles": [],
            "runtime_profiles": [],
            "provenance_summary": {},
        },
        "release": {
            "pack": {"name": "synthpack", "version": "0.1.0"},
            "semantic_parent": {"parent_ref": "synthpack", "digest": _digest("e")},
            "source_set": {"manifest_id": "synthpack-associated-artifacts",
                           "set_digest": _digest("f")},
            "views": [
                {
                    "view": "participant",
                    "set": {"manifest_id": "synthpack-participant-associated-artifacts",
                            "set_digest": _digest("1")},
                    "completeness": "non-exhaustive",
                    "publications": publications,
                    "capability_claims": [],
                }
            ],
        },
        "distribution": {"availability": [], "channels": []},
    }
    profile.update(overrides)
    return profile


def _index(requirements: list[ArtifactRequirement]) -> dict[str, ArtifactRequirement]:
    """Index test requirements by compiled address, as the real collector does."""
    return {
        publication.compiled_requirement_address(("nodes", req.requirement_id)): req
        for req in requirements
    }


def _codes(profile: dict[str, object], requirements: list[ArtifactRequirement]) -> set[str]:
    return {
        v.code
        for v in publication.publication_violations(profile, requirements=_index(requirements))
    }


class ExactArtifactAuthorityTests(unittest.TestCase):
    """An exact artifact keeps its authority through publication."""

    def test_exact_artifact_published_verbatim_is_accepted(self) -> None:
        codes = _codes(_profile([_publication()]), [exact_requirement()])
        self.assertEqual(codes, set())

    def test_exact_requirement_relabeled_as_candidate_is_rejected(self) -> None:
        """Publishing an exact artifact under a candidate selector is substitution."""
        row = _publication(candidate_id="pg-15")
        codes = _codes(_profile([row]), [exact_requirement()])
        self.assertIn("publication.exact-substitution", codes)

    def test_exact_requirement_published_with_other_digest_is_rejected(self) -> None:
        """A different digest is a substitute, not the authored exact artifact."""
        row = _publication(artifact={
            "artifact_id": "web-image",
            "version": "1.0.0",
            "digest": _digest("9"),
            "media_type": _MEDIA,
        })
        codes = _codes(_profile([row]), [exact_requirement()])
        self.assertIn("publication.exact-substitution", codes)


class ConstrainedRequirementTests(unittest.TestCase):
    """A constrained requirement advertises declared candidates, never a closed set."""

    def _candidate_row(self, **overrides: object) -> dict[str, object]:
        row = _publication(
            publication_id="pub-db",
            requirement_id="db-image",
            requirement_address="provision.nodes.db-image.source-artifact",
            candidate_id="pg-15",
            artifact={
                "artifact_id": "db-image",
                "version": "1.0.0",
                "digest": _digest("b"),
                "media_type": _MEDIA,
            },
            mechanism={
                "mechanism": "published-candidate",
                "profile": "raes-artifact-satisfaction",
                "version": "1",
                "digest": _digest("c"),
            },
        )
        row.update(overrides)
        return row

    def test_multiple_declared_candidates_are_accepted(self) -> None:
        """Advertising several conforming candidates is legitimate, not exhaustive."""
        second = self._candidate_row(
            publication_id="pub-db-2",
            candidate_id="pg-16",
            artifact={
                "artifact_id": "db-image",
                "version": "1.0.0",
                "digest": _digest("d"),
                "media_type": _MEDIA,
            },
        )
        profile = _profile([self._candidate_row(), second])
        self.assertEqual(_codes(profile, [constrained_requirement()]), set())

    def test_undeclared_candidate_is_rejected(self) -> None:
        row = self._candidate_row(candidate_id="pg-99")
        codes = _codes(_profile([row]), [constrained_requirement()])
        self.assertIn("publication.selector-unknown", codes)

    def test_candidate_published_with_other_bytes_is_rejected(self) -> None:
        """A declared candidate id must carry the declared immutable artifact."""
        row = self._candidate_row(artifact={
            "artifact_id": "db-image",
            "version": "1.0.0",
            "digest": _digest("9"),
            "media_type": _MEDIA,
        })
        codes = _codes(_profile([row]), [constrained_requirement()])
        self.assertIn("publication.artifact-mismatch", codes)

    def test_constrained_row_without_a_selector_is_rejected(self) -> None:
        """A constrained requirement has no exact artifact to supply implicitly."""
        row = self._candidate_row()
        row.pop("candidate_id")
        codes = _codes(_profile([row]), [constrained_requirement()])
        self.assertIn("publication.selector-missing", codes)


class OpenRequirementTests(unittest.TestCase):
    """An open requirement delegates selection; it never gets a fabricated asset."""

    def test_open_requirement_with_no_publications_is_accepted(self) -> None:
        """Publishing nothing is valid and implies nothing about satisfiability."""
        self.assertEqual(_codes(_profile([]), [open_requirement()]), set())

    def test_open_requirement_publishing_an_artifact_is_rejected(self) -> None:
        row = _publication(
            publication_id="pub-cache",
            requirement_id="cache-image",
            requirement_address="provision.nodes.cache-image.source-artifact",
            artifact={
                "artifact_id": "cache-image",
                "version": "1.0.0",
                "digest": _digest("7"),
                "media_type": _MEDIA,
            },
        )
        codes = _codes(_profile([row]), [open_requirement()])
        self.assertIn("publication.open-overreach", codes)


class UnknownRequirementTests(unittest.TestCase):
    def test_row_for_an_unauthored_requirement_is_rejected(self) -> None:
        row = _publication(
            requirement_id="not-authored",
            requirement_address="provision.nodes.not-authored.source-artifact")
        codes = _codes(_profile([row]), [exact_requirement()])
        self.assertIn("publication.requirement-unknown", codes)

    def test_two_selectors_on_one_row_are_rejected(self) -> None:
        row = _publication(
            requirement_id="db-image",
            requirement_address="provision.nodes.db-image.source-artifact",
            candidate_id="pg-15", locked_input_id="base",
        )
        codes = _codes(_profile([row]), [constrained_requirement()])
        self.assertIn("publication.selector-ambiguous", codes)


class MechanismAuthorityTests(unittest.TestCase):
    """Mechanism vocabulary stays RAES-governed; this package declares none."""

    def test_ungoverned_mechanism_name_is_rejected(self) -> None:
        """The upstream model is the authority for what a mechanism may be called."""
        row = _publication(mechanism={
            "mechanism": "bake-it-yourself",
            "profile": "raes-artifact-satisfaction",
            "version": "1",
            "digest": _digest("c"),
        })
        codes = _codes(_profile([row]), [exact_requirement()])
        self.assertIn("publication.mechanism-invalid", codes)

    def test_malformed_artifact_digest_is_rejected(self) -> None:
        row = _publication(artifact={
            "artifact_id": "web-image",
            "version": "1.0.0",
            "digest": "not-a-digest",
            "media_type": _MEDIA,
        })
        codes = _codes(_profile([row]), [exact_requirement()])
        self.assertIn("publication.artifact-invalid", codes)

    def test_mechanism_outside_permitted_routes_is_rejected(self) -> None:
        """A governed mechanism the author never permitted is still not permitted."""
        row = _publication(mechanism={
            "mechanism": "dynamic-composition",
            "profile": "raes-artifact-satisfaction",
            "version": "1",
            "digest": _digest("c"),
        })
        codes = _codes(_profile([row]), [exact_requirement()])
        self.assertIn("publication.mechanism-unpermitted", codes)


class CapabilityClaimTests(unittest.TestCase):
    """A backend-profile name alone is not evidence of mechanism support."""

    def _profile_with_claim(self, claim: dict[str, object]) -> dict[str, object]:
        profile = _profile([])
        profile["release"]["views"][0]["capability_claims"] = [claim]
        return profile

    def test_bare_backend_profile_name_is_not_satisfaction_evidence(self) -> None:
        claim = {
            "requirement_id": "cache-image",
            "requirement_address": "provision.nodes.cache-image.source-artifact",
            "backend_profile": {"profile_id": "provisioning-only", "version": "1"},
        }
        codes = _codes(self._profile_with_claim(claim), [open_requirement()])
        self.assertIn("publication.capability-unproven", codes)

    def test_concrete_validated_mechanism_capability_is_accepted(self) -> None:
        claim = {
            "requirement_id": "cache-image",
            "requirement_address": "provision.nodes.cache-image.source-artifact",
            "backend_profile": {"profile_id": "provisioning-only", "version": "1"},
            "mechanism_capability": {
                "mechanism": {
                    "mechanism": "backend-owned-artifact",
                    "profile": "raes-artifact-satisfaction",
                    "version": "1",
                    "digest": _digest("c"),
                },
                "supported_requirement_kinds": ["source-artifact"],
                "supported_routes": [{"acquisition": "pull", "timing": "realization"}],
            },
        }
        codes = _codes(self._profile_with_claim(claim), [open_requirement()])
        self.assertEqual(codes, set())

    def test_capability_claim_for_an_unauthored_requirement_is_rejected(self) -> None:
        claim = {
            "requirement_id": "not-authored",
            "requirement_address": "provision.nodes.not-authored.source-artifact",
            "backend_profile": {"profile_id": "provisioning-only", "version": "1"},
            "mechanism_capability": {
                "mechanism": {
                    "mechanism": "backend-owned-artifact",
                    "profile": "raes-artifact-satisfaction",
                    "version": "1",
                    "digest": _digest("c"),
                },
                "supported_requirement_kinds": ["source-artifact"],
                "supported_routes": [{"acquisition": "pull", "timing": "realization"}],
            },
        }
        codes = _codes(self._profile_with_claim(claim), [open_requirement()])
        self.assertIn("publication.requirement-unknown", codes)


class ReleaseIdentityTests(unittest.TestCase):
    """Immutable release identity is separate from mutable distribution facts."""

    def test_identity_is_the_bound_tuple_not_a_new_digest(self) -> None:
        """ADR 0028: the tuple is represented directly, not re-canonicalized."""
        identity = publication.release_identity(_profile([]))
        self.assertEqual(identity["pack"], {"name": "synthpack", "version": "0.1.0"})
        self.assertEqual(identity["semantic_parent"]["digest"], _digest("e"))
        self.assertEqual(identity["source_set"]["set_digest"], _digest("f"))
        self.assertEqual(identity["views"]["participant"]["set_digest"], _digest("1"))

    def test_changing_availability_does_not_change_release_identity(self) -> None:
        """Provider/location records evolve without re-identifying the release."""
        before = publication.release_identity(_profile([]))
        moved = _profile([])
        moved["distribution"]["availability"] = [
            {"provider": "example-registry", "location": "https://example.test/packs/synthpack"}
        ]
        self.assertEqual(publication.release_identity(moved), before)

    def test_changing_channels_does_not_change_release_identity(self) -> None:
        before = publication.release_identity(_profile([]))
        moved = _profile([])
        moved["distribution"]["channels"] = [
            {"channel": "stable", "release_identity": before}
        ]
        self.assertEqual(publication.release_identity(moved), before)

    def test_changing_a_view_set_digest_does_change_release_identity(self) -> None:
        """A different view byte-set is a different release, not a re-publish."""
        before = publication.release_identity(_profile([]))
        changed = _profile([])
        changed["release"]["views"][0]["set"]["set_digest"] = _digest("8")
        self.assertNotEqual(publication.release_identity(changed), before)


class ChannelResolutionTests(unittest.TestCase):
    """Mutable channels resolve to the complete immutable release identity."""

    def test_channel_resolving_to_this_release_is_accepted(self) -> None:
        profile = _profile([])
        profile["distribution"]["channels"] = [
            {"channel": "stable", "release_identity": publication.release_identity(profile)}
        ]
        self.assertEqual(_codes(profile, [exact_requirement()]), set())

    def test_channel_resolving_to_another_release_is_rejected(self) -> None:
        profile = _profile([])
        other = publication.release_identity(_profile([]))
        other["pack"] = {"name": "synthpack", "version": "9.9.9"}
        profile["distribution"]["channels"] = [
            {"channel": "stable", "release_identity": other}
        ]
        codes = _codes(profile, [exact_requirement()])
        self.assertIn("publication.channel-unresolved", codes)


class SecretContentTests(unittest.TestCase):
    """Credentials and entitlement are never pack or publication content."""

    def test_credential_userinfo_in_an_availability_uri_is_rejected(self) -> None:
        profile = _profile([])
        profile["distribution"]["availability"] = [
            {"provider": "example-registry",
             "location": "https://user:secret@example.test/packs/synthpack"}
        ]
        codes = _codes(profile, [exact_requirement()])
        self.assertIn("publication.availability-secret", codes)

    def test_secret_bearing_query_parameter_is_rejected(self) -> None:
        profile = _profile([])
        profile["distribution"]["availability"] = [
            {"provider": "example-registry",
             "location": "https://example.test/packs/synthpack?signature=abc123"}
        ]
        codes = _codes(profile, [exact_requirement()])
        self.assertIn("publication.availability-secret", codes)

    def test_plain_public_location_is_accepted(self) -> None:
        profile = _profile([])
        profile["distribution"]["availability"] = [
            {"provider": "example-registry",
             "location": "https://example.test/packs/synthpack"}
        ]
        self.assertEqual(_codes(profile, [exact_requirement()]), set())

    def test_mutable_distribution_key_inside_release_identity_is_rejected(self) -> None:
        """Availability must not migrate into the immutable identity block."""
        profile = _profile([])
        profile["release"]["availability"] = [{"provider": "example-registry"}]
        codes = _codes(profile, [exact_requirement()])
        self.assertIn("publication.identity-mutable-field", codes)

    def test_diagnostics_never_echo_the_offending_location(self) -> None:
        """Bounded, body-free diagnostics: stable code plus field path only."""
        profile = _profile([])
        profile["distribution"]["availability"] = [
            {"provider": "example-registry",
             "location": "https://user:hunter2@example.test/x?token=deadbeef"}
        ]
        for violation in publication.publication_violations(
                profile, requirements=_index([exact_requirement()])):
            self.assertNotIn("hunter2", violation.code + violation.path)
            self.assertNotIn("deadbeef", violation.code + violation.path)


_REQUIREMENT_SDL = """
name: example-pack
nodes:
  target:
    type: vm
    source:
      name: web-image
      version: 1.0.0
      artifact_requirement:
        requirement_id: web-image
        explicitness: exact
        exact_artifact:
          artifact_id: web-image
          version: 1.0.0
          digest: "{digest}"
          media_type: {media}
        permitted_routes:
          - mechanism:
              mechanism: exact-artifact
              profile: raes-artifact-satisfaction
              version: "1"
              digest: "{mech}"
            acquisition: pull
            timing: realization
"""


class AuthoredRequirementCollectionTests(unittest.TestCase):
    """Authored requirements come from the parsed scenario, never from the profile."""

    def _scenario(self):
        from raes import parse_sdl

        return parse_sdl(
            _REQUIREMENT_SDL.format(
                digest=_digest("a"), media=_MEDIA, mech=_digest("c")
            ),
            migration_policy="accept",
        )

    def test_requirements_are_recovered_from_a_parsed_scenario(self) -> None:
        found = publication.authored_artifact_requirements([self._scenario()])
        address = publication.compiled_requirement_address(("nodes", "target", "source"))
        self.assertIn(address, found)
        self.assertEqual(found[address].explicitness.value, "exact")
        self.assertEqual(found[address].exact_artifact.digest, _digest("a"))

    def test_scenario_without_artifact_requirements_yields_nothing(self) -> None:
        from raes import parse_sdl

        scenario = parse_sdl(
            "name: example-pack\nnodes:\n  target:\n    type: vm\n",
            migration_policy="accept",
        )
        self.assertEqual(publication.authored_artifact_requirements([scenario]), {})

    def test_collection_walks_every_source_owner_not_just_nodes(self) -> None:
        """The owner set is discovered structurally so it cannot go stale.

        RAES lets a Source hang off nodes, content, features, conditions,
        injects, and events. Hard-coding that list would silently miss a
        requirement the author declared elsewhere.
        """
        from raes import Scenario

        owners = {
            field
            for field in Scenario.model_fields
            if publication._field_may_hold_source(Scenario, field)
        }
        self.assertLessEqual(
            {"nodes", "content", "features", "conditions", "injects", "events"}, owners
        )

    def test_publication_against_authored_requirement_round_trips(self) -> None:
        """End to end: profile rows validate against SDL-authored authority."""
        found = publication.authored_artifact_requirements([self._scenario()])
        address = publication.compiled_requirement_address(("nodes", "target", "source"))
        row = _publication(requirement_address=address)
        violations = publication.publication_violations(
            _profile([row]), requirements=found
        )
        self.assertEqual(violations, [])


class SchemaBackedValidationTests(unittest.TestCase):
    """One helper checks shape and authority; the emitter calls it."""

    def _validate(self, profile: dict[str, object]) -> set[str]:
        return {
            v.code
            for v in publication.validate_publication_document(
                profile, requirements=_index([exact_requirement()]))
        }

    def test_wellformed_document_passes(self) -> None:
        self.assertEqual(self._validate(_profile([_publication()])), set())

    def test_unknown_top_level_key_is_rejected(self) -> None:
        profile = _profile([])
        profile["catalog"] = {"blessed": True}
        self.assertIn("publication.schema.unknown", self._validate(profile))

    def test_wrong_schema_version_is_rejected(self) -> None:
        profile = _profile([])
        profile["schema_version"] = "environment-pack-publication/v99"
        self.assertIn("publication.schema.const", self._validate(profile))

    def test_missing_required_block_is_rejected(self) -> None:
        profile = _profile([])
        profile.pop("distribution")
        self.assertIn("publication.schema.required", self._validate(profile))

    def test_unknown_release_view_is_rejected(self) -> None:
        profile = _profile([])
        profile["release"]["views"][0]["view"] = "catalog-only"
        self.assertIn("publication.schema.enum", self._validate(profile))

    def test_view_cannot_declare_an_exhaustive_alternative_set(self) -> None:
        """`completeness` is a const, so a closed-set claim is unrepresentable."""
        profile = _profile([])
        profile["release"]["views"][0]["completeness"] = "exhaustive"
        self.assertIn("publication.schema.const", self._validate(profile))

    def test_restricted_is_the_publication_view_for_oracle_only(self) -> None:
        """`oracle_only` maps to `restricted` and gains no oracle semantics."""
        profile = _profile([])
        profile["release"]["views"][0]["view"] = "restricted"
        self.assertEqual(self._validate(profile), set())

    def test_authority_violations_are_reported_alongside_shape(self) -> None:
        profile = _profile([_publication(candidate_id="pg-15")])
        self.assertIn("publication.exact-substitution", self._validate(profile))


class SchemaAlignmentTests(unittest.TestCase):
    """The profile consumes RAES vocabulary; it declares none of its own."""

    def setUp(self) -> None:
        import yaml

        self.schema = yaml.safe_load(
            publication.publication_schema_path().read_text(encoding="utf-8")
        )

    def _declared_vocabulary(self, node: object) -> set[str]:
        found: set[str] = set()
        if isinstance(node, dict):
            props = node.get("properties")
            if isinstance(props, dict):
                for key, child in props.items():
                    found.add(str(key))
                    found |= self._declared_vocabulary(child)
            for key in ("enum", "const"):
                value = node.get(key)
                for item in value if isinstance(value, list) else [value]:
                    if isinstance(item, str):
                        found.add(item)
            for key, child in node.items():
                if key not in ("properties", "enum", "const"):
                    found |= self._declared_vocabulary(child)
        elif isinstance(node, list):
            for item in node:
                found |= self._declared_vocabulary(item)
        return found

    def test_schema_does_not_enumerate_raes_mechanism_vocabulary(self) -> None:
        """Mechanism names stay upstream so they cannot drift out of step."""
        raes_mechanisms = {
            "exact-artifact",
            "backend-owned-artifact",
            "published-candidate",
            "dynamic-composition",
            "materialization-specification",
        }
        declared = self._declared_vocabulary(self.schema)
        self.assertEqual(declared & raes_mechanisms, set())

    def test_schema_does_not_redeclare_raes_acquisition_or_timing(self) -> None:
        raes_axes = {
            "pull", "copy", "import", "local-lookup", "none",
            "publication", "pack-ingestion", "backend-preparation", "realization",
        }
        self.assertEqual(self._declared_vocabulary(self.schema) & raes_axes, set())

    def test_schema_cites_the_governing_adr(self) -> None:
        text = publication.publication_schema_path().read_text(encoding="utf-8").lower()
        self.assertIn("adr 0028", text)


class CompiledAddressAuthorityTests(unittest.TestCase):
    """Authority is keyed by compiled address, not by an unscoped local id.

    RAES scopes candidate/constraint/locked-input ids to one requirement, so two
    owners may legitimately reuse a local id. Resolving by id alone would bind a
    claim to the wrong authored requirement and drop every duplicate but one.
    """

    def test_syntactically_invalid_address_is_rejected(self) -> None:
        row = _publication(requirement_address="not a valid address!")
        codes = _codes(_profile([row]), [exact_requirement()])
        self.assertIn("publication.address-invalid", codes)

    def test_missing_address_is_rejected(self) -> None:
        row = _publication()
        row.pop("requirement_address")
        codes = _codes(_profile([row]), [exact_requirement()])
        self.assertIn("publication.address-invalid", codes)

    def test_address_of_another_requirement_is_rejected(self) -> None:
        """Relabelling an artifact with a foreign compiled address must not pass."""
        row = _publication(
            requirement_address="provision.nodes.db-image.source-artifact")
        codes = _codes(_profile([row]), [exact_requirement(), constrained_requirement()])
        self.assertIn("publication.requirement-id-mismatch", codes)

    def test_duplicate_local_ids_at_distinct_addresses_both_survive(self) -> None:
        """Two owners sharing a local id must both be indexed, not collapsed."""
        from raes import parse_sdl

        one_node = _REQUIREMENT_SDL.format(
            digest=_digest("a"), media=_MEDIA, mech=_digest("c"))
        # A second node declaring the *same* local requirement id.
        node_block = one_node.split("nodes:\n", 1)[1]
        scenario = parse_sdl(
            one_node + node_block.replace("  target:", "  other:", 1),
            migration_policy="accept",
        )

        found = publication.authored_artifact_requirements([scenario])
        self.assertEqual(len(found), 2, "a duplicate local id overwrote another owner")
        for owner in ("target", "other"):
            address = publication.compiled_requirement_address(("nodes", owner, "source"))
            self.assertIn(address, found)
            self.assertEqual(found[address].requirement_id, "web-image")

    def test_same_address_in_two_scenarios_is_ambiguous_not_last_wins(self) -> None:
        """Two SDL documents can share an owner trail; resolving must not guess."""
        from raes import parse_sdl

        first = parse_sdl(
            _REQUIREMENT_SDL.format(
                digest=_digest("a"), media=_MEDIA, mech=_digest("c")
            ),
            migration_policy="accept",
        )
        second = parse_sdl(
            _REQUIREMENT_SDL.format(
                digest=_digest("b"), media=_MEDIA, mech=_digest("c")
            ),
            migration_policy="accept",
        )
        found = publication.authored_artifact_requirements([first, second])
        address = publication.compiled_requirement_address(("nodes", "target", "source"))
        self.assertIsNone(found[address], "an ambiguous address silently resolved")

        row = _publication(requirement_address=address)
        codes = {
            v.code
            for v in publication.publication_violations(
                _profile([row]), requirements=found)
        }
        self.assertIn("publication.address-ambiguous", codes)


class CapabilityApplicabilityTests(unittest.TestCase):
    """A structurally valid capability must also be the applicable one."""

    def _claim(self, **capability_overrides: object) -> dict[str, object]:
        capability = {
            "mechanism": {
                "mechanism": "backend-owned-artifact",
                "profile": "raes-artifact-satisfaction",
                "version": "1",
                "digest": _digest("c"),
            },
            "supported_requirement_kinds": ["source-artifact"],
            "supported_routes": [{"acquisition": "pull", "timing": "realization"}],
        }
        capability.update(capability_overrides)
        profile = _profile([])
        profile["release"]["views"][0]["capability_claims"] = [{
            "requirement_id": "cache-image",
            "requirement_address": "provision.nodes.cache-image.source-artifact",
            "backend_profile": {"profile_id": "provisioning-only", "version": "1"},
            "mechanism_capability": capability,
        }]
        return profile

    def test_applicable_capability_is_accepted(self) -> None:
        self.assertEqual(_codes(self._claim(), [open_requirement()]), set())

    def test_capability_for_an_unpermitted_mechanism_is_rejected(self) -> None:
        """A valid capability the author never permitted is not evidence."""
        profile = self._claim(mechanism={
            "mechanism": "dynamic-composition",
            "profile": "raes-artifact-satisfaction",
            "version": "1",
            "digest": _digest("c"),
        })
        self.assertIn("publication.capability-inapplicable",
                      _codes(profile, [open_requirement()]))

    def test_capability_not_supporting_the_requirement_kind_is_rejected(self) -> None:
        profile = self._claim(supported_requirement_kinds=["something-else"])
        self.assertIn("publication.capability-inapplicable",
                      _codes(profile, [open_requirement()]))

    def test_capability_without_a_matching_route_is_rejected(self) -> None:
        """Acquisition/timing must match a route the author actually permitted."""
        profile = self._claim(
            supported_routes=[{"acquisition": "copy", "timing": "publication"}])
        self.assertIn("publication.capability-inapplicable",
                      _codes(profile, [open_requirement()]))


class TrustedBackendProfileTests(unittest.TestCase):
    """A capability claim must name a real, trusted RAES backend profile.

    Otherwise a pack author who cannot modify a trusted profile could still name
    one and attach a self-constructed capability, and a consumer resolving by
    profile would treat an unsupported mechanism as authorized for that backend.
    """

    def _claim_with_profile(self, backend_profile: object) -> dict[str, object]:
        profile = _profile([])
        profile["release"]["views"][0]["capability_claims"] = [{
            "requirement_id": "cache-image",
            "requirement_address": "provision.nodes.cache-image.source-artifact",
            "backend_profile": backend_profile,
            "mechanism_capability": {
                "mechanism": {
                    "mechanism": "backend-owned-artifact",
                    "profile": "raes-artifact-satisfaction",
                    "version": "1",
                    "digest": _digest("c"),
                },
                "supported_requirement_kinds": ["source-artifact"],
                "supported_routes": [{"acquisition": "pull", "timing": "realization"}],
            },
        }]
        return profile

    def test_profile_resolving_upstream_is_accepted(self) -> None:
        profile = self._claim_with_profile(
            {"profile_id": "provisioning-only", "version": "1"})
        self.assertEqual(_codes(profile, [open_requirement()]), set())

    def test_invented_profile_name_is_rejected(self) -> None:
        profile = self._claim_with_profile(
            {"profile_id": "totally-made-up-profile", "version": "1"})
        self.assertIn("publication.backend-profile-untrusted",
                      _codes(profile, [open_requirement()]))

    def test_every_trusted_profile_declares_the_manifest_contract(self) -> None:
        """The binding rests on backend-manifest-v2 being the mechanism carrier."""
        import raes_contracts.contracts  # noqa: F401
        from raes_contracts.backend_profiles import load_backend_profile

        model = load_backend_profile("provisioning-only")
        self.assertIn("backend-manifest-v2", model.required_contracts)


class SemanticParentDigestTests(unittest.TestCase):
    """Release identity is the parent reference *and* digest (ADR 0028)."""

    def test_claim_without_a_parent_digest_is_rejected(self) -> None:
        """A parent id alone lets changed semantics keep the same identity."""
        profile = _profile([_publication()])
        profile["release"]["semantic_parent"] = {"parent_ref": "synthpack"}
        self.assertIn("publication.binding-missing",
                      _codes(profile, [exact_requirement()]))

    def test_claim_free_release_without_a_parent_digest_is_accepted(self) -> None:
        profile = _profile([])
        profile["release"]["semantic_parent"] = {"parent_ref": "synthpack"}
        self.assertEqual(_codes(profile, [exact_requirement()]), set())


class ClaimingViewMustBeBoundTests(unittest.TestCase):
    """A view that publishes something must expose a verifiable byte set."""

    def test_claim_in_a_view_without_a_set_is_rejected(self) -> None:
        profile = _profile([_publication()])
        profile["release"]["views"][0].pop("set")
        codes = _codes(profile, [exact_requirement()])
        self.assertIn("publication.view-set-missing", codes)

    def test_empty_view_without_a_set_is_accepted(self) -> None:
        profile = _profile([])
        profile["release"]["views"][0].pop("set")
        self.assertEqual(_codes(profile, [exact_requirement()]), set())


class AvailabilitySecretFilterTests(unittest.TestCase):
    """The locator filter fails closed: unknown query material is not published."""

    def _codes_for(self, location: str) -> set[str]:
        profile = _profile([])
        profile["distribution"]["availability"] = [
            {"provider": "example-registry", "location": location}]
        return _codes(profile, [exact_requirement()])

    def test_provider_specific_credential_parameters_are_rejected(self) -> None:
        """A denylist cannot keep up with per-provider signed-URL formats."""
        for location in (
            "https://example.test/p?access_token=abc",
            "https://example.test/p?api_key=abc",
            "https://example.test/p?x-goog-signature=abc",
            "https://example.test/p?X-Amz-Credential=abc",
            "https://example.test/p?unknown_future_secret=abc",
        ):
            with self.subTest(location=location):
                self.assertIn("publication.availability-secret",
                              self._codes_for(location))

    def test_fragment_is_rejected(self) -> None:
        self.assertIn("publication.availability-secret",
                      self._codes_for("https://example.test/p#token=abc"))

    def test_allowlisted_non_secret_query_is_accepted(self) -> None:
        self.assertEqual(self._codes_for("https://example.test/p?tag=v1"), set())


class ContentIdentityBindingTests(unittest.TestCase):
    """A verifiable claim needs a verifiable release; no claim needs no binding.

    ADR 0012 makes pack content identity opt-in, while ADR 0028 requires a
    validated RAES semantic parent and associated-artifact set before a release
    may be published. Both hold: a release that claims nothing needs no binding,
    and any publication or capability claim requires one.
    """

    def _unbound(self, publications: list[dict[str, object]]) -> dict[str, object]:
        profile = _profile(publications)
        profile["release"].pop("semantic_parent")
        profile["release"].pop("source_set")
        return profile

    def test_release_claiming_nothing_needs_no_binding(self) -> None:
        violations = publication.validate_publication_document(
            self._unbound([]), requirements=_index([exact_requirement()])
        )
        self.assertEqual(violations, [])

    def test_publication_claim_without_a_binding_is_rejected(self) -> None:
        codes = {
            v.code
            for v in publication.validate_publication_document(
                self._unbound([_publication()]),
                requirements=_index([exact_requirement()]),
            )
        }
        self.assertIn("publication.binding-missing", codes)

    def test_capability_claim_without_a_binding_is_rejected(self) -> None:
        profile = self._unbound([])
        profile["release"]["views"][0]["capability_claims"] = [{
            "requirement_id": "cache-image",
            "requirement_address": "provision.nodes.cache-image.source-artifact",
            "backend_profile": {"profile_id": "provisioning-only", "version": "1"},
            "mechanism_capability": {
                "mechanism": {
                    "mechanism": "backend-owned-artifact",
                    "profile": "raes-artifact-satisfaction",
                    "version": "1",
                    "digest": _digest("c"),
                },
                "supported_requirement_kinds": ["source-artifact"],
                "supported_routes": [{"acquisition": "pull", "timing": "realization"}],
            },
        }]
        codes = {
            v.code
            for v in publication.validate_publication_document(
                profile, requirements=_index([open_requirement()])
            )
        }
        self.assertIn("publication.binding-missing", codes)


class AntiExtensionCoverageTests(unittest.TestCase):
    """The anti-extension guard covers every packaged schema, not just one."""

    def _ci(self):
        import importlib.util
        import os

        path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "src", "raes_env_packs", "content_ci.py",
        )
        spec = importlib.util.spec_from_file_location("content_ci_publication", path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    def test_guard_inspects_the_publication_schema(self) -> None:
        ci = self._ci()
        guarded = {path.name for path in ci.packaged_schema_paths()}
        self.assertIn("publication-profile.schema.yaml", guarded)
        self.assertIn("pack-compatibility.schema.yaml", guarded)

    def test_a_forbidden_layer_in_the_publication_schema_is_caught(self) -> None:
        """Regression guard: the new schema cannot smuggle in RAES semantics."""
        ci = self._ci()
        import yaml

        schema = yaml.safe_load(
            publication.publication_schema_path().read_text(encoding="utf-8")
        )
        schema["properties"]["telemetry"] = {"type": "object"}
        offending = sorted(
            key for key in ci._schema_properties(schema)
            if key in ci.FORBIDDEN_MANIFEST_LAYERS
        )
        self.assertEqual(offending, ["telemetry"])

    def test_shipped_publication_schema_declares_no_forbidden_layer(self) -> None:
        ci = self._ci()
        failures: list[str] = []
        ci.check_anti_extension(failures, ())
        self.assertEqual([f for f in failures if "publication" in f], [])


class SemanticBindingTests(unittest.TestCase):
    """A content-identified pack really does bind its RAES identities.

    Regression guard: the binding reads RAES's own ``ref_id`` / ``ref_digest``
    parent fields. Reading a plausible-but-wrong attribute name would make every
    binding silently absent, which in turn would silently permit an unverifiable
    release to claim nothing and pass.
    """

    def _content_identified_pack(self):
        import json
        import shutil
        import tempfile
        from pathlib import Path

        import raes_contracts.contracts  # noqa: F401  (import-order guard)
        from raes_contracts.associated_artifacts import (
            AssociatedArtifactManifestModel,
            associated_artifact_set_digest,
        )

        # The pack directory name must equal the pack name for the shared
        # author-static contract to accept it.
        parent = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, parent, ignore_errors=True)
        root = parent / "example-pack"
        (root / "sdl").mkdir(parents=True)
        (root / "pack.yaml").write_text(
            "name: example-pack\nversion: 0.1.0\n"
            "associated_artifact_manifest: associated-artifacts.json\n",
            encoding="utf-8",
        )
        (root / "sdl" / "example.sdl.yaml").write_text(
            "name: example-pack\nnodes:\n  target:\n    type: vm\n", encoding="utf-8"
        )
        artifacts = {}
        for index, rel in enumerate(("pack.yaml", "sdl/example.sdl.yaml")):
            body = (root / rel).read_bytes()
            artifacts[f"artifact-{index}"] = {
                "artifact_id": f"artifact-{index}",
                "role": "other",
                "media_type": "application/octet-stream",
                "uri": f"raes-environment-pack:/{rel}",
                "checksum": {"algorithm": "sha256",
                             "value": __import__("hashlib").sha256(body).hexdigest()},
                "size_bytes": len(body),
                "created_at": "2026-07-28T00:00:00Z",
                "source": "environment-pack-author",
                "sensitivity": "internal",
            }
        model = AssociatedArtifactManifestModel.model_validate({
            "schema_version": "associated-artifact-manifest/v1",
            "manifest_id": "example-pack-associated-artifacts",
            "manifest_version": "0.1.0",
            "canonicalization_profile": "associated-artifact-set/v1",
            "scope": "scenario",
            "parent_ref": {"ref_kind": "scenario", "ref_id": "example-pack"},
            "artifacts": artifacts,
            "set_digest": "sha256:" + "0" * 64,
        })
        model = model.model_copy(
            update={"set_digest": associated_artifact_set_digest(model)})
        (root / "associated-artifacts.json").write_text(
            json.dumps(json.loads(model.model_dump_json()), indent=2) + "\n",
            encoding="utf-8")
        return root

    def test_release_binds_the_raes_parent_and_source_set(self) -> None:
        from raes_env_packs import release

        root = self._content_identified_pack()
        profile = release.release_metadata(str(root))
        self.assertEqual(
            profile["release"]["semantic_parent"]["parent_ref"], "example-pack")
        self.assertTrue(
            profile["release"]["source_set"]["set_digest"].startswith("sha256:"))
        self.assertEqual(
            profile["release"]["source_set"]["manifest_id"],
            "example-pack-associated-artifacts")


class PerViewSetIdentityTests(SemanticBindingTests):
    """Set identity does not inherit: each non-empty view carries its own."""

    def _built(self):
        import tempfile

        from raes_env_packs import release

        root = self._content_identified_pack()
        (root / "docs").mkdir(exist_ok=True)
        (root / "docs" / "brief.md").write_text("# brief\n", encoding="utf-8")
        (root / "docs" / "operator.md").write_text("# operator\n", encoding="utf-8")
        import yaml as _yaml

        (root / "pack.compatibility.yaml").write_text(_yaml.safe_dump({
            "schema_version": "environment-pack-compatibility/v2",
            "pack": {"name": "example-pack", "title": "Example pack",
                     "version": "0.1.0", "status": "draft",
                     "source": {"requirement": None, "issues": [],
                                "upstream_references": []}},
            "artifact_boundaries": {
                "participant_visible": [{"path": "docs/brief.md", "export": "public"}],
                "operator_only": [{"path": "docs/operator.md", "export": "operator"}],
                "oracle_only": [], "commercial": []},
            "runtime_profiles": [], "delivery_bundles": [], "platform_features": [],
            "assets": [], "operator_surfaces": [],
            "validation": {"commands": [], "gates": []},
        }), encoding="utf-8")
        (root / "docs" / "provenance-ledger.yaml").write_text(_yaml.safe_dump({
            "schema_version": "environment-pack-provenance/v3",
            "pack": {"name": "example-pack"},
            "sources": [{"source_id": "orig", "name": "Original design",
                         "license": "proprietary", "usage": "generated-from",
                         "attribution_required": False}],
            "artifacts": [{"artifact_id": "a1", "path": "docs/",
                           "classification": "open"}],
            "content_safety": {
                "no_real_malware": True, "no_real_third_party_targets": True,
                "no_real_credentials": True, "no_sensitive_data": True,
                "offensive_tooling_boundary": True},
            "review": {"status": "approved", "gates": [
                {"gate_id": "licensing", "status": "approved"},
                {"gate_id": "attribution", "status": "approved"},
                {"gate_id": "sensitive-data", "status": "approved"},
                {"gate_id": "offensive-tooling", "status": "approved"}]},
        }), encoding="utf-8")
        manifest = (root / "pack.yaml").read_text(encoding="utf-8")
        (root / "pack.yaml").write_text(
            manifest
            + "title: Example pack\n"
            + "compatibility_manifest: pack.compatibility.yaml\n"
            + "provenance_ledger: docs/provenance-ledger.yaml\n",
            encoding="utf-8")
        # Re-derive so the declared manifest still covers the exact inventory.
        self._redeclare(root)
        out = tempfile.mkdtemp()
        self.addCleanup(__import__("shutil").rmtree, out, ignore_errors=True)
        self._out = out
        return release.build_release(str(root), out)

    def _redeclare(self, root) -> None:
        import hashlib
        import json

        import raes_contracts.contracts  # noqa: F401
        from raes_contracts.associated_artifacts import (
            AssociatedArtifactManifestModel, associated_artifact_set_digest)

        rels = sorted(
            str(p.relative_to(root)).replace("\\", "/")
            for p in root.rglob("*")
            if p.is_file() and p.name != "associated-artifacts.json")
        artifacts = {}
        for index, rel in enumerate(rels):
            body = (root / rel).read_bytes()
            artifacts[f"artifact-{index}"] = {
                "artifact_id": f"artifact-{index}", "role": "other",
                "media_type": "application/octet-stream",
                "uri": f"raes-environment-pack:/{rel}",
                "checksum": {"algorithm": "sha256",
                             "value": hashlib.sha256(body).hexdigest()},
                "size_bytes": len(body), "created_at": "2026-07-28T00:00:00Z",
                "source": "environment-pack-author", "sensitivity": "internal",
            }
        model = AssociatedArtifactManifestModel.model_validate({
            "schema_version": "associated-artifact-manifest/v1",
            "manifest_id": "example-pack-associated-artifacts",
            "manifest_version": "0.1.0",
            "canonicalization_profile": "associated-artifact-set/v1",
            "scope": "scenario",
            "parent_ref": {"ref_kind": "scenario", "ref_id": "example-pack"},
            "artifacts": artifacts, "set_digest": "sha256:" + "0" * 64})
        model = model.model_copy(
            update={"set_digest": associated_artifact_set_digest(model)})
        (root / "associated-artifacts.json").write_text(
            json.dumps(json.loads(model.model_dump_json()), indent=2) + "\n",
            encoding="utf-8")

    def _views(self, profile):
        return {v["view"]: v.get("set") for v in profile["release"]["views"]}

    def test_each_nonempty_view_gets_its_own_set_identity(self) -> None:
        profile, failures = self._built()
        self.assertEqual(failures, [])
        views = self._views(profile)
        self.assertIsNotNone(views["participant"])
        self.assertIsNotNone(views["operator"])
        self.assertNotEqual(
            views["participant"]["set_digest"], views["operator"]["set_digest"])

    def test_a_view_set_digest_is_not_the_source_pack_digest(self) -> None:
        """A filtered view is a different payload set than the whole pack."""
        profile, _failures = self._built()
        source = profile["release"]["source_set"]["set_digest"]
        for view_set in self._views(profile).values():
            if view_set is not None:
                self.assertNotEqual(view_set["set_digest"], source)

    def test_empty_views_invent_no_placeholder_artifact(self) -> None:
        profile, _failures = self._built()
        views = self._views(profile)
        self.assertIsNone(views["restricted"])
        self.assertIsNone(views["commercial"])

    def test_each_view_manifest_is_emitted_beside_its_view(self) -> None:
        """A set digest without descriptors is unverifiable by a consumer."""
        import json
        import os

        profile, failures = self._built()
        self.assertEqual(failures, [])
        root = os.path.join(
            self._out, f"example-pack-{profile['release']['pack']['version']}")
        for view, view_set in self._views(profile).items():
            if view_set is None:
                continue
            emitted = os.path.join(root, f"{view}-associated-artifacts.json")
            self.assertTrue(os.path.isfile(emitted), f"no manifest for view {view}")
            with open(emitted, encoding="utf-8") as fh:
                manifest = json.load(fh)
            self.assertEqual(manifest["set_digest"], view_set["set_digest"])
            self.assertTrue(manifest["artifacts"])
            # The manifest may not live inside the set it describes.
            self.assertFalse(os.path.exists(os.path.join(root, view, os.path.basename(emitted))))

    def test_view_digest_follows_the_staged_bytes(self) -> None:
        """Identity binds the promoted bytes, not whatever the source holds later."""
        import hashlib
        import json
        import os

        profile, _failures = self._built()
        root = os.path.join(
            self._out, f"example-pack-{profile['release']['pack']['version']}")
        with open(os.path.join(root, "participant-associated-artifacts.json"),
                  encoding="utf-8") as fh:
            manifest = json.load(fh)
        for artifact in manifest["artifacts"].values():
            rel = artifact["uri"].split(":/", 1)[1]
            staged = os.path.join(root, "participant", *rel.split("/"))
            self.assertTrue(os.path.isfile(staged))
            with open(staged, "rb") as fh:
                self.assertEqual(
                    artifact["checksum"]["value"],
                    hashlib.sha256(fh.read()).hexdigest(),
                    "view descriptor does not describe the promoted bytes")

    def test_view_identity_is_reproducible_across_rebuilds(self) -> None:
        """Identity must not drift on rebuild, or immutability is unenforceable."""
        first, _ = self._built()
        second, _ = self._built()
        self.assertEqual(self._views(second), self._views(first))


class StagedViewModeTests(unittest.TestCase):
    """Generated views use fixed safe modes, not inherited source metadata."""

    def test_staged_files_do_not_inherit_setid_or_world_writable_modes(self) -> None:
        import os
        import shutil
        import stat
        import tempfile

        from raes_env_packs import release
        from tests.test_release import _make_pack

        parent = tempfile.mkdtemp()
        out = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, parent, ignore_errors=True)
        self.addCleanup(shutil.rmtree, out, ignore_errors=True)

        pack = _make_pack(parent, delivery_bundles=[])
        # A pack file carrying set-user-id and world-writable bits.
        brief = os.path.join(pack, "assets", "briefing", "brief.md")
        os.chmod(brief, 0o4777)

        meta, failures = release.build_release(pack, out)
        self.assertEqual(failures, [])
        staged = os.path.join(
            out, f"{meta['release']['pack']['name']}-{meta['release']['pack']['version']}",
            "participant", "assets", "briefing", "brief.md")
        self.assertTrue(os.path.isfile(staged))
        mode = os.stat(staged).st_mode
        self.assertFalse(mode & stat.S_ISUID, "staged view kept a set-user-id bit")
        self.assertFalse(mode & stat.S_ISGID, "staged view kept a set-group-id bit")
        self.assertFalse(mode & stat.S_IWOTH, "staged view is world-writable")
        self.assertEqual(stat.S_IMODE(mode), release.STAGED_FILE_MODE)


class ViewMembershipTests(unittest.TestCase):
    """A supplied artifact must be present in the view it claims to ship in."""

    def _codes_with_members(self, members: dict[str, set[str]]) -> set[str]:
        return {
            v.code
            for v in publication.publication_violations(
                _profile([_publication()]),
                requirements=_index([exact_requirement()]),
                view_members=members,
            )
        }

    def test_artifact_present_in_its_view_is_accepted(self) -> None:
        self.assertEqual(self._codes_with_members({"participant": {_digest("a")}}), set())

    def test_artifact_absent_from_its_view_is_rejected(self) -> None:
        """Otherwise a view could expose unrelated bytes under a trusted claim."""
        codes = self._codes_with_members({"participant": {_digest("z")}})
        self.assertIn("publication.artifact-not-in-view", codes)

    def test_membership_is_skipped_when_no_staged_sets_are_supplied(self) -> None:
        """A standalone document check has no bytes to join against."""
        self.assertEqual(_codes(_profile([_publication()]), [exact_requirement()]), set())


class AccessPolicyRefSecretTests(unittest.TestCase):
    """Every emitted availability reference is secret-filtered, not just `location`."""

    def _codes_for(self, **row: object) -> set[str]:
        profile = _profile([])
        profile["distribution"]["availability"] = [dict({"provider": "reg"}, **row)]
        return _codes(profile, [exact_requirement()])

    def test_credential_in_access_policy_ref_is_rejected(self) -> None:
        codes = self._codes_for(
            access_policy_ref="https://user:secret@example.test/policy")
        self.assertIn("publication.availability-secret", codes)

    def test_signed_query_in_access_policy_ref_is_rejected(self) -> None:
        codes = self._codes_for(
            access_policy_ref="https://example.test/policy?access_token=abc")
        self.assertIn("publication.availability-secret", codes)

    def test_plain_policy_reference_is_accepted(self) -> None:
        self.assertEqual(self._codes_for(access_policy_ref="org-policy:standard-access"),
                         set())


class PublicationViewVocabularyTests(unittest.TestCase):
    """`BOUNDARY_TIERS` is the one seam from authored groups to publication views."""

    def test_oracle_only_maps_to_the_restricted_publication_view(self) -> None:
        """`restricted` carries no scenario or validation-oracle meaning."""
        from raes_env_packs import release

        self.assertEqual(release.BOUNDARY_TIERS["oracle_only"], "restricted")

    def test_every_boundary_group_maps_to_a_schema_declared_view(self) -> None:
        """The seam cannot drift from the vocabulary the profile schema allows."""
        import yaml

        from raes_env_packs import release

        schema = yaml.safe_load(
            publication.publication_schema_path().read_text(encoding="utf-8")
        )
        declared = set(schema["$defs"]["release_view"]["properties"]["view"]["enum"])
        self.assertEqual(set(release.BOUNDARY_TIERS.values()), declared)


if __name__ == "__main__":
    unittest.main()
