# Spec: Title Card
**Version:** 1.0.0 | **Component:** renderer (`render/`), themes (`theme.py`), `clip`
**Status:** Owner choices made up front (H-021); spec, plan and build in one run (H-020 flow).
AC8: the owner approved and asked to merge PR #13 ("Merge karo", 2026-09-29).
**Plan step:** 15 (`docs/development_plan.md`) · **Branch:** `feature/title-card` · **Decisions:** H-021, H-020, D-018

## 1. Problem Statement

Indian lyric shorts open with a credit card, "Song | Singer" (Bollywood adds the film). The singer
name is a discovery keyword (research §9). Today the owner adds it by hand in CapCut, in a look
that does not match the lyric theme.

## 2. Objective

When `songs/<song>/title.txt` exists, every theme's render shows its text as a small card at the
top of the frame for the first ~3 s, drawn in that theme's own font, colours and legibility
layer. Without the file, renders are pixel-identical to today.

## 3. Scope & Constraints

**Will Do:**
- Read `songs/<song>/title.txt`: one or two non-blank lines, drawn exactly as written (spelling,
  casing, separators, emoji, film name). Only surrounding spaces and blank lines are dropped.
- Card at the top of the safe zone (first row's box top at y 420), centred on the theme's `center_x`. It fades
  in over 0.3 s from frame 0, holds, and fades out by 3.0 s.
- Card look per theme (H-021): the theme's font at about half its lyric size, its `text_rgb`, its
  shadow (stroke outline when it has one), its stroke; Phonk Neon also has its glow at rest
  strength under its dark rim.
- A too-wide line shrinks the card (down to 28 px); still too wide → render refuses.
- `clip` copies `title.txt` into the clip folder.
- Checks: the card is on the decoded overlay while it holds; no lyric ink under the card while it
  shows (a failure, so a clash is never silent); safe zone as before.
- Report line naming the card text and its time span.

**Will NOT Do:**
- Change the lyrics, their timing or their layout (red lines 1 and 2 untouched).
- Title text from the CLI, `words.json` or metadata; a persistent card; a progress bar or album
  art; Devanagari shaping (step 14).
- Pulse the card on beats.

**Hard Rules:**
- The card text is `title.txt` as written; nothing is cased, translated or reordered.
- No `title.txt` → every frame byte-identical to a render without this feature.
- Card pixels stay inside the theme's safe zone (x 60–960, y 380–1540) where the theme has one.

## 4. Core Design

- `render/card.py`: read `title.txt`, build one RGBA card image per render, and wrap the theme's
  frame stream: frames inside the card's span are composed with the faded card; every other frame
  passes through untouched.
- Card numbers in `theme.py` (shared defaults; a theme may override): `card_scale 0.5`,
  `card_top 420`, `card_s 3.0`, `card_in_s 0.3`, `card_out_s 0.5`, `card_min_size 28`,
  `card_glow 0.0` (Phonk Neon: its `pulse_low`).
- Two lines stack at the theme's row pitch, each centred.

## 5. Edge Cases

| Situation | Behaviour |
|---|---|
| No `title.txt` | No card, no note; frames identical |
| Empty / only blank lines | No card; report note |
| Three or more lines | Render refuses, naming the file |
| A character no theme font has | Render refuses (the layout's "no font has" error) |
| Line too wide at 28 px | Render refuses, naming the line |
| Song shorter than 3 s | The card ends with the song |
| Lyrics under the card (e.g. Pop Karaoke's past line early) | Check fails with the first frame |

## 6. Acceptance Criteria

1. With `title.txt`, `render --theme X` shows the card on frames 0 … 3.0 s for all eight themes;
   every render check passes on `khidki_s2`, `khidki_s2_em`.
2. Without `title.txt`, all eight themes' frames are hash-identical to `dev`.
3. Card text drawn is `title.txt` as written (unit: the drawn mask equals the mask of the file's
   lines; casing kept).
4. Fade (unit): opacity rises from frame 0, is full while holding, is 0 from 3.0 s on.
5. Collision (unit): lyric ink under the card fails the check; no ink passes.
6. Errors (unit): three lines, a too-long line → refuse; blank file → no card with a note.
7. `clip` copies `title.txt`.
8. Owner approves the card's look on a preview.
9. Gate passes.
