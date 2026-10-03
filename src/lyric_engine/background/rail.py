"""The rail look (H-038, docs/backgrounds/classics_rail.md): "Rail ki Seeti", for old classics. A
steam-era station platform at night, seen along the platform. The train stands on the right: its
tender, the cab with the fire glowing inside, the engine at the far end with its chimney steaming and
its headlight throwing a big soft cone into the fog ahead. The steam carries the light, lit warm by
the headlight and the lamps. A couple stands under a lamp to see someone off.

Song reaction (facts only): each sung word brightens the headlight's glow a little; each new line
sends a fresh puff rolling back under the canopy; a marked word blows the whistle (a thick white
plume, gold where the headlight catches it, the lamps' haze swelling); on the last line the train
pulls away into the fog, its coach sliding past and its tail lamp receding, and the steam thins over
the empty track ("gaadi chali gayi").

The station and the standing train are drawn once, with a depth map, so the steam, the far glow and
the moving train never show through nearer things; per frame only the steam, the glows, the wet
floor's reflection and (while it leaves) the train are worked out. Frames are pure functions of k
(worker processes). Built from the sample songs/_review/backgrounds/templates/classics/rail.py."""
from __future__ import annotations

import math

import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage

from . import paint as P

W, H = P.W, P.H
RF, RVX, RVY, EYE = 1100.0, 500.0, 800.0, 1.6     # focal length, vanishing point, eye height (m)
HZ = int(RVY)                                      # the horizon row
EDGE_X, TRACK_X, BED_Y = 3.0, 4.7, -0.9            # platform edge, track centre, track bed level
RAIL_TOP = BED_Y + 0.16
CAN_Y, CAN_X, CAN_END, BLD_X = 5.0, 2.7, 46.0, -7.0
COL_X, COLS = -2.0, (6.0, 12.5, 19.0, 25.5, 32.0, 38.5)
LAMP_X, LAMP_Y, LAMPS = 1.3, 3.9, (8.5, 15.0, 21.5, 28.0, 34.5)
NEAR_LAMP = (-0.4, 4.2, 2.8)                        # above us, out of frame: it lights the near floor
FOG = 42.0
SIDE_X = TRACK_X - 1.6                             # the train's near side
COACHES = ((-21.0, 5.6),)                         # one coach, just out of frame on the right at rest
TENDER, CAB, BOILER = (6.0, 11.8), (12.2, 14.8), (14.8, 23.6)
CHIMNEY_Z, DOME_Z, FRONT_Z = 22.8, 19.4, 24.0
HEAD_Y = RAIL_TOP + 4.0
WARM, AMBER, COOL = P.lin("#ffe6c4"), P.lin("#ffc27c"), P.lin("#7f92ba")
FIRE = P.lin("#ff8a3c")
SCRIM = 0.4
DEPART = 55.0                                      # m the train goes on the last line


def proj(X, Y, Z):
    z = max(Z, 0.05)
    return RVX + RF * X / z, RVY - RF * (Y - EYE) / z


def scale(Z):
    return RF / max(Z, 0.05)


def haze(Z):
    return math.exp(-max(Z, 0.0) / FOG)


def raster(shapes, blur=0.6, box=None):
    """Polygons and lines drawn at 2x and shrunk (clean edges), 0..1. box: (x0, y0, x1, y1) full px
    limits the work to that region (the result is still full size)."""
    x0, y0, x1, y1 = box or (0, 0, W, H)
    im = Image.new("L", (2 * (x1 - x0), 2 * (y1 - y0)), 0)
    d = ImageDraw.Draw(im)
    for sh in shapes:
        kind, pts = sh[0], [(2 * (x - x0), 2 * (y - y0)) for x, y in sh[1]]
        if kind == "poly":
            d.polygon(pts, fill=sh[2] if len(sh) > 2 else 255)
        else:
            d.line(pts, fill=sh[3] if len(sh) > 3 else 255, width=max(1, int(round(2 * sh[2]))), joint="curve")
    m = np.asarray(im.resize((x1 - x0, y1 - y0), Image.LANCZOS), np.float32) / 255
    if blur:
        m = ndimage.gaussian_filter(m, blur)
    if box is None:
        return m
    out = np.zeros((H, W), np.float32)
    out[y0:y1, x0:x1] = m
    return out


def closed_curve(pts, n=4):
    """A smooth closed outline through the control points (Catmull-Rom)."""
    m = len(pts)
    out = []
    for i in range(m):
        p0, p1, p2, p3 = (np.array(pts[(i + k) % m], np.float32) for k in (-1, 0, 1, 2))
        for t in np.linspace(0, 1, n, endpoint=False):
            out.append(tuple(0.5 * ((2 * p1) + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t * t
                                    + (-p0 + 3 * p1 - 3 * p2 + p3) * t ** 3)))
    return out


def woman_uv():
    """A woman in a saree in profile facing right (toward the train), metres (u forward, v up): the
    pallu drawn over her head and down her back, hands together at her chest, pleats at the hem."""
    return [closed_curve([(-0.12, 0.0), (-0.13, 0.45), (-0.12, 0.85), (-0.1, 1.0), (-0.15, 1.2), (-0.17, 1.36),
                          (-0.15, 1.5), (-0.07, 1.6), (0.02, 1.615), (0.08, 1.57), (0.1, 1.51), (0.118, 1.475),
                          (0.085, 1.43), (0.075, 1.38), (0.14, 1.3), (0.135, 1.2), (0.1, 1.08), (0.09, 1.0),
                          (0.11, 0.6), (0.16, 0.12), (0.19, 0.0)])]


def man_uv():
    """A man in profile facing right: kurta, a shawl over his shoulders, a Gandhi cap; his steel
    trunk on the floor behind him."""
    body = closed_curve([(-0.12, 0.0), (-0.085, 0.06), (-0.075, 0.46), (-0.145, 0.5), (-0.13, 0.72),
                         (-0.14, 0.9), (-0.175, 0.94), (-0.165, 1.12), (-0.16, 1.28), (-0.14, 1.4), (-0.07, 1.46),
                         (-0.085, 1.53), (-0.105, 1.6), (-0.12, 1.625), (-0.03, 1.655), (0.05, 1.652),
                         (0.115, 1.62), (0.095, 1.585), (0.1, 1.54), (0.12, 1.515), (0.098, 1.49), (0.085, 1.455),
                         (0.06, 1.43), (0.12, 1.38), (0.14, 1.22), (0.13, 1.0), (0.12, 0.76), (0.14, 0.5),
                         (0.085, 0.46), (0.1, 0.06), (0.17, 0.0)])
    return [body]


def billow_tex(rng, n=256) -> np.ndarray:
    """Cumulus texture: rounded lobes with creases between them (sum of |noise| octaves), 0..1."""
    t = np.zeros((n, n), np.float32)
    for sig, wgt in ((n / 9, 1.0), (n / 20, 0.5), (n / 45, 0.25)):
        g = ndimage.gaussian_filter(rng.standard_normal((n, n)), sig, mode="wrap")
        t += wgt * np.abs(g / g.std())
    return ((t - t.min()) / (t.max() - t.min())).astype(np.float32)


class Scene:
    look = "rail"
    in_order = False                 # any frame can be drawn on its own

    def __init__(self, facts):
        self.facts = facts
        f = facts
        self.last = f.last_line_s if f.last_line_s is not None else 0.85 * f.duration
        self.marks = [w_[0] for w_ in f.marks]
        self.lines = list(f.line_starts)
        self.starts = f.starts
        self.tex = billow_tex(np.random.default_rng(5))
        self.yy, self.xx = P.grids()
        self._stage()
        self.train0 = self._train(0.0)
        self.stage_full = self._with_train(self.train0)
        self.depth_full = self.train0[3]
        bx, by = f.block_centre
        self.vig = P.vignette(0.0, border=0.35) * (1 - SCRIM * P.scrim(bx, by, 600, 330))

    def describe(self) -> str:
        return (f"a steam-era platform at night; whistle on {len(self.marks)} marked word(s); "
                f"the train leaves at {self.last:.1f} s")

    # --- the station, drawn once --------------------------------------------------------------------
    def _stage(self):
        rng = np.random.default_rng(41)
        yy, xx = self.yy, self.xx
        fill = P.lin("#6f84ad") * 0.012
        air = P.gradient([(0.0, "#02040a"), (0.3, "#060b16"), (0.38, "#0b1220"), (RVY / H, "#1d2b48"),
                          (0.62, "#121b2e"), (1.0, "#0a0f1a")])
        P.blob(air, RVX + 60, RVY - 10, 600, 130, COOL, 0.07)        # cold fog low on the line
        self.lamp_px = []
        for lz in LAMPS:
            lx, ly = proj(LAMP_X, LAMP_Y - 0.1, lz)
            ls = scale(lz)
            self.lamp_px.append((lx, ly, ls, lz))
            P.blob(air, lx, ly + 0.2 * ls, 0.55 * ls, 0.5 * ls, AMBER, 0.16 * haze(lz) ** 0.5)
            P.blob(air, lx, ly + 0.9 * ls, 1.7 * ls, 1.5 * ls, AMBER, 0.012)
        self.air = air.astype(np.float32)
        dens = np.clip(1.0 + 0.4 * P.fbm(rng, ((24, 2.5, 1.0), (8, 2.0, 0.4))), 0.4, None)

        # the ground: stone flags on the platform, the track bed beyond its edge
        below = yy > RVY
        dy = np.maximum(yy - RVY, 0.35)
        zf = RF * EYE / dy
        xf = (xx - RVX) * zf / RF
        zt = RF * (EYE - BED_Y) / dy
        xt = (xx - RVX) * zt / RF
        plat = np.clip((EDGE_X - xf) / (zf / RF) + 0.5, 0, 1) * below
        self.plat = plat.astype(np.float32)
        flag = np.floor(xf / 1.2) * 7.31 + np.floor((zf + 0.3) / 1.1) * 3.17
        alb = 0.2 * (0.85 + 0.15 * np.tanh(P.fbm(rng, ((3, 1.0, 1.0), (12, 2.0, 0.8)))))
        alb = alb * (0.62 + 0.38 * np.sin(flag * 12.9898) ** 2)
        coping = np.clip((xf - (EDGE_X - 0.45)) / (zf / RF) + 0.5, 0, 1)
        alb = alb * (1 + 0.7 * coping)
        light_f = np.zeros((H, W), np.float32)
        for lz in LAMPS:
            cosv = LAMP_Y / np.sqrt(LAMP_Y ** 2 + (xf - LAMP_X) ** 2 + (zf - lz) ** 2)
            light_f += cosv ** 9 + 0.06 * cosv ** 4
        nx, ny, nz = NEAR_LAMP
        cosn = ny / np.sqrt(ny ** 2 + (xf - nx) ** 2 + (zf - nz) ** 2)
        light_f += 1.1 * cosn ** 16 + 0.03 * cosn ** 3
        floor = alb[..., None] * (fill * 4.0 + light_f[..., None] * AMBER * 0.22)
        # joints between the flags, the coping's seam
        dzj = np.abs((zf + 0.3) / 1.1 - np.round((zf + 0.3) / 1.1)) * 1.1 * RF * EYE / zf ** 2
        dxj = np.abs(xf / 1.2 - np.round(xf / 1.2)) * 1.2 * RF / zf
        dcj = np.abs(xf - (EDGE_X - 0.45)) * RF / zf
        jm = np.maximum(np.maximum(np.exp(-(dzj / 1.0) ** 2), np.exp(-(dxj / 1.0) ** 2) * 0.8), np.exp(-(dcj / 1.3) ** 2))
        floor *= (1 - 0.6 * jm)[..., None]
        self.wet = (plat * (0.5 + 1.1 * np.sin(flag * 78.233) ** 2) * (yy > RVY + 4)).astype(np.float32)
        floor += self.wet[..., None] * 0.006 * COOL * np.exp(-(yy - RVY) / 500.0)[..., None]   # wet stone: a cold sheen
        # lamps' long soft reflections in the wet stone, fading before they reach the lyrics
        for lx, ly, ls, lz in self.lamp_px:
            my = RVY + RF * (LAMP_Y + EYE) / lz
            rfl = np.exp(-((xx - lx) / (0.22 * ls + 5)) ** 2) * np.exp(-((yy - my) / (0.9 * ls + 25)) ** 2)
            floor += (rfl * 0.035 * P.smooth((1010 - yy) / 120))[..., None] * AMBER
        grav = 0.8 + 0.2 * np.tanh(P.fbm(rng, ((2, 0.8, 1.0), (6, 1.5, 0.6))))
        slp = ndimage.gaussian_filter((((zt % 0.66) < 0.26) * (np.abs(xt - TRACK_X) < 1.35)).astype(np.float32), 0.7)
        bed = (0.14 * grav * (1 - 0.45 * slp))[..., None] * (fill * 2.5)
        ground = floor * plat[..., None] + bed * (1 - plat)[..., None]
        Tg = np.exp(-np.where(plat > 0.5, zf, zt) * dens / FOG)
        x = np.where(below[..., None], ground * Tg[..., None] + self.air * (1 - Tg)[..., None], self.air)
        dep = np.where(below, np.where(plat > 0.5, zf, zt), 1e3).astype(np.float32)   # what each pixel shows: its depth
        del floor, bed, ground, alb, light_f, grav, slp, jm
        # the rails, catching the cold sky and the lamps
        rails = []
        for rx in (TRACK_X - 0.84, TRACK_X + 0.84):
            zs = np.geomspace(1.2, 160, 120)
            pl = [proj(rx - 0.04, RAIL_TOP, z) for z in zs]
            pr = [proj(rx + 0.04, RAIL_TOP, z) for z in zs]
            rails.append(("poly", pl + pr[::-1]))
        rm = raster(rails, 0.4) * (1 - plat)
        x += (rm * (0.04 + 0.05 * np.exp(-zt / 12.0)) * np.exp(-zt / FOG))[..., None] * (COOL * 0.6 + AMBER * 0.4)

        # the station building along the back, its waiting-room arches glowing faintly
        zb = RF * (-BLD_X) / np.maximum(RVX - xx, 1.0)
        yb = EYE + (RVY - yy) * zb / RF
        bm = ((xx < RVX) & (yb > 0) & (yb < CAN_Y) & (zb > 1.5) & (zb < CAN_END)).astype(np.float32)
        bm = ndimage.gaussian_filter(bm, 0.6)
        Tb = np.exp(-zb / FOG)
        lamp_wall = sum(1.0 / (1 + ((zb - lz) ** 2 + (BLD_X - LAMP_X) ** 2) / 4.0 ** 2) for lz in LAMPS)
        wall = P.lin("#141821") * (0.5 + 0.9 * lamp_wall)[..., None] * (0.9 + 0.1 * np.tanh(P.fbm(rng, ((6, 1.0, 1.0),))))[..., None]
        x = x * (1 - bm)[..., None] + bm[..., None] * (wall * Tb[..., None] + self.air * (1 - Tb)[..., None])
        dep = np.where(bm > 0.5, zb, dep)
        wins = []
        for wz in (9.5, 13.5, 17.5, 21.5, 25.5, 29.5):
            arch = [proj(BLD_X, 0.3, wz), proj(BLD_X, 2.3, wz)] + \
                   [proj(BLD_X, 2.3 + 0.6 * math.sin(a), wz + 0.6 - 0.6 * math.cos(a)) for a in np.linspace(0, np.pi, 12)] + \
                   [proj(BLD_X, 0.3, wz + 1.2)]
            wins.append(("poly", arch))
        wm = raster(wins, 1.4)
        x += (wm * 0.05 * Tb)[..., None] * AMBER
        x += (ndimage.gaussian_filter(wm, 14) * 0.05 * Tb)[..., None] * AMBER       # their glow on the wall

        # the canopy overhead: corrugated iron, trusses at the columns, lit from below by the lamps
        dya = np.maximum(RVY - yy, 0.35)
        zc = RF * (CAN_Y - EYE) / dya
        xc = (xx - RVX) * zc / RF
        can = (np.clip((CAN_X - xc) / (zc / RF) + 0.5, 0, 1) * np.clip((CAN_END - zc) / 0.5 + 0.5, 0, 1)
               * (yy < RVY)).astype(np.float32)
        self.can = can
        rib = 0.86 + 0.14 * np.cos(2 * np.pi * xc / 0.36) * np.clip(1 - (zc / RF) / 0.03, 0, 1)
        ceil_l = sum(0.06 / (1 + ((xc - LAMP_X) ** 2 + (zc - lz) ** 2) / 1.4 ** 2) for lz in LAMPS)
        ceil_l = ceil_l + 0.1 / (1 + ((xc - NEAR_LAMP[0]) ** 2 + (zc - NEAR_LAMP[2]) ** 2) / 1.6 ** 2)
        truss = sum(np.exp(-((zc - cz_) * RF * (CAN_Y - EYE) / zc ** 2 / (0.35 * scale(cz_) + 1.5)) ** 2) for cz_ in COLS + (2.0,))
        ceiling = P.lin("#0a0d14") * (1 - 0.5 * truss)[..., None] + ceil_l[..., None] * AMBER * 0.3
        rim_t = sum(np.exp(-(((zc - cz_ + 0.25) * RF * (CAN_Y - EYE) / zc ** 2) / 1.4) ** 2) for cz_ in COLS + (2.0,))
        ceiling += (rim_t * ceil_l * 1.6)[..., None] * AMBER                            # truss edges lit from below
        Tc = np.exp(-zc / FOG)
        x = x * (1 - can)[..., None] + can[..., None] * (ceiling * Tc[..., None] + self.air * (1 - Tc)[..., None]) * rib[..., None]
        dep = np.where(can > 0.5, zc, dep)
        del ceiling, Tc, rib, ceil_l, truss, rim_t, zc, xc, dya, zb, yb, Tb, wall

        # the dagger-board valance along the canopy's edge: uneven, lit from below, hazed by distance
        boards = []
        z0 = 2.5
        while z0 < CAN_END:
            wd = 0.17 + 0.05 * rng.random()
            z1 = z0 + wd
            ln = 0.62 + 0.14 * rng.random()
            boards.append(("poly", [proj(CAN_X, CAN_Y + 0.06, z0), proj(CAN_X, CAN_Y + 0.06, z1),
                                    proj(CAN_X, CAN_Y - ln + 0.2, z1), proj(CAN_X, CAN_Y - ln, (z0 + z1) / 2),
                                    proj(CAN_X, CAN_Y - ln + 0.2, z0)]))
            z0 = z1 + 0.03 + 0.03 * rng.random()
        vm = raster(boards, 0.5)
        zv = RF * CAN_X / np.maximum(xx - RVX, 1.0)
        yv = EYE + (RVY - yy) * zv / RF
        lit_v = sum(1.0 / (1 + ((zv - lz) ** 2 + (CAN_X - LAMP_X) ** 2 + (yv - LAMP_Y) ** 2) / 1.9 ** 2) for lz in LAMPS)
        lit_v = lit_v * (0.35 + 0.65 * P.smooth((CAN_Y - yv) / 0.6))
        Tv = np.exp(-zv / FOG)
        board = P.lin("#d8ccae") * (0.01 + 0.05 * lit_v)[..., None] * (AMBER * 0.45 + 0.55)
        x = x * (1 - vm)[..., None] + vm[..., None] * (board * Tv[..., None] + self.air * (1 - Tv)[..., None])
        dep = np.where(vm > 0.5, zv, dep)
        del vm, zv, yv, lit_v, Tv, board

        # the cast-iron columns and their arched brackets, a lamp-side rim, hazed by distance
        for z in sorted(COLS, reverse=True):
            s_ = []
            top, w, pw, cw = CAN_Y - 0.35, 0.12, 0.23, 0.2

            def q(X, Y):
                return proj(X, Y, z)
            s_.append(("poly", [q(COL_X - pw, 0), q(COL_X + pw, 0), q(COL_X + pw, 0.5), q(COL_X + w + 0.03, 0.62),
                                q(COL_X + w, top - 0.35), q(COL_X + cw, top - 0.17), q(COL_X + cw, top), q(COL_X - cw, top),
                                q(COL_X - cw, top - 0.17), q(COL_X - w, top - 0.35), q(COL_X - w - 0.03, 0.62),
                                q(COL_X - pw, 0.5)]))
            for sgn in (-1, 1):
                R = 0.7
                arc = [q(COL_X + sgn * (w + R + R * math.cos(a)), top - R + R * math.sin(a)) for a in np.linspace(np.pi, np.pi / 2, 18)]
                s_.append(("poly", arc + [q(COL_X + sgn * w, top + 0.02)]))
            s_.append(("poly", [q(-7.8, top), q(CAN_X, top), q(CAN_X, top + 0.16), q(-7.8, top + 0.16)]))   # the cross beam
            m = raster(s_, 0.4 + 3.0 / z)
            T = haze(z)
            near_lamp = max(math.exp(-((z - lz) / 3.5) ** 2) for lz in LAMPS + (NEAR_LAMP[2],))
            x = x * (1 - m)[..., None] + m[..., None] * (P.lin("#07090d") * T + self.air * (1 - T))
            dep = np.where(m > 0.5, z, dep)
            rim = np.clip(m - np.roll(m, -max(1, int(0.03 * scale(z))), axis=1), 0, 1)   # the side facing the lamps
            x += (ndimage.gaussian_filter(rim, 0.8) * (0.02 + 0.05 * near_lamp) * T)[..., None] * AMBER
            under = np.clip(m - np.roll(m, -2, axis=0), 0, 1)                            # undersides lit from below
            x += (under * 0.04 * near_lamp * T)[..., None] * AMBER

        # the lamps: an enamel shade on a rod, its lit inside seen from below, soft
        for lx, ly, ls, lz in self.lamp_px:
            shade = [("line", [proj(LAMP_X, CAN_Y, lz), proj(LAMP_X, LAMP_Y + 0.26, lz)], max(0.03 * ls, 1.0)),
                     ("poly", [proj(LAMP_X - 0.07, LAMP_Y + 0.26, lz), proj(LAMP_X + 0.07, LAMP_Y + 0.26, lz),
                               proj(LAMP_X + 0.25, LAMP_Y, lz), proj(LAMP_X - 0.25, LAMP_Y, lz)])]
            m = raster(shade, 0.5)
            T = haze(lz)
            x = x * (1 - m)[..., None] + m[..., None] * (P.lin("#07090d") * T + self.air * (1 - T))
            dep = np.where(m > 0.5, lz, dep)
            P.blob(x, lx, ly + 0.03 * ls, 0.2 * ls + 3, 0.05 * ls + 3, P.lin("#ffd49a"), 0.28 * T)

        # the couple seeing someone off, under the second lamp; a coolie farther down
        for fn, X, Z in ((man_uv, 0.8, 10.0), (woman_uv, 0.3, 9.7)):
            s = scale(Z)
            fx, fy = proj(X, 0.0, Z)
            foot = [proj(X + 0.4 * math.cos(a), 0.0, Z + 0.25 * math.sin(a)) for a in np.linspace(0, 2 * np.pi, 24)]
            x *= (1 - 0.55 * raster([("poly", foot)], max(1.0, 0.05 * s)))[..., None]
            m = raster([("poly", [(fx + u * s, fy - v * s) for u, v in ol]) for ol in fn()], 0.7)
            T = haze(Z)
            x = x * (1 - m)[..., None] + m[..., None] * (P.lin("#050608") * T + self.air * (1 - T))
            dep = np.where(m > 0.5, Z, dep)
            top = np.clip(m - np.roll(m, max(1, int(0.015 * s)), axis=0), 0, 1)
            x += (ndimage.gaussian_filter(top, 0.8) * 0.22 * T)[..., None] * AMBER          # the lamp above
            side = np.clip(m - np.roll(m, -max(1, int(0.012 * s)), axis=1), 0, 1)
            x += (ndimage.gaussian_filter(side, 0.8) * 0.05 * T)[..., None] * WARM           # the engine's glow
        tm = raster([("poly", [proj(0.95, 0.0, 10.4), proj(1.55, 0.0, 10.4), proj(1.55, 0.36, 10.4), proj(0.95, 0.36, 10.4)])], 0.6)
        x = x * (1 - tm)[..., None] + tm[..., None] * P.lin("#1a1612") * 0.5
        dep = np.where(tm > 0.5, 10.4, dep)
        self.depth = dep.astype(np.float32)
        self.wet *= dep >= np.where(plat > 0.5, zf, zt) - 1e-3       # only where the floor itself shows
        x += (np.clip(tm - np.roll(tm, 2, axis=0), 0, 1) * 0.08)[..., None] * AMBER
        self.stage = x.astype(np.float32)

        # near: a steel trunk with a bedroll on it at the lower left, out of focus, the lamp above
        # catching its top edges (drawn over the steam)
        lug = raster([("poly", [(-30, 1655), (300, 1640), (318, 1660), (322, 1960), (-30, 1960)]),
                      ("poly", [(18 + 120 * math.cos(a) * 1.0 + 0.0, 1588 + 62 * math.sin(a)) for a in np.linspace(0, 2 * np.pi, 40)]),
                      ("poly", [(18, 1526), (262, 1520), (262, 1652), (18, 1652)]),
                      ("poly", [(262 + 46 * math.cos(a), 1586 + 66 * math.sin(a)) for a in np.linspace(-np.pi / 2, np.pi / 2, 20)])], 0)
        lid = raster([("line", [(-30, 1700), (318, 1688)], 4.0)], 0) * lug
        rim = np.clip(lug - np.roll(lug, 8, axis=0), 0, 1)
        col = lug[..., None] * (P.lin("#0a0807") * (1 - 0.5 * lid)[..., None] + (rim * 0.12)[..., None] * AMBER)
        LY = slice(1400, H)
        LX = slice(0, 460)
        self.lug_box = (LY, LX)
        self.lug = ndimage.gaussian_filter(lug[LY, LX], 6)[..., None].astype(np.float32)
        self.lug_col = np.stack([ndimage.gaussian_filter(col[LY, LX, c], 6) for c in range(3)], -1).astype(np.float32)

    # --- the train --------------------------------------------------------------------------------
    def _train(self, d: float):
        """The train moved d m away: its mask (hidden by the platform and the canopy), colour and the
        cab's fire opening, worked out only in the region it covers."""
        box = (int(RVX) - 10, 0, W, 1700)                           # the train is always right of the vanishing point
        groups = []                                                  # (depth, shapes, windows)

        def q(X, h, Z):
            return proj(TRACK_X + X, RAIL_TOP + h, Z + d)
        for z0, z1 in COACHES:
            side = [("poly", [q(-1.6, 0.85, z0), q(-1.6, 0.85, z1), q(-1.6, 3.9, z1), q(-1.6, 3.9, z0)]),
                    ("poly", [q(-1.6, 3.9, z0), q(-1.6, 3.9, z1), q(-1.15, 4.3, z1), q(-1.15, 4.3, z0)]),
                    ("poly", [q(-1.6, 0.85, z0), q(1.6, 0.85, z0), q(1.6, 3.9, z0), q(1.15, 4.3, z0), q(-1.15, 4.3, z0),
                              q(-1.6, 3.9, z0)])]
            wins = [("poly", [q(-1.62, 2.1, w0), q(-1.62, 2.1, w0 + 0.9), q(-1.62, 3.0, w0 + 0.9), q(-1.62, 3.0, w0)])
                    for w0 in np.arange(z0 + 1.4, z1 - 1.3, 1.75)]
            groups.append(((z0 + z1) / 2 + d, side, wins))
        tz0, tz1 = TENDER
        groups.append(((tz0 + tz1) / 2 + d, [("poly", [q(-1.55, 1.0, tz0), q(1.55, 1.0, tz0), q(1.55, 3.75, tz0), q(-1.55, 3.75, tz0)]),
                                             ("poly", [q(-1.55, 1.0, tz0), q(-1.55, 1.0, tz1), q(-1.55, 3.75, tz1), q(-1.55, 3.75, tz0)])], []))
        cz0, cz1 = CAB
        cab = [("poly", [q(-1.6, 1.4, cz0), q(-1.6, 1.4, cz1), q(-1.6, 4.1, cz1), q(-1.6, 4.1, cz0)]),
               ("poly", [q(-1.6, 4.1, cz0), q(-1.1, 4.4, cz0), q(-1.1, 4.4, cz1), q(-1.6, 4.1, cz1)]),
               ("poly", [q(-1.6, 1.4, cz0), q(1.6, 1.4, cz0), q(1.6, 4.1, cz0), q(1.1, 4.4, cz0), q(-1.1, 4.4, cz0), q(-1.6, 4.1, cz0)])]
        fire = [("poly", [q(-1.62, 2.4, cz0 + 0.5), q(-1.62, 2.4, cz0 + 1.6), q(-1.62, 3.5, cz0 + 1.6), q(-1.62, 3.5, cz0 + 0.5)])]
        groups.append(((cz0 + cz1) / 2 + d, cab, []))
        bz0, bz1 = BOILER
        boil = []
        for zz in np.arange(bz0, bz1, 0.5):
            boil.append(("poly", [q(0.98 * math.cos(a), 2.98 + 0.98 * math.sin(a), zz) for a in np.linspace(0, 2 * np.pi, 36)]))
        boil.append(("poly", [q(-1.62, 2.1, bz0), q(-1.62, 2.1, bz1), q(-1.62, 2.24, bz1), q(-1.62, 2.24, bz0)]))
        boil.append(("poly", [q(-1.4, 0.3, bz0), q(-1.4, 0.3, bz1), q(-1.4, 2.1, bz1), q(-1.4, 2.1, bz0)]))
        for dz_, r_ in ((DOME_Z - 2.4, 0.3), (DOME_Z, 0.36)):
            boil.append(("poly", [q(r_ * math.cos(a), 3.85 + r_ * math.sin(a) * 1.1, dz_) for a in np.linspace(0, np.pi, 16)]
                         + [q(r_, 3.6, dz_), q(-r_, 3.6, dz_)]))
        boil.append(("poly", [q(-0.25, 3.8, CHIMNEY_Z), q(0.25, 3.8, CHIMNEY_Z), q(0.28, 4.45, CHIMNEY_Z), q(0.34, 4.55, CHIMNEY_Z),
                              q(-0.34, 4.55, CHIMNEY_Z), q(-0.28, 4.45, CHIMNEY_Z)]))
        for wz in (bz0 + 1.2, bz0 + 3.0, bz0 + 4.8, bz0 + 6.6):
            boil.append(("poly", [q(-1.5, 0.86 + 0.86 * math.sin(a), wz + 0.86 * math.cos(a)) for a in np.linspace(0, 2 * np.pi, 30)]))
        groups.append(((bz0 + bz1) / 2 + d, boil, []))
        col = np.zeros((H, W, 3), np.float32)
        mask = np.zeros((H, W), np.float32)
        dep = np.full((H, W), 1e3, np.float32)
        body = P.lin("#050608")
        for zg, shapes, wins in sorted(groups, key=lambda g: -g[0]):
            if zg > 400:
                continue
            m = raster(shapes, 0.6, box)
            T = haze(zg)
            c = body * T + self.air * (1 - T)
            col = col * (1 - m)[..., None] + m[..., None] * c
            mask = mask + m * (1 - mask)
            dep = np.where(m > 0.5, zg, dep)
            if wins:
                wm = raster(wins, 0.9, box) * m
                lit = (0.6 + 0.4 * np.sin(np.arange(len(wins)) * 2.3)).mean()
                col += (wm * 0.035 * lit * T)[..., None] * AMBER
        hide = (1 - self.plat) * (1 - self.can) * np.clip((self.depth - dep) / 0.5 + 0.5, 0, 1)   # nearer things in front
        mask *= hide
        col *= hide[..., None]
        fm = raster(fire, 0.8, box) * hide
        # backlit by the headlight's glow in the fog ahead: a warm rim along the engine's top
        top = np.clip(mask - np.roll(mask, 2, axis=0), 0, 1)
        hx, hy = proj(TRACK_X, HEAD_Y, FRONT_Z + 3 + d)
        near_head = np.exp(-(((self.xx - hx) / 320) ** 2 + ((self.yy - hy) / 220) ** 2))
        col += (ndimage.gaussian_filter(top, 0.7) * near_head * 0.45 * haze(FRONT_Z + d) ** 0.5)[..., None] * WARM
        return mask[..., None], col, fm, np.where(mask > 0.5, dep, self.depth)

    def _with_train(self, tr) -> np.ndarray:
        m, col = tr[0], tr[1]
        return self.stage * (1 - m) + col

    # --- the song ---------------------------------------------------------------------------------
    def depart(self, t: float) -> float:
        if t < self.last:
            return 0.0
        u = min((t - self.last) / max(self.facts.duration - self.last, 1.0), 1.0)
        return DEPART * u ** 1.8

    def _puffs(self, t: float, d_now: float) -> list:
        """Every steam puff alive at t as world-space blobs (X, Y, Z, r, density, kind)."""
        out = []
        last = self.last
        gone = min(d_now / DEPART, 1.0)
        # the chimney: a soft puff about every 0.3 s, varied, thinning once the train has gone
        for k in range(int((t - 6.0) / 0.3), int(t / 0.3) + 1):
            te = k * 0.3
            a = t - te
            if a < 0:
                continue
            rs = np.random.default_rng(1000 + k)
            dz = self.depart(te)
            r = (0.3 + 0.3 * a ** 0.8) * rs.uniform(0.8, 1.2)
            Y = RAIL_TOP + 4.6 + 1.4 * a ** 0.8
            X = TRACK_X - 0.12 * a + rs.normal(0, 0.12) * (0.3 + 0.3 * a)
            Z = CHIMNEY_Z + dz + 0.3 - 0.5 * a
            dd = 1.9 * (0.5 / r) ** 0.8 * math.exp(-a / 2.5) * rs.uniform(0.7, 1.15) * (1 - 0.7 * min(dz / DEPART, 1))
            out.append((X, Y, Z, r, dd, "chimney", rs.uniform(0, 1), rs.uniform(0, 1)))
        # each new line: a fresh, bigger puff that rolls back under the canopy toward us
        for i, ls in enumerate(self.lines):
            a = t - ls
            if not 0 <= a < 9.0:
                continue
            rs = np.random.default_rng(3000 + i)
            for j in range(3):
                aj = a - 0.25 * j
                if aj < 0:
                    continue
                r = (0.6 + 0.45 * aj) * rs.uniform(0.85, 1.15)
                out.append((TRACK_X - 0.5 - 0.45 * aj + rs.normal(0, 0.2), RAIL_TOP + 5.0 + 1.4 * (1 - math.exp(-aj / 1.0)) - 0.12 * aj,
                            CHIMNEY_Z - 2.2 * aj, r, 1.0 * math.exp(-aj / 4.0) * (0.6 / r) ** 0.5, "line",
                            rs.uniform(0, 1), rs.uniform(0, 1)))
        # the whistle on a marked word: a thick white plume that shoots up and rolls sideways
        for i, m in enumerate(self.marks):
            a = t - m
            if not 0 <= a < 4.0:
                continue
            rs = np.random.default_rng(5000 + i)
            dz = self.depart(m)
            for j in range(9):
                aj = a - 0.07 * j
                if aj < 0:
                    continue
                up = 2.2 * (1 - math.exp(-aj / 0.4)) + 0.6 * aj
                r = (0.6 + 1.1 * aj ** 0.75) * rs.uniform(0.8, 1.2)
                side = rs.normal(0, 0.35) + 0.5 * aj * rs.uniform(-1, 1)              # it rolls sideways
                out.append((TRACK_X + side, RAIL_TOP + 4.4 + up * rs.uniform(0.6, 1.0),
                            DOME_Z + dz - 0.3 * aj + rs.normal(0, 0.3), r, 2.6 * math.exp(-aj / 1.6), "whistle",
                            rs.uniform(0, 1), rs.uniform(0, 1)))
        # steam that has rolled back under the canopy and hangs there, drifting toward us
        rs = np.random.default_rng(77)
        for i in range(8):
            Z = 9.0 + ((i * 2.1 - 0.3 * t) % 16.0)
            out.append((rs.uniform(-2.8, 2.0), rs.uniform(3.4, 4.5), Z, rs.uniform(1.3, 2.1),
                        0.38 * rs.uniform(0.6, 1.0) * (1 - 0.35 * gone) * P.smooth((Z - 8.5) / 2.0), "hang",
                        rs.uniform(0, 1), rs.uniform(0, 1)))
        # once the train has gone, its steam still hangs low over the empty track, thinning
        if gone > 0:
            rs = np.random.default_rng(91)
            for i in range(9):
                Z = 14 + i * 3.0
                out.append((TRACK_X + rs.uniform(-1.0, 1.8), rs.uniform(1.0, 3.8), Z, rs.uniform(1.4, 2.6),
                            0.5 * gone * (1 - 0.5 * gone) * rs.uniform(0.5, 1.0), "trail", rs.uniform(0, 1), rs.uniform(0, 1)))
        return out

    def _steam(self, t: float, d: float, head_l: float, fire_l: float, lamp_l: float, glow, depth):
        """The steam layer at half size: colour (premultiplied) and coverage."""
        hh, hw = H // 2, W // 2
        C = np.zeros((hh, hw, 3), np.float32)
        A = np.zeros((hh, hw), np.float32)
        n = self.tex.shape[0]
        hx3, hy3, hz3 = TRACK_X, HEAD_Y, FRONT_Z + d                       # the headlight (points away)
        fx3, fy3, fz3 = SIDE_X, 2.2, CAB[0] + 1.0 + d                      # the fire in the cab
        hsx, hsy = proj(hx3, hy3, hz3 + 3)
        amb = P.lin("#6d7ca2") * 0.05
        puffs = sorted(self._puffs(t, d), key=lambda p: -p[2])
        can_h = P.down(self.can[..., None], 2)[..., 0]
        dep_h = depth[::2, ::2]
        for X, Y, Z, r, dens, kind, ox, oy in puffs:
            if Z < 0.8:
                continue
            px, py = proj(X, Y, Z)
            R = r * scale(Z) / 2
            cx, cy = px / 2, py / 2
            if R < 0.8 or cx + R < 0 or cx - R > hw or cy + R < 0 or cy - R > hh:
                continue
            x0, x1 = int(max(cx - R - 2, 0)), int(min(cx + R + 3, hw))
            y0, y1 = int(max(cy - R - 2, 0)), int(min(cy + R + 3, hh))
            yy, xx = np.mgrid[y0:y1, x0:x1].astype(np.float32)
            u, v = (xx - cx) / R, (yy - cy) / R
            prof = np.sqrt(np.clip(1 - u * u - v * v, 0, 1))
            tx = ndimage.map_coordinates(self.tex, [((v * 0.4 + oy) * n) % n, ((u * 0.4 + ox) * n) % n], order=1, mode="wrap")
            dn = np.clip(prof * (0.3 + 1.15 * tx) - 0.16, 0, None)
            # light: the headlight's scatter (strong in front of the engine), the lamps, the fire
            d2h = (X - hx3) ** 2 + (Y - hy3) ** 2 + (Z - hz3) ** 2
            Ih = head_l * 1.3 * (0.35 + 0.65 * min(max((Z - hz3 + 2.0) / 3.0, 0), 1)) / (1 + d2h / 2.6 ** 2) * haze(hz3) ** 0.3
            Il = sum(0.2 * lamp_l / (1 + ((X - LAMP_X) ** 2 + (Y - LAMP_Y) ** 2 + (Z - lz) ** 2) / 1.7 ** 2) for lz in LAMPS)
            If = fire_l * 0.35 / (1 + ((X - fx3) ** 2 + (Y - fy3) ** 2 + (Z - fz3) ** 2) / 1.6 ** 2)
            light = WARM * Ih + AMBER * Il + FIRE * If
            if kind == "whistle":
                light = light * 0.6 + P.lin("#fff3e2") * (0.22 + 0.3 * Ih)
                light = light + AMBER * 0.35 * Ih * np.clip(v + 0.3, 0, 1).mean()   # gold underside
            sx, sy = (hsx / 2 - cx), (hsy / 2 - cy)
            sn = math.hypot(sx, sy) + 1e-3
            lam = np.clip(u * sx / sn + v * sy / sn + prof * 0.4, 0, 1)
            back = 1.2 * min(Ih, 1.0) * (1.0 if Z < hz3 else 0.3)
            rim = (1 - prof) ** 2 * back
            shade = (0.25 + 0.75 * lam + 1.2 * rim) * (0.75 + 0.5 * tx)
            col = light * shade[..., None] + amb + P.lin("#9fb0d4") * 0.03 * np.clip(-v * 0.9 + prof * 0.35, 0, 1)[..., None]
            a = 1 - np.exp(-dn * dens * haze(Z) ** 0.5)
            if kind in ("chimney", "whistle") and Y > CAN_Y - 0.3:
                a = a * (1 - can_h[y0:y1, x0:x1])
            a = a * np.clip((dep_h[y0:y1, x0:x1] - Z) / (0.3 * r + 0.3) + 0.5, 0, 1)   # nearer things stay in front
            T = haze(Z)
            behind = self.air[2 * y0:2 * y1:2, 2 * x0:2 * x1:2] + glow[y0:y1, x0:x1]
            col = col * T + behind * (0.75 - 0.25 * T)       # white steam scatters the lit fog it sits in
            C[y0:y1, x0:x1] = C[y0:y1, x0:x1] * (1 - a)[..., None] + a[..., None] * col
            A[y0:y1, x0:x1] = A[y0:y1, x0:x1] * (1 - a) + a
        return C, A

    # --- a frame ----------------------------------------------------------------------------------
    def frame(self, k: int, ink=None) -> np.ndarray:
        """Frame k of the background, (H, W, 3) uint8 sRGB (a fixed scrim keeps the lyrics calm)."""
        t = k / self.facts.fps
        d = self.depart(t)
        voice = P.envelope(t, self.starts, 0.15, 0.7)
        whistle = P.envelope(t, self.marks, 0.15, 2.0)
        head_l = (1.0 + 0.18 * voice + 0.25 * whistle)
        lamp_l = 1.0 + 0.3 * whistle
        fire_l = 0.85 + 0.1 * math.sin(t * 7.3) + 0.05 * math.sin(t * 17.1 + 1.0)
        if d > 0:
            tr = self._train(d)
            x = self._with_train(tr)
        else:
            tr = self.train0
            x = self.stage_full.copy()
        # glows: the headlight's cone in the fog ahead, the fire, the lamps' haze swelling
        q = np.zeros((H // 4, W // 4, 3), np.float32)
        qn = np.zeros((H // 4, W // 4, 3), np.float32)              # glows near us: not occluded
        hz = FRONT_Z + d
        T = haze(hz)
        for dz, sz, lev in ((2.5, 1.4, 0.35), (5.0, 3.0, 0.14), (8.0, 6.0, 0.05)):
            gx, gy = proj(TRACK_X + 0.1 * dz, HEAD_Y - 0.1 * dz, hz + dz)
            P.stamp(q, 4, gx, gy, sz * scale(hz + dz) + 20, 0.8 * sz * scale(hz + dz) + 16, WARM, lev * head_l * T ** 0.6)
        P.stamp(q, 4, *proj(TRACK_X, HEAD_Y, hz + 30), 260, 120, WARM, 0.03 * head_l * T)
        fx, fy = proj(SIDE_X - 0.3, 2.4, CAB[0] + 1.0 + d)
        P.stamp(qn, 4, fx, fy, 1.6 * scale(CAB[0] + d), 1.3 * scale(CAB[0] + d), FIRE, 0.06 * fire_l * haze(CAB[0] + d))
        for lx, ly, ls, lz in self.lamp_px:
            P.stamp(qn, 4, lx, ly + 0.3 * ls, 0.9 * ls, 0.8 * ls, AMBER, 0.05 * (lamp_l - 1) * haze(lz) ** 0.5)
        zr = COACHES[0][0] + d
        if zr > 5.0:                                                 # the last coach's tail lamp, soft
            tx, ty = proj(SIDE_X + 0.35, 0.9, zr)
            P.stamp(qn, 4, tx, ty, 0.25 * scale(zr) + 6, 0.25 * scale(zr) + 6, P.lin("#ff5a3c"), 0.12 * haze(zr) ** 0.7)
        depth = tr[3] if d > 0 else self.depth_full
        x += P.up(q) * (np.clip(depth / hz, 0, 1) ** 2)[..., None] + P.up(qn)   # nearer things hide the far glow
        x += tr[2][..., None] * (FIRE * 0.5 * fire_l * haze(CAB[0] + d))
        # the steam
        C, A = self._steam(t, d, head_l, fire_l, lamp_l, P.up(q + qn, W // 2, H // 2), depth)
        x *= 1 - P.up(A)[..., None]
        x += P.up(C)
        # the wet stone mirrors the glows and the steam above it, long and soft (quarter size)
        small = P.down(x[:HZ], 4)
        D = 2 * RF * EYE / 30.0
        rows = np.arange(HZ // 4, H // 4, dtype=np.float32) * 4 + 2
        src = np.clip((2 * HZ + D - rows) / 4, 0, HZ // 4 - 1).astype(np.int32)
        refl = np.stack([ndimage.gaussian_filter(small[src, :, c], (9, 1.2)) for c in range(3)], -1)
        fade = (0.05 + 0.4 * np.exp(-(rows - HZ) / 150.0)) * P.smooth((1040 - rows) / 160)
        refl *= fade[:, None, None]
        x[HZ:] += P.up(refl, W, H - HZ) * self.wet[HZ:, :, None]
        reg = x[self.lug_box]
        reg *= 1 - self.lug
        reg += self.lug_col
        return P.finish(x, bloom=0.25, bloom_sigma=6, knee=0.42, soft=0.5, vig=self.vig)
