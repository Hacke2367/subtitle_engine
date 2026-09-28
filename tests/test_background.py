"""background/ (engine-made backgrounds; spec 17): --bg names, song facts, the room's arc, gusts,
seed and picks, the compose step (text shadows and tint, alpha untouched), the legibility rule,
the CLI, and a short end-to-end render with a finished short.

The room tests build the real room (about a second); the render test uses a short real ffmpeg
encode (qtrle).
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
from lyric_engine.background import SongFacts, paint, parse_bg, seed_of, song_facts
from lyric_engine.background.compose import (Legibility, compose_frame, final_checks,
                                             frame_contrast)
from lyric_engine.background.room import DUSK, GOLD, ROSE, SKY, Room
from lyric_engine.theme import SOFT_ROMANTIC_V2 as THEME
from tests.test_render import make_song

W, H = 1080, 1920


def facts(name="khidki_s2_em", duration=14.0, last=10.0, marks=()) -> SongFacts:
    return SongFacts(name, seed_of(name), duration, int(duration * 30), 30, last,
                     tuple((s, f'"w{i}" (line 1)') for i, s in enumerate(marks)), ())


def bare(f: SongFacts, **attrs) -> Room:
    """A Room without its art: enough for the arc, the lamp and the gusts."""
    room = Room.__new__(Room)
    room.facts, room.look = f, DUSK
    room.gust_times = [s for s, _ in f.marks]
    for key, value in attrs.items():
        setattr(room, key, value)
    return room


def overlay(ink_box=None, rgb=(255, 243, 230)) -> bytes:
    """A transparent frame, optionally with a solid block of text-coloured ink."""
    ov = np.zeros((H, W, 4), np.uint8)
    if ink_box:
        x0, y0, x1, y1 = ink_box
        ov[y0:y1, x0:x1, :3] = rgb
        ov[y0:y1, x0:x1, 3] = 255
    return ov.tobytes()


class ParseBgTest(unittest.TestCase):  # AC9
    def test_default_mood_and_explicit_mood(self):
        self.assertEqual(parse_bg("room"), ("room", "dusk"))
        self.assertEqual(parse_bg("room:dusk"), ("room", "dusk"))

    def test_refusals_name_the_choices(self):
        with self.assertRaisesRegex(ValueError, r"unknown background 'truck'; built: room"):
            parse_bg("truck")
        with self.assertRaisesRegex(ValueError, r"room:rain is designed but not built yet "
                                                r"\(plan step 23\); built: dusk"):
            parse_bg("room:rain")
        with self.assertRaisesRegex(ValueError, r"unknown mood 'noon' for room; built: dusk"):
            parse_bg("room:noon")


class CliTest(unittest.TestCase):  # AC9
    def test_render_refuses_an_unbuilt_mood(self):
        err = io.StringIO()
        with redirect_stderr(err), self.assertRaises(SystemExit) as ctx:
            cli.main(["render", "songs/x", "--bg", "room:rain"])
        self.assertEqual(ctx.exception.code, 2)
        self.assertIn("not built yet", err.getvalue())

    def test_make_passes_the_background_through(self):
        with mock.patch("lyric_engine.workflow.ensure_aligned", return_value=0), \
                mock.patch.object(cli, "_render", return_value=0) as rendered:
            self.assertEqual(cli.main(["make", "songs/x", "--bg", "room"]), 0)
        self.assertEqual(rendered.call_args.args[-1], ("room", "dusk"))


class SongFactsTest(unittest.TestCase):  # red line 1: only aligned times
    def test_last_line_and_marks(self):
        doc = {"words": [
            {"i": 0, "text": "Jis", "line": 0, "start": 0.5, "end": 0.8},
            {"i": 1, "text": "dekha", "line": 0, "start": 1.0, "end": 1.5},
            {"i": 2, "text": "Dil", "line": 1, "start": None, "end": None},
            {"i": 3, "text": "thaam", "line": 1, "start": 3.2, "end": 3.6},
            {"i": 4, "text": "gaye", "line": 2, "start": None, "end": None}]}
        f = song_facts(doc, frozenset({1, 2}), 5.0, 150, 30, "song")
        self.assertEqual(f.last_line_s, 3.2)   # line 3 has no timed word: line 2 is the last shown
        self.assertEqual(f.marks, ((1.0, '"dekha" (line 1)'),))
        self.assertEqual(f.untimed_marks, ('"Dil" (line 2)',))
        self.assertEqual(f.seed, seed_of("song"))


class RoomTestBase(unittest.TestCase):
    room: Room

    @classmethod
    def setUpClass(cls):
        cls.room = Room(facts(marks=(2.0,)), DUSK)


class ArcTest(RoomTestBase):  # AC5
    def test_keyframes_and_lamp(self):
        r = self.room
        sun, _, _, lamp, _ = r.arc(0.0)
        np.testing.assert_allclose(sun, GOLD, atol=1e-6)
        np.testing.assert_allclose(r.arc(7.0)[0], ROSE, atol=1e-6)   # 0.7 of the way
        sun, sun_i, ambient, _, f = r.arc(10.0)
        np.testing.assert_allclose(sun, SKY, atol=1e-6)
        np.testing.assert_allclose(ambient, DUSK.ambient_keys[-1][1], atol=1e-6)
        self.assertEqual(f, 1.0)
        self.assertEqual(lamp, 0.0)
        self.assertEqual(r.lamp_level(9.99), 0.0)
        self.assertGreater(r.lamp_level(10.01), 0.0)
        self.assertEqual(r.lamp_level(10.0 + DUSK.lamp_flicker_s + DUSK.lamp_ramp_s + 0.01), 1.0)
        self.assertEqual(r.lamp_level(13.9), 1.0)   # the outro holds

    def test_same_fractions_for_a_short_and_a_long_song(self):
        long = bare(facts(duration=172.0, last=150.0))
        for frac in (0.0, 0.25, 0.5, 0.7, 0.95, 1.0):
            a, b = self.room.arc(10.0 * frac), long.arc(150.0 * frac)
            for x, y in zip(a, b):
                np.testing.assert_allclose(x, y, atol=1e-5)

    def test_no_shown_line_means_no_lamp(self):
        r = bare(facts(last=None))
        self.assertEqual(r.lamp_level(13.0), 0.0)
        self.assertAlmostEqual(r.fraction(7.0), 0.5)


class GustTest(RoomTestBase):  # AC6
    def test_envelope(self):
        self.assertEqual(paint.envelope(1.0, [], 0.35, 1.6), 0.0)
        self.assertEqual(paint.envelope(1.99, [2.0], 0.35, 1.6), 0.0)
        self.assertAlmostEqual(paint.envelope(2.35, [2.0], 0.35, 1.6), 1.0)
        self.assertEqual(paint.envelope(3.6, [2.0], 0.35, 1.6), 0.0)

    def test_overlapping_gusts_never_add_up(self):
        for t in np.arange(0.0, 3.0, 0.01):
            self.assertLessEqual(paint.envelope(t, [0.0, 0.2, 0.4], 0.35, 1.6), 1.0)

    def test_room_gusts_at_marked_words_only(self):
        self.assertEqual(self.room.gust(1.9), 0.0)
        self.assertGreater(self.room.gust(2.3), 0.9)
        self.assertEqual(bare(facts()).gust(2.3), 0.0)


class SeedTest(RoomTestBase):  # AC8
    def test_stable_seed_and_identical_frames(self):
        self.assertEqual(seed_of("khidki_s2_em"), 573687872)   # crc32: the same on every machine
        again = Room(facts(marks=(2.0,)), DUSK)
        self.assertEqual(again.picks, self.room.picks)
        np.testing.assert_array_equal(again.albedo, self.room.albedo)
        for k in (0, 65, 330):
            a, b = self.room.light(k), again.light(k)
            np.testing.assert_array_equal(a.sun, b.sun)
            np.testing.assert_array_equal(a.air, b.air)

    def test_two_test_folders_differ(self):
        other = Room(facts(name="khidki_s2"), DUSK)
        self.assertNotEqual(other.picks, self.room.picks)
        self.assertIn("dupatta", self.room.picks.describe())


class ComposeTest(RoomTestBase):  # AC4, red line 2
    def test_text_is_the_overlay_tinted_and_the_rest_is_the_room(self):
        k, box = 60, (400, 900, 600, 980)
        empty = np.frombuffer(compose_frame(overlay(), self.room, k, THEME.text_rgb, Legibility()),
                              np.uint8).reshape(H, W, 4)
        lit = np.frombuffer(compose_frame(overlay(box), self.room, k, THEME.text_rgb, Legibility()),
                            np.uint8).reshape(H, W, 4)
        self.assertTrue((lit[..., 3] == 255).all())
        far = np.ones((H, W), bool)   # beyond the ink, its shadows and their blur
        far[box[1] - 120:box[3] + 120, box[0] - 120:box[2] + 120] = False
        np.testing.assert_array_equal(lit[far], empty[far])
        tint = self.room.light(k).tint
        expected = np.round(np.asarray(THEME.text_rgb) * np.round(255 * tint) / 255)
        ink = lit[box[1]:box[3], box[0]:box[2], :3].reshape(-1, 3)
        self.assertLessEqual(np.abs(ink - expected).max(), 1)   # the room never shows through

    def test_tint_is_bounded(self):
        for k in range(0, 420, 15):
            tint = self.room.light(k).tint
            self.assertTrue(((tint >= 0.9) & (tint <= 1.0)).all(), (k, tint))

    def test_the_shadow_darkens_only_near_the_ink(self):
        k, box = 30, (400, 900, 600, 980)   # afternoon: the sun shadow falls down-right
        empty = np.frombuffer(compose_frame(overlay(), self.room, k, THEME.text_rgb, Legibility()),
                              np.uint8).reshape(H, W, 4).astype(int)
        lit = np.frombuffer(compose_frame(overlay(box), self.room, k, THEME.text_rgb, Legibility()),
                            np.uint8).reshape(H, W, 4).astype(int)
        below = (slice(box[3] + 2, box[3] + 10), slice(box[0] + 20, box[2]))
        self.assertLess(lit[below][..., :3].sum(), empty[below][..., :3].sum())


class LegibilityTest(unittest.TestCase):  # AC7
    def test_a_bright_wall_fails_and_a_dim_one_passes(self):
        box = (300, 800, 700, 900)
        bright = SimpleNamespace(albedo_half=np.ones((H // 2, W // 2, 3), np.float32))
        light = np.full((H // 2, W // 2, 3), 0.9, np.float32)
        c = frame_contrast(bright, light, THEME.text_rgb, np.ones(3, np.float32), box)
        self.assertLess(c, 3.0)
        log = Legibility()
        log.note(12, c)
        log.note(13, 5.0)
        self.assertEqual(log.worst, (12, c))
        with mock.patch("lyric_engine.render.check._probe",
                        return_value={"size": (W, H), "rate": "30/1", "frames": 10,
                                      "pix_fmt": "yuv420p", "codec": "h264", "audio": True}):
            fails = final_checks(Path("final_room_dusk.mp4"), 10, THEME, log)
        self.assertEqual(fails, [f"legibility: 1 frame(s) below 3:1 in the lyric area; first: "
                                 f"frame 12 ({c:.2f}:1)"])
        dim = frame_contrast(bright, light * 0.2, THEME.text_rgb, np.ones(3, np.float32), box)
        self.assertGreaterEqual(dim, 3.0)


class BackgroundRenderTest(unittest.TestCase):  # AC1, AC3
    def test_render_writes_a_finished_short_and_leaves_the_overlay_alone(self):
        with tempfile.TemporaryDirectory() as tmp:
            song = make_song(Path(tmp), lyrics="Mere\n*saamne*\n", duration=2.0)
            plain = render.render(song, codec="qtrle", theme=THEME)
            hashes = {key: _frame_hash(p) for key, p in plain.outputs.items()}
            result = render.render(song, codec="qtrle", theme=THEME, bg=("room", "dusk"))
            self.assertEqual(result.checks, [])
            final = result.outputs["final"]
            self.assertEqual(final.name, "final_room_dusk.mp4")
            self.assertEqual({key: _frame_hash(result.outputs[key]) for key in hashes}, hashes)
            report = (result.render_dir / "report.md").read_text(encoding="utf-8")
            self.assertIn("## Background", report)
            self.assertIn("- Gusts (marked words): 1.00 s \"saamne\" (line 2)", report)
            render.render(song, codec="qtrle", theme=THEME)
            report = (result.render_dir / "report.md").read_text(encoding="utf-8")
            self.assertNotIn("## Background", report)


def _frame_hash(path: Path) -> str:
    out = subprocess.run(["ffmpeg", "-v", "error", "-i", str(path), "-map", "0:v", "-f",
                          "framemd5", "-"], capture_output=True, text=True, check=True).stdout
    return "\n".join(line for line in out.splitlines() if not line.startswith("#"))


if __name__ == "__main__":
    unittest.main()
