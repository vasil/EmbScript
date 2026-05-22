from __future__ import annotations

import numpy as np

from embscript.phase1.routing.brick import BrickFill
from embscript.phase1.stitch_budget import within_tolerance


def test_brick_hits_target_on_open_field():
    mask = np.ones((64, 64), dtype=bool)
    density = np.full((64, 64), 0.5, dtype=np.float32)
    segments = BrickFill().route(mask, density, target_stitches=500)
    assert len(segments) == 1
    assert within_tolerance(len(segments[0]), 500)


def test_brick_stays_inside_mask():
    mask = np.zeros((32, 32), dtype=bool)
    mask[8:24, 8:24] = True
    density = mask.astype(np.float32) * 0.5
    segments = BrickFill().route(mask, density, target_stitches=80)
    for segment in segments:
        for x, y in segment:
            ix, iy = int(x), int(y)
            assert mask[iy, ix], f"point ({x}, {y}) escaped the mask"


def test_brick_returns_empty_for_empty_mask():
    mask = np.zeros((16, 16), dtype=bool)
    density = np.zeros((16, 16), dtype=np.float32)
    assert BrickFill().route(mask, density, target_stitches=100) == []


def test_brick_alternates_row_direction():
    mask = np.ones((64, 64), dtype=bool)
    density = np.full((64, 64), 0.5, dtype=np.float32)
    segments = BrickFill().route(mask, density, target_stitches=300)
    assert len(segments) == 1
    poly = segments[0]

    rows: list[list[tuple[float, float]]] = []
    current = [poly[0]]
    for p in poly[1:]:
        if p[1] != current[-1][1]:
            rows.append(current)
            current = [p]
        else:
            current.append(p)
    rows.append(current)

    assert len(rows) >= 2
    long_rows = [r for r in rows if len(r) >= 2]
    assert len(long_rows) >= 2
    sign0 = long_rows[0][-1][0] - long_rows[0][0][0]
    sign1 = long_rows[1][-1][0] - long_rows[1][0][0]
    assert sign0 * sign1 < 0, "adjacent rows should walk in opposite x directions"
