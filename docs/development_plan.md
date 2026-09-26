# Development Plan: Kinetic Lyric Engine (V1)

Source of truth for WHAT and WHY: `docs/project_context.md`. This file orders the work.
Steps run in order. Each gets a spec in `docs/specs/NN_<slug>.md` before any code.

## Status board

| #  | Step                                   | Branch                          | Status      |
|----|----------------------------------------|---------------------------------|-------------|
| 01 | Alpha overlay proof in CapCut          | `feature/alpha-overlay-proof`   | Done ([PR #1](https://github.com/Hacke2367/subtitle_engine/pull/1)) |
| 02 | Word alignment → `words.json`          | `feature/word-alignment`        | Review ([PR #2](https://github.com/Hacke2367/subtitle_engine/pull/2)) |
| 03 | Soft Romantic renderer                 | `feature/soft-romantic-render`  | Review      |
| 04 | Line anchors (`.lrc`) for alignment    | `feature/lrc-anchors`           | Not started |

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
- Emphasis marker syntax in `lyrics.txt` (step 03).
