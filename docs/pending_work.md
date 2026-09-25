# Pending Work

## WIP

`feature/alpha-overlay-proof` (from `dev` @ b08e6b1, 2026-09-26): step 01, status Owner test.
Generator, encoder and checker built (`scripts/alpha_proof.py`); all four variants pass the
automated checks (AC1–5, AC9). AC6–8 need the owner's CapCut test.

## Current focus

Owner imports the test clips from `out/01_alpha_proof/` into CapCut desktop (A/B/C `.mov`) and
CapCut mobile (`G_green.mp4`), following the checklist in `out/01_alpha_proof/results.md`.

## Next up

1. Owner reports the CapCut results; record them in `docs/decision.md` or
   `docs/human_decision.md` (AC8); update project_context/plan if the output plan changes.
2. `/ship` step 01 → PR into `dev`.
3. Owner answers H-004 (alignment provider) before step 02.

## Owner to-dos (not blocking)

- `docs/reference/knietic_lyric.pdf` is blank (3 empty pages). Re-export it from Gemini if it
  held anything, or delete it.
