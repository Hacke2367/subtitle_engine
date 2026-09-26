"""workflow.py: clip line selection and snapping, clip folder I/O, make's alignment decision."""
from __future__ import annotations

import io
import json
import subprocess
import tempfile
import unittest
import wave
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest import mock

from lyric_engine import align, timing, workflow
from lyric_engine.timing import RawWord
from lyric_engine.workflow import ClipError, plan_clip


def w(line: int, start, end, flagged: bool = False) -> dict:
    return {"line": line, "start": start, "end": end, "flagged": flagged}


# lines: 0 at 1-3 s, 1 at 4-6 s, 2 blank (stanza break), 3 at 7-9 s; the song is 10 s long
DOC = {"words": [w(0, 1.0, 1.5), w(0, 1.6, 3.0), w(1, 4.0, 5.0), w(1, 5.1, 6.0),
                 w(3, 7.0, 8.0), w(3, 8.1, 9.0)]}


class PlanClipTest(unittest.TestCase):
    def plan(self, a, b, doc=DOC, duration=10.0):
        p = plan_clip(doc, a, b, duration)
        return p.start, p.end, p.lines

    def test_edges_in_gaps_are_kept(self):          # an intro / outro chosen by the owner stays
        self.assertEqual(self.plan(3.5, 6.5), (3.5, 6.5, [1]))
        self.assertEqual(self.plan(0.5, 6.2), (0.5, 6.2, [0, 1]))

    def test_start_inside_a_line_snaps_into_the_next_gap(self):
        # line 1 (4-6) crosses --from 4.5: it is left out; the cut starts 0.3 s before line 3
        self.assertEqual(self.plan(4.5, 9.5), (6.7, 9.5, [3]))

    def test_end_inside_a_line_snaps_into_the_previous_gap(self):
        # line 1 crosses --to 5.0: the cut ends half-way into the 1 s gap after line 0
        self.assertEqual(self.plan(0.5, 5.0), (0.5, 3.5, [0]))

    def test_end_clamped_to_the_song(self):
        self.assertEqual(self.plan(6.5, 30.0), (6.5, 10.0, [3]))

    def test_no_whole_line_inside(self):
        with self.assertRaisesRegex(ClipError, "no whole lyric line"):
            plan_clip(DOC, 1.5, 2.5, 10.0)

    def test_bad_ranges(self):
        for a, b in ((5.0, 5.0), (6.0, 2.0), (-1.0, 3.0), (10.5, 12.0)):
            with self.assertRaises(ClipError, msg=(a, b)):
                plan_clip(DOC, a, b, 10.0)

    def test_flagged_line_inside_or_next_to_the_clip_is_refused(self):
        doc = {"words": [*DOC["words"][:2], w(1, 4.0, 5.0, flagged=True), DOC["words"][3],
                         *DOC["words"][4:]]}
        with self.assertRaisesRegex(ClipError, "line 2 .*between"):
            plan_clip(doc, 0.5, 9.5, 10.0)
        with self.assertRaisesRegex(ClipError, "line 2 .*just after"):
            plan_clip(doc, 0.5, 3.5, 10.0)
        with self.assertRaisesRegex(ClipError, "line 2 .*just before"):   # skips the blank line
            plan_clip(doc, 6.5, 9.5, 10.0)

    def test_long_lead_in_is_warned(self):
        doc = {"words": [w(0, 5.0, 6.0)]}
        self.assertEqual(len(plan_clip(doc, 0.5, 6.5, 10.0).warnings), 1)


def make_source(root: Path, name: str = "full") -> Path:
    """A 10 s silent song with lyrics "ek do / (blank) / teen chaar" and a valid words.json."""
    song = root / name
    song.mkdir()
    with wave.open(str(song / "audio.wav"), "wb") as f:
        f.setnchannels(1)
        f.setsampwidth(2)
        f.setframerate(16000)
        f.writeframes(b"\x00\x00" * 160000)
    (song / "lyrics.txt").write_text("ek do\n\nteen chaar\n", encoding="utf-8")
    lyrics = timing.read_lyrics(song / "lyrics.txt")
    words = timing.build_words(lyrics, [RawWord(1.0, 1.4, 0.9), RawWord(1.5, 2.0, 0.9),
                                        RawWord(4.0, 4.5, 0.9), RawWord(4.6, 5.0, 0.9)])
    timing.apply_flags(words, 10.0, None)
    doc = timing.make_doc(name, song / "audio.wav", 10.0, timing.sha256_file(song / "audio.wav"),
                          lyrics, {"variant": "T", "input": "raw", "settings": {},
                                   "reused_cache": False}, words)
    timing.save_words(song / "words.json", doc)
    return song


def duration_of(path: Path) -> float:
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of",
                          "csv=p=0", str(path)], capture_output=True, text=True).stdout
    return float(out)


class ClipSongTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.source = make_source(self.root)

    def tearDown(self):
        self.tmp.cleanup()

    def test_clip_folder_has_cut_audio_and_verbatim_lines(self):
        out = self.root / "clip"
        plan = workflow.clip_song(self.source, 3.5, 5.8, out)
        self.assertEqual((plan.start, plan.end, plan.lines), (3.5, 5.8, [2]))
        self.assertEqual((out / "lyrics.txt").read_bytes(), b"teen chaar\n")   # LF, as written
        self.assertAlmostEqual(duration_of(out / "audio.wav"), 2.3, delta=0.01)
        meta = json.loads((out / "clip.json").read_text(encoding="utf-8"))
        self.assertEqual((meta["start_s"], meta["end_s"], meta["lines"]), (3.5, 5.8, [3]))
        self.assertEqual(timing.read_lyrics(out / "lyrics.txt").words, [("teen", 0), ("chaar", 0)])

    def test_stanza_break_between_selected_lines_is_kept(self):
        out = self.root / "both"
        workflow.clip_song(self.source, 0.5, 5.8, out)
        self.assertEqual((out / "lyrics.txt").read_text(encoding="utf-8"), "ek do\n\nteen chaar\n")

    def test_never_overwrites_a_folder(self):
        out = self.root / "clip"
        out.mkdir()
        with self.assertRaisesRegex(ClipError, "already exists"):
            workflow.clip_song(self.source, 3.5, 5.8, out)

    def test_source_must_be_aligned_and_fresh(self):
        (self.source / "lyrics.txt").write_text("ek do\n\nteen chaar paanch\n", encoding="utf-8")
        with self.assertRaisesRegex(ClipError, "cannot be used"):
            workflow.clip_song(self.source, 3.5, 5.8, self.root / "clip")
        (self.source / "words.json").unlink()
        with self.assertRaisesRegex(ClipError, "no words.json"):
            workflow.clip_song(self.source, 3.5, 5.8, self.root / "clip")
        self.assertFalse((self.root / "clip").exists())


class EnsureAlignedTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.song = make_source(Path(self.tmp.name))
        patcher = mock.patch.object(align, "align_song", return_value=0)
        self.align_song = patcher.start()
        self.addCleanup(patcher.stop)

    def tearDown(self):
        self.tmp.cleanup()

    def run_it(self) -> int:
        with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
            return workflow.ensure_aligned(self.song)

    def test_existing_valid_alignment_is_kept(self):    # it may hold hand corrections
        self.assertEqual(self.run_it(), 0)
        self.align_song.assert_not_called()

    def test_missing_alignment_is_made(self):
        (self.song / "words.json").unlink()
        self.assertEqual(self.run_it(), 0)
        self.align_song.assert_called_once_with(self.song)

    def test_stale_alignment_is_refused(self):
        (self.song / "lyrics.txt").write_text("ek do\n\nteen chaar paanch\n", encoding="utf-8")
        self.assertEqual(self.run_it(), 2)
        self.align_song.assert_not_called()


if __name__ == "__main__":
    unittest.main()
