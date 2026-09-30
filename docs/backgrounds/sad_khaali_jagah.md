# Background: sad songs, "Khaali jagah" (`khaali`)

**Status:** final. The still was approved by the owner (H-037); the engine look (`--bg khaali`,
module `src/lyric_engine/background/khaali.py`) was approved by Claude, to whom the owner handed
the approval (H-040).

The owner's rules of H-032 hold (`romantic_lights.md`): light felt, never poking the eye; the
whole screen used; real depth; the lyrics the clearest thing. Everything is drawn by code (the
owner has no AI plan: "ye image tum hi banao").

## The idea

A place that once held two people, now empty. The viewer fills the empty half of the bench
themselves; nothing on screen says who is missing, so any sad lyric fits.

## Layers

- **Far:** a night sky over a city far away: its lights, out of focus in the fog, low behind the
  bench.
- **Mid:** a streetlight at the right, its cone of cold light falling through the rain onto an
  empty bench, a pool of light and a long reflection on the wet ground.
- **Near:** the rain, lit only where the cone catches it, with small splashes in the pool of
  light.
- **Frame:** dark, a light dark border, a calm patch behind the lyric block (0.45 at its
  centre, like rain's in D-034), so the lit rain in the cone stays behind the words
  (Soft Romantic v2).

## Motion

- Steady rain; the city's lights hold still.
- The camera moves in very slowly over the song, the lamp and bench more than the far lights
  (6% against 2%), so the place has depth without anything being pushed.

## Song reaction

- **Marked word:** for a moment the place turns warm, like a memory: the cold light and the fog
  turn amber (the "yaad" still), then it goes cold again (in over 0.8 s, held 1.2 s, out over
  2.5 s; never fully warm).
- **Last line:** the streetlight falters once and goes out; the song ends on the empty place in
  the dark, the city's lights still there.
- Other words: nothing. A sad song needs stillness.

## Songs

Heartbreak, separation, missing someone, waiting.

## Build order

1. The moving sample on `khidki_s2_em` (done), approved by the owner before any pipeline work.
2. The engine version on the step 17 pipeline (`--bg khaali`), matching the approved sample, with
   the legibility check.
