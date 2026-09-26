# Development Plan: Kinetic Lyric Engine (V1)

Source of truth for WHAT and WHY: `docs/project_context.md`. This file orders the work.
Steps run in order. Each gets a spec in `docs/specs/NN_<slug>.md` before any code.

## Status board

| #  | Step                                   | Branch                          | Status      |
|----|----------------------------------------|---------------------------------|-------------|
| 01 | Alpha overlay proof in CapCut          | `feature/alpha-overlay-proof`   | Done ([PR #1](https://github.com/Hacke2367/subtitle_engine/pull/1)) |
| 02 | Word alignment → `words.json`          | `feature/word-alignment`        | Done ([PR #2](https://github.com/Hacke2367/subtitle_engine/pull/2)) |
| 03 | Soft Romantic renderer                 | `feature/soft-romantic-render`  | Done ([PR #3](https://github.com/Hacke2367/subtitle_engine/pull/3), via #2) |
| 04 | Line anchors (`.lrc`) for alignment    | `feature/lrc-anchors`           | Deferred (optional, D-014) |
| 05 | Workflow: `clip` + `make` commands     | `feature/workflow-clip-make`    | Done ([PR #4](https://github.com/Hacke2367/subtitle_engine/pull/4), via #3 → #2) |
| 06 | Emphasis words (`*word*`)              | `feature/emphasis-markers`      | Build       |
| 07 | Pop Karaoke theme (V1.1)               | `feature/pop-karaoke-theme`     | Not started |

## 01 — Alpha overlay proof in CapCut

**Delivers:** a 5-second, 1080×1920 test overlay with a transparent background (a few words of
static and moving text), plus the same clip on a solid green background as an mp4.
**Needs:** H-003 (decided: both desktop and mobile). ffmpeg (8.0.1 already on PATH).
**Done when:** the owner imports the alpha `.mov` into CapCut desktop and the background shows
through the transparent areas, and the green mp4 keys out cleanly with Chroma Key in CapCut
mobile. Both outputs are primary (H-003).
**Why first:** if CapCut does not honour the alpha channel, the output plan changes before any
animation work is sunk into it.

## 02 — Word alignment → `words.json`

**Delivers:** `songs/<song>/` audio + `lyrics.txt` → `words.json` with a start/end time per word,
via an alignment API. Words the aligner could not place are marked as flagged, never estimated.
**Needs:** H-004 (decided: try ElevenLabs API and a local pipeline, keep the better). Step 01
done. An ElevenLabs API key in `.env`. The test song's audio + lyrics from the owner.
**Done when:** on one real Hinglish song, the owner spot-checks `words.json` against the audio;
every word's text matches `lyrics.txt` exactly; any unaligned word is listed in the run report.
**Red lines touched:** both.

## 03 — Soft Romantic renderer

**Delivers:** `words.json` → full-song alpha overlay (+ green mp4 fallback) in the Soft Romantic
theme: 9:16 layout with auto-wrap / max words per line, gentle reveal, glow on the current word,
owner-marked emphasis, font fallback for missing glyphs.
**Needs:** step 02 done. Look decided in the step's spec.
**Done when:** the owner plays the overlay over the song in CapCut and every word lights up as it
is sung, with no drift across the song. Editing `words.json` by hand and re-rendering works with
no alignment API call.
**Red lines touched:** never alter the lyrics text.

## 04 — Line anchors (`.lrc`) for alignment

**Delivers:** optional owner-supplied line timings (`.lrc` or tapped) that constrain word
alignment to within each line.
**Needs:** step 02 done; worth doing once real songs show where unanchored alignment drifts.
**Done when:** on a song where step 02 drifted, anchored alignment flags fewer words.

## Open technical choices (decide in each step's spec, not here)

- Alpha codec inside `.mov` that CapCut accepts (step 01 tests this).
- Alignment provider (step 02; ElevenLabs forced alignment is the default candidate).
- Rendering approach (step 03; the blueprint suggests MoviePy, not locked).
- ~~Emphasis marker syntax in `lyrics.txt`~~: `*word*` (H-009), built in step 06.

## 05 — Workflow: `clip` + `make` commands

**Delivers:** `clip` cuts a portion of an aligned full song into a new song folder: the audio cut
at line boundaries, plus exactly the lyric lines sung in it, verbatim. `make` aligns a song folder
if needed and renders it in one command.
**Needs:** steps 02 and 03 (stacked branch, D-014).
**Done when:** a short goes from full song + time range to overlay with two commands, tested on a
second portion of the test song. A different song is pending the owner.

## 06 — Emphasis words (`*word*`)

**Delivers:** the owner marks hook words as `*word*` in `lyrics.txt`. The reader strips the
asterisks, alignment never sees them, and Soft Romantic gives marked words one emphasis move.
`lyrics.txt` is the only place emphasis lives, so moving markers needs no re-align. The asterisks
are never drawn (H-009). Spec: `docs/specs/06_emphasis_markers.md`.
**Needs:** H-009 (decided). Research notes: `docs/research/lyric_aesthetics.md` (sections 2, 3).
**Done when:** a marked song renders with the move on exactly the marked words, the on-screen
text equals `lyrics.txt` minus the asterisks, and an existing unmarked song renders unchanged.

## 07 — Pop Karaoke theme (V1.1)

**Delivers:** a second theme, Pop Karaoke: left-to-right fill on the sung word, active line
scales in slightly, past line dims; bold sans, white plus one accent. A way to pick the theme per
render. Emphasis words from step 06 get this theme's own move.
**Needs:** step 06 merged; H-011 (decided). Research notes: sections 3, 4, 6, 7.
**Done when:** the test song renders in both themes from the same `words.json`, every render
check passes, and the owner approves the Pop Karaoke look.
