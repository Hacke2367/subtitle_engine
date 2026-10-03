"""Chaand ka ghoonghat: a full moon behind a veil of high cloud. The veil's hem breathes on every
sung word, lifts higher (a peek) on each marked word and lifts right off on the last line, along
its own cloud shapes. Clouds drift, trees sway a hair. The moon stays dim behind the veil for the
first ~3 s (the title card sits over it) and then comes out. Everything is a pure function of the
frame number and the song facts."""
from __future__ import annotations

import math

import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage

from . import paint as P

W, H = P.W, P.H
F = 2
w, h = W // F, H // F
WP = 2 * w                                   # period of the drifting textures (half px)
MX, MY, MR = 560.0, 440.0, 92.0              # the moon (full px)
MOON = P.lin("#f8ebcf")
SILVER = P.lin("#b4c2e4")
BLUEAIR = P.lin("#5673bd")
SLATE = P.lin("#0b1228")
TY0 = 1330                                   # tree band: rows TY0..H
PUSH = 0.06                                  # the push-in over the song (6 %)
sm = P.smooth


def pnoise(rng, hh, ww, sy, sx, shrink=1):
    """Smooth noise, std 1, periodic in both axes."""
    a = rng.standard_normal((hh // shrink, ww // shrink)).astype(np.float32)
    a = ndimage.gaussian_filter(a, (sy / shrink, sx / shrink), mode="wrap")
    a = (a - a.mean()) / (a.std() + 1e-6)
    if shrink > 1:
        a = ndimage.zoom(a, shrink, order=1, mode="grid-wrap", grid_mode=True)
    return a.astype(np.float32)


def octaves(rng, hh, ww, spec):
    out = np.zeros((hh, ww), np.float32)
    for sy, sx, wt, sh in spec:
        out += wt * pnoise(rng, hh, ww, sy, sx, sh)
    return out / math.sqrt(sum(s[2] ** 2 for s in spec))


def warp(tex, rng, ay, ax):
    hh, ww = tex.shape
    yy, xx = np.mgrid[0:hh, 0:ww].astype(np.float32)
    wy = pnoise(rng, hh, ww, 40, 60, 4)
    wx = pnoise(rng, hh, ww, 40, 60, 4)
    return ndimage.map_coordinates(tex, [yy + ay * wy, xx + ax * wx], order=1, mode="grid-wrap").astype(np.float32)


def roll(tex, shift):
    """A (h, w) window of a periodic texture starting `shift` px along (scalar or per row), with
    sub-pixel linear blending, so slow drift never steps."""
    hh, wp = tex.shape
    s = np.asarray(shift, np.float64)
    s0 = np.floor(s)
    fr = (s - s0).astype(np.float32)[..., None]
    base = s0.astype(np.int64)[..., None] + np.arange(w)[None, :]
    rows = np.arange(hh)[:, None]
    a = tex[rows, base % wp]
    b = tex[rows, (base + 1) % wp]
    return a + (b - a) * fr


# --- trees -----------------------------------------------------------------------------------------
S2 = 2


def _seg(d, p0, p1, wd):
    d.line([(p0[0] * S2, (p0[1] - TY0) * S2), (p1[0] * S2, (p1[1] - TY0) * S2)], fill=255,
           width=max(int(wd * S2), 1))
    r = wd * S2 / 2
    d.ellipse([p1[0] * S2 - r, (p1[1] - TY0) * S2 - r, p1[0] * S2 + r, (p1[1] - TY0) * S2 + r], fill=255)


def _grow(d, rng, x, y, ang, length, wd, depth, tips, mids):
    n = max(int(length / 16), 3)
    a = ang
    for i in range(n):
        a += rng.normal(0, 0.10)
        a += 0.10 * (-math.pi / 2 - a)
        nx, ny = x + math.cos(a) * length / n, y + math.sin(a) * length / n
        _seg(d, (x, y), (nx, ny), wd * (1 - 0.4 * i / n))
        x, y = nx, ny
        if depth <= 1 and i == n // 2:
            mids.append((x, y))
    if depth > 0:
        k = 2 if rng.random() < 0.65 else 3
        for j in range(k):
            da = (j - (k - 1) / 2) * rng.uniform(0.5, 0.75)
            _grow(d, rng, x, y, a + da + rng.normal(0, 0.1), length * rng.uniform(0.62, 0.8), wd * 0.66,
                  depth - 1, tips, mids)
    else:
        tips.append((x, y))


def _clump(d, rng, cx, cy, R):
    for _ in range(int(9 + R / 4)):
        a = rng.uniform(0, 2 * math.pi)
        rr = R * math.sqrt(rng.uniform(0, 1)) * 0.8
        r = R * rng.uniform(0.28, 0.5)
        x, y = cx + rr * math.cos(a) * 1.15, cy + rr * math.sin(a) * 0.8
        d.ellipse([(x - r) * S2, (y - r * 0.82 - TY0) * S2, (x + r) * S2, (y + r * 0.82 - TY0) * S2], fill=255)


def _tree(dbr, dcl, rng, bx, by, fork_y, tw, crown, R, depth=2, limb=None, trunk=True):
    """A mango/neem: a thick trunk that forks into limbs, under a dense dome of leaf clumps whose
    lumpy rim breaks the skyline. crown = (cx, cy, rx, ry)."""
    cx, cy, rx, ry = crown
    if trunk:
        x, y = bx, by
        n = 10
        for i in range(n):
            ny = y + (fork_y - by) / n
            nx = x + (cx - bx) * 0.2 / n + rng.normal(0, 1.5)
            _seg(dbr, (x, y), (nx, ny), tw * (1 - 0.35 * i / n) * (1 + 1.4 * (i == 0)))
            x, y = nx, ny
        tips, mids = [], []
        for j in range(3):
            ang = -math.pi / 2 + (j - 1) * 0.8 + rng.normal(0, 0.1)
            _grow(dbr, rng, x, y, ang, limb or (fork_y - cy) * 0.6, tw * 0.6, depth, tips, mids)
    # the dome: clumps filling the hull, more on top, then a lumpy rim
    area = rx * ry
    for _ in range(int(area / (R * R) * 1.6)):
        a = rng.uniform(math.pi * 0.95, math.pi * 2.05) if rng.random() < 0.75 else rng.uniform(0, math.pi)
        rr = math.sqrt(rng.uniform(0.05, 1)) * 0.85
        _clump(dcl, rng, cx + rx * rr * math.cos(a), cy + ry * rr * math.sin(a) * 0.9 + ry * 0.15,
               R * rng.uniform(0.8, 1.15))
    for a in np.linspace(math.pi * 1.02, math.pi * 1.98, int(rx / R * 2.4)) + rng.normal(0, 0.05, int(rx / R * 2.4)):
        _clump(dcl, rng, cx + rx * 0.93 * math.cos(a), cy + ry * 0.93 * math.sin(a) + ry * 0.12,
               R * rng.uniform(0.45, 0.75))
    if trunk:
        for tx, ty in tips:
            _clump(dcl, rng, tx, ty, R * 0.8)


def _row_mask(rng, trees, leaf_sigma, hole):
    bh = H - TY0
    br = Image.new("L", (W * S2, bh * S2), 0)
    cl = Image.new("L", (W * S2, bh * S2), 0)
    dbr, dcl = ImageDraw.Draw(br), ImageDraw.Draw(cl)
    for t in trees:
        _tree(dbr, dcl, rng, *t["a"], **t.get("k", {}))
    br = np.asarray(br.resize((W, bh), Image.BOX), np.float32) / 255
    cl = np.asarray(cl.resize((W, bh), Image.BOX), np.float32) / 255
    cl = ndimage.gaussian_filter(cl, 3.0)
    lf = ndimage.gaussian_filter(rng.standard_normal((bh, W)).astype(np.float32), leaf_sigma)
    lf /= lf.std() + 1e-6
    lo = ndimage.gaussian_filter(rng.standard_normal((bh, W)).astype(np.float32), 7)
    lo /= lo.std() + 1e-6
    c = sm((cl + 0.17 * lf - 0.5) / 0.12)
    br = ndimage.gaussian_filter(br, 0.6)
    return np.maximum(c, br).astype(np.float32)


def _sheen(mask, rng, strength):
    """Soft continuous light on the crown shoulders that face the moon."""
    bh = mask.shape[0]
    hgt = 0.65 * ndimage.gaussian_filter(mask, 16) + 0.35 * ndimage.gaussian_filter(mask, 5)
    gy, gx = np.gradient(hgt)
    yy, xx = np.mgrid[0:bh, 0:W].astype(np.float32)
    dx, dy = MX - xx, MY - (yy + TY0)
    d = np.hypot(dx, dy) + 1
    lit = np.clip(-(gx * dx / d + gy * dy / d) * 34, 0, 1.4)
    lf = ndimage.gaussian_filter(rng.standard_normal((bh, W)).astype(np.float32), 3)
    lf = 0.75 + 0.25 * lf / (lf.std() + 1e-6)
    return (lit * np.clip(lf, 0.3, 1.4) * mask * strength).astype(np.float32)


def build_trees():
    rng = np.random.default_rng(41)
    far = _row_mask(rng, [dict(a=(bx, 1760, 1800, 10, (bx, 1600 + 25 * math.sin(bx), 110, 45), 30),
                               k=dict(trunk=False)) for bx in range(-40, W + 100, 130)], 2.4, 0.0)
    mid = _row_mask(rng, [dict(a=(330, 1960, 1790, 34, (330, 1630, 150, 95), 40), k=dict(depth=2, limb=110)),
                          dict(a=(660, 1960, 1800, 34, (660, 1660, 140, 85), 40), k=dict(depth=2, limb=100)),
                          dict(a=(1010, 1960, 1790, 34, (1000, 1600, 150, 100), 40), k=dict(depth=2, limb=110))],
                    2.6, 0.0)
    near = _row_mask(rng, [dict(a=(110, 1990, 1800, 46, (140, 1590, 250, 165), 58), k=dict(depth=2, limb=150)),
                           dict(a=(960, 1990, 1810, 40, (930, 1625, 235, 150), 54), k=dict(depth=2, limb=140))],
                     3.0, 0.0)
    return [(far, _sheen(far, rng, 0.5)), (mid, _sheen(mid, rng, 0.8)), (near, _sheen(near, rng, 1.0))]


# --- the scene -------------------------------------------------------------------------------------
class Scene:
    look = "chaand"
    in_order = False

    def __init__(self, facts):
        self.facts = facts
        song = np.random.default_rng(facts.seed)
        self.ph = song.uniform(0, WP, 4)
        self.sway_ph = song.uniform(0, 6.28, 3)
        self.fold_ph = song.uniform(0, 6.28, 2)
        rng = np.random.default_rng(1207)
        yq, xq = np.mgrid[0:h, 0:w].astype(np.float32)
        self.Yf, self.Xf = 2 * yq + 0.5, 2 * xq + 0.5
        dx, dy = MX - self.Xf, MY - self.Yf
        r = np.hypot(dx, dy)
        self.r = r
        self.ux, self.uy = dx / (r + 1), dy / (r + 1)
        wn = np.exp(-r / 260)[..., None]
        self.lcol = (MOON * wn + SILVER * (1 - wn)).astype(np.float32)
        # far: the night sky and the haze low down
        g = P.gradient([(0.0, "#03060e"), (0.22, "#060b1c"), (0.45, "#0a1330"), (0.68, "#111b3e"),
                        (0.80, "#1b2a58"), (0.90, "#16214a"), (1.0, "#0e1636")])[::2, 0, :]
        self.sky = g[:, None, :].astype(np.float32)
        hz = np.exp(-((self.Yf - 1640) / 140) ** 2) * (0.6 + 0.4 * np.exp(-np.abs(self.Xf - MX) / 600))
        self.haze = (hz[..., None] * P.lin("#34467f") * 0.35).astype(np.float32)
        # veil textures
        t1 = octaves(rng, h, WP, [(70, 170, 1.0, 4), (30, 80, 0.6, 2), (12, 32, 0.35, 2), (5, 14, 0.18, 1)])
        self.vt1 = warp(t1, rng, 30, 60)
        self.vt2 = octaves(rng, h, WP, [(14, 55, 1.0, 2), (6, 24, 0.6, 1)])
        # mid bank
        b = octaves(rng, h, WP, [(45, 170, 1.0, 4), (20, 80, 0.55, 2), (9, 38, 0.3, 1), (4, 16, 0.15, 1)])
        b = warp(b, rng, 30, 70)
        yy = np.arange(h, dtype=np.float32)
        YH = 2000.0
        v = np.clip(YH * YH / (YH - np.minimum(yy, 800)) - YH, 0, None)
        self.bt = ndimage.map_coordinates(b, [np.repeat(v[:, None], WP, 1), np.repeat(np.arange(WP, dtype=np.float32)[None], h, 0)],
                                          order=1, mode="grid-wrap").astype(np.float32)
        top = 700 - 130 * ((self.Xf - MX) / 540) ** 2
        lo = 1380 + 60 * pnoise(rng, 1, 1024, 1, 90, 1)[0][np.arange(w) % 1024][None, :]
        self.comp = (-1.9 + 2.3 * sm((self.Yf - top + 60) / 280) + 0.3 * sm((self.Yf - 950) / 200)
                     - 1.7 * sm((self.Yf - lo) / 220)).astype(np.float32)
        self.bank_speed = (0.6 + 0.8 * self.Yf[:, 0] / H).astype(np.float32)
        yl = self.Yf[690:880]
        self.lwin = (sm((yl - 1380) / 120) * (1 - sm((yl - 1720) / 140)) * 0.7).astype(np.float32)
        # the march toward the moon, at quarter size (static geometry)
        hq, wq = h // 2, w // 2
        qy, qx = np.mgrid[0:hq, 0:wq].astype(np.float32)
        mxq, myq = MX / 4, MY / 4
        dxq, dyq = mxq - (qx + 0.5), myq - (qy + 0.5)
        dq = np.hypot(dxq, dyq) + 1e-3
        Lq = np.minimum(dq, 150.0)
        self.msteps = 14
        cs = []
        for i in range(self.msteps):
            sfr = (i + 0.5) / self.msteps * Lq
            cs.append(np.stack([qy + dyq / dq * sfr, qx + dxq / dq * sfr]))
        self.mc = np.concatenate([np.stack([c[0].ravel() for c in cs])[None].reshape(1, -1),
                                  np.stack([c[1].ravel() for c in cs])[None].reshape(1, -1)], 0)
        self.mL = (Lq * 4 / 70.0).astype(np.float32)
        # near scud and low streaks
        sc = octaves(rng, h, WP, [(3, 14, 1.0, 1), (6, 40, 0.6, 1)])
        self.st = sc
        self.scud = [(930, 34, 0.0, 0.50), (1470, 40, 330, 0.65), (800, 26, 620, 0.35)]
        self.lt = octaves(rng, h, WP, [(2.5, 40, 1.0, 1), (6, 110, 0.6, 2)])
        # calm behind the lyrics
        lb = facts.lyric_box
        cx, cy = facts.block_centre
        if lb:
            rx, ry = (lb[2] - lb[0]) / 2 + 280, (lb[3] - lb[1]) / 2 + 240
        else:
            rx, ry = 600, 420
        sc_ = np.exp(-(((self.Xf - cx) / rx) ** 2 + ((self.Yf - cy) / ry) ** 2) * 1.2)
        self.scrim = (1 - 0.35 * sc_)[..., None].astype(np.float32)
        # the moon's disc (full res patch)
        self.PR = int(MR + 30)
        self.px0, self.py0 = int(MX) - self.PR, int(MY) - self.PR
        self._moon(rng)
        self.trees = build_trees()
        self.tree_col = [P.lin("#1e2c58"), P.lin("#121a36"), P.lin("#0d1328")]
        self.vig = P.vignette(0.30, 0.35)
        self.dur = facts.duration
        L = facts.last_line_s if (facts.words and facts.last_line_s is not None) else 0.85 * self.dur
        self.L = min(L, self.dur - 2.6) if self.dur > 6 else L
        self.marks = [m[0] for m in facts.marks]
        bh = H - TY0
        self.ty, self.tx = np.mgrid[0:bh, 0:W].astype(np.float32)

    def describe(self) -> str:
        m = len(self.marks)
        return f"moon behind a veil of cloud; hem breathes per word, {m} peek(s), full lift at {self.L:.1f}s"

    # -- moon ------------------------------------------------------------------------------------
    def _moon(self, rng):
        n = 2 * self.PR
        yy, xx = np.mgrid[0:n, 0:n].astype(np.float32)
        u, v = (xx + self.px0 + 0.5 - MX) / MR, (yy + self.py0 + 0.5 - MY) / MR
        rr = np.hypot(u, v)
        self.cover = np.clip((1 - rr) * MR / 1.6 + 0.5, 0, 1).astype(np.float32)
        wob = ndimage.gaussian_filter(rng.standard_normal((n, n)).astype(np.float32), 5)
        wob /= wob.std()
        fine = ndimage.gaussian_filter(rng.standard_normal((n, n)).astype(np.float32), 1.2)
        fine /= fine.std()
        # (u, v, a, b, tilt): big connected seas of the familiar face
        seas = [(-0.52, -0.12, 0.30, 0.52, 0.2, 1.0),    # Procellarum
                (-0.30, -0.50, 0.32, 0.26, 0.3, 1.0),    # Imbrium
                (0.22, -0.38, 0.22, 0.20, 0.0, 1.0),     # Serenitatis
                (0.40, -0.02, 0.30, 0.22, -0.3, 1.0),    # Tranquillitatis
                (0.0, -0.26, 0.20, 0.10, 0.0, 0.9),      # bridge Imbrium-Serenitatis
                (-0.12, 0.02, 0.30, 0.14, 0.0, 0.85),    # bridge Procellarum-Tranquillitatis
                (0.62, 0.30, 0.13, 0.22, 0.3, 0.8),      # Fecunditatis
                (-0.40, 0.42, 0.22, 0.16, 0.0, 0.85)]    # Nubium / Humorum
        dark = np.zeros_like(rr)
        for cu, cv, a, b, tilt, k in seas:
            c, s = math.cos(tilt), math.sin(tilt)
            du, dv = u - cu, v - cv
            rho = np.hypot((du * c + dv * s) / a, (-du * s + dv * c) / b) + 0.22 * wob
            dark = np.maximum(dark, k * sm((1.15 - rho) / 0.6))
        dark = ndimage.gaussian_filter(dark, 2.2)
        bright = np.exp(-(((u + 0.1) / 0.18) ** 2 + ((v - 0.72) / 0.14) ** 2))
        alb = (1 - 0.30 * dark) * (1 + 0.03 * fine + 0.06 * bright) * (1 - 0.22 * np.clip(rr, 0, 1) ** 3)
        self.alb = (alb * self.cover).astype(np.float32)

    # -- timing ----------------------------------------------------------------------------------
    def opening(self, t: float) -> float:
        f = self.facts
        if not f.words:
            x = t / (0.85 * self.dur)
            return float(min(1.0, sm(x) + 0.018 * math.sin(2 * math.pi * t / 6.5) * (1 - sm(x))))
        base = 0.0 + 0.10 * float(sm(t / self.L))
        level, active = base, 0.0
        for n, s in enumerate(self.marks):
            peak = min(0.27 + 0.11 * n, 0.62)
            rest = 0.42 * peak
            a = t - s
            if a < -0.9:
                continue
            if a < 0:
                e = peak * float(sm((a + 0.9) / 0.9))
            elif a < 1.5:
                e = peak
            elif a < 3.1:
                e = rest + (peak - rest) * (1 - float(sm((a - 1.5) / 1.6)))
            else:
                e = rest
            active = max(active, e)
            if a >= 3.1:
                level = max(level, rest)
        breath = P.envelope(t, [s - 0.1 for s in f.starts], 0.25, 1.0) * 0.04
        o = max(level + breath, active)
        lift = float(sm((t - self.L) / 2.6))
        return float(min(1.0, max(o, lift)))

    # -- frame -----------------------------------------------------------------------------------
    def _static(self):
        r = self.r
        e = np.clip(r - MR, 0, None)
        self.aur0 = ((0.20 * np.exp(-e / 24) + 0.06 * np.exp(-e / 80))[..., None] * MOON).astype(np.float32)
        self.aur1 = ((0.05 * np.exp(-e / 160) + 0.010 * np.exp(-r / 520) + 0.012 * np.exp(-r / 800))[..., None]
                     * BLUEAIR).astype(np.float32)
        self.incore = sm((r - MR * 0.5) / (MR * 1.3)) * 0.75 + 0.25
        self.e330, self.e500, self.e380 = np.exp(-r / 330), np.exp(-r / 500), np.exp(-r / 380)
        self.rows_i = np.arange(H - TY0)[:, None]
        self.cols_i = np.arange(W)[None, :]
        self.vfall = 1 - (np.arange(H - TY0) / (H - TY0 - 1.0)) ** 1.3
        yb = np.arange(H - TY0, dtype=np.float32)[:, None] + TY0
        self.mist = [(np.exp(-((yb - y0) / sy) ** 2) * np.ones((1, W), np.float32) * a).astype(np.float32)
                     for y0, sy, a in ((1600, 70, 0.030), (1720, 60, 0.018), (1850, 90, 0.012))]
        self.mistcol = P.lin("#3e4e7c")

    def _sway(self, m, sh):
        s0 = np.floor(sh)
        fr = (sh - s0).astype(np.float32)[:, None]
        i0 = np.clip(self.cols_i + s0.astype(np.int64)[:, None], 0, W - 2)
        a, b = m[self.rows_i, i0], m[self.rows_i, i0 + 1]
        return a + (b - a) * fr

    def frame(self, k: int, ink=None) -> np.ndarray:
        if not hasattr(self, "aur0"):
            self._static()
        t = k / self.facts.fps
        o = self.opening(t)
        rise = 0.2 + 0.8 * float(sm((t - 2.8) / 1.4))   # the moon comes out after the title card
        Xf, Yf, r = self.Xf, self.Yf, self.r
        flux = 0.5 + 0.5 * float(sm(o / 0.8))
        # ---- the veil
        apex = (MY + 62) - (MY + 62 - 170) * o ** 0.72
        arch = 0.0003 + 0.0018 * o ** 0.6
        xc = Xf[0] - MX
        hem = (apex + arch * xc ** 2 + 0.06 * xc + 14 * np.sin(2 * math.pi * (xc / 420 - t / 8) + self.fold_ph[0])
               + 8 * np.sin(2 * math.pi * (xc / 190 + t / 6) + self.fold_ph[1])).astype(np.float32)
        F1 = roll(self.vt1, self.ph[0] + 5.0 * t)
        F2 = roll(self.vt2, self.ph[1] + 7.5 * t)
        dist = (hem[None, :] - Yf) / 100            # above the hem, in 100 px
        arg = dist + 0.75 * F1 + 0.22 * F2
        D0 = sm((arg + 0.25) / 1.0)
        fib = np.clip(0.5 + 0.3 * F2, 0, 1)
        D = D0 * (0.50 + 0.50 * sm(0.5 + 0.55 * F1 + 0.3 * F2)) * (0.75 + 0.25 * sm(dist / 4.2))
        Tv = np.exp(-2.1 * D)
        dm = float(D[int(MY / 2) - 20:int(MY / 2) + 20, int(MX / 2) - 20:int(MX / 2) + 20].mean())
        breath = (1 + 0.10 * dm) * (1 + 0.04 * math.sin(2 * math.pi * t / 5.5))
        swell = 1 + 0.6 * P.envelope(t, self.marks, 0.3, 2.0)   # the moon glows up on a hero word
        aur = (self.aur0 + self.aur1 * (0.7 + 1.4 * o)) * breath * rise * swell
        Sx = (self.sky + self.haze * (0.75 + 0.25 * flux) + aur) * Tv[..., None]
        # the veil is lit from the moon: brightest along its hem, fading up into the sheet
        edge = np.exp(-np.clip(arg, 0, None) * 1.25)
        puff = np.clip(0.60 + 0.42 * F1 + 0.15 * F2, 0.12, 1.6)
        lum = (0.50 * self.e330 + 0.04 + 0.10 * o * self.e500) * self.incore * rise
        glow = D * lum * (0.30 + 0.70 * edge) * puff
        rimb = 4 * D0 * (1 - D0)
        glow += rimb * (0.30 * self.e330 + 0.02) * (0.15 + 0.85 * o) * puff * self.incore * rise
        Sx += glow[..., None] * self.lcol + (D * 0.010)[..., None] * P.lin("#2b3a68")
        # ---- the mid bank, lit by the moon through the cloud between
        Db = sm((roll(self.bt, self.ph[2] + 9.0 * t * self.bank_speed) * 1.0 + self.comp + 0.5) / 1.6) ** 1.15
        Dq = Db.reshape(h // 2, 2, w // 2, 2).mean((1, 3))
        acc = ndimage.map_coordinates(Dq, self.mc, order=1, mode="nearest").reshape(self.msteps, h // 2, w // 2).mean(0)
        trans = P.resize(np.exp(-acc * self.mL * 2.4).astype(np.float32), w, h)
        body = 0.7 + 0.32 * np.clip(roll(self.vt2, self.ph[2] * 0.3 + 3.3 * t), -1.5, 1.5)
        lit = trans * (0.50 * self.e380 + 0.02) * flux * body * (0.5 + 0.5 * rise)
        Tm = np.exp(-3.0 * Db)
        Sx = Sx * Tm[..., None] + (1 - Tm)[..., None] * SLATE + (lit * (1 - Tm))[..., None] * self.lcol
        # ---- low streaks across the horizon haze (only the rows they live in)
        r0, r1 = 690, 880
        Dl = np.clip(roll(self.lt[r0:r1], self.ph[3] + 14.0 * t) * 0.9 + 0.2, 0, 1) * self.lwin
        Sx[r0:r1] = Sx[r0:r1] * (1 - Dl[..., None]) + Dl[..., None] * P.lin("#0a1026")
        # ---- near scud (dark, faster)
        for y0, th, x0, a in self.scud:
            ra, rb = max(int((y0 - 3 * th) / 2), 0), min(int((y0 + 3 * th) / 2), h)
            rows = np.exp(-(((Yf[ra:rb, :1] - y0) / th) ** 2))
            tx = roll(self.st[ra:rb], x0 + 20.0 * t)
            Dn = np.clip(rows * (0.85 + 0.35 * tx) * a, 0, 0.9)
            Sx[ra:rb] = Sx[ra:rb] * (1 - Dn[..., None]) + Dn[..., None] * P.lin("#05070f")
        Sx *= self.scrim
        # ---- full size
        x = P.up(Sx)
        # the moon's crisp disc behind the veil
        px0, py0, n = self.px0, self.py0, 2 * self.PR
        box = (px0 / 2, py0 / 2, (px0 + n) / 2, (py0 + n) / 2)
        Tp = P.resize(Tv, n, n, box=box)
        aurp = np.stack([P.resize((aur[..., c] * Tv), n, n, box=box) for c in range(3)], -1)
        disc = 0.95 * rise * self.alb[..., None] * MOON * Tp[..., None]
        x[py0:py0 + n, px0:px0 + n] += disc - self.cover[..., None] * aurp
        np.clip(x, 0, None, out=x)
        # ---- trees: a far grove, a middle row, near crowns; mist between them
        band = x[TY0:]
        for i, (mask, sheen) in enumerate(self.trees):
            band += (self.mist[i] * (0.75 + 0.25 * flux))[..., None] * self.mistcol
            if i > 0:
                sh = 1.6 * (i + 0.6) * math.sin(2 * math.pi * t / (4.0 + i) + self.sway_ph[i]) * self.vfall
                m, s = self._sway(mask, sh), self._sway(sheen, sh)
            else:
                m, s = mask, sheen
            s = s * (0.05 + 0.20 * o) * (0.6 if i == 0 else 1.0)
            band += m[..., None] * (self.tree_col[i] - band)
            band += s[..., None] * SILVER
        rgb = P.finish(x, bloom=0.32, bloom_sigma=8, knee=0.5, soft=0.5, vig=self.vig)
        # a slow push-in toward the moon over the whole song, so the night is never still
        z = 1 + PUSH * min(t / max(self.dur, 1.0), 1.0)
        bw, bh = W / z, H / z
        x0, y0 = MX - (MX / W) * bw, MY - (MY / H) * bh
        img = Image.fromarray(rgb).resize((W, H), Image.BICUBIC, box=(x0, y0, x0 + bw, y0 + bh))
        return np.asarray(img)
