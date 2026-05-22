"""Color separation: quantize a raster image into N color layers via k-means."""

from __future__ import annotations

import numpy as np
from sklearn.cluster import KMeans

MAX_FIT_SAMPLES = 200_000


def separate(image_rgb: np.ndarray, n_colors: int) -> tuple[np.ndarray, np.ndarray]:
    """Cluster pixels into n_colors palette entries.

    Returns:
        masks: (n_colors, H, W) boolean array, one mask per palette entry.
        palette: (n_colors, 3) uint8 RGB values, mean RGB of each cluster's pixels.
    """
    H, W = image_rgb.shape[:2]
    pixels = image_rgb.reshape(-1, 3).astype(np.float32)

    if pixels.shape[0] > MAX_FIT_SAMPLES:
        rng = np.random.default_rng(0)
        idx = rng.choice(pixels.shape[0], MAX_FIT_SAMPLES, replace=False)
        sample = pixels[idx]
    else:
        sample = pixels

    km = KMeans(n_clusters=n_colors, n_init=10, random_state=0).fit(sample)
    labels = km.predict(pixels).reshape(H, W)

    masks = np.stack([labels == k for k in range(n_colors)], axis=0)
    palette = np.zeros((n_colors, 3), dtype=np.uint8)
    for k in range(n_colors):
        if masks[k].any():
            palette[k] = image_rgb[masks[k]].mean(axis=0).astype(np.uint8)

    return masks, palette
