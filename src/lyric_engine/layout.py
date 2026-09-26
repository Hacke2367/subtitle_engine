"""9:16 layout: font fallback, word masks, wrapping a lyric line into centred rows.

Plan: docs/specs/03_soft_romantic_render_impl.md. The dataclasses below are the contract render.py
builds on; do not change their fields.
"""
from __future__ import annotations

import itertools
import math
import re
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from fontTools.ttLib import TTFont
from PIL import Image, ImageDraw, ImageFont

from lyric_engine.theme import Theme


class LayoutError(ValueError):
    """The line cannot be laid out without clipping text or drawing a missing glyph."""


@dataclass(frozen=True)
class WordBox:
    index: int        # words.json "i"
    text: str         # exact words.json text (red line 2)
    x: int            # top-left of the word's mask on the full canvas, at rest (before any rise)
    y: int
    w: int            # mask size = word_mask(text, fonts) size
    h: int
    emphasis: bool = False   # *marked*: measured and drawn with word_fonts(..., True) (H-013)


@dataclass(frozen=True)
class LineLayout:
    line: int                 # lyrics line index
    font_size: int
    words: tuple[WordBox, ...]


# --- Fonts and word masks (plan §4) ------------------------------------------------------------
# Unicode Default_Ignorable_Code_Point: invisible by definition (ZWJ, variation selectors, soft
# hyphen, BOM, ...). Fonts can still map them to a glyph (Segoe UI Emoji's VS16 is a 1.4 em wide
# blank: a gap after every phone-typed heart, U+2764 U+FE0F), so they are never drawn. They stay
# in the word's text.
_IGNORABLE = re.compile("[\u00ad\u034f\u061c\u115f\u1160\u17b4\u17b5\u180b-\u180f\u200b-\u200f"
                        "\u202a-\u202e\u2060-\u206f\u3164\ufe00-\ufe0f\ufeff\uffa0\ufff0-\ufff8"
                        "\U0001bca0-\U0001bca3\U0001d173-\U0001d17a\U000e0000-\U000e0fff]")


def _latin(ch: str) -> bool:
    """Latin script plus the digits and punctuation Latin text uses (tracking and typewriter
    split these into single letters; anything else stays whole)."""
    c = ord(ch)
    return c < 0x250 or 0x1E00 <= c < 0x1F00 or 0x2000 <= c < 0x2070


@lru_cache(maxsize=None)
def _coverage(path: Path) -> frozenset[int]:
    """Code points a font file maps, read once per file. fontNumber=0: first face of a .ttc."""
    with TTFont(path, fontNumber=0, lazy=True) as font:
        return frozenset(font.getBestCmap() or ())


class FontSet:
    """The theme's fonts at one size. The box (ascent, descent) and the space come from the
    primary font only, so every word mask shares one height and baseline. With theme.tracking,
    letters sit tracking × size px further apart (spec 09); with 0, nothing changes."""

    def __init__(self, theme: Theme, size: int):
        if not Path(theme.font).is_file():
            raise LayoutError(f"theme font not found: {theme.font}")
        paths = [Path(theme.font), *(p for p in map(Path, theme.fallback_fonts) if p.is_file())]
        self.size = size
        self._fonts = [(ImageFont.truetype(str(p), size, index=0), _coverage(p)) for p in paths]
        self._shrunk: dict[tuple[int, int], ImageFont.FreeTypeFont] = {}
        primary = self._fonts[0][0]
        self.ascent, self.descent = primary.getmetrics()
        self.tracking = theme.tracking * size
        self.space = primary.getlength(" ")
        if self.tracking:   # a space is one more tracked character: a gap on each side
            self.space += 2 * self.tracking

    def _runs(self, text: str) -> list[tuple[str, int, ImageFont.FreeTypeFont]]:
        """Consecutive characters grouped by the first font whose cmap has them, with that
        font's index (0 = the primary font)."""
        groups: list[list] = []  # [run text, font index]
        for ch in _IGNORABLE.sub("", text):
            i = next((i for i, (_, cmap) in enumerate(self._fonts) if ord(ch) in cmap), None)
            if i is None:
                raise LayoutError(f"no font has {ch!r} (U+{ord(ch):04X}) in word {text!r}")
            if groups and groups[-1][1] == i:
                groups[-1][0] += ch
            else:
                groups.append([ch, i])
        return [(run, i, self._fitted(run, i)) for run, i in groups]

    def runs(self, text: str) -> list[tuple[str, ImageFont.FreeTypeFont]]:
        return [(run, font) for run, _, font in self._runs(text)]

    def units(self, text: str) -> list[tuple[str, int, ImageFont.FreeTypeFont, float]]:
        """The word as tracked units: (string, font index, font, x at pad 0). Each Latin
        character of the primary font is a unit; any other run stays one unit, so emoji
        sequences and Devanagari are never pulled apart. Units sit `tracking` px apart; kerning
        inside a run is kept (research §4: x_i = len(run[:i+1]) − len(run[i]))."""
        out, pen = [], 0.0
        for run, i, font in self._runs(text):
            segs: list[list] = []   # [string, offset in run]
            for j, ch in enumerate(run):
                if i == 0 and (_latin(ch) or not segs or _latin(run[j - 1])):
                    segs.append([ch, j])
                elif segs:
                    segs[-1][0] += ch
                else:
                    segs.append([ch, j])
            for seg, j in segs:
                x = pen + font.getlength(run[:j + len(seg)]) - font.getlength(seg)
                out.append((seg, i, font, x + self.tracking * len(out)))
            pen += font.getlength(run)
        return out

    def typeable(self, text: str) -> bool:
        """Whether the typewriter can type the word letter by letter: every unit is one Latin
        character drawn by the primary font."""
        units = self.units(text)
        return bool(units) and all(len(s) == 1 and i == 0 and _latin(s) for s, i, _, _ in units)

    def advance(self, text: str) -> float:
        if not self.tracking:
            return sum((font.getlength(run) for run, font in self.runs(text)), 0.0)
        units = self.units(text)
        return units[-1][3] + units[-1][2].getlength(units[-1][0]) if units else 0.0

    def _fitted(self, run: str, i: int) -> ImageFont.FreeTypeFont:
        """Font i at this size, or the largest smaller size at which the run's ink stays inside
        the box vertically.

        The primary's ascent/descent box is tighter than some glyphs: emoji, Devanagari matras
        and accented capitals rise above it (😊 by 9 px at 84 px). Shrinking just that run keeps
        all ink inside the box at any pad, so sprites never clip and rows never touch. Plain
        Hinglish is never shrunk (among ASCII only brackets and "|" overflow).
        """
        font, size = self._fonts[i][0], self.size
        while True:
            _, top, _, bottom = font.getbbox(run, anchor="ls")
            if (-top <= self.ascent and bottom <= self.descent) or size == 1:
                return font
            size = max(1, math.floor(size * min(self.ascent / max(-top, 1),
                                                self.descent / max(bottom, 1))))
            if (i, size) not in self._shrunk:
                self._shrunk[i, size] = font.font_variant(size=size)
            font = self._shrunk[i, size]


@lru_cache(maxsize=None)
def font_set(theme: Theme, size: int) -> FontSet:
    return FontSet(theme, size)


def word_fonts(theme: Theme, size: int, emphasis: bool) -> FontSet:
    """The fonts a word of a line laid out at `size` is measured and drawn with: a *marked* word
    at emphasis_scale times the line's size, so the ratio holds when a long line shrinks."""
    return font_set(theme, round(size * theme.emphasis_scale) if emphasis else size)


def word_mask(text: str, fonts: FontSet, pad: int = 0, stroke: int = 0) -> Image.Image:
    """The word's ink as an "L" mask, (ceil(advance) + 2·pad) × (ascent + descent + 2·pad), with
    the baseline at pad + ascent. The mask that measures a word (pad=0) is the one that draws it.

    Vertically all ink is inside the box (FontSet._fitted). Side bearings can put ink slightly
    left of 0 or right of the advance (1 px for the "f" of "saaf"); only a pad keeps that.
    stroke > 0: the glyphs plus an outline that many px wide (a theme's stroke layer), same size;
    the caller keeps pad ≥ stroke.
    """
    mask = Image.new("L", (math.ceil(fonts.advance(text)) + 2 * pad,
                           fonts.ascent + fonts.descent + 2 * pad), 0)
    draw = ImageDraw.Draw(mask)
    outline = {"stroke_width": stroke, "stroke_fill": 255} if stroke else {}
    if fonts.tracking:   # the same units and x that FontSet.advance measured
        for unit, _, font, x in fonts.units(text):
            draw.text((pad + x, pad + fonts.ascent), unit, font=font, fill=255, anchor="ls",
                      **outline)
        return mask
    x = float(pad)
    for run, font in fonts.runs(text):
        draw.text((x, pad + fonts.ascent), run, font=font, fill=255, anchor="ls", **outline)
        x += font.getlength(run)
    return mask


# --- Line layout (plan §4) -----------------------------------------------------------------------
Item = tuple[int, str, float]  # (words.json "i", text, advance)


def layout_line(words: list[tuple[int, str]], line: int, theme: Theme,
                emphasis: frozenset[int] = frozenset()) -> LineLayout:
    """Wrap one lyric line into balanced, centred rows at the largest size, from font_size down
    to min_font_size in font_step steps, that gives ≤ max_rows rows of ≤ max_width px. Words whose
    index is in `emphasis` take word_fonts(..., True) space."""
    sizes = [*range(theme.font_size, theme.min_font_size, -theme.font_step), theme.min_font_size]
    for size in sizes:
        fonts = font_set(theme, size)
        try:
            items = [(i, text, word_fonts(theme, size, i in emphasis).advance(text))
                     for i, text in words]
        except LayoutError as exc:  # a missing glyph: no size fixes that
            raise LayoutError(f"line {line + 1}: {exc}") from None
        rows = _wrap(items, fonts.space, theme.max_width)
        if rows is not None and len(rows) <= theme.max_rows:
            rows = _balance(rows, fonts.space, theme.max_width)
            return LineLayout(line, size, _place(rows, theme, line, size, emphasis))

    size = theme.min_font_size
    wide = [text for i, text in words
            if math.ceil(word_fonts(theme, size, i in emphasis).advance(text)) > theme.max_width]
    why = (f"the word {wide[0]!r} is wider than {theme.max_width} px" if wide
           else f"it needs more than {theme.max_rows} rows of {theme.max_width} px")
    raise LayoutError(f"line {line + 1} does not fit even at {theme.min_font_size} px: {why}")


def _offsets(row: list[Item], space: float) -> list[int]:
    """Each word's x from its row's left edge: preceding advances plus one space per gap."""
    xs, pen = [], 0.0
    for _, _, advance in row:
        xs.append(round(pen))
        pen += advance + space
    return xs


def _row_width(row: list[Item], space: float) -> int:
    return _offsets(row, space)[-1] + math.ceil(row[-1][2])


def _wrap(items: list[Item], space: float, max_width: int) -> list[list[Item]] | None:
    """Greedy rows; None if a single word is wider than max_width."""
    rows: list[list[Item]] = []
    for item in items:
        if rows and _row_width(rows[-1] + [item], space) <= max_width:
            rows[-1].append(item)
        elif _row_width([item], space) <= max_width:
            rows.append([item])
        else:
            return None
    return rows


def _balance(rows: list[list[Item]], space: float, max_width: int) -> list[list[Item]]:
    """Greedy's row count, but the split with the narrowest widest row (ties: the widest
    narrowest row), so a line never ends on a lone word: "Ek chaand ka tukda rehta / hai"
    becomes "Ek chaand ka / tukda rehta hai". At most max_rows rows, so brute force is tiny."""
    if len(rows) < 2:
        return rows
    items = [item for row in rows for item in row]
    best, best_key = rows, None
    for cuts in itertools.combinations(range(1, len(items)), len(rows) - 1):
        split = [items[a:b] for a, b in zip((0, *cuts), (*cuts, len(items)))]
        widths = [_row_width(row, space) for row in split]
        key = (max(widths), -min(widths))
        if max(widths) <= max_width and (best_key is None or key < best_key):
            best, best_key = split, key
    return best


def _place(rows: list[list[Item]], theme: Theme, line: int, size: int,
           emphasis: frozenset[int]) -> tuple[WordBox, ...]:
    """Each row centred on theme.center_x, its words on one baseline; the block of rows centred at
    anchor_y · height. A row is as tall as its tallest word; the gap between rows is the plain
    row pitch minus a plain word's height, so rows without marked words sit exactly as before."""
    fonts = font_set(theme, size)
    h = fonts.ascent + fonts.descent
    gap = round(h * theme.row_spacing) - h
    row_fonts = [[word_fonts(theme, size, i in emphasis) for i, _, _ in row] for row in rows]
    ascents = [max(f.ascent for f in fs) for fs in row_fonts]
    heights = [a + max(f.descent for f in fs) for a, fs in zip(ascents, row_fonts)]
    y = round(theme.anchor_y * theme.height - (sum(heights) + gap * (len(rows) - 1)) / 2)
    boxes = []
    for row, fs, ascent, height in zip(rows, row_fonts, ascents, heights):
        left = (2 * theme.center_x - _row_width(row, fonts.space)) // 2   # 540: as (width − w) // 2
        boxes += [WordBox(i, text, left + x, y + ascent - f.ascent, math.ceil(advance),
                          f.ascent + f.descent, i in emphasis)
                  for (i, text, advance), x, f in zip(row, _offsets(row, fonts.space), fs)]
        y += height + gap
    if any(b.x < 0 or b.y < 0 or b.x + b.w > theme.width or b.y + b.h > theme.height
           for b in boxes):
        raise LayoutError(f"line {line + 1} does not fit on the {theme.width}x{theme.height} "
                          "canvas; check the theme's layout box")
    return tuple(boxes)
