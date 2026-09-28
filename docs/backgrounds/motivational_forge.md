# Background: the blacksmith's forge (motivational songs)

**Status:** direction approved on 2026-09-29 (H-030); the owner left the pick to Claude. Not
built yet; the next step is its spec.

## Why this direction

Same brief as the romantic room (H-022, H-024): fits the song's vibe, feels fresh and made by an
artist rather than downloaded, makes the lyrics on it look good, and takes any lyric later.
Motivational songs add two things: the viewer wants a push (goosebumps), and the story of
motivation is a transformation.

## Five principles for a motivational background

1. **Every beat is a blow of effort.** The background shows impact on the beat: a strike,
   sparks. A pulse of light alone is not enough.
2. **From raw to finished.** The background starts raw and is finished by the end, so the viewer
   sees their own journey.
3. **The effort, not the person.** No athlete's or bodybuilder's body: it looks like stock and
   the viewer cannot see themselves in it. Only the marks of work.
4. **Darkness and fire.** One warm light in the dark gives intensity, and lyrics read cleanly on
   the dark.
5. **A desi proverb.** "Tap ke hi sona kundan banta hai" (only gold that goes through the fire
   becomes kundan). Everyone knows it; the background shows it.

## The forge, through the viewer's eyes (default mood)

- **Opening frame:** a blacksmith's forge in the dark. Coals glow red, embers float in the air,
  and a red-hot bar of iron lies on the anvil.
- **The beat starts:** every beat, a hammer strikes. Only the hammer's shadow is seen, and a
  fountain of sparks bursts from the iron.
- **With every line:** the iron takes a little more shape, from a straight bar to an edged blade.
- **On a marked word:** the hardest strike, and the frame fills with sparks.
- **On a drop:** the bellows blow and the fire roars up.
- **Last line:** the blade is plunged into water, a cloud of steam rises, and then the finished
  blade gleams in the light. That frame can be the thumbnail.

Why it works: the strikes land on the beat, so the song and the effort move together; the
viewer watches the iron take shape line by line and stays to see it finished; a gym-goer, a
student or anyone struggling can see themselves in the iron, since it is tied to no one sport;
the lyrics sit in the dark above the anvil and the sparks stay below, so the lyrics stay clear.

## One forge, five moods

| Mood | What it shows | Songs |
|---|---|---|
| Forge at night (default) | Darkness, red coals, sparks | Gym, struggle, full intensity ("Zinda") |
| Forge at dawn | Blue morning light through a window, the day's first strike | New beginnings, students ("Aashayein") |
| Storm | Rain and lightning outside, the fire inside | Fighting the odds ("Lakshya", "Kar Har Maidaan Fateh") |
| Gold | Molten gold poured into a mould, golden light | Victory, celebration ("Chak De India") |
| Low fire | A quiet fire, light smoke, calm | Calm, deep motivation ("Ruk Jaana Nahin") |

## Reusable for any lyric (owner's constraint)

- The background reads only the song's length, each word's time, the beats, `drops.txt` and the
  `*marked*` words. It never reads what the words mean, so any lyric of any length works; the
  iron's shaping stretches to the song's length and is finished on the last line.
- The lyric area (the dark above the anvil) is in the same place in every mood, inside the
  themes' lyric block (safe zone x 60-960, y 380-1540).
- Seeded changes per video: the tools on the wall, the embers, the shape of the finished piece.
- Text themes that fit: Beat Pop, Phonk Neon; Cinematic for the low-fire mood.

## Avoid

Bodybuilders, footage of cricketers or athletes, running at sunrise, mountain summits, lions,
eagles, boxing rings, dark "sigma" or "grindset" edits, money and cars, chess pieces.

## Build order

1. The default mood (forge at night) on a real motivational song; the owner puts one in
   `songs/`.
2. The other moods one at a time.

## Notes for the spec (not decided)

- Strikes on `beats.json` beats, the hardest on marked words, the bellows on `drops.txt` drops;
  sparks, embers and steam as particles.
- The hammer is only a shadow; no person is drawn.
- Sparks stay near the anvil, below the lyric block; nothing bright crosses the lyrics.
- One art style shared with the other backgrounds (H-027 note); a finished-video render (H-023).
