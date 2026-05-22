"""Write embroidery machine files via pyembroidery."""

from __future__ import annotations

from pathlib import Path

import pyembroidery

Polyline = list[tuple[float, float]]

_WRITERS = {
    "dst": pyembroidery.write_dst,
    "jef": pyembroidery.write_jef,
    "pes": pyembroidery.write_pes,
    "exp": pyembroidery.write_exp,
    "vp3": pyembroidery.write_vp3,
}

SUPPORTED_FORMATS: set[str] = set(_WRITERS.keys())

UNITS_PER_MM = 10  # pyembroidery's native unit is 0.1 mm.


def write_pattern(
    output: Path,
    layers: list[tuple[str, Polyline]],
    fmt: str,
) -> None:
    """Sequence layers as pyembroidery stitch blocks with COLOR_CHANGE between them."""
    if fmt not in _WRITERS:
        raise ValueError(f"Unsupported format: {fmt!r}. Supported: {sorted(SUPPORTED_FORMATS)}")

    pattern = pyembroidery.EmbPattern()
    non_empty_index = 0
    for color, polyline_mm in layers:
        if not polyline_mm:
            continue
        if non_empty_index > 0:
            pattern.add_command(pyembroidery.COLOR_CHANGE)

        thread = pyembroidery.EmbThread()
        thread.set_hex_color(color.lstrip("#"))
        pattern.add_thread(thread)

        for x_mm, y_mm in polyline_mm:
            pattern.add_stitch_absolute(
                pyembroidery.STITCH,
                x_mm * UNITS_PER_MM,
                y_mm * UNITS_PER_MM,
            )
        non_empty_index += 1

    pattern.add_command(pyembroidery.END)
    _WRITERS[fmt](pattern, str(output))
