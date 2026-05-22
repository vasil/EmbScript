from __future__ import annotations

import re
from pathlib import Path

import numpy as np
import pytest
from PIL import Image

from embscript.cli.raster_to_svg import main as raster_main
from embscript.cli.svg_to_stitch import main as stitch_main
from embscript.phase1.stitch_budget import within_tolerance

PERL_IMAGE = Path(__file__).resolve().parent.parent / "Images" / "perl.jpg"

_NUM_RE = re.compile(r'(\w+)="([\d.]+)mm"')


def _svg_attrs(svg_text: str) -> dict[str, float]:
    out: dict[str, float] = {}
    for name, value in _NUM_RE.findall(svg_text):
        if name in {"width", "height"}:
            out[name] = float(value)
    return out


def _two_color_image_2x1(tmp_path: Path) -> Path:
    # 32 high, 64 wide -> aspect width:height = 2:1.
    img = np.zeros((32, 64, 3), dtype=np.uint8)
    img[:, :32] = (50, 50, 50)
    img[:, 32:] = (200, 200, 200)
    p = tmp_path / "two_one.png"
    Image.fromarray(img).save(p)
    return p


def test_canvas_default(tmp_path):
    src = _two_color_image_2x1(tmp_path)
    out = tmp_path / "out.svg"
    raster_main(
        [
            "--image", str(src),
            "--stitches", "100",
            "--colors", "2",
            "--method", "brick",
            "--seed", "0",
            "--output", str(out),
        ]
    )
    attrs = _svg_attrs(out.read_text())
    assert attrs["width"] == pytest.approx(100.0)
    assert attrs["height"] == pytest.approx(50.0)


def test_canvas_width_only(tmp_path):
    src = _two_color_image_2x1(tmp_path)
    out = tmp_path / "out.svg"
    raster_main(
        [
            "--image", str(src),
            "--stitches", "100",
            "--colors", "2",
            "--method", "brick",
            "--width", "200",
            "--seed", "0",
            "--output", str(out),
        ]
    )
    attrs = _svg_attrs(out.read_text())
    assert attrs["width"] == pytest.approx(200.0)
    assert attrs["height"] == pytest.approx(100.0)


def test_canvas_height_only(tmp_path):
    src = _two_color_image_2x1(tmp_path)
    out = tmp_path / "out.svg"
    raster_main(
        [
            "--image", str(src),
            "--stitches", "100",
            "--colors", "2",
            "--method", "brick",
            "--height", "75",
            "--seed", "0",
            "--output", str(out),
        ]
    )
    attrs = _svg_attrs(out.read_text())
    assert attrs["width"] == pytest.approx(150.0)
    assert attrs["height"] == pytest.approx(75.0)


def test_canvas_both_contain(tmp_path):
    src = _two_color_image_2x1(tmp_path)  # 64 x 32 (W x H), aspect 2:1
    out = tmp_path / "out.svg"
    raster_main(
        [
            "--image", str(src),
            "--stitches", "100",
            "--colors", "2",
            "--method", "brick",
            "--width", "100",
            "--height", "100",
            "--seed", "0",
            "--output", str(out),
        ]
    )
    # scale = min(100/64, 100/32) = 100/64 -> 100 x 50.
    attrs = _svg_attrs(out.read_text())
    assert attrs["width"] == pytest.approx(100.0)
    assert attrs["height"] == pytest.approx(50.0)


@pytest.mark.skipif(not PERL_IMAGE.exists(), reason="Images/perl.jpg fixture not present")
def test_perl_camel_at_150mm_height(tmp_path):
    svg_path = tmp_path / "perl.svg"
    dst_path = tmp_path / "perl.dst"
    target_stitches = 4000

    rc1 = raster_main(
        [
            "--image", str(PERL_IMAGE),
            "--stitches", str(target_stitches),
            "--colors", "3",
            "--method", "brick",
            "--height", "150",
            "--seed", "0",
            "--output", str(svg_path),
        ]
    )
    assert rc1 == 0
    attrs = _svg_attrs(svg_path.read_text())
    # Image is 685 x 513; at height 150mm, width = 685/513 * 150 ≈ 200.292
    assert attrs["height"] == pytest.approx(150.0, abs=0.01)
    assert attrs["width"] == pytest.approx(685 / 513 * 150, abs=0.5)

    rc2 = stitch_main(
        [
            "--svg", str(svg_path),
            "--format", "dst",
            "--output", str(dst_path),
        ]
    )
    assert rc2 == 0
    assert dst_path.exists() and dst_path.stat().st_size > 0

    # The SVG point count is the authoritative stitch target. DST encoding may
    # insert intermediate JUMPs to satisfy format-specific stitch-length limits.
    from embscript.phase2.svg_parser import parse_layers
    svg_layers = parse_layers(svg_path)
    svg_total = sum(len(seg) for _, segs in svg_layers for seg in segs)
    assert within_tolerance(svg_total, target_stitches, 0.10), (
        f"SVG total {svg_total} not within 10% of target {target_stitches}"
    )
