# Background: the lamp in the niche (Sufi and devotional songs)

**Status:** direction approved by the owner on 2026-09-29 (H-028). Not built yet; the next step
is its spec.

## Why this direction

Same brief as the romantic room (H-022, H-024): fits the song's vibe, feels fresh and made by an
artist rather than downloaded, makes the lyrics on it look good, and takes any lyric later.
Sufi and devotional songs add two things: people listen to them for peace, and religious imagery
needs care. One world covers both, because the lamp (chiraag, diya) is sacred in both.

## Five principles for a spiritual background

1. **Peace first.** Few things in the frame, deep darkness, one warm light, slow motion.
2. **The feeling of devotion, never an image of God.** No deities, holy books or saints' faces:
   it is sensitive, and it would look the same on every song. Light, smoke, lamps and flowers are
   sacred in nearly every tradition.
3. **Light is the hero.** The lyrics are read by the flame's light, as if sitting beside a lamp.
4. **A slow rise.** Sufi songs and bhajans start slow and build to a peak; the background starts
   calm and is full of light by the end.
5. **The mark of time.** Lime plaster, stone, old brass, a clay lamp. None of it looks
   downloaded.

## The lamp and the moth, through the viewer's eyes (default mood)

- **Opening frame:** darkness. An old lime-plastered wall with an arched niche (taaq) holding a
  lit clay lamp. Incense smoke drifts through the light, and a small golden moth (parwana)
  circles the flame.
- **The lyrics:** on the wall below the lamp, in the flame's warm light. When the flame moves,
  the lyrics' faint shadow moves with it.
- **On a clap or beat:** the flame jumps a little and the smoke swirls.
- **On a marked word:** the flame flares and the whole wall turns golden for a moment.
- **With every line:** the moth comes a little closer to the flame.
- **Last line:** the moth enters the flame and light spreads across the whole screen. In Sufism
  this is fana, losing the self to become one. That frame can be the thumbnail.

Why it works: the moth and the flame (parwana and shamaa) are the oldest image in Urdu and Sufi
poetry, so those who know it get goosebumps and those who don't still see a beautiful story; one
flame in the dark is the calmest frame and the easiest to read lyrics on; and it looks like an
old painting of light in darkness, not stock footage.

## One lamp, five moods

| Mood | What it shows | Songs |
|---|---|---|
| Dargah night (default) | Lime-plaster wall, clay lamp, incense, the moth | Sufi, qawwali |
| Temple morning | Stone wall, brass diya, marigolds, blue morning light; one more diya lights with every line | Bhajan, aarti, calm devotion |
| Ghat evening | Lamps floating on the water, smoke | Ganga and Shiv bhajans, emotional devotion |
| Fervour | Flames leaping on the beat, saffron-red light, smoke | Shiv Tandav and other high-energy devotional songs |
| Nirgun | Only the flame and smoke, no symbol at all | Kabir, nirgun, universal spiritual songs |

## Reusable for any lyric (owner's constraint)

- The background reads only the song's length, each word's time, the beats, `drops.txt` and the
  `*marked*` words. It never reads what the words mean, so any lyric of any length works.
- The lyric area on the wall is in the same place in every mood, inside the themes' lyric block
  (safe zone x 60-960, y 380-1540).
- The owner picks the mood per song; the engine does not guess a song's faith.
- Symbols of different faiths never share a frame.
- Text themes that fit: Cinematic (ivory and gold, like written poetry) above all; Beat Pop for
  the fervour mood.

## Avoid

Photos or AI images of gods, images of holy places or holy books, saints' faces, glowing "Om"
stock, spinning mandala stock, light rays through clouds, the galaxy "spiritual" look, 3D lotuses.

## Build order

1. The default mood (dargah night) on a real Sufi song; the owner puts one in `songs/`.
2. The other moods one at a time.

## Notes for the spec (not decided)

- Procedural: a flickering flame, drifting smoke, the moth's path tightening towards the flame
  line by line, a final bloom of light; in the temple mood, lamps lighting one per line instead
  of the moth.
- The lyrics lit by the flame, with a moving shadow, touch text rendering as in the romantic
  room; the spec decides how, without ever changing the text (red line 2).
- One art style shared with the other backgrounds (H-027 note); a finished-video render (H-023).
