"""CMYK color separation: decompose RGB into cyan, magenta, yellow, black layers."""

from __future__ import annotations

import numpy as np

CMYK_PALETTE_RGB = np.array(
    [
        [0, 255, 255],  # cyan
        [255, 0, 255],  # magenta
        [255, 255, 0],  # yellow
        [0, 0, 0],      # black
    ],
    dtype=np.uint8,
)

DEFAULT_MASK_THRESHOLD = 0.05


def cmyk_separate(
    image_rgb: np.ndarray,
    mask_threshold: float = DEFAULT_MASK_THRESHOLD,
) -> tuple[np.ndarray, list[np.ndarray], np.ndarray]:
    """Decompose RGB into per-channel CMYK masks, densities, and a fixed palette.

    Each layer's density is the CMYK channel intensity in [0, 1]; the mask is
    True wherever that channel exceeds `mask_threshold`. Unlike KMeans, the
    masks may overlap: a single source pixel can contribute to multiple layers,
    which matches how a printer (or embroidery machine) lays colored thread on
    fabric to mix colors visually.
    """
    rgb = image_rgb.astype(np.float32) / 255.0
    r, g, b = rgb[..., 0], rgb[..., 1], rgb[..., 2]

    k = 1.0 - np.maximum(np.maximum(r, g), b)
    denom = 1.0 - k
    safe_denom = np.where(denom > 1e-6, denom, 1.0)
    c = np.where(denom > 1e-6, (1.0 - r - k) / safe_denom, 0.0)
    m = np.where(denom > 1e-6, (1.0 - g - k) / safe_denom, 0.0)
    y = np.where(denom > 1e-6, (1.0 - b - k) / safe_denom, 0.0)

    densities = [c.astype(np.float32), m.astype(np.float32), y.astype(np.float32), k.astype(np.float32)]
    masks = np.stack([d > mask_threshold for d in densities], axis=0)

    return masks, densities, CMYK_PALETTE_RGB.copy()
