"""Orthogonal masonry-fill routing method."""

from __future__ import annotations

import numpy as np

from embscript.phase1.stitch_budget import TARGET_TOLERANCE, within_tolerance

Polyline = list[tuple[float, float]]

MAX_PITCH_ITERATIONS = 8
PITCH_MIN = 0.5


class BrickFill:
    """Serpentine horizontal-strip fill with alternating row offsets.

    Row pitch is binary-searched to land the realised stitch count within
    `TARGET_TOLERANCE` of `target_stitches`. Within-row stride is density-modulated
    so darker regions get closer stitches.
    """

    def route(
        self,
        mask: np.ndarray,
        density: np.ndarray,
        target_stitches: int,
        *,
        row_pitch_px: float | None = None,
        stitch_length_px: float | None = None,
        **_: object,
    ) -> list[Polyline]:
        if not mask.any():
            return []

        H, W = mask.shape
        ys, xs = np.where(mask)
        y_min, y_max = int(ys.min()), int(ys.max())
        x_min, x_max = int(xs.min()), int(xs.max())
        mask_area = float(mask.sum())

        if row_pitch_px is not None:
            row_pitch = max(PITCH_MIN, float(row_pitch_px))
            stitch_length = max(PITCH_MIN, float(stitch_length_px) if stitch_length_px else row_pitch)
            polyline = self._fill_pass(
                mask, density, row_pitch, stitch_length, W, H, x_min, x_max, y_min, y_max
            )
            return [polyline] if polyline else []

        if target_stitches <= 0:
            return []

        pitch = max(PITCH_MIN, float(np.sqrt(mask_area / target_stitches)))
        pitch_lo = PITCH_MIN
        pitch_hi = max(pitch * 4.0, float(max(y_max - y_min, x_max - x_min)))

        best: Polyline = []
        best_err = float("inf")

        for _ in range(MAX_PITCH_ITERATIONS):
            polyline = self._fill_pass(mask, density, pitch, pitch, W, H, x_min, x_max, y_min, y_max)
            err = abs(len(polyline) - target_stitches)
            if err < best_err:
                best_err = err
                best = polyline
            if within_tolerance(len(polyline), target_stitches, TARGET_TOLERANCE):
                return [polyline] if polyline else []
            if len(polyline) > target_stitches:
                pitch_lo = pitch
            else:
                pitch_hi = pitch
            pitch = (pitch_lo + pitch_hi) / 2.0

        return [best] if best else []

    @staticmethod
    def _fill_pass(
        mask: np.ndarray,
        density: np.ndarray,
        row_pitch: float,
        stitch_length: float,
        W: int,
        H: int,
        x_min: int,
        x_max: int,
        y_min: int,
        y_max: int,
    ) -> Polyline:
        polyline: Polyline = []
        y = y_min + 0.5
        row = 0
        direction = 1

        while y <= y_max + 0.5:
            offset = (row % 2) * (row_pitch / 2.0)
            if direction == 1:
                x = x_min + offset + 0.5
            else:
                x = x_max - offset + 0.5

            while (direction == 1 and x <= x_max + 0.5) or (
                direction == -1 and x >= x_min - 0.5
            ):
                ix, iy = int(x), int(y)
                if 0 <= ix < W and 0 <= iy < H and mask[iy, ix]:
                    polyline.append((x, y))
                cx = min(W - 1, max(0, ix))
                cy = min(H - 1, max(0, iy))
                stride = stitch_length * (1.5 - float(density[cy, cx]))
                if stride < PITCH_MIN:
                    stride = PITCH_MIN
                x += direction * stride

            y += row_pitch
            row += 1
            direction *= -1

        return polyline
