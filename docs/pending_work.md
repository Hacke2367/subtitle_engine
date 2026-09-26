# Pending Work

Last updated: 2026-09-27 (step 07 shipped for review)

## WIP

Step 07, Pop Karaoke theme, on `feature/pop-karaoke-theme` ([PR #6](https://github.com/Hacke2367/subtitle_engine/pull/6)). Status:
Review. Built, gate green, every acceptance criterion passes except AC10 (the owner's look
approval). Previews: `songs/khidki_s2_em/render/pop-karaoke/preview.mp4` (3 marked words),
`songs/khidki_s2/render/pop-karaoke/preview.mp4`, full song
`songs/khidki_full/render/pop-karaoke/preview.mp4`.

## Current focus

V1.1 styling. Step 07 (Pop Karaoke, H-011) is in review; then steps 08-13 (H-012, D-017).

## Next up

1. **Resume point:** the owner watches the Pop Karaoke previews (AC10). Look changes are
   `POP_KARAOKE` values in `theme.py` (accent, font size, past-line opacity/size, timings), then
   re-render; new behaviour only if the owner asks. On approval and "merge", run `/merge_pr`.
2. Step 08 (Soft Romantic v2) after step 07 merges; it also brings Soft Romantic inside the safe
   zone (x 60-960; today its rows are centred on 540 with a 900 px box, so x 90-990).
3. Owner: try a different song end to end (spec 05 AC4).
4. Step 04 (`.lrc` anchors) only if a real song drifts.

## Waiting on the owner

- Approve the Pop Karaoke look (spec 07 AC10), or name the changes (e.g. accent yellow
  `#FFD60A` / cyan `#00E5FF` instead of hot pink, bigger or smaller text).
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
