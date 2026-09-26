"""render.py: timeline maths, word/line state, refusals, sprites, frames, one 2 s end-to-end render.

Everything except the end-to-end test is offline and font-free: layouts are hand-made WordBoxes
(injected layout_fn) and sprite masks are mocked.
"""
from __future__ import annotations

import dataclasses
import hashlib
import shutil
import tempfile
import unittest
import wave
from pathlib import Path
from unittest import mock

from PIL import Image

from lyric_engine import render, timing
from lyric_engine.layout import LineLayout, WordBox
from lyric_engine.render import LinePlan, RenderError, WordPlan
from lyric_engine.theme import SOFT_ROMANTIC as THEME

W, H = THEME.width, THEME.height   # fps 30, lead 0.05 s, reveal 6 frames, fade 8 frames


def fake_layout(words, line, theme, emphasis=frozenset()):
    """One row of 100x80 boxes, 120 px apart: layout geometry without fonts."""
    return LineLayout(line, theme.font_size, tuple(
        WordBox(i, text, 100 + 120 * k, 1000, 100, 80) for k, (i, text) in enumerate(words)))


def word(i, text, line, start, end, reasons=()):
    return {"i": i, "text": text, "line": line, "start": start, "end": end, "score": 0.9,
            "flagged": bool(reasons), "reasons": list(reasons)}


def plan(words, n_frames=300, layout_fn=fake_layout):
    return render.plan_timeline({"words": words}, THEME, n_frames, layout_fn=layout_fn)


def make_song(root: Path, lyrics: str = "Mere\nsaamne\n", times=((0.3, 0.7), (1.0, 1.6)),
              duration: float = 2.0) -> Path:
    """A song folder: silent audio.wav, lyrics.txt and a words.json made by timing's own writers."""
    song = root / "song"
    song.mkdir()
    audio = song / "audio.wav"
    with wave.open(str(audio), "wb") as w:   # silence, 16 kHz mono
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(16000)
        w.writeframes(b"\x00\x00" * round(16000 * duration))
    (song / "lyrics.txt").write_text(lyrics, encoding="utf-8")
    lyrics_obj = timing.read_lyrics(song / "lyrics.txt")
    words = timing.build_words(lyrics_obj, [timing.RawWord(s, e, None if s is None else 0.9)
                                            for s, e in times])
    timing.apply_flags(words, duration, None)
    doc = timing.make_doc("song", audio, duration, timing.sha256_file(audio), lyrics_obj,
                          {"variant": "test", "input": "raw", "settings": {}}, words)
    timing.save_words(song / "words.json", doc)
    return song


class PlanTimelineTest(unittest.TestCase):
    def test_reveal_and_end_frames(self):  # AC1: reveal = floor((start − lead)·fps)
        lines, skipped = plan([word(0, "Mere", 0, 1.04, 1.34), word(1, "saamne", 0, 1.44, 2.24)])
        # (1.04 − 0.05)·30 = 29.7 → 29, (1.44 − 0.05)·30 = 41.7 → 41; ends 38.7 → 38, 65.7 → 65
        self.assertEqual([(wp.reveal, wp.end) for wp in lines[0].words], [(29, 38), (41, 65)])
        self.assertEqual(lines[0].first, 29)
        self.assertEqual(skipped, [])

    def test_exact_frame_boundary_not_floored_early(self):
        # (0.35 − 0.05)·30 and (1.05 − 0.05)·30 are exactly 9 and 30; float noise must not floor
        lines, _ = plan([word(0, "a", 0, 0.35, 0.5), word(1, "b", 0, 1.05, 1.2)])
        self.assertEqual([wp.reveal for wp in lines[0].words], [9, 30])

    def test_reveal_clamped_at_zero(self):
        lines, _ = plan([word(0, "a", 0, 0.02, 0.3), word(1, "b", 0, 0.0, 0.3)])
        self.assertEqual([wp.reveal for wp in lines[0].words], [0, 0])

    def test_end_never_before_reveal(self):  # a flagged bad_duration word (allowed)
        lines, _ = plan([word(0, "a", 0, 1.0, 0.9, ("bad_duration",))])
        self.assertEqual((lines[0].words[0].reveal, lines[0].words[0].end), (28, 28))

    def test_natural_stop_hold_and_fade(self):
        lines, _ = plan([word(0, "a", 0, 1.0, 1.5), word(1, "b", 0, 1.6, 2.0)])
        lp = lines[0]
        self.assertEqual(lp.stop, 78)          # ceil((2.0 + 0.6)·30)
        self.assertEqual(lp.fade_start, 70)    # stop − round(0.25·30)

    def test_stop_clamped_to_next_line_first(self):  # AC1: visibility ends before the next line
        lines, _ = plan([word(0, "a", 0, 1.0, 1.5), word(1, "b", 1, 1.8, 2.2)])
        self.assertEqual(lines[1].first, 52)   # floor(1.75·30)
        self.assertEqual(lines[0].stop, 52)    # natural ceil(2.1·30) = 63, clamped
        self.assertEqual(lines[0].fade_start, 44)

    def test_stop_clamped_to_frame_count(self):
        lines, _ = plan([word(0, "a", 0, 1.0, 1.5)], n_frames=50)
        self.assertEqual(lines[0].stop, 50)

    def test_close_lines_shorten_the_fade(self):
        lines, _ = plan([word(0, "a", 0, 1.04, 1.1), word(1, "b", 1, 1.2, 1.4)])
        # D-013: "a" reveals over frames 29-35 but "b" starts at 34, so the fade shortens to a
        # cut: full opacity until the next line, never dimmed mid-reveal
        self.assertEqual((lines[0].first, lines[0].stop, lines[0].fade_start), (29, 34, 34))
        self.assertEqual(render.line_opacity(lines[0], 33), 1.0)
        self.assertEqual(render.line_opacity(lines[0], 34), 0.0)

    def test_fade_waits_for_last_word_reveal(self):  # D-013
        # "b" (line 0's last word) reveals at frame 58; the next line starts at 67. The old rule
        # (stop - 8 = 59) would dim "b" mid-reveal; the fade now starts once it settles (64).
        lines, _ = plan([word(0, "a", 0, 1.0, 1.5), word(1, "b", 0, 2.0, 2.1),
                         word(2, "c", 1, 2.3, 2.6)])
        self.assertEqual((lines[0].stop, lines[0].fade_start), (67, 64))

    def test_line_without_timed_word_is_skipped(self):
        lines, skipped = plan([word(0, "a", 0, 1.0, 1.5),
                               word(1, "b", 1, None, None, ("not_placed",)),
                               word(2, "c", 2, 3.0, 3.5)])
        self.assertEqual([lp.layout.line for lp in lines], [0, 2])
        self.assertEqual(skipped, [1])

    def test_untimed_word_is_static(self):  # AC1: --allow-flagged gives no animation
        lines, _ = plan([word(0, "a", 0, 1.0, 1.5), word(1, "b", 0, None, None, ("not_placed",))])
        wp = lines[0].words[1]
        self.assertEqual((wp.reveal, wp.end), (None, None))
        for n in (0, 28, 29, 40, 100):
            self.assertEqual(render.word_state(wp, n, THEME), (1.0, 0.0, 0.0))

    def test_one_line_on_screen_even_when_a_flagged_word_jumps_back(self):
        lines, _ = plan([word(0, "a", 0, 1.0, 1.5), word(1, "b", 0, 2.0, 2.5),
                         word(2, "c", 1, 0.5, 0.8, ("out_of_order",)), word(3, "d", 1, 3.0, 3.4),
                         word(4, "e", 2, 4.0, 4.5)])
        self.assertEqual([lp.layout.line for lp in lines], [1, 0, 2])   # time order
        for a, b in zip(lines, lines[1:]):
            self.assertLessEqual(a.stop, b.first)
        for n in range(300):
            self.assertLessEqual(sum(render.line_opacity(lp, n) > 0 for lp in lines), 1)

    def test_layout_must_keep_the_words_json_text(self):  # red line 2
        def lowercasing(words, line, theme, emphasis=frozenset()):
            lay = fake_layout(words, line, theme)
            return dataclasses.replace(lay, words=tuple(dataclasses.replace(b, text=b.text.lower())
                                                        for b in lay.words))
        with self.assertRaises(AssertionError):
            plan([word(0, "Mere", 0, 1.0, 1.5)], layout_fn=lowercasing)


class WordStateTest(unittest.TestCase):
    wp = WordPlan(WordBox(0, "Mere", 0, 0, 10, 10), reveal=30, end=45, text="Mere")
    # The maths is tested on pinned motion values, so look tuning in theme.py can't break it.
    theme = dataclasses.replace(THEME, fps=30, reveal_s=0.20, rise_px=12, glow_in_s=0.08,
                                glow_out_s=0.30)

    def state(self, n, wp=None):
        return tuple(round(v, 3) for v in render.word_state(wp or self.wp, n, self.theme))

    def test_before_reveal(self):
        self.assertEqual(self.state(29), (0, 0, 0))

    def test_reveal_frames(self):
        self.assertEqual(self.state(30), (0, 12, 0))         # progress 0, fully lowered
        self.assertEqual(self.state(33), (0.5, 6, 1))        # half-way; glow ramped in (2.4 fr)
        self.assertEqual(self.state(36), (1, 0, 1))          # revealed, at rest

    def test_glow_holds_until_end_then_fades(self):
        self.assertEqual(self.state(45), (1, 0, 1))
        self.assertEqual(self.state(48), (1, 0, 0.667))      # 3 of 9 fade frames
        self.assertEqual(self.state(54), (1, 0, 0))
        self.assertEqual(self.state(500), (1, 0, 0))         # sung words stay visible

    def test_short_word_glow_is_continuous(self):
        wp = dataclasses.replace(self.wp, end=30)
        self.assertEqual([self.state(n, wp)[2] for n in (30, 31, 32, 39)],
                         [0, 0.417, 0.778, 0])


class LineOpacityTest(unittest.TestCase):
    def test_span_and_linear_fade(self):
        lp = LinePlan(LineLayout(0, 84, ()), first=10, stop=30, fade_start=22, words=[])
        self.assertEqual([render.line_opacity(lp, n) for n in (9, 10, 21, 22, 26, 29, 30)],
                         [0, 1, 1, 1, 0.5, 0.125, 0])


class LoadForRenderTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def test_valid_song_loads(self):
        doc, audio, emphasis = render.load_for_render(make_song(self.root), allow_flagged=False)
        self.assertEqual(audio.name, "audio.wav")
        self.assertEqual([w["text"] for w in doc["words"]], ["Mere", "saamne"])
        self.assertEqual(emphasis, frozenset())

    def test_flagged_words_refused_and_listed(self):
        song = make_song(self.root, times=((0.3, 0.7), (None, None)))
        with self.assertRaises(RenderError) as ctx:
            render.load_for_render(song, allow_flagged=False)
        self.assertIn('word 1 "saamne" (line 2): not_placed', str(ctx.exception))
        self.assertIn("--allow-flagged", str(ctx.exception))
        doc, _, _ = render.load_for_render(song, allow_flagged=True)
        self.assertTrue(doc["words"][1]["flagged"])

    def test_stale_lyrics_refused(self):
        song = make_song(self.root)
        (song / "lyrics.txt").write_text("Mere\nSaamne\n", encoding="utf-8")
        with self.assertRaises(RenderError) as ctx:
            render.load_for_render(song, allow_flagged=True)   # never allowed, even with the flag
        self.assertIn("stale", str(ctx.exception))
        self.assertIn("--overwrite", str(ctx.exception))

    def test_stale_audio_refused(self):
        song = make_song(self.root)
        with wave.open(str(song / "audio.wav"), "wb") as w:
            w.setnchannels(1)
            w.setsampwidth(2)
            w.setframerate(16000)
            w.writeframes(b"\x00\x00" * 16000)
        with self.assertRaises(RenderError) as ctx:
            render.load_for_render(song, allow_flagged=False)
        self.assertIn("stale: audio.wav", str(ctx.exception))

    def test_invalid_hand_edit_refused_with_validator_messages(self):
        song = make_song(self.root)
        doc = timing.load_words(song / "words.json")
        doc["words"][1]["end"] = 0.9   # before its start, but not flagged
        timing.save_words(song / "words.json", doc)
        with self.assertRaises(RenderError) as ctx:
            render.load_for_render(song, allow_flagged=True)
        self.assertIn("end 0.9 is not after start 1.0", str(ctx.exception))

    def test_missing_or_broken_words_json(self):
        song = make_song(self.root)
        (song / "words.json").write_text("{", encoding="utf-8")
        with self.assertRaisesRegex(RenderError, "not valid JSON"):
            render.load_for_render(song, allow_flagged=False)
        (song / "words.json").unlink()
        with self.assertRaisesRegex(RenderError, "run `align"):
            render.load_for_render(song, allow_flagged=False)

    def test_render_refuses_before_writing_anything(self):
        song = make_song(self.root, times=((0.3, 0.7), (None, None)))
        with self.assertRaises(RenderError):
            render.render(song)
        with self.assertRaisesRegex(RenderError, "unknown codec"):
            render.render(song, codec="h265")
        self.assertFalse((song / "render").exists())


class BuildSpritesTest(unittest.TestCase):
    def setUp(self):
        self.lines, _ = plan([word(0, "Mere", 0, 1.0, 1.5), word(1, "saamne,", 0, 1.6, 2.0),
                              word(2, "Kuchh", 1, 3.0, 3.5)])
        self.drawn = []

        def word_mask(text, fonts, pad=0):   # the size layout measured: 100x80 (+ pad)
            self.drawn.append(text)
            mask = Image.new("L", (100 + 2 * pad, 80 + 2 * pad), 0)
            mask.paste(255, (pad + 10, pad + 10, pad + 90, pad + 70))
            return mask
        patches = [mock.patch.object(render.layout, "font_set", create=True,
                                     return_value=object()),
                   mock.patch.object(render.layout, "word_mask", word_mask, create=True)]
        for p in patches:
            p.start()
            self.addCleanup(p.stop)

    def test_drawn_strings_are_the_words_json_text(self):  # AC5
        sprites = render.build_sprites(self.lines, THEME)
        self.assertEqual(self.drawn, ["Mere", "saamne,", "Kuchh"])
        pad = 3 * THEME.glow_radius
        for text_img, glow_img, p in sprites.values():
            self.assertEqual(p, pad)
            self.assertEqual(text_img.size, (100 + 2 * pad, 80 + 2 * pad))
            self.assertEqual(glow_img.size, text_img.size)

    def test_straight_alpha_colours(self):  # solid colour layers: no dark fringe pixels
        text_img, glow_img, pad = render.build_sprites(self.lines, THEME)[0]
        self.assertEqual(glow_img.convert("RGB").getextrema(),
                         tuple((c, c) for c in THEME.glow_rgb))
        self.assertEqual(text_img.getpixel((pad + 50, pad + 40)), (*THEME.text_rgb, 255))

    def test_text_mismatch_raises_before_drawing(self):  # red line 2
        lp = self.lines[0]
        lp.words[0] = dataclasses.replace(lp.words[0], text="mere")
        with self.assertRaises(AssertionError):
            render.build_sprites(self.lines, THEME)
        self.assertEqual(self.drawn, [])

    def test_mask_must_match_the_layout_box(self):
        wp = self.lines[0].words[0]
        self.lines[0].words[0] = dataclasses.replace(wp, box=dataclasses.replace(wp.box, w=99))
        with self.assertRaises(AssertionError):
            render.build_sprites(self.lines, THEME)


class ComposeFrameTest(unittest.TestCase):
    def setUp(self):
        self.box = WordBox(0, "Mere", 100, 200, 10, 10)
        self.lines = [LinePlan(LineLayout(0, 84, (self.box,)), first=30, stop=90, fade_start=82,
                               words=[WordPlan(self.box, 30, 45, "Mere")])]
        text = Image.new("RGBA", (14, 14), (0, 0, 0, 0))
        text.paste((*THEME.text_rgb, 255), (2, 2, 12, 12))
        glow = Image.new("RGBA", (14, 14), (*THEME.glow_rgb, 0))   # invisible: isolates the text
        self.sprites = {0: (text, glow, 2)}

    def frame(self, n, lines=None):
        return render.compose_frame(n, self.lines if lines is None else lines, self.sprites, THEME)

    @staticmethod
    def alpha(frame, x, y):
        return frame[(y * W + x) * 4 + 3]

    def test_empty_frame_is_all_zero(self):
        for f in (self.frame(0), self.frame(30), self.frame(90), self.frame(5, lines=[])):
            self.assertEqual(len(f), W * H * 4)
            self.assertEqual(f.count(0), len(f))
        self.assertIs(self.frame(0), self.frame(95))   # one shared zero frame

    def test_word_solid_after_reveal(self):
        f, at = self.frame(40), (205 * W + 105) * 4
        self.assertEqual(len(f), W * H * 4)
        self.assertEqual(f[at:at + 4], bytes((*THEME.text_rgb, 255)))
        self.assertEqual(self.alpha(f, 50, 50), 0)

    def test_rise_starts_below_rest(self):
        f = self.frame(33)                     # half-way: drawn 6 px below its resting box
        self.assertGreater(self.alpha(f, 105, 213), 0)
        self.assertEqual(self.alpha(f, 105, 202), 0)

    def test_line_fade(self):
        self.assertEqual(self.alpha(self.frame(86), 105, 205), 128)   # (90 − 86) / 8 = 0.5

    def test_untimed_word_static_from_line_start(self):
        lines = [dataclasses.replace(self.lines[0], words=[WordPlan(self.box, None, None, "Mere")])]
        self.assertEqual(self.alpha(self.frame(30, lines), 105, 205), 255)

    def test_cache_gives_identical_frames(self):
        cache = render.FadeCache()
        for n in (31, 33, 86, 33):
            self.assertEqual(render.compose_frame(n, self.lines, self.sprites, THEME, cache),
                             self.frame(n))


class FfmpegCommandTest(unittest.TestCase):
    def test_one_process_one_frame_input_three_outputs(self):  # plan §2.1
        outs = {k: Path("r") / v for k, v in render.OUTPUTS.items()}
        cmd = render._ffmpeg_cmd(THEME, "prores", Path("audio.wav"), outs)
        self.assertEqual(cmd.count("-i"), 2)
        self.assertEqual(cmd[cmd.index("-i") + 1], "-")
        graph = cmd[cmd.index("-filter_complex") + 1]
        self.assertIn("split=3", graph)
        self.assertEqual(graph.count("overlay=shortest=1"), 2)
        preview = cmd[cmd.index(str(outs["green"])) + 1:]
        self.assertIn("-shortest", preview)
        self.assertIn("aac", preview)
        self.assertEqual(cmd[-1], str(outs["preview"]))


@unittest.skipUnless(shutil.which("ffmpeg") and shutil.which("ffprobe"), "ffmpeg not on PATH")
class RenderSmokeTest(unittest.TestCase):
    """A synthetic 2 s song end to end, with real fonts and ffmpeg (qtrle: the fast codec)."""

    def test_two_second_song(self):
        with tempfile.TemporaryDirectory() as tmp:
            song = make_song(Path(tmp))
            words_sha = hashlib.sha256((song / "words.json").read_bytes()).hexdigest()
            before = {p for p in song.rglob("*")}
            result = render.render(song, codec="qtrle")

            self.assertEqual(result.checks, [])
            self.assertEqual(result.frames, 60)
            self.assertEqual(result.skipped_lines, [])
            for path in result.outputs.values():
                self.assertGreater(path.stat().st_size, 0)
            self.assertIn("**pass**", (result.render_dir / "report.md").read_text("utf-8"))
            # AC7: words.json byte-identical; new files only under render/
            self.assertEqual(hashlib.sha256((song / "words.json").read_bytes()).hexdigest(),
                             words_sha)
            new = {p for p in song.rglob("*")} - before
            self.assertTrue(all(p == result.render_dir or result.render_dir in p.parents
                                for p in new), new)

            # The sync check is not vacuous: a timeline 10 frames late fails it.
            doc = timing.load_words(song / "words.json")
            lines, _ = render.plan_timeline(doc, THEME, result.frames)
            late = [dataclasses.replace(lp, words=[dataclasses.replace(wp, reveal=wp.reveal + 10)
                                                   for wp in lp.words]) for lp in lines]
            fails = render.check_outputs(result, late, THEME, result.frames)
            self.assertTrue(any(f.startswith("sync:") for f in fails), fails)

    def test_encoder_failure_removes_partial_outputs(self):
        with tempfile.TemporaryDirectory() as tmp:
            song = make_song(Path(tmp))
            bad = {**render.ALPHA_CODECS, "bad": ("format=rgba", ["-c:v", "no_such_encoder"])}
            with mock.patch.object(render.encode, "ALPHA_CODECS", bad), \
                    self.assertRaisesRegex(RenderError, "ffmpeg failed .*no_such_encoder"):
                render.render(song, codec="bad")
            self.assertEqual(list((song / "render").iterdir()), [])


class EmphasisRenderTest(unittest.TestCase):
    """End to end: a marker added after alignment renders with no re-align, bigger, and passes
    the sync check measured on the bigger word (spec 06, H-013)."""

    def test_marker_added_after_align(self):
        with tempfile.TemporaryDirectory() as tmp:
            song = make_song(Path(tmp), times=((0.3, 1.2), (1.3, 1.6)))
            words_sha = hashlib.sha256((song / "words.json").read_bytes()).hexdigest()
            (song / "lyrics.txt").write_text("*Mere*\nsaamne\n", encoding="utf-8")
            result = render.render(song, codec="qtrle")
            self.assertEqual(result.checks, [])
            self.assertEqual(result.emphasis, ['"Mere" (line 1)'])
            self.assertIn('Emphasis words: 1: "Mere" (line 1)',
                          (result.render_dir / "report.md").read_text("utf-8"))
            self.assertEqual(hashlib.sha256((song / "words.json").read_bytes()).hexdigest(),
                             words_sha)

    def test_malformed_marker_stops_render_with_the_hint(self):
        with tempfile.TemporaryDirectory() as tmp:
            song = make_song(Path(tmp))
            (song / "lyrics.txt").write_text("*Mere\nsaamne\n", encoding="utf-8")
            with self.assertRaisesRegex(RenderError, r"(?s)line 1: .*\*tere\* \*bina\*"):
                render.load_for_render(song, allow_flagged=False)


if __name__ == "__main__":
    unittest.main()
