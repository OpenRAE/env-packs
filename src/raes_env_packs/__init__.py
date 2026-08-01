"""RAES environment-pack definition and authoring/validation tooling.

This package bundles the canonical environment-pack schemas, template, and contract
source (under ``resources/``) together with the tools that
enforce them, so consumers install one version-matched artifact instead of
vendoring the contract.
"""

from importlib.metadata import version

from .digest import (
    PackDigestError,
    ResolvedPackArtifact,
    derive_pack_content_manifest,
    pack_content_digest,
    resolve_pack_artifact,
    validate_pack_content_manifest,
    verify_pack_content_digest,
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
    "Diagnostic",
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
