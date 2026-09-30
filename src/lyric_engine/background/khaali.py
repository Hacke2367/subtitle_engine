"""The khaali look (H-037, docs/backgrounds/sad_khaali_jagah.md): "Khaali jagah", an empty bench under
a streetlight in the rain, at night. Cold light falls in a cone through steady rain onto the empty
bench, with a pool of light and a reflection on the wet ground and the city's lights far away in
the fog. The camera moves in very slowly over the song, the lamp and bench more than the far lights.
On each marked word the place turns warm for a moment, like a memory, and goes cold again; on the
last line the streetlight falters once and goes out.

Ported from the sample songs/_review/backgrounds/sad/khaali_video.py, with a calm patch behind the
lyric block (0.45: the lit rain in the cone would otherwise fall to 1.9:1 behind the text). Every
frame is a pure function of its time, so frames can be drawn in any order (worker processes). The
big arrays are kept as float16 (the stage twice, cold and warm, is about 50 MB this way)."""
from __future__ import annotations

import math

import numpy as np
from PIL import Image, ImageDraw, ImageFilter
from scipy import ndimage

from . import paint as P

W, H = P.W, P.H
GROUND = 1500                        # the wet ground starts here
LX, LY = 690, 610                    # the lamp
PUSH_NEAR, PUSH_FAR = 0.06, 0.02     # how far the camera moves in over the song (near things, far)
CENTRE = (600.0, 1350.0)             # it moves in towards the bench
N_DROPS, N_SPLASH = 2400, 160
SCRIM = 0.45                         # calm patch behind the lyric block


def _mask(draw_fn, blur: float = 0.0) -> np.ndarray:
    """A silhouette drawn at 2x (clean edges), 0..1 at full size."""
    im = Image.new("L", (W * 2, H * 2), 0)
    draw_fn(ImageDraw.Draw(im), lambda *v: [2 * c for c in v])
    m = np.asarray(im.resize((W, H), Image.LANCZOS), np.float32) / 255
    return ndimage.gaussian_filter(m, blur) if blur else m


def _stage(warm: bool) -> dict:
    """The place drawn once: far (sky and city lights), the lamp's light, the rim light; the cold
    stage also holds the silhouettes and the cone. warm: the memory's palette."""
    rng = np.random.default_rng(4)
    yy, xx = P.grids()
    lamp = P.lin("#ffc27a") if warm else P.lin("#dfe7ff")
    fog = P.lin("#b88a6a") if warm else P.lin("#6f84a8")
    far = (P.gradient([(0.0, "#0d0806"), (0.55, "#1a110c"), (GROUND / H, "#2a1a12"), (1.0, "#090605")])
           if warm else
           P.gradient([(0.0, "#05070d"), (0.55, "#0a0f1c"), (GROUND / H, "#141a2a"), (1.0, "#05060a")]))
    city = np.zeros_like(far)
    for _ in range(40):                                        # the city's lights, far, in the fog
        P.point(city, rng.uniform(0, W), GROUND - 120 + rng.normal(0, 30),
                lamp * 0.6 + P.lin("#ffb070") * 0.4, rng.uniform(0.03, 0.08), 26)
    far += P.defocus(city, 26)
    del city
    ang = np.arctan2(xx - LX, yy - LY)
    dist = np.hypot(xx - LX, yy - LY)
    cone = (np.exp(-(ang / 0.42) ** 2) * (yy > LY) / (1 + (dist / 900) ** 2)).astype(np.float32)
    del ang, dist
    mist = 0.8 + 0.2 * P.fbm(rng, ((24, 2.0, 1.0),))
    light = (cone * mist * 0.10)[..., None] * lamp
    P.blob(light, LX, LY + 10, 70, 45, lamp, 0.9)                    # the lamp itself, soft
    P.blob(light, LX, LY + 10, 220, 170, lamp, 0.10)
    pool = np.exp(-(((xx - LX) / 330) ** 2 + ((yy - (GROUND + 130)) / 90) ** 2)) * (yy > GROUND)
    light += (pool * 0.12)[..., None] * lamp                         # its pool on the wet ground
    refl = (np.exp(-((xx - LX) / 40) ** 2) * np.clip((yy - GROUND) / 400, 0, 1)
            * np.exp(-(yy - GROUND) / 300) * (yy > GROUND))
    light += (refl * 0.25)[..., None] * lamp                         # its reflection
    del pool, refl
    light += (P.soft_blur(np.clip(cone, 0, 1)[..., None], 80)[..., 0] * 0.05)[..., None] * fog
    bench = _mask(lambda d, s: (d.rounded_rectangle(s(360, 1512, 770, 1540), radius=8, fill=255),
                                d.rounded_rectangle(s(360, 1418, 770, 1440), radius=8, fill=255),
                                d.rounded_rectangle(s(360, 1456, 770, 1476), radius=8, fill=255),
                                *[d.rectangle(s(x0, 1418, x0 + 18, 1655), fill=255) for x0 in (384, 734)],
                                *[d.rectangle(s(x0, 1530, x0 + 16, 1665), fill=255) for x0 in (400, 718)],
                                d.rectangle(s(384, 1600, 752, 1612), fill=255)), 0.8)
    rim = np.clip(bench - np.roll(bench, -3, axis=0), 0, 1)        # the light catches its top edges
    out = {"far": far.astype(np.float16), "light": light.astype(np.float16),
           "rim": (rim[..., None] * 0.25 * lamp).astype(np.float16), "lamp": lamp}
    if not warm:
        post = _mask(lambda d, s: (d.rectangle(s(772, LY - 20, 786, 1640), fill=255),
                                   d.line(s(779, LY - 10, 740, LY - 40, 690, LY - 35), fill=255, width=10),
                                   d.polygon(s(650, LY - 30, 730, LY - 30, 715, LY + 5, 665, LY + 5),
                                             fill=255)), 0.8)
        shadow = _mask(lambda d, s: d.polygon(s(360, 1660, 770, 1660, 860, 1720, 450, 1720), fill=255), 6)
        out.update(cone=cone.astype(np.float16), sil=np.maximum(post, bench).astype(np.float16),
                   shadow=shadow.astype(np.float16))
    return out


def _zoom(a: np.ndarray, z: float) -> np.ndarray:
    """a (h, w[, c]) seen z times closer, about CENTRE (bilinear), as a new float32 array."""
    if abs(z - 1) < 1e-6:
        return a.astype(np.float32)          # callers add to it: never hand out the stage
    cx, cy = CENTRE
    box = (cx - cx / z, cy - cy / z, cx + (W - cx) / z, cy + (H - cy) / z)
    if a.ndim == 2:
        return P.resize(a, W, H, box)
    return np.stack([P.resize(a[..., c], W, H, box) for c in range(a.shape[2])], -1)


def memory_level(t: float, marks) -> float:
    """Warm for a moment on each marked word: rises over 0.8 s, holds 1.2 s, fades over 2.5 s, never
    all the way (0.9): a memory, not a new place."""
    best = 0.0
    for s in marks:
        a = t - s
        if a < 0 or a > 4.5:
            continue
        v = P.smooth(a / 0.8) if a < 2.0 else 1 - P.smooth((a - 2.0) / 2.5)
        best = max(best, 0.9 * float(v))
    return best


def lamp_level(t: float, last: float) -> float:
    """The streetlight: on, then at the last line it falters once and goes out."""
    if t < last:
        return 1.0
    a = t - last
    if a < 0.18:
        return 1 - 0.55 * float(P.smooth(a / 0.18))                     # it falters ...
    if a < 0.45:
        return 0.45 + 0.4 * float(P.smooth((a - 0.18) / 0.27))          # ... catches ...
    return 0.85 * (1 - float(P.smooth((a - 0.45) / 1.6)))               # ... and dies


class Scene:
    look = "khaali"
    in_order = False                 # any frame can be drawn on its own

    def __init__(self, facts):
        self.facts = facts
        self.cold, self.warm = _stage(False), _stage(True)
        rng = np.random.default_rng(facts.seed)
        self.x = rng.uniform(-80, W, N_DROPS)
        self.y0 = rng.uniform(0, H + 200, N_DROPS)
        self.v = rng.uniform(900, 1300, N_DROPS)
        self.len = rng.uniform(25, 70, N_DROPS)
        self.a = rng.uniform(0.3, 1.0, N_DROPS)
        self.splash = np.stack([rng.uniform(LX - 330, LX + 330, N_SPLASH),
                                rng.uniform(GROUND + 60, GROUND + 230, N_SPLASH),
                                rng.uniform(0, 1, N_SPLASH), rng.uniform(0.35, 0.8, N_SPLASH)], 1)
        bx, by = facts.block_centre
        self.scrim = (1 - SCRIM * P.scrim(bx, by + 40, 680, 420)).astype(np.float32)
        self.vig = P.vignette(0.0, border=0.4)
        self.dark = P.lin("#0a0c12") * 1.4
        self.marks = [w[0] for w in facts.marks]
        self.last = facts.last_line_s if facts.last_line_s is not None else 0.85 * facts.duration

    def describe(self) -> str:
        return (f"an empty bench under a streetlight in the rain; warm memory on {len(self.marks)} "
                f"marked word(s); the lamp goes out at {self.last:.1f} s")

    def _streaks(self, t: float) -> np.ndarray:
        c = Image.new("L", (W, H), 0)
        d = ImageDraw.Draw(c)
        y = (self.y0 + self.v * t) % (H + 200) - 100
        for x, yy, length, a in zip(self.x + 0.1 * (y + 100), y, self.len, self.a):
            d.line([(x, yy), (x + 0.1 * length, yy + length)], fill=int(a * 255 * 0.5), width=1)
        for sx, sy, ph, per in self.splash:                         # splashes on the wet ground
            u = ((t / per) + ph) % 1.0
            if u < 0.3:
                r = 2 + 10 * u / 0.3
                d.ellipse([sx - r, sy - r * 0.3, sx + r, sy + r * 0.3], outline=int(150 * (1 - u / 0.3)))
        return np.asarray(c.filter(ImageFilter.GaussianBlur(0.6)), np.float32) / 255

    def frame(self, k: int, ink=None) -> np.ndarray:
        """Frame k of the background, (H, W, 3) uint8 sRGB (the calm patch is fixed, so the text's
        box is not needed)."""
        t = k / self.facts.fps
        e = float(P.smooth(t / self.facts.duration))
        zn, zf = 1 + PUSH_NEAR * e, 1 + PUSH_FAR * e
        m, lv = memory_level(t, self.marks), lamp_level(t, self.last)

        def mix(key):
            cold = self.cold[key]
            if m <= 0:
                return cold
            return cold.astype(np.float32) * (1 - m) + self.warm[key].astype(np.float32) * m

        lamp = self.cold["lamp"] * (1 - m) + self.warm["lamp"] * m
        x = _zoom(mix("far"), zf)
        x += _zoom(mix("light"), zn) * lv
        cone = _zoom(self.cold["cone"], zn)
        s = self._streaks(t) * (0.03 + cone * 1.6 * lv)
        x += s[..., None] * (lamp * 0.6 + 0.4)
        x *= (1 - 0.5 * _zoom(self.cold["shadow"], zn) * lv)[..., None]
        sil = _zoom(self.cold["sil"], zn)[..., None]
        x = x * (1 - sil) + sil * self.dark
        x += _zoom(mix("rim"), zn) * lv
        x *= self.scrim
        return P.finish(x, bloom=0.25, bloom_sigma=6, knee=0.45, soft=0.5, vig=self.vig)
