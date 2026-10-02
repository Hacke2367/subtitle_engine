"""Lofi motion (Lofi Minimal, Lofi Typewriter): spec docs/specs/09_lofi_minimal_theme.md, plan
*_impl.md.

One line on screen at a time. In lofi-minimal the line shows ahead, dim (upcoming); each word
turns to the accent (current) from its own start frame to its own end frame, then settles back to
the text colour (sung). In lofi-typewriter nothing shows ahead: a word's letters type in inside
its own span. Word frames come only from timeline.word_plans and letter frames only from the
word's own start/end (red line 1); entrances, exits and cuts never move them. Every drawn string
goes through frames.checked_mask (red line 2).
"""
from __future__ import annotations

from dataclasses import dataclass, field

from PIL import Image, ImageFilter

from ..layout import LineLayout, word_fonts
from ..theme import Theme
from .frames import _LUTS, LEVELS, _scaled, _solid, band_parts, checked_mask
from .karaoke import ease_in_quad, ease_out_cubic, smoothstep, sprite_pad
from .lifecycle import schedule
from .timeline import WordPlan, _ceil_frame, _floor_frame, laid_out_lines, word_plans

REST = (1.0, 0.0)   # line_state of a line at rest: (opacity, dy)


# --- Data --------------------------------------------------------------------------------------
@dataclass
class LofiLine:
    layout: LineLayout
    words: list[WordPlan]     # v1's per-word frames; also what build_sprites reads
    letters: dict[int, tuple[int, ...]]   # typewriter: word index -> each letter's first frame
    first_cur: int            # earliest frame a word of the line turns current
    last_end: int             # latest end frame of its words
    settled: int              # the line never leaves before this (last_end, or a letter's fade)
    enter: int = 0            # first visible frame: the entrance starts
    rest: int = 0             # first frame at rest (full opacity, no rise)
    leave: int = 0            # the exit fade starts here ...
    stop: int = 0             # ... and ends here (exclusive)
    notes: list[str] = field(default_factory=list)   # for the report: cuts, words typed whole

    @property
    def name(self) -> str:
        return f"line {self.layout.line + 1}"

    def label(self, wp: WordPlan) -> str:
        return label(wp, self.layout)


LSprites = dict[int, tuple[Image.Image, Image.Image, int, tuple[int, ...]]]
# word index -> (shadow RGBA, glyph "L" mask, pad, band edges in sprite x: 0, ..., width)


class LofiCache:
    """The visible line's word looks, its image for the last looks, and its last faded layer.
    Dropped when the visible line changes (one line at a time)."""

    def __init__(self) -> None:
        self.line: int | None = None
        self.looks: dict[tuple, Image.Image] = {}
        self.image: tuple[tuple, Image.Image] | None = None
        self.layer: tuple[tuple, Image.Image] | None = None
        self.leaving: dict[int, LofiCache] = {}   # handover: the line sliding out has its own


def label(wp: WordPlan, lay: LineLayout) -> str:
    return f'word {wp.box.index} "{wp.text}" (line {lay.line + 1})'


# --- Timeline ----------------------------------------------------------------------------------
def letter_frames(w: dict, n: int, theme: Theme) -> tuple[int, ...]:
    """Each of n letters' first frame: letter i at start − lead + i·s, s = min(stagger,
    (end − start) / n). Only the word's own span sets them: letter 0 is its reveal frame and the
    last starts before its end (spec §4.4, red line 1)."""
    s = min(theme.type_stagger_s, (w["end"] - w["start"]) / n)
    t0 = w["start"] - theme.lead_s
    return tuple(max(0, _floor_frame(t0 + i * s, theme.fps)) for i in range(n))


def plan_lofi(doc: dict, theme: Theme, n_frames: int, emphasis: frozenset[int] = frozenset(),
              layout_fn=None) -> tuple[list[LofiLine], list[int]]:
    """Shown lines in time order with their life cycle (spec §4.2, plan §5.1), and the lines
    skipped because none of their words has a time. At most one line is visible per frame."""
    tw = theme.typewriter
    LF = _ceil_frame(theme.letter_fade_s, theme.fps)
    rows, skipped = laid_out_lines(doc, theme, layout_fn, emphasis)
    lines = []
    for words, lay in rows:
        wps = word_plans(words, lay, theme)
        timed = [wp for wp in wps if wp.reveal is not None]
        last = max(wp.end for wp in timed)
        ll = LofiLine(lay, wps, {}, min(wp.reveal for wp in timed), last, last)
        for w, wp in zip(words, wps):
            if not tw or wp.reveal is None:
                continue
            fonts = word_fonts(theme, lay.font_size, wp.box.emphasis)
            typeable = fonts.typeable(wp.text)
            frames = letter_frames(w, len(fonts.units(wp.text)) if typeable else 1, theme)
            ll.letters[wp.box.index] = frames
            ll.settled = max(ll.settled, frames[-1] + LF)   # never fade a letter still coming in
            if not typeable:
                ll.notes.append(f"{label(wp, lay)}: typed whole (non-Latin or fallback-font "
                                "characters)")
        lines.append(ll)
    lines.sort(key=lambda ll: (ll.first_cur, ll.layout.line))
    schedule(lines, theme, n_frames, ahead=not tw)
    if theme.handover and not tw:
        _handover(lines, theme, n_frames)
    return lines, skipped


HANDOVER_OUT_S = 0.3   # the leaving line fades out this fast (faster when the next line is close)
HANDOVER_IN_S = 0.2    # the shortest fade-in of the next line


def _handover(lines: list[LofiLine], theme: Theme, n_frames: int) -> None:
    """Lines sung close together hand over instead of cutting, and never share the screen: from
    max(the next line's preroll, the leaving line's last word) the leaving line fades out, then the
    next fades in. Word frames never move (red line 1)."""
    fps = theme.fps
    P, Ein = round(theme.preroll_s * fps), _ceil_frame(theme.enter_s, fps)
    H, X = _ceil_frame(theme.hold_s, fps), round(theme.fade_out_s * fps)
    for ll, nxt in zip(lines, lines[1:]):
        E, F = ll.settled, nxt.first_cur
        if F - P >= E + H + X:       # room to clear on its own: the plain plan stands
            continue
        t = max(min(max(F - P, E), F - 2), ll.rest, 0)
        ll.leave = t
        ll.stop = t + max(1, min(round(HANDOVER_OUT_S * fps), (F - t) // 3))
        nxt.enter = ll.stop
        nxt.rest = nxt.enter + max(round(HANDOVER_IN_S * fps), min(Ein, F - 1 - nxt.enter))
        ll.notes = [note for note in ll.notes if "cut, not faded" not in note
                    and "are not shown" not in note]
    for ll in lines:
        ll.stop = min(ll.stop, n_frames)
        ll.rest, ll.leave = min(ll.rest, ll.stop), min(ll.leave, ll.stop)
        ll.enter = min(ll.enter, ll.rest)


def colour_state(wp: WordPlan, n: int, theme: Theme) -> tuple[float, float]:
    """(opacity, mix) of a word at frame n; mix 0 = text colour, 1 = accent (spec §4.3). Current
    from the reveal frame, fully current on the end frame (the fade-in shrinks to fit), then
    settling to the text colour. An untimed word never turns current."""
    u = theme.upcoming_opacity
    if wp.reveal is None:
        return (1.0, 0.0) if theme.typewriter else (u, 0.0)
    if n < wp.reveal:
        return u, 0.0
    if n >= wp.end:
        return 1.0, 1.0 - smoothstep((n - wp.end) / (theme.sung_in_s * theme.fps))
    fi = min(_ceil_frame(theme.current_in_s, theme.fps), wp.end - wp.reveal)
    p = ease_out_cubic((n - wp.reveal) / fi)   # fi > 0 here: end > reveal
    return u + (1 - u) * p, p


def letter_levels(frames: tuple[int, ...], n: int, theme: Theme) -> tuple[int, ...]:
    """Each letter's opacity level at frame n: 0 on its first frame, full a letter fade later."""
    fade = _ceil_frame(theme.letter_fade_s, theme.fps)
    return tuple(round(max(0.0, min(1.0, (n - f) / fade)) * LEVELS) for f in frames)


def line_state(ll: LofiLine, n: int, theme: Theme) -> tuple[float, float]:
    """(opacity, dy) of the line at frame n; opacity 0 when it is not on screen. Exactly REST at
    rest, so the line is then pasted untouched."""
    if not ll.enter <= n < ll.stop:
        return 0.0, 0.0
    if n < ll.rest:
        e = ease_out_cubic((n - ll.enter) / (ll.rest - ll.enter))
        return e, theme.rise_px * (1 - e)
    if n >= ll.leave:
        x = ease_in_quad((n - ll.leave) / max(1, ll.stop - ll.leave))
        return 1.0 - x, -theme.exit_rise_px * x
    return REST


def readable(lines: list[LofiLine], ll: LofiLine, m: int, theme: Theme) -> bool:
    """Whether the check can read a word of line ll on frame m: ll at rest (or, typewriter, not
    shown yet), and no other line on screen (only a cut leaves one there)."""
    own = line_state(ll, m, theme) == REST or (theme.typewriter and m < ll.enter)
    return own and not any(o is not ll and line_state(o, m, theme)[0] > 0 for o in lines)


# --- Sprites -----------------------------------------------------------------------------------
def build_sprites(lines: list[LofiLine], theme: Theme) -> LSprites:
    """Per word: its shadow, its glyph mask (coloured per state at draw time), the pad, and the
    typewriter's letter bands. Bands split at the middle of each tracking gap and tile the sprite,
    so a fully typed word is exactly the whole word (plan §2.7)."""
    pad, sprites = sprite_pad(theme), {}
    for ll in lines:
        for wp in ll.words:
            fonts = word_fonts(theme, ll.layout.font_size, wp.box.emphasis)
            mask = checked_mask(wp.text, wp.box, fonts, pad)
            shadow = Image.new("L", mask.size, 0)
            shadow.paste(_scaled(mask.filter(ImageFilter.GaussianBlur(theme.shadow_radius)),
                                 theme.shadow_alpha), theme.shadow_offset)
            edges = (0, mask.width)
            if theme.typewriter and fonts.typeable(wp.text):
                xs = [x for _, _, _, x in fonts.units(wp.text)][1:]
                edges = (0, *(round(pad + x - fonts.tracking / 2) for x in xs), mask.width)
            sprites[wp.box.index] = (_solid(theme.shadow_rgb, shadow), mask, pad, edges)
    return sprites


def mix_rgb(a: tuple[int, int, int], b: tuple[int, int, int], level: int) -> tuple[int, ...]:
    return tuple(round(x + (y - x) * level / LEVELS) for x, y in zip(a, b))


# --- Frames ------------------------------------------------------------------------------------
def word_look(ll: LofiLine, wp: WordPlan, n: int, theme: Theme) -> tuple | None:
    """A word's look key at frame n: (opacity level, mix level), plus the letter levels while it
    is typing; None when nothing of it is drawn."""
    opacity, mix = colour_state(wp, n, theme)
    ml = round(mix * LEVELS)
    if not theme.typewriter:
        level = round(opacity * LEVELS)
        return (level, ml) if level > 0 else None
    if wp.reveal is None:   # untimed: whole, in the sung colour, with its line
        return LEVELS, 0
    levels = letter_levels(ll.letters[wp.box.index], n, theme)
    if not any(levels):
        return None
    return (LEVELS, ml) if min(levels) == LEVELS else (LEVELS, ml, levels)


def look_sprite(sprites: LSprites, index: int, key: tuple, theme: Theme,
                cache: LofiCache, rest: tuple[int, int, int] | None = None) -> Image.Image:
    """The word at a look: shadow + glyph composed at full opacity in the mixed colour, then
    faded, so solid ink keeps the exact state colour at any opacity (plan §2.3). While typing,
    each letter band is faded to its own level."""
    img = cache.looks.get((index, *key))
    if img is not None:
        return img
    under, mask, _, edges = sprites[index]
    ml = key[1]
    base = cache.looks.get((index, LEVELS, ml))
    if base is None:
        base = Image.alpha_composite(under, _solid(mix_rgb(rest or theme.text_rgb, theme.accent_rgb,
                                                           ml), mask))
        cache.looks[index, LEVELS, ml] = base
    if len(key) == 3:
        img = Image.new("RGBA", base.size, (0, 0, 0, 0))
        for x0, x1, level in zip(edges, edges[1:], key[2]):
            if level:
                band = base.crop((x0, 0, x1, base.height))
                if level < LEVELS:
                    band.putalpha(band.getchannel("A").point(_LUTS[level]))
                img.paste(band, (x0, 0))
    elif key[0] < LEVELS:
        img = base.copy()
        img.putalpha(base.getchannel("A").point(_LUTS[key[0]]))
    else:
        img = base
    cache.looks[(index, *key)] = img
    return img


def line_image(ll: LofiLine, sprites: LSprites, n: int, theme: Theme,
               cache: LofiCache) -> tuple[Image.Image, int, int]:
    """The line's words at their frame-n looks on one canvas, and its top-left at rest. A word's
    shadow never reaches another word's ink (word gap and row gap exceed the shadow), so each
    word is pasted whole, in any order."""
    pad = sprites[ll.words[0].box.index][2]
    x0 = min(wp.box.x for wp in ll.words) - pad
    y0 = min(wp.box.y for wp in ll.words) - pad
    key = tuple(word_look(ll, wp, n, theme) for wp in ll.words)
    if cache.image is not None and cache.image[0] == key:
        return cache.image[1], x0, y0
    x1 = max(wp.box.x + wp.box.w for wp in ll.words) + pad
    y1 = max(wp.box.y + wp.box.h for wp in ll.words) + pad
    img = Image.new("RGBA", (x1 - x0, y1 - y0), (0, 0, 0, 0))
    for wp, look in zip(ll.words, key):
        if look is not None:
            rest = theme.emphasis_rgb if wp.box.emphasis else None   # a marked word keeps its colour
            img.alpha_composite(look_sprite(sprites, wp.box.index, look, theme, cache, rest),
                                dest=(wp.box.x - pad - x0, wp.box.y - pad - y0))
    cache.image = (key, img)
    return img, x0, y0


def frame_parts(n: int, lines: list[LofiLine], sprites: LSprites, theme: Theme,
                cache: LofiCache) -> list:
    """Frame n as bytes-like pieces (frames.band_parts): the visible line, faded and risen (with
    handover, also the line sliding out above it)."""
    visible = [ll for ll in lines if ll.enter <= n < ll.stop]
    if not visible:
        return band_parts([], theme)
    current, rest = visible[-1], visible[:-1]
    cache.leaving = {ll.layout.line: cache.leaving.get(ll.layout.line) or LofiCache() for ll in rest}
    layers = [layer for ll in rest
              if (layer := _layer(n, ll, sprites, theme, cache.leaving[ll.layout.line]))]
    if layer := _layer(n, current, sprites, theme, cache):
        layers.append(layer)
    return band_parts(layers, theme)


def _layer(n: int, ll: LofiLine, sprites: LSprites, theme: Theme,
           cache: LofiCache) -> tuple[Image.Image, tuple[int, int]] | None:
    """One line at frame n, faded and moved, or None when nothing of it shows."""
    if cache.line != ll.layout.line:
        cache.line, cache.looks, cache.image, cache.layer = ll.layout.line, {}, None, None
    opacity, dy = line_state(ll, n, theme)
    level = min(LEVELS, round(opacity * LEVELS))
    if level <= 0:
        return None
    img, x0, y0 = line_image(ll, sprites, n, theme, cache)
    lkey = (cache.image[0], level)
    if cache.layer is None or cache.layer[0] != lkey:
        layer = img
        if level < LEVELS:
            layer = img.copy()
            layer.putalpha(img.getchannel("A").point(_LUTS[level]))
        cache.layer = (lkey, layer)
    return cache.layer[1], (x0, y0 + round(dy))
