"""The command's own rules: no API call when a transcript fits, and nothing overwritten quietly.

Offline: ffmpeg and the transcription engine are stubbed, so no audio and no API key are needed.
"""
import contextlib
import io
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import mock

from voice_subs import cli, media, transcript
from tests.test_transcript import RESPONSE


OVERLAYS = []        # (dest, size) of every overlay the stub "rendered"


def run(source: Path, work: Path, argv_extra=()):
    argv = ["subs", str(source), "--work", str(work), *argv_extra]
    with mock.patch.object(media, "extract_audio", lambda src, dest: _stub_audio(dest)), \
         mock.patch.object(media, "duration", lambda path: 2.5), \
         mock.patch.object(media, "fingerprint", lambda path: "abc123"), \
         mock.patch.object(media, "video_format", lambda path: ((720, 1280), 25.0)), \
         mock.patch.object(media, "render_overlay", _stub_overlay), \
         mock.patch("voice_subs.scribe.transcribe") as transcribe, \
         contextlib.redirect_stdout(io.StringIO()), \
         contextlib.redirect_stderr(io.StringIO()):
        transcribe.return_value = RESPONSE
        code = cli.main(argv)
    return code, transcribe.call_count


def _stub_overlay(ass: Path, dest: Path, size, fps, seconds) -> Path:
    OVERLAYS.append((dest, size))
    dest.write_bytes(b"mov")
    return dest


def _stub_audio(dest: Path) -> Path:
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(b"not really mp3")
    return dest


class CliTest(unittest.TestCase):
    def setUp(self):
        self._tmp = TemporaryDirectory()
        self.tmp = Path(self._tmp.name)
        self.source = self.tmp / "clip_01.mp4"
        self.source.write_bytes(b"not really mp4")
        self.work = self.tmp / "work"
        self.addCleanup(self._tmp.cleanup)

    def test_one_call_makes_the_srt_and_the_transcript(self):
        code, calls = run(self.source, self.work)
        self.assertEqual((code, calls), (0, 1))
        self.assertTrue((self.work / transcript.NAME).is_file())
        srt = (self.work / "clip_01.srt").read_text(encoding="utf-8")
        self.assertIn("vo experience hai", srt)
        self.assertIn("-->", srt)

    def test_running_again_reuses_the_transcript_and_calls_no_api(self):
        run(self.source, self.work)
        code, calls = run(self.source, self.work, ["--overwrite"])
        self.assertEqual((code, calls), (0, 0))

    def test_an_existing_srt_is_never_replaced_without_being_asked(self):
        run(self.source, self.work)
        (self.work / "clip_01.srt").write_text("mine\n", encoding="utf-8")
        code, calls = run(self.source, self.work)
        self.assertEqual((code, calls), (1, 0))
        self.assertEqual((self.work / "clip_01.srt").read_text(encoding="utf-8"), "mine\n")

    def test_a_transcript_from_other_audio_is_refused_not_overwritten(self):
        run(self.source, self.work)
        path = self.work / transcript.NAME
        data = transcript.load(path)
        data["source"]["fingerprint"] = "different"
        transcript.save(data, path)
        code, calls = run(self.source, self.work, ["--overwrite"])
        self.assertEqual((code, calls), (1, 0))
        self.assertEqual(transcript.load(path)["source"]["fingerprint"], "different")

    def test_fresh_replaces_it_after_being_asked(self):
        run(self.source, self.work)
        code, calls = run(self.source, self.work, ["--overwrite", "--fresh"])
        self.assertEqual((code, calls), (0, 1))

    def test_every_run_writes_the_srt_the_ass_and_an_overlay_strip(self):
        OVERLAYS.clear()
        source = self.tmp / "03_x_00.04.33.mp4"          # dots in the name, as the clips have
        source.write_bytes(b"x")
        code, _ = run(source, self.work)
        self.assertEqual(code, 0)
        self.assertEqual(sorted(p.name for p in self.work.glob("03_x*")),
                         ["03_x_00.04.33.ass", "03_x_00.04.33.mov", "03_x_00.04.33.srt"])
        # The strip is the video's width and only as tall as two lines need (420 at 1080).
        self.assertEqual(OVERLAYS, [(self.work / "03_x_00.04.33.mov", (720, 280))])

    def test_a_file_that_is_not_video_or_audio_is_refused(self):
        other = self.tmp / "notes.txt"
        other.write_text("hello", encoding="utf-8")
        self.assertEqual(run(other, self.work)[0], 1)

    def test_slug_keeps_the_source_name_and_drops_odd_characters(self):
        self.assertEqual(cli._slug("03_dYSQ1NF1hvw_00.04.33"), "03_dYSQ1NF1hvw_00.04.33")
        self.assertEqual(cli._slug("my clip (final)"), "my-clip--final")

    def test_two_clips_with_the_same_name_get_their_own_work_folders(self):
        first, second = self.tmp / "a" / "clip_01.mp4", self.tmp / "b" / "clip_01.mp4"
        for path in (first, second):
            path.parent.mkdir()
            path.write_bytes(b"x")
        self.assertNotEqual(cli._work_name(first), cli._work_name(second))
        self.assertEqual(cli._work_name(first), cli._work_name(first))   # same file, same folder
        self.assertTrue(cli._work_name(first).startswith("clip_01-"))


if __name__ == "__main__":
    unittest.main()
