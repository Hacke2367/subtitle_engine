"""The romantic room (docs/backgrounds/romantic_room.md, spec 17): one sunlit wall whose light
follows the song. A mood is a RoomLook; `dusk` (afternoon to dusk) is the default and, for now,
the only one built. The room reads only the song's facts (length, word times, marked words' times,
the seed), never what the words say."""
from __future__ import annotations

import math
from dataclasses import dataclass, field

import numpy as np
from PIL import Image

from . import paint, room_art as art

# (name, rgb 0..1): the dupatta's colour is one of the seeded picks
DUPATTAS = (("rani pink", (0.78, 0.16, 0.42)), ("marigold", (0.92, 0.58, 0.10)),
            ("peacock", (0.07, 0.46, 0.50)), ("maroon", (0.47, 0.09, 0.15)))


@dataclass(frozen=True)
class RoomLook:
    """One mood's numbers. Fractions run from 0 (first frame) to 1 (the last shown line's first
    word); colours are 0..1 light colours."""
    sun_keys: tuple                     # ((fraction, (r, g, b), intensity), ...)
    ambient_keys: tuple                 # ((fraction, (r, g, b)), ...)
    sun_gain: float = 0.66              # the patch's brightness on the wall at full intensity
    lamp_rgb: tuple = (1.0, 0.70, 0.40)
    lamp_gain: float = 1.7
    lamp_ramp_s: float = 1.4            # the lamp's glow reaches full over this ...
    lamp_flicker_s: float = 0.35        # ... after one flicker in its first moments
    gust_rise_s: float = 0.35           # a marked word's gust swells over this ...
    gust_s: float = 1.6                 # ... and is gone this long after the word starts
    gust_bloom: float = 0.3            # the sun patch brightens this much at a gust's peak
    sun_shadow_from: tuple = (10, 14)   # the lyrics' sun shadow offset (full px) at the start ...
    sun_shadow_to: tuple = (26, 24)     # ... and at the end of the arc: it lengthens
    sun_shadow_alpha: float = 0.7      # share of the sun it blocks
    lamp_shadow: tuple = (14, -18)      # the lamp is low on the left: its shadow falls up-right
    lamp_shadow_alpha: float = 0.7
    shadow_soft: int = 3                # half-size box radius of the lyrics' shadows
    tint_k: float = 0.2                 # the text moves this far toward the light's colour
    patch_drift: tuple = (22, 46)       # the patch moves this far (half px) over the arc ...
    patch_stretch: float = 1.1          # ... and lengthens to this


GOLD, ROSE, MAUVE, SKY = (1.0, 0.80, 0.52), (1.0, 0.62, 0.56), (0.86, 0.52, 0.64), (0.5, 0.62, 1.0)
DUSK = RoomLook(   # after sunset the jaali still lets in a little blue skylight
    sun_keys=((0.0, GOLD, 1.0), (0.4, GOLD, 0.96), (0.7, ROSE, 0.82), (0.88, MAUVE, 0.5),
              (1.0, SKY, 0.34)),
    ambient_keys=((0.0, (0.26, 0.21, 0.18)), (0.7, (0.25, 0.19, 0.21)), (1.0, (0.17, 0.20, 0.33))))
MOODS = {"dusk": DUSK}


@dataclass(frozen=True)
class Picks:
    """The seeded details (spec 4.3); the jaali, window and wall never change."""
    plant: str
    curtain: str
    prop: str
    dupatta: str
    dupatta_rgb: tuple

    def describe(self) -> str:
        return (f"money plant on the {self.plant}, {self.curtain} curtain, {self.prop} on the "
                f"table, {self.dupatta} dupatta")


def pick(rng: np.random.Generator) -> Picks:
    """Always drawn first and in this order, so a folder keeps its room."""
    plant = ("left", "right")[rng.integers(2)]
    curtain = ("plain", "block-print", "lace")[rng.integers(3)]
    prop = ("chai", "radio", "letter")[rng.integers(3)]
    name, rgb = DUPATTAS[rng.integers(len(DUPATTAS))]
    return Picks(plant, curtain, prop, name, rgb)


@dataclass
class Light:
    """One frame's light, half size: see compose.compose_frame for how it is used."""
    ambient: np.ndarray                 # (3,)
    sun: np.ndarray                     # (h, w): the patch with leaves, curtain, gust, intensity
    sun_rgb: np.ndarray                 # (3,)
    sun_shadow: tuple                   # (dx, dy, alpha): full px, share of the sun it blocks
    lamp: np.ndarray | None             # (h, w) × level, or None while off
    lamp_rgb: np.ndarray
    lamp_shadow: tuple
    air: np.ndarray                     # (h, w): dust in the beam, chai steam
    glow: float                         # the lamp shade's own glow, 0..1
    tint: np.ndarray                    # (3,) per-channel text multiplier, each in [0.9, 1]


@dataclass
class Room:
    facts: object                       # background.SongFacts
    look: RoomLook
    size: tuple = (art.W, art.H)
    picks: Picks = field(init=False)
    albedo: np.ndarray = field(init=False)

    def __post_init__(self) -> None:
        rng = np.random.default_rng(self.facts.seed)
        self.picks = pick(rng)
        self.albedo = art.wall()
        self.shade = art.props(self.albedo, self.picks)
        self.albedo_half = np.stack([paint.down2(self.albedo[..., c]) for c in range(3)], -1)
        rgba = np.full((*self.albedo.shape[:2], 4), 255, np.uint8)
        rgba[..., :3] = np.clip(self.albedo * 255 + 0.5, 0, 255)
        self.albedo_img = Image.fromarray(rgba, "RGBA")
        self.patch = art.jaali_patch()
        self.leaves = art.leaves(self.picks.plant, rng)
        self.lamp_map = art.lamp_light()
        # dust motes: x, y, size, phase, speed, glint (0..1 each)
        self.motes = rng.uniform(0, 1, (70, 6)).astype(np.float32)
        self.curtain_side = "right" if self.picks.plant == "left" else "left"
        self.gust_times = [s for s, _ in self.facts.marks]
        # the lit shade (brightest at its open bottom) and its halo; nothing above y 1540
        x0, y0, x1, y1 = art.LAMP[0] - 150, 1540, art.LAMP[0] + 170, art.TABLE_Y + 60
        ramp = np.linspace(0.0, 1.0, y1 - y0, dtype=np.float32)[:, None]
        lit = self.shade[y0:y1, x0:x1] * (0.1 + 0.3 * np.clip((ramp - 0.1) * 2.2, 0, 1))
        halo = paint.blur(self.shade[y0 - 60:y1 + 60, x0:x1], 22.0)[60:-60]
        self.glow = (x0, y0, (lit + halo * 0.3)[..., None]
                     * np.asarray(self.look.lamp_rgb, np.float32))

    # --- song time -------------------------------------------------------------------------------
    def fraction(self, t: float) -> float:
        last = self.facts.last_line_s
        end = last if last is not None else self.facts.duration
        return min(1.0, max(0.0, t / end)) if end > 0 else 1.0

    def lamp_level(self, t: float) -> float:
        """0 before the last shown line's first word; one flicker, then a smooth rise to 1."""
        start = self.facts.last_line_s
        if start is None or t < start:
            return 0.0
        x, flicker = t - start, self.look.lamp_flicker_s
        if x < flicker:   # on, a blink off, on again
            return 0.0 if flicker * 0.4 <= x <= flicker * 0.7 else 0.35
        return 0.35 + 0.65 * float(paint.smooth((x - flicker) / self.look.lamp_ramp_s))

    def arc(self, t: float) -> tuple[np.ndarray, float, np.ndarray, float, float]:
        """(sun_rgb, sun intensity, ambient_rgb, lamp level, fraction) at time t (spec 4.2)."""
        f = self.fraction(t)
        keys = self.look.sun_keys
        sun_rgb = paint.keyframes([(k[0], k[1]) for k in keys], f)
        sun_i = float(paint.keyframes([(k[0], k[2]) for k in keys], f))
        ambient = paint.keyframes(self.look.ambient_keys, f)
        return sun_rgb, sun_i, ambient, self.lamp_level(t), f

    def gust(self, t: float) -> float:
        return paint.envelope(t, self.gust_times, self.look.gust_rise_s, self.look.gust_s)

    # --- one frame -------------------------------------------------------------------------------
    def light(self, k: int) -> Light:
        look, t = self.look, k / self.facts.fps
        sun_rgb, sun_i, ambient, lamp_level, f = self.arc(t)
        g = self.gust(t)
        canvas = self.patch.copy()
        mask, (x0, y0) = art.leaf_shadow(self.leaves, t, 1.0 + 1.5 * g)
        canvas[y0:y0 + mask.shape[0], x0:x0 + mask.shape[1]] *= 1.0 - 0.85 * mask
        art.apply_curtain(canvas, self.curtain_side, self.picks.curtain, t, g)
        s = float(paint.smooth(f))
        dx, dy = look.patch_drift[0] * s, look.patch_drift[1] * s
        stretch = 1.0 + (look.patch_stretch - 1.0) * s
        box = (art.PAD - dx, art.PAD - dy, art.PAD - dx + art.HW, art.PAD - dy + art.HH / stretch)
        sun = paint.resize(canvas, art.HW, art.HH, box)
        sun *= look.sun_gain * sun_i * (1.0 + look.gust_bloom * g)
        lamp = self.lamp_map * (look.lamp_gain * lamp_level) if lamp_level > 0 else None
        air = self._air(t, sun, sun_i)
        sx = look.sun_shadow_from[0] + (look.sun_shadow_to[0] - look.sun_shadow_from[0]) * f
        sy = look.sun_shadow_from[1] + (look.sun_shadow_to[1] - look.sun_shadow_from[1]) * f
        return Light(ambient, sun, sun_rgb, (sx, sy, look.sun_shadow_alpha), lamp,
                     np.asarray(look.lamp_rgb, np.float32),
                     (*look.lamp_shadow, look.lamp_shadow_alpha), air, lamp_level,
                     self._tint(ambient, sun_rgb, sun_i, lamp_level))

    def _air(self, t: float, sun: np.ndarray, sun_i: float) -> np.ndarray:
        """Dust motes lit by the beam (dimmed inside the lyric area) and the chai's steam."""
        air = np.zeros((art.HH, art.HW), np.float32)
        m = self.motes
        xs = (m[:, 0] * art.HW + 18 * np.sin(t * (0.15 + 0.2 * m[:, 4]) + 6.28 * m[:, 3])) % art.HW
        ys = (m[:, 1] * art.HH - t * (2 + 5 * m[:, 4])
              + 12 * np.sin(t * 0.2 + 9 * m[:, 3])) % art.HH
        xi, yi = xs.astype(int), ys.astype(int)
        lit = sun[yi, xi] * (0.5 + 0.5 * np.sin(t * 1.3 + 20 * m[:, 5])) ** 2
        inside = (yi >= 190) & (yi < 770) & (xi >= 30) & (xi < 480)
        np.add.at(air, (yi, xi), lit * np.where(inside, 0.3, 1.0) * (1.5 + 3 * m[:, 2]))
        if self.picks.prop == "chai":   # three wisps from the glass, gone before y 1540
            for w in range(3):
                for j in range(26):
                    h = j / 25
                    y = int(814 - 34 * h - w * 3)
                    x = int(200 + 5 * math.sin(t * 1.1 + h * 5 + w * 2.1) + (w - 1) * 5)
                    air[y, x] += 0.05 * (1 - h) * (0.6 + 0.4 * math.sin(t * 2 + w))
        return paint.soft(air, 1) * 4.0

    def _tint(self, ambient, sun_rgb, sun_i, lamp_level) -> np.ndarray:
        """Per-channel text multiplier toward the lyrics' main light colour, each in [0.9, 1]."""
        light = (ambient + sun_rgb * sun_i * self.look.sun_gain
                 + np.asarray(self.look.lamp_rgb) * lamp_level * 0.3)
        colour = np.clip(light / max(float(light.max()), 1e-6), 0.5, 1.0)
        return (1.0 - self.look.tint_k * (1.0 - colour)).astype(np.float32)
