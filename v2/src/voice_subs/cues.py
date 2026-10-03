"""Timed words -> subtitle cues -> an `.srt` file.

Plain rules, no LLM (D-102): a cue ends where the speaker pauses, where a sentence ends, or
when it would get too long or too slow to read. Every cue's times come from the words inside it
(red line 2); the only freedom taken is holding a very short cue on screen a little longer, into
the silence that follows it, so a one-word cue does not flash.

Words are never merged, split, reordered or respelled here (red line 1): a cue's text is its
words joined by single spaces, in order.
"""
from __future__ import annotations

from dataclasses import dataclass

PAUSE_S = 0.45          # a gap this long between two words reads as a pause -> new cue
MAX_CHARS = 42          # one comfortable subtitle line
MAX_DUR_S = 6.0         # no cue sits on screen longer than this
MIN_DUR_S = 1.0         # a short cue is held this long if the silence after it allows
HOLD_GAP_S = 0.05       # always leave this much blank between two cues
SENTENCE_ENDS = ".?!।"


@dataclass
class Cue:
    start: float
    end: float
    text: str


def to_cues(words: list[dict], *, duration: float | None = None, pause_s: float = PAUSE_S,
            max_chars: int = MAX_CHARS, max_dur_s: float = MAX_DUR_S) -> list[Cue]:
    """Group timed words (transcript.timed_words) into cues, in order."""
    groups: list[list[dict]] = []
    for word in words:
        if not groups or _breaks_before(word, groups[-1], pause_s, max_chars, max_dur_s):
            groups.append([word])
        else:
            groups[-1].append(word)
    cues = [Cue(start=float(g[0]["start"]), end=float(g[-1]["end"]),
                text=" ".join(w["text"].strip() for w in g)) for g in groups]
    return _hold_short(cues, duration)


def _breaks_before(word: dict, group: list[dict], pause_s: float, max_chars: int,
                   max_dur_s: float) -> bool:
    """Does a new cue start at this word?"""
    last = group[-1]
    if last["text"].rstrip().endswith(tuple(SENTENCE_ENDS)):
        return True                                             # one cue per sentence
    if float(word["start"]) - float(last["end"]) >= pause_s:
        return True                                             # the speaker paused
    length = sum(len(w["text"].strip()) for w in group) + len(group)  # + the spaces
    if length + len(word["text"].strip()) > max_chars:
        return True
    return float(word["end"]) - float(group[0]["start"]) > max_dur_s


def _hold_short(cues: list[Cue], duration: float | None) -> list[Cue]:
    """Hold a cue shorter than MIN_DUR_S on screen, but never into the next cue or past the end."""
    for i, cue in enumerate(cues):
        if cue.end - cue.start >= MIN_DUR_S:
            continue
        limit = cues[i + 1].start - HOLD_GAP_S if i + 1 < len(cues) else (
            duration if duration is not None else cue.end)
        cue.end = max(cue.end, min(cue.start + MIN_DUR_S, limit))
    return cues


def to_srt(cues: list[Cue]) -> str:
    """The cues as SubRip text (what CapCut, VLC and YouTube all read)."""
    blocks = [f"{i}\n{_stamp(c.start)} --> {_stamp(c.end)}\n{c.text}"
              for i, c in enumerate(cues, start=1)]
    return "\n\n".join(blocks) + "\n"


def _stamp(seconds: float) -> str:
    """HH:MM:SS,mmm, as SubRip writes a time."""
    ms = max(0, round(seconds * 1000))
    hours, ms = divmod(ms, 3_600_000)
    minutes, ms = divmod(ms, 60_000)
    secs, ms = divmod(ms, 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{ms:03d}"
