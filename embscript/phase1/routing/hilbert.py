"""Hilbert space-filling curve routing.

Generates a Hilbert curve covering the mask bounding box, filters to points
inside the mask, then walks that ordered list. Deterministic, no overlap,
perfectly uniform coverage in a fractal pattern.
"""

from __future__ import annotations

import numpy as np

Polyline = list[tuple[float, float]]


def _hilbert_d2xy(order: int, d: int) -> tuple[int, int]:
    """Convert distance along a Hilbert curve of given order to (x, y)."""
    x = y = 0
    t = d
    s = 1
    n = 1 << order
    while s < n:
        rx = 1 & (t // 2)
        ry = 1 & (t ^ rx)
        if ry == 0:
            if rx == 1:
                x = s - 1 - x
                y = s - 1 - y
            x, y = y, x
        x += s * rx
        y += s * ry
        t //= 4
        s *= 2
    return x, y


class HilbertCurve:
    def route(
        self,
        mask: np.ndarray,
        density: np.ndarray,
        target_stitches: int,
        **_: object,
    ) -> list[Polyline]:
        if not mask.any() or target_stitches <= 0:
            return []

        H, W = mask.shape
        ys, xs = np.where(mask)
        y_min, y_max = int(ys.min()), int(ys.max())
        x_min, x_max = int(xs.min()), int(xs.max())
        bbox_w = x_max - x_min + 1
        bbox_h = y_max - y_min + 1

        # Order = log2(N) where N x N grid gives ~target_stitches when filtered.
        # Aim for ~target_stitches/coverage points inside the mask.
        coverage = float(mask.sum()) / float(bbox_w * bbox_h)
        n_needed = int(target_stitches / max(coverage, 1e-3))
        order = max(2, int(np.ceil(np.log2(np.sqrt(n_needed)))))
        n = 1 << order
        scale_x = bbox_w / n
        scale_y = bbox_h / n

        polyline: Polyline = []
        for d in range(n * n):
            gx, gy = _hilbert_d2xy(order, d)
            px = x_min + gx * scale_x + 0.5
            py = y_min + gy * scale_y + 0.5
            ix, iy = int(px), int(py)
            if 0 <= ix < W and 0 <= iy < H and mask[iy, ix]:
                polyline.append((px, py))
                if len(polyline) >= target_stitches:
                    break

        return [polyline] if polyline else []
