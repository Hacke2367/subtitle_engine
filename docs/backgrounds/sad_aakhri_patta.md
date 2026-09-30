# Background: sad songs, "Aakhri patta" (`aakhri`)

**Status:** built into the engine (`--bg aakhri`, mood `dusk`) from a moving sample made by an
agent from the still (critic 6.5/10, H-038) and the critic's fixes; **not yet approved by the
owner** (D-035). Module `src/lyric_engine/background/aakhri.py` (about 940 lines: one art module,
kept whole rather than split). The agent rates it 6.5-7/10.

## The idea

A big old peepal at dusk sheds its leaves one per sung word. One leaf hangs alone, lit from behind;
the viewer waits for it to fall. It lets go on the last line.

## Layers

- **Far:** steel-indigo sky sinking from dusk to a deeper blue, rose on the undersides of high
  clouds, a thin ember line at the horizon, soft village and tree rows in haze.
- **Mid:** the peepal, a near-black forking silhouette whose crown is clusters of peepal leaves; a
  calm dark lyric band; the hero leaf in a gap in the brightest cloud.
- **Near:** falling leaves in two depth classes, a blurred near leaf passing at the right edge, a
  drift of leaves on the ground.

## Song reaction (any song length)

- The share of words already sung sets how many crown leaves remain: dense at the start, bare at
  the last word. Each sung word releases leaves (a few fall in full, the rest dissolve).
- Marked word: a gust streams leaves off to the right, the tree sways about 2.8x for ~3 s.
- Last line (or 85% of the length with no words): the hero leaf drifts down toward the camera,
  grows from 80 to 150 px, turns broadside and glows gold, landing on the ground at the ember line.
- Behind the text on screen (the `ink` box) rim lights and leaf glows dim, so the lyrics stay clear.
- No words: leaves are released evenly over the length.

## Known issues (agent's report)

- The bare tree's fine twigs end in thorn-like points; bottom-left roots read as planks.
- Far rows are soft blobs; rooftops and water tanks may not read.
- The near blurred leaf is an orange-brown smudge; clouds slightly mauve, not steel-blue.
- About 1.1 s per frame single-process; with worker processes the text box is passed to each worker.

Sample: `songs/_review/backgrounds/templates/sad/aakhri_sample.mp4` (review only).
