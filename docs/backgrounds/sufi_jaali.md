# Background: Sufi, "Jaali se subah" (`jaali`)

**Status:** built into the engine (`--bg jaali`, mood `dawn`), picked by the owner in H-038. Claude
rebuilt it from the still (critic 6/10) with the critic's fixes and checked the moving sample and a
real render; it waits for the owner to see it (as H-040 did for the first six). Module
`src/lyric_engine/background/jaali.py`.

## The idea

The last hour of the night in a dargah hall (tahajjud / brahma muhurat). A carved stone jaali high in
the back wall lets the moon's light in; line by line that light walks across the floor toward the
viewer, the night turns rose and then gold, and on the last line the warm pattern of the lattice
lies at the viewer's feet ("the light reached me").

## Layers

- **Far:** the back wall of lime-washed sandstone (uneven courses, staggered joints, patina and damp
  stains) with a pointed-arch jaali in a carved reveal and a rectangular frame (alfiz). The lattice
  is a lace of 8-point star rings with thin webs (about a third stone), cut by a carved band that
  follows the arch; a few stars are filled, some dusty. Its cut faces catch a thin sliver of light on
  the side toward the source.
- **Mid:** beams in incense haze. One parallel beam (moon, then sun), traced in perspective, each
  hole's light ending where it reaches the floor; soft shadows of things outside drift across the
  window and streak the beams into rays. Brightest near the window, fading as they come down.
- **Floor:** polished stone slabs in perspective; the lattice's light lies on it (traced back to the
  window), softer the farther it travelled; dust glows just above it; the lit wall shows faintly in
  the polish.
- **Near:** the near arcade's pillars and cusped arch, out of focus, with a rim toward the hall.

## Motion and song reaction

- Haze drifts, the outside shadows drift (the rays shimmer), clouds pass behind the lattice and now
  and then veil the moon.
- Every timed word: a breath of incense rises into the beams (it shows only where it crosses light)
  and the haze swells a little.
- Every marked word: the moon clears for about 3 s (brighter beams, a crisper floor pattern).
- Every line: the light moves one eased step (1.8 s) forward, so the pattern walks toward the viewer.
- Over the song: night (silver-blue) → rose → dawn (warm gold), complete just after the last line
  starts; with no words, the same arc over 85% of the length.

## Colours

Night: light `#c8d5f6`, scatter `#35507e`. Rose: light `#f2c6c8`. Dawn: light `#ffd394`, scatter
`#a8622c`. The night lingers navy in the corners at dawn.

## Critic fixes (from the still)

Night is blue-silver, not green; the lattice is open lace with thin webs, not a perforated board, and
fills its arch inside a carved band; the floor pattern comes from the window (blocked holes, dapple,
soft toward the camera); beams connect window and floor; the brightest haze is beside the text, with
a calm patch behind the lyrics; the dawn is warm ivory-gold with no gradient fill and no starburst;
wall courses are irregular.

## Known issues

- The floor pattern is still regular (a lattice is regular); near the wall it reads a little like
  tiles until the dapple moves.
- At night the lower third is dark (the pool lies far by the wall at first).
- The hall has no side walls; its scale comes from the pillars and the floor slabs only.
- 1.2 s per frame on the laptop; init about 3.5 s per process.

Sample: `songs/_review/backgrounds/templates/sufi/jaali_sample.mp4` (review only).
