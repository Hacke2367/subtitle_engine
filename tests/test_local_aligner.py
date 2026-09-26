"""local_aligner pure logic: word -> tokens, and aligned spans -> one RawWord per word.

No model, no audio, no network. place() runs on a hand-made emission (needs torchaudio only).
"""
import importlib.util
import unittest
from pathlib import Path

from lyric_engine import local_aligner as la
from lyric_engine.timing import RawWord

NONE = RawWord(None, None, None)
A, B = la.LABELS.index("a"), la.LABELS.index("b")


class TokenizeTest(unittest.TestCase):
    def test_lowercase_letters_and_apostrophe_kept_punctuation_dropped(self):
        ids = [la.LABELS.index(c) for c in "ain't"]
        self.assertEqual(la.tokenize(["Ain't,"]), [ids])

    def test_words_with_nothing_the_model_knows_are_empty(self):
        self.assertEqual(la.tokenize(["...", "42", "—", "ok"]),
                         [[], [], [], [la.LABELS.index("o"), la.LABELS.index("k")]])

    def test_nothing_placeable_returns_unplaced_without_touching_audio(self):
        raw, native = la.align(Path("no-such-file.wav"), ["!!", "42"])
        self.assertEqual(raw, [NONE, NONE])
        self.assertEqual((native["n_tokens"], native["unplaced"]), (0, 2))

    def test_line_indexes_must_match_words(self):
        with self.assertRaises(ValueError):
            la.align(Path("no-such-file.wav"), ["ek", "do"], lines=[0])


@unittest.skipUnless(importlib.util.find_spec("torchaudio"), "torchaudio not installed")
class PlaceTest(unittest.TestCase):
    @staticmethod
    def emission(frames: int, peaks: dict[int, int]):
        """Log-probs: blank everywhere but token peaks[f] at frame f, plus the model's star column."""
        import torch

        em = torch.full((frames, len(la.LABELS)), -10.0)
        em[:, la.BLANK] = -0.01
        for f, token in peaks.items():
            em[f, la.BLANK], em[f, token] = -10.0, -0.01
        return torch.cat([em, torch.zeros(frames, 1)], dim=1)

    def test_one_raw_word_per_word_and_empty_words_unplaced(self):
        raw = la.place(self.emission(20, {3: A, 6: B, 12: A}), [[A, B], [], [A]])
        self.assertEqual(raw, [RawWord(0.06, 0.14, 0.99), NONE, RawWord(0.24, 0.26, 0.99)])

    def test_repeated_letter_needs_its_own_frames(self):
        raw = la.place(self.emission(10, {2: A, 5: A}), [[A, A]])
        self.assertEqual(raw, [RawWord(0.04, 0.12, 0.99)])

    def test_star_between_lines_absorbs_unwritten_singing(self):
        k = la.LABELS.index("k")  # sung at frames 5-9 but not in the lyrics
        em = self.emission(16, {2: A, **{f: k for f in range(5, 10)}, 12: B})
        raw = la.place(em, [[A], [B]], lines=[0, 1])
        self.assertEqual(raw, [RawWord(0.04, 0.06, 0.99), RawWord(0.24, 0.26, 0.99)])

    def test_too_few_frames_is_an_error_not_a_guess(self):
        with self.assertRaises(RuntimeError):
            la.place(self.emission(4, {}), [[A, A, A, B]])


if __name__ == "__main__":
    unittest.main()
