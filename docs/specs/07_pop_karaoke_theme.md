# Spec: Pop Karaoke Theme
**Version:** 1.0.1 | **Component:** themes (`theme.py`), layout, renderer (`render/`), render checks, CLI (`render`, `make`)
**Status:** Approved by owner 2026-09-27 ("yes"), including the §7 choices. v1.0.1: §4.3 wording
made exact (a leaving past line finishes its fade as the new line enters; AC4), no change in scope.
AC10: the owner approved by saying "merge" on PR #6 (2026-09-27).
**Plan step:** 07 (`docs/development_plan.md`) · **Branch:** `feature/pop-karaoke-theme` · **Decisions:** H-011, H-013, H-009

## 1. Problem Statement

The engine has one look, Soft Romantic: words fade in one by one as they are sung, with a soft
rose glow. That suits slow romantic songs, not upbeat pop, and every short from the channel
would look the same. H-011 picked Pop Karaoke as the second theme: the whole line is readable
before it is sung, and colour sweeps across each word exactly as the singer voices it. This is
the look viewers know from Apple Music and karaoke, and the one that shows off word-level sync
best. There is also no way today to choose a theme for a render, and a second render would
overwrite the first one's outputs.

## 2. Objective

`render songs/<song> --theme pop-karaoke` turns the same `words.json` into a Pop Karaoke overlay
(line shown ahead, left-to-right accent fill on each word over its own aligned time, finished
line dims above the next one), saved beside the Soft Romantic render, with every render check
passing.

## 3. Scope & Constraints

**Will Do:**
- A second theme, `pop-karaoke`, with the look in §4.
- Pick the theme per render: a `--theme` option on `render` and `make`. Default stays
  `soft-romantic`, so every existing command behaves as today.
- One output folder per theme, `songs/<song>/render/<theme>/`, holding that theme's
  `overlay.mov`, `overlay_green.mp4`, `preview.mp4` and `report.md`. Two themes never overwrite
  each other. The report names the theme.
- Marked `*word*`s follow H-013 in this theme: `emphasis_scale` × their line's size, for as long
  as the line is on screen, and they fill over their own time like any word.
- Ship the theme font in the repo: Poppins SemiBold (SIL OFL, licence file alongside), so the
  render and tests do not depend on what is installed on the machine.
- Render checks for the new theme: a fill-sync check (each word's fill starts and ends on its own
  time) and a safe-zone check (§4.6).
- A theme-level guard: a theme whose text, accent, stroke or glow colour is near the key green
  (hue 120) is refused when built, for every theme (styling rules, research §7).
- Unit tests for the fill timing, line states, safe zone, theme choice and output folders.
  Offline, synthetic fixtures (`songs/` is not in git).

**Will NOT Do:**
- Change Soft Romantic's look. Its frames stay pixel-identical; only its output folder moves.
  Its own upgrades, including the safe zone, belong to step 08.
- A next-line preview (the line after the current one waiting on screen), blur on inactive
  lines, glow, a highlight pill, or any beat-driven motion (steps 08–13).
- An extra emphasis treatment in this theme (colour, glow, pop). Size is the one emphasis
  (H-013).
- A per-song default theme, a theme per line, theme files outside `theme.py`, or command-line
  colour/size overrides. Tuning a look means editing `theme.py`.
- Syllable-level fill. The fill knows only a word's start and end.
- Deleting or moving outputs from older renders in `songs/<song>/render/`.
- Devanagari shaping (step 14). Poppins has Devanagari glyphs, but this Pillow cannot shape them.

**Hard Rules:**
- **Red line 1:** a word's fill starts at its own `start` and completes at its own `end` (both
  minus the theme's uniform lead), moving linearly in between. No fill is ever shortened,
  stretched or given to a word without a timing. Line entrances, dimming and exits are
  decoration: they never move a word's fill.
- **Red line 2:** every drawn string is the `words.json` text, which is `lyrics.txt` minus the
  marker asterisks. No auto-casing, no caps-only font. Poppins keeps real lowercase.
- Styling rules for theme steps (plan, research §5–§8): ease-out in, ease-in out, overshoot at
  most 10%; one font family plus the existing glyph fallback; one palette; a legibility layer;
  text inside the safe zone; no hue-120 green.

## 4. Core Design

### 4.1 Theme choice and output folders

The themes are a fixed, named set in `theme.py` (`soft-romantic`, `pop-karaoke`). `render` and
`make` take `--theme NAME`; an unknown name is a usage error that lists the valid names. The
chosen theme decides both the look and the output folder `render/<theme>/`. Nothing about the
theme is written into `words.json`, so any song renders in any theme with no re-align, and a
hand-edited `words.json` works in both.

### 4.2 What the screen shows

At most two lyric lines are on screen: the **current line** at the anchor, and the **past line**
(the one before it) above it.

| State | Look |
|---|---|
| Current line, word not yet sung | white, full opacity |
| Current line, word being sung | accent colour sweeps across it left to right, soft edge |
| Current line, word sung | accent colour, stays until the line leaves |
| Past line | its sung look, at 40% opacity and 80% size, just above the current line |
| Flagged word (only with `--allow-flagged`) | white, never fills (it has no time to fill on) |

Every word keeps a dark stroke and a soft shadow in every state, so white and accent both read
on bright footage.

### 4.3 Line life cycle

1. **Enter.** A line appears `preroll` before its first word's fill starts, or right after the
   previous line's last word finishes, whichever is later, but never later than one entrance
   duration before its first word's fill starts. It fades in and scales from 94% to 100% with an
   ease-out that overshoots by at most 10% of the move. So it is always at rest (full size, full
   opacity, final place) when its first word's fill starts.
2. **Sing.** Each word fills on its own time (§4.4).
3. **Hand over.** When the next line enters, the current line moves up into the past slot while
   dimming and shrinking, over the same duration. A line already in the past slot fades out,
   finishing as the new line enters, so no more than two lines are ever visible.
4. **Clear.** If the next line does not enter within `hold` after a line's last word ends (an
   instrumental gap), the line fades out and the screen empties; a past line fades with it. The
   next line then enters alone.

If the next line has to enter before the current line's last word has finished (lines sung back
to back), that word keeps filling on its own time in the past slot. The report lists it as a
note, not a failure.

### 4.4 Fill

A word's fill progress is 0 before `start − lead`, 1 after `end − lead`, and linear in time
between them. The filled part is the word's left fraction of that progress, so the edge sweeps
left to right across the word's own drawn glyphs. Spaces never fill. A word shorter than a frame
fills in one frame.

### 4.5 Start values (all in `theme.py`; the owner tunes them after the preview)

| Value | Start | Source |
|---|---|---|
| Font | Poppins SemiBold, existing fallback chain after it | research §3, §6 |
| Line size / smallest shrink size | 96 px / 64 px, up to 3 rows | research §8 |
| Text / accent | white `#FFFFFF` / hot pink `#FF2E88` | research §7 palette 4 |
| Stroke | `#0B0B14`, about 4% of the word's size | research §8 |
| Shadow | black, 50%, small blur, slight drop | research §8 |
| Enter / hand-over | 0.28 s, ease-out with ≤10% overshoot | research §5 |
| Preroll / hold / exit fade | 0.5 s / 1.0 s / 0.2 s | research §5 |
| Past line | 40% opacity, 80% size | research §3 |
| Lead | 0.05 s, same as Soft Romantic | spec 03 |
| Emphasis | `emphasis_scale` 1.5 (H-013 range 1.5–2.0) | H-013 |

### 4.6 Safe zone

Every Pop Karaoke frame keeps all drawn text, stroke and shadow included, inside x 60–960,
y 380–1540 at 1080×1920. The text block is centred on x 510, the middle of that zone. A line
that does not fit shrinks or wraps as today. When the past line would not fit above the current
line inside the zone, it fades out at hand-over instead of moving up.

### 4.7 Render checks

The existing checks (sizes, frame rate, frame count, alpha, audio) run for both themes. The
existing alpha-based sync check stays for Soft Romantic. Pop Karaoke gets:

- **Fill sync:** for each timed word, read from the decoded overlay, the word shows no accent
  in the frame before its fill starts, and is fully accent by the frame after its fill ends.
- **Safe zone:** no visible pixel outside the zone in any frame.

## 5. Edge Cases & Error Handling

| Case | Behaviour |
|---|---|
| No `--theme` | `soft-romantic`, outputs in `render/soft-romantic/` |
| `--theme unknown` | usage error listing valid theme names; nothing rendered |
| Old outputs directly in `render/` | left untouched; the owner may delete them |
| First word within enter time of 0:00 | the line is shown at rest from frame 0, no entrance |
| Lines sung back to back (next starts before last word ends) | §4.3: last word keeps its fill time in the past slot; report note |
| Long instrumental gap | line fades out after `hold`; screen empty; next line enters alone |
| Word with no `start`/`end`, `--allow-flagged` | drawn white, never fills; listed in the report as today |
| Word with no timing, no `--allow-flagged` | render refuses, as today |
| Line with no timed word | skipped and reported, as today |
| Marked word on a line that had to shrink | ratio kept (H-013), fills on its own time |
| Past line too tall to fit above the current one | it fades out at hand-over |
| A line too long even at the smallest size and 3 rows | render refuses and names the line, as today |
| A theme colour near key green | theme refused when built, error names the colour and the rule |
| Poppins file missing from the repo | render refuses and names the missing font file (never silent fallback) |
| Accent or white glyph missing from Poppins (emoji, Devanagari) | fallback font draws it, as today; the fill covers it the same way |

## 6. Acceptance Criteria

1. **Theme choice:** `render songs/khidki_s2 --theme pop-karaoke` and a plain
   `render songs/khidki_s2` both succeed from the same `words.json`, with no align call, and write
   to `render/pop-karaoke/` and `render/soft-romantic/`. Neither overwrites the other. Each
   `report.md` names its theme. `make --theme pop-karaoke` works the same way. An unknown name
   fails with the list of valid names.
2. **Soft Romantic untouched:** the default render of `khidki_s2` gives frames pixel-identical to
   `dev`'s renderer at every 30th frame.
3. **Fill timing (unit test):** for synthetic words, fill progress is 0 on the frame before
   `start − lead`, 1 on the frame of `end − lead`, and linear between. A flagged word's
   progress is 0 in every frame.
4. **Line states (unit test):** at most two lines are visible in any frame; a line is at rest
   before its first word's fill starts; hand-over and clear follow §4.3 on synthetic timings,
   including back to back lines, an instrumental gap and a first word at 0:00.
5. **Render checks pass:** Pop Karaoke's fill-sync and safe-zone checks, plus all existing
   output checks, pass on `khidki_s2` and on `khidki_s2_em` (marked words).
6. **Emphasis:** in Pop Karaoke, a marked word's box is exactly its text measured at
   `emphasis_scale` × its line's size; words in a row share a baseline and no boxes overlap
   (spec 06 AC5, re-run for this theme).
7. **Text:** every drawn string equals its `words.json` text in both themes (existing
   assertion, enforced for the new theme too).
8. **Key green:** a theme with any colour at hue 120 (±15°) and saturation above 50% is refused;
   both shipped themes are accepted.
9. **Speed:** Pop Karaoke renders `khidki_s2` in at most twice Soft Romantic's time on this
   laptop.
10. **Look:** the owner approves the Pop Karaoke look in
    `songs/khidki_s2_em/render/pop-karaoke/preview.mp4`; any change asked for is made as a
    `theme.py` value, not new behaviour, unless the owner asks for new behaviour.
11. The gate passes (unit tests + alpha proof).

## 7. Choices made for the owner (object to any before `/plan`)

- **Two lines on screen** (current plus dimmed past line), as in Apple Music, rather than one
  line at a time. One-at-a-time is simpler, but "past line dims" in H-011 needs the past line
  visible.
- **Hot pink accent** on white. Yellow `#FFD60A` or cyan `#00E5FF` is a one-value change.
- **Output folders per theme** (`render/<theme>/`), including Soft Romantic, so the eight planned
  themes sit side by side. Paths in docs that say `render/overlay.mov` move to
  `render/soft-romantic/overlay.mov`.
- **Poppins bundled in the repo** (about 150 KB, OFL allows it), rather than a Windows font or a
  manual install, so renders are the same on any machine.
