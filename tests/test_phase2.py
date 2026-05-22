from __future__ import annotations

import numpy as np
import pyembroidery
from PIL import Image

from embscript.cli.raster_to_svg import main as raster_main
from embscript.cli.svg_to_stitch import main as stitch_main
from embscript.phase1.svg_writer import write_svg
from embscript.phase2.stitch_writer import write_pattern
from embscript.phase2.svg_parser import parse_layers


def _two_color_image(size: int = 32) -> np.ndarray:
    img = np.zeros((size, size, 3), dtype=np.uint8)
    img[:, : size // 2] = (50, 50, 50)
    img[:, size // 2 :] = (200, 200, 200)
    return img


def test_svg_parser_round_trip(tmp_path):
    svg_path = tmp_path / "in.svg"
    layers_in = [
        ("#3c3c3c", [[(0.0, 0.0), (10.0, 10.0), (20.0, 5.0)]]),
        ("#c8c8c8", [[(5.0, 5.0), (15.0, 15.0)]]),
    ]
    write_svg(svg_path, 50.0, 50.0, layers_in)

    layers_out = parse_layers(svg_path)
    assert len(layers_out) == 2
    assert layers_out[0][0] == "#3c3c3c"
    assert layers_out[1][0] == "#c8c8c8"
    assert layers_out[0][1] == [[(0.0, 0.0), (10.0, 10.0), (20.0, 5.0)]]
    assert layers_out[1][1] == [[(5.0, 5.0), (15.0, 15.0)]]


def test_svg_parser_multi_segment_layer(tmp_path):
    svg_path = tmp_path / "multi.svg"
    layers_in = [
        ("#000000", [
            [(0.0, 0.0), (5.0, 5.0)],
            [(20.0, 20.0), (25.0, 25.0), (30.0, 20.0)],
        ]),
    ]
    write_svg(svg_path, 50.0, 50.0, layers_in)
    layers_out = parse_layers(svg_path)
    assert len(layers_out) == 1
    assert len(layers_out[0][1]) == 2


def test_svg_parser_handles_empty_layer(tmp_path):
    svg_path = tmp_path / "empty.svg"
    write_svg(svg_path, 50.0, 50.0, [("#000000", [])])
    layers = parse_layers(svg_path)
    assert layers == [("#000000", [])]


def test_write_pattern_dst_round_trips(tmp_path):
    out = tmp_path / "out.dst"
    layers = [
        ("#3c3c3c", [[(0.0, 0.0), (5.0, 0.0), (5.0, 5.0), (0.0, 5.0)]]),
        ("#c8c8c8", [[(10.0, 0.0), (15.0, 0.0), (15.0, 5.0)]]),
    ]
    write_pattern(out, layers, "dst")
    assert out.exists() and out.stat().st_size > 0

    pattern = pyembroidery.read_dst(str(out))
    assert pattern.count_color_changes() == 1
    total_points = sum(len(seg) for _, segs in layers for seg in segs)
    assert pattern.count_stitches() >= total_points


def test_write_pattern_inserts_trim_between_segments(tmp_path):
    out = tmp_path / "out.dst"
    layers = [
        ("#000000", [
            [(0.0, 0.0), (5.0, 0.0), (5.0, 5.0)],
            [(50.0, 0.0), (55.0, 0.0), (55.0, 5.0)],
        ]),
    ]
    write_pattern(out, layers, "dst")
    pattern = pyembroidery.read_dst(str(out))
    # Two segments within one color -> at least one trim.
    trims = sum(1 for s in pattern.stitches if s[2] == pyembroidery.TRIM)
    assert trims >= 1


def test_write_pattern_skips_empty_layers(tmp_path):
    out = tmp_path / "out.dst"
    layers = [
        ("#000000", []),
        ("#ff0000", [[(0.0, 0.0), (5.0, 0.0), (5.0, 5.0)]]),
    ]
    write_pattern(out, layers, "dst")
    pattern = pyembroidery.read_dst(str(out))
    assert pattern.count_color_changes() == 0


def test_end_to_end_pipeline(tmp_path):
    img_path = tmp_path / "two_color.png"
    Image.fromarray(_two_color_image()).save(img_path)
    svg_path = tmp_path / "design.svg"
    dst_path = tmp_path / "design.dst"

    rc1 = raster_main(
        [
            "--image", str(img_path),
            "--stitches", "200",
            "--colors", "2",
            "--method", "brownian",
            "--overlap-tolerance", "0.5",
            "--max-stitch-mm", "0",
            "--seed", "42",
            "--output", str(svg_path),
        ]
    )
    assert rc1 == 0
    rc2 = stitch_main(
        [
            "--svg", str(svg_path),
            "--format", "dst",
            "--output", str(dst_path),
        ]
    )
    assert rc2 == 0
    assert dst_path.exists() and dst_path.stat().st_size > 0

    pattern = pyembroidery.read_dst(str(dst_path))
    assert pattern.count_color_changes() == 1
    # Realised stitch count within ±5% of the target.
    realised = pattern.count_stitches()
    assert 190 <= realised <= 250  # generous upper to account for trims/jumps
