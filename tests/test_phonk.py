"""render/phonk.py (Phonk Neon; spec 13): theme rules, lighting, glow pulse, drop split and shake,
the line shown ahead, frames, the CLI choice, and a short end-to-end render with its checks.

Timeline tests use hand-made layouts (no drawing). Frame and render tests use the bundled Pirata
One and a short real ffmpeg encode (qtrle, the fast codec). Render tests write beats.json by hand,
so librosa never runs.
"""
from __future__ import annotations

import contextlib
import hashlib
import io
import re
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path

from PIL import Image

from lyric_engine import cli, render, timing
from lyric_engine.layout import LineLayout, WordBox, layout_line
from lyric_engine.render import phonk
from lyric_engine.render.beatpop import accent, plan_beatpop
from lyric_engine.render.frames import _zero_frame
from lyric_engine.render.phonk import FLICKER, NeonCache, pulse, split, word_level
from lyric_engine.theme import DEFAULT_THEME, PHONK_NEON as THEME, THEMES
from tests.test_beatpop import doc_of, t, write_beats
from tests.test_karaoke import low_layout
from tests.test_render import make_song, word

D, S, SHAKE = 9, 8, 15   # pulse, split and shake frames at 30 fps (spec §4.4)
LOW = round(THEME.pulse_low * 32) / 32


def plan(doc, beat_frames=(), drop_frames=(), n_frames=900, layout_fn=low_layout):
    show, _ = plan_beatpop(doc, THEME, n_frames, beats=[t(b) for b in beat_frames],
                           drops=[t(d) for d in drop_frames], layout_fn=layout_fn, ahead=True)
    return show


def frame(n, show, sprites, cache=None):
    return b"".join(bytes(p) for p in phonk.frame_parts(n, show, sprites, THEME,
                                                        cache or NeonCache()))


def opaque(show, sprites, n):
    img = Image.frombytes("RGBA", (THEME.width, THEME.height), frame(n, show, sprites))
    return {c[:3] for _, c in img.getcolors(1 << 20) if c[3] == 255}


class ThemeTest(unittest.TestCase):
    def test_listed_beside_the_others_and_default_unchanged(self):
        self.assertIn("phonk-neon", THEMES)
        self.assertEqual(DEFAULT_THEME, "soft-romantic-v2")
        self.assertTrue(Path(THEME.font).is_file(), "Pirata One must be bundled in fonts/")
        self.assertTrue((Path(THEME.font).parent / "OFL-PirataOne.txt").is_file())

    def test_guards(self):
        for change, message in ((dict(unlit_rgb=None), "unlit_rgb"),
                                (dict(pulse_low=1.5), "pulse_low"),
                                (dict(drop_scale=0.9), "drop_scale"),
                                (dict(preroll_s=0.1), "preroll_s"),
                                (dict(split_px=-1), "negative"),
                                (dict(glow_rgb=(0, 255, 0)), "key")):
            with self.subTest(change), self.assertRaisesRegex(ValueError, message):
                replace(THEME, **change)


class LightTest(unittest.TestCase):  # AC3
    def test_unlit_before_its_frame_full_on_it_then_flickers_to_rest(self):
        wp = plan(doc_of([(10, 30)])).lines[0].words[0]
        self.assertEqual([word_level(wp, n) for n in range(0, 10)], [0.0] * 10)
        self.assertEqual([word_level(wp, n) for n in range(10, 17)], [*FLICKER, 1.0, 1.0])
        self.assertEqual(word_level(wp, wp.end), 1.0)

    def test_short_words_are_lit_at_rest_by_their_end(self):
        for span in ((10, 10), (10, 11), (10, 12)):
            wp = plan(doc_of([span])).lines[0].words[0]
            self.assertEqual(word_level(wp, 10), 1.0, span)
            self.assertEqual(word_level(wp, wp.end), 1.0, span)

    def test_untimed_word_is_never_lit(self):
        wp = plan(doc_of([(10, 20), None])).lines[0].words[1]
        self.assertEqual({word_level(wp, n) for n in range(200)}, {0.0})


class PulseTest(unittest.TestCase):  # AC4
    def test_peaks_on_each_beat_frame_and_settles(self):
        show = plan(doc_of([(10, 120)]), beat_frames=[20, 50])
        for b in (20, 50):
            self.assertEqual(pulse(show, b, THEME), 1.0)
            self.assertEqual(pulse(show, b - 1, THEME), LOW)
            self.assertTrue(LOW < pulse(show, b + 1, THEME) < 1.0)
            self.assertEqual(pulse(show, b + D, THEME), LOW)
        self.assertEqual(pulse(show, 5, THEME), LOW)

    def test_beats_never_scale_or_move_the_line(self):
        show = plan(doc_of([(10, 120)]), beat_frames=[20, 50])
        self.assertEqual({accent(show, n, THEME) for n in range(100)}, {(1.0, 0, 0)})


class DropTest(unittest.TestCase):  # AC5
    def test_split_and_shake_peak_on_the_drop_and_settle(self):
        show = plan(doc_of([(10, 120)]), beat_frames=[40], drop_frames=[40])
        self.assertEqual(split(show, 39, THEME), 0)
        self.assertEqual(split(show, 40, THEME), THEME.split_px)
        self.assertTrue(0 < split(show, 41, THEME) < THEME.split_px)
        self.assertEqual(split(show, 40 + S, THEME), 0)
        scale, dx, dy = accent(show, 40, THEME)
        self.assertEqual(scale, THEME.drop_scale)
        self.assertTrue(dx or dy)
        self.assertEqual(accent(show, 40 + SHAKE, THEME), (1.0, 0, 0))

    def test_nothing_drawn_for_a_drop_with_no_line(self):
        show = plan(doc_of([(10, 20)]), drop_frames=[200], layout_fn=layout_line)
        self.assertEqual(show.notes, ["drop at 0:06.7: no line on screen, nothing shaken"])
        self.assertEqual(frame(200, show, phonk.build_sprites(show, THEME)),
                         _zero_frame(THEME.width, THEME.height))


class AheadTest(unittest.TestCase):  # AC6
    def test_line_waits_unlit_before_its_first_word(self):
        show = plan(doc_of([(30, 40), (45, 50)]))
        pl = show.lines[0]
        self.assertEqual((pl.enter, pl.rest), (15, 21))   # preroll 0.5 s, entrance 0.2 s
        for n in range(pl.enter, 30):
            self.assertEqual({word_level(wp, n) for wp in pl.words}, {0.0}, n)
        self.assertEqual(phonk.line_state(show, pl, pl.rest, THEME), (1.0, 0, 0, 1.0))

    def test_one_line_at_a_time(self):
        show = plan(doc_of([(30, 40)], [(45, 60)], [(150, 160)]))
        for n in range(250):
            self.assertLessEqual(sum(pl.enter <= n < pl.stop for pl in show.lines), 1, n)


class FramesTest(unittest.TestCase):  # AC8
    def test_real_frame_unlit_then_lit_with_glow(self):
        doc = {"lyrics": {"lines": ["Jis roz"]},
               "words": [word(0, "Jis", 0, t(30), t(60)), word(1, "roz", 0, t(80), t(110))]}
        show = plan(doc, beat_frames=[70], layout_fn=layout_line)
        sprites = phonk.build_sprites(show, THEME)
        ahead, lit = opaque(show, sprites, 25), opaque(show, sprites, 70)
        self.assertIn(THEME.unlit_rgb, ahead)
        self.assertNotIn(THEME.text_rgb, ahead)
        self.assertTrue({THEME.text_rgb, THEME.unlit_rgb} <= lit)
        glow = Image.frombytes("RGBA", (THEME.width, THEME.height), frame(70, show, sprites))
        self.assertIn(THEME.glow_rgb, {c[:3] for _, c in glow.getcolors(1 << 20) if c[3] < 255})

    def test_drawn_text_must_be_the_words_json_text(self):
        show = plan(doc_of([(10, 20)]))
        show.lines[0].layout = LineLayout(0, THEME.font_size, (WordBox(0, "X", 200, 1000, 100, 80),))
        show.lines[0].words[0].box = show.lines[0].layout.words[0]
        with self.assertRaisesRegex(AssertionError, "layout text"):
            phonk.build_sprites(show, THEME)

    def test_cache_gives_identical_frames(self):
        doc = {"lyrics": {"lines": ["Jis roz se"]},
               "words": [word(k, w, 0, t(20 + 20 * k), t(38 + 20 * k))
                         for k, w in enumerate(["Jis", "roz", "se"])]}
        show = plan(doc, beat_frames=[25, 50], drop_frames=[50], layout_fn=layout_line)
        sprites, cache = phonk.build_sprites(show, THEME), NeonCache()
        for n in range(0, 130, 2):
            self.assertEqual(frame(n, show, sprites, cache), frame(n, show, sprites), n)


class PhonkRenderTest(unittest.TestCase):  # AC1, AC7
    def test_render_passes_its_checks_and_they_are_not_vacuous(self):
        with tempfile.TemporaryDirectory() as tmp:
            song = make_song(Path(tmp), lyrics="mere saamne\nwaali khidki\n",
                             times=((0.3, 0.7), (0.8, 1.4), (2.6, 3.0), (3.1, 3.9)),
                             duration=5.0)
            beat_times = [0.25 + 0.5 * k for k in range(10)]
            write_beats(song, beat_times)
            (song / "drops.txt").write_text("2.75\n", encoding="utf-8")
            shas = {name: hashlib.sha256((song / name).read_bytes()).hexdigest()
                    for name in ("words.json", "beats.json")}
            result = render.render(song, codec="qtrle", theme=THEME)
            self.assertEqual(result.checks, [])
            self.assertEqual(result.render_dir, song / "render" / "phonk-neon")
            self.assertIn("drop 2.75 → 2.75 s", result.notes)
            read = next(n for n in result.notes if n.startswith("pulse check read"))
            self.assertGreaterEqual(int(re.search(r"read (\d+) of", read)[1]), 2, read)
            report = (result.render_dir / "report.md").read_text("utf-8")
            self.assertIn("light check of 4 timed word(s)", report)
            self.assertEqual({name: hashlib.sha256((song / name).read_bytes()).hexdigest()
                              for name in shas}, shas)

            doc = timing.load_words(song / "words.json")
            def fresh():
                show, _ = plan_beatpop(doc, THEME, result.frames, beats=beat_times,
                                       drops=[2.75], ahead=True)
                return show

            def fails(show, theme=THEME):
                return render.check_outputs(result, show, theme, result.frames)

            late = fresh()   # the plan says 5 frames later: the drawn words light 5 frames early
            for pl in late.lines:
                for wp in pl.words:
                    wp.reveal, wp.end = wp.reveal + 5, wp.end + 5
            self.assertTrue(any(f.startswith("light:") for f in fails(late)))
            off = fresh()
            off.beats = [b + 3 for b in off.beats]
            self.assertTrue(any(f.startswith("pulse:") for f in fails(off)))
            tight = replace(THEME, safe_zone=(60, 380, 960, 1150))   # cuts through the text
            self.assertTrue(any(f.startswith("safe zone:") for f in fails(fresh(), tight)))


class CliThemeTest(unittest.TestCase):  # AC1
    def test_phonk_neon_is_offered(self):
        with tempfile.TemporaryDirectory() as tmp:
            song = make_song(Path(tmp), times=((0.3, 0.6), (1.2, 1.6)))
            write_beats(song, [0.5, 1.0, 1.5])
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(cli.main(["make", str(song), "--theme", "phonk-neon",
                                           "--codec", "qtrle"]), 0)
            self.assertEqual([p.name for p in (song / "render").iterdir()], ["phonk-neon"])


if __name__ == "__main__":
    unittest.main()
