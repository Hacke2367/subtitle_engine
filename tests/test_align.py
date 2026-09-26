"""align.py orchestration with a fake engine: cache reuse (AC8), raw check (AC6), red lines."""
from __future__ import annotations

import io
import json
import os
import tempfile
import unittest
import wave
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest import mock

from lyric_engine import align, eleven, timing
from lyric_engine.timing import RawWord

FAKE = align.Variant("T-raw", "fake", "raw", None)


def setUpModule():
    # Error messages get redacted with the API key; tests must never read the real .env or env var.
    global _no_key
    _no_key = [mock.patch.object(eleven, "ENV_PATH", Path(tempfile.gettempdir()) / "no-such.env"),
               mock.patch.dict(os.environ, {eleven.KEY_VAR: ""})]
    for p in _no_key:
        p.start()


def tearDownModule():
    for p in _no_key:
        p.stop()


def make_song(root: Path, lyrics: str = "ek do teen\nchaar paanch\n") -> Path:
    song = root / "song"
    song.mkdir()
    with wave.open(str(song / "audio.wav"), "wb") as w:   # 2 s of silence, 16 kHz mono
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(16000)
        w.writeframes(b"\x00\x00" * 32000)
    (song / "lyrics.txt").write_text(lyrics, encoding="utf-8")
    return song


class FakeEngine:
    def __init__(self, missing: set[int] = frozenset()):
        self.calls = 0
        self.missing = missing

    def __call__(self, audio: Path, words: list[str]):
        self.calls += 1
        self.words = words
        raw = [RawWord(None, None, None) if i in self.missing
               else RawWord(0.1 + 0.3 * i, 0.3 + 0.3 * i, 0.9) for i in range(len(words))]
        return raw, {"engine": "fake"}


class RunVariantTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.song = make_song(Path(self.tmp.name))

    def tearDown(self):
        self.tmp.cleanup()

    def test_cache_reused_without_engine_call(self):
        engine = FakeEngine()
        first = align.run_variant(self.song, FAKE, artifacts=False, engine=engine)
        self.assertIsNone(first.error)
        self.assertFalse(first.reused)
        second = align.run_variant(self.song, FAKE, artifacts=False, engine=engine)
        self.assertTrue(second.reused)
        self.assertEqual(engine.calls, 1)
        align.run_variant(self.song, FAKE, artifacts=False, engine=engine, fresh=True)
        self.assertEqual(engine.calls, 2)

    def test_lyrics_change_invalidates_cache(self):
        engine = FakeEngine()
        align.run_variant(self.song, FAKE, artifacts=False, engine=engine)
        (self.song / "lyrics.txt").write_text("ek do teen\nchaar paanch chhe\n", encoding="utf-8")
        align.run_variant(self.song, FAKE, artifacts=False, engine=engine)
        self.assertEqual(engine.calls, 2)

    def test_words_json_matches_raw_and_lyrics(self):
        result = align.run_variant(self.song, FAKE, artifacts=False, engine=FakeEngine())
        out = self.song / "bakeoff" / FAKE.name
        self.assertEqual(align.verify_against_raw(out), [])
        self.assertEqual([w["text"] for w in result.doc["words"]],
                         ["ek", "do", "teen", "chaar", "paanch"])
        self.assertEqual(timing.validate(timing.load_words(out / "words.json"),
                                         self.song / "lyrics.txt", self.song / "audio.wav"), [])

    def test_tampered_time_is_caught(self):
        align.run_variant(self.song, FAKE, artifacts=False, engine=FakeEngine())
        out = self.song / "bakeoff" / FAKE.name
        doc = timing.load_words(out / "words.json")
        doc["words"][1]["start"] = 0.35
        timing.save_words(out / "words.json", doc)
        errors = align.verify_against_raw(out)
        self.assertEqual(len(errors), 1)
        self.assertIn("word 1", errors[0])

    def test_unplaced_word_is_flagged_never_estimated(self):
        result = align.run_variant(self.song, FAKE, artifacts=False, engine=FakeEngine({2}))
        word = result.doc["words"][2]
        self.assertIsNone(word["start"])
        self.assertIsNone(word["end"])
        self.assertTrue(word["flagged"])
        self.assertIn("not_placed", word["reasons"])

    def test_annotated_lyrics_rejected_before_engine(self):
        (self.song / "lyrics.txt").write_text("ek do teen (x2)\n", encoding="utf-8")
        engine = FakeEngine()
        result = align.run_variant(self.song, FAKE, artifacts=False, engine=engine)
        self.assertEqual(engine.calls, 0)
        self.assertIn("line 1", result.error)


class AlignEmphasisTest(unittest.TestCase):
    """Spec 06 AC2: *word* markers never reach an aligner or words.json."""

    def test_engines_get_words_without_markers(self):
        with tempfile.TemporaryDirectory() as tmp:
            song = make_song(Path(tmp), "ek *do* teen\nchaar *paanch,*\n")
            engine = FakeEngine()
            result = align.run_variant(song, FAKE, artifacts=False, engine=engine)
            self.assertEqual(engine.words, ["ek", "do", "teen", "chaar", "paanch,"])
            self.assertEqual([w["text"] for w in result.doc["words"]], engine.words)
            # ElevenLabs sends exactly these words as its request text.
            urlopen = mock.MagicMock()
            urlopen.return_value.__enter__.return_value.read.return_value = json.dumps(
                {"words": [{"text": w, "start": i, "end": i + 0.5, "loss": 0.0}
                           for i, w in enumerate(engine.words)]}).encode()
            with mock.patch("urllib.request.urlopen", urlopen):
                eleven.align(song / "audio.wav", engine.words, api_key="test-key")
            body = urlopen.call_args.args[0].data
            self.assertIn(b'name="text"\r\n\r\nek do teen chaar paanch,\r\n', body)
            self.assertNotIn(b"*", body.split(b'name="text"')[1])


class AlignSongTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.song = make_song(Path(self.tmp.name))
        self.engine = FakeEngine()
        patches = [mock.patch.object(align, "VARIANTS", (FAKE,)),
                   mock.patch.object(align, "_engine", lambda name: self.engine)]
        for p in patches:
            p.start()
            self.addCleanup(p.stop)

    def tearDown(self):
        self.tmp.cleanup()

    def test_never_overwrites_corrections_silently(self):
        with redirect_stdout(io.StringIO()):
            self.assertEqual(align.align_song(self.song, variant=FAKE.name), 0)
        target = self.song / "words.json"
        edited = json.loads(target.read_text(encoding="utf-8"))
        edited["words"][0]["start"] = 0.12
        target.write_text(json.dumps(edited), encoding="utf-8")
        with redirect_stderr(io.StringIO()):
            self.assertEqual(align.align_song(self.song, variant=FAKE.name), 2)
        self.assertEqual(json.loads(target.read_text(encoding="utf-8"))["words"][0]["start"], 0.12)
        with redirect_stdout(io.StringIO()):
            self.assertEqual(align.align_song(self.song, variant=FAKE.name, overwrite=True), 0)
        backup = json.loads((self.song / "words.json.bak").read_text(encoding="utf-8"))
        self.assertEqual(backup["words"][0]["start"], 0.12)

    def test_no_default_variant_yet(self):
        with mock.patch.object(align, "DEFAULT_VARIANT", None), redirect_stderr(io.StringIO()):
            self.assertEqual(align.align_song(self.song), 2)

    def test_unknown_variant_is_an_error(self):
        with redirect_stderr(io.StringIO()):
            self.assertEqual(align.align_song(self.song, variant="nope"), 2)


if __name__ == "__main__":
    unittest.main()
