"""Orthogonal masonry-fill routing method."""

from __future__ import annotations

import numpy as np

Polyline = list[tuple[float, float]]


class BrickFill:
    """Serpentine horizontal-strip fill with alternating row offsets.

    Row pitch and within-row stitch pitch are derived from the density field.
    Rows are joined by short verticals so the resulting polyline is continuous.
    """

    def route(
        self,
        mask: np.ndarray,
        density: np.ndarray,
        target_stitches: int,
        **_: object,
    ) -> Polyline:
        raise NotImplementedError
