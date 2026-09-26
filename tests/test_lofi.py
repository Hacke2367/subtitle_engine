"""render/lofi.py (Lofi Minimal, Lofi Typewriter; spec 09): theme rules, colour states, letter
frames, the one-line life cycle, frames, the CLI choice, and short end-to-end renders with the
colour-state, typing and safe-zone checks.

Timeline tests use hand-made layouts (no fonts). Frame and render tests use the bundled Poppins
Light and a short real ffmpeg encode (qtrle, the fast codec).
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
from lyric_engine.render import lofi
from lyric_engine.render.frames import LEVELS
from lyric_engine.render.lofi import (
    REST, LofiCache, colour_state, letter_frames, letter_levels, line_state, plan_lofi, word_look,
)
from lyric_engine.render.timeline import WordPlan
from lyric_engine.theme import DEFAULT_THEME, LOFI_MINIMAL as THEME, LOFI_TYPEWRITER as TW
from tests.test_karaoke import low_layout
from tests.test_render import make_song, word

EIN, P, H, X, FI, FS, LF = 18, 27, 45, 15, 4, 12, 3   # frames at 30 fps (plan §5)
W, HT = THEME.width, THEME.height


def t(frame: int) -> float:
    """A time that lands exactly on this frame after the 0.05 s lead (unrounded, unlike
    tests.test_karaoke.t, whose 4-decimal rounding moves most frames one earlier)."""
    return frame / 30 + 0.05


def lines_of(*spans, theme=THEME, layout_fn=low_layout, n_frames=900):
    """One line per (first, last) frame pair, one word each: start first, end last."""
    words = [word(k, f"w{k}", k, t(a), t(b)) for k, (a, b) in enumerate(spans)]
    return plan_lofi({"words": words}, theme, n_frames, layout_fn=layout_fn)[0]


def real_plan(words, theme=THEME, n_frames=300):
    return plan_lofi({"words": words}, theme, n_frames)[0]


def visible(lines, n, theme=THEME):
    return [ll for ll in lines if line_state(ll, n, theme)[0] > 0]


def wp(reveal, end):
    return WordPlan(WordBox(0, "w", 0, 0, 10, 10), reveal, end, "w")


def frame(n, lines, sprites, theme=THEME, cache=None):
    return b"".join(bytes(p) for p in lofi.frame_parts(n, lines, sprites, theme,
                                                        cache or LofiCache()))


class ThemeTest(unittest.TestCase):
    def test_the_two_themes_share_one_look(self):
        self.assertEqual(replace(THEME, name="lofi-typewriter", typewriter=True), TW)
        self.assertEqual((THEME.motion, THEME.safe_zone, THEME.center_x, THEME.tracking),
                         ("lofi", (60, 380, 960, 1540), 510, 0.10))
        self.assertTrue(Path(THEME.font).is_file(), "Poppins Light must be bundled in fonts/")
        self.assertEqual(Path(THEME.font).name, "Poppins-Light.ttf")
        self.assertEqual(DEFAULT_THEME, "soft-romantic-v2")   # H-015 unchanged

    def test_rules_are_enforced(self):
        with self.assertRaisesRegex(ValueError, "accent_rgb"):
            replace(THEME, accent_rgb=None)
        with self.assertRaisesRegex(ValueError, "preroll_s"):
            replace(THEME, preroll_s=0.6)
        replace(TW, preroll_s=0.6)   # the typewriter shows nothing ahead: no preroll needed
        with self.assertRaisesRegex(ValueError, "tracking"):
            replace(THEME, tracking=-0.1)
        with self.assertRaisesRegex(ValueError, "key"):
            replace(THEME, accent_rgb=(0, 255, 0))


class ColourStateTest(unittest.TestCase):  # AC3
    def test_current_from_start_to_end_then_sung(self):
        w = wp(10, 40)
        self.assertEqual(colour_state(w, 9, THEME), (0.35, 0.0))
        mixes = [colour_state(w, n, THEME)[1] for n in range(10, 10 + FI + 1)]
        self.assertEqual(mixes[0], 0.0)
        self.assertEqual(mixes, sorted(mixes))
        for n in range(10 + FI, 41):
            self.assertEqual(colour_state(w, n, THEME), (1.0, 1.0), n)
        self.assertLess(colour_state(w, 41, THEME)[1], 1.0)
        self.assertEqual(colour_state(w, 40 + FS, THEME), (1.0, 0.0))
        self.assertEqual(colour_state(w, 200, THEME), (1.0, 0.0))

    def test_a_short_word_is_fully_current_on_its_end_frame(self):
        for reveal, end in ((10, 10), (10, 11), (10, 12)):
            self.assertEqual(colour_state(wp(reveal, end), end, THEME), (1.0, 1.0))
            self.assertEqual(colour_state(wp(reveal, end), reveal - 1, THEME), (0.35, 0.0))

    def test_a_flagged_word_never_turns_current(self):
        for n in range(0, 300, 7):
            self.assertEqual(colour_state(wp(None, None), n, THEME), (0.35, 0.0))
            self.assertEqual(colour_state(wp(None, None), n, TW), (1.0, 0.0))


class LetterTest(unittest.TestCase):  # AC4
    def test_letters_type_inside_the_words_own_span(self):
        w = {"start": t(10), "end": t(40)}
        frames = letter_frames(w, 5, TW)
        self.assertEqual(frames[0], 10)
        self.assertEqual(frames, (10, 11, 13, 15, 17))   # 0.06 s = 1.8 frames apart
        short = {"start": t(10), "end": t(12)}   # 2 frames for 5 letters: stagger shrinks
        s = (short["end"] - short["start"]) / 5
        frames = letter_frames(short, 5, TW)
        self.assertEqual(frames[0], 10)
        self.assertLessEqual(frames[-1], 12)
        self.assertLess(short["start"] - 0.05 + 4 * s, short["end"] - 0.05)
        self.assertEqual(frames, tuple(sorted(frames)))

    def test_letter_levels_fade_in_from_each_letters_frame(self):
        self.assertEqual(letter_levels((10, 12), 10, TW), (0, 0))
        self.assertEqual(letter_levels((10, 12), 10 + LF, TW), (LEVELS, round(LEVELS / 3)))
        self.assertEqual(letter_levels((10, 12), 12 + LF, TW), (LEVELS, LEVELS))

    def test_letter_zero_is_the_words_reveal(self):
        for ll in lines_of((10, 40), (100, 130), theme=TW):
            self.assertEqual(ll.letters[ll.words[0].box.index][0], ll.words[0].reveal)

    def test_a_fully_typed_word_is_the_whole_word(self):
        lines = real_plan([word(0, "dekha", 0, t(10), t(40))], TW)
        sprites, cache = lofi.build_sprites(lines, TW), LofiCache()
        edges = sprites[0][3]
        self.assertEqual(len(edges), 6)   # five letters
        whole = lofi.look_sprite(sprites, 0, (LEVELS, LEVELS), TW, cache)
        typed = lofi.look_sprite(sprites, 0, (LEVELS, LEVELS, (LEVELS,) * 5), TW, cache)
        self.assertEqual(typed.tobytes(), whole.tobytes())
        first = lofi.look_sprite(sprites, 0, (LEVELS, LEVELS, (LEVELS, 0, 0, 0, 0)), TW, cache)
        alpha = first.getchannel("A")
        self.assertGreater(alpha.crop((0, 0, edges[1], alpha.height)).getextrema()[1], 200)
        self.assertEqual(alpha.crop((edges[1], 0, alpha.width, alpha.height)).getextrema(), (0, 0))

    def test_a_non_latin_word_appears_whole(self):
        lines = real_plan([word(0, "दिल", 0, t(10), t(40)), word(1, "dil😊", 0, t(42), t(60))], TW)
        (ll,) = lines
        self.assertEqual(ll.letters, {0: (10,), 1: (42,)})
        self.assertEqual(len(ll.notes), 2)
        self.assertTrue(all("typed whole" in note for note in ll.notes))
        self.assertEqual(len(lofi.build_sprites(lines, TW)[0][3]), 2)   # one band

    def test_a_flagged_word_is_drawn_whole_and_never_types(self):
        (ll,) = real_plan([word(0, "mere", 0, t(10), t(40)),
                           word(1, "saamne", 0, None, None, ["unaligned"])], TW)
        self.assertNotIn(1, ll.letters)
        for n in (ll.enter, 20, 60):
            self.assertEqual(word_look(ll, ll.words[1], n, TW), (LEVELS, 0))


class PlanLofiTest(unittest.TestCase):  # AC5
    CASES = {"gap": ((10, 40), (200, 230)), "close": ((10, 40), (100, 130)),
             "shrink": ((10, 40), (60, 90)), "cut": ((10, 40), (41, 60)),
             "overlap": ((10, 40), (35, 60)), "at 0:00": ((0, 20), (40, 60))}

    def test_one_line_at_a_time_and_never_leaving_early(self):
        for theme in (THEME, TW):
            for name, spans in self.CASES.items():
                with self.subTest(theme.name, case=name):
                    lines = lines_of(*spans, theme=theme)
                    for n in range(0, 400):
                        self.assertLessEqual(len(visible(lines, n, theme)), 1, n)
                    a, b = lines
                    if name not in ("cut", "overlap"):
                        self.assertGreaterEqual(a.leave, a.settled)
                        self.assertGreaterEqual(a.settled, a.last_end)
                        self.assertTrue(lofi.readable(lines, b, b.first_cur - 1, theme))

    def test_minimal_life_cycle_frames(self):
        a, b = lines_of((10, 40), (200, 230))   # instrumental gap: hold, clear, preroll
        self.assertEqual((a.enter, a.rest, a.leave, a.stop), (0, 0, 40 + H, 40 + H + X))
        self.assertEqual((b.enter, b.rest), (200 - P, 200 - P + EIN))
        a, b = lines_of((40, 70), (130, 160))   # close: leave early, next rests on F − 1
        self.assertEqual((a.enter, a.rest), (40 - P, 40 - P + EIN))
        self.assertEqual((a.stop, a.leave), (130 - 1 - EIN, 130 - 1 - EIN - X))
        self.assertEqual((b.enter, b.rest), (130 - 1 - EIN, 129))
        a, b = lines_of((10, 40), (60, 90))     # shrink in proportion
        self.assertEqual((a.leave, a.stop, b.enter, b.rest), (40, 49, 49, 59))
        self.assertEqual(a.notes + b.notes, [])
        self.assertEqual(line_state(b, 59, THEME), REST)
        self.assertLess(line_state(b, 58, THEME)[0], 1)

    def test_cut_and_back_to_back_lines_are_notes(self):
        a, b = lines_of((10, 40), (41, 60))
        self.assertEqual((a.leave, a.stop, b.enter, b.rest), (41, 41, 41, 41))
        self.assertEqual(len(a.notes), 1)
        self.assertIn("cut, not faded", a.notes[0])
        a, b = lines_of((10, 40), (35, 60))
        self.assertEqual(a.stop, 35)
        self.assertEqual(len(a.notes), 2)
        self.assertIn("its last 6 frame(s) are not shown", a.notes[1])

    def test_first_word_near_0_is_at_rest_from_frame_0(self):
        for first in (0, 10, EIN):
            (a,) = lines_of((first, first + 20))
            self.assertEqual((a.enter, a.rest), (0, 0), first)
        (a,) = lines_of((30, 50))
        self.assertEqual((a.enter, a.rest), (3, 3 + EIN))

    def test_typewriter_life_cycle(self):
        a, b = lines_of((10, 40), (60, 90), theme=TW)
        self.assertEqual((a.enter, a.rest), (10, 10))
        self.assertEqual((a.stop, a.leave, b.enter, b.rest), (59, 44, 60, 60))
        a, b = lines_of((10, 40), (50, 90), theme=TW)   # shrink: all of it goes to the exit
        self.assertEqual((a.leave, a.stop, b.enter), (40, 49, 50))

    def test_the_last_letters_fade_holds_the_line(self):
        (a,) = lines_of((10, 10), theme=TW)   # "w0" has two letters, both on frame 10
        self.assertEqual(a.letters[0], (10, 10))
        self.assertEqual(a.settled, 10 + LF)
        self.assertEqual(a.leave, 10 + LF + H)


class LineStateTest(unittest.TestCase):  # AC5
    def test_entrance_rest_and_exit(self):
        a, _ = lines_of((40, 70), (200, 230))
        self.assertEqual(line_state(a, a.enter - 1, THEME), (0.0, 0.0))
        op, dy = line_state(a, a.enter, THEME)
        self.assertEqual((op, dy), (0.0, THEME.rise_px))
        ops = [line_state(a, n, THEME)[0] for n in range(a.enter, a.rest + 1)]
        self.assertEqual(ops, sorted(ops))
        for n in range(a.rest, a.leave + 1):
            self.assertEqual(line_state(a, n, THEME), REST, n)
        op, dy = line_state(a, a.stop - 1, THEME)
        self.assertLess(op, 0.2)
        self.assertLess(dy, 0)
        self.assertEqual(line_state(a, a.stop, THEME), (0.0, 0.0))


class FramesTest(unittest.TestCase):  # AC4 pixels, AC9
    def test_states_draw_their_exact_colours(self):
        lines = real_plan([word(0, "dekha", 0, t(40), t(80))])
        sprites = lofi.build_sprites(lines, THEME)
        box = lines[0].words[0].box

        def solid_pixel(n):
            img = Image.frombytes("RGBA", (W, HT), frame(n, lines, sprites))
            crop = img.crop((box.x, box.y, box.x + box.w, box.y + box.h))
            alpha = crop.getchannel("A")
            top = alpha.getextrema()[1]
            x, y = next((x, y) for y in range(crop.height) for x in range(crop.width)
                        if alpha.getpixel((x, y)) == top)
            return crop.getpixel((x, y))

        self.assertEqual(solid_pixel(39), (*THEME.text_rgb, round(255 * 11 / 32)))   # upcoming
        self.assertEqual(solid_pixel(40 + FI), (*THEME.accent_rgb, 255))            # current
        self.assertEqual(solid_pixel(80 + FS), (*THEME.text_rgb, 255))              # sung

    def test_typewriter_draws_nothing_before_the_first_letter(self):
        lines = real_plan([word(0, "dekha", 0, t(40), t(80))], TW)
        sprites = lofi.build_sprites(lines, TW)
        self.assertEqual(frame(39, lines, sprites, TW), bytes(W * HT * 4))
        self.assertNotEqual(frame(41, lines, sprites, TW), bytes(W * HT * 4))

    def test_cache_gives_identical_frames(self):
        for theme in (THEME, TW):
            lines = real_plan([word(0, "mere", 0, t(30), t(40)),
                               word(1, "saamne", 1, t(60), t(90))], theme)
            sprites, cache = lofi.build_sprites(lines, theme), LofiCache()
            for n in (5, 12, 31, 33, 44, 45, 60, 62, 90, 100, 45, 160):
                self.assertEqual(frame(n, lines, sprites, theme, cache),
                                 frame(n, lines, sprites, theme), (theme.name, n))

    def test_drawn_text_must_be_the_words_json_text(self):
        lines = real_plan([word(0, "mere", 0, t(10), t(20))])
        bad = [replace(lines[0], words=[replace(lines[0].words[0], text="Mere")])]
        with self.assertRaisesRegex(AssertionError, "words.json text"):
            lofi.build_sprites(bad, THEME)


class LofiRenderTest(unittest.TestCase):  # AC1, AC7
    def test_renders_pass_their_checks_and_they_are_not_vacuous(self):
        for theme, check in ((THEME, "colour-state check of 4 timed word(s)"),
                             (TW, "typing check of 4 timed word(s)")):
            with self.subTest(theme.name), tempfile.TemporaryDirectory() as tmp:
                song = make_song(Path(tmp), lyrics="mere saamne\nwaali khidki\n",
                                 times=((0.3, 0.7), (0.8, 1.4), (2.6, 3.0), (3.1, 3.9)),
                                 duration=5.0)
                words_sha = hashlib.sha256((song / "words.json").read_bytes()).hexdigest()
                result = render.render(song, codec="qtrle", theme=theme)
                self.assertEqual(result.checks, [])
                self.assertEqual(result.notes, [])   # every word was read, none cut
                self.assertEqual(result.render_dir, song / "render" / theme.name)
                report = (result.render_dir / "report.md").read_text("utf-8")
                self.assertIn(f"Theme: {theme.name}", report)
                self.assertIn(check, report)
                self.assertEqual(hashlib.sha256((song / "words.json").read_bytes()).hexdigest(),
                                 words_sha)

                doc = timing.load_words(song / "words.json")
                lines, _ = plan_lofi(doc, theme, result.frames)
                late = [replace(ll, words=[replace(w, reveal=w.reveal + 10, end=w.end + 10)
                                           for w in ll.words],
                                letters={i: tuple(f + 10 for f in fs)
                                         for i, fs in ll.letters.items()}) for ll in lines]
                fails = render.check_outputs(result, late, theme, result.frames)
                prefix = "sync:" if theme.typewriter else "state:"
                self.assertTrue(any(f.startswith(prefix) for f in fails), fails)
                tight = replace(theme, safe_zone=(60, 380, 960, 1150))   # cuts through the text
                fails = render.check_outputs(result, lines, tight, result.frames)
                self.assertTrue(any(f.startswith("safe zone:") for f in fails), fails)


class CliThemeTest(unittest.TestCase):  # AC1
    def test_both_lofi_themes_are_offered(self):
        with tempfile.TemporaryDirectory() as tmp:
            song = make_song(Path(tmp), times=((0.3, 0.6), (1.2, 1.6)))
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(cli.main(["render", str(song), "--theme", "lofi-minimal",
                                           "--codec", "qtrle"]), 0)
                self.assertEqual(cli.main(["make", str(song), "--theme", "lofi-typewriter",
                                           "--codec", "qtrle"]), 0)
            self.assertEqual(sorted(p.name for p in (song / "render").iterdir()),
                             ["lofi-minimal", "lofi-typewriter"])


if __name__ == "__main__":
    unittest.main()
