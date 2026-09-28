# Implementation Plan: Background Layer + Romantic Room
**Spec:** `docs/specs/17_bg_romantic_room.md` v1.0.0 · **Branch:** `feature/bg-romantic-room`
**Status:** Written with the spec in one run (H-020 flow); updated after the build where the
build measured something better (marked *Built:*).

## 1. Files

| Action | File | Reason |
|---|---|---|
| CREATE | `src/lyric_engine/background/__init__.py` | Registry (`WORLDS`, `DESIGNED`, `FITS`), `parse_bg`, `SongFacts`, `song_facts`, `build_scene`, `report_lines`. No numpy at import (the CLI imports it for `--bg`) |
| CREATE | `background/paint.py` | Shared art tools every world uses (one art style, H-027 note): smoothstep, keyframes, gust envelope, plaster texture, grain, half↔full resize, sRGB luminance and contrast |
| CREATE | `background/compose.py` | `with_background` (frame-stream wrapper → stacked overlay + finished frame), `compose_frame` (text shadows, lit text), `Legibility` log, `final_checks` |
| CREATE | `background/room.py` | `RoomLook` (a mood's numbers), `DUSK`, `MOODS`, `Picks`, `Room` (arc, gusts, per-frame `Light`) |
| CREATE | `background/room_art.py` | The room's static art, drawn once per render: wall albedo, jaali light patch, leaf shapes, curtain, ledge, lamp, prop, chair + dupatta |
| MODIFY | `render/__init__.py` | `render(..., bg=None)`: facts, scene, `final` output, wrapper, checks, notes, report lines |
| MODIFY | `render/encode.py` | `_ffmpeg_cmd`: with `outputs["final"]`, a stacked input (overlay over finished frame) and a fourth output; unchanged string without it |
| MODIFY | `render/check.py` | `_probe` also returns `codec`; `write_report(..., extra=())` appends lines before Notes |
| MODIFY | `cli.py` | `--bg` on `render` and `make` (`type=_bg`), passed through `_render` / `_make` |
| CREATE | `tests/test_background.py` | AC4–AC9 units, one short end-to-end render |
| MODIFY | `requirements.txt` | numpy moves from "transitive" to a direct line (the background imports it) |
| MODIFY | docs | `CLAUDE.md` (command, architecture), `project_context.md` (scope: finished short, H-023), `decision.md` (D-028–D-031), plan/pending/session log |

## 2. Architecture Decisions

- **D-028: one ffmpeg process, stacked input.** With `--bg`, each piped frame is 1080×3840 RGBA:
  the theme's overlay bytes on top (passed through untouched), the finished frame below. The graph
  splits and crops; the top half goes through exactly today's three chains, the bottom half to
  H.264. Derives from: overlay outputs unchanged (spec 3, AC3) and CLAUDE.md's "one ffmpeg
  process". Rejected: a second ffmpeg process (a second writer, error path and cleanup for no gain);
  compositing in ffmpeg (the lighting needs the overlay's alpha in Python).
- **D-029: lighting at half resolution.** Every light term (ambient, sun patch with jaali, leaves,
  curtain, dust, lamp) and the text's shadows are summed into one 540×960 light image, upscaled
  once (bilinear) and multiplied by the full-resolution albedo (wall, props, grain). Light is soft
  by nature, so half resolution costs nothing visible and cuts the per-frame work about 4×. Derives
  from: the 10-minute target (AC10). Rejected: `moderngl` first (a new dependency before numpy is
  shown too slow; kept as the fallback). *Built:* the full-size step runs in 8-bit PIL C ops
  (light clipped at 1 and upscaled as RGBA, `ImageChops.multiply` with the albedo, the tinted
  overlay by `alpha_composite`): 250 → about 100 ms per frame. Blurs use `scipy.ndimage`
  (PIL cannot blur mode F).
- **D-030: text shadows block light, not paint black.** The overlay's alpha, shifted away from each
  light and blurred, removes part of that light term (sun, then lamp). The shadow is therefore the
  wall's own colour, lengthens and fades with the sun, and is cast by the lamp at the end, with no
  extra rules. Derives from: spec 4.4.
- **D-031: props drawn by code; seed from the folder name.** `zlib.crc32(folder name)` (Python's
  `hash()` changes per process). Derives from: spec 3 (no AI art), 4.3, AC8.
- Text lighting multiplies the overlay's RGB per channel by `tint` ∈ [0.9, 1]³ and keeps its alpha
  (red line 2, AC4). The legibility log is computed while drawing (no decode), on the background
  before text shadows (the worst case).
- `background/` is a subpackage from the start: five modules, each under ~300 lines.
- The scene is duck-typed (`size`, `albedo`, `albedo_half`, `lyric_half`, `light(k)`); no base
  class for one world.

## 3. Data Structures

`background/__init__.py`
- `WORLDS = {"room": ("dusk",)}`: built moods, first is the default (spec 3).
- `DESIGNED = {"room": ("morning", "dusk", "rain", "moonlit", "mist", "festival")}` (spec 5 row 3).
- `FITS = {"room": {"soft-romantic", "soft-romantic-v2", "cinematic", "lofi-minimal",
  "lofi-typewriter"}}` (spec 4.6).
- `LYRIC_AREA = (60, 380, 960, 1540)` (Hard Rule).
- `@dataclass(frozen=True) SongFacts`: `name: str`, `seed: int` (D-031), `duration: float`,
  `n: int`, `fps: int`, `last_line_s: float | None` (last shown line's first timed word, words.json
  start: red line 1), `marks: tuple[tuple[float, str], ...]` (timed marked word starts + label for
  the report), `untimed_marks: tuple[str, ...]`.

`background/room.py`
- `@dataclass(frozen=True) RoomLook`: `sun_keys` ((fraction, rgb, intensity), …),
  `ambient_keys` ((fraction, rgb), …), `lamp_rgb`, `lamp_ramp_s`, `lamp_flicker_s`,
  `gust_rise_s`, `gust_s`, `gust_bloom`, `gust_lift_px`, `sun_shadow_from`, `sun_shadow_to`
  ((dx, dy) full px), `sun_shadow_alpha`, `lamp_shadow` ((dx, dy)), `lamp_shadow_alpha`,
  `shadow_blur`, `tint_k` (≤ 0.2, AC4), `patch_drift` ((dx, dy) over the arc), `patch_stretch`.
  `DUSK = RoomLook(...)`; `MOODS = {"dusk": DUSK}`.
- `@dataclass(frozen=True) Picks`: `plant: "left"|"right"`, `curtain: "plain"|"block-print"|
  "lace"`, `prop: "chai"|"radio"|"letter"`, `dupatta: str` (name) + `dupatta_rgb`;
  `describe() -> str` for the report (AC8).
- `@dataclass Light` (per frame): `ambient (3,)`, `sun (h, w) float32`, `sun_rgb (3,)`,
  `sun_shadow (dx, dy, alpha)`, `lamp (h, w) | None`, `lamp_rgb (3,)`, `lamp_shadow (dx, dy,
  alpha)`, `air (h, w) float32 | None` (dust, steam), `glow: list[(rgb array, (x, y))]` (lamp
  shade, full res, additive), `tint (3,)`.
- `Room`: `size`, `facts`, `look`, `picks`, `albedo (H, W, 3) float32`, `albedo_half`,
  `lyric_half` (the lyric area as a half-res slice), static art from `room_art`, `gust_times`.

`background/compose.py`
- `@dataclass Legibility`: `worst: tuple[int, float] | None` (frame, contrast), `failed:
  list[tuple[int, float]]`, `draw_s: float` (time spent, for the report).

## 4. Function Specifications

`background/__init__.py`
- `parse_bg(text) -> tuple[str, str]`: `"room"` → `("room", "dusk")`. Raises `ValueError` with the
  exact messages in §6. Used by `cli._bg` (wraps into `argparse.ArgumentTypeError`).
- `song_facts(doc, emphasis, duration, n, fps, name) -> SongFacts`: timed = `start` and `end` not
  None; `last_line_s` = the first timed word's start on the highest line with a timed word.
- `build_scene(bg, facts, theme)`: imports `room` lazily; returns `Room(facts, MOODS[mood], size)`.
- `report_lines(scene, bg, theme, final, legibility) -> list[str]` and
  `fit_note(world, theme) -> str | None`.

`background/paint.py` (numpy, scipy.ndimage, PIL)
- `smooth(x)`, `keyframes(keys, f)` (smoothstep between neighbours, clamped),
  `envelope(t, starts, rise, total) -> float` (max over starts: never adds up, AC6),
  `plaster(h, w, seed) -> (h, w) float32` (blurred multi-scale noise), `grain(h, w) -> (h, w)`
  (fixed seed: the same grain in every world), `resize(a, w, h, box)` (PIL mode "F" bilinear),
  `up2`, `down2(a)` (2×2 mean), `blur(a, sigma)` (`ndimage.gaussian_filter`, art drawn once),
  `soft(a, r)` (two box blurs, per frame),
  `luminance(rgb01) -> array` (sRGB → linear → Rec.709 Y), `contrast(l1, l2) -> float`.

`background/room.py`
- `Room.__init__(facts, look, size)`: rng from `facts.seed` → `Picks` (drawn first, in a fixed
  order) → `room_art` layers → dust and sway phases.
- `Room.arc(t) -> (sun_rgb, sun_i, ambient_rgb, lamp_level, f)`: `f = t / last_line_s` clamped (or
  `t / duration` when there is no shown line: then no lamp). Lamp level: 0 before `last_line_s`,
  one flicker within `lamp_flicker_s`, smooth ramp to 1 by `lamp_ramp_s` (AC5).
- `Room.gust(t) -> float` in [0, 1]: `paint.envelope` over the timed marks (AC6).
- `Room.light(k) -> Light`: arc + gust at `t = k / fps`; sun map = drifted, stretched patch ×
  leaf and curtain shadows (sway × (1 + gust)) × `sun_i · (1 + gust_bloom · gust)`; lamp map ×
  level; air = dust (in the beam, 30% inside the lyric area) + chai steam; tint from the dominant
  light colour, channels clamped so every multiplier is in [0.9, 1] (AC4).

`background/room_art.py` (drawn once; PIL with 2× supersampling where edges show)
- `wall(size, seed)`: warm plaster albedo × grain × vignette.
- `jaali_patch(half_size)`: two arched openings with a diamond lattice, sheared for light from the
  upper left; crisp at the top, blurred to a calm glow behind the lyric area; soft penumbra; on a
  canvas larger than the frame so it can drift.
- `leaves(picks, rng)`: heart-shaped money-plant leaves along a hanging vine on `picks.plant`'s
  side of the patch, with per-leaf sway phases; `leaf_shadow(leaves, t, sway)` draws the frame's
  mask at half res.
- `apply_curtain(canvas, side, print_, t, lift)`: fold profile + print pattern (transmittance),
  worked out across the window's (u, v) band and laid into the patch canvas row by row.
- `props(size, picks)`: ledge, lamp (off), prop, chair + dupatta into the albedo, all below
  y 1540; returns the albedo layer, the lamp shade's glow sprite and the steam origin.
- `lamp_light(half_size)`: the lamp's light on the wall (upward fan + falloff), peak 1.

`background/compose.py`
- `compose_frame(overlay: bytes, scene, k, theme, log) -> bytes`: §5.2.
- `with_background(frames, scene, theme, log) -> Iterator[list]`: yields `[*parts,
  compose_frame(...)]` per frame (the overlay parts untouched: AC3).
- `final_checks(path, n, theme, log) -> list[str]`: ffprobe (h264, yuv420p, 1080×1920, 30/1,
  `n` frames, audio) + legibility failures.

`render/encode.py`
- `_ffmpeg_cmd(theme, codec, audio, outputs)`: unchanged when `"final"` not in outputs. Otherwise
  input `-s 1080x3840`; graph prefix `[0:v]split=2[t][b];[t]crop=1080:1920:0:0,split=3[a][g][p]`
  (rest as today) + `[b]crop=1080:1920:0:1920,{TO_BT709},format=yuv420p[fin]`; extra output
  `-map [fin] -map 1:a:0 -c:v libx264 -preset medium -crf 18 -profile:v high -movflags +faststart
  BT709 tags -c:a aac -b:a 192k final` (no `-shortest`, so all `n` frames stay).

## 5. Logic Flow

### 5.1 `render()` with `bg`
1. Load, plan and card as today.
2. If `bg`: `facts = song_facts(...)`, `scene = build_scene(bg, facts, theme)`,
   `outputs["final"] = render_dir / f"final_{world}_{mood}.mp4"`, `log = Legibility()`.
3. `_remove` the outputs (the final included) and the report.
4. Frames → `with_card` (if card) → `with_background` (if bg) → `_encode`.
5. Checks as today; if bg: `+= final_checks(...)`; notes: fit note, untimed marks.
6. `write_report(..., extra=report_lines(...) if bg else ())`.

### 5.2 `compose_frame`
1. `ov = frombuffer(overlay).reshape(H, W, 4)`; `a = ov[..., 3]`.
2. `L = scene.light(k)`; `light = ambient + sun·sun_rgb + lamp·lamp_rgb + air·sun_rgb` (half res).
3. Legibility (only with ink, alpha ≥ 16): `Y = p99(luminance(albedo_half · light))` over the
   ink box grown by 24 px inside the lyric area (*Built:* the whole-area p99 failed on the lamp's
   light at the bottom-left, where no lyric sits); text `Yt = luminance(text_rgb/255 · tint)`;
   `c = contrast(Yt, Y)`; log worst; `c < 3.0` → `failed`.
4. If any alpha: ink bbox (+ blur margin + max offset) at half res; per light with alpha > 0:
   `sh = blur(shift(down2(a/255), offset/2), shadow_blur) · alpha`; `light[box] −= term[box] ·
   sh`.
5. `bg = multiply(albedo_img, upscale(uint8(clip(light, 0, 1))))` (PIL, RGBA) + the lamp
   shade's glow (`ImageChops.add` on its box).
6. Text over (straight alpha): the overlay's drawn box (alpha ≥ 1), multiplied by the tint, by
   `alpha_composite`.
7. `bg.tobytes()` (RGBA, alpha 255).

## 6. Edge Case Implementation Map

| Spec edge case | Mechanism | Where |
|---|---|---|
| No `--bg` | `bg is None`: no import, no wrapper, no `final`, `extra=()` | `render/__init__.py` |
| Unknown world / mood | `ValueError("unknown background 'x'; built: room (moods: dusk)")` / `"unknown mood 'x' for room; built: dusk"` → argparse exit 2 | `parse_bg`, `cli._bg` |
| Designed, not built | `"room:rain is designed but not built yet (plan step 23); built: dusk"` | `parse_bg` |
| Theme outside range | `fit_note` → `result.notes` and the Background section | `__init__.py` |
| No marks | `envelope` over no starts = 0 | `paint.envelope` |
| Untimed mark | skipped in `song_facts`, listed in `untimed_marks` → note | `song_facts` |
| Overlapping marks | `max` of envelopes | `paint.envelope` |
| One line / early last line | `f` clamps to 1; the lamp still starts at `last_line_s` | `Room.arc` |
| Outro | `f` = 1 and lamp 1 after the ramp | `Room.arc` |
| No shown line | `last_line_s None` → `f = t / duration`, no lamp | `Room.arc` |
| Title card | part of the overlay frames before `with_background` | order in `render()` |
| Legibility fail | `"legibility: N frame(s) below 3:1 in the lyric area; first: frame k (2.41:1)"` | `final_checks` |
| ffmpeg fails | `final` is in `outputs`, so `_encode` removes it | `encode._encode` |
| Old finals | only `outputs["final"]` is removed | `render()` |
| `--codec` | touches only the alpha chain | `_ffmpeg_cmd` |

## 7. File Layout

- `background/__init__.py`: docstring → constants → `SongFacts` → `parse_bg` → `song_facts` →
  `build_scene` → `fit_note`, `report_lines`.
- `paint.py`: docstring → timing curves → textures → resize/blur → luminance.
- `room.py`: docstring → `RoomLook`, `DUSK`, `MOODS` → `Picks`, `pick` → `Light` → `Room`.
- `room_art.py`: docstring → wall → jaali patch → leaves → curtain → props → lamp light.
- `compose.py`: docstring → `Legibility` → `compose_frame` → `with_background` → `final_checks`.

## 8. Dependencies

- numpy (installed, 2.2.6), PIL; nothing new. `background` never imports `render` (only
  `theme`); `render` imports `background` lazily inside `render()`; `compose.final_checks` imports
  `render.check._probe/_video_failures` lazily.
- Conflicts: `_probe` gains a `codec` key (additive). `write_report` gains `extra` (default empty:
  report unchanged). CLAUDE.md's "one ffmpeg process writes all three outputs" becomes four with
  `--bg`; CLAUDE.md line count checked before editing (≤ 200).

## 9. Hard Boundaries (build checklist)

- [x] No `--bg` → no numpy import in `render()`, frame stream unwrapped, ffmpeg command
  unchanged (AC2).
- [x] The overlay parts reach ffmpeg exactly as without `--bg` (AC3).
- [x] The room never reads word text; labels only for the report.
- [x] No estimated time: untimed marks do nothing (red line 1).
- [x] Text alpha never altered; RGB × tint only (red line 2, AC4).
- [x] Props below y 1540; no bright detail crosses the lyric area (legibility log).
- [x] No per-frame random noise; everything from the seed and `t`.

## 10. Acceptance Criteria (runnable)

1. `venv/Scripts/python -m lyric_engine.cli render songs/khidki_s2_em --bg room` → prints
   `final: …final_room_dusk.mp4`, `checks: pass`, exit 0; `ffprobe` shows h264 yuv420p 1080x1920
   30/1 + aac. Same for `khidki_s2`, a 30 s clip (`clip songs/khidki_full --from 0:27 --to 0:57
   --out songs/khidki_30s`, then `make`), `khidki_full`.
2. `scratchpad/hashes.sh` (framemd5 of every output of all eight themes) on the branch equals the
   `dev` baseline; `grep -L "## Background" songs/khidki_s2_em/render/*/report.md` lists all eight.
3. The same hashes of the three overlay outputs with and without `--bg room` (v2) are equal.
4. `python -m unittest tests.test_background -k Compose` passes.
5. `-k Arc` passes. 6. `-k Gust` passes. 7. `-k Legib` passes and AC1 reports pass the rule.
8. `-k Seed` passes; the report's Background section names seed and picks.
9. `-k Cli` passes (`room:rain` → exit 2 "not built yet"; `make --bg room` reaches `render`).
10. Report wall times for 14 s / 30 s / full; 30 s × 2 extrapolates to ≤ 10 min, else `moderngl`.
11. Owner approves (`khidki_s2_em`, `khidki_full`). 12. `/gate` green.
