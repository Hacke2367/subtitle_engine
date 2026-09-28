# Background: the truck's back (hip-hop songs)

**Status:** direction approved by the owner on 2026-09-29 (H-026). Not built yet; the next step
is its spec.

## Why this direction

Same brief as the romantic room (H-022, H-024): fits the song's vibe, feels fresh and made by an
artist rather than downloaded, makes the lyrics on it look good, and takes any lyric later.
Hip-hop adds two things: the lyrics are fast and dense and the viewer wants to read every bar,
and punchlines are the moments people quote.

## Five principles for a hip-hop background

1. **Bars first.** The lyric area is the cleanest, highest-contrast part of the frame; the noise
   stays at the edges.
2. **Feel the beat, don't just see it.** The background jolts on the beat, as if the bass is
   shaking it; a pulse of light alone is not enough.
3. **Punchlines hit.** A `*marked*` word is a punchline, and the background reacts to it. That is
   the moment people comment on and share.
4. **Own soil.** Desi street, not a copy of an American neighbourhood. Desi hip-hop's pride is
   the desi road.
5. **Raw texture.** Paint, dust, rust, photocopy grain. Not shiny 3D chrome.

## The truck, through the viewer's eyes (default mood)

- **Opening frame:** a highway at night; the back of a truck fills the screen. Hand-painted:
  peacocks, eyes, flowers, glinting reflectors, black tassels and chains hanging below, red tail
  lights.
- **The beat starts:** on every beat the truck bounces over a pothole, the tassels and chains
  swing, dust flies.
- **The bars:** they appear in the plain centre panel, the spot where a truck carries its
  painted line ("Buri nazar wale tera munh kala"). Truck-back lines are India's original
  punchlines; here the rapper's bars take their place.
- **On a punchline:** a horn from behind, a headlight flash, and a hard jolt.
- **On a drop:** black exhaust smoke and the whole frame shakes.
- **The end:** the truck pulls away; the tail lights shrink into the dark.

Why it works: truck art is real Indian folk art, so it looks hand-made, and it is rarely seen in
lyric videos; a 9:16 screen has the proportions of a truck's back; Beat Pop's mustard pill
already looks like truck lettering and Beat Pop bumps its line on every beat, so with the truck
bouncing on the same beats the text reads as painted on the truck.

## One truck, five moods

| Mood | What it shows | Songs |
|---|---|---|
| Night highway (default) | Dark, red tail lights, headlights of the car behind | Hard, serious rap |
| Dhaba afternoon | Harsh sun, dust, heat | Fun, commercial desi hip-hop |
| Rainy night | Wet road, red light reflected in it | Emotional, introspective rap |
| City traffic | Neon boards, autos, horns | Hustle, city rap |
| Punjab road | Fields, mustard flowers, a tractor | Punjabi hip-hop |

## Reusable for any lyric (owner's constraint)

- The truck reads only the song's length, each word's time, the beats, `drops.txt` and the
  `*marked*` words. It never reads what the words mean, so any lyric of any length works.
- The lyric panel is in the same place in every mood, inside the themes' lyric block (safe zone
  x 60-960, y 380-1540).
- Seeded changes per video: paint motifs, colours, reflector patterns, tassels.
- Painted words on the truck (for example "HORN OK PLEASE") stay few and far from the lyric
  panel, so nothing competes with the bars.
- Text themes that fit: Beat Pop, Phonk Neon. Soft Romantic and Cinematic do not.

## Out of range

Party and dance songs (celebration rather than street) get their own background.

## Avoid

Graffiti walls, neon cities, red smoke, money-guns-cars flex, skulls, glitch or VHS effects,
anime phonk edits, the rapper's photo, American brick-wall streets.

## Build order

1. The default mood (night highway) on a real hip-hop song; the owner puts one in `songs/`
   (Khidki does not fit).
2. The other moods one at a time.

## Notes for the spec (not decided)

- The truck's bounce and Beat Pop's line bump must use the same beat times (`beats.json`).
- Motion right under the lyric panel stays small, so fast bars stay readable.
- Likely: the painted truck as layered cut-outs (AI stills made once in folk truck-art style, or
  drawn), procedurally swinging tassels and chains, dust, and light flashes as overlays. Tools and
  prices: `docs/research/background_tools.md`.
- A finished-video render, as for the romantic room (H-023).
