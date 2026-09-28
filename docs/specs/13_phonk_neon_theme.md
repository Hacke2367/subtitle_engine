# Spec: Phonk Neon Theme
**Version:** 1.0.0 | **Component:** themes (`theme.py`), renderer (`render/`), render checks
**Status:** Owner choices made up front (H-020); spec, plan and build run in one go (H-020 flow).
The owner judges the finished look (AC10).
**Plan step:** 13 (`docs/development_plan.md`) · **Branch:** `feature/phonk-neon-theme` · **Decisions:** H-020, H-019, H-018, H-016, H-013, H-012, H-009, D-018, D-021, D-022, D-024

## 1. Problem Statement

Beat Pop (step 12) moves text on the beat, but it is a daylight look: white type on a mustard
pill. Phonk, gym and night-drive edits use neon: saturated letters with a same-hue glow that
breathes with the kick, and a glitch hit on the drop (research §3 shortlist 6, blueprint
"Phonk / Aggressive"). Beats (`beats.json`) and drops (`drops.txt`) already exist; this step is
the second theme to use them.

## 2. Objective

`render songs/<song> --theme phonk-neon` renders the same `words.json` as one line at a time in
Pirata One. The line waits as an unlit purple tube; each word flickers on as it is sung and
stays lit; the lit words' glow pulses on every beat; on each drop the line RGB-splits and shakes.
Every render check passes, the other seven themes stay pixel-identical, and the owner approves
the look.

## 3. Scope & Constraints

**Will Do:**
- One new theme, `phonk-neon`, beside the others (outputs in `render/phonk-neon/`, D-018).
- Neon sign words (H-020): the line shows ahead of its first word, every word unlit (dim
  purple, no glow). Each word flickers on at its own start (on, dim, on, half, on, over ~5
  frames, shrunk to the word's span) and stays lit until the line leaves.
- Glow pulse: lit words carry a purple glow (`#BE46FF`) at rest strength ~0.55. On each beat
  frame it peaks at 1.0 and eases back over ~0.3 s. Unlit words have no glow, so they never
  pulse.
- Drop hit (H-020): at each `drops.txt` time (snapped to a beat, as Beat Pop), the line splits
  into a red and a cyan copy ±12 px that close back over ~0.25 s, and shakes with Beat Pop's
  shake (±14 px over 0.5 s) and a small scale punch (1.06×).
- A dark rim (a softened black stroke outline) around every word, lit or not, drawn over the
  glow: the legibility layer on bright footage (D-025).
- Bundle Pirata One Regular (SIL OFL) in `fonts/` with its licence. It has real lowercase, so
  casing stays as written.
- Marked `*word*`s at `emphasis_scale` × their line's size (H-013); they light and pulse like
  the rest.
- Render checks: light sync, pulse sync and the safe zone (§4.6), plus the output checks.
- Report lines: tempo and beats used, each drop (written → snapped), beats not read, notes.
- Unit tests on synthetic fixtures, offline.

**Will NOT Do:**
- Move, quantise or snap any word to a beat (red line 1). Beats and drops move decoration only.
- Light a word before its own start, or ever light an untimed (flagged) word.
- A line bump on beats (Beat Pop's look); a background or full-frame flash; scan lines, zoom
  burst, per-letter glitch.
- Detect drops automatically (H-019 stands: drops are owner-written).
- Blackletter Devanagari (step 14); any Devanagari character falls back to Nirmala UI, unshaped.
- Change the other seven themes, the default theme (`soft-romantic-v2`, H-015), `words.json`,
  `beats.json`, alignment, or `lyrics.txt`.

**Hard Rules:**
- **Red line 1:** a word is unlit on every frame before `start − lead` and lit (full) on that
  frame. Its flicker ends by its `end − lead` frame. A pulse, split or shake never lights a word,
  never hides a shown word, and never moves a word's frames.
- **Red line 2:** every drawn string is the `words.json` text; only `*` markers are hidden.
- Styling rules (plan): one display font, one palette, no hue-120 green (red `#FF1E3C` and cyan
  `#00E1FF` are far from it), a legibility layer, and every drawn pixel inside x 60–960,
  y 380–1540 in every frame, glow, split and shake included.

## 4. Core Design

### 4.1 Data flow

```
words.json ─┐
lyrics.txt ─┼─► phonk-neon renderer ─► render/phonk-neon/overlay.mov + overlay_green.mp4 + preview.mp4
beats.json ─┤    (ensure_beats: computed once if missing)
drops.txt ──┘    (optional, owner-written; same reader as Beat Pop)
```

### 4.2 What the screen shows

- One lyric line at a time, wrapped into rows, lower-middle of the frame (Beat Pop's box).
- **Entrance:** the line fades in unlit over ~0.2 s, starting ~0.5 s before its first word (as
  Lofi Minimal, H-016), or at once when the previous line leaves later than that.
- **Lighting:** each word flickers on at its own start and stays lit. The line's life cycle is
  the shared one-block-at-a-time schedule (D-021).
- **Glow pulse:** one pulse value for the frame, from the latest beat: peak on the beat frame,
  back to rest over ~0.3 s. Beats with no lit word on screen show nothing.
- **Drop:** RGB split and shake peak on the drop frame, then settle. A drop with no line on
  screen shows nothing (report note).
- **Exit:** the line fades out (~0.25 s) after a short hold.

### 4.3 Beats and drops

As Beat Pop (spec 12 §4.3–4.4): `beats.ensure_beats`, `drops.txt` snapped to the nearest beat,
the words' `lead_s` on both. The loader is shared, so errors and notes read the same.

### 4.4 Start values (all in `theme.py`; tuned after the owner's look)

| Value | Start |
|---|---|
| Font | Pirata One Regular, 100 px (min 64) |
| Lit core / glow | light purple `#E1A5FF` / purple `#BE46FF`, wide + tight blur |
| Unlit tube | dark purple `#582476`, no glow |
| Rim | black, 85%, the 4% stroke outline softened 2 px, over the glow (D-025) |
| Glow pulse | rest 0.55, peak 1.0 on the beat, back over 0.3 s |
| Flicker | on, 20%, on, 50%, on (one step per frame) |
| Drop | split ±12 px red `#FF1E3C` / cyan `#00E1FF` over 0.25 s; shake ±14 px, 1.06× over 0.5 s |
| Preroll / entrance / hold / exit | 0.5 s / 0.2 s / 0.8 s / 0.25 s |
| Layout box | 700 px about x 510, anchor 0.60 (as Beat Pop; exact margin in the plan) |

### 4.5 Emphasis and fonts

Marked words at `emphasis_scale` × their line's size (H-013), via `layout.word_fonts`, so a
character Pirata One lacks falls back instead of drawing tofu.

### 4.6 Render checks

The output checks (sizes, frame rate, frame count, alpha, audio) run as for every theme.

- **Light sync:** from the decoded overlay's colour, each timed word's ink shows the unlit colour
  on the frame before `start − lead` and the lit colour on that frame. A word whose line is not
  alone, at rest and unshaken on both frames is a report note, never a silent pass.
- **Pulse sync:** for each beat while the line is alone, at rest and unshaken on the frames
  before, of and after the beat, the glow around its steadily lit words (lit and not flickering
  on all three frames, away from any word that changes) is stronger on the beat frame than the
  frame before, and not weaker than the frame after. Beats that cannot be read that way are
  counted in a note.
- **Safe zone:** no drawn pixel outside x 60–960, y 380–1540 in any frame.

### 4.7 Test songs

`khidki_s2` (14 s), `khidki_s2_em` (marked words), `khidki_full` (172 s, with its test
`drops.txt`).

## 5. Edge Cases & Error Handling

| Situation | Behaviour |
|---|---|
| No `beats.json` / invalid / librosa missing / no beats | As Beat Pop (spec 12 §5); no beats → glow stays at rest |
| No `drops.txt` / bad line / out of song | As Beat Pop: no hit / refuse with the line number |
| Drop with no line on screen | Nothing shown; report note |
| Two drops closer than the hit | The later one restarts it |
| Word shorter than the flicker | Flicker shrunk to its span; fully lit by `end − lead` |
| Beat on a word's flicker frame | Both apply; that word is not used for the pulse read |
| Next line starts before the hold ends | Shared life cycle: early exit, or a cut with a note |
| Flagged word, `--allow-flagged` | Shown unlit with its line; never lit, never glows |
| Line with no timed word | Not shown; listed in the report |
| Marked word at 2.0× with glow, split and shake | The layout box keeps it inside the safe zone; the check proves it |

## 6. Acceptance Criteria

1. **Theme choice:** `render songs/khidki_s2 --theme phonk-neon` (and `make --theme
   phonk-neon`) renders into `render/phonk-neon/`; `words.json` and `beats.json` are
   byte-identical after; plain `render` still uses `soft-romantic-v2`.
2. **Other themes unchanged:** all seven existing themes' frames hash-identical to `dev` on
   `khidki_s2` and `khidki_s2_em`.
3. **Lighting (unit):** a word is unlit before its `start − lead` frame, full on it, at rest by
   its `end − lead` frame (short words included); an untimed word is never lit.
4. **Pulse (unit):** the glow strength peaks on each beat frame, is at rest once settled, and
   is the same for every lit word on a frame.
5. **Drop (unit):** split and shake peak on the drop frame and are zero after their spans;
   nothing is drawn for a drop with no line.
6. **Line ahead (unit):** the line is on screen, every word unlit, before its first word; one
   line at a time.
7. **Render checks:** `render --theme phonk-neon` on the three test songs says **pass** in every
   `report.md`. Not vacuous: words lit 5 frames early fail light sync, pulses moved 3 frames
   off the beat fail pulse sync, and a tight safe zone fails the zone check.
8. **Text:** a box/text mismatch raises before drawing (red line 2 assertion).
9. **Speed:** `khidki_s2` phonk-neon wall time ≤ 2× its `soft-romantic` wall time.
10. **By eye and ear (owner):** in `khidki_full`'s `preview.mp4` the glow pulses on the beat,
    the split lands on the drops, and the owner approves the look. Changes become `theme.py`
    values.
11. **Gate:** `/gate` passes.

## 7. Choices made for the owner (object any time; each is a `theme.py` value or a small change)

- **No line bump on beats.** Only the glow pulses: neon breathes, Beat Pop bounces. Keeps the two
  themes distinct.
- **The core is lighter than the glow** (`#E1A5FF` over `#BE46FF`), as real neon tubes read:
  hot centre, saturated bloom.
- **Split copies sit under the lit core**, so the word itself stays readable during the hit.
- **An untimed word stays unlit**: lighting is a timing claim (red line 1).
