# Pending Work

Last updated: 2026-09-28 (step 11 built, in review)

## WIP

Step 11 (beat detection) on `feature/beat-detection` (from `dev` @ f852c53). Stage: Review.
Built: `beats.py`, `beats` command, `beats.json` + `beats_preview.m4a`. Gate green (283 tests,
alpha proof). Only AC10 left: the owner listens to the click preview.

## Current focus

V1.1 styling. Six themes: Soft Romantic v2 (default, H-015), Soft Romantic v1, Pop Karaoke,
Lofi Minimal, Lofi Typewriter (H-016) and Cinematic (H-017) (`--theme`, outputs in
`render/<theme>/`, D-018). Now: step 11, beat detection (H-012, D-017), feeding step 12
(Beat Pop).

## Next up

1. **Resume point:** owner plays `songs/khidki_full/beats_preview.m4a` (spec 11 AC10). Clicks on
   the kick/snare → merge [PR #10](https://github.com/Hacke2367/subtitle_engine/pull/10) (`/merge_pr 10`). Clicks at twice or half the beat → rerun
   `beats songs/khidki_full --bpm <N>` and listen again (detected 143.55 BPM; a slow song may
   really be ~72). Then `/start_work` step 12 (Beat Pop), which reads `beats.ensure_beats`.
2. Optional cleanup: `render/check.py` (≈359 lines) and `render/karaoke.py` (≈310) are past
   the ~300-line split guideline (`lofi.py` is 268 since step 10); split only if the owner
   wants it (e.g. a `chore/` branch).
3. Steps 11–13 follow in plan order (H-012, D-017), one branch each; step 14 (Devanagari
   shaping) only when a song needs it.
4. Owner: try a different song end to end (spec 05 AC4), now with any theme.
5. Step 04 (`.lrc` anchors) only if a real song drifts.

## Waiting on the owner

- Listen to `songs/khidki_full/beats_preview.m4a` (spec 11 AC10): do the clicks sit on the
  kick and snare?
- Optional: a beat-heavy song (Punjabi / party) in `songs/`, if `khidki_full`'s drums are too
  soft to judge the click preview by ear (spec 11 §4.5); step 12 needs one anyway.
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
