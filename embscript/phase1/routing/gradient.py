"""Gradient-aligned flow: stitches follow image-edge contours.

Direction at each pixel = perpendicular to the local image gradient, so the
walker traces lines along edges (like a hatch shading the form of the subject).
"""

from __future__ import annotations

import math

import numpy as np
from scipy.ndimage import gaussian_filter, sobel

from embscript.phase1.routing._walk import Polyline, field_walk


class GradientFlow:
    def route(
        self,
        mask: np.ndarray,
        density: np.ndarray,
        target_stitches: int,
        *,
        overlap_tolerance: float = 0.0,
        rng: np.random.Generator | None = None,
        unlimited: bool = False,
        smooth_sigma: float = 2.0,
        chaos: float = 0.15,
        **_: object,
    ) -> list[Polyline]:
        smoothed = gaussian_filter(density.astype(np.float32), sigma=smooth_sigma)
        gx = sobel(smoothed, axis=1)
        gy = sobel(smoothed, axis=0)
        # Walk perpendicular to gradient (along contours).
        angle_field = np.arctan2(gx, -gy).astype(np.float32)
        H, W = mask.shape

        def sample_angle(x, y, attempt, rng):
            ix = min(W - 1, max(0, int(x)))
            iy = min(H - 1, max(0, int(y)))
            base = float(angle_field[iy, ix])
            sigma = chaos * math.pi * (1.0 + attempt / 8.0)
            if attempt < 24:
                return base + float(rng.normal(0.0, sigma))
            return base + math.pi + float(rng.normal(0.0, sigma))

        return field_walk(
            mask, density, target_stitches,
            sample_angle,
            overlap_tolerance=overlap_tolerance,
            rng=rng,
            unlimited=unlimited,
        )
