# Pending Work

Last updated: 2026-09-26 (step 06 merged, PR #5)

## WIP

None. Step 06 (emphasis words) merged into `dev` via [PR #5](https://github.com/Hacke2367/subtitle_engine/pull/5).

## Current focus

V1.1 styling. Emphasis is done: `*word*` in `lyrics.txt`, drawn 1.5x its line (H-009, H-013).
Next: step 07, Pop Karaoke, the first new theme (H-011), then steps 08-13 (H-012, D-017).

## Next up

1. **Resume point:** `/start_work` step 07 (Pop Karaoke theme, branch `feature/pop-karaoke-theme`)
   off the updated `dev`, then `/spec`. No pending `H-` item blocks it (H-011 decided). The spec
   must cover a way to pick the theme per render, and the styling rules in
   `development_plan.md`; marked words keep the H-013 size rule.
2. Steps 08–13 follow in plan order (H-012, D-017), one branch each; step 14 (Devanagari
   shaping) only when a song needs it.
3. Owner: try a different song end to end (spec 05 AC4).
4. Step 04 (`.lrc` anchors) only if a real song drifts.

## Waiting on the owner

- FYI: emphasis ships at 1.5x; set `emphasis_scale` (up to 2.0) in `theme.py` any time. The 2x
  preview is in `songs/khidki_s2_em_2x`.
- Try a different song: `align` → `clip` → `make` (spec 05 AC4).
- Rotate the ElevenLabs API key (it was pasted in chat).
- FYI (D-010): the local model's weights are non-commercial (CC-BY-NC). Fine for V1, but it
  matters if this ever becomes a SaaS.

## Owner to-dos

- `docs/reference/knietic_lyric.pdf` is blank (3 empty pages). Re-export it from Gemini if it
  held anything, or delete it.
