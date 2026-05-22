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
    p.add_argument(
        "--min-density",
        type=float,
        default=0.0,
        help="Drop pixels with density below this threshold (0..1). Carves blank "
        "negative space into the design — the routing method can't visit those pixels.",
    )
    p.add_argument(
        "--fill",
        action="store_true",
        help="Walk until the mask is filled; --stitches becomes a spacing guide rather "
        "than a hard cap. brownian only for now.",
    )
    p.add_argument(
        "--binarize",
        action="store_true",
        help="Flatten density to a hard mask: every pixel above --min-density gets "
        "density 1.0. Produces black-and-white output instead of gradient.",
    )
    p.add_argument(
        "--width",
        type=float,
        default=None,
        help="Canvas width in mm. Aspect ratio is always preserved.",
    )
    p.add_argument(
        "--height",
        type=float,
        default=None,
        help="Canvas height in mm. If --width and --height are both given, the design "
        "is contained inside the box (smaller scale wins).",
    )
    p.add_argument("--output", type=Path, required=True, help="Output SVG path.")
    return p


def _canvas_size(w_px: int, h_px: int, width_arg: float | None, height_arg: float | None) -> tuple[float, float]:
    """Resolve canvas dimensions in mm while preserving image aspect ratio."""
    if width_arg is None and height_arg is None:
        return DEFAULT_WIDTH_MM, DEFAULT_WIDTH_MM * h_px / w_px
    if width_arg is not None and height_arg is None:
        return width_arg, width_arg * h_px / w_px
    if height_arg is not None and width_arg is None:
        return height_arg * w_px / h_px, height_arg
    scale = min(width_arg / w_px, height_arg / h_px)  # type: ignore[operator]
    return w_px * scale, h_px * scale


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    img = Image.open(args.image).convert("RGB")
    rgb = np.asarray(img)
    h_px, w_px = rgb.shape[:2]

    masks, palette = separate(rgb, args.colors)
    densities = [density_for_layer(rgb, masks[k]) for k in range(args.colors)]
    if args.min_density > 0.0:
        for k in range(args.colors):
            below = densities[k] < args.min_density
            masks[k] = masks[k] & ~below
            densities[k] = np.where(below, 0.0, densities[k])
    if args.binarize:
        for k in range(args.colors):
            densities[k] = masks[k].astype(np.float32)
    budgets = allocate(densities, args.stitches)

    rng = np.random.default_rng(args.seed)
    method = METHODS[args.method]()

    width_mm, height_mm = _canvas_size(w_px, h_px, args.width, args.height)
    scale = width_mm / w_px
    print(f"Canvas: {width_mm:.3f} x {height_mm:.3f} mm", file=sys.stderr)

    layers: list[tuple[str, list[list[tuple[float, float]]]]] = []
    total_actual = 0
    for k in range(args.colors):
        segments_px = method.route(
            masks[k],
            densities[k],
            budgets[k],
            overlap_tolerance=args.overlap_tolerance,
            rng=rng,
            unlimited=args.fill,
        )
        layer_count = sum(len(s) for s in segments_px)
        total_actual += layer_count
        color = "#{:02x}{:02x}{:02x}".format(*palette[k])
        segments_mm = [[(x * scale, y * scale) for x, y in seg] for seg in segments_px]
        layers.append((color, segments_mm))
        print(
            f"layer {k} ({color}): target={budgets[k]} actual={layer_count} "
            f"in {len(segments_px)} segment(s)",
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
