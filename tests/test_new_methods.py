from __future__ import annotations

import numpy as np
import pytest

from embscript.phase1.routing import METHODS


@pytest.mark.parametrize("method_name", ["levy", "gradient", "attractor", "hilbert"])
def test_method_stays_inside_mask(method_name):
    mask = np.zeros((40, 40), dtype=bool)
    mask[5:35, 5:35] = True
    density = mask.astype(np.float32) * 0.7
    method = METHODS[method_name]()
    segments = method.route(
        mask, density, target_stitches=300,
        overlap_tolerance=0.6, rng=np.random.default_rng(0),
    )
    for segment in segments:
        for x, y in segment:
            ix, iy = int(x), int(y)
            assert 0 <= ix < 40 and 0 <= iy < 40
            assert mask[iy, ix], f"{method_name}: ({x}, {y}) outside mask"


@pytest.mark.parametrize("method_name", ["levy", "gradient", "attractor", "hilbert"])
def test_method_returns_non_empty_polyline(method_name):
    mask = np.ones((40, 40), dtype=bool)
    density = np.full((40, 40), 0.5, dtype=np.float32)
    method = METHODS[method_name]()
    segments = method.route(
        mask, density, target_stitches=200,
        overlap_tolerance=0.5, rng=np.random.default_rng(0),
    )
    assert len(segments) == 1
    assert len(segments[0]) > 50
