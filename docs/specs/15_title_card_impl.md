# Implementation Plan: Title Card
**Spec:** `docs/specs/15_title_card.md` v1.0.0 · **Branch:** `feature/title-card`
**Status:** Written with the spec in one run (H-020 flow).

## 1. Files

| File | Change |
|---|---|
| `theme.py` | `card_*` fields (shared defaults); `PHONK_NEON.card_glow = pulse_low` |
| `render/card.py` | New: `read_title`, `build_card`, `Card.level`, `with_card` (frame wrapper + clash log), `card_checks` |
| `render/__init__.py` | Load the card, wrap `parts`, note, append `card_checks` |
| `workflow.py` | `clip` copies `title.txt` |
| `tests/test_card.py` | New: AC3–AC7 |

## 2. Details

- `read_title(song_dir)`: `title.txt` as UTF-8 (BOM dropped); lines stripped, blanks dropped.
  None if no file; `[]` if empty (note); > 2 lines → `RenderError`.
- `build_card(lines, theme)`: size `round(card_scale · font_size)`, minus `font_step` until every
  line's advance ≤ the width (safe zone width, else `max_width`) − 2·pad, down to
  `card_min_size`, else `RenderError`. Per line: glyph (`layout.word_mask`, pad), outline
  (`stroke_px`) when `stroke_frac`. Layers per line: glow (`card_glow` × wide blur × boost, only
  if `card_glow`), shadow of the outline (or glyph), stroke outline in `stroke_rgb` (if set),
  glyph in `text_rgb`. Rows at `row_spacing · (ascent + descent)`, each centred on `center_x`;
  the first row's box top at `card_top`.
- Timing: `I = ceil(card_in_s·fps)`, `E = min(n, ceil(card_s·fps))`, `O = ceil(card_out_s·fps)`.
  Level at frame k: `(k + 1)/I` while `k < I`, `(E − k)/O` while `k ≥ E − O`, else 1, as 1/32
  steps; frames ≥ E untouched.
- `with_card(frames, card, theme)`: for k < E, join the parts to one RGBA frame; if the frame's
  alpha (≥ 16) meets the card's drawn bbox, log k in `card.clashes`; composite the faded card;
  yield `[bytes]`. Other frames pass through as they are.
- `card_checks`: clashes → `"card: lyrics drawn under the title card on N frame(s); first: k"`.
  One alpha decode of the first E frames: the card's hold frame `(I + E − O) // 2` has mean alpha
  ≥ `SYNC_ON_MIN` over the card's glyph ink.

## 3. Hard Boundaries (build checklist)

- [x] No `title.txt` → the frame stream is not wrapped at all (byte-identical, AC2).
- [x] Card text = `title.txt` lines as written; no case change.
- [x] Lyrics, timings and layouts untouched.
