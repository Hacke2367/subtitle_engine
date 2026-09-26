# Pending Work

Last updated: 2026-09-26 (step 06 shipped for review)

## WIP

- Step 06, emphasis words (`*word*`), on `feature/emphasis-markers` (base `dev @ 72dee83`).
  Status: Review, PR open (see the plan's status board). Gate green; every spec 06 AC passes.
  Also carries the styling research and session (6)'s roadmap (steps 08-14, H-012, D-017).

## Current focus

V1.1 styling. H-009 decided `*word*` emphasis; H-011 decided Pop Karaoke as the first new theme.
Step 06 (emphasis) comes first, then step 07 (Pop Karaoke) on its own branch (D-016).

## Next up

1. **Resume point:** the owner merges step 06's PR (`/merge_pr`), then `/start_work` step 07
   (Pop Karaoke) off the updated `dev`.
2. Step 07: `/start_work` for Pop Karaoke once step 06 is merged.
3. Steps 08–13 follow in plan order (H-012, D-017), one branch each; step 14 (Devanagari
   shaping) only when a song needs it.
4. Owner: try a different song end to end (spec 05 AC4).
5. Step 04 (`.lrc` anchors) only if a real song drifts.

## Waiting on the owner

- Merge step 06's PR (1.5x shipped; 2x preview in `songs/khidki_s2_em_2x` if you change your mind).
- Try a different song: `align` → `clip` → `make` (spec 05 AC4).
- Rotate the ElevenLabs API key (it was pasted in chat).
- FYI (D-010): the local model's weights are non-commercial (CC-BY-NC). Fine for V1, but it
  matters if this ever becomes a SaaS.

## Owner to-dos

- `docs/reference/knietic_lyric.pdf` is blank (3 empty pages). Re-export it from Gemini if it
  held anything, or delete it.
