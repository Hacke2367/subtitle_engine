"""The jaali look (H-038, docs/backgrounds/sufi_jaali.md): "Jaali se subah". A carved stone lattice
high in the back wall of a dark dargah hall. Moonlight falls through it in soft beams through incense
haze and lays the lattice's pattern on the polished floor near the wall. Line by line the light moves
one eased step forward, so the pattern walks across the floor toward the viewer; over the song the
night turns rose, then gold, and on the last line the warm pattern lies at the viewer's feet.

One physical light: a parallel beam (moon, then sun). The beams in the air are the lattice's light
zoomed about the beam's vanishing point (exact for a parallel beam), cut where each hole's light
reaches the floor; the floor pattern traces every floor point back to the lattice (closed form). The
hall, the lattice and the pillars are drawn once; per frame only light is worked out, so every frame
is a pure function of its time (worker processes).

Song reaction (facts only): each sung word breathes a little incense into the beams (it glows only
where it crosses light); a marked word clears the moon for ~3 s (crisper, brighter pattern); each
line moves the light a step; the last line completes the dawn. Ported from the sample
songs/_review/backgrounds/templates/sufi/jaali.py."""
from __future__ import annotations

import math

import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage

from . import paint as P

W, H = P.W, P.H
E8 = 8                                      # the soft light is worked out at 1/8 size
h8, w8 = H // E8, W // E8
# Camera: an eye 1.5 m above the floor, level, looking at the back wall. Screen y 1280 is eye
# level; the wall meets the floor at FY. Metres on the wall per px: PXM.
CF, CX0, CY0, HC = 1100.0, 540.0, 1280.0, 1.5
FY = 1450
ZW = CF * HC / (FY - CY0)                   # ~9.7 m to the back wall
PXM = ZW / CF
# The window: a pointed arch; the lattice inside a carved band.
JX0, JX1, JYA, JYS, JYB = 322, 738, 76, 330, 760
JCX = (JX0 + JX1) / 2
PITCH, R_STAR, M_STAR, WEB, BAND = 60.0, 0.47, 4.0, 6.0, 20.0
CX_0, CX_1, CY_0, CY_1 = 200, 880, 0, 840   # the carved area, worked at full size
YTOP = HC + (CY0 - JYA) * PXM               # the window's top, metres above the floor
ZNEAR = 2.5                                 # beams nearer the camera than this fade out
NIGHT_R, NIGHT_LX, DAWN_R, DAWN_LX = 0.44, -0.16, 0.84, -0.04   # the light's path per metre of drop
STEPS = 220
SCRIM = 0.5
AMB, GLOW_S, GLOW_L, BOUNCE, FLOOR_AMB = 0.07, 0.3, 0.06, 0.45, 0.04   # how the hall is lit
POOL, BEAM, VEIL, SKY = 2.4, 0.11, 0.05, 0.36
FADE = 4.0                                  # m: the beams fade as they come down

NIGHT = dict(light="#c8d5f6", scat="#35507e", amb="#41507a", sky="#a7bae6", floor="#141b2c",
             rim="#8fa3d6")
DAWN = dict(light="#ffd394", scat="#a8622c", amb="#3a2414", sky="#ffd79c", floor="#2a170a",
            rim="#ffc98e")
# the first light before dawn (brahma muhurat): the night passes through rose, never through grey
ROSE = dict(light="#f2c6c8", scat="#6a4a6e", amb="#4a3a52", sky="#e9c2c4", floor="#1f1620",
            rim="#e8b4b8")


def palette(warm: float) -> dict:
    """The light's colours at this point of the night: night -> rose -> dawn (linear light)."""
    a, b, u = (NIGHT, ROSE, warm / 0.5) if warm < 0.5 else (ROSE, DAWN, (warm - 0.5) / 0.5)
    return {key: P.lin(a[key]) * (1 - u) + P.lin(b[key]) * u for key in NIGHT}


def _hash(a):
    return ((np.sin(a * 12.9898 + 78.233) * 43758.5453) % 1.0).astype(np.float32)


def _arch_d(x, y):
    """Signed distance (positive inside) to the window's two-centred pointed arch."""
    half = (JX1 - JX0) / 2
    rise = JYS - JYA
    r = (half ** 2 + rise ** 2) / (2 * half)
    cl, cr = JX0 + r, JX1 - r
    d_side = np.minimum(x - JX0, JX1 - x)
    d_l = r - np.sqrt((x - cl) ** 2 + (y - JYS) ** 2)
    d_r = r - np.sqrt((x - cr) ** 2 + (y - JYS) ** 2)
    head = np.where(y < JYS, np.minimum(d_l, d_r), 1e4)
    return np.minimum(np.minimum(d_side, JYB - y), head).astype(np.float32)


def _star(ex, ey, r, m, n=8, rot=math.pi / 8):
    """Signed distance to an n-point star polygon of radius r centred at 0 (Quilez's sdStar)."""
    c, s = math.cos(rot), math.sin(rot)
    ex, ey = c * ex - s * ey, s * ex + c * ey
    an, en = math.pi / n, math.pi / m
    acx, acy = math.cos(an), math.sin(an)
    ecx, ecy = math.cos(en), math.sin(en)
    px = np.abs(ex)
    bn = np.mod(np.arctan2(px, ey), 2 * an) - an
    L = np.hypot(px, ey)
    qx, qy = L * np.cos(bn) - r * acx, L * np.abs(np.sin(bn)) - r * acy
    hh = np.clip(-(qx * ecx + qy * ecy), 0, r * acy / ecy)
    qx, qy = qx + ecx * hh, qy + ecy * hh
    return (np.hypot(qx, qy) * np.sign(qx)).astype(np.float32)


def _mask(draw_fn) -> np.ndarray:
    """A silhouette drawn at 2x (clean edges), 0..1 at full size."""
    im = Image.new("L", (W * 2, H * 2), 0)
    draw_fn(ImageDraw.Draw(im), lambda *v: [2 * c for c in v])
    return np.asarray(im.resize((W, H), Image.LANCZOS), np.float32) / 255


def _near_arcade(d, s):
    """The near arcade: a pillar at each side with a bracket capital and a moulded base, carrying a
    cusped arch whose flanks cross the top of the frame."""
    for side in (-1, 1):
        def X(v):
            return v if side < 0 else W - v
        curve = [(430 - 270 * (1 - (1 - u) ** 1.6), -30 + 420 * u ** 1.3)
                 for u in (i / 40 for i in range(41))]
        pts = [(X(-40), -40), (X(430), -40)] + [(X(a), b) for a, b in curve]
        pts += [(X(160), 410), (X(138), 414), (X(138), 436)]
        for i in range(1, 13):
            u = i / 12
            pts.append((X(138 - 36 * (1 - math.cos(u * math.pi / 2))), 436 + 56 * math.sin(u * math.pi / 2)))
        pts += [(X(102), 1640), (X(114), 1650), (X(114), 1690), (X(128), 1700), (X(128), 1746),
                (X(146), 1756), (X(146), H + 40), (X(-40), H + 40)]
        d.polygon(s(*[c for p in pts for c in p]), fill=255)
        for j in range(1, 6):                                   # cusps bitten into the flank
            a, b = curve[int(j * 40 / 6)]
            d.ellipse(s(X(a) - 25, b - 25, X(a) + 25, b + 25), fill=0)


class Scene:
    look = "jaali"
    in_order = False                 # any frame can be drawn on its own

    def __init__(self, facts):
        self.facts = facts
        rng = np.random.default_rng(11)                        # the hall is the same for every song
        f = facts
        self.last = f.last_line_s if f.last_line_s is not None else 0.85 * f.duration
        self.lines = list(f.line_starts)
        self.marks = [w_[0] for w_ in f.marks]
        self.starts = f.starts
        self._lattice(rng)
        self._hall(rng)
        self._floor_geometry()
        self._haze(rng)
        bx, by = f.block_centre
        scrim = (1 - SCRIM * P.scrim(bx, by, 560, 330)).astype(np.float32)
        self.scrim8 = P.down(scrim, E8)[..., 0]
        self.vig = P.vignette(0.0, border=0.35) * scrim          # the calm patch rides on the border pass
        self.fall = (0.16 * np.exp(-np.arange(H - FY, dtype=np.float32) / 260))[:, None, None]
        self.norm = 1.0
        self.norm = float(np.percentile(self._shafts(NIGHT_R, NIGHT_LX), 99.7)) + 1e-6

    def describe(self) -> str:
        return (f"a dargah's stone jaali; its light walks toward the viewer over {len(self.lines)} "
                f"line(s), the moon clears on {len(self.marks)} marked word(s), dawn by "
                f"{self.last:.1f} s")

    # --- drawn once ------------------------------------------------------------------------------
    def _lattice(self, rng):
        """The carved lattice (full size, in the carved area): openings, how much light each lets
        through, the slab, and the cut faces that can catch light."""
        ys, xs = np.mgrid[CY_0:CY_1, CX_0:CX_1].astype(np.float32)
        dist = _arch_d(xs, ys)
        ox, oy = JCX, JYB - BAND - 0.5 * PITCH
        u, v = (xs - ox) / PITCH, (ys - oy) / PITCH
        iu, iv = np.floor(u), np.floor(v)
        best = np.full(xs.shape, 1e9, np.float32)
        sid = np.zeros(xs.shape, np.float32)
        for du in (0, 1):
            for dv in (0, 1):
                d = _star(xs - ox - (iu + du) * PITCH, ys - oy - (iv + dv) * PITCH, R_STAR * PITCH, M_STAR)
                sel = d < best
                best = np.where(sel, d, best)
                sid = np.where(sel, (iu + du) * 131 + (iv + dv) * 17, sid)
        cid = np.where(best < 0, sid, iu * 71 + iv * 29 + 5003)       # each opening's own id
        h1, h2 = _hash(cid), _hash(cid * 1.37 + 311.7)
        wob = 1 + 0.18 * P.fbm(rng, ((24, 2.0, 1.0),), CY_1 - CY_0, CX_1 - CX_0)
        wear = 0.5 * P.fbm(rng, ((3, 0.8, 1.0),), CY_1 - CY_0, CX_1 - CX_0)
        op = np.clip((np.abs(best) - 0.5 * WEB * wob + wear) / 1.0 + 0.5, 0, 1)
        star = best < 0
        op *= np.clip((dist - BAND) / 1.2 + 0.5, 0, 1) * ~(star & (h1 < 0.05))   # a few stars filled
        dust = np.where(star, np.where(h1 < 0.14, 0.45, 1.0) * (0.75 + 0.25 * h2), 0.85 + 0.15 * h2)
        self.dist = dist
        self.dust = dust.astype(np.float32)
        ob = ndimage.gaussian_filter(op, 1.6)
        gy, gx = np.gradient(ob)
        gn = np.sqrt(gx * gx + gy * gy) + 1e-4
        band = np.clip(ob * (1 - op) * 3.0, 0, 1) * (dist > 0)
        self.face = np.stack([band * gx / gn, band * gy / gn], 0).astype(np.float32)   # cut faces
        self.see = (op * (0.55 + 0.45 * dust)).astype(np.float32)
        T = np.zeros((CY_1, W), np.float32)                   # light let through, frame coords
        core = 0.6 + 0.4 * np.exp(-((xs - JCX) / 230) ** 2 - ((ys - 470) / 330) ** 2)   # brighter middle
        T[CY_0:CY_1, CX_0:CX_1] = op * dust * core
        self.T = T[CY_0:CY_1, CX_0:CX_1]
        t8 = P.down(T, E8)
        self.T8 = [ndimage.gaussian_filter(t8, s) for s in (0.35, 0.9)]
        self.Tf = [ndimage.gaussian_filter(self.T, s) for s in (1.0, 2.2, 4.5, 9.0)]
        self.Tf_sig = np.array([1.0, 2.2, 4.5, 9.0], np.float32)
        # soft shadows of things outside (branches, cloud edges) drifting across the window: they
        # streak the beams into rays and dapple the floor pattern
        rr = ndimage.gaussian_filter(rng.standard_normal((t8.shape[0], 2 * w8)), (3.0, 2.2), mode="wrap")
        self.rays = np.clip(0.55 + 0.75 * rr / rr.std(), 0.12, 1.0).astype(np.float32)
        yrow = np.arange(self.T8[0].shape[0], dtype=np.float32) * E8 + E8 / 2
        self.row_Y = HC + (CY0 - yrow) * PXM                  # each 1/8 row's height (m)
        # clouds drifting behind the lattice, seen through its openings
        cl = P.fbm(rng, ((30, 2.0, 1.0), (10, 2.0, 0.4)), CY_1 - CY_0, CX_1 - CX_0 + 400)
        self.cloud_tex = np.clip(0.92 + 0.12 * cl, 0.6, 1.2).astype(np.float32)
        # the sky behind is brighter toward the moon (upper right) and later the sun (above the apex)
        self.sky_n = (0.7 + 0.6 * np.exp(-((xs - JX1 - 60) ** 2 + (ys - JYA + 40) ** 2) / (2 * 330.0 ** 2)))[..., None]
        self.sky_d = (0.75 + 0.5 * np.exp(-((xs - JCX) ** 2 + (ys - JYA + 120) ** 2) / (2 * 380.0 ** 2)))[..., None]
        self.sky_n, self.sky_d = self.sky_n.astype(np.float32), self.sky_d.astype(np.float32)

    def _hall(self, rng):
        """The back wall and floor albedo with the carved frame's relief baked in, the near arcade."""
        yy, xx = P.grids()
        alb = np.empty((H, W), np.float32)
        # sandstone courses of uneven height, staggered blocks of random width
        tone = np.ones((FY, W), np.float32)
        joint = np.zeros((FY, W), np.float32)
        y = -rng.uniform(0, 30)
        xs = np.arange(W, dtype=np.float32)
        while y < FY:
            ch = rng.uniform(34, 60)
            y0, y1 = int(max(y, 0)), int(min(y + ch, FY))
            if y1 > y0:
                edges = np.cumsum(rng.uniform(80, 200, 14)) - rng.uniform(0, 200)
                k = np.searchsorted(edges, xs)
                dv = np.minimum(np.abs(xs - edges[np.clip(k - 1, 0, 13)]), np.abs(xs - edges[np.clip(k, 0, 13)]))
                rows = np.arange(y0, y1, dtype=np.float32)
                dh = np.minimum(rows - y, y + ch - rows)[:, None]
                jv = np.exp(-(dv[None, :] / 1.3) ** 2)
                joint[y0:y1] = np.maximum(jv, np.exp(-(dh / 1.3) ** 2))
                tone[y0:y1] = (1 + 0.09 * (_hash(k * 7.1 + y * 0.37) - 0.5))[None, :]
            y += ch
        patina = (1 + 0.11 * P.fbm(rng, ((40, 2.0, 1.0),)) + 0.05 * P.fbm(rng, ((8, 1.5, 1.0),))
                  + 0.04 * P.fbm(rng, ((1, 0.7, 1.0),)))
        damp = ndimage.gaussian_filter(rng.standard_normal((H // 4, W // 4)).astype(np.float32), (18, 1.6))
        damp = P.resize(np.clip(damp / damp.std() - 0.6, 0, None), W, H)
        wear_j = np.clip(0.55 + 0.6 * P.fbm(rng, ((6, 1.0, 1.0),)), 0, 1)
        alb[:] = patina * (1 - 0.10 * damp * P.smooth((yy - 200) / 900))
        alb[:FY] *= tone * (1 - 0.22 * joint * wear_j[:FY])
        # the carved frame: splayed reveal, a round moulding, the rectangular alfiz; no joints there
        ys_, xs_ = yy[CY_0:CY_1, CX_0:CX_1], xx[CY_0:CY_1, CX_0:CX_1]
        od = -self.dist
        frame_in = np.minimum(np.minimum(xs_ - (JX0 - 100), (JX1 + 100) - xs_),
                              np.minimum(ys_ - (JYA - 92), (JYB + 56) - ys_))
        carved = (od < 70) | (frame_in > -4)
        hgt = np.where(od < 0, -1.0 + 0.35 * P.smooth((od + BAND) / BAND), np.where(od < 36, -1 + od / 36, 0.0))
        hgt += 0.45 * np.sin(np.pi * np.clip((od - 40) / 26, 0, 1)) * (od > 40) * (od < 66)
        hgt += 0.5 * np.sin(np.pi * np.clip((frame_in - 2) / 26, 0, 1)) * (frame_in > 2) * (frame_in < 28) * (od > 0)
        hgt -= 0.12 * P.smooth((frame_in - 28) / 4) * (od > 70)
        band_bead = (od < 0) & (od > -BAND)                   # the carved band inside the arch
        hgt += 0.25 * np.sin(np.pi * np.clip(-od / BAND, 0, 1)) * band_bead
        hgt = ndimage.gaussian_filter(hgt.astype(np.float32), 1.6)
        gyh, gxh = np.gradient(hgt)
        nx, ny = -30 * gxh, -30 * gyh
        nn = np.sqrt(nx * nx + ny * ny + 1)
        relief = np.clip((ny * 0.55 + 0.78) / nn, 0, None) / 0.78
        ao = 1 - 0.35 * np.exp(-np.clip(od, 0, None) / 10) * (od > 0)
        carve = alb[CY_0:CY_1, CX_0:CX_1]
        base = patina[CY_0:CY_1, CX_0:CX_1]
        carve[:] = np.where(carved, base, carve) * relief * ao
        # lattice stone: bar-to-bar tone
        bar = 1 + 0.10 * P.fbm(rng, ((5, 1.0, 1.0),), CY_1 - CY_0, CX_1 - CX_0)
        carve[:] = np.where(self.dist > 0, base * bar * 0.9, carve)
        # the floor: polished stone slabs in perspective
        zf = CF * HC / (yy[FY:] - CY0)
        Xf = (xx[FY:] - CX0) * zf / CF
        dX = np.abs(Xf - np.round(Xf / 0.9) * 0.9) * CF / zf
        dZ = np.abs(zf - np.round(zf / 0.9) * 0.9) * CF * HC / zf ** 2
        fj = np.maximum(np.exp(-(dX / 1.4) ** 2), np.exp(-(dZ / 1.2) ** 2))
        slab = _hash(np.floor(Xf / 0.9) * 13.7 + np.floor(zf / 0.9) * 3.1)
        alb[FY:] = 0.62 * (1 + 0.08 * (slab - 0.5)) * (1 + 0.05 * P.fbm(rng, ((14, 2.0, 1.0),))[FY:]) \
            * (1 - 0.15 * fj)
        self.alb = (alb[..., None] * P.lin("#a89e92")).astype(np.float32)
        self.alb[FY:] = alb[FY:, :, None] * P.lin("#8e847a")
        self.alb *= (1 - 0.35 * np.exp(-((yy - FY) / 3.0) ** 2))[..., None]   # shadow at the wall's foot
        # the near arcade, out of focus, with a rim where it faces the hall
        near = _mask(_near_arcade)
        edt = ndimage.distance_transform_edt(near > 0.5).astype(np.float32)
        inner = np.where(xx < W / 2, xx, W - xx)
        face = (0.35 + 0.9 * np.exp(-edt / 26.0) * P.smooth((inner - 40) / 60)) \
            * (1 + 0.10 * P.fbm(rng, ((20, 2.0, 1.0),)))
        rim = near * np.clip(1 - ndimage.gaussian_filter(near, 5.0), 0, 1) * 4.0 * P.smooth((yy - 380) / 200)
        nb = ndimage.gaussian_filter(near, 11.0)
        fb = ndimage.gaussian_filter(face * near, 11.0)
        rb = ndimage.gaussian_filter(rim, 11.0)
        regions = [(slice(0, 540), slice(0, W)), (slice(540, H), slice(0, 240)), (slice(540, H), slice(840, W))]
        rest = nb.copy()
        for ys, xs in regions:
            rest[ys, xs] = 0
        assert rest.max() < 2e-3, "the arcade reaches outside its strips"
        self.pillars = [((ys, xs), nb[ys, xs, None].astype(np.float32), fb[ys, xs, None].astype(np.float32),
                         rb[ys, xs, None].astype(np.float32)) for ys, xs in regions]
        # at dawn the night lingers in the upper corners and far edges of the hall
        corner = np.clip(np.exp(-((xx - 540) / 520) ** 2 * 0.9 - ((yy - 900) / 1100) ** 2) * 1.6, 0, 1)
        self.linger8 = P.down((1 - corner)[..., None], E8)[..., 0]

    def _floor_geometry(self):
        """Every half-size floor pixel's depth and sideways place (m)."""
        ys = np.arange(FY, H, 2, dtype=np.float32) + 1
        xs = np.arange(0, W, 2, dtype=np.float32) + 1
        self.fz = np.repeat((CF * HC / (ys - CY0))[:, None], xs.size, 1)
        self.fX = (xs[None, :] - CX0) * self.fz / CF

    def _haze(self, rng):
        """Incense haze drifting through the beams (1/8 size, periodic)."""
        a = ndimage.gaussian_filter(rng.standard_normal((h8, 2 * w8)), (4, 7), mode="wrap")
        b = ndimage.gaussian_filter(rng.standard_normal((h8, 2 * w8)), (2, 3), mode="wrap")
        self.haze_a = (a / a.std()).astype(np.float32)
        self.haze_b = (b / b.std()).astype(np.float32)
        song = np.random.default_rng(self.facts.seed)
        self.puff = [(s, song.uniform(80, 360), song.uniform(-0.3, 0.3)) for s in self.starts]

    # --- the song's state --------------------------------------------------------------------------
    def state(self, t: float) -> dict:
        if self.lines:
            step = sum(float(P.smooth((t - s) / 1.8)) for s in self.lines) / len(self.lines)
        else:
            step = float(P.smooth(t / self.last))
        grace = 0.0
        for m in self.marks:
            a = t - m
            if 0 <= a < 3.6:
                grace = max(grace, float(P.smooth(a / 0.45) * (1 - P.smooth((a - 2.6) / 0.9))))
        warm = float(P.smooth((t - 0.55 * self.last) / (0.45 * self.last + 1.5)))
        passing = float(P.smooth((math.sin(2 * math.pi * t / 19.0 + 1.3) - 0.55) / 0.45))
        cloud = (0.2 + 0.35 * passing) * (1 - grace) * (1 - warm)
        swell = P.envelope(t, self.starts, 0.3, 1.6)
        return dict(step=step, grace=grace, warm=warm, cloud=cloud, swell=swell)

    # --- light ------------------------------------------------------------------------------------
    def _glow(self, warm: float) -> np.ndarray:
        return self.sky_n * (1 - warm) + self.sky_d * warm

    def _rays(self, t: float) -> np.ndarray:
        """The drifting outside shadows over the lattice at time t (1/8 size, frame columns)."""
        d = 0.45 * t
        i, f = int(d), d - int(d)
        a = np.roll(self.rays, -(i % (2 * w8)), 1)
        return a[:, :w8] * (1 - f) + a[:, 1:w8 + 1] * f

    def _shafts(self, r: float, lx: float, rays=None) -> np.ndarray:
        """Beams in the air (1/8 size): the lattice's light zoomed about the beam's vanishing point
        (a parallel beam seen in perspective), each hole's light ending where it reaches the floor."""
        vx, vy = (CX0 - CF * lx / r) / E8, (CY0 - CF / r) / E8
        lnorm = math.sqrt(lx * lx + 1 + r * r)
        zmax = ZW / max(ZNEAR, ZW - YTOP * r)
        acc = np.zeros((h8, w8), np.float32)
        for i in range(STEPS):
            z = 1 + (zmax - 1) * (i + 0.5) / STEPS
            s = ZW / r * (1 - 1 / z)
            depth = ZW - s * r
            wt = (ZW / r) / (z * z) * (zmax - 1) / STEPS * (0.3 + 0.7 * math.exp(-s / FADE)) \
                * float(P.smooth((depth - ZNEAR) / 3.0))
            if wt <= 0:
                continue
            above = self.row_Y - s                             # each row's light: height above the floor
            live = np.clip(above / 0.3, 0, 1) * (0.8 + 0.9 * np.exp(-np.maximum(above, 0) / 2.0))
            if not live.any():
                break
            src = self.T8[0 if s < 7 else 1] * live[:, None]
            if rays is not None:
                src = src * rays
            f = 1 / z
            im = Image.fromarray(np.ascontiguousarray(src, np.float32), "F").transform(
                (w8, h8), Image.AFFINE, (f, 0, vx * (1 - f), 0, f, vy * (1 - f)), resample=Image.BILINEAR)
            acc += np.asarray(im, np.float32) * wt
        return acc / self.norm

    def _pool(self, r: float, lx: float, sharp: float, rays=None) -> np.ndarray:
        """The lattice's light on the floor (half size, floor rows): every floor point traced back
        along the beam to the lattice, softer the farther the light travelled."""
        lnorm = math.sqrt(lx * lx + 1 + r * r)
        s = (ZW - self.fz) / r                                  # drop from the wall plane to here
        qx = CX0 + (self.fX - s * lx) / PXM - CX_0
        qy = CY0 - (s - HC) / PXM - CY_0
        sig = (3.2 + 1.0 * np.clip(s - 5.5, 0, None)) * sharp   # wall px
        lv = np.clip(np.interp(sig, self.Tf_sig, np.arange(4)), 0, 2.999)
        l0 = lv.astype(np.int32)
        fr = lv - l0
        out = np.zeros(s.shape, np.float32)
        ok = (s > 0) & (qx > -20) & (qx < CX_1 - CX_0 + 20) & (qy > -20) & (qy < CY_1 - CY_0 + 20)
        for L in range(3):
            sel = ok & (l0 == L)
            if sel.any():
                a = ndimage.map_coordinates(self.Tf[L], [qy[sel], qx[sel]], order=1, prefilter=False)
                b = ndimage.map_coordinates(self.Tf[L + 1], [qy[sel], qx[sel]], order=1, prefilter=False)
                out[sel] = a * (1 - fr[sel]) + b * fr[sel]
        if rays is not None:
            ry = ndimage.map_coordinates(rays, [(qy[ok] + CY_0) / E8 - 0.5, (qx[ok] + CX_0) / E8 - 0.5],
                                         order=1, mode="nearest", prefilter=False)
            out[ok] *= 0.6 + 0.4 * ry                           # the outside shadows dapple the pattern
        return out * np.exp(-0.04 * s * lnorm) / lnorm

    # --- a frame ----------------------------------------------------------------------------------
    def frame(self, k: int, ink=None) -> np.ndarray:
        """Frame k of the background, (H, W, 3) uint8 sRGB (a fixed scrim keeps the lyrics calm)."""
        t = k / self.facts.fps
        st = self.state(t)
        warm, grace = st["warm"], st["grace"]
        C = palette(warm)
        step = st["step"]
        r = NIGHT_R + (DAWN_R - NIGHT_R) * step
        lx = NIGHT_LX + (DAWN_LX - NIGHT_LX) * step
        I = (1 - 0.45 * st["cloud"]) * (1 + 0.35 * grace) * (1 + 0.45 * warm)

        # beams in drifting haze, with a breath of incense on each sung word
        rays = self._rays(t)
        sh = self._shafts(r, lx, rays)
        dx = 1.6 * t
        i0 = int(dx) % (2 * w8)
        fr = dx - int(dx)
        ha = np.roll(self.haze_a, -i0, 1)[:, :w8 + 1]
        hb = np.roll(self.haze_b, int(3.1 * t) % (2 * w8), 1)[:, :w8]
        haze = np.clip(0.95 + (0.18 - 0.1 * warm) * (ha[:, :w8] * (1 - fr) + ha[:, 1:] * fr) + 0.08 * hb, 0.5, None)
        smoke = np.zeros((h8, w8, 1), np.float32)
        for s0, x0, drift in self.puff:
            a = t - s0
            if 0 <= a < 6.0:
                lvl = float(P.smooth(a / 0.5)) * math.exp(-a / 2.2)
                P.stamp(smoke, E8, x0 + drift * 60 * a + 25 * math.sin(a * 1.3), 1700 - 140 * a,
                        35 + 22 * a, 55 + 30 * a, np.ones(1, np.float32), 0.45 * lvl)
        haze = haze * (1 + 0.25 * st["swell"]) + smoke[..., 0] * (1 - 0.6 * warm)
        beams = sh * haze * I * self.scrim8
        # what lights the hall: its ambient, the lit haze in front of the wall, the pool's bounce
        pool = self._pool(r, lx, 1.0 - 0.45 * grace, rays) * I * (0.75 + 0.25 * warm)
        pool8 = np.zeros((h8, w8), np.float32)
        p8 = P.down(pool[..., None], 4)[..., 0]
        f8 = int(round(FY / E8))
        pool8[f8:f8 + p8.shape[0]] = p8[:h8 - f8]
        glow = ndimage.gaussian_filter(sh, 9) * 0.5 + ndimage.gaussian_filter(sh, 28) * 1.1
        bounce = np.roll(ndimage.gaussian_filter(pool8, 10), -16, 0)
        linger = (self.linger8 * warm)[..., None]
        amb = C["amb"] * (1 - linger) + P.lin("#26344c") * linger
        E = (amb * AMB + (glow * I * (1 - 0.7 * warm))[..., None] * (C["scat"] * GLOW_S + C["light"] * GLOW_L)
             + (bounce * BOUNCE)[..., None] * C["light"])
        E[f8:] = E[f8:] * 0.5 + C["floor"] * FLOOR_AMB
        x = self.alb * P.up(E.astype(np.float32))
        x[FY:] += self.alb[FY:] * (P.resize(pool, W, H - FY)[..., None] * (C["light"] * POOL))

        # the lattice: sky behind, the stone's cut faces catching the light on the source's side
        c = x[CY_0:CY_1, CX_0:CX_1]
        dxs, dys = CX0 - CF * lx / r - JCX, CY0 - CF / r - 400
        dn = math.hypot(dxs, dys)
        facing = (self.face[0] * dxs + self.face[1] * dys) / dn
        lit = np.clip(facing, 0, 1) ** 1.3
        c *= (1 - 0.5 * np.clip(-facing, 0, 1))[..., None]
        off = 5.0 * t
        j0 = int(off) % 400
        ff = off - int(off)
        cl = self.cloud_tex[:, j0:j0 + CX_1 - CX_0] * (1 - ff) + self.cloud_tex[:, j0 + 1:j0 + 1 + CX_1 - CX_0] * ff
        sky = C["sky"] * (SKY * (1 - 0.35 * st["cloud"]) * (1 + 0.25 * grace) * (1 + 1.1 * warm))
        see = self.see[..., None]
        c[:] = c * (1 - see) + (cl[..., None] * self._glow(warm) * sky) * see
        c += (lit * (0.05 + 0.10 * warm) * (1 + 0.6 * grace) * I)[..., None] * C["light"]

        # light in the air in front of everything: beams, their veil, dust glowing over the pool
        air = np.roll(ndimage.gaussian_filter(pool8, 5), -7, 0)
        # the window glows in the haze in front of it (felt, not a hot point)
        halo = np.zeros((h8, w8), np.float32)
        halo[:self.T8[1].shape[0]] = self.T8[1]
        halo = ndimage.gaussian_filter(halo, 9) * ((0.05 + 0.16 * warm) * I)
        add = (beams[..., None] * (C["light"] * (BEAM * (1 + 0.5 * warm)))
               + ndimage.gaussian_filter(beams, 12)[..., None] * (C["scat"] * (VEIL * (1 - 0.5 * warm)))
               + air[..., None] * (C["light"] * 0.14) + halo[..., None] * C["sky"])
        x += P.up(add.astype(np.float32))
        # the polished floor mirrors the lit wall and air a little
        m = FY - (H - FY)
        x[FY:] += P.soft_blur(x[m:FY][::-1], 10) * self.fall

        # near: the arcade's pillars, out of focus (only where they are)
        hall = float(beams.mean()) * 4 + 0.3
        rim = C["rim"] * ((0.012 + 0.02 * warm) * I * hall)
        for (ys, xs), nb, fb, rb in self.pillars:
            reg = x[ys, xs]
            reg *= 1 - nb
            reg += fb * (C["amb"] * 0.05) + rb * rim
        return P.finish(x, bloom=0.25, bloom_sigma=6, knee=0.42, soft=0.5, vig=self.vig)
