# Pending Work

Last updated: 2026-09-26 (spec 06 approved, plan written)

## WIP

- Step 06, emphasis words (`*word*`), on `feature/emphasis-markers` (base `dev @ 72dee83`).
  Status: Build (spec approved, plan `docs/specs/06_emphasis_markers_impl.md`). Also carries the styling research (`docs/research/lyric_aesthetics.md`).

## Current focus

V1.1 styling. H-009 decided `*word*` emphasis; H-011 decided Pop Karaoke as the first new theme.
Step 06 (emphasis) comes first, then step 07 (Pop Karaoke) on its own branch (D-016).

## Next up

1. **Resume point:** build step 06 from `docs/specs/06_emphasis_markers_impl.md`, in its §11
   order. First action: the AC3 baseline (frame hashes of `songs/khidki_s2` from a `dev`
   worktree) before any source edit.
2. Step 07: `/start_work` for Pop Karaoke once step 06 is merged.
3. Owner: try a different song end to end (spec 05 AC4).
4. Step 04 (`.lrc` anchors) only if a real song drifts.

## Waiting on the owner

- Try a different song: `align` → `clip` → `make` (spec 05 AC4).
- Rotate the ElevenLabs API key (it was pasted in chat).
- FYI (D-010): the local model's weights are non-commercial (CC-BY-NC). Fine for V1, but it
  matters if this ever becomes a SaaS.

## Owner to-dos

- `docs/reference/knietic_lyric.pdf` is blank (3 empty pages). Re-export it from Gemini if it
  held anything, or delete it.
