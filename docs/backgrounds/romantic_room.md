# Background: the sunlit room (romantic songs)

**Status:** rejected by the owner on 2026-09-29 after it was built (step 17, PR #16): "ye aisa
background tha jis mein 1 sec mein skip kardu" (H-032). Replaced by `romantic_lights.md`. Kept
for the record of what did not work.

## Why this direction

The channel's bet is that the lyric styling itself is the content (H-022). The owner turned down
seven background prototypes (four vibe scenes, three song-driven ideas) because they were common
and did not match the song's vibe. What the owner asked for: a background that fits the song's
mood, feels fresh, feels made by an artist rather than downloaded, makes the lyrics on it look
good, and can take any lyric later.

## Five principles for a romantic background

1. **Show the person's absence, never a face.** A face pulls the eye away from the lyrics and
   looks like stock footage. An empty room, a half-drunk cup of chai, a dupatta on a chair: the
   viewer puts their own person there. Romance on screen is mostly waiting and remembering.
2. **Quiet space for the lyrics.** The lyrics are the hero, the background is the stage. Detail
   sits at the edges; the lyric area stays calm.
3. **The lyrics belong to the scene.** The light that falls on the room also falls on the text,
   and the text casts a faint shadow on the wall, so it looks written there, not pasted on.
4. **Motion as slow as breathing.** A curtain, the light, floating dust. Nothing jumps.
5. **A hand-made texture and a small story.** Plaster or paper grain and a little imperfection
   give the made-by-an-artist feel. Something changes from the first line to the last, so there
   is a reason to watch to the end, and the last frame can be the thumbnail.

## The room, through the viewer's eyes (default mood)

- **Opening frame:** the warm-coloured wall of an empty room. Afternoon sun comes through a
  window: the shadow of a jaali, the moving shadow of money-plant leaves, dust floating in the
  light. A dupatta hangs on a chair in the corner.
- **The song starts:** the lyrics appear in the patch of sunlight, tinted by the same golden
  light, with a faint shadow on the wall.
- **Through the song:** the light slowly moves and turns from gold to rose, as if the day is
  ending. On a marked word the curtain lifts in the wind and the light blooms for a moment.
- **Last line:** evening. The room turns blue and a small lamp comes on. That frame can be the
  thumbnail.

Why it works: a plain wall is the cleanest surface for lyrics; the jaali, the money plant and the
chai feel like the viewer's own home; everything is drawn by code, so it does not look downloaded.

## One room, six moods

The room stays the same in every video (the channel's recognisable place, built once). A mood,
picked per song like a theme, changes the time of day, weather, light colour and props.

| Mood | What the room shows | Songs |
|---|---|---|
| Morning | Soft white-gold light, the curtain moving | New love, happy, light songs |
| Afternoon to dusk (default) | Light from gold to rose, a lamp comes on at the end | Longing, waiting, first sight (Khidki) |
| Rainy evening | Blue-grey light; shadows of raindrops running down the window glass, on the wall | Separation, heartbreak |
| Moonlit night | Cool moonlight through the jaali, a warm lamp in the corner | Night songs, intimacy, lullaby-like |
| Misty winter morning | Haze, diffused light, steam from chai | Calm, settled love |
| Festival night | Fairy lights and the glow of diyas | Wedding and celebration romance |

The same room can end a song either way: a happy song ends with the lamp coming on, a sad one
with it going out.

## Reusable for any lyric (owner's constraint)

- The room reads only the song's length, each word's time, the beats, and the owner's
  `drops.txt` and `*marked*` words for small reactions. It never reads what the words mean, so any
  lyric of any length works; the light's journey stretches to the song's length.
- The lyric area on the wall is in the same place in every mood, matching the themes' lyric
  block (safe zone x 60-960, y 380-1540).
- Small seeded changes per video (where the plant stands, the curtain print, the prop on the
  table: chai, a radio, a letter) keep repeated videos fresh while the room stays the same.
- Text themes that fit: Soft Romantic v2, Cinematic, Lofi Minimal / Typewriter. Beat Pop and
  Phonk Neon do not.

## Out of range

Fast party or dance romance (Punjabi beats) does not suit a quiet room; it stays with Beat Pop
and Phonk Neon.

## Avoid

Sunset couple silhouettes, anime or Ghibli-style AI couples, rose petals, bokeh, starry skies,
stock couples in the rain, and any face.

## Build order

1. The default mood (afternoon to dusk) on Khidki; the owner judges it.
2. The other moods one at a time.

## Notes for the spec (not decided)

- This makes the engine render a finished video (background + text + audio), a scope change
  from V1 (H-023).
- Likely procedural: a light patch, soft shadows cast by the jaali, leaves and curtain, dust
  motes, and a colour grade that follows song time; props as painted cut-outs (AI stills made
  once, or CC0 art). Tools and prices: `docs/research/background_tools.md`.
- "Lyrics catch the room's light and cast a shadow on the wall" touches text rendering; the spec
  decides how, without ever changing the text (red line 2).
