# Pending Work

Last updated: 2026-09-27 (step 10 merged, PR #9)

## WIP

None. Step 10 (Cinematic) merged into `dev` ([PR #9](https://github.com/Hacke2367/subtitle_engine/pull/9)); the owner approved the look.

## Current focus

V1.1 styling. Six themes: Soft Romantic v2 (default, H-015), Soft Romantic v1, Pop Karaoke,
Lofi Minimal, Lofi Typewriter (H-016) and Cinematic (H-017) (`--theme`, outputs in
`render/<theme>/`, D-018). Next: step 11, beat detection (H-012, D-017).

## Next up

1. **Resume point:** `/start_work` step 11 (beat detection, `feature/beat-detection`), then
   `/spec`. The spec needs two owner calls: the library (`aubio`, lighter, vs `librosa`, pulls
   numba; research §10 F) and where beats live (inside `words.json` or beside it, which would
   amend D-001). Beats drive decoration only, never a word timing (red line 1).
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
