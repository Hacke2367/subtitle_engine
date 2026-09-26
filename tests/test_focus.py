"""render/focus.py (Soft Romantic v2, spec 08): word frames equal v1's, the glow breath, the line
stack life cycle, frames, the CLI choice, and short end-to-end renders with the sync and
safe-zone checks.

Timeline tests use hand-made layouts (no fonts). Frame and render tests use v1's Windows fonts
and a short real ffmpeg encode (qtrle, the fast codec).
"""
from __future__ import annotations

import contextlib
import hashlib
import io
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path

from PIL import Image

from lyric_engine import cli, render, timing
from lyric_engine.layout import WordBox
from lyric_engine.render import focus
from lyric_engine.render.focus import REST, breath, line_state, plan_focus, word_look
from lyric_engine.render.timeline import WordPlan, word_state
from lyric_engine.theme import SOFT_ROMANTIC, SOFT_ROMANTIC_V2 as THEME
from tests.test_karaoke import high_layout, low_layout, t
from tests.test_render import make_song, word

E, L, H, X, REV = 11, 6, 30, 9, 6   # hand-over, lead, hold, exit, reveal in frames at 30 fps
W, HT = THEME.width, THEME.height


def lines_of(*spans, layout_fn=low_layout, n_frames=900):
    """One line per (first, last) frame pair, one word each: start first, end last."""
    words = [word(k, f"w{k}", k, t(a), t(b)) for k, (a, b) in enumerate(spans)]
    return plan_focus({"words": words}, THEME, n_frames, layout_fn=layout_fn)[0]


def visible(lines, n):
    return [fl for fl in lines if line_state(fl, n, THEME)[2] > 0]


def wp(reveal, end):
    return WordPlan(WordBox(0, "w", 0, 0, 10, 10), reveal, end, "w")


class ThemeTest(unittest.TestCase):
    def test_v2_is_v1s_look_inside_the_safe_zone(self):
        for name in ("font", "fallback_fonts", "font_size", "min_font_size", "text_rgb",
                     "glow_rgb", "glow_radius", "glow_boost", "shadow_rgb", "shadow_alpha",
                     "shadow_radius", "shadow_offset", "lead_s", "reveal_s", "rise_px",
                     "glow_in_s", "glow_out_s", "emphasis_scale", "anchor_y"):
            self.assertEqual(getattr(THEME, name), getattr(SOFT_ROMANTIC, name), name)
        self.assertEqual((THEME.motion, THEME.safe_zone, THEME.center_x),
                         ("focus", (60, 380, 960, 1540), 510))


class WordFramesTest(unittest.TestCase):  # AC3
    def test_reveal_and_end_frames_equal_v1s(self):
        words = [word(0, "a", 0, 0.03, 0.4), word(1, "b", 0, None, None, ("unaligned",)),
                 word(2, "c", 0, 0.51, 1.9), word(3, "d", 1, 2.0, 2.2), word(4, "e", 2, 9.3, 9.9)]
        doc = {"words": words}
        v1, _ = render.plan_timeline(doc, SOFT_ROMANTIC, 600, layout_fn=low_layout)
        v2, _ = plan_focus(doc, THEME, 600, layout_fn=low_layout)
        frames = lambda lines: {w.box.index: (w.reveal, w.end) for ln in lines for w in ln.words}
        self.assertEqual(frames(v2), frames(v1))
        untimed = next(w for ln in v2 for w in ln.words if w.reveal is None)
        for n in range(0, 600, 7):
            self.assertEqual(word_look(untimed, n, THEME), (1.0, 0.0, 0.0))
            self.assertEqual(breath(untimed, n, THEME), 1.0)


class BreathTest(unittest.TestCase):  # AC4
    def test_short_word_glows_exactly_as_v1(self):
        short = wp(30, 57)                       # 27 frames: 0.9 s
        for n in range(200):
            self.assertEqual(word_look(short, n, THEME), word_state(short, n, THEME))

    def test_threshold_is_the_words_own_frames(self):
        self.assertEqual(focus.held(wp(30, 60), THEME), True)
        self.assertEqual(focus.held(wp(30, 59), THEME), False)
        self.assertEqual(focus.held(wp(None, None), THEME), False)

    def test_held_word_breathes_inside_its_glow_window_only(self):
        held = wp(30, 90)                        # 2 s
        glow = [word_look(held, n, THEME)[2] for n in range(200)]
        breathing = glow[36:91]                  # glow full at 30 + ceil(0.18 * 30) = 36
        self.assertTrue(all(0.65 - 1e-9 <= g <= 1 for g in breathing), breathing)
        self.assertLess(min(breathing), 0.99)
        self.assertLessEqual(abs(glow[91] - glow[90]), 1 / 9 + 1e-9)   # one fade-out step
        self.assertEqual(glow[:30], [0.0] * 30)
        self.assertTrue(all(g == 0 for g in glow[99:]))
        for n in range(90, 99):                  # the fade-out starts from the frozen breath
            self.assertAlmostEqual(glow[n], word_state(held, n, THEME)[2] * glow[90])
        self.assertEqual([word_look(held, n, THEME)[:2] for n in range(200)],
                         [word_state(held, n, THEME)[:2] for n in range(200)])


class PlanFocusTest(unittest.TestCase):  # AC5
    def assert_invariants(self, lines, n_frames=900):
        for n in range(n_frames):
            self.assertLessEqual(len(visible(lines, n)), 2, n)
        for fl in lines:
            if fl.handover is not None:
                self.assertGreaterEqual(fl.handover, fl.last_reveal)
            self.assertEqual(line_state(fl, fl.first, THEME), REST)

    def test_hand_over_moves_the_line_into_the_past_slot(self):
        a, b = lines_of((30, 60), (80, 110))
        self.assert_invariants([a, b])
        self.assertEqual((a.handover, a.past, a.past_dy), (80 - L, True, -114))
        self.assertEqual(line_state(a, a.handover, THEME), REST)
        scale, dy, op, blur = line_state(a, a.handover + E, THEME)
        self.assertAlmostEqual(scale, 0.85)
        self.assertAlmostEqual(dy, -114)
        self.assertAlmostEqual(op, 0.4)
        self.assertAlmostEqual(blur, 6.0)
        self.assertEqual((b.fade_start, b.stop), (110 + H, 110 + H + X))   # b clears ...
        self.assertEqual((a.fade_start, a.stop), (b.fade_start, b.stop))  # ... and a with it

    def test_past_line_leaves_as_the_next_hand_over_starts(self):
        a, b, c = lines_of((30, 60), (80, 110), (130, 160))
        self.assert_invariants([a, b, c])
        self.assertEqual(a.stop, b.handover)
        self.assertEqual(a.fade_start, b.handover - X)

    def test_instrumental_gap_clears_the_screen(self):
        a, b = lines_of((30, 60), (200, 230))
        self.assert_invariants([a, b])
        self.assertIsNone(a.handover)
        self.assertEqual((a.fade_start, a.stop), (60 + H, 60 + H + X))
        self.assertEqual(visible([a, b], 150), [])

    def test_back_to_back_waits_for_the_last_word_to_start(self):
        words = [word(0, "a", 0, t(30), t(40)), word(1, "b", 0, t(78), t(90)),
                 word(2, "c", 1, t(80), t(95))]
        a, b = plan_focus({"words": words}, THEME, 900, layout_fn=low_layout)[0]
        self.assert_invariants([a, b])
        self.assertEqual(a.handover, 78)          # not 80 - 6: word b starts its reveal at 78
        self.assertEqual(word_look(a.words[1], 84, THEME), word_state(a.words[1], 84, THEME))

    def test_first_word_at_zero(self):
        (a,) = lines_of((0, 20))
        self.assertEqual(a.first, 0)
        self.assertEqual(line_state(a, 0, THEME), REST)

    def test_past_slot_that_does_not_fit_fades_and_blurs_in_place(self):
        a, b = lines_of((30, 60), (80, 110), layout_fn=high_layout)
        self.assert_invariants([a, b])
        self.assertFalse(a.past)
        self.assertEqual((a.fade_start, a.stop), (a.handover, a.handover + X))
        scale, dy, op, blur = line_state(a, a.handover + 6, THEME)
        self.assertEqual((scale, dy), (1.0, 0.0))
        self.assertTrue(0 < op < 1 and 0 < blur < 6)


def real_plan(words, n_frames=150):
    doc = {"words": words}
    return plan_focus(doc, THEME, n_frames)[0], render.plan_timeline(doc, THEME, n_frames)[0]


def frame(n, lines, sprites, cache=None):
    return b"".join(focus.frame_parts(n, lines, sprites, THEME, cache or focus.FocusCache()))


class FramesTest(unittest.TestCase):  # AC8, drawing
    def test_a_line_at_rest_draws_exactly_v1s_pixels(self):
        v2, v1 = real_plan([word(0, "Mere", 0, t(10), t(20)), word(1, "saamne", 0, t(24), t(40)),
                            word(2, "waali", 0, t(44), t(50))])
        sprites = render.build_sprites(v2, THEME)
        for n in range(0, 72, 3):             # v1 starts its fade at 73, v2 clears at 80
            self.assertEqual(frame(n, v2, sprites), render.compose_frame(n, v1, sprites, THEME), n)

    def test_the_past_line_is_dimmed_above_the_current_one(self):
        v2, _ = real_plan([word(0, "Mere", 0, t(10), t(20)), word(1, "saamne", 1, t(40), t(60))])
        a, b = v2
        sprites = render.build_sprites(v2, THEME)
        img = Image.frombytes("RGBA", (W, HT), frame(a.handover + E + 1, v2, sprites))
        top = min(w.box.y for w in b.words)
        above = img.getchannel("A").crop((0, 0, W, top - 20))
        self.assertGreater(above.getextrema()[1], 0)
        self.assertLessEqual(above.getextrema()[1], round(0.4 * 255) + 1)

    def test_cache_gives_identical_frames(self):
        v2, _ = real_plan([word(0, "Mere", 0, t(10), t(20)), word(1, "saamne", 1, t(40), t(80))])
        sprites, cache = render.build_sprites(v2, THEME), focus.FocusCache()
        for n in (12, 30, 36, 40, 45, 60, 45, 140):
            self.assertEqual(frame(n, v2, sprites, cache), frame(n, v2, sprites), n)

    def test_drawn_text_must_be_the_words_json_text(self):
        v2, _ = real_plan([word(0, "Mere", 0, t(10), t(20))])
        bad = [replace(v2[0], words=[replace(v2[0].words[0], text="Mere!")])]
        with self.assertRaisesRegex(AssertionError, "words.json text"):
            render.build_sprites(bad, THEME)


class FocusRenderTest(unittest.TestCase):  # AC1, AC6
    def test_render_passes_its_checks_and_they_are_not_vacuous(self):
        with tempfile.TemporaryDirectory() as tmp:
            song = make_song(Path(tmp), times=((0.3, 0.6), (1.2, 1.6)))
            words_sha = hashlib.sha256((song / "words.json").read_bytes()).hexdigest()
            result = render.render(song, codec="qtrle", theme=THEME)
            self.assertEqual(result.checks, [])
            self.assertEqual(result.notes, [])   # both words were read, none skipped
            self.assertEqual(result.render_dir, song / "render" / "soft-romantic-v2")
            report = (result.render_dir / "report.md").read_text("utf-8")
            self.assertIn("Theme: soft-romantic-v2", report)
            self.assertIn("sync check of 2 timed word(s) on the overlay's alpha; safe-zone", report)
            self.assertEqual(hashlib.sha256((song / "words.json").read_bytes()).hexdigest(),
                             words_sha)

            doc = timing.load_words(song / "words.json")
            lines, _ = plan_focus(doc, THEME, result.frames)
            late = [replace(fl, words=[replace(w, reveal=w.reveal + 10, end=w.end + 10)
                                       for w in fl.words]) for fl in lines]
            fails = render.check_outputs(result, late, THEME, result.frames)
            self.assertTrue(any(f.startswith("sync:") for f in fails), fails)
            tight = replace(THEME, safe_zone=(60, 380, 960, 1150))   # cuts through the text
            fails = render.check_outputs(result, lines, tight, result.frames)
            self.assertTrue(any(f.startswith("safe zone:") for f in fails), fails)


class CliThemeTest(unittest.TestCase):  # AC1, AC10
    def test_v2_is_the_default_and_v1_stays_available(self):
        with tempfile.TemporaryDirectory() as tmp:
            song = make_song(Path(tmp), times=((0.3, 0.6), (1.2, 1.6)))
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(cli.main(["make", str(song), "--codec", "qtrle"]), 0)
            self.assertEqual([p.name for p in (song / "render").iterdir()], ["soft-romantic-v2"])
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(cli.main(["render", str(song), "--theme", "soft-romantic",
                                           "--codec", "qtrle"]), 0)
            self.assertTrue((song / "render" / "soft-romantic" / "overlay.mov").is_file())


if __name__ == "__main__":
    unittest.main()
