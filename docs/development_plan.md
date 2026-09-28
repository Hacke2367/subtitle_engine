# Development Plan: Kinetic Lyric Engine (V1, V1.1 styling, backgrounds)

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
| 06 | Emphasis words (`*word*`)              | `feature/emphasis-markers`      | Done ([PR #5](https://github.com/Hacke2367/subtitle_engine/pull/5)) |
| 07 | Pop Karaoke theme (V1.1)               | `feature/pop-karaoke-theme`     | Done ([PR #6](https://github.com/Hacke2367/subtitle_engine/pull/6)) |
| 08 | Soft Romantic v2                       | `feature/soft-romantic-v2`      | Done ([PR #7](https://github.com/Hacke2367/subtitle_engine/pull/7)) |
| 09 | Lofi Minimal theme                     | `feature/lofi-minimal-theme`    | Done ([PR #8](https://github.com/Hacke2367/subtitle_engine/pull/8)) |
| 10 | Cinematic theme                        | `feature/cinematic-theme`       | Done ([PR #9](https://github.com/Hacke2367/subtitle_engine/pull/9)) |
| 11 | Beat detection                         | `feature/beat-detection`        | Done ([PR #10](https://github.com/Hacke2367/subtitle_engine/pull/10)) |
| 12 | Beat Pop theme                         | `feature/beat-pop-theme`        | Done ([PR #11](https://github.com/Hacke2367/subtitle_engine/pull/11)) |
| 13 | Phonk Neon theme                       | `feature/phonk-neon-theme`      | Done ([PR #12](https://github.com/Hacke2367/subtitle_engine/pull/12)) |
| 14 | Devanagari shaping                     | `feature/devanagari-shaping`    | Deferred (only when a song needs it) |
| 15 | Title card ("Song \| Singer")          | `feature/title-card`            | Done ([PR #13](https://github.com/Hacke2367/subtitle_engine/pull/13)) |
| 16 | Line breaks at sung pauses             | `feature/pause-line-breaks`     | Optional (only if the owner asks) |
| 17 | Background layer + romantic room       | `feature/bg-romantic-room`      | Review (owner judges the look) |
| 18 | Hip-hop truck background               | `feature/bg-hiphop-truck`       | Planned (H-026) |
| 19 | Party baraat background                | `feature/bg-party-baraat`       | Planned (H-027) |
| 20 | Sufi lamp background                   | `feature/bg-sufi-lamp`          | Planned (H-028) |
| 21 | Motivational forge background          | `feature/bg-motivational-forge` | Planned (H-030) |
| 22 | Journey train background               | `feature/bg-journey-train`      | Planned (H-031) |
| 23 | Other moods of every background        | `feature/bg-moods`              | Planned (after each default is approved) |

Steps 08–14: the owner builds every researched style (H-012), in this order by default (D-017).
The owner can reorder any step before it starts.

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
- Font files for the new themes (Poppins, Anton, Tiro Devanagari Hindi, Cormorant, ...; all SIL
  OFL): bundle them with their licence in the repo, or require a local install. First needed in
  step 07.
- libass through ffmpeg as an internal render route for karaoke-family themes (research §10 B).
  The output stays `.mov` / `.mp4`; `.ass` as an output remains out of scope.
- Beat-detection library (step 11) and Devanagari shaping route (step 14).

## 05 — Workflow: `clip` + `make` commands

**Delivers:** `clip` cuts a portion of an aligned full song into a new song folder: the audio cut
at line boundaries, plus exactly the lyric lines sung in it, verbatim. `make` aligns a song folder
if needed and renders it in one command.
**Needs:** steps 02 and 03 (stacked branch, D-014).
**Done when:** a short goes from full song + time range to overlay with two commands, tested on a
second portion of the test song. A different song is pending the owner.

## 06 — Emphasis words (`*word*`)

**Delivers:** the owner marks hook words as `*word*` in `lyrics.txt`. The reader strips the
asterisks, alignment never sees them, and marked words are drawn 1.5x-2x their line's size (H-013).
`lyrics.txt` is the only place emphasis lives, so moving markers needs no re-align. The asterisks
are never drawn (H-009). Spec: `docs/specs/06_emphasis_markers.md`.
**Needs:** H-009 (decided). Research notes: `docs/research/lyric_aesthetics.md` (sections 2, 3).
**Done when:** a marked song renders with the move on exactly the marked words, the on-screen
text equals `lyrics.txt` minus the asterisks, and an existing unmarked song renders unchanged.

## 07 — Pop Karaoke theme (V1.1)

**Delivers:** a second theme, Pop Karaoke: left-to-right fill on the sung word, active line
scales in slightly, past line dims; bold sans, white plus one accent. A way to pick the theme per
render. Marked `*word*`s keep H-013's size rule (1.5x-2x their line) in this theme's look.
**Needs:** step 06 merged; H-011 (decided). Research notes: sections 3, 4, 6, 7.
**Done when:** the test song renders in both themes from the same `words.json`, every render
check passes, and the owner approves the Pop Karaoke look.

## Styling rules for every theme step (07–13)

Source: `docs/research/lyric_aesthetics.md`. Each theme's spec covers these, and its "Done when"
includes them.

- Timing and restraint over motion: text lands with the voice; ease-out in, ease-in out;
  overshoot at most 10%; only owner-marked `*word*`s are emphasised, at 1.5x-2x their line (H-013).
- At most two font families, one palette and one motion set per theme; no hue-120 green,
  because the green-screen output keys it out (§6, §7).
- A legibility layer that survives bright footage: shadow, stroke or soft scrim (§8).
- Text stays inside the safe zone x 60–960, y 380–1540 at 1080×1920 (§8).
- Red lines hold: spelling and casing exactly as in `lyrics.txt`, so no auto-lowercase or
  auto-uppercase and no caps-only fonts unless the owner writes caps; decoration never invents
  or moves a word timing.
- Render stays within ~10 min per song: sprites built once, animated parameters quantised and
  cached, only pastes per frame (§4).

## 08 — Soft Romantic v2

**Delivers:** an upgrade of the owner's everyday theme (research §3, shortlist 1). The past line
dims and blurs out, the active-word glow lasts exactly the word's aligned duration, and long held
notes get a slow glow "breath". Step 06's emphasis move carries over. Whether v2 replaces v1 or
sits beside it is decided in its spec.
**Needs:** step 07 merged (theme selection, scale and dim primitives). Look check: H-010 kept
Soft Romantic with no ghosting of upcoming words, so the research's waiting next line ships only
if the owner re-approves it in this spec.
**Done when:** the test song renders in v2, every render check passes, and the owner prefers it
over v1.

## 09 — Lofi Minimal theme

**Delivers:** the research's Minimal Lowercase look for lofi, sad and black-screen status edits
(§3, shortlist 3; blueprint "Lofi / Vaporwave"). Light sans with wide tracking, slow fade and
rise, long holds, sung / current / upcoming colour states, and an optional letter-by-letter
typewriter for Latin text. The lowercase look comes from the owner writing the lyrics in
lowercase, never from the engine (red line 2). Typewriter letters reveal inside their word's
aligned span and get no timestamps of their own (red line 1). Film grain stays in the footage.
**Needs:** step 07 merged.
**Done when:** the test song renders in this theme, every render check passes, and the owner
approves the look.

## 10 — Cinematic theme

**Delivers:** the research's Cinematic Ivory for ghazals and slow ballads (§3, shortlist 4;
blueprint "Minimalist Cinematic"). Serif type (Tiro Devanagari Hindi or Cormorant Garamond
Italic), ivory and antique gold, blur-in reveal, very slow motion, no glow.
**Needs:** step 08 (sprite blur cache).
**Done when:** the test song renders in this theme, every render check passes, and the owner
approves the look.

## 11 — Beat detection

**Delivers:** beat and onset times per song, computed once from the audio and cached like the
alignment, so re-renders stay free. Beats drive decoration only (pulse, pop, shake, flash); they
never create or move a word timing (red line 1).
**Needs:** a library choice in its spec (research §10 F: `librosa` pulls numba, `aubio` is
lighter) within the CPU budget. D-001 makes `words.json` the only contract between stages, so the
spec decides whether beats live inside it or beside it, which would amend D-001.
**Done when:** on the test song, detected beats match the kick and snare by ear in a click-track
preview, and a second render reuses the cached beats.

## 12 — Beat Pop theme

**Delivers:** a hype theme for Punjabi, party and rap songs (§3, shortlist 5). Heavy condensed
sans (Anton, with Anek Devanagari as companion), white plus mustard or red, 4–6 px black stroke,
`easeOutBack` word pops, a highlight pill under the sung word, and an optional shake on drops.
Anton keeps real lowercase; caps-only fonts such as Bebas Neue would change on-screen casing.
**Needs:** step 11.
**Done when:** word pops and drop accents land on the beat by ear, every render check passes, and
the owner approves the look.

## 13 — Phonk Neon theme

**Delivers:** the blueprint's "Phonk / Aggressive" plus the research's Neon (§3, shortlist 6).
Saturated text with a same-hue glow that pulses on beats, and white flash, shake or RGB split on
drops, in a blackletter or wide bold display face.
**Needs:** step 11 (and step 12's beat-driven motion, reused).
**Done when:** glow pulses and drop hits land on the beat by ear, every render check passes, and
the owner approves the look.

## 14 — Devanagari shaping (deferred)

**Delivers:** correct Devanagari conjuncts and matras, for Devanagari lyrics or a Devanagari hero
word in a display face (Yatra One, Rozha One). This venv's Pillow has no raqm, so it draws
Devanagari wrong today; Latin Hinglish is unaffected. Route in its spec: libass through ffmpeg
(verified on this machine) or `uharfbuzz` + `freetype-py` (research §10).
**Needs:** a song that actually needs Devanagari.
**Done when:** हिन्दी, क्ष and दृष्टि render with correct conjuncts and matra order, matching a
browser rendering of the same text.

## 15 — Title card

**Delivers:** a "Song | Singer" card at the start of a short (research §9), usable with every
theme. Picked by the owner after step 13 (2026-09-28).
**Needs:** nothing new; the spec settles what the card shows, where the text comes from, and how
long it stays.
**Done when:** the card renders on the test songs with every theme, every render check passes,
and the owner approves the look.

## 16 — Line breaks at sung pauses

**Delivers:** a long lyric line that wraps into rows breaks where the singer pauses, not only
where the width runs out (research §2, UIST 2023 guidelines). Opt-in per theme, so a theme that
does not opt in stays pixel-identical.
**Needs:** nothing new: `words.json` already has each word's start and end. The spec settles
what counts as a pause and which themes opt in.
**Done when:** on the test songs, rows break at the longest in-line gaps within the width limit,
every render check passes, and the owner approves the look.

## Backgrounds (steps 17–23)

The owner's north star (H-022): the lyric styling itself is the content. Each background's
direction is owner-approved in `docs/backgrounds/<world>.md`; its spec settles the details and the
owner judges the look. The owner wants every approved background built, starting the session
after 2026-09-29, in step order. Tools and prices: `docs/research/background_tools.md`; rejected
prototypes and why: H-024.

Rules for every background step:
- The engine renders a finished short: background, the theme's overlay and the audio (scope
  change, H-023). With no background chosen, every existing output stays byte-identical.
- A background reads only the song's length, each word's time, the beats, `drops.txt` and the
  `*marked*` words, never what the words mean, so any lyric works (owner's constraint).
- The lyric area sits in the same place in every mood, inside the theme's lyric block; nothing
  bright crosses the lyrics.
- One art style across all backgrounds: hand-made, warm light, the same grain (H-027 note).
- Default mood first; the other moods follow in step 23 once the owner approves the default.
- Red lines hold: backgrounds never move a word's time or change its text.

## 17 — Background layer + romantic room

**Delivers:** a background layer under any theme, chosen per song (a world and a mood; names
decided in the spec), with seeded variation per video, and a finished-video output with audio.
First world: the romantic room's default mood (afternoon to dusk),
`docs/backgrounds/romantic_room.md`.
**Needs:** nothing new to install for a first cut (numpy, PIL, scipy); `moderngl` only if the
look or render time needs it (research section 2). The spec settles how the lyrics catch the
room's light and cast a shadow without changing the text.
**Done when:** the room renders under Soft Romantic v2 on the Khidki songs, the finished video
plays with audio, outputs without a background are byte-identical to `dev`, render time is
measured, and the owner approves the look.

## 18 — Hip-hop truck background

**Delivers:** the truck world's default mood (night highway), `docs/backgrounds/hiphop_truck.md`.
**Needs:** step 17; a hip-hop test song in `songs/` (owner); painted truck art (AI stills made
once, or drawn: the spec decides).
**Done when:** the truck bounces on the same beats as Beat Pop's bump, punchlines flash on marked
words, drops bring smoke, every check passes, and the owner approves the look.

## 19 — Party baraat background

**Delivers:** the baraat world's default mood (baraat night), `docs/backgrounds/party_baraat.md`.
**Needs:** step 17; a party test song in `songs/` (owner).
**Done when:** lamps bounce on the beats, rockets on marked words and anaar fountains on drops
stay clear of the lyrics, every check passes, and the owner approves the look.

## 20 — Sufi lamp background

**Delivers:** the lamp world's default mood (dargah night), `docs/backgrounds/sufi_chiraag.md`.
**Needs:** step 17; a Sufi test song in `songs/` (owner).
**Done when:** the moth closes on the flame line by line and enters it on the last line, the
flame reacts to beats and marked words, every check passes, and the owner approves the look.

## 21 — Motivational forge background

**Delivers:** the forge world's default mood (forge at night),
`docs/backgrounds/motivational_forge.md`.
**Needs:** step 17; a motivational test song in `songs/` (owner).
**Done when:** strikes land on the beats, the iron is finished on the last line, sparks stay
below the lyrics, every check passes, and the owner approves the look.

## 22 — Journey train background

**Delivers:** the train world's default mood (Punjab fields), `docs/backgrounds/journey_train.md`.
**Needs:** step 17; a journey test song in `songs/` (owner).
**Done when:** a pole passes the door on every beat, the tunnel comes on a drop, the journey
arrives on the last line, every check passes, and the owner approves the look.

## 23 — Other moods of every background

**Delivers:** the remaining moods listed in each `docs/backgrounds/<world>.md`, one at a time,
after the owner approves that world's default mood.
**Done when:** each mood renders on a fitting song and the owner approves it.

## Later candidates (not scheduled; the owner picks)

- Backgrounds for mother and family songs, patriotic songs (before 26 January 2027), and old
  classics as a room mood (H-029).
