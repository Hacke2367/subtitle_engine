"""ElevenLabs forced alignment: song audio + the known lyrics words -> start/end/score per word.

Exactly one POST to /v1/forced-alignment per call and no retry: every call is billed (spec §7).
Stdlib HTTP on purpose (plan §2.4): one endpoint doesn't justify requests + python-dotenv.
Only times come back, 1:1 with the input words, so the lyrics text can't change here (red line 2).
A word the API returns no timing for stays unplaced, never estimated (red line 1).
"""
from __future__ import annotations

import difflib
import http.client
import json
import math
import os
import urllib.error
import urllib.request
import uuid
from pathlib import Path

from .timing import RawWord, normalize

API_URL = "https://api.elevenlabs.io/v1/forced-alignment"
KEY_VAR = "ELEVENLABS_API_KEY"
ENV_PATH = Path(__file__).resolve().parents[2] / ".env"   # repo root, gitignored
SNIPPET_CHARS = 300          # of a response body quoted in an error, counted after redaction
USER_AGENT = "lyric-engine/0.1"
AUDIO_TYPES = {".wav": "audio/wav", ".mp3": "audio/mpeg", ".m4a": "audio/mp4",
               ".aac": "audio/aac", ".flac": "audio/flac", ".ogg": "audio/ogg",
               ".opus": "audio/opus", ".mp4": "video/mp4"}


class ElevenLabsError(RuntimeError):
    """The alignment call failed or returned something unusable. Never contains the API key."""


def load_api_key(env_path: Path | None = None) -> str | None:
    """ELEVENLABS_API_KEY from the environment first, else its KEY=value line in .env."""
    key = os.environ.get(KEY_VAR, "").strip()
    if key:
        return key
    try:
        text = Path(env_path or ENV_PATH).read_text(encoding="utf-8-sig", errors="replace")
    except OSError:
        return None
    for line in text.splitlines():
        name, sep, value = line.strip().partition("=")
        # Comment and blank lines never match; the last assignment wins, as in python-dotenv.
        if sep and name.removeprefix("export ").strip() == KEY_VAR:
            key = _unquote(value.strip())
    return key or None


def redact(text: str, key: str | None) -> str:
    """text with every occurrence of the key replaced (an empty key would match everywhere)."""
    return text.replace(key, "<redacted>") if key else text


def align(audio: Path, words: list[str], *, api_key: str | None = None,
          timeout_s: float = 300) -> tuple[list[RawWord], dict]:
    """Force-align words (the lyrics tokens, verbatim) to audio: one RawWord per word, in order.

    native = the full API response + {"mapping": "index" | "sequential", "unmatched": n}.
    """
    key = api_key or load_api_key()
    if not key:
        raise ElevenLabsError(f"no {KEY_VAR} in environment or .env")
    if not (key.isascii() and key.isprintable()):
        # http.client would reject it with the key's repr in the message, which redact() misses.
        raise ElevenLabsError(f"{KEY_VAR} has characters an HTTP header can't carry")
    audio = Path(audio)
    body, content_type = _multipart(audio.name, audio.read_bytes(), " ".join(words))
    request = urllib.request.Request(API_URL, data=body, method="POST", headers={
        "xi-api-key": key, "Content-Type": content_type, "Accept": "application/json",
        "User-Agent": USER_AGENT})
    payload = _send(request, key, timeout_s)

    try:
        response = json.loads(payload)
    except ValueError as exc:
        raise ElevenLabsError(f"bad JSON in response: {_snippet(payload, key)}") from exc
    entries = response.get("words") if isinstance(response, dict) else None
    if not isinstance(entries, list) or not all(isinstance(e, dict) for e in entries):
        raise ElevenLabsError(f"response has no 'words' list: {_snippet(payload, key)}")

    # Whitespace-only entries are spacing between words, not lyrics words.
    entries = [e for e in entries if isinstance(e.get("text"), str) and e["text"].strip()]
    if len(entries) == len(words):
        raw, unmatched, mapping = [_raw_word(e) for e in entries], 0, "index"
    else:
        raw, unmatched = _match_in_order(words, entries)
        mapping = "sequential"
    return raw, {**response, "mapping": mapping, "unmatched": unmatched}


def _send(request: urllib.request.Request, key: str, timeout_s: float) -> bytes:
    """The one HTTP call. Every failure becomes an ElevenLabsError with the key redacted."""
    try:
        with urllib.request.urlopen(request, timeout=timeout_s) as response:
            return response.read()
    except urllib.error.HTTPError as exc:            # before OSError: HTTPError is a URLError
        try:
            body = exc.read()
        except (OSError, http.client.HTTPException):
            body = b""
        raise ElevenLabsError(f"HTTP {exc.code}: {_snippet(body, key)}") from exc
    except (OSError, http.client.HTTPException) as exc:  # URLError, timeout, dropped connection
        reason = exc.reason if isinstance(exc, urllib.error.URLError) else exc
        detail = str(reason) or type(reason).__name__
        raise ElevenLabsError(f"network error: {redact(detail, key)}") from exc


def _multipart(filename: str, audio: bytes, text: str) -> tuple[bytes, str]:
    """multipart/form-data body with the `file` and `text` fields, and its Content-Type."""
    boundary = f"lyric-engine-{uuid.uuid4().hex}"
    safe_name = "".join("_" if c in '"\r\n' else c for c in filename)
    audio_type = AUDIO_TYPES.get(Path(filename).suffix.lower(), "application/octet-stream")
    body = b"".join([
        f'--{boundary}\r\nContent-Disposition: form-data; name="file"; filename="{safe_name}"\r\n'
        f"Content-Type: {audio_type}\r\n\r\n".encode(),
        audio,
        f'\r\n--{boundary}\r\nContent-Disposition: form-data; name="text"\r\n\r\n{text}\r\n'
        f"--{boundary}--\r\n".encode(),
    ])
    return body, f"multipart/form-data; boundary={boundary}"


def _match_in_order(words: list[str], entries: list[dict]) -> tuple[list[RawWord], int]:
    """Order-preserving match of lyrics words to API words on normalize(); the rest stay unplaced.

    difflib (longest common runs first), not a forward scan: when the API skips a word, a forward
    scan would take that word's next repeat (a chorus) and shift every word after it.
    """
    # A word that normalises to "" gets a unique key, so it never matches anything.
    lyrics = [normalize(w) or f"\0lyrics{i}" for i, w in enumerate(words)]
    api = [normalize(e["text"]) or f"\0api{k}" for k, e in enumerate(entries)]
    raw = [RawWord(None, None, None) for _ in words]
    matched = 0
    for block in difflib.SequenceMatcher(None, lyrics, api, autojunk=False).get_matching_blocks():
        for n in range(block.size):
            raw[block.a + n] = _raw_word(entries[block.b + n])
        matched += block.size
    return raw, len(words) - matched


def _raw_word(entry: dict) -> RawWord:
    """Times rounded to ms (plan §2.3); score = 1/(1+loss), higher is better (plan §2.5)."""
    start, end, loss = (_number(entry.get(k)) for k in ("start", "end", "loss"))
    # 4 significant digits keep words.json readable whatever the (undocumented) loss scale is.
    score = None if loss is None or loss < 0 else float(f"{1 / (1 + loss):.4g}")
    return RawWord(_ms(start), _ms(end), score)


def _number(value: object) -> float | None:
    """A finite JSON number as float, else None (a missing value is never replaced by a guess)."""
    if isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value):
        return float(value)
    return None


def _ms(t: float | None) -> float | None:
    return None if t is None else round(t, 3)


def _snippet(body: bytes, key: str) -> str:
    # Redact before cutting, so a key straddling the cut can't leak half of itself.
    return redact(body.decode("utf-8", errors="replace"), key)[:SNIPPET_CHARS]


def _unquote(value: str) -> str:
    if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
        return value[1:-1]
    return value.split(" #", 1)[0].strip()   # unquoted: drop an inline comment
