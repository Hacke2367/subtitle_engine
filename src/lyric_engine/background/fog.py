"""The fog look in moonlight (H-035, docs/backgrounds/romantic_lights.md): silver-blue moonlight
falls in rays through gaps in leaves from beyond the top left, brightest where it comes in and
fading as it comes down; slow wisps of fog glow where a ray catches them and darken the air in
shadow; the lower part of the frame falls into darkness. The leaves sway, so the rays shift;
each sung word brightens the rays a little, and a marked word opens a new ray that stays.

Ported from the approved sample songs/_review/backgrounds/lights2/fog_video.py (`full
moonlight`). The light is worked out at quarter size (it is soft) and enlarged once per frame.
The leaves and fog use fixed seeds (the approved stage); new rays use the song's seed."""
from __future__ import annotations

import math

import numpy as np
from PIL import Image
from scipy import ndimage

from . import paint as P

W, H, F = P.W, P.H, 4
h, w = H // F, W // F
SX, SY = -40 / F, -260 / F          # the light, beyond the top left corner (quarter units)
PAD = 40
LIGHT, SCATTER = P.lin("#b9ccff"), P.lin("#46699e")
DARKER = 0.85                       # the owner's "thoda dark theme ... ekdum thoda"
STAGE_SEED = 5


def _radial(gaps: np.ndarray, steps: int = 140, reach: float = 0.92) -> np.ndarray:
    """Light through the gaps, streaked away from the source (PIL affine zooms about it)."""
    im = Image.fromarray(np.ascontiguousarray(gaps, np.float32), "F")
    acc = np.zeros((h, w), np.float32)
    for i in range(steps):
        f = 1.0 - reach * i / steps
        z = im.transform((w, h), Image.AFFINE, (f, 0, SX * (1 - f), 0, f, SY * (1 - f)),
                         resample=Image.BILINEAR)
        acc += np.asarray(z, np.float32) * (1 - i / steps) ** 1.5
    return acc / steps


class Scene:
    look = "fog"
    in_order = False                 # any frame can be drawn on its own

    def __init__(self, facts):
        self.facts = facts
        rng = np.random.default_rng(STAGE_SEED)
        yy, _ = P.grids()
        base = P.gradient([(0.0, "#040a16"), (0.45, "#050b1b"), (1.0, "#010206")])
        P.blob(base, 0, -150, 620, 580, P.lin("#e2eaff"), 0.5 * DARKER)   # where the light comes in
        self.base = base
        u = np.clip((yy - H * 0.42) / (H * 0.58), 0, 1)
        self.dark = (1 - 0.74 * P.smooth(u))[..., None].astype(np.float32)   # the ground in shadow
        cx, cy = facts.lyric_centre
        self.scrim = 1 - 0.25 * P.scrim(cx, cy, 600, 420)         # calm behind the lyrics
        wisp = ndimage.gaussian_filter(rng.standard_normal((h * 2, w * 2)), (7, 16))
        self.wisp_tex = np.clip(0.5 + 0.5 * wisp / wisp.std(), 0, 1).astype(np.float32)
        n1 = ndimage.gaussian_filter(rng.standard_normal((h + 2 * PAD, w + 2 * PAD)), 4.5)
        n2 = ndimage.gaussian_filter(rng.standard_normal((h + 2 * PAD, w + 2 * PAD)), 2.2)
        self.n1, self.n2 = (n1 / n1.std()).astype(np.float32), (n2 / n2.std()).astype(np.float32)
        yq, xq = np.mgrid[0:h, 0:w].astype(np.float32)
        self.yq, self.xq = yq, xq
        self.near_src = np.exp(-(((xq - SX) / (w * 0.75)) ** 2 + ((yq - SY) / (h * 0.45)) ** 2))
        dens = ndimage.gaussian_filter(rng.standard_normal((h * 2, w * 2)), 12.0)
        self.dens_tex = np.clip(0.85 + 0.15 * dens / dens.std(), 0.4, None).astype(np.float32)
        self.falloff = np.exp(-np.hypot(xq - SX, yq - SY) / (h * 0.6)).astype(np.float32)
        song = np.random.default_rng(facts.seed)
        self.new_rays = [(song.uniform(w * 0.1, w * 0.55), song.uniform(-10, h * 0.12))
                         for _ in facts.marks]
        self.norm = float((ndimage.gaussian_filter(_radial(self._gaps(0.0)), 1.0)
                           * self.falloff).max()) + 1e-6    # fixed, so the light never flickers
        self.vig = P.vignette(0.32)

    def describe(self) -> str:
        return f"moonlight rays through fog; {len(self.new_rays)} new ray(s) on marked words"

    def _gaps(self, t: float) -> np.ndarray:
        """The gaps between the leaves near the light at time t (they sway and flutter)."""
        ox = 5 * math.sin(2 * math.pi * t / 7.0)
        oy = 2.5 * math.sin(2 * math.pi * t / 9.0)
        fx = 3 * math.sin(2 * math.pi * t / 2.3 + 1.0)
        a = ndimage.shift(self.n1, (oy, ox), order=1, mode="wrap")[PAD:PAD + h, PAD:PAD + w]
        b = ndimage.shift(self.n2, (0, fx), order=1, mode="wrap")[PAD:PAD + h, PAD:PAD + w]
        g = np.clip((a * 0.8 + b * 0.3 - 0.95) * 3.0, 0, 1) * self.near_src
        for (cx, cy), mark in zip(self.new_rays, self.facts.marks):   # a marked word opens a ray
            u = min(max((t - mark[0]) / 1.2, 0), 1)
            if u > 0:
                g += P.smooth(u) * 0.9 * np.exp(-(((self.xq - cx) / 5) ** 2 + ((self.yq - cy) / 5) ** 2))
        return ndimage.gaussian_filter(np.clip(g, 0, 1), 1.3).astype(np.float32)

    def frame(self, k: int, ink=None) -> np.ndarray:
        """Frame k of the background, (H, W, 3) uint8 sRGB (the fixed scrim keeps the lyrics
        calm, so the text's box is not needed)."""
        t = k / self.facts.fps
        rays = (np.clip(ndimage.gaussian_filter(_radial(self._gaps(t)), 1.0) / self.norm, 0, None)
                ** 1.25) * self.falloff
        swell = 1 + 0.35 * P.envelope(t, self.facts.starts, 0.25, 1.4)   # each word: a little more light
        dx, dy = int(PAD + 8 * t) % w, int(3 * t) % h                      # the fog drifts
        dens = self.dens_tex[dy:dy + h, dx:dx + w]
        wx, wy = int(14 * t) % w, int(2 * t) % h                           # wisps drift across
        wisp = self.wisp_tex[wy:wy + h, wx:wx + w]
        q = (rays * (dens * 0.8 + wisp * 0.45) * 1.1 * DARKER * swell)[..., None] * LIGHT
        q += ndimage.gaussian_filter(rays, 15)[..., None] * 0.22 * SCATTER
        shade = P.up((1 - 0.35 * wisp * (1 - np.clip(rays * 2, 0, 1)))[..., None])   # fog in shadow
        x = self.base * shade
        x += P.up(q.astype(np.float32))
        x *= self.dark
        x *= self.scrim
        x *= P.title_calm(t, 0.5)   # the rays are brightest where the title card sits
        return P.finish(x, bloom=0.35, bloom_sigma=7, knee=0.42, soft=0.5, vig=self.vig)
