"""render/beatpop.py (Beat Pop; spec 12): theme rules, pop, pill, beat bump and drop shake,
drops.txt, the one-line life cycle, frames, the CLI choice, and a short end-to-end render with its
checks.

Timeline tests use hand-made layouts (no drawing). Frame and render tests use the bundled Anton
and a short real ffmpeg encode (qtrle, the fast codec). Render tests write beats.json by hand, so
librosa never runs.
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

from lyric_engine import beats, cli, render, timing
from lyric_engine.layout import LineLayout, WordBox, layout_line
from lyric_engine.render import beatpop
from lyric_engine.render.beatpop import PopCache, Show, accent, line_state, plan_beatpop, word_look
from lyric_engine.render.frames import _zero_frame
from lyric_engine.theme import BEAT_POP as THEME, DEFAULT_THEME, THEMES
from tests.test_karaoke import low_layout
from tests.test_render import make_song, word

P, D, S = 8, 5, 15   # pop, bump fall, shake frames at 30 fps (spec §4.5)
MUSTARD, BLACK = THEME.pill_rgb, THEME.pill_text_rgb


def t(frame: int) -> float:
    """A time that lands exactly on this frame after the 0.05 s lead."""
    return frame / 30 + 0.05


def doc_of(*lines):
    """One lyric line per argument, each a list of word spans: (first, last) frame, or None for
    an untimed word."""
    words, lyric = [], []
    for li, spans in enumerate(lines):
        texts = [f"w{li}{k}" for k in range(len(spans))]
        lyric.append(" ".join(texts))
        for text, sp in zip(texts, spans):
            words.append(word(len(words), text, li,
                              *((None, None) if sp is None else (t(sp[0]), t(sp[1])))))
    return {"lyrics": {"lines": lyric}, "words": words}


def plan(doc, beat_frames=(), drop_frames=(), n_frames=900, layout_fn=low_layout):
    show, _ = plan_beatpop(doc, THEME, n_frames, beats=[t(b) for b in beat_frames],
                           drops=[t(d) for d in drop_frames], layout_fn=layout_fn)
    return show


def looks(show, n):
    pl = show.lines[0]
    return [word_look(pl, wp, n, THEME) for wp in pl.words]


def frame(n, show, sprites, cache=None):
    return b"".join(bytes(p) for p in beatpop.frame_parts(n, show, sprites, THEME,
                                                          cache or PopCache()))


def write_beats(song: Path, times: list[float]) -> None:
    """A valid beats.json for the song's audio, by hand: render reuses it, librosa never runs."""
    audio = song / "audio.wav"
    doc = beats.make_doc(song.name, audio, timing.sha256_file(audio), 5.0,
                         beats.Detection(120.0, times, []), None)
    beats.save_beats(song / beats.BEATS_FILE, doc)


class ThemeTest(unittest.TestCase):
    def test_listed_beside_the_others_and_default_unchanged(self):
        self.assertIn("beat-pop", THEMES)
        self.assertEqual(DEFAULT_THEME, "soft-romantic-v2")
        self.assertTrue(Path(THEME.font).is_file(), "Anton must be bundled in fonts/")
        self.assertTrue((Path(THEME.font).parent / "OFL-Anton.txt").is_file())

    def test_guards(self):
        for change, message in ((dict(pill_rgb=None), "pill_rgb"),
                                (dict(pop_scale=0), "pop_scale"),
                                (dict(bump_scale=0.9), "bump_scale"),
                                (dict(exit_scale=1.2), "exit"),
                                (dict(shake_px=-1), "negative"),
                                (dict(pill_rgb=(0, 255, 0)), "key")):
            with self.subTest(change), self.assertRaisesRegex(ValueError, message):
                replace(THEME, **change)


class PopTest(unittest.TestCase):  # AC3
    def test_pop_from_the_sung_frame_to_rest(self):
        show = plan(doc_of([(10, 40)]))
        self.assertEqual(looks(show, 9), [None])
        (q, sung), = looks(show, 10)
        self.assertTrue(q < 1 and sung)
        self.assertEqual(looks(show, 10 + P - 1), [(1.0, True)])
        peak = max(looks(show, n)[0][0] for n in range(10, 10 + P))
        self.assertTrue(1.0 < peak <= 1.10, peak)
        self.assertEqual(looks(show, 40), [(1.0, False)])

    def test_short_words_are_at_rest_by_their_end(self):
        for first, last in ((10, 11), (10, 13)):
            show = plan(doc_of([(first, last)]))
            wp = show.lines[0].words[0]
            done = wp.reveal + beatpop.pop_frames(wp, THEME) - 1
            self.assertLessEqual(done, max(wp.reveal, wp.end - 1))
            self.assertEqual(looks(show, done)[0][0], 1.0)

    def test_untimed_word_is_at_rest_from_its_lines_first_frame(self):
        show = plan(doc_of([(10, 20), None]))
        self.assertEqual(looks(show, 9), [None, None])
        self.assertEqual(looks(show, 10)[1], (1.0, False))
        self.assertFalse(any(looks(show, n)[1][1] for n in range(10, 60)))


class PillTest(unittest.TestCase):  # AC4
    def test_sung_exactly_on_its_span_and_never_in_a_gap(self):
        show = plan(doc_of([(10, 20), (25, 30), (30, 40)]))
        sung = [[n for n in range(0, 60) if (lk := looks(show, n)[k]) and lk[1]] for k in range(3)]
        self.assertEqual(sung, [list(range(10, 20)), list(range(25, 30)), list(range(30, 40))])
        self.assertFalse(any(lk and lk[1] for lk in looks(show, 22)))   # the gap
        self.assertEqual([lk[1] for lk in looks(show, 30)], [False, False, True])   # hand-over

    def test_real_frame_black_word_on_mustard_then_white(self):
        doc = {"lyrics": {"lines": ["Jis roz"]},
               "words": [word(0, "Jis", 0, t(10), t(40)), word(1, "roz", 0, t(60), t(90))]}
        show = plan(doc, layout_fn=layout_line)
        sprites = beatpop.build_sprites(show, THEME)
        on = Image.frombytes("RGBA", (THEME.width, THEME.height), frame(20, show, sprites))
        after = Image.frombytes("RGBA", (THEME.width, THEME.height), frame(45, show, sprites))
        colours = {c for _, c in on.getcolors(1 << 20) if c[3] == 255}
        self.assertIn((*MUSTARD, 255), colours)
        self.assertIn((*BLACK, 255), colours)
        self.assertNotIn((*MUSTARD, 255), {c for _, c in after.getcolors(1 << 20)})
        a, b = show.lines[0].layout.words
        px = round(THEME.pill_pad * show.lines[0].layout.font_size)
        self.assertGreaterEqual(b.x - (a.x + a.w + px), 17)   # a pill never reaches the next word
        pill = sprites[0][3]
        self.assertEqual(pill.size, sprites[0][2].size)


class AccentTest(unittest.TestCase):  # AC5
    def test_bump_peaks_on_the_beat_and_settles(self):
        show = Show([], [30, 60], [])
        self.assertEqual(accent(show, 29, THEME), (1.0, 0, 0))
        self.assertEqual(accent(show, 30, THEME), (THEME.bump_scale, 0, 0))
        self.assertTrue(1.0 < accent(show, 31, THEME)[0] < THEME.bump_scale)
        self.assertEqual(accent(show, 30 + D, THEME), (1.0, 0, 0))
        self.assertEqual(accent(show, 60, THEME)[0], THEME.bump_scale)

    def test_drop_peaks_bigger_shakes_and_settles(self):
        show = Show([], [30], [30])
        scale, dx, dy = accent(show, 30, THEME)
        self.assertEqual(scale, THEME.drop_scale)   # the larger, not 1.05 × 1.12
        self.assertNotEqual((dx, dy), (0, 0))
        for n in range(30, 30 + S):
            _, dx, dy = accent(show, n, THEME)
            self.assertLessEqual(max(abs(dx), abs(dy)), THEME.shake_px)
        self.assertEqual(accent(show, 30 + S, THEME), (1.0, 0, 0))

    def test_nothing_drawn_for_a_beat_or_drop_with_no_line(self):
        show = plan(doc_of([(100, 120)]), beat_frames=[31], drop_frames=[31],
                    layout_fn=layout_line)
        self.assertEqual(show.notes, ["drop at 0:01.1: no line on screen, nothing shaken"])
        self.assertEqual(frame(31, show, beatpop.build_sprites(show, THEME)),
                         _zero_frame(THEME.width, THEME.height))

    def test_exit_fades_and_shrinks(self):
        show = plan(doc_of([(10, 20)]))
        pl = show.lines[0]
        self.assertEqual(line_state(show, pl, pl.leave - 1, THEME), (1.0, 0, 0, 1.0))
        scale, _, _, opacity = line_state(show, pl, pl.stop - 1, THEME)
        self.assertTrue(scale < 1.0 and 0 < opacity < 1)
        self.assertEqual(line_state(show, pl, pl.stop, THEME)[3], 0.0)


class DropsTest(unittest.TestCase):  # AC6
    def test_read_and_snap(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "drops.txt"
            path.write_text("1:05.5\n\n# the intro drop\n45   # first\n0:45.5\n", encoding="utf-8")
            drops = beats.read_drops(path, 100.0)
            self.assertEqual(drops, [("45", 45.0), ("0:45.5", 45.5), ("1:05.5", 65.5)])
            self.assertEqual(beats.snap([t for _, t in drops], [44.9, 45.25, 66.0]),
                             [44.9, 45.25, 66.0])
            self.assertEqual(beats.snap([1.5], [1.0, 2.0]), [1.0])   # a tie goes earlier
            self.assertEqual(beats.snap([3.0], []), [3.0])
            self.assertEqual(beats.read_drops(Path(tmp) / "none.txt", 100.0), [])
            for text, message in (("45\nsoon\n", "line 2: not a time"),
                                  ("2:00\n", "line 1: 2:00 is after the song's end")):
                path.write_text(text, encoding="utf-8")
                with self.subTest(text), self.assertRaisesRegex(beats.BeatsError, message):
                    beats.read_drops(path, 100.0)

    def test_parse_time(self):
        self.assertEqual([timing.parse_time(x) for x in ("27", "27.5", "0:27", "1:05.5")],
                         [27, 27.5, 27, 65.5])
        for bad in ("-1", "1:2:3", "x", "nan"):
            with self.subTest(bad), self.assertRaisesRegex(ValueError, "not a time"):
                timing.parse_time(bad)


class LifeTest(unittest.TestCase):
    def test_one_line_at_a_time_and_the_frame_before_each_is_empty(self):
        show = plan(doc_of([(10, 20), (22, 30)], [(40, 50)], [(120, 130)]))
        for n in range(200):
            self.assertLessEqual(sum(pl.enter <= n < pl.stop for pl in show.lines), 1, n)
        for pl in show.lines[1:]:
            self.assertFalse(any(o.enter <= pl.first_cur - 1 < o.stop for o in show.lines), pl.name)
        self.assertEqual([pl.enter for pl in show.lines], [10, 40, 120])


class FramesTest(unittest.TestCase):  # AC9
    def test_drawn_text_must_be_the_words_json_text(self):
        def wrong(words, line, theme, emphasis=frozenset()):
            return LineLayout(line, theme.font_size, tuple(
                WordBox(i, "X", 200, 1000, 100, 80) for i, _ in words))
        show = plan(doc_of([(10, 20)]), layout_fn=low_layout)
        show.lines[0].layout = wrong([(0, "w00")], 0, THEME)
        show.lines[0].words[0].box = show.lines[0].layout.words[0]
        with self.assertRaisesRegex(AssertionError, "layout text"):
            beatpop.build_sprites(show, THEME)

    def test_cache_gives_identical_frames(self):
        doc = {"lyrics": {"lines": ["Jis roz se"]},
               "words": [word(k, w, 0, t(10 + 20 * k), t(28 + 20 * k))
                         for k, w in enumerate(["Jis", "roz", "se"])]}
        show = plan(doc, beat_frames=[15, 40], drop_frames=[40], layout_fn=layout_line)
        sprites, cache = beatpop.build_sprites(show, THEME), PopCache()
        for n in range(0, 120, 3):
            self.assertEqual(frame(n, show, sprites, cache), frame(n, show, sprites), n)


class BeatPopRenderTest(unittest.TestCase):  # AC1, AC7
    def test_render_passes_its_checks_and_they_are_not_vacuous(self):
        with tempfile.TemporaryDirectory() as tmp:
            song = make_song(Path(tmp), lyrics="mere saamne\nwaali khidki\n",
                             times=((0.3, 0.7), (0.8, 1.4), (2.6, 3.0), (3.1, 3.9)),
                             duration=5.0)
            write_beats(song, [0.25 + 0.5 * k for k in range(10)])
            (song / "drops.txt").write_text("2.75\n", encoding="utf-8")
            shas = {name: hashlib.sha256((song / name).read_bytes()).hexdigest()
                    for name in ("words.json", "beats.json")}
            result = render.render(song, codec="qtrle", theme=THEME)
            self.assertEqual(result.checks, [])
            self.assertEqual(result.render_dir, song / "render" / "beat-pop")
            self.assertIn("beats: 120 BPM, 10 beats (beats.json reused)", result.notes)
            self.assertIn("drop 2.75 → 2.75 s", result.notes)
            report = (result.render_dir / "report.md").read_text("utf-8")
            self.assertIn("Theme: beat-pop", report)
            self.assertIn("pop and pill check of 4 timed word(s)", report)
            self.assertEqual({name: hashlib.sha256((song / name).read_bytes()).hexdigest()
                              for name in shas}, shas)

            doc = timing.load_words(song / "words.json")
            def fresh():
                show, _ = plan_beatpop(doc, THEME, result.frames,
                                       beats=[0.25 + 0.5 * k for k in range(10)], drops=[2.75])
                return show

            def fails(show, theme=THEME):
                return render.check_outputs(result, show, theme, result.frames)

            late = fresh()   # the plan says 5 frames later: the drawn words are 5 frames early
            for pl in late.lines:
                for wp in pl.words:
                    wp.reveal, wp.end = wp.reveal + 5, wp.end + 5
            self.assertTrue(any(f.startswith("pop:") for f in fails(late)))
            short = fresh()   # the plan ends 5 frames sooner: the drawn pill stays 5 frames late
            for pl in short.lines:
                for wp in pl.words:
                    wp.end -= 5
            self.assertTrue(any(f.startswith("pill:") for f in fails(short)))
            off = fresh()
            off.beats = [b + 3 for b in off.beats]
            self.assertTrue(any(f.startswith("beat:") for f in fails(off)))
            tight = replace(THEME, safe_zone=(60, 380, 960, 1150))   # cuts through the text
            self.assertTrue(any(f.startswith("safe zone:") for f in fails(fresh(), tight)))


class CliThemeTest(unittest.TestCase):  # AC1
    def test_beat_pop_is_offered(self):
        with tempfile.TemporaryDirectory() as tmp:
            song = make_song(Path(tmp), times=((0.3, 0.6), (1.2, 1.6)))
            audio = song / "audio.wav"
            beats.save_beats(song / beats.BEATS_FILE, beats.make_doc(
                song.name, audio, timing.sha256_file(audio), 2.0,
                beats.Detection(120.0, [0.5, 1.0, 1.5], []), None))
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(cli.main(["make", str(song), "--theme", "beat-pop",
                                           "--codec", "qtrle"]), 0)
            self.assertEqual([p.name for p in (song / "render").iterdir()], ["beat-pop"])


if __name__ == "__main__":
    unittest.main()
