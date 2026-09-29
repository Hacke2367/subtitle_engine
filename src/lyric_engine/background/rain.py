"""The rain look (H-034, docs/backgrounds/romantic_lights.md): a soft overcast evening, a few soft
clouds drifting high up, mist on the horizon, a faint tree line far away and wet ground that
mirrors the sky. Rain falls slowly and colourless, each drop at its own depth (far: small, slow,
landing near the horizon; near: bigger, softer, landing low), swaying a little in the wind.
Where a drop lands, a faint ripple spreads and a soft pastel colour rises out of the ground; each
sung word lands a bigger bloom below it, a marked word the biggest, in rose.

Ported from the approved sample songs/_review/backgrounds/lights2/rain3_video.py. The stage (sky,
clouds, trees, ground) uses fixed seeds, so it is the same place in every video; the drops use
the song's seed. One change from the sample: the patch behind the lyrics is calmer (half, not a
third, and reaching lower), since lyrics near the bright horizon fell to 2.4:1 (D-034)."""
from __future__ import annotations

import math

import numpy as np
from PIL import Image, ImageDraw, ImageFilter
from scipy import ndimage

from . import paint as P

W, H, Q = P.W, P.H, 4
HY = 1400                           # the horizon: the ground runs from here to the bottom
RAIN = P.lin("#eef3fb")
PALETTE = [P.lin(c) for c in ("#ff8fb1", "#ffb38a", "#b89cff", "#7fd6d0", "#ffd27a")]
ACCENT = P.lin("#ff7aa6")
N_DROPS = 700
CLOUD_PAD = 900
STAGE_SEED, CLOUD_SEED = 5, 21      # the approved sample's stage


def _stage() -> np.ndarray:
    rng = np.random.default_rng(STAGE_SEED)
    yy, _ = P.grids()
    sky = P.gradient([(0.0, "#3f4b60"), (0.45, "#5f6d84"), (0.69, "#8793a6"), (0.73, "#6d798c"),
                      (0.85, "#4d5869"), (1.0, "#3b4453")])
    clouds = P.fbm(rng, ((40, 2.0, 1.0), (12, 2.0, 0.4))) * np.clip(1 - yy / HY, 0, 1)
    sky *= (1 + 0.06 * clouds)[..., None]
    sky += np.exp(-((yy - HY + 20) / 130) ** 2)[..., None] * P.lin("#b8c2d0") * 0.14   # horizon mist
    top = HY - 70 - 45 * np.clip(ndimage.gaussian_filter(rng.standard_normal(W), 18) * 4, -1, 1) \
        - 20 * np.clip(ndimage.gaussian_filter(rng.standard_normal(W), 4) * 3, -1, 1)
    trees = ndimage.gaussian_filter(((yy > top[None, :]) & (yy < HY)).astype(np.float32), 3)
    sky = sky * (1 - 0.18 * trees[..., None]) + trees[..., None] * P.lin("#56627a") * 0.05
    g = np.clip((yy - HY) / 8, 0, 1)
    tex = 1 + 0.02 * P.fbm(rng, ((12, 2.0, 1.0),))
    ground = P.gradient([(0.0, "#000000"), (HY / H, "#6f7b8e"), (1.0, "#2a313c")]) * tex[..., None]
    rows = np.clip(2 * HY - np.arange(H), 0, H - 1)            # the wet ground mirrors the sky
    mirror = ndimage.gaussian_filter(sky[rows], (5, 1.5, 0)) * 0.6
    wgt = (np.exp(-np.clip(np.arange(H) - HY, 0, None) / 260) * 0.7)[:, None, None]
    ground = ground * (1 - wgt) + mirror * wgt
    base = sky * (1 - g[..., None]) + ground * g[..., None]
    base += (np.exp(-((yy - HY) / 60) ** 2) * 0.06)[..., None] * P.lin("#c3ccd8")   # no hard edge
    return base.astype(np.float32)


def _clouds() -> tuple[np.ndarray, np.ndarray]:
    """A few soft clouds high in the sky, wider than the frame so they can drift: (colour,
    alpha), brighter tops, darker undersides."""
    rng = np.random.default_rng(CLOUD_SEED)
    h, w = HY // Q, (W + CLOUD_PAD) // Q
    d = sum(wt * ndimage.gaussian_filter(rng.standard_normal((h, w)), sg, mode="wrap")
            for sg, wt in (((16, 42), 1.0), ((6, 14), 0.35), ((2, 5), 0.06)))
    d = (d - d.mean()) / d.std()
    rows = np.arange(h, dtype=np.float32)[:, None] / h
    dens = np.clip((d - 0.35) / 1.1, 0, 1) ** 1.2 * np.clip((0.62 - rows) / 0.3, 0, 1)
    dens = ndimage.gaussian_filter(dens, 2.5)
    lit = np.clip((dens - np.roll(dens, 6, axis=0)) * 2 + 0.5, 0, 1)
    dens, lit = P.resize(dens, W + CLOUD_PAD, HY), P.resize(lit, W + CLOUD_PAD, HY)
    colour = (P.lin("#7a869b")[None, None, :] * (1 - lit[..., None])
              + P.lin("#a3adbd")[None, None, :] * lit[..., None])
    colour = colour * (1 - 0.25 * dens[..., None]) + P.lin("#5b687e") * 0.25 * dens[..., None]
    return colour.astype(np.float32), (dens * 0.55).astype(np.float32)


class Scene:
    look = "rain"
    in_order = False                 # any frame can be drawn on its own

    def __init__(self, facts):
        self.facts = facts
        self.base = _stage()
        self.clouds = _clouds()
        rng = np.random.default_rng(facts.seed)
        z = rng.uniform(0, 1, N_DROPS) ** 0.8                      # depth: 0 far, 1 near
        self.z = z
        self.x = rng.uniform(-60, W + 60, N_DROPS)
        self.phase = rng.uniform(0, 1, N_DROPS)
        self.col = rng.integers(len(PALETTE), size=N_DROPS)
        self.glow = rng.uniform(0, 1, N_DROPS) < 0.55
        self.v = (300 + 420 * z) * rng.uniform(0.88, 1.12, N_DROPS)   # slow rain
        self.land = HY + 30 + (H - HY - 60) * z
        self.top = -60.0
        bx, by = facts.block_centre     # calm behind the lyrics: the sky near the horizon is
        self.scrim = 1 - 0.5 * P.scrim(bx, by + 40, 680, 420)      # bright, so more than the sample
        self.vig = P.vignette(0.22)

    def describe(self) -> str:
        return f"slow colourless rain ({N_DROPS} drops), colour rising where it lands"

    def frame(self, k: int, ink=None) -> np.ndarray:
        """Frame k of the background, (H, W, 3) uint8 sRGB (the fixed scrim keeps the lyrics
        calm, so the text's box is not needed)."""
        t = k / self.facts.fps
        x = self.base.copy()
        off = int(CLOUD_PAD - 7 * t) % CLOUD_PAD                # the clouds drift slowly
        ca = self.clouds[1][:, off:off + W, None]
        x[:HY] *= 1 - ca
        x[:HY] += self.clouds[0][:, off:off + W] * ca
        streaks, near, rings = (Image.new("L", (W, H), 0) for _ in range(3))
        ds, dn, dr = ImageDraw.Draw(streaks), ImageDraw.Draw(near), ImageDraw.Draw(rings)
        colour = np.zeros((H // Q, W // Q, 3), np.float32)
        wind = 0.08 + 0.03 * math.sin(2 * math.pi * t / 9)
        for i in range(N_DROPS):
            z, v, land = self.z[i], self.v[i], self.land[i]
            period = (land - self.top) / v
            s = (t + self.phase[i] * period) % period            # time since its last landing
            y = self.top + v * s
            x0 = self.x[i] + wind * (y - self.top) + 6 * math.sin(t * 0.8 + i)
            length = max(10, v / 22)                             # a slow drop: a short streak
            (dn if z > 0.88 else ds).line([(x0 - wind * length, y - length), (x0, y)],
                                          fill=int(60 + 150 * z), width=max(1, int(1 + 2.5 * z)))
            if s < 1.5:                                          # it landed s seconds ago
                lx = self.x[i] + wind * (land - self.top) + 6 * math.sin((t - s) * 0.8 + i)
                r = (4 + 60 * z) * (0.3 + s / 1.5)
                fade = (1 - s / 1.5) ** 2
                asp = 0.16 + 0.22 * z
                dr.ellipse([lx - r, land - r * asp, lx + r, land + r * asp],
                           outline=int(90 * fade), width=1 if z < 0.6 else 2)
                if self.glow[i]:                                 # colour rises out of the ground
                    c = PALETTE[self.col[i]]
                    P.stamp(colour, Q, lx, land, (16 + 44 * z) * (0.6 + s), (5 + 12 * z) * (0.6 + s),
                            c, 0.14 * fade)
                    P.stamp(colour, Q, lx, land - (40 + 140 * z) * s, 8 + 18 * z, 26 + 60 * z,
                            c, 0.075 * fade)
        for j, (s, marked, cx, _cy) in enumerate(self.facts.words):   # each sung word: a bloom
            age = t - s
            if 0 <= age < 2.2:
                ly = HY + 260
                r = (70 if marked else 45) * (0.4 + age)
                fade = (1 - age / 2.2) ** 2
                dr.ellipse([cx - r, ly - r * 0.3, cx + r, ly + r * 0.3], outline=int(230 * fade), width=3)
                c = ACCENT if marked else PALETTE[j % len(PALETTE)]
                P.stamp(colour, Q, cx, ly, r * 1.1, r * 0.35, c, (0.22 if marked else 0.14) * fade)
                P.stamp(colour, Q, cx, ly - 160 * age, r * 0.45, r * 0.9, c,
                        (0.07 if marked else 0.045) * fade)
        streak = np.asarray(streaks.filter(ImageFilter.GaussianBlur(0.6)), np.float32) / 255
        streak += np.asarray(near.filter(ImageFilter.GaussianBlur(3.0)), np.float32) / 255 * 0.7
        ring = np.asarray(rings.filter(ImageFilter.GaussianBlur(0.8)), np.float32) / 255
        x += (streak * 0.22)[..., None] * RAIN + (ring * 0.12)[..., None] * RAIN
        col = P.up(colour)
        x += col + ring[..., None] * col * 1.2                   # the rings catch a little colour
        x *= self.scrim
        return P.finish(x, bloom=0.2, bloom_sigma=6, knee=0.5, soft=0.45, vig=self.vig)
