"""Write a color-layered SVG: one <g> per color, polyline geometry in millimetres."""

from __future__ import annotations

from pathlib import Path

import svgwrite

Polyline = list[tuple[float, float]]

STROKE_WIDTH_MM = 0.2


def write_svg(
    path: Path,
    width_mm: float,
    height_mm: float,
    layers: list[tuple[str, list[Polyline]]],
) -> None:
    """Write the embscript-shaped SVG.

    Each entry in `layers` is (#RRGGBB, segments) where segments is a list of
    polylines. Each contiguous segment becomes one <polyline> inside the layer's
    <g>; disconnected segments stay visually separate (no connecting line).
    """
    dwg = svgwrite.Drawing(
        str(path),
        size=(f"{width_mm}mm", f"{height_mm}mm"),
        viewBox=f"0 0 {width_mm} {height_mm}",
    )
    for i, (color, segments) in enumerate(layers):
        g = dwg.g(id=f"layer-{i}", stroke=color, fill="none", stroke_width=STROKE_WIDTH_MM)
        for segment in segments:
            if segment:
                g.add(dwg.polyline(points=segment))
        dwg.add(g)
    dwg.save()
