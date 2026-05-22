"""Tonal density map per color layer."""

from __future__ import annotations

import numpy as np


def density_for_layer(image_rgb: np.ndarray, mask: np.ndarray) -> np.ndarray:
    """Build a 0..1 density field for a single color layer.

    Density is `(1 - luminance) * mask`. Not normalized within the mask, so a dark
    layer integrates to more density than a light layer of the same area — which is
    what drives the cross-layer stitch allocation.
    """
    rgb = image_rgb.astype(np.float32) / 255.0
    luminance = 0.2126 * rgb[..., 0] + 0.7152 * rgb[..., 1] + 0.0722 * rgb[..., 2]
    return ((1.0 - luminance) * mask).astype(np.float32)
