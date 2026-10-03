"""Shared art tools for every background look (one art style across looks, H-032): linear-light
colours, OKLab skies, soft glows and out-of-focus lights, soft noise, quarter-size light layers,
matte dots, and the finishing pass every look shares (bloom, a soft highlight shoulder, a dark
border, fine grain). Arrays are float32 linear light in [0, 1] unless a docstring says otherwise.
Ported from the owner-approved samples (songs/_review/backgrounds/lights2/)."""
from __future__ import annotations

import math
from functools import lru_cache
from typing import Iterable, Sequence

import numpy as np
from PIL import Image
from scipy import ndimage, signal

W, H = 1080, 1920


@lru_cache(maxsize=1)
def grids() -> tuple[np.ndarray, np.ndarray]:
    """(YY, XX) full-size pixel coordinate grids, float32."""
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    return yy, xx


# --- timing curves ---------------------------------------------------------------------------
def smooth(x):
    """Smoothstep of x clamped to [0, 1] (scalar or array)."""
    x = np.clip(x, 0.0, 1.0)
    return x * x * (3.0 - 2.0 * x)


def envelope(t: float, starts: Iterable[float], rise: float, total: float) -> float:
    """A swell that rises over `rise` s from each start and is gone `total` s after it; overlapping
    swells take the stronger one, so they never add up past 1."""
    best = 0.0
    for s in starts:
        a = t - s
        if 0.0 <= a < total:
            u = a / rise if a < rise else 1.0 - (a - rise) / (total - rise)
            best = max(best, float(smooth(u)))
    return best


# --- colour ----------------------------------------------------------------------------------
def lin(hex_colour: str) -> np.ndarray:
    """'#rrggbb' -> linear-light RGB."""
    h = hex_colour.lstrip("#")
    c = np.array([int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)], np.float32)
    return np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4).astype(np.float32)


def to_srgb(c):
    c = np.clip(c, 0, None)
    return np.where(c <= 0.0031308, 12.92 * c, 1.055 * np.power(c, 1 / 2.4) - 0.055)


def luminance(rgb: np.ndarray) -> np.ndarray:
    """Relative luminance (WCAG) of sRGB values in [0, 1], shape (..., 3)."""
    c = np.clip(rgb, 0.0, 1.0)
    linear = np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)
    return linear @ np.array([0.2126, 0.7152, 0.0722], np.float32)


def contrast(l1: float, l2: float) -> float:
    """WCAG contrast ratio of two relative luminances."""
    hi, lo = max(l1, l2), min(l1, l2)
    return (hi + 0.05) / (lo + 0.05)


_M1 = np.array([[0.4122214708, 0.5363325363, 0.0514459929],
                [0.2119034982, 0.6806995451, 0.1073969566],
                [0.0883024619, 0.2817188376, 0.6299787005]], np.float32)
_M2 = np.array([[0.2104542553, 0.7936177850, -0.0040720468],
                [1.9779984951, -2.4285922050, 0.4505937099],
                [0.0259040371, 0.7827717662, -0.8086757660]], np.float32)


def gradient(stops: Sequence[tuple[float, str]]) -> np.ndarray:
    """A vertical gradient (H, W, 3) in linear light, mixed in OKLab so blends never go muddy."""
    labs = np.array([np.cbrt(lin(c) @ _M1.T) @ _M2.T for _, c in stops])
    fr = np.array([f for f, _ in stops])
    ys = np.linspace(0, 1, H)
    j = np.clip(np.searchsorted(fr, ys) - 1, 0, len(fr) - 2)
    u = smooth((ys - fr[j]) / np.maximum(fr[j + 1] - fr[j], 1e-6))
    lab = labs[j] * (1 - u)[:, None] + labs[j + 1] * u[:, None]
    col = ((lab @ np.linalg.inv(_M2).T) ** 3 @ np.linalg.inv(_M1).T).astype(np.float32)
    return np.repeat(np.clip(col, 0, None)[:, None, :], W, axis=1)


# --- light -----------------------------------------------------------------------------------
def blob(img, cx, cy, sx, sy, colour, strength) -> None:
    """A soft elliptical glow (Gaussian), added in linear light, in place (full size)."""
    x0, x1 = max(int(cx - 4 * sx), 0), min(int(cx + 4 * sx) + 1, W)
    y0, y1 = max(int(cy - 4 * sy), 0), min(int(cy + 4 * sy) + 1, H)
    if x1 <= x0 or y1 <= y0:
        return
    xs = np.arange(x0, x1, dtype=np.float32)[None, :]
    ys = np.arange(y0, y1, dtype=np.float32)[:, None]
    g = np.exp(-(((xs - cx) / sx) ** 2 + ((ys - cy) / sy) ** 2) / 2)
    img[y0:y1, x0:x1] += g[..., None] * colour * strength


def point(layer, x, y, colour, level, radius) -> None:
    """A light source that, blurred to a disc of `radius` by defocus(), glows at about `level`."""
    blob(layer, x, y, 1.5, 1.5, colour, level * radius * radius / 4.5)


def down(a: np.ndarray, f: int) -> np.ndarray:
    """f x f mean of an (h, w[, c]) array."""
    h, w = a.shape[0] // f, a.shape[1] // f
    if a.ndim == 2:
        return a[:h * f, :w * f].reshape(h, f, w, f).mean(axis=(1, 3), dtype=np.float32)
    return a[:h * f, :w * f].reshape(h, f, w, f, -1).mean(axis=(1, 3), dtype=np.float32)


def resize(a: np.ndarray, w: int, h: int, box: tuple | None = None) -> np.ndarray:
    """Bilinear resize of a 2-D float array to (h, w), optionally of a sub-box."""
    im = Image.fromarray(np.ascontiguousarray(a, np.float32), "F")
    return np.array(im.resize((w, h), Image.BILINEAR, box=box), np.float32)


def up(small: np.ndarray, w: int = W, h: int = H) -> np.ndarray:
    """Bilinear enlarge of an (h, w[, c]) float map to full size."""
    if small.ndim == 2:
        return resize(small, w, h)
    return np.stack([resize(small[..., c], w, h) for c in range(small.shape[2])], -1)


def soft_blur(img: np.ndarray, sigma: float, f: int = 4) -> np.ndarray:
    """A wide Gaussian blur of a full-size (H, W, c) image, worked out at 1/f size."""
    small = down(img, f)
    return up(np.stack([ndimage.gaussian_filter(small[..., c], sigma / f)
                        for c in range(small.shape[2])], -1), img.shape[1], img.shape[0])


def defocus(lights: np.ndarray, radius: float) -> np.ndarray:
    """Out-of-focus lens blur: every light becomes a soft-edged disc of `radius` (full px), worked
    out at quarter size."""
    f = 4
    small = down(lights, f)
    r = radius / f
    k = int(math.ceil(r)) + 2
    yy, xx = np.mgrid[-k:k + 1, -k:k + 1].astype(np.float32)
    d = np.sqrt(xx * xx + yy * yy)
    kern = np.clip(r + 0.8 - d, 0, 1)
    kern *= 0.85 + 0.15 * np.clip((d - 0.6 * r) / (0.4 * r + 1e-3), 0, 1)
    kern /= kern.sum()
    out = np.stack([signal.fftconvolve(small[..., c], kern, mode="same") for c in range(3)], -1)
    return up(np.clip(out, 0, None).astype(np.float32))


def fbm(rng: np.random.Generator, scales, h: int = H, w: int = W) -> np.ndarray:
    """Soft noise, mean about 0: ((shrink, sigma, weight), ...), each scale made `shrink` times
    smaller and enlarged, so broad scales stay cheap."""
    out = np.zeros((h, w), np.float32)
    for shrink, sigma, weight in scales:
        n = ndimage.gaussian_filter(rng.standard_normal((h // shrink + 1, w // shrink + 1)), sigma)
        n = ((n - n.mean()) / (n.std() + 1e-6)).astype(np.float32)[:h // shrink, :w // shrink]
        out += weight * (resize(n, w, h) if shrink > 1 else n[:h, :w])
    return out


def stamp(canvas, q, cx, cy, sx, sy, colour, level) -> None:
    """A soft coloured glow on a canvas that is 1/q of full size (units: full-size px)."""
    hh, ww = canvas.shape[:2]
    cx, cy, sx, sy = cx / q, cy / q, max(sx / q, 0.5), max(sy / q, 0.5)
    x0, x1 = max(int(cx - 3 * sx), 0), min(int(cx + 3 * sx) + 2, ww)
    y0, y1 = max(int(cy - 3 * sy), 0), min(int(cy + 3 * sy) + 2, hh)
    if x1 <= x0 or y1 <= y0:
        return
    xs = np.arange(x0, x1, dtype=np.float32)[None, :]
    ys = np.arange(y0, y1, dtype=np.float32)[:, None]
    g = np.exp(-(((xs - cx) / sx) ** 2 + ((ys - cy) / sy) ** 2) / 2)
    canvas[y0:y1, x0:x1] += g[..., None] * colour * level


def disc(img, cx, cy, r, colour, alpha) -> None:
    """A matte dot: an anti-aliased disc laid over the image (not added: it gives no light)."""
    x0, x1 = max(int(cx - r - 2), 0), min(int(cx + r + 3), W)
    y0, y1 = max(int(cy - r - 2), 0), min(int(cy + r + 3), H)
    if x1 <= x0 or y1 <= y0:
        return
    xs = np.arange(x0, x1, dtype=np.float32)[None, :] - cx
    ys = np.arange(y0, y1, dtype=np.float32)[:, None] - cy
    a = (np.clip(r + 0.5 - np.sqrt(xs * xs + ys * ys), 0, 1) * alpha)[..., None]
    img[y0:y1, x0:x1] = img[y0:y1, x0:x1] * (1 - a) + colour * a


# --- finishing -------------------------------------------------------------------------------
@lru_cache(maxsize=1)
def _lut() -> np.ndarray:
    return (np.clip(to_srgb(np.linspace(0, 1, 4096)), 0, 1) * 255 + 0.5).astype(np.uint8)


@lru_cache(maxsize=1)
def _grain() -> np.ndarray:
    return np.random.default_rng(3).normal(0, 1.4, (H, W, 1)).astype(np.float32)


@lru_cache(maxsize=8)
def vignette(strength: float, border: float = 0.0) -> np.ndarray:
    """(H, W, 1) darkening: a round vignette, times an optional soft dark border 150 px wide."""
    yy, xx = grids()
    v = 1 - strength * np.clip(((xx - W / 2) / (W * 0.8)) ** 2 + ((yy - H * 0.5) / (H * 0.66)) ** 2, 0, 1)
    if border:
        edge = np.minimum(np.minimum(xx, W - 1 - xx), np.minimum(yy, H - 1 - yy))
        v = v * (1 - border * (1 - smooth(edge / 150.0)))
    return v[..., None].astype(np.float32)


@lru_cache(maxsize=1)
def _card_band() -> np.ndarray:
    y = np.arange(H, dtype=np.float32)
    return (smooth((y - 340) / 80) * (1 - smooth((y - 600) / 90)))[:, None, None]


def title_calm(t: float, strength: float) -> np.ndarray:
    """(H, 1, 1) darkening of the title card's rows (card_top 420, two rows) while it shows, the
    first ~3 s, fading out by 3.6 s, so a bright part of a look never sits behind the card."""
    return 1 - strength * float(1 - smooth((t - 2.4) / 1.2)) * _card_band()


def scrim(cx: float, cy: float, rx: float = 600, ry: float = 330) -> np.ndarray:
    """(H, W, 1) 1 at the lyrics' centre falling to 0: how much to calm the frame behind them."""
    yy, xx = grids()
    return np.exp(-(((xx - cx) / rx) ** 2 + ((yy - cy) / ry) ** 2) * 1.2)[..., None].astype(np.float32)


def finish(x: np.ndarray, *, bloom: float, bloom_sigma: float, knee: float, soft: float,
           vig: np.ndarray) -> np.ndarray:
    """The shared last pass: bloom, a soft shoulder above `knee` (nothing burns), the vignette and
    border, sRGB and fine grain -> (H, W, 3) uint8. Works in place on a copy (the frame is 25 MB
    of float, so every pass saved counts)."""
    if bloom:
        small = down(x, 4)
        x = x + up(np.stack([ndimage.gaussian_filter(small[..., c], bloom_sigma) for c in range(3)],
                            -1)) * bloom
    else:
        x = np.array(x, np.float32)
    over = x > knee                      # few pixels: the shoulder only where it bends
    x[over] = knee + soft * (1 - np.exp(-(x[over] - knee) / soft))
    x *= vig
    x *= 4095
    idx = x.astype(np.int32)
    np.clip(idx, 0, 4095, out=idx)
    rgb = _lut()[idx].astype(np.float32)
    rgb += _grain()
    np.clip(rgb, 0, 255, out=rgb)
    return rgb.astype(np.uint8)
