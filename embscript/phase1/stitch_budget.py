"""Stitch budget allocation and tolerance-bounded path refinement."""

from __future__ import annotations

import numpy as np

TARGET_TOLERANCE = 0.05  # ±5% of --stitches


def allocate(densities: list[np.ndarray], total_stitches: int) -> list[int]:
    """Allocate the total stitch budget across layers proportional to integrated density."""
    raise NotImplementedError


def within_tolerance(actual: int, target: int, tolerance: float = TARGET_TOLERANCE) -> bool:
    return abs(actual - target) <= int(round(target * tolerance))
