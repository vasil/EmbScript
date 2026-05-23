"""Regression: chaotic methods must seed every disconnected mask region.

The density-weighted seed picker used to ignore small disconnected pieces of
the mask (e.g. a camel's legs) because large regions dominated the probability
distribution. The fix tracks connected components and forces a seed in any
unvisited component before falling back to density-weighted picks.
"""

from __future__ import annotations

import numpy as np
import pytest

from embscript.phase1.routing import METHODS


def _two_blob_mask() -> tuple[np.ndarray, np.ndarray]:
    """A 60x60 mask with two disjoint blobs: a large body and a small leg."""
    mask = np.zeros((60, 60), dtype=bool)
    mask[5:45, 5:45] = True  # 40x40 body (1600 px)
    mask[50:58, 50:58] = True  # 8x8 leg (64 px), disconnected from body
    density = mask.astype(np.float32) * 0.7
    return mask, density


@pytest.mark.parametrize("method_name", ["levy", "gradient", "attractor", "perlin"])
def test_each_chaotic_method_covers_both_blobs(method_name):
    mask, density = _two_blob_mask()
    method = METHODS[method_name]()
    segments = method.route(
        mask,
        density,
        target_stitches=400,
        overlap_tolerance=0.5,
        rng=np.random.default_rng(0),
    )
    assert segments, f"{method_name} returned no segments"

    body_hits = 0
    leg_hits = 0
    for segment in segments:
        for x, y in segment:
            ix, iy = int(x), int(y)
            if 5 <= ix < 45 and 5 <= iy < 45:
                body_hits += 1
            elif 50 <= ix < 58 and 50 <= iy < 58:
                leg_hits += 1

    assert body_hits > 0, f"{method_name}: body blob has no stitches"
    assert leg_hits > 0, (
        f"{method_name}: detached leg blob has no stitches "
        f"(body={body_hits}, leg={leg_hits}) — coverage-aware seeding regressed"
    )
