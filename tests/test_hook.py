"""hook: where a clip of the song's main part starts and ends (no models needed here)."""
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import numpy as np

from lyric_engine import hook as H


def sung(spans, total=70.0):
    a = np.zeros(round(total / H.FINE_S), dtype=bool)
    for s, e in spans:
        a[round(s / H.FINE_S):round(e / H.FINE_S)] = True
    return a


class PhraseTest(unittest.TestCase):
    def test_a_lone_hum_is_skipped_and_the_first_line_starts_the_clip(self):
        a = sung([(21.7, 24.9), (27.9, 31.2), (31.6, 35.0), (35.4, 55.4)])
        self.assertAlmostEqual(H._phrase_start(25.0, a, a.astype(float)), 27.65, places=1)

    def test_the_clip_ends_after_the_last_whole_line(self):
        a = sung([(27.9, 31.2), (31.6, 55.4), (62.0, 63.0)])   # a breath inside, a pause after
        self.assertAlmostEqual(H._phrase_end(57.7, a, a.astype(float)), 55.9, places=1)


class SourceTest(unittest.TestCase):
    def test_full_song_is_preferred_and_a_missing_one_is_explained(self):
        with tempfile.TemporaryDirectory() as tmp:
            d = Path(tmp)
            with self.assertRaisesRegex(FileNotFoundError, "audio.mp3"):
                H.source_audio(d)
            (d / "audio.wav").write_bytes(b"")
            self.assertEqual(H.source_audio(d).name, "audio.wav")
            (d / "full.mp3").write_bytes(b"")
            self.assertEqual(H.source_audio(d).name, "full.mp3")


if __name__ == "__main__":
    unittest.main()
