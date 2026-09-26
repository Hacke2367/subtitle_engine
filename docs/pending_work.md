# Pending Work

Last updated: 2026-09-26 (after merging #2/#3/#4)

## WIP

None. Steps 02, 03 and 05 were merged into `dev` via PRs #2/#3/#4 (D-015).

## Current focus

V1 is done: song + lyrics → word-synced Soft Romantic overlay for CapCut, and `clip` + `make`
bring a short down to two commands. Next phase: styling (V1.1).

## Next up

1. **Resume point:** plan the styling phase. The owner answers **H-009** (emphasis marker,
   recommendation `*word*`) and picks the **first new theme** (Phonk / Lofi / Pop karaoke /
   Minimal). New themes are a scope change from V1's "one theme": log it with `/log_decision`,
   update `project_context.md`, add plan step 06, then `/start_work`.
2. Owner: try a different song end to end (spec 05 AC4).
3. Step 04 (`.lrc` anchors) only if a real song drifts.

## Waiting on the owner

- H-009: how to mark emphasis words (recommendation: `*word*` in lyrics.txt).
- Try a different song: `align` → `clip` → `make` (spec 05 AC4).
- Rotate the ElevenLabs API key (it was pasted in chat).
- FYI (D-010): the local model's weights are non-commercial (CC-BY-NC). Fine for V1, but it
  matters if this ever becomes a SaaS.

## Owner to-dos

- `docs/reference/knietic_lyric.pdf` is blank (3 empty pages). Re-export it from Gemini if it
  held anything, or delete it.
