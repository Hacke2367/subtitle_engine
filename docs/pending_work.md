# Pending Work

Last updated: 2026-09-26 (handoff after steps 01–03)

## WIP

- `feature/soft-romantic-render` (stacked on `feature/word-alignment`, D-011): step 03, status
  Review, [PR #3](https://github.com/Hacke2367/subtitle_engine/pull/3) into `feature/word-alignment`
  (retarget to `dev` once PR #2 merges). The first real
  overlay is at `songs/khidki/render/`: 900 frames, 33.7 s render, all checks pass, one note
  (word 10 "hai" sung back to back).
- `feature/word-alignment`: step 02, Review,
  [PR #2](https://github.com/Hacke2367/subtitle_engine/pull/2).

## Current focus

V1 steps 01–03 are built. What's left needs the owner (see "Waiting on the owner"). Step 04
(`.lrc` line anchors) is optional per the plan; the khidki clip aligned with 0 flags without it.

## Next up

1. **Resume point:** steps 02 and 03 are in Review (PRs #2 and #3), waiting on the owner. Read
   `docs/pending_work.md` "Waiting on the owner" and `songs/khidki/render/report.md` first.
   Owner: watch `songs/khidki/render/preview.mp4` (look + sync) and import
   `render/overlay.mov` / `overlay_green.mp4` into CapCut desktop / mobile (H-006) → fix the
   default codec.
2. Owner: merge PR #2, then PR #3 (retargeted to `dev`).
3. Step 04 only if real songs drift without line anchors.

## Done

- Step 01, alpha overlay proof ([PR #1](https://github.com/Hacke2367/subtitle_engine/pull/1)):
  automated checks pass. The CapCut import test is deferred (H-006).

## Waiting on the owner

- Merge PR #2, then PR #3 (retargeted to `dev`); both fully accepted after H-010.
- H-009: how to mark emphasis words (recommendation: `*word*` in lyrics.txt).
- Choose the next direction (workflow commands vs more styling / themes).
- Rotate the ElevenLabs API key (it was pasted in chat).
- FYI (D-010): the local model's weights are non-commercial (CC-BY-NC). Fine for V1, but it
  matters if this ever becomes a SaaS.

## Owner to-dos

- `docs/reference/knietic_lyric.pdf` is blank (3 empty pages). Re-export it from Gemini if it
  held anything, or delete it.
