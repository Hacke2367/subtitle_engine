"""Where cues break, how long they stay, and the .srt they become."""
import unittest

from voice_subs.cues import (HOLD_S, LAST_HOLD_S, LEAD_S, MIN_DUR_S, Cue, to_cues,
                              to_srt)


def words(*triples):
    return [{"text": t, "start": s, "end": e} for t, s, e in triples]


def said(sentence: str, start: float = 0.0, step: float = 0.4):
    """A sentence spoken evenly, one word every `step` seconds from `start`."""
    return words(*[(w, start + i * step, start + i * step + step - 0.05)
                   for i, w in enumerate(sentence.split())])


class BreakTest(unittest.TestCase):
    def test_a_pause_starts_a_new_cue(self):
        cues = to_cues(said("ek do teen") + said("char paanch chhe", start=1.8))
        self.assertEqual([c.text for c in cues], ["ek do teen", "char paanch chhe"])

    def test_a_sentence_end_starts_a_new_cue(self):
        cues = to_cues(said("ye sach hai.") + said("aur phir kya", start=1.2))
        self.assertEqual([c.text for c in cues], ["ye sach hai.", "aur phir kya"])

    def test_a_long_line_is_split_before_it_passes_the_limit(self):
        cues = to_cues(said(" ".join(f"word{i}" for i in range(12)), step=0.3), max_chars=20)
        self.assertTrue(all(len(c.text) <= 26 for c in cues), [c.text for c in cues])

    def test_a_long_run_splits_into_even_cues_not_a_full_one_and_a_scrap(self):
        line = "aur vo experience kisi na kisi quantity mein har field mein kaam aata hai."
        texts = [c.text for c in to_cues(said(line, step=0.25))]
        self.assertEqual(len(texts), 2)
        self.assertTrue(all(len(t.split()) >= 5 for t in texts), texts)

    def test_a_cue_s_words_never_run_longer_than_the_limit(self):
        cues = to_cues(said("a " * 10, step=1.0), max_dur_s=3.0, pause_s=5.0)
        self.assertTrue(all(len(c.text.split()) <= 3 for c in cues), [c.text for c in cues])

    def test_the_words_are_kept_in_order_and_unchanged(self):
        line = "Maturity aapke andar aati hai"
        self.assertEqual(to_cues(said(line))[0].text, line)

    def test_a_split_never_strands_a_word_that_leans_on_its_neighbour(self):
        line = "aur vo experience kisi na kisi quantity mein har field"
        texts = [c.text for c in to_cues(said(line, step=0.3), max_chars=36)]
        self.assertTrue(all(not t.startswith("mein") for t in texts), texts)
        self.assertTrue(all(not t.endswith(("kisi", "ek")) for t in texts), texts)
        self.assertEqual(" ".join(texts), line)              # every word, once, in order


class ScrapTest(unittest.TestCase):
    def test_a_scrap_joins_the_sentence_it_belongs_to(self):
        cues = to_cues(said("You can be able to select") + said("this.", start=2.9)
                       + said("So if you select the menu", start=3.6))
        self.assertEqual(cues[0].text, "You can be able to select this.")

    def test_a_scrap_after_a_long_silence_stays_alone(self):
        cues = to_cues(said("pehli baat ye hai.") + said("bas.", start=4.0))
        self.assertEqual(cues[-1].text, "bas.")


class DisplayTimeTest(unittest.TestCase):
    def test_a_cue_shows_just_before_its_first_word_and_never_before_zero(self):
        cues = to_cues(said("ek do teen", start=0.05) + said("char paanch chhe", start=3.0))
        self.assertEqual(cues[0].start, 0.0)
        self.assertAlmostEqual(cues[1].start, 3.0 - LEAD_S)

    def test_back_to_back_cues_swap_with_no_blank_between(self):
        cues = to_cues(said("ye sach hai.") + said("aur phir kya hua", start=1.25))
        self.assertEqual(cues[0].end, cues[1].start)

    def test_a_blank_too_short_to_read_as_a_pause_is_closed(self):
        # 0.6 s of silence: holding 0.4 s and leading 0.1 s would leave a 0.1 s blink.
        cues = to_cues(said("ye sach hai.") + said("aur phir kya hua", start=1.75))
        self.assertEqual(cues[0].end, cues[1].start)

    def test_after_a_real_silence_a_cue_holds_briefly_then_clears(self):
        cues = to_cues(said("ek do teen") + said("char paanch chhe", start=5.0))
        self.assertAlmostEqual(cues[0].end, 1.15 + HOLD_S)

    def test_a_short_cue_is_held_long_enough_to_read(self):
        cues = to_cues(words(("haan", 1.0, 1.2)) + said("phir se dekho", start=6.0))
        self.assertAlmostEqual(cues[0].end - cues[0].start, MIN_DUR_S)

    def test_a_cue_never_ends_before_its_last_word_or_runs_into_the_next(self):
        spoken = said(" ".join(f"w{i}" for i in range(12)), step=0.7)
        cues = to_cues(spoken, max_chars=12)
        for cue, nxt in zip(cues, cues[1:]):
            self.assertLessEqual(cue.end, nxt.start)
        ends = {c.text.split()[-1]: c.end for c in cues}
        for word in spoken:
            if word["text"] in ends:
                self.assertGreaterEqual(ends[word["text"]], word["end"])

    def test_the_last_cue_stays_to_the_end_of_the_clip_but_not_past_it(self):
        cues = to_cues(said("kuchh na hoga.", start=10.0), duration=12.0)
        self.assertEqual(cues[-1].end, 12.0)
        cues = to_cues(said("kuchh na hoga.", start=10.0), duration=40.0)
        self.assertAlmostEqual(cues[-1].end, 11.15 + LAST_HOLD_S)


class SrtTest(unittest.TestCase):
    def test_the_file_reads_as_subrip(self):
        text = to_srt([Cue(0.0, 1.5, "pehla"), Cue(1.6, 3.25, "doosra")])
        self.assertEqual(text, "1\n00:00:00,000 --> 00:00:01,500\npehla\n\n"
                               "2\n00:00:01,600 --> 00:00:03,250\ndoosra\n")

    def test_an_hour_in_is_stamped_with_hours(self):
        self.assertIn("01:02:03,004", to_srt([Cue(3723.004, 3724.0, "x")]))


if __name__ == "__main__":
    unittest.main()
