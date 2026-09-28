# Pending Work

Last updated: 2026-09-29 (step 15 built, owner look pending)

## WIP

Step 15 (Title card) built on `feature/title-card` in one run (H-020 flow, H-021 look). Waiting on
the owner's look (AC8) before merge ([PR #13](https://github.com/Hacke2367/subtitle_engine/pull/13)). Look sheet: `songs/title_card_looks.png`.

## Current focus

V1.1 styling. Eight themes: Soft Romantic v2 (default, H-015), Soft Romantic v1, Pop Karaoke,
Lofi Minimal, Lofi Typewriter (H-016), Cinematic (H-017), Beat Pop (H-019) and Phonk Neon
(H-020) (`--theme`, outputs in `render/<theme>/`, D-018). Beat data: `beats` command,
`drops.txt` (D-022, D-024). Title card from `title.txt` (step 15). Working flow (H-020): owner
answers the look questions up front, then spec → plan → build in one run; the owner judges the
finished look.

## Next up

1. **Resume point:** owner writes `songs/<song>/title.txt` (one or two lines, as they should
   appear) and looks at the card in any theme's `preview.mp4`. Changes → `card_*` values in
   `theme.py`; approval → merge the PR.
2. Step 14 (Devanagari shaping) only when a song needs it. Remaining "Later candidates":
   line breaks by sung pauses.
3. Optional cleanup: `render/check.py` (≈369 lines) and `render/karaoke.py` (≈313) are past
   the ~300-line split guideline; split only if the owner wants it (a `chore/` branch).
4. Owner: try a different song end to end (spec 05 AC4), now with any theme.
5. Step 04 (`.lrc` anchors) only if a real song drifts.

## Waiting on the owner

- Write `songs/<song>/title.txt` for the songs you post (e.g. `♪ Khidki | Kishore Kumar`).
- Write your own drop times in `songs/<song>/drops.txt` (the ones in `khidki_full` are test
  values: 0:28.0, 1:30.8).
- Optional: a beat-heavy test song (Punjabi / party / rap) in `songs/<name>/` (`audio.*` +
  `lyrics.txt`) for the Beat Pop look check; `khidki_full` is used otherwise.
- Optional: listen to `songs/khidki_full/beats_preview.m4a`; if the clicks sit at twice or half
  the beat, run `beats songs/khidki_full --bpm <N>`.
- FYI (D-018): renders now go to `songs/<song>/render/<theme>/`. Older outputs directly in
  `songs/<song>/render/` were left in place; delete them whenever you like.
- FYI: emphasis ships at 1.5x; set `emphasis_scale` (up to 2.0) in `theme.py` any time. The 2x
  preview is in `songs/khidki_s2_em_2x`.
- Try a different song: `align` → `clip` → `make` (spec 05 AC4).
- FYI (D-010): the local model's weights are non-commercial (CC-BY-NC). Fine for V1, but it
  matters if this ever becomes a SaaS.

## Owner to-dos

- `docs/reference/knietic_lyric.pdf` is blank (3 empty pages). Re-export it from Gemini if it
  held anything, or delete it.
