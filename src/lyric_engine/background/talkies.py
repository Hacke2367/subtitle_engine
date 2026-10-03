"""The talkies look (H-038 classics idea, docs/backgrounds/classics_talkies.md): "Purani Talkies",
for old classics. A seat in the stalls of an old single-screen hall at night: the projector's beam
comes down from above and behind us through slow smoke onto the screen, over rows of dark heads; the
film is black and white, too soft and far to read; rows of empty seats lie between us and them.

Song reaction (facts only): each sung word lifts the film's light a little; each new line is a cut
(the screen eases into a new soft shot); a marked word lets colour breathe into the film and the beam
(warm amber with faded teal shadows) while the hall stays silver; on the last line the show ends: the
beam goes out, the crimson curtain closes across the screen and warm house lights come up on the
walls, the audience still seated ("picture khatam"). The film starts dim, so a title card at the
top reads in the first seconds.

The hall is drawn once; per frame only the film, the beam's smoke, the light the screen throws on
the hall, the curtain and the house lights are worked out. Frames are pure functions of k."""
from __future__ import annotations

import math

import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage

from . import paint as P
from .chaand import octaves, roll, warp   # the shared periodic noise and its drift

W, H = P.W, P.H
SX0, SX1 = 175, 905                       # the screen's left and right edges
SKEW = 12                                 # its right edge is farther: shorter by 2 x SKEW px
STOP, SBOT = 330, 770
PX, PY = 440.0, -90.0                     # the projector's port, just above the frame
SILVER = P.lin("#dfe5ee")
AMBER = P.lin("#f2c98a")
TEAL = P.lin("#40605e")
WARM = P.lin("#ffc890")
VELVET = P.lin("#5a1018")
AIR = P.lin("#141a26")
SCRIM = 0.3
GAIN = 1.7                                # the whole hall: it read too dark on a phone (D-041)
N_SHOTS = 12
sm = P.smooth


def stop(x):
    return STOP + SKEW * (x - SX0) / (SX1 - SX0)


def sbot(x):
    return SBOT - SKEW * (x - SX0) / (SX1 - SX0)


def raster(shapes, box, blur=0.6):
    """Polygons drawn at 2x inside box (x0, y0, x1, y1) and shrunk: a full-size mask, 0..1."""
    x0, y0, x1, y1 = box
    im = Image.new("L", (2 * (x1 - x0), 2 * (y1 - y0)), 0)
    d = ImageDraw.Draw(im)
    for pts in shapes:
        d.polygon([(2 * (x - x0), 2 * (y - y0)) for x, y in pts], fill=255)
    m = np.asarray(im.resize((x1 - x0, y1 - y0), Image.LANCZOS), np.float32) / 255
    out = np.zeros((H, W), np.float32)
    out[y0:y1, x0:x1] = ndimage.gaussian_filter(m, blur) if blur else m
    return out


def ellipse(cx, cy, rx, ry, n=28, a0=0.0, a1=2 * math.pi):
    return [(cx + rx * math.cos(a), cy + ry * math.sin(a)) for a in np.linspace(a0, a1, n)]


def person(rs, cx, top, s):
    """One seated person seen from behind, s: the head's height in px, top: the head's top row.
    Returns (head shapes, body shapes): a head with hair, a bun, a cap, a pallu or a plait, and
    round shoulders (no hard corners, so their lit edges never zigzag)."""
    kind = rs.choice(["man", "man", "puff", "cap", "bun", "pallu", "plait", "child"], p=[.2, .12, .1, .1, .14, .14, .1, .1])
    if kind == "child":
        s *= 0.78
        top += 0.35 * s
    hw = s * rs.uniform(0.36, 0.42)
    cy = top + 0.5 * s
    tilt = rs.normal(0, 0.06)
    head = [ellipse(cx, cy - 0.04 * s, hw * 1.22, 0.56 * s) if kind == "puff" else ellipse(cx, cy, hw, 0.5 * s)]
    sw = s * rs.uniform(1.0, 1.3) * (0.8 if kind == "child" else 1.0)
    neck = top + 0.9 * s
    body = [[(cx - 0.2 * s, neck - 0.15 * s), (cx + 0.2 * s, neck - 0.15 * s), (cx + 0.2 * s, neck + 0.4 * s),
             (cx - 0.2 * s, neck + 0.4 * s)],
            ellipse(cx, neck + 0.85 * s, sw, 0.62 * s, 30, -math.pi, 0) + [(cx + sw, neck + 2.6 * s), (cx - sw, neck + 2.6 * s)]]
    if kind == "cap":
        head.append([(cx - hw * 1.02, top + 0.2 * s), (cx + hw * 1.02, top + 0.22 * s), (cx + hw * 0.7, top - 0.12 * s),
                     (cx - hw * 0.7, top - 0.1 * s)])
    elif kind == "bun":
        head.append(ellipse(cx + rs.uniform(-0.1, 0.1) * s, top + 0.62 * s, 0.24 * s, 0.2 * s))
    elif kind == "pallu":
        head.append(ellipse(cx, cy - 0.02 * s, hw * 1.18, 0.56 * s))
        body.append(ellipse(cx, neck + 0.55 * s, sw * 0.95, 0.75 * s, 30, -math.pi, 0) + [(cx + sw * 0.95, neck + 1.2 * s),
                                                                                      (cx - sw * 0.95, neck + 1.2 * s)])
    elif kind == "plait":
        body.append([(cx - 0.07 * s, cy + 0.3 * s), (cx + 0.07 * s, cy + 0.3 * s), (cx + 0.05 * s, neck + 1.1 * s),
                     (cx - 0.05 * s, neck + 1.1 * s)])
    piv = (cx, neck + 0.6 * s)

    def turn(shapes):
        return [[(piv[0] + (x - piv[0]) * math.cos(tilt) - (y - piv[1]) * math.sin(tilt),
                  piv[1] + (x - piv[0]) * math.sin(tilt) + (y - piv[1]) * math.cos(tilt)) for x, y in pts] for pts in shapes]
    return turn(head), turn(body)


def seat_row(rs, top, wd, ht, x_off):
    """A row of seat backs: rounded tops side by side with narrow gaps (armrests)."""
    shapes = []
    x = x_off - wd
    while x < W + wd:
        w_ = wd * rs.uniform(0.95, 1.05)
        r = 0.32 * w_
        pts = ellipse(x + r, top + r, r, r, 12, math.pi, 1.5 * math.pi) + \
            ellipse(x + w_ - r, top + r, r, r, 12, 1.5 * math.pi, 2 * math.pi) + \
            [(x + w_, top + ht), (x, top + ht)]
        shapes.append(pts)
        x += w_ + 0.08 * wd
    return shapes


def shot(rng, kind: str) -> np.ndarray:
    """One soft film shot, (54, 96) brightness 0..1: far, out of focus and too soft to read, but
    shaped like a scene of the era (a misty river with a boat, a jharokha window, hills at dawn, a
    lamp-lit room, an avenue of trees)."""
    hh, ww = 108, 192                                         # drawn at 2x, then shrunk
    yy, xx = np.mgrid[0:hh, 0:ww].astype(np.float32)
    u, v = xx / ww, yy / hh
    if kind == "river":
        hz = rng.uniform(0.45, 0.6)
        img = np.where(v < hz, 0.75 - 0.35 * v, 0.55 - 0.2 * (v - hz))
        bank = hz - 0.06 - 0.04 * np.sin(u * rng.uniform(8, 14) + rng.uniform(0, 6)) ** 2
        img = np.where((v > bank) & (v < hz), 0.18, img)
        mx = rng.uniform(0.2, 0.8)
        img += 0.35 * np.exp(-(((u - mx) / 0.05) ** 2 + ((v - 0.22) / 0.09) ** 2))
        img += 0.18 * np.exp(-(((u - mx) / 0.02) ** 2 + ((v - (2 * hz - 0.22)) / 0.15) ** 2)) * (v > hz)
        bx = rng.uniform(0.25, 0.75)
        boat = (np.abs(u - bx) < 0.09 - 3.0 * np.clip(v - hz - 0.12, 0, None)) & (v > hz + 0.08) & (v < hz + 0.14)
        img = np.where(boat | ((np.abs(u - bx - 0.02) < 0.008) & (v > hz - 0.02) & (v < hz + 0.1)), 0.1, img)
    elif kind == "window":
        img = np.full((hh, ww), 0.12, np.float32) + 0.05 * v
        wx, wy, wr = rng.uniform(0.3, 0.7), 0.3, 0.16
        arch = ((np.abs(u - wx) < wr) & (v > wy) & (v < 0.85)) | (((u - wx) / wr) ** 2 + ((v - wy) / 0.18) ** 2 < 1)
        img = np.where(arch, 0.9 - 0.3 * v, img)
        bars = arch & ((np.abs(u - wx) < 0.008) | (np.abs(v - 0.55) < 0.01))
        img = np.where(bars, 0.2, img)
        cur = np.abs(u - wx - wr * rng.choice([-0.7, 0.7])) < 0.07 + 0.02 * np.sin(v * 30)
        img = np.where(cur & arch, 0.35, img)
        img += 0.25 * np.exp(-(((u - wx) / 0.25) ** 2 + ((v - 0.95) / 0.06) ** 2))
    elif kind == "hills":
        img = 0.85 - 0.45 * v + 0.25 * np.exp(-(((u - rng.uniform(0.2, 0.8)) / 0.2) ** 2 + ((v - 0.35) / 0.12) ** 2))
        for i, lev in enumerate((0.62, 0.45, 0.3, 0.16)):
            ph, f_ = rng.uniform(0, 6), rng.uniform(3, 7)
            ridge = 0.42 + 0.13 * i - 0.06 * np.sin(u * f_ + ph) - 0.03 * np.sin(u * 2.3 * f_ + 2 * ph)
            img = np.where(v > ridge, lev, img)
    elif kind == "lamp":
        img = np.full((hh, ww), 0.08, np.float32)
        lx = rng.choice([0.25, 0.75])
        img += 0.75 * np.exp(-(((u - lx) / 0.12) ** 2 + ((v - 0.45) / 0.16) ** 2))
        door = (np.abs(u - (1 - lx)) < 0.09) & (v > 0.25) & (v < 0.9)
        img = np.where(door, 0.4, img)
        img = np.where((np.abs(u - lx) < 0.025) & (v > 0.5) & (v < 0.8), 0.15, img)
    else:                                                     # an avenue of trees to a bright end
        img = 0.25 + 0.6 * np.exp(-(((u - 0.5) / 0.12) ** 2 + ((v - 0.45) / 0.2) ** 2))
        d = np.abs(u - 0.5) / np.maximum(v - 0.3, 0.02)
        img = np.where((v > 0.48) & (d < 0.5), 0.45 - 0.2 * v, img)
        for k in range(1, 7):
            z = 0.12 * k
            for sx in (-1, 1):
                tx = 0.5 + sx * (0.05 + 0.08 / z)
                img = np.where((((u - tx) / (0.05 / z ** 0.6)) ** 2 + ((v - 0.35) / (0.18 / z ** 0.4)) ** 2 < 1), 0.12, img)
    img = np.asarray(Image.fromarray(np.clip(img, 0, 1).astype(np.float32), "F").resize((96, 54), Image.BILINEAR), np.float32)
    img = ndimage.gaussian_filter(img + 0.03 * rng.standard_normal(img.shape), 0.7)
    yy2, xx2 = np.mgrid[0:54, 0:96].astype(np.float32)
    img *= 0.75 + 0.25 * np.exp(-(((xx2 - 48) / 58) ** 2 + ((yy2 - 27) / 33) ** 2))
    return np.clip(img, 0.06, 1.0).astype(np.float32)


class Scene:
    look = "talkies"
    in_order = False                 # any frame can be drawn on its own

    def __init__(self, facts):
        self.facts = facts
        f = facts
        self.yy, self.xx = P.grids()
        rng = np.random.default_rng(1955)
        self.dur = f.duration
        L = f.last_line_s if (f.words and f.last_line_s is not None) else 0.85 * f.duration
        self.L = min(L, self.dur - 3.0) if self.dur > 7 else L
        self.starts = f.starts
        self.marks = [m[0] for m in f.marks]
        self.lines = list(f.line_starts) if f.words else list(np.arange(3.0, f.duration, 4.0))
        self._film(np.random.default_rng(f.seed + 3))
        self._hall(rng)
        self._beam(rng)
        bx, by = f.block_centre
        lb = f.lyric_box
        rx, ry = ((lb[2] - lb[0]) / 2 + 380, (lb[3] - lb[1]) / 2 + 340) if lb else (700, 500)
        calm = P.scrim(bx, by, rx, ry)
        self.calm = calm[..., 0]
        self.vig = P.vignette(0.2, 0.3) * (1 - SCRIM * calm)

    def describe(self) -> str:
        return (f"an old single-screen hall; {len(self.lines)} cut(s), colour on {len(self.marks)} "
                f"marked word(s); the show ends at {self.L:.1f} s")

    # --- the film: soft shots, too far and out of focus to read -----------------------------------
    def _film(self, rng):
        hh, ww = 54, 96
        shots = [shot(rng, kind) for kind in (["river", "window", "hills", "lamp", "avenue"] * 3)[:N_SHOTS]]
        rng.shuffle(shots)
        self.shots = shots
        # where each screen pixel samples the shot (the screen is a slightly skewed quad)
        ys, xs = np.mgrid[STOP - 2:SBOT + 2, SX0:SX1].astype(np.float32)
        t, b = stop(xs), sbot(xs)
        u = (xs - SX0) / (SX1 - SX0)
        v = (ys - t) / (b - t)
        edge = (sm(u * 140) * sm((1 - u) * 140) * sm(v * 120) * sm((1 - v) * 120)).astype(np.float32)
        self.scr_box = (slice(STOP - 2, SBOT + 2), slice(SX0, SX1))
        self.scr_mask = edge
        self.scr_uv = np.stack([np.clip(v, 0, 1) * (hh - 1), np.clip(u, 0, 1) * (ww - 1)])
        self.scr_shade = (0.82 + 0.18 * np.exp(-((u - 0.5) ** 2 + (v - 0.45) ** 2) / 0.18)).astype(np.float32)

    def film(self, t: float) -> np.ndarray:
        """The shot on screen at t, (54, 96) brightness: each cut eases in over half a second."""
        k = sum(1 for s in self.lines if s <= t)
        cur = self.shots[k % N_SHOTS]
        if k == 0:
            return cur
        a = float(sm((t - self.lines[k - 1]) / 0.5))
        return self.shots[(k - 1) % N_SHOTS] * (1 - a) + cur * a

    # --- the hall, drawn once ---------------------------------------------------------------------
    def _hall(self, rng):
        yy, xx = self.yy, self.xx
        # the room: dark walls, a little lighter near the screen where its light falls
        x = np.repeat(np.repeat(AIR[None, None, :] * 0.25, H, 0), W, 1).astype(np.float32)
        spill = np.exp(-(((xx - 540) / 560) ** 2 + ((yy - 560) / 420) ** 2))
        self.spill = spill.astype(np.float32)
        x += (spill * 0.05)[..., None] * AIR
        # the side curtains (open) and the valance: velvet folds, lit from the screen side
        cur = np.zeros((H, W), np.float32)
        for xa, xb in ((95, 178), (902, 985)):
            cur = np.maximum(cur, raster([[(xa, 285), (xb, 285), (xb + (6 if xa < 500 else -6), 830),
                                           (xa, 830)]], (0, 260, W, 860), 1.0))
        val = raster([[(95, 270), (985, 270), (985, 338), (95, 338)]], (0, 250, W, 360), 1.2)
        folds = 0.55 + 0.45 * np.sin(xx / 13.0 + 1.6 * np.sin(xx / 47.0)) ** 2
        self.cur_static = np.maximum(cur, val)
        self.fold = folds.astype(np.float32)
        x = x * (1 - self.cur_static[..., None]) + self.cur_static[..., None] * VELVET * 0.035 * folds[..., None]
        # the audience: rows of seated people seen from behind, far rows small and hazy
        heads = np.zeros((H, W), np.float32)
        head_c = np.zeros((H, W, 3), np.float32)
        rims = np.zeros((H, W), np.float32)
        rows = [(700, 24, 0.5), (738, 31, 0.36), (786, 40, 0.22), (846, 52, 0.1), (922, 66, 0.0)]
        for r, (top, s, hz) in enumerate(rows):
            rs = np.random.default_rng(300 + r)
            hs, bs = [], []
            xpos = rs.uniform(-s, s)
            while xpos < W + s:
                if rs.random() > 0.1:                               # an empty seat now and then
                    h_, b_ = person(rs, xpos, top + rs.normal(0, 0.06 * s), s * rs.uniform(0.9, 1.1))
                    hs += h_
                    bs += b_
                xpos += s * rs.uniform(1.45, 2.3)
            box = (0, top - s, W, min(H, int(top + 4 * s)))
            hm = raster(hs, box, 0.6 + 0.02 * s)
            m = np.maximum(hm, raster(bs, box, 0.6 + 0.02 * s))
            col = AIR * (0.10 + 1.0 * hz)                          # far rows sit in the screen's haze
            x = x * (1 - m[..., None]) + m[..., None] * col
            head_c = head_c * (1 - m[..., None]) + m[..., None] * col
            heads = np.maximum(heads, m)
            k = max(1, int(0.07 * s))
            rim = np.clip(hm - np.roll(hm, k, axis=0), 0, 1) * (1 - hz)          # the tops of heads only
            rims = rims * (1 - m) + ndimage.gaussian_filter(rim, 0.7)
        self.heads, self.head_c, self.rims = heads, head_c, rims.astype(np.float32)
        # rows of empty seats between us and them, and the near row out of focus
        seats = np.zeros((H, W), np.float32)
        seat_rim = np.zeros((H, W), np.float32)
        for i, (top, wd, ht, blur) in enumerate(((1000, 96, 60, 0.8), (1060, 110, 80, 1.0),
                                                  (1145, 130, 110, 1.4), (1265, 158, 150, 2.0),
                                                  (1430, 200, 220, 3.5), (1660, 270, 400, 7.0))):
            rs = np.random.default_rng(500 + i)
            m = raster(seat_row(rs, top, wd, ht, rs.uniform(0, wd)), (0, top - 10, W, min(H, top + ht + 20)), blur)
            x = x * (1 - m[..., None]) + m[..., None] * VELVET * (0.006 + 0.004 * i)
            seats = np.maximum(seats, m)
            rim = np.clip(m - np.roll(m, max(1, int(wd / 40)), axis=0), 0, 1)
            seat_rim = seat_rim * (1 - m) + ndimage.gaussian_filter(rim, 0.6 + blur * 0.4)
        # two people close to us at the corners, big and out of focus
        near = []
        for cx, top in ((40, 1480), (1050, 1520)):
            near += sum(person(np.random.default_rng(int(cx)), cx, top, 250), [])
        nm = ndimage.gaussian_filter(raster(near, (0, 1300, W, H), 0), 14)
        x = x * (1 - nm[..., None]) + nm[..., None] * AIR * 0.05
        self.near = nm
        self.seat_rim = seat_rim.astype(np.float32) * (1 - nm)
        self.hall = x.astype(np.float32)
        # the closing curtain: two crimson panels with uneven pleats, lit from below at the end
        xx1 = np.arange(W, dtype=np.float32)
        pleat = np.zeros(W, np.float32)
        p = 0.0
        for xi in range(W):
            p += 2 * math.pi / (22 + 10 * math.sin(xi / 61.0) + 6 * math.sin(xi / 23.0 + 1.0))
            pleat[xi] = p
        self.pleat = (0.45 + 0.55 * np.sin(pleat) ** 2).astype(np.float32)
        self.xx1 = xx1
        # the house lights: deco uplights on the side walls, throwing soft fans up the wall
        hl = np.zeros((H, W, 3), np.float32)
        for cx in (45, 1035):
            for k_, (sy, lev) in enumerate(((160, 0.10), (380, 0.05))):
                fan = np.exp(-((xx - cx) / (40 + 0.35 * np.clip(620 - yy, 0, None))) ** 2) * np.exp(-((yy - 520) / sy) ** 2)
                hl += (fan * lev)[..., None] * WARM
            P.blob(hl, cx, 650, 36, 22, WARM, 0.1)
        P.blob(hl, 540, 830, 520, 60, WARM, 0.05)                    # footlights along the stage
        hl += (np.exp(-((yy - 600) / 700) ** 2) * 0.012)[..., None] * WARM
        self.house = hl

    # --- the beam ---------------------------------------------------------------------------------
    def _beam(self, rng):
        yy, xx = self.yy, self.xx
        ang = np.arctan2(xx - PX, yy - PY)
        a0 = math.atan2(SX0 + 10 - PX, 290 - PY)
        a1 = math.atan2(SX1 - 10 - PX, 290 - PY)
        inside = sm((ang - a1) / -0.06 + 0.3) * sm((ang - a0) / 0.06 + 0.3)
        d = np.hypot(xx - PX, yy - PY)
        fall = (1.2 / (1 + d / 260)) * (1 - sm((yy - 215) / 75))
        rays = ndimage.gaussian_filter1d(rng.standard_normal(720).astype(np.float32), 1.4, mode="wrap")
        rays = (rays - rays.mean()) / rays.std()
        ai = ((ang - a0) / (a1 - a0) * 360 + 180).astype(np.int32) % 720
        self.beam = (inside * fall * (0.88 + 0.12 * np.tanh(rays[ai]))).astype(np.float32)
        self.beam_box = (slice(0, 300), slice(0, W))
        self.beam = self.beam[:300]
        g = np.random.default_rng(88)
        smoke = octaves(g, 152, 1080, [(15, 30, 1.0, 2), (6, 12, 0.6, 1), (2.5, 4.5, 0.3, 1)])
        self.smoke = warp(smoke, g, 7, 14)                     # half size, drifting (chaand.roll)

    # --- the song ---------------------------------------------------------------------------------
    def colour(self, t: float) -> float:
        return P.envelope(t, self.marks, 0.6, 3.2)

    def ending(self, t: float) -> float:
        return float(sm((t - self.L - 0.3) / 3.2))

    def frame(self, k: int, ink=None) -> np.ndarray:
        t = k / self.facts.fps
        end = self.ending(t)
        col = self.colour(t)
        start = float(sm((t - 2.4) / 1.4))                            # the film comes up after the title
        voice = P.envelope(t, self.starts, 0.15, 0.8) if self.facts.words else 0.0
        bright = (0.5 + 0.5 * start) * (1 + 0.07 * voice + 0.12 * col) * (1 - 0.8 * end)
        # the film: black and white, colour breathing in on marked words
        shot = self.film(t)
        lum = ndimage.map_coordinates(shot, self.scr_uv, order=1) * self.scr_shade
        grey = SILVER * lum[..., None]
        warm = AMBER * lum[..., None] ** 1.3 + TEAL * 0.9 * (1 - lum[..., None]) ** 2 * lum[..., None]
        film = (grey * (1 - col) + warm * col) * 0.24 * bright
        x = self.hall.copy()
        m = self.scr_mask[..., None]
        x[self.scr_box] = x[self.scr_box] * (1 - m) + film * m
        hm = self.heads[self.scr_box][..., None]                     # the audience sits in front of it
        x[self.scr_box] = x[self.scr_box] * (1 - hm) + self.head_c[self.scr_box]
        mean = film.reshape(-1, 3).mean(0) / max(0.24 * bright, 1e-3)    # the screen's light colour
        tint = mean / max(float(mean.max()), 1e-3)
        lightl = 0.30 * bright
        # the screen lights the hall: walls, curtains, the heads' and seats' edges
        x += (self.spill * (1 - 0.85 * self.heads) * 0.05 * lightl)[..., None] * tint
        x += (self.cur_static * self.fold * self.spill * 0.10 * lightl)[..., None] * tint * VELVET * 3
        x += (self.rims * (0.3 + 0.4 * col) * lightl * (1 - 0.85 * self.calm))[..., None] * tint
        x += (self.seat_rim * 0.022 * lightl * (1 - 0.85 * self.calm))[..., None] * tint
        # the beam through slow smoke
        sk = P.resize(roll(self.smoke, 1.5 * t), W, 300)
        sk2 = P.resize(roll(self.smoke[::-1], 0.85 * t + 200.0), W, 300)
        smoke = np.clip(0.45 + 0.5 * sk + 0.25 * sk2, 0.05, 1.6)
        held = P.envelope(t, self.starts, 0.4, 2.2) if self.facts.words else 0.0
        b = self.beam * smoke * (0.06 + 0.02 * held) * bright * (1 - end)
        x[:300] += b[..., None] * (SILVER * (1 - col) + AMBER * col)
        # the show ends: the curtain closes across the screen, warm house lights come up
        if end > 0:
            x = self._curtain(x, end)
            hl = self.house * end
            x += hl
            x += (self.rims * 0.25 * end)[..., None] * WARM * (1 - 0.6 * self.calm[..., None])
        return P.finish(x * GAIN, bloom=0.3, bloom_sigma=7, knee=0.45, soft=0.5, vig=self.vig)

    def _curtain(self, x, end):
        close = float(sm(end / 0.85))
        mid = 540.0
        left_edge = 178 + (mid + 6 - 178) * close
        right_edge = 902 - (902 - mid + 6) * close
        xs = self.xx1
        cover = np.clip((left_edge - xs) / 3 + 0.5, 0, 1) * (xs > 150) + np.clip((xs - right_edge) / 3 + 0.5, 0, 1) * (xs < 930)
        cover = np.clip(cover, 0, 1)
        rows = slice(285, 830)
        yy = self.yy[rows]
        foot = np.exp(-(830 - yy) / 260)                              # footlights from below
        lit = (0.02 + 0.10 * end * foot) * (1 + 0.2 * np.exp(-(830 - yy) / 40))
        pleat = self.pleat * (1 - 0.15 * (xs > 540))
        c = (VELVET[None, None, :] * (lit * pleat[None, :])[..., None]
             + (0.004 * foot * pleat[None, :])[..., None] * WARM)
        a = (cover[None, :] * np.ones_like(yy))[..., None]
        reg = x[rows]
        x[rows] = reg * (1 - a) + c * a
        return x
