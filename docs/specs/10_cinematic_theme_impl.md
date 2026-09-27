# Plan: Cinematic Theme
**Spec:** `docs/specs/10_cinematic_theme.md` (v1.0.0, approved by owner 2026-09-27; v1.0.1 wording
fix in §11 step 1)
**Branch:** `feature/cinematic-theme` · **Decisions:** H-017, H-012, H-013, H-010, H-009, D-017, D-018, D-020
**Work split:** one developer, in the build order of §11 (no agents).

> **As built (2026-09-27), where it differs from the text below:**
> - `_relaid` is not a function: `_couplet` re-lays a line through `laid_out_lines` with
>   `functools.partial(layout_fn, size=s)`, which re-checks the placed words (red line 2). No
>   `_span`: `_couplet` builds one-line blocks to compare frames. `Block.font_size(wp)` gives a
>   word's line size to sprites and the check.
> - Settled looks are cached only at full opacity, no blur, mix 0 or `LEVELS` (the gold-to-ivory
>   fade looks are built per frame): a block's fade levels would otherwise hold ~200 MB.
> - Plan §2.9 measured: at the start values (shadow radius 8, word gap ≥ 15 px) a neighbour's
>   shadow never reaches another word's ink, so draw order changes no pixel today; it does from
>   shadow radius 12, which `FramesTest` pins at 16.
> - Plan §2.11's bbox bound fails (17 px vs a 15 px gap at 64 px: an "f" leans at the top, a "Q"
>   overhangs at the bottom). `ItalicTest` compares per row from the baseline, plain and marked
>   sizes mixed: worst 19 px vs a 22 px gap (96 px, 2x).
> - `layout_line`'s "does not fit" message names the size it tried (`min_font_size` unchanged
>   when no size is given).
> - Sizes: `cinematic.py` 295 lines (target 280), `lofi.py` 307 → 268, `check.py` 359.

## 1. Files

| Action | File | Reason |
|---|---|---|
| MODIFY | `src/lyric_engine/theme.py` | motion `"cinematic"`; fields `blur_px`, `couplet_gap`, `couplet_max_gap_s`; guards; `CINEMATIC`; `THEMES` |
| MODIFY | `src/lyric_engine/layout.py` | `layout_line(..., size=None)`: lay out at exactly one size (a couplet's shared size) |
| CREATE | `src/lyric_engine/render/lifecycle.py` | the one-block-at-a-time life cycle, moved out of `plan_lofi` unchanged, shared by lofi and cinematic |
| MODIFY | `src/lyric_engine/render/lofi.py` | `plan_lofi` calls `lifecycle.schedule`; `LofiLine.name` / `.label()` |
| CREATE | `src/lyric_engine/render/cinematic.py` | stanza pairing, couplet stacking, blocks, blur-in and colour looks, sprites, frames, readability |
| CREATE | `src/lyric_engine/render/cinematic_check.py` | reveal-sync samples and check, safe zone |
| MODIFY | `src/lyric_engine/render/check.py` | dispatch `"cinematic"` in `check_outputs`; report wording |
| MODIFY | `src/lyric_engine/render/__init__.py` | dispatch `theme.motion == "cinematic"` |
| CREATE | `fonts/CormorantGaramond-MediumItalic.ttf` | theme font, static instance wght 500 of the Google Fonts italic variable file (SIL OFL 1.1) |
| CREATE | `fonts/OFL-CormorantGaramond.txt` | its licence (`fonts/OFL.txt` is Poppins') |
| CREATE | `tests/test_cinematic.py` | theme, pairing, stacking, reveal, block life cycle, frames, italic lean, end-to-end, CLI |
| MODIFY | `tests/test_layout.py` | `ALL_THEMES` / `LONG_FOR` gain cinematic (AC7); `layout_line(size=)` test |
| MODIFY | `tests/test_karaoke.py` | `THEMES` name list gains `cinematic` |
| MODIFY | `docs/specs/10_cinematic_theme.md` | v1.0.1: two edge-case rows say how they are met (§2.11, §2.12) |
| MODIFY | `CLAUDE.md`, `docs/development_plan.md`, `docs/pending_work.md`, `docs/session_log.md`, `docs/decision.md` | theme list, modules, status, D-021 |

`frames.py`, `timeline.py`, `karaoke.py`, `focus.py`, `lofi_check.py`, `encode.py`, `cli.py`
(choices come from `THEMES`), `timing.py`, `align.py`, `workflow.py`: no change.

## 2. Architecture Decisions

1. **A fifth motion family, `"cinematic"`, in `render/cinematic.py`.** Couplets, blur and gold
   states share nothing with Lofi's colour states or typing beyond the life cycle. Rejected: a
   flag in `lofi.py` (307 lines already, and its looks key on upcoming/typing states).
2. **The life cycle moves to `render/lifecycle.py` and both families call it.** Spec §4.3 says
   the block rules *are* Lofi Typewriter's (D-020). `plan_lofi` lines 101-144 move verbatim into
   `schedule(items, theme, n_frames, ahead)`, `tw` becoming `not ahead`; the note strings read
   `item.name` / `item.label(wp)`, which give exactly today's text for a `LofiLine`. Rejected: a
   second copy of the trickiest frame arithmetic in the repo. Guard: AC2 hashes both lofi themes.
3. **A block is 1 or 2 `LineLayout`s laid out once, then shifted** (`dataclasses.replace` on the
   frozen `WordBox`, new `LineLayout`). Both lines exist from the block's first frame, so the
   first line never moves (spec §4.2). Rejected: a multi-line layout in `layout.py` (289 lines;
   its docstring freezes the dataclass contract, which shifting keeps).
4. **Shared couplet size via `layout_line(..., size=s)`**: `sizes = [s]` instead of the
   `font_size → min_font_size` ladder. Called only when the two fitted sizes differ; a line that
   fits at size `f` fits at any `s ≤ f` (narrower words, same `max_width`). Rejected:
   `replace(theme, font_size=s)` (a new `font_set` cache entry per copy, and a theme that is not
   `THEMES`' own).
5. **Stanzas from `doc["lyrics"]["lines"]`** (blank lines kept as `""` by `timing`), so pairing
   needs no `lyrics.txt` read and follows a clip's own first line (spec §4.2). Pairing is on lyric
   positions first, skipped lines dropped after, so a skipped line's partner is a single.
6. **Split test on frames:** `first_cur(b) − last_end(a) > round(couplet_max_gap_s · fps)`, or
   `first_cur(b) < first_cur(a)` (an allowed flagged word out of order) → two singles.
7. **First ink on the reveal frame.** Blur-in progress is `p = min(1, (n − reveal + 1) / fi)`,
   `fi = max(1, min(ceil(reveal_s · fps), end − reveal))`: ink on `reveal`, complete on
   `reveal + fi − 1 ≤ end` (spec §4.4, AC4). Other themes draw nothing on their reveal frame; they
   are untouched. Eased with `ease_out_cubic`; opacity `e`, blur radius `round(blur_px · (1 − e))`.
8. **Blur-in blurs the "L" masks, not RGBA.** A word's shadow and glyph are each one solid colour
   (`frames._solid`), so blurring the alpha alone is exact, with no premultiply. The whole-block
   exit blur (multicolour) goes through `karaoke.transformed` (premultiplied), as step 08.
9. **Two-pass block image: every shadow, then every glyph** (as `focus.line_image`'s glows under
   texts). A neighbour's blurring shadow never darkens a sung word's gold ink, which is also what
   the check reads.
10. **Caching:** blurred masks per `(word, kind, radius)` (L, ≤ 11 radii); full looks cached only
    at rest (`r == 0`, full opacity) per mix level; blur-in looks built per frame (each is used on
    about one frame). Everything drops when the visible block changes (one block at a time).
    Memory stays at one block's masks.
11. **Italic lean:** layout stays advance-based. A unit test proves the widest right lean plus
    left overhang of Cormorant Medium Italic (ASCII letters, 64-192 px) is narrower than the word
    gap, and the safe-zone check reads drawn pixels. Spec v1.0.1 edge row says so (was: "spacing
    counts the drawn ink").
12. **Short words and neighbour blur are read, not noted.** With (7) a 1-frame word is complete
    on its own frame, and with (9) a neighbour's glyph halo over gold ink is gold. Only frames
    where the block is leaving or another block is on screen become notes. Spec v1.0.1 edge row.
13. **Pad = `sprite_pad(theme) + 3 · ceil(blur_px)`** for every sprite and the block canvas, so no
    blur or shadow is clipped. Vertical placement keeps boxes `HALO = sprite_pad(theme)` inside
    y 380-1540. `max_width` 800 starts; the safe-zone check is never loosened, `max_width` goes
    down if it fails.
14. **Checks in `render/cinematic_check.py`**, reusing `check._colour_alpha`, `_ink`, `_Sample`,
    `_wanted`, `_zone_failure`, `SYNC_ON_MIN`, `SYNC_DROP_MIN` and `lofi_check.STATE_CURRENT_MIN`,
    `STATE_SPAN_MIN`. Rejected: parameterising `lofi_check._state_checks`, whose "before" test is
    the dim upcoming colour, meaningless on an empty frame.
15. **Font instanced once, not loaded variable.** `fontTools.varLib.instancer` (already a
    dependency) pins wght 500 into a static TTF; `FontSet` stays as is. Rejected: variable-font
    axes in `FontSet` for one theme.

## 3. Data Structures

### 3.1 `theme.py`

```
MOTIONS = ("reveal", "karaoke", "focus", "lofi", "cinematic")
# Cinematic only (spec 10): blur-in / blur-out, couplets. Reuses reveal_s (blur-in),
# accent_rgb (current), sung_in_s (fade to text_rgb), hold_s, fade_out_s (blur-out).
blur_px: float = 10.0            # blur-in start radius and blur-out end radius
couplet_gap: float = 0.5         # extra space between a couplet's two lines, × row pitch
couplet_max_gap_s: float = 4.0   # a pair sung further apart shows as two singles
```

`__post_init__`: `motion == "cinematic"` needs `accent_rgb` (as lofi); `blur_px`, `couplet_gap`,
`couplet_max_gap_s` ≥ 0 (a `ValueError` naming the field). Key-green guard covers the new colours.

```
# 800 px centred on 510 leaves ~50 px for shadow, blur and italic lean inside x 60-960 (plan 10 §2.13)
CINEMATIC = Theme(
    "cinematic", motion="cinematic",
    font=REPO_FONTS / "CormorantGaramond-MediumItalic.ttf", font_size=96, min_font_size=64,
    max_width=800, center_x=510, safe_zone=(60, 380, 960, 1540),
    text_rgb=(237, 230, 214), accent_rgb=(201, 166, 107),          # #EDE6D6 ivory, #C9A66B gold
    shadow_rgb=(0, 0, 0), shadow_alpha=0.7, shadow_radius=8, shadow_offset=(0, 3),
    reveal_s=0.5, sung_in_s=0.8, hold_s=2.0, fade_out_s=0.8, blur_px=10.0)
```

`THEMES` gains it last; `DEFAULT_THEME` unchanged (H-015).

### 3.2 `render/cinematic.py`

```
@dataclass
class Block:
    lines: tuple[LineLayout, ...]   # 1 or 2, shifted into place; line order (spec §4.2)
    words: list[WordPlan]           # every word, line order; boxes are the shifted ones
    line_of: dict[int, int]         # word index -> lyric line (labels, untimed words)
    line_first: dict[int, int]      # lyric line -> its first reveal: untimed words show from here
    first_cur: int                  # earliest reveal of the block: its first frame
    last_end: int                   # latest end frame
    settled: int                    # never leaves before this (= last_end, spec §4.3)
    enter: int = 0; rest: int = 0; leave: int = 0; stop: int = 0   # set by lifecycle.schedule
    notes: list[str] = field(default_factory=list)                 # cuts, too-tall splits
    name -> str                     # "line 3" or "lines 1-2" (property)
    label(wp) -> str                # 'word 4 "dekha" (line 1)'

CSprites = dict[int, tuple[Image.Image, Image.Image, int]]   # word -> (shadow L, glyph L, pad)

class CinematicCache:     # one block at a time; reset when the visible block changes
    block: int | None     # first lyric line of the visible block
    masks: dict[tuple[int, str, int], Image.Image]           # (word, "shadow"|"glyph", r) -> L
    looks: dict[tuple, tuple[Image.Image, Image.Image]]      # (word, level, r, ml) -> RGBA pair
    image: tuple[tuple, Image.Image] | None                  # (look key of all words, image)
    layer: tuple[tuple, Image.Image, tuple[int, int]] | None # ((image key, level, r), layer, pos)
```

A word's look key: `(level, r, ml)`: opacity level 0-`LEVELS`, blur radius px (int), mix level
0-`LEVELS` (0 ivory, `LEVELS` gold). `None` = not drawn.

### 3.3 `render/lifecycle.py`

Items are duck-typed (`LofiLine`, `Block`): `first_cur`, `settled`, `last_end`, `words`,
`notes`, `name`, `label(wp)`; `schedule` writes `enter`, `rest`, `leave`, `stop`.

## 4. Function Specifications

### `layout.py`
- `layout_line(words, line, theme, emphasis=frozenset(), size: int | None = None) -> LineLayout`:
  `size` given → only that size is tried; `LayoutError` as today if it does not fit.

### `render/lifecycle.py`
- `schedule(items: list, theme: Theme, n_frames: int, ahead: bool) -> None`: items already in
  time order. `ahead` = the item shows before its first word (lofi-minimal: entrance `enter_s`,
  preroll `preroll_s`); else no entrance. Hold `hold_s`, exit `fade_out_s`. Body = today's
  `plan_lofi` lines 101-144, including the final clamp to `n_frames`.

### `render/lofi.py`
- `plan_lofi`: builds and sorts lines as today, then `schedule(lines, theme, n_frames, ahead=not
  theme.typewriter)`.
- `LofiLine.name` → `f"line {self.layout.line + 1}"`; `LofiLine.label(wp)` → `label(wp, self.layout)`.

### `render/cinematic.py`
- `couplet_groups(lyric_lines: list[str]) -> list[tuple[int, ...]]`: lyric line indexes in
  groups of 2, then a leftover 1, per stanza; a line whose `strip()` is empty ends a stanza.
- `_stack(lays: list[LineLayout], theme: Theme) -> tuple[LineLayout, ...] | None`: §5.2; `None`
  if the block is taller than the safe zone allows.
- `plan_cinematic(doc, theme, n_frames, emphasis=frozenset(), layout_fn=None) ->
  tuple[list[Block], list[int]]`: §5.1. Raises `LayoutError` as `laid_out_lines` does.
- `blur_in_frames(wp: WordPlan, theme: Theme) -> int`: `fi` of §2.7 (timed words only).
- `word_look(b: Block, wp: WordPlan, n: int, theme: Theme) -> tuple[int, int, int] | None`: §5.3.
- `block_state(b: Block, n: int, theme: Theme) -> tuple[float, float]`: `(opacity, blur)`;
  `(0, 0)` off screen; `REST = (1.0, 0.0)` from `enter` to `leave`; from `leave`,
  `x = ease_in_quad((n − leave) / max(1, stop − leave))`, `(1 − x, blur_px · x)`.
- `readable(blocks, b, m, theme) -> bool`: `(m < b.enter or block_state(b, m) == REST)` and no
  other block with opacity > 0 on `m`.
- `build_sprites(blocks, theme) -> CSprites`: per word, `checked_mask(wp.text, wp.box, fonts,
  pad)` (red line 2, measured = drawn) and its shadow mask (blur `shadow_radius`, scaled by
  `shadow_alpha`, pasted at `shadow_offset`), as `lofi.build_sprites` minus the letter bands.
- `_mask(sprites, index, kind, r, cache) -> Image.Image`: the L mask blurred by `r` (r 0 = as
  built), cached.
- `_look(sprites, index, key, theme, cache) -> tuple[Image.Image, Image.Image]`: `(shadow RGBA,
  glyph RGBA)` = `_solid(shadow_rgb, mask_r)`, `_solid(mix_rgb(text, accent, ml), mask_r)`, alpha
  through `_LUTS[level]` below `LEVELS`; cached only when `r == 0 and level == LEVELS`.
- `block_image(b, sprites, n, theme, cache) -> tuple[Image.Image, int, int]`: canvas = union of
  boxes ± pad; all shadows, then all glyphs; reused while the look key is unchanged.
- `frame_parts(n, blocks, sprites, theme, cache) -> list`: §5.4.

### `render/cinematic_check.py`
- `cinematic_checks(result, blocks, theme, n_frames) -> list[str]`: block notes into
  `result.notes`, then §5.5.

### `render/check.py`
- `check_outputs`: `if theme.motion == "cinematic": from .cinematic_check import
  cinematic_checks; return fails + cinematic_checks(...)` (local import: no cycle, as lofi).
- `write_report`: `frame_checks` gains `f"reveal check of {timed} timed word(s) on the overlay's
  colour and alpha" if theme.motion == "cinematic"`.

### `render/__init__.py`
- `render()`: `elif theme.motion == "cinematic":` → `cinematic.plan_cinematic`,
  `cinematic.build_sprites`, `cinematic.CinematicCache()`, `cinematic.frame_parts`.

## 5. Logic Flow

### 5.1 `plan_cinematic`
1. `rows, skipped = laid_out_lines(doc, theme, layout_fn, emphasis)`; index rows by lyric line.
2. For each group of `couplet_groups(doc["lyrics"]["lines"])`, keep the lines present in `rows`.
3. Per kept line: `wps = word_plans(words, lay, theme)` (frames do not depend on position).
4. Pair `(a, b)`: if §2.6 split → two singles. Else sizes differ → re-layout both at
   `min(size_a, size_b)` through `layout_fn(..., size=s)`; `_stack([lay_a, lay_b])`; `None` →
   two singles and a note on the first: `"lines A-B: shown one at a time (the couplet is taller
   than the safe zone)"`.
5. Singles: `_stack([lay])` (a single always fits: 3 rows at most).
6. Rebuild `word_plans` on the shifted layouts; build `Block` (`line_first` = min reveal of
   each line's timed words; `first_cur`, `last_end`, `settled = last_end`).
7. Sort by `(first_cur, first lyric line)`; `schedule(blocks, theme, n_frames, ahead=False)`.

### 5.2 `_stack`
1. `fonts = font_set(theme, lays[0].font_size)`, `h = ascent + descent`,
   `pitch = round(h · row_spacing)` (as `layout._place`).
2. `gap = (pitch − h) + round(couplet_gap · pitch)`; spans `(top, bottom) = karaoke._block(lay)`.
3. `T = Σ(bottom − top) + gap · (len − 1)`; `y0, y1 = safe_zone[1] + HALO, safe_zone[3] − HALO`.
4. If `T > y1 − y0` → `None`.
5. `Y = min(round(anchor_y · height − T / 2), y1 − T)`; `Y = max(Y, y0)`.
6. Shift each line so its top lands at `Y`, then `Y += (bottom − top) + gap`.

### 5.3 `word_look(b, wp, n)`
1. Untimed: `None` if `n < b.line_first[line]`, else `(LEVELS, 0, 0)` (sharp ivory, never gold).
2. `n < wp.reveal` → `None`.
3. `fi = blur_in_frames(wp)`; `e = ease_out_cubic(min(1, (n − reveal + 1) / fi))`;
   `level = max(1, round(e · LEVELS))`, `r = round(blur_px · (1 − e))`.
4. `mix = 1` if `n < wp.end`, else `1 − smoothstep((n − end) / (sung_in_s · fps))`;
   `ml = round(mix · LEVELS)`.
5. Return `(level, r, ml)`. By §2.7, `e == 1` for every `n ≥ end`.

### 5.4 `frame_parts`
1. Visible block `b` = the one with `enter ≤ n < stop`; none → `band_parts([])`.
2. Block changed → reset the cache.
3. `(opacity, blur) = block_state(b, n)`; `level = min(LEVELS, round(opacity · LEVELS))`;
   `level ≤ 0` → empty frame.
4. `img, x0, y0 = block_image(...)`; `lkey = (image key, level, round(blur))`; miss →
   `karaoke.transformed(img, x0, y0, b.lines[0], 1.0, 0.0, level, theme, round(blur))`.
5. `band_parts([(layer, pos)])`.

### 5.5 `cinematic_checks`
1. Channel `c` = the one where `text_rgb` and `accent_rgb` differ most (blue: 214 vs 107);
   `span < STATE_SPAN_MIN` → the one failure, as lofi.
2. Per timed word with ink (`_ink`): `on = reveal + fi − 1`; `held = end − 1` if `> on`;
   `before = reveal − 1` if `reveal > 0`. Any of them not `readable` → note `"<label>: its block
   was leaving or another block was on screen on frame N, so it was not read (sung back to
   back)"`, skip.
3. `_colour_alpha(result, theme, c, _wanted(samples))`; decode error → one failure; frame count
   ≠ `n_frames` → failure.
4. `on` / `held`: alpha < `SYNC_ON_MIN` → `reveal: <label>: mean alpha A at frame N, expected >=
   200 once complete`; gold share `(text[c] − mean) / span < STATE_CURRENT_MIN` → `reveal:
   <label>: P% gold at frame N; expected 100%`.
5. `before`: alpha > `on − SYNC_DROP_MIN` → `reveal: <label>: mean alpha A at frame N, the frame
   before its first frame; expected no ink`.
6. `outside` → `_zone_failure`.

## 6. Edge Case Implementation Map

| Spec case | Mechanism | Where |
|---|---|---|
| Odd stanza | leftover 1-tuple | `couplet_groups` |
| Pair > 4 s apart; out of order | two singles | `plan_cinematic` §5.1 step 4 (§2.6) |
| Line with no timed word | dropped after pairing; partner single | `plan_cinematic` step 2 |
| Couplet too tall | `_stack` → `None`; singles + note | `_stack`, `plan_cinematic` step 4 |
| Clip mid-couplet | pairing from the clip's own `lyrics.lines` | `couplet_groups` input |
| Next block before `hold`; back to back; cut; gap; first word at 0:00 | lofi-typewriter rules | `lifecycle.schedule` (`ahead=False`) |
| Word shorter than one frame / than `reveal` | `fi = max(1, min(R, end − reveal))` | `blur_in_frames` |
| Italic lean | lean < word gap (test); pad holds it; zone check on pixels | §2.11, `build_sprites` pad |
| Devanagari / emoji | existing fallback chain in `FontSet` | `layout.py` (unchanged) |
| Marked word in a shrunk couplet | `word_fonts(theme, shared size, True)` | `layout_line(size=)`, `build_sprites` |
| Flagged word, `--allow-flagged` | sharp ivory from `line_first` | `word_look` step 1 |
| No timing, no `--allow-flagged` | refused | `load_for_render` (unchanged) |
| Line too long at min size | `LayoutError` | `layout_line` (unchanged) |
| Font file missing | `LayoutError: theme font not found` | `FontSet.__init__` (unchanged) |
| Blur halos on green mp4 | partial alpha keys like the shadow | `encode` (unchanged) |

## 7. File Layout

`render/lifecycle.py`: module docstring (spec 09 §4.2, spec 10 §4.3, D-020; the item fields) →
imports → `schedule`.

`render/cinematic.py`: docstring (spec, red lines: frames only from `word_plans`, strings only
through `checked_mask`) → imports → constants (`REST`) → `# --- Data` (`Block`, `CSprites`,
`CinematicCache`) → `# --- Timeline` (`couplet_groups`, `_stack`, `plan_cinematic`,
`blur_in_frames`, `word_look`, `block_state`, `readable`) → `# --- Sprites` (`build_sprites`,
`_mask`, `_look`) → `# --- Frames` (`block_image`, `frame_parts`). Target ≤ 280 lines.

`render/cinematic_check.py`: docstring (spec §4.6) → imports → `cinematic_checks` → `_samples`.

`tests/test_cinematic.py`: docstring → imports/helpers (`t(frame)`, `doc_of(lines, spans)`,
`tall_layout`, `sized_layout`) → `ThemeTest` → `CoupletTest` (AC3) → `RevealTest` (AC4) →
`BlockTest` (AC5) → `FramesTest` (AC8) → `ItalicTest` → `CinematicRenderTest` (AC6 unit) →
`CliThemeTest` (AC1).

## 8. Dependencies

- No new packages. `cinematic.py` imports `dataclasses`, `PIL.Image`, `ImageFilter`; from
  `..layout` `LineLayout`, `font_set`, `word_fonts`; `..theme` `Theme`; `.timeline` `WordPlan`,
  `_ceil_frame`, `laid_out_lines`, `word_plans`; `.karaoke` `_block`, `ease_in_quad`,
  `ease_out_cubic`, `smoothstep`, `sprite_pad`, `transformed`; `.frames` `_LUTS`, `LEVELS`,
  `_scaled`, `_solid`, `band_parts`, `checked_mask`; `.lofi` `mix_rgb`; `.lifecycle` `schedule`.
- `cinematic_check.py` imports `cinematic`, `lofi_check.STATE_CURRENT_MIN`, `STATE_SPAN_MIN`, and
  from `.check` as §2.14; `check.py` imports it inside `check_outputs` only.
- Font: `https://github.com/google/fonts/raw/main/ofl/cormorantgaramond/CormorantGaramond-Italic%5Bwght%5D.ttf`
  → `venv/Scripts/python -m fontTools.varLib.instancer <file> wght=500 -o
  fonts/CormorantGaramond-MediumItalic.ttf`; licence `.../ofl/cormorantgaramond/OFL.txt`. If the
  variable file has moved, the static `CormorantGaramond-MediumItalic.ttf` from the upstream
  CatharsisFonts/Cormorant release (same OFL).
- Conflicts found: `plan_lofi` lines 101-144 move (§2.2); `tests/test_karaoke.py:60` pins the
  `THEMES` list; `tests/test_layout.py:38-40` `LONG_FOR` / `ALL_THEMES`; tests' fake layouts
  (`low_layout`) take no `size` (only called with it when sizes differ, which fakes never do);
  lofi tests pass docs without `"lyrics"`, cinematic tests must include `lyrics.lines`.
- `CLAUDE.md` is 108 lines: room for the theme and module lines. `check.py` goes 354 → ~358.

## 9. Hard Boundaries

- [x] No blur, colour fade, hold, exit or cut changes `WordPlan.reveal` / `end` (red line 1).
- [x] A timed word has ink on `reveal`, none before, and is complete by `end`; untimed words are
      never gold.
- [x] Every drawn string goes through `checked_mask` (red line 2); nothing changes casing.
- [x] No upcoming word is drawn (H-017); at most one block on screen per frame.
- [x] The other five themes stay byte-identical (AC2), lofi included after the extraction.
- [x] No glow, stroke, backplate, scale, rise, drift, grain or beat input in `cinematic`.
- [x] The safe-zone check is never loosened; tune `max_width` instead.
- [x] `render()` never calls alignment; nothing is written outside `render/cinematic/`.

## 10. Acceptance Criteria (runnable)

`$PY` = `venv/Scripts/python`; song runs use the owner's `songs/khidki_s2`, `songs/khidki_s2_em`,
`songs/khidki_s2_lofi`.

1. **Theme choice:** `$PY -m lyric_engine.cli render songs/khidki_s2 --theme cinematic` → exit 0;
   `render/cinematic/` holds `overlay.mov`, `overlay_green.mp4`, `preview.mp4`, `report.md` with
   `Theme: cinematic`; `words.json` hash unchanged. `make songs/khidki_s2 --theme cinematic` →
   exit 0. Plain `render` → `render/soft-romantic-v2/`. Unit: `$PY -m unittest
   tests.test_cinematic -k Cli` → `OK`.
2. **Other themes untouched:** before any source edit, `git worktree add <scratch>/dev_tree dev`;
   `<scratch>/frame_hashes.py` hashes `frame_parts` bytes of the five existing themes at every
   10th frame of the three songs; `PYTHONPATH=<scratch>/dev_tree/src` → `dev.json`, branch →
   `branch.json`; `fc dev.json branch.json` → no differences (after §11 steps 2, 3 and 8).
3. **Couplets:** `$PY -m unittest tests.test_cinematic -k Couplet` → `OK` (groups for
   `["a","b","","c","d","e"]` = `[(0,1),(3,4),(5,)]`; > 4 s pair, skipped-line pair, too-tall pair
   (note) → singles; shared size = the smaller; line a's boxes above line b's by exactly `gap`;
   every box within y `380 + HALO`..`1540 − HALO`).
4. **Blur-in and colour:** `$PY -m unittest tests.test_cinematic -k Reveal` → `OK` (`None` on
   `reveal − 1`; `level > 0` on `reveal`; `(LEVELS, 0, LEVELS)` from `reveal + fi − 1` through
   `end`; `ml == 0` at `end + ceil(0.8·30)`; 1-frame and 3-frame words complete by `end`; flagged
   word `None` before `line_first`, `(LEVELS, 0, 0)` after, never `ml > 0`).
5. **Block life cycle:** `$PY -m unittest tests.test_cinematic -k Block` and `tests.test_lofi` →
   `OK` (≤ 1 block visible every frame; `F − 1` empty; `leave ≥ last_end`; hold, early leave,
   shrink, cut with notes, back to back, instrumental gap, first word at 0:00).
6. **Render checks:** `render --theme cinematic` on the three songs → every `report.md` says
   `**pass**`. Not vacuous: `$PY -m unittest tests.test_cinematic -k CinematicRender` → words
   drawn 10 frames late fail with `reveal:`; a safe zone of `(60, 380, 960, 1150)` fails with
   `safe zone:`.
7. **Emphasis:** `$PY -m unittest tests.test_layout -k Emphasis` → `OK`, cinematic included, at
   1.5 and 2.0.
8. **Text:** `$PY -m unittest tests.test_cinematic -k Frames` → a box/text mismatch raises
   `AssertionError` from `cinematic.build_sprites` before drawing.
9. **Speed:** wall time in `songs/khidki_s2/render/cinematic/report.md` ≤ 2 × the one in
   `render/soft-romantic/report.md` (both rendered on this branch, same session).
10. **Look:** the owner approves `songs/khidki_s2_em/render/cinematic/preview.mp4`; changes asked
    for become `theme.py` values.
11. **Gate:** `/gate` → unit tests `OK`, alpha proof passes.

## 11. Build order

1. AC2 baseline (dev worktree, `frame_hashes.py`, `dev.json`) before any source edit. Font:
   download, instance, licence into `fonts/`. Spec v1.0.1 wording (§2.11, §2.12).
2. Pure extraction: `render/lifecycle.py`, `plan_lofi` calls it → `tests.test_lofi` `OK`; AC2
   hashes identical.
3. `layout_line(size=)` + test → AC2 hashes identical.
4. `theme.py` fields, guards, `CINEMATIC` + `ThemeTest`; `test_karaoke` names; `test_layout`
   `ALL_THEMES` / `LONG_FOR` (shorter line if 2x emphasis cannot fit 800 px) → AC7.
5. `cinematic.py` timeline (§5.1-5.3) + `CoupletTest`, `RevealTest`, `BlockTest` (AC3-AC5).
6. `cinematic.py` sprites and frames + `FramesTest`, `ItalicTest` (AC8).
7. `cinematic_check.py`, `check.py` dispatch + report, `render/__init__.py` dispatch,
   `CinematicRenderTest`, `CliThemeTest` (AC1 unit, AC6 unit).
8. Real runs: AC1, AC2, AC6, AC9 on the three songs (tune `max_width` if the zone fails); D-021
   in `decision.md` (first ink on the reveal frame, couplet placement, pad/HALO); `CLAUDE.md`
   theme list and modules; gate; `/ship`; ask the owner for AC10.
