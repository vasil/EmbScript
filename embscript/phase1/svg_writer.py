"""Write a color-layered SVG: one <g> per color, polyline geometry in millimetres."""

from __future__ import annotations

from pathlib import Path

Polyline = list[tuple[float, float]]


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
    raise NotImplementedError
