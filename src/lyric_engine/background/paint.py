"""Shared art tools for every background world (one art style across worlds, H-027 note):
timing curves, the plaster texture and grain, half/full resolution, luminance and contrast.
Arrays are float32 in [0, 1] unless a docstring says otherwise."""
from __future__ import annotations

from typing import Iterable, Sequence

import numpy as np
from PIL import Image
from scipy import ndimage

GRAIN_SEED = 20260929   # fixed: the same grain in every world and every video


# --- Timing curves ---------------------------------------------------------------------------
def smooth(x):
    """Smoothstep of x clamped to [0, 1] (scalar or array)."""
    x = np.clip(x, 0.0, 1.0)
    return x * x * (3.0 - 2.0 * x)


def keyframes(keys: Sequence[tuple], f: float) -> np.ndarray:
    """keys = ((fraction, value), ...) in rising order, value a number or a tuple. The value at f,
    eased with smoothstep between neighbours and held flat outside the first and last key."""
    if f <= keys[0][0]:
        return np.asarray(keys[0][1], np.float32)
    for (f0, v0), (f1, v1) in zip(keys, keys[1:]):
        if f <= f1:
            w = float(smooth((f - f0) / (f1 - f0))) if f1 > f0 else 1.0
            return (np.asarray(v0, np.float32) * (1 - w) + np.asarray(v1, np.float32) * w)
    return np.asarray(keys[-1][1], np.float32)


def envelope(t: float, starts: Iterable[float], rise: float, total: float) -> float:
    """A swell that rises over `rise` seconds from each start and is gone `total` seconds after it.
    Overlapping swells take the stronger one, so they never add up past 1."""
    best = 0.0
    for s in starts:
        x = t - s
        if 0.0 <= x < total:
            best = max(best, float(smooth(x / rise) if x < rise
                                   else smooth(1.0 - (x - rise) / (total - rise))))
    return best


# --- Textures --------------------------------------------------------------------------------
def blur(a: np.ndarray, radius: float) -> np.ndarray:
    """Gaussian blur (sigma = radius) of a 2-D float array; for art drawn once."""
    return ndimage.gaussian_filter(a, radius, mode="nearest") if radius > 0 else a


def soft(a: np.ndarray, radius: int) -> np.ndarray:
    """Two box blurs of width 2r+1: a near-Gaussian soft edge, fast enough for every frame."""
    if radius <= 0:
        return a
    size = 2 * radius + 1
    return ndimage.uniform_filter(ndimage.uniform_filter(a, size, mode="constant"), size,
                                  mode="constant")


def resize(a: np.ndarray, w: int, h: int, box: tuple | None = None) -> np.ndarray:
    """Bilinear resize of a 2-D float array to (h, w), optionally of a sub-box (x0, y0, x1, y1)."""
    im = Image.fromarray(np.ascontiguousarray(a, np.float32), "F")
    return np.array(im.resize((w, h), Image.BILINEAR, box=box), np.float32)   # writable


def noise(h: int, w: int, rng: np.random.Generator,
          scales: Sequence[tuple[int, float, float]]) -> np.ndarray:
    """Soft multi-scale noise, mean 0, unit spread: ((shrink, blur sigma, weight), ...); each scale
    is made `shrink` times smaller and enlarged, so broad scales stay cheap."""
    out = np.zeros((h, w), np.float32)
    for shrink, sigma, weight in scales:
        small = blur(rng.standard_normal((-(-h // shrink), -(-w // shrink))).astype(np.float32),
                     sigma)
        layer = small if shrink == 1 else resize(small, w, h)
        out += weight * layer / (layer.std() + 1e-6)
    return out / (out.std() + 1e-6)


def plaster(h: int, w: int, seed: int) -> np.ndarray:
    """A hand-made plaster wall: broad patches and fine trowel marks, around 1."""
    rng = np.random.default_rng(seed)
    return 1.0 + 0.05 * noise(h, w, rng, ((16, 3.0, 1.0), (4, 3.0, 0.55), (1, 2.0, 0.3)))


def grain(h: int, w: int) -> np.ndarray:
    """Fine paper-like grain around 1, fixed for every world (never per frame)."""
    rng = np.random.default_rng(GRAIN_SEED)
    return 1.0 + 0.02 * noise(h, w, rng, ((1, 0.6, 1.0), (1, 1.5, 0.5)))


# --- Resolution ------------------------------------------------------------------------------
def down2(a: np.ndarray) -> np.ndarray:
    """2x2 mean of a 2-D array with even sides."""
    h, w = a.shape
    return a.reshape(h // 2, 2, w // 2, 2).mean(axis=(1, 3), dtype=np.float32)


def up2(a: np.ndarray) -> np.ndarray:
    """Bilinear x2 of a (h, w) or (h, w, c) float array."""
    if a.ndim == 2:
        return resize(a, a.shape[1] * 2, a.shape[0] * 2)
    return np.stack([up2(a[..., c]) for c in range(a.shape[2])], axis=-1)


# --- Luminance -------------------------------------------------------------------------------
def luminance(rgb: np.ndarray) -> np.ndarray:
    """Relative luminance (WCAG) of sRGB values in [0, 1], shape (..., 3)."""
    c = np.clip(rgb, 0.0, 1.0)
    lin = np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)
    return lin @ np.array([0.2126, 0.7152, 0.0722], np.float32)


def contrast(l1: float, l2: float) -> float:
    """WCAG contrast ratio of two relative luminances."""
    hi, lo = max(l1, l2), min(l1, l2)
    return (hi + 0.05) / (lo + 0.05)
