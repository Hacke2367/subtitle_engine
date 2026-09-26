# Pending Work

Last updated: 2026-09-27 (step 07 merged, PR #6)

## WIP

None. Step 07 (Pop Karaoke theme) merged into `dev` via
[PR #6](https://github.com/Hacke2367/subtitle_engine/pull/6).

## Current focus

V1.1 styling. Two themes ship: Soft Romantic and Pop Karaoke (`--theme`, outputs in
`render/<theme>/`, D-018). Next: step 08, Soft Romantic v2, then steps 09-13 (H-012, D-017).

## Next up

1. **Resume point:** `/start_work` step 08 (Soft Romantic v2, branch `feature/soft-romantic-v2`)
   off the updated `dev`, then `/spec`. No pending `H-` item blocks it. The spec must decide
   whether v2 replaces v1 or sits beside it, and must ask the owner to re-approve any waiting
   next line (H-010 kept "no ghosting"). It should also bring Soft Romantic inside the safe zone
   (x 60-960; today x 90-990) and reuse step 07's dim/scale primitives in `render/karaoke.py`.
2. Steps 09–13 follow in plan order (H-012, D-017), one branch each; step 14 (Devanagari
   shaping) only when a song needs it.
3. Owner: try a different song end to end (spec 05 AC4), now with either theme.
4. Step 04 (`.lrc` anchors) only if a real song drifts.

## Waiting on the owner

- FYI (D-018): renders now go to `songs/<song>/render/<theme>/`. Older outputs directly in
  `songs/<song>/render/` were left in place; delete them whenever you like.
- FYI: emphasis ships at 1.5x; set `emphasis_scale` (up to 2.0) in `theme.py` any time. The 2x
  preview is in `songs/khidki_s2_em_2x`.
- Try a different song: `align` → `clip` → `make` (spec 05 AC4).
- Rotate the ElevenLabs API key (it was pasted in chat).
- FYI (D-010): the local model's weights are non-commercial (CC-BY-NC). Fine for V1, but it
  matters if this ever becomes a SaaS.

## Owner to-dos

- `docs/reference/knietic_lyric.pdf` is blank (3 empty pages). Re-export it from Gemini if it
  held anything, or delete it.
