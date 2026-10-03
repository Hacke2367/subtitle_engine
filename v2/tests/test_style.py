"""Styled subtitles: words lit on their own times, unchanged, and an overlay that keeps its alpha."""
import re
import shutil
import subprocess
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from voice_subs import media
from voice_subs.cues import Cue, to_cues
from voice_subs.style import STYLES, Style, _line_break, pick_heroes, to_ass


def words(*triples):
    return [{"text": t, "start": s, "end": e} for t, s, e in triples]


def spaced(sentence: str):
    return words(*[(w, i, i + 0.5) for i, w in enumerate(sentence.split())])


SAID = words(("prayaas", 1.0, 1.4), ("karne", 1.45, 1.7), ("ka", 1.8, 1.9))


def events(ass: str, layer: int) -> list[str]:
    return [line for line in ass.splitlines() if line.startswith(f"Dialogue: {layer},")]


def plain(text: str) -> str:
    """The event text as it would be read: override blocks and line breaks taken out."""
    return re.sub(r"\{[^}]*\}", "", text.split(",", 9)[-1]).replace("\\N", " ")


class AssTest(unittest.TestCase):
    def test_every_style_writes_its_layers_once_per_cue(self):
        cues = to_cues(SAID)
        for name, style in STYLES.items():
            with self.subTest(style=name):
                ass = to_ass(cues, SAID, style)
                for layer in (0, 1, 2):
                    self.assertEqual(len(events(ass, layer)), len(cues))

    def test_the_words_on_screen_are_the_cue_s_words_unchanged(self):
        cues = to_cues(SAID)
        for name, style in STYLES.items():
            with self.subTest(style=name):
                for layer in (0, 1, 2):
                    self.assertEqual(plain(events(to_ass(cues, SAID, style), layer)[0]),
                                     "prayaas karne ka")

    def test_each_word_lights_up_at_its_own_time_from_the_audio(self):
        cues = to_cues(SAID)                 # shows at 0.9 s, 100 ms before the first word
        text = events(to_ass(cues, SAID, STYLES["ink"]), 2)[0]
        starts = [int(m) for m in
                  re.findall(r"\\t\((\d+),\d+,\\1c&H[0-9A-F]{6}&\\1a&H00&\)", text)]
        # 1.0, 1.45, 1.8 s, each lit 60 ms early, relative to the cue's 0.9 s.
        self.assertEqual(starts, [40, 490, 840])

    def test_a_word_stays_lit_until_the_next_one_starts(self):
        glow = events(to_ass(to_cues(SAID), SAID, STYLES["ink"]), 1)[0]
        # "prayaas" ends at 1.4 s, but "karne" lights at 490 ms: prayaas's glow goes out then.
        self.assertIn("\\t(490,630,\\3a&HFF&)}prayaas", glow)

    def test_no_word_gets_a_transform_libass_reads_as_the_whole_event(self):
        said = words(("pehla", 0.0, 0.4), ("doosra", 0.45, 0.9))
        for name, style in STYLES.items():
            with self.subTest(style=name):
                self.assertNotIn("\\t(0,", to_ass(to_cues(said), said, style))

    def test_back_to_back_cues_swap_without_a_fade(self):
        said = spaced("ye sach hai.") + words(*[(w, 3.2 + i * 0.5, 3.6 + i * 0.5)
                                                for i, w in enumerate("aur phir kya".split())])
        texts = events(to_ass(to_cues(said), said, STYLES["ink"]), 2)
        self.assertIn("\\fad(120,0)", texts[0])     # fades in from nothing, swaps out
        self.assertIn("\\fad(0,120)", texts[1])     # swaps in, fades out at the end

    def test_cue_times_are_the_cue_s_own(self):
        ass = to_ass([Cue(61.234, 62.5, "ek")], words(("ek", 61.334, 62.0)), STYLES["ink"])
        self.assertIn("Dialogue: 2,0:01:01.23,0:01:02.50,Text", ass)

    def test_words_that_do_not_spell_the_cue_are_refused(self):
        with self.assertRaises(ValueError):
            to_ass([Cue(0, 1, "ek do")], words(("ek", 0, 0.4), ("teen", 0.5, 1)), STYLES["ink"])

    def test_the_canvas_follows_the_video(self):
        ass = to_ass(to_cues(SAID), SAID, STYLES["ink"], size=(720, 1280))
        self.assertIn("PlayResX: 720", ass)
        self.assertIn("Style: Text,Instrument Sans SemiBold,45,", ass)   # 68 x 720/1080


def heroes_of(*sentences: str, step_s: float = 4.0) -> list[str | None]:
    """The hero word picked for each sentence, each sentence its own cue, step_s apart."""
    cues, per = [], []
    for n, sentence in enumerate(sentences):
        line = words(*[(w, n * step_s + i * 0.3, n * step_s + i * 0.3 + 0.25)
                       for i, w in enumerate(sentence.split())])
        cues.append(Cue(line[0]["start"], line[-1]["end"] + 0.5, sentence))
        per.append(line)
    picks = pick_heroes(cues, per)
    return [None if p is None else ws[p]["text"] for ws, p in zip(per, picks)]


class HeroTest(unittest.TestCase):
    def test_the_hero_is_the_longest_word_that_carries_meaning(self):
        self.assertEqual(heroes_of("ki jindagi ko jina bahut aasaan kaam hai."), ["jindagi"])

    def test_grammar_common_verbs_and_adverbs_are_never_the_hero(self):
        self.assertEqual(heroes_of("aur mujhe sach mein lagta hai",
                                   "this because I'm currently"), [None, None])

    def test_a_code_like_word_beats_a_longer_one(self):
        self.assertEqual(heroes_of("So I always change it to MP4"), ["MP4"])

    def test_the_same_hero_never_comes_back_within_ten_seconds(self):
        picks = heroes_of("prayog karein koshish karein", "dusri koshish karein", "bas itna",
                          step_s=4.0)
        self.assertEqual(picks[:2].count("koshish"), 1)

    def test_a_strong_later_word_is_never_blocked_by_a_weak_earlier_one(self):
        picks = heroes_of("har field mein", "Maturity aapke andar", step_s=1.5)
        self.assertEqual(picks, [None, "Maturity"])     # 1.5 s apart: room for one only

    def test_the_last_line_keeps_its_hero(self):
        picks = heroes_of("kyon dare jindagi mein kya hoga?", "kuchh na hoga to tajurba hoga.",
                          step_s=1.5)
        self.assertEqual(picks, [None, "tajurba"])

    def test_the_signature_sets_only_its_hero_in_the_serif_and_back(self):
        said = words(("koshish", 0.0, 0.6), ("karein", 0.65, 1.0))
        text = events(to_ass([Cue(0.0, 1.5, "koshish karein")], said,
                             STYLES["signature"]), 2)[0]
        self.assertIn("\\fnInstrument Serif\\i1\\fs86", text)          # 66 x 1.3
        self.assertIn("koshish{\\fnInstrument Sans SemiBold\\i0\\fs66}", text)
        self.assertIn("{\\fsp4.0} ", text)                             # room beside the italic
        self.assertEqual(plain(text), "koshish karein")


class PlateTest(unittest.TestCase):
    def test_one_bright_moment_puts_the_whole_clip_on_plates_and_never_switches(self):
        said = spaced("ek do teen") + words(*[(w, 5 + i * 0.5, 5.4 + i * 0.5)
                                              for i, w in enumerate("char paanch chhe".split())])
        cues = to_cues(said)
        backs = events(to_ass(cues, said, STYLES["signature"], light=[0.2, 0.95]), 0)
        self.assertTrue(all(",Plate," in b for b in backs), backs)
        backs = events(to_ass(cues, said, STYLES["signature"], light=[0.2, 0.3]), 0)
        self.assertTrue(all(",Halo," in b for b in backs), backs)

    def test_on_a_plate_unsaid_words_are_brighter(self):
        ass = to_ass(to_cues(SAID), SAID, STYLES["signature"], light=[0.95])
        self.assertIn("\\1a&H40&", events(ass, 2)[0])

    def test_with_no_light_measured_every_cue_gets_the_halo(self):
        ass = to_ass(to_cues(SAID), SAID, STYLES["ink"])
        self.assertNotIn(",Plate,,", ass)


class LineBreakTest(unittest.TestCase):
    def test_a_short_cue_stays_on_one_line(self):
        self.assertIsNone(_line_break(SAID, 22))

    def test_a_long_cue_splits_into_two_even_lines(self):
        said = spaced("aur vo experience kisi na kisi quantity")
        self.assertEqual(_line_break(said, 22), 3)     # "aur vo experience" / "kisi na kisi..."

    def test_a_cue_a_little_over_the_line_stays_on_one(self):
        self.assertIsNone(_line_break(spaced("mushkil kaam nahin hai."), 22))

    def test_no_word_is_left_alone_on_a_line(self):
        said = spaced("because most of the editing app")
        self.assertNotIn(_line_break(said, 20), (1, len(said) - 1))

    def test_a_line_never_splits_a_word_from_the_one_it_leans_on(self):
        self.assertNotEqual(_line_break(spaced("aur mujhe sach mein lagta hai"), 20), 3)
        said = spaced("aur main isilie ek line hamesha bolta hun")
        self.assertNotEqual(_line_break(said, 24), 4)  # never "... isilie ek / line ..."


@unittest.skipUnless(shutil.which("ffmpeg"), "needs ffmpeg")
class OverlayTest(unittest.TestCase):
    """The overlay .mov keeps a half-clear word half-clear (ffmpeg's own mode squared it)."""

    def test_a_dim_word_keeps_its_opacity_in_the_overlay(self):
        dim = Style(name="t", font="Instrument Sans SemiBold", size=200, line_chars=40,
                    upcoming="FFFFFF", upcoming_alpha=140, active="FFFFFF", spoken="FFFFFF",
                    glow=None, glow_alpha=255, glow_size=0, halo_alpha=255, bottom=0.4)
        said = words(("HH", 5.0, 5.5))          # not said yet in the first second: dim
        with TemporaryDirectory() as tmp:
            ass = Path(tmp) / "t.ass"
            ass.write_text(to_ass([Cue(0.0, 1.0, "HH")], said, dim, size=(540, 960)),
                           encoding="utf-8")
            mov = media.render_overlay(ass, Path(tmp) / "t.mov", (540, 960), 10.0, 1.0)
            alpha = subprocess.run(
                ["ffmpeg", "-v", "error", "-ss", "0.5", "-i", str(mov), "-frames:v", "1",
                 "-vf", "alphaextract", "-f", "rawvideo", "-pix_fmt", "gray", "-"],
                check=True, capture_output=True).stdout
        # The solid inside of the letters: opacity (255 - 140) / 255 = 45%, i.e. alpha ~115.
        self.assertAlmostEqual(max(alpha), 115, delta=6)


if __name__ == "__main__":
    unittest.main()
