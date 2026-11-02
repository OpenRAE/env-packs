"""Admission of inert local authoring inputs, before any content is read.

RAES remains responsible for import resolution. The local authoring lane never
admits a registry-policy file: the pinned resolver's empty registry policy then
refuses remote imports, including transitive imports, before transport or cache
access. Its local resolver also checks the resolved import stays below the
importing module's directory before opening it, including during transitive
expansion. Callers must supply immutable trees beneath trusted parent directories.
"""
from pathlib import PurePosixPath

from . import _pack_fs


def admit_members(
    members: tuple[str, ...], *, error_type: type[ValueError] = _pack_fs.PackFilesystemError,
) -> None:
    """Reject a RAES trust policy file without opening the members."""
    if any(PurePosixPath(path).name.casefold() == "raes-trust.yaml" for path in members):
        raise error_type("operator files are not admitted to local authoring")
