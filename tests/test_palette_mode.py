from __future__ import annotations

import re

import numpy as np
from PIL import Image

from embscript.cli.raster_to_svg import main as raster_main


def _three_block_image(tmp_path):
    img = np.zeros((30, 90, 3), dtype=np.uint8)
    img[:, :30] = (200, 30, 30)   # red
    img[:, 30:60] = (30, 200, 30)  # green
    img[:, 60:90] = (30, 30, 200)  # blue
    p = tmp_path / "blocks.png"
    Image.fromarray(img).save(p)
    return p


def test_palette_mode_emits_each_detected_color(tmp_path):
    src = _three_block_image(tmp_path)
    out = tmp_path / "palette.svg"
    rc = raster_main(
        [
            "--image", str(src),
            "--stitches", "300",
            "--colors", "3",
            "--separation", "palette",
            "--method", "brownian",
            "--max-stitch-mm", "0",
            "--width", "60",
            "--seed", "0",
            "--output", str(out),
        ]
    )
    assert rc == 0
    text = out.read_text()
    strokes = set(re.findall(r'stroke="(#[0-9a-f]{6})"', text))
    # 3 distinct stroke colors — the detected RGB palette of the source blocks.
    assert len(strokes) == 3
    # Each detected color should be dominant in one channel (red/green/blue blocks).
    channel_winners = []
    for hexcolor in strokes:
        r, g, b = int(hexcolor[1:3], 16), int(hexcolor[3:5], 16), int(hexcolor[5:7], 16)
        channel_winners.append(max(range(3), key=lambda i: (r, g, b)[i]))
    assert set(channel_winners) == {0, 1, 2}
