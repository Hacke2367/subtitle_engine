"""Where cues break, how long they stay, and the .srt they become."""
import unittest

from voice_subs.cues import (HOLD_S, LAST_HOLD_S, LEAD_S, MIN_DUR_S, Cue, to_cues,
                              to_srt)


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

    def test_a_cue_s_words_never_run_longer_than_the_limit(self):
        said = words(*[("a", i * 1.0, i * 1.0 + 0.9) for i in range(10)])
        cues = to_cues(said, max_dur_s=3.0, pause_s=5.0)
        self.assertTrue(all(len(c.text.split()) <= 3 for c in cues), [c.text for c in cues])

    def test_the_words_are_kept_in_order_and_unchanged(self):
        said = words(("Maturity", 0.0, 0.5), ("aapke", 0.55, 0.9), ("andar", 0.95, 1.4))
        self.assertEqual(to_cues(said)[0].text, "Maturity aapke andar")

    def test_a_length_break_never_strands_a_word_that_leans_on_its_neighbour(self):
        line = "aur vo experience kisi na kisi quantity mein har field".split()
        said = words(*[(w, i * 0.3, i * 0.3 + 0.25) for i, w in enumerate(line)])
        texts = [c.text for c in to_cues(said, max_chars=36)]
        self.assertTrue(all(not t.startswith("mein") for t in texts), texts)
        self.assertTrue(all(not t.endswith(("kisi", "ek")) for t in texts), texts)
        self.assertEqual(" ".join(texts), " ".join(line))     # every word, once, in order


class DisplayTimeTest(unittest.TestCase):
    def test_a_cue_shows_just_before_its_first_word_and_never_before_zero(self):
        cues = to_cues(words(("ek", 0.05, 0.4), ("do", 2.0, 2.4)))
        self.assertEqual(cues[0].start, 0.0)
        self.assertAlmostEqual(cues[1].start, 2.0 - LEAD_S)

    def test_back_to_back_cues_swap_with_no_blank_between(self):
        cues = to_cues(words(("hai.", 0.0, 0.5), ("aur", 0.6, 1.0), ("phir", 1.05, 1.6)))
        self.assertEqual(cues[0].end, cues[1].start)

    def test_after_a_silence_a_cue_holds_briefly_then_clears(self):
        cues = to_cues(words(("ek", 0.0, 1.5), ("do", 5.0, 5.4)))
        self.assertAlmostEqual(cues[0].end, 1.5 + HOLD_S)

    def test_a_short_cue_is_held_long_enough_to_read(self):
        cues = to_cues(words(("haan", 1.0, 1.2), ("phir", 6.0, 6.4)))
        self.assertAlmostEqual(cues[0].end - cues[0].start, MIN_DUR_S)

    def test_a_cue_never_ends_before_its_last_word_or_runs_into_the_next(self):
        said = words(*[(f"w{i}", i * 0.7, i * 0.7 + 0.6) for i in range(12)])
        cues = to_cues(said, max_chars=12)
        for cue, nxt in zip(cues, cues[1:]):
            self.assertLessEqual(cue.end, nxt.start)
        last_word_end = {c.text.split()[-1]: c.end for c in cues}
        for w in said:
            if w["text"] in last_word_end:
                self.assertGreaterEqual(last_word_end[w["text"]], w["end"])

    def test_the_last_cue_stays_to_the_end_of_the_clip_but_not_past_it(self):
        cues = to_cues(words(("hoga.", 10.0, 10.5)), duration=12.0)
        self.assertEqual(cues[-1].end, 12.0)
        cues = to_cues(words(("hoga.", 10.0, 10.5)), duration=40.0)
        self.assertAlmostEqual(cues[-1].end, 10.5 + LAST_HOLD_S)


class SrtTest(unittest.TestCase):
    def test_the_file_reads_as_subrip(self):
        text = to_srt([Cue(0.0, 1.5, "pehla"), Cue(1.6, 3.25, "doosra")])
        self.assertEqual(text, "1\n00:00:00,000 --> 00:00:01,500\npehla\n\n"
                               "2\n00:00:01,600 --> 00:00:03,250\ndoosra\n")

    def test_an_hour_in_is_stamped_with_hours(self):
        self.assertIn("01:02:03,004", to_srt([Cue(3723.004, 3724.0, "x")]))


if __name__ == "__main__":
    unittest.main()
