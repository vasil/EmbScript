"""Phase 1 CLI: raster image → color-layered SVG."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
from PIL import Image

from embscript.phase1.color_separation import separate
from embscript.phase1.density_map import density_for_layer
from embscript.phase1.routing import METHODS
from embscript.phase1.stitch_budget import allocate
from embscript.phase1.svg_writer import write_svg

DEFAULT_WIDTH_MM = 100.0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="embscript-raster",
        description="Convert a raster image into a color-layered SVG with one continuous path per color.",
    )
    p.add_argument("--image", type=Path, required=True, help="Input raster image (PNG/JPEG/...).")
    p.add_argument("--stitches", type=int, required=True, help="Target total stitch count (±~5%).")
    p.add_argument("--colors", type=int, required=True, help="Number of color layers to separate.")
    p.add_argument(
        "--method",
        choices=sorted(METHODS.keys()),
        default="brownian",
        help="Routing algorithm for the per-color continuous path.",
    )
    p.add_argument(
        "--overlap-tolerance",
        type=float,
        default=0.0,
        help="brownian only: 0 = strict self-avoidance, 1 = unrestricted overlap.",
    )
    p.add_argument("--seed", type=int, default=None, help="RNG seed for reproducible runs.")
    p.add_argument("--output", type=Path, required=True, help="Output SVG path.")
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    img = Image.open(args.image).convert("RGB")
    rgb = np.asarray(img)
    h_px, w_px = rgb.shape[:2]

    masks, palette = separate(rgb, args.colors)
    densities = [density_for_layer(rgb, masks[k]) for k in range(args.colors)]
    budgets = allocate(densities, args.stitches)

    rng = np.random.default_rng(args.seed)
    method = METHODS[args.method]()

    width_mm = DEFAULT_WIDTH_MM
    height_mm = DEFAULT_WIDTH_MM * h_px / w_px
    scale = width_mm / w_px

    layers: list[tuple[str, list[tuple[float, float]]]] = []
    total_actual = 0
    for k in range(args.colors):
        polyline_px = method.route(
            masks[k],
            densities[k],
            budgets[k],
            overlap_tolerance=args.overlap_tolerance,
            rng=rng,
        )
        total_actual += len(polyline_px)
        color = "#{:02x}{:02x}{:02x}".format(*palette[k])
        polyline_mm = [(x * scale, y * scale) for x, y in polyline_px]
        layers.append((color, polyline_mm))
        print(
            f"layer {k} ({color}): target={budgets[k]} actual={len(polyline_px)}",
            file=sys.stderr,
        )

    write_svg(args.output, width_mm, height_mm, layers)
    print(
        f"Wrote {args.output} — {total_actual} stitches total (target {args.stitches})",
        file=sys.stderr,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
