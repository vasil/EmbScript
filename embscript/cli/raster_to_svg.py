"""Phase 1 CLI: raster image → color-layered SVG."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from embscript.phase1.routing import METHODS


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
    p.add_argument("--output", type=Path, required=True, help="Output SVG path.")
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    raise NotImplementedError("Phase 1 pipeline not yet implemented")


if __name__ == "__main__":
    sys.exit(main())
