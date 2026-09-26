# Spec: Workflow Commands (`clip`, `make`)
**Version:** 1.0.0 | **Component:** `workflow.py`, CLI
**Status:** Approved by the owner's instruction ("pahele tum karke, 2 kaam karo", D-014)
**Plan step:** 05 · **Branch:** `feature/workflow-clip-make` (stacked on step 03)

## 1. Problem Statement
Making one short takes five manual steps today: cut the audio, make a folder, copy exactly the
lyric lines sung in that part, run `align`, run `render`. Getting the lines right by hand is the
error-prone part, and a wrong line breaks sync. The project's success signal is "far less effort
than manual".

## 2. Objective
Full song + a rough time range → a ready overlay in two commands:
`clip songs/<full> --from A --to B` and `make songs/<clip>`.

## 3. Scope & Constraints
**Will Do:**
- `clip`: uses the full song's `words.json` (it must be aligned, valid and not stale) to find the
  lyric lines lying **entirely** inside [A, B]. Snaps the cut so no line is ever cut in half. Writes
  a new song folder containing: `audio.wav` (lossless cut), `lyrics.txt` (those lines verbatim,
  blank stanza lines between them kept), and `clip.json` (source, requested and actual range,
  lines).
- `make`: aligns the folder if it has no `words.json`, then renders. An existing valid `words.json`
  is used as is (it may hold the owner's corrections). A stale one is refused.
- Offline tests for line selection, snapping, refusals, verbatim lyrics, and make's decisions.

**Will NOT Do:**
- Overwrite an existing song folder or an existing `words.json`.
- Guess lyrics for singing that isn't in the full song's `lyrics.txt` (unwritten repeats).
- Re-use the full song's word times for the clip: the clip is re-aligned on its own audio.

**Hard Rules:**
- Red line 2: the clip's lyrics are the source lines verbatim, with nothing re-typed or cleaned.
- Red line 1: `clip` invents no word time. It only chooses where to cut the audio, from line spans
  the aligner produced.
- A line containing a flagged word can't anchor a cut, so `clip` refuses and names it.

## 4. Core Design
Line span = [first word start, last word end] of a line whose words are all timed and unflagged.
Selected lines = spans inside [A, B].
- **Start:** A is kept if it falls in the gap before the first selected line (so an intro can stay).
  If it falls inside a line, the cut moves to that line's gap, at most 0.3 s before the first
  selected word and never past the middle of the gap.
- **End:** B is handled the same way on the other side, with at most 1.0 s of tail.
- Both are clamped to the audio.
- If more than 3 s of audio precede the first selected word, `clip` prints a warning (unwritten
  singing may be there).

## 5. Edge Cases
- Full song not aligned, or stale → refuse and say to run `align`.
- No whole line inside [A, B] → refuse and name the nearest lines.
- A selected line has a flagged word → refuse and name it.
- The output folder exists → refuse.
- A > B, a negative A, or B past the end → refuse or clamp, with a clear message.
- `make` with a flagged `words.json` → render's own refusal (`--allow-flagged` passes through).

## 6. Acceptance Criteria
1. Offline unit tests pass: selection, both snapping sides, the flagged, empty and existing
   refusals, verbatim lyrics with stanza breaks, and make's three paths (missing → align + render,
   valid → render only, stale → refuse).
2. `clip songs/khidki_full --from 27 --to 57` selects lines 1–8, the same as the hand-made clip.
3. A second portion of the test song (stanza 2) goes `clip` → `make` → render checks pass.
4. A different song is pending: the owner provides one.
