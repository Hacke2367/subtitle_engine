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

## Waiting on the owner (H-008: work continues around these)

- Watch `songs/khidki/render/preview.mp4`: approve or tune the Soft Romantic look
  (theme.py). Open question: show upcoming words faintly ("ghost") so a line
  looks centred while it reveals?
- Merge PRs (explicit instruction needed).
- **ElevenLabs key lacks the `forced_alignment` permission** (bake-off got HTTP 401, no charge).
  Enable it in the ElevenLabs dashboard (or make a key with it), then run
  `venv/Scripts/python -m lyric_engine.cli bakeoff songs/khidki` to add E-raw/E-vocals.
- Confirm the aligner by watching `songs/khidki/bakeoff/L-vocals/preview.mp4` (D-009 picked
  L-vocals provisionally). Listen closely to chorus lines 2–4, which have the lowest scores.
- H-009: how to mark emphasis words (recommendation: `*word*` in lyrics.txt). The renderer
  ships without emphasis until this is answered.
- FYI (D-010): the local model's weights are non-commercial (CC-BY-NC). Fine for V1, but it
  matters if this ever becomes a SaaS.
- Rotate the ElevenLabs API key (it was pasted in chat).

## Owner to-dos

- **Before step 03's spec (H-006):** import `out/01_alpha_proof/` clips into CapCut desktop and
  mobile using the checklist in `out/01_alpha_proof/results.md`, and report the results.
- `docs/reference/knietic_lyric.pdf` is blank (3 empty pages). Re-export it from Gemini if it
  held anything, or delete it.
