from __future__ import annotations

import numpy as np

from embscript.phase1.cmyk_separation import CMYK_PALETTE_RGB, cmyk_separate


def test_cmyk_palette_is_fixed():
    img = np.zeros((4, 4, 3), dtype=np.uint8)
    _, _, palette = cmyk_separate(img)
    assert (palette == CMYK_PALETTE_RGB).all()


def test_pure_cyan_pixel_lights_up_cyan_layer_only():
    img = np.full((2, 2, 3), 0, dtype=np.uint8)
    img[:, :] = (0, 255, 255)  # pure cyan
    masks, densities, _ = cmyk_separate(img)
    assert masks[0].all()  # C
    assert not masks[1].any()  # M
    assert not masks[2].any()  # Y
    assert not masks[3].any()  # K
    assert densities[0].mean() > 0.9


def test_black_pixel_lights_up_k_only():
    img = np.zeros((2, 2, 3), dtype=np.uint8)
    masks, densities, _ = cmyk_separate(img)
    assert not masks[0].any()
    assert not masks[1].any()
    assert not masks[2].any()
    assert masks[3].all()
    assert densities[3].mean() > 0.9


def test_white_pixel_no_layers_active():
    img = np.full((2, 2, 3), 255, dtype=np.uint8)
    masks, _, _ = cmyk_separate(img)
    for m in masks:
        assert not m.any()
