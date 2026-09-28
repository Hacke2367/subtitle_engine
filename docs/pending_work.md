# Pending Work

Last updated: 2026-09-28 (step 11 merged, PR #10)

## WIP

None. Step 11 (beat detection) merged into `dev` ([PR #10](https://github.com/Hacke2367/subtitle_engine/pull/10)). The owner merged on the objective
check (84 % of beats within 50 ms of a kick/snare hit, 143.55 BPM not double time); the by-ear
listen of `songs/khidki_full/beats_preview.m4a` is optional now.

## Current focus

V1.1 styling. Six themes: Soft Romantic v2 (default, H-015), Soft Romantic v1, Pop Karaoke,
Lofi Minimal, Lofi Typewriter (H-016) and Cinematic (H-017) (`--theme`, outputs in
`render/<theme>/`, D-018). Beat data exists now (`beats` command, `beats.ensure_beats`, D-022).
Next: step 12, Beat Pop (H-012, D-017).

## Next up

1. **Resume point:** `/start_work` step 12 (Beat Pop, `feature/beat-pop-theme`), then `/spec`.
   It renders with `beats.ensure_beats(song_dir)` (computes `beats.json` once if missing). Needs
   from the owner: a beat-heavy test song (Punjabi / party / rap) in `songs/`, since
   `khidki_full` is a romantic song; the spec also decides drops (owner-marked or detected) and
   Anton + Anek Devanagari fonts (SIL OFL, bundled as Poppins was, D-018).
2. Optional cleanup: `render/check.py` (≈359 lines) and `render/karaoke.py` (≈310) are past
   the ~300-line split guideline (`lofi.py` is 268 since step 10); split only if the owner
   wants it (e.g. a `chore/` branch).
3. Steps 12–13 follow in plan order (H-012, D-017), one branch each; step 14 (Devanagari
   shaping) only when a song needs it.
4. Owner: try a different song end to end (spec 05 AC4), now with any theme.
5. Step 04 (`.lrc` anchors) only if a real song drifts.

## Waiting on the owner

- A beat-heavy test song (Punjabi / party / rap) in `songs/<name>/` (`audio.*` + `lyrics.txt`)
  for step 12, Beat Pop.
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
