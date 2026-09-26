# Spec: Lofi Minimal Theme
**Version:** 1.0.1 | **Component:** themes (`theme.py`), layout (tracking), renderer (`render/`), render checks
**Status:** Approved by owner 2026-09-27 ("yes"), including the §7 choices. v1.0.1: §4.3 wording
made exact (a short word's fade into current shrinks to fit its own span), no change in scope.
**Plan step:** 09 (`docs/development_plan.md`) · **Branch:** `feature/lofi-minimal-theme` · **Decisions:** H-016, H-012, H-013, H-009, D-017, D-018

## 1. Problem Statement

The engine has three looks: Soft Romantic v1 and v2 (warm, glowing, word-by-word) and Pop Karaoke
(bold, colour fill). None of them fits the lofi, sad and black-screen status edits the research
found (§3 shortlist 3, §9 "sad status"). Those edits use small, light type with lots of air: one
line at a time, slow fade and rise, long holds, and the sung word marked by a quiet colour change
instead of glow or fill. The blueprint calls this style "Lofi / Vaporwave". H-012 puts it next.

## 2. Objective

`render songs/<song> --theme lofi-minimal` and `--theme lofi-typewriter` render the same
`words.json` in the Minimal Lowercase look (§4), with every render check passing, the other
three themes unchanged, and the owner approving the look.

## 3. Scope & Constraints

**Will Do:**
- Two new themes, both beside the existing ones (outputs in `render/<theme>/`, D-018):
  - `lofi-minimal`: the whole line shows ahead in a dim **upcoming** state; each word turns to
    the **current** colour while it is sung, then settles to the **sung** colour (H-016).
  - `lofi-typewriter`: the same look, but nothing shows ahead: each word's letters type in one
    by one inside that word's own aligned time (H-016).
- One line on screen at a time, entering with a slow fade and rise and leaving with a slow fade.
- Wide tracking (extra letter spacing) as a theme value. It is part of the word as drawn and
  measured.
- Bundle Poppins Light (SIL OFL, same family and licence file as the bundled Poppins SemiBold).
- Marked `*word*`s at `emphasis_scale` × their line's size, in both themes (H-013).
- Render checks: a colour-state sync check (`lofi-minimal`), a typing sync check
  (`lofi-typewriter`), and the safe-zone check, as §4.6.
- Unit tests for the colour states, typing times, line life cycle, tracking and themes; offline,
  synthetic fixtures.
- A lowercase test song for the look preview (§4.7).

**Will NOT Do:**
- Change any casing. The lowercase look comes from the owner writing the lyrics in lowercase;
  the engine draws `lyrics.txt` as written (red line 2). No auto-lowercase, no lowercase font.
- Change Soft Romantic v1, v2 or Pop Karaoke. Their frames stay pixel-identical (tracking 0).
- A past-line stack, blur, glow, stroke, backplate or scale pop. The sung word is marked by
  colour only; the legibility layer is a soft shadow.
- A caret, sound-driven or beat-driven motion (beat data is step 11), or per-letter timestamps.
- Film grain, vignette or light leaks: they belong to the footage in CapCut (research §2).
- Typewriter for non-Latin text (Devanagari, emoji): such a word appears whole (§4.4).
- Change the default theme (it stays `soft-romantic-v2`, H-015), `words.json`, alignment, or the
  command-line options beyond the two new `--theme` names.
- Devanagari shaping (step 14).

**Hard Rules:**
- **Red line 1:** a word turns current on the frame of `start − lead` and stays current until
  the frame of `end − lead`. In `lofi-typewriter` its first letter starts on the frame of
  `start − lead` and its last letter starts before `end − lead`. Letters get no timestamps of
  their own: their spacing is derived from the word's own span (§4.4). Line entrances, exits and
  colour fades are decoration and never move a word's current window. A word with no timing
  never turns current and never types.
- **Red line 2:** every drawn string is the `words.json` text (the existing assertion, including
  the tracked mask). Typing reveals the word's own drawn mask; it never draws a different string.
- Styling rules (plan, research §5-§8): ease-out in, ease-in out, no overshoot; one font family
  plus the existing glyph fallback; one palette; a legibility layer; text inside the safe zone
  x 60-960, y 380-1540; no hue-120 green (the existing theme guard).

## 4. Core Design

### 4.1 What the screen shows

One lyric line at a time, centred on x 510 at the theme's anchor.

| State | `lofi-minimal` | `lofi-typewriter` |
|---|---|---|
| Word not yet sung (**upcoming**) | cream at 35% opacity | not drawn |
| Word being sung (**current**) | blush pink, full opacity; fades in from upcoming over 0.12 s from `start − lead` | its letters type in (§4.4) in blush pink |
| Word sung (**sung**) | cream, full opacity; fades from blush over 0.4 s from `end − lead` | same |
| Flagged word (only with `--allow-flagged`) | stays upcoming for as long as its line is on screen | drawn whole in the sung colour from its line's first frame |

Every drawn letter carries the soft shadow in every state.

### 4.2 Line life cycle

1. **Enter.** `lofi-minimal`: the line fades in and rises 20 px over 0.6 s (ease-out), starting
   `preroll` (0.9 s) before its first word turns current, so it rests in the upcoming state for a
   moment first. `lofi-typewriter`: there is no entrance; the first letter typed is the entrance.
2. **Sing.** Each word changes state (or types) on its own time.
3. **Leave.** After the line's last word ends, the line holds for `hold` (1.5 s), then fades out
   while rising 10 px more, over 0.5 s (ease-in). The screen is then empty until the next line.

Rules when lines come close together:
- A line never starts leaving before its last word's `end − lead`, so every word shows its whole
  current window at full line opacity.
- Two lines are never on screen at once: the next line's entrance starts only when the old line
  has finished leaving.
- When the next line needs the screen before `hold` is over, the old line leaves early, as late
  as it can while the next line is still at rest when its first word turns current.
- When the time between the old line's last word end and the next line's first word start is
  shorter than exit plus entrance (`lofi-typewriter`: shorter than the exit), those durations
  shrink in proportion.
- Below two frames, the old line disappears and the next line shows at rest on the same frame (a
  cut). The report lists it as a note, not a failure. Lines sung back to back, where the next
  first word starts before the old last word ends, are cut on the next word's current frame;
  the old last word loses its remaining frames. Report note.

A first word within the entrance time of 0:00 shows its line at rest from frame 0.

### 4.3 Colour states

A word's current state starts on the frame of `start − lead` (lead 0.05 s, same as the other
themes) and ends on the frame of `end − lead`. The fade into current (0.12 s) and the fade into
sung (0.4 s) start at those frames and never shift them. For a word shorter than the fade-in, the
fade-in shrinks to fit its own span, so every timed word is fully current on its end frame; the
fade to sung then starts from full current, with no jump.

### 4.4 Typewriter (`lofi-typewriter`)

A word of `n` letters types letter by letter, left to right. Letter `i` (from 0) starts at
`start − lead + i × s`, with `s = min(stagger, (end − start) / n)` and `stagger` 0.06 s, so a
typed word finishes typing inside its own span: quickly on a long word, compressed on a short
one. Each letter fades in over 0.1 s. Letters are cut from the word's own drawn mask at glyph
edges, so the typed word is pixel-identical to the whole word once every letter is in (kerning
and tracking kept).

A word with any character outside Latin script, or drawn by a fallback font, appears whole on
its current frame, as if it had one letter. The report lists it once per render as a note.

### 4.5 Start values (all in `theme.py`; the owner tunes them after the preview)

| Value | Start | Source |
|---|---|---|
| Font | Poppins Light (bundled), existing fallback chain after it | research §3, §6 |
| Line size / smallest shrink size | 76 px / 52 px, wrap as today | research §8 (44 px floor) |
| Tracking | 0.10 × the word's size between letters | research §2 ("wide tracking") |
| Upcoming / current / sung | cream `#F5EFE6` at 35% / blush `#F7C6D0` / cream `#F5EFE6` | research §7 palette 3 |
| Shadow | `#2B2A33`, 50%, soft blur, small drop | research §7 palette 3, §8 |
| Enter / preroll | 0.6 s fade + 20 px rise / 0.9 s | research §5 |
| Hold / exit | 1.5 s / 0.5 s fade + 10 px rise | research §3 ("long holds") |
| Colour fades | 0.12 s into current, 0.4 s into sung | research §5 |
| Typewriter | 0.06 s per letter at most, 0.1 s letter fade | research §2 (30-120 ms stagger) |
| Text box / safe zone | centred on x 510, inside x 60-960, y 380-1540 | research §8, spec 07 §4.6 |
| Lead / emphasis | 0.05 s / `emphasis_scale` 1.5 | spec 03, H-013 |

### 4.6 Render checks

The existing output checks (sizes, frame rate, frame count, alpha, audio) run as for every theme.
Read only on frames where the word's line is at rest and alone on screen; a word that cannot be
read that way is a report note, never a silent pass.

- **Colour-state sync (`lofi-minimal`):** from the decoded overlay, each timed word shows no
  current colour on the frame before `start − lead`, is fully current once its fade-in completes
  (shrunk to fit a short word), and is still current on the frame before `end − lead`.
- **Typing sync (`lofi-typewriter`):** from the decoded overlay's alpha, each timed word has no
  ink on the frame before `start − lead` and all its ink once its last letter's fade completes,
  never later than `end − lead` plus one letter fade.
- **Safe zone:** no drawn pixel (the same alpha threshold as Pop Karaoke) outside x 60-960,
  y 380-1540 in any frame.

### 4.7 Test song

`songs/khidki_s2_lofi/`: `khidki_s2_em`'s audio and lyrics with every line written in lowercase
by hand (markers kept), aligned fresh with the default local aligner. It exists only so the
preview shows the look as intended; `khidki_s2` and `khidki_s2_em` render in both themes as they
are, capital letters included.

## 5. Edge Cases & Error Handling

| Case | Behaviour |
|---|---|
| Lyrics not in lowercase | drawn exactly as written; the theme never changes casing |
| Next line due before `hold` ends | old line leaves early (§4.2); the next line is at rest by its first word |
| Lines sung back to back | cut on the next word's current frame; report note (§4.2) |
| Long instrumental gap | line leaves after `hold`; screen empty; next line enters alone |
| First word near 0:00 | line at rest from frame 0, no entrance |
| Word shorter than one frame | turns current and sung on the same frames as its times give; typewriter shows several letters on one frame |
| Word shorter than the fade into current | the fade-in shrinks to fit its span; fully current on its end frame, then fades to sung (§4.3) |
| Non-Latin or fallback-font word in `lofi-typewriter` | appears whole on its current frame; report note |
| Marked word on a line that had to shrink | size ratio kept (H-013); changes state or types on its own time |
| Word with no `start`/`end`, `--allow-flagged` | §4.1 flagged row; listed in the report as today |
| Word with no timing, no `--allow-flagged` | render refuses, as today |
| Line with no timed word | skipped and reported, as today |
| A line too long even at the smallest size and 3 rows | render refuses and names the line, as today |
| Poppins Light missing from `fonts/` | render refuses and names the missing file (never a silent fallback) |
| Dim upcoming words on the green mp4 | key at partial alpha like the shadow; the alpha `.mov` is exact |

## 6. Acceptance Criteria

1. **Theme choice:** `render songs/khidki_s2 --theme lofi-minimal` and `--theme lofi-typewriter`
   succeed from the existing `words.json` with no align call and write to `render/lofi-minimal/`
   and `render/lofi-typewriter/`; each `report.md` names its theme. `make --theme ...` works the
   same way. A plain `render` still uses `soft-romantic-v2`.
2. **Other themes untouched:** `soft-romantic`, `soft-romantic-v2` and `pop-karaoke` renders of
   `khidki_s2` give frames pixel-identical to `dev`'s renderer at every 30th frame.
3. **Colour states (unit test):** on synthetic words, a word shows no current colour on the frame
   before `start − lead`, is current from its fade-in through the frame before `end − lead`, and
   reaches sung 0.4 s later; a flagged word stays upcoming in every frame.
4. **Typing (unit test):** on synthetic words, the first letter starts on the frame of
   `start − lead`, letters start in reading order, the last starts before `end − lead`, the
   stagger is 0.06 s or `(end − start) / n` if smaller, and the fully typed word equals the whole
   word pixel for pixel. A non-Latin word appears whole on its current frame; a flagged word never
   types.
5. **Line life cycle (unit test):** at most one line is visible in any frame; a line never starts
   leaving before its last word's `end − lead`; a `lofi-minimal` line is at rest in the upcoming
   state before its first word turns current; hold, early leave, proportional shrink and cut
   follow §4.2 on synthetic timings, including back-to-back lines, an instrumental gap and a
   first word at 0:00.
6. **Tracking (unit test):** a word's box is its text measured with the theme's tracking, the
   drawn mask equals the measured mask, and tracking 0 gives exactly today's box.
7. **Render checks pass:** colour-state sync (`lofi-minimal`), typing sync (`lofi-typewriter`),
   safe zone, and all existing output checks pass on `khidki_s2`, `khidki_s2_em` (marked words)
   and `khidki_s2_lofi`.
8. **Emphasis:** in both themes, a marked word's box is exactly its text measured at
   `emphasis_scale` × its line's size (with tracking); words in a row share a baseline and no
   boxes overlap (spec 06 AC5, re-run).
9. **Text:** every drawn string equals its `words.json` text in both themes (existing assertion).
10. **Speed:** each theme renders `khidki_s2` in at most twice Soft Romantic v1's time on this
    laptop.
11. **Look:** the owner approves `songs/khidki_s2_lofi/render/lofi-minimal/preview.mp4` and
    `.../lofi-typewriter/preview.mp4`. Changes asked for are made as `theme.py` values, not new
    behaviour, unless the owner asks for new behaviour.
12. The gate passes (unit tests + alpha proof).

## 7. Choices made for the owner (object to any before `/plan`)

- **One line at a time**, no past line: the "lots of air" of lofi and sad-status edits (research
  §3, §9). Pop Karaoke and Soft Romantic v2 already have the two-line stack.
- **Pastel palette** (cream, dim cream, blush), the blueprint's "Lofi / Vaporwave". The
  black-screen grey palette (`#F2F2F2` / `#9CA3AF`) is a value change.
- **Colour only marks the sung word**: no glow, stroke or pop, so it reads as minimal and not as
  a quieter Soft Romantic.
- **Poppins Light, 76 px, tracking 0.10**: small and airy but above the 44 px floor; same family
  as Pop Karaoke, a different weight. DM Sans would be one more bundled font.
- **Typewriter stagger 0.06 s, capped by the word's own span**: reads as typing, never runs past
  the word. No caret.
- **Test song `khidki_s2_lofi`** (§4.7), a lowercase copy I write by hand from `khidki_s2_em`'s
  lyrics and align locally (free, a few minutes of CPU).
