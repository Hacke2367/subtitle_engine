# Plan: Beat Pop Theme
**Spec:** `docs/specs/12_beat_pop_theme.md` (v1.0.0, approved by owner 2026-09-28)
**Branch:** `feature/beat-pop-theme` · **Decisions:** H-019, H-018, H-013, H-010, H-009, D-018, D-021, D-022
**Work split:** one developer, in the build order of §11 (no agents).

> **As built (2026-09-28), where it differs from the text below:**
> - `min_font_size` is 64, not 72: `MEDIUM_LINE` with a 2x word (spec 06 AC5 layout test) needs
>   more than 3 rows of 700 px at 72 (it fits at 66). Pop Karaoke and Cinematic also stop at 64.
> - A sung word is drawn with no shadow or stroke: on the first contact sheet the "H" of "Ham"
>   stuck its stroke out of the pill's round corner. The pill is its legibility layer. Corner
>   radius 0.2 × height (`PILL_ROUND`), not 0.3.
> - Sprites are 4 "L" masks (shadow, outline, glyph, pill) + pad, so the shadow and stroke keep
>   their own theme colours.
> - Beat sync (§2.14, §5.4.3) compares the drawn width on b − 1, b, b + 1 with the *planned*
>   width (`_extents` from the renderer's own sprites, each drawn word at its pop scale and pill
>   state, times the line scale), ±4 px (`BEAT_TOL`), where the planned rise on b is ≥ 6 px. The
>   first version skipped every beat near a pop and read only 6 of 32 beats on `khidki_s2`. This
>   one reads 30 of 32.
> - `readable(show, pl, m)` takes no theme.

Measured for this plan: Anton Regular 2.116 (Google Fonts, SIL OFL) at 110 px has ascent 130,
descent 37, space 26 px, cap top 28 px and descender bottom 145 px below the box top, full a–z,
and no Devanagari.

## 1. Files

| Action | File | Reason |
|---|---|---|
| MODIFY | `src/lyric_engine/theme.py` | motion `"beatpop"`; fields §3.1; guards; `BEAT_POP`; `THEMES` |
| CREATE | `src/lyric_engine/render/beatpop.py` | plan (lines, life cycle, beat and drop frames), pop / pill / bump / shake, sprites, frames |
| CREATE | `src/lyric_engine/render/beatpop_check.py` | pop sync, pill sync, beat sync, safe zone on the decoded overlay |
| MODIFY | `src/lyric_engine/render/__init__.py` | dispatch `"beatpop"`; `load_beats_for_render` (beats + drops, errors → `RenderError`) |
| MODIFY | `src/lyric_engine/render/karaoke.py` | `transformed(..., dx=0.0)`: horizontal shift for the shake |
| MODIFY | `src/lyric_engine/render/check.py` | dispatch `"beatpop"` in `check_outputs`; report wording |
| MODIFY | `src/lyric_engine/beats.py` | `DROPS_FILE`, `read_drops`, `snap` |
| MODIFY | `src/lyric_engine/timing.py` | `parse_time` (the `clip` time format as a plain function) |
| MODIFY | `src/lyric_engine/cli.py` | `_seconds` calls `timing.parse_time` (same messages) |
| CREATE | `fonts/Anton-Regular.ttf`, `fonts/OFL-Anton.txt` | theme font and its licence |
| CREATE | `tests/test_beatpop.py` | theme, pop, pill, bump/shake, drops, life cycle, frames, render + checks, CLI |
| MODIFY | `tests/test_layout.py`, `tests/test_karaoke.py` | `ALL_THEMES` / `LONG_FOR` / name list gain `beat-pop` (AC8) |
| MODIFY | `CLAUDE.md`, `docs/decision.md`, `docs/development_plan.md`, `docs/pending_work.md`, `docs/session_log.md` | theme list, modules, `drops.txt`, D-024, status |

`frames.py`, `timeline.py`, `lifecycle.py`, `focus.py`, `lofi.py`, `cinematic.py`,
`lofi_check.py`, `cinematic_check.py`, `encode.py`, `layout.py`, `align.py`, `workflow.py`: no
change.

## 2. Architecture Decisions

1. **A sixth motion family, `"beatpop"`, in `render/beatpop.py`.** One line at a time with
   words appearing as sung is Cinematic's shape (D-021 life cycle), but Beat Pop adds per-word
   scale, a pill layer, a stroke layer and a per-frame line transform driven by beats. Rejected:
   flags in `cinematic.py` (295 lines, couplets and blur keyed looks).
2. **The life cycle is `lifecycle.schedule(lines, theme, n, ahead=False)`, unchanged.** A line
   appears on its first word's frame, holds `hold_s`, exits over `fade_out_s`, and the frame
   before the next line's first word is empty (spec §4.2). `PopLine` carries the fields
   `schedule` reads.
3. **Word frames only from `timeline.word_plans`** (red line 1). Pop frames
   `fi = max(1, min(ceil(reveal_s·fps), end − reveal))`, progress `(n − reveal + 1) / fi`: ink
   on the reveal frame, at rest on `reveal + fi − 1 ≤ end − 1` (or on `reveal` when
   `end == reveal`), as D-021. Pill and black glyph on frames `reveal ≤ n < end` only. A word
   whose span floors to zero frames never gets the pill.
4. **Pop scale `pop_scale + (1 − pop_scale)·ease_out_back(x)`**, exactly 1.0 from `x ≥ 1`.
   `ease_out_back` overshoots its travel by 10%, so the peak is `1 + 0.1·(1 − 0.6)` = 1.04× rest
   (spec: at most 1.10×).
5. **Beat bump and drop shake are one per-frame line accent `(scale, dx, dy)`**, applied with
   `karaoke.transformed` about the line's centre (`center_x`, block centre), as every line
   transform in the repo is. Bump: latest beat frame `b ≤ n`, `d = n − b`,
   `D = max(1, ceil(bump_s·fps))`, scale `1 + (bump_scale − 1)·(1 − d/D)²` while `d < D`. Drop:
   latest drop frame `f ≤ n`, `S = ceil(shake_s·fps)`, `k = (1 − d/S)²` while `d < S`; scale
   `1 + (drop_scale − 1)·k`, offset `round(shake_px·k·SHAKE[d % 8])`. **Line scale =
   max(bump, drop), not the product**: a drop is snapped onto a beat, and 1.05 × 1.12 = 1.176
   would break the layout's margin. Peaks land on the beat or drop frame (instant rise, eased
   fall: spec §7). Scales are rounded to 3 decimals so frames repeat and cache.
6. **`SHAKE`: eight fixed unit offsets** `(1, .35) (−.8, −.6) (.45, .9) (−1, .15) (.7, −.7)
   (−.3, 1) (.9, .5) (−.6, −.9)`. Deterministic, so re-renders are byte-identical and the check
   can predict them; every component ≤ 1, so `|dx|, |dy| ≤ shake_px`.
7. **Beats and drops share the words' lead:** frame `floor((t − lead_s)·fps)`, kept in
   `[0, n)`, deduplicated (spec §4.4).
8. **`transformed` gains `dx: float = 0.0`** (last parameter). With `dx == 0` every caller's
   code path and pixels are unchanged. Karaoke, focus and cinematic keep calling it as today;
   AC2 hashes prove it.
9. **Sprites are "L" masks only** (under = shadow ∪ stroke, glyph, pill), coloured per line in
   `PopCache`. Every layer is one solid colour, so scaling an alpha is exact. RGBA copies of a
   whole song's words would hold hundreds of MB on this 8 GB machine. Draw order on the line
   canvas: every under (black), then the pill (mustard), then every glyph (white, or black while
   sung), so no stroke or shadow ever sits on a pill or a letter.
10. **Pill geometry** (per word, in sprite coordinates, pad `p`): x from `p − px` to
    `p + box.w + px`; y from `p + ascent + capTop − px` to `p + ascent + descBottom + px`, where
    `capTop = font.getbbox("H", anchor="ls")[1]` and `descBottom = font.getbbox("g",
    anchor="ls")[3]` of the word's primary font, and `px = round(pill_pad·size)`. Corner radius is
    `0.3 × height`. Drawn at 4× and reduced with LANCZOS once (anti-aliased). At 110 px:
    px 9, pill y 19–154 inside the 167 px box. The gap to the next word's box is 26 − 9 = 17 px,
    and the neighbour's stroke is 5.5 px, so a pill never touches a neighbour.
11. **Pad `pad_px(theme) = max(sprite_pad(theme), ceil(pill_pad·font_size·EMPHASIS_MAX) + 1)`**
    = 26 px at the start values (stroke 11 at 2×, shadow 3·4 + 3). The line canvas adds
    `ceil(0.05·widest box)` so a popping word's 1.04× overshoot is never clipped.
12. **Layout box: `max_width` 700, `center_x` 510, `anchor_y` 0.60, `max_rows` 3.** Horizontal:
    `700/2·1.12 + 26·1.12 + 14 + 8 (edge pop)` = 443 ≤ 450 (x 60–960 about 510). Vertical, three
    110 px rows: `(167 + 2·192)/2·1.12 + 29 + 14` = 352 about 1152 → y 800–1504 inside 380–1540.
    At `anchor_y` 0.62 the bottom reaches 1542. The render safe-zone check proves each song.
13. **The checks read alpha only** (one decode): ink, pill presence and line size are all alpha.
    The pill-only region (the pill minus the word's outline dilated by 2 px) holds nothing but
    the pill: the word's own shadow there is ≤ 40% and blurred. So alpha there tells pill from no
    pill. Geometry of each sample on its frame comes from the plan: `accent(show, m)` plus the
    exit state. A mask is mapped with the same rounding as `transformed`, then eroded 1 px for
    "must be solid" reads.
14. **Beat sync reads line width**: the frame's alpha bbox (alpha ≥ `SAFE_ALPHA_MIN`), the same
    bbox the safe-zone scan already computes every frame. A beat is *readable* when its line is
    on screen and not leaving on `b − 1, b, b + 1`, no other line shows, every word's look
    (pop scale, sung) is the same on the three frames, and the predicted width rise at `b` is
    ≥ 6 px. Readable → `W(b) − W(b−1) ≥ 3` and `W(b) ≥ W(b+1) − 1`. The rest go into one note
    with their count (spec §4.7: a note, never a silent pass).
15. **Beats and drops are loaded in `render/__init__.py`** (`load_beats_for_render`), next to
    `load_for_render`: it is the only place that touches song files. `plan_beatpop` takes plain
    second lists, so it is testable with no files and no librosa. `beats` is imported inside the
    `"beatpop"` branch (it pulls numpy); librosa loads only if `beats.json` must be computed.
16. **`drops.txt` lives in `beats.py`** (`read_drops`, `snap`): it is beat input, and a new
    module for ~35 lines is not worth a file. The time format is `timing.parse_time`, shared with
    `clip --from/--to`.

## 3. Data Structures

### 3.1 `theme.py`

New fields (defaults are inert for every other theme):

| Field | Default | `BEAT_POP` | Enforces |
|---|---|---|---|
| `pill_rgb` | `None` | `(255, 193, 7)` | mustard pill (H-019) |
| `pill_text_rgb` | `None` | `(0, 0, 0)` | sung word black on the pill |
| `pill_pad` | `0.08` | `0.08` | pill margin, × the word's size |
| `pop_scale` | `0.6` | `0.6` | pop start scale |
| `bump_scale`, `bump_s` | `1.05`, `0.15` | same | beat bump peak and fall |
| `drop_scale`, `shake_px`, `shake_s` | `1.12`, `14`, `0.5` | same | drop peak, shake reach and fall |
| `exit_scale` | `0.95` | `0.95` | exit shrink |

`MOTIONS` gains `"beatpop"`. Guards (in `__post_init__`): a beatpop theme needs `stroke_rgb`,
`pill_rgb` and `pill_text_rgb`; `0 < pop_scale ≤ 1`; `bump_scale ≥ 1`; `drop_scale ≥ 1`;
`0 < exit_scale ≤ 1`; `bump_s`, `shake_s`, `shake_px`, `pill_pad` ≥ 0 (added to the negatives
loop). Key green is already checked for every `*_rgb`.

```
BEAT_POP = Theme("beat-pop", motion="beatpop",
    font=REPO_FONTS / "Anton-Regular.ttf", font_size=110, min_font_size=72,
    max_width=700, center_x=510, anchor_y=0.60, safe_zone=(60, 380, 960, 1540),
    text_rgb=(255, 255, 255), stroke_rgb=(0, 0, 0), stroke_frac=0.05,
    pill_rgb=(255, 193, 7), pill_text_rgb=(0, 0, 0),
    shadow_rgb=(0, 0, 0), shadow_alpha=0.4, shadow_radius=4, shadow_offset=(0, 3),
    reveal_s=0.25, hold_s=0.8, fade_out_s=0.2)
```

### 3.2 `render/beatpop.py`

- `SHAKE`: the eight offsets of §2.6.
- `@dataclass PopLine`: `layout: LineLayout`, `words: list[WordPlan]`, `first_cur: int`,
  `last_end: int`, `settled: int` (= `last_end`), `enter/rest/leave/stop: int = 0`,
  `notes: list[str]`; `name` → `"line N"`; `label(wp)` → `'word i "text" (line N)'`
  (the `schedule` contract, `lifecycle.py` docstring).
- `@dataclass Show`: `lines: list[PopLine]`, `beats: list[int]`, `drops: list[int]` (frames,
  ascending), `notes: list[str]` (report lines: beats used, drops, drops with no line).
- `BSprites = dict[int, tuple[Image.Image, Image.Image, Image.Image, int]]`: word → (under L,
  glyph L, pill L, pad).
- `class PopCache`: `line: int | None`, `looks: dict` (word, look → coloured RGBA layers),
  `image: (key, img) | None`, `layer: (key, img, pos) | None`. Dropped when the line changes.

### 3.3 `beats.py`

- `DROPS_FILE = "drops.txt"`.

## 4. Function Specifications

### `timing.py`
- `parse_time(text: str) -> float`: `27`, `27.5`, `0:27`, `1:05.5` → seconds. Raises
  `ValueError("not a time: '<text>' (use 27, 0:27 or 1:05.5)")` for anything else (negative,
  more than one colon, not a number). `cli._seconds` converts it to `ArgumentTypeError` with the
  same text.

### `beats.py`
- `read_drops(path: Path, duration: float) -> list[tuple[str, float]]`: `[]` if the file is
  missing. Per line: text after `#` dropped, stripped, blanks skipped; `parse_time`, else
  `BeatsError("<path>, line K: not a time: '<text>' (use 45, 0:45 or 1:05.5)")`; `> duration`
  → `BeatsError("<path>, line K: <text> is after the song's end (<d> s)")`. Returns
  `(text, seconds)` sorted by time.
- `snap(times: list[float], beat_times: list[float]) -> list[float]`: each time → the nearest
  beat (`bisect`, ties to the earlier one); unchanged when `beat_times` is empty.

### `render/__init__.py`
- `load_beats_for_render(song_dir: Path, duration: float) -> tuple[list[float], list[float],
  list[str]]`: `beats.ensure_beats(song_dir)` and `read_drops`. `BeatsError` →
  `RenderError(str)`; `ModuleNotFoundError` → `RenderError("<name> is not installed: pip install
  -r requirements.txt")`. Returns beat times, snapped drop times, notes: `"beats: <tempo> BPM, <n>
  beats (beats.json computed|reused)"`, each `ensure_beats` note, each `"drop <text> → <t> s"`,
  and `"no beats: drops used as written"` when there are drops but no beats; a tempo-0 file adds
  `"no beats: no bump"`.
- `render`: new branch `theme.motion == "beatpop"`: load, `beatpop.plan_beatpop(...)`,
  `show.notes[:0] = notes`, `beatpop.build_sprites`, `beatpop.PopCache()`,
  `beatpop.frame_parts`.

### `render/karaoke.py`
- `transformed(img, x0, y0, lay, scale, dy, level, theme, blur=0.0, dx=0.0)`: the transform
  branch also runs when `dx != 0`; new x is `round(cx + dx + (x0 − cx)·scale)`.

### `render/beatpop.py`
- `plan_beatpop(doc, theme, n_frames, emphasis=frozenset(), beats=(), drops=(), layout_fn=None)
  -> tuple[Show, list[int]]`: §5.1.
- `pop_frames(wp, theme) -> int`: §2.3.
- `word_look(pl, wp, n, theme) -> tuple[float, bool] | None`: `(pop scale, sung)`, or None when
  not drawn. An untimed word is `(1.0, False)` from `pl.first_cur`, never popping, never sung.
- `accent(show, n, theme) -> tuple[float, int, int]`: `(scale, dx, dy)` from beats and drops
  (§2.5). `(1.0, 0, 0)` with none active.
- `line_state(show, pl, n, theme) -> tuple[float, int, int, float]`: `(scale, dx, dy,
  opacity)`; opacity 0 outside `[enter, stop)`. From `leave`: `x = ease_in_quad((n − leave) /
  max(1, stop − leave))`, opacity `1 − x`, scale × `1 + (exit_scale − 1)·x`.
- `readable(show, pl, m, theme) -> bool`: `m < pl.enter`, or `pl.enter ≤ m < pl.leave`; and no
  other line has opacity > 0 on `m`.
- `pad_px(theme) -> int`: §2.11.
- `pill_mask(fonts: FontSet, box: WordBox, pad: int, theme) -> Image.Image`: §2.10.
- `build_sprites(show, theme) -> BSprites`: per word, `checked_mask` (red line 2), outline via
  `layout.word_mask(stroke=stroke_px)`, shadow of the outline (blur `shadow_radius`, ×
  `shadow_alpha`, offset), under = `ImageChops.lighter(shadow, outline)` (both black), pill mask.
- `frame_parts(n, show, sprites, theme, cache) -> list`: §5.3.

### `render/beatpop_check.py`
- `beatpop_checks(result, show, theme, n_frames) -> list[str]`: §5.4.
- `_map(mask: Image.Image, rest_xy: tuple[int, int], pl, show, m, theme) -> tuple[Image.Image,
  tuple[int, int]]`: a rest-position mask moved to frame `m` (line scale about the line centre,
  shake), with `transformed`'s rounding; NEAREST resize.

### `render/check.py`
- `check_outputs`: `if theme.motion == "beatpop"`: import `beatpop_check` locally (as lofi and
  cinematic), return `fails + beatpop_checks(...)`.
- `write_report`: `frame_checks` for beatpop: `"pop and pill check of {timed} timed word(s) and
  beat check of the line's size, on the overlay's alpha"`.

## 5. Logic Flow

### 5.1 `plan_beatpop`
1. `rows, skipped = laid_out_lines(doc, theme, layout_fn, emphasis)` (red line 2 assertion
   inside).
2. Per row: `wps = word_plans(words, lay, theme)`; timed = reveal not None;
   `PopLine(lay, wps, min reveal, max end, max end)`.
3. Sort by `(first_cur, line)`; `schedule(lines, theme, n_frames, ahead=False)`.
4. `beats` → frames `floor((t − lead)·fps)` in `[0, n)`, sorted, unique; the same for `drops`.
5. For each drop frame with no line having `enter ≤ f < stop`: note `"drop at <mm:ss.s>: no
   line on screen, nothing shaken"`.
6. Return `Show(lines, beat_frames, drop_frames, notes)`, `skipped`.

### 5.2 `word_look` and `accent`
- `word_look`: untimed → None before `pl.first_cur`, else `(1.0, False)`. Timed: None if
  `n < reveal`; `x = (n − reveal + 1) / pop_frames`; scale `1.0` if `x ≥ 1`, else
  `round(pop_scale + (1 − pop_scale)·ease_out_back(x), 3)`; sung `reveal ≤ n < end`.
- `accent`: `bisect_right(beats, n) − 1` → latest beat; the same for drops; §2.5 formulas;
  returns `(max(bump, drop) rounded to 3, dx, dy)`.

### 5.3 `frame_parts`
1. `pl` = the line with `enter ≤ n < stop`, else `band_parts([])`.
2. Line changed → reset the cache.
3. `scale, dx, dy, op = line_state(...)`; `level = min(LEVELS, round(op·LEVELS))`; ≤ 0 → empty.
4. `key = tuple(word_look(...) for wp in pl.words)`; if the cached image key differs, build
   the canvas (§2.11 margin): for each drawn word, its three layers coloured (cached per
   `(word, scale)`; a popping word's masks are resized by its scale about its box centre,
   BICUBIC), pasted in the §2.9 order; the pill and black glyph only when sung.
5. `lkey = (key, scale, dx, dy, level)`; if it differs from the cached layer:
   `transformed(img, x0, y0, pl.layout, scale, dy, level, theme, dx=dx)`.
6. `band_parts([(layer, pos)])`.

### 5.4 `beatpop_checks`
1. `result.notes += show.notes + [every line's notes]`.
2. Samples per timed word with ink (`_ink`), each only where `readable(show, pl, m)` holds
   for all its frames, else one note `"<label>: its line was leaving or another line was on
   screen on frame <m>, so it was not read"`:
   - **pop before** `reveal − 1` (if ≥ 0): solid pixels (alpha ≥ 128) in the word's mapped
     box ≤ 2% of its rest ink pixels → else `"pop: <label>: ink on frame <m>, the frame before
     it is sung"`.
   - **pop on** `reveal`: ≥ 25% of its rest ink pixels → else `"pop: <label>: no ink on frame
     <m>, where it is sung"`.
   - **complete** `c = reveal + pop_frames − 1`: mean alpha over the mapped, eroded ink ≥
     `SYNC_ON_MIN` → else `"pop: <label>: not complete on frame <c>"`.
   - **pill on** `c` when `c < end`: mean alpha over the mapped, eroded pill-only mask ≥
     `SYNC_ON_MIN` → else `"pill: <label>: no pill on frame <c>, while it is sung"`.
   - **pill off** `end` (when `end` is readable and the line is still on screen) and
     `reveal − 1`: mean ≤ pill-on mean − `SYNC_DROP_MIN` → else `"pill: <label>: pill on frame
     <m>, outside its span"`.
3. Beat samples (§2.14) at `b − 1, b, b + 1`; failures `"beat: frame <b>: line width
   <W(b−1)> → <W(b)> → <W(b+1)> px, expected a peak on the beat"`; unreadable count →
   `"beat check: <k> of <m> beats with a line on screen not read (a word popping or a line
   change next to the beat)"` when `k > 0`.
4. One alpha decode (`alphaextract,format=gray`) visits every frame: sample crops on wanted
   frames, bbox (the `_SAFE_LUT` point + `getbbox`) on beat frames ± 1, safe zone on every
   frame (`_zone_box`). Frame count mismatch → failure as in the other checks.

## 6. Edge Case Implementation Map

| Spec §5 case | Mechanism | Location |
|---|---|---|
| No `beats.json` | `ensure_beats` computes and saves; note says computed | `render.load_beats_for_render` |
| `beats.json` invalid | `BeatsError` → `RenderError`; nothing rendered | same |
| No beats (tempo 0) | empty beat frames → `accent` bump 1.0; drops unsnapped; notes | same, `plan_beatpop` |
| librosa missing | `ModuleNotFoundError` → `RenderError` in the beatpop branch only | same |
| No `drops.txt` | `read_drops` → `[]` | `beats.read_drops` |
| Bad line / after the end | `BeatsError` with file and line → `RenderError` | `beats.read_drops` |
| Drop with no line | nothing drawn (no line); note | `plan_beatpop` §5.1.5 |
| Two drops within the shake | latest drop frame wins (`bisect`) | `accent` |
| Beats faster than the fall | latest beat restarts the bump | `accent` |
| Beat on a pop frame | line scale × word scale (independent layers) | `frame_parts` |
| Word shorter than the pop | `pop_frames` shrinks to the span | `pop_frames` |
| Consecutive words | pill on `[reveal, end)` per word: the next starts on the same frame | `word_look` |
| Flagged word | `(1.0, False)` from the line's first frame | `word_look` |
| Line with no timed word | `laid_out_lines` skips it (existing report line) | — |
| 2.0× word + drop | layout box §2.12; safe-zone check on every frame | `theme.py`, check |
| Clip folder | nothing special: `ensure_beats` on the clip's audio; its own `drops.txt` if any | — |

## 7. File Layout

`render/beatpop.py`: docstring (spec, H-019, red lines: word frames only from `word_plans`,
beats and drops decoration only, `checked_mask`); imports; `SHAKE`; data (`PopLine`, `Show`,
`BSprites`, `PopCache`); timeline (`plan_beatpop`, `pop_frames`, `word_look`, `accent`,
`line_state`, `readable`); sprites (`pad_px`, `pill_mask`, `build_sprites`); frames
(`_layers`, `line_image`, `frame_parts`). Target ≤ 290 lines.

`render/beatpop_check.py`: docstring; imports; `beatpop_checks`; `_samples`; `_beat_samples`;
`_map`. Target ≤ 200 lines.

`tests/test_beatpop.py`: helpers (`t(frame)`, `doc_of`, `show_of`, `beats_json(song, times)`);
`ThemeTest`, `PopTest` (AC3), `PillTest` (AC4), `AccentTest` (AC5), `DropsTest` (AC6),
`LifeTest`, `FramesTest` (AC9), `BeatPopRenderTest` (AC1, AC7), `CliThemeTest` (AC1).

## 8. Dependencies

- `beatpop.py` imports: `bisect`, `math`, `dataclasses`; PIL `Image`, `ImageChops`,
  `ImageDraw`; `..layout` (`LineLayout`, `WordBox`, `FontSet`, `word_fonts`, `word_mask`);
  `..theme` (`EMPHASIS_MAX`, `Theme`); `.frames` (`LEVELS`, `_scaled`, `_solid`, `band_parts`,
  `checked_mask`); `.karaoke` (`_block`, `ease_in_quad`, `ease_out_back`, `sprite_pad`,
  `stroke_px`, `transformed`); `.lifecycle` (`schedule`); `.timeline` (`WordPlan`,
  `_ceil_frame`, `_floor_frame`, `laid_out_lines`, `word_plans`).
- `beatpop_check.py` imports `.check` helpers (`SYNC_ON_MIN`, `SYNC_DROP_MIN`, `SAFE_ALPHA_MIN`,
  `_SAFE_LUT`, `_decode_cmd`, `_ink`, `_stream`, `_zone_box`, `_zone_failure`) and `beatpop`.
  `check.py` imports it locally (circular import, as `lofi_check`).
- `render/__init__.py` → `beats` (lazy, beatpop branch only) → librosa only when computing.
- Conflicts: none. `transformed`'s new parameter is last and defaults to 0. `parse_time` is new;
  `cli._seconds` keeps its messages.
- Fonts: Anton Regular from `github.com/google/fonts/raw/main/ofl/anton/` (static TTF, no
  instancing needed), `OFL.txt` saved as `fonts/OFL-Anton.txt`.

## 9. Hard Boundaries

- [x] No word frame comes from anything but `word_plans`; beats and drops never touch
  `reveal`/`end` (red line 1).
- [x] No word ink before its reveal frame; the pill and the black glyph only on
  `reveal ≤ n < end`; untimed words never pop or get the pill.
- [x] Every drawn string goes through `checked_mask` (red line 2); no case change.
- [x] `words.json`, `beats.json`, `drops.txt` and `lyrics.txt` are read, never written, by render.
- [x] The other six themes' frames are byte-identical to `dev` (AC2).
- [x] No hue-120 colour; overshoot ≤ 10%; two fonts at most (Anton + existing fallbacks).
- [x] librosa is never imported by render unless `beats.json` must be computed.

## 10. Acceptance Criteria (runnable)

`$PY` = `venv/Scripts/python`. Songs: `khidki_s2`, `khidki_s2_em`, `khidki_full` (with
`songs/khidki_full/drops.txt`).

1. **Theme choice:** `$PY -m lyric_engine.cli render songs/khidki_s2 --theme beat-pop` → exit
   0, outputs in `songs/khidki_s2/render/beat-pop/`; sha256 of `words.json` and `beats.json`
   equal before and after. Unit: `$PY -m unittest tests.test_beatpop -k CliTheme` → `OK`
   (`make --theme beat-pop` in a temp song; plain `render` default still `soft-romantic-v2`).
2. **Other themes unchanged:** before any source edit, `git worktree add <scratch>/dev_tree dev`.
   `<scratch>/frame_hashes.py` hashes `frame_parts` bytes of the six existing themes at every
   5th frame of `khidki_s2` and `khidki_s2_em`, run with `PYTHONPATH=<scratch>/dev_tree/src` →
   `dev.json` and on the branch → `branch.json`. `fc dev.json branch.json` → no differences.
3. **Pop:** `-k PopTest` → `OK` (no look before reveal; `(q, True)` with `q < 1` on reveal; 1.0
   on `reveal + fi − 1 ≤ end − 1`; 1- and 3-frame words complete by their end; max over the pop
   ≤ 1.10).
4. **Pill:** `-k PillTest` → `OK` (sung exactly on `[reveal, end)`; none in a gap; never for an
   untimed word; consecutive words hand over on one frame; black glyph pixels on the pill in a
   drawn frame; pill mask inside the box, 17 px clear of the next box at 110 px).
5. **Bump and shake:** `-k AccentTest` → `OK` (peak `bump_scale` on each beat frame, 1.0 from
   `D` frames after; drop peak `drop_scale` and offsets ≤ `shake_px` ending by `S`; max not
   product on a shared frame; no layer drawn for a beat or drop with no line).
6. **Drops:** `-k DropsTest` → `OK` (`45`, `0:45`, `1:05.5`, blank, `# comment`, inline
   comment; nearest-beat snap, ties earlier; bad text and after-the-end → `BeatsError` with the
   line number; missing file → `[]`).
7. **Render checks:** `render --theme beat-pop` on the three songs → every `report.md` says
   **pass**. Unit `-k BeatPopRender` (a synthetic song with a hand-written `beats.json` and
   `drops.txt`, so no librosa) → `checks == []`, and each of: reveals +5 frames in the plan →
   `pop:`; ends −5 frames → `pill:`; beat frames +3 → `beat:`; zone `(60, 380, 960, 1150)` →
   `safe zone:`.
8. **Emphasis:** `$PY -m unittest tests.test_layout -k Emphasis` → `OK` with `beat-pop` in
   `ALL_THEMES` at 1.5 and 2.0.
9. **Text:** `-k FramesTest` → a box/text mismatch raises `AssertionError` from
   `beatpop.build_sprites` before drawing.
10. **Speed:** `render/beat-pop/report.md` wall time of `khidki_s2` ≤ 2 × its
    `render/soft-romantic/report.md` wall time, both rendered on this branch in one session.
11. **Look (owner):** `songs/khidki_full/render/beat-pop/preview.mp4`: bumps on the beat, shake
    on the written drops, look approved. Changes become `theme.py` values.
12. **Gate:** `/gate` → unit tests `OK`, alpha proof passes.

## 11. Build order

1. AC2 baseline: dev worktree, `frame_hashes.py`, `dev.json`. Anton + licence into `fonts/`.
2. `timing.parse_time`, `cli._seconds`; `beats.read_drops`, `snap` + `DropsTest` (AC6).
3. `transformed(dx=)` → AC2 hashes identical.
4. `theme.py` fields, guards, `BEAT_POP` + `ThemeTest`; `test_karaoke` names; `test_layout`
   `ALL_THEMES` / `LONG_FOR` (AC8).
5. `beatpop.py` timeline (§5.1-5.2) + `PopTest`, `PillTest`, `AccentTest`, `LifeTest`.
6. `beatpop.py` sprites and frames + `FramesTest` (AC9).
7. `render/__init__.py` branch + `load_beats_for_render`; `beatpop_check.py`; `check.py`
   dispatch and report; `BeatPopRenderTest`, `CliThemeTest` (AC1, AC7 unit).
8. Real runs: `khidki_s2`, `khidki_s2_em`, `khidki_full` (+ `drops.txt`), AC2, AC7, AC10; D-024;
   `CLAUDE.md`; gate; `/ship`; ask the owner for AC11.
