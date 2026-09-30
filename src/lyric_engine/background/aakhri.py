"""Aakhri patta (the last leaf): a big old peepal at dusk, a near-black silhouette against a rose-lit
high cloud deck. Every sung word shakes leaves loose, the crown empties with the song, a marked word
is a gust, and on the last line the one backlit leaf that hung alone lets go and drifts down toward
the camera, glowing against the ember line, to land on the drift.

Standalone Scene module (engine contract): frame(k) is a pure function of k and the song facts."""
from __future__ import annotations

import math

import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage

from . import paint as P

W, H, Q = P.W, P.H, 4
HORIZON = 1566
HERO = (606.0, 398.0)            # where the last leaf's stalk ends
HERO_L = 80.0                    # its blade length (crown leaves are 34-72 px)
GAP = (606.0, 440.0, 135.0)      # the clear gap around it (x, y, r)
TAU = 2 * math.pi

ROSE = P.lin("#e0a090")
EMBER = P.lin("#d88a52")
ROSE2 = P.lin("#c890aa")
EMBER_DEEP = P.lin("#b4502c")


def smooth(x):
    return P.smooth(x)


# --- the peepal leaf --------------------------------------------------------------------------
def _catmull(p, per=5):
    p = np.asarray(p, np.float64)
    pp = np.concatenate([p[:1], p, p[-1:]])
    out = []
    for i in range(1, len(pp) - 2):
        p0, p1, p2, p3 = pp[i - 1], pp[i], pp[i + 1], pp[i + 2]
        for t in np.linspace(0, 1, per, endpoint=False):
            out.append(0.5 * (2 * p1 + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t * t
                              + (-p0 + 3 * p1 - 3 * p2 + p3) * t ** 3))
    out.append(pp[-2])
    return np.array(out)


# one half of a blade: base (0) to the tip of the long drip tail (1); broad heart at the stalk
HALF = _catmull([(0.0, 0.0), (-0.04, 0.07), (-0.035, 0.17), (0.02, 0.27), (0.12, 0.345), (0.25, 0.37),
                 (0.38, 0.345), (0.50, 0.275), (0.60, 0.18), (0.68, 0.10), (0.76, 0.05), (0.86, 0.022),
                 (0.94, 0.009), (1.0, 0.0)])
U0 = 0.4                         # the blade's own centre, along its length


def blade_uv(flip: float, curl: float = 0.0, bend: float = 0.0) -> np.ndarray:
    """Blade outline (N, 2) in leaf units: u along the leaf (0 base .. 1 tail tip), v across.
    flip 0..1: the turn about the midrib (0 edge-on); curl: one half more foreshortened; bend:
    the midrib curves sideways."""
    fl = max(abs(flip), 0.07)
    a = HALF[:, 0]
    mid = bend * (0.22 * a * a + 0.9 * np.clip(a - 0.72, 0, None) ** 2) * (0.4 + 0.6 * fl)
    top = np.stack([a, mid - HALF[:, 1] * fl * (1 - curl)], -1)
    bot = np.stack([a, mid + HALF[:, 1] * fl * (1 + curl)], -1)[::-1]
    return np.concatenate([top, bot])


def to_px(uv, L, rot, cx, cy):
    """Leaf units -> px, blade centre at (cx, cy), +u pointing along angle `rot` (pi/2 = tail down)."""
    c, s = math.cos(rot), math.sin(rot)
    u = (uv[:, 0] - U0) * L
    v = uv[:, 1] * L
    return np.stack([cx + u * c - v * s, cy + u * s + v * c], -1)


def stalk_px(L, rot, cx, cy, pet=0.35):
    c, s = math.cos(rot), math.sin(rot)
    a, b = -U0 * L, -(U0 + pet) * L
    return [(cx + a * c, cy + a * s), (cx + b * c, cy + b * s)]


def leaf_alpha(L, flip, rot, curl=0.0, bend=0.0, ss=3, pet=0.35, veins=False, pad=6):
    """A leaf as a coverage patch. Returns (alpha float32 (h, w), ox, oy) where (ox, oy) is the
    patch's top-left relative to the blade centre; also the vein image when asked."""
    uv = blade_uv(flip, curl, bend)
    pts = to_px(uv, L, rot, 0.0, 0.0)
    st = stalk_px(L, rot, 0.0, 0.0, pet)
    allp = np.concatenate([pts, np.array(st)])
    x0, y0 = np.floor(allp.min(0)) - pad
    x1, y1 = np.ceil(allp.max(0)) + pad
    w, h = int(x1 - x0), int(y1 - y0)
    im = Image.new("L", (w * ss, h * ss), 0)
    d = ImageDraw.Draw(im)
    d.polygon([((px - x0) * ss, (py - y0) * ss) for px, py in pts], fill=255)
    d.line([((px - x0) * ss, (py - y0) * ss) for px, py in st], fill=255, width=max(1, int(ss * max(1.0, L / 45))))
    a = np.asarray(im.reduce(ss), np.float32) / 255.0 if ss > 1 else np.asarray(im, np.float32) / 255.0
    vein = None
    if veins:
        vim = Image.new("L", (w * ss, h * ss), 0)
        vd = ImageDraw.Draw(vim)
        fl = max(abs(flip), 0.07)
        mid = lambda aa: bend * (0.22 * aa * aa + 0.9 * np.clip(aa - 0.72, 0, None) ** 2) * (0.4 + 0.6 * fl)
        ma = np.linspace(-0.02, 0.96, 12)
        mp = to_px(np.stack([ma, mid(ma)], -1), L, rot, 0, 0)
        vd.line([((px - x0) * ss, (py - y0) * ss) for px, py in mp], fill=255, width=max(1, int(ss * L / 60)))
        for i in range(7):
            ai = 0.06 + 0.085 * i
            for side, kk in ((-1, 1 - curl), (1, 1 + curl)):
                aa = np.array([ai, ai + 0.06, ai + 0.13, ai + 0.2])
                frac = np.array([0.0, 0.5, 0.8, 0.93])
                vv = mid(aa) + side * frac * np.interp(aa, HALF[:, 0].clip(0, None), HALF[:, 1]) * fl * kk
                vp = to_px(np.stack([aa, vv], -1), L, rot, 0, 0)
                vd.line([((px - x0) * ss, (py - y0) * ss) for px, py in vp], fill=255,
                        width=max(1, int(ss * L / 120)))
        vein = np.asarray(vim.reduce(ss), np.float32) / 255.0
    return a, int(x0), int(y0), vein


def blit(x, cx, cy, a, ox, oy, col, *, op=1.0, rim_col=None, rim_amt=0.0, rim_r=2, quiet=1.0):
    """Lay a coverage patch over x (linear light): dark body colour `col`, opacity `op`, a lit rim on
    its upper-right edge (added light, dimmed by `quiet` where the lyrics are)."""
    px, py = int(round(cx)) + ox, int(round(cy)) + oy
    h, w = a.shape
    xa, ya, xb, yb = max(px, 0), max(py, 0), min(px + w, W), min(py + h, H)
    if xb <= xa or yb <= ya:
        return
    sub = a[ya - py:yb - py, xa - px:xb - px]
    reg = x[ya:yb, xa:xb]
    m = (sub * op)[..., None]
    reg *= 1 - m
    reg += m * col
    if rim_col is not None and rim_amt > 0:
        sh = np.zeros_like(a)
        sh[rim_r:, :-rim_r] = a[:-rim_r, rim_r:]
        rim = np.clip(a - sh, 0, 1)[ya - py:yb - py, xa - px:xb - px]
        reg += (rim * rim_amt * quiet * op)[..., None] * rim_col


# --- the tree (fixed: the place) -----------------------------------------------------------------
def grow(rng, x, y, ang, length, w0, curv, depth, segs, tips, step=22.0):
    n = max(2, int(length / step))
    w = w0
    for i in range(n):
        ang += curv + rng.normal(0, 0.07 + 0.02 * depth)
        st = step * (0.85 + 0.3 * rng.random())
        nx, ny = x + math.cos(ang) * st, y + math.sin(ang) * st
        if math.hypot(nx - GAP[0], ny - GAP[1]) < GAP[2] + 10 or (ny > 790 and nx > 175) or ny < -40 or nx > W + 80:
            break
        wn = max(w0 * (1 - 0.62 * (i + 1) / n), 1.3)
        segs.append((x, y, nx, ny, w, wn))
        x, y, w = nx, ny, wn
        if depth < 5 and 1 <= i < n - 1 and wn > 2.2 and rng.random() < 0.22:
            side = rng.choice([-1, 1])
            grow(rng, x, y, ang + side * rng.uniform(0.45, 0.85), (length - i * step) * rng.uniform(0.5, 0.85),
                 wn * 0.72, curv * 0.6 + rng.normal(0, 0.015), depth + 1, segs, tips)
    if depth < 5 and length > 50 and w > 1.6 and rng.random() < 0.75:
        for side in (-1, 1):
            if rng.random() < 0.7:
                grow(rng, x, y, ang + side * rng.uniform(0.4, 0.75), rng.uniform(40, 85), max(w * 0.75, 1.4),
                     rng.normal(0.012, 0.015), depth + 1, segs, tips, step=17.0)
    tips.append((x, y, ang, depth, w))


def limb(rng, pts, w0, w1, segs, tips, every=90.0, reach=(120, 260), sprout=True):
    """A main limb through control points (Catmull-Rom), sprouting side branches as it goes."""
    dense = _catmull(pts, per=12)
    d = np.hypot(*np.diff(dense, axis=0).T)
    cum = np.concatenate([[0], np.cumsum(d)])
    tot = cum[-1]
    nxt = every * rng.uniform(0.4, 1.0)
    for i in range(len(dense) - 1):
        u0, u1 = cum[i] / tot, cum[i + 1] / tot
        segs.append((*dense[i], *dense[i + 1], w0 + (w1 - w0) * u0, w0 + (w1 - w0) * u1))
        if sprout and cum[i] > nxt and cum[i] < tot - 40:
            nxt += every * rng.uniform(0.6, 1.3)
            ang = math.atan2(dense[i + 1][1] - dense[i][1], dense[i + 1][0] - dense[i][0])
            side = rng.choice([-1, 1])
            w = w0 + (w1 - w0) * u0
            grow(rng, *dense[i], ang + side * rng.uniform(0.5, 0.95), rng.uniform(*reach), max(w * 0.5, 3.0),
                 rng.normal(0, 0.012), 1, segs, tips)
    if sprout:
        ang = math.atan2(dense[-1][1] - dense[-2][1], dense[-1][0] - dense[-2][0])
        grow(rng, *dense[-1], ang, 120, max(w1, 3.0), 0.0, 1, segs, tips)


def trunk_right(ys):
    ys = np.asarray(ys, np.float64)
    top = 0.72 + 0.28 * np.clip(ys / 600.0, 0, 1)
    x = (58 + 10 * np.sin(ys / 130.0 + 0.8) + 5 * np.sin(ys / 37.0)) * top
    x += 70 * np.clip((ys - 1640.0) / 190.0, 0, 1) ** 2.2
    return x + 1.6 * np.sin(ys / 9.0 + 1.0)


def make_tree():
    rng = np.random.default_rng(1947)
    segs, tips = [], []
    for pts, w0, w1 in (
            ([(40, 930), (190, 835), (360, 735), (560, 665), (760, 625), (930, 570), (1100, 470)], 54, 12),
            ([(60, 720), (165, 530), (285, 350), (380, 205), (440, 90), (475, -40)], 40, 10),
            ([(50, 500), (200, 365), (330, 280), (470, 232), (640, 215), (830, 185), (1100, 100)], 34, 8),
            ([(45, 120), (230, 70), (520, 45), (820, 25), (1100, 10)], 20, 7),
            ([(760, 625), (850, 520), (935, 400), (1000, 290), (1100, 170)], 24, 8)):
        limb(rng, pts, w0, w1, segs, tips, every=70.0, reach=(130, 300))
    root_segs = []
    for pts, w0, w1 in (([(50, 1700), (140, 1765), (300, 1812), (470, 1850), (640, 1885)], 62, 7),
                        ([(30, 1760), (110, 1840), (210, 1905), (310, 1965)], 52, 9),
                        ([(80, 1730), (230, 1762), (400, 1790), (540, 1806)], 30, 5)):
        limb(rng, pts, w0, w1, root_segs, [], sprout=False)
    segs = segs + root_segs
    segs = np.array(segs)
    tips = np.array(tips)
    # the last leaf's twig: from the nearest free node, arching out to its stalk end
    ends = segs[:, 2:4]
    cand = np.hypot(ends[:, 0] - HERO[0], ends[:, 1] - HERO[1])
    cand[(ends[:, 0] > HERO[0] + 40) | (ends[:, 1] > HERO[1] + 30)] = 1e9
    j = int(np.argmin(cand + np.where(segs[:, 5] < 2.6, 1e5, 0)))
    sx, sy = ends[j]
    mx, my = (sx + HERO[0]) / 2 - 15, min(sy, HERO[1]) - 60
    hero_twig = [(sx, sy, mx, my, segs[j, 5], 3.0)]
    bez = []
    for t in np.linspace(0, 1, 9):
        bx = (1 - t) ** 2 * sx + 2 * (1 - t) * t * mx + t * t * HERO[0]
        by = (1 - t) ** 2 * sy + 2 * (1 - t) * t * (my) + t * t * HERO[1]
        bez.append((bx, by))
    hero_segs = []
    for a, b, wa, wb in zip(bez[:-1], bez[1:], np.linspace(min(segs[j, 5], 5.0), 2.6, 8), np.linspace(min(segs[j, 5], 5.0), 2.6, 9)[1:]):
        hero_segs.append((a[0], a[1], b[0], b[1], wa, wb))
    return segs, tips, np.array(hero_segs)


def draw_wood(segs, hero_segs) -> Image.Image:
    """The bole, roots and every limb on a 2x canvas (255 where wood)."""
    S = 2
    im = Image.new("L", (W * S, H * S), 0)
    d = ImageDraw.Draw(im)
    ys = np.linspace(-20, 1830, 160)
    right = list(zip(trunk_right(ys), ys))
    poly = [(-80, -20)] + right + [(150, 1830), (-80, 1830)]
    d.polygon([(px * S, py * S) for px, py in poly], fill=255)
    for grp in (segs, hero_segs):
        for x0, y0, x1, y1, w0, w1 in grp:
            dx, dy = x1 - x0, y1 - y0
            ln = math.hypot(dx, dy) + 1e-9
            for (w, px, py) in ((w0, x0, y0), (w1, x1, y1)):
                pass
            nx0, ny0 = -dy / ln * w0 / 2, dx / ln * w0 / 2
            nx1, ny1 = -dy / ln * w1 / 2, dx / ln * w1 / 2
            d.polygon([((x0 + nx0) * S, (y0 + ny0) * S), ((x1 + nx1) * S, (y1 + ny1) * S),
                       ((x1 - nx1) * S, (y1 - ny1) * S), ((x0 - nx0) * S, (y0 - ny0) * S)], fill=255)
            if w1 > 1.6:
                d.ellipse([(x1 - w1 / 2) * S, (y1 - w1 / 2) * S, (x1 + w1 / 2) * S, (y1 + w1 / 2) * S], fill=255)
    return im


# --- far village / tree rows --------------------------------------------------------------------
def canopy(d, rng, cx, base, w, h, s=2, fill=255):
    """An irregular multi-lobed canopy on a forking trunk, with broken edges."""
    ccx, ccy = cx, base - h * 0.62
    rx, ry = w / 2, h * 0.36
    n = int(14 + w * h / 650)
    for _ in range(n):
        a = rng.uniform(0, TAU)
        rad = math.sqrt(rng.uniform(0.15, 1.0))
        px, py = ccx + math.cos(a) * rx * rad, ccy + math.sin(a) * ry * rad * (0.85 if math.sin(a) > 0 else 1.0)
        r = rng.uniform(0.09, 0.2) * h
        d.ellipse([(px - r) * s, (py - r * 0.85) * s, (px + r) * s, (py + r * 0.85) * s], fill=fill)
    for _ in range(int(n * 0.9)):                        # small clumps on the edge: broken outline
        a = rng.uniform(0, TAU)
        px, py = ccx + math.cos(a) * rx * rng.uniform(0.92, 1.12), ccy + math.sin(a) * ry * rng.uniform(0.9, 1.15)
        r = rng.uniform(0.025, 0.06) * h
        d.ellipse([(px - r) * s, (py - r) * s, (px + r) * s, (py + r) * s], fill=fill)
    d.ellipse([(ccx - rx * 0.6) * s, (ccy - ry * 0.55) * s, (ccx + rx * 0.6) * s, (ccy + ry * 0.6) * s], fill=fill)
    tw = max(1.5, h / 34)
    for _ in range(rng.integers(2, 4)):                   # forking trunk
        bx = cx + rng.normal(0, w * 0.06)
        ty = ccy + rng.uniform(-0.1, 0.25) * ry
        tx = bx + rng.normal(0, w * 0.12)
        my = base - (base - ty) * 0.5
        d.line([(cx * s, base * s), ((bx + tx) / 2 * s, my * s), (tx * s, ty * s)], fill=fill, width=int(tw * s))
    d.line([(cx * s, (base + 4) * s), (cx * s, (base - h * 0.3) * s)], fill=fill, width=int(tw * 1.6 * s))


def building(d, rng, x, base, w, h, s=2, fill=255):
    """A flat-roofed house: parapet steps, sometimes a water tank or a small dome."""
    d.rectangle([x * s, (base - h) * s, (x + w) * s, (base + 3) * s], fill=fill)
    if rng.random() < 0.8:
        sw = w * rng.uniform(0.35, 0.6)
        sx = x + (rng.uniform(0, w - sw))
        d.rectangle([sx * s, (base - h - h * 0.3) * s, (sx + sw) * s, (base - h) * s], fill=fill)
    if rng.random() < 0.5:
        tx = x + rng.uniform(0.1, 0.7) * w
        tw, th = max(4, w * 0.22), max(5, h * 0.3)
        d.rectangle([tx * s, (base - h - th - 3) * s, (tx + tw) * s, (base - h - 3) * s], fill=fill)
        d.ellipse([tx * s, (base - h - th - 6) * s, (tx + tw) * s, (base - h - th) * s], fill=fill)
        d.line([(tx + 1) * s, (base - h - 3) * s, (tx + 1) * s, (base - h) * s], fill=fill, width=s)
    elif rng.random() < 0.25:
        r = w * 0.2
        d.pieslice([(x + w / 2 - r) * s, (base - h - r) * s, (x + w / 2 + r) * s, (base - h + r) * s], 180, 360, fill=fill)


def far_layers():
    """Three rows of village and trees, hazier and bluer the farther (uint8 alpha each, rows
    Y0..Y1) with their colours."""
    rng = np.random.default_rng(77)
    S = 2
    Y0, Y1 = 1340, 1620
    layers = []
    for spec in ("far", "mid", "near"):
        im = Image.new("L", (W * S, (Y1 - Y0) * S), 0)
        d = ImageDraw.Draw(im)
        if spec == "far":
            x = -30
            while x < W + 40:
                if rng.random() < 0.55:
                    w = rng.uniform(40, 90)
                    canopy(_shift(d, Y0), rng, x + w / 2, HORIZON - 4, w, rng.uniform(26, 58))
                else:
                    w = rng.uniform(22, 48)
                    building(_shift(d, Y0), rng, x, HORIZON - 3, w, rng.uniform(12, 30))
                x += w * rng.uniform(0.55, 0.95)
        elif spec == "mid":
            for cx in (-20, 150, 330, 520, 700, 880, 1040):
                cx += rng.uniform(-50, 50)
                if rng.random() < 0.75:
                    canopy(_shift(d, Y0), rng, cx, HORIZON + 2, rng.uniform(90, 170), rng.uniform(70, 125))
                else:
                    building(_shift(d, Y0), rng, cx, HORIZON + 2, rng.uniform(60, 110), rng.uniform(34, 60))
        else:
            canopy(_shift(d, Y0), rng, 980, HORIZON + 12, 330, 215)
            canopy(_shift(d, Y0), rng, 400, HORIZON + 12, 165, 128)
            canopy(_shift(d, Y0), rng, 660, HORIZON + 10, 95, 82)
        layers.append(np.asarray(im.reduce(S), np.uint8))
    return Y0, layers


class _shift:
    """A drawing wrapper that moves everything up by y0 (so a layer canvas holds only its band)."""

    def __init__(self, d, y0):
        self.d, self.y0, = d, y0

    def _f(self, xy, s=2):
        a = list(xy)
        if a and isinstance(a[0], (tuple, list)):
            return [(p[0], p[1] - self.y0 * s) for p in a]
        return [v - (self.y0 * s if i % 2 else 0) for i, v in enumerate(a)]

    def ellipse(self, xy, **k):
        self.d.ellipse(self._f(xy), **k)

    def rectangle(self, xy, **k):
        self.d.rectangle(self._f(xy), **k)

    def line(self, xy, **k):
        self.d.line(self._f(xy), **k)

    def pieslice(self, xy, a, b, **k):
        self.d.pieslice(self._f(xy), a, b, **k)


# --- the scene ------------------------------------------------------------------------------------
class Scene:
    look = "aakhri"
    in_order = False

    def __init__(self, facts):
        self.f = self.facts = facts      # `facts`: the engine's contract (report, workers)
        self.fps = facts.fps
        self.dur = facts.duration
        rng = np.random.default_rng(facts.seed)
        self._build_sky()
        self._build_ground()
        self.far_y0, self.far = far_layers()
        segs, tips, hero_segs = make_tree()
        self.wood = draw_wood(segs, hero_segs)
        self._build_trunk_bark()
        self._build_crown(tips, rng)
        self._schedule(rng)
        self.vig = P.vignette(0.32, border=0.35)
        sc = P.scrim(*facts.block_centre, rx=640, ry=400)
        self.calm_base = sc[::Q, ::Q, 0].copy()
        self._mist = self._mist_noise(np.random.default_rng(5))
        self.quiet_cache = {}
        self._rel_pose = {}
        self.rest_cache = {}
        self.k_row = np.arange(H, dtype=np.float32)[:, None]

    def describe(self) -> str:
        return (f"peepal crown of {self.M} leaves empties with the sung words ({self.n_words} words, "
                f"{len(self.f.marks)} gusts), last leaf falls at {self.t_hero:.1f} s")

    # ---------------- statics ----------------
    def _build_sky(self):
        qh, qw = H // Q, W // Q
        self.qh, self.qw = qh, qw
        yy = (np.arange(qh, dtype=np.float32) * Q + Q / 2)[:, None]
        xx = (np.arange(qw, dtype=np.float32) * Q + Q / 2)[None, :]
        H_ = HORIZON / H
        dusk = P.gradient([(0.0, "#0b0f1f"), (0.14, "#0f1526"), (0.34, "#141a2b"), (0.50, "#131a2e"),
                           (0.64, "#121a31"), (H_ - 0.07, "#172037"), (H_ - 0.03, "#212842"), (H_ - 0.008, "#2a2c46"),
                           (H_, "#312f48"), (1.0, "#0a0a12")])
        deep = P.gradient([(0.0, "#070a15"), (0.14, "#0a0f1e"), (0.34, "#0d1324"), (0.50, "#0d1427"),
                           (0.64, "#0e1529"), (H_ - 0.07, "#111a2e"), (H_ - 0.03, "#181d34"), (H_ - 0.008, "#22233b"),
                           (H_, "#292639"), (1.0, "#07070e")])
        self.base_a = dusk[Q // 2::Q, 0, :][:qh].copy()[:, None, :]
        self.base_b = deep[Q // 2::Q, 0, :][:qh].copy()[:, None, :]
        del dusk, deep
        rng = np.random.default_rng(31)
        n1 = ndimage.gaussian_filter(rng.standard_normal((qh, qw)), (3.5, 15), mode="wrap")
        n2 = ndimage.gaussian_filter(rng.standard_normal((qh, qw)), (1.8, 6), mode="wrap")
        n3 = ndimage.gaussian_filter(rng.standard_normal((qh, qw)), (9, 30), mode="wrap")
        f = 0.6 * n1 / n1.std() + 0.3 * n2 / n2.std() + 0.5 * n3 / n3.std()
        ymask = smooth((760 - yy) / 520) * smooth((yy + 40) / 160)
        D = smooth(np.clip(f * 0.5 + 0.22, 0, 1)) ** 1.5 * ymask
        gap = np.exp(-(((xx - GAP[0]) / 200) ** 2 + ((yy - 430) / 120) ** 2))
        D = np.clip(D * (1 - 0.55 * gap) + 0.75 * gap, 0, 1)
        Ds = ndimage.gaussian_filter(D, 1.6)
        gy = np.gradient(Ds, axis=0)
        under = np.clip(-gy * 9.0, 0, 1)
        lit = Ds * (0.12 + 0.88 * under) * (0.6 + 0.6 * gap)
        body = P.lin("#26304c")
        self.cloud = (lit[..., None] * ROSE2 * 0.36 + Ds[..., None] * body * 0.30).astype(np.float32)
        ex = (0.55 + 0.45 * smooth(xx / W)).astype(np.float32)
        glow = np.exp(-np.clip(HORIZON - yy, -40, None) ** 2 / (2 * 70.0 ** 2)) * (yy < HORIZON + 4) * ex
        self.glow = glow[..., None].astype(np.float32)
        cx, cy = self.f.block_centre
        self.sky_scrim = (1 - 0.3 * np.exp(-(((xx - cx) / 650) ** 2 + ((yy - cy) / 380) ** 2) * 1.2))[..., None].astype(np.float32)
        ys = np.arange(HORIZON - 26, HORIZON + 1, dtype=np.float32)
        self.ember_rows = ys
        self.ember_x = (0.35 + 0.65 * smooth(np.arange(W, dtype=np.float32) / W * 1.15)) * (
            0.8 + 0.2 * np.sin(np.arange(W) / 83.0))

    def _build_ground(self):
        rng = np.random.default_rng(12)
        h = H - HORIZON
        yy = (np.arange(h, dtype=np.float32) + 0.5)[:, None]
        u = yy / h
        base = P.lin("#0b0f1d") * (1 - u[..., None]) + P.lin("#04060b") * u[..., None]
        tex = P.fbm(rng, ((6, 4, 0.5), (16, 6, 0.6), (2, 1.2, 0.22)), h=h, w=W)
        g = np.repeat(base, W, axis=1) * (1 + 0.35 * tex[..., None])
        # bunds: lines converging on a far point, catching a little ember
        im = Image.new("L", (W, h), 0)
        d = ImageDraw.Draw(im)
        vx = 640
        for bx in rng.uniform(-900, 1900, 15):
            d.line([(vx + (bx - vx) * 0.04, 2), (bx, h)], fill=int(rng.uniform(70, 150)), width=int(rng.integers(1, 3)))
        for yb in (30, 75, 140, 230):
            d.line([(0, yb + rng.integers(-3, 3)), (W, yb + rng.integers(-6, 6))], fill=70, width=1)
        bunds = np.asarray(im, np.float32) / 255.0
        bunds = ndimage.gaussian_filter(bunds, 1.1)
        ember_under = (np.exp(-yy / 120.0)).astype(np.float32)
        g += (bunds * ember_under)[..., None] * P.lin("#7a3a2a") * 0.10
        # low shrubs, hazy: clumps on the far field
        sh = Image.new("L", (W * 2, h * 2), 0)
        sd = ImageDraw.Draw(sh)
        for cx in (90, 290, 430, 640, 800, 960, 1030):
            cx += rng.uniform(-30, 30)
            ww, hh = rng.uniform(40, 90), rng.uniform(9, 20)
            yb = rng.uniform(18, 60)
            for _ in range(int(ww / 5)):
                px = cx + rng.normal(0, ww / 3)
                r = rng.uniform(0.25, 0.6) * hh
                yc = yb - rng.uniform(0, hh)
                sd.ellipse([(px - r) * 2, (yc - r) * 2, (px + r) * 2, (yc + r) * 2], fill=255)
        shm = np.asarray(sh.reduce(2), np.float32) / 255.0
        shm = ndimage.gaussian_filter(shm, 1.6) * 0.9
        g = g * (1 - shm[..., None]) + shm[..., None] * P.lin("#0a0c16")
        # foreground grass blades at the bottom right
        gr = Image.new("L", (W * 2, h * 2), 0)
        gd = ImageDraw.Draw(gr)
        for _ in range(70):
            bx = rng.uniform(560, 1120)
            by = h + 10
            ln = rng.uniform(60, 220) * (0.6 + 0.4 * (bx - 500) / 620)
            lean = rng.normal(0.12, 0.12)
            pts = [(bx, by), (bx + lean * ln * 0.4, by - ln * 0.55), (bx + lean * ln, by - ln)]
            gd.line([(px * 2, py * 2) for px, py in pts], fill=255, width=int(rng.integers(2, 5)))
        grm = np.asarray(gr.reduce(2), np.float32) / 255.0
        self.grass = grm
        g = g * (1 - grm[..., None] * 0.95)
        full = np.zeros((H, W, 3), np.float32)
        full[HORIZON:] = g
        lrng = np.random.default_rng(21)
        for _ in range(70):                        # leaves already on the field: piled near the trunk
            near = lrng.random() < 0.6
            lx = lrng.uniform(60, 520) if near else lrng.uniform(300, 1080)
            ly = lrng.uniform(1700, 1905) if near else lrng.uniform(1600, 1900)
            Lf = 34 * (0.55 + 0.45 * (ly - 1580) / 340) * lrng.uniform(0.7, 1.15)
            a, ox, oy, _v = leaf_alpha(Lf, lrng.uniform(0.2, 0.45), lrng.uniform(-math.pi, math.pi), curl=0.15, ss=3)
            blit(full, lx, ly, a, ox, oy, P.lin("#22130d") * lrng.uniform(0.5, 1.0), rim_col=EMBER * 0.8, rim_amt=0.05, rim_r=1)
        self.ground = full[HORIZON:].copy()
        del full
        self.ground_ember = (np.exp(-yy / 70.0)[..., None] * EMBER * 0.035 * (0.4 + 0.6 * (np.arange(W) / W)[None, :, None] ** 1.2)).astype(np.float32)
        self.ground_edge_y = yy

    def _build_trunk_bark(self):
        rng = np.random.default_rng(9)
        n = ndimage.gaussian_filter(rng.standard_normal((H, 280)), (38, 1.5))
        n = n / n.std()
        self.bark = np.clip(n * 0.55 + 0.25, 0, 1).astype(np.float16) ** 2

    def _mist_noise(self, rng):
        a = ndimage.gaussian_filter1d(rng.standard_normal(W + 900), 55, mode="wrap")
        b = ndimage.gaussian_filter1d(rng.standard_normal(W + 900), 28, mode="wrap")
        a = (a - a.mean()) / a.std()
        b = (b - b.mean()) / b.std()
        return a, b

    def _build_crown(self, tips, rng):
        """Every leaf on the tree: anchor, size, hang angle, turn."""
        prng = np.random.default_rng(404)
        pick = tips[tips[:, 3] >= 1]
        order = prng.permutation(len(pick))
        L0 = 54.0
        rows = []
        for i in order:
            tx, ty, ang, depth, w = pick[i]
            if ty > 780:
                continue
            cnt = int(prng.integers(6, 13))
            for _ in range(cnt):
                ax, ay = tx + prng.normal(0, 16), ty + prng.normal(0, 12)
                th = math.pi / 2 + prng.normal(0, 0.85)
                s = float(np.clip(prng.lognormal(0, 0.27), 0.62, 1.3))
                fl = float(prng.choice([-1, 1]) * (prng.uniform(0.1, 0.22) if prng.random() < 0.14 else prng.uniform(0.3, 1.0)))
                L = L0 * s
                pet = 0.3
                cxx = ax + math.cos(th) * (pet + U0) * L
                cyy = ay + math.sin(th) * (pet + U0) * L
                if math.hypot(cxx - GAP[0], cyy - GAP[1]) < GAP[2] - 15:
                    continue
                if cyy > 800 or ax < -10 or ax > W + 20:
                    continue
                rows.append((ax, ay, th, L, fl, prng.uniform(-0.3, 0.3), pet, prng.uniform(0, TAU)))
            if len(rows) >= 820:
                break
        self.cl = np.array(rows, np.float64)        # ax ay theta L flip curl pet phase
        self.M = len(self.cl)
        self.back = prng.random(self.M) < 0.34      # hazier leaves behind the front ones

    def _schedule(self, rng):
        """Release times and fall paths of every crown leaf, from the song (or an even rhythm)."""
        f = self.f
        M = self.M
        dur = self.dur
        starts = np.array(f.starts, np.float64)
        self.n_words = len(starts)
        self.t_hero = float(f.last_line_s) if f.last_line_s is not None else 0.85 * dur
        self.t_hero = float(max(min(self.t_hero, dur - 3.0), 1.0))
        n_eq = len(starts) if len(starts) else max(8, int(round(dur / 0.55)))
        if len(starts) == 0:
            starts = np.linspace(0.05 * dur, 0.94 * dur, n_eq)
        # release order: the breezy right side and the higher twigs go first
        key = rng.uniform(0, 1, M) + 0.45 * (1 - self.cl[:, 0] / W) + 0.15 * (self.cl[:, 1] / 800)
        rank = np.argsort(np.argsort(key))
        per_word = M / n_eq
        grp = np.minimum((rank / per_word).astype(int), n_eq - 1)
        span = np.minimum(np.diff(np.append(starts, starts[-1] + 1.0)), 1.0) * 0.85
        eff = starts.copy()                          # the last line's words hurry the crown bare by the last leaf
        late = np.nonzero(starts > self.t_hero - 1.0)[0]
        if len(late):
            eff[late] = self.t_hero - 1.0 + np.arange(len(late)) / len(late) * 1.3
        t_rel = eff[grp] + rng.uniform(0, 1, M) * np.maximum(np.minimum(span[grp], 0.9), 0.25)
        last_ok = self.t_hero + 0.5
        t_rel = np.minimum(t_rel, last_ok)
        gust = np.zeros(M, bool)
        self.mark_t = [m[0] for m in f.marks]
        for ts in self.mark_t:                       # a gust: a stream of leaves goes off to the right
            fut = np.nonzero((t_rel > ts + 0.4) & ~gust)[0]
            if len(fut) == 0:
                continue
            nearest = fut[np.argsort(t_rel[fut])[:70]]
            right = nearest[np.argsort(-self.cl[nearest, 0] + rng.normal(0, 150, len(nearest)))[:11]]
            for j, i in enumerate(right):
                t_rel[i] = ts + 0.05 + j * 0.13 + rng.uniform(0, 0.1)
                gust[i] = True
        self.t_rel = t_rel
        self.gust = gust
        fly_p = min(1.0, 3.2 / per_word) if per_word > 1 else 1.0
        self.flyer = (rng.random(M) < fly_p) | gust
        far = (rng.random(M) < 0.35) & ~gust
        self.far_leaf = far
        self.depth_s = np.where(far, rng.uniform(0.5, 0.65, M), 1.0)
        v_mid = rng.uniform(175, 255, M)
        v_far = rng.uniform(95, 135, M)
        self.v = np.where(far, v_far, v_mid) * np.where(self.flyer, 1.0, 1.35)
        ylo = np.where(far, rng.uniform(1582, 1660, M), rng.uniform(1690, 1895, M))
        self.y_land = ylo
        self.vx = rng.normal(22, 26, M)
        self.vg = np.where(gust, rng.uniform(210, 300, M), 0.0)
        self.swA = np.where(far, rng.uniform(22, 48, M), rng.uniform(55, 115, M)) * np.where(self.flyer, 1.0, 0.6)
        self.swW = TAU / rng.uniform(2.4, 3.9, M)
        self.swP = rng.uniform(0, TAU, M)
        self.tuW = TAU / rng.uniform(1.7, 3.1, M)
        self.tuP = rng.uniform(0, TAU, M)
        self.rest_rot = rng.uniform(-math.pi, math.pi, M)
        self.life = np.where(self.flyer, 0.0, rng.uniform(1.2, 2.0, M))   # short-lived droppers fade out
        # near, out-of-focus leaves at the frame edge: a few over the song, one with each far-apart mark
        nts = [-2.5, 0.27 * dur, 0.52 * dur, 0.76 * dur]
        for ts in self.mark_t:
            if all(abs(ts - q) > 5.0 for q in nts):
                nts.append(ts)
            if len(nts) >= 9:
                break
        nrng = np.random.default_rng(f.seed + 11)
        self.near = []
        for ts in nts:
            side = nrng.choice([-1, 1])
            self.near.append(dict(t=ts, T=nrng.uniform(7.5, 10.5), L=nrng.uniform(250, 380),
                                  x0=(nrng.uniform(1030, 1150)),
                                  xd=nrng.normal(0, 30), y0=nrng.uniform(-300, -180),
                                  ph=nrng.uniform(0, TAU), rot=nrng.uniform(0.6, 2.4), fl=nrng.uniform(0.5, 0.9)))

    # ---------------- motion ----------------
    def gustiness(self, t):
        return P.envelope(t, self.mark_t, 0.5, 3.0) if self.mark_t else 0.0

    def sway(self, x, y, t, g=None):
        if g is None:
            g = self.gustiness(t)
        wy = np.clip((1250.0 - y) / 1250.0, 0, 1) ** 1.4
        wx = 0.25 + 0.75 * np.clip(x / 700.0, 0, 1)
        m = 1 + 1.8 * g
        a = 9.0 * (np.sin(TAU * t / 9.1 + 0.7) + 0.55 * np.sin(TAU * t / 5.3 + 2.1)) * wy * wx * m
        b = 2.6 * np.sin(TAU * t / 6.7 + 1.3) * wy * wx * m
        return a, b

    def crown_pose(self, i, t, g):
        """(blade centre, rot, L, flip) of crown leaf i at time t, before the tree's sway."""
        ax, ay, th, L, fl, curl, pet, ph = self.cl[i]
        d = 0.05 * math.sin(TAU * t / 3.4 + ph) * (1 + 1.4 * g) + 0.03 * math.sin(TAU * t / 1.7 + 2 * ph)
        c, s = math.cos(th + d), math.sin(th + d)
        return (ax + c * (pet + U0) * L, ay + s * (pet + U0) * L), th + d, L, fl

    def fall_pose(self, i, tau):
        """Pose of released leaf i `tau` s after letting go: (cx, cy, rot, flip, L scale, resting)."""
        (cx0, cy0), rot0, L, fl = self._rel_pose[i]
        tau0 = 0.9
        v = self.v[i]
        dist = max(self.y_land[i] - cy0, 60.0)
        T = dist / v + tau0
        tc = min(tau, T)
        w = float(smooth((tc - (T - 0.9)) / 0.9))
        ease = tc - tau0 * (1 - math.exp(-tc / tau0))
        ramp = 1 - math.exp(-tc / 0.8)
        A = self.swA[i] * (1 - 0.92 * w)
        y = cy0 + v * ease
        x = (cx0 + self.vx[i] * tc + self.vg[i] * 1.2 * (1 - math.exp(-tc / 1.2))
             + A * ramp * math.sin(self.swW[i] * tc + self.swP[i]))
        lean = 0.75 * ramp * math.cos(self.swW[i] * tc + self.swP[i]) * (1 - w)
        rot = rot0 + lean * (1 if self.swP[i] < math.pi else -1) + (self.rest_rot[i] - rot0) * w * 0.6
        ph2 = math.acos(min(max(abs(fl), 0.0), 1.0))
        flip = abs(math.cos(self.tuW[i] * tc + ph2)) * (1 - w) + 0.3 * w
        sc = self.depth_s[i] * (1 - 0.22 * w)
        return x, y, rot, max(flip, 0.09), sc, tau >= T, T

    def prepare_release(self, t_unused=None):
        pass

    # ---------------- per frame ----------------
    def quiet_map(self, ink):
        """(H/Q, W/Q) 1 where the lyrics are this frame (softened), 0 elsewhere."""
        q = np.zeros((self.qh, self.qw), np.float32)
        if ink is not None:
            x0, y0 = max(int((ink[0] - 70) / Q), 0), max(int((ink[1] - 70) / Q), 0)
            x1, y1 = int((ink[2] + 70) / Q) + 1, int((ink[3] + 70) / Q) + 1
            q[y0:y1, x0:x1] = 1.0
            q = ndimage.gaussian_filter(q, 55 / Q)
        return q

    def frame(self, k: int, ink=None) -> np.ndarray:
        t = k / self.fps
        s = float(min(max(t / max(self.dur, 1e-6), 0.0), 1.0) ** 1.15)
        g = self.gustiness(t)
        qm = self.quiet_map(ink)
        quiet_full = None
        # --- sky
        sky = (self.base_a * (1 - s) + self.base_b * s
               + self.cloud * (1 - 0.6 * s) + self.glow * (EMBER * (0.16 * (1 - s) + 0.07 * s)
                                                          + np.array([0.0, 0.0, 0.0], np.float32)))
        sky = sky * self.sky_scrim
        sky = sky * (1 - 0.16 * qm[..., None])
        x = P.up(sky.astype(np.float32))
        # thin ember line at the horizon: thinner and redder as the song goes
        ecol = EMBER * (1 - s) + EMBER_DEEP * s
        wid = 4.2 - 1.6 * s
        prof = np.exp(-((HORIZON - self.ember_rows) / wid) ** 2) * (1.25 - 0.4 * s)
        er = self.ember_rows.astype(int)
        x[er[0]:er[-1] + 1] += (prof[:, None, None] * self.ember_x[None, :, None]) * ecol * 0.85
        # --- far rows (paler and bluer with distance), mist over them
        y0 = self.far_y0
        rows = np.arange(y0, y0 + self.far[0].shape[0], dtype=np.float32)[:, None, None]
        hz = np.exp(-(HORIZON - rows) / 45.0) * (rows < HORIZON + 10)
        sky_h = x[y0:y0 + self.far[0].shape[0]]
        for a8, col, op, hazeamt in zip(self.far, ("#3a4468", "#232a47", "#10131f"), (0.62, 0.8, 0.95), (0.35, 0.25, 0.12)):
            a = (a8.astype(np.float32) / 255.0 * op)[..., None]
            c = P.lin(col) * (1 - 0.35 * s) * (1 - hz * hazeamt * 0.0)
            c = c + hz * EMBER * (0.05 * hazeamt * (1 - 0.6 * s))
            sky_h *= 1 - a
            sky_h += a * c
            if col == "#3a4468":
                self._mist_over(x, t, s)
        # --- ground
        gr = self.ground + self.ground_ember * (1 - 0.6 * s)
        x[HORIZON:] = gr
        # --- tree
        Ac = self.tree_alpha(t, g, k)
        Af = Ac.astype(np.float32) * (1 / 255.0)
        if quiet_full is None:
            quiet_full = 1 - 0.85 * P.up(qm)
        treecol = P.lin("#05050a")
        np.multiply(x, (1 - Af)[..., None], out=x)
        x += Af[..., None] * treecol
        sh = np.pad(Af, ((2, 0), (0, 2)), mode="edge")[:H, 2:2 + W]
        rim = np.clip(Af - sh, 0, 1)
        del sh
        yy = self.k_row
        mixr = smooth((yy - 650) / 900.0)
        rimcol = (ROSE * (0.10 * (1 - 0.65 * s)) * (1 - mixr)[..., None] + EMBER * 0.045 * mixr[..., None]).astype(np.float32)
        x += (rim * quiet_full)[..., None] * rimcol[:, None, :] if False else (rim * quiet_full)[..., None] * rimcol.reshape(H, 1, 3)
        # bark ridges catching the ember on the trunk
        bk = self.bark.astype(np.float32)
        x[:, :280] += (bk * Af[:, :280] * quiet_full[:, :280])[..., None] * (EMBER * 0.030 * (1 - 0.5 * s)) * (smooth((yy - 500) / 900.0)[..., None])
        del rim, Af
        # --- leaves in the air and on the ground
        self.paint_leaves(x, t, g, qm, s)
        self.paint_near(x, t, qm, s)
        self.paint_hero(x, t, qm, s)
        return P.finish(x, bloom=0.30, bloom_sigma=6.0, knee=0.62, soft=0.4, vig=self.vig)

    def _mist_over(self, x, t, s):
        a, b = self._mist
        n = 0.55 + 0.25 * np.interp(np.arange(W) - 5.0 * t, np.arange(W + 900), a) + \
            0.2 * np.interp(np.arange(W) + 9.0 * t, np.arange(W + 900), b)
        y0, y1 = HORIZON - 70, HORIZON + 6
        ys = np.arange(y0, y1, dtype=np.float32)[:, None]
        prof = np.exp(-((ys - (HORIZON - 14)) / 22.0) ** 2) * 0.22
        m = (prof * np.clip(n, 0, 1)[None, :])[..., None]
        col = P.lin("#3c4462") * 0.6 + EMBER * 0.12
        x[y0:y1] += m * col * (1 - 0.5 * s)

    def tree_alpha(self, t, g, k):
        """Wood and the leaves still on the crown, swayed, as a (H, W) uint8 coverage map."""
        S = 2
        cv = Image.new("L", (W * S, H * S), 0)
        dr = ImageDraw.Draw(cv)
        alive = np.nonzero(self.t_rel > t)[0]
        poses = {}
        for i in alive:
            poses[i] = self.crown_pose(i, t, g)
        for layer_back in (True, False):
            if layer_back:
                for i in alive:
                    if self.back[i]:
                        self._crown_poly(dr, i, poses[i], S, 150)
                from PIL import ImageChops
                cv = ImageChops.lighter(cv, self.wood)
                dr = ImageDraw.Draw(cv)
            else:
                for i in alive:
                    if not self.back[i]:
                        self._crown_poly(dr, i, poses[i], S, 255)
        nx, ny = 10, 16
        data = []
        cw, ch = W / nx, H / ny
        for j in range(ny):
            for i in range(nx):
                x0, y0, x1, y1 = i * cw, j * ch, (i + 1) * cw, (j + 1) * ch
                quad = []
                for (px, py) in ((x0, y0), (x0, y1), (x1, y1), (x1, y0)):
                    a, b = self.sway(px, py, t, g)
                    quad += [(px - a) * S, (py - b) * S]
                data.append(((int(round(x0 * S)), int(round(y0 * S)), int(round(x1 * S)), int(round(y1 * S))), quad))
        warped = cv.transform((W * S, H * S), Image.MESH, data, Image.BILINEAR)
        out = warped.reduce(S)
        return np.asarray(out.filter(__import__("PIL.ImageFilter", fromlist=["x"]).GaussianBlur(0.5)), np.uint8)

    def _crown_poly(self, dr, i, pose, S, fill):
        (cx, cy), rot, L, fl = pose
        ax, ay, th, L_, _, curl, pet, ph = self.cl[i]
        pts = to_px(blade_uv(fl, curl, 0.12 * fl), L, rot, cx, cy)
        dr.polygon([(px * S, py * S) for px, py in pts], fill=fill)
        c, s = math.cos(rot), math.sin(rot)
        bx, by = cx - c * U0 * L, cy - s * U0 * L
        dr.line([(ax * S, ay * S), (bx * S, by * S)], fill=fill, width=2)

    # ---------------- leaves ----------------
    def _released(self, t):
        return np.nonzero(self.t_rel <= t)[0]

    def paint_leaves(self, x, t, g, qm, s):
        if not hasattr(self, "_rel_pose"):
            self._rel_pose = {}
        ids = self._released(t)
        body_dark = P.lin("#06060c")
        body_brown = P.lin("#2a1810")
        for i in ids:
            if i not in self._rel_pose:
                tr = self.t_rel[i]
                gg = self.gustiness(tr)
                (cx, cy), rot, L, fl = self.crown_pose(i, tr, gg)
                a, b = self.sway(cx, cy, tr, gg)
                self._rel_pose[i] = ((cx + a, cy + b), rot, L, fl)
            tau = t - self.t_rel[i]
            cx, cy, rot, flip, sc, rest, T = self.fall_pose(i, tau)
            op = 1.0
            if self.life[i] > 0:                      # short-lived leaves dissolve quickly
                op = float(max(0.0, 1 - max(0.0, tau - 0.25) / self.life[i]))
                if op <= 0:
                    continue
            if not (-200 < cx < W + 200 and -200 < cy < H + 200):
                continue
            L = self._rel_pose[i][2] * sc
            far = self.far_leaf[i]
            qv = self._q_at(qm, cx, cy)
            if rest:
                key = i
                cached = self.rest_cache.get(key)
                if cached is None:
                    cached = leaf_alpha(L, 0.3, rot, curl=0.15, ss=3)
                    self.rest_cache[key] = cached
                a, ox, oy, _ = cached
                ember = 1.0
                lit = float(0.5 + 0.5 * smooth((cy - 1600) / 200))
                blit(x, cx, cy, a, ox, oy, body_brown * (0.6 + 0.4 * lit) * 0.75,
                     rim_col=EMBER, rim_amt=0.10 * (1 - 0.6 * s), rim_r=1 + int(L > 40), quiet=qv, op=op)
            else:
                a, ox, oy, _ = leaf_alpha(L, flip, rot, curl=0.12, ss=3)
                high = 1 - smooth((cy - 300) / 1100)
                rc = ROSE * (0.11 * (1 - 0.5 * s)) * high + EMBER * 0.07 * (1 - high)
                if far:
                    col = P.lin("#151b30") * 1.0
                    blit(x, cx, cy, a, ox, oy, col, op=op * 0.85, rim_col=rc, rim_amt=0.7, rim_r=1, quiet=qv)
                else:
                    blit(x, cx, cy, a, ox, oy, body_dark, op=op, rim_col=rc, rim_amt=1.0, rim_r=2, quiet=qv)

    def _q_at(self, qm, cx, cy):
        qx, qy = int(min(max(cx / Q, 0), self.qw - 1)), int(min(max(cy / Q, 0), self.qh - 1))
        return float(1 - 0.92 * qm[qy, qx])

    def paint_near(self, x, t, qm, s):
        for nl in self.near:
            tau = t - nl["t"]
            if tau < 0 or tau > nl["T"]:
                continue
            u = tau / nl["T"]
            cy = nl["y0"] + (H + 500) * (u ** 1.0) * 0.9 + 0 * u
            cx = nl["x0"] + nl["xd"] * u + 30 * math.sin(TAU * u * 1.3 + nl["ph"])
            rot = nl["rot"] + 0.9 * math.sin(TAU * u * 1.1 + nl["ph"] + 1)
            flip = 0.35 + 0.6 * abs(math.cos(TAU * u * 0.9 + nl["ph"]))
            L = nl["L"]
            fade = float(smooth(min(u / 0.12, 1.0)) * smooth(min((1 - u) / 0.12, 1.0)))
            qv = self._q_at(qm, cx, cy)
            a, ox, oy, vein = leaf_alpha(L, flip, rot, curl=0.12, ss=1, veins=True, pad=40)
            a = ndimage.gaussian_filter(a, 11)
            vein = ndimage.gaussian_filter(vein, 11) * 0.8
            col = P.lin("#150d14")
            blit(x, cx, cy, a, ox, oy, col, op=0.62 * fade, rim_col=EMBER * 0.25 + ROSE2 * 0.4, rim_amt=0.5 * (1 - 0.5 * s),
                 rim_r=9, quiet=qv)
            px, py = int(round(cx)) + ox, int(round(cy)) + oy
            h, w = a.shape
            xa, ya, xb, yb = max(px, 0), max(py, 0), min(px + w, W), min(py + h, H)
            if xb > xa and yb > ya:
                v = vein[ya - py:yb - py, xa - px:xb - px] * a[ya - py:yb - py, xa - px:xb - px]
                x[ya:yb, xa:xb] += (v * 0.035 * qv * fade)[..., None] * EMBER

    # ---------------- the last leaf ----------------
    def hero_state(self, t):
        """(cx, cy, rot, flip, L, glow, fell) of the last leaf at time t."""
        t_h = self.t_hero
        a, b = self.sway(HERO[0], HERO[1], t)
        swing = 0.05 * math.sin(TAU * t / 4.1 + 0.5) + 0.018 * math.sin(TAU * t / 1.9)
        hang = math.pi / 2 + 0.06 + swing
        if t < t_h:
            cx = HERO[0] + a + math.cos(hang) * (0.3 + U0) * HERO_L
            cy = HERO[1] + b + math.sin(hang) * (0.3 + U0) * HERO_L
            return cx, cy, hang, 0.78 + 0.1 * math.sin(TAU * t / 5.3), HERO_L, 0.0, False
        Tf = float(np.clip(self.dur - t_h - 0.5, 2.6, 7.0))
        tau = t - t_h
        u = min(tau / Tf, 1.0)
        e = float(smooth(u))
        c0x = HERO[0] + a + math.cos(hang) * (0.3 + U0) * HERO_L
        c0y = HERO[1] + b + math.sin(hang) * (0.3 + U0) * HERO_L
        ex, ey = 640.0, 1618.0
        ramp = 1 - math.exp(-tau / 0.7)
        damp = (1 - u) ** 0.8
        ease_y = (u ** 1.35) * (1 - 0.0)
        cy = c0y + (ey - c0y) * (0.35 * e + 0.65 * ease_y)
        sideways = 175 * math.sin(TAU * 0.5 * u * 1.15) * damp + 90 * math.sin(TAU * u * 1.6 + 1.0) * damp * (1 - e)
        cx = c0x + (ex - c0x) * e + sideways * ramp
        rot = hang + 0.75 * math.sin(TAU * u * 1.3 + 0.4) * damp * ramp + (0.35 - hang) * e * 0.0
        rot += (0.25 - 0.0) * e
        flip = 0.8 * (1 - e) + 1.0 * e
        flip = flip * (0.45 + 0.55 * abs(math.cos(TAU * u * 1.5 + 0.4) * damp + (1 - damp)))
        L = HERO_L + (150.0 - HERO_L) * float(smooth(u ** 0.9))
        return cx, cy, rot, max(flip, 0.12), L, float(e), True

    def paint_hero(self, x, t, qm, s):
        cx, cy, rot, flip, L, e, fell = self.hero_state(t)
        qv = self._q_at(qm, cx, cy)
        hang_glow = 1.0 if not fell else 1.0
        # the warm light: dim against the cloud while it hangs, gold once it is low against the ember
        lev = 0.50 + 0.65 * e
        a, ox, oy, vein = leaf_alpha(L, flip, rot, curl=0.12, bend=0.10, ss=3, veins=True, pad=int(L * 0.6) + 20)
        # interior glow: distance in from the blade edge
        inner = ndimage.distance_transform_edt(a > 0.5)
        half = 0.17 * L * max(flip, 0.25)
        core = np.clip(inner / max(half, 2.0), 0, 1)
        rng = np.random.default_rng(7)
        core = core ** 0.8
        edge_c = P.lin("#3a1708")
        mid_c = P.lin("#c2751a")
        hi_c = P.lin("#f0b540") if e > 0 else P.lin("#e0a030")
        col = edge_c[None, None, :] * (1 - core[..., None]) + mid_c[None, None, :] * core[..., None]
        bright = np.clip(core * 1.3, 0, 1)
        col = col + hi_c * (bright ** 2 * 0.45)[..., None]
        col = col * (0.75 + 0.25 * np.clip(ndimage.gaussian_filter(rng.standard_normal(a.shape), 3), -1, 1))[..., None]
        col = col + (vein * 0.55 * core)[..., None] * P.lin("#ffe2a0") * 0.5     # pale veins
        col = col * (1 - 0.5 * np.clip(ndimage.gaussian_filter(vein, 0.0), 0, 0)[..., None])
        # a browning edge with a spot or two
        spots = np.zeros_like(a)
        for _ in range(3):
            py, px = rng.integers(0, a.shape[0]), rng.integers(0, a.shape[1])
            yy, xx = np.mgrid[0:a.shape[0], 0:a.shape[1]]
            spots += np.exp(-((yy - py) ** 2 + (xx - px) ** 2) / (2 * (L * 0.05) ** 2))
        col = col * (1 - 0.6 * np.clip(spots * (1 - core), 0, 1)[..., None])
        amp = lev * (1 - 0.88 * (1 - qv))
        px, py = int(round(cx)) + ox, int(round(cy)) + oy
        h, w = a.shape
        xa, ya, xb, yb = max(px, 0), max(py, 0), min(px + w, W), min(py + h, H)
        if xb > xa and yb > ya:
            sa = a[ya - py:yb - py, xa - px:xb - px][..., None]
            sc = col[ya - py:yb - py, xa - px:xb - px]
            reg = x[ya:yb, xa:xb]
            reg *= 1 - sa * 0.97
            reg += sa * sc * amp * (0.85 if not fell else 1.0)
        # a tight soft rim glow, not a round halo
        halo = ndimage.gaussian_filter(a, max(L * 0.10, 2.0))
        if xb > xa and yb > ya:
            x[ya:yb, xa:xb] += (halo[ya - py:yb - py, xa - px:xb - px] * 0.13 * amp * (1 - 0.5 * e))[..., None] * (P.lin("#f0a050") * (1 - e) + P.lin("#ffc070") * e)
        P.blob(x, cx, cy, L * 1.1, L * 0.9, P.lin("#e89a4a"), 0.018 * (0.5 + e) * (1 - 0.88 * (1 - qv)))
