"""Stochastic self-avoiding walk routing method."""

from __future__ import annotations

import numpy as np

Polyline = list[tuple[float, float]]

N_CANDIDATE_DIRECTIONS = 32


class BrownianWalk:
    """Density-weighted random walk constrained to the mask.

    Coordinates returned are in pixel space; the CLI scales them to millimetres
    before handing off to the SVG writer.
    """

    def route(
        self,
        mask: np.ndarray,
        density: np.ndarray,
        target_stitches: int,
        *,
        overlap_tolerance: float = 0.0,
        rng: np.random.Generator | None = None,
        **_: object,
    ) -> Polyline:
        if target_stitches <= 0 or not mask.any():
            return []

        rng = rng if rng is not None else np.random.default_rng()
        H, W = mask.shape

        mask_area = float(mask.sum())
        base_step = max(1.0, float(np.sqrt(mask_area / target_stitches)))
        min_dist = base_step * 0.7 * (1.0 - float(overlap_tolerance))
        check_self_avoid = min_dist > 0.0
        cell_size = min_dist if check_self_avoid else base_step

        spatial_hash: dict[tuple[int, int], list[tuple[float, float]]] = {}

        def cell_key(x: float, y: float) -> tuple[int, int]:
            return (int(x / cell_size), int(y / cell_size))

        def add_point(x: float, y: float) -> None:
            spatial_hash.setdefault(cell_key(x, y), []).append((x, y))

        def is_clear(x: float, y: float) -> bool:
            if not check_self_avoid:
                return True
            cx, cy = cell_key(x, y)
            min_d2 = min_dist * min_dist
            for dx in (-1, 0, 1):
                for dy in (-1, 0, 1):
                    for px, py in spatial_hash.get((cx + dx, cy + dy), ()):
                        if (px - x) ** 2 + (py - y) ** 2 < min_d2:
                            return False
            return True

        def inside(x: float, y: float) -> bool:
            ix, iy = int(x), int(y)
            return 0 <= ix < W and 0 <= iy < H and bool(mask[iy, ix])

        def density_at(x: float, y: float) -> float:
            ix = min(W - 1, max(0, int(x)))
            iy = min(H - 1, max(0, int(y)))
            return float(density[iy, ix])

        flat_d = density.flatten()
        if flat_d.sum() > 0:
            idx = int(rng.choice(flat_d.size, p=flat_d / flat_d.sum()))
        else:
            ys, xs = np.where(mask)
            i = int(rng.integers(0, xs.size))
            idx = int(ys[i]) * W + int(xs[i])
        x = (idx % W) + 0.5
        y = (idx // W) + 0.5

        polyline: Polyline = [(x, y)]
        add_point(x, y)

        while len(polyline) < target_stitches:
            local_d = density_at(x, y)
            step = base_step * (1.5 - local_d)
            angles = rng.uniform(0.0, 2.0 * np.pi, N_CANDIDATE_DIRECTIONS)

            best: tuple[float, float] | None = None
            best_density = -1.0
            fallback: tuple[float, float] | None = None

            for angle in angles:
                nx = x + step * float(np.cos(angle))
                ny = y + step * float(np.sin(angle))
                if not inside(nx, ny):
                    continue
                if fallback is None:
                    fallback = (nx, ny)
                if not is_clear(nx, ny):
                    continue
                nd = density_at(nx, ny)
                if nd > best_density:
                    best_density = nd
                    best = (nx, ny)

            chosen = best if best is not None else fallback
            if chosen is None:
                break

            x, y = chosen
            polyline.append((x, y))
            add_point(x, y)

        return polyline
