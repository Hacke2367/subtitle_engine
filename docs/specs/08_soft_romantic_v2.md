# Spec: Soft Romantic v2
**Version:** 1.0.0 | **Component:** themes (`theme.py`), renderer (`render/`), render checks
**Status:** Approved by owner 2026-09-27 ("yes"), including the §7 choices.
AC10: the owner preferred v2 ("yes v2", 2026-09-27, H-015); the default theme is now v2.
**Plan step:** 08 (`docs/development_plan.md`) · **Branch:** `feature/soft-romantic-v2` · **Decisions:** H-014, H-010, H-013, H-009, D-013, D-018

## 1. Problem Statement

Soft Romantic is the owner's everyday theme (H-010), but it shows one line at a time: when the
next line starts, the finished one simply disappears. The research (§0, §3 shortlist 1) found that
the premium version of this look keeps the finished line on screen as a dimmed, blurred memory
above the one being sung, and gives long held notes a slow glow "breath" instead of a flat glow.
Soft Romantic also draws outside the safe zone for Reels (x 90-990 today; the union safe zone is
x 60-960, research §8), so text on the right edge can sit under Instagram's action rail.

## 2. Objective

`render songs/<song> --theme soft-romantic-v2` renders the same `words.json` in Soft Romantic v2
(v1's word-by-word reveal and glow, plus a dimmed and blurred past line, a glow breath on held
notes, and every pixel inside the safe zone), beside v1's render, with every render check passing
and the owner preferring it over v1.

## 3. Scope & Constraints

**Will Do:**
- A new theme, `soft-romantic-v2`, with the look in §4. It sits beside v1 (H-014) and renders
  into `songs/<song>/render/soft-romantic-v2/` (D-018).
- Keep v1's per-word behaviour: each word fades and rises in as it is sung and carries the rose
  glow until its end, on exactly v1's frames.
- A two-line stack: the finished line moves up into a past slot, dimming, shrinking and blurring,
  when the next line starts.
- A slow glow breath on long held words.
- Every drawn pixel (glow and shadow included) inside the safe zone x 60-960, y 380-1540.
- Marked `*word*`s at `emphasis_scale` × their line's size, as in v1 (H-013).
- Render checks for v2: the reveal sync check (as v1, read with the line at rest) and the
  safe-zone check (as Pop Karaoke).
- Once the owner prefers v2 over v1 (AC10), the default theme for `render` and `make` becomes
  `soft-romantic-v2`; v1 stays available as `--theme soft-romantic`.
- Unit tests for the stack, breath, frames and theme; offline, synthetic fixtures.

**Will NOT Do:**
- Change v1. Its frames stay pixel-identical, safe zone included.
- Show upcoming words before they are sung: no waiting next line, no ghosting (H-010, H-014).
- An emphasis move beyond size (scale pop, tracking, colour); H-013 dropped the swell.
- Beat- or loudness-driven motion. The breath comes from a word's aligned duration only; beat
  data is step 11.
- A blur-in word reveal (Cinematic's primitive, step 10), a stroke, a backplate, or new colours.
- Bundle Candara: it is a Microsoft font and cannot be redistributed. v2 uses v1's fonts.
- Change Pop Karaoke, `words.json`, alignment, or the command-line options.
- Devanagari shaping (step 14).

**Hard Rules:**
- **Red line 1:** a word's reveal starts on the frame of `start − lead` and its glow holds until
  the frame of `end − lead`, exactly as v1. The stack, dimming, blur, breath and clearing are
  decoration: none of them moves, shortens or stretches a word's reveal or glow window, and a
  word with no timing never reveals, glows or breathes.
- **Red line 2:** every drawn string is the `words.json` text (the existing assertion). No
  auto-casing.
- Styling rules (plan, research §5-§8): ease-out in, ease-in out, no overshoot in this theme;
  v1's one font family plus the glyph fallback; v1's palette; v1's shadow as the legibility layer;
  no hue-120 green (the existing theme guard).

## 4. Core Design

### 4.1 What the screen shows

At most two lyric lines: the **current line** at v1's anchor, and the **past line** above it.

| State | Look |
|---|---|
| Current line, word not yet sung | not drawn (as v1) |
| Word revealing | fades in and rises 12 px over 0.2 s from its reveal frame (as v1) |
| Word being sung | cream, rose glow at full strength until its end frame (as v1) |
| Long held word (§4.3) | glow breathes slowly while held |
| Word sung | cream; its glow fades over 0.3 s after its end (as v1) |
| Past line | its sung look at 40% opacity, 85% size, blurred about 6 px, just above the current line |
| Flagged word (only with `--allow-flagged`) | drawn static, full cream, no glow (as v1) |

### 4.2 Line life cycle

1. **Appear.** A line's words appear one by one as they are sung (v1). There is no line
   entrance: the words are the entrance.
2. **Hand over.** When the next line starts, the current line moves up into the past slot while
   dimming, shrinking and blurring, over 0.35 s with an ease-out. The move starts 0.2 s before
   the next line's first word reveals, so the slot is clear when that word lands, but never
   before the current line's last word has started its reveal. A word still revealing or glowing
   then keeps its own frames in the past slot, dimmed with its line; the report lists it as a
   note (sung back to back), not a failure.
3. **Past line leaves.** A line already in the past slot fades out (ease-in), finishing as the
   next hand-over starts, so no more than two lines are ever visible.
4. **Clear.** If the next line does not start within `hold` (1.0 s) after a line's last word
   ends, the line fades out while blurring, and a past line fades with it; the screen empties.
   The next line then appears alone, word by word.

When the past slot would not fit above the current line inside the safe zone, the finished line
fades out in place at hand-over instead of moving up.

### 4.3 Glow breath on held notes

A word whose aligned duration (`end − start`) is at least `breath_min_s` (1.0 s) is a held note.
Once its glow is full, the glow strength follows a slow cosine from 100% down to about 65% and
back, one cycle every 2.0 s, until the word's end frame. The usual 0.3 s glow fade-out then starts
from wherever the breath is, with no jump. The breath changes glow strength only: never the
word's opacity, size or position, and never outside the word's own glow window. Shorter words
glow exactly as in v1.

### 4.4 Start values (all in `theme.py`; the owner tunes them after the preview)

| Value | Start | Source |
|---|---|---|
| Font, sizes, colours, glow, shadow, reveal, lead | v1's values | spec 03, D-013 |
| Text box | centred on x 510; narrower than v1's 900 px so glow and shadow stay inside x 60-960 (width set in `/plan`, enforced by the check) | research §8 |
| Hand-over | 0.35 s ease-out, starts 0.2 s before the next line | research §5 |
| Past line | 40% opacity, 85% size, blur about 6 px, 40 px above the current line | research §3, spec 07 |
| Hold / exit fade | 1.0 s / 0.3 s | research §5 |
| Breath | words ≥ 1.0 s; 100% ↔ 65% glow; 2.0 s per cycle | research §3 |
| Emphasis | `emphasis_scale` 1.5 (H-013 range 1.5-2.0) | H-013 |

### 4.5 Render checks

The existing output checks (sizes, frame rate, frame count, alpha, audio) run as for every theme.
v2 adds:

- **Reveal sync (v1's check):** for each timed word, read from the decoded overlay's alpha, the
  word's ink is absent on the frame before its reveal and solid once its reveal completes. A word
  is read only on frames where its line is at rest in the current slot and no other line overlaps
  its box; a word that cannot be read that way is a report note, never a silent pass.
- **Safe zone:** no drawn pixel (the same alpha threshold as Pop Karaoke) outside x 60-960,
  y 380-1540 in any frame.

## 5. Edge Cases & Error Handling

| Case | Behaviour |
|---|---|
| No `--theme` (before AC10 approval) | `soft-romantic` (v1), unchanged |
| No `--theme` (after AC10 approval) | `soft-romantic-v2`; v1 via `--theme soft-romantic` |
| Next line starts before the current line's last word has revealed | hand-over waits for that word to start its reveal; the word finishes on its own frames in the past slot; report note |
| Long instrumental gap | line fades and blurs out after `hold`; screen empty; next line appears alone |
| First line sung at 0:00 | its first word reveals from frame 0 as v1 (no past line exists) |
| Held word that is also the line's last word, next line close behind | the breath keeps running in the past slot, dimmed, until its end frame |
| Held word with `end` far past the voice (aligner put silence into it) | it breathes for its whole aligned duration; fixing it is a `words.json` edit, not a render guess |
| Past line too tall to fit above the current one | it fades out in place at hand-over |
| Marked word on a line that had to shrink | size ratio kept (H-013); reveals, glows and breathes on its own time |
| Word with no `start`/`end`, `--allow-flagged` | static, no glow, no breath; listed in the report as today |
| Word with no timing, no `--allow-flagged` | render refuses, as today |
| Line with no timed word | skipped and reported, as today |
| A line too long even at the smallest size and 3 rows | render refuses and names the line, as today |
| Blurred past line on the green mp4 | keys with a soft edge, like the glow (step 01's known limit); the alpha `.mov` is exact |

## 6. Acceptance Criteria

1. **Theme choice:** `render songs/khidki_s2 --theme soft-romantic-v2` succeeds from the existing
   `words.json` with no align call and writes to `render/soft-romantic-v2/`; its `report.md` names
   the theme. `make --theme soft-romantic-v2` works the same way.
2. **v1 untouched:** `render songs/khidki_s2 --theme soft-romantic` gives frames pixel-identical
   to `dev`'s renderer at every 30th frame.
3. **Word frames (unit test):** on synthetic words, v2's reveal and glow-hold frames equal v1's for
   every word; a flagged word never reveals, glows or breathes.
4. **Breath (unit test):** a word shorter than 1.0 s has v1's glow in every frame; a held word's
   glow stays between 65% and 100% while held, dips below 100% at least once in a 2 s hold, changes
   by no more than one glow step between adjacent frames at its end frame, and is 0 outside its
   glow window.
5. **Stack (unit test):** at most two lines are visible in any frame; a hand-over never starts
   before the current line's last word has started its reveal; the past line reaches 40% opacity,
   85% size and full blur; clear and past-line exit follow §4.2 on synthetic timings, including
   back-to-back lines, an instrumental gap and a first word at 0:00.
6. **Render checks pass:** v2's reveal-sync and safe-zone checks, plus all existing output checks,
   pass on `khidki_s2` and on `khidki_s2_em` (marked words).
7. **Emphasis:** in v2, a marked word's box is exactly its text measured at `emphasis_scale` ×
   its line's size; words in a row share a baseline and no boxes overlap (spec 06 AC5, re-run for
   this theme).
8. **Text:** every drawn string equals its `words.json` text (existing assertion, enforced in v2).
9. **Speed:** v2 renders `khidki_s2` in at most twice v1's time on this laptop.
10. **Look:** the owner compares `songs/khidki_s2_em/render/soft-romantic-v2/preview.mp4` with the
    v1 preview and prefers v2; then the default theme becomes `soft-romantic-v2`. Changes asked
    for are made as `theme.py` values, not new behaviour, unless the owner asks for new behaviour.
11. The gate passes (unit tests + alpha proof).

## 7. Choices made for the owner (object to any before `/plan`)

- **Past line 40% / 85% / ~6 px blur**, like Pop Karaoke's past slot plus blur. Stronger dimming
  or no shrink is a value change.
- **Hand-over starts 0.2 s early**, so the old line is out of the way when the new line's first
  word lands. It moves only the finished line, never a word's timing.
- **Hold 1.0 s instead of v1's 0.6 s**, so normal gaps between lines hand over to the stack
  instead of emptying the screen between every line.
- **Breath on words of 1.0 s or longer**, 65-100% over 2 s: slow enough to read as breathing, not
  pulsing. A deeper or faster breath is a value change.
- **Default flips to v2 only after you prefer it** (AC10); until then plain `render` stays v1.
