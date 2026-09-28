"""The sunlit room's art, drawn once per render (spec 17 §4.2): the wall, the jaali's light patch,
the money plant and the curtain (as shadows in the patch), and the props below the lyric area.
Full-size layers are (1920, 1080[, 3]); light layers are half size (960, 540). Everything is
float32 in [0, 1]; the wall and the jaali never change, only the seeded picks do (spec 4.3)."""
from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np
from PIL import Image, ImageDraw

from . import paint

W, H = 1080, 1920
HW, HH = W // 2, H // 2
WALL_SEED = 1729          # the room's own wall: the same plaster in every video
WALL_RGB = (0.78, 0.585, 0.47)   # faded peach limewash
PAD = 96                  # half-size margin around the patch canvas, so the patch can drift
# The window's light on the wall, in half-size frame units: top-left corner of the window's
# box, its size, and the lean of the beam (x moves right by SHEAR per unit down)
WIN_X, WIN_Y, WIN_W, WIN_H, SHEAR = -8, 12, 330, 790, 0.22
ARCH = 0.2                # the arched top, as a share of the window's height
LATTICE = 40              # jaali cell (half-size px) and its bar width, in cells
BAR = 0.13
CRISP_TO, SOFT_FROM = 150, 330   # crisp jaali above this y, fully soft below that (half size)
TABLE_Y = 1702            # the table's top edge; every prop stands below y 1540
LAMP = (170, 1622)        # the lamp shade's centre (full size)


# --- Wall -----------------------------------------------------------------------------------
def wall() -> np.ndarray:
    """The warm plaster wall: texture × the shared grain × a soft vignette, (H, W, 3)."""
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    vignette = 1.0 - 0.42 * np.clip(((xx - W * 0.5) / (W * 0.78)) ** 2
                                    + ((yy - H * 0.42) / (H * 0.72)) ** 2, 0.0, 1.0)
    shade = paint.plaster(H, W, WALL_SEED) * paint.grain(H, W) * vignette
    return shade[..., None] * np.asarray(WALL_RGB, np.float32)


# --- The jaali's light patch -------------------------------------------------------------------
def window_uv(x: np.ndarray, y: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Half-size frame coordinates → the window's own (u, v), 0..1 across and down."""
    v = (y - WIN_Y) / WIN_H
    u = (x - WIN_X - SHEAR * (y - WIN_Y)) / WIN_W
    return u, v


def _inside(u: np.ndarray, v: np.ndarray) -> np.ndarray:
    """1 inside the arched window, else 0."""
    body = (u >= 0) & (u <= 1) & (v >= ARCH) & (v <= 1)
    arch = ((u - 0.5) / 0.5) ** 2 + ((v - ARCH) / ARCH) ** 2 <= 1.0
    return (body | (arch & (v < ARCH))).astype(np.float32)


def jaali_patch() -> np.ndarray:
    """The sun patch on a canvas PAD larger than the half-size frame on every side: crisp jaali
    near the top, a calm soft glow behind the lyric area (spec 4.2), brighter at the top."""
    ch, cw = HH + 2 * PAD, HW + 2 * PAD
    yy, xx = np.mgrid[0:ch * 2, 0:cw * 2].astype(np.float32) / 2.0 - PAD   # 2x, for clean bars
    u, v = window_uv(xx, yy)
    x, y = u * WIN_W / LATTICE, v * WIN_H / LATTICE   # chakri jaali: interlocking circles
    fx, fy = x - np.floor(x), y - np.floor(y)
    ring = np.full(fx.shape, np.inf, np.float32)
    for cx in (0.0, 1.0):
        for cy in (0.0, 1.0):
            ring = np.minimum(ring, np.abs(np.hypot(fx - cx, fy - cy) - 0.7071))
    holes = (ring > BAR / 2).astype(np.float32)
    frame = _inside((u - 0.03) / 0.94, (v - 0.02) / 0.97)   # the window's own frame, dark
    crisp = paint.blur(paint.down2(holes * frame), 1.0)
    soft = paint.blur(crisp, 14.0) * 1.15
    ys = np.arange(ch, dtype=np.float32)[:, None] - PAD
    mix = paint.smooth((ys - CRISP_TO) / (SOFT_FROM - CRISP_TO))
    patch = crisp * (1 - mix) + soft * mix
    patch = paint.blur(patch, 2.0) * (1.25 - 0.4 * np.clip(ys / HH, 0, 1))
    rng = np.random.default_rng(WALL_SEED + 1)
    return np.clip(patch * (1.0 + 0.07 * paint.noise(ch, cw, rng, ((8, 3.0, 1.0),))), 0, None)


# --- Money plant --------------------------------------------------------------------------------
@dataclass(frozen=True)
class Leaf:
    x: float              # its node on the vine, canvas units (half size), at rest
    y: float
    size: float           # leaf length
    angle: float          # radians, 0 = tip straight down
    phase: float
    period: float
    reach: float          # 0 at the vine's anchor, 1 at its end: how far it swings


# A pothos (money plant) leaf: heart-shaped with a long pointed tip, length 1, tip down, the
# stalk joining at (0, 0.1); the tip curls a little to one side
_RIGHT = ((0.08, 0.03), (0.22, 0.0), (0.37, 0.03), (0.47, 0.14), (0.51, 0.30), (0.48, 0.47),
          (0.39, 0.64), (0.26, 0.80), (0.12, 0.93))
_LEAF = [(x + 0.07 * y * y, y) for x, y in
         ((0.0, 0.06), *_RIGHT, (0.03, 1.0), *((-x * 0.92, y) for x, y in reversed(_RIGHT)))]


def leaves(side: str, rng: np.random.Generator) -> list[Leaf]:
    """A money-plant vine hanging inside one side of the window, as leaves in canvas units: it
    trails down in a loose S, leaves turned every way, smaller toward its growing tip."""
    u0 = 0.17 if side == "left" else 0.83
    top_y = WIN_Y + WIN_H * ARCH * 0.45
    out = []
    for i in range(9):
        r = i / 8
        y = top_y + r * 400 + rng.uniform(-10, 10)
        bend = 26 * math.sin(r * 4.2 + 0.5) * (1 if side == "left" else -1)
        x = WIN_X + u0 * WIN_W + SHEAR * (y - WIN_Y) + bend
        turn = (1 if i % 2 else -1) * rng.uniform(0.5, 1.4) + rng.uniform(-0.25, 0.25)
        out.append(Leaf(x + PAD, y + PAD, rng.uniform(44, 62) * (1 - 0.35 * r), turn,
                        rng.uniform(0, 2 * math.pi), rng.uniform(5.0, 8.0), r))
    return out


def _swing(l: Leaf, t: float, sway: float) -> tuple[float, float, float]:
    """(dx, dy, dangle) of a node: the vine swings as one, each leaf flutters a little."""
    whole = math.sin(2 * math.pi * t / 7.0)
    own = math.sin(2 * math.pi * t / l.period + l.phase)
    return (sway * 16 * l.reach ** 1.5 * whole, sway * 2 * l.reach * abs(whole),
            sway * (0.08 * whole + 0.12 * own))


def leaf_shadow(leaf_list: list[Leaf], t: float, sway: float) -> tuple[np.ndarray, tuple]:
    """The vine's shadow at time t (0..1, 1 = full shadow) on its canvas box: (mask, (x0, y0))."""
    x0 = int(min(l.x for l in leaf_list)) - 90
    y0 = int(min(l.y for l in leaf_list)) - 50
    w = int(max(l.x for l in leaf_list)) + 90 - x0
    h = int(max(l.y for l in leaf_list)) + 90 - y0
    im = Image.new("L", (w * 2, h * 2), 0)
    draw = ImageDraw.Draw(im)
    nodes = []
    for l in leaf_list:
        dx, dy, da = _swing(l, t, sway)
        nx, ny = (l.x - x0 + dx) * 2, (l.y - y0 + dy) * 2
        nodes.append((nx, ny))
        ang, k = l.angle + da, l.size * 2
        c, s = math.cos(ang), math.sin(ang)
        bx, by = nx - s * 0.25 * k, ny + c * 0.25 * k   # the stalk, then the leaf
        draw.line([(nx, ny), (bx, by)], fill=230, width=3)
        draw.polygon([(bx + k * (px * c - (py - 0.1) * s), by + k * (px * s + (py - 0.1) * c))
                      for px, py in _LEAF], fill=235)
    top = (nodes[0][0], nodes[0][1] - 80)
    draw.line([top, *nodes], fill=230, width=4, joint="curve")
    mask = paint.down2(np.asarray(im, np.float32) / 255.0)
    return paint.soft(mask, 1), (x0, y0)


# --- Curtain ------------------------------------------------------------------------------------
CURTAIN_U = 0.45   # the widest the curtain's shadow reaches across the window, gust included


def apply_curtain(canvas: np.ndarray, side: str, print_: str, t: float, lift: float) -> None:
    """Dim the patch canvas (in place) where the sheer curtain hangs, on the side opposite the
    plant. It breathes a little; `lift` 0..1 (a gust) billows its lower part out (spec 4.2).
    Worked out across the window (u, v) and laid into the canvas row by row along the lean."""
    uw = int(CURTAIN_U * WIN_W)
    v = (np.arange(WIN_H, dtype=np.float32) / WIN_H)[:, None]
    u = (np.arange(uw, dtype=np.float32) / WIN_W)[None, :]
    edge = 0.2 + 0.02 * math.sin(2 * math.pi * t / 9.0) + lift * 0.22 * v ** 1.5
    cover = paint.smooth((edge - u) / 0.04)
    folds = 0.5 + 0.5 * np.sin(u * 48 + lift * 3 * v + 0.6 * np.sin(v * 7 + t * 0.4))
    cloth = 0.42 + 0.14 * folds
    if print_ == "block-print":
        cloth = cloth - 0.12 * ((np.sin(u * WIN_W / 7.0) * np.sin(v * WIN_H / 7.0)) > 0.75)
    elif print_ == "lace":
        cloth = cloth + 0.2 * ((np.sin(u * WIN_W / 3.2) * np.sin(v * WIN_H / 3.2)) > 0.55)
    trans = 1.0 - cover * (1.0 - cloth)
    if side == "right":   # hanging at the window's right edge: mirror across
        trans = trans[:, ::-1]
    top = PAD + WIN_Y
    for row in range(WIN_H):
        x = int(round(PAD + WIN_X + SHEAR * row + (WIN_W - uw if side == "right" else 0)))
        lo, hi = max(x, 0), min(x + uw, canvas.shape[1])
        if hi > lo:
            canvas[top + row, lo:hi] *= trans[row, lo - x:hi - x]


# --- Props (below the lyric area) ---------------------------------------------------------------
def _sprite(box: tuple[int, int, int, int], paint_fn) -> tuple[np.ndarray, np.ndarray]:
    """Draw with paint_fn(draw, s) on a 2x RGBA canvas for box; return (rgb, alpha) at 1x."""
    x0, y0, x1, y1 = box
    im = Image.new("RGBA", ((x1 - x0) * 2, (y1 - y0) * 2), (0, 0, 0, 0))
    draw = ImageDraw.Draw(im)
    paint_fn(draw, lambda *v: [2 * (c - (x0 if i % 2 == 0 else y0)) for i, c in enumerate(v)])
    small = np.asarray(im.resize((x1 - x0, y1 - y0), Image.LANCZOS), np.float32) / 255.0
    return small[..., :3], small[..., 3:]


def _place(albedo: np.ndarray, cover: np.ndarray, box: tuple, paint_fn, form=None) -> None:
    """Draw a prop into the albedo with soft form shading (lighter top, darker rims) and add its
    coverage to `cover` (for the contact shadow on the wall)."""
    rgb, a = _sprite(box, paint_fn)
    x0, y0, x1, y1 = box
    yy = np.linspace(1.08, 0.78, y1 - y0, dtype=np.float32)[:, None, None]
    inner = paint.blur(a[..., 0], 3.0)[..., None]
    shade = yy * (0.72 + 0.28 * paint.smooth((inner - 0.35) / 0.5))
    if form is not None:
        shade = shade * form(y1 - y0, x1 - x0)[..., None]
    region = albedo[y0:y1, x0:x1]
    region[:] = region * (1 - a) + rgb * shade * a
    cover[y0:y1, x0:x1] = np.maximum(cover[y0:y1, x0:x1], a[..., 0])


def _c(rgb: tuple[float, float, float]) -> tuple[int, int, int]:
    return tuple(int(round(255 * c)) for c in rgb)


def props(albedo: np.ndarray, picks) -> np.ndarray:
    """Draw the table, lamp, prop and chair with the dupatta into the albedo (in place); return
    the lamp shade's mask (full size, 0..1) for its glow."""
    cover = np.zeros((H, W), np.float32)
    def table(d, s):
        d.rectangle(s(0, TABLE_Y, W, H), fill=_c((0.25, 0.155, 0.10)))
        d.rectangle(s(0, TABLE_Y - 8, W, TABLE_Y + 4), fill=_c((0.44, 0.29, 0.18)))
        for i, y in enumerate(range(TABLE_Y + 40, H, 46)):
            d.line(s(0, y, W, y + (6 if i % 2 else -4)), fill=_c((0.21, 0.13, 0.085)), width=4)
    _place(albedo, cover, (0, TABLE_Y - 8, W, H), table)

    lx, ly = LAMP
    def lamp(d, s):
        d.ellipse(s(lx - 40, TABLE_Y - 14, lx + 40, TABLE_Y + 6), fill=_c((0.55, 0.42, 0.20)))
        d.rectangle(s(lx - 5, ly + 36, lx + 5, TABLE_Y - 6), fill=_c((0.58, 0.44, 0.22)))
        d.polygon(s(lx - 40, ly - 40, lx + 40, ly - 40, lx + 70, ly + 40, lx - 70, ly + 40),
                  fill=_c((0.84, 0.75, 0.60)))
        for i in range(1, 8):   # pleats, and a trim at the top and bottom
            f = i / 8
            d.line(s(lx - 40 + 80 * f, ly - 38, lx - 70 + 140 * f, ly + 38),
                   fill=_c((0.70, 0.60, 0.46)), width=2)
        d.line(s(lx - 40, ly - 39, lx + 40, ly - 39), fill=_c((0.52, 0.38, 0.22)), width=5)
        d.line(s(lx - 70, ly + 38, lx + 70, ly + 38), fill=_c((0.52, 0.38, 0.22)), width=6)
    _place(albedo, cover, (lx - 80, ly - 50, lx + 80, TABLE_Y + 10), lamp)
    shade = Image.new("L", (W * 2, H * 2), 0)
    ImageDraw.Draw(shade).polygon([(2 * x, 2 * y) for x, y in (
        (lx - 40, ly - 40), (lx + 40, ly - 40), (lx + 70, ly + 40), (lx - 70, ly + 40))], fill=255)
    shade_mask = np.asarray(shade.resize((W, H), Image.LANCZOS), np.float32) / 255.0

    px = 400
    if picks.prop == "chai":
        def prop(d, s):
            d.polygon(s(px - 30, 1634, px + 30, 1634, px + 23, TABLE_Y, px - 23, TABLE_Y),
                      fill=_c((0.72, 0.70, 0.64)))
            d.polygon(s(px - 27, 1650, px + 27, 1650, px + 21, TABLE_Y - 3, px - 21, TABLE_Y - 3),
                      fill=_c((0.50, 0.28, 0.12)))
        _place(albedo, cover, (px - 40, 1625, px + 40, TABLE_Y + 4), prop)
    elif picks.prop == "radio":
        def prop(d, s):
            d.arc(s(px - 50, 1575, px + 50, 1650), 190, 350, fill=_c((0.30, 0.22, 0.16)), width=10)
            d.rounded_rectangle(s(px - 80, 1605, px + 80, TABLE_Y), radius=24,
                                fill=_c((0.46, 0.17, 0.12)))
            for gx in range(px - 64, px + 4, 12):
                for gy in range(1622, TABLE_Y - 14, 12):
                    d.ellipse(s(gx, gy, gx + 6, gy + 6), fill=_c((0.26, 0.10, 0.08)))
            d.ellipse(s(px + 22, 1628, px + 62, 1668), fill=_c((0.82, 0.72, 0.52)))
        _place(albedo, cover, (px - 90, 1570, px + 90, TABLE_Y + 4), prop)
    else:
        def prop(d, s):
            d.polygon(s(px - 60, TABLE_Y - 4, px + 70, TABLE_Y - 4, px + 76, TABLE_Y + 8,
                        px - 54, TABLE_Y + 8), fill=_c((0.80, 0.74, 0.62)))
            d.polygon(s(px - 40, TABLE_Y - 2, px + 34, TABLE_Y - 2, px + 50, 1596, px - 22, 1590),
                      fill=_c((0.88, 0.83, 0.72)))
            for i in range(6):
                y = 1612 + i * 14
                d.line(s(px - 26 + i * 1.5, y, px + 36 + i * 0.5, y + 3),
                       fill=_c((0.62, 0.56, 0.48)), width=2)
        _place(albedo, cover, (px - 70, 1580, px + 90, TABLE_Y + 12), prop)

    wood, dark = _c((0.34, 0.21, 0.12)), _c((0.27, 0.16, 0.095))
    def chair(d, s):
        for x in (790, 1010):
            d.rectangle(s(x - 14, 1590, x + 14, H), fill=wood)
            d.ellipse(s(x - 18, 1560, x + 18, 1596), fill=wood)
        d.chord(s(776, 1560, 1024, 1680), 180, 360, fill=dark)
        d.rectangle(s(790, 1740, 1010, 1766), fill=dark)
    _place(albedo, cover, (760, 1550, W, H), chair)

    cloth, gota = _c(picks.dupatta_rgb), _c((0.86, 0.68, 0.30))
    def dupatta(d, s):   # over the top rail, one end falling in front with an uneven hem
        d.polygon(s(826, 1612, 858, 1580, 936, 1576, 972, 1606, 984, 1760, 996, 1902, 954, 1914,
                    912, 1898, 868, 1916, 826, 1900, 816, 1760), fill=cloth)
        d.line(s(822, 1880, 868, 1896, 912, 1880, 954, 1896, 992, 1884), fill=gota, width=7)
        for i in range(9):
            x = 826 + i * 19
            d.ellipse(s(x, 1896 + (i % 2) * 6, x + 6, 1902 + (i % 2) * 6), fill=gota)

    def folds(h, w):   # soft vertical folds that open out toward the hem
        yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
        return 0.7 + 0.3 * (0.5 + 0.5 * np.sin(xx / (7 + 5 * yy / h) + 0.8 * np.sin(yy / 50)))
    _place(albedo, cover, (806, 1566, 1004, H), dupatta, folds)

    band = slice(1440, H)   # contact shadow: the wall darkens softly around what stands on it
    ao = paint.blur(cover[band], 14.0)
    albedo[band] *= (1.0 - 0.5 * ao * (1.0 - cover[band]))[..., None]
    return shade_mask


# --- Lamp light --------------------------------------------------------------------------------
def lamp_light() -> np.ndarray:
    """The lit lamp's light on the wall at half size, peak about 1: a fan up from the shade's
    open top, a pool around it, and light down onto the table."""
    yy, xx = np.mgrid[0:HH, 0:HW].astype(np.float32)
    cx, cy = LAMP[0] / 2, LAMP[1] / 2
    dx, dy = xx - cx, yy - cy
    d = np.hypot(dx, dy) + 1e-3
    pool = 1.0 / (1.0 + (d / 70.0) ** 2)
    up = np.where(dy < 0, np.exp(-(np.arctan2(dx, -dy) / 0.7) ** 2), 0.0)
    down = np.where(dy > 0, np.exp(-(np.arctan2(dx, dy) / 1.1) ** 2), 0.0)
    warm = 1.0 / (1.0 + (d / 300.0) ** 2)   # the whole corner warms
    light = 0.6 * pool + (0.8 * up + 0.7 * down) / (1.0 + (d / 200.0) ** 2) + 0.35 * warm
    return (light / light.max()).astype(np.float32)
