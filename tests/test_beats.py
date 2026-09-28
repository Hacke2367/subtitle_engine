"""beats.py: detection on synthetic audio, beats.json reuse / rebuild / hand edits, preview, CLI."""
from __future__ import annotations

import io
import json
import subprocess
import sys
import tempfile
import unittest
import wave
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest import mock

import librosa
import numpy as np

from lyric_engine import align, beats, cli, timing
from lyric_engine.beats import BeatsError

SR = beats.SR
REF = np.arange(0.5, 20, 0.5)                  # 120 BPM for 20 s
GAP = np.concatenate([np.arange(0.5, 10, 0.5), np.arange(13.0, 23, 0.5)])   # silent 9.5-13 s


def clicks(times, dur: float) -> np.ndarray:
    return librosa.clicks(times=times, sr=SR, length=int(dur * SR), click_duration=0.03)


def write_wav(path: Path, y: np.ndarray) -> None:
    with wave.open(str(path), "wb") as f:
        f.setnchannels(1)
        f.setsampwidth(2)
        f.setframerate(SR)
        f.writeframes((np.clip(y, -1, 1) * 32767).astype("<i2").tobytes())


def song_dir(root: Path, y: np.ndarray, name: str = "song") -> Path:
    song = root / name
    song.mkdir()
    write_wav(song / "audio.wav", y)
    return song


class DetectTest(unittest.TestCase):
    def test_click_track(self):
        det = beats.detect(clicks(REF, 20.5))
        got = np.array(det.beats)
        for r in REF[REF > 1]:
            self.assertLessEqual(np.min(np.abs(got - r)), 0.05, f"click at {r} s has no beat")
        for b in got:
            self.assertLessEqual(np.min(np.abs(REF - b)), 0.05, f"beat at {b} s is not on a click")
        self.assertLess(abs(det.tempo - 120) / 120, 0.02)
        self.assertEqual(det.silent, [])

    def test_silent_gap(self):
        det = beats.detect(clicks(GAP, 23.5))
        self.assertEqual([b for b in det.beats if 9.75 < b < 12.75], [])
        self.assertEqual(len(det.silent), 1)
        self.assertTrue(9.5 < det.silent[0][0] < det.silent[0][1] <= 13.0)

    def test_silence(self):
        self.assertEqual(beats.detect(np.zeros(10 * SR, dtype=np.float32)), beats.Detection(0.0, [], []))

    def test_bpm_hint(self):
        det = beats.detect(clicks(REF, 20.5), bpm=60)
        self.assertAlmostEqual(float(np.median(np.diff(det.beats))), 1.0, delta=0.05)
        self.assertEqual(det.tempo, 60)


class _SongCase(unittest.TestCase):
    """A 12 s, 120 BPM click song in a temp folder (no lyrics.txt: the beat stage never needs it)."""
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        self.song = song_dir(self.root, clicks(REF[REF < 12], 12.5))
        self.path = self.song / beats.BEATS_FILE

    def edit(self, change) -> bytes:
        doc = beats.load_beats(self.path)
        change(doc)
        beats.save_beats(self.path, doc)
        return self.path.read_bytes()


class EnsureTest(_SongCase):
    def test_computed_doc(self):
        r = beats.ensure_beats(self.song)
        self.assertFalse(r.reused)
        self.assertEqual(r.audio, self.song / "audio.wav")
        doc = beats.load_beats(self.path)
        self.assertEqual(doc, r.doc)
        self.assertEqual(list(doc), ["version", "song", "audio", "detector", "created", "tempo_bpm", "beats"])
        self.assertEqual(doc["audio"]["sha256"], timing.sha256_file(self.song / "audio.wav"))
        self.assertAlmostEqual(doc["audio"]["duration_s"], 12.5, places=2)
        self.assertEqual(doc["detector"]["library"], "librosa")
        self.assertIsNone(doc["detector"]["bpm_hint"])
        self.assertEqual(beats.problems(doc), [])
        self.assertGreater(len(doc["beats"]), 20)

    def test_reuse(self):
        beats.ensure_beats(self.song)
        before = self.path.read_bytes()
        with mock.patch.object(beats, "detect") as detect:
            r = beats.ensure_beats(self.song)
        detect.assert_not_called()
        self.assertTrue(r.reused)
        self.assertEqual(r.notes, [])
        self.assertEqual(self.path.read_bytes(), before)

    def test_words_untouched(self):             # red line 1: the beat stage never touches words.json
        words = self.song / "words.json"
        words.write_text('{"sentinel": true}\n', encoding="utf-8")
        before = words.read_bytes()
        beats.ensure_beats(self.song, fresh=True)
        self.assertEqual(words.read_bytes(), before)
        other = song_dir(self.root, clicks(REF[REF < 6], 6.5), "other")
        beats.ensure_beats(other)
        self.assertFalse((other / "words.json").exists())

    def test_silence_is_saved(self):
        song = song_dir(self.root, np.zeros(5 * SR), "quiet")
        r = beats.ensure_beats(song)
        self.assertEqual((r.doc["tempo_bpm"], r.doc["beats"]), (0.0, []))
        self.assertIn("no steady beat found: beats.json has no beats", r.notes)
        self.assertTrue(beats.ensure_beats(song).reused)

    def test_missing_audio(self):
        empty = self.root / "empty"
        empty.mkdir()
        with self.assertRaises(FileNotFoundError):
            beats.ensure_beats(empty)
        self.assertFalse((empty / beats.BEATS_FILE).exists())

    def test_undecodable_audio(self):
        song = self.root / "broken"
        song.mkdir()
        (song / "audio.mp3").write_bytes(b"not audio at all")
        with self.assertRaisesRegex(BeatsError, "cannot decode audio.mp3"):
            beats.ensure_beats(song)
        self.assertFalse((song / beats.BEATS_FILE).exists())


class RebuildTest(_SongCase):
    def setUp(self):
        super().setUp()
        beats.ensure_beats(self.song)

    def test_audio_changed(self):
        write_wav(self.song / "audio.wav", clicks(np.arange(0.5, 12, 0.6), 12.5))
        r = beats.ensure_beats(self.song)
        self.assertFalse(r.reused)
        self.assertEqual(r.notes[0], "audio changed: beats rebuilt")
        self.assertEqual(r.doc["audio"]["sha256"], timing.sha256_file(self.song / "audio.wav"))

    def test_fresh(self):
        with mock.patch.object(beats, "detect", wraps=beats.detect) as detect:
            r = beats.ensure_beats(self.song, fresh=True)
        detect.assert_called_once()
        self.assertFalse(r.reused)

    def test_older_version(self):
        self.edit(lambda d: d.update(version=0))
        r = beats.ensure_beats(self.song)
        self.assertFalse(r.reused)
        self.assertEqual(r.notes[0], "older format (version 0): beats rebuilt")
        self.assertEqual(r.doc["version"], beats.BEATS_VERSION)

    def test_bpm_hint(self):
        r = beats.ensure_beats(self.song, bpm=60)
        self.assertFalse(r.reused)
        self.assertAlmostEqual(float(np.median(np.diff(r.doc["beats"]))), 1.0, delta=0.05)
        self.assertEqual(r.doc["detector"]["bpm_hint"], 60)
        self.assertIn("tempo hint: 60 BPM", r.notes)
        self.assertTrue(beats.ensure_beats(self.song).reused)    # a later render keeps the fix


class HandEditTest(_SongCase):
    def setUp(self):
        super().setUp()
        beats.ensure_beats(self.song)

    def test_valid_edit_is_kept(self):
        self.edit(lambda d: d["beats"].pop(3))
        edited = beats.load_beats(self.path)["beats"]
        with mock.patch.object(beats, "detect") as detect:
            r = beats.ensure_beats(self.song)
        detect.assert_not_called()
        self.assertTrue(r.reused)
        self.assertEqual(r.doc["beats"], edited)

    def assert_refused(self, before: bytes, message: str):
        with mock.patch.object(beats, "detect") as detect, \
                self.assertRaisesRegex(BeatsError, message):
            beats.ensure_beats(self.song)
        detect.assert_not_called()
        self.assertEqual(self.path.read_bytes(), before)

    def test_invalid_edits_are_refused(self):
        def swap(d):
            d["beats"][2], d["beats"][3] = d["beats"][3], d["beats"][2]
        cases = {
            "unsorted": (swap, r"beats\[3\] = .* is not after beats\[2\]"),
            "out of range": (lambda d: d["beats"].append(99.0), r"is outside 0-12\.5"),
            "not a number": (lambda d: d["beats"].__setitem__(2, "x"), r"beats\[2\] is not a number"),
            "newer version": (lambda d: d.update(version=9), "version 9 is not one this engine writes"),
            "negative tempo": (lambda d: d.update(tempo_bpm=-1), "tempo_bpm is not a number >= 0"),
        }
        original = self.path.read_bytes()
        for name, (change, message) in cases.items():
            with self.subTest(name):
                self.path.write_bytes(original)
                self.assert_refused(self.edit(change), message)

    def test_broken_json_is_refused(self):
        self.path.write_bytes(self.path.read_bytes()[:-30])
        self.assert_refused(self.path.read_bytes(), "not valid JSON at line")

    def test_fresh_replaces_a_broken_file(self):
        self.path.write_text("{", encoding="utf-8")
        r = beats.ensure_beats(self.song, fresh=True)
        self.assertEqual(beats.problems(beats.load_beats(self.path)), [])
        self.assertFalse(r.reused)


class PreviewTest(_SongCase):
    def test_preview(self):
        r = beats.ensure_beats(self.song)
        out = beats.write_preview(r.audio, r.doc, self.root / "preview.m4a")
        self.assertAlmostEqual(align.probe_duration(out), r.doc["audio"]["duration_s"], delta=0.1)

    def test_preview_without_beats(self):
        song = song_dir(self.root, np.zeros(3 * SR), "quiet")
        r = beats.ensure_beats(song)
        out = beats.write_preview(r.audio, r.doc, song / beats.PREVIEW_FILE)
        self.assertAlmostEqual(align.probe_duration(out), 3.0, delta=0.1)


class CliBeatsTest(_SongCase):
    def run_cli(self, *args) -> tuple[int, str, str]:
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            code = cli.main(["beats", str(self.song), *args])
        return code, out.getvalue(), err.getvalue()

    def test_computed_then_reused(self):
        code, out, _ = self.run_cli()
        self.assertEqual(code, 0)
        self.assertIn("(computed)", out)
        self.assertIn(f"preview: {self.song / beats.PREVIEW_FILE}", out)
        self.assertRegex(out, r"tempo: [\d.]+ BPM  beats: \d+  first: [\d.]+ s  last: [\d.]+ s")
        self.assertTrue((self.song / beats.PREVIEW_FILE).exists())
        code, out, _ = self.run_cli()
        self.assertEqual(code, 0)
        self.assertIn("(reused)", out)

    def test_bad_bpm(self):
        for bpm in ("0", "-90", "fast", "400"):
            with self.subTest(bpm), self.assertRaises(SystemExit) as cm:
                self.run_cli("--bpm", bpm)
            self.assertEqual(cm.exception.code, 2)
        self.assertFalse(self.path.exists())

    def test_invalid_file(self):
        self.run_cli()
        self.path.write_text("[]", encoding="utf-8")
        code, _, err = self.run_cli()
        self.assertEqual(code, 2)
        self.assertIn("not a JSON object", err)

    def test_preview_failure_keeps_beats(self):
        with mock.patch.object(beats, "write_preview", side_effect=RuntimeError("ffmpeg preview failed")):
            code, out, err = self.run_cli()
        self.assertEqual(code, 1)
        self.assertIn("ffmpeg preview failed", err)
        self.assertNotIn("preview:", out)
        self.assertEqual(beats.problems(beats.load_beats(self.path)), [])


class ImportIsolationTest(unittest.TestCase):
    def test_other_commands_never_load_librosa(self):
        code = ("import sys; import lyric_engine.cli, lyric_engine.render, lyric_engine.workflow, "
                "lyric_engine.align, lyric_engine.review; "
                "print(sorted(m for m in ('librosa', 'numba', 'scipy', 'sklearn', 'soundfile') "
                "if m in sys.modules))")
        proc = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(proc.stdout.strip(), "[]")


if __name__ == "__main__":
    unittest.main()
