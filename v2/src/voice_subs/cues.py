"""Timed words -> subtitle cues -> an `.srt` file.

Plain rules, no LLM (D-102). The words are first cut into runs wherever a sentence ends or the
speaker pauses. A run too long for one cue is cut into the fewest near-equal cues, never
between a word and the one it leans on ("kisi na kisi", "sach mein", "your screen"), and a
scrap left over (one or two words, or under a second) joins its neighbour.

Cue times are display times built from the words' own times (red line 2), never estimated: a
cue appears LEAD_S before its first word (text that arrives with the voice reads late), and
stays after its last word until the next cue, or HOLD_S into a real silence, so back-to-back
cues never blink and the last word is never cut off while it is still being said. The words'
own times are untouched; the highlight in `style.py` still follows each word exactly (D-109).

Words are never merged, split, reordered or respelled here (red line 1): a cue's text is its
words joined by single spaces, in order.
"""
from __future__ import annotations

import math
import re
from dataclasses import dataclass

PAUSE_S = 0.45          # a gap this long between two words reads as a pause -> new cue
MAX_CHARS = 42          # two short lines on a 9:16 screen
MAX_DUR_S = 6.0         # no cue's words run longer than this
LEAD_S = 0.10           # a cue shows this long before its first word is heard
HOLD_S = 0.40           # and stays this long into a silence after its last word
JOIN_S = 0.35           # a blank shorter than this between two cues is a blink: close it
MIN_DUR_S = 1.2         # a short cue is held this long if the silence after it allows
LAST_HOLD_S = 4.0       # the last cue stays up to this long, to the end of the clip
SCRAP_WORDS, SCRAP_S = 3, 0.9   # a cue with fewer words, or shorter than this, is a scrap
MERGE_GAP_S = 1.0       # a scrap joins a neighbour this close
MERGE_SLACK = 6         # and may make it this many characters longer than MAX_CHARS
LEAN_COST = 400         # what splitting a word from the one it leans on costs a cut
SENTENCE_ENDS = ".?!।"

# Words that lean on a neighbour: a line or cue never starts with the first kind
# (postpositions, auxiliaries, the light verb after a noun, an object pronoun: "sach / mein",
# "prayog / karein", "install / it") or ends with the second (determiners, quantifiers,
# subject pronouns, conjunctions, prepositions, -ly intensifiers: "ek / line", "your / screen",
# "kisi na / kisi", "extremely / crude"). Use leans_back / leans_forward; shared with style.py.
# A word spelled the same in both languages goes where it is more common: "the" is English's
# article (leans forward) far more often than Hindi's "the" (were).
LEANS_BACK = frozenset("""mein me ka ki ke ko se ne par pe tak hai hain tha thi ho hoga hogi
    honge hun hoon bhi hi wala wali wale karein karna karne karta karti karte kiya kiye karenge
    kar hota hoti hote hona hone hua hui hue raha rahi rahe sakta sakti sakte gaya gayi gaye
    diya diye liya liye
    it them him""".split())
LEANS_FORWARD = frozenset("""ek is us ye yeh vo woh koi kisi kuch kuchh har bahut sab sabse
    apna apni apne mera meri mere tera teri tere uska uski uske iska iski iske aisa aisi aise
    dusri dusra dusre pehla pehli pehle agar jab jo jaise to na main hum aap tum
    the a an of and in my your our their this that i we you youre theyre be been most first
    very at for from with by into than so its im hes shes thats theres ive youve weve id if
    because when while where which who whose although though unless until since after before
    on about over under through without within other another or but nor aur ya lekin magar
    do does did can will would should could must not have has had am are was""".split())


def leans_back(text: str) -> bool:
    """Does this word lean on the word before it (so a line must not start with it)?"""
    return core(text) in LEANS_BACK


def leans_forward(text: str) -> bool:
    """Does this word lean on the word after it (so a line must not end with it)?"""
    letters = core(text)
    return letters in LEANS_FORWARD or (len(letters) > 4 and letters.endswith("ly"))


@dataclass
class Cue:
    start: float
    end: float
    text: str


def to_cues(words: list[dict], *, duration: float | None = None, pause_s: float = PAUSE_S,
            max_chars: int = MAX_CHARS, max_dur_s: float = MAX_DUR_S) -> list[Cue]:
    """Group timed words (transcript.timed_words) into cues, in order."""
    groups: list[list[dict]] = []
    for run in _runs(words, pause_s):
        groups += _split_even(run, max_chars, max_dur_s)
    return _display_times(_merge_scraps(groups, max_chars, max_dur_s), duration)


def core(text: str) -> str:
    """A word without its punctuation, lowercased: what the word lists are checked against."""
    return re.sub(r"[^\w]", "", text).lower()


def _runs(words: list[dict], pause_s: float) -> list[list[dict]]:
    """The words cut wherever a sentence ends or the speaker pauses."""
    runs: list[list[dict]] = []
    for word in words:
        if runs:
            last = runs[-1][-1]
            ended = last["text"].rstrip().endswith(tuple(SENTENCE_ENDS))
            paused = float(word["start"]) - float(last["end"]) >= pause_s
            if not ended and not paused:
                runs[-1].append(word)
                continue
        runs.append([word])
    return runs


def _chars(words: list[dict]) -> int:
    return sum(len(w["text"].strip()) for w in words) + len(words) - 1


def _span(words: list[dict]) -> float:
    return float(words[-1]["end"]) - float(words[0]["start"])


def _split_even(run: list[dict], max_chars: int, max_dur_s: float) -> list[list[dict]]:
    """A run cut into the fewest cues that fit, as even as possible, at the best seams."""
    parts = min(len(run), max(1, math.ceil(_chars(run) / max_chars),
                              math.ceil(_span(run) / max_dur_s)))
    if parts == 1:
        return [run]
    target, n = _chars(run) / parts, len(run)
    best = [[math.inf] * (n + 1) for _ in range(parts + 1)]
    back = [[0] * (n + 1) for _ in range(parts + 1)]
    best[0][0] = 0.0
    for j in range(1, parts + 1):
        for i in range(j, n + 1):
            for k in range(j - 1, i):
                if best[j - 1][k] == math.inf:
                    continue
                piece = run[k:i]
                cost = best[j - 1][k] + (_chars(piece) - target) ** 2
                if _chars(piece) > max_chars + MERGE_SLACK or _span(piece) > max_dur_s:
                    cost += 10_000
                if k:
                    cost += _seam_cost(run, k)
                if cost < best[j][i]:
                    best[j][i], back[j][i] = cost, k
    pieces, i = [], n
    for j in range(parts, 0, -1):
        k = back[j][i]
        pieces.append(run[k:i])
        i = k
    return pieces[::-1]


def _seam_cost(run: list[dict], k: int) -> float:
    """What cutting the run before word k costs: leaning words cost, a comma or a breath helps."""
    before, after = run[k - 1], run[k]
    cost = 0.0
    if leans_back(after["text"]):
        cost += LEAN_COST
    if leans_forward(before["text"]):
        cost += LEAN_COST
    if before["text"].rstrip().endswith((",", ";", ":", "—", "-")):
        cost -= 60
    return cost - 200 * min(float(after["start"]) - float(before["end"]), 0.4)


def _merge_scraps(groups: list[list[dict]], max_chars: int,
                  max_dur_s: float) -> list[list[dict]]:
    """Join each scrap (a word or two, or under a second) to its nearer neighbour, if close."""
    groups = [list(g) for g in groups]
    i = 0
    while i < len(groups):
        group = groups[i]
        if len(groups) == 1 or (len(group) >= SCRAP_WORDS and _span(group) >= SCRAP_S):
            i += 1
            continue
        options = []
        for j in (i - 1, i + 1):
            if 0 <= j < len(groups):
                a, b = (groups[j], group) if j < i else (group, groups[j])
                gap = float(b[0]["start"]) - float(a[-1]["end"])
                # Prefer the side the scrap's own sentence is on: "select / this." joins back.
                same_sentence = not a[-1]["text"].rstrip().endswith(tuple(SENTENCE_ENDS))
                if gap < MERGE_GAP_S and _chars(a + b) <= max_chars + MERGE_SLACK \
                        and _span(a + b) <= max_dur_s:
                    options.append((not same_sentence, gap, j))
        if not options:
            i += 1
            continue
        *_, j = min(options)
        if j < i:
            groups[j] += group
            del groups[i]
            i = j
        else:
            groups[j] = group + groups[j]
            del groups[i]
    return groups


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
            # Held into the silence; a blank too short to read as a pause is closed instead.
            end = limit if limit - (last[i] + HOLD_S) < JOIN_S else last[i] + HOLD_S
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
