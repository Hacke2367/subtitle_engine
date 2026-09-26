"""eleven.py: word mapping, key handling and the request itself. urlopen is always mocked."""
from __future__ import annotations

import io
import json
import os
import tempfile
import unittest
import urllib.error
from pathlib import Path
from unittest.mock import MagicMock, patch

from lyric_engine import eleven
from lyric_engine.timing import RawWord

KEY = "sk_test_SECRET_0123456789"
WORDS = ["Mere", "saamne", "waali", "khidki"]
UNPLACED = RawWord(None, None, None)


def _entry(text: str, start: float, end: float, loss: float = 0.0) -> dict:
    return {"text": text, "start": start, "end": end, "loss": loss}


def _urlopen(payload: dict | bytes) -> MagicMock:
    """A urlopen mock whose response body is payload (a dict is sent as JSON)."""
    body = payload if isinstance(payload, bytes) else json.dumps(payload).encode()
    urlopen = MagicMock()
    urlopen.return_value.__enter__.return_value.read.return_value = body
    return urlopen


class AlignTest(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.audio = Path(tmp.name) / "clip.wav"
        self.audio.write_bytes(b"RIFF\x00\x01fake-audio\xff\xfe\r\n--")

    def _align(self, payload: dict | bytes, words: list[str] = WORDS):
        urlopen = _urlopen(payload)
        with patch("urllib.request.urlopen", urlopen):
            raw, native = eleven.align(self.audio, words, api_key=KEY)
        self.assertEqual(urlopen.call_count, 1)          # one paid call, never a retry
        return raw, native, urlopen

    def _error(self, **urlopen_kwargs) -> str:
        with patch("urllib.request.urlopen", **urlopen_kwargs) as urlopen:
            with self.assertRaises(eleven.ElevenLabsError) as ctx:
                eleven.align(self.audio, WORDS, api_key=KEY)
        self.assertEqual(urlopen.call_count, 1)
        message = str(ctx.exception)
        self.assertNotIn("SECRET", message)
        return message

    def test_equal_count_maps_by_index_with_rounded_times(self):
        payload = {"words": [_entry("Mere", 0.12345, 0.5), _entry("saamne", 0.6, 1.0004),
                             _entry("waali", 1.1, 1.5), _entry("khidki", 1.6, 2.0)],
                   "characters": [{"text": "M", "start": 0.1, "end": 0.2}], "loss": 0.4}
        raw, native, _ = self._align(payload)
        self.assertEqual([(r.start, r.end) for r in raw],
                         [(0.123, 0.5), (0.6, 1.0), (1.1, 1.5), (1.6, 2.0)])
        self.assertEqual((native["mapping"], native["unmatched"]), ("index", 0))
        self.assertEqual(native["loss"], 0.4)                      # the full response is kept
        self.assertEqual(native["characters"], payload["characters"])

    def test_whitespace_entries_are_dropped(self):
        payload = {"words": [_entry("Mere", 0.1, 0.5), _entry(" ", 0.5, 0.6),
                             _entry("saamne", 0.6, 1.0), _entry("\n", 1.0, 1.1),
                             _entry("waali", 1.1, 1.5), _entry("", 1.5, 1.5),
                             _entry("khidki", 1.6, 2.0)]}
        raw, native, _ = self._align(payload)
        self.assertEqual(native["mapping"], "index")
        self.assertEqual([r.start for r in raw], [0.1, 0.6, 1.1, 1.6])
        self.assertEqual(len(native["words"]), 7)

    def test_count_mismatch_matches_in_order_and_never_invents(self):
        # The API skipped "waali", split "dil-e-nadaan" and returned "—" as a word.
        words = ["Mere", "saamne", "waali", "Khidki,", "dil-e-nadaan", "—", "mein"]
        payload = {"words": [_entry("mere", 0.1, 0.5), _entry("saamne", 0.6, 1.0),
                             _entry("khidki", 1.6, 2.0), _entry("dil", 2.1, 2.2),
                             _entry("e", 2.2, 2.3), _entry("nadaan", 2.3, 2.8),
                             _entry("—", 2.8, 2.9), _entry("mein", 3.0, 3.4, loss=1.0)]}
        raw, native, _ = self._align(payload, words)
        self.assertEqual((native["mapping"], native["unmatched"]), ("sequential", 3))
        self.assertEqual(raw, [RawWord(0.1, 0.5, 1.0), RawWord(0.6, 1.0, 1.0), UNPLACED,
                               RawWord(1.6, 2.0, 1.0), UNPLACED, UNPLACED,
                               RawWord(3.0, 3.4, 0.5)])

    def test_skipped_word_does_not_take_a_later_repeat(self):
        # A forward scan would give the first "tum" the second one's time.
        payload = {"words": [_entry("ho", 1.0, 1.4), _entry("tum", 2.0, 2.5)]}
        raw, native, _ = self._align(payload, ["tum", "ho", "tum"])
        self.assertEqual(raw, [UNPLACED, RawWord(1.0, 1.4, 1.0), RawWord(2.0, 2.5, 1.0)])
        self.assertEqual(native["unmatched"], 1)

    def test_score_is_one_over_one_plus_loss(self):
        payload = {"words": [_entry("Mere", 0.1, 0.5, loss=0.0), _entry("saamne", 0.6, 1.0, 1.0),
                             _entry("waali", 1.1, 1.5, loss=2.0),
                             {"text": "khidki", "start": 1.6, "end": 2.0}]}
        raw, _, _ = self._align(payload)
        self.assertEqual([r.score for r in raw], [1.0, 0.5, 0.3333, None])

    def test_missing_times_stay_missing(self):
        payload = {"words": [_entry("Mere", 0.1, 0.5), {"text": "saamne", "loss": 0.0},
                             _entry("waali", None, 1.5), _entry("khidki", 1.6, float("nan"))]}
        raw, _, _ = self._align(payload)
        self.assertEqual([(r.start, r.end) for r in raw],
                         [(0.1, 0.5), (None, None), (None, 1.5), (1.6, None)])

    def test_request_is_one_multipart_post(self):
        payload = {"words": [_entry(w, i, i + 0.5) for i, w in enumerate(WORDS)]}
        _, _, urlopen = self._align(payload)
        request = urlopen.call_args.args[0]
        self.assertEqual(urlopen.call_args.kwargs["timeout"], 300)
        self.assertEqual((request.full_url, request.get_method()), (eleven.API_URL, "POST"))
        self.assertEqual(request.get_header("Xi-api-key"), KEY)
        content_type = request.get_header("Content-type")
        self.assertTrue(content_type.startswith("multipart/form-data; boundary="))
        boundary = content_type.split("boundary=", 1)[1].encode()
        body = request.data
        self.assertTrue(body.startswith(b"--" + boundary + b"\r\n"))
        self.assertIn(b'name="file"; filename="clip.wav"\r\nContent-Type: audio/wav\r\n\r\n'
                      + self.audio.read_bytes() + b"\r\n--" + boundary + b"\r\n", body)
        self.assertIn(b'name="text"\r\n\r\nMere saamne waali khidki\r\n', body)
        self.assertTrue(body.endswith(b"--" + boundary + b"--\r\n"))

    def test_missing_key_fails_before_any_request(self):
        with tempfile.TemporaryDirectory() as tmp, patch.dict(os.environ), \
                patch.object(eleven, "ENV_PATH", Path(tmp) / ".env"), \
                patch("urllib.request.urlopen") as urlopen:
            os.environ.pop(eleven.KEY_VAR, None)
            with self.assertRaises(eleven.ElevenLabsError) as ctx:
                eleven.align(self.audio, WORDS)
        self.assertEqual(str(ctx.exception), "no ELEVENLABS_API_KEY in environment or .env")
        urlopen.assert_not_called()

    def test_unsendable_key_fails_without_echoing_it(self):
        with patch("urllib.request.urlopen") as urlopen:
            with self.assertRaises(eleven.ElevenLabsError) as ctx:
                eleven.align(self.audio, WORDS, api_key="sk_SECRET\nline2")
        self.assertNotIn("SECRET", str(ctx.exception))
        urlopen.assert_not_called()

    def test_http_error_body_is_redacted(self):
        body = json.dumps({"detail": {"status": "invalid_api_key",
                                      "message": f"API key {KEY} is invalid"}}).encode()
        error = urllib.error.HTTPError(eleven.API_URL, 401, "Unauthorized", {}, io.BytesIO(body))
        message = self._error(side_effect=error)
        self.assertTrue(message.startswith("HTTP 401: "))
        self.assertIn("API key <redacted> is invalid", message)

    def test_http_error_body_is_cut_after_redaction(self):
        body = ("x" * 295 + KEY + "y" * 500).encode()    # the key straddles the 300-char cut
        error = urllib.error.HTTPError(eleven.API_URL, 500, "Server Error", {}, io.BytesIO(body))
        message = self._error(side_effect=error)
        self.assertEqual(message, "HTTP 500: " + "x" * 295 + "<reda")

    def test_network_errors(self):
        for error in (urllib.error.URLError("getaddrinfo failed"), TimeoutError("timed out")):
            with self.subTest(error=type(error).__name__):
                message = self._error(side_effect=error)
                self.assertTrue(message.startswith("network error: "), message)

    def test_unusable_response(self):
        for body in (b"<html>502 Bad Gateway</html>", b'{"detail": "no words here"}', b"[]"):
            with self.subTest(body=body):
                self._error(new=_urlopen(body))


class ApiKeyTest(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.env = Path(tmp.name) / ".env"
        environ = patch.dict(os.environ)
        environ.start()
        self.addCleanup(environ.stop)
        os.environ.pop(eleven.KEY_VAR, None)

    def test_environment_comes_first(self):
        self.env.write_text("ELEVENLABS_API_KEY=from-file\n", encoding="utf-8")
        os.environ[eleven.KEY_VAR] = "from-env"
        self.assertEqual(eleven.load_api_key(self.env), "from-env")

    def test_dotenv_lines(self):
        cases = {
            "# ELEVENLABS_API_KEY=commented\n\nOTHER=1\nELEVENLABS_API_KEY=plain\n": "plain",
            'export ELEVENLABS_API_KEY="double"\n': "double",
            "ELEVENLABS_API_KEY = 'single'\r\n": "single",
            "ELEVENLABS_API_KEY=abc # note\n": "abc",
            "\N{BYTE ORDER MARK}ELEVENLABS_API_KEY=after-bom\n": "after-bom",
            "OTHER=1\n# ELEVENLABS_API_KEY=commented\n": None,
            "ELEVENLABS_API_KEY=\n": None,
        }
        for text, expected in cases.items():
            with self.subTest(text=text):
                self.env.write_text(text, encoding="utf-8")
                self.assertEqual(eleven.load_api_key(self.env), expected)

    def test_no_env_file(self):
        self.assertIsNone(eleven.load_api_key(self.env))

    def test_redact(self):
        self.assertEqual(eleven.redact(f"a {KEY} b {KEY}", KEY), "a <redacted> b <redacted>")
        self.assertEqual(eleven.redact("text", None), "text")
        self.assertEqual(eleven.redact("text", ""), "text")


if __name__ == "__main__":
    unittest.main()
