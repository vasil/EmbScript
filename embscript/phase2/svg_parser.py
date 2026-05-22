"""Parse a color-layered SVG into per-color polylines."""

from __future__ import annotations

from pathlib import Path

Polyline = list[tuple[float, float]]


def parse_layers(svg_path: Path) -> list[tuple[str, Polyline]]:
    """Return [(#RRGGBB, polyline), ...] in layer order.

    Expects the embscript SVG dialect: one <g> per color, polylines only,
    coordinates in millimetres.
    """
    raise NotImplementedError
