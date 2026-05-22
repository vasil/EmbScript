from __future__ import annotations

import numpy as np
from PIL import Image

from embscript.cli.raster_to_svg import main as raster_main
from embscript.phase1.color_separation import separate
from embscript.phase1.density_map import density_for_layer
from embscript.phase1.routing.brownian import BrownianWalk
from embscript.phase1.stitch_budget import allocate


def _two_color_image(size: int = 32) -> np.ndarray:
    img = np.zeros((size, size, 3), dtype=np.uint8)
    img[:, : size // 2] = (50, 50, 50)
    img[:, size // 2 :] = (200, 200, 200)
    return img


def test_color_separation_finds_two_clusters():
    img = _two_color_image()
    masks, palette = separate(img, 2)
    assert masks.shape == (2, 32, 32)
    assert masks.sum() == 32 * 32
    assert (~(masks[0] & masks[1])).all()


def test_density_zero_outside_mask():
    img = np.full((4, 4, 3), 100, dtype=np.uint8)
    mask = np.zeros((4, 4), dtype=bool)
    mask[1, 1] = True
    d = density_for_layer(img, mask)
    assert d[0, 0] == 0.0
    assert d[1, 1] > 0.0


def test_density_proportional_to_darkness():
    dark = np.full((4, 4, 3), 30, dtype=np.uint8)
    light = np.full((4, 4, 3), 220, dtype=np.uint8)
    mask = np.ones((4, 4), dtype=bool)
    assert density_for_layer(dark, mask).sum() > density_for_layer(light, mask).sum()


def test_allocate_sums_to_total():
    d1 = np.ones((4, 4), dtype=np.float32)
    d2 = np.full((4, 4), 3.0, dtype=np.float32)
    counts = allocate([d1, d2], 1000)
    assert sum(counts) == 1000
    assert counts[1] > counts[0]


def test_allocate_empty_densities_returns_zeros():
    z = np.zeros((4, 4), dtype=np.float32)
    assert allocate([z, z], 1000) == [0, 0]


def test_brownian_hits_target_on_open_field():
    mask = np.ones((64, 64), dtype=bool)
    density = np.full((64, 64), 0.5, dtype=np.float32)
    walker = BrownianWalk()
    segments = walker.route(
        mask, density, target_stitches=500, overlap_tolerance=0.5, rng=np.random.default_rng(42)
    )
    total = sum(len(s) for s in segments)
    assert 450 <= total <= 500


def test_brownian_returns_empty_for_empty_mask():
    mask = np.zeros((16, 16), dtype=bool)
    density = np.zeros((16, 16), dtype=np.float32)
    segments = BrownianWalk().route(mask, density, target_stitches=100, rng=np.random.default_rng(0))
    assert segments == []


def test_brownian_stays_inside_mask():
    mask = np.zeros((32, 32), dtype=bool)
    mask[10:22, 10:22] = True
    density = mask.astype(np.float32) * 0.8
    segments = BrownianWalk().route(
        mask, density, target_stitches=100, overlap_tolerance=0.8, rng=np.random.default_rng(1)
    )
    for segment in segments:
        for x, y in segment:
            ix, iy = int(x), int(y)
            assert mask[iy, ix], f"point ({x}, {y}) is outside the mask"


def test_end_to_end_brownian(tmp_path):
    img_path = tmp_path / "two_color.png"
    Image.fromarray(_two_color_image()).save(img_path)
    out = tmp_path / "out.svg"

    rc = raster_main(
        [
            "--image", str(img_path),
            "--stitches", "200",
            "--colors", "2",
            "--method", "brownian",
            "--overlap-tolerance", "0.5",
            "--max-stitch-mm", "0",
            "--seed", "42",
            "--output", str(out),
        ]
    )
    assert rc == 0
    assert out.exists()
    content = out.read_text()
    assert 'id="layer-0"' in content
    assert 'id="layer-1"' in content
    assert "<polyline" in content
