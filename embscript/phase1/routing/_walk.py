"""Shared walk infrastructure for chaotic routing methods.

Provides density-weighted seed picking, self-avoidance via spatial hash, and
jump-on-stuck termination. The caller supplies a `sample_angle` function that
returns one candidate angle given the current position and an attempt index.
"""

from __future__ import annotations

import math
from typing import Callable

import numpy as np

Polyline = list[tuple[float, float]]

N_CANDIDATE_DIRECTIONS = 32


def field_walk(
    mask: np.ndarray,
    density: np.ndarray,
    target_stitches: int,
    sample_angle: Callable[[float, float, int, np.random.Generator], float],
    *,
    overlap_tolerance: float = 0.0,
    rng: np.random.Generator | None = None,
    unlimited: bool = False,
    step_length: Callable[[float, float, np.random.Generator], float] | None = None,
) -> list[Polyline]:
    """Generic chaotic walk.

    `sample_angle(x, y, attempt, rng)` returns a candidate step direction in
    radians. Called up to N_CANDIDATE_DIRECTIONS times per step until a candidate
    falls inside the mask and clears the spatial hash.
    `step_length(x, y, rng)` controls per-step distance; defaults to density-
    modulated base_step.
    """
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

    def default_step(x: float, y: float, _rng: np.random.Generator) -> float:
        return base_step * (1.5 - density_at(x, y))

    step_fn = step_length or default_step

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

    polyline: Polyline = [(x, y)]
    add_point(x, y)

    if unlimited:
        sat_radius_sq = max(min_dist, base_step * 0.5) ** 2
        saturation = max(target_stitches, int(mask_area / (sat_radius_sq * 3.14159 / 4)))
        total_cap = min(200_000, int(saturation * 1.5))
    else:
        total_cap = target_stitches
    consecutive_jump_failures = 0
    max_consecutive_failures = 8

    while len(polyline) < total_cap:
        step = step_fn(x, y, rng)

        best: tuple[float, float] | None = None
        for attempt in range(N_CANDIDATE_DIRECTIONS):
            angle = sample_angle(x, y, attempt, rng)
            nx = x + step * math.cos(angle)
            ny = y + step * math.sin(angle)
            if not inside(nx, ny):
                continue
            if not is_clear(nx, ny):
                continue
            best = (nx, ny)
            break

        if best is None:
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
            polyline.append((x, y))
            add_point(x, y)
            continue

        consecutive_jump_failures = 0
        x, y = best
        polyline.append((x, y))
        add_point(x, y)

    return [polyline] if polyline else []
