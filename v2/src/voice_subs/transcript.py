"""The transcript: V2's one contract between stages, and the file the user edits.

Everything after transcription reads this file and nothing else, so a fix by hand costs no API
call (red line 3). It owns its own format and validates it.

    {"version": 1, "made": "<iso>",
     "source": {"name": "clip_01.mp4", "audio": "audio.mp3", "duration": 33.0,
                "fingerprint": "<hash of the audio>"},
     "engine": {"name": "elevenlabs/scribe_v1", "language": "hin", "confidence": 0.99,
                "script": "roman"},
     "words": [{"text": "prayaas", "start": 0.22, "end": 0.6, "devanagari": "प्रयास"}],
     "flags": ["..."]}

`text` is what goes on screen. `devanagari` is kept only as the engine's original, for checking
a romanized word by hand; nothing downstream reads it. A word the engine gave no time for keeps
`start`/`end` as null and is flagged, never estimated (red line 2).
"""
from __future__ import annotations

import datetime as _dt
import json
from pathlib import Path

VERSION = 1
NAME = "transcript.json"


class TranscriptError(RuntimeError):
    """The transcript file is missing, unreadable, or not valid."""


def from_scribe(response: dict, *, source: str, audio: str, duration: float,
                fingerprint: str, to_roman: bool = True) -> dict:
    """Build a transcript from the engine's response. The words are kept verbatim."""
    from .roman import has_devanagari, romanize

    words, flags, events = [], [], 0
    for entry in response.get("words", []):
        if not isinstance(entry, dict):
            continue
        kind = entry.get("type", "word")
        text = entry.get("text")
        if not isinstance(text, str) or not text.strip():
            continue                      # spacing between words carries no text of its own
        if kind == "audio_event":
            events += 1                   # [laughs], [applause]: not spoken words
            continue
        if kind != "word":
            continue
        start, end = _time(entry.get("start")), _time(entry.get("end"))
        word = {"text": text, "start": start, "end": end}
        if to_roman and has_devanagari(text):
            word["text"], word["devanagari"] = romanize(text), text
        if start is None or end is None:
            flags.append(f"word {len(words) + 1} {word['text']!r} came back with no timing; "
                         "it is in the transcript but will be left out of the subtitles")
        words.append(word)
    if events:
        flags.append(f"{events} sound event(s) (laughter, applause) left out: not spoken words")
    if not words:
        flags.append("the engine found no words in this audio")

    language = response.get("language_code")
    confidence = _time(response.get("language_probability"))
    return {
        "version": VERSION,
        "made": _dt.datetime.now().isoformat(timespec="seconds"),
        "source": {"name": source, "audio": audio, "duration": round(float(duration), 3),
                   "fingerprint": fingerprint},
        "engine": {"name": "elevenlabs/scribe_v1", "language": language,
                   "confidence": confidence,
                   "script": "roman" if to_roman else "as transcribed"},
        "words": words,
        "flags": flags,
    }


def save(data: dict, path: Path) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    return path


def load(path: Path) -> dict:
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
    except OSError as exc:
        raise TranscriptError(f"can't read {path}: {exc.strerror}") from exc
    except ValueError as exc:
        raise TranscriptError(f"{path} is not valid JSON ({exc}); fix or delete it") from exc
    problems = validate(data)
    if problems:
        raise TranscriptError(f"{path} is not a valid transcript:\n  - "
                              + "\n  - ".join(problems))
    return data


def validate(data: object) -> list[str]:
    """Everything wrong with a transcript, as plain sentences. Empty list = valid."""
    problems: list[str] = []
    if not isinstance(data, dict):
        return ["the file is not a JSON object"]
    if data.get("version") != VERSION:
        problems.append(f"version is {data.get('version')!r}, expected {VERSION}")
    words = data.get("words")
    if not isinstance(words, list):
        return problems + ["'words' is missing or not a list"]
    duration = data.get("source", {}).get("duration") if isinstance(data.get("source"), dict) \
        else None
    last_end = 0.0
    for i, word in enumerate(words, start=1):
        if not isinstance(word, dict) or not isinstance(word.get("text"), str) \
                or not word["text"].strip():
            problems.append(f"word {i} has no text")
            continue
        start, end = word.get("start"), word.get("end")
        if start is None or end is None:
            continue                            # an untimed word is allowed, and is flagged
        if not isinstance(start, (int, float)) or not isinstance(end, (int, float)):
            problems.append(f"word {i} {word['text']!r} has a non-numeric time")
            continue
        if end < start:
            problems.append(f"word {i} {word['text']!r} ends before it starts")
        if start + 1e-6 < last_end:
            problems.append(f"word {i} {word['text']!r} starts before the word before it ends")
        if isinstance(duration, (int, float)) and start > duration + 1:
            problems.append(f"word {i} {word['text']!r} starts after the audio ends")
        last_end = max(last_end, float(end))
    return problems


def matches_audio(data: dict, fingerprint: str) -> bool:
    """Was this transcript made from this exact audio? (Red line 3: never silently redo it.)"""
    source = data.get("source") if isinstance(data.get("source"), dict) else {}
    return bool(source.get("fingerprint")) and source["fingerprint"] == fingerprint


def timed_words(data: dict) -> list[dict]:
    """The words that have times, in order: the only ones the subtitles can carry."""
    return [w for w in data["words"] if w.get("start") is not None and w.get("end") is not None]


def _time(value: object) -> float | None:
    """A number from the engine, rounded; anything else (including null) is None."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    return round(float(value), 3)
