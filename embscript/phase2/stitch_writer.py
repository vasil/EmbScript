"""Write embroidery machine files via pyembroidery."""

from __future__ import annotations

from pathlib import Path

Polyline = list[tuple[float, float]]

SUPPORTED_FORMATS: set[str] = {"dst", "jef", "pes", "exp", "vp3"}


def write_pattern(
    output: Path,
    layers: list[tuple[str, Polyline]],
    fmt: str,
) -> None:
    """Sequence layers as pyembroidery stitch blocks with thread changes between them."""
    raise NotImplementedError
