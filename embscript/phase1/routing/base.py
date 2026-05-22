"""Routing method protocol."""

from __future__ import annotations

from typing import Protocol

import numpy as np

Polyline = list[tuple[float, float]]


class RoutingMethod(Protocol):
    """Generate a single continuous polyline for one color layer.

    Implementations must:
      - confine the path to the mask
      - modulate local stitch density by the density field
      - target the given stitch count within stitch_budget.TARGET_TOLERANCE
    """

    def route(
        self,
        mask: np.ndarray,
        density: np.ndarray,
        target_stitches: int,
        **options: object,
    ) -> Polyline: ...
