# Implementation Plan: Phonk Neon Theme
**Spec:** `docs/specs/13_phonk_neon_theme.md` v1.0.0 · **Branch:** `feature/phonk-neon-theme`
**Status:** Written with the spec in one run (H-020 flow).

## 1. Files

| File | Change |
|---|---|
| `fonts/PirataOne-Regular.ttf`, `fonts/OFL-PirataOne.txt` | New: the display face and its licence |
| `theme.py` | Motion `"phonk"`; fields `lit_rgb`, `unlit_rgb`, `pulse_low`, `pulse_s`, `split_px`, `split_s`, `split_rgb`; guards; `PHONK_NEON` in `THEMES` |
| `render/beatpop.py` | `plan_beatpop(..., ahead=False)` passed to `schedule`; Beat Pop unchanged |
| `render/phonk.py` | New: light level, pulse, split, line state, sprites, frame parts, `readable` |
| `render/phonk_check.py` | New: light sync, pulse sync, safe zone (one colour + alpha decode) |
| `render/__init__.py`, `render/check.py` | Dispatch `"phonk"` (shares Beat Pop's beats loader); report line |
| `tests/test_phonk.py` | New: AC3–AC8 |
| `CLAUDE.md`, docs | Theme list, architecture line |

`--theme` choices come from `THEMES`, so the CLI needs no change.

## 2. Details

### 2.1 Timeline (reuses Beat Pop)
`plan_beatpop(doc, theme, n, emphasis, beats, drops, ahead=True)` gives the lines, beat frames
and drop frames (words' lead applied, D-024) and the drop-with-no-line notes. With `ahead`, the
shared `schedule` shows each line `preroll_s` early with an `enter_s` entrance (as Lofi).

### 2.2 Light level of word `wp` at frame `n`
- Untimed: 0.0 (unlit) whenever its line shows.
- `n < reveal`: 0.0. Else `k = n − reveal`, `F = min(len(FLICKER), end − reveal)`:
  `FLICKER[k]` for `k < F`, else 1.0. `FLICKER = (1.0, 0.2, 1.0, 0.5, 1.0)`: full on the
  reveal frame, at rest by `end` (`k ≥ F` there).

### 2.3 Pulse, split, shake
- Pulse `p(n)`: latest beat `b ≤ n`, `d = n − b`, `D = ceil(pulse_s·fps)`:
  `pulse_low + (1 − pulse_low)·(1 − d/D)²` for `d < D`, else `pulse_low`; quantised to 1/32.
- Split `s(n)`: latest drop, `S = ceil(split_s·fps)`: `round(split_px·(1 − d/S)²)` for
  `d < S`, else 0.
- Shake and drop scale: `beatpop.accent` with `bump_scale = 1.0`, so beats never scale.

### 2.4 Line state
`(scale, dx, dy, opacity)`: `accent`; opacity `ease_out_cubic` over `enter..rest`, 1 at rest,
`1 − ease_in_quad` over `leave..stop` (Beat Pop's exit without its shrink).

### 2.5 Sprites (per word, built once)
Pad `P = max(3·glow_radius, sprite_pad)`, ≥ `split_px`. Masks: glyph (`checked_mask`), rim
(the `stroke_frac` outline blurred `shadow_radius`, × `shadow_alpha`, at `shadow_offset`), glow
(`screen(blur(glyph, R)·boost, blur(glyph, R/3)·boost)`, `R = glow_radius`).

### 2.6 Line image and frame
Line canvas = union of the words' padded sprite rects. Per line: one rim layer (all words). Per
light-level key: glow mask (`lighter` of each lit word's glow × its level) and core layer
(each word's glyph in `unlit + (lit − unlit)·level`). Per `(key, p, s)`: `glow_rgb` on
glow × `p`, then the rim (over the glow: D-025), then red copy of the cores' alpha shifted `−s` and cyan `+s`, then
the cores. Then `karaoke.transformed` (scale, shake, opacity) and `band_parts`. Caches: the
visible line's rim, word colour layers per level, last key's layers, last image, last layer.

### 2.7 Checks
- Light: per timed word with ink, `_Sample(on = reveal, before = reveal − 1)` when `readable`
  on both (line alone, `rest ≤ m < leave`, `accent == (1, 0, 0)`); else a note. Channel
  `c = argmax |lit − unlit|`; lit share ≥ 0.75 on `on`, ≤ 0.25 on `before`; alpha ≥
  `SYNC_ON_MIN` on `on`.
- Pulse: per beat `b` with `readable` on `b − 1, b, b + 1` and planned `p(b) − p(b − 1) ≥ 0.1`:
  steady words = level 1.0 on all three; changing = levels differ. Region = steady boxes grown
  by `2R`, minus changing boxes grown by `3R`; read if ≥ 200 px. Mean alpha: `a(b) > a(b − 1)
  + 1` and `a(b + 1) ≤ a(b) + 0.5`, else `"pulse: …"`. Note: "pulse check read N of M beats".
- Both via `check._colour_alpha` (one decode, safe zone included).

### 2.8 Theme values
Spec §4.4. `glow_radius 18`, `glow_boost 1.5`; rim `stroke_frac 0.04`, `shadow_alpha 0.85`,
`shadow_radius 2`, offset `(0, 1)` (first try: a soft 55% halo under the glow, D-025). Reach
measured on Pirata One: glow ≤ 31 px. Box 700 px about
x 510: worst side 160 − 700·0.03 − 14 − 12 − 31 = 82 ≥ 60.

## 3. Tests (`tests/test_phonk.py`)
Theme listed and guards; lighting (AC3); pulse peaks and rest (AC4); split and shake (AC5);
line ahead unlit and one line at a time (AC6); frame colours on a real frame; text assertion
(AC8); cache gives identical frames; end-to-end render passes, and late lights, shifted pulses
and a tight zone fail (AC7); `make --theme phonk-neon`.

## 4. Verification
Gate; frame hashes of the seven old themes vs the `dev` baseline (AC2); renders of
`khidki_s2`, `khidki_s2_em`, `khidki_full` (AC7, AC9); look frames for the owner (AC10).

## 5. Hard Boundaries (build checklist)

- [x] No word frame comes from anything but `word_plans`; beats and drops never touch
  `reveal`/`end` (red line 1). `phonk.py` assigns neither.
- [x] A word is unlit before its reveal frame and full on it; an untimed word is never lit.
- [x] Every drawn string goes through `checked_mask` (red line 2); Pirata One keeps real
  lowercase, no case change.
- [x] `words.json`, `beats.json`, `drops.txt` and `lyrics.txt` are read, never written, by render.
- [x] The other seven themes' frames are hash-identical to `dev` (AC2).
- [x] No hue-120 colour (the theme guard checks every `*_rgb`); one display font plus the shared
  fallbacks.
- [x] librosa is never imported by render unless `beats.json` must be computed (shared loader).
- [x] Emphasis at 1.5× and 2.0× lays out (`tests.test_layout`, `phonk-neon` in `ALL_THEMES`).

## 6. As built

- First look: a soft 55% black halo under the glow left lit words the least legible state on
  bright footage. The rim now sits over the glow (D-025).
- CLI: `main` sets `stdout` to `errors="replace"`: a drop note's "→" crashed a piped cp1252
  stdout after the render had finished (Beat Pop had the same latent bug).
- `khidki_s2`: 27.6 s vs Soft Romantic 21.8 s; pulse read 26 of 32 beats. `khidki_full`: 257.4 s,
  pulse read 97 of 119 beats, both drops snapped (27.91 s, 90.86 s).
