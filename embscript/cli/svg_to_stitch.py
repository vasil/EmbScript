"""Phase 2 CLI: color-layered SVG → embroidery machine file."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from embscript.phase2.stitch_writer import SUPPORTED_FORMATS


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="embscript-stitch",
        description="Convert a color-layered SVG into an embroidery machine file via pyembroidery.",
    )
    p.add_argument("--svg", type=Path, required=True, help="Input SVG produced by embscript-raster.")
    p.add_argument(
        "--format",
        choices=sorted(SUPPORTED_FORMATS),
        default="dst",
        help="Output embroidery format (default: dst = Tajima).",
    )
    p.add_argument("--output", type=Path, required=True, help="Output stitch file path.")
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    raise NotImplementedError("Phase 2 pipeline not yet implemented")


if __name__ == "__main__":
    sys.exit(main())
