# Pending Work

Last updated: 2026-10-01 (khaali + backdrop built; Aakhri patta and Chaand in progress)

## WIP

Step 17 on `feature/bg-romantic-room` ([PR #16](https://github.com/Hacke2367/subtitle_engine/pull/16), not merged).
The pipeline is built and kept: `--bg`, a finished short with audio, stacked encode, checks;
D-028 to D-030. The room itself was rejected by the owner after it was built.

The owner then finalized three romantic light looks from moving samples (H-032 to H-036,
`docs/backgrounds/romantic_lights.md`): rain, fog and milan. All three are now built into the
engine (`--bg rain|fog|milan`; spec 17 v2, D-033, D-034), ported from the samples; the room's
modules are deleted. Rain needed a calmer patch behind the lyrics to pass the 3:1 check; the
owner decides keep or revert (H-039). Background frames of rain and fog are drawn in 4 worker
processes.

**V1 is complete (owner, 2026-09-29):** V1 core plus the V1.1 themes, beat detection and the
title card are merged into `dev`; step 15 was the last ([PR #13](https://github.com/Hacke2367/subtitle_engine/pull/13)).

## Current focus

Post-V1 (H-022 onward): engine-made backgrounds, one world per song type, each with moods.
Romantic: three light looks final and built (rain, fog, milan; H-034 to H-036), the room
rejected. Designed before H-032's rules, not built: hip-hop truck, party baraat, Sufi lamp,
motivational forge, journey train (`docs/backgrounds/`). Plan steps 17–23 build them; the owner
wants them built from the next session on. Not designed yet (H-029): mother and family,
patriotic, old classics.

V1 complete; proving it on more songs. Eight themes: Soft Romantic v2 (default, H-015), Soft Romantic v1, Pop Karaoke,
Lofi Minimal, Lofi Typewriter (H-016), Cinematic (H-017), Beat Pop (H-019) and Phonk Neon
(H-020) (`--theme`, outputs in `render/<theme>/`, D-018). Beat data: `beats` command,
`drops.txt` (D-022, D-024). Title card from `title.txt` (step 15). Working flow (H-020): owner
answers the look questions up front, then spec → plan → build in one run; the owner judges the
finished look.

## Next up

1. **Resume point (2026-10-01):** built into the engine on `feature/bg-romantic-room` (PR #16),
   all waiting for the owner's look approval:
   - romantic: rain, fog, milan (H-034 to H-036, final samples), chaand (Chaand ka ghoonghat,
     agent-built, ~7/10);
   - sad: khaali (Khaali jagah, from the approved still), aakhri (Aakhri patta, agent-built,
     ~6.5-7/10);
   - `backdrop` command: the look alone, with a song or `--seconds N` (D-035).
   Owner answers: H-039 (rain patch), approve or note each look from its 14 s / 30 s renders
   (`songs/khidki_30s/render/soft-romantic-v2/final_*.mp4`). Next per the owner's plan (H-038
   picks): Rail ki Seeti (classics), Taaron ka jaal (hip-hop, needs a beat test song), Jaali se
   subah (sufi: cache static parts first), Shamiyane ki parchhaiyan (party, beat song), Parchhaiyan
   (family). Stills and critic notes: `docs/backgrounds/template_stills.md`,
   `songs/_review/backgrounds/templates/_results.json`. Build flow: an agent makes
   `templates/<type>/<look>.py` with the Scene contract and tests it with
   `songs/_review/backgrounds/run_scene.py`, then it moves to `src/lyric_engine/background/`
   (import `from . import paint as P`, expose `.facts`), one line in `WORLDS`, a doc, a 30 s render.
   Kinaare ke nishaan (sad) has stills only.
2. Step 14 (Devanagari shaping) only when a song needs it. Step 16 (line breaks at sung
   pauses) only if the owner asks; it is outside the original V1 scope.
3. Optional cleanup: `render/check.py` (≈369 lines) and `render/karaoke.py` (≈313) are past
   the ~300-line split guideline; split only if the owner wants it (a `chore/` branch).
4. Owner: try a different song end to end (spec 05 AC4), now with any theme.
5. Step 04 (`.lrc` anchors) only if a real song drifts.

## Waiting on the owner

- For steps 18–22: one test song per type in `songs/<name>/` (`audio.*` + `lyrics.txt`):
  hip-hop, party/dance, Sufi, motivational, journey. The Khidki songs cover step 17.

- Write `songs/<song>/title.txt` for the songs you post (e.g. `♪ Khidki | Kishore Kumar`).
- Write your own drop times in `songs/<song>/drops.txt` (the ones in `khidki_full` are test
  values: 0:28.0, 1:30.8).
- Optional: a beat-heavy test song (Punjabi / party / rap) in `songs/<name>/` (`audio.*` +
  `lyrics.txt`) for the Beat Pop look check; `khidki_full` is used otherwise.
- Optional: listen to `songs/khidki_full/beats_preview.m4a`; if the clicks sit at twice or half
  the beat, run `beats songs/khidki_full --bpm <N>`.
- FYI (D-018): renders now go to `songs/<song>/render/<theme>/`. Older outputs directly in
  `songs/<song>/render/` were left in place; delete them whenever you like.
- FYI: emphasis ships at 1.5x; set `emphasis_scale` (up to 2.0) in `theme.py` any time. The 2x
  preview is in `songs/khidki_s2_em_2x`.
- Try a different song: `align` → `clip` → `make` (spec 05 AC4).
- FYI (D-010): the local model's weights are non-commercial (CC-BY-NC). Fine for V1, but it
  matters if this ever becomes a SaaS.

## Owner to-dos

- `docs/reference/knietic_lyric.pdf` is blank (3 empty pages). Re-export it from Gemini if it
  held anything, or delete it.
