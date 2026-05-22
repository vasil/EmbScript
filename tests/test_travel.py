from __future__ import annotations

import math

import numpy as np

from embscript.phase1.travel import bfs_path, enforce_max_step, resample_path


def test_bfs_path_connects_disconnected_regions_via_bridge():
    mask = np.zeros((10, 30), dtype=bool)
    mask[2:8, 0:8] = True
    mask[2:8, 22:30] = True
    mask[4:6, 8:22] = True
    path = bfs_path(mask, (3, 5), (26, 5))
    assert path is not None
    assert path[0] == (3.5, 5.5)
    assert path[-1] == (26.5, 5.5)
    for x, y in path:
        ix, iy = int(x), int(y)
        assert mask[iy, ix], f"({x}, {y}) outside union mask"


def test_bfs_path_returns_none_when_unreachable():
    mask = np.zeros((10, 30), dtype=bool)
    mask[2:8, 0:8] = True
    mask[2:8, 22:30] = True
    assert bfs_path(mask, (3, 5), (26, 5)) is None


def test_resample_keeps_endpoints_and_spaces_intermediates():
    path = [(float(i), 0.0) for i in range(11)]
    sampled = resample_path(path, max_step=3.0)
    assert sampled[0] == (0.0, 0.0)
    assert sampled[-1] == (10.0, 0.0)
    for a, b in zip(sampled, sampled[1:]):
        assert math.hypot(b[0] - a[0], b[1] - a[1]) <= 4.0


def test_enforce_max_step_subdivides_straight_line():
    poly = [(0.0, 0.0), (10.0, 0.0)]
    out = enforce_max_step(poly, max_step_px=3.0, union_mask=None)
    for a, b in zip(out, out[1:]):
        assert math.hypot(b[0] - a[0], b[1] - a[1]) <= 3.0 + 1e-6
    assert out[0] == (0.0, 0.0) and out[-1] == (10.0, 0.0)


def test_enforce_max_step_routes_through_union_mask():
    mask = np.zeros((10, 30), dtype=bool)
    mask[2:8, 0:8] = True
    mask[2:8, 22:30] = True
    mask[4:6, 8:22] = True
    poly = [(3.5, 5.5), (26.5, 5.5)]
    out = enforce_max_step(poly, max_step_px=3.0, union_mask=mask)
    assert len(out) > 2  # subdivided
    for x, y in out:
        ix, iy = int(x), int(y)
        assert mask[iy, ix], f"travel stitch at ({x}, {y}) left the union mask"


def test_enforce_max_step_keeps_short_segments_unchanged():
    poly = [(0.0, 0.0), (1.0, 0.0), (2.0, 0.0)]
    out = enforce_max_step(poly, max_step_px=3.0, union_mask=None)
    assert out == poly
