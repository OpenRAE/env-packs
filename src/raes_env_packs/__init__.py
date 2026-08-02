"""RAES environment-pack definition and authoring/validation tooling.

This package bundles the canonical environment-pack schemas, template, and contract
source (under ``resources/``) together with the tools that
enforce them, so consumers install one version-matched artifact instead of
vendoring the contract.
"""

from importlib.metadata import version

from .component_boundary import (
    Component,
    ComponentBoundaryError,
    pack_component_boundary,
    validate_publication_supply_document,
)
from .digest import (
    PackDigestError,
    ResolvedPackArtifact,
    derive_pack_content_manifest,
    pack_content_digest,
    resolve_pack_artifact,
    validate_pack_content_manifest,
    verify_pack_content_digest,
)
from .distribution import (
    DistributionError,
    OperationPlan,
    Selector,
    apply_install,
    export_pack_archive,
    plan_install,
    plan_lock,
    plan_publish,
    plan_update,
    plan_verify,
    stage_pack_archive,
)
from .release_provenance import (
    build_release_provenance,
    validate_release_provenance,
)
from .sbom import generate_sbom, sbom_digest, validate_sbom_document
from .verify import (
    VerificationResult,
    load_release_evidence,
    verify_pack_release,
)
from .kits import (
    KitError,
    KitLimits,
    KitProposal,
    KitRecoveryError,
    KitRelease,
    KitSource,
    apply_proposal,
    build_kit_catalog,
    inspect_kit,
    load_kit_release,
    proposal_document,
    propose_add,
    propose_remove,
    propose_replace,
    propose_update,
    search_catalog,
    source_release,
)
from .validation import (
    Diagnostic,
    PackValidationLimits,
    ValidationResult,
    validate_pack,
)

# The version lives in pyproject.toml ([project].version), bumped by release-please
# (ADR 0008); __version__ derives from the installed package metadata.
__version__ = version("raes-env-packs")

__all__ = [
    "__version__",
    "Component",
    "ComponentBoundaryError",
    "Diagnostic",
    "DistributionError",
    "OperationPlan",
    "Selector",
    "VerificationResult",
    "apply_install",
    "build_release_provenance",
    "export_pack_archive",
    "generate_sbom",
    "load_release_evidence",
    "pack_component_boundary",
    "plan_install",
    "plan_lock",
    "plan_publish",
    "plan_update",
    "plan_verify",
    "sbom_digest",
    "stage_pack_archive",
    "validate_publication_supply_document",
    "validate_release_provenance",
    "validate_sbom_document",
    "verify_pack_release",
    "KitError",
    "KitLimits",
    "KitProposal",
    "KitRecoveryError",
    "KitRelease",
    "KitSource",
    "PackDigestError",
    "PackValidationLimits",
    "ResolvedPackArtifact",
    "ValidationResult",
    "apply_proposal",
    "build_kit_catalog",
    "derive_pack_content_manifest",
    "inspect_kit",
    "load_kit_release",
    "pack_content_digest",
    "proposal_document",
    "propose_add",
    "propose_remove",
    "propose_replace",
    "propose_update",
    "resolve_pack_artifact",
    "search_catalog",
    "source_release",
    "validate_pack_content_manifest",
    "validate_pack",
    "verify_pack_content_digest",
]
