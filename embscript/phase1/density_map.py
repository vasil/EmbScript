"""Tonal density map per color layer."""

from __future__ import annotations

import numpy as np


def density_for_layer(image_rgb: np.ndarray, mask: np.ndarray) -> np.ndarray:
    """Build a 0..1 density field for a single color layer.

    Density is high where the source is dark *and* the pixel belongs to this layer's mask;
    elsewhere it is 0. The returned field drives the local stitch density downstream.
    """
    raise NotImplementedError
