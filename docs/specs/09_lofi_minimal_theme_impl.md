# Plan: Lofi Minimal Theme
**Spec:** `docs/specs/09_lofi_minimal_theme.md` (v1.0.1, approved by owner 2026-09-27)
**Branch:** `feature/lofi-minimal-theme` · **Decisions:** H-016, H-012, H-013, H-009, D-017, D-018
**Work split:** one developer, in the build order of §11 (no agents).

> **As built (2026-09-27), where it differs from the text below:**
> - `LofiCache` holds one line's looks, image and layer (one line at a time), not per-line dicts.
> - `line_image` pastes each word's look whole, in any order: at 76 px the word gap (~34 px) and
>   the gap between rows' ink (~49 px) exceed the shadow's reach (~14 px), so no shadow lands on
>   another word's ink and no two-pass compose is needed.
> - The fade into current eases out (cubic) and the fade to sung is a smoothstep.
> - `tests/test_lofi.py` uses its own exact `t(frame)`: `tests.test_karaoke.t` rounds to 4
>   decimals, which moves most frames one earlier.
> - Sizes: `render/lofi.py` 307 lines (target was 280), `check.py` 354 (the `_colour_alpha`
>   extraction); both near the ~300 guideline, left for an optional `chore/` split.

## 1. Files

| Action | File | Reason |
|---|---|---|
| MODIFY | `src/lyric_engine/theme.py` | motion `"lofi"`; `tracking` (every theme, default 0); lofi-only fields; `LOFI_MINIMAL`, `LOFI_TYPEWRITER`; `THEMES` |
| MODIFY | `src/lyric_engine/layout.py` | tracking: `FontSet.units()`, tracked `advance`/`space`/`word_mask`; `typeable()` |
| CREATE | `src/lyric_engine/render/lofi.py` | line life cycle, colour states, letter frames, sprites, frame composition, readability |
| CREATE | `src/lyric_engine/render/lofi_check.py` | colour-state and typing sync samples; the lofi frame checks |
| MODIFY | `src/lyric_engine/render/check.py` | extract the colour + alpha decode from `_karaoke_checks`; `_alpha_sync(samples=...)`; dispatch `"lofi"`; report wording |
| MODIFY | `src/lyric_engine/render/__init__.py` | dispatch `theme.motion == "lofi"` |
| CREATE | `fonts/Poppins-Light.ttf` | the theme font (SIL OFL 1.1; `fonts/OFL.txt` already covers the Poppins family) |
| CREATE | `tests/test_lofi.py` | theme, colour states, letters, life cycle, frames, end-to-end, CLI |
| MODIFY | `tests/test_layout.py` | tracking tests; emphasis tests also over both lofi themes (AC8) |
| MODIFY | `tests/test_karaoke.py` | `THEMES` name list gains the two lofi themes |
| MODIFY | `CLAUDE.md`, `docs/development_plan.md`, `docs/pending_work.md`, `docs/session_log.md`, `docs/decision.md` | theme list, `lofi` modules, status, D-020 |

`frames.py`, `timeline.py`, `karaoke.py`, `focus.py`, `encode.py`, `cli.py` (choices come from
`THEMES`), `timing.py`, `align.py`, `workflow.py`: no change.

## 2. Architecture Decisions

1. **A fourth motion family, `"lofi"`, in its own module `render/lofi.py`; the typewriter is a
   theme flag, not a fifth family.** Both themes share the line life cycle, colour states,
   sprites and checks; only what a word draws before and during its current window differs
   (H-016: two themes, one look). Rejected: branches in `karaoke.py` (at 312 lines, and it is
   about fills; spec: Pop Karaoke pixel-identical) or `focus.py` (reveal/glow family).
2. **Per-word frames come from `timeline.word_plans`** (`reveal` = frame of `start − lead`,
   `end` = frame of `end − lead`). The colour state and the letter frames are functions of those
   frames and of the word's own seconds only (red line 1 by construction).
3. **Colour state = (opacity, mix).** `mix` 0 = `text_rgb` (upcoming and sung), 1 = `accent_rgb`
   (current). A word's look sprite is shadow + glyph composed **at full opacity in the mixed
   colour, then faded** by the alpha LUT. Solid ink pixels so keep the exact state colour even at
   35% opacity, which is what makes the colour check readable on the upcoming frame. Rejected:
   cross-fading two glyph sprites (the shadow darkens semi-transparent ink and the check would
   read it as colour).
4. **Short words:** the fade into current lasts `min(ceil(current_in_s × fps), end − reveal)`
   frames (0 = current at once), so every timed word is fully current on its `end` frame (spec
   v1.0.1 §4.3). The fade to sung (smoothstep over `sung_in_s`) always starts from mix 1.
5. **Line life cycle on frames, one line at a time** (spec §4.2). With `F` = the next line's
   first current frame and `E` = this line's last end frame, the frames between them,
   `A = F − 1 − E`, are split as exit then entrance. The `− 1` keeps frame `F − 1` clean: the
   next line is already at rest there (`lofi-minimal`) or the screen holds no other line
   (`lofi-typewriter`), so its first word's "before" frame is always readable by the check.
   This is D-020.
6. **Tracking lives in `layout.FontSet`**, so the mask that measures a word is the mask that
   draws it (red line 2, `checked_mask`). Tracking is `theme.tracking × FontSet.size`, so a
   marked word gets tracking at its own size. Units: each Latin character drawn by the primary
   font is its own unit; a run of non-Latin primary characters, or any fallback-font run, is one
   unit (emoji sequences and Devanagari are never split). Units sit `tracking` px apart, with
   kerning kept inside a run by the research formula `x_i = getlength(run[:i+1]) −
   getlength(run[i])` (§4 of the research). A word gap becomes `space + 2 × tracking`.
   **With tracking 0 every method runs exactly today's code path** (AC2).
7. **Typewriter bands.** A typeable word (every unit a single Latin primary character) is cut
   into one vertical band per letter: band `i` spans sprite columns from the middle of the
   tracking gap before letter `i` to the middle of the gap after it; the first band starts at
   the sprite's left edge and the last ends at its right edge. The bands tile the sprite, so a
   fully typed word is pixel-identical to the whole word (AC4). A letter's shadow tail can reach
   ~3 px into the next band; that faint spill is accepted (a shadow, never ink, and far below the
   check's alpha drop). A non-typeable word is one band.
8. **Sprites reuse `karaoke.sprite_pad`** (`stroke_frac` 0 → shadow blur + offset only) and
   `frames.checked_mask`, `_solid`, `_scaled`. `lofi.build_sprites` keeps the glyph **mask**
   (not a coloured sprite), since the colour is chosen per state. Rejected: extending
   `karaoke.build_sprites` (it needs a stroke colour and would put Pop Karaoke's output at risk).
9. **Line image, then line fade and integer rise** (as `focus.line_image` / `_layer`). No scale
   and no blur, so no premultiplied transform; the line layer is the line image faded by the
   LUT and pasted `round(dy)` px lower or higher. At rest it is pasted untouched.
10. **Checks.** `lofi-minimal` needs colour and alpha per sample: `_karaoke_checks`' decode
    (one colour plane stacked on alpha) moves into a shared helper that returns both means; Pop
    Karaoke's results are unchanged. `lofi-typewriter` needs alpha only: `_alpha_sync` takes an
    optional `samples` list. The lofi sampling lives in `render/lofi_check.py` because
    `check.py` is at 331 lines (CLAUDE.md: ~300). `check_outputs` imports it inside the function
    (`lofi_check` imports helpers from `check`, so a top-level import would be circular).
11. **Colour channel for the check:** the channel where `text_rgb` and `accent_rgb` differ most
    (green, 239 vs 198: 41 levels). Thresholds are shares of that span: current ≥ 75%, upcoming
    ≤ 25%. A lofi theme whose colours differ by less than 32 levels is refused by the check with
    a clear message (Pop Karaoke's rule, with a lower floor for the pastel palette).
12. **Report notes come from the plan.** `plan_lofi` records per-line notes (a cut, a word that
    lost frames, a word typed whole); `lofi_check.lofi_checks` appends them to `result.notes`,
    once each. `render()` needs no new code path for notes.

## 3. Data Structures

### 3.1 `theme.py`

| Field | Type, default | Used by | Enforces |
|---|---|---|---|
| `tracking` | `float = 0.0` | layout, every theme | extra px between units / word size; 0 = today (spec §3 Will NOT) |
| `upcoming_opacity` | `float = 0.35` | lofi | upcoming state (spec §4.1) |
| `current_in_s` | `float = 0.12` | lofi | fade into current (§4.3) |
| `sung_in_s` | `float = 0.4` | lofi | fade into sung (§4.3) |
| `exit_rise_px` | `int = 10` | lofi | exit rise (§4.2) |
| `typewriter` | `bool = False` | lofi | `lofi-typewriter` behaviour (H-016) |
| `type_stagger_s` | `float = 0.06` | lofi | per-letter stagger cap (§4.4) |
| `letter_fade_s` | `float = 0.1` | lofi | letter fade (§4.4) |

Reused, with lofi meanings noted in comments: `accent_rgb` (current colour), `text_rgb`
(upcoming and sung colour), `enter_s` (entrance, 0.6), `preroll_s` (0.9), `rise_px` (entrance
rise, 20), `hold_s` (1.5), `fade_out_s` (exit, 0.5).

`__post_init__` adds: `motion == "lofi"` needs `accent_rgb`; for lofi without typewriter,
`round(preroll_s × fps) > ceil(enter_s × fps)` (a line can rest before its first word);
`tracking ≥ 0`. `MOTIONS` gains `"lofi"`.

```
LOFI_MINIMAL = Theme("lofi-minimal", motion="lofi", font=REPO_FONTS / "Poppins-Light.ttf",
    font_size=76, min_font_size=52, tracking=0.10, max_width=860, center_x=510,
    safe_zone=(60, 380, 960, 1540), text_rgb=(245, 239, 230), accent_rgb=(247, 198, 208),
    shadow_rgb=(43, 42, 51), shadow_alpha=0.5, shadow_radius=6, shadow_offset=(0, 2),
    enter_s=0.6, preroll_s=0.9, rise_px=20, hold_s=1.5, fade_out_s=0.5)
LOFI_TYPEWRITER = replace(LOFI_MINIMAL, name="lofi-typewriter", typewriter=True)
THEMES: (SOFT_ROMANTIC, SOFT_ROMANTIC_V2, POP_KARAOKE, LOFI_MINIMAL, LOFI_TYPEWRITER)
```

`DEFAULT_THEME` unchanged (H-015). `max_width` 860 is a start value: the safe-zone check is the
guard (tune the width, never the check).

### 3.2 `render/lofi.py`

```
@dataclass
class LofiLine:
    layout: LineLayout
    words: list[WordPlan]          # from timeline.word_plans; build_sprites reads .box/.text
    letters: dict[int, tuple[int, ...]]   # typewriter: word index -> letter start frames
    first_cur: int                 # earliest reveal of its timed words
    last_end: int                  # latest end of its timed words
    settled: int                   # last_end, or (typewriter) its last letter's fade end if later
    enter: int = 0                 # first visible frame
    rest: int = 0                  # first frame at rest (full opacity, no rise)
    leave: int = 0                 # exit starts (never before settled)
    stop: int = 0                  # first frame no longer visible (exclusive)
    notes: list[str] = field(default_factory=list)   # report notes (decision 12)

LSprites = dict[int, tuple[Image.Image, Image.Image, int, tuple[int, ...]]]
# word index -> (under: shadow RGBA, glyph "L" mask, pad, band edges in sprite x: 0 ... width)

class LofiCache:
    looks: dict[tuple, Image.Image]    # (word, opacity level, mix level[, letter levels]) -> sprite
    images: dict[int, tuple[tuple, Image.Image]]           # line -> (look key, line image)
    layers: dict[int, tuple[tuple, Image.Image, tuple[int, int]]]
    line: int | None                   # the visible line; everything is dropped when it changes
```

## 4. Function Specifications

### `layout.py`

- `FontSet.__init__`: adds `self.tracking = theme.tracking * size` (float px). `self.space =
  primary.getlength(" ") + 2 * self.tracking` only when tracking > 0 (else today's line).
- `FontSet.units(text) -> list[tuple[str, ImageFont.FreeTypeFont, float]]`: each unit's
  string, font and x at pad 0 (decision 6). Calls `runs()`. Raises `LayoutError` as `runs()`.
- `FontSet.advance(text) -> float`: tracking 0 → unchanged; else last unit's x + its
  `getlength`.
- `FontSet.typeable(text) -> bool`: every unit is one character, drawn by the primary font, in
  Latin (`ord < 0x250`, `0x1E00-0x1EFF`, or `0x2000-0x206F` general punctuation).
- `word_mask(text, fonts, pad, stroke)`: tracking 0 → unchanged loop; else draws each unit at
  `pad + x`, same box size rule (`ceil(advance) + 2·pad`).
- `layout_line`, `_wrap`, `_balance`, `_place`: no change; they read `advance` and `space`.

### `render/lofi.py`

- `plan_lofi(doc, theme, n_frames, emphasis=frozenset(), layout_fn=None) -> tuple[list[LofiLine],
  list[int]]`: lines in time order with their life cycle and letter frames (§5.1). Calls
  `timeline.laid_out_lines`, `word_plans`, `letter_frames`.
- `letter_frames(w: dict, n: int, theme) -> tuple[int, ...]`: letter `i` at
  `max(0, _floor_frame(start − lead + i·s, fps))`, `s = min(type_stagger_s, (end − start) / n)`.
  Letter 0 equals `word_plans`' reveal; the last is ≤ the word's `end` frame.
- `colour_state(wp, n, theme) -> tuple[float, float]`: `(opacity, mix)` per §5.2.
- `letter_levels(frames, n, theme) -> tuple[int, ...]`: per letter `round(ramp((n − f) /
  ceil(letter_fade_s × fps)) × LEVELS)`.
- `line_state(ll, n, theme) -> tuple[float, float]`: `(opacity, dy)`; `(0, 0)` off screen,
  exactly `(1.0, 0.0)` at rest (§5.3).
- `readable(lines, ll, m, theme) -> bool`: `line_state(ll, m) == (1.0, 0.0)` (at rest; the
  first exit frame still is), or (typewriter and `m < ll.enter`); and no other line of `lines`
  has opacity > 0 on `m` (only a cut leaves one there, decision 5).
- `build_sprites(lines, theme) -> LSprites`: per word `checked_mask(text, box, fonts, pad)`
  (red line 2), shadow from the mask as `frames.build_sprites` does, band edges from
  `fonts.units` when `theme.typewriter and fonts.typeable(text)`, else `(0, width)`.
- `word_look(ll, wp, n, theme) -> tuple`: the look key: `(o_level, m_level)` or, while typing,
  `(LEVELS, m_level, letter levels)`; `None` when nothing is drawn.
- `look_sprite(sprites, index, key, theme, cache) -> Image.Image`: §5.4.
- `line_image(ll, sprites, n, theme, cache) -> tuple[Image.Image, tuple, int, int]`: every
  word's look sprite on one canvas (words never overlap, so order is free); cached on the key.
- `frame_parts(n, lines, sprites, theme, cache) -> list`: the visible line (at most one) as a
  faded, shifted layer through `frames.band_parts`.

### `render/lofi_check.py`

- `lofi_checks(result, lines, theme, n_frames) -> list[str]`: appends every line's notes to
  `result.notes`; then `_state_checks` (`lofi-minimal`) or `check._alpha_sync(..., samples=
  _typing_samples(...))` (`lofi-typewriter`).
- `_state_checks(result, lines, theme, n_frames) -> list[str]`: §5.5.
- `_typing_samples(result, lines, theme) -> list[check._Sample]`: per typeable-or-whole timed
  word: `on` = last letter frame + letter fade frames, `before` = reveal − 1 (None at 0); a word
  whose `on` or `before` frame is not `readable` becomes a note.

### `render/check.py`

- `_colour_alpha(result, theme, c, wanted) -> tuple[dict, list, int, str | None]`: extracted
  from `_karaoke_checks`: one decode of plane `c` stacked on alpha; returns per `(label, kind)`
  `(colour mean, alpha mean)`, the safe-zone frames outside, the decoded count and an error.
  `_karaoke_checks` then reads only the colour mean: its results are unchanged.
- `_alpha_sync(result, lines, theme, n_frames, samples=None)`: `samples` given → used as is.
- `check_outputs`: `theme.motion == "lofi"` → `from .lofi_check import lofi_checks`.
- `write_report`: frame-check line for lofi: `"colour-state check of N timed word(s) on the
  overlay's colour and alpha"` or `"typing check of N timed word(s) on the overlay's alpha"`.

### `render/__init__.py`

- `render()`: `elif theme.motion == "lofi": lines, skipped = lofi.plan_lofi(...)`; `sprites,
  cache, parts = lofi.build_sprites(lines, theme), lofi.LofiCache(), lofi.frame_parts`.

## 5. Logic Flow

### 5.1 `plan_lofi`

1. `rows, skipped = laid_out_lines(doc, theme, layout_fn, emphasis)`.
2. Per row: `wps = word_plans(words, lay, theme)`; timed = reveal not None; `first_cur`,
   `last_end` from timed. Typewriter: per timed word, `n` = unit count if `typeable` else 1;
   `letters[i] = letter_frames(w, n, theme)`; `settled = max(last_end, max over its timed
   words of letters[i][-1] + ceil(letter_fade_s·fps))`, so a line never fades while a letter is still fading in (else
   `settled = last_end`: the fade into current ends by `end`, §5.2); a non-typeable word adds the note
   `word i "text" (line L): typed whole (non-Latin or fallback-font characters)`.
3. Sort by `(first_cur, line)`.
4. Frames: `Ein = 0 if typewriter else ceil(enter_s·fps)`, `P = 0 if typewriter else
   round(preroll_s·fps)`, `H = ceil(hold_s·fps)`, `X = round(fade_out_s·fps)`.
5. First line: typewriter → `enter = rest = first_cur`. Else if `first_cur − 1 − Ein < 0` →
   `enter = rest = 0` (at rest from frame 0); else `enter = max(0, first_cur − P)`,
   `rest = enter + Ein`.
6. For each line `k` with a next line (`F = nxt.first_cur`, `E = k.settled`, `A = F − 1 − E`):
   - if `A ≥ X + Ein`: `k.stop = min(E + H + X, F − 1 − Ein)`; `k.leave = k.stop − X`;
     next: typewriter → `enter = rest = F`; else `enter = max(F − P, k.stop)`, `rest = enter + Ein`.
   - elif `A ≥ 2`: shrink: `x = min(A − (1 if Ein else 0), max(1, round(A·X / (X + Ein))))`,
     `e = A − x`; `k.leave = E`, `k.stop = E + x`; next `enter = k.stop`, `rest = enter + e`
     (typewriter: `enter = rest = F`).
   - else (cut): `k.leave = k.stop = max(F, k.enter)`; next `enter = rest = F`; `k.rest =
     min(k.rest, k.stop)`; note `line L: cut, not faded (the next line starts N frame(s) after
     its last word ends)`; if `F ≤ E`, also note per word of `k` whose `end ≥ F`: `word i
     "text" (line L): its last E − F + 1 frame(s) are not shown (sung back to back)`.
7. Last line: `stop = min(settled + H + X, n_frames)`, `leave = stop − X`.
8. Every line: `stop = min(stop, n_frames)`; `leave = min(max(leave, min(settled, stop)),
   stop)`; `rest = min(rest, stop)`.

### 5.2 `colour_state(wp, n, theme)`

1. Untimed: typewriter → `(1, 0)`; else `(upcoming_opacity, 0)`.
2. `n < reveal` → `(upcoming_opacity, 0)` (typewriter draws nothing there: its letters are 0).
3. `fi = min(ceil(current_in_s·fps), end − reveal)`; `p = 1 if fi == 0 else
   ease_out_cubic((n − reveal) / fi)`.
4. `n < end` → `(u + (1 − u)·p, p)`; `n ≥ end` → `q = smoothstep((n − end) / (sung_in_s·fps))`,
   `(1, 1 − q)`. At `n == end`, `q = 0`: fully current on the end frame (spec §4.3).

### 5.3 `line_state(ll, n, theme)`

1. Off screen (`n < enter` or `n ≥ stop`) → `(0, 0)`.
2. `n < rest` → `e = ease_out_cubic((n − enter) / (rest − enter))`: `(e, rise_px·(1 − e))`.
3. `n ≥ leave` → `x = ease_in_quad((n − leave) / max(1, stop − leave))`:
   `(1 − x, −exit_rise_px·x)`.
4. Else `(1.0, 0.0)`.

### 5.4 `word_look` and `look_sprite`

1. `o, m = colour_state(...)`; `ml = round(m·LEVELS)`.
2. `lofi-minimal`: key `(round(o·LEVELS), ml)`.
3. Typewriter, timed: levels = `letter_levels(letters[i], n)`; all 0 → `None`; all `LEVELS` →
   `(LEVELS, ml)` (the whole word, shared with every later frame); else `(LEVELS, ml, levels)`.
   Untimed → `(LEVELS, 0)` from the line's first frame.
4. `look_sprite`: base = `alpha_composite(under, _solid(mix_rgb(text, accent, ml), mask))`,
   cached as `(index, LEVELS, ml)`; opacity level < LEVELS → `base` with alpha through
   `_LUTS[level]`; letter levels → a blank sprite with each band `[e_j, e_j+1)` of `base`
   pasted through `_LUTS[level_j]`. `mix_rgb` rounds each channel of the lerp.

### 5.5 `_state_checks` (`lofi-minimal`)

1. `c` = channel of max `|text − accent|`; span < 32 → return `["state: accent ... too close
   ... to check the colour states"]`.
2. Per timed word with ink (`check._ink`): `fi` as §5.2; `on = reveal + fi`; `held = end − 1`
   if `end − 1 > on` else None; `before = reveal − 1` if `reveal > 0` else None. Any of these
   frames not `readable` → note `word ...: its line was not at rest on frame K, so it was not
   read (sung back to back)` and skip the word.
3. `wanted` from samples `(on, before)` and `(held)`; `_colour_alpha(result, theme, c, wanted)`.
4. Fail when: alpha(on) < `SYNC_ON_MIN`; current share at `on` or `held` < 0.75; at `before`,
   current share > 0.25 or alpha > alpha(on) − `SYNC_DROP_MIN`. Messages start `state:`.
5. Safe-zone frames outside → `check._zone_failure`.

## 6. Edge Case Implementation Map

| Spec edge case | Mechanism | Location |
|---|---|---|
| Lyrics not in lowercase | nothing changes case; `checked_mask` asserts the text | `frames.checked_mask` |
| Next line due before `hold` ends | `k.stop = min(E + H + X, F − 1 − Ein)` | `plan_lofi` step 6 |
| Lines sung back to back | cut branch; notes per lost word | `plan_lofi` step 6 |
| Long instrumental gap | natural stop `E + H + X`; next enters at `F − P` | `plan_lofi` step 6 |
| First word near 0:00 | `enter = rest = 0` | `plan_lofi` step 5 |
| Word shorter than one frame | `end = reveal` → `fi = 0`; letters share frames | `colour_state`, `letter_frames` |
| Word shorter than the fade-in | `fi = min(Fi, end − reveal)` | `colour_state` step 3 |
| Non-Latin / fallback word, typewriter | `typeable` false → one band, one letter frame; note | `plan_lofi` step 2, `build_sprites` |
| Marked word on a shrunk line | layout unchanged; tracking at the word's size | `layout.FontSet`, `word_fonts` |
| Untimed word, `--allow-flagged` | `colour_state` step 1; excluded from `first_cur`/`last_end` and checks | `lofi.py`, `lofi_check.py` |
| Untimed word, no flag / line with no timed word / line too long | unchanged | `load_for_render`, `laid_out_lines`, `layout` |
| Poppins Light missing | `FontSet` raises `theme font not found: ...` | `layout.FontSet.__init__` (unchanged) |
| Dim words on the green mp4 | no mechanism; known limit, alpha `.mov` exact | — |

## 7. File Layout

`render/lofi.py`, in order: module docstring (spec, red lines, reuse) → imports → `# --- Data`
(`LofiLine`, `LSprites`, `LofiCache`) → `# --- Timeline` (`letter_frames`, `plan_lofi`,
`colour_state`, `letter_levels`, `line_state`, `readable`) → `# --- Sprites` (`build_sprites`,
`mix_rgb`) → `# --- Frames` (`word_look`, `look_sprite`, `line_image`, `frame_parts`). Target
≤ 280 lines.

`render/lofi_check.py`: docstring → imports → constants (`STATE_CURRENT_MIN = 0.75`,
`STATE_BEFORE_MAX = 0.25`, `STATE_SPAN_MIN = 32`) → `lofi_checks` → `_state_checks` →
`_typing_samples`. Target ≤ 120 lines.

`tests/test_lofi.py`: helpers (reuse `tests.test_render.make_song`, `word`;
`tests.test_karaoke.low_layout`, `t`) → `ThemeTest` → `ColourStateTest` (AC3) →
`LetterTest` (AC4) → `PlanLofiTest`, `LineStateTest` (AC5) → `FramesTest` (AC4 pixels, AC9) →
`LofiRenderTest` (AC1, AC7) → `CliThemeTest` (AC1).

## 8. Dependencies

- No new packages. `lofi.py` imports `math`, `dataclasses`, `PIL.Image`, `ImageFilter`; from
  `..layout` `LineLayout`, `word_fonts`; `..theme` `Theme`; `.timeline` `WordPlan`,
  `_ceil_frame`, `_floor_frame`, `laid_out_lines`, `word_plans`; `.karaoke`
  `ease_out_cubic`, `ease_in_quad`, `smoothstep`, `sprite_pad`; `.frames` `_LUTS`, `LEVELS`,
  `_scaled`, `_solid`, `band_parts`, `checked_mask`.
- `lofi_check.py` imports `lofi` and from `.check` `_Sample`, `_ink`, `_wanted`,
  `_colour_alpha`, `_alpha_sync`, `_zone_failure`, `SYNC_ON_MIN`, `SYNC_DROP_MIN`. `check.py`
  imports `lofi_check` inside `check_outputs` only (no cycle at import time).
- Poppins Light: `https://github.com/google/fonts/raw/main/ofl/poppins/Poppins-Light.ttf`
  (same source family as the bundled SemiBold, D-018).
- Conflicts found: `check._karaoke_checks` holds the colour decode inline (extract first, §11
  step 2); `tests/test_karaoke.py:60` pins the `THEMES` list; `layout.py`'s docstring says the
  dataclass fields must not change (they do not: `FontSet` is not a dataclass).
- `CLAUDE.md` is 106 lines: room for the theme list and the `lofi` module lines.

## 9. Hard Boundaries

- [x] No colour state, letter frame, entrance, exit or cut changes `WordPlan.reveal` / `end`.
- [x] No letter gets a timestamp from anywhere but its word's own start/end (red line 1).
- [x] A word turns current on its reveal frame and is fully current on its end frame.
- [x] Every drawn string goes through `checked_mask` with the tracked mask (red line 2).
- [x] Nothing lowercases, uppercases or substitutes text.
- [x] `soft-romantic`, `soft-romantic-v2` and `pop-karaoke` frames stay byte-identical (AC2);
      tracking 0 runs today's layout code paths.
- [x] At most one lyric line visible in any frame; a line never leaves before `settled`.
- [x] No glow, stroke, blur, backplate, scale, caret or beat input in the lofi themes.
- [x] The safe-zone check is never loosened; tune `max_width` instead.
- [x] `render()` never calls alignment; nothing is written outside `render/<theme>/`.

## 10. Acceptance Criteria (runnable)

`$PY` = `venv/Scripts/python`; song runs use the owner's `songs/khidki_s2`, `songs/khidki_s2_em`
and the new `songs/khidki_s2_lofi` (§11 step 7).

1. **Theme choice:** `$PY -m lyric_engine.cli render songs/khidki_s2 --theme lofi-minimal` and
   `--theme lofi-typewriter` → exit 0, `render/lofi-minimal/` and `render/lofi-typewriter/` each
   hold `overlay.mov`, `overlay_green.mp4`, `preview.mp4`, `report.md` with `Theme: <name>`;
   `words.json` hash unchanged. `make songs/khidki_s2 --theme lofi-minimal` → exit 0. Plain
   `render` → `render/soft-romantic-v2/`. Unit: `$PY -m unittest tests.test_lofi -k Cli` → `OK`.
2. **Other themes untouched:** before any source edit, `git worktree add <scratch>/dev_tree dev`;
   `<scratch>/frame_hashes.py` hashes `frame_parts` bytes of `soft-romantic`,
   `soft-romantic-v2` and `pop-karaoke` at every 10th frame of `khidki_s2` and `khidki_s2_em`;
   run with `PYTHONPATH=<scratch>/dev_tree/src` → `dev.json`, then on the branch →
   `branch.json`; `fc dev.json branch.json` → no differences.
3. **Colour states:** `$PY -m unittest tests.test_lofi -k ColourState` → `OK` (mix 0 on
   `reveal − 1`, 1 from `reveal + fi` through `end`, 0 at `end + ceil(sung_in_s·fps)`; a 1-frame
   word is fully current on its end frame; a flagged word `(0.35, 0)` on every frame).
4. **Typing:** `$PY -m unittest tests.test_lofi -k Letter` → `OK` (letter 0 == reveal; strictly
   ordered in time; last frame ≤ end and last time < `end − lead`; stagger 0.06 s or `(end −
   start)/n`; a fully typed word's sprite equals the whole word's bytes; a Devanagari or emoji
   word has one band on its reveal frame; a flagged word draws whole, never types).
5. **Line life cycle:** `$PY -m unittest tests.test_lofi -k PlanLofi -k LineState` → `OK` (≤ 1
   line visible every frame; `leave ≥ settled ≥ last_end`; `lofi-minimal` at rest on `first_cur − 1`;
   `(1.0, 0.0)` exactly at rest; hold, early leave, shrink and cut on synthetic timings incl.
   back to back, an instrumental gap and a first word at 0:00; cut lines carry notes).
6. **Tracking:** `$PY -m unittest tests.test_layout -k Tracking` → `OK` (box == tracked
   measure; drawn mask == measured mask; tracking 0 == today's `advance`, `space`, mask bytes;
   emoji sequence and Devanagari runs stay one unit).
7. **Render checks:** `render --theme lofi-minimal` and `--theme lofi-typewriter` on
   `khidki_s2`, `khidki_s2_em` and `khidki_s2_lofi` → every `report.md` says `**pass**`. Not
   vacuous: `$PY -m unittest tests.test_lofi -k LofiRender` → words shifted 10 frames late fail
   with `state:` (`lofi-minimal`) and `sync:` (`lofi-typewriter`); a safe zone of
   `(60, 380, 960, 1150)` fails with `safe zone:`.
8. **Emphasis:** `$PY -m unittest tests.test_layout -k Emphasis` → `OK`, now over both lofi
   themes too, at 1.5 and 2.0.
9. **Text:** `$PY -m unittest tests.test_lofi -k Frames` → a box/text mismatch raises
   `AssertionError` from `lofi.build_sprites` before drawing.
10. **Speed:** wall time in `songs/khidki_s2/render/lofi-*/report.md` ≤ 2 × the one in
    `render/soft-romantic/report.md` (all rendered on this branch, same session).
11. **Look:** the owner approves `songs/khidki_s2_lofi/render/lofi-minimal/preview.mp4` and
    `render/lofi-typewriter/preview.mp4`; changes asked for become `theme.py` values.
12. **Gate:** `/gate` → unit tests `OK`, alpha proof passes.

## 11. Build order

1. AC2 baseline: dev worktree + `frame_hashes.py` → `dev.json`, before any source edit.
   Download Poppins Light into `fonts/`.
2. Pure extraction: `check._colour_alpha` from `_karaoke_checks`; `_alpha_sync(samples=)` →
   full unit suite `OK`.
3. `layout.py` tracking + `TrackingTest` (AC6); AC2 hashes identical.
4. `theme.py` fields + both themes + `ThemeTest`; `test_karaoke` names; `test_layout` emphasis
   over the lofi themes (AC8; add `LONG_FOR` entries, shorter line if 76 px + tracking at 2x
   cannot fit 860 px).
5. `render/lofi.py` + unit tests (AC3, AC4, AC5, AC9).
6. `render/lofi_check.py`, `check.py` dispatch + report, `render/__init__.py` dispatch,
   end-to-end tests (AC1 unit, AC7 unit).
7. Test song: `songs/khidki_s2_lofi/` = `khidki_s2_em`'s `audio.wav` + its `lyrics.txt` in
   lowercase (written by hand, markers kept); `$PY -m lyric_engine.cli align songs/khidki_s2_lofi`.
8. Real runs: AC1, AC2, AC7, AC10; D-020 in `decision.md`; `CLAUDE.md` theme list and modules;
   gate; `/ship`; ask the owner for AC11.
