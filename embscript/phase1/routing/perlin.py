"""Perlin-style noise-flow routing method.

Each step samples a base direction from a smooth 2D noise field at the current
position, then perturbs it with Gaussian noise. Adjacent stitches tend to flow
in the same direction, giving brushed-stroke fills.
"""

from __future__ import annotations

import math

import numpy as np
from scipy.ndimage import zoom

from embscript.phase1.routing.base import Polyline

N_CANDIDATE_DIRECTIONS = 32


def _value_noise_field(
    shape: tuple[int, int],
    scale: int,
    octaves: int,
    rng: np.random.Generator,
) -> np.ndarray:
    """Multi-octave smooth value noise in approximately [-1, 1]."""
    H, W = shape
    field = np.zeros((H, W), dtype=np.float32)
    amplitude = 1.0
    norm = 0.0
    for o in range(octaves):
        s = max(2, scale // (2 ** o))
        gh = max(2, H // s + 2)
        gw = max(2, W // s + 2)
        grid = rng.uniform(-1.0, 1.0, (gh, gw)).astype(np.float32)
        layer = zoom(grid, (H / gh, W / gw), order=3)
        if layer.shape[0] < H or layer.shape[1] < W:
            pad_h = max(0, H - layer.shape[0])
            pad_w = max(0, W - layer.shape[1])
            layer = np.pad(layer, ((0, pad_h), (0, pad_w)), mode="edge")
        layer = layer[:H, :W]
        field += amplitude * layer
        norm += amplitude
        amplitude *= 0.5
    return field / max(norm, 1e-6)


class PerlinFlow:
    """Density-weighted self-avoiding walk that follows a Perlin-style noise field.

    Direction at each step is sampled from a smooth noise field, perturbed by
    Gaussian noise whose std grows when the walker is blocked. Step length and
    self-avoidance match BrownianWalk so the two methods are interchangeable
    behind the same CLI.
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
        noise_scale: int = 64,
        noise_octaves: int = 4,
        chaos: float = 0.2,
        **_: object,
    ) -> list[Polyline]:
        if not mask.any():
            return []
        if not unlimited and target_stitches <= 0:
            return []

        rng = rng if rng is not None else np.random.default_rng()
        H, W = mask.shape

        angle_field = _value_noise_field((H, W), scale=noise_scale, octaves=noise_octaves, rng=rng) * np.pi

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

        def angle_at(x: float, y: float) -> float:
            ix = min(W - 1, max(0, int(x)))
            iy = min(H - 1, max(0, int(y)))
            return float(angle_field[iy, ix])

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
            local_d = density_at(x, y)
            step = base_step * (1.5 - local_d)
            base_angle = angle_at(x, y)

            best: tuple[float, float] | None = None
            for attempt in range(N_CANDIDATE_DIRECTIONS):
                sigma = chaos * math.pi * (1.0 + attempt / 8.0)
                if attempt < N_CANDIDATE_DIRECTIONS - 4:
                    angle = base_angle + float(rng.normal(0.0, sigma))
                else:
                    angle = base_angle + math.pi + float(rng.normal(0.0, sigma))
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
