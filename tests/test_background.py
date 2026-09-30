"""background/ (engine-made backgrounds; spec 17, looks H-034 to H-036): --bg names, song facts,
the shared art tools, each look's song reactions and determinism, the compose step (the overlay
laid over as it is), the legibility rule, the CLI, and a short end-to-end render.

The look tests build real full-size scenes (about a second each); the render test uses a short
real ffmpeg encode (qtrle).
"""
from __future__ import annotations

import io
import subprocess
import tempfile
import unittest
from contextlib import redirect_stderr
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

import numpy as np

from lyric_engine import cli, render
from lyric_engine.background import (WORLDS, SongFacts, backdrop, build_scene, khaali, paint, parse_bg,
                                     seed_of, song_facts,
                                     word_boxes)
from lyric_engine.background.compose import (Legibility, compose_frame, drawn_ahead, final_checks,
                                             frame_contrast)
from lyric_engine.theme import SOFT_ROMANTIC_V2 as THEME
from tests.test_render import make_song

W, H = 1080, 1920


def facts(words=(), name="khidki_s2_em", duration=14.0, last=10.0) -> SongFacts:
    """words: ((start, marked, cx, cy), ...); the lyrics sit in LYRICS."""
    words = tuple(sorted(words))
    return SongFacts(name, seed_of(name), duration, int(duration * 30), 30, words,
                     tuple(sorted({w[0] for w in words})) if words else (), last, (510.0, 1100.0), (),
                     LYRICS)


LYRICS = (160, 1040, 900, 1160)


def box(i, x, y, w=100, h=60, emphasis=False):
    return SimpleNamespace(index=i, x=x, y=y, w=w, h=h, emphasis=emphasis)


class ParseBgTest(unittest.TestCase):  # AC9
    def test_default_mood_and_explicit_mood(self):
        self.assertEqual(parse_bg("rain"), ("rain", "evening"))
        self.assertEqual(parse_bg("fog:moonlight"), ("fog", "moonlight"))
        self.assertEqual(parse_bg("milan"), ("milan", "night"))
        self.assertEqual(parse_bg("khaali"), ("khaali", "night"))

    def test_refusals_name_the_choices(self):
        with self.assertRaisesRegex(ValueError, r"unknown background 'room'; built: rain"):
            parse_bg("room")
        with self.assertRaisesRegex(ValueError, r"unknown mood 'gold' for fog; built: moonlight"):
            parse_bg("fog:gold")


class CliTest(unittest.TestCase):  # AC9
    def test_render_refuses_an_unknown_look(self):
        err = io.StringIO()
        with redirect_stderr(err), self.assertRaises(SystemExit) as ctx:
            cli.main(["render", "songs/x", "--bg", "room"])
        self.assertEqual(ctx.exception.code, 2)
        self.assertIn("unknown background", err.getvalue())

    def test_make_passes_the_background_through(self):
        with mock.patch("lyric_engine.workflow.ensure_aligned", return_value=0), \
                mock.patch.object(cli, "_render", return_value=0) as rendered:
            self.assertEqual(cli.main(["make", "songs/x", "--bg", "rain"]), 0)
        self.assertEqual(rendered.call_args.args[-1], ("rain", "evening"))


class SongFactsTest(unittest.TestCase):  # red line 1: only aligned times
    def test_words_marks_lines_and_places(self):
        doc = {"words": [
            {"i": 0, "text": "Jis", "line": 0, "start": 0.5, "end": 0.8},
            {"i": 1, "text": "dekha", "line": 0, "start": 1.0, "end": 1.5},
            {"i": 2, "text": "Dil", "line": 1, "start": None, "end": None},
            {"i": 3, "text": "thaam", "line": 1, "start": 3.2, "end": 3.6},
            {"i": 4, "text": "gaye", "line": 2, "start": None, "end": None}]}
        plan = [SimpleNamespace(words=[SimpleNamespace(box=box(0, 100, 1000)),
                                       SimpleNamespace(box=box(1, 300, 1000))]),
                SimpleNamespace(words=[SimpleNamespace(box=box(3, 200, 1100))])]
        f = song_facts(doc, frozenset({1, 2}), 5.0, 150, 30, "song", word_boxes(plan))
        self.assertEqual(f.last_line_s, 3.2)          # line 3 has no timed word: line 2 is last
        self.assertEqual(f.line_starts, (0.5, 3.2))
        self.assertEqual(f.marks, [(1.0, True, 350.0, 1030.0)])
        self.assertEqual(f.untimed_marks, ('"Dil" (line 2)',))
        self.assertEqual(f.seed, seed_of("song"))
        self.assertEqual(f.lyric_box, (100, 1000, 400, 1160))
        self.assertEqual(f.lyric_centre, (250.0, 1080.0 - 90))   # the words' block, raised a little

    def test_word_boxes_reads_beat_pops_show(self):
        show = SimpleNamespace(lines=[SimpleNamespace(words=[SimpleNamespace(box=box(5, 0, 0))])])
        self.assertEqual(list(word_boxes(show)), [5])


class PaintTest(unittest.TestCase):
    def test_envelope_never_adds_up(self):
        self.assertEqual(paint.envelope(1.0, [], 0.3, 1.5), 0.0)
        self.assertAlmostEqual(paint.envelope(2.3, [2.0], 0.3, 1.5), 1.0)
        for t in np.arange(0.0, 3.0, 0.01):
            self.assertLessEqual(paint.envelope(t, [0.0, 0.2, 0.4], 0.3, 1.5), 1.0)

    def test_finish_makes_a_frame(self):
        x = paint.gradient([(0.0, "#000000"), (1.0, "#ffffff")])
        out = paint.finish(x * 2, bloom=0.2, bloom_sigma=6, knee=0.5, soft=0.45, vig=paint.vignette(0.2))
        self.assertEqual((out.shape, out.dtype), ((H, W, 3), np.uint8))
        self.assertLess(out[H - 5, W // 2].mean(), 250)       # the shoulder: nothing burns to white


class LookTestBase(unittest.TestCase):
    WORD = (6.0, False, 700.0, 1100.0)
    MARK = (6.0, True, 700.0, 1100.0)


class RainTest(LookTestBase):  # H-034
    def test_a_word_lands_a_bloom_below_it(self):
        k = int(6.6 * 30)
        with_word = build_scene(("rain", "evening"), facts([self.WORD])).frame(k).astype(int)
        without = build_scene(("rain", "evening"), facts([])).frame(k).astype(int)
        diff = np.abs(with_word - without).max(axis=2)
        self.assertGreater(diff[1560:1760, 560:840].max(), 15)   # the ground below the word
        self.assertEqual(diff[:1300].max(), 0)                   # and nowhere else
        self.assertEqual(diff[:, :450].max(), 0)

    def test_the_same_song_draws_the_same_frame(self):
        a = build_scene(("rain", "evening"), facts([self.WORD])).frame(90)
        b = build_scene(("rain", "evening"), facts([self.WORD])).frame(90)
        np.testing.assert_array_equal(a, b)


class FogTest(LookTestBase):  # H-035
    def test_a_word_brightens_the_rays(self):
        k = int(6.3 * 30)
        with_word = build_scene(("fog", "moonlight"), facts([self.WORD])).frame(k).astype(int)
        without = build_scene(("fog", "moonlight"), facts([])).frame(k).astype(int)
        top = (slice(0, 700), slice(0, W))
        self.assertGreater(with_word[top].mean(), without[top].mean() + 0.5)


class MilanTest(LookTestBase):  # H-036
    def test_a_marked_word_brings_a_meeting_near_it(self):
        scene = build_scene(("milan", "night"), facts([self.MARK]))
        scene.frame(int(6.2 * 30))
        marked = [b for b in scene.blooms if b[3]]
        self.assertEqual(len(marked), 1)
        t, x, y, _ = marked[0]
        self.assertAlmostEqual(t, 6.0, delta=1 / 30 + 1e-6)
        self.assertEqual((x, y), (700.0, LYRICS[3] + 130.0))   # under the word, below the lyrics

    def test_dots_dim_behind_the_text(self):
        calm, plain = (build_scene(("milan", "night"), facts([])) for _ in range(2))
        ink = (300, 900, 800, 1100)
        box = (slice(900, 1100), slice(300, 800))
        bright = []
        for k in range(1, 400, 20):    # 13 s of drifting dots, a frame every 2/3 s
            self.assertLess(calm.frame(k, ink)[box].max(), 140, f"frame {k}")
            bright.append(plain.frame(k, None)[box].max())
        self.assertGreater(max(bright), 140)       # without text there, dots pass bright

    def test_frames_come_in_order(self):
        scene = build_scene(("milan", "night"), facts([]))
        scene.frame(5)
        with self.assertRaisesRegex(ValueError, "in order"):
            scene.frame(3)


class ComposeTest(unittest.TestCase):  # red line 2
    def test_the_overlay_is_laid_over_as_it_is(self):
        bg = np.full((H, W, 3), 40, np.uint8)
        scene = SimpleNamespace(frame=lambda k, ink: bg)
        ov = np.zeros((H, W, 4), np.uint8)
        ov[1000:1100, 400:700] = (250, 240, 230, 255)
        out = np.frombuffer(compose_frame(ov.tobytes(), scene, 0, THEME.text_rgb, Legibility()),
                            np.uint8).reshape(H, W, 4)
        np.testing.assert_array_equal(out[1000:1100, 400:700, :3], ov[1000:1100, 400:700, :3])
        np.testing.assert_array_equal(out[:900, :, :3], bg[:900])
        self.assertTrue((out[..., 3] == 255).all())


class DrawnAheadTest(unittest.TestCase):
    def test_worker_frames_are_the_frames_drawn_here(self):
        f = facts([LookTestBase.MARK], duration=0.1)             # 3 frames
        here = build_scene(("fog", "moonlight"), f)
        frames = list(drawn_ahead(("fog", "moonlight"), f, workers=2))
        self.assertEqual(len(frames), 3)
        for k, frame in enumerate(frames):
            np.testing.assert_array_equal(frame, here.frame(k))

    def test_only_a_simulation_is_drawn_in_order(self):
        from lyric_engine.background import fog, milan, rain
        self.assertEqual([m.Scene.in_order for m in (rain, fog, milan)], [False, False, True])


class LegibilityTest(unittest.TestCase):
    def test_a_bright_background_fails_and_a_dim_one_passes(self):
        box = (300, 1000, 700, 1100)
        bright = np.full((H, W, 3), 235, np.uint8)
        c = frame_contrast(bright, THEME.text_rgb, box)
        self.assertLess(c, 3.0)
        self.assertGreaterEqual(frame_contrast(np.full((H, W, 3), 30, np.uint8), THEME.text_rgb, box), 3.0)
        log = Legibility()
        log.note(12, c)
        log.note(13, 5.0)
        self.assertEqual(log.worst, (12, c))
        with mock.patch("lyric_engine.render.check._probe",
                        return_value={"size": (W, H), "rate": "30/1", "frames": 10,
                                      "pix_fmt": "yuv420p", "codec": "h264", "audio": True}):
            fails = final_checks(Path("final_milan_night.mp4"), 10, THEME, log)
        self.assertEqual(fails, [f"legibility: 1 frame(s) below 3:1 around the text; first: "
                                 f"frame 12 ({c:.2f}:1)"])


class BackgroundRenderTest(unittest.TestCase):  # AC1, AC3
    def test_render_writes_a_finished_short_and_leaves_the_overlay_alone(self):
        with tempfile.TemporaryDirectory() as tmp:
            song = make_song(Path(tmp), lyrics="Mere\n*saamne*\n", duration=2.0)
            plain = render.render(song, codec="qtrle", theme=THEME)
            hashes = {key: _frame_hash(p) for key, p in plain.outputs.items()}
            result = render.render(song, codec="qtrle", theme=THEME, bg=("milan", "night"))
            self.assertEqual(result.checks, [])
            self.assertEqual(result.outputs["final"].name, "final_milan_night.mp4")
            self.assertEqual({key: _frame_hash(result.outputs[key]) for key in hashes}, hashes)
            report = (result.render_dir / "report.md").read_text(encoding="utf-8")
            self.assertIn("## Background", report)
            self.assertIn("marked 1", report)
            render.render(song, codec="qtrle", theme=THEME)
            report = (result.render_dir / "report.md").read_text(encoding="utf-8")
            self.assertNotIn("## Background", report)


class WorkerRenderTest(unittest.TestCase):   # a look drawn out of order, in worker processes
    def test_render_with_workers_passes_and_leaves_the_overlay_alone(self):
        with tempfile.TemporaryDirectory() as tmp:
            song = make_song(Path(tmp), lyrics="Mere\n*saamne*\n", duration=2.0)
            plain = render.render(song, codec="qtrle", theme=THEME)
            hashes = {key: _frame_hash(p) for key, p in plain.outputs.items()}
            with mock.patch("lyric_engine.background.compose.WORKERS", 2):
                result = render.render(song, codec="qtrle", theme=THEME, bg=("fog", "moonlight"))
            self.assertEqual(result.checks, [])
            self.assertEqual(_streams(result.outputs["final"], "v:0"), ["h264,60"])
            self.assertEqual({key: _frame_hash(result.outputs[key]) for key in hashes}, hashes)


class EveryLookTest(unittest.TestCase):
    def test_each_look_draws_a_frame_with_no_words(self):   # the song-independent mode
        for look, (mood, *_rest) in WORLDS.items():
            with self.subTest(look=look):
                scene = build_scene((look, mood), facts([]))
                frame = scene.frame(0)
                self.assertEqual((frame.shape, frame.dtype), ((H, W, 3), np.uint8))
                self.assertIsInstance(scene.describe(), str)
                self.assertIsInstance(scene.in_order, bool)
                if not scene.in_order:               # a pure function of the frame number
                    np.testing.assert_array_equal(frame, scene.frame(0))


class KhaaliTest(LookTestBase):  # H-037
    def test_warm_on_a_marked_word_and_the_lamp_goes_out(self):
        self.assertEqual(khaali.memory_level(5.0, [6.0]), 0.0)
        self.assertAlmostEqual(khaali.memory_level(7.0, [6.0]), 0.9)
        self.assertEqual(khaali.memory_level(12.0, [6.0]), 0.0)
        self.assertEqual(khaali.lamp_level(5.0, 10.0), 1.0)
        self.assertEqual(khaali.lamp_level(13.0, 10.0), 0.0)

    def test_the_frame_turns_warm_then_dark(self):
        scene = build_scene(("khaali", "night"), facts([self.MARK], last=10.0))
        lamp = (slice(520, 700), slice(560, 800))
        cold, warm, dark = (scene.frame(int(t * 30)).astype(float) for t in (5.0, 7.2, 13.0))
        ratio = lambda f: f[lamp][..., 0].mean() / f[lamp][..., 2].mean()    # red over blue
        self.assertGreater(ratio(warm), ratio(cold) + 0.3)
        self.assertGreater(cold[lamp].mean(), dark[lamp].mean() + 30)


def _streams(path: Path, kind: str) -> list[str]:
    out = subprocess.run(["ffprobe", "-v", "error", "-select_streams", kind, "-count_packets",
                          "-show_entries", "stream=codec_name,nb_read_packets", "-of", "csv=p=0", str(path)],
                         capture_output=True, text=True, check=True).stdout
    return out.split()


class BackdropTest(unittest.TestCase):  # step 0: the look without lyrics
    def test_generic_backdrop_has_the_length_asked_and_no_audio(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = backdrop.make_generic(("milan", "night"), 0.5, Path(tmp) / "b.mp4")
            self.assertEqual(_streams(out, "v:0"), ["h264,15"])
            self.assertEqual(_streams(out, "a"), [])

    def test_song_backdrop_writes_only_the_backdrop_with_the_songs_audio(self):
        with tempfile.TemporaryDirectory() as tmp:
            song = make_song(Path(tmp), lyrics="Mere\n*saamne*\n", duration=2.0)
            result = render.render(song, codec="qtrle", theme=THEME, bg=("milan", "night"),
                                   backdrop=True)
            self.assertEqual(result.checks, [])
            self.assertEqual([p.name for p in result.render_dir.iterdir()], ["backdrop_milan_night.mp4"])
            out = result.outputs["backdrop"]
            self.assertEqual(_streams(out, "v:0"), ["h264,60"])
            self.assertEqual(len(_streams(out, "a")), 1)
            with self.assertRaises(render.RenderError):
                render.render(song, codec="qtrle", theme=THEME, backdrop=True)

    def test_cli_wants_a_song_or_seconds(self):
        for argv in (["backdrop", "--bg", "rain"], ["backdrop", "songs/x", "--seconds", "5", "--bg", "rain"]):
            err = io.StringIO()
            with redirect_stderr(err):
                self.assertEqual(cli.main(argv), 2)
            self.assertIn("song folder, or --seconds", err.getvalue())


def _frame_hash(path: Path) -> str:
    out = subprocess.run(["ffmpeg", "-v", "error", "-i", str(path), "-map", "0:v", "-f",
                          "framemd5", "-"], capture_output=True, text=True, check=True).stdout
    return "\n".join(line for line in out.splitlines() if not line.startswith("#"))


if __name__ == "__main__":
    unittest.main()
