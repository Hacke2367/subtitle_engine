# Plan: Pop Karaoke Theme
**Spec:** `docs/specs/07_pop_karaoke_theme.md` (v1.0.1, approved by owner 2026-09-27)
**Branch:** `feature/pop-karaoke-theme` · **Decisions:** H-011, H-013, H-009, D-018 (new, §2.9)
**Work split:** one developer, in the build order of §11 (no agents).

## 1. Files

| Action | File | Reason |
|---|---|---|
| CREATE | `fonts/Poppins-SemiBold.ttf`, `fonts/OFL.txt` | theme font in the repo (spec §3), from `google/fonts` `ofl/poppins/` |
| MODIFY | `src/lyric_engine/theme.py` | karaoke fields, `center_x`, `safe_zone`, key-green guard, `POP_KARAOKE`, `THEMES` |
| MODIFY | `src/lyric_engine/layout.py` | `word_mask(..., stroke=)`; `_place` centres rows on `theme.center_x` |
| MODIFY | `src/lyric_engine/render/timeline.py` | extract `laid_out_lines()` from `plan_timeline` (pure refactor, shared) |
| MODIFY | `src/lyric_engine/render/frames.py` | extract `checked_mask()` and `band_parts()` (pure refactor, shared) |
| CREATE | `src/lyric_engine/render/karaoke.py` | karaoke timeline, line states, fill, sprites, frame composition |
| MODIFY | `src/lyric_engine/render/check.py` | split SR alpha sync into `_alpha_sync`; add `_karaoke_checks` (fill sync + safe zone); report wording |
| MODIFY | `src/lyric_engine/render/__init__.py` | `render/<theme>/` folder; dispatch on `theme.motion` |
| MODIFY | `src/lyric_engine/cli.py` | `--theme` on `render` and `make` |
| CREATE | `tests/test_karaoke.py` | fill, line states, sprites, frames, theme guard, end-to-end, CLI |
| MODIFY | `tests/test_render.py` | output folder is now `render/soft-romantic/` |
| MODIFY | `tests/test_layout.py` | `center_x` placement; stroke mask size |
| MODIFY | `CLAUDE.md`, `docs/decision.md`, `docs/development_plan.md`, `docs/pending_work.md` | commands, output paths, D-018, status |

`workflow.py`, `timing.py`, `align.py`, `encode.py`, `review.py`, `scripts/alpha_proof.py`: no change.

## 2. Architecture Decisions

1. **One `Theme` dataclass, a `motion` field picks the renderer** (`"reveal"` = Soft Romantic,
   `"karaoke"` = Pop Karaoke). Spec §4.1: themes are a fixed set in `theme.py`, all look numbers
   there (CLAUDE.md). Rejected: a `Theme` subclass per style (one implementation each, no shared
   interface to gain) and dispatch on `theme.name` (breaks when a second karaoke theme appears).
2. **Soft Romantic keeps its code path.** `plan_timeline`, `build_sprites`, `_frame_parts`,
   `_sync_samples` stay; only pure extractions (§2.3) touch them. Spec AC2: pixel-identical.
   New karaoke logic lives in `render/karaoke.py`, so no SR branch gains an `if karaoke`.
3. **Share by extraction, not by copy.** `laid_out_lines` (group, skip untimed lines, layout,
   red-line-2 assertion), `checked_mask` (the red-line-2 text and mask-size assertions) and
   `band_parts` (zero frame / band bytes) are lifted out of SR functions and reused by karaoke.
   The red-line assertions then exist once and guard both themes (spec AC7).
4. **Line image, then transform.** Per visible line, compose its words (each at its fill state)
   into one line image, then scale / shift / fade that image. Entrance, hand-over and exit are
   whole-line moves (spec §4.3), so transforming one image is the cheapest correct way.
   At rest (scale 1, shift 0) the image is pasted unscaled, so the fill check reads exact pixels.
   Rejected: scaling every word sprite (N resizes per frame, same result).
5. **Fill = blend of two sprites per word.** `base` (shadow + stroke + white glyph) and `hot`
   (same, accent glyph) share one alpha, so `Image.composite(hot, base, weight)` changes colour
   only. `weight` is a column ramp from the fill edge (§5.3). Research §4 "karaoke sweep", ~1 ms.
6. **Fill progress is frame-based**: 0 before the word's start frame, 1 from its end frame,
   linear between (spec §4.4, AC3). The frames come from `_floor_frame(t − lead)` exactly as SR's
   reveal, so both themes put a word on the same frame (red line 1).
7. **At most two lines by construction.** After planning, every line's `stop` is clamped to the
   `enter` of the line two places later (§5.2 step 7). Spec AC4 then holds for any timing.
8. **Fill check reads one colour plane plus alpha in one decode.** `format=gbrap`,
   `extractplanes=<c>+a`, `vstack` → one gray stream of 1080×3840 per frame. Channel `c` is the
   RGB channel where text and accent differ most (G for white vs `#FF2E88`: 255 vs 46).
   Rejected: full RGBA decode (4× the bytes, 7000 frames on a full song).
9. **Output folders and font (spec §7, owner-approved) → D-018.** `render/<theme.name>/` for every
   theme; Poppins SemiBold and its OFL in `fonts/`, found via `REPO_FONTS` relative to
   `theme.py` (package is installed editable, so it resolves to the repo).
10. **Safe zone as a render check, not a layout refusal.** Horizontally, `max_width` 860 inside
    the 900 px zone leaves 20 px per side for stroke + shadow + the ≤1% entrance overshoot.
    Vertically, 3 rows at 96 px (~442 px, ~540 px with a 2x word) fit easily. The check proves it
    on every frame. Rejected: a layout-time zone test (duplicates the check, needs overhang maths
    in `layout.py`).

## 3. Data Structures

### 3.1 `theme.py`

New module constants: `REPO_FONTS = Path(__file__).resolve().parents[2] / "fonts"`;
`KEY_HUE, KEY_HUE_TOL, KEY_SAT_MIN = 120, 15, 0.5` (spec AC8).

New `Theme` fields (defaults leave Soft Romantic unchanged):

| Field | Default | PK value | Enforces |
|---|---|---|---|
| `motion: str` | `"reveal"` | `"karaoke"` | §2.1 dispatch; `__post_init__` refuses other values |
| `center_x: int` | `540` | `510` | spec §4.6 centre of x 60–960 |
| `safe_zone: tuple[int,int,int,int] \| None` | `None` | `(60, 380, 960, 1540)` | spec §4.6; `None` = no zone check (SR, step 08) |
| `accent_rgb: tuple \| None` | `None` | `(255, 46, 136)` | spec §4.5; required when `motion == "karaoke"` |
| `stroke_rgb: tuple \| None` | `None` | `(11, 11, 20)` | legibility layer (styling rules) |
| `stroke_frac: float` | `0.0` | `0.04` | stroke width = 4% of the word's own size |
| `fill_soft_px: int` | `8` | `8` | soft fill edge |
| `preroll_s: float` | `0.5` | `0.5` | spec §4.3 enter |
| `enter_s: float` | `0.28` | `0.28` | entrance and hand-over duration |
| `enter_scale: float` | `0.94` | `0.94` | entrance start scale |
| `past_scale: float` | `0.8` | `0.8` | past slot |
| `past_opacity: float` | `0.4` | `0.4` | past slot |
| `past_gap_px: int` | `40` | `40` | gap between past line bottom and current line top |

PK also sets: `font=REPO_FONTS / "Poppins-SemiBold.ttf"`, `font_size=96`, `min_font_size=64`,
`max_width=860`, `text_rgb=(255, 255, 255)`, `shadow_rgb=(0, 0, 0)`, `shadow_alpha=0.5`,
`shadow_radius=4`, `shadow_offset=(0, 3)`, `hold_s=1.0`, `fade_out_s=0.2` (the exit fade, reused
field). Unused by karaoke: the glow fields, `reveal_s`, `rise_px`.

`THEMES: dict[str, Theme] = {t.name: t for t in (SOFT_ROMANTIC, POP_KARAOKE)}`; order = CLI order.

### 3.2 `render/karaoke.py`

```
@dataclass
class FillWord:
    box: WordBox
    text: str                 # words.json text; checked_mask asserts box.text == text
    start: int | None         # fill start frame (floor(start − lead)); None = untimed, never fills
    end: int | None           # fill end frame, ≥ start

@dataclass
class KaraokeLine:
    layout: LineLayout
    words: list[FillWord]
    first_fill: int           # min start of timed words
    last_end: int             # max end of timed words
    enter: int                # first visible frame (entrance begins)
    rest: int                 # first frame at rest (enter + E, or 0 for the 0:00 edge)
    handover: int | None      # next line's enter when it hands over; None = clears
    past: bool                # moves into the past slot at handover (False: fades in place)
    past_dy: int              # block-centre shift into the past slot (negative = up)
    fade_start: int           # exit fade from here …
    stop: int                 # … to 0 at stop (exclusive); stop ≤ n_frames

KSprites = dict[int, tuple[Image.Image, Image.Image, int]]   # word i -> (base, hot, pad)

class LineCache:              # per visible line: last fill key -> composed line image
    images: dict[int, tuple[tuple, Image.Image]]   # keyed by layout.line
```

Frame counts used throughout: `E = ceil(enter_s·fps)`, `P = round(preroll_s·fps)`,
`H = ceil(hold_s·fps)`, `X = round(fade_out_s·fps)`.

## 4. Function Specifications

### `theme.py`
- `_near_key_green(rgb) -> bool`: `colorsys.rgb_to_hsv`; true when `|h·360 − 120| ≤ 15` and
  `s > 0.5`.
- `Theme.__post_init__` (extend): after the H-013 check, raise `ValueError` if `motion` is not
  `"reveal"`/`"karaoke"`; if `motion == "karaoke"` and `accent_rgb` or `stroke_rgb` is `None`;
  if any of `text_rgb, glow_rgb, shadow_rgb, accent_rgb, stroke_rgb` (non-`None`) is near key
  green: `"theme {name}: {field} {rgb} is too close to the key green (hue 120); the green-screen
  output would key it out"`.

### `layout.py`
- `word_mask(text, fonts, pad=0, stroke=0) -> Image`: unchanged for `stroke=0` (no stroke kwargs
  passed to `draw.text`). For `stroke > 0`, each run is drawn with `stroke_width=stroke,
  stroke_fill=255`: the glyph plus its outline, same image size. Caller guarantees `pad ≥ stroke`.
- `_place(...)`: `left = (2 * theme.center_x - _row_width(row, fonts.space)) // 2`. For
  `center_x = 540` this equals today's `(width − row_width) // 2` bit for bit.

### `render/timeline.py`
- `laid_out_lines(doc, theme, layout_fn, emphasis) -> tuple[list[tuple[list[dict], LineLayout]], list[int]]`:
  the first half of today's `plan_timeline` loop, moved verbatim (group by line in line order;
  line with no timed word → `skipped`; `layout_fn(...)`; the red-line-2 `AssertionError`).
  `plan_timeline` calls it, then builds `WordPlan`s as now.

### `render/frames.py`
- `checked_mask(text, box, fonts, pad, stroke=0) -> Image`: the two `AssertionError`s now inline
  in `build_sprites` (text vs `box.text`, mask size vs box + pad), then returns the mask.
  `build_sprites` calls it with `stroke=0`.
- `band_parts(layers, theme) -> list`: the tail of `_frame_parts` from `if not layers` to the
  return, moved verbatim. `_frame_parts` calls it.

### `render/karaoke.py`
- `ease_out_back(x)`, `ease_out_cubic(x)`, `ease_in_quad(x)`: research §5 formulas, `x` clamped
  to 0..1; `ease_out_back` uses `c1 = 1.70158` (peak ≈ 1.100, the ≤10% overshoot limit).
- `fill_progress(fw, n) -> float`: `0.0` if `fw.start is None or n < fw.start`; `1.0` if
  `n ≥ fw.end`; else `(n − start) / (end − start)`.
- `stroke_px(theme, size) -> int`: `max(1, round(size · stroke_frac))`, or 0 when `stroke_frac`
  is 0.
- `sprite_pad(theme) -> int`: `stroke_px(theme, ceil(font_size · EMPHASIS_MAX)) +
  3·shadow_radius + max(abs(v) for v in shadow_offset)`. One pad for every word.
- `plan_karaoke(doc, theme, n_frames, emphasis=frozenset(), layout_fn=None) -> tuple[list[KaraokeLine], list[int]]`:
  §5.2. Same return shape as `plan_timeline` (lines, skipped).
- `line_state(kl, n, theme) -> tuple[float, float, float]`: `(scale, dy, opacity)`; opacity 0
  when `n` is outside `[enter, stop)`. §5.3.
- `build_sprites(lines, theme) -> KSprites`: per word, `fonts = word_fonts(theme,
  lp.layout.font_size, box.emphasis)`, `s = stroke_px(theme, fonts.size)`, glyph =
  `checked_mask(text, box, fonts, pad)`, outline = `word_mask(text, fonts, pad, stroke=s)`,
  shadow = blurred outline × `shadow_alpha`, offset. `base = shadow ⊕ solid(stroke_rgb, outline) ⊕
  solid(text_rgb, glyph)`, `hot` = same with `accent_rgb`. Reuses `frames._solid`, `_scaled`.
- `word_image(fw, sprites, n, theme) -> Image`: `base` at progress 0, `hot` at 1, else
  `Image.composite(hot, base, weight)` with the §5.3 column ramp.
- `line_image(kl, sprites, n, theme, cache) -> tuple[Image, int, int]`: the line's words at their
  fill states on one transparent canvas covering the union of word boxes ± pad; returns the image
  and its top-left on the frame at rest. Key = tuple of each word's fill state (`0`, `1`, or the
  quantised edge px); unchanged key → cached image.
- `frame_parts(n, lines, sprites, theme, cache) -> list`: visible lines (past first, current
  second), `line_state` → transform (§5.4) → layers → `frames.band_parts`.

### `render/check.py`
- `check_outputs(result, lines, theme, n_frames)`: the three ffprobe checks as now, then
  `_alpha_sync(...)` for `motion == "reveal"` (today's code, moved verbatim) or
  `_karaoke_checks(...)` for `"karaoke"`.
- `_ink(text, fonts) -> Image | None`: the solid-pixel mask of the pad-0 glyph mask (today's
  `mask.point(... 255 if v >= top ...)`), `None` for a mask with no ink. Used by both checks.
- `_karaoke_checks(result, lines, theme, n_frames) -> list[str]`: §5.5.
- `write_report(...)`: the "Output check" sentence names the checks run for the theme's motion.

### `render/__init__.py`
- `render(...)`: `render_dir = song_dir / "render" / theme.name`, `mkdir(parents=True,
  exist_ok=True)` (still after every refusal, so a refused render writes nothing). For
  `theme.motion == "karaoke"`: `karaoke.plan_karaoke` / `karaoke.build_sprites` /
  `karaoke.frame_parts` with a `karaoke.LineCache`; else today's calls. Docstring paths updated.

### `cli.py`
- `render` and `make` gain `--theme` with `choices=list(THEMES)`, `default="soft-romantic"`.
  `_render(song, codec, allow_flagged, theme_name)` passes `theme=THEMES[theme_name]`;
  `_make` passes it through. An unknown name is argparse's own error (exit 2, lists choices).

## 5. Logic Flow

### 5.1 Render (karaoke)
1. `load_for_render` as today (refusals unchanged: flagged, stale, malformed marker).
2. `n = ceil(duration·fps)`; `lines, skipped = plan_karaoke(doc, theme, n, emphasis)`.
3. `sprites = karaoke.build_sprites(lines, theme)` (red-line-2 asserts inside `checked_mask`).
4. `render_dir = song/render/pop-karaoke`; remove old outputs there; one ffmpeg encode fed by
   `frame_parts(k, ...)` for k in 0..n−1.
5. `check_outputs` → `_karaoke_checks`; `write_report`.

### 5.2 `plan_karaoke`
1. `rows, skipped = laid_out_lines(doc, theme, layout_fn, emphasis)`.
2. For each `(words, lay)`: `FillWord`s; timed word: `start = max(0, _floor_frame(start − lead))`,
   `end = max(start, _floor_frame(end − lead))`; untimed: `None, None`. `first_fill`, `last_end`
   over timed words.
3. Sort lines by `(first_fill, line)` (as SR).
4. Enter, in order: `latest = first_fill − E − 1`.
   - If `latest < 0`: `enter = rest = 0` (first word within the entrance time of 0:00).
   - Else: `enter = min(max(first_fill − P, prev.last_end + 1 if prev else 0), latest)`, then
     `enter = max(enter, prev.enter + 1)` if there is a prev (strict order); `rest = enter + E`.
5. Leave, per line with `nxt` = next line or `None`, `clear_at = last_end + H`:
   - `nxt` exists and `nxt.enter ≤ clear_at + X` → `handover = nxt.enter`;
     `past_dy, past = _past_slot(kl, nxt, theme)`.
   - else → `handover = None`, `fade_start = clear_at`, `stop = clear_at + X`.
6. Past-line exit, per line with a handover (needs step 5 done for `nxt`):
   - `past` false → fades in place: `fade_start = handover`, `stop = handover + X`.
   - `nxt.handover` not `None` → `stop = nxt.handover`, `fade_start = max(handover, stop − X)`.
   - `nxt` clears → fades with it: `fade_start = nxt.fade_start`, `stop = nxt.stop`.
7. Clamp: `stop = min(stop, n_frames, lines[k+2].enter if it exists)`,
   `fade_start = min(fade_start, stop)`. At most two lines visible (§2.7).

`_past_slot(kl, nxt, theme) -> (int, bool)`: block of `kl` at rest `T..B` (word boxes), centre
`cy`; target centre `nxt.T − past_gap_px − past_scale·(B − T)/2`; `past_dy = round(target − cy)`;
fits iff `target − past_scale·((B − T)/2 + pad) ≥ safe_zone[1]` (true when `safe_zone` is None).

### 5.3 `line_state` and fill weight
- `e = 1` if `n ≥ rest` else `(n − enter)/E`. Scale-in = `1.0` exactly when `n ≥ rest`, else
  `enter_scale + (1 − enter_scale)·ease_out_back(e)`; opacity-in = `ease_out_cubic(e)`.
- `h = 0` unless `past` and `handover ≤ n`: then `ease_out_cubic((n − handover)/E)`.
  `scale = scale_in·(1 + (past_scale − 1)·h)`, `dy = past_dy·h`,
  `opacity = op_in·(1 + (past_opacity − 1)·h)`.
- `n ≥ fade_start`: `opacity *= 1 − ease_in_quad((n − fade_start)/max(1, stop − fade_start))`.
- Fill weight of sprite column `x` (sprite width `Ws = box.w + 2·pad`), `0 < p < 1`:
  `clamp((pad + p·(box.w + soft) − x) / soft, 0, 1)`, one row resized to the sprite height.

### 5.4 `frame_parts`
1. `visible = [kl for kl in lines if kl.enter ≤ n < kl.stop]` sorted by enter (past first).
   Empty → `[zero]`.
2. Per line: `scale, dy, op = line_state(...)`; `img, x0, y0 = line_image(...)`.
   - `scale == 1 and dy == 0` → layer `(img, (x0, y0))`.
   - else → `img.resize((round(w·scale), round(h·scale)), BICUBIC)`, placed so the block centre
     `(center_x, cy)` maps to `(center_x, cy + dy)`.
   - `op < 1` → alpha through `frames._LUTS[level]`, `level = round(op·LEVELS)`; 0 → skip.
3. `frames.band_parts(layers, theme)`.

### 5.5 `_karaoke_checks`
1. Channel `c` = argmax over R, G, B of `|text_rgb[c] − accent_rgb[c]|`; if that gap is < 64,
   fail `"fill: accent {accent} is too close to text colour {text} to check the fill"`.
2. Samples per timed word with ink (`_ink`): `at_rest(m)` = `rest ≤ m < fade_start` and
   (`handover is None or m ≤ handover`).
   - `before = start − 1` if `start > 0` and `at_rest(start − 1)`, else `None`.
   - `after = end`; not `at_rest(end)` → note
     `"{label}: its line moved to the past slot before its fill finished (sung back to back)"`,
     no sample.
3. One decode: `ffmpeg -i overlay.mov -filter_complex "[0:v]format=gbrap,extractplanes={c}+a[c][a];[c][a]vstack" -f rawvideo -pix_fmt gray -`.
   Per frame (1080×3840): top half = channel, bottom half = alpha.
   - Wanted frames: mean channel value in the word box over its ink →
     `filled = (text_c − mean)/(text_c − accent_c)`.
   - Every frame, if `safe_zone`: bbox of alpha ≥ `SAFE_ALPHA_MIN` (16); outside the zone →
     count it, keep the first frame and bbox.
4. Fails: decode error / frame count (as SR); `before` filled > 0.05 →
   `"fill: {label}: {f:.0%} filled at frame {before}, the frame before its fill starts; expected 0%"`;
   `after` filled < 0.95 → `"fill: {label}: {f:.0%} filled at frame {after}, where its fill ends;
   expected 100%"`; zone → `"safe zone: {k} frame(s) draw outside x 60-960, y 380-1540; first:
   frame {n}, bbox {bbox}"`.

## 6. Edge Case Implementation Map

| Spec edge case | Mechanism | Location |
|---|---|---|
| No `--theme` | argparse default `soft-romantic`; `render(theme=SOFT_ROMANTIC)` default | `cli.py`, `render/__init__.py` |
| `--theme unknown` | argparse `choices` → exit 2 listing names, before any work | `cli.py` |
| Old outputs in `render/` | never touched: only `render/<theme>/` files are removed/written | `render()` |
| First word near 0:00 | `latest < 0` → `enter = rest = 0` | `plan_karaoke` step 4 |
| Back-to-back lines | enter capped at `latest`; last word keeps its fill frames; check note | step 4, §5.5 step 2 |
| Instrumental gap | `nxt.enter > clear_at + X` → clear; past line fades with it | steps 5–6 |
| Flagged untimed word, `--allow-flagged` | `start = None` → `fill_progress` 0 always; no check sample | `FillWord`, `fill_progress`, §5.5 |
| Flagged without `--allow-flagged` | existing `load_for_render` refusal | unchanged |
| Line with no timed word | `laid_out_lines` → `skipped` | `timeline.py` |
| Marked word on a shrunk line | `word_fonts(..., emphasis)` for mask, stroke and check | `build_sprites`, `_ink` |
| Past line too tall | `_past_slot` false → fades in place | step 5–6 |
| Line too long | existing `LayoutError` from `layout_line` | unchanged |
| Colour near key green | `Theme.__post_init__` `ValueError` | `theme.py` |
| Poppins missing | existing `FontSet` `LayoutError("theme font not found: ...")` | `layout.py` |
| Glyph missing from Poppins | existing fallback runs; fill blends the whole sprite | `layout.py`, `word_image` |
| 3 lines at once | clamp `stop ≤ lines[k+2].enter` | step 7 |

## 7. File Layout

`render/karaoke.py`, in order: module docstring (spec link, red lines) → imports → easing functions → `FillWord`, `KaraokeLine` →
`# --- Timeline` `fill_progress`, `_past_slot`, `plan_karaoke`, `line_state` →
`# --- Sprites` `stroke_px`, `sprite_pad`, `build_sprites`, `word_image` →
`# --- Frames` `LineCache`, `line_image`, `frame_parts`. Target ≤ 250 lines.

`tests/test_karaoke.py`: helpers (synthetic doc, `make_song` reuse from `tests.test_render`) →
`ThemeTest` → `FillProgressTest` → `PlanKaraokeTest` → `LineStateTest` → `SpritesTest` →
`FrameTest` → `KaraokeEmphasisLayoutTest` → `KaraokeRenderTest` (end to end) → `CliThemeTest`.

## 8. Dependencies

- New imports: `colorsys` (theme), `math` / `dataclasses` / Pillow (karaoke). No new package.
- `karaoke.py` → `layout` (`word_fonts`, `word_mask`, `LineLayout`, `WordBox`), `timeline`
  (`laid_out_lines`, `_floor_frame`, `_ceil_frame`), `frames` (`checked_mask`, `band_parts`,
  `_solid`, `_scaled`, `_LUTS`, `LEVELS`, `_zero_frame`), `theme` (`EMPHASIS_MAX`).
- `check.py` → `karaoke` (`KaraokeLine` fields only).
- Font file must be in place before `POP_KARAOKE` is used (tests included).
- **Conflicts found:** `tests/test_render.py` `test_encoder_failure_removes_partial_outputs`
  lists `song/render` (now `render/soft-romantic`). `.gitignore` must not exclude `fonts/*.ttf`
  (check at build). `CLAUDE.md` says outputs are in `render/`. `check.py` (187 lines) grows to
  about 280; if it passes 300, move `_karaoke_checks` into `render/karaoke_check.py`.

## 9. Hard Boundaries

- [ ] Never change a Soft Romantic pixel (AC2 hashes).
- [ ] Never derive a fill frame from anything but that word's own `start`/`end` minus `lead`.
- [ ] Never fill an untimed word; never give it a frame.
- [ ] Never draw a string other than the `words.json` text (asserts via `checked_mask`).
- [ ] Never write outside `songs/<song>/render/<theme>/`; never delete files in `render/`.
- [ ] Never write theme data into `words.json`.
- [ ] Never add a package dependency; never load a font from outside the theme's font list.

## 10. Acceptance Criteria (runnable)

`PY=venv/Scripts/python`; commands from the repo root.

1. **Theme choice**: `$PY -m lyric_engine.cli render songs/khidki_s2 --theme pop-karaoke` and
   `$PY -m lyric_engine.cli render songs/khidki_s2` → both exit 0, `checks: pass`; outputs listed
   under `render/pop-karaoke/` and `render/soft-romantic/`; `grep Theme songs/khidki_s2/render/*/report.md`
   shows each name; `words.json` sha256 unchanged. `make songs/khidki_s2 --theme pop-karaoke` → exit 0,
   "using the existing alignment". `render songs/khidki_s2 --theme nope` → exit 2,
   `invalid choice: 'nope' (choose from 'soft-romantic', 'pop-karaoke')`.
   Unit: `$PY -m unittest tests.test_karaoke -k Cli` → `OK`.
2. **Soft Romantic untouched**: before any source edit, `git worktree add <scratch>/dev_tree dev`;
   `<scratch>/frame_hashes.py songs/khidki_s2` hashes `compose_frame` bytes of every 30th frame,
   run with `PYTHONPATH=<scratch>/dev_tree/src` → `dev.json`, then on the branch → `branch.json`;
   `fc dev.json branch.json` → no differences.
3. **Fill timing**: `$PY -m unittest tests.test_karaoke -k FillProgress` → `OK` (0 on
   `start − 1`, 1 on `end`, linear between, one-frame word, untimed always 0).
4. **Line states**: `$PY -m unittest tests.test_karaoke -k PlanKaraoke -k LineState` → `OK`
   (≤ 2 lines visible on every frame of each synthetic timing; `rest ≤ first_fill − 1`;
   back-to-back, instrumental gap, word at 0:00, past slot not fitting; entrance overshoot
   ≤ 10% of the move; scale exactly 1.0 at rest).
5. **Render checks**: AC1's pop-karaoke render and
   `$PY -m lyric_engine.cli render songs/khidki_s2_em --theme pop-karaoke` → `checks: pass`.
   Not vacuous: `$PY -m unittest tests.test_karaoke -k KaraokeRender` → a fill timeline shifted
   10 frames late fails with `fill:`; a theme with `safe_zone` shrunk by 200 px fails with
   `safe zone:`.
6. **Emphasis**: `$PY -m unittest tests.test_karaoke -k Emphasis` → `OK` (box = text measured at
   `emphasis_scale` × line size, also after shrink; shared baseline; no overlap; at 1.5 and 2.0).
7. **Text**: `$PY -m unittest tests.test_karaoke -k Sprites` → a box/text mismatch raises
   `AssertionError` before drawing (via `checked_mask`); existing `tests.test_render` red-line
   tests still pass.
8. **Key green**: `$PY -m unittest tests.test_karaoke -k Theme` → `(0, 255, 0)` and
   `(40, 200, 60)` refused with `ValueError` naming the field; `THEMES` builds both themes.
9. **Speed**: wall time in `songs/khidki_s2/render/pop-karaoke/report.md` ≤ 2 × the one in
   `render/soft-romantic/report.md`.
10. **Look**: the owner watches `songs/khidki_s2_em/render/pop-karaoke/preview.mp4` and approves,
    or asks for `theme.py` value changes.
11. **Gate**: `/gate` → unit tests `OK`, alpha proof passes.

## 11. Build order

1. AC2 baseline first: worktree + `dev.json`, before any source edit.
2. Font files + `.gitignore` check; D-018 in `decision.md`.
3. Pure extractions (`laid_out_lines`, `checked_mask`, `band_parts`, `_alpha_sync`, `_ink`) →
   full unit suite still `OK` → AC2 hashes still identical.
4. `theme.py` + `layout.py` changes + `ThemeTest` and layout tests.
5. `render/karaoke.py` + its unit tests (AC3, AC4, AC6, AC7).
6. `check.py` karaoke checks, `render/__init__.py`, `cli.py`, `test_render.py` path fix,
   end-to-end tests (AC1 unit, AC5 unit).
7. Real runs: AC1, AC2, AC5, AC9; `CLAUDE.md` paths; gate; `/ship`; ask the owner for AC10.
