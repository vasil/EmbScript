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
        unlimited: bool = False,
        **_: object,
    ) -> list[Polyline]:
        if not mask.any():
            return []
        if not unlimited and target_stitches <= 0:
            return []

        rng = rng if rng is not None else np.random.default_rng()
        H, W = mask.shape

        mask_area = float(mask.sum())
        spacing_target = target_stitches if target_stitches > 0 else int(mask_area / 4)
        base_step = max(1.0, float(np.sqrt(mask_area / max(spacing_target, 1))))
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
        d_probs = (flat_d / flat_d.sum()) if flat_d.sum() > 0 else None

        def pick_seed() -> tuple[float, float] | None:
            if d_probs is not None:
                last: tuple[float, float] | None = None
                for _ in range(50):
                    idx = int(rng.choice(flat_d.size, p=d_probs))
                    sx = (idx % W) + 0.5
                    sy = (idx // W) + 0.5
                    last = (sx, sy)
                    if is_clear(sx, sy):
                        return (sx, sy)
                return last
            ys, xs = np.where(mask)
            if xs.size == 0:
                return None
            i = int(rng.integers(0, xs.size))
            return (float(xs[i]) + 0.5, float(ys[i]) + 0.5)

        seed = pick_seed()
        if seed is None:
            return []
        x, y = seed

        segments: list[Polyline] = []
        current: Polyline = [(x, y)]
        add_point(x, y)

        if unlimited:
            sat_radius_sq = max(min_dist, base_step * 0.5) ** 2
            saturation = max(target_stitches, int(mask_area / (sat_radius_sq * 3.14159 / 4)))
            total_cap = min(200_000, int(saturation * 1.5))
        else:
            total_cap = target_stitches
        consecutive_jump_failures = 0
        max_consecutive_failures = 8

        def total_stitches() -> int:
            return sum(len(s) for s in segments) + len(current)

        while total_stitches() < total_cap:
            local_d = density_at(x, y)
            step = base_step * (1.5 - local_d)
            angles = rng.uniform(0.0, 2.0 * np.pi, N_CANDIDATE_DIRECTIONS)

            best: tuple[float, float] | None = None
            best_density = -1.0

            for angle in angles:
                nx = x + step * float(np.cos(angle))
                ny = y + step * float(np.sin(angle))
                if not inside(nx, ny):
                    continue
                if not is_clear(nx, ny):
                    continue
                nd = density_at(nx, ny)
                if nd > best_density:
                    best_density = nd
                    best = (nx, ny)

            if best is None:
                if current:
                    segments.append(current)
                current = []
                new_seed = pick_seed()
                if new_seed is None:
                    break
                nsx, nsy = new_seed
                if not is_clear(nsx, nsy):
                    consecutive_jump_failures += 1
                    if consecutive_jump_failures >= max_consecutive_failures:
                        break
                    continue
                consecutive_jump_failures = 0
                x, y = nsx, nsy
                current = [(x, y)]
                add_point(x, y)
                continue

            consecutive_jump_failures = 0
            x, y = best
            current.append((x, y))
            add_point(x, y)

        if current:
            segments.append(current)
        return [s for s in segments if s]
