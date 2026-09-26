# Plan: Soft Romantic v2
**Spec:** `docs/specs/08_soft_romantic_v2.md` (v1.0.0, approved by owner 2026-09-27)
**Branch:** `feature/soft-romantic-v2` · **Decisions:** H-014, H-010, H-013, H-009, D-013, D-018
**Work split:** one developer, in the build order of §11 (no agents).

> **As built (2026-09-27), where it differs from the text below:**
> - Hand-over condition (§5.1 step 5) is `nxt.first − L ≤ clear_at + X`, not `nxt.first ≤ clear_at`
>   (Pop Karaoke's rule): a line still fading out of the current slot must never meet the next
>   line's first word there. A line can so stay up to `X + L` (0.5 s) past `hold` before handing over.
> - `readable()` tests the other line's block as moved, with no 2 × glow-radius margin (§2.10):
>   with the margin, every line's first word fell to a note, since the old line is still ~15%
>   short of the past slot on the frame before that word. Faint halos stay inside `SYNC_DROP_MIN`.
> - `FocusCache.images` holds `(key, image)`; x0/y0 are recomputed (cheap).
> - AC2 hashes every 10th frame (not 30th) of `khidki_s2` and `khidki_s2_em`: 42 frames per theme.
> - A line at rest draws byte-identical pixels to v1's `compose_frame` (FramesTest), a stronger
>   check than the plan asked for.

## 1. Files

| Action | File | Reason |
|---|---|---|
| MODIFY | `src/lyric_engine/theme.py` | motion `"focus"`; focus-only fields (blur, hand-over lead, breath); `SOFT_ROMANTIC_V2`; `THEMES` |
| MODIFY | `src/lyric_engine/render/timeline.py` | extract `word_plans()` from `plan_timeline` (pure refactor, shared) |
| MODIFY | `src/lyric_engine/render/karaoke.py` | extract `transformed()` from `_layer` (pure refactor), with an optional blur |
| CREATE | `src/lyric_engine/render/focus.py` | v2 line stack, breath, line states, frame composition, sync readability |
| MODIFY | `src/lyric_engine/render/check.py` | shared safe-zone scan; `_alpha_sync` reads focus samples and scans the zone; report wording |
| MODIFY | `src/lyric_engine/render/__init__.py` | dispatch `theme.motion == "focus"` |
| MODIFY | `src/lyric_engine/cli.py` | only after AC10: default theme `soft-romantic-v2` |
| CREATE | `tests/test_focus.py` | theme, word frames, breath, stack, frames, end-to-end, CLI |
| MODIFY | `tests/test_layout.py` | emphasis tests also run for `SOFT_ROMANTIC_V2` (AC7) |
| MODIFY | `CLAUDE.md`, `docs/development_plan.md`, `docs/pending_work.md`, `docs/session_log.md` | theme list, `focus` module, status |

`layout.py`, `frames.py`, `encode.py`, `timing.py`, `align.py`, `workflow.py`, `review.py`,
`scripts/alpha_proof.py`: no change. `make` needs no change: it passes `--theme` through.

## 2. Architecture Decisions

1. **A third motion family, `"focus"`, in its own module `render/focus.py`.** v2 reveals words like
   v1 but moves whole lines like Pop Karaoke. Spec §3: v1 stays pixel-identical, so v1's
   `plan_timeline` / `_frame_parts` gain no `if v2` branch; `karaoke.py` is at 298 lines and is
   about fills. Rejected: a flag on the `"reveal"` path (risks AC2), adding to `karaoke.py`
   (past the ~300-line rule, wrong concern).
2. **Per-word frames come from v1's own code.** `timeline.word_plans()` is lifted out of
   `plan_timeline` and called by both; per-frame word look is `timeline.word_state()` times the
   breath factor. AC3 (v2 frames equal v1's) and red line 1 then hold by construction; the breath
   only multiplies glow.
3. **Line moves reuse Pop Karaoke's primitives, imported from `karaoke.py`:** `ease_out_cubic`,
   `ease_in_quad`, `_block`, `_past_slot`, `_enter_frames`, and a new `transformed()` extracted
   from `karaoke._layer` (scale about the block centre, shift, premultiplied, then alpha fade).
   `transformed()` gains `blur=0.0`; with 0 it does exactly what `_layer` did, so Pop Karaoke stays
   pixel-identical (checked in AC2 alongside v1). Rejected: a copy in `focus.py` (two versions of
   the same maths drift).
4. **Line image, then transform** (as Pop Karaoke, impl 07 §2.4). Each visible line's words are
   composed at their states (every glow under every text, v1's rule) into one image, then scaled,
   shifted, blurred and faded as one. At rest (scale 1, shift 0, blur 0, full opacity) the image
   is pasted unscaled, so the sync check reads exact pixels.
5. **Blur in premultiplied `RGBa`**, in the same pass as the resize: blurring straight alpha pulls
   dark (0,0,0,0) pixels into the edges. Measured on this laptop: one blur of a 960×420 line image
   ≈ 14 ms. It runs only on transition and exit frames; a held past line is cached (§5.4), so AC9
   (≤ 2× v1) holds.
6. **Breath is frame-based**: a word is held when `wp.end − wp.reveal ≥ round(breath_min_s × fps)`,
   i.e. its aligned duration on its own frames (every other rule in the renderer is on frames).
   The factor is a cosine from 1 down to `breath_low` and back, starting on the frame the glow
   first reaches full (`reveal + ceil(glow_in_s × fps)`), frozen at its value on `wp.end` so the
   glow fade-out starts from there with no jump (spec §4.3).
7. **Hand-over reuses `enter_s` as its duration** (Pop Karaoke's "entrance and hand-over
   duration"; v2 has no entrance) instead of a new field. v2 sets it to 0.35 s.
8. **Text box 820 px wide, centred on x 510.** v1's glow (radius 16, boost 1.8) reaches alpha 16,
   the safe-zone threshold, about 29 px past a glyph edge; the shadow about 9 px. 900 − 2 × 29 =
   842; 820 leaves margin. The safe-zone check (AC6) is the real guard: tune the width, never the
   check.
9. **Past-slot fit uses the sprite pad (3 × glow radius = 48 px)** in `_past_slot`: slightly
   conservative (a very tall past line fades in place a little sooner), no new parameter.
10. **The sync check stays v1's alpha check; only the sampling changes.** `focus.readable()` says
    whether a word can be read cleanly on a frame (its line at rest in the current slot or not yet
    drawn, and no other visible line's transformed block, grown by 2 × glow radius, over its box).
    A word that cannot be read on its "on" or "before" frame becomes a report note (spec §4.5:
    never a silent pass). The safe-zone scan moves into a helper shared with `_karaoke_checks`.
11. **Default flips in `cli.py` only, and only after AC10.** `render.render(theme=...)` keeps
    `SOFT_ROMANTIC` as its Python default so existing tests keep meaning what they say.

## 3. Data Structures

### 3.1 `theme.py`

| Field / name | Value | Enforces |
|---|---|---|
| `MOTIONS` | `("reveal", "karaoke", "focus")` | spec §4 motion families |
| `past_blur_px: float` | `6.0` (focus only) | past line "blurred about 6 px" (§4.1) |
| `handover_lead_s: float` | `0.2` (focus only) | hand-over starts 0.2 s before the next line (§4.2) |
| `breath_min_s: float` | `1.0` (focus only) | held-note threshold (§4.3) |
| `breath_low: float` | `0.65` (focus only) | glow 100% ↔ 65% (§4.3) |
| `breath_period_s: float` | `2.0` (focus only) | one cycle every 2.0 s (§4.3) |
| `SOFT_ROMANTIC_V2` | `Theme("soft-romantic-v2", motion="focus", max_width=820, center_x=510, safe_zone=(60, 380, 960, 1540), enter_s=0.35, past_scale=0.85, past_opacity=0.4, past_gap_px=40, hold_s=1.0, fade_out_s=0.3)` | spec §4.4; everything else inherits v1's defaults (font, sizes, colours, glow, shadow, reveal, lead, emphasis) |
| `THEMES` | `(SOFT_ROMANTIC, SOFT_ROMANTIC_V2, POP_KARAOKE)` | `--theme` choices |

Field comments follow the existing pattern ("Karaoke only (spec 07)" → a "Focus only (spec 08)"
block). `enter_s`'s comment gains "(focus: hand-over only)".

### 3.2 `render/focus.py`

```
@dataclass
class FocusLine:
    layout: LineLayout
    words: list[WordPlan]     # v1's per-word frames (timeline.word_plans); duck-types LinePlan
                              # for frames.build_sprites (.layout, .words[].box/.text)
    first: int                # first visible frame = earliest reveal of its timed words
    last_reveal: int          # latest reveal: a hand-over never starts before it (§4.2)
    last_end: int             # latest end frame: hold counts from here
    handover: int | None = None   # frame the move to the past slot starts; None = clears
    past: bool = False        # moves up at handover (False: fades and blurs in place)
    past_dy: int = 0          # block-centre shift into the past slot (negative = up)
    fade_start: int = 0       # exit fade (ease-in) and blur from here ...
    stop: int = 0             # ... to nothing at stop (exclusive)

class FocusCache:
    images: dict[int, tuple[tuple, Image.Image, int, int]]   # line -> (word-state key, image, x0, y0)
    layers: dict[int, tuple[tuple, Image.Image, tuple[int, int]]]   # line -> (transform key, image, pos)
    fades: dict[int, frames.FadeCache]                        # line -> faded word sprites
```

Sprites: `frames.build_sprites(lines, theme)` unchanged (text + shadow, glow, pad = 3 × glow
radius). Word-state key per word: `(round(opacity × LEVELS), round(rise), round(glow × LEVELS))`.

## 4. Function Specifications

### `render/timeline.py`
- `word_plans(words: list[dict], lay: LineLayout, theme: Theme) -> list[WordPlan]` — body of
  `plan_timeline`'s inner loop (current lines 80-88), moved verbatim. `plan_timeline` calls it.

### `render/karaoke.py`
- `transformed(img, x0, y0, lay, scale, dy, level, theme, blur=0.0) -> tuple[Image, tuple[int, int]]`
  — moved from `_layer` (current lines 276-284). If `scale != 1 or dy != 0 or blur > 0`: convert
  to `RGBa`, resize about `(theme.center_x, block centre)` when scaled, `GaussianBlur(blur)` when
  `blur > 0`, shift by `dy`, convert back. If `level < LEVELS`: alpha through `_LUTS[level]`.
  `_layer` calls it with `blur=0.0`. Raises nothing.

### `render/focus.py`
- `plan_focus(doc, theme, n_frames, emphasis=frozenset(), layout_fn=None) -> tuple[list[FocusLine], list[int]]`
  — lines in time order with their stack life cycle (§5.1); skipped lines. Calls
  `timeline.laid_out_lines`, `timeline.word_plans`, `karaoke._past_slot`, `karaoke._enter_frames`.
  Raises what `laid_out_lines` raises (`LayoutError`, red-line-2 `AssertionError`).
- `held(wp: WordPlan, theme) -> bool` — timed and `wp.end − wp.reveal ≥ round(breath_min_s × fps)`.
- `breath(wp, n, theme) -> float` — 1.0 unless held and `n ≥ b0`; then
  `1 − (1 − breath_low) × (1 − cos(2π × (min(n, wp.end) − b0) / P)) / 2`, with
  `b0 = wp.reveal + ceil(glow_in_s × fps)`, `P = breath_period_s × fps`.
- `word_look(wp, n, theme) -> tuple[float, float, float]` — `timeline.word_state(wp, n, theme)`
  with glow × `breath(wp, n, theme)`. Untimed word: `(1, 0, 0)` as v1.
- `line_state(fl, n, theme) -> tuple[float, float, float, float]` — `(scale, dy, opacity, blur)`;
  opacity 0 off screen; exactly `(1.0, 0.0, 1.0, 0.0)` at rest (§5.2).
- `readable(lines, fl, wp, m, theme) -> bool` — §2.10, used by the check.
- `line_image(fl, sprites, n, theme, cache) -> tuple[Image, tuple, int, int]` — §5.3.
- `_layer(fl, sprites, n, theme, cache) -> tuple[Image, tuple[int, int]] | None` — §5.4.
- `frame_parts(n, lines, sprites, theme, cache) -> list` — §5.4; returns `frames.band_parts(...)`.

### `render/check.py`
- `_zone_box(alpha: bytes | memoryview, size, zone) -> tuple | None` — the drawn bbox (alpha ≥
  `SAFE_ALPHA_MIN`) when it leaves `zone`, else None. Moved out of `_karaoke_checks.visit`.
- `_zone_failure(outside, zone) -> str` — the existing "safe zone: N frame(s) ..." message.
- `_focus_samples(result, lines, theme) -> list[_Sample]` — §5.5.
- `_alpha_sync(...)` — samples from `_focus_samples` when `theme.motion == "focus"`, else
  `_sync_samples`; `visit` also runs `_zone_box` when `theme.safe_zone` is set (v1: None, so v1's
  check is unchanged). `check_outputs` dispatch unchanged (`"focus"` goes to `_alpha_sync`).
- `write_report` — frame-check line: "sync check of N timed word(s) on the overlay's alpha", plus
  "; safe-zone check of every frame" when `theme.safe_zone` is set.

### `render/__init__.py`
- `render()` — `elif theme.motion == "focus"`: `focus.plan_focus(doc, theme, n, emphasis=...)`,
  `build_sprites(lines, theme)`, `focus.FocusCache()`, `focus.frame_parts`. Docstring names v2.

### `cli.py` (after AC10 only)
- `render` and `make` `--theme` default `"soft-romantic-v2"`; help text says v1 is
  `--theme soft-romantic`.

## 5. Logic Flow

### 5.1 `plan_focus`
1. `rows, skipped = laid_out_lines(doc, theme, layout_fn, emphasis)`.
2. Per row: `wps = word_plans(words, lay, theme)`; over timed words (`reveal` not None):
   `FocusLine(lay, wps, first=min reveal, last_reveal=max reveal, last_end=max end)`.
3. Sort by `(first, layout.line)`.
4. `E = _enter_frames(theme)`, `L = round(handover_lead_s × fps)`, `H = _ceil_frame(hold_s, fps)`,
   `X = round(fade_out_s × fps)`, `pad = 3 × glow_radius`.
5. For each line `k`, `nxt = lines[k+1]` or None, `clear_at = last_end + H`:
   - if `nxt` and `nxt.first ≤ clear_at`: `handover = max(nxt.first − L, last_reveal)`;
     `past_dy, past = _past_slot(layout, nxt.layout, theme, pad)`.
   - else: `fade_start, stop = clear_at, clear_at + X` (clear, §4.2.4).
6. For each line with a `handover`:
   - not `past`: `fade_start, stop = handover, handover + X` (fades and blurs in place).
   - `past` and `nxt.handover` set: `stop = nxt.handover`, `fade_start = max(handover, stop − X)`.
   - `past` and `nxt` clears: `fade_start, stop = nxt.fade_start, nxt.stop` (fade together).
7. Never three lines: `stop = min(stop, n_frames, lines[k+2].first)` (when it exists);
   `fade_start = min(fade_start, stop)`.

### 5.2 `line_state`
1. Not `first ≤ n < stop` → `(1, 0, 0, 0)`.
2. `h = ease_out_cubic((n − handover) / E)` if `past` and `handover` set and `n > handover`, else 0
   (at rest on the hand-over frame itself, as Pop Karaoke as built).
3. `scale = 1 + (past_scale − 1)h`, `dy = past_dy × h`, `op = 1 + (past_opacity − 1)h`,
   `blur = past_blur_px × h`.
4. If `n ≥ fade_start`: `x = (n − fade_start) / max(1, stop − fade_start)`;
   `op ×= 1 − ease_in_quad(x)`; `blur = max(blur, past_blur_px × x)`.

### 5.3 `line_image`
1. `pad` from the first word's sprite. `key = tuple(word-state key of word_look(wp, n) per word)`.
2. Cache hit on `(line, key)` → return it.
3. Canvas: `x0 = min box.x − pad`, `y0 = min box.y − pad`, `x1 = max(box.x + w) + pad`,
   `y1 = max(box.y + h) + pad + rise_px` (a revealing word is drawn up to `rise_px` lower).
4. Every word's glow (level > 0), then every word's text (level > 0), each through
   `cache.fades[line].faded(sprite, level, (index, kind, level))`, at
   `(box.x − pad − x0, box.y − pad + round(rise) − y0)`.
5. Store and return `(img, key, x0, y0)`.

### 5.4 `_layer` and `frame_parts`
- `_layer`: `(scale, dy, op, blur) = line_state`; `level = min(LEVELS, round(op × LEVELS))`;
  0 → None. `img, key, x0, y0 = line_image(...)`; transform key `(key, scale, dy, blur, level)`;
  cache hit → return; else `karaoke.transformed(img, x0, y0, layout, scale, dy, level, theme, blur)`,
  store, return.
- `frame_parts`: `visible = [fl for fl in lines if fl.first ≤ n < fl.stop]` (time order: past line
  first, so it is drawn under the current one); drop `images`, `layers`, `fades` entries of lines
  not visible; `band_parts([layers...], theme)`.

### 5.5 `_focus_samples`
For each line, each timed word with ink (`_ink`):
1. `on = reveal + ceil(reveal_s × fps)`; `before = reveal − 1` if `reveal > 0` else None.
2. If not `readable(on)` or (`before` is not None and not `readable(before)`): note
   `"<label>: another line overlapped it, or its line left the current slot, before it could be
   read (sung back to back)"`; skip.
3. Else `_Sample(label, box, ink, on, before, cut=False)`. `_alpha_sync` then applies v1's
   thresholds (`SYNC_ON_MIN`, `SYNC_DROP_MIN`) and failure texts (`sync: ...`).

`readable(m)`: if `m ≥ fl.first`, `line_state(fl, m)` must equal `(1, 0, 1, 0)`; and for every other
line visible at `m` with opacity > 0, its word-box block scaled about `(center_x, block centre)`,
shifted by `dy` and grown by `2 × glow_radius` must not intersect `wp.box`.

## 6. Edge Case Implementation Map

| Spec edge case | Mechanism | Location |
|---|---|---|
| No `--theme`, before / after AC10 | argparse default `soft-romantic` / `soft-romantic-v2` | `cli.py` parsers |
| Next line before last word revealed | `handover = max(nxt.first − L, last_reveal)`; word keeps its frames via `word_look` in the past line; check note | `plan_focus` step 5, `_focus_samples` |
| Long instrumental gap | `nxt.first > clear_at` → clear; past line fades together | `plan_focus` steps 5-6 |
| First line at 0:00 | `word_plans` clamps reveal to 0; no previous line | `timeline.word_plans` |
| Held last word, next line close | `word_look` is per word, independent of line state | `focus.word_look` |
| Held word with silence in it | breath runs to `wp.end`; nothing reads audio | `focus.breath` |
| Past line too tall | `_past_slot` → `past=False` → fade and blur in place | `plan_focus` step 6 |
| Marked word on a shrunk line | layout (spec 06) unchanged; sprites via `layout.word_fonts` | `frames.build_sprites` |
| Untimed word, `--allow-flagged` | `word_state` → `(1, 0, 0)`; `breath` → 1; excluded from `first/last_*` | `focus.word_look`, `plan_focus` step 2 |
| Untimed word, no `--allow-flagged` | refused before planning | `render.load_for_render` (unchanged) |
| Line with no timed word | skipped | `timeline.laid_out_lines` (unchanged) |
| Line too long | `LayoutError` names the line | `layout` (unchanged) |
| Blurred past line on the green mp4 | no mechanism; known limit, alpha `.mov` exact | report unchanged |

## 7. File Layout

`render/focus.py`, in order: module docstring (spec, red lines, how it reuses v1 and karaoke) →
imports → `# --- Data` (`FocusLine`, `FocusCache`) → `# --- Timeline` (`plan_focus`, `held`,
`breath`, `word_look`, `line_state`, `readable`) → `# --- Frames` (`line_image`, `_layer`,
`frame_parts`). Target ≤ 250 lines.

`tests/test_focus.py`: helpers (reuse `tests.test_render.make_song`, `word`, and
`tests.test_karaoke.low_layout` / `high_layout`) → `ThemeTest` → `WordFramesTest` (AC3) →
`BreathTest` (AC4) → `PlanFocusTest`, `LineStateTest` (AC5) → `FramesTest` (AC8, at-rest pixels,
blur only off rest) → `FocusRenderTest` (AC1, AC6) → `CliThemeTest` (AC1).

## 8. Dependencies

- No new packages. `focus.py` imports `math`, `dataclasses`, `PIL.Image`; from `..layout`
  `LineLayout`; `..theme` `Theme`; `.timeline` `WordPlan`, `laid_out_lines`, `word_plans`,
  `word_state`; `.karaoke` `ease_out_cubic`, `ease_in_quad`, `_block`, `_past_slot`,
  `_enter_frames`, `transformed`; `.frames` `FadeCache`, `LEVELS`, `band_parts`.
- `check.py` and `render/__init__.py` import `focus`; `focus` imports neither (no cycle).
- Conflicts found: `karaoke._layer` holds the transform inline (extract first, §11 step 2);
  `check._karaoke_checks.visit` holds the zone scan inline (extract); `check.py` is at 289 lines,
  so the zone extraction must offset `_focus_samples` (target ≤ ~305).
- `CLAUDE.md` is 104 lines: room for the theme list and the `focus` module line.

## 9. Hard Boundaries

- [x] `focus.py` never computes a word frame of its own: reveal and end come only from
      `word_plans` (red line 1); the breath only scales glow, never opacity, rise, size or place.
- [x] No hand-over, fade, blur or breath changes `WordPlan.reveal` / `end`.
- [x] Every drawn string goes through `frames.build_sprites` → `checked_mask` (red line 2).
- [x] v1 (`"reveal"`) and Pop Karaoke (`"karaoke"`) produce byte-identical frames (AC2).
- [x] No upcoming word is drawn before its reveal (H-010, H-014).
- [x] No new colour, font, stroke or backplate; no hue-120 green (existing guard).
- [x] At most two lines visible in any frame.
- [x] The safe-zone check is never loosened to make a render pass; tune `max_width` instead.
- [x] `render()` never calls alignment; nothing is written outside `render/soft-romantic-v2/`.

## 10. Acceptance Criteria (runnable)

`$PY` = `venv/Scripts/python`; song runs use the owner's `songs/khidki_s2` and `songs/khidki_s2_em`.

1. **Theme choice:** `$PY -m lyric_engine.cli render songs/khidki_s2 --theme soft-romantic-v2` →
   exit 0, `songs/khidki_s2/render/soft-romantic-v2/{overlay.mov,overlay_green.mp4,preview.mp4,report.md}`,
   report line `Theme: soft-romantic-v2`, `words.json` hash unchanged, no align output.
   `$PY -m lyric_engine.cli make songs/khidki_s2 --theme soft-romantic-v2` → exit 0, same folder.
   Unit: `$PY -m unittest tests.test_focus -k Cli` → `OK`.
2. **v1 untouched:** before any source edit, `git worktree add <scratch>/dev_tree dev`;
   `<scratch>/frame_hashes.py songs/khidki_s2` hashes v1 `compose_frame` and Pop Karaoke
   `frame_parts` bytes at every 30th frame; run with `PYTHONPATH=<scratch>/dev_tree/src` →
   `dev.json`, then on the branch → `branch.json`; `fc dev.json branch.json` → no differences.
3. **Word frames:** `$PY -m unittest tests.test_focus -k WordFrames` → `OK` (for synthetic words,
   `plan_focus` reveal/end per word == `plan_timeline`'s; a flagged word: glow 0 and breath 1 on
   every frame).
4. **Breath:** `$PY -m unittest tests.test_focus -k Breath` → `OK` (0.9 s word: `word_look` ==
   `word_state` on every frame; 2 s word: glow in [0.65, 1] from full-glow frame to `end`, < 1 at
   least once; `|glow(end+1) − glow(end)| ≤ 1 / (glow_out_s × fps)`; 0 outside the glow window).
5. **Stack:** `$PY -m unittest tests.test_focus -k PlanFocus -k LineState` → `OK` (≤ 2 lines
   visible on every frame of each synthetic timing; `handover ≥ last_reveal`; past line reaches
   `(0.85, past_dy, 0.4, 6.0)`; state exactly `(1, 0, 1, 0)` at rest; back-to-back, instrumental
   gap, first word at 0:00, past slot not fitting).
6. **Render checks:** AC1's render and
   `$PY -m lyric_engine.cli render songs/khidki_s2_em --theme soft-romantic-v2` → `checks: pass`.
   Not vacuous: `$PY -m unittest tests.test_focus -k FocusRender` → reveals shifted 10 frames late
   fail with `sync:`; `safe_zone` shrunk to `(60, 380, 960, 1150)` fails with `safe zone:`.
7. **Emphasis:** `$PY -m unittest tests.test_layout -k Emphasis` → `OK`, now over
   `(THEME, SOFT_ROMANTIC_V2, POP_KARAOKE)` at 1.5 and 2.0.
8. **Text:** `$PY -m unittest tests.test_focus -k Frames` → a box/text mismatch raises
   `AssertionError` from `build_sprites` before drawing; `tests.test_render` still `OK`.
9. **Speed:** wall time in `songs/khidki_s2/render/soft-romantic-v2/report.md` ≤ 2 × the one in
   `render/soft-romantic/report.md` (both rendered on this branch, same session).
10. **Look:** the owner compares `songs/khidki_s2_em/render/soft-romantic-v2/preview.mp4` with
    `render/soft-romantic/preview.mp4` and prefers v2 → CLI default flips (§4 `cli.py`),
    `$PY -m unittest tests.test_focus -k Cli` checks the new default.
11. **Gate:** `/gate` → unit tests `OK`, alpha proof passes.

## 11. Build order

1. AC2 baseline: dev worktree + `frame_hashes.py` → `dev.json`, before any source edit.
2. Pure extractions: `timeline.word_plans`, `karaoke.transformed`, `check._zone_box` /
   `_zone_failure` → full unit suite `OK` → AC2 hashes identical.
3. `theme.py` fields + `SOFT_ROMANTIC_V2` + `ThemeTest`; `test_layout` emphasis over v2 (AC7). If
   the 71-character stress line cannot fit v2's 820 px at 2x, use the 58-character line, as
   Pop Karaoke did.
4. `render/focus.py` + unit tests (AC3, AC4, AC5, AC8).
5. `check.py` focus sampling + zone scan, `render/__init__.py` dispatch, end-to-end tests (AC1
   unit, AC6 unit).
6. Real runs on `khidki_s2` and `khidki_s2_em` (v1 and v2): AC1, AC2, AC6, AC9. `CLAUDE.md`
   theme list; gate; `/ship`; ask the owner for AC10.
7. On the owner's preference for v2: flip the CLI default + test, `CLAUDE.md`, gate, update PR.
