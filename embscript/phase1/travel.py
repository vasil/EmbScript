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


def enforce_max_step(
    polyline: Polyline,
    max_step_px: float,
    union_mask: np.ndarray | None = None,
) -> Polyline:
    """Replace any segment longer than max_step_px with a path-through-mask + resample.

    If union_mask is given and a path through it exists, the replacement follows the
    mask. Otherwise (or if no path is found), the long segment is straight-line
    subdivided into <= max_step_px pieces.
    """
    if len(polyline) < 2 or max_step_px <= 0:
        return list(polyline)

    out: Polyline = [polyline[0]]
    for i in range(1, len(polyline)):
        x0, y0 = out[-1]
        x1, y1 = polyline[i]
        if math.hypot(x1 - x0, y1 - y0) <= max_step_px:
            out.append((x1, y1))
            continue

        path = None
        if union_mask is not None:
            path = bfs_path(union_mask, (x0, y0), (x1, y1))

        if path is None:
            out.extend(_straight_subdivide((x0, y0), (x1, y1), max_step_px))
            continue

        resampled = resample_path(path, max_step_px)
        for pt in resampled[1:]:
            out.append(pt)
    return out
