# Background: the train's open door (journey songs: friendship, travel, life)

**Status:** direction approved on 2026-09-29 (H-031); the owner left the pick to Claude. Not
built yet; the next step is its spec.

## Why this direction

Same brief as the romantic room (H-022, H-024): fits the song's vibe, feels fresh and made by an
artist rather than downloaded, makes the lyrics on it look good, and takes any lyric later.
Journey songs add two things: the feeling of moving, and a destination.

## Five principles for a journey background

1. **The feeling of moving forward.** Near things pass fast and far things slowly, so the viewer
   feels they are the one travelling.
2. **The journey's rhythm on the song's beat.** The rhythm of the rails matches the beat: poles,
   bridges and girders pass on the beat.
3. **The world from the viewer's own place.** Everything is seen from where the viewer stands,
   with no person in frame, so they put themselves (or their friend) there.
4. **A changing view, one destination.** The view changes from start to end and arrives
   somewhere, which is the reason to watch to the end.
5. **Desi roads.** Not a Ladakh bike ride. Indian rail, kulhad chai, mustard fields, waterfalls:
   everyone's own memories.

## The door, through the viewer's eyes (default mood)

- **Opening frame:** the open door of a moving train, an iron handrail on one side. Outside,
  mustard fields rush past and distant hills drift slowly. In a bottom corner, steam rises from
  a kulhad of chai.
- **On the beat:** a pole passes on every beat, and the wires between the poles rise and fall.
  On a bridge, the iron girders go by on the beat.
- **On a marked word:** a flock of birds rises from the field.
- **On a drop:** the train enters a tunnel; for a moment it is dark and only the lyrics glow,
  then light bursts in and a wide river bridge opens up.
- **Last line:** the train reaches the sea in the evening light. That frame can be the
  thumbnail.

Why it works: the Indian train is everyone's memory (trips with friends, going home, college);
a 9:16 screen has the proportions of a train door; poles passing on the beat are satisfying to
watch; from Kishore's "Gaadi bula rahi hai" to "Yaaron", the train has long stood for life's
journey; and the open door leaves a clear sky for the lyrics.

## One train, five moods

| Mood | What it shows | Songs |
|---|---|---|
| Punjab fields (default) | Mustard, sunshine, poles, a bridge | Friendship, trips, happiness ("Yaaron", "Dil Chahta Hai") |
| Konkan monsoon | Green hills, waterfalls, tunnels, rivers | Travel, freedom ("Ilahi", "Safarnama") |
| Desert evening | Sand dunes, a silhouetted line of camels, a red sun | Songs about life ("Musafir", "Zindagi Ek Safar Hai Suhana") |
| Hill toy train | Mist, deodars, a winding track | Calm, nostalgic journeys |
| Night train | Village lights, the moon, a station's yellow lamp | Missing home, travelling alone ("Chitthi Aayi Hai") |

## Reusable for any lyric (owner's constraint)

- The background reads only the song's length, each word's time, the beats, `drops.txt` and the
  `*marked*` words. It never reads what the words mean, so any lyric of any length works; the
  journey stretches to the song's length and arrives on the last line.
- The lyric area (the sky framed by the door) is in the same place in every mood, inside the
  themes' lyric block (safe zone x 60-960, y 380-1540).
- Seeded changes per video: the landscape's features (tree lines, villages, rivers), the
  handrail side, the object on the floor.
- Text themes that fit: Pop Karaoke (happy), Lofi Minimal (calm), Cinematic (reflective).

## Avoid

Ladakh bike rides, GoPro or drone highway shots, a backpack on a summit, friends jumping at
sunset in silhouette, footprints on a beach, a hand out of a car window, plane and passport
stock, cloud timelapses.

## Build order

1. The default mood (Punjab fields) on a real journey song; the owner puts one in `songs/`.
2. The other moods one at a time.

## Notes for the spec (not decided)

- Pole spacing comes from the beat times, so a pole reaches the door frame exactly on each beat;
  the train's speed follows the tempo.
- The tunnel comes on a `drops.txt` drop; with no drops, no tunnel.
- Landscape as painted parallax layers; the sky behind the lyrics stays calm; the handrail sits
  at the frame's edge.
- One art style shared with the other backgrounds (H-027 note); a finished-video render (H-023).
