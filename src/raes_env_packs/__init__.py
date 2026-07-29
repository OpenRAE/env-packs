"""RAES environment-pack definition and authoring/validation tooling.

This package bundles the canonical environment-pack schemas, template, and contract
source (under ``resources/``) together with the tools that
enforce them, so consumers install one version-matched artifact instead of
vendoring the contract.
"""

from importlib.metadata import version

from .digest import (
    PackDigestError,
    derive_pack_content_manifest,
    pack_content_digest,
    validate_pack_content_manifest,
    verify_pack_content_digest,
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
    "PackDigestError",
    "PackValidationLimits",
    "ValidationResult",
    "derive_pack_content_manifest",
    "pack_content_digest",
    "validate_pack_content_manifest",
    "validate_pack",
    "verify_pack_content_digest",
]
