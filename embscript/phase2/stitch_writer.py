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
    layers: list[tuple[str, list[Polyline]]],
    fmt: str,
) -> None:
    """Sequence layers as pyembroidery stitch blocks.

    Between layers (color changes): emit COLOR_CHANGE.
    Between segments within a color: emit TRIM and JUMP to the new segment's start.
    """
    if fmt not in _WRITERS:
        raise ValueError(f"Unsupported format: {fmt!r}. Supported: {sorted(SUPPORTED_FORMATS)}")

    pattern = pyembroidery.EmbPattern()
    non_empty_index = 0
    for color, segments in layers:
        non_empty_segments = [s for s in segments if s]
        if not non_empty_segments:
            continue
        if non_empty_index > 0:
            pattern.add_command(pyembroidery.COLOR_CHANGE)

        thread = pyembroidery.EmbThread()
        thread.set_hex_color(color.lstrip("#"))
        pattern.add_thread(thread)

        for seg_index, segment in enumerate(non_empty_segments):
            if seg_index > 0:
                pattern.add_command(pyembroidery.TRIM)
                first_x, first_y = segment[0]
                pattern.add_stitch_absolute(
                    pyembroidery.JUMP,
                    first_x * UNITS_PER_MM,
                    first_y * UNITS_PER_MM,
                )
            for x_mm, y_mm in segment:
                pattern.add_stitch_absolute(
                    pyembroidery.STITCH,
                    x_mm * UNITS_PER_MM,
                    y_mm * UNITS_PER_MM,
                )
        non_empty_index += 1

    pattern.add_command(pyembroidery.END)
    _WRITERS[fmt](pattern, str(output))
