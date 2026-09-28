# Pending Work

Last updated: 2026-09-28 (step 13 built, owner look pending)

## WIP

Step 13 (Phonk Neon) built on `feature/phonk-neon-theme`: spec, plan and code in one run (H-020
flow). Gate green; all checks pass on `khidki_s2`, `khidki_s2_em`, `khidki_full`. Waiting on the
owner's look (AC10) before merge.

## Current focus

V1.1 styling. Eight themes: Soft Romantic v2 (default, H-015), Soft Romantic v1, Pop Karaoke,
Lofi Minimal, Lofi Typewriter (H-016), Cinematic (H-017), Beat Pop (H-019) and Phonk Neon
(H-020) (`--theme`, outputs in `render/<theme>/`, D-018). Beat data: `beats` command,
`drops.txt` (D-022, D-024). Working flow (H-020): owner answers the look questions up front,
then spec → plan → build in one run; the owner judges the finished look.

## Next up

1. **Resume point:** owner watches `songs/khidki_full/render/phonk-neon/preview.mp4` (and
   `khidki_s2`). Look changes → `theme.py` values on this branch; approval → merge PR.
2. Step 14 (Devanagari shaping) only when a song needs it. After that the plan has no scheduled
   step; "Later candidates" in `development_plan.md` are the owner's pick.
3. Optional cleanup: `render/check.py` (≈367 lines) and `render/karaoke.py` (≈313) are past
   the ~300-line split guideline; split only if the owner wants it (a `chore/` branch).
4. Owner: try a different song end to end (spec 05 AC4), now with any theme.
5. Step 04 (`.lrc` anchors) only if a real song drifts.

## Waiting on the owner

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
