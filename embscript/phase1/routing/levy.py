"""Lévy flight: random walk with heavy-tailed step lengths.

Most steps are short (clustering), with rare long jumps that connect clusters.
Naturalistic exploration pattern (animal foraging, financial walks).
"""

from __future__ import annotations

import math

import numpy as np

from embscript.phase1.routing._walk import Polyline, field_walk


class LevyFlight:
    def route(
        self,
        mask: np.ndarray,
        density: np.ndarray,
        target_stitches: int,
        *,
        overlap_tolerance: float = 0.0,
        rng: np.random.Generator | None = None,
        unlimited: bool = False,
        alpha: float = 1.5,
        **_: object,
    ) -> list[Polyline]:
        # Direction: uniform random, fresh each attempt.
        def sample_angle(x, y, attempt, rng):
            return float(rng.uniform(-math.pi, math.pi))

        # Step length: Lévy-like via inverse-CDF transform.
        mask_area = float(mask.sum())
        spacing_target = target_stitches if target_stitches > 0 else int(mask_area / 4)
        base = max(1.0, float(np.sqrt(mask_area / max(spacing_target, 1))))
        max_step = base * 8.0  # cap so we don't shoot off the canvas

        def levy_step(x, y, rng):
            u = float(rng.uniform(1e-3, 1.0))
            l = base * (u ** (-1.0 / alpha))
            return min(l, max_step)

        return field_walk(
            mask, density, target_stitches,
            sample_angle,
            overlap_tolerance=overlap_tolerance,
            rng=rng,
            unlimited=unlimited,
            step_length=levy_step,
        )
