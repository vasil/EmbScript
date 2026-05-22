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
    layers: list[tuple[str, Polyline]],
) -> None:
    """Write the embscript-shaped SVG.

    Each entry in `layers` is (#RRGGBB, polyline). Coordinates are in millimetres,
    y-down, matching SVG and most embroidery machine conventions.
    """
    dwg = svgwrite.Drawing(
        str(path),
        size=(f"{width_mm}mm", f"{height_mm}mm"),
        viewBox=f"0 0 {width_mm} {height_mm}",
    )
    for i, (color, polyline) in enumerate(layers):
        g = dwg.g(id=f"layer-{i}", stroke=color, fill="none", stroke_width=STROKE_WIDTH_MM)
        if polyline:
            g.add(dwg.polyline(points=polyline))
        dwg.add(g)
    dwg.save()
