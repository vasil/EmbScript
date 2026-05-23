from __future__ import annotations

import numpy as np

from embscript.phase1.routing.perlin import PerlinFlow


def test_perlin_flow_returns_single_polyline_near_target():
    mask = np.ones((40, 40), dtype=bool)
    density = np.full((40, 40), 0.5, dtype=np.float32)
    segments = PerlinFlow().route(
        mask, density, target_stitches=300, overlap_tolerance=0.5,
        rng=np.random.default_rng(0),
    )
    assert len(segments) == 1
    total = len(segments[0])
    assert 250 <= total <= 300


def test_perlin_flow_returns_empty_for_empty_mask():
    mask = np.zeros((16, 16), dtype=bool)
    density = np.zeros((16, 16), dtype=np.float32)
    assert PerlinFlow().route(mask, density, target_stitches=100, rng=np.random.default_rng(0)) == []


def test_perlin_flow_stays_inside_mask():
    mask = np.zeros((40, 40), dtype=bool)
    mask[10:30, 10:30] = True
    density = mask.astype(np.float32) * 0.8
    segments = PerlinFlow().route(
        mask, density, target_stitches=150, overlap_tolerance=0.6,
        rng=np.random.default_rng(1),
    )
    for segment in segments:
        for x, y in segment:
            ix, iy = int(x), int(y)
            assert mask[iy, ix], f"({x}, {y}) outside the mask"
