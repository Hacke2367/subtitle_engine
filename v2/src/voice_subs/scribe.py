"""ElevenLabs Scribe speech-to-text: an audio file -> words with start and end times.

One POST to /v1/speech-to-text per call and no retry: every call is billed. Stdlib HTTP on
purpose - one endpoint does not justify a dependency. The key is read from the environment or
`.env` and never logged (red line 4); every error message runs through `redact`.

Measured on a Hinglish clip (2026-10-03): the engine returns Hindi words in Devanagari and
English words in Latin, with word-level times. `roman.py` handles the script; the words
themselves are kept exactly as the engine wrote them (red line 1).
"""
from __future__ import annotations

import http.client
import json
import os
import urllib.error
import urllib.request
import uuid
from pathlib import Path

API_URL = "https://api.elevenlabs.io/v1/speech-to-text"
MODEL = "scribe_v1"
KEY_VAR = "ELEVENLABS_API_KEY"
# v2/.env first (V2 is its own project), then the repository root's, which already has the key.
# In a git worktree the root checkout has no .env (it is gitignored, so it is not copied there):
# set ELEVENLABS_API_KEY in the environment, or put a v2/.env next to this folder.
ENV_PATHS = (Path(__file__).resolve().parents[2] / ".env",
             Path(__file__).resolve().parents[3] / ".env")
SNIPPET_CHARS = 300
USER_AGENT = "voice-subs/0.1"
AUDIO_TYPES = {".mp3": "audio/mpeg", ".wav": "audio/wav", ".m4a": "audio/mp4",
               ".aac": "audio/aac", ".flac": "audio/flac", ".ogg": "audio/ogg",
               ".opus": "audio/opus", ".mp4": "video/mp4"}


class ScribeError(RuntimeError):
    """The transcription call failed or returned something unusable. Never holds the API key."""


def load_api_key(env_paths: tuple[Path, ...] | None = None) -> str | None:
    """ELEVENLABS_API_KEY from the environment first, else its KEY=value line in a .env."""
    key = os.environ.get(KEY_VAR, "").strip()
    if key:
        return key
    for path in env_paths or ENV_PATHS:
        try:
            text = Path(path).read_text(encoding="utf-8-sig", errors="replace")
        except OSError:
            continue
        for line in text.splitlines():
            name, sep, value = line.strip().partition("=")
            if sep and name.removeprefix("export ").strip() == KEY_VAR:
                key = value.strip().strip('"').strip("'")
        if key:
            return key
    return None


def redact(text: str, key: str | None) -> str:
    return text.replace(key, "<redacted>") if key else text


def transcribe(audio: Path, *, language: str | None = None, api_key: str | None = None,
               timeout_s: float = 900) -> dict:
    """The engine's own response for audio: {"language_code", "text", "words": [...]}.

    language is an ISO code to force (e.g. "hin"); None lets the engine detect it.
    """
    key = api_key or load_api_key()
    if not key:
        raise ScribeError(f"no {KEY_VAR} in the environment or a .env file")
    if not (key.isascii() and key.isprintable()):
        # http.client would reject it with the key's repr in the message, which redact() misses.
        raise ScribeError(f"{KEY_VAR} has characters an HTTP header can't carry")
    audio = Path(audio)
    fields = {"model_id": MODEL, "timestamps_granularity": "word"}
    if language:
        fields["language_code"] = language
    body, content_type = _multipart(fields, audio.name, audio.read_bytes())
    request = urllib.request.Request(API_URL, data=body, method="POST", headers={
        "xi-api-key": key, "Content-Type": content_type, "Accept": "application/json",
        "User-Agent": USER_AGENT})
    payload = _send(request, key, timeout_s)

    try:
        response = json.loads(payload)
    except ValueError as exc:
        raise ScribeError(f"bad JSON in response: {_snippet(payload, key)}") from exc
    if not isinstance(response, dict) or not isinstance(response.get("words"), list):
        raise ScribeError(f"response has no 'words' list: {_snippet(payload, key)}")
    return response


def _send(request: urllib.request.Request, key: str, timeout_s: float) -> bytes:
    """The one HTTP call. Every failure becomes a ScribeError with the key redacted."""
    try:
        with urllib.request.urlopen(request, timeout=timeout_s) as response:
            return response.read()
    except urllib.error.HTTPError as exc:            # before OSError: HTTPError is a URLError
        try:
            detail = exc.read()
        except (OSError, http.client.HTTPException):
            detail = b""
        raise ScribeError(f"HTTP {exc.code}: {_snippet(detail, key)}") from exc
    except (OSError, http.client.HTTPException) as exc:
        reason = exc.reason if isinstance(exc, urllib.error.URLError) else exc
        raise ScribeError(f"network error: {redact(str(reason) or type(reason).__name__, key)}"
                          ) from exc


def _multipart(fields: dict[str, str], filename: str, audio: bytes) -> tuple[bytes, str]:
    """multipart/form-data body with the text fields and the audio file, and its Content-Type."""
    boundary = f"voice-subs-{uuid.uuid4().hex}"
    safe_name = "".join("_" if c in '"\r\n' else c for c in filename)
    audio_type = AUDIO_TYPES.get(Path(filename).suffix.lower(), "application/octet-stream")
    parts = [f'--{boundary}\r\nContent-Disposition: form-data; name="{name}"\r\n\r\n'
             f"{value}\r\n".encode() for name, value in fields.items()]
    parts.append(f'--{boundary}\r\nContent-Disposition: form-data; name="file"; '
                 f'filename="{safe_name}"\r\nContent-Type: {audio_type}\r\n\r\n'.encode())
    parts.append(audio)
    parts.append(f"\r\n--{boundary}--\r\n".encode())
    return b"".join(parts), f"multipart/form-data; boundary={boundary}"


def _snippet(body: bytes, key: str) -> str:
    text = body.decode("utf-8", "replace").strip().replace("\n", " ")
    return redact(text[:SNIPPET_CHARS], key) or "<empty response>"
