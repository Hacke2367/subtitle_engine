"""The transcript contract: what is kept from the engine, what is flagged, what is refused."""
import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from voice_subs import transcript

RESPONSE = {
    "language_code": "hin",
    "language_probability": 0.99,
    "text": "वो experience hai",
    "words": [
        {"text": "वो", "start": 0.1, "end": 0.3, "type": "word"},
        {"text": " ", "start": 0.3, "end": 0.32, "type": "spacing"},
        {"text": "experience", "start": 0.32, "end": 0.9, "type": "word"},
        {"text": "hai", "start": 0.95, "end": 1.2, "type": "word"},
        {"text": "[तालियां]", "start": 1.3, "end": 2.0, "type": "audio_event"},
    ],
}


def build(response=None, **kwargs):
    options = {"source": "clip.mp4", "audio": "audio.mp3", "duration": 2.5,
               "fingerprint": "abc123", **kwargs}
    return transcript.from_scribe(response or RESPONSE, **options)


class FromScribeTest(unittest.TestCase):
    def test_only_spoken_words_are_kept(self):
        data = build()
        self.assertEqual([w["text"] for w in data["words"]], ["vo", "experience", "hai"])

    def test_a_sound_event_is_reported_not_dropped_in_silence(self):
        self.assertTrue(any("sound event" in f for f in build()["flags"]))

    def test_the_engine_s_own_devanagari_is_kept_beside_the_roman(self):
        self.assertEqual(build()["words"][0]["devanagari"], "वो")
        self.assertNotIn("devanagari", build()["words"][1])      # an English word is untouched

    def test_devanagari_can_be_kept_as_the_text(self):
        data = build(to_roman=False)
        self.assertEqual(data["words"][0]["text"], "वो")
        self.assertEqual(data["engine"]["script"], "as transcribed")

    def test_a_word_with_no_timing_is_flagged_and_never_given_one(self):
        response = {**RESPONSE, "words": [{"text": "वो", "type": "word"}]}
        data = build(response)
        self.assertIsNone(data["words"][0]["start"])
        self.assertTrue(any("no timing" in f for f in data["flags"]))
        self.assertEqual(transcript.timed_words(data), [])

    def test_a_new_transcript_is_valid(self):
        self.assertEqual(transcript.validate(build()), [])


class ValidateTest(unittest.TestCase):
    def test_a_wrong_version_is_reported(self):
        data = {**build(), "version": 99}
        self.assertTrue(any("version" in p for p in transcript.validate(data)))

    def test_words_out_of_order_are_reported(self):
        data = build()
        data["words"][2]["start"] = 0.2
        self.assertTrue(any("starts before" in p for p in transcript.validate(data)))

    def test_an_empty_word_is_reported(self):
        data = build()
        data["words"][0]["text"] = "  "
        self.assertTrue(any("no text" in p for p in transcript.validate(data)))

    def test_anything_that_is_not_a_transcript_is_reported(self):
        self.assertTrue(transcript.validate([1, 2, 3]))


class FileTest(unittest.TestCase):
    def test_saved_and_loaded_unchanged(self):
        data = build()
        with TemporaryDirectory() as tmp:
            path = transcript.save(data, Path(tmp) / transcript.NAME)
            self.assertEqual(transcript.load(path), data)

    def test_a_broken_file_is_refused_with_its_path(self):
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / transcript.NAME
            path.write_text("{not json", encoding="utf-8")
            with self.assertRaises(transcript.TranscriptError):
                transcript.load(path)

    def test_a_transcript_knows_which_audio_it_came_from(self):
        data = build()
        self.assertTrue(transcript.matches_audio(data, "abc123"))
        self.assertFalse(transcript.matches_audio(data, "other"))


if __name__ == "__main__":
    unittest.main()
