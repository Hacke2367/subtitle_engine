# Plan: Soft Romantic Renderer
**Spec:** `docs/specs/03_soft_romantic_render.md` (v1.0.0, Claude-approved under H-008)
**Branch:** `feature/soft-romantic-render` (stacked on step 02, D-011)
**Work split:** agent **Y** (layout + fonts), agent **R** (render pipeline + output check), integrator (theme, CLI, real run).

## 1. Files

| Action | File | Owner | Reason |
|---|---|---|---|
| DONE | `src/lyric_engine/theme.py` | integrator | `Theme` dataclass + `SOFT_ROMANTIC` (all look numbers in one place) |
| MODIFY | `src/lyric_engine/layout.py` | **Y** | contract dataclasses exist; add `FontSet`, `word_mask`, `layout_line` |
| CREATE | `tests/test_layout.py` | **Y** | fallback, masks, wrapping, shrink, refusal |
| MODIFY | `requirements.txt` | **Y** only | pin `fonttools` |
| MODIFY | `src/lyric_engine/render.py` | **R** | load/refuse, timeline, sprites, compositor, one-pass ffmpeg, output check, report |
| CREATE | `tests/test_render.py` | **R** | timeline maths, refusals, compose, 2 s end-to-end smoke |
| MODIFY | `src/lyric_engine/cli.py` | integrator | `render` subcommand |
| MODIFY | docs, `CLAUDE.md` | integrator | tracking |

## 2. Architecture Decisions

1. **Frames drawn once, encoded three ways in one ffmpeg process.** Raw RGBA goes to stdin; `split=3` feeds the alpha `.mov`, the green mp4 and the audio preview. Rejected: three passes (3× render time), or a PNG sequence on disk (5 400 files for 3 minutes).
2. **Sprites pre-rendered per word** (glow blur once), then faded per frame through a cache quantised to 1/32 opacity steps. That keeps a frame to a few `alpha_composite` calls.
3. **Straight alpha by construction:** each sprite is a solid colour layer with the mask as its alpha (the step 01 fix). No dark fringes.
4. **Word geometry comes only from `layout.py`**, and the mask used to measure a word is the mask used to draw it. That means a single source of truth for positions, so text never shifts between measurement and drawing.
5. **Fallback by font cmap (fontTools)**, not by render-and-compare. It is exact, and a missing glyph is detected before anything is drawn.
6. **One line on screen at a time:** a line's end is clamped to the next line's first reveal, so lines can't collide.
7. **The output check decodes the alpha plane once** (`alphaextract`, raw gray on a pipe) and samples the needed frames, instead of one ffmpeg call per frame.
8. **Alpha codec table copied from D-005** (`scripts/alpha_proof.py` is a script, not importable). Default `theme.alpha_codec = "prores"` stays provisional (D-011).

## 3. Data Structures

`layout.py` (contract, already written): `WordBox(index, text, x, y, w, h)`,
`LineLayout(line, font_size, words: tuple[WordBox, ...])`, `LayoutError`.

`render.py` (R):

```python
ALPHA_CODECS = {   # D-005 formats; output always overlay.mov
    "prores": ("format=yuva444p10le", ["-c:v", "prores_ks", "-profile:v", "4444", "-alpha_bits", "16",
                                        "-vendor", "apl0", <BT.709 tags>]),   # vf gets TO_BT709 prefix
    "png":    ("format=rgba", ["-c:v", "png"]),
    "qtrle":  ("format=argb", ["-c:v", "qtrle"]),
}

class RenderError(RuntimeError): ...

@dataclass
class WordPlan:
    box: WordBox
    reveal: int | None      # first frame of the reveal; None = untimed (static, --allow-flagged only)
    end: int | None         # frame of the word's end (end − lead); glow holds until here

@dataclass
class LinePlan:
    layout: LineLayout
    first: int              # first visible frame
    stop: int               # first frame no longer visible (exclusive), ≤ next line's first
    fade_start: int         # line opacity falls linearly from here to 0 at `stop`
    words: list[WordPlan]

@dataclass
class RenderResult:
    render_dir: Path
    outputs: dict[str, Path]        # "overlay", "green", "preview"
    frames: int
    wall_s: float
    skipped_lines: list[int]        # lines with no timed word (not shown)
    checks: list[str]               # output-check failures; [] = pass
```

## 4. Function Specifications

**`layout.py` (Y)**

| Function | Behaviour | Raises |
|---|---|---|
| `class FontSet(theme, size)` | Loads `theme.font` + `theme.fallback_fonts` at `size` (`.ttc` → index 0). Coverage from a fontTools `getBestCmap()`, read once per font file (cache). Attributes `size`, `ascent`, `descent` (primary `getmetrics()`), `space` (primary advance of `" "`). | `LayoutError` if the primary font is missing |
| `FontSet.runs(text) -> list[tuple[str, FreeTypeFont]]` | Consecutive characters grouped by the first font whose cmap has them. | `LayoutError(f"no font has {ch!r} (U+{ord(ch):04X}) in word {text!r}")` |
| `FontSet.advance(text) -> float` | Sum of `getlength` per run | — |
| `font_set(theme, size) -> FontSet` | `lru_cache`d constructor | — |
| `word_mask(text, fonts, pad=0) -> Image("L")` | Size `(ceil(advance) + 2·pad, ascent + descent + 2·pad)`. Runs drawn left to right with `anchor="ls"` at baseline `pad + ascent`, fill 255. | via `runs` |
| `layout_line(words: list[tuple[int, str]], line, theme) -> LineLayout` | Sizes from `theme.font_size` down to `theme.min_font_size` in steps of `theme.font_step`: greedy-wrap by advance + space into rows ≤ `max_width`; accept the first size with ≤ `max_rows` rows. Rows centred at x = (width − row_width)/2. Block centred at y = `anchor_y`·height, row pitch = round((ascent + descent)·`row_spacing`). Each `WordBox`: x/y = top-left of its pad-0 mask; w/h = mask size; text verbatim. | `LayoutError(f"line {line+1} does not fit …")` |

**`render.py` (R)**

| Function | Behaviour | Raises |
|---|---|---|
| `load_for_render(song_dir, *, allow_flagged) -> (doc, audio)` | `align.song_paths`, `timing.load_words(song/words.json)`, `timing.validate(doc, lyrics, audio)`. Any error → refuse (a stale doc says to re-run `align --overwrite`). Flagged words without `allow_flagged` → refuse, listing `i`, text, line+1, reasons, with a hint. | `RenderError` |
| `plan_timeline(doc, theme, n_frames, layout_fn=layout_line) -> (list[LinePlan], skipped)` | Group words by `line` (skip blank lines). reveal = max(0, floor((start − lead)·fps)); end = max(reveal, floor((end − lead)·fps)). Untimed word → `reveal=None` (only reachable with allow_flagged). A line with no timed word → skipped. first = min reveal; natural stop = ceil((max end_s + hold_s)·fps); stop = min(natural, next line's first, n_frames); fade_start = max(first, stop − round(fade_out_s·fps)). | `LayoutError` passes through |
| `word_state(wp, n, theme) -> (opacity, rise_px, glow)` | Untimed: (1, 0, 0). Before reveal: (0, 0, 0). Reveal progress p = (n − reveal)/(reveal_s·fps), clamped 0..1; ease = smoothstep; opacity = ease; rise = rise_px·(1 − ease). Glow: ramps 0→1 over glow_in from reveal, 1 until `end`, then falls to 0 over glow_out. | — |
| `line_opacity(lp, n) -> float` | 0 outside [first, stop); 1 before fade_start; then linear to 0 at stop | — |
| `build_sprites(lines, theme) -> dict[int, (text_sprite, glow_sprite, pad)]` | pad = 3·glow_radius. Text sprite = shadow (blurred mask, shadow_rgb, α·shadow_alpha, offset) under text (text_rgb + mask). Glow = glow_rgb + min(255, blurred mask·glow_boost). Asserts the sprite's word text == WordBox text == doc text (red line 2). | — |
| `compose_frame(n, lines, sprites, theme) -> bytes` | Returns a cached all-zero frame when nothing is visible. Otherwise: transparent canvas; for each word of the visible line, glow (α × glow × line_op), then text (α × opacity × line_op) at (x − pad, y − pad − rise). Uses the faded-sprite cache. Output RGBA bytes. | — |
| `render(song_dir, *, codec=None, allow_flagged=False, theme=SOFT_ROMANTIC) -> RenderResult` | n_frames = ceil(duration·fps). Starts one ffmpeg process: `-f rawvideo -pix_fmt rgba -s WxH -r fps -i -` plus `-i audio`; `filter_complex`: `split=3`, then alpha (`TO_BT709` + codec vf for prores, or the codec vf), green (`color=key_green` bg + `overlay=format=rgb` + BT.709 yuv420p + libx264 crf 16), preview (`color=preview_bg` + overlay + `scale=540:960` + yuv420p + libx264 veryfast crf 26 + aac from input 1, `-shortest`). Writes frames to stdin; on failure kills ffmpeg, deletes partial outputs and raises with the stderr tail. Then runs `check_outputs` and writes `render/report.md`. | `RenderError` |
| `check_outputs(result, lines, theme, n_frames) -> list[str]` | ffprobe: overlay & green 1080×1920, `30/1`, `nb_read_frames == n_frames`, no audio; the overlay pix_fmt has alpha; the preview is 540×960 with audio. Sync: decode the overlay alpha once (`-vf alphaextract,format=gray -f rawvideo -`). For each timed word: mean alpha over the pixels where its pad-0 mask is 255 must be ≥ 200 at frame min(reveal + ceil(reveal_s·fps) + 1, stop − fade frames − 1), and at least 100 lower at frame reveal − 1 (skipped when reveal = 0). Each failure message names the word. | — |

## 5. Logic Flow (`render`)

1. `doc, audio = load_for_render(...)`; `duration = align.probe_duration(audio)`; `n = ceil(duration·fps)`.
2. `lines, skipped = plan_timeline(...)`, then `sprites = build_sprites(...)`.
3. Clear `render/` of the three output names, start ffmpeg, and write frames 0..n−1.
4. Close stdin and wait. Non-zero → clean up and raise.
5. `checks = check_outputs(...)`; write the report; return the result. The CLI prints the outputs and checks, and exits 0 only when checks == [].

## 6. Edge Case Map

| Spec edge case | Mechanism | Where |
|---|---|---|
| Flagged words | refuse with the list, or `--allow-flagged` | `load_for_render` |
| Untimed words (allowed) | `reveal=None` → static, no glow | `plan_timeline`, `word_state` |
| Line without timed words | skipped + reported | `plan_timeline`, report |
| Stale / invalid words.json | validator errors → refuse | `load_for_render` |
| Overlong word / too many rows | `LayoutError` naming the line | `layout_line` |
| Missing glyph | `LayoutError` naming the char and word | `FontSet.runs` |
| Audio longer than the lyrics | transparent frames up to n | `compose_frame` |
| Lines too close | stop clamped to the next first | `plan_timeline` |
| ffmpeg failure | kill, delete partials, raise | `render` |

## 7. Dependencies

- New: `fonttools` (pinned by Y). Existing: Pillow, ffmpeg 8.0.1 (libx264, prores_ks, png, qtrle, aac).
- `render` → `layout`, `theme`, `timing`, `align.song_paths/probe_duration`. `layout` → `theme` (types) and fontTools.
- Conflicts: `render.py` and `layout.py` stubs are replaced. `cli.py` gains `render`.

## 8. Hard Boundaries

- [x] No time invented: every reveal/glow frame derives from that word's own `start`/`end` (minus the uniform lead). (`timeline.plan_timeline`; untimed words stay static; timeline tests.)
- [x] Drawn text == `words.json` text (asserted when sprites are built). (Also asserted in `plan_timeline`; tested with a lower-casing layout.)
- [x] Refuses on flagged/stale input unless explicitly allowed (flagged only; never stale). (Tests: flagged listed; stale refused even with `--allow-flagged`.)
- [x] Writes only inside `songs/<song>/render/`; `words.json` untouched. (Real run: sha256 unchanged; end-to-end test checks the file set.)
- [x] Tests run offline without song files; the end-to-end smoke test uses a synthetic 2 s song in a temp dir.
- [x] Agents edit only their own files; no git writes. (Integrator later added balanced wrap to `layout.py` (D-012) and split `render.py` into `render/` (D-013).)

## 9. Acceptance Criteria (runnable)

| # | Command | Pass |
|---|---|---|
| 1 | `venv/Scripts/python -m unittest discover -s tests -t .` | OK |
| 2–4 | `venv/Scripts/python -m lyric_engine.cli render songs/khidki` | 3 outputs; `checks: pass` (ffprobe + sync on every timed word) |
| 5 | test in `test_render.py` + the assertion in `build_sprites` | pass |
| 6 | the render report's wall time for the 30 s clip | ≤ 180 s |
| 7 | sha256 of `songs/khidki/words.json` before and after; render writes only under `render/` | equal |
| 8 | owner: `preview.mp4` look, CapCut import | pending (H-008) |
