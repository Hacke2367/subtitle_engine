# Pending Work

Last updated: 2026-09-26 (handoff after steps 01–03)

## WIP

- `feature/workflow-clip-make` (stacked on step 03, D-014): step 05, Review. `clip` + `make`
  work: the 27–57 s clip is byte-identical to the hand-made one; stanza 2 (75–89 s) went
  clip → make with 22/22 words, 0 flagged, checks pass, 45 s.
- `feature/soft-romantic-render`: step 03, Review,
  [PR #3](https://github.com/Hacke2367/subtitle_engine/pull/3) (stacked on #2).
- `feature/word-alignment`: step 02, Review,
  [PR #2](https://github.com/Hacke2367/subtitle_engine/pull/2).

## Current focus

Base plus workflow are done. A short is now: `align songs/<full>` once, then
`clip songs/<full> --from A --to B`, then `make songs/<clip>`.

## Next up

1. **Resume point:** steps 02, 03 and 05 are in Review, waiting on the owner to merge (#2 → #3 →
   step 05's PR, each retargeted to `dev` in turn). Then styling: H-009 emphasis, then more themes,
   which is a scope change to log.
2. Owner: try a **different song** end to end (spec 05 AC4).
3. Step 04 (`.lrc` anchors) only if a real song drifts.

## Waiting on the owner

- Merge PR #2, then PR #3 (retargeted to `dev`); both fully accepted after H-010.
- H-009: how to mark emphasis words (recommendation: `*word*` in lyrics.txt).
- Try a different song: `align` → `clip` → `make` (spec 05 AC4).
- Rotate the ElevenLabs API key (it was pasted in chat).
- FYI (D-010): the local model's weights are non-commercial (CC-BY-NC). Fine for V1, but it
  matters if this ever becomes a SaaS.

## Owner to-dos

- `docs/reference/knietic_lyric.pdf` is blank (3 empty pages). Re-export it from Gemini if it
  held anything, or delete it.
