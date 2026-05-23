"""Shared walk infrastructure for chaotic routing methods.

Provides density-weighted seed picking, self-avoidance via spatial hash, and
jump-on-stuck termination. The caller supplies a `sample_angle` function that
returns one candidate angle given the current position and an attempt index.
"""

from __future__ import annotations

import math
from typing import Callable

import numpy as np
from scipy.ndimage import label as _label_components

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

    labels, num_components = _label_components(mask)
    labels = labels.astype(np.int32)
    if num_components > 0:
        component_sizes = np.bincount(labels.ravel(), minlength=num_components + 1)
        # Only track meaningful components for coverage. Stipple/halftone inputs
        # produce thousands of single-pixel components from k-means quantization;
        # those are noise, not features that deserve their own seed.
        largest_size = int(component_sizes[1:].max()) if num_components > 0 else 0
        min_scout_size = max(4, largest_size // 100)
        components_by_size = sorted(
            (c for c in range(1, num_components + 1) if component_sizes[c] >= min_scout_size),
            key=lambda c: int(component_sizes[c]),
            reverse=True,
        )
    else:
        components_by_size = []
    visited_components: set[int] = set()
    component_pixel_cache: dict[int, tuple[np.ndarray, np.ndarray]] = {}

    def cell_key(x: float, y: float) -> tuple[int, int]:
        return (int(x / cell_size), int(y / cell_size))

    def mark_visited(x: float, y: float) -> None:
        iy = min(H - 1, max(0, int(y)))
        ix = min(W - 1, max(0, int(x)))
        lbl = int(labels[iy, ix])
        if lbl > 0:
            visited_components.add(lbl)

    def add_point(x: float, y: float) -> None:
        spatial_hash.setdefault(cell_key(x, y), []).append((x, y))
        mark_visited(x, y)

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

    def component_pixels(c: int) -> tuple[np.ndarray, np.ndarray]:
        if c not in component_pixel_cache:
            ys_c, xs_c = np.where(labels == c)
            component_pixel_cache[c] = (xs_c, ys_c)
        return component_pixel_cache[c]

    def pick_seed() -> tuple[float, float] | None:
        # First: try to seed in any unvisited connected component (largest first).
        # This guarantees small disconnected pieces of the mask (legs, etc.) get
        # at least one seed even when density-weighting would always pick the
        # dominant region.
        for lbl in components_by_size:
            if lbl in visited_components:
                continue
            xs_c, ys_c = component_pixels(lbl)
            if xs_c.size == 0:
                visited_components.add(lbl)
                continue
            for _ in range(50):
                i = int(rng.integers(0, xs_c.size))
                sx = float(xs_c[i]) + 0.5
                sy = float(ys_c[i]) + 0.5
                if is_clear(sx, sy):
                    return (sx, sy)
            # No clearable spot in this component (already saturated) — treat it
            # as visited so we move on to the next unvisited component.
            visited_components.add(lbl)
        # Fallback: density-weighted picking (original behaviour).
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

    # Scout-seed any remaining disconnected components. Without this, a small
    # mask region (e.g. a camel's leg) never gets a stitch if the walker stays
    # inside the dominant component for the whole budget.
    for _ in range(len(components_by_size)):
        if len(visited_components) >= len(components_by_size):
            break
        extra = pick_seed()
        if extra is None:
            break
        polyline.append(extra)
        add_point(*extra)
    x, y = polyline[-1]

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
