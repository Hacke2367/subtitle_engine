"""Focus motion (Soft Romantic v2): spec docs/specs/08_soft_romantic_v2.md, plan *_impl.md.

Words reveal and glow on exactly v1's frames (timeline.word_plans and word_state: red line 1); a
held word's glow only breathes, inside its own glow window. When the next line starts, the
finished line moves up into the past slot, dimming, shrinking and blurring (Pop Karaoke's
primitives). Upcoming words are never drawn (H-010, H-014). Every drawn string goes through
frames.build_sprites -> checked_mask (red line 2).
"""
from __future__ import annotations

import math
from dataclasses import dataclass

from PIL import Image

from ..layout import LineLayout
from ..theme import Theme
from .frames import LEVELS, FadeCache, Sprites, band_parts
from .karaoke import _block, _enter_frames, _past_slot, ease_in_quad, ease_out_cubic, transformed
from .timeline import WordPlan, _ceil_frame, laid_out_lines, word_plans, word_state

REST = (1.0, 0.0, 1.0, 0.0)   # line_state of a line in the current slot: (scale, dy, opacity, blur)


# --- Data --------------------------------------------------------------------------------------
@dataclass
class FocusLine:
    layout: LineLayout
    words: list[WordPlan]     # v1's per-word frames; also what frames.build_sprites reads
    first: int                # first visible frame: its earliest reveal
    last_reveal: int          # a hand-over never starts before this (spec §4.2)
    last_end: int             # hold counts from here
    handover: int | None = None   # the move into the past slot starts here; None = clears
    past: bool = False        # moves up at handover (False: fades and blurs in place)
    past_dy: int = 0          # block-centre shift into the past slot (negative = up)
    fade_start: int = 0       # exit fade and blur from here ...
    stop: int = 0             # ... to nothing at stop (exclusive)


class FocusCache:
    """Per visible line: its image for the last word states, its last drawn layer, and its faded
    word sprites. Entries of lines that left the screen are dropped."""

    def __init__(self) -> None:
        self.images: dict[int, tuple[tuple, Image.Image]] = {}
        self.layers: dict[int, tuple[tuple, Image.Image, tuple[int, int]]] = {}
        self.fades: dict[int, FadeCache] = {}


# --- Timeline ----------------------------------------------------------------------------------
def plan_focus(doc: dict, theme: Theme, n_frames: int, emphasis: frozenset[int] = frozenset(),
               layout_fn=None) -> tuple[list[FocusLine], list[int]]:
    """Shown lines in time order with their stack life cycle (spec §4.2), and the lines skipped
    because none of their words has a time. At most two lines are visible per frame."""
    fps = theme.fps
    E, L = _enter_frames(theme), round(theme.handover_lead_s * fps)
    H, X = _ceil_frame(theme.hold_s, fps), round(theme.fade_out_s * fps)
    rows, skipped = laid_out_lines(doc, theme, layout_fn, emphasis)
    lines = []
    for words, lay in rows:
        wps = word_plans(words, lay, theme)
        timed = [wp for wp in wps if wp.reveal is not None]
        lines.append(FocusLine(lay, wps, min(wp.reveal for wp in timed),
                               max(wp.reveal for wp in timed), max(wp.end for wp in timed)))
    lines.sort(key=lambda fl: (fl.first, fl.layout.line))

    pad = 3 * theme.glow_radius   # frames.build_sprites' pad
    for k, fl in enumerate(lines):   # hand over to the next line, or clear
        nxt = lines[k + 1] if k + 1 < len(lines) else None
        clear_at = fl.last_end + H
        # Hand over if the move would start before a clear could finish: a line still fading
        # out in the current slot must never meet the next line's first word there.
        if nxt is not None and nxt.first - L <= clear_at + X:
            fl.handover = max(nxt.first - L, fl.last_reveal)
            fl.past_dy, fl.past = _past_slot(fl.layout, nxt.layout, theme, pad)
        else:
            fl.fade_start, fl.stop = clear_at, clear_at + X
    for k, fl in enumerate(lines):   # a past line leaves as the next hand-over starts
        if fl.handover is None:
            continue
        nxt = lines[k + 1]
        if not fl.past:
            fl.fade_start, fl.stop = fl.handover, fl.handover + X
        elif nxt.handover is not None:
            fl.stop = nxt.handover
            fl.fade_start = max(fl.handover, fl.stop - X)
        else:   # the current line clears: fade together
            fl.fade_start, fl.stop = nxt.fade_start, nxt.stop
    for k, fl in enumerate(lines):   # never three lines at once
        fl.stop = min(fl.stop, n_frames, *([lines[k + 2].first] if k + 2 < len(lines) else []))
        fl.fade_start = min(fl.fade_start, fl.stop)
    return lines, skipped


def held(wp: WordPlan, theme: Theme) -> bool:
    """A held note: the word's own frames span at least breath_min_s."""
    return wp.reveal is not None and wp.end - wp.reveal >= round(theme.breath_min_s * theme.fps)


def breath(wp: WordPlan, n: int, theme: Theme) -> float:
    """Glow factor: 1, except for a held word once its glow is full, where it follows a slow
    cosine down to breath_low and back, frozen on the word's end frame (spec §4.3)."""
    if not held(wp, theme):
        return 1.0
    full = wp.reveal + _ceil_frame(theme.glow_in_s, theme.fps)
    if n <= full:
        return 1.0
    phase = (min(n, wp.end) - full) / (theme.breath_period_s * theme.fps)
    return 1 - (1 - theme.breath_low) * (1 - math.cos(2 * math.pi * phase)) / 2


def word_look(wp: WordPlan, n: int, theme: Theme) -> tuple[float, float, float]:
    """(opacity, rise_px, glow) at frame n: v1's word_state, glow times the breath."""
    opacity, rise, glow = word_state(wp, n, theme)
    return opacity, rise, glow * breath(wp, n, theme)


def line_state(fl: FocusLine, n: int, theme: Theme) -> tuple[float, float, float, float]:
    """(scale, dy, opacity, blur) of the line at frame n; opacity 0 when it is not on screen.
    Exactly REST in the current slot, so the line is then drawn untouched."""
    if not fl.first <= n < fl.stop:
        return 1.0, 0.0, 0.0, 0.0
    h = 0.0
    if fl.past and fl.handover is not None and n > fl.handover:
        h = ease_out_cubic((n - fl.handover) / _enter_frames(theme))
    scale, dy = 1 + (theme.past_scale - 1) * h, fl.past_dy * h
    opacity, blur = 1 + (theme.past_opacity - 1) * h, theme.past_blur_px * h
    if n >= fl.fade_start:
        x = (n - fl.fade_start) / max(1, fl.stop - fl.fade_start)
        opacity *= 1 - ease_in_quad(x)
        blur = max(blur, theme.past_blur_px * x)
    return scale, dy, opacity, blur


def readable(lines: list[FocusLine], fl: FocusLine, m: int, theme: Theme,
             rect: tuple[int, int, int, int]) -> bool:
    """Whether the sync check can read a word of line fl on frame m, where `rect` is the frame
    area it reads (the word's ink): fl at rest in the current slot (or not drawn yet), and no
    other visible line's block (its boxes' extent, as moved) over `rect`. Faint halos (glow,
    shadow, blur) of a line nearby stay well inside the check's SYNC_DROP_MIN."""
    if m >= fl.first and line_state(fl, m, theme) != REST:
        return False
    for other in lines:
        if other is fl:
            continue
        scale, dy, opacity, _ = line_state(other, m, theme)
        if opacity <= 0:
            continue
        top, bottom = _block(other.layout)
        left = min(o.box.x for o in other.words)
        right = max(o.box.x + o.box.w for o in other.words)
        cx, cy = theme.center_x, (top + bottom) / 2
        x0, x1 = cx + (left - cx) * scale, cx + (right - cx) * scale
        y0, y1 = cy + dy + (top - cy) * scale, cy + dy + (bottom - cy) * scale
        if x0 < rect[2] and rect[0] < x1 and y0 < rect[3] and rect[1] < y1:
            return False
    return True


# --- Frames ------------------------------------------------------------------------------------
def line_image(fl: FocusLine, sprites: Sprites, n: int, theme: Theme,
               cache: FocusCache) -> tuple[Image.Image, tuple, int, int]:
    """The line's words at their frame-n looks on one canvas (every glow under every text), its
    look key, and its top-left on the frame at rest."""
    pad = sprites[fl.words[0].box.index][2]
    x0 = min(wp.box.x for wp in fl.words) - pad
    y0 = min(wp.box.y for wp in fl.words) - pad
    key = tuple((round(op * LEVELS), round(rise), round(glow * LEVELS))
                for op, rise, glow in (word_look(wp, n, theme) for wp in fl.words))
    hit = cache.images.get(fl.layout.line)
    if hit is not None and hit[0] == key:
        return hit[1], key, x0, y0
    x1 = max(wp.box.x + wp.box.w for wp in fl.words) + pad
    y1 = max(wp.box.y + wp.box.h for wp in fl.words) + pad + theme.rise_px   # rise draws lower
    img = Image.new("RGBA", (x1 - x0, y1 - y0), (0, 0, 0, 0))
    fades = cache.fades.setdefault(fl.layout.line, FadeCache())
    for kind, sprite_at, level_at in (("glow", 1, 2), ("text", 0, 0)):   # glows under texts
        for wp, look in zip(fl.words, key):
            if look[level_at] > 0:
                sprite = sprites[wp.box.index][sprite_at]
                img.alpha_composite(
                    fades.faded(sprite, look[level_at], (wp.box.index, kind, look[level_at])),
                    dest=(wp.box.x - pad - x0, wp.box.y - pad + look[1] - y0))
    cache.images[fl.layout.line] = (key, img)
    return img, key, x0, y0


def _layer(fl: FocusLine, sprites: Sprites, n: int, theme: Theme,
           cache: FocusCache) -> tuple[Image.Image, tuple[int, int]] | None:
    scale, dy, opacity, blur = line_state(fl, n, theme)
    level = min(LEVELS, round(opacity * LEVELS))
    if level <= 0:
        return None
    img, key, x0, y0 = line_image(fl, sprites, n, theme, cache)
    tkey = (key, scale, dy, blur, level)
    hit = cache.layers.get(fl.layout.line)
    if hit is not None and hit[0] == tkey:
        return hit[1], hit[2]
    img, pos = transformed(img, x0, y0, fl.layout, scale, dy, level, theme, blur)
    cache.layers[fl.layout.line] = (tkey, img, pos)
    return img, pos


def frame_parts(n: int, lines: list[FocusLine], sprites: Sprites, theme: Theme,
                cache: FocusCache) -> list:
    """Frame n as bytes-like pieces (frames.band_parts): the past line under the current one."""
    visible = [fl for fl in lines if fl.first <= n < fl.stop]   # time order: past line first
    live = {fl.layout.line for fl in visible}
    for store in (cache.images, cache.layers, cache.fades):
        for line in [line for line in store if line not in live]:
            del store[line]
    layers = [layer for fl in visible if (layer := _layer(fl, sprites, n, theme, cache))]
    return band_parts(layers, theme)
