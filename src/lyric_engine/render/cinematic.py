"""Cinematic motion: spec docs/specs/10_cinematic_theme.md, plan *_impl.md.

Couplets (H-017): the lines of a stanza show in pairs, one block on screen at a time, with Lofi
Typewriter's life cycle (lifecycle.schedule). No word shows before it is sung: each blurs into
focus in the accent (gold) from its own reveal frame, is complete by its own end frame, then
settles to the text colour (ivory). Word frames come only from timeline.word_plans (red line 1);
blur, colour, hold and exit never move them. Every drawn string goes through frames.checked_mask
(red line 2).
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field, replace
from functools import partial

from PIL import Image, ImageFilter

from .. import layout
from ..layout import LineLayout, font_set, word_fonts
from ..theme import Theme
from .frames import _LUTS, LEVELS, _scaled, _solid, band_parts, checked_mask
from .karaoke import _block, ease_in_quad, ease_out_cubic, smoothstep, sprite_pad, transformed
from .lifecycle import schedule
from .lofi import mix_rgb
from .timeline import WordPlan, _ceil_frame, laid_out_lines, word_plans

REST = (1.0, 0.0)   # block_state of a block at rest: (opacity, blur)


# --- Data --------------------------------------------------------------------------------------
@dataclass
class Block:
    lines: tuple[LineLayout, ...]   # 1 or 2 lyric lines, shifted into place, in line order
    words: list[WordPlan]           # every word, line order; boxes at their shifted place
    line_of: dict[int, int]         # word index -> lyric line
    line_first: dict[int, int]      # lyric line -> its first reveal: untimed words show from here
    first_cur: int                  # earliest reveal: the block's first frame
    last_end: int                   # latest end frame of its words
    settled: int                    # never leaves before this (= last_end, spec §4.3)
    enter: int = 0                  # first visible frame (= first_cur: no entrance)
    rest: int = 0
    leave: int = 0                  # the blur-out starts here ...
    stop: int = 0                   # ... and ends here (exclusive)
    notes: list[str] = field(default_factory=list)   # for the report: cuts, too-tall couplets

    @property
    def name(self) -> str:
        nums = [lay.line + 1 for lay in self.lines]
        return f"line {nums[0]}" if len(nums) == 1 else f"lines {nums[0]}-{nums[-1]}"

    def label(self, wp: WordPlan) -> str:
        return f'word {wp.box.index} "{wp.text}" (line {self.line_of[wp.box.index] + 1})'

    def font_size(self, wp: WordPlan) -> int:
        line = self.line_of[wp.box.index]
        return next(lay.font_size for lay in self.lines if lay.line == line)


CSprites = dict[int, tuple[Image.Image, Image.Image, int]]   # word -> (shadow L, glyph L, pad)


class CinematicCache:
    """The visible block's blurred masks, its settled looks, its image for the last looks and its
    last layer. Dropped when the visible block changes (one block at a time)."""

    def __init__(self) -> None:
        self.block: int | None = None   # first lyric line of the visible block
        self.masks: dict[tuple[int, int, int], Image.Image] = {}
        self.looks: dict[tuple, tuple[Image.Image, Image.Image]] = {}
        self.image: tuple[tuple, Image.Image] | None = None
        self.layer: tuple[tuple, Image.Image, tuple[int, int]] | None = None


def pad_px(theme: Theme) -> int:
    """One pad for every sprite and the block canvas: shadow reach plus the widest blur."""
    return sprite_pad(theme) + 3 * math.ceil(theme.blur_px)


# --- Timeline ----------------------------------------------------------------------------------
def couplet_groups(lyric_lines: list[str]) -> list[tuple[int, ...]]:
    """Lyric line indexes in pairs per stanza (blank lines split stanzas): 1+2, 3+4; an odd
    stanza's last line alone (spec §4.2)."""
    groups: list[tuple[int, ...]] = []
    run: list[int] = []
    for k, text in enumerate([*lyric_lines, ""]):
        if text.strip():
            run.append(k)
            continue
        groups += [tuple(run[i:i + 2]) for i in range(0, len(run), 2)]
        run = []
    return groups


def _stack(lays: list[LineLayout], theme: Theme) -> tuple[LineLayout, ...] | None:
    """The lines one under the other, the couplet gap between them, the block centred on anchor_y
    and moved up only as far as its bottom needs to stay in the safe zone; None when it is taller
    than the safe zone (spec §4.2, plan §5.2)."""
    fonts = font_set(theme, lays[0].font_size)
    h = fonts.ascent + fonts.descent
    pitch = round(h * theme.row_spacing)
    gap = pitch - h + round(theme.couplet_gap * pitch)
    spans = [_block(lay) for lay in lays]
    total = sum(bottom - top for top, bottom in spans) + gap * (len(lays) - 1)
    zone, halo = theme.safe_zone or (0, 0, theme.width, theme.height), sprite_pad(theme)
    y0, y1 = zone[1] + halo, zone[3] - halo
    if total > y1 - y0:
        return None
    y = max(y0, min(round(theme.anchor_y * theme.height - total / 2), y1 - total))
    out = []
    for lay, (top, bottom) in zip(lays, spans):
        out.append(LineLayout(lay.line, lay.font_size,
                              tuple(replace(b, y=b.y + y - top) for b in lay.words)))
        y += bottom - top + gap
    return tuple(out)


def _make_block(parts: list[tuple[list[dict], LineLayout]], theme: Theme) -> Block:
    wps: list[WordPlan] = []
    line_of, line_first = {}, {}
    for words, lay in parts:
        plans = word_plans(words, lay, theme)
        wps += plans
        line_of.update((wp.box.index, lay.line) for wp in plans)
        line_first[lay.line] = min(wp.reveal for wp in plans if wp.reveal is not None)
    last = max(wp.end for wp in wps if wp.reveal is not None)
    return Block(tuple(lay for _, lay in parts), wps, line_of, line_first,
                 min(line_first.values()), last, last)


def plan_cinematic(doc: dict, theme: Theme, n_frames: int, emphasis: frozenset[int] = frozenset(),
                   layout_fn=None) -> tuple[list[Block], list[int]]:
    """Shown blocks in time order with their life cycle (spec §4.2-4.3, plan §5.1), and the lines
    skipped because none of their words has a time. At most one block is visible per frame."""
    layout_fn = layout_fn or layout.layout_line
    rows, skipped = laid_out_lines(doc, theme, layout_fn, emphasis)
    shown = {lay.line: (words, lay) for words, lay in rows}
    blocks = []
    for group in couplet_groups(doc["lyrics"]["lines"]):
        kept = [shown[k] for k in group if k in shown]
        block, note = _couplet(kept, theme, layout_fn, emphasis) if len(kept) == 2 else (None, None)
        if block is not None:
            blocks.append(block)
            continue
        for k, (words, lay) in enumerate(kept):   # singles
            blocks.append(_make_block([(words, (_stack([lay], theme) or (lay,))[0])], theme))
            if k == 0 and note:
                blocks[-1].notes.append(note)
    blocks.sort(key=lambda b: (b.first_cur, b.lines[0].line))
    schedule(blocks, theme, n_frames, ahead=False)
    return blocks, skipped


def _couplet(kept: list[tuple[list[dict], LineLayout]], theme: Theme, layout_fn,
             emphasis: frozenset[int]) -> tuple[Block | None, str | None]:
    """Two shown lines of a stanza as one block, or (None, a note or None) when they show as
    singles: sung out of order or more than couplet_max_gap_s apart (no note), or too tall."""
    a, b = (_make_block([part], theme) for part in kept)
    if (b.first_cur < a.first_cur
            or b.first_cur - a.last_end > round(theme.couplet_max_gap_s * theme.fps)):
        return None, None
    size = min(lay.font_size for _, lay in kept)
    fit = partial(layout_fn, size=size)   # laid_out_lines re-checks the placed words (red line 2)
    parts = [part if part[1].font_size == size
             else laid_out_lines({"words": part[0]}, theme, fit, emphasis)[0][0] for part in kept]
    stacked = _stack([lay for _, lay in parts], theme)
    if stacked is None:
        return None, (f"lines {a.lines[0].line + 1}-{b.lines[0].line + 1}: shown one at a time "
                      "(couplet taller than the safe zone)")
    return _make_block([(w, lay) for (w, _), lay in zip(parts, stacked)], theme), None


def blur_in_frames(wp: WordPlan, theme: Theme) -> int:
    """Frames of a timed word's blur-in: reveal_s, shrunk to its own span, at least 1 (spec §4.4,
    plan §2.7): ink on its reveal frame, complete on reveal + fi − 1, never after its end frame."""
    return max(1, min(_ceil_frame(theme.reveal_s, theme.fps), wp.end - wp.reveal))


def word_look(b: Block, wp: WordPlan, n: int, theme: Theme) -> tuple[int, int, int] | None:
    """A word's look at frame n: (opacity level, blur px, mix level; LEVELS = accent), or None
    when it is not drawn. An untimed word is sharp text colour from its own line's first frame,
    never the accent (spec §4.1)."""
    if wp.reveal is None:
        return None if n < b.line_first[b.line_of[wp.box.index]] else (LEVELS, 0, 0)
    if n < wp.reveal:
        return None
    e = ease_out_cubic((n - wp.reveal + 1) / blur_in_frames(wp, theme))
    mix = 1.0 if n < wp.end else 1.0 - smoothstep((n - wp.end) / (theme.sung_in_s * theme.fps))
    return max(1, round(e * LEVELS)), round(theme.blur_px * (1 - e)), round(mix * LEVELS)


def block_state(b: Block, n: int, theme: Theme) -> tuple[float, float]:
    """(opacity, blur) of the block at frame n; opacity 0 when it is not on screen. Exactly REST
    until it leaves, so the block is then pasted untouched."""
    if not b.enter <= n < b.stop:
        return 0.0, 0.0
    if n < b.leave:
        return REST
    x = ease_in_quad((n - b.leave) / max(1, b.stop - b.leave))
    return 1.0 - x, theme.blur_px * x


def readable(blocks: list[Block], b: Block, m: int, theme: Theme) -> bool:
    """Whether the check can read a word of block b on frame m: b at rest (or not shown yet), and
    no other block on screen (only a cut leaves one there)."""
    own = m < b.enter or block_state(b, m, theme) == REST
    return own and not any(o is not b and block_state(o, m, theme)[0] > 0 for o in blocks)


# --- Sprites -----------------------------------------------------------------------------------
def build_sprites(blocks: list[Block], theme: Theme) -> CSprites:
    """Per word: its shadow and glyph as "L" masks (coloured per look at draw time) and the pad."""
    pad, sprites = pad_px(theme), {}
    for b in blocks:
        for wp in b.words:
            fonts = word_fonts(theme, b.font_size(wp), wp.box.emphasis)
            mask = checked_mask(wp.text, wp.box, fonts, pad)
            shadow = Image.new("L", mask.size, 0)
            shadow.paste(_scaled(mask.filter(ImageFilter.GaussianBlur(theme.shadow_radius)),
                                 theme.shadow_alpha), theme.shadow_offset)
            sprites[wp.box.index] = (shadow, mask, pad)
    return sprites


def _mask(sprites: CSprites, index: int, kind: int, r: int, cache: CinematicCache) -> Image.Image:
    """Mask `kind` (0 shadow, 1 glyph) blurred by r px. Each is one solid colour when drawn, so
    blurring the alpha alone is exact (plan §2.8)."""
    if r == 0:
        return sprites[index][kind]
    key = (index, kind, r)
    if key not in cache.masks:
        cache.masks[key] = sprites[index][kind].filter(ImageFilter.GaussianBlur(r))
    return cache.masks[key]


def _look(sprites: CSprites, index: int, key: tuple[int, int, int], theme: Theme,
          cache: CinematicCache) -> tuple[Image.Image, Image.Image]:
    """(shadow, glyph) RGBA of a word at a look. Only the two settled looks are cached; a blur-in
    or colour-fade look is used on about one frame."""
    hit = cache.looks.get((index, *key))
    if hit is not None:
        return hit
    level, r, ml = key
    pair = []
    for kind, rgb in ((0, theme.shadow_rgb), (1, mix_rgb(theme.text_rgb, theme.accent_rgb, ml))):
        alpha = _mask(sprites, index, kind, r, cache)
        pair.append(_solid(rgb, alpha if level >= LEVELS else alpha.point(_LUTS[level])))
    look = (pair[0], pair[1])
    if level == LEVELS and r == 0 and ml in (0, LEVELS):
        cache.looks[(index, *key)] = look
    return look


# --- Frames ------------------------------------------------------------------------------------
def block_image(b: Block, sprites: CSprites, n: int, theme: Theme,
                cache: CinematicCache) -> tuple[Image.Image, int, int]:
    """The block's words at their frame-n looks on one canvas, every shadow under every glyph
    (plan §2.9), and its top-left on the frame."""
    pad = sprites[b.words[0].box.index][2]
    x0 = min(wp.box.x for wp in b.words) - pad
    y0 = min(wp.box.y for wp in b.words) - pad
    key = tuple(word_look(b, wp, n, theme) for wp in b.words)
    if cache.image is not None and cache.image[0] == key:
        return cache.image[1], x0, y0
    x1 = max(wp.box.x + wp.box.w for wp in b.words) + pad
    y1 = max(wp.box.y + wp.box.h for wp in b.words) + pad
    img = Image.new("RGBA", (x1 - x0, y1 - y0), (0, 0, 0, 0))
    looks = [(wp, _look(sprites, wp.box.index, look, theme, cache))
             for wp, look in zip(b.words, key) if look is not None]
    for part in (0, 1):
        for wp, pair in looks:
            img.alpha_composite(pair[part], dest=(wp.box.x - pad - x0, wp.box.y - pad - y0))
    cache.image = (key, img)
    return img, x0, y0


def frame_parts(n: int, blocks: list[Block], sprites: CSprites, theme: Theme,
                cache: CinematicCache) -> list:
    """Frame n as bytes-like pieces (frames.band_parts): the one visible block, blurred and faded
    while it leaves."""
    b = next((b for b in blocks if b.enter <= n < b.stop), None)
    if b is None:
        return band_parts([], theme)
    if cache.block != b.lines[0].line:
        cache.block, cache.masks, cache.looks = b.lines[0].line, {}, {}
        cache.image = cache.layer = None
    opacity, blur = block_state(b, n, theme)
    level = min(LEVELS, round(opacity * LEVELS))
    if level <= 0:
        return band_parts([], theme)
    img, x0, y0 = block_image(b, sprites, n, theme, cache)
    lkey = (cache.image[0], level, round(blur))
    if cache.layer is None or cache.layer[0] != lkey:
        layer, pos = transformed(img, x0, y0, b.lines[0], 1.0, 0.0, level, theme, round(blur))
        cache.layer = (lkey, layer, pos)
    return band_parts([(cache.layer[1], cache.layer[2])], theme)
