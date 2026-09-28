"""Karaoke motion (Pop Karaoke): spec docs/specs/07_pop_karaoke_theme.md, plan *_impl.md.

A line is on screen before it is sung. Colour fills each word left to right between that word's
own start and end frames (red line 1); nothing else ever moves a fill. When the next line enters,
the finished line moves up, shrinks and dims into the past slot. Every drawn string goes through
frames.checked_mask (red line 2).
"""
from __future__ import annotations

import math
from dataclasses import dataclass

from PIL import Image, ImageFilter

from .. import layout
from ..layout import LineLayout, WordBox
from ..theme import EMPHASIS_MAX, Theme
from .frames import _LUTS, LEVELS, _scaled, _solid, band_parts, checked_mask
from .timeline import _ceil_frame, _floor_frame, _timed, laid_out_lines


# --- Easing (research §5) ----------------------------------------------------------------------
def _clamp(x: float) -> float:
    return max(0.0, min(1.0, x))


def ease_out_back(x: float) -> float:
    """Overshoots the target by 10% at most (c1 = 1.70158), then settles on it."""
    x, c1 = _clamp(x), 1.70158
    return 1 + (c1 + 1) * (x - 1) ** 3 + c1 * (x - 1) ** 2


def ease_out_cubic(x: float) -> float:
    return 1 - (1 - _clamp(x)) ** 3


def ease_in_quad(x: float) -> float:
    return _clamp(x) ** 2


def smoothstep(x: float) -> float:
    x = _clamp(x)
    return x * x * (3 - 2 * x)


# --- Data --------------------------------------------------------------------------------------
@dataclass
class FillWord:
    box: WordBox
    text: str                 # the words.json text; checked_mask asserts box.text == text
    start: int | None         # fill start frame, floor(start − lead); None = untimed, never fills
    end: int | None           # fill end frame, ≥ start


@dataclass
class KaraokeLine:
    layout: LineLayout
    words: list[FillWord]
    first_fill: int           # earliest fill start of its timed words
    last_end: int             # latest fill end of its timed words
    enter: int = 0            # first visible frame: the entrance starts
    rest: int = 0             # first frame at rest (full size, full opacity, final place)
    handover: int | None = None   # the next line's enter, when it takes over; None = clears
    past: bool = False        # moves into the past slot at handover (False: fades in place)
    past_dy: int = 0          # block-centre shift into the past slot (negative = up)
    fade_start: int = 0       # exit fade from here ...
    stop: int = 0             # ... to nothing at stop (exclusive)


KSprites = dict[int, tuple[Image.Image, Image.Image, Image.Image, int]]
# word index -> (under: shadow + stroke, glyph in text colour, glyph in accent, pad)


# --- Timeline ----------------------------------------------------------------------------------
def fill_progress(fw: FillWord, n: int) -> float:
    """0 before the word's start frame, 1 from its end frame, linear between (spec §4.4)."""
    if fw.start is None or n < fw.start:
        return 0.0
    if n >= fw.end:
        return 1.0
    return (n - fw.start) / (fw.end - fw.start)


def _enter_frames(theme: Theme) -> int:
    return max(1, _ceil_frame(theme.enter_s, theme.fps))


def _block(lay: LineLayout) -> tuple[int, int]:
    """Top and bottom of the line's word boxes at rest."""
    return min(b.y for b in lay.words), max(b.y + b.h for b in lay.words)


def _past_slot(lay: LineLayout, nxt: LineLayout, theme: Theme, pad: int) -> tuple[int, bool]:
    """Shift of the line's centre into the past slot above `nxt`, and whether it fits there."""
    top, bottom = _block(lay)
    half = (bottom - top) / 2
    target = _block(nxt)[0] - theme.past_gap_px - theme.past_scale * half
    fits = (theme.safe_zone is None
            or target - theme.past_scale * (half + pad) >= theme.safe_zone[1])
    return round(target - (top + bottom) / 2), fits


def plan_karaoke(doc: dict, theme: Theme, n_frames: int, emphasis: frozenset[int] = frozenset(),
                 layout_fn=None) -> tuple[list[KaraokeLine], list[int]]:
    """Shown lines in time order with their fill frames and life cycle (spec §4.3), and the lines
    skipped because none of their words has a time. At most two lines are visible per frame."""
    fps, lead = theme.fps, theme.lead_s
    E, P = _enter_frames(theme), round(theme.preroll_s * fps)
    H, X = _ceil_frame(theme.hold_s, fps), round(theme.fade_out_s * fps)
    rows, skipped = laid_out_lines(doc, theme, layout_fn, emphasis)
    lines = []
    for words, lay in rows:
        fws = []
        for w, box in zip(words, lay.words):
            if not _timed(w):
                fws.append(FillWord(box, w["text"], None, None))
                continue
            start = max(0, _floor_frame(w["start"] - lead, fps))
            fws.append(FillWord(box, w["text"], start,
                                max(start, _floor_frame(w["end"] - lead, fps))))
        timed = [f for f in fws if f.start is not None]
        lines.append(KaraokeLine(lay, fws, min(f.start for f in timed), max(f.end for f in timed)))
    lines.sort(key=lambda kl: (kl.first_fill, kl.layout.line))

    prev = None   # enter: preroll ahead, after the previous line's last word, at rest in time
    for kl in lines:
        latest = kl.first_fill - E - 1
        if latest < 0:   # sung within the entrance time of 0:00: shown at rest from frame 0
            kl.enter = kl.rest = 0
        else:
            kl.enter = min(max(kl.first_fill - P, prev.last_end + 1 if prev else 0), latest)
            kl.enter = max(kl.enter, prev.enter + 1) if prev else kl.enter
            kl.rest = kl.enter + E
        prev = kl

    pad = sprite_pad(theme)
    for k, kl in enumerate(lines):   # leave: hand over to the next line, or clear
        nxt = lines[k + 1] if k + 1 < len(lines) else None
        clear_at = kl.last_end + H
        if nxt is not None and nxt.enter <= clear_at + X:
            kl.handover = nxt.enter
            kl.past_dy, kl.past = _past_slot(kl.layout, nxt.layout, theme, pad)
        else:
            kl.fade_start, kl.stop = clear_at, clear_at + X
    for k, kl in enumerate(lines):   # a past line leaves as the line after next enters
        if kl.handover is None:
            continue
        nxt = lines[k + 1]
        if not kl.past:
            kl.fade_start, kl.stop = kl.handover, kl.handover + X
        elif nxt.handover is not None:
            kl.stop = nxt.handover
            kl.fade_start = max(kl.handover, kl.stop - X)
        else:   # the current line clears: fade together
            kl.fade_start, kl.stop = nxt.fade_start, nxt.stop
    for k, kl in enumerate(lines):   # never three lines at once
        kl.stop = min(kl.stop, n_frames, *([lines[k + 2].enter] if k + 2 < len(lines) else []))
        kl.fade_start = min(kl.fade_start, kl.stop)
    return lines, skipped


def line_state(kl: KaraokeLine, n: int, theme: Theme) -> tuple[float, float, float]:
    """(scale, dy, opacity) of the line at frame n; opacity 0 when it is not on screen.
    Exactly (1.0, 0.0, 1.0) at rest, so the line is then drawn unscaled."""
    if not kl.enter <= n < kl.stop:
        return 1.0, 0.0, 0.0
    E = _enter_frames(theme)
    scale, dy, op = 1.0, 0.0, 1.0
    if n < kl.rest:
        e = (n - kl.enter) / E
        scale = theme.enter_scale + (1 - theme.enter_scale) * ease_out_back(e)
        op = smoothstep(e)   # faint while a handed-over line is still moving out of the way
    if kl.past and kl.handover is not None and n > kl.handover:
        h = ease_out_cubic((n - kl.handover) / E)
        scale *= 1 + (theme.past_scale - 1) * h
        op *= 1 + (theme.past_opacity - 1) * h
        dy = kl.past_dy * h
    if n >= kl.fade_start:
        op *= 1 - ease_in_quad((n - kl.fade_start) / max(1, kl.stop - kl.fade_start))
    return scale, dy, op


# --- Sprites -----------------------------------------------------------------------------------
def stroke_px(theme: Theme, size: int) -> int:
    return max(1, round(size * theme.stroke_frac)) if theme.stroke_frac else 0


def sprite_pad(theme: Theme) -> int:
    """One pad for every word: room for the widest stroke plus the shadow's blur and offset."""
    return (stroke_px(theme, math.ceil(theme.font_size * EMPHASIS_MAX))
            + 3 * theme.shadow_radius + max(abs(v) for v in theme.shadow_offset))


def build_sprites(lines: list[KaraokeLine], theme: Theme) -> KSprites:
    """Per word: the shadow + stroke layer, and its glyph in the text and the accent colour.
    Both glyphs share one alpha, so blending them changes colour only."""
    pad, sprites = sprite_pad(theme), {}
    for kl in lines:
        for fw in kl.words:
            fonts = layout.word_fonts(theme, kl.layout.font_size, fw.box.emphasis)
            glyph = checked_mask(fw.text, fw.box, fonts, pad)
            outline = layout.word_mask(fw.text, fonts, pad, stroke=stroke_px(theme, fonts.size))
            shadow = Image.new("L", glyph.size, 0)
            shadow.paste(_scaled(outline.filter(ImageFilter.GaussianBlur(theme.shadow_radius)),
                                 theme.shadow_alpha), theme.shadow_offset)
            under = Image.alpha_composite(_solid(theme.shadow_rgb, shadow),
                                          _solid(theme.stroke_rgb, outline))
            sprites[fw.box.index] = (under, _solid(theme.text_rgb, glyph),
                                     _solid(theme.accent_rgb, glyph), pad)
    return sprites


def _fill_state(fw: FillWord, n: int, theme: Theme, pad: int) -> str | int:
    """"base", "hot", or the fill edge's x in the sprite (whole px, so frames are cacheable)."""
    p = fill_progress(fw, n)
    if p <= 0:
        return "base"
    if p >= 1:
        return "hot"
    return round(pad + p * (fw.box.w + theme.fill_soft_px))


def _filled(base: Image.Image, hot: Image.Image, edge: int, soft: int) -> Image.Image:
    """The glyph with the accent up to `edge`, fading to the text colour over `soft` px."""
    row = Image.new("L", (base.width, 1))
    row.putdata([round(255 * _clamp((edge - x) / soft)) for x in range(base.width)])
    return Image.composite(hot, base, row.resize(base.size, Image.NEAREST))


# --- Frames ------------------------------------------------------------------------------------
class LineCache:
    """Per visible line: its composed image for the last fill state, and its last drawn layer.
    Entries of lines that left the screen are dropped."""

    def __init__(self) -> None:
        self.images: dict[int, tuple[tuple, Image.Image]] = {}
        self.layers: dict[int, tuple[tuple, Image.Image, tuple[int, int]]] = {}


def line_image(kl: KaraokeLine, sprites: KSprites, n: int, theme: Theme,
               cache: LineCache) -> tuple[Image.Image, tuple, int, int]:
    """The line's words at their fill states on one canvas (every shadow and stroke under every
    glyph), its fill key, and its top-left on the frame at rest."""
    pad = sprites[kl.words[0].box.index][3]
    x0, y0 = min(f.box.x for f in kl.words) - pad, min(f.box.y for f in kl.words) - pad
    key = tuple(_fill_state(fw, n, theme, pad) for fw in kl.words)
    hit = cache.images.get(kl.layout.line)
    if hit is not None and hit[0] == key:
        return hit[1], key, x0, y0
    x1 = max(f.box.x + f.box.w for f in kl.words) + pad
    y1 = max(f.box.y + f.box.h for f in kl.words) + pad
    img = Image.new("RGBA", (x1 - x0, y1 - y0), (0, 0, 0, 0))
    for fw in kl.words:
        img.alpha_composite(sprites[fw.box.index][0], dest=(fw.box.x - pad - x0,
                                                            fw.box.y - pad - y0))
    for fw, state in zip(kl.words, key):
        _, base, hot, _ = sprites[fw.box.index]
        glyph = (base if state == "base" else hot if state == "hot"
                 else _filled(base, hot, state, theme.fill_soft_px))
        img.alpha_composite(glyph, dest=(fw.box.x - pad - x0, fw.box.y - pad - y0))
    cache.images[kl.layout.line] = (key, img)
    return img, key, x0, y0


def _layer(kl: KaraokeLine, sprites: KSprites, n: int, theme: Theme,
           cache: LineCache) -> tuple[Image.Image, tuple[int, int]] | None:
    scale, dy, op = line_state(kl, n, theme)
    level = min(LEVELS, round(op * LEVELS))
    if level <= 0:
        return None
    img, key, x0, y0 = line_image(kl, sprites, n, theme, cache)
    tkey = (key, scale, dy, level)
    hit = cache.layers.get(kl.layout.line)
    if hit is not None and hit[0] == tkey:
        return hit[1], hit[2]
    img, pos = transformed(img, x0, y0, kl.layout, scale, dy, level, theme)
    cache.layers[kl.layout.line] = (tkey, img, pos)
    return img, pos


def transformed(img: Image.Image, x0: int, y0: int, lay: LineLayout, scale: float, dy: float,
                level: int, theme: Theme, blur: float = 0.0, dx: float = 0.0
                ) -> tuple[Image.Image, tuple[int, int]]:
    """A line image scaled about its block centre, shifted by (dx, dy), blurred, then faded to
    `level`, and its new top-left. Scale and blur run premultiplied: no dark fringes. Untouched
    at rest."""
    if scale != 1.0 or dx != 0.0 or dy != 0.0 or blur > 0:
        top, bottom = _block(lay)
        cx, cy = theme.center_x, (top + bottom) / 2
        img = img.convert("RGBa")
        if scale != 1.0 or dx != 0.0 or dy != 0.0:
            size = (max(1, round(img.width * scale)), max(1, round(img.height * scale)))
            img = img.resize(size, Image.BICUBIC)
            x0, y0 = round(cx + dx + (x0 - cx) * scale), round(cy + dy + (y0 - cy) * scale)
        if blur > 0:
            img = img.filter(ImageFilter.GaussianBlur(blur))
        img = img.convert("RGBA")
    if level < LEVELS:
        img = img.copy()
        img.putalpha(img.getchannel("A").point(_LUTS[level]))
    return img, (x0, y0)


def frame_parts(n: int, lines: list[KaraokeLine], sprites: KSprites, theme: Theme,
                cache: LineCache) -> list:
    """Frame n as bytes-like pieces (frames.band_parts): the past line under the current one."""
    visible = [kl for kl in lines if kl.enter <= n < kl.stop]   # enter order: past line first
    live = {kl.layout.line for kl in visible}
    for store in (cache.images, cache.layers):
        for line in [line for line in store if line not in live]:
            del store[line]
    layers = [layer for kl in visible if (layer := _layer(kl, sprites, n, theme, cache))]
    return band_parts(layers, theme)
