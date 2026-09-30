# Implementation Plan: Background Layer + Romantic Light Looks
**Spec:** `docs/specs/17_bg_romantic_lights.md` v2.0.0 · **Branch:** `feature/bg-romantic-room`
**Status:** v2. The pipeline of v1 (the room, rejected: H-032) stays: `--bg` parsing, song facts,
the stacked ffmpeg input and the finished short, the report section and the checks (D-028). The
room's modules and its compose (lit text, text shadows) are gone; the looks are ported from the
owner-approved sample scripts in `songs/_review/backgrounds/lights2/` (D-033).

## 1. Files

| Action | File | Reason |
|---|---|---|
| MODIFY | `src/lyric_engine/background/__init__.py` | Looks `rain`, `fog`, `milan` in `WORLDS`; `SongFacts` gains each word's place, the lyric block and line starts; `word_boxes` reads any theme's plan; `build_scene` imports the look |
| REWRITE | `background/paint.py` | The samples' shared tools: linear light, OKLab gradients, glows at full and quarter size, lens defocus, soft noise, matte dots, vignette with dark border, scrim, the finishing pass (bloom, soft shoulder, sRGB, grain) |
| CREATE | `background/rain.py`, `fog.py`, `milan.py` | One `Scene` per look, ported from `rain3_video.py`, `fog_video.py` (full moonlight) and `milan_video.py` |
| REWRITE | `background/compose.py` | The overlay over the look as it is; the look gets the text's ink box; `Legibility`, `final_checks` unchanged in meaning |
| DELETE | `background/room.py`, `room_art.py` | The rejected room |
| MODIFY | `render/__init__.py` | `song_facts(..., word_boxes(lines))`; the untimed-mark note's wording |
| MODIFY | `cli.py` | `--bg` help names the looks |
| REWRITE | `tests/test_background.py` | The looks' tests (section 5) |

## 2. Architecture Decisions

- **Port, not redesign.** Each look's module keeps its sample's numbers (palettes, speeds, sizes,
  finishing pass), so the engine draws what the owner approved. The two changes for the engine:
  the song's seed for what varies per song, and milan's calm behind the text (below).
- **Fixed stage, seeded details.** The stage (rain's sky, clouds, ground; fog's leaves, fog
  textures) uses the sample's fixed seeds; rain's drops, fog's new rays and milan's dots use
  `crc32(folder name)`.
- **Scene API:** `Scene(facts)`, `describe()`, `frame(k, ink) -> (H, W, 3) uint8`. `ink` is the
  overlay's ink box on frame k (alpha ≥ 16), computed by `compose` before the look draws.
- **Milan is a simulation.** Dots move by an Ornstein-Uhlenbeck wander stepped once per frame,
  so `frame(k)` steps forward to k and refuses to go back; the render streams frames in order.
- **Milan's calm behind the text.** A quarter-size mask: the ink box grown by 70 px and softened
  (σ 20 px) is the target; the mask takes it at once and otherwise fades over 0.8 s. Dots and
  their light are multiplied by `1 − 0.75 × mask`. Marked meetings sit 130 px below the lyric
  block under the word (the sample's "150 px above the word" fell behind v2's past line: 2.39:1).
- **rain and fog** ignore `ink`: their fixed scrim over the lyric block keeps 3:1 (measured,
  section 6).

## 3. Data Structures

```python
@dataclass(frozen=True)
class SongFacts:
    name: str; seed: int; duration: float; n: int; fps: int
    words: tuple            # ((start, marked, cx, cy), ...) timed words, time order
    line_starts: tuple      # first timed word of each shown line
    last_line_s: float | None
    lyric_centre: tuple     # block centre, raised 90 px (the scrim's centre)
    untimed_marks: tuple    # report labels
    lyric_box: tuple | None # (x0, y0, x1, y1) around every word's box
```

`Legibility`: `worst`, `failed`, `draw_s`, `frames` (unchanged from v1).

## 4. Logic Flow

1. `render()` builds the plan as today; with `bg`, `song_facts(doc, emphasis, duration, n, fps,
   folder name, word_boxes(lines))` → `build_scene(bg, facts)`.
2. The frame stream: theme frames → title card → `with_background`: for frame k, the overlay's
   pieces go on untouched; `compose_frame` finds the ink box, calls `scene.frame(k, ink)`, notes
   the contrast, `alpha_composite`s the overlay and appends the finished frame (D-028).
3. After encoding: `check_outputs` as today, then `final_checks` (ffprobe + legibility) and the
   report's Background section.

## 5. Tests (`tests/test_background.py`)

| Class | What |
|---|---|
| `ParseBgTest` | defaults, explicit mood, refusals naming the choices |
| `CliTest` | `render --bg room` exits 2; `make --bg rain` passes `("rain", "evening")` through |
| `SongFactsTest` | timed words only, marks with places, line starts, the lyric block, untimed labels; `word_boxes` reads Beat Pop's `Show` |
| `PaintTest` | envelopes never add up; the finishing pass's shoulder |
| `RainTest` | a word changes the ground under it and nothing above y 1300 or left of x 450; same folder, same frame |
| `FogTest` | a word brightens the rays |
| `MilanTest` | a marked meeting within a frame of its start, under the word 130 px below the lyrics; dots behind the text stay dim while the same dots pass bright without text; frames only in order |
| `ComposeTest` | the overlay's pixels where opaque, the look's where transparent, alpha 255 |
| `LegibilityTest` | bright fails, dim passes; the check's message |
| `BackgroundRenderTest` | a 2 s render with `--bg milan`: checks pass, overlay frames hash-identical, Background section only with `--bg` |

## 6. Measured

`khidki_s2_em` (14 s, 420 frames), Soft Romantic v2, all checks pass. Measured while ten other
agents were drawing stills on the same laptop, so the times are upper bounds:

| Look | Wall | Lowest contrast | Notes |
|---|---|---|---|
| milan | 233 s | pass | drawn in this process (a simulation) |
| rain | 263 s (602 s before the worker pool) | 3.15:1 (2.42:1 with the sample's patch) | D-034 |
| fog | 259 s | 6.11:1 | |

Idle laptop, `khidki_30s` (30 s, 900 frames), 2026-10-01: rain 274 s (a 60 s short ≈ 9 min,
AC10 met), aakhri 318 s (≈ 10.6 min), chaand 437 s and khaali 570 s (both measured while two
agents rendered; re-measure idle before relying on them).

- The finishing pass does the shoulder only on pixels above the knee and works in place: 2.3×
  faster, the same bytes.
- rain and fog draw their frames in 4 worker processes (`compose.drawn_ahead`), at most two
  frames per worker ahead; the frames are the same bytes as drawn in one process (tested).

## 7. Hard Boundaries (build checklist)

- [x] No `--bg` → no numpy import in `render()`, frame stream unwrapped, ffmpeg command
  unchanged (AC2).
- [x] The overlay parts reach ffmpeg exactly as without `--bg` (AC3).
- [x] The looks never read word text; labels only for the report.
- [x] No estimated time: untimed words and marks do nothing (red line 1).
- [x] The overlay is composited as it is: alpha and colours untouched (red line 2).
- [x] No per-frame random noise except the simulation's, which is seeded and stepped in order.
