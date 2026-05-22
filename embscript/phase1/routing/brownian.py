"""Stochastic self-avoiding walk routing method."""

from __future__ import annotations

import numpy as np

Polyline = list[tuple[float, float]]


class BrownianWalk:
    """Density-weighted random walk constrained to the mask.

    Self-avoidance is enforced via a spatial hash; the min-distance threshold
    derives from `overlap_tolerance` (0 = strict avoid, 1 = unrestricted).
    Step length is modulated by local density so darker regions get more stitches.
    """

    def route(
        self,
        mask: np.ndarray,
        density: np.ndarray,
        target_stitches: int,
        *,
        overlap_tolerance: float = 0.0,
        **_: object,
    ) -> Polyline:
        raise NotImplementedError
