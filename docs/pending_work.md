# Pending Work

Last updated: 2026-09-28 (step 12 merged, PR #11)

## WIP

None. Step 12 (Beat Pop) merged into `dev` ([PR #11](https://github.com/Hacke2367/subtitle_engine/pull/11)); the owner approved and asked to merge.

## Current focus

V1.1 styling. Seven themes: Soft Romantic v2 (default, H-015), Soft Romantic v1, Pop Karaoke,
Lofi Minimal, Lofi Typewriter (H-016), Cinematic (H-017) and Beat Pop (H-019) (`--theme`,
outputs in `render/<theme>/`, D-018). Beat data: `beats` command, `drops.txt` (D-022, D-024).
The owner wants to speed up the work from the next session and will say how first.

## Next up

1. **Resume point:** ask for / follow the owner's direction on speeding up the work (their first
   message next session). By plan order the next step is 13, Phonk Neon (`/start_work`,
   `feature/phonk-neon-theme`): saturated text with a same-hue glow pulsing on beats, and white
   flash, shake or RGB split on drops (research §3 shortlist 6). Its spec needs owner calls: the
   display font (blackletter vs wide bold; casing must stay as written), the drop effect, and the
   glow colour. It reuses step 12's beat motion (`beatpop.accent`, `drops.txt`).
2. Optional cleanup: `render/check.py` (≈359 lines) and `render/karaoke.py` (≈310) are past
   the ~300-line split guideline (`lofi.py` is 268 since step 10); split only if the owner
   wants it (e.g. a `chore/` branch).
3. Step 13 (Phonk Neon) follows in plan order (H-012, D-017), one branch each; step 14 (Devanagari
   shaping) only when a song needs it.
4. Owner: try a different song end to end (spec 05 AC4), now with any theme.
5. Step 04 (`.lrc` anchors) only if a real song drifts.

## Waiting on the owner

- Tell Claude how you want to speed up the work (next session).
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
