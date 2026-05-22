"""Travel-path planning: BFS through the union mask + subdivision to a max stitch length."""

from __future__ import annotations

import math
from collections import deque

import numpy as np

Polyline = list[tuple[float, float]]

_NEIGHBOURS = (
    (-1, 0), (1, 0), (0, -1), (0, 1),
    (-1, -1), (-1, 1), (1, -1), (1, 1),
)


def bfs_path(union_mask: np.ndarray, start_xy: tuple[float, float], end_xy: tuple[float, float]) -> Polyline | None:
    """Shortest 8-connected path through union_mask from start to end, in pixel space.

    Returns a list of (x, y) cell-centre points along the path, or None if unreachable.
    """
    H, W = union_mask.shape
    sx, sy = int(start_xy[0]), int(start_xy[1])
    ex, ey = int(end_xy[0]), int(end_xy[1])

    if not (0 <= sx < W and 0 <= sy < H and union_mask[sy, sx]):
        return None
    if not (0 <= ex < W and 0 <= ey < H and union_mask[ey, ex]):
        return None
    if (sx, sy) == (ex, ey):
        return [(sx + 0.5, sy + 0.5)]

    visited = np.zeros((H, W), dtype=bool)
    parent: dict[tuple[int, int], tuple[int, int]] = {}
    queue: deque[tuple[int, int]] = deque()
    queue.append((sx, sy))
    visited[sy, sx] = True

    found = False
    while queue:
        cx, cy = queue.popleft()
        if (cx, cy) == (ex, ey):
            found = True
            break
        for dx, dy in _NEIGHBOURS:
            nx, ny = cx + dx, cy + dy
            if 0 <= nx < W and 0 <= ny < H and union_mask[ny, nx] and not visited[ny, nx]:
                visited[ny, nx] = True
                parent[(nx, ny)] = (cx, cy)
                queue.append((nx, ny))

    if not found:
        return None

    rev: list[tuple[int, int]] = [(ex, ey)]
    cur = (ex, ey)
    while cur != (sx, sy):
        cur = parent[cur]
        rev.append(cur)
    rev.reverse()
    return [(x + 0.5, y + 0.5) for x, y in rev]


def resample_path(path: Polyline, max_step: float) -> Polyline:
    """Walk along path, emitting a point every ~max_step along arc length.

    Keeps the first and last points; intermediate points are inserted at roughly even
    spacing. Consecutive output points are guaranteed to be within max_step of each
    other along straight lines (since arc length ≥ straight-line distance).
    """
    if len(path) < 2 or max_step <= 0:
        return list(path)

    out: Polyline = [path[0]]
    accumulated = 0.0
    last_x, last_y = path[0]
    for i in range(1, len(path)):
        x, y = path[i]
        seg = math.hypot(x - last_x, y - last_y)
        accumulated += seg
        if accumulated >= max_step:
            out.append((x, y))
            accumulated = 0.0
        last_x, last_y = x, y
    if out[-1] != path[-1]:
        out.append(path[-1])
    return out


def _straight_subdivide(p0: tuple[float, float], p1: tuple[float, float], max_step: float) -> Polyline:
    x0, y0 = p0
    x1, y1 = p1
    dist = math.hypot(x1 - x0, y1 - y0)
    if dist <= max_step:
        return [(x1, y1)]
    n = max(1, math.ceil(dist / max_step))
    return [(x0 + (x1 - x0) * (j / n), y0 + (y1 - y0) * (j / n)) for j in range(1, n + 1)]


def goal_walk(
    union_mask: np.ndarray,
    start: tuple[float, float],
    end: tuple[float, float],
    max_step: float,
    rng: np.random.Generator,
    chaos: float = 0.7,
    max_iters: int = 2000,
    candidates: int = 32,
) -> Polyline | None:
    """Goal-directed random walk through union_mask from start to end.

    Each step samples a direction from a Gaussian centred on the bearing to the
    goal, with std scaling with `chaos` (0 = straight to goal, 1 ~= unbiased).
    Returns the full polyline including start and end, or None if stuck.
    """
    H, W = union_mask.shape
    sx, sy = float(start[0]), float(start[1])
    ex, ey = float(end[0]), float(end[1])

    if not (0 <= int(ex) < W and 0 <= int(ey) < H and union_mask[int(ey), int(ex)]):
        return None

    out: Polyline = [(sx, sy)]
    x, y = sx, sy
    std = max(0.05, chaos) * (math.pi / 2)

    for _ in range(max_iters):
        dx = ex - x
        dy = ey - y
        dist = math.hypot(dx, dy)
        if dist <= max_step:
            out.append((ex, ey))
            return out

        goal_angle = math.atan2(dy, dx)
        # Squeeze the noise as we approach the goal so the path actually lands.
        local_std = std * min(1.0, dist / (4.0 * max_step))

        moved = False
        for _ in range(candidates):
            angle = goal_angle + float(rng.normal(0.0, local_std))
            nx = x + max_step * math.cos(angle)
            ny = y + max_step * math.sin(angle)
            ix, iy = int(nx), int(ny)
            if 0 <= ix < W and 0 <= iy < H and union_mask[iy, ix]:
                x, y = nx, ny
                out.append((x, y))
                moved = True
                break
        if not moved:
            return None

    return None


def enforce_max_step(
    polyline: Polyline,
    max_step_px: float,
    union_mask: np.ndarray | None = None,
    rng: np.random.Generator | None = None,
    chaos: float = 0.7,
) -> Polyline:
    """Replace any segment longer than max_step_px so consecutive points are <= max_step_px.

    For each oversized segment:
      1. If union_mask given, try a chaotic goal_walk through the mask.
      2. If that fails, try the deterministic BFS path + resample.
      3. As a last resort, straight-line subdivision.
    """
    if len(polyline) < 2 or max_step_px <= 0:
        return list(polyline)

    walker_rng = rng if rng is not None else np.random.default_rng()
    out: Polyline = [polyline[0]]
    for i in range(1, len(polyline)):
        x0, y0 = out[-1]
        x1, y1 = polyline[i]
        if math.hypot(x1 - x0, y1 - y0) <= max_step_px:
            out.append((x1, y1))
            continue

        path: Polyline | None = None
        if union_mask is not None:
            path = goal_walk(union_mask, (x0, y0), (x1, y1), max_step_px, walker_rng, chaos)
            if path is None:
                bfs = bfs_path(union_mask, (x0, y0), (x1, y1))
                if bfs is not None:
                    path = resample_path(bfs, max_step_px)

        if path is None:
            out.extend(_straight_subdivide((x0, y0), (x1, y1), max_step_px))
            continue

        for pt in path[1:]:
            out.append(pt)
    return out
