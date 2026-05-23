"""Render a side-by-side comparison strip of the seven routing methods.

For each method, renders `Images/perl.jpg` via embscript-raster (if the cached
SVG isn't already present in examples/output/), then rasterizes the SVGs via
PIL and arranges them in a 2x4 grid with method labels.

Run from the repo root:

    python examples/render_routing_comparison.py
"""

from __future__ import annotations

import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

METHODS = ["brownian", "brick", "perlin", "levy", "gradient", "attractor", "hilbert"]
INPUT_IMAGE = "Images/perl.jpg"
RENDER_ARGS = ["--colors", "3", "--stitches", "800", "--seed", "42", "--width", "80"]
SVG_NS = {"svg": "http://www.w3.org/2000/svg"}

CELL_W = 320
CELL_H = 240
LABEL_H = 28
COLS = 4
PAD = 8


def _strip_unit(value: str) -> float:
    return float(value.removesuffix("mm").removesuffix("px"))


def rasterize_svg(svg_path: Path, w_px: int, h_px: int) -> Image.Image:
    """Rasterize an EmbScript SVG to a PIL image at the given pixel size."""
    tree = ET.parse(svg_path)
    root = tree.getroot()
    width_mm = _strip_unit(root.attrib["width"])
    height_mm = _strip_unit(root.attrib["height"])

    scale = min(w_px / width_mm, h_px / height_mm)
    draw_w = int(width_mm * scale)
    draw_h = int(height_mm * scale)

    img = Image.new("RGB", (draw_w, draw_h), "white")
    drw = ImageDraw.Draw(img)

    for group in root.findall("svg:g", SVG_NS):
        stroke = group.attrib.get("stroke", "#000000")
        for poly in group.findall("svg:polyline", SVG_NS):
            pts_attr = poly.attrib.get("points", "")
            coords = []
            for token in pts_attr.split():
                x_str, y_str = token.split(",")
                coords.append((float(x_str) * scale, float(y_str) * scale))
            if len(coords) >= 2:
                drw.line(coords, fill=stroke, width=1)

    if (draw_w, draw_h) != (w_px, h_px):
        canvas = Image.new("RGB", (w_px, h_px), "white")
        canvas.paste(img, ((w_px - draw_w) // 2, (h_px - draw_h) // 2))
        return canvas
    return img


def _load_font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    for path in (
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ):
        if Path(path).exists():
            return ImageFont.truetype(path, size)
    return ImageFont.load_default()


def ensure_svgs(repo_root: Path, svg_dir: Path) -> None:
    """Render any missing per-method SVGs via the embscript-raster CLI."""
    svg_dir.mkdir(parents=True, exist_ok=True)
    cli = shutil.which("embscript-raster")
    if cli is None:
        candidate = repo_root / ".venv" / "bin" / "embscript-raster"
        if candidate.exists():
            cli = str(candidate)
    if cli is None:
        raise RuntimeError(
            "embscript-raster not found; install the package (pip install -e .) "
            "or activate the venv before running this script."
        )
    image = repo_root / INPUT_IMAGE
    if not image.exists():
        raise FileNotFoundError(f"input image missing: {image}")
    for method in METHODS:
        out = svg_dir / f"cmp_{method}.svg"
        if out.exists():
            continue
        print(f"rendering {method} ...", file=sys.stderr)
        subprocess.run(
            [cli, "--image", str(image), "--method", method, *RENDER_ARGS, "--output", str(out)],
            check=True,
            stdout=subprocess.DEVNULL,
        )


def build_strip(svg_dir: Path, out_path: Path) -> None:
    rows = (len(METHODS) + COLS - 1) // COLS
    strip_w = COLS * CELL_W + (COLS + 1) * PAD
    strip_h = rows * (CELL_H + LABEL_H) + (rows + 1) * PAD
    strip = Image.new("RGB", (strip_w, strip_h), "white")
    drw = ImageDraw.Draw(strip)
    font = _load_font(18)

    for idx, method in enumerate(METHODS):
        svg_path = svg_dir / f"cmp_{method}.svg"
        if not svg_path.exists():
            print(f"missing {svg_path}", file=sys.stderr)
            continue
        cell = rasterize_svg(svg_path, CELL_W, CELL_H)
        r, c = divmod(idx, COLS)
        x = PAD + c * (CELL_W + PAD)
        y = PAD + r * (CELL_H + LABEL_H + PAD)
        strip.paste(cell, (x, y))
        drw.rectangle([x, y, x + CELL_W - 1, y + CELL_H - 1], outline="#cccccc")
        bbox = drw.textbbox((0, 0), method, font=font)
        tw = bbox[2] - bbox[0]
        drw.text(
            (x + (CELL_W - tw) // 2, y + CELL_H + 4),
            method,
            fill="#222222",
            font=font,
        )

    strip.save(out_path, "PNG", optimize=True)
    print(f"wrote {out_path}")


if __name__ == "__main__":
    repo_root = Path(__file__).resolve().parent.parent
    svg_dir = repo_root / "examples" / "output"
    ensure_svgs(repo_root, svg_dir)
    build_strip(
        svg_dir=svg_dir,
        out_path=svg_dir / "routing_methods_comparison.png",
    )
