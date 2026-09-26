"""review.py: comparison maths, run report, the preview's ASS events, one offline preview render."""
from __future__ import annotations

import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from lyric_engine import review

TEXTS = ["Mere", "saamne", "waali", "khidki", "mein"]


def _word(i: int, text: str, line: int, start: float | None, end: float | None,
          score: float | None = 0.9, reasons: tuple[str, ...] = ()) -> dict:
    return {"i": i, "text": text, "line": line, "start": start, "end": end, "score": score,
            "flagged": bool(reasons), "reasons": list(reasons)}


def _doc(words: list[dict], lines: list[str], duration: float = 10.0,
         variant: str = "E-raw") -> dict:
    return {"version": 1, "song": "test",
            "audio": {"file": "audio.wav", "duration_s": duration, "sha256": "0" * 64},
            "lyrics": {"file": "lyrics.txt", "sha256": "0" * 64, "lines": lines},
            "aligner": {"variant": variant, "input": "raw", "settings": {}, "reused_cache": False},
            "created": "2026-09-26T19:00:00", "words": words}


def _starts_doc(variant: str, starts: list[float | None]) -> dict:
    words = [_word(i, t, 0, s, None if s is None else s + 0.3,
                   reasons=() if s is not None else ("not_placed",))
             for i, (t, s) in enumerate(zip(TEXTS, starts))]
    return _doc(words, [" ".join(TEXTS)], variant=variant)


def _events(ass: str) -> list[tuple[int, str, str, str, str]]:
    """Dialogue lines as (layer, start, end, style, text)."""
    events = []
    for line in ass.splitlines():
        if line.startswith("Dialogue: "):
            layer, start, end, style, *_, text = line[len("Dialogue: "):].split(",", 9)
            events.append((int(layer), start, end, style, text))
    return events


class ComparisonTest(unittest.TestCase):
    def setUp(self):
        # spreads: i0 0.3, i1 0.6, i2 0.2 (B unplaced), i3 0.0; i4 only placed by A -> skipped
        self.docs = {"A": _starts_doc("A", [0.0, 1.0, 2.0, 3.0, 4.0]),
                     "B": _starts_doc("B", [0.1, 1.5, None, 3.0, None]),
                     "C": _starts_doc("C", [0.3, 0.9, 2.2, None, None])}

    def test_disagreement_maths(self):
        rows = review._disagreements(self.docs, top_n=10)
        self.assertEqual([(r.index, r.spread, r.earliest) for r in rows],
                         [(1, 0.6, 0.9), (0, 0.3, 0.0), (2, 0.2, 2.0), (3, 0.0, 3.0)])
        self.assertEqual(rows[2].starts, {"A": 2.0, "B": None, "C": 2.2})
        self.assertEqual(len(review._disagreements(self.docs, top_n=2)), 2)

    def test_comparison_report(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "comparison.md"
            review.write_comparison({**self.docs, "D": None}, {"D": "HTTP 401: <redacted>"},
                                    out, top_n=3)
            text = out.read_text(encoding="utf-8")
        self.assertIn("| A | ok | 0 of 5 (0%) | [report](A/report.md) |", text)
        self.assertIn("| B | ok | 2 of 5 (40%) **mostly flagged** |", text)
        self.assertIn("| D | error: HTTP 401: <redacted> | - | - |", text)
        rows = [line for line in text.splitlines() if line.startswith("| 0")]
        self.assertEqual(rows, ["| 00:00.9 | 1 | saamne | 1 | 1.000 | 1.500 | 0.900 | 0.600 |",
                                "| 00:00.0 | 0 | Mere | 1 | 0.000 | 0.100 | 0.300 | 0.300 |",
                                "| 00:02.0 | 2 | waali | 1 | 2.000 | - | 2.200 | 0.200 |"])

    def test_nothing_to_compare(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "comparison.md"
            review.write_comparison({"A": self.docs["A"], "B": None}, {"B": "boom"}, out)
            self.assertIn("nothing to compare", out.read_text(encoding="utf-8"))

    def test_mmss(self):
        self.assertEqual([review._mmss(t) for t in (0.0, 0.94, 65.34, 59.96)],
                         ["00:00.0", "00:00.9", "01:05.3", "01:00.0"])


class RunReportTest(unittest.TestCase):
    def test_flagged_words_lowest_scores_and_warning(self):
        words = [_word(0, "Mere", 0, 0.5, 0.9, score=0.95),
                 _word(1, "saa|mne", 0, 1.0, 1.4, score=0.2, reasons=("low_confidence",)),
                 _word(2, "waali", 1, None, None, score=None, reasons=("not_placed",)),
                 _word(3, "khidki", 1, 2.0, 1.9, score=0.5, reasons=("bad_duration",))]
        doc = _doc(words, ["Mere saa|mne", "waali khidki"])
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "report.md"
            review.write_run_report(doc, out, wall_s=12.34, reused=True, cost_note="37 credits")
            text = out.read_text(encoding="utf-8")
        self.assertIn("**Warning: 75% of the words are flagged**", text)
        for expected in ("Wall time: 12.3 s", "Reused cached aligner result: yes",
                         "Cost: 37 credits", "3 of 4 words flagged (75.0%)", "| not_placed | 1 |",
                         r"| 1 | saa\|mne | 1 | 1.000 | 1.400 | 0.2 | low_confidence |",
                         "| 2 | waali | 2 | - | - | - | not_placed |",
                         "| 3 | khidki | 2 | 2.000 | 1.900 | 0.5 | bad_duration |"):
            self.assertIn(expected, text)
        lowest = text.split("lowest-score words")[1]
        self.assertLess(lowest.index("saa"), lowest.index("khidki"))
        self.assertLess(lowest.index("khidki"), lowest.index("Mere"))
        self.assertNotIn("waali", lowest)                   # no score, so not ranked


class WriteAssTest(unittest.TestCase):
    def _ass(self, doc: dict) -> str:
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "preview.ass"
            review.write_ass(doc, out, title="E-raw")
            return out.read_text(encoding="utf-8")

    def test_layers_flags_and_unplaced_words(self):
        words = [_word(0, "Mere", 0, 1.0, 1.4),
                 _word(1, "saamne", 0, 1.5, 2.0, reasons=("low_confidence",)),
                 _word(2, "waali", 0, 2.1, 2.6),
                 _word(3, "khidki", 0, None, None, score=None, reasons=("not_placed",)),
                 _word(4, "chaand", 2, None, None, score=None, reasons=("not_placed",))]
        ass = self._ass(_doc(words, ["Mere saamne waali khidki", "", "chaand"], duration=3.5))
        self.assertIn("PlayResX: 540\nPlayResY: 960", ass)
        events = _events(ass)
        base = [e for e in events if e[3] == "Lyric" and e[0] == 0]
        lit = [e for e in events if e[3] == "Lyric" and e[0] == 1]

        # One base event: line 0, padded 0.25 s. Line 2 has no placed word: nothing at all.
        self.assertEqual([e[1:3] for e in base], [("0:00:00.75", "0:00:02.85")])
        self.assertEqual(base[0][4], r"{\pos(270,480)}Mere {\c&H0000FF&}saamne{\c&HFFFFFF&} "
                                     r"waali {\c&H0000FF&}khidki{\c&HFFFFFF&}")
        self.assertNotIn("chaand", ass)

        # Lit: only placed, non-flagged words. Mere until saamne's start, waali until its end.
        self.assertEqual([e[1:3] for e in lit], [("0:00:01.00", "0:00:01.50"),
                                                 ("0:00:02.10", "0:00:02.60")])
        self.assertEqual(lit[0][4], r"{\pos(270,480)\alpha&HFF&}{\alpha&H00&\c&H00FFFF&}Mere"
                                    r"{\alpha&HFF&} saamne waali khidki")
        self.assertIn(r"{\alpha&H00&\c&H00FFFF&}waali{\alpha&HFF&}", lit[1][4])

        # Title top-left for the whole clip, a clock tick per second top-right.
        info = [e for e in events if e[3] == "Info"]
        self.assertEqual((info[0][1], info[0][2], info[0][4]),
                         ("0:00:00.00", "0:00:03.50", r"{\an7\pos(12,12)}E-raw"))
        self.assertEqual([e[4] for e in info[1:]], [rf"{{\an9\pos(528,12)}}00:0{s}"
                                                     for s in range(4)])
        self.assertEqual(info[-1][1:3], ("0:00:03.00", "0:00:03.50"))

    def test_neighbouring_lines_never_overlap(self):
        words = [_word(0, "Mere", 0, 1.0, 2.0), _word(1, "saamne", 1, 2.2, 3.0),
                 _word(2, "waali", 2, 5.0, 5.5)]
        ass = self._ass(_doc(words, ["Mere", "saamne", "waali"]))
        base = [e[1:3] for e in _events(ass) if e[3] == "Lyric" and e[0] == 0]
        # 2.0 -> 2.2 is too short for two pads: both stop at the middle. 3.0 -> 5.0 isn't.
        self.assertEqual(base, [("0:00:00.75", "0:00:02.10"), ("0:00:02.10", "0:00:03.25"),
                                ("0:00:04.75", "0:00:05.75")])

    def test_escapes_override_characters(self):
        words = [_word(0, "{x}", 0, 1.0, 2.0)]
        ass = self._ass(_doc(words, ["{x}"]))
        self.assertIn(r"{\pos(270,480)}\{x\}", ass)


@unittest.skipUnless(shutil.which("ffmpeg") and shutil.which("ffprobe"), "ffmpeg not on PATH")
class RenderPreviewTest(unittest.TestCase):
    def test_two_second_preview(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            audio = tmp / "silence.wav"
            subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-f", "lavfi",
                            "-i", "anullsrc=r=44100:cl=mono", "-t", "2", str(audio)],
                           check=True, capture_output=True)
            words = [_word(0, "Mere", 0, 0.2, 0.6),
                     _word(1, "saamne", 0, 0.7, 1.2, reasons=("low_confidence",)),
                     _word(2, "khidki", 0, None, None, score=None, reasons=("not_placed",))]
            doc = _doc(words, ["Mere saamne khidki"], duration=2.0)

            out = review.render_preview(doc, audio, tmp / "E-raw" / "preview.mp4", title="E-raw")

            self.assertTrue(out.is_file())
            self.assertTrue((tmp / "E-raw" / "preview.ass").is_file())
            probe = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                                    "-of", "default=nw=1:nk=1", str(out)],
                                   capture_output=True, text=True, check=True)
            self.assertAlmostEqual(float(probe.stdout), 2.0, delta=0.15)


if __name__ == "__main__":
    unittest.main()
