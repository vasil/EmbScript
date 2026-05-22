"""Parse a color-layered SVG into per-color polylines."""

from __future__ import annotations

import re
from pathlib import Path
from xml.etree import ElementTree as ET

Polyline = list[tuple[float, float]]

SVG_NS = "http://www.w3.org/2000/svg"
_NUM = re.compile(r"-?\d+(?:\.\d+)?(?:[eE][+-]?\d+)?")


def _parse_points(points_str: str) -> Polyline:
    nums = [float(m) for m in _NUM.findall(points_str)]
    return [(nums[i], nums[i + 1]) for i in range(0, len(nums) - 1, 2)]


def parse_layers(svg_path: Path) -> list[tuple[str, Polyline]]:
    """Return [(#RRGGBB, polyline), ...] in document order.

    Expects the embscript SVG dialect: one <g> per color with id="layer-N"
    and a single <polyline points="..."> child, coordinates in millimetres.
    """
    tree = ET.parse(svg_path)
    root = tree.getroot()

    layers: list[tuple[str, Polyline]] = []
    for g in root.iter(f"{{{SVG_NS}}}g"):
        if not (g.get("id") or "").startswith("layer-"):
            continue
        color = (g.get("stroke") or "#000000").lower()
        polyline_el = g.find(f"{{{SVG_NS}}}polyline")
        if polyline_el is None or not polyline_el.get("points"):
            layers.append((color, []))
            continue
        layers.append((color, _parse_points(polyline_el.get("points", ""))))
    return layers
