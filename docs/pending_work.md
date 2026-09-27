# Pending Work

Last updated: 2026-09-27 (step 10 started)

## WIP

Step 10 (Cinematic theme) on `feature/cinematic-theme` (from `dev` @ e884a60). Status: Review,
[PR #9](https://github.com/Hacke2367/subtitle_engine/pull/9).
Built per plan 10 §11 steps 1-8: `cinematic` renders `khidki_s2`, `khidki_s2_em`,
`khidki_s2_lofi` with every check passing (~26 s vs Soft Romantic 20.9 s); the other five themes
are byte-identical to `dev` (AC2). Waiting on: the owner's look review (AC10), then merge.

## Current focus

V1.1 styling. Five themes: Soft Romantic v2 (default, H-015), Soft Romantic v1, Pop Karaoke,
Lofi Minimal and Lofi Typewriter (H-016) (`--theme`, outputs in `render/<theme>/`, D-018).
Now: step 10, Cinematic (H-012, D-017).

## Next up

1. **Resume point:** owner reviews `songs/khidki_s2_em/render/cinematic/preview.mp4` (spec 10
   AC10); look changes go in as `theme.py` values, then `/ship` updates PR #9; the owner merges.
2. Optional cleanup: `render/check.py` (≈359 lines) and `render/karaoke.py` (≈310) are past
   the ~300-line split guideline (`lofi.py` is 268 since step 10); split only if the owner
   wants it (e.g. a `chore/` branch).
3. Steps 11–13 follow in plan order (H-012, D-017), one branch each; step 14 (Devanagari
   shaping) only when a song needs it.
4. Owner: try a different song end to end (spec 05 AC4), now with any theme.
5. Step 04 (`.lrc` anchors) only if a real song drifts.

## Waiting on the owner

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
