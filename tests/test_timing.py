"""Tests for lyric_engine.timing: lyrics reading, flag rules, words.json IO and validation.

Offline and song-free: temp files, plus the tracked placeholder songs/example/lyrics.txt.
Run: venv/Scripts/python -m unittest tests.test_timing -v
"""
from __future__ import annotations

import copy
import hashlib
import json
import re
import tempfile
import unittest
from pathlib import Path

from lyric_engine.timing import (
    MAX_WORD_S, Lyrics, LyricsError, RawWord, Word, apply_flags, build_words, flag_summary, load_words,
    make_doc, normalize, read_lyrics, save_words, sha256_file, validate,
)

REPO = Path(__file__).resolve().parent.parent
EXAMPLE_LYRICS = REPO / "songs" / "example" / "lyrics.txt"
DURATION = 30.0
ALIGNER = {"variant": "L-vocals", "input": "vocals", "settings": {}, "reused_cache": False}
DELETE = object()  # edited(): remove the key instead of setting it


def timed(*timings: tuple) -> list[Word]:
    """Words w0, w1, ... on line 0 with the given (start, end, score)."""
    return [Word(i, f"w{i}", 0, start, end, score) for i, (start, end, score) in enumerate(timings)]


def edited(doc: dict, edits: dict) -> dict:
    """A deep copy of doc with each {(key, key, ...): value} edit applied."""
    doc = copy.deepcopy(doc)
    for (*parents, last), value in edits.items():
        target = doc
        for key in parents:
            target = target[key]
        if value is DELETE:
            del target[last]
        else:
            target[last] = value
    return doc


class TempDirTest(unittest.TestCase):
    def setUp(self) -> None:
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.dir = Path(tmp.name)

    def write(self, name: str, content: str | bytes) -> Path:
        path = self.dir / name
        path.write_bytes(content.encode("utf-8") if isinstance(content, str) else content)
        return path


class ReadLyricsTest(TempDirTest):
    def test_example_lyrics_reproduced_line_by_line(self):  # AC2
        text = EXAMPLE_LYRICS.read_text(encoding="utf-8")
        lyrics = read_lyrics(EXAMPLE_LYRICS)
        self.assertEqual(len(lyrics.lines), len(text.splitlines()))
        self.assertEqual(lyrics.lines, text.splitlines())
        for n, line in enumerate(text.splitlines()):
            with self.subTest(line=n):
                self.assertEqual([t for t, li in lyrics.words if li == n], line.split())
        self.assertEqual(lyrics.sha256, hashlib.sha256(EXAMPLE_LYRICS.read_bytes()).hexdigest())

    def test_blank_lines_crlf_and_verbatim_tokens(self):
        path = self.write("lyrics.txt", "\r\nMere, SAAMNE\twaali!\r\n\r\n   \r\nkhidkī mein 🌙\r\n")
        lyrics = read_lyrics(path)
        self.assertEqual(lyrics.lines, ["", "Mere, SAAMNE\twaali!", "", "   ", "khidkī mein 🌙"])
        self.assertEqual(lyrics.words, [("Mere,", 1), ("SAAMNE", 1), ("waali!", 1),
                                        ("khidkī", 4), ("mein", 4), ("🌙", 4)])

    def test_bom_is_dropped_but_hashed(self):
        data = b"\xef\xbb\xbf" + "Mere samne\nwaali khidki\n".encode("utf-8")
        lyrics = read_lyrics(self.write("lyrics.txt", data))
        self.assertEqual(lyrics.lines, ["Mere samne", "waali khidki"])
        self.assertEqual(lyrics.words[0], ("Mere", 0))
        self.assertEqual(lyrics.sha256, hashlib.sha256(data).hexdigest())

    def test_annotations_rejected_naming_every_line(self):  # AC3
        cases = {"repeat": ("tum paas ho\ndil ki baatein (x2)\n", [2]),
                 "section": ("tum paas ho\n\n[chorus]\ndil ki baatein\n", [3]),
                 "both": ("[chorus]\ntum paas ho\n\nho (x2)\n", [1, 4])}
        for name, (text, lines) in cases.items():
            with self.subTest(name):
                with self.assertRaises(LyricsError) as ctx:
                    read_lyrics(self.write(f"{name}.txt", text))
                message = str(ctx.exception)
                self.assertEqual([int(n) for n in re.findall(r"\bline (\d+)", message)], lines)
                self.assertIn("in full", message)

    def test_every_bracket_kind_rejected(self):
        for ch in "()[]{}":
            with self.subTest(ch), self.assertRaises(LyricsError):
                read_lyrics(self.write("lyrics.txt", f"tum paas {ch} ho\n"))

    def test_no_words_rejected(self):
        for name, text in {"empty": "", "only blank lines": "\n  \n\t\n"}.items():
            with self.subTest(name), self.assertRaises(LyricsError):
                read_lyrics(self.write("lyrics.txt", text))

    def test_non_utf8_rejected(self):
        with self.assertRaises(LyricsError):
            read_lyrics(self.write("lyrics.txt", "dil ki baat’\n".encode("cp1252")))


class NormalizeTest(unittest.TestCase):
    def test_examples(self):
        cases = {"Mere,": "mere", "--": "", "KHIDKI!": "khidki", "Dil's": "dil's",
                 "2gether": "2gether"}
        for word, want in cases.items():
            with self.subTest(word):
                self.assertEqual(normalize(word), want)


class BuildWordsTest(TempDirTest):
    def test_text_from_lyrics_times_from_raw(self):
        lyrics = read_lyrics(self.write("lyrics.txt", "Mere samne\n\nkhidki\n"))
        raw = [RawWord(0.5, 0.9, 0.8), RawWord(None, None, None), RawWord(1.2, 1.7, None)]
        words = build_words(lyrics, raw)
        self.assertEqual([(w.index, w.text, w.line) for w in words],
                         [(0, "Mere", 0), (1, "samne", 0), (2, "khidki", 2)])
        self.assertEqual([RawWord(w.start, w.end, w.score) for w in words], raw)
        self.assertFalse(any(w.flagged or w.reasons for w in words))

    def test_length_mismatch_raises(self):
        lyrics = read_lyrics(self.write("lyrics.txt", "Mere samne\n"))
        with self.assertRaises(ValueError):
            build_words(lyrics, [RawWord(0.5, 0.9, 0.8)])


class ApplyFlagsTest(unittest.TestCase):
    def flags(self, timings: list[tuple], min_score: float | None = None) -> list[list[str]]:
        words = timed(*timings)
        apply_flags(words, DURATION, min_score)
        self.assertEqual([w.flagged for w in words], [bool(w.reasons) for w in words])
        return [w.reasons for w in words]

    def test_clean_input_has_no_flags(self):
        timings = [(0.5, 1.0, 0.9), (1.0, 1.6, 0.8),
                   (1.55, 2.0, None),                    # overlap within tolerance
                   (3.0, 3.0 + MAX_WORD_S, 0.7),         # exactly the longest allowed word
                   (29.5, DURATION + 0.04, 0.5)]         # end within tolerance; score == min
        self.assertEqual(self.flags(timings, min_score=0.5), [[]] * 5)

    def test_each_reason_fires(self):
        cases = {  # name: (timings, min_score, expected reasons per word)
            "not_placed": ([(None, None, None)], None, [["not_placed"]]),
            "not_placed, end missing": ([(1.0, None, 0.9)], None, [["not_placed"]]),
            "low_confidence": ([(1.0, 1.5, 0.2)], 0.5, [["low_confidence"]]),
            "bad_duration, zero length": ([(1.0, 1.0, 0.9)], None, [["bad_duration"]]),
            "bad_duration, too long": ([(1.0, 1.5 + MAX_WORD_S, 0.9)], None, [["bad_duration"]]),
            "out_of_order, earlier start": ([(2.0, 2.05, 0.9), (1.97, 2.5, 0.9)], None,
                                            [[], ["out_of_order"]]),
            "out_of_order, overlap past tolerance": ([(1.0, 2.0, 0.9), (1.8, 2.5, 0.9)], None,
                                                     [[], ["out_of_order"]]),
            "out_of_bounds, negative start": ([(-0.2, 0.3, 0.9)], None, [["out_of_bounds"]]),
            "out_of_bounds, past the audio": ([(29.5, DURATION + 0.2, 0.9)], None,
                                              [["out_of_bounds"]]),
        }
        for name, (timings, min_score, want) in cases.items():
            with self.subTest(name):
                self.assertEqual(self.flags(timings, min_score), want)

    def test_low_confidence_needs_a_threshold_and_a_score(self):
        self.assertEqual(self.flags([(1.0, 1.5, 0.2)], min_score=None), [[]])
        self.assertEqual(self.flags([(1.0, 1.5, None)], min_score=0.5), [[]])

    def test_previous_placed_word(self):
        # an unplaced word is skipped when looking back...
        self.assertEqual(self.flags([(1.0, 2.0, 0.9), (None, None, None), (1.5, 2.5, 0.9)]),
                         [[], ["not_placed"], ["out_of_order"]])
        # ...and so is a flagged one: order is judged against the last trusted word only
        self.assertEqual(self.flags([(5.0, 5.0, 0.9), (4.0, 4.5, 0.9)]),
                         [["bad_duration"], []])

    def test_backward_jump_output_always_validates(self):
        # an aligner jumping back two words: both stragglers flagged, and the doc still validates
        words = timed((5.0, 5.5, 0.9), (1.0, 1.5, 0.9), (2.0, 2.5, 0.9), (6.0, 6.5, 0.9))
        apply_flags(words, DURATION, None)
        self.assertEqual([w.reasons for w in words], [[], ["out_of_order"], ["out_of_order"], []])
        lyrics = Lyrics(Path("lyrics.txt"), "x", ["w0 w1 w2 w3"],
                        [("w0", 0), ("w1", 0), ("w2", 0), ("w3", 0)])
        doc = make_doc("s", Path("audio.wav"), DURATION, "y", lyrics, ALIGNER, words)
        self.assertEqual(validate(doc), [])

    def test_reasons_in_REASONS_order(self):
        self.assertEqual(self.flags([(1.0, 2.0, 0.9), (-1.0, -1.0, 0.1)], min_score=0.5),
                         [[], ["low_confidence", "bad_duration", "out_of_order", "out_of_bounds"]])

    def test_idempotent_clears_stale_flags_and_keeps_times(self):
        words = timed((1.0, 2.0, 0.9), (1.5, 1.5, 0.1), (None, None, None))
        words[0].flagged, words[0].reasons = True, ["not_placed"]  # left from an earlier run
        apply_flags(words, DURATION, 0.5)
        first = [(w.flagged, list(w.reasons)) for w in words]
        apply_flags(words, DURATION, 0.5)
        self.assertEqual([(w.flagged, w.reasons) for w in words], first)
        self.assertEqual(first, [(False, []),
                                 (True, ["low_confidence", "bad_duration", "out_of_order"]),
                                 (True, ["not_placed"])])
        # red line 1: flagging never invents or moves a time
        self.assertEqual([(w.start, w.end, w.score) for w in words],
                         [(1.0, 2.0, 0.9), (1.5, 1.5, 0.1), (None, None, None)])


class FlagSummaryTest(unittest.TestCase):
    def test_counts_and_mostly_flagged_boundary(self):
        words = timed(*[(float(i), i + 0.5, 0.9) for i in range(10)])
        for w, reasons in zip(words, (["not_placed"], ["low_confidence", "out_of_order"],
                                      ["out_of_order"])):
            w.flagged, w.reasons = True, reasons
        summary = flag_summary(words)
        self.assertEqual((summary["total"], summary["flagged"]), (10, 3))
        self.assertAlmostEqual(summary["share"], 0.3)
        self.assertEqual(summary["by_reason"], {"not_placed": 1, "low_confidence": 1,
                                                "bad_duration": 0, "out_of_order": 2,
                                                "out_of_bounds": 0})
        self.assertFalse(summary["mostly_flagged"])  # 3/10 is not above 0.30
        words[3].flagged, words[3].reasons = True, ["bad_duration"]
        self.assertTrue(flag_summary(words)["mostly_flagged"])  # 4/10 is

    def test_empty(self):
        summary = flag_summary([])
        self.assertEqual((summary["total"], summary["share"], summary["mostly_flagged"]),
                         (0, 0.0, False))


class WordsJsonTest(TempDirTest):
    def setUp(self) -> None:
        super().setUp()
        lyrics = read_lyrics(self.write("lyrics.txt", "Mere samne waali\n\nkhidkī mein 🌙\n"))
        words = build_words(lyrics, [RawWord(0.5, 0.9, 0.93), RawWord(0.9, 1.4, 0.8),
                                     RawWord(None, None, None), RawWord(2.0, 2.61, 0.5),
                                     RawWord(2.6, 3.1, None), RawWord(None, None, None)])
        apply_flags(words, 30.125, None)
        self.doc = make_doc("khidki", self.dir / "audio.wav", 30.125, "ab" * 32, lyrics, ALIGNER,
                            words)
        self.path = self.dir / "words.json"

    def test_make_doc_shape(self):
        doc = self.doc
        self.assertEqual(list(doc), ["version", "song", "audio", "lyrics", "aligner", "created",
                                     "words"])
        self.assertEqual(doc["audio"], {"file": "audio.wav", "duration_s": 30.125,
                                        "sha256": "ab" * 32})
        self.assertEqual(list(doc["lyrics"]), ["file", "sha256", "lines"])
        self.assertEqual(doc["lyrics"]["lines"], ["Mere samne waali", "", "khidkī mein 🌙"])
        self.assertEqual(doc["aligner"], ALIGNER)
        self.assertRegex(doc["created"], r"^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d$")
        self.assertEqual(list(doc["words"][0]), ["i", "text", "line", "start", "end", "score",
                                                 "flagged", "reasons"])
        self.assertEqual(doc["words"][0], {"i": 0, "text": "Mere", "line": 0, "start": 0.5,
                                           "end": 0.9, "score": 0.93, "flagged": False,
                                           "reasons": []})
        self.assertEqual([w["text"] for w in doc["words"]],
                         ["Mere", "samne", "waali", "khidkī", "mein", "🌙"])
        self.assertEqual(validate(doc), [])

    def test_round_trip(self):
        save_words(self.path, self.doc)
        loaded = load_words(self.path)
        self.assertEqual(loaded, self.doc)
        self.assertEqual(list(loaded), list(self.doc))  # key order survives

    def test_layout_one_word_per_line(self):
        save_words(self.path, self.doc)
        text = self.path.read_text(encoding="utf-8")
        self.assertTrue(text.endswith("\n}\n"))
        lines = text.splitlines()
        self.assertEqual(lines[:2], ["{", '  "version": 1,'])  # header indented 2 spaces
        first = lines.index('  "words": [')
        n = len(self.doc["words"])
        self.assertEqual(lines[first + 1 + n:], ["  ]", "}"])
        for line, word in zip(lines[first + 1:first + 1 + n], self.doc["words"]):
            self.assertTrue(line.startswith('    {"i": '), line)
            self.assertEqual(json.loads(line.strip().rstrip(",")), word)
        self.assertIn('"text": "khidkī"', text)  # ensure_ascii=False: readable, not \u escapes
        self.assertNotIn("\\u", text)

    def test_load_tolerates_bom(self):
        save_words(self.path, self.doc)
        self.path.write_bytes(b"\xef\xbb\xbf" + self.path.read_bytes())
        self.assertEqual(load_words(self.path), self.doc)


class ValidateTest(TempDirTest):
    def setUp(self) -> None:
        super().setUp()
        self.lyrics_path = self.write("lyrics.txt", "Mere samne\n\nwaali khidki mein\n")
        self.audio_path = self.write("audio.wav", b"RIFF not really audio")
        lyrics = read_lyrics(self.lyrics_path)
        words = build_words(lyrics, [RawWord(0.5, 0.9, 0.9), RawWord(0.9, 1.4, 0.8),
                                     RawWord(None, None, None), RawWord(2.0, 2.6, 0.7),
                                     RawWord(2.6, 3.1, 0.9)])
        apply_flags(words, 10.0, None)
        self.doc = make_doc("song", self.audio_path, 10.0, sha256_file(self.audio_path), lyrics,
                            ALIGNER, words)

    def test_good_doc_is_valid(self):
        self.assertEqual(self.doc["words"][2]["reasons"], ["not_placed"])  # flagged is fine
        self.assertEqual(validate(self.doc), [])
        self.assertEqual(validate(self.doc, self.lyrics_path, self.audio_path), [])
        save_words(self.dir / "words.json", self.doc)
        self.assertEqual(validate(load_words(self.dir / "words.json"), self.lyrics_path,
                                  self.audio_path), [])

    def test_accepts_legit_hand_edits(self):
        cases = {
            "flag cleared after adding times": {("words", 2, "start"): 1.5,
                                                ("words", 2, "end"): 1.9,
                                                ("words", 2, "flagged"): False,
                                                ("words", 2, "reasons"): []},
            "equal starts": {("words", 1, "start"): 0.5},
            "end within the audio-end tolerance": {("words", 4, "end"): 10.04},
            "flagged word with impossible times": {("words", 2, "start"): 0.1,
                                                   ("words", 2, "end"): 0.05},
        }
        for name, edits in cases.items():
            with self.subTest(name):
                self.assertEqual(validate(edited(self.doc, edits)), [])

    def test_rejects_hand_edit_mistakes(self):
        cases = {  # name: (edits, index of the word the one error must name, or None)
            "text changed": ({("words", 1, "text"): "Samne"}, 1),
            "line changed": ({("words", 3, "line"): 0}, 3),
            "start before an earlier start": ({("words", 3, "start"): 0.7}, 3),
            "flag cleared with no time": ({("words", 2, "flagged"): False,
                                           ("words", 2, "reasons"): []}, 2),
            "flagged with no reasons": ({("words", 0, "flagged"): True}, 0),
            "unknown reason": ({("words", 2, "reasons"): ["not_placed", "guessed"]}, 2),
            "i not contiguous": ({("words", 3, "i"): 7}, 3),
            "negative start": ({("words", 0, "start"): -0.1}, 0),
            "end not after start": ({("words", 0, "end"): 0.5}, 0),
            "end past the audio": ({("words", 4, "end"): 10.2}, 4),
            "word deleted": ({("words", 4): DELETE}, None),
            "wrong version": ({("version",): 2}, None),
        }
        for name, (edits, word_i) in cases.items():
            with self.subTest(name):
                doc = edited(self.doc, edits)
                errors = validate(doc)
                self.assertEqual(len(errors), 1, errors)
                if word_i is not None:
                    prefix = f'word {word_i} ("{doc["words"][word_i]["text"]}"): '
                    self.assertTrue(errors[0].startswith(prefix), errors)

    def test_stale_lyrics(self):
        self.lyrics_path.write_bytes(b"Mere saamne\n\nwaali khidki mein\n")
        errors = validate(self.doc, lyrics_path=self.lyrics_path)
        self.assertEqual(len(errors), 1, errors)
        self.assertIn("stale", errors[0])

    def test_stale_audio(self):
        self.audio_path.write_bytes(b"RIFF a different take")
        errors = validate(self.doc, audio_path=self.audio_path)
        self.assertEqual(len(errors), 1, errors)
        self.assertIn("stale", errors[0])

    def test_lines_edited_inside_words_json(self):
        doc = edited(self.doc, {("lyrics", "lines", 0): "Mere Samne",
                                ("words", 1, "text"): "Samne"})
        self.assertEqual(validate(doc), [])  # consistent with itself...
        errors = validate(doc, lyrics_path=self.lyrics_path)  # ...but no longer lyrics.txt
        self.assertEqual(len(errors), 1, errors)
        self.assertIn("lyrics.lines", errors[0])

    def test_malformed_input_is_reported_not_raised(self):
        cases = {
            "no words": {("words",): DELETE},
            "words not a list": {("words",): {"i": 0}},
            "word not an object": {("words", 1): 42},
            "word missing a key": {("words", 1, "start"): DELETE},
            "start is text": {("words", 1, "start"): "0.9"},
            "start is a bool": {("words", 1, "start"): True},
            "start is NaN": {("words", 1, "start"): float("nan")},
            "start is a huge int": {("words", 1, "start"): 10 ** 400},
            "flagged is text": {("words", 1, "flagged"): "false"},
            "reasons is text": {("words", 2, "reasons"): "not_placed"},
            "reason is an object": {("words", 2, "reasons"): [{}]},
            "score is text": {("words", 0, "score"): "high"},
            "no lyrics": {("lyrics",): DELETE},
            "lines not a list": {("lyrics", "lines"): "Mere samne"},
            "a line is a number": {("lyrics", "lines", 1): 5},
            "no audio": {("audio",): DELETE},
            "duration is text": {("audio", "duration_s"): "10"},
            "no created": {("created",): DELETE},
        }
        for name, edits in cases.items():
            with self.subTest(name):
                errors = validate(edited(self.doc, edits), self.lyrics_path, self.audio_path)
                self.assertTrue(errors)
                self.assertTrue(all(isinstance(e, str) for e in errors), errors)
        for doc in (None, [], "words", {}):
            with self.subTest(doc=doc):
                self.assertTrue(validate(doc))
        missing = self.dir / "missing.txt"
        self.assertEqual(len(validate(self.doc, lyrics_path=missing, audio_path=missing)), 2)


if __name__ == "__main__":
    unittest.main()
