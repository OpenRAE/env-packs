"""Load a pack's RAES experiment artifact set (issue #504, ADR 0042).

``load_pack_experiments`` runs the shared static authority once and returns the
admitted experiments from that same pass. A pack with any diagnostic returns no
experiment: :class:`PackExperimentError` carries the bounded
:class:`~raes_env_packs.validation.ValidationResult` instead.

The consumer lane denies SDL imports exactly as :func:`validate_pack` does.
Static validity is not trial admission; compile a returned experiment with
trusted apparatus context through :meth:`PackExperiment.compilation_request`
and the RAES trial compiler.
"""

from __future__ import annotations

import os

from ._experiment_set import PackExperiment
from .validation import PackValidationLimits, ValidationResult, _validate_pack_snapshot


class PackExperimentError(ValueError):
    """The pack failed static validation, so no experiment was admitted."""

    def __init__(self, result: ValidationResult) -> None:
        super().__init__("pack failed static validation")
        self.result = result


def load_pack_experiments(
    pack_root: str | os.PathLike[str],
    *,
    limits: PackValidationLimits | None = None,
) -> tuple[PackExperiment, ...]:
    """Return every admitted experiment in one statically valid pack.

    The result is ordered by authoring-input path. A pack without an
    ``experiments/`` directory returns an empty tuple.
    """

    result, snapshot = _validate_pack_snapshot(pack_root, limits=limits)
    if not result.ok:
        raise PackExperimentError(result)
    return snapshot.experiments


__all__ = ["PackExperiment", "PackExperimentError", "load_pack_experiments"]
