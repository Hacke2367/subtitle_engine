# Pending Work

Last updated: 2026-09-26 (step 07 started)

## WIP

Step 07, Pop Karaoke theme, on `feature/pop-karaoke-theme` (base `dev` @ 0ba2a4f). Status: Spec.

## Current focus

V1.1 styling. Emphasis is done: `*word*` in `lyrics.txt`, drawn 1.5x its line (H-009, H-013).
Now: step 07, Pop Karaoke, the first new theme (H-011), then steps 08-13 (H-012, D-017).

## Next up

1. **Resume point:** owner reviews `docs/specs/07_pop_karaoke_theme.md` (§7 lists the choices
   made for them: two lines on screen, hot pink accent, `render/<theme>/` folders, Poppins in
   the repo). On their yes, run `/plan`. Nothing gets built before that.
2. Steps 08–13 follow in plan order (H-012, D-017), one branch each; step 14 (Devanagari
   shaping) only when a song needs it.
3. Owner: try a different song end to end (spec 05 AC4).
4. Step 04 (`.lrc` anchors) only if a real song drifts.

## Waiting on the owner

- FYI: emphasis ships at 1.5x; set `emphasis_scale` (up to 2.0) in `theme.py` any time. The 2x
  preview is in `songs/khidki_s2_em_2x`.
- Try a different song: `align` → `clip` → `make` (spec 05 AC4).
- Rotate the ElevenLabs API key (it was pasted in chat).
- FYI (D-010): the local model's weights are non-commercial (CC-BY-NC). Fine for V1, but it
  matters if this ever becomes a SaaS.

## Owner to-dos

- `docs/reference/knietic_lyric.pdf` is blank (3 empty pages). Re-export it from Gemini if it
  held anything, or delete it.
