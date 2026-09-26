# Spec: Soft Romantic Renderer
**Version:** 1.0.0 | **Component:** Stage 2: rendering (`theme.py`, `layout.py`, `render.py`)
**Status:** Approved by Claude under H-008 (owner away); owner review pending
**Plan step:** 03 (`docs/development_plan.md`) · **Branch:** `feature/soft-romantic-render` (stacked, D-011)

## 1. Problem Statement

Step 02 produces `words.json`: every lyric word with its sung time. The owner still has nothing to
drop into CapCut. This step is the product: it turns `words.json` into a transparent 9:16 overlay
where each word appears the moment it is sung, in the Soft Romantic look (warm, soft, glowing,
calm; no shake or glitch). The owner lays it over their own background in CapCut desktop (alpha
`.mov`) or mobile (green-screen mp4, H-003).

## 2. Objective

`render songs/<song>` → an alpha `.mov` and a green mp4, 1080×1920 at 30 fps, full song length from
t=0, where every word reveals at its `words.json` time, with its text exactly as in `lyrics.txt`.
A low-res preview with the song audio lets the owner judge look and sync without opening CapCut.

## 3. Scope & Constraints

**Will Do:**
- Read `songs/<song>/words.json`. Validate it against the song's `lyrics.txt` and audio (not stale)
  before rendering anything.
- **Layout:** one lyric line on screen at a time. The line wraps into rows within a max width,
  centred horizontally around a vertical anchor clear of Shorts/Reels UI. A line that is too long
  gets a smaller font, down to a minimum.
- **Animation (initial Soft Romantic look, tunable in `theme.py`):**
  - each word fades in and rises slightly at its start time (a small uniform display lead, see
    §4);
  - the word being sung carries a soft warm glow that fades out after it ends;
  - sung words stay visible;
  - the line fades out after its last word (a short hold), or when the next line begins, whichever
    comes first.
- **Font fallback:** each character missing from the theme font is drawn with the first fallback
  font that has it. A character no font has stops the render. Tofu boxes are never drawn.
- **Outputs**, all from one set of rendered frames, in the song's `render/` folder:
  - `overlay.mov`: alpha, 1080×1920, 30 fps, full length, no audio. Its codec is a setting:
    ProRes 4444 / PNG / QuickTime Animation, the three formats proven in step 01.
  - `overlay_green.mp4`: the same frames on pure green, H.264 yuv420p, no audio.
  - `preview.mp4`: the frames over a dark background, 540×960, with the song's audio. Review only.
- **Automated output check** after rendering: size, fps, frame count, alpha present, no audio in
  the overlays, plus sampled sync checks (a word's pixels appear at its reveal frame and not
  before).
- CLI: `render songs/<song>`, with `--codec` and `--allow-flagged`.
- Unit tests for layout and timeline maths, and for the refusal rules. Offline, with no song files.

**Will NOT Do:**
- **Emphasis words:** their syntax touches red line 2 and needs the owner's call (H-009, pending).
  The theme only reserves an emphasis style.
- Other themes, custom tags, AI styling.
- Backgrounds, audio mixing or a finished video (the preview is review-only).
- Choosing the final default codec: that waits for the owner's CapCut test (H-006, D-011).
- Editing `words.json` or re-aligning: the render reads alignment and never writes it.

**Hard Rules:**
- **Red line 1:** the renderer never invents a time. A word reveals at its own `start` (minus the
  uniform display lead). With `--allow-flagged`, a word with no time is shown statically for its
  line's visible span and never animated as if sung. A line with no timed word is not shown at all,
  and the render says so.
- **Red line 2:** the drawn text of every word is exactly its `words.json` text, which the
  validator ties to `lyrics.txt`. No case changes, no punctuation stripping.
- By default, a render refuses when `words.json` has flagged words or is stale, and lists what to
  fix. `--allow-flagged` is an explicit owner opt-in.
- The render never writes outside `songs/<song>/render/` and never modifies `words.json`.

## 4. Core Design

**Pipeline:**

```
words.json ─ validate (stale? flagged?) ─► lines of words with times
    │
    ├─ layout: font, wrap into rows, word boxes (x, y, w, h); computed once per line
    ├─ sprites: per word, text + glow pre-rendered once (the blur is expensive)
    └─ timeline: per frame, visible line(s), each word's reveal progress and glow level
          │
          ▼
   frame compositor (RGBA 1080×1920) ─► ONE ffmpeg process, raw RGBA on stdin
          ├─ overlay.mov        (alpha codec setting)
          ├─ overlay_green.mp4  (over #00FF00, yuv420p)
          └─ preview.mp4        (over dark, 540×960, + song audio)
   ─► output check ─► render report
```

**Timeline rules (frame-exact, fps = 30):**
- Word reveal starts at `start − lead`, with a theme lead of about 0.05 s so the text lands with the
  voice, not after it. Reveal duration is ~0.2 s: opacity 0→1 while rising ~12 px.
- Glow on the current word: ramps up at its reveal, holds until its `end`, then fades over ~0.3 s.
- Line visible from its first word's reveal until `min(last word end + hold, next line's first
  reveal)`, fading out over ~0.25 s. Two lines never overlap on screen.
- Frames with nothing visible are fully transparent (and cheap: no drawing).

**Look (initial values, `theme.py`, owner reviews via `preview.mp4`):**
- Font: Candara Bold (warm humanist, soft curves). Size ~84 px, shrinking to ≥ 56 px for long
  lines. Fallbacks: Segoe UI Semibold → Segoe UI Symbol → Nirmala UI → Segoe UI Emoji.
- Text colour: warm cream. Glow colour: soft rose/peach with a wide soft blur. A faint soft shadow
  keeps text readable on bright backgrounds.
- Max text width 900 px (90 px side margins). The line block is centred at ~62% of the frame
  height, above the platform UI zone at the bottom.
- Palette hues stay away from the key green (reuses the step 01 rule), so the green output keys
  cleanly apart from glow edges (a known limit from step 01).

## 5. Edge Cases & Error Handling

- **Flagged words present:** refuse, listing each word (index, text, line, reasons) and pointing
  at `--allow-flagged` and at hand-fixing `words.json`.
- **With `--allow-flagged`:** timed flagged words animate at their aligner time. Untimed words
  appear static with their line. A line with no timed words is skipped, and the render reports it.
- **Stale `words.json`** (lyrics or audio changed): refuse, and point at `align … --overwrite`.
- **Hand-edited `words.json` invalid:** refuse with the validator's messages.
- **A word wider than the max width even at the minimum font size:** refuse, naming the line.
  Never clip text.
- **Missing glyph in every font:** refuse, naming the character and the word.
- **Audio longer than the last line:** the overlay stays transparent to the end, so its duration
  equals the song.
- **Lines closer together than the fade:** the fade-out shortens so they never overlap.
- **ffmpeg or encoder failure:** a clear error with the stderr tail. Partial outputs are removed so
  a stale file isn't mistaken for a result.
- **Existing outputs:** overwritten. They are derived from `words.json`, which is never touched.

## 6. Acceptance Criteria

1. Unit tests pass offline: wrapping (no row wider than the max, word order and text preserved,
   font shrink); timeline (reveal frame = floor((start − lead) × fps), clamped ≥ 0; a line's
   visibility ends before the next line starts; a glow window per word); refusal on flagged or
   stale input; `--allow-flagged` gives untimed words no animation.
2. `render songs/khidki` produces `overlay.mov`, `overlay_green.mp4` and `preview.mp4`.
3. `overlay.mov`: 1080×1920, 30/1, frame count = ceil(duration × 30) (900 for the 30 s clip), has
   alpha, no audio. `overlay_green.mp4`: same size, fps and frame count, no audio. `preview.mp4`:
   540×960 with an audio stream.
4. Sync check on the rendered alpha: for the first word of every line, its box has alpha 0 on the
   frame before its reveal starts and alpha > 0 five frames after.
5. Every drawn string equals the `words.json` word text (asserted in code where sprites are made,
   and tested).
6. A 30 s clip renders in ≤ 3 min on this laptop. The report states the time.
7. Nothing is written outside `songs/<song>/render/`, and `words.json` is byte-identical before
   and after.
8. **Owner (pending, H-008):** watches `songs/khidki/render/preview.mp4` and approves or tunes the
   look; imports `overlay.mov` / `overlay_green.mp4` in CapCut (H-006) to fix the default codec.

## 7. Dependencies

- `words.json` from step 02 (`songs/khidki/words.json`, L-vocals).
- Pillow (present); ffmpeg 8.0.1; **fontTools** (new, pure Python, pinned) to read font character
  maps for fallback.
- Windows fonts: Candara, Segoe UI, Segoe UI Symbol, Nirmala UI, Segoe UI Emoji (all present).
