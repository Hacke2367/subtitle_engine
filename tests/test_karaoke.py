"""render/karaoke.py (Pop Karaoke, spec 07): fill timing, line life cycle, sprites, frames, the
theme guard, the CLI choice, and short end-to-end renders with the fill and safe-zone checks.

Timeline tests use hand-made layouts (no fonts). Sprite, frame and render tests use the bundled
Poppins and a short real ffmpeg encode (qtrle, the fast codec).
"""
from __future__ import annotations

import contextlib
import hashlib
import io
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path

from PIL import Image, ImageChops, ImageStat

from lyric_engine import cli, layout, render, timing
from lyric_engine.layout import LineLayout, WordBox
from lyric_engine.render import karaoke
from lyric_engine.render.karaoke import (FillWord, KaraokeLine, fill_progress, line_state,
                                         plan_karaoke)
from lyric_engine.theme import POP_KARAOKE as THEME
from lyric_engine.theme import SOFT_ROMANTIC, THEMES
from tests.test_render import make_song, word

E, P, H, X = 9, 15, 30, 6   # enter, preroll, hold, exit fade in frames at 30 fps (lead 0.05 s)


def low_layout(words, line, theme, emphasis=frozenset()):
    """One row of 100x80 boxes at y 1000: any line fits in the past slot above another."""
    return LineLayout(line, theme.font_size, tuple(
        WordBox(i, text, 200 + 120 * k, 1000, 100, 80) for k, (i, text) in enumerate(words)))


def high_layout(words, line, theme, emphasis=frozenset()):
    """Boxes near the top of the safe zone: a past slot above would leave it."""
    return LineLayout(line, theme.font_size, tuple(
        WordBox(i, text, 200 + 120 * k, 420, 100, 80) for k, (i, text) in enumerate(words)))


def t(frame: int) -> float:
    """A words.json time that lands on this frame after the 0.05 s lead."""
    return round(frame / 30 + 0.05, 4)


def lines_of(*spans, layout_fn=low_layout, n_frames=900):
    """One line per (first, last) frame pair, one word each: start first, end last."""
    words = [word(k, f"w{k}", k, t(a), t(b)) for k, (a, b) in enumerate(spans)]
    return plan_karaoke({"words": words}, THEME, n_frames, layout_fn=layout_fn)[0]


def visible(lines, n):
    return [kl for kl in lines if kl.enter <= n < kl.stop]


class ThemeTest(unittest.TestCase):
    def test_both_themes_are_offered(self):
        self.assertEqual(list(THEMES), ["soft-romantic", "pop-karaoke"])
        self.assertTrue(Path(THEME.font).is_file(), "Poppins must be bundled in fonts/")

    def test_key_green_colours_are_refused(self):  # AC8
        for field, rgb in (("accent_rgb", (0, 255, 0)), ("text_rgb", (40, 200, 60)),
                           ("stroke_rgb", (0, 120, 0))):
            with self.subTest(field), self.assertRaisesRegex(ValueError, f"{field}.*key green"):
                replace(THEME, **{field: rgb})
        with self.assertRaisesRegex(ValueError, "glow_rgb"):
            replace(SOFT_ROMANTIC, glow_rgb=(0, 255, 0))
        replace(THEME, accent_rgb=(31, 184, 166))   # teal, the research's safe "green"
        replace(THEME, accent_rgb=(232, 255, 71))   # lime-yellow

    def test_karaoke_needs_its_colours_and_a_known_motion(self):
        with self.assertRaisesRegex(ValueError, "accent_rgb and stroke_rgb"):
            replace(THEME, accent_rgb=None)
        with self.assertRaisesRegex(ValueError, "motion"):
            replace(THEME, motion="bounce")


class FillProgressTest(unittest.TestCase):  # AC3
    box = WordBox(0, "a", 0, 0, 10, 10)

    def test_zero_before_start_one_from_end_linear_between(self):
        fw = FillWord(self.box, "a", 10, 20)
        self.assertEqual([fill_progress(fw, n) for n in (0, 9, 10, 15, 20, 30)],
                         [0.0, 0.0, 0.0, 0.5, 1.0, 1.0])

    def test_word_shorter_than_a_frame_fills_in_one_frame(self):
        fw = FillWord(self.box, "a", 10, 10)
        self.assertEqual((fill_progress(fw, 9), fill_progress(fw, 10)), (0.0, 1.0))

    def test_untimed_word_never_fills(self):
        fw = FillWord(self.box, "a", None, None)
        self.assertTrue(all(fill_progress(fw, n) == 0.0 for n in range(100)))

    def test_frames_come_from_the_words_own_times(self):  # red line 1
        doc = {"words": [word(0, "Mere", 0, 1.05, 1.55), word(1, "saamne", 0, None, None)]}
        (kl,), _ = plan_karaoke(doc, THEME, 300, layout_fn=low_layout)
        self.assertEqual([(f.start, f.end) for f in kl.words], [(30, 45), (None, None)])


class PlanKaraokeTest(unittest.TestCase):  # AC4
    def test_line_enters_preroll_ahead_and_is_at_rest_before_its_fill(self):
        (kl,) = lines_of((60, 75))
        self.assertEqual((kl.enter, kl.rest), (60 - P, 60 - P + E))
        self.assertLessEqual(kl.rest, kl.first_fill - 1)
        self.assertEqual((kl.handover, kl.fade_start, kl.stop), (None, 75 + H, 75 + H + X))

    def test_next_line_waits_for_the_previous_last_word(self):
        a, b = lines_of((40, 90), (105, 120))
        self.assertEqual(b.enter, 91)
        self.assertEqual(a.handover, 91)

    def test_back_to_back_lines_still_rest_before_the_fill(self):
        a, b = lines_of((40, 90), (93, 110))
        self.assertEqual((b.enter, b.rest), (93 - E - 1, 92))
        self.assertLess(a.handover, a.last_end)   # its last word fills on in the past slot

    def test_first_word_at_zero_is_shown_at_rest_from_frame_zero(self):
        (kl,) = lines_of((1, 20))
        self.assertEqual((kl.enter, kl.rest), (0, 0))
        self.assertEqual(line_state(kl, 0, THEME), (1.0, 0.0, 1.0))

    def test_instrumental_gap_clears_the_screen(self):
        a, b = lines_of((40, 90), (300, 320))
        self.assertIsNone(a.handover)
        self.assertEqual((a.fade_start, a.stop), (90 + H, 90 + H + X))
        self.assertLess(a.stop, b.enter)

    def test_past_line_leaves_as_the_line_after_next_enters(self):
        a, b, c = lines_of((40, 60), (75, 95), (110, 130))
        self.assertTrue(a.past)
        self.assertEqual(a.stop, c.enter)
        self.assertEqual(a.fade_start, max(a.handover, c.enter - X))

    def test_past_line_fades_with_a_clearing_line(self):
        a, b = lines_of((40, 60), (75, 95))
        self.assertEqual((a.fade_start, a.stop), (b.fade_start, b.stop))

    def test_past_line_that_does_not_fit_fades_in_place(self):
        a, b = lines_of((40, 60), (75, 95), layout_fn=high_layout)
        self.assertFalse(a.past)
        self.assertEqual((a.fade_start, a.stop), (a.handover, a.handover + X))

    def test_never_more_than_two_lines_on_screen(self):
        spans = [(5, 12), (20, 26), (30, 60), (62, 64), (66, 90), (91, 92), (93, 150),
                 (400, 430), (431, 440), (445, 500), (520, 521), (522, 523), (524, 600)]
        lines = lines_of(*spans)
        self.assertTrue(all(len(visible(lines, n)) <= 2 for n in range(900)))
        for kl in lines:
            self.assertLess(kl.enter, kl.stop)

    def test_line_without_a_timed_word_is_skipped(self):
        doc = {"words": [word(0, "a", 0, 1.0, 1.2), word(1, "b", 1, None, None)]}
        lines, skipped = plan_karaoke(doc, THEME, 300, layout_fn=low_layout)
        self.assertEqual(([kl.layout.line for kl in lines], skipped), ([0], [1]))

    def test_layout_must_keep_the_words_json_text(self):  # red line 2
        def lying(words, line, theme, emphasis=frozenset()):
            return low_layout([(i, text.upper()) for i, text in words], line, theme)
        with self.assertRaisesRegex(AssertionError, "layout of line 1"):
            plan_karaoke({"words": [word(0, "dil", 0, 1.0, 1.2)]}, THEME, 300, layout_fn=lying)


class LineStateTest(unittest.TestCase):  # AC4
    def test_entrance_overshoot_is_at_most_ten_percent(self):
        peak = max(karaoke.ease_out_back(k / 1000) for k in range(1001))
        self.assertLessEqual(peak, 1.1001)
        (kl,) = lines_of((60, 75))
        scales = [line_state(kl, n, THEME)[0] for n in range(kl.enter, kl.rest)]
        move = 1 - THEME.enter_scale
        self.assertAlmostEqual(scales[0], THEME.enter_scale)
        self.assertLessEqual(max(scales), 1 + 0.1 * move + 1e-9)
        self.assertEqual(line_state(kl, kl.rest, THEME), (1.0, 0.0, 1.0))

    def test_past_slot_values_after_the_handover(self):
        a, b, c = lines_of((40, 60), (75, 95), (200, 230))
        scale, dy, op = line_state(a, a.handover + E, THEME)
        self.assertAlmostEqual(scale, THEME.past_scale)
        self.assertAlmostEqual(op, THEME.past_opacity)
        self.assertAlmostEqual(dy, a.past_dy)
        self.assertLess(a.past_dy, 0)
        self.assertEqual(line_state(a, a.handover, THEME), (1.0, 0.0, 1.0))

    def test_exit_fade_and_off_screen(self):
        (kl,) = lines_of((60, 75))
        ops = [line_state(kl, n, THEME)[2] for n in range(kl.fade_start, kl.stop)]
        self.assertEqual(ops[0], 1.0)
        self.assertEqual(ops, sorted(ops, reverse=True))
        self.assertEqual(line_state(kl, kl.stop, THEME)[2], 0.0)
        self.assertEqual(line_state(kl, kl.enter - 1, THEME)[2], 0.0)


def real_lines(words, n_frames=120, emphasis=frozenset()):
    return plan_karaoke({"words": words}, THEME, n_frames, emphasis=emphasis)[0]


def frame(n, lines, sprites, cache=None):
    parts = karaoke.frame_parts(n, lines, sprites, THEME, cache or karaoke.LineCache())
    return Image.frombytes("RGBA", (THEME.width, THEME.height), b"".join(bytes(p) for p in parts))


def filled_share(img, fw, font_size):
    """Share of the word's solid glyph pixels in the accent colour (G channel: 255 vs 46)."""
    fonts = layout.word_fonts(THEME, font_size, fw.box.emphasis)
    ink = layout.word_mask(fw.text, fonts).point(lambda v: 255 if v == 255 else 0)
    b = fw.box
    g = ImageStat.Stat(img.getchannel("G").crop((b.x, b.y, b.x + b.w, b.y + b.h)), ink).mean[0]
    return (255 - g) / (255 - THEME.accent_rgb[1])


class SpritesAndFramesTest(unittest.TestCase):
    def setUp(self):
        self.lines = real_lines([word(0, "Mere", 0, t(30), t(45)), word(1, "saamne,", 0, None, None),
                                 word(2, "kuchh", 0, t(50), t(60))])
        self.sprites = karaoke.build_sprites(self.lines, THEME)

    def test_glyphs_share_one_alpha_and_match_the_box(self):  # AC7
        for fw in self.lines[0].words:
            under, base, hot, pad = self.sprites[fw.box.index]
            size = (fw.box.w + 2 * pad, fw.box.h + 2 * pad)
            self.assertEqual((under.size, base.size, hot.size), (size, size, size))
            self.assertEqual(base.getchannel("A").tobytes(), hot.getchannel("A").tobytes())
            self.assertEqual(base.convert("RGB").getcolors(), [(size[0] * size[1], THEME.text_rgb)])
            self.assertEqual(hot.convert("RGB").getcolors(), [(size[0] * size[1],
                                                               THEME.accent_rgb)])

    def test_text_mismatch_raises_before_drawing(self):  # red line 2
        kl = self.lines[0]
        bad = replace(kl, words=[replace(kl.words[0], text="MERE"), *kl.words[1:]])
        with self.assertRaisesRegex(AssertionError, "not the words.json text"):
            karaoke.build_sprites([bad], THEME)

    def test_stroke_mask_is_the_glyph_plus_an_outline(self):
        fonts = layout.word_fonts(THEME, THEME.font_size, False)
        glyph, outline = layout.word_mask("dil", fonts, 10), layout.word_mask("dil", fonts, 10, 4)
        self.assertEqual(glyph.size, outline.size)
        self.assertIsNone(ImageChops.subtract(glyph, outline).getbbox())   # covers every glyph px
        self.assertGreater(sum(outline.histogram()[1:]), sum(glyph.histogram()[1:]))

    def test_fill_starts_and_ends_on_the_words_own_frames(self):  # red line 1
        size = self.lines[0].layout.font_size
        mere, flagged, kuchh = self.lines[0].words
        self.assertLess(filled_share(frame(29, self.lines, self.sprites), mere, size), 0.02)
        self.assertGreater(filled_share(frame(45, self.lines, self.sprites), mere, size), 0.98)
        half = filled_share(frame(37, self.lines, self.sprites), mere, size)
        self.assertTrue(0.2 < half < 0.8, half)
        self.assertLess(filled_share(frame(49, self.lines, self.sprites), kuchh, size), 0.02)
        kl = self.lines[0]
        for n in range(kl.rest, kl.fade_start, 7):   # the untimed word never fills
            self.assertLess(filled_share(frame(n, self.lines, self.sprites), flagged, size), 0.02)

    def test_cached_frames_are_identical(self):
        cache = karaoke.LineCache()
        for n in (10, 37, 37, 60, 61):
            self.assertEqual(frame(n, self.lines, self.sprites, cache).tobytes(),
                             frame(n, self.lines, self.sprites).tobytes(), n)


class KaraokeRenderTest(unittest.TestCase):  # AC1, AC5
    def test_render_passes_its_checks_and_they_are_not_vacuous(self):
        with tempfile.TemporaryDirectory() as tmp:
            song = make_song(Path(tmp), times=((0.3, 0.6), (1.2, 1.6)))
            words_sha = hashlib.sha256((song / "words.json").read_bytes()).hexdigest()
            result = render.render(song, codec="qtrle", theme=THEME)
            self.assertEqual(result.checks, [])
            self.assertEqual(result.render_dir, song / "render" / "pop-karaoke")
            report = (result.render_dir / "report.md").read_text("utf-8")
            self.assertIn("Theme: pop-karaoke", report)
            self.assertIn("fill check of 2 timed word(s)", report)
            self.assertEqual(hashlib.sha256((song / "words.json").read_bytes()).hexdigest(),
                             words_sha)

            doc = timing.load_words(song / "words.json")
            lines, _ = plan_karaoke(doc, THEME, result.frames)
            late = [replace(kl, words=[replace(fw, start=fw.start + 10, end=fw.end + 10)
                                       for fw in kl.words]) for kl in lines]
            fails = render.check_outputs(result, late, THEME, result.frames)
            self.assertTrue(any(f.startswith("fill:") for f in fails), fails)
            tight = replace(THEME, safe_zone=(60, 380, 960, 1150))   # cuts through the text
            fails = render.check_outputs(result, lines, tight, result.frames)
            self.assertTrue(any(f.startswith("safe zone:") for f in fails), fails)


class CliThemeTest(unittest.TestCase):  # AC1
    def test_theme_choice_and_output_folders(self):
        with tempfile.TemporaryDirectory() as tmp:
            song = make_song(Path(tmp), times=((0.3, 0.6), (1.2, 1.6)))
            err = io.StringIO()
            with contextlib.redirect_stderr(err), self.assertRaises(SystemExit) as caught:
                cli.main(["render", str(song), "--theme", "nope"])
            self.assertEqual(caught.exception.code, 2)
            self.assertIn("invalid choice: 'nope'", err.getvalue())
            self.assertFalse((song / "render").exists())

            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                self.assertEqual(cli.main(["render", str(song), "--codec", "qtrle"]), 0)
                self.assertEqual(cli.main(["make", str(song), "--theme", "pop-karaoke",
                                           "--codec", "qtrle"]), 0)
            self.assertIn("using the existing alignment", out.getvalue())
            for name in ("soft-romantic", "pop-karaoke"):
                self.assertTrue((song / "render" / name / "overlay.mov").is_file(), name)


if __name__ == "__main__":
    unittest.main()
