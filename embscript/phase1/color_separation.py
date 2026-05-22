"""Color separation: quantize a raster image into N color layers via k-means in Lab space."""

from __future__ import annotations

import numpy as np


def separate(image_rgb: np.ndarray, n_colors: int) -> tuple[np.ndarray, np.ndarray]:
    """Cluster pixels into n_colors palette entries.

    Returns:
        masks: (n_colors, H, W) boolean array, one mask per palette entry.
        palette: (n_colors, 3) uint8 RGB values, one per cluster centroid.
    """
    raise NotImplementedError
