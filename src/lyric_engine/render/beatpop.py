"""Beat Pop motion: spec docs/specs/12_beat_pop_theme.md, plan *_impl.md.

One lyric line at a time (lifecycle.schedule, as Cinematic). No word shows before it is sung:
each pops in (easeOutBack) from its own reveal frame and is at rest by its own end frame; while
it is sung it sits black on a mustard pill (H-019). The whole line bumps on every beat and shakes
on each owner-written drop. Word frames come only from timeline.word_plans (red line 1): beats
and drops scale and shift the line, never a word's frames. Every drawn string goes through
frames.checked_mask (red line 2).
"""
from __future__ import annotations

import math
from bisect import bisect_right
from dataclasses import dataclass, field

from PIL import Image, ImageDraw, ImageFilter

from ..layout import FontSet, LineLayout, WordBox, word_fonts, word_mask
from ..theme import EMPHASIS_MAX, Theme
from .frames import LEVELS, _scaled, _solid, band_parts, checked_mask
from .karaoke import ease_in_quad, ease_out_back, sprite_pad, stroke_px, transformed
from .lifecycle import schedule
from .timeline import WordPlan, _ceil_frame, _floor_frame, laid_out_lines, word_plans

# Drop shake directions, one per frame in turn: fixed, so renders repeat and the check can
# predict them; no component above 1, so no offset exceeds shake_px (plan §2.6)
SHAKE = ((1, .35), (-.8, -.6), (.45, .9), (-1, .15), (.7, -.7), (-.3, 1), (.9, .5), (-.6, -.9))
POP_MARGIN = 0.05   # line canvas room for a popping word's overshoot (1.04x), × the widest word
PILL_SS = 4         # the pill is drawn this many times larger, then reduced: smooth corners
PILL_ROUND = 0.2    # corner radius × pill height: small enough that a glyph's corner stays in


# --- Data --------------------------------------------------------------------------------------
@dataclass
class PopLine:
    layout: LineLayout
    words: list[WordPlan]
    first_cur: int            # its first reveal: the line's first frame (no entrance)
    last_end: int             # latest end frame of its words
    settled: int              # never leaves before this (= last_end)
    enter: int = 0
    rest: int = 0
    leave: int = 0            # the exit starts here ...
    stop: int = 0             # ... and ends here (exclusive)
    notes: list[str] = field(default_factory=list)   # for the report: cuts

    @property
    def name(self) -> str:
        return f"line {self.layout.line + 1}"

    def label(self, wp: WordPlan) -> str:
        return f'word {wp.box.index} "{wp.text}" (line {self.layout.line + 1})'


@dataclass
class Show:
    lines: list[PopLine]
    beats: list[int]          # beat frames (beat − lead), ascending
    drops: list[int]          # drop frames (snapped drop − lead), ascending
    notes: list[str] = field(default_factory=list)   # for the report: beats used, drops


BSprites = dict[int, tuple[Image.Image, Image.Image, Image.Image, Image.Image, int]]
# word index -> (shadow, stroke outline, glyph, pill: "L" masks, one solid colour each; pad)


class PopCache:
    """The visible line's coloured word layers per pop scale, its image for the last looks and
    its last drawn layer. Dropped when the visible line changes (one line at a time)."""

    def __init__(self) -> None:
        self.line: int | None = None
        self.words: dict[tuple[int, float], tuple] = {}
        self.image: tuple[tuple, Image.Image, int, int] | None = None
        self.layer: tuple[tuple, Image.Image, tuple[int, int]] | None = None


# --- Timeline ----------------------------------------------------------------------------------
def _frames(times, theme: Theme, n_frames: int) -> list[int]:
    """Beat or drop times as frames, with the words' lead (plan §2.7)."""
    frames = {_floor_frame(t - theme.lead_s, theme.fps) for t in times}
    return sorted(f for f in frames if 0 <= f < n_frames)


def plan_beatpop(doc: dict, theme: Theme, n_frames: int, emphasis: frozenset[int] = frozenset(),
                 beats=(), drops=(), layout_fn=None) -> tuple[Show, list[int]]:
    """Shown lines in time order with their life cycle, the beat and drop frames (spec §4.2), and
    the lines skipped because none of their words has a time. `beats`, `drops`: seconds (drops
    already snapped to beats). At most one line is visible per frame."""
    rows, skipped = laid_out_lines(doc, theme, layout_fn, emphasis)
    lines = []
    for words, lay in rows:
        wps = word_plans(words, lay, theme)
        timed = [wp for wp in wps if wp.reveal is not None]
        last = max(wp.end for wp in timed)
        lines.append(PopLine(lay, wps, min(wp.reveal for wp in timed), last, last))
    lines.sort(key=lambda pl: (pl.first_cur, pl.layout.line))
    schedule(lines, theme, n_frames, ahead=False)
    show = Show(lines, _frames(beats, theme, n_frames), _frames(drops, theme, n_frames))
    for f in show.drops:
        if not any(pl.enter <= f < pl.stop for pl in lines):
            t = f / theme.fps + theme.lead_s
            show.notes.append(f"drop at {int(t // 60)}:{t % 60:04.1f}: no line on screen, "
                              "nothing shaken")
    return show, skipped


def pop_frames(wp: WordPlan, theme: Theme) -> int:
    """Frames of a timed word's pop: reveal_s, shrunk to its own span, at least 1 (plan §2.3):
    ink on its reveal frame, at rest on reveal + fi − 1, never after its end frame."""
    return max(1, min(_ceil_frame(theme.reveal_s, theme.fps), wp.end - wp.reveal))


def word_look(pl: PopLine, wp: WordPlan, n: int, theme: Theme) -> tuple[float, bool] | None:
    """(pop scale, sung) of a word at frame n, or None when it is not drawn. Sung (black on its
    pill) exactly on reveal <= n < end. An untimed word is at rest from its line's first frame,
    never popping, never sung."""
    if wp.reveal is None:
        return None if n < pl.first_cur else (1.0, False)
    if n < wp.reveal:
        return None
    x = (n - wp.reveal + 1) / pop_frames(wp, theme)
    q = 1.0 if x >= 1 else round(theme.pop_scale + (1 - theme.pop_scale) * ease_out_back(x), 3)
    return q, n < wp.end


def accent(show: Show, n: int, theme: Theme) -> tuple[float, int, int]:
    """(line scale, dx, dy) at frame n: the bump of the latest beat and the shake of the latest
    drop, each at its peak on its own frame, then easing back (plan §2.5). The larger scale wins:
    a drop sits on a beat, and their product would outgrow the layout's margin."""
    fps, scale, dx, dy = theme.fps, 1.0, 0, 0
    i = bisect_right(show.beats, n) - 1
    D = max(1, _ceil_frame(theme.bump_s, fps))
    if i >= 0 and (d := n - show.beats[i]) < D:
        scale = 1 + (theme.bump_scale - 1) * (1 - d / D) ** 2
    j = bisect_right(show.drops, n) - 1
    S = max(1, _ceil_frame(theme.shake_s, fps))
    if j >= 0 and (d := n - show.drops[j]) < S:
        k = (1 - d / S) ** 2
        scale = max(scale, 1 + (theme.drop_scale - 1) * k)
        ux, uy = SHAKE[d % len(SHAKE)]
        dx, dy = round(theme.shake_px * k * ux), round(theme.shake_px * k * uy)
    return round(scale, 3), dx, dy


def line_state(show: Show, pl: PopLine, n: int, theme: Theme) -> tuple[float, int, int, float]:
    """(scale, dx, dy, opacity) of the line at frame n; opacity 0 when it is not on screen. While
    it leaves it fades and shrinks to exit_scale, on top of any bump."""
    if not pl.enter <= n < pl.stop:
        return 1.0, 0, 0, 0.0
    scale, dx, dy = accent(show, n, theme)
    if n < pl.leave:
        return scale, dx, dy, 1.0
    x = ease_in_quad((n - pl.leave) / max(1, pl.stop - pl.leave))
    return round(scale * (1 + (theme.exit_scale - 1) * x), 3), dx, dy, 1.0 - x


def readable(show: Show, pl: PopLine, m: int) -> bool:
    """Whether the check can read line pl on frame m: not shown yet or not leaving, and no other
    line on screen (only a cut leaves one there)."""
    own = m < pl.enter or pl.enter <= m < pl.leave
    return own and not any(o is not pl and o.enter <= m < o.stop for o in show.lines)


# --- Sprites -----------------------------------------------------------------------------------
def pad_px(theme: Theme) -> int:
    """One pad for every sprite: stroke and shadow reach, or the widest pill margin (plan §2.11)."""
    return max(sprite_pad(theme), math.ceil(theme.pill_pad * theme.font_size * EMPHASIS_MAX) + 1)


def pill_mask(fonts: FontSet, box: WordBox, pad: int, theme: Theme) -> Image.Image:
    """The word's pill, an "L" mask the size of its padded sprite (plan §2.10): cap top to
    descender bottom of its font, grown by pill_pad × its size, round ends, inside the box."""
    px = round(theme.pill_pad * fonts.size)
    cap = fonts.runs("H")[0][1].getbbox("H", anchor="ls")[1]
    low = fonts.runs("g")[0][1].getbbox("g", anchor="ls")[3]
    x0, x1 = pad - px, pad + box.w + px
    y0 = max(pad, pad + fonts.ascent + cap - px)
    y1 = min(pad + box.h, pad + fonts.ascent + low + px)
    size = (box.w + 2 * pad, box.h + 2 * pad)
    big = Image.new("L", (size[0] * PILL_SS, size[1] * PILL_SS), 0)
    ImageDraw.Draw(big).rounded_rectangle(
        (x0 * PILL_SS, y0 * PILL_SS, x1 * PILL_SS - 1, y1 * PILL_SS - 1),
        radius=round(PILL_ROUND * (y1 - y0) * PILL_SS), fill=255)
    return big.resize(size, Image.LANCZOS)


def build_sprites(show: Show, theme: Theme) -> BSprites:
    """Per word: shadow, stroke outline, glyph and pill masks, coloured at draw time."""
    pad, sprites = pad_px(theme), {}
    for pl in show.lines:
        for wp in pl.words:
            fonts = word_fonts(theme, pl.layout.font_size, wp.box.emphasis)
            glyph = checked_mask(wp.text, wp.box, fonts, pad)
            outline = word_mask(wp.text, fonts, pad, stroke=stroke_px(theme, fonts.size))
            shadow = Image.new("L", glyph.size, 0)
            shadow.paste(_scaled(outline.filter(ImageFilter.GaussianBlur(theme.shadow_radius)),
                                 theme.shadow_alpha), theme.shadow_offset)
            sprites[wp.box.index] = (shadow, outline, glyph, pill_mask(fonts, wp.box, pad, theme),
                                     pad)
    return sprites


# --- Frames ------------------------------------------------------------------------------------
def _word_layers(sprites: BSprites, wp: WordPlan, q: float, theme: Theme,
                 cache: PopCache) -> tuple:
    """(under, pill, glyph in text colour, glyph on the pill, top-left) of a word at pop scale q,
    scaled about its box centre. Each mask is one solid colour, so scaling its alpha is exact."""
    hit = cache.words.get((wp.box.index, q))
    if hit is not None:
        return hit
    shadow, outline, glyph, pill, pad = sprites[wp.box.index]
    b = wp.box
    x, y = b.x - pad, b.y - pad
    if q != 1.0:
        size = (max(1, round(glyph.width * q)), max(1, round(glyph.height * q)))
        shadow, outline, glyph, pill = (m.resize(size, Image.BICUBIC)
                                        for m in (shadow, outline, glyph, pill))
        cx, cy = b.x + b.w / 2, b.y + b.h / 2
        x, y = round(cx + (x - cx) * q), round(cy + (y - cy) * q)
    under = Image.alpha_composite(_solid(theme.shadow_rgb, shadow),
                                  _solid(theme.stroke_rgb, outline))
    layers = (under, _solid(theme.pill_rgb, pill), _solid(theme.text_rgb, glyph),
              _solid(theme.pill_text_rgb, glyph), (x, y))
    cache.words[(wp.box.index, q)] = layers
    return layers


def line_image(pl: PopLine, sprites: BSprites, n: int, theme: Theme,
               cache: PopCache) -> tuple[Image.Image, int, int]:
    """The line's words at their frame-n looks on one canvas, its top-left on the frame: every
    shadow and stroke, then the pill, then every glyph (plan §2.9). A sung word has no shadow or
    stroke: the pill is its legibility layer, and a stroke would stick out of its round ends."""
    key = tuple(word_look(pl, wp, n, theme) for wp in pl.words)
    if cache.image is not None and cache.image[0] == key:
        return cache.image[1], cache.image[2], cache.image[3]
    margin = sprites[pl.words[0].box.index][4] + math.ceil(
        POP_MARGIN * max(wp.box.w for wp in pl.words))
    x0 = min(wp.box.x for wp in pl.words) - margin
    y0 = min(wp.box.y for wp in pl.words) - margin
    x1 = max(wp.box.x + wp.box.w for wp in pl.words) + margin
    y1 = max(wp.box.y + wp.box.h for wp in pl.words) + margin
    img = Image.new("RGBA", (x1 - x0, y1 - y0), (0, 0, 0, 0))
    drawn = [(look[1], _word_layers(sprites, wp, look[0], theme, cache))
             for wp, look in zip(pl.words, key) if look is not None]
    for sung, (under, pill, text, on_pill, (x, y)) in drawn:
        if not sung:
            img.alpha_composite(under, dest=(x - x0, y - y0))
    for sung, (under, pill, text, on_pill, (x, y)) in drawn:
        if sung:
            img.alpha_composite(pill, dest=(x - x0, y - y0))
    for sung, (under, pill, text, on_pill, (x, y)) in drawn:
        img.alpha_composite(on_pill if sung else text, dest=(x - x0, y - y0))
    cache.image = (key, img, x0, y0)
    return img, x0, y0


def frame_parts(n: int, show: Show, sprites: BSprites, theme: Theme, cache: PopCache) -> list:
    """Frame n as bytes-like pieces (frames.band_parts): the one visible line, bumped, shaken,
    and faded while it leaves."""
    pl = next((pl for pl in show.lines if pl.enter <= n < pl.stop), None)
    if pl is None:
        return band_parts([], theme)
    if cache.line != pl.layout.line:
        cache.line, cache.words, cache.image, cache.layer = pl.layout.line, {}, None, None
    scale, dx, dy, opacity = line_state(show, pl, n, theme)
    level = min(LEVELS, round(opacity * LEVELS))
    if level <= 0:
        return band_parts([], theme)
    img, x0, y0 = line_image(pl, sprites, n, theme, cache)
    lkey = (cache.image[0], scale, dx, dy, level)
    if cache.layer is None or cache.layer[0] != lkey:
        layer, pos = transformed(img, x0, y0, pl.layout, scale, dy, level, theme, dx=dx)
        cache.layer = (lkey, layer, pos)
    return band_parts([(cache.layer[1], cache.layer[2])], theme)
