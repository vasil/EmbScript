"""Strange-attractor flow: direction field driven by a De Jong chaotic map.

For each pixel in normalized [-2, 2]² coordinates:
    fx = sin(a * y) - cos(b * x)
    fy = sin(c * x) - cos(d * y)
The angle atan2(fy, fx) produces a chaotic but structured field: ribbons,
swirls, and spiral basins emerge from the map's parameters.
"""

from __future__ import annotations

import math

import numpy as np

from embscript.phase1.routing._walk import Polyline, field_walk


class StrangeAttractor:
    def route(
        self,
        mask: np.ndarray,
        density: np.ndarray,
        target_stitches: int,
        *,
        overlap_tolerance: float = 0.0,
        rng: np.random.Generator | None = None,
        unlimited: bool = False,
        a: float = -2.7,
        b: float = -0.09,
        c: float = -0.86,
        d: float = -2.2,
        chaos: float = 0.15,
        **_: object,
    ) -> list[Polyline]:
        H, W = mask.shape
        ys = (np.arange(H, dtype=np.float32) / H) * 4.0 - 2.0
        xs = (np.arange(W, dtype=np.float32) / W) * 4.0 - 2.0
        Y, X = np.meshgrid(ys, xs, indexing="ij")
        fx = np.sin(a * Y) - np.cos(b * X)
        fy = np.sin(c * X) - np.cos(d * Y)
        angle_field = np.arctan2(fy, fx).astype(np.float32)

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
