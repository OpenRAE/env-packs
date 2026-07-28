"""Environment-pack publication profile (ADR 0028).

The publication profile turns one validated pack release into distributable,
verifiable release views. It is a *pack-domain* contract: it records which
permitted assets or specifications are supplied with a release and their
non-secret availability. It is **not** a second semantic authority.

RAES owns author posture, mechanism vocabulary, acquisition, timing, permitted
routes, trust references, and associated-artifact byte binding. This module
consumes those through the public API of the exact ``raes`` pin and copies no
RAES schema, enum, address grammar, mechanism list, or validator. In particular
a published mechanism profile and artifact identity are checked by *constructing
the upstream models*, so an upstream tightening applies here automatically and
this package can never drift out of step with the governed vocabulary.

Publication is a claim about release assets; it never overrides what the author
declared. An exact artifact stays exact, a constrained requirement may advertise
conforming candidates without that set becoming exhaustive, an open requirement
may lean on a declared backend capability, and a requirement may be published
with nothing at all.
"""

from __future__ import annotations

import dataclasses
from collections.abc import Iterator, Mapping
from pathlib import Path
from typing import get_args
from urllib.parse import parse_qsl, urlsplit

from raes.artifact_requirements import (
    ArtifactIdentity,
    ArtifactMechanismProfile,
    ArtifactRequirement,
    ArtifactSatisfactionRoute,
    Source,
)
from raes_contracts.addressing import (
    PLAN_ADDRESS_ROOT_BY_DOMAIN,
    render_compiled_address,
    require_compiled_address,
)
from raes_contracts.artifact_requirements import ArtifactMechanismCapability
from raes_contracts.backend_profiles import load_backend_profile

from raes_env_packs import validation

PUBLICATION_SCHEMA_VERSION = "environment-pack-publication/v1"

# The authored local-id selectors a publication row may carry. Absence means the
# row supplies the requirement's own exact artifact. These are RAES-authored id
# *joins*, not a pack-defined role vocabulary.
_SELECTORS = ("candidate_id", "locked_input_id", "specification_id")

# Stable diagnostic codes. Named once so a code cannot drift between the site
# that raises it, the tests that assert it, and the prose that documents it.
CODE_REQUIREMENT_UNKNOWN = "publication.requirement-unknown"
CODE_REQUIREMENT_ID_MISMATCH = "publication.requirement-id-mismatch"
CODE_ADDRESS_INVALID = "publication.address-invalid"
CODE_ADDRESS_AMBIGUOUS = "publication.address-ambiguous"
CODE_SELECTOR_AMBIGUOUS = "publication.selector-ambiguous"
CODE_SELECTOR_MISSING = "publication.selector-missing"
CODE_SELECTOR_UNKNOWN = "publication.selector-unknown"
CODE_EXACT_SUBSTITUTION = "publication.exact-substitution"
CODE_ARTIFACT_MISMATCH = "publication.artifact-mismatch"
CODE_ARTIFACT_INVALID = "publication.artifact-invalid"
CODE_ARTIFACT_NOT_IN_VIEW = "publication.artifact-not-in-view"
CODE_OPEN_OVERREACH = "publication.open-overreach"
CODE_MATERIALIZATION_UNPERMITTED = "publication.materialization-unpermitted"
CODE_MECHANISM_INVALID = "publication.mechanism-invalid"
CODE_MECHANISM_UNPERMITTED = "publication.mechanism-unpermitted"
CODE_CAPABILITY_UNPROVEN = "publication.capability-unproven"
CODE_CAPABILITY_INAPPLICABLE = "publication.capability-inapplicable"
CODE_BACKEND_PROFILE_UNTRUSTED = "publication.backend-profile-untrusted"
CODE_BINDING_MISSING = "publication.binding-missing"
CODE_VIEW_SET_MISSING = "publication.view-set-missing"
CODE_IDENTITY_MUTABLE_FIELD = "publication.identity-mutable-field"
CODE_AVAILABILITY_SECRET = "publication.availability-secret"
CODE_CHANNEL_UNRESOLVED = "publication.channel-unresolved"


@dataclasses.dataclass(frozen=True)
class PublicationViolation(object):
    """A bounded, body-free publication diagnostic.

    ``code`` is a stable diagnostic term and ``path`` a bounded field location.
    Neither carries artifact bytes, URI query values, credentials, restricted
    paths, or raw upstream exception text.
    """

    code: str
    path: str


def _rows(profile: object) -> Iterator[tuple[dict[str, object], str, str]]:
    """Yield each publication row with its bounded field path and view name."""

    release = profile.get("release") if isinstance(profile, dict) else None
    views = release.get("views") if isinstance(release, dict) else None
    for view_index, view in enumerate(views or []):
        if not isinstance(view, dict):
            continue
        publications = view.get("publications")
        base = f"$.release.views[{view_index}].publications"
        name = view.get("view") if isinstance(view.get("view"), str) else ""
        for row_index, row in enumerate(publications or []):
            if isinstance(row, dict):
                yield row, f"{base}[{row_index}]", name


def _selectors(row: Mapping[str, object]) -> tuple[str, ...]:
    """Return the authored local-id selectors present on one row."""

    return tuple(name for name in _SELECTORS if row.get(name) is not None)


def _exact_violations(
    row: Mapping[str, object], requirement: ArtifactRequirement, path: str
) -> list[PublicationViolation]:
    """An exact requirement may reference only its exact immutable artifact.

    A selector would relabel that artifact as a candidate, locked input, or
    materialization output, and any other identity is a substitute. RAES forbids
    both; publication must not launder either past that authority.
    """

    if _selectors(row) or not _matches_identity(row, requirement.exact_artifact):
        return [PublicationViolation(CODE_EXACT_SUBSTITUTION, path)]
    return []


def _matches_identity(row: Mapping[str, object], expected: object) -> bool:
    """True when the row's published artifact equals one authored identity."""

    artifact = row.get("artifact")
    if expected is None or not isinstance(artifact, dict):
        return False
    return (
        artifact.get("artifact_id") == expected.artifact_id
        and artifact.get("version") == expected.version
        and artifact.get("digest") == expected.digest
        and artifact.get("media_type") == expected.media_type
    )


def _candidate_violations(
    row: Mapping[str, object], requirement: ArtifactRequirement, path: str
) -> list[PublicationViolation]:
    """A declared candidate id must carry that candidate's immutable artifact."""

    for candidate in requirement.candidates:
        if candidate.candidate_id == row.get("candidate_id"):
            if _matches_identity(row, candidate.artifact):
                return []
            return [PublicationViolation(CODE_ARTIFACT_MISMATCH, path)]
    return [PublicationViolation(CODE_SELECTOR_UNKNOWN, path)]


def _locked_input_violations(
    row: Mapping[str, object], requirement: ArtifactRequirement, path: str
) -> list[PublicationViolation]:
    """A locked input stays a locked input, bound to its authored identity."""

    for locked in requirement.locked_inputs:
        if locked.input_id == row.get("locked_input_id"):
            if _matches_identity(row, locked.artifact):
                return []
            return [PublicationViolation(CODE_ARTIFACT_MISMATCH, path)]
    return [PublicationViolation(CODE_SELECTOR_UNKNOWN, path)]


def _specification_violations(
    row: Mapping[str, object], requirement: ArtifactRequirement, path: str
) -> list[PublicationViolation]:
    """A specification is publishable only at its exact authored id/profile/digest."""

    for spec in requirement.materialization_specifications:
        if spec.specification_id == row.get("specification_id"):
            mechanism = row.get("mechanism")
            profile = mechanism if isinstance(mechanism, dict) else {}
            if (
                row.get("specification_digest") == spec.digest
                and profile.get("mechanism") == spec.profile.mechanism
                and profile.get("profile") == spec.profile.profile
                and profile.get("version") == spec.profile.version
                and profile.get("digest") == spec.profile.digest
            ):
                return []
            return [PublicationViolation(CODE_MATERIALIZATION_UNPERMITTED, path)]
    return [PublicationViolation(CODE_SELECTOR_UNKNOWN, path)]


_SELECTOR_CHECKS = {
    "candidate_id": _candidate_violations,
    "locked_input_id": _locked_input_violations,
    "specification_id": _specification_violations,
}


def _constrained_violations(
    row: Mapping[str, object], requirement: ArtifactRequirement, path: str
) -> list[PublicationViolation]:
    """A constrained requirement supplies one of its own declared authorities.

    There is no exact artifact to supply implicitly, so a row without a selector
    names nothing the author admitted. Advertising several declared candidates is
    legitimate and never makes the advertised set exhaustive.
    """

    selectors = _selectors(row)
    if not selectors:
        return [PublicationViolation(CODE_SELECTOR_MISSING, path)]
    return _SELECTOR_CHECKS[selectors[0]](row, requirement, path)


def _open_violations(
    row: Mapping[str, object], _requirement: ArtifactRequirement, path: str
) -> list[PublicationViolation]:
    """An open requirement gets no fabricated image, candidate, or recipe.

    Backend-native or dynamic satisfaction is claimed by capability reference on
    the view, never by inventing a pack artifact the author never admitted.
    """

    if _selectors(row) or row.get("artifact") is not None:
        return [PublicationViolation(CODE_OPEN_OVERREACH, path)]
    return []


_POSTURE_CHECKS = {
    "exact": _exact_violations,
    "constrained": _constrained_violations,
    "open": _open_violations,
}


def publication_schema_path() -> Path:
    """Path to the packaged publication-profile schema."""

    return Path(__file__).with_name("resources") / "schemas" / "publication-profile.schema.yaml"


def validate_publication_document(
    profile: object,
    *,
    requirements: Mapping[str, ArtifactRequirement],
    view_members: Mapping[str, set[str]] | None = None,
) -> list[PublicationViolation]:
    """Validate one publication profile's shape and its RAES authority joins.

    This is the single helper the release emitter and any future consumer adapter
    call. It reuses the repository's packaged-schema loader and schema-subset
    validator rather than introducing a second validation path, and it re-parses
    no pack, provenance, compatibility, or SDL contract of its own.
    """

    schema = validation._trusted_schema(publication_schema_path())
    violations = [
        PublicationViolation(f"publication.schema.{item.code}", item.path)
        for item in validation._schema_violations(profile, schema, schema)
    ]
    violations.extend(publication_violations(
        profile, requirements=requirements, view_members=view_members))
    return violations


def _field_may_hold_source(model: type, field: str) -> bool:
    """True when ``model.field`` can structurally contain a RAES ``Source``.

    Used to discover which scenario containers own artifact requirements instead
    of hard-coding the list. RAES may attach a ``Source`` to nodes, content,
    features, conditions, injects, or events today; a hard-coded set would
    silently miss a requirement the author declared through a container added
    upstream later.
    """

    info = getattr(model, "model_fields", {}).get(field)
    return info is not None and _annotation_holds_source(info.annotation, set())


def _annotation_holds_source(annotation: object, seen: set[object]) -> bool:
    """Recursively decide whether a type annotation can yield a ``Source``."""

    if annotation is Source:
        return True
    if annotation in seen:
        return False
    seen.add(annotation)
    nested = getattr(annotation, "model_fields", None)
    children = (
        [info.annotation for info in nested.values()]
        if nested is not None
        else list(get_args(annotation))
    )
    return any(_annotation_holds_source(child, seen) for child in children)


def _iter_sources(
    value: object, seen: set[int], trail: tuple[str, ...] = ()
) -> Iterator[tuple[Source, tuple[str, ...]]]:
    """Yield every ``Source`` reachable from a parsed RAES model, with its trail.

    The trail is the owning container path (for example ``("nodes", "target")``),
    which is what distinguishes two requirements that happen to share a local id.
    """

    if id(value) in seen:
        return
    seen.add(id(value))
    if isinstance(value, Source):
        yield value, trail
    for step, child in _child_nodes(value):
        yield from _iter_sources(child, seen, trail + step)


def _child_nodes(value: object) -> Iterator[tuple[tuple[str, ...], object]]:
    """Yield ``(trail_step, child)`` for every traversable child of ``value``."""

    fields = getattr(type(value), "model_fields", None)
    if fields is not None:
        for field in fields:
            yield (field,), getattr(value, field, None)
    elif isinstance(value, Mapping):
        for key, item in value.items():
            yield ((str(key),) if isinstance(key, str) else ()), item
    elif isinstance(value, (list, tuple, set, frozenset)):
        for index, item in enumerate(value):
            yield (str(index),), item


# RAES compiles a source artifact requirement under the provisioning plan root.
# The root name and the address grammar are RAES-owned; this package only asks
# the addressing helpers to render and validate them.
_PLAN_ROOT = PLAN_ADDRESS_ROOT_BY_DOMAIN["provisioning"]
_REQUIREMENT_KIND = "source-artifact"
# The governed contract under which a backend declares its artifact mechanisms.
_BACKEND_MANIFEST_CONTRACT = "backend-manifest-v2"


def compiled_requirement_address(trail: tuple[str, ...]) -> str:
    """Render the compiled address for a requirement owned at ``trail``."""

    return render_compiled_address(_PLAN_ROOT, *trail, _REQUIREMENT_KIND)


def authored_artifact_requirements(
    scenarios: object,
) -> dict[str, ArtifactRequirement]:
    """Index every authored artifact requirement by its compiled RAES address.

    This is the authority every release claim is joined back to, and it is keyed
    by address rather than by local id on purpose: RAES scopes candidate,
    constraint, and locked-input ids to one requirement, so two owners may
    legitimately declare the same local id. Collapsing them into an id-keyed map
    would let a claim bind to the wrong authored requirement, and would silently
    drop every requirement after the first.
    """

    found: dict[str, ArtifactRequirement | None] = {}
    seen: set[int] = set()
    for scenario in scenarios or ():
        for source, trail in _iter_sources(scenario, seen):
            requirement = source.artifact_requirement
            if requirement is None:
                continue
            address = compiled_requirement_address(trail)
            if address in found and found[address] is not requirement:
                # Two SDL documents can carry the same owner trail. Silently
                # keeping the last one would validate a claim against whichever
                # scenario happened to be parsed last; mark the address ambiguous
                # so resolving it fails instead.
                found[address] = None
            else:
                found[address] = requirement
    return found


def release_identity(profile: object) -> dict[str, object]:
    """Return the immutable release identity tuple, represented directly.

    Per ADR 0028 this repository defines no second canonicalization or release
    digest: identity is the pack id/version together with the RAES semantic
    parent, the validated source-pack associated-artifact set, and the set of
    every non-empty release view. Mutable channel and provider/location records
    are deliberately outside it, so distribution can evolve without an unchanged
    release acquiring a new identity.
    """

    release = profile.get("release") if isinstance(profile, dict) else None
    release = release if isinstance(release, dict) else {}
    views: dict[str, object] = {}
    for view in release.get("views") or []:
        if isinstance(view, dict) and isinstance(view.get("view"), str):
            views[view["view"]] = view.get("set")
    return {
        "pack": release.get("pack"),
        "semantic_parent": release.get("semantic_parent"),
        "source_set": release.get("source_set"),
        "views": views,
    }


# Mutable distribution and secret-bearing vocabulary. These are resolution or
# access facts, never immutable release identity and never pack content.
_MUTABLE_IDENTITY_KEYS = frozenset({"availability", "channels", "channel", "location"})
_SECRET_KEYS = frozenset(
    {"credential", "credentials", "token", "secret", "password", "entitlement"}
)
# Query parameters that are known to be non-secret locator refinements. Anything
# outside this allowlist is rejected. A denylist of known credential parameter
# names cannot work here: signed-URL and bearer-token schemes differ per provider
# (`signature`, `access_token`, `api_key`, `x-goog-signature`, `X-Amz-Credential`,
# ...) and a name the list has not seen yet would be written verbatim into a
# published release. Fail closed instead, so a new credential format is rejected
# rather than exfiltrated.
_NON_SECRET_QUERY_KEYS = frozenset({"tag", "version", "digest", "arch", "os"})


def _binding_violations(profile: object) -> list[PublicationViolation]:
    """Any published claim requires a validated RAES identity binding.

    ADR 0012 keeps pack content identity opt-in and ADR 0028 requires a
    validated semantic parent and associated-artifact set before a release is
    published. Both hold at once: a release that claims nothing has nothing to
    verify, while a single publication or capability claim is only meaningful
    against bound, verifiable bytes.
    """

    release = profile.get("release") if isinstance(profile, dict) else None
    if not isinstance(release, dict):
        return []
    claiming = [view for view in _views(release) if _view_claims(view)]
    if not claiming:
        return []
    return (
        _parent_binding_violations(release)
        + _claiming_view_violations(release)
    )


def _views(release: Mapping[str, object]) -> list[Mapping[str, object]]:
    """Return the well-formed view entries of one release block."""

    return [view for view in release.get("views") or [] if isinstance(view, Mapping)]


def _view_claims(view: Mapping[str, object]) -> bool:
    """True when a view publishes an artifact or asserts a capability."""

    return bool(view.get("publications") or view.get("capability_claims"))


def _parent_binding_violations(
    release: Mapping[str, object],
) -> list[PublicationViolation]:
    """A claim needs the semantic parent and associated-artifact set bindings.

    ADR 0028 identifies a release by the semantic parent *reference and digest*.
    A parent id alone would let the same id carry changed semantics without
    changing release identity, so a claim needs the digest too.
    """

    violations = [
        PublicationViolation(CODE_BINDING_MISSING, f"$.release.{block}")
        for block in ("semantic_parent", "source_set")
        if not release.get(block)
    ]
    parent = release.get("semantic_parent")
    if isinstance(parent, Mapping) and not parent.get("digest"):
        violations.append(PublicationViolation(
            CODE_BINDING_MISSING, "$.release.semantic_parent.digest"))
    return violations


def _claiming_view_violations(
    release: Mapping[str, object],
) -> list[PublicationViolation]:
    """A view that publishes something must be a bound, non-empty view.

    Without this a claim could target a view that exposes no bytes at all, and a
    consumer would have no set against which to verify what it received.
    """

    return [
        PublicationViolation(CODE_VIEW_SET_MISSING, f"$.release.views[{index}].set")
        for index, view in enumerate(_views(release))
        if _view_claims(view) and not view.get("set")
    ]


def _identity_block_violations(profile: object) -> list[PublicationViolation]:
    """The immutable identity block carries no mutable or secret vocabulary."""

    release = profile.get("release") if isinstance(profile, dict) else None
    if not isinstance(release, dict):
        return []
    return [
        PublicationViolation(CODE_IDENTITY_MUTABLE_FIELD, f"$.release.{key}")
        for key in sorted(release)
        if key in _MUTABLE_IDENTITY_KEYS or key in _SECRET_KEYS
    ]


def _location_is_secret_bearing(location: str) -> bool:
    """True when a published locator may carry credential material.

    Userinfo, any fragment, and any query parameter outside the non-secret
    allowlist are all treated as potentially secret-bearing.
    """

    try:
        parsed = urlsplit(location)
    except ValueError:
        return True
    if parsed.username or parsed.password or parsed.fragment:
        return True
    return any(
        name.strip().lower() not in _NON_SECRET_QUERY_KEYS
        for name, _value in parse_qsl(parsed.query, keep_blank_values=True)
    )


def _availability_violations(profile: object) -> list[PublicationViolation]:
    """Availability records are non-secret data; credentials are not pack content.

    Diagnostics name the record position only. The offending locator is never
    echoed, so a bounded error surface cannot itself disclose a credential.
    """

    distribution = profile.get("distribution") if isinstance(profile, dict) else None
    rows = distribution.get("availability") if isinstance(distribution, dict) else None
    violations: list[PublicationViolation] = []
    for index, row in enumerate(rows or []):
        if not isinstance(row, Mapping):
            continue
        path = f"$.distribution.availability[{index}]"
        # Every emitted reference is checked, not just `location`. An
        # access-policy pointer is published verbatim too, so an authenticated
        # URL, signed query, or secret-store coordinate placed there would reach
        # every release consumer exactly as one in `location` would.
        for field in ("location", "access_policy_ref"):
            value = row.get(field)
            if isinstance(value, str) and _location_is_secret_bearing(value):
                violations.append(
                    PublicationViolation(CODE_AVAILABILITY_SECRET,
                                         f"{path}.{field}"))
        violations.extend(
            PublicationViolation(CODE_AVAILABILITY_SECRET, f"{path}.{key}")
            for key in sorted(row)
            if key in _SECRET_KEYS
        )
    return violations


def _channel_violations(profile: object) -> list[PublicationViolation]:
    """Every channel resolves to this release's complete immutable identity."""

    distribution = profile.get("distribution") if isinstance(profile, dict) else None
    rows = distribution.get("channels") if isinstance(distribution, dict) else None
    identity = release_identity(profile)
    return [
        PublicationViolation(CODE_CHANNEL_UNRESOLVED,
                             f"$.distribution.channels[{index}]")
        for index, row in enumerate(rows or [])
        if not isinstance(row, Mapping) or row.get("release_identity") != identity
    ]


def _upstream_valid(model: type, value: object) -> bool:
    """True when RAES accepts ``value`` as one of its own governed models.

    Delegating here is what keeps mechanism names, digest syntax, and identity
    shape RAES-owned. This package holds no copy of that vocabulary, so an
    upstream tightening takes effect without a change on this side.
    """

    if not isinstance(value, Mapping):
        return False
    try:
        model(**value)
    except (TypeError, ValueError):
        return False
    return True


def _structure_violations(
    row: Mapping[str, object], path: str
) -> list[PublicationViolation]:
    """Reject a row whose RAES-governed values upstream would not accept."""

    violations: list[PublicationViolation] = []
    artifact = row.get("artifact")
    if artifact is not None and not _upstream_valid(ArtifactIdentity, artifact):
        violations.append(PublicationViolation(CODE_ARTIFACT_INVALID, path))
    mechanism = row.get("mechanism")
    if mechanism is not None and not _upstream_valid(ArtifactMechanismProfile, mechanism):
        violations.append(PublicationViolation(CODE_MECHANISM_INVALID, path))
    return violations


def _route_violations(
    row: Mapping[str, object], requirement: ArtifactRequirement, path: str
) -> list[PublicationViolation]:
    """The supplied mechanism must be one the author actually permitted.

    A governed mechanism name is not consent. Acquisition and timing stay the
    authored route values; publication neither guesses nor defaults them.
    """

    mechanism = row.get("mechanism")
    if not isinstance(mechanism, Mapping):
        return []
    permitted = [
        route.mechanism
        for route in requirement.permitted_routes
        if mechanism.get("mechanism") == route.mechanism.mechanism
        and mechanism.get("profile") == route.mechanism.profile
        and mechanism.get("version") == route.mechanism.version
        and mechanism.get("digest") == route.mechanism.digest
    ]
    if permitted:
        return []
    return [PublicationViolation(CODE_MECHANISM_UNPERMITTED, path)]


def _claims(profile: object) -> Iterator[tuple[Mapping[str, object], str]]:
    """Yield each capability claim with its bounded field path."""

    release = profile.get("release") if isinstance(profile, dict) else None
    views = release.get("views") if isinstance(release, dict) else None
    for view_index, view in enumerate(views or []):
        if not isinstance(view, dict):
            continue
        base = f"$.release.views[{view_index}].capability_claims"
        for claim_index, claim in enumerate(view.get("capability_claims") or []):
            if isinstance(claim, Mapping):
                yield claim, f"{base}[{claim_index}]"


def _claim_violations(
    profile: object, requirements: Mapping[str, ArtifactRequirement]
) -> list[PublicationViolation]:
    """A satisfaction claim needs a concrete, validated mechanism capability.

    A versioned backend profile proves only what that profile contract says; a
    bare profile name is not evidence that a mechanism is supported.
    """

    violations: list[PublicationViolation] = []
    for claim, path in _claims(profile):
        requirement, unresolved = _resolve(claim, requirements, path)
        if requirement is None:
            violations.extend(unresolved)
            continue
        capability = claim.get("mechanism_capability")
        if capability is None or not _upstream_valid(ArtifactMechanismCapability, capability):
            violations.append(PublicationViolation(CODE_CAPABILITY_UNPROVEN, path))
            continue
        untrusted = _backend_profile_violations(claim, path)
        if untrusted:
            violations.extend(untrusted)
            continue
        violations.extend(_capability_applies(capability, requirement, path))
    return violations


def _backend_profile_violations(
    claim: Mapping[str, object], path: str
) -> list[PublicationViolation]:
    """The named backend profile must be a real, trusted RAES profile.

    Without this a pack author could name any profile string and attach a
    self-constructed capability, and a consumer resolving by profile would treat
    an unsupported mechanism as authorized for that backend. The profile is
    resolved from the RAES corpus shipped by the exact pin, and must require
    ``backend-manifest-v2`` -- the governed contract under which a backend
    declares its artifact mechanisms.

    The concrete per-backend manifest is a deployment fact and is not present at
    release time, so this establishes a *compatibility* claim against a real
    profile contract. Proof that a particular backend supports the mechanism
    comes only from that backend at realization (ADR 0028).
    """

    return [] if _is_trusted_backend_profile(claim.get("backend_profile")) else [
        PublicationViolation(CODE_BACKEND_PROFILE_UNTRUSTED, path)]


def _is_trusted_backend_profile(profile: object) -> bool:
    """True when the reference resolves to a real, artifact-aware RAES profile."""

    profile_id = profile.get("profile_id") if isinstance(profile, Mapping) else None
    if not isinstance(profile_id, str):
        return False
    try:
        model = load_backend_profile(profile_id)
    # Upstream raises its own error types for an unknown or malformed profile.
    except Exception:
        return False
    return _BACKEND_MANIFEST_CONTRACT in getattr(model, "required_contracts", ())


def _capability_applies(
    capability: Mapping[str, object], requirement: ArtifactRequirement, path: str
) -> list[PublicationViolation]:
    """A structurally valid capability must also be the *applicable* one.

    Shape alone proves nothing: an unrelated but well-formed capability would
    otherwise stand in as satisfaction evidence. The declared mechanism must be
    one the author permitted, one of its acquisition/timing routes must match a
    permitted route, and the requirement kind must be supported.
    """

    permitted = _permitted_routes_for(capability.get("mechanism"), requirement)
    kinds = capability.get("supported_requirement_kinds") or []
    supported = {
        (route.get("acquisition"), route.get("timing"))
        for route in capability.get("supported_routes") or []
        if isinstance(route, Mapping)
    }
    applies = (
        bool(permitted)
        and _REQUIREMENT_KIND in kinds
        and any((route.acquisition, route.timing) in supported for route in permitted)
    )
    return [] if applies else [
        PublicationViolation(CODE_CAPABILITY_INAPPLICABLE, path)]


def _permitted_routes_for(
    mechanism: object, requirement: ArtifactRequirement
) -> list[ArtifactSatisfactionRoute]:
    """Return the authored routes whose mechanism profile equals ``mechanism``."""

    profile = mechanism if isinstance(mechanism, Mapping) else {}
    return [
        route for route in requirement.permitted_routes
        if profile.get("mechanism") == route.mechanism.mechanism
        and profile.get("profile") == route.mechanism.profile
        and profile.get("version") == route.mechanism.version
        and profile.get("digest") == route.mechanism.digest
    ]


def _resolve(
    claim: Mapping[str, object],
    requirements: Mapping[str, ArtifactRequirement],
    path: str,
) -> tuple[ArtifactRequirement | None, list[PublicationViolation]]:
    """Resolve one claim to its authored requirement by compiled address.

    The address is the authority key; the local ``requirement_id`` is a secondary
    field that must agree with the requirement living at that address. Resolving
    by id alone would let a claim carry one requirement's artifact under another
    requirement's compiled address, which a consumer resolving by address would
    then honour under authority RAES never granted.
    """

    code, requirement = _resolution_outcome(claim, requirements)
    if code is not None:
        return None, [PublicationViolation(code, path)]
    return requirement, []


def _resolution_outcome(
    claim: Mapping[str, object],
    requirements: Mapping[str, ArtifactRequirement],
) -> tuple[str | None, ArtifactRequirement | None]:
    """Return ``(failure_code, requirement)`` for one address resolution."""

    try:
        address = require_compiled_address(
            claim.get("requirement_address"), field_name="requirement_address")
    except (TypeError, ValueError):
        return CODE_ADDRESS_INVALID, None

    requirement = requirements.get(address)
    if address in requirements and requirement is None:
        code = CODE_ADDRESS_AMBIGUOUS
    elif requirement is None:
        code = CODE_REQUIREMENT_UNKNOWN
    elif claim.get("requirement_id") != requirement.requirement_id:
        code = CODE_REQUIREMENT_ID_MISMATCH
    else:
        code = None
    return code, (None if code else requirement)


def _membership_violations(
    row: Mapping[str, object],
    view: str,
    view_members: Mapping[str, set[str]] | None,
    path: str,
) -> list[PublicationViolation]:
    """An artifact claimed as supplied must be present in its view's byte set.

    Otherwise a release could advertise a trusted artifact while the view
    actually exposes unrelated bytes, and a consumer holding only the view
    manifest could not tell the difference.

    ``view_members`` is available only when the caller derived the staged view
    sets; a standalone document check has no bytes to join against and skips it.
    """

    artifact = row.get("artifact")
    if view_members is None or not isinstance(artifact, Mapping):
        return []
    digest = artifact.get("digest")
    if isinstance(digest, str) and digest in view_members.get(view, set()):
        return []
    return [PublicationViolation(CODE_ARTIFACT_NOT_IN_VIEW, path)]


def publication_violations(
    profile: object,
    *,
    requirements: Mapping[str, ArtifactRequirement],
    view_members: Mapping[str, set[str]] | None = None,
) -> list[PublicationViolation]:
    """Return every publication-authority violation in one profile document.

    ``requirements`` maps each *compiled RAES address* to the authored
    requirement recovered from the pack's parsed scenario. Every release claim is
    joined back to that authority; nothing is inferred from the profile alone.
    """

    violations: list[PublicationViolation] = []
    for row, path, view in _rows(profile):
        requirement, unresolved = _resolve(row, requirements, path)
        if requirement is None:
            violations.extend(unresolved)
            continue
        violations.extend(_membership_violations(row, view, view_members, path))
        structural = _structure_violations(row, path)
        if structural:
            # A value RAES would not accept cannot be judged against author
            # intent; report the governed-vocabulary failure and stop there.
            violations.extend(structural)
            continue
        if len(_selectors(row)) > 1:
            violations.append(PublicationViolation(CODE_SELECTOR_AMBIGUOUS, path))
            continue
        violations.extend(_route_violations(row, requirement, path))
        check = _POSTURE_CHECKS.get(requirement.explicitness.value)
        if check is not None:
            violations.extend(check(row, requirement, path))
    violations.extend(_claim_violations(profile, requirements))
    violations.extend(_binding_violations(profile))
    violations.extend(_identity_block_violations(profile))
    violations.extend(_availability_violations(profile))
    violations.extend(_channel_violations(profile))
    return violations
