# Spec: Emphasis Words (`*word*`)
**Version:** 1.0.0 | **Component:** lyrics reader and `words.json` contract (`timing.py`), aligner input, `clip`, Soft Romantic renderer
**Status:** Ready for Review
**Plan step:** 06 (`docs/development_plan.md`) · **Branch:** `feature/emphasis-markers` · **Decisions:** H-009, D-016

## 1. Problem Statement

Every word in the overlay gets the same treatment today. The hook words of a song ("dil", "tu",
the title line) get no weight, and the research (`docs/research/lyric_aesthetics.md` §2) finds
that a premium lyric edit gives 3-5 hand-picked hook words one small extra move, and nothing else.
The owner knows which words matter; the engine has no way to hear it. V1 scope already promised
"emphasis words marked by hand in `lyrics.txt`", and step 03 shipped without it because the marker
touches red line 2. H-009 settled the marker: `*word*`, never drawn.

## 2. Objective

The owner wraps a word in asterisks in `lyrics.txt`, re-renders, and that word, and only that
word, swells gently as it is sung; the asterisks never reach the screen, the aligner or the
timings.

## 3. Scope & Constraints

**Will Do:**
- Read `*word*` markers in `lyrics.txt`: one marker per word, around the whole word including
  its punctuation (`*dil,*`). Reject malformed markers with the line number, as brackets are
  rejected today.
- Keep the asterisks away from the aligners: both engines receive the words without markers.
- Make `lyrics.txt` the only place emphasis lives. Adding, removing or moving markers after
  alignment does not make `words.json` stale, does not need a re-align, and keeps the owner's
  hand-edited timings.
- Soft Romantic gets **one** emphasis move, the swell: the marked word grows slightly around its
  own centre while it is sung (about 1.06×, eased in with the reveal), holds for its sung
  duration, and settles back to normal size after it ends. Size and timings live in `theme.py`
  for the owner to tune from `preview.mp4`.
- `clip` keeps the source's markers on the lines it copies.
- The render summary lists the emphasised words, so the owner can confirm what was picked up.
- Unit tests for the marker rules, aligner input, staleness and the swell's frame region.
  Offline, with synthetic fixtures (`songs/` is not in git).

**Will NOT Do:**
- A second emphasis move (glow, colour, tracking) or a per-word choice of move: one move per
  theme (research §2, §12). Pop Karaoke's own move comes in step 07.
- A cap or warning on how many words are marked. Restraint is the owner's call.
- Emphasis on a span of words as one unit. Each word is marked on its own: `*tere* *bina*`.
- Changing where words sit: wrapping and word positions are computed at normal size, and
  neighbours never move.
- Any emphasis field in `words.json`, or a new tag syntax (the blueprint's `<glow>` etc. stay out
  of scope).

**Hard Rules:**
- **Red line 2, with its one exception (H-009):** on-screen text equals `lyrics.txt` with the
  marker asterisks removed. Nothing else changes: spelling, casing, punctuation, line breaks.
  An asterisk inside a word (`f**k`) is lyric text, drawn as written.
- **Red line 1:** the swell is timed by the word's own aligned start and end. An unaligned word
  shown with `--allow-flagged` gets no swell, since it has no sung time.
- Lyrics are never auto-fixed. A malformed marker stops `align`, `clip` and `render` with a
  message that names the line and shows the correct form.

## 4. Core Design

1. **Marker grammar** (lyrics reader, `timing.py`). Words are still whitespace-separated tokens.
   A token that starts **and** ends with `*`, with at least one character between that is not
   `*` at either end, is a marked word: its text is the inside, and it is emphasised. Any other
   token that starts or ends with `*` is malformed.
2. **Aligner input.** Aligners get the marker-free text of each word (they already reduce words
   to letters and digits for matching; the ElevenLabs request text must not carry `*` either).
3. **`words.json`** stays a timing file. Each word's `text` is the marker-free text, the text
   that is drawn. The copy of the lyrics lines inside it is marker-free too. Emphasis is not
   stored there.
4. **Staleness.** `words.json` is stale when `lyrics.txt` changed in anything other than its
   markers, or when the audio changed, as today. A markers-only edit is not stale. Existing
   `words.json` files (made before this step, no markers) stay valid without re-aligning.
5. **Render.** The renderer reads the current `lyrics.txt`, pairs its words 1:1 with
   `words.json` by position, and gives the marked ones Soft Romantic's swell. The drawn string
   is checked against `words.json`'s `text`, as it is today.
6. **`clip`** writes the new song's `lyrics.txt` from the source `lyrics.txt` lines, markers
   included, not from the marker-free copy in `words.json`.

## 5. Edge Cases & Error Handling

| Input | Result |
|---|---|
| `*dil*` | word `dil`, emphasised |
| `*dil,*` | word `dil,`, emphasised |
| `*dil*,` / `*dil` / `dil*` / `**dil**` / `*` / `**` | `LyricsError`: line number + "wrap the whole word, punctuation inside: `*dil,*`" |
| `*tere bina*` | `LyricsError` (tokens `*tere` and `bina*`): "mark each word on its own: `*tere* *bina*`" |
| `f**k` | literal word `f**k`, not emphasised |
| Markers added or moved after `align` | `validate` passes; `render` runs with no re-align; `words.json` unchanged |
| A word's letters changed after `align` | stale, as today: re-align needed |
| Marked word is flagged (unaligned), `--allow-flagged` | drawn static, no swell |
| Marked word sung very briefly (shorter than the swell's ease) | swell scales down with the word's own duration; never extends past its timing window into the next word's |
| Old `words.json`, no markers anywhere | renders pixel-identically to before this step |
| Every word on a line marked | allowed; each swells on its own time |

## 6. Acceptance Criteria

1. **Marker rules:** unit tests cover every row of the §5 marker table: the right text and
   emphasis flag, or a `LyricsError` naming the line.
2. **Aligners never see `*`:** a unit test shows the ElevenLabs request text and the local
   aligner's words for a marked lyrics file contain no asterisk.
3. **Old songs untouched:** the existing `songs/khidki` and `songs/khidki_s2` `words.json` files
   validate unchanged. Re-rendering `khidki_s2` gives frames pixel-identical to `dev`'s renderer
   at every 30th frame.
4. **Markers-only edit is free:** after adding 2-3 markers to `khidki_s2/lyrics.txt`,
   `validate` passes, `render` succeeds without `align`, and `words.json` is byte-for-byte
   unchanged. Changing a word's letters instead still reports stale.
5. **Swell on exactly the marked words:** rendering the same `words.json` with and without
   markers, frames differ only inside the marked words' swell boxes, and only between each
   marked word's reveal and the end of its settle. No swell box overlaps a neighbouring word's
   ink at default settings.
6. **Text:** the drawn text of every word equals its `words.json` `text`, which equals the
   `lyrics.txt` token minus the marker asterisks (existing red-line assertion, still enforced).
7. **Clip:** clipping a marked song gives a `lyrics.txt` with the same markers on the copied
   lines.
8. **Flagged:** a flagged marked word rendered with `--allow-flagged` shows no swell (unit test).
9. **Speed:** rendering `khidki_s2` with 3 marked words takes at most 10% longer than without.
10. **Look:** the owner approves the swell in `khidki_s2`'s `preview.mp4` (tune `theme.py`
    until they do).
11. The gate passes (unit tests + alpha proof).
