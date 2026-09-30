# Spec: Background Layer + Romantic Light Looks
**Version:** 2.0.0 | **Component:** `background/` package, renderer (`render/`), `cli.py`
**Status:** v1 (the romantic room) was built and rejected on sight (H-032). v2 builds the three
romantic looks the owner finalized from moving samples: rain (H-034), fog (H-035) and milan
(H-036), described in `docs/backgrounds/romantic_lights.md`. The owner judges the engine's
finished shorts (AC11).
**Plan step:** 17 (`docs/development_plan.md`) · **Branch:** `feature/bg-romantic-room` · **Decisions:** H-022 to H-025, H-032 to H-036, D-018, D-028, D-033

## 1. Problem Statement

The engine makes only a transparent overlay; the owner adds a background in CapCut, and every
channel under a song uses the same stock images or footage (H-023). The channel's bet is that the
lyric styling itself is the content (H-022), so the owner wants engine-made backgrounds per song
type. The first one, a sunlit room, was rejected: the owner wants light that is felt, never
poking the eye, the whole screen used and real depth (H-032). Three looks were then made as
moving samples and approved. Nothing in the engine can draw them or write a finished short.

## 2. Objective

`render songs/<song> --bg rain` (or `fog`, `milan`) writes, next to the theme's usual outputs, an
upload-ready 9:16 short with audio: the look under the theme's lyrics, drawn by the engine as in
its approved sample and following the song's words. Without `--bg`, every output is identical to
today.

## 3. Scope & Constraints

**Will Do:**
- A background layer any theme's frames go on top of, chosen per render with
  `--bg LOOK[:MOOD]` on `render` and `make`. Looks `rain` (mood `evening`), `fog` (`moonlight`)
  and `milan` (`night`), each with its one mood as the default.
- Each look drawn as in its approved sample, with the sample's numbers (section 4.2).
- The finished short: `render/<theme>/final_<look>_<mood>.mp4` (e.g. `final_rain_evening.mp4`),
  1080×1920, 30 fps, H.264 yuv420p (BT.709), AAC audio from the song folder's audio, song length
  from t = 0, ready to upload to Shorts / Reels without CapCut.
- The looks follow the song: word times, where each word sits on screen, the marked words (4.3).
- Seeded variation: what varies per song comes from the folder name; each look's place does not.
- Report section for the background; render checks for the finished short and its legibility.
- Render time measured.

**Will NOT Do:**
- Other song types' looks (sad: H-037; the picks of H-038): later steps, each after its sample.
- Change `overlay.mov`, `overlay_green.mp4` or `preview.mp4`: they stay the theme's own layers
  for CapCut, with or without `--bg`.
- Read beats or `drops.txt`: these looks move slowly and follow the words (H-032's slow natural
  motion).
- Light the text or cast its shadow (v1's §4.4): the overlay goes over the look as it is.
- AI-generated or downloaded art: everything is drawn by code (the owner has no AI plan).
- A `--seed` to reroll, a fast preview mode.

**Hard Rules:**
- Red line 1: the looks read only aligned word times from `words.json`; an untimed word triggers
  nothing. They never move or estimate a word's time.
- Red line 2: the lyric pixels in the finished short are the overlay's pixels laid over the look
  by alpha compositing, with the overlay's alpha and colours unchanged. The text is never redrawn
  or recoloured.
- The looks never read what the words say, so any lyric of any length works (owner's constraint,
  H-024).
- The lyric area is fixed: x 60–960, y 380–1540 (the themes' safe zone). Behind the text the look
  stays calm and darker than the text (legibility rule, 4.5).
- No `--bg` → every output frame hash-identical to `dev`, and `report.md` has no Background
  section.
- Same song folder and `--bg` → the same background frames on every render.

## 4. Core Design

### 4.1 Components and data flow

- `background/` package: the look registry and song facts (`__init__`), the shared art tools and
  the finishing pass every look shares (`paint`), one module per look, and `compose` (the overlay
  over the look, the legibility log, the finished short's check).
- Song facts, read once per render: song length and frame count; each timed word's start, whether
  it is marked, and where it sits on screen (its box from the theme's render plan); the lyric
  block around every word's box; each shown line's first timed word; the seed (from the song
  folder's name).
- The render streams the theme's frames as today. With `--bg`, each frame is also laid over the
  look's frame for that time (the look is told where the text is on that frame), and the result
  goes to the finished short. The overlay outputs receive exactly the frames they receive without
  `--bg`.

### 4.2 The looks (what the viewer sees)

The full direction, palettes and the owner's words are in `docs/backgrounds/romantic_lights.md`.
- **rain, evening:** a soft overcast evening; a few soft clouds drift high up; mist on the
  horizon, a faint tree line far away and wet ground that mirrors the sky. Slow, colourless rain,
  each drop at its own depth (far: small and slow, landing near the horizon; near: bigger and
  softer, landing low), swaying a little in the wind. Where a drop lands a faint ripple spreads
  and a soft pastel colour rises out of the ground.
- **fog, moonlight:** silver-blue moonlight falls in rays through gaps in leaves from beyond the
  top left, brightest where it comes in and fading as it comes down; slow wisps of fog glow where
  a ray catches them and darken the air in shadow; the lower frame falls into darkness. The leaves
  sway, so the rays shift.
- **milan, night:** matte dots, clearly visible and giving no light of their own, drift on a
  smooth random wander over an almost black night with a faint plum haze and a light dark border.
  When two meet they linger a moment and light up, a soft warm light blooms and fades, and a faint
  memory of it stays.

### 4.3 How the looks follow the song

- **rain:** each timed word lands a bigger bloom (ripple and colour) on the ground under it; a
  marked word lands the biggest, in rose.
- **fog:** each timed word brightens the rays a little (a swell over 0.25 s, gone after 1.4 s;
  swells never add up); a marked word opens a new ray that stays.
- **milan:** from 2.6 s before a marked word, the two free dots nearest the meeting point drift
  together and meet as it is sung, just below the lyrics under that word; other meetings happen
  wherever dots meet.
- A word or mark with no aligned time triggers nothing.

### 4.4 Variation

Each look's place (rain's sky, clouds and ground; fog's leaves and fog) uses its approved sample's
fixed seeds: the same place in every video, the channel's recognisable look. What changes per song
uses the seed from the folder name (`zlib.crc32`): rain's drops, the places of fog's new rays,
milan's dots. Re-rendering a song keeps its background.

### 4.5 Legibility rule

Behind the text the look stays darker than the text: on every frame with lyrics (or the title
card) on screen, the contrast between the theme's `text_rgb` and the 99th-percentile background
luminance around the text (its ink box grown by 24 px, inside the lyric area) is at least 3:1
(WCAG AA for large text; the lyrics are 56–110 px). How the looks keep it: each calms a fixed
patch behind the lyric block; milan also dims its dots and their light behind the text on screen
that frame, at once where text appears and fading back over 0.8 s after it leaves.

### 4.6 Theme fit

The looks are made for Soft Romantic v1 and v2, Cinematic, Lofi Minimal and Lofi Typewriter. Any
other theme still renders with `--bg`; the report notes that the theme is outside the look's range.

### 4.7 Report

`report.md` gains a Background section only with `--bg`: look and mood (and the theme-fit note),
the seed and the folder name it comes from, one line on what the look did, the counts of words,
marked words and lines, any marked word skipped as untimed, background time per frame, and the
legibility result.

## 5. Edge Cases & Error Handling

| Situation | Behaviour |
|---|---|
| No `--bg` | Nothing changes; no Background section |
| Unknown look or mood (`--bg room`) | CLI refuses, listing the built choices |
| Theme outside the looks' range | Renders; report note |
| No marked words (`khidki_s2`) | Words still react; milan's meetings are all chance ones |
| Marked word untimed (with `--allow-flagged`) | Nothing for it; report note |
| Marks close together | rain's blooms each fade on their own; fog's swells never exceed one; milan gives each mark its own pair of dots |
| Title card present | Part of the overlay: laid over as it is, and the legibility rule covers it |
| Legibility rule fails on some frame | Render check failure naming the first frame and its contrast; outputs kept for review, like every check |
| ffmpeg fails | All partial outputs of this render, the finished short included, are removed (as today) |
| Old `final_*.mp4` from another look | Left in place; a render replaces only its own file |
| `--codec` | Affects only `overlay.mov`, as today |

## 6. Acceptance Criteria

1. `render songs/khidki_s2_em --theme soft-romantic-v2 --bg rain` (and `fog`, `milan`) writes the
   usual three outputs plus `final_<look>_<mood>.mp4`; ffprobe: H.264 yuv420p, 1080×1920, 30 fps,
   one AAC audio stream, duration equal to the song ± 1 frame; every render check passes.
2. Without `--bg`, all eight themes' output frames are hash-identical to `dev` on `khidki_s2_em`,
   and no report has a Background section.
3. With `--bg`, the frames of `overlay.mov`, `overlay_green.mp4` and `preview.mp4` are
   hash-identical to the same render without `--bg`.
4. Compose (unit): where the overlay is transparent the finished frame is the look's frame; where
   it is opaque, the overlay's pixels; the finished frame is opaque.
5. Song reactions (unit): rain: a word changes the ground under it and nothing far from it; fog:
   a word brightens the rays; milan: a marked word gives one meeting within a frame of its start,
   under the word below the lyrics, and dots dim behind the text.
6. Song facts (unit): only timed words count; marks, line starts, the lyric block and untimed
   marks are as in `words.json` and the render plan.
7. Legibility (unit + render): the 3:1 rule holds on every frame with text of the AC1 renders; a
   deliberately bright background fails the check.
8. Seed (unit): two renders of one folder give identical background frames.
9. CLI: an unknown look or mood is refused with the choices; `make --bg rain` passes the choice
   through.
10. Render time per look is in the report and the PR. Target: a 60 s short renders in at most
    10 minutes on this laptop.
11. The owner approves the finished shorts on `khidki_s2_em`.
12. Gate passes.

## 6b. Added in v2.1: khaali and the backdrop (D-035)

- Look `khaali` (mood `night`, sad: `docs/backgrounds/sad_khaali_jagah.md`). AC: renders with every
  check passing; lowest contrast 4.4:1 (14 s), 3.2:1 (30 s clip).
- `backdrop`: only the background, no lyrics drawn (`backdrop songs/<song> --bg LOOK`, with the
  song's words and audio; or `--seconds N`, no song, payoff at 85%). AC: the file has the asked
  length, audio only with a song, no other output of the render dir is written or touched;
  a backdrop without a look is refused.

## 7. Dependencies

numpy, PIL and scipy, already in the venv and in `requirements.txt` since v1. Nothing new.
