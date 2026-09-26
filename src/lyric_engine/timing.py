"""The words.json contract: load, save, validate. The only thing align.py and render.py share.

Also owns the lyrics reader and the flag rules, so every aligner variant is judged the same way
(spec docs/specs/02_word_alignment.md, plan docs/specs/02_word_alignment_impl.md).
"""
from __future__ import annotations

import hashlib
import json
import math
import re
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

# --- Contract (shared by align, eleven, local_aligner, review; do not change signatures) -------
WORDS_VERSION = 1
REASONS = ("not_placed", "low_confidence", "bad_duration", "out_of_order", "out_of_bounds")
MAX_WORD_S = 6.0        # a single sung word longer than this is implausible
OVERLAP_TOL_S = 0.10    # allowed overlap with the previous placed word
BOUNDS_TOL_S = 0.05     # allowed overshoot past the audio end
MOSTLY_FLAGGED = 0.30   # above this share → "lyrics probably don't match audio"


class LyricsError(ValueError):
    """lyrics.txt cannot be used as-is (the owner must fix it; we never alter it)."""


@dataclass
class Lyrics:
    path: Path
    sha256: str                     # of the file's bytes
    lines: list[str]                # verbatim (emphasis markers kept), blank lines kept as ""
    words: list[tuple[str, int]]    # (token from line.split() minus its *marker*, line index)
    emphasis: frozenset[int] = field(default_factory=frozenset)   # indexes of *marked* words


@dataclass
class RawWord:
    """Aligner output for one lyrics word, 1:1 with Lyrics.words. None = not placed."""
    start: float | None
    end: float | None
    score: float | None


@dataclass
class Word:
    index: int
    text: str
    line: int
    start: float | None
    end: float | None
    score: float | None
    flagged: bool = False
    reasons: list[str] = field(default_factory=list)


_NOT_ALIGNABLE = re.compile(r"[^a-z0-9']")


def normalize(word: str) -> str:
    """Aligner-internal form of a word: lowercase, only [a-z0-9']. Never shown on screen."""
    return _NOT_ALIGNABLE.sub("", word.lower())


def sha256_file(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def flag_summary(words: list[Word]) -> dict:
    total = len(words)
    flagged = sum(1 for w in words if w.flagged)
    share = flagged / total if total else 0.0
    by_reason = {r: sum(1 for w in words if r in w.reasons) for r in REASONS}
    return {"total": total, "flagged": flagged, "share": share, "by_reason": by_reason,
            "mostly_flagged": share > MOSTLY_FLAGGED}


# --- Lyrics, flags, words.json IO and validation (plan §4) ------------------------------------
_ANNOTATION_CHARS = "()[]{}"
# Emphasis (H-009): a whole token *word*; the inside neither starts nor ends with "*". Any other
# token starting or ending with "*" is malformed; an asterisk inside a word (f**k) is lyric text.
_MARKED = re.compile(r"\*([^\s*](?:\S*[^\s*])?)\*")
_MARKED_IN_LINE = re.compile(r"(?<!\S)\*([^\s*](?:\S*[^\s*])?)\*(?!\S)")
MARKER_HINT = ("Wrap one whole word, punctuation inside: *dil,*. "
               "Mark each word on its own: *tere* *bina*.")
_WORD_KEYS = ("i", "text", "line", "start", "end", "score", "flagged", "reasons")


def _marker(token: str) -> tuple[str, bool] | None:
    """(text, emphasised) of a lyrics token; None when it holds a malformed marker."""
    if m := _MARKED.fullmatch(token):
        return m[1], True
    return None if token[:1] == "*" or token[-1:] == "*" else (token, False)


def strip_markers(lines: list[str]) -> list[str]:
    """Lines with every *word* marker's asterisks removed; spacing and all else kept."""
    return [_MARKED_IN_LINE.sub(r"\1", line) for line in lines]


def marker_problems(lines: list[str]) -> list[str]:
    """One "line N: ..." entry per line holding a malformed marker; [] = fine."""
    out = []
    for n, line in enumerate(lines, start=1):
        bad = [t for t in line.split() if _marker(t) is None]
        if bad:
            out.append(f"line {n}: {line.strip()} (cannot read: {', '.join(bad)})")
    return out


def read_lyrics(path: Path) -> Lyrics:
    """lyrics.txt -> verbatim lines (blank ones kept as "") and (token, line index) words."""
    path = Path(path)
    data = path.read_bytes()
    try:
        text = data.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise LyricsError(f"{path.name} is not UTF-8 (bad byte at offset {exc.start}); "
                          "save it as UTF-8") from None
    lines = text.splitlines()
    bad = [f"  line {n}: {line.strip()}" for n, line in enumerate(lines, start=1)
           if any(ch in line for ch in _ANNOTATION_CHARS)]
    if bad:
        raise LyricsError("\n".join([
            f"{path.name} has brackets, used for annotations like (x2) or [chorus]:", *bad,
            "Write every repeat out in full, with no annotations (for sung words in brackets, "
            "keep the words and drop the brackets). Lyrics are never edited automatically."]))
    if bad := marker_problems(lines):
        raise LyricsError("\n".join([
            f"{path.name} has emphasis markers it cannot read:", *(f"  {b}" for b in bad),
            MARKER_HINT + " Lyrics are never edited automatically."]))
    words = _tokens(strip_markers(lines))
    if not words:
        raise LyricsError(f"{path.name} has no words")
    emphasis = frozenset(i for i, (token, _) in enumerate(_tokens(lines)) if _marker(token)[1])
    return Lyrics(path, hashlib.sha256(data).hexdigest(), lines, words, emphasis)


def build_words(lyrics: Lyrics, raw: list[RawWord]) -> list[Word]:
    """Pair lyrics words 1:1 with aligner output: text and line from lyrics, times from raw."""
    if len(raw) != len(lyrics.words):
        raise ValueError(f"aligner returned {len(raw)} results for {len(lyrics.words)} words")
    return [Word(i, text, line, r.start, r.end, r.score)
            for i, ((text, line), r) in enumerate(zip(lyrics.words, raw))]


def apply_flags(words: list[Word], duration_s: float, min_score: float | None) -> None:
    """Recompute flagged/reasons of every word from scratch (idempotent). Never touches a time."""
    # Order is judged against the nearest earlier trusted (placed, unflagged) word, the same rule
    # validate() uses, so apply_flags output always validates even when an aligner jumps back.
    prev: Word | None = None
    for w in words:
        placed = w.start is not None and w.end is not None
        hit = {
            "not_placed": not placed,
            "low_confidence": (min_score is not None and w.score is not None
                               and w.score < min_score),
            "bad_duration": placed and (w.end <= w.start or w.end - w.start > MAX_WORD_S),
            "out_of_order": (placed and prev is not None
                             and (w.start < prev.start or w.start < prev.end - OVERLAP_TOL_S)),
            "out_of_bounds": placed and (w.start < 0 or w.end > duration_s + BOUNDS_TOL_S),
        }
        w.reasons = [r for r in REASONS if hit[r]]
        w.flagged = bool(w.reasons)
        if placed and not w.flagged:
            prev = w


def make_doc(song: str, audio_path: Path, duration_s: float, audio_sha: str, lyrics: Lyrics,
             aligner: dict, words: list[Word]) -> dict:
    """The words.json document (plan §3). Its key order is the key order on disk."""
    return {
        "version": WORDS_VERSION,
        "song": song,
        "audio": {"file": Path(audio_path).name, "duration_s": duration_s, "sha256": audio_sha},
        "lyrics": {"file": Path(lyrics.path).name, "sha256": lyrics.sha256,
                   "lines": strip_markers(lyrics.lines)},
        "aligner": aligner,
        "created": datetime.now().isoformat(timespec="seconds"),
        "words": [{"i": w.index, "text": w.text, "line": w.line, "start": w.start, "end": w.end,
                   "score": w.score, "flagged": w.flagged, "reasons": list(w.reasons)}
                  for w in words],
    }


def save_words(path: Path, doc: dict) -> None:
    """Write doc for hand-editing: header indented 2 spaces, each word object on one line."""
    parts = []
    for key, value in doc.items():
        if key == "words":
            rows = ",\n".join("    " + json.dumps(w, ensure_ascii=False) for w in value)
            text = f"[\n{rows}\n  ]"
        else:  # json.dumps escapes newlines inside strings, so every "\n" here is layout
            text = json.dumps(value, indent=2, ensure_ascii=False).replace("\n", "\n  ")
        parts.append(f"  {json.dumps(key)}: {text}")
    Path(path).write_text("{\n" + ",\n".join(parts) + "\n}\n", encoding="utf-8", newline="\n")


def load_words(path: Path) -> dict:
    # utf-8-sig: a text editor may add a BOM when the owner hand-edits the file
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def validate(doc: dict, lyrics_path: Path | None = None,
             audio_path: Path | None = None) -> list[str]:
    """Every problem with a words.json doc; [] means valid. Bad input is reported, never raised.

    Given lyrics_path / audio_path, the doc is also reported stale if that file changed after
    alignment. For lyrics, only the text counts: lyrics.lines must equal lyrics.txt's lines
    without emphasis markers, so adding, moving or removing *markers* is never stale (H-009).
    """
    if not isinstance(doc, dict):
        return ["words.json is not a JSON object"]
    audio = doc["audio"] if isinstance(doc.get("audio"), dict) else {}
    lyrics = doc["lyrics"] if isinstance(doc.get("lyrics"), dict) else {}
    duration, lines, words = audio.get("duration_s"), lyrics.get("lines"), doc.get("words")
    header = {
        "song": isinstance(doc.get("song"), str),
        "audio.file": isinstance(audio.get("file"), str),
        "audio.duration_s": _is_num(duration),
        "audio.sha256": isinstance(audio.get("sha256"), str),
        "lyrics.file": isinstance(lyrics.get("file"), str),
        "lyrics.sha256": isinstance(lyrics.get("sha256"), str),
        "lyrics.lines": isinstance(lines, list) and all(isinstance(ln, str) for ln in lines),
        "aligner": isinstance(doc.get("aligner"), dict),
        "created": isinstance(doc.get("created"), str),
        "words": isinstance(words, list),
    }
    errors = []
    if doc.get("version") != WORDS_VERSION:
        errors.append(f"version: expected {WORDS_VERSION}, got {doc.get('version')!r}")
    errors += [f"{key}: missing or invalid" for key, ok in header.items() if not ok]

    expected = _tokens(lines) if header["lyrics.lines"] else None
    words = words if header["words"] else []
    if header["words"] and expected is not None and len(words) != len(expected):
        errors.append(f"words has {len(words)} entries but lyrics.lines has {len(expected)} words")
    limit = duration + BOUNDS_TOL_S if header["audio.duration_s"] else math.inf
    prev = None  # (index, start) of the nearest earlier non-flagged word
    for n, w in enumerate(words):
        shown = w.get("text", "") if isinstance(w, dict) else ""
        label = f'word {n} ("{shown}"): '
        if not isinstance(w, dict):
            errors.append(label + "not a JSON object")
            continue
        missing = [key for key in _WORD_KEYS if key not in w]
        if missing:
            errors.append(label + "missing " + ", ".join(missing))
            continue
        if type(w["i"]) is not int or w["i"] != n:
            errors.append(label + f'"i" is {w["i"]!r}, expected {n}')
        if expected is not None and n < len(expected):
            text, line = expected[n]
            if w["text"] != text:
                errors.append(label + f'text differs from lyrics.lines: expected "{text}"')
            if type(w["line"]) is not int or w["line"] != line:
                errors.append(label + f'"line" is {w["line"]!r}, expected {line}')

        reasons, flagged = w["reasons"], w["flagged"]
        if not isinstance(reasons, list):
            errors.append(label + '"reasons" must be a list')
        elif unknown := [r for r in reasons if r not in REASONS]:
            errors.append(label + f"unknown reasons {unknown}; allowed: {', '.join(REASONS)}")
        if not isinstance(flagged, bool):
            errors.append(label + '"flagged" must be true or false')
        elif flagged and reasons == []:
            errors.append(label + "flagged but has no reasons")

        start, end = w["start"], w["end"]
        if flagged is not False:  # flagged (or "flagged" invalid, reported above): times optional
            errors += [label + f'"{key}" must be a number or null' for key in ("start", "end")
                       if w[key] is not None and not _is_num(w[key])]
        elif not (_is_num(start) and _is_num(end)):
            errors.append(label + "not flagged, so it needs a numeric start and end: add both "
                                  "times, or set flagged back to true")
        else:
            if start < 0:
                errors.append(label + f"start {start} is negative")
            if end <= start:
                errors.append(label + f"end {end} is not after start {start}")
            if end > limit:
                errors.append(label + f"end {end} is past the audio end ({duration} s)")
            if prev is not None and start < prev[1]:
                errors.append(label + f"start {start} is before word {prev[0]}'s start {prev[1]}")
            prev = (n, start)
        if w["score"] is not None and not _is_num(w["score"]):
            errors.append(label + '"score" must be a number or null')

    for what, path, section in (("lyrics", lyrics_path, lyrics), ("audio", audio_path, audio)):
        if path is None:
            continue
        try:
            data = Path(path).read_bytes()
        except OSError as exc:
            errors.append(f"cannot read {path}: {exc.strerror or exc}")
            continue
        name = Path(path).name
        changed = hashlib.sha256(data).hexdigest() != section.get("sha256")
        if what == "audio":
            if changed:
                errors.append(f"stale: {name} changed after this words.json was made "
                              "(sha256 differs); re-run align")
            continue
        file_lines = data.decode("utf-8-sig", "replace").splitlines()
        if bad := marker_problems(file_lines):
            errors += [f"{name} {b}" for b in bad] + [MARKER_HINT]
        elif strip_markers(file_lines) != lines:
            errors.append(f"stale: {name} changed after this words.json was made; re-run align"
                          if changed else f"lyrics.lines differ from {name}; they must be its "
                          "lines without the emphasis asterisks")
    return errors


def _tokens(lines: list[str]) -> list[tuple[str, int]]:
    # The single definition of "the words of lyrics.txt", shared by read_lyrics and validate.
    return [(token, n) for n, line in enumerate(lines) for token in line.split()]


def _is_num(x) -> bool:
    """A finite JSON number. (bool is an int subclass in Python, but never a time.)"""
    try:
        return isinstance(x, (int, float)) and not isinstance(x, bool) and math.isfinite(x)
    except OverflowError:  # an int too large for a float
        return False
