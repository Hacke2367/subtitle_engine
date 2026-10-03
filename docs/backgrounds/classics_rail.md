# Background: old classics, "Rail ki Seeti" (`rail`)

**Status:** built into the engine (`--bg rail`, mood `night`), picked by the owner in H-038. Claude
redesigned it from the still (critic 6.5/10) and checked the moving sample and a real render; it
waits for the owner to see it. Module `src/lyric_engine/background/rail.py`. Decision: D-037.

## The idea

The farewell of the old films: a steam train at a night platform, and on the last line "gaadi chali
gayi" — the train pulls away into the fog and the platform is left empty under the lamps, with the
couple who came to see someone off still standing there.

## Changed from the still (and why)

- **The engine is seen from the side, front away from us.** The still's front-facing engine read as
  a cartoon face (the critic's worst note); from the side there is no face to read, and the
  departure is what the spec asks ("its side slides away, the headlight moves off into the fog").
- **A couple instead of a lone woman.** A lone woman at a night platform with her pallu down her
  back read as the haunted-station "chudail" trope. Now she has her pallu over her head and stands
  with a man in a shawl and a Gandhi cap, his trunk at his feet.
- No black bar at the top: the canopy's underside with thin cross beams and lamp-lit trusses. No
  reflection streaks through the lyrics: the wet stone's reflections fade before y ≈ 1040.

## Layers

- **Far:** the cold blue fog at the platform's end, the headlight's warm cone in it, the station
  building's waiting-room arches glowing faintly on the left.
- **Mid:** the cast-iron columns and arched brackets, hanging lamps (soft glows, no hot points), the
  dagger-board valance, the train: tender, the cab with its fire door glowing, the boiler, domes and
  chimney; the couple; the steam (chimney plume, puffs rolling under the canopy, the whistle).
- **Near:** a blurred steel trunk with a bedroll at the lower left, the wet stone floor with a lamp's
  pool and a cold sheen.

## Motion and song reaction

- The chimney breathes a puff every 0.3 s (varied), the cab's fire flickers, hanging steam drifts
  toward us under the canopy.
- Every timed word: the headlight's glow in the fog brightens a little.
- Every line: a fresh, bigger puff rolls back under the canopy.
- Every marked word: the whistle, a thick white plume rolling sideways, gold where the headlight
  catches it; the lamps' haze swells.
- Last line (or 85% of the length with no words): the train pulls away (55 m by the end, slow at
  first), its coach and lit windows sliding past, its red tail lamp receding into the fog; its steam
  thins over the empty track.

## Known issues

- The lower half is a quiet, dim floor; the trunk at the lower left reads only as luggage-like.
- On a short clip the departure is quick (it always ends with the clip).
- The engine is a silhouette; at phone size it reads by its cab fire, chimney and steam.
- 0.95–1.2 s per frame on the laptop; init about 9 s per process.

Sample: `songs/_review/backgrounds/templates/classics/rail_sample.mp4` (review only).
