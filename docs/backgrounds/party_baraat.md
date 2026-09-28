# Background: the baraat's lights (party and dance songs)

**Status:** direction approved by the owner on 2026-09-29 (H-027). Not built yet; the next step
is its spec.

## Why this direction

Same brief as the romantic room (H-022, H-024): fits the song's vibe, feels fresh and made by an
artist rather than downloaded, makes the lyrics on it look good, and takes any lyric later.
Party songs add three things: energy from the first second, the drop as the moment people wait
for, and people, since nobody parties alone.

## Five principles for a party background

1. **Energy from the first second.** The first frame is already full of light and colour, but
   the lyric area stays clear.
2. **The whole world dances.** On the beat everything moves together, all the lights and all the
   people; only the lyric area stays still.
3. **The drop is the celebration.** The drop gets the biggest moment: fireworks, flowers.
4. **Our own celebration.** Not club lasers. An Indian party is a baraat: band-baaja, dhol,
   marigolds, anaar fireworks.
5. **People, not faces.** People appear only as silhouettes; a face pulls the eye from the
   lyrics.

## The baraat, through the viewer's eyes (default mood)

- **Opening frame:** a baraat on a street at night. Along the bottom and the sides walk the
  light-bearers, glowing chandelier-like lamps on their heads; the band's brass instruments
  shine. The people are black silhouettes, as if cut from paper; only the light glows like the
  real thing. The open dark sky in the middle is where the lyrics sit.
- **On the beat:** all the lamps bounce together, as if their bearers are dancing, and a glint
  runs along the brass.
- **On a marked word:** a rocket goes up and bursts, golden sparks at the edges.
- **On a drop:** anaar fountains erupt at the bottom and marigold petals fly.
- **The end:** the biggest burst of fireworks, and the baraat moves on.

Why it works: every Indian knows the baraat's lights, yet they are rarely seen in lyric videos;
paper-cut silhouettes with real-looking glow feel made by an artist; the dark sky is a clean
place for lyrics; and party songs are the songs a baraat dances to.

## One baraat, five moods

| Mood | What it shows | Songs |
|---|---|---|
| Baraat night (default) | Light-bearers, the band, anaar fireworks | Bollywood dance, wedding songs |
| Sangeet | Indoor hall, fairy lights, a glowing dance floor | Film dance numbers, sangeet |
| Haldi / mehndi | Daylight, yellow and green, marigold strings | Playful songs, mehndi songs |
| DJ cart | LED panels, speakers, lights | Punjabi party, club hits |
| Holi | Clouds of gulaal bursting on the beat | Holi songs, songs about colour |

## Reusable for any lyric (owner's constraint)

- The background reads only the song's length, each word's time, the beats, `drops.txt` and the
  `*marked*` words. It never reads what the words mean, so any lyric of any length works.
- The lyric area (the open sky, or its equivalent in each mood) is in the same place in every
  mood, inside the themes' lyric block (safe zone x 60-960, y 380-1540).
- Seeded changes per video: lamp designs, colours, the silhouettes' poses.
- Text themes that fit: Beat Pop, Pop Karaoke.

## Avoid

Club lasers, strobes, disco balls, crowds with hands in the air, neon, confetti, EDM equaliser
bars, stock fireworks, glitter, photos of dancers.

## Build order

1. The default mood (baraat night) on a real party song; the owner puts one in `songs/`.
2. The other moods one at a time.

## Notes for the spec (not decided)

- Silhouettes as paper-cut layers; lamps and brass as glowing sprites; fireworks and petals as
  particles, driven by `beats.json`, `drops.txt` and the marked words.
- Fireworks and sparks stay at the edges; nothing bright crosses the lyric area.
- One art style across all backgrounds (hand-made, warm light, the same grain), so the room, the
  truck and the baraat look made by one artist: Claude's suggestion, stated 2026-09-29, not
  objected to.
- A finished-video render, as for the romantic room (H-023).
