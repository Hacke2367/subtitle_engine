"""The ghata look (H-038 classics idea, docs/backgrounds/classics_ghata.md): "Kaali Ghata", for old
classics. A monsoon evening over open fields: a heavy dark cloud mass rolls in from the left over
a last warm band of light at the horizon; a telegraph line runs away across the fields, and tall
grass stands close to us.

Song reaction (facts only): each sung word sends a gust (a wave runs through the grass, the wires
swing); each new line lets the cloud base creep lower over the band of light; a marked word lights
the clouds softly from inside, like lightning far away (it swells and fades, never a flash); on the
last line the first rain arrives and the band goes out ("barsaat aa gayi").

The clouds are lit only from below, by the band: a pixel's light falls with the cloud matter
between it and the horizon, so only the undersides that hang lowest catch the warm light. Frames
are pure functions of k (worker processes)."""
from __future__ import annotations

import math

import numpy as np
from PIL import Image, ImageDraw, ImageFilter
from scipy import ndimage

from . import paint as P
from .chaand import octaves, pnoise, roll, warp   # the shared periodic noise and its drift

W, H = P.W, P.H
F = 2
w, h = W // F, H // F
WP = 2 * w                                        # period of the drifting textures (half px)
HZ = 1560                                         # the horizon row
RF, VX, EYE = 1100.0, 540.0, 1.6                  # focal length, vanishing x, eye height (m)
BAND = P.lin("#f0a878")                           # the last light: amber with a little rose
ROSE = P.lin("#d98a86")
SLATE = P.lin("#121a28")
INNER = P.lin("#c9c3e0")                          # far lightning seen through cloud: pale, cool
RAIN = P.lin("#dfe6f2")
SCRIM = 0.42
sm = P.smooth


def proj(X, Y, Z):
    return VX + RF * X / Z, HZ - RF * (Y - EYE) / Z


def billow(rng, hh, ww, spec):
    """Cumulus texture: rounded lobes with creases between them (|noise| octaves), periodic."""
    out = np.zeros((hh, ww), np.float32)
    for sy, sx, wt, sh in spec:
        out += wt * np.abs(pnoise(rng, hh, ww, sy, sx, sh))
    out = (out - out.mean()) / (out.std() + 1e-6)
    return out.astype(np.float32)


def raster(shapes, box, blur=0.5):
    """Lines and polygons drawn at 2x inside box (x0, y0, x1, y1) and shrunk: an (y1-y0, x1-x0) mask."""
    x0, y0, x1, y1 = box
    im = Image.new("L", (2 * (x1 - x0), 2 * (y1 - y0)), 0)
    d = ImageDraw.Draw(im)
    for kind, pts, *rest in shapes:
        pts = [(2 * (x - x0), 2 * (y - y0)) for x, y in pts]
        if kind == "poly":
            d.polygon(pts, fill=255)
        else:
            d.line(pts, fill=rest[1] if len(rest) > 1 else 255, width=max(1, round(2 * rest[0])),
                   joint="curve")
    m = np.asarray(im.resize((x1 - x0, y1 - y0), Image.LANCZOS), np.float32) / 255
    return ndimage.gaussian_filter(m, blur) if blur else m


class Scene:
    look = "ghata"
    in_order = False                 # any frame can be drawn on its own

    def __init__(self, facts):
        self.facts = facts
        song = np.random.default_rng(facts.seed)
        self.ph = song.uniform(0, WP, 4)
        rng = np.random.default_rng(1931)
        yq, xq = np.mgrid[0:h, 0:w].astype(np.float32)
        self.Yf, self.Xf = F * yq + 0.5, F * xq + 0.5
        # the cloud textures: big lobes for the mass, a lower shelf with its own rhythm
        self.tm = warp(billow(rng, h, WP, [(95, 150, 1.0, 4), (40, 62, 0.55, 2), (18, 24, 0.35, 1),
                                           (7, 9, 0.16, 1)]), rng, 10, 22)
        self.ts = warp(billow(rng, h, WP, [(60, 120, 1.0, 4), (24, 46, 0.5, 2), (9, 16, 0.22, 1)]),
                       rng, 18, 40)
        self.tf = octaves(rng, h, WP, [(8, 40, 1.0, 1), (3, 14, 0.5, 1)])     # fine scud in the band
        self.edge = pnoise(rng, 1, WP, 1, 70, 1)[0]                            # the shelf's ragged base
        # the sky behind: near black at the top, slate lower down, the band at the horizon
        self.sky = P.gradient([(0.0, "#05070c"), (0.35, "#0a0e17"), (0.6, "#121825"),
                               (0.74, "#1b2130"), (HZ / H, "#3a3236"), (1.0, "#0b0c0f")])[::F, :1, :]
        # the land: a tree line on the horizon, fields that catch a little of the band
        self.land, self.land_a = self._land(rng)
        # telegraph poles running away to the left (m): their crossarm ends carry two wires
        self.poles = [(15.0 - 13.0 * i, 42.0 + 55.0 * i) for i in range(10)]
        self.pole_mask = raster(self._pole_shapes(), (0, 1380, W, 1640), 0.4)
        # grass close to us: blades (base x, height px, lean, thickness, phase)
        g = np.random.default_rng(77)
        n = 420
        self.blades = np.stack([g.uniform(-30, W + 30, n), g.uniform(120, 300, n) * g.uniform(0.7, 1.0, n),
                                g.normal(0.12, 0.12, n), g.uniform(1.0, 2.8, n), g.uniform(0, 6.28, n)], 1)
        self.blades = self.blades[np.argsort(self.blades[:, 1])]
        # rain drops for the last line (depth 0 far .. 1 near)
        r = np.random.default_rng(facts.seed + 5)
        nd = 520
        self.rz = r.uniform(0, 1, nd) ** 0.8
        self.rx = r.uniform(-80, W + 80, nd)
        self.rph = r.uniform(0, 1, nd)
        self.rv = (420 + 520 * self.rz) * r.uniform(0.9, 1.1, nd)
        # calm behind the lyrics
        bx, by = facts.block_centre
        lb = facts.lyric_box
        rx, ry = ((lb[2] - lb[0]) / 2 + 260, (lb[3] - lb[1]) / 2 + 220) if lb else (600, 400)
        self.scrim_h = (1 - SCRIM * np.exp(-(((self.Xf - bx) / rx) ** 2 + ((self.Yf - by) / ry) ** 2) * 1.2)
                        )[..., None].astype(np.float32)
        self.calm_full = P.scrim(bx, by, rx, ry)[..., 0]
        self.vig = P.vignette(0.25, 0.3)
        # the song
        f = facts
        self.dur = f.duration
        L = f.last_line_s if (f.words and f.last_line_s is not None) else 0.85 * f.duration
        self.L = min(L, self.dur - 2.5) if self.dur > 6 else L
        self.starts = f.starts
        self.marks = [m[0] for m in f.marks]
        self.lines = list(f.line_starts)
        mr = np.random.default_rng(f.seed + 9)
        self.mark_xy = [(mr.uniform(180, 900), mr.uniform(260, 700)) for _ in self.marks]

    def describe(self) -> str:
        return (f"monsoon clouds over fields; {len(self.marks)} glow(s) inside the clouds; "
                f"rain from {self.L:.1f} s")

    # --- the land, drawn once ---------------------------------------------------------------------
    def _land(self, rng):
        yy, xx = P.grids()
        x = np.zeros((H, W, 3), np.float32)
        a = np.zeros((H, W), np.float32)
        # fields: dark earth, a wet sheen near the horizon that mirrors the band, furrows toward us
        below = (yy >= HZ).astype(np.float32)
        dy = np.clip(yy - HZ, 0, None)
        tex = 0.8 + 0.2 * np.tanh(P.fbm(rng, ((3, 1.0, 1.0), (10, 2.0, 0.8))))
        field = P.lin("#141513") * tex[..., None] * (0.6 + 0.4 * np.exp(-dy / 220))[..., None]
        # flooded paddies near the horizon: long thin strips of water that mirror the band
        strips = pnoise(rng, H // 2, W // 2, 1.2, 50.0, 1)
        wet = P.up(np.clip(strips * 1.0 - 0.9, 0, 1)[..., None])[..., 0] * np.exp(-dy / 55)
        x += (field + (wet * 0.10)[..., None] * BAND) * below[..., None]
        a += below
        # the tree line: one continuous ragged silhouette; a few big trees whose crowns are clusters
        # of small uneven clumps (never smooth domes)
        top = (HZ - 12 - 10 * np.clip(ndimage.gaussian_filter(rng.standard_normal(W), 26) * 6, -1, 1)
               - 6 * np.clip(ndimage.gaussian_filter(rng.standard_normal(W), 6) * 4, -1, 1)
               - 3 * np.clip(ndimage.gaussian_filter(rng.standard_normal(W), 1.5) * 2, -1, 1))
        hedge = ((yy > top[None, :]) & (yy < HZ + 3)).astype(np.float32)
        # a few big trees (mango, neem): a trunk and a crown made of uneven clumps, sky between
        shapes = []
        for cx in rng.uniform(40, 1040, 6):
            R = rng.uniform(22, 40)                                  # half the crown's width
            cy = HZ - 8 - 0.95 * R
            shapes.append(("line", [(cx, HZ + 2), (cx + rng.normal(0, 2), cy + 0.2 * R)], max(1.0, 0.08 * R)))
            shapes.append(("poly", [(cx + 0.8 * R * math.cos(a), cy + 0.12 * R + 0.32 * R * math.sin(a))
                                    for a in np.linspace(0, 2 * np.pi, 24)]))
            for _ in range(26):                                      # a broad, uneven canopy of leaf clumps
                dx = rng.uniform(-1, 1)
                bx = cx + dx * R
                by = cy + 0.15 * R - rng.uniform(0, 0.62) * R * math.sqrt(max(1 - dx * dx, 0))
                r = rng.uniform(0.1, 0.2) * R
                shapes.append(("poly", [(bx + r * math.cos(a), by + 0.85 * r * math.sin(a))
                                        for a in np.linspace(0, 2 * np.pi, 12)]))
        box = (0, HZ - 120, W, HZ + 10)
        tm = np.zeros((H, W), np.float32)
        tm[box[1]:box[3]] = raster(shapes, box, 0.8)
        trees = np.maximum(ndimage.gaussian_filter(hedge, 1.2), tm)
        x = x * (1 - trees[..., None]) + trees[..., None] * P.lin("#0a0a0c")
        a = np.maximum(a, trees)
        return x.astype(np.float32), a.astype(np.float32)

    def _pole_shapes(self, swing: float = 0.0):
        shapes = []
        ends = []
        for X, Z in self.poles:
            bx, by = proj(X, 0.0, Z)
            tx, ty = proj(X, 7.2, Z)
            s = RF / Z
            shapes.append(("line", [(bx, by), (tx, ty)], max(0.6, 0.22 * s)))
            for ya in (6.7, 6.1):                                     # two crossarms
                l, r = proj(X - 0.8, ya, Z), proj(X + 0.8, ya, Z)
                shapes.append(("line", [l, r], max(0.5, 0.12 * s)))
            ends.append([(X + dx, ya, Z) for ya in (6.7, 6.1) for dx in (-0.7, 0.7)])
        self.ends = ends
        return shapes

    def _wires(self, swing: float):
        """The wires between neighbouring poles: sagging, swinging a little with the wind."""
        shapes = []
        for a, b in zip(self.ends, self.ends[1:]):
            for j, ((X0, Y0, Z0), (X1, Y1, Z1)) in enumerate(zip(a, b)):
                pts = []
                for u in np.linspace(0, 1, 14):
                    sag = 0.9 * 4 * u * (1 - u)
                    Xs = X0 + (X1 - X0) * u + swing * (0.6 + 0.1 * j) * 4 * u * (1 - u)
                    pts.append(proj(Xs, Y0 + (Y1 - Y0) * u - sag, Z0 + (Z1 - Z0) * u))
                shapes.append(("line", pts, 0.55))
        return shapes

    # --- the song ---------------------------------------------------------------------------------
    def creep(self, t: float) -> float:
        """How far the cloud base has come down over the band, 0..1 (1: the band is gone)."""
        if not self.facts.words:
            return float(0.85 * sm(t / max(self.dur, 1.0)))
        n = max(len(self.lines), 1)
        steps = sum(float(sm((t - s) / 1.6)) for s in self.lines) / n
        return float(min(1.0, 0.75 * steps + 0.25 * sm((t - self.L) / 2.0)))

    def gust(self, t: float) -> float:
        if not self.facts.words:
            return 0.35 + 0.25 * math.sin(t * 0.9) * math.sin(t * 0.37 + 1.0)
        return P.envelope(t, self.starts, 0.25, 1.5)

    def rain(self, t: float) -> float:
        return float(sm((t - self.L) / 2.2))

    # --- a frame ----------------------------------------------------------------------------------
    def frame(self, k: int, ink=None) -> np.ndarray:
        t = k / self.facts.fps
        c = self.creep(t)
        Xf, Yf = self.Xf, self.Yf
        # the cloud base: the shelf hangs lowest; it comes down as the song goes on
        base = 1330 + 150 * c + 18 * np.clip(roll(self.edge[None, :], self.ph[3] + 6 * t)[0], -1.5, 1.5)
        band_top = base - 30
        # the sky behind, with the warm band under the cloud base
        x = np.repeat(self.sky, w, axis=1).copy()
        under = sm((Yf - band_top) / 160) * (1 - sm((Yf - HZ) / 30))
        bandl = (1 - 0.85 * c) * under * (0.55 + 0.45 * sm((Yf - band_top - 60) / 140))
        x += bandl[..., None] * (BAND * 0.42 + ROSE * 0.06)
        # the clouds: the high mass and the low shelf (faster, nearer), as density
        Tm = roll(self.tm, self.ph[0] + 4.0 * t)
        Ts = roll(self.ts, self.ph[1] + 9.0 * t)
        dm = sm((Tm * 0.55 + 1.15 - 3.2 * sm((Yf - (base - 280)) / 300)) / 1.1)
        ds = sm((Ts * 0.6 + 0.6 - 4.0 * sm((Yf - base + 30) / 45) - 1.2 * sm((base - 330 - Yf) / 240)) / 0.9)
        D = np.maximum(dm, ds)
        # light from the band below: what reaches each pixel through the cloud beneath it
        below = np.flip(np.cumsum(np.flip(D, 0), 0), 0) * (F / 40.0)
        lit = np.exp(-1.6 * below) * (1 - 0.85 * c) * sm((Yf - 200) / 600)
        # the lobes' form: faces turned down catch the band a little deeper in, faces turned up the
        # last cold light of the sky above; lobes lighter than the creases between them
        Tsm = np.where(ds > dm, Ts, Tm)
        gy = np.gradient(Tsm, axis=0)
        lobe = sm(Tsm * 0.45 + 0.5)
        down = np.clip(-gy * 6.0, 0, 1) * np.exp(-0.5 * below) * (1 - 0.85 * c)
        upf = np.clip(gy * 6.0, 0, 1)
        col = (SLATE * (0.45 + 0.75 * lobe)[..., None] + upf[..., None] * P.lin("#3c475e") * 0.05
               + (lit + 0.35 * down)[..., None] * (BAND * 0.38 + ROSE * 0.10) * (0.7 + 0.5 * lobe)[..., None])
        # far lightning inside the mass on marked words: a soft swell that lights the cloud from
        # within, strongest on the lobes facing it, the creases staying dark
        for (mx, my), s in zip(self.mark_xy, self.marks):
            g = P.envelope(t, [s], 0.35, 1.6)
            if g <= 0:
                continue
            glow = np.exp(-(((Xf - mx) / 360) ** 2 + ((Yf - my) / 280) ** 2))
            col += (g * 0.22 * glow * (0.25 + lobe))[..., None] * INNER
            x += (g * 0.04 * glow)[..., None] * INNER
        A = 1 - np.exp(-3.2 * D)
        x = x * (1 - A[..., None]) + col * A[..., None]
        # scud: thin dark fragments drifting fast across the band
        sc = np.clip(roll(self.tf, self.ph[2] + 22 * t) * 0.8 - 0.2, 0, 1) * under * 0.5
        x = x * (1 - sc[..., None]) + sc[..., None] * SLATE * 0.6
        x *= self.scrim_h
        x = P.up(x)
        # the land
        x = x * (1 - self.land_a[..., None]) + self.land
        x[HZ:] += (np.exp(-(np.arange(H - HZ) / 50.0)) * 0.05 * (1 - 0.85 * c))[:, None, None] * BAND
        # the telegraph line against the band: poles fixed, wires swinging with the gusts
        gu = self.gust(t)
        swing = 0.25 * gu * math.sin(2 * math.pi * t / 1.7)
        box = (0, 1380, W, 1640)
        m = np.maximum(self.pole_mask, raster(self._wires(swing), box, 0.35))
        reg = x[1380:1640]
        reg *= 1 - 0.9 * m[..., None]
        # rain
        rn = self.rain(t)
        if rn > 0:
            x = self._rain(x, t, rn)
        # grass close to us, a gust running through it from left to right
        x = self._grass(x, t, gu)
        return P.finish(x, bloom=0.22, bloom_sigma=7, knee=0.45, soft=0.5, vig=self.vig)

    def _grass(self, x, t, gu):
        y0 = 1590
        im = Image.new("L", (W, H - y0), 0)
        d = ImageDraw.Draw(im)
        base_y = H - y0 + 10
        for bx, ht, lean, th, ph in self.blades:
            wave = P.envelope(t - bx / 900.0, self.starts, 0.3, 1.6) if self.facts.words else gu
            bend = lean + 0.10 * math.sin(t * 1.3 + ph) + 0.55 * wave
            pts = []
            for s in np.linspace(0, 1, 7):
                pts.append((bx + bend * ht * s * s, base_y - ht * s * (1 - 0.15 * abs(bend) * s)))
            d.line(pts, fill=255, width=max(1, round(th)), joint="curve")
        m = np.asarray(im.filter(ImageFilter.GaussianBlur(1.1)), np.float32)[..., None] / 255
        reg = x[y0:]
        tip = np.clip(m[..., 0] - np.roll(m[..., 0], 3, axis=0), 0, 1)[..., None]
        reg *= 1 - m
        reg += m * P.lin("#08090a") + tip * BAND * 0.05 * (1 - 0.8 * self.creep(t))
        return x

    def _rain(self, x, t, rn):
        im = Image.new("L", (W, H), 0)
        d = ImageDraw.Draw(im)
        wind = 0.10
        n = int(len(self.rz) * rn)
        for i in range(n):
            z, v = self.rz[i], self.rv[i]
            land = HZ + 20 + (H - HZ - 20) * z
            period = (land + 60) / v
            s = (t + self.rph[i] * period) % period
            y = -60 + v * s
            x0 = self.rx[i] + wind * y
            ln = 14 + 26 * z
            d.line([(x0 - wind * ln, y - ln), (x0, y)], fill=int(40 + 130 * z), width=1 if z < 0.7 else 2)
        m = np.asarray(im.filter(ImageFilter.GaussianBlur(0.7)), np.float32) / 255
        m *= rn * (1 - 0.65 * self.calm_full)
        x += (m * 0.16)[..., None] * RAIN
        return x
