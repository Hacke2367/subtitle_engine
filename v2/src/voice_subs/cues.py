"""Timed words -> subtitle cues -> an `.srt` file.

Plain rules, no LLM (D-102): a cue ends where the speaker pauses, where a sentence ends, or
when it would get too long or too slow to read. A length break never strands a word that leans
on its neighbour ("kisi / na", "quantity / mein"): it moves one word back instead.

Cue times are display times built from the words' own times (red line 2), never estimated: a
cue appears LEAD_S before its first word (text that arrives with the voice reads late), and
stays after its last word until the next cue, or HOLD_S into a silence, so back-to-back cues
never blink and the last word is never cut off while it is still being said. The words' own
times are untouched; the highlight in `style.py` still follows each word exactly.

Words are never merged, split, reordered or respelled here (red line 1): a cue's text is its
words joined by single spaces, in order.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

PAUSE_S = 0.45          # a gap this long between two words reads as a pause -> new cue
MAX_CHARS = 42          # two short lines on a 9:16 screen
MAX_DUR_S = 6.0         # no cue's words run longer than this
LEAD_S = 0.10           # a cue shows this long before its first word is heard
HOLD_S = 0.40           # and stays this long into a silence after its last word
MIN_DUR_S = 1.2         # a short cue is held this long if the silence after it allows
LAST_HOLD_S = 4.0       # the last cue stays up to this long, to the end of the clip
SENTENCE_ENDS = ".?!।"

# Hinglish (and English) words that lean on a neighbour: a line or cue never starts with the
# first kind (postpositions, auxiliaries: "sach / mein") or ends with the second (determiners,
# quantifiers: "ek / line"). Shared with style.py's line breaks.
LEANS_BACK = frozenset("""mein me ka ki ke ko se ne par pe tak hai hain tha thi the ho hoga hogi
    honge hun hoon to bhi hi wala wali wale""".split())
LEANS_FORWARD = frozenset("""ek is us ye yeh vo woh koi kisi kuch kuchh har bahut sab sabse
    apna apni apne mera meri mere tera teri tere uska uski uske iska iski iske aisa aisi aise
    the a an of to and in my your our their this that""".split())


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
        reason = _break_before(word, groups[-1], pause_s, max_chars, max_dur_s) if groups \
            else "first"
        if reason is None:
            groups[-1].append(word)
        elif reason == "length" and len(groups[-1]) > 1 and (
                core(word["text"]) in LEANS_BACK or core(groups[-1][-1]["text"]) in LEANS_FORWARD):
            groups.append([groups[-1].pop(), word])     # "kisi / na kisi" -> "/ kisi na kisi"
        else:
            groups.append([word])
    return _display_times(groups, duration)


def core(text: str) -> str:
    """A word without its punctuation, lowercased: what the word lists are checked against."""
    return re.sub(r"[^\w]", "", text).lower()


def _break_before(word: dict, group: list[dict], pause_s: float, max_chars: int,
                  max_dur_s: float) -> str | None:
    """Why a new cue starts at this word ("sentence", "pause", "length"), or None."""
    last = group[-1]
    if last["text"].rstrip().endswith(tuple(SENTENCE_ENDS)):
        return "sentence"                                       # one cue per sentence
    if float(word["start"]) - float(last["end"]) >= pause_s:
        return "pause"                                          # the speaker paused
    length = sum(len(w["text"].strip()) for w in group) + len(group)  # + the spaces
    if length + len(word["text"].strip()) > max_chars:
        return "length"
    if float(word["end"]) - float(group[0]["start"]) > max_dur_s:
        return "length"
    return None


def _display_times(groups: list[list[dict]], duration: float | None) -> list[Cue]:
    """Each group's on-screen times: a short lead, then held until the next cue or a silence."""
    first = [float(g[0]["start"]) for g in groups]
    last = [float(g[-1]["end"]) for g in groups]
    starts = []
    for i, word_start in enumerate(first):
        start = max(0.0, word_start - LEAD_S)
        if i:
            start = max(start, last[i - 1])     # never over the previous cue's last word
        starts.append(start)
    cues = []
    for i, group in enumerate(groups):
        if i + 1 < len(groups):
            limit = starts[i + 1]
            end = limit if limit - last[i] < HOLD_S else last[i] + HOLD_S
        else:
            limit = duration if duration is not None else last[i] + LAST_HOLD_S
            end = min(limit, last[i] + LAST_HOLD_S)
        end = max(end, min(starts[i] + MIN_DUR_S, limit), last[i])
        cues.append(Cue(start=round(starts[i], 3), end=round(end, 3),
                        text=" ".join(w["text"].strip() for w in group)))
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
