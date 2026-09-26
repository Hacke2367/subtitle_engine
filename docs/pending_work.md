# Pending Work

## WIP

None. Step 01 merged into `dev` via [PR #1](https://github.com/Hacke2367/subtitle_engine/pull/1).

## Current focus

Step 02 of `docs/development_plan.md`: word alignment → `words.json`.

## Next up

1. `/start_work` → step 02, branch `feature/word-alignment` → `/spec`. H-004 answered by the
   owner (option c: try ElevenLabs API and a local pipeline on one song); record it at start.
2. Owner provides the test song "Mere Samne Wali Khidki Mein": audio + exact lyrics in
   `songs/<name>/`, and an ElevenLabs API key in `.env`.

## Done

- Step 01, alpha overlay proof: automated checks pass. The CapCut import test is deferred (H-006).

## Owner to-dos

- **Before step 03's spec (H-006):** import `out/01_alpha_proof/` clips into CapCut desktop and
  mobile using the checklist in `out/01_alpha_proof/results.md`, and report the results.
- `docs/reference/knietic_lyric.pdf` is blank (3 empty pages). Re-export it from Gemini if it
  held anything, or delete it.
