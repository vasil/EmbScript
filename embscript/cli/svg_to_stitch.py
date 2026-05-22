"""Phase 2 CLI: color-layered SVG → embroidery machine file."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from embscript.phase2.stitch_writer import SUPPORTED_FORMATS, write_pattern
from embscript.phase2.svg_parser import parse_layers


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

    out_ext = args.output.suffix.lstrip(".").lower()
    if out_ext and out_ext != args.format:
        print(
            f"warning: output extension .{out_ext} does not match --format {args.format}",
            file=sys.stderr,
        )

    layers = parse_layers(args.svg)
    write_pattern(args.output, layers, args.format)

    total = sum(len(seg) for _, segments in layers for seg in segments)
    non_empty = sum(1 for _, segments in layers if any(segments))
    total_segments = sum(len(segments) for _, segments in layers)
    print(
        f"Wrote {args.output} — {total} stitches across {non_empty} color(s) "
        f"in {total_segments} segment(s)",
        file=sys.stderr,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
