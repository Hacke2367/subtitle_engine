# Pending Work

## WIP

`feature/word-alignment` (from `dev` @ 52e87d6): step 02, status Review; PR into `dev` (link
below once opened). Bake-off on the 30 s clip `songs/khidki` (27.0–57.0 s, lines 1–8): L-vocals
valid (0/44 flagged), E-variants blocked by the key permission. Provisional default L-vocals
(D-009).

## Current focus

Step 03 (Soft Romantic renderer), stacked on the step 02 branch until the owner merges (H-008).

## Next up

1. `/start_work` step 03 from `feature/word-alignment` → spec → plan → build (codec left
   configurable until the CapCut test, H-006).
2. When the owner is back: merge step 02, enable the ElevenLabs permission and re-run the
   bake-off, and watch the L-vocals preview.

## Done

- Step 01, alpha overlay proof ([PR #1](https://github.com/Hacke2367/subtitle_engine/pull/1)):
  automated checks pass. The CapCut import test is deferred (H-006).

## Waiting on the owner (H-008: work continues around these)

- Merge PRs (explicit instruction needed).
- **ElevenLabs key lacks the `forced_alignment` permission** (bake-off got HTTP 401, no charge).
  Enable it in the ElevenLabs dashboard (or make a key with it), then run
  `venv/Scripts/python -m lyric_engine.cli bakeoff songs/khidki` to add E-raw/E-vocals.
- Confirm the aligner by watching `songs/khidki/bakeoff/L-vocals/preview.mp4` (D-009 picked
  L-vocals provisionally). Listen closely to chorus lines 2–4, which have the lowest scores.
- FYI (D-010): the local model's weights are non-commercial (CC-BY-NC). Fine for V1, but it
  matters if this ever becomes a SaaS.
- Rotate the ElevenLabs API key (it was pasted in chat).

## Owner to-dos

- **Before step 03's spec (H-006):** import `out/01_alpha_proof/` clips into CapCut desktop and
  mobile using the checklist in `out/01_alpha_proof/results.md`, and report the results.
- `docs/reference/knietic_lyric.pdf` is blank (3 empty pages). Re-export it from Gemini if it
  held anything, or delete it.
