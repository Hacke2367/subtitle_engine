"""Devanagari -> Roman: the inherent-a rules, nasals, and Latin left alone."""
import unittest

from voice_subs.roman import has_devanagari, romanize


class RomanTest(unittest.TestCase):
    def test_words_read_as_a_hinglish_speaker_types_them(self):
        cases = {
            "घर": "ghar",                  # the inherent a is silent at the end of a word
            "करता": "karta",               # and mid-word before a vowel of its own
            "करें": "karein",              # but never in the first syllable (not "krein")
            "बोलता": "bolta",
            "जिंदगी": "jindagi",           # kept after a nasal (not "jindgi")
            "संपर्क": "sampark",           # a nasal before p/b/m is "m"
            "प्रयास": "prayaas",           # kept after a cluster (not "pryaas")
            "मुश्किल": "mushkil",
            "समझ": "samajh",
            "क्या": "kya",
            "होगा": "hoga",                # final aa is written "a"
            "में": "mein",
            "नहीं": "nahin",
            "ज्ञान": "gyaan",
            "अच्छा": "achchha",
            "है।": "hai.",                 # a danda is a full stop
            "१२": "12",
        }
        for word, expected in cases.items():
            with self.subTest(word=word):
                self.assertEqual(romanize(word), expected)

    def test_latin_and_punctuation_pass_through_untouched(self):
        self.assertEqual(romanize("Maturity, field 2024!"), "Maturity, field 2024!")

    def test_a_mixed_line_keeps_the_english_words_as_written(self):
        self.assertEqual(romanize("वो experience किसी ना किसी field में"),
                         "vo experience kisi na kisi field mein")

    def test_has_devanagari(self):
        self.assertTrue(has_devanagari("वो experience"))
        self.assertFalse(has_devanagari("experience"))


if __name__ == "__main__":
    unittest.main()
