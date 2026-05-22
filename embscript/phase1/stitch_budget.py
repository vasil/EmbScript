"""Stitch budget allocation and tolerance-bounded path refinement."""

from __future__ import annotations

import numpy as np

TARGET_TOLERANCE = 0.05  # ±5% of --stitches


def allocate(densities: list[np.ndarray], total_stitches: int) -> list[int]:
    """Allocate the total stitch budget across layers proportional to integrated density.

    Layers with zero integrated density get zero stitches. Rounding error is absorbed
    by the first non-empty layer so the sum exactly equals `total_stitches`.
    """
    integrated = np.array([float(d.sum()) for d in densities])
    n = len(densities)
    if n == 0 or integrated.sum() <= 0 or total_stitches <= 0:
        return [0] * n

    raw = integrated / integrated.sum() * total_stitches
    counts = [int(round(x)) for x in raw]

    diff = total_stitches - sum(counts)
    if diff != 0:
        for i, val in enumerate(integrated):
            if val > 0:
                counts[i] += diff
                break
    return counts


def within_tolerance(actual: int, target: int, tolerance: float = TARGET_TOLERANCE) -> bool:
    return abs(actual - target) <= int(round(target * tolerance))
