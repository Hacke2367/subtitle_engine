# Spec: Cinematic Theme
**Version:** 1.0.1 | **Component:** themes (`theme.py`), layout (couplet block), renderer (`render/`), render checks
**Status:** Approved by owner 2026-09-27 ("yes"), including the §7 choices. v1.0.1: §4.6 and two
§5 rows say how short words, neighbour blur and italic lean are met (plan §2.11-2.12); no change in
scope. AC10: the owner approved the look ("maine preview dekha mujhe acha laga") and asked to
merge PR #9 (2026-09-27).
**Plan step:** 10 (`docs/development_plan.md`) · **Branch:** `feature/cinematic-theme` · **Decisions:** H-017, H-012, H-013, H-010, H-009, D-017, D-018, D-020

## 1. Problem Statement

The engine has five looks: Soft Romantic v1 and v2 (warm, glowing), Pop Karaoke (bold fill) and
the two Lofi themes (light sans, one line). None fits ghazals and slow ballads. The research
(§3 shortlist 4, §9 "Ghazal") found those edits use a book serif in ivory and antique gold,
very slow motion, no glow, and poem-like layout: a couplet (sher) centred with generous spacing.
The blueprint calls this style "Minimalist Cinematic". H-012 and D-017 put it next, after step
08, whose line blur it reuses.

## 2. Objective

`render songs/<song> --theme cinematic` renders the same `words.json` as couplets whose words
blur into focus as they are sung (§4), with every render check passing, the other five themes
unchanged, and the owner approving the look.

## 3. Scope & Constraints

**Will Do:**
- One new theme, `cinematic`, beside the existing ones (outputs in `render/cinematic/`, D-018).
- Couplets (H-017): the lines of a stanza show in pairs (1+2, 3+4); the first line stays while
  the second reveals below it, then both leave together. A leftover line shows alone.
- Words appear only as they are sung (H-017, as H-010): each blurs into focus on its own time,
  in antique gold, then settles to ivory.
- A slow blur-out exit for the whole couplet.
- Bundle Cormorant Garamond Medium Italic (SIL OFL) in `fonts/`, with its licence.
- Marked `*word*`s at `emphasis_scale` × their line's size (H-013).
- Render checks: a reveal sync check and the safe-zone check, as §4.6.
- Unit tests for pairing, couplet layout, blur-in, colour, block life cycle and the theme;
  offline, synthetic fixtures.

**Will NOT Do:**
- Show any word before it is sung: no dim upcoming line, no rack focus (H-017).
- Change Soft Romantic v1, v2, Pop Karaoke, Lofi Minimal or Lofi Typewriter. Their frames stay
  pixel-identical.
- Glow, stroke, backplate, scale pop, rise, or a slow drift / push-in on the text. The legibility
  layer is a soft shadow.
- Letterbox bars, film grain, vignette or colour grade: they belong to the footage in CapCut
  (research §2).
- Any pairing syntax beyond blank lines in `lyrics.txt`; any change to `lyrics.txt` casing or
  text (red line 2).
- Beat-driven motion (beat data is step 11).
- Devanagari shaping (step 14) or a Nastaliq / Urdu script font.
- Change the default theme (it stays `soft-romantic-v2`, H-015), `words.json`, alignment, or the
  command-line options beyond the new `--theme cinematic`.

**Hard Rules:**
- **Red line 1:** a word's first ink is on the frame of `start − lead` and no earlier; it is
  complete (sharp, full opacity, gold) no later than the frame of `end − lead` and stays gold
  until then. Blur-in, colour fade, the couplet's hold and its exit are decoration and never move
  a word's first frame. A word with no timing never turns gold.
- **Red line 2:** every drawn string is the `words.json` text (the existing assertion). Blur is
  applied to the word's own drawn sprite; it never draws a different string.
- Styling rules (plan, research §5-§8): ease-out in, ease-in out, no overshoot; one font family
  plus the existing glyph fallback; one palette; a legibility layer; every drawn pixel, blur and
  shadow included, inside the safe zone x 60-960, y 380-1540; no hue-120 green (the existing
  theme guard).

## 4. Core Design

### 4.1 What the screen shows

One **block** at a time: a couplet (two lyric lines) or a single line, centred on x 510.

| Word state | Look |
|---|---|
| Not sung yet | not drawn |
| Being sung (**current**) | antique gold; blurs into focus from its first frame (§4.4) |
| Sung | ivory; fades from gold over 0.8 s from the frame of `end − lead` |
| Flagged (only with `--allow-flagged`) | sharp ivory from its own line's first frame; never gold |

Every drawn word carries the soft shadow, blurred with it while it blurs.

### 4.2 Couplets

- **Pairing.** Blank lines in `lyrics.txt` split stanzas (they are kept in `words.json`'s
  `lyrics.lines`). Inside a stanza, lines pair in order: 1+2, 3+4, and so on. An odd stanza's
  last line is a single. Pairing counts from the song folder's own first line, so a clip that
  starts mid-couplet pairs from its own first line.
- **Split.** A pair shows as two singles when its second line's first word starts more than
  `couplet_max_gap_s` (4 s) after its first line's last word ends, so a line never waits alone
  through an interlude.
- **Skipped lines.** A line with no timed word is skipped and reported, as today; its partner
  shows as a single.
- **Layout.** Both lines of a couplet are laid out when the block starts, so the first line never
  moves when the second appears. Each line wraps as today (balanced wrap, up to 3 rows); both
  lines use one font size, the smaller of their two fitted sizes. The second line sits below the
  first with an extra `couplet_gap` (0.5 × the row pitch). The block is centred on `anchor_y` and
  moved up only as far as needed to keep its bottom inside y 1540. A couplet taller than the
  safe zone at the smallest size shows as two singles; the report lists it as a note.

### 4.3 Block life cycle

1. **Enter.** No entrance: the block's first word blurring in is the entrance.
2. **Sing.** Each word blurs in and changes colour on its own time. The first line stays, sharp,
   while the second line's words appear below it.
3. **Leave.** After the block's last word ends, it holds for `hold` (2.0 s), then blurs out
   (blur 0 → 10 px) while fading, over 0.8 s (ease-in). The screen is then empty until the next
   block.

The rules for blocks close together are Lofi Typewriter's (spec 09 §4.2, D-020), with "line"
read as "block":
- Two blocks are never on screen at once, and the frame before the next block's first word
  (`F − 1`) is empty.
- A block never starts leaving before its last word's `end − lead`, so every word shows its whole
  current window.
- When the next block needs the screen before `hold` is over, the old block leaves early, as
  late as it can.
- When the time between the old block's last word end and `F − 1` is shorter than the exit, the
  exit shrinks to fit. Below two frames, the old block disappears on `F` (a cut); report note.
  Blocks sung back to back (the next first word starts before the old last word ends) are cut on
  the next word's first frame; the old last word loses its remaining frames. Report note.

### 4.4 Blur-in and colour

A word's first frame is the frame of `start − lead` (lead 0.05 s, as every theme). From there it
goes from blur 10 px and opacity 0 to blur 0 and full opacity over `reveal` (0.5 s, ease-out). For
a word shorter than `reveal`, the blur-in shrinks to fit its own span, so every timed word is
complete on the frame of `end − lead`. The word is gold from its first frame until that frame,
then fades to ivory over 0.8 s, starting from complete, with no jump.

### 4.5 Start values (all in `theme.py`; the owner tunes them after the preview)

| Value | Start | Source |
|---|---|---|
| Font | Cormorant Garamond Medium Italic (bundled), existing fallback chain after it | research §3, §6 |
| Line size / smallest shrink size | 96 px / 64 px (Cormorant's small x-height) | research §8 (96-125 px, 44 px floor) |
| Tracking | 0 | italic lowercase reads worse spaced out |
| Current / sung | antique gold `#C9A66B` / ivory `#EDE6D6` | research §7 palette 7 |
| Shadow | `#000000`, 70%, soft blur, small drop | research §7 palette 7, §8 |
| Blur-in | 0.5 s, 10 px → 0, opacity 0 → 1, ease-out | research §4 ("radius ramps ~12 to 0") |
| Gold → ivory | 0.8 s from `end − lead` | "very slow" |
| Hold / exit | 2.0 s / 0.8 s blur-out 0 → 10 px + fade, ease-in | research §3 ("very slow") |
| Couplet gap / split | 0.5 × row pitch / 4 s | research §9 ("generous line spacing") |
| Text box / safe zone | centred on x 510, inside x 60-960, y 380-1540 | research §8, spec 07 §4.6 |
| Lead / emphasis | 0.05 s / `emphasis_scale` 1.5 | spec 03, H-013 |

### 4.6 Render checks

The existing output checks (sizes, frame rate, frame count, alpha, audio) run as for every theme.

- **Reveal sync:** from the decoded overlay, each timed word has no ink on the frame before
  `start − lead`, and is complete (its at-rest ink, sharp, in gold) once its blur-in completes
  (shrunk to fit a short word) and still on the frame before `end − lead`. Read only where the
  block is not leaving and no other block is on screen; a word that cannot be read that way is a
  report note, never a silent pass. A neighbour's blur-in halo is gold over gold ink (every
  shadow is drawn under every glyph), so it never blocks a read.
- **Safe zone:** no drawn pixel (the same alpha threshold as Pop Karaoke) outside x 60-960,
  y 380-1540 in any frame, blur-in and blur-out included.

### 4.7 Test songs

`khidki_s2` and `khidki_s2_em` (four lines, one stanza: two couplets; marked words), and
`khidki_s2_lofi` (lowercase). No new song folder.

## 5. Edge Cases & Error Handling

| Case | Behaviour |
|---|---|
| Odd stanza | last line shows as a single (§4.2) |
| Couplet's second line far behind the first (> 4 s) | two singles (§4.2) |
| One line of a pair has no timed word | skipped and reported as today; partner shows as a single |
| Couplet too tall at the smallest size | two singles; report note (§4.2) |
| Clip starting mid-couplet | pairs from the clip's own first line (§4.2) |
| Next block due before `hold` ends | old block leaves early (§4.3) |
| Blocks sung back to back | cut on the next word's first frame; report note (§4.3) |
| Long instrumental gap | block leaves after `hold`; screen empty |
| First word near 0:00 | blurs in from its own frame; no entrance to fit |
| Word shorter than one frame | complete on its own first frame (no blur-in); read by the check like any word |
| Word shorter than `reveal` | blur-in shrinks to fit its span (§4.4) |
| Italic letters leaning past their advance | the word gap is wider than the font's widest lean (unit test) and the safe-zone check reads drawn pixels, so a leaning letter never touches the next word or leaves the safe zone |
| Devanagari or emoji in a line | existing fallback chain draws it (Devanagari unshaped until step 14) |
| Marked word on a line that had to shrink | size ratio kept (H-013), at the couplet's shared size |
| Word with no `start`/`end`, `--allow-flagged` | §4.1 flagged row; listed in the report as today |
| Word with no timing, no `--allow-flagged` | render refuses, as today |
| A line too long even at the smallest size and 3 rows | render refuses and names the line, as today |
| Cormorant Garamond missing from `fonts/` | render refuses and names the missing file (never a silent fallback) |
| Blur halos on the green mp4 | key at partial alpha like the shadow; the alpha `.mov` is exact |

## 6. Acceptance Criteria

1. **Theme choice:** `render songs/khidki_s2 --theme cinematic` succeeds from the existing
   `words.json` with no align call and writes to `render/cinematic/`; `report.md` names the theme.
   `make --theme cinematic` works the same way. A plain `render` still uses `soft-romantic-v2`.
2. **Other themes untouched:** `soft-romantic`, `soft-romantic-v2`, `pop-karaoke`, `lofi-minimal`
   and `lofi-typewriter` renders of `khidki_s2` give frames pixel-identical to `dev`'s renderer
   at every 30th frame.
3. **Couplets (unit test):** on synthetic lyrics, lines pair 1+2, 3+4 inside each stanza; an odd
   stanza's last line is a single; a pair more than 4 s apart, a pair with a skipped line, and a
   pair too tall for the safe zone each show as singles. In a couplet, both lines have the same
   font size, the first line's boxes are identical before and after the second line appears, and
   the block lies inside the safe zone.
4. **Blur-in and colour (unit test):** on synthetic words, a word has no ink on the frame before
   `start − lead`, has ink on that frame, is complete (blur 0, full opacity, gold) no later than
   the frame of `end − lead` (after `reveal`, or its own span if shorter), is gold through the
   frame before `end − lead`, and is ivory 0.8 s later. A flagged word is sharp ivory from its
   line's first frame and never gold.
5. **Block life cycle (unit test):** at most one block is visible in any frame; frame `F − 1`
   before each block is empty; a block never starts leaving before its last word's `end − lead`;
   hold, early leave, shrink and cut follow §4.3 on synthetic timings, including back-to-back
   blocks, an instrumental gap and a first word at 0:00.
6. **Render checks pass:** reveal sync, safe zone, and all existing output checks pass on
   `khidki_s2`, `khidki_s2_em` (marked words) and `khidki_s2_lofi`.
7. **Emphasis:** a marked word's box is exactly its text measured at `emphasis_scale` × its
   couplet's size; words in a row share a baseline and no boxes overlap (spec 06 AC5, re-run).
8. **Text:** every drawn string equals its `words.json` text (existing assertion).
9. **Speed:** `cinematic` renders `khidki_s2` in at most twice Soft Romantic v1's time on this
   laptop.
10. **Look:** the owner approves `songs/khidki_s2_em/render/cinematic/preview.mp4`. Changes asked
    for are made as `theme.py` values, not new behaviour, unless the owner asks for new behaviour.
11. The gate passes (unit tests + alpha proof).

## 7. Choices made for the owner (object to any before `/plan`)

- **Cormorant Garamond Medium Italic** over Tiro Devanagari Hindi: the lyrics are Hinglish in
  Latin script, and Cormorant reads as "cinematic serif" where Tiro reads as a book face. Tiro
  covers Devanagari in the same file; switching is one font file and one `theme.py` value.
- **Gold marks the word being sung**, ivory once sung: the only sync cue besides the blur-in,
  since the brief has no glow. Marked words differ by size only, as every theme.
- **Blur-in 0.5 s, shrunk to a short word's span**: slow on held notes, never still blurry after
  the word is sung (red line 1: the visual never implies a later timing).
- **No entrance, a 2 s hold, a 0.8 s blur-out**: the slowest motion of all themes.
- **Couplets split past a 4 s gap**, so a first line never waits alone through an interlude.
- **Shadow only, no backplate**: the research's `#0F0F0F` 65% backplate is a look no theme has
  yet; the 70% shadow keeps it readable on bright footage.
