"""Tests for lyric_engine.layout: font fallback, word masks, wrapping, font shrink and refusals.

Offline and song-free (the khidki lines are copied in below); uses the Windows fonts the theme
names. Run: venv/Scripts/python -m unittest tests.test_layout -v
"""
from __future__ import annotations

import math
import unittest
from dataclasses import replace
from itertools import combinations, product
from pathlib import Path

from PIL import ImageFont

from lyric_engine.layout import (
    FontSet, LayoutError, LineLayout, WordBox, font_set, layout_line, word_mask,
)
from lyric_engine.theme import (
    BEAT_POP, CINEMATIC, FONTS, LOFI_MINIMAL, LOFI_TYPEWRITER, POP_KARAOKE,
    SOFT_ROMANTIC as THEME, SOFT_ROMANTIC_V2,
)

# songs/khidki/lyrics.txt is gitignored; its 8 lines, verbatim
KHIDKI = [
    "Mere saamne waali khidki mein",
    "Ek chaand ka tukda rehta hai",
    "Mere saamne waali khidki mein",
    "Ek chaand ka tukda rehta hai",
    "Afsos ye hai ke vo hamse",
    "Kuchh ukhda ukhda rehta hai",
    "Mere saamne waali khidki mein",
    "Ek chaand ka tukda rehta hai",
]
LONG_LINE = "Mere saamne waali khidki mein ek chaand ka tukda rehta hai afsos ye hai"
# Longest line Pop Karaoke's wide font (and lofi's tracked one) still fits in 3 rows with a 2x
# word (they shrink to their smallest size)
MEDIUM_LINE = "Mere saamne waali khidki mein ek chaand ka tukda rehta hai"
LONG_FOR = {"soft-romantic": LONG_LINE, "soft-romantic-v2": LONG_LINE, "pop-karaoke": MEDIUM_LINE,
            "lofi-minimal": MEDIUM_LINE, "lofi-typewriter": MEDIUM_LINE, "cinematic": MEDIUM_LINE,
            "beat-pop": MEDIUM_LINE}
ALL_THEMES = (THEME, SOFT_ROMANTIC_V2, POP_KARAOKE, LOFI_MINIMAL, LOFI_TYPEWRITER, CINEMATIC,
              BEAT_POP)
FALLBACK_LINE = "dil😊 kuchh🥰 ❤\ufe0f कुछ दिल Öl saaf"
NO_FONT = "\ufdd0"  # a noncharacter: never assigned, in none of the theme's five fonts
MISSING = Path("C:/no/such/font.ttf")
SIZES = [*range(THEME.font_size, THEME.min_font_size - 1, -THEME.font_step)]


def indexed(line: str, first: int = 0) -> list[tuple[int, str]]:
    """(words.json "i", text) pairs, the way render groups a line's words."""
    return [(first + n, token) for n, token in enumerate(line.split())]


def rows_of(layout: LineLayout) -> list[list[WordBox]]:
    by_y: dict[int, list[WordBox]] = {}
    for box in layout.words:
        by_y.setdefault(box.y, []).append(box)
    return [by_y[y] for y in sorted(by_y)]


def runs_by_file(fonts: FontSet, text: str) -> list[tuple[str, str]]:
    return [(run, Path(font.path).name) for run, font in fonts.runs(text)]


class FontSetTest(unittest.TestCase):
    def setUp(self) -> None:
        self.fonts = font_set(THEME, THEME.font_size)

    def test_metrics_and_space_come_from_the_primary_font(self):
        primary = ImageFont.truetype(str(THEME.font), THEME.font_size)
        self.assertEqual((self.fonts.ascent, self.fonts.descent), primary.getmetrics())
        self.assertEqual(self.fonts.space, primary.getlength(" "))
        self.assertIs(font_set(THEME, THEME.font_size), self.fonts)

    def test_plain_hinglish_is_one_primary_run_at_every_size(self):
        words = {w for line in [*KHIDKI, LONG_LINE] for w in line.split()}
        for size in SIZES:
            fonts = font_set(THEME, size)
            for word in words:
                with self.subTest(size=size, word=word):
                    [(run, font)] = fonts.runs(word)
                    self.assertEqual((run, Path(font.path).name, font.size),
                                     (word, "Candarab.ttf", size))

    def test_each_character_goes_to_the_first_font_that_has_it(self):
        cases = {
            # Segoe UI Symbol precedes Segoe UI Emoji in the theme and has the older emoji
            "dil😊": [("dil", "Candarab.ttf"), ("😊", "seguisym.ttf")],
            "dil🥰": [("dil", "Candarab.ttf"), ("🥰", "seguiemj.ttf")],
            "क": [("क", "Nirmala.ttc")],
            "dilक": [("dil", "Candarab.ttf"), ("क", "Nirmala.ttc")],
            "ghaṭ": [("gha", "Candarab.ttf"), ("ṭ", "seguisb.ttf")],
        }
        for text, expected in cases.items():
            with self.subTest(text=text):
                self.assertEqual(runs_by_file(self.fonts, text), expected)

    def test_invisible_characters_are_not_drawn(self):
        # Phones type the heart as U+2764 U+FE0F; Segoe UI Emoji's VS16 glyph is a 115 px blank.
        self.assertEqual(runs_by_file(self.fonts, "❤\ufe0f"), [("❤", "seguisym.ttf")])
        self.assertEqual(self.fonts.advance("❤\ufe0f"), self.fonts.advance("❤"))
        self.assertEqual(runs_by_file(self.fonts, "dil\u200dse"), [("dilse", "Candarab.ttf")])

    def test_character_no_font_has_raises_naming_it_and_the_word(self):
        calls = {"runs": self.fonts.runs, "advance": self.fonts.advance,
                 "word_mask": lambda text: word_mask(text, self.fonts)}
        for name, call in calls.items():
            with self.subTest(call=name):
                with self.assertRaises(LayoutError) as ctx:
                    call("dil" + NO_FONT)
                self.assertIn("U+FDD0", str(ctx.exception))
                self.assertIn(repr("dil" + NO_FONT), str(ctx.exception))

    def test_missing_primary_raises_and_missing_fallback_is_skipped(self):
        with self.assertRaisesRegex(LayoutError, "font not found"):
            FontSet(replace(THEME, font=MISSING), THEME.font_size)
        theme = replace(THEME, fallback_fonts=(MISSING, FONTS / "seguiemj.ttf"))
        fonts = FontSet(theme, THEME.font_size)
        self.assertEqual(runs_by_file(fonts, "🥰"), [("🥰", "seguiemj.ttf")])
        with self.assertRaisesRegex(LayoutError, r"U\+0915"):  # Nirmala UI is not in this set
            fonts.runs("क")


class WordMaskTest(unittest.TestCase):
    TEXTS = ["Mere", "saaf", "dil😊", "🥰", "❤\ufe0f", "कुछ", "दिल", "हूँ", "Öl", "|"]

    def setUp(self) -> None:
        self.fonts = font_set(THEME, THEME.font_size)

    def test_size_is_ceil_advance_by_box_height_plus_pad(self):
        f = self.fonts
        for text in self.TEXTS:
            for pad in (0, 7, 48):
                with self.subTest(text=text, pad=pad):
                    mask = word_mask(text, f, pad)
                    self.assertEqual(mask.mode, "L")
                    self.assertEqual(mask.size, (math.ceil(f.advance(text)) + 2 * pad,
                                                 f.ascent + f.descent + 2 * pad))

    def test_padding_only_moves_the_word(self):
        # The mask that measures a word (pad=0) is the mask that draws it (plan decision 4).
        for text in self.TEXTS:
            with self.subTest(text=text):
                bare, padded = word_mask(text, self.fonts), word_mask(text, self.fonts, pad=48)
                inner = padded.crop((48, 48, 48 + bare.width, 48 + bare.height))
                self.assertEqual(inner.tobytes(), bare.tobytes())

    def test_ink_never_leaves_the_box_vertically(self):
        # Emoji, Devanagari matras and accented capitals rise above Candara's ascent at full
        # size; their runs are drawn smaller instead, so nothing is cut off at any pad.
        f, pad = self.fonts, 40
        for text in self.TEXTS:
            with self.subTest(text=text):
                mask = word_mask(text, f, pad)
                _, top, _, bottom = mask.getbbox()
                self.assertGreaterEqual(top, pad)
                self.assertLessEqual(bottom, pad + f.ascent + f.descent)
                self.assertEqual(mask.getextrema()[1], 255)
        [(_, emoji)] = f.runs("😊")
        self.assertLess(emoji.size, THEME.font_size)


class LayoutLineTest(unittest.TestCase):
    def test_balanced_rows_no_lone_last_word(self):
        # greedy put "hai" alone on row 2 of this line; balanced wrap splits it evenly
        for line in KHIDKI:
            rows = rows_of(layout_line(indexed(line), 0, THEME))
            if len(rows) > 1:
                self.assertGreater(len(rows[-1]), 1, f"lone last word in {line!r}")
        rows = rows_of(layout_line(indexed("Ek chaand ka tukda rehta hai"), 0, THEME))
        widths = [row[-1].x + row[-1].w - row[0].x for row in rows]
        self.assertLess(max(widths) - min(widths), THEME.max_width // 3)

    def assert_well_placed(self, layout: LineLayout, words: list[tuple[int, str]]) -> None:
        """Text and order kept, rows within limits, boxes = masks, inside the canvas, apart."""
        fonts = font_set(THEME, layout.font_size)
        self.assertEqual([(b.index, b.text) for b in layout.words], words)
        rows = rows_of(layout)
        self.assertLessEqual(len(rows), THEME.max_rows)
        for row in rows:
            self.assertLessEqual(row[-1].x + row[-1].w - row[0].x, THEME.max_width)
        for b in layout.words:
            self.assertEqual((b.w, b.h), word_mask(b.text, fonts).size)
            self.assertTrue(0 <= b.x and b.x + b.w <= THEME.width
                            and 0 <= b.y and b.y + b.h <= THEME.height, b)
        for a, b in combinations(layout.words, 2):
            apart = (a.x + a.w <= b.x or b.x + b.w <= a.x
                     or a.y + a.h <= b.y or b.y + b.h <= a.y)
            self.assertTrue(apart, f"{a} overlaps {b}")

    def test_khidki_lines_fit_at_full_size(self):
        first = 0
        for n, line in enumerate(KHIDKI):
            with self.subTest(line=n + 1):
                words = indexed(line, first)
                first += len(words)
                layout = layout_line(words, n, THEME)
                self.assertEqual((layout.line, layout.font_size), (n, THEME.font_size))
                self.assert_well_placed(layout, words)

    def test_fallback_words_keep_the_box_contract(self):
        words = indexed(FALLBACK_LINE)
        self.assert_well_placed(layout_line(words, 0, THEME), words)

    def test_long_line_shrinks_the_font(self):
        words = indexed(LONG_LINE)
        self.assertEqual(len(words), 14)
        layout = layout_line(words, 0, THEME)
        self.assertIn(layout.font_size, SIZES[1:])
        self.assert_well_placed(layout, words)
        with self.assertRaisesRegex(LayoutError, "rows"):  # full size alone does not fit
            layout_line(words, 0, replace(THEME, min_font_size=THEME.font_size))

    def test_size_lays_out_at_exactly_that_size(self):
        """A Cinematic couplet shares one size (plan 10 §2.4); no size = today's ladder."""
        words = indexed(KHIDKI[0])
        free = layout_line(words, 0, THEME)
        self.assertEqual(layout_line(words, 0, THEME, size=free.font_size), free)
        self.assertEqual(layout_line(words, 0, THEME, size=60).font_size, 60)
        with self.assertRaisesRegex(LayoutError, r"does not fit even at 84 px: .*rows"):
            layout_line(indexed(LONG_LINE), 0, THEME, size=84)

    def test_rows_and_block_are_centred(self):
        for line in [*KHIDKI[:2], KHIDKI[4], LONG_LINE, FALLBACK_LINE]:
            with self.subTest(line=line):
                layout = layout_line(indexed(line), 0, THEME)
                fonts = font_set(THEME, layout.font_size)
                rows = rows_of(layout)
                for row in rows:
                    left, right = row[0].x, THEME.width - (row[-1].x + row[-1].w)
                    self.assertLessEqual(abs(left - right), 1)
                h = fonts.ascent + fonts.descent
                pitch = round(h * THEME.row_spacing)
                self.assertEqual([r[0].y - rows[0][0].y for r in rows],
                                 [k * pitch for k in range(len(rows))])
                centre = (rows[0][0].y + rows[-1][0].y + h) / 2
                self.assertLessEqual(abs(centre - THEME.anchor_y * THEME.height), 1)

    def test_absurdly_long_word_raises_with_the_line_number(self):
        word = "khidki" * 30
        with self.assertRaisesRegex(LayoutError, r"^line 5 does not fit") as ctx:
            layout_line([(40, "Ek"), (41, word)], 4, THEME)
        self.assertIn(word, str(ctx.exception))

    def test_too_many_rows_raises_with_the_line_number(self):
        with self.assertRaisesRegex(LayoutError, r"^line 1 does not fit .* rows"):
            layout_line(indexed(" ".join(["khidki"] * 60)), 0, THEME)

    def test_missing_glyph_names_the_line(self):
        with self.assertRaisesRegex(LayoutError, r"^line 3: no font has .*U\+FDD0"):
            layout_line([(0, "chaand"), (1, "dil" + NO_FONT)], 2, THEME)


class TrackingTest(unittest.TestCase):
    """Spec 09: tracking is part of the word as measured and drawn; 0 changes nothing."""

    def test_tracking_zero_is_todays_measure(self):
        fonts = font_set(THEME, 84)
        self.assertEqual(fonts.tracking, 0)
        primary = ImageFont.truetype(str(THEME.font), 84)
        self.assertEqual(fonts.space, primary.getlength(" "))
        for text in [*" ".join(KHIDKI).split(), *FALLBACK_LINE.split()]:
            self.assertEqual(fonts.advance(text),
                             sum((f.getlength(r) for r, f in fonts.runs(text)), 0.0))

    def test_tracked_advance_adds_one_gap_per_unit(self):
        tracked, plain = font_set(LOFI_MINIMAL, 76), font_set(replace(LOFI_MINIMAL, tracking=0), 76)
        self.assertAlmostEqual(tracked.tracking, 7.6)
        self.assertAlmostEqual(tracked.space, plain.space + 2 * 7.6)
        for text in [*" ".join(KHIDKI).split(), *FALLBACK_LINE.split()]:
            with self.subTest(text):
                gaps = len(tracked.units(text)) - 1
                self.assertAlmostEqual(tracked.advance(text), plain.advance(text) + 7.6 * gaps,
                                       places=6)

    def test_drawn_mask_is_the_measured_mask(self):
        for size in (76, 114):   # a line size and a 1.5x marked word
            fonts = font_set(LOFI_MINIMAL, size)
            for text in [*" ".join(KHIDKI).split(), *FALLBACK_LINE.split()]:
                mask = word_mask(text, fonts)
                self.assertEqual(mask.size, (math.ceil(fonts.advance(text)),
                                             fonts.ascent + fonts.descent), text)
                self.assertIsNotNone(mask.getbbox(), text)
        lay = layout_line(indexed(KHIDKI[0]), 0, LOFI_MINIMAL)
        fonts = font_set(LOFI_MINIMAL, lay.font_size)
        for box in lay.words:
            self.assertEqual((box.w, box.h), word_mask(box.text, fonts).size)

    def test_units_split_latin_letters_only(self):
        fonts = font_set(LOFI_MINIMAL, 76)
        units = lambda text: [u for u, _, _, _ in fonts.units(text)]
        self.assertEqual(units("Öl,"), ["Ö", "l", ","])
        self.assertEqual(units("dil😊"), ["d", "i", "l", "😊"])
        self.assertEqual(units("❤️"), ["❤"])            # the ignorable VS16 is not drawn
        self.assertEqual(units("👍🏽"), ["👍🏽"])               # a skin-tone sequence stays whole
        self.assertEqual(units("कुछ"), ["कुछ"])
        xs = [x for _, _, _, x in fonts.units("dekha")]
        self.assertEqual(xs, sorted(xs))

    def test_typeable(self):
        fonts = font_set(LOFI_TYPEWRITER, 76)
        for text in ("dekha", "hain,", "Öl"):
            self.assertTrue(fonts.typeable(text), text)
        for text in ("dil😊", "कुछ", "❤️"):
            self.assertFalse(fonts.typeable(text), text)


class EmphasisLayoutTest(unittest.TestCase):
    """H-013: a *marked* word is 1.5x-2x its line's other words, and the layout makes room."""

    def test_rule_is_enforced_by_the_theme(self):
        for scale in (1.5, 1.75, 2.0):
            replace(THEME, emphasis_scale=scale)
        for scale in (1.06, 1.49, 2.01, 3.0):
            with self.subTest(scale), self.assertRaisesRegex(ValueError, "H-013"):
                replace(THEME, emphasis_scale=scale)

    def test_marked_word_is_scale_times_the_line_size_even_when_shrunk(self):
        for scale, base in product((1.5, 2.0), ALL_THEMES):
            theme = replace(base, emphasis_scale=scale)
            for line in ("Jis roz se dekha hai usko", LONG_FOR[base.name]):
                words = indexed(line)
                lay = layout_line(words, 0, theme, emphasis=frozenset({3}))
                big = font_set(theme, round(lay.font_size * scale))
                box = next(b for b in lay.words if b.index == 3)
                self.assertTrue(box.emphasis)
                self.assertEqual((box.w, box.h), word_mask(box.text, big).size)
                plain = [b for b in lay.words if b.index != 3]
                self.assertFalse(any(b.emphasis for b in plain))
                fonts = font_set(theme, lay.font_size)
                self.assertTrue(all(b.h == fonts.ascent + fonts.descent for b in plain))

    def test_rows_share_a_baseline_and_nothing_overlaps(self):
        for scale, base in product((1.5, 2.0), ALL_THEMES):
            theme = replace(base, emphasis_scale=scale)
            for line in [*KHIDKI, LONG_FOR[base.name]]:
                words = indexed(line)
                marked = frozenset({0, len(words) // 2})
                lay = layout_line(words, 0, theme, emphasis=marked)
                small = font_set(theme, lay.font_size)
                big = font_set(theme, round(lay.font_size * scale))
                base = {b.index: b.y + (big if b.emphasis else small).ascent for b in lay.words}
                rows: dict[int, list[WordBox]] = {}
                for b in lay.words:
                    rows.setdefault(base[b.index], []).append(b)
                self.assertLessEqual(len(rows), theme.max_rows)
                for row in rows.values():
                    row.sort(key=lambda b: b.x)
                    for a, b in zip(row, row[1:]):
                        self.assertLessEqual(a.x + a.w, b.x, (line, a.text, b.text))
                for a, b in combinations(lay.words, 2):
                    if base[a.index] != base[b.index]:
                        self.assertTrue(a.y + a.h <= b.y or b.y + b.h <= a.y, (line, a, b))
                self.assertTrue(all(0 <= b.x and b.x + b.w <= theme.width for b in lay.words))

    def test_no_marks_lays_out_exactly_as_before(self):
        for line in [*KHIDKI, LONG_LINE]:
            words = indexed(line)
            self.assertEqual(layout_line(words, 0, THEME, emphasis=frozenset()),
                             layout_line(words, 0, THEME))


class CenterXTest(unittest.TestCase):
    """Rows centre on theme.center_x: 540 for Soft Romantic, 510 for Pop Karaoke (spec 07 §4.6)."""

    def test_rows_centre_on_the_theme_centre(self):
        for theme in (THEME, POP_KARAOKE):
            for line in KHIDKI[:2]:
                for row in rows_of(layout_line(indexed(line), 0, theme)):
                    centre = (row[0].x + row[-1].x + row[-1].w) / 2
                    self.assertLessEqual(abs(centre - theme.center_x), 1, (theme.name, line))


if __name__ == "__main__":
    unittest.main()
