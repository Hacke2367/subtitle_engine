"""Where cues break, how long they stay, and the .srt they become."""
import unittest

from voice_subs.cues import Cue, to_cues, to_srt


def words(*triples):
    return [{"text": t, "start": s, "end": e} for t, s, e in triples]


class BreakTest(unittest.TestCase):
    def test_a_pause_starts_a_new_cue(self):
        cues = to_cues(words(("ek", 0.0, 0.3), ("do", 0.4, 0.7), ("teen", 1.5, 1.9)))
        self.assertEqual([c.text for c in cues], ["ek do", "teen"])

    def test_a_sentence_end_starts_a_new_cue(self):
        cues = to_cues(words(("hai.", 0.0, 0.3), ("aur", 0.35, 0.7)))
        self.assertEqual([c.text for c in cues], ["hai.", "aur"])

    def test_a_long_line_is_split_before_it_passes_the_limit(self):
        said = words(*[(f"word{i}", i * 0.3, i * 0.3 + 0.25) for i in range(12)])
        cues = to_cues(said, max_chars=20)
        self.assertTrue(all(len(c.text) <= 20 for c in cues), [c.text for c in cues])

    def test_a_cue_never_runs_longer_than_the_limit(self):
        said = words(*[("a", i * 1.0, i * 1.0 + 0.9) for i in range(10)])
        cues = to_cues(said, max_dur_s=3.0, pause_s=5.0)
        self.assertTrue(all(c.end - c.start <= 4.0 for c in cues))

    def test_cue_times_come_from_the_words_themselves(self):
        cues = to_cues(words(("ek", 1.25, 1.5), ("do", 1.6, 2.9)))
        self.assertEqual((cues[0].start, cues[0].end), (1.25, 2.9))

    def test_the_words_are_kept_in_order_and_unchanged(self):
        said = words(("Maturity", 0.0, 0.5), ("aapke", 0.55, 0.9), ("andar", 0.95, 1.4))
        self.assertEqual(to_cues(said)[0].text, "Maturity aapke andar")


class HoldTest(unittest.TestCase):
    def test_a_short_cue_is_held_on_screen(self):
        cues = to_cues(words(("haan", 0.0, 0.2), ("phir", 5.0, 5.4)), duration=9.0)
        self.assertAlmostEqual(cues[0].end, 1.0)

    def test_the_hold_never_reaches_the_next_cue(self):
        cues = to_cues(words(("haan", 0.0, 0.2), ("phir", 0.7, 1.4)), duration=9.0)
        self.assertLess(cues[0].end, cues[1].start)

    def test_the_hold_never_passes_the_end_of_the_audio(self):
        cues = to_cues(words(("haan", 8.6, 8.8)), duration=8.9)
        self.assertLessEqual(cues[0].end, 8.9)


class SrtTest(unittest.TestCase):
    def test_the_file_reads_as_subrip(self):
        text = to_srt([Cue(0.0, 1.5, "pehla"), Cue(1.6, 3.25, "doosra")])
        self.assertEqual(text, "1\n00:00:00,000 --> 00:00:01,500\npehla\n\n"
                               "2\n00:00:01,600 --> 00:00:03,250\ndoosra\n")

    def test_an_hour_in_is_stamped_with_hours(self):
        self.assertIn("01:02:03,004", to_srt([Cue(3723.004, 3724.0, "x")]))


if __name__ == "__main__":
    unittest.main()
