"""Routing method protocol."""

from __future__ import annotations

from typing import Protocol

import numpy as np

Polyline = list[tuple[float, float]]


class RoutingMethod(Protocol):
    """Generate one or more continuous polyline segments for one color layer.

    Implementations must:
      - confine each segment to the mask
      - modulate local stitch density by the density field
      - target the given stitch count within stitch_budget.TARGET_TOLERANCE

    The returned list groups stitches into contiguous segments. When the mask is
    a single connected region, a single segment is returned. When the routing
    method needs to teleport (e.g. across disconnected regions), it returns
    multiple segments — the SVG writer keeps them as separate <polyline>s and
    the stitch writer inserts TRIM/JUMP between them.
    """

    def route(
        self,
        mask: np.ndarray,
        density: np.ndarray,
        target_stitches: int,
        **options: object,
    ) -> list[Polyline]: ...
