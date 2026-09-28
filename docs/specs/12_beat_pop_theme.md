# Spec: Beat Pop Theme
**Version:** 1.0.0 | **Component:** themes (`theme.py`), renderer (`render/`), render checks, drops input (`drops.txt`)
**Status:** Approved by owner 2026-09-28 ("yes"), including the §7 choices. AC11: the owner
approved and asked to merge PR #11 ("ok, merge karo", 2026-09-28).
**Plan step:** 12 (`docs/development_plan.md`) · **Branch:** `feature/beat-pop-theme` · **Decisions:** H-019, H-018, H-013, H-012, H-010, H-009, D-017, D-018, D-021, D-022

## 1. Problem Statement

All six themes move only with the voice. Punjabi, party and rap edits also move with the
*music*: words pop in hard, the text punches on the beat, and the frame shakes on the drop
(research §3 shortlist 5, §9 "Party: word-by-word pops on the beat"). Step 11 made beat times
available (`beats.json`), and H-019 decided what the beat drives. This step is the first theme
to use beats.

## 2. Objective

`render songs/<song> --theme beat-pop` renders the same `words.json` as one line at a time
whose words pop in as sung on a mustard pill, while the line bumps on every beat and shakes on
the drops the owner wrote. Every render check passes, the other six themes stay unchanged, and
the owner approves the look.

## 3. Scope & Constraints

**Will Do:**
- One new theme, `beat-pop`, beside the existing ones (outputs in `render/beat-pop/`, D-018).
- Words pop in as sung (H-019): each springs in with `easeOutBack` (~10% overshoot) from its own
  start. Nothing is shown before it is sung (as H-010).
- A mustard pill (`#FFC107`) behind the word being sung, with that word drawn in black, for
  exactly the word's aligned span; before and after it the word is white with a black stroke.
- A beat bump (H-019): on every beat while a line is on screen, the whole line (words and pill)
  punches up ~5% and settles back.
- A drop shake (H-019): at each time in `songs/<song>/drops.txt`, snapped to the nearest beat,
  the line on screen shakes and bumps harder, then settles.
- Beats from `beats.ensure_beats` (step 11): computed once if missing, reused after (D-022).
- Bundle Anton Regular (SIL OFL) in `fonts/` with its licence.
- Marked `*word*`s at `emphasis_scale` × their line's size (H-013); they pop and bump like the
  rest.
- Render checks: pop sync, pill sync, beat sync and the safe zone (§4.7), plus the existing
  output checks.
- Report lines: tempo and beat count used, each drop (as written → snapped), and notes (§5).
- Unit tests on synthetic fixtures, offline: theme values, pop, pill, bump, shake, drops reader,
  checks not vacuous.

**Will NOT Do:**
- Move, quantise or snap any word to a beat. A word's timing comes only from `words.json`
  (red line 1). Beats and drops move decoration only.
- Show a word or a dim line ahead (H-019: words pop as sung).
- Detect drops automatically, or read drops from anywhere but `drops.txt` (H-019). Add any
  marker syntax to `lyrics.txt` (only `*word*` exists, H-009).
- Onsets, downbeats, bass envelope, glow or neon pulse (step 13), background flash, zoom burst,
  RGB split, glitch.
- Carry `drops.txt` into a clip. `clip` copies lyrics only; a clip's drops are written in the
  clip's own time.
- Bundle Anek Devanagari. The lyrics are Latin Hinglish; any Devanagari character falls back to
  the existing fallback fonts (Nirmala UI), unshaped as in every theme until step 14.
- Change the other six themes (their frames stay pixel-identical), the default theme
  (`soft-romantic-v2`, H-015), `words.json`, `beats.json`, alignment, or `lyrics.txt` casing
  and text.

**Hard Rules:**
- **Red line 1:** a word's first ink is on the frame of `start − lead` and never earlier. Its
  pop completes no later than the frame of `end − lead`. Its pill is on from the frame of
  `start − lead` through the frame before `end − lead` and on no other frame. A beat bump or
  drop shake never shows a word before its first frame, never removes a shown word, and never
  shows the pill on a word outside its span. An untimed (flagged) word never pops and never gets
  the pill.
- **Red line 2:** every drawn string is the `words.json` text. Anton keeps real lowercase, so
  casing matches `lyrics.txt`. Only `*` markers are hidden (H-009).
- Styling rules (plan): overshoot at most 10%, two fonts at most, no hue-120 green, a stroke
  legibility layer, and every drawn pixel inside x 60–960, y 380–1540 in every frame,
  largest bump and shake included.

## 4. Core Design

### 4.1 Data flow

```
words.json ─┐
lyrics.txt ─┼─► beat-pop renderer ─► render/beat-pop/overlay.mov + overlay_green.mp4 + preview.mp4
beats.json ─┤    (ensure_beats: computed once if missing)
drops.txt ──┘    (optional, owner-written)
```

The renderer reads `beats.json` only through `beats.ensure_beats`, and `drops.txt` only
through its reader. Nothing is written back to any input.

### 4.2 What the screen shows

- One lyric line at a time, wrapped into rows like every theme, centred in the lower-middle of
  the frame. A line appears when its first word is sung and leaves after a short hold past its
  last word, or earlier, so the next line's first word lands on an empty screen (the
  one-block-at-a-time life cycle Lofi and Cinematic share, D-021).
- **Pop:** each word springs in from about 60% scale to rest with `easeOutBack` over ~0.25 s
  (shrunk to the word's span when the word is shorter). It stays at rest, white with a black
  stroke, until the line leaves.
- **Pill:** a rounded mustard box sits behind the word being sung, and that word turns black.
  The pill appears with the word (it pops with it) and is gone on the word's end frame, so in a
  gap between words no word has the pill. It does not slide between words: a slide would put
  the pill on a word before that word is sung.
- **Beat bump:** on the frame of `beat − lead`, the whole line (rows, words, pill) is at its
  peak scale (~1.05) about its own centre. It eases back to 1.0 over ~0.15 s. The next beat
  starts a new bump even if the last one has not settled. With no line on screen, a beat shows
  nothing.
- **Drop shake:** on the frame of `drop − lead`, the line peaks at a bigger scale (~1.12) and
  starts shaking. The offsets shrink to zero over ~0.5 s. A drop with no line on screen shows
  nothing, and the report says so.
- **Exit:** the line fades and shrinks slightly (~0.2 s).

### 4.3 `drops.txt`

- Optional file `songs/<song>/drops.txt`: one time per line in the `clip` time format (`45`,
  `0:45`, `1:05.5`). Blank lines and `#` comments are ignored.
- Each time snaps to the nearest beat in `beats.json`. With no beats, it is used as written,
  with a note.
- Read at render time; editing it and re-rendering needs no re-align and no re-detection.

### 4.4 Beats in the render

- `beats.ensure_beats(song_dir)`: reuse `beats.json`, or compute and save it once (D-022).
- The same `lead_s` as words applies to beats and drops, so bump, shake and voice all land the
  same way.
- The report records: tempo, beat count, `beats.json` computed or reused, each drop
  (`0:45 → 45.12 s`), and notes.

### 4.5 Start values (all in `theme.py`; the owner tunes them after the preview)

| Value | Start |
|---|---|
| Font | Anton Regular, 110 px (min 72) |
| Text / stroke | white `#FFFFFF` / black `#000000`, stroke ≈ 5% of the word's size (4–6 px) |
| Pill / sung word | mustard `#FFC107` / black `#000000`; corner radius and padding from the word's size |
| Shadow | black, 40%, small, as a second legibility layer |
| Pop | from 0.6× to rest, `easeOutBack`, 0.25 s |
| Beat bump | peak 1.05×, back over 0.15 s |
| Drop | peak 1.12×, shake ±14 px, settles over 0.5 s |
| Hold / exit | 0.8 s / 0.2 s |
| Layout box | narrow enough that the line at 1.12× plus the shake stays in the safe zone (exact width in `/plan`) |

### 4.6 Emphasis and fonts

Marked words are drawn at `emphasis_scale` × their line's size (H-013), including the pill
around them. Fonts come through `layout.word_fonts` like every theme, so a character Anton lacks
falls back instead of drawing tofu.

### 4.7 Render checks

The existing output checks (sizes, frame rate, frame count, alpha, audio) run as for every theme.

- **Pop sync:** from the decoded overlay, each timed word has no ink on the frame before
  `start − lead` and has ink on that frame. It is complete by the frame of `end − lead`.
- **Pill sync:** the pill colour is present at each timed word's place on its span's frames
  (checked on its first and last frames at least), and absent on the frame before
  `start − lead` and on the frame of `end − lead`.
- **Beat sync:** for each beat while a line is on screen and not leaving, the line's drawn size
  on the beat frame is larger than on the frame before, and not smaller than on the frame after.
  A beat that cannot be read that way (a word popping in on the same frame, a line change) is a
  report note, never a silent pass.
- **Safe zone:** no drawn pixel outside x 60–960, y 380–1540 in any frame, bumps and shakes
  included.

### 4.8 Test songs

`khidki_s2` (14 s), `khidki_s2_em` (marked words), `khidki_full` (172 s, 143.55 BPM, beats
checked against its drums in step 11) with a hand-written `drops.txt`. If the owner adds a
Punjabi / party song, the look is also judged on it.

## 5. Edge Cases & Error Handling

| Situation | Behaviour |
|---|---|
| No `beats.json` | Computed once by `ensure_beats`; report says "computed" |
| `beats.json` invalid (a broken hand edit) | Render refuses with the beats error; nothing rendered |
| No beats (tempo 0) | No bumps; drops used as written; report note |
| librosa missing | Only `beat-pop` refuses, with the install line; other themes unaffected |
| No `drops.txt` | No shake; nothing reported |
| A `drops.txt` line that is not a time | Render refuses, naming the file and line number |
| A drop outside the song | Render refuses, naming the line |
| Drop with no line on screen | Nothing shown; report note with the time |
| Two drops closer than the shake | The later one restarts the shake |
| Beats faster than the bump decay | Each beat restarts the bump from its peak |
| Beat on the frame a word pops in | Both apply (scales multiply); pop sync still holds |
| Word shorter than the pop | Pop shrunk to the word's span: at rest by `end − lead` |
| Consecutive words (no gap) | The pill leaves one word and appears on the next on the same frame |
| Flagged word, `--allow-flagged` | Shown at rest when its line appears; never pops, never gets the pill (as every theme) |
| Line with no timed word | Not shown; listed in the report (existing behaviour) |
| Marked word at 2.0× plus drop bump | Layout box keeps it inside the safe zone; the check proves it |
| Clip folder | Beats from the clip's own audio (step 11); `drops.txt` only if the owner writes one there |

## 6. Acceptance Criteria

1. **Theme choice:** `render songs/khidki_s2 --theme beat-pop` (and `make --theme beat-pop`)
   renders from the existing `words.json` into `render/beat-pop/`. `words.json` and
   `beats.json` are byte-identical after, and plain `render` still uses `soft-romantic-v2`.
2. **Other themes unchanged:** the six existing themes' frames are pixel-identical to `dev` on
   `khidki_s2` and `khidki_s2_em`.
3. **Pop (unit):** a word has no ink before its `start − lead` frame, has ink on it, is at rest
   by its `end − lead` frame (short words included), and its scale never exceeds 1.10× rest
   during the pop.
4. **Pill (unit):** the pill is under word *i* on exactly its span's frames, with the word
   black on it. It is under no word in a gap, never under a flagged word, and it jumps (no
   slide) between consecutive words.
5. **Bump and shake (unit):** the line's scale peaks on each beat frame while on screen, and is
   1.0 once settled with no beat. A drop gives the bigger peak and shake offsets that end within
   0.5 s. Nothing is drawn for a beat or drop with no line on screen.
6. **Drops (unit):** `drops.txt` with `45`, `0:45`, `1:05.5`, blanks and `#` comments reads
   correctly and snaps to the nearest beat. A bad line and an out-of-song time refuse with the
   line number. No file gives no drops.
7. **Render checks:** `render --theme beat-pop` on the three test songs, with a `drops.txt` on
   `khidki_full`, says **pass** in every `report.md`. Not vacuous: words drawn 5 frames early
   fail pop sync, a pill kept 5 frames past its word fails pill sync, bumps moved 3 frames off
   the beat fail beat sync, and a tight safe zone fails the zone check.
8. **Emphasis:** spec 06 AC5 (layout) passes for `beat-pop` at 1.5× and 2.0×.
9. **Text:** a box/text mismatch between the layout and `words.json` raises before drawing
   (red line 2 assertion).
10. **Speed:** `khidki_s2` beat-pop wall time ≤ 2× its `soft-romantic` wall time, same session.
11. **By ear and eye (owner):** in `preview.mp4` of `khidki_full` (or the owner's party song),
    the bumps land on the beat, the shake lands on the written drops, and the owner approves
    the look. Changes asked for become `theme.py` values.
12. **Gate:** `/gate` passes.

## 7. Choices made for the owner (object to any before `/plan`)

- **The pill jumps, it does not slide**, and it lasts exactly the word's aligned span. A slide
  (research §4) would put it on a word before that word is sung.
- **Bump peak on the beat frame, then decay.** An instant rise reads as a punch on the kick. A
  rise that led into the beat would start before it.
- **Beats and drops use the words' `lead_s`**, so the eye gets the bump at the same moment it
  gets the word.
- **No Anek Devanagari yet**: the lyrics are Latin, and Devanagari needs step 14's shaping to
  look right anyway. Nirmala UI stays the fallback, as in every theme.
- **Anton at 110 px**: condensed, so ~20–28 characters fit a row at a size that reads as hype
  (research §8: 96–125 px).
- **Shadow kept under the stroke**: stroke alone thins out on bright, busy footage (§8 standard
  social combo).
- **A drop with no line on screen shows nothing**: there is no text to shake, and a flash or
  zoom would be a new motion (out of scope).
