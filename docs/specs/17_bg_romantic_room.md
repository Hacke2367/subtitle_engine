# Spec: Background Layer + Romantic Room
**Version:** 1.0.0 | **Component:** new `background/` package, renderer (`render/`), `cli.py`
**Status:** Direction approved up front (H-023 to H-025, `docs/backgrounds/romantic_room.md`);
spec, plan and build in one run (H-020 flow). The owner judges the finished look (AC11).
**Plan step:** 17 (`docs/development_plan.md`) · **Branch:** `feature/bg-romantic-room` · **Decisions:** H-022 to H-025, H-027 note, D-018

## 1. Problem Statement

The engine makes only a transparent overlay; the owner adds a background in CapCut, and every
channel under a song uses the same stock images or footage (H-023). The channel's bet is that the
lyric styling itself is the content (H-022), and the owner approved an engine-made world per song
type, starting with a sunlit room for romantic songs (H-024, H-025). Nothing in the engine can
draw a background, light the lyrics to match it, or write a finished short with audio.

## 2. Objective

`render songs/<song> --bg room` writes, next to the theme's usual outputs, an upload-ready 9:16
short with audio: the romantic room's default mood (afternoon to dusk) under the theme's lyrics,
the lyrics lit by the room's light and casting a faint shadow on its wall. Without `--bg`, every
output is identical to today.

## 3. Scope & Constraints

**Will Do:**
- A background layer any theme's frames go on top of, chosen per render with
  `--bg WORLD[:MOOD]` on `render` and `make`. First world `room`; its one built mood `dusk`
  (afternoon to dusk, the default, so `--bg room` = `--bg room:dusk`).
- The room's `dusk` mood as described in `docs/backgrounds/romantic_room.md`, drawn by the engine
  (section 4).
- The finished short: `render/<theme>/final_<world>_<mood>.mp4` (e.g. `final_room_dusk.mp4`),
  1080×1920, 30 fps, H.264 yuv420p (BT.709), AAC audio from the song folder's audio, song length
  from t = 0, ready to upload to Shorts / Reels without CapCut.
- The lyrics (and the title card, when there is one) catch the room's light and cast a shadow on
  its wall, in the finished short only (section 4.4).
- Seeded variation: a few props change per song folder; the room itself never does.
- Report section for the background; render checks for the finished short and its legibility.
- Render time measured on 14 s, 30 s and full-song renders.

**Will NOT Do:**
- The room's other five moods (morning, rain, moonlit night, misty winter, festival): step 23.
- Other worlds (truck, baraat, lamp, forge, train): steps 18–22.
- Change `overlay.mov`, `overlay_green.mp4` or `preview.mp4`: they stay the theme's own layers
  for CapCut, with or without `--bg`.
- Read beats or `drops.txt` for this mood: the room moves as slowly as breathing (principle 4),
  so a quiet room never needs `beats.json`.
- AI-generated or downloaded art in this step: every prop is drawn by code (section 4.2). AI
  stills stay the fallback if the owner finds the drawn props weak.
- A `--seed` to reroll the props, picking props by hand, a fast preview mode.
- Faces, couples, rose petals, bokeh, starry skies, sunset silhouettes (the doc's avoid list).

**Hard Rules:**
- Red line 1: the room reads only word times from `words.json` (aligned times only; an untimed
  word triggers nothing). It never moves or estimates a word's time.
- Red line 2: the lyric pixels in the finished short are the overlay's pixels, recoloured by the
  light and nothing else: same ink, same place, same shape. The text is never redrawn.
- The room never reads what the words say, so any lyric of any length works (owner's
  constraint, H-024).
- The lyric area is fixed for the world: x 60–960, y 380–1540 (the themes' safe zone). Props sit
  outside it; behind the text the wall stays calm and darker than the text (legibility rule, 4.5).
- No `--bg` → every output frame hash-identical to `dev`, and `report.md` has no Background
  section.
- Same song folder and `--bg` → the same background frames on every render.

## 4. Core Design

### 4.1 Components and data flow

- `background/` package: the world registry (`room` → its moods), the shared parts every world
  uses (song facts, the time arc, grain, the compose step, the finished-video check), and
  `room.py` (the room itself). Split further only past ~300 lines per module.
- Song facts, read once per render: song length, each word's aligned start, the `*marked*` words
  (from `lyrics.txt`, as the themes read them), the last shown line's first timed word, and the
  seed (from the song folder's name).
- The render streams the theme's frames as today. With `--bg`, each frame is also composed onto
  that frame's background and lit (4.4), and the result goes to the finished short. The overlay
  outputs receive exactly the frames they receive without `--bg`.

### 4.2 The room, `dusk` mood (what the viewer sees)

Everything is drawn by code, and the room's story is told mostly through light and shadow on one
wall, which code does well and which keeps the hand-made, un-downloaded feel:

- **The wall** fills the frame: warm plaster (a static hand-made texture, the shared grain; no
  per-frame noise, which bloats the file and smears on a platform re-encode).
- **The light:** afternoon sun from an off-frame window at the upper left. It falls on the wall
  as a patch shaped by a jaali; the patch is crisp near the top and soft (no pattern edges)
  behind the lyric area. Dust motes drift in the beam.
- **Shadows at the edges:** money-plant leaves swaying slowly on one side; a curtain's shadow at
  the window edge.
- **Lower corners (y 1540–1920):** a chair back with a dupatta over it in one corner; a small
  table lamp in the other; a prop on a ledge. These sit where platform UI may cover them, so
  nothing the story needs depends on seeing their full shape; the lamp's light on the wall carries
  the ending.
- **Time arc,** stretched to the song: gold light at the start, turning rose, reaching dusk blue at
  the last shown line's first word; the sun patch lowers and lengthens as it goes. At that word the
  lamp comes on and its warm glow spreads up the wall (the thumbnail frame). After it, dusk and the
  lamp hold to the end of the audio.
- **Marked words:** at each timed `*marked*` word's start, a gust: the curtain's shadow lifts and
  the light blooms for about 1.5 s. A gust that starts during another restarts it; they never add
  up.

### 4.3 Seeded variation

The seed comes from the song folder's name, so re-rendering a song keeps its room, and two clips
of one song get different details. It picks: which side the money plant stands, the curtain's
print (seen in its shadow), the prop on the ledge (chai glass with steam, a radio, a folded
letter) and the dupatta's colour. The jaali, the window and the wall stay fixed: the channel's
recognisable place.

### 4.4 How the lyrics catch the light

Applied to each overlay frame in the finished short only:

- **Shadow on the wall:** the overlay's ink casts a soft, low-opacity shadow onto the wall, in the
  wall's own darker colour (never black), offset away from the window. As the sun lowers the
  shadow lengthens and fades with the sun; once the lamp comes on, the lamp casts it instead,
  falling away from the lamp.
- **Light on the text:** the text's colours shift toward the current light colour (gold, rose,
  dusk blue, then the lamp's warm) by a bounded amount, keeping at least 90% of the theme's
  brightness. The theme's own glow and shadow stay as they are in the overlay.
- The overlay's alpha is used unchanged (Hard Rule, red line 2).

### 4.5 Legibility rule

Behind the text the background stays darker than the text: on every frame with lyrics (or the
title card) on screen, the contrast between the lit text colour (from the theme's `text_rgb`) and
the 99th-percentile background luminance around the text (its ink box grown by 24 px, inside the
lyric area) is at least 3:1 (WCAG AA for large text; the lyrics are 56–110 px). Gusts, dust and
the lamp's light count. Measured around the text, not over the whole lyric area, so the lamp can
warm the lower wall at the end while no lyric sits there. The effect: a dim room with one warm
shaft of light, the lyrics the brightest thing in it.

### 4.6 Theme fit

The room is made for Soft Romantic v1 and v2, Cinematic, Lofi Minimal and Lofi Typewriter. Any
other theme still renders with `--bg room`; the report notes that the theme is outside the room's
range.

### 4.7 Report

`report.md` gains a Background section only with `--bg`: world and mood, seed and the props it
picked, the lamp's time, each gust's time (and any marked word skipped as untimed), the theme-fit
note, the finished short's path and size, background time per frame, and the legibility result.

## 5. Edge Cases & Error Handling

| Situation | Behaviour |
|---|---|
| No `--bg` | Nothing changes; no Background section |
| Unknown world or mood | CLI refuses, listing the built choices |
| A designed mood not built yet (`room:rain`) | Refuses: "not built yet (plan step 23)" |
| Theme outside the room's range | Renders; report note |
| No marked words (`khidki_s2`) | No gusts |
| Marked word untimed (with `--allow-flagged`) | No gust for it; report note |
| Marks closer than a gust's length | The gust restarts; strength never exceeds one gust |
| Only one shown line, or it starts in the first seconds | The arc compresses to that start; the lamp still comes on at it |
| Audio continues after the last line (outro) | Dusk and the lamp hold to the end |
| Title card present | Lit and shadowed like the lyrics |
| Legibility rule fails on some frame | Render check failure naming the first frame and its contrast; outputs kept for review, like every check |
| ffmpeg fails | All partial outputs of this render, the finished short included, are removed (as today) |
| Old `final_*.mp4` from another mood, or from a render before a timing fix | Left in place; a render replaces only its own `final_<world>_<mood>.mp4` and the report names it |
| `--codec` | Affects only `overlay.mov`, as today |

## 6. Acceptance Criteria

1. `render songs/khidki_s2_em --theme soft-romantic-v2 --bg room` writes the usual three outputs
   plus `final_room_dusk.mp4`; ffprobe: H.264 yuv420p, 1080×1920, 30 fps, one AAC audio stream,
   duration equal to the song ± 1 frame; every render check passes. Same on `khidki_s2`, a 30 s
   clip of `khidki_full`, and `khidki_full`.
2. Without `--bg`, all eight themes' output frames are hash-identical to `dev` on `khidki_s2_em`,
   and no report has a Background section.
3. With `--bg room`, the frames of `overlay.mov`, `overlay_green.mp4` and `preview.mp4` are
   hash-identical to the same render without `--bg`.
4. Compose (unit): where the overlay is fully transparent and no shadow falls, the finished frame
   equals the background; the overlay's alpha footprint is unchanged; the text colour moves by no
   more than the tint limit and keeps ≥ 90% of the theme's brightness.
5. Arc (unit): gold at t = 0, rose midway, dusk blue at the last shown line's first word; the lamp
   off before that word and fully on after its ramp; the same keyframes fall at the same fractions
   for a 14 s and a 172 s song.
6. Gusts (unit): one per timed marked word, starting at its `words.json` start; none without marks;
   overlapping marks never exceed one gust's strength.
7. Legibility (unit + render): the 3:1 rule holds on every frame with text of the AC1 renders; a
   deliberately bright background fails the check.
8. Seed (unit): two renders of one folder give identical background frames; the two test folder
   names `khidki_s2` and `khidki_s2_em` differ in at least one pick; the report names the seed and
   the picks.
9. CLI: an unknown world or mood is refused with the choices; `room:rain` is refused as not built
   yet; `make --bg room` passes the choice through.
10. Render time for the 14 s, 30 s and full-song renders is in the report and the PR. Target: a
    60 s short renders with the room in at most 10 minutes on this laptop; if the drawing misses
    it, the plan's fallback (research §2, `moderngl`) is taken before shipping.
11. The owner approves the look on `khidki_s2_em` and `khidki_full`.
12. Gate passes.

## 7. Dependencies

Nothing new to install for the first cut: numpy, PIL and scipy are already in the venv.
`moderngl` (MIT, tested on this laptop's Iris Xe, research §2) only if render time or the look
needs it; adding it goes in `requirements.txt` with a D- decision.
