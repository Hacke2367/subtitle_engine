# Background: romantic light looks (rain, fog, drive)

**Status:** three looks approved by the owner on 2026-09-29 from mockup stills (H-032). None is
built yet. They replace the sunlit room (`romantic_room.md`), which the owner rejected after it
was built.

## The owner's rules (H-032), for every background from now on

1. **The light is felt, never poking the eye.** Large soft light, haze, rays and washes. No
   small hot points, no sparkles, nothing festive or childish (no fireworks, lanterns or diyas as
   decoration).
2. **The whole screen is used.** One lit scene from top to bottom, not a cluster in one corner.
3. **Real depth.** At least three layers (far, mid, near), each with its own blur and haze, and
   in motion each moves at its own speed.
4. **The lyrics stay the clearest thing.** Behind the text the frame is calmer and darker (the
   3:1 rule of spec 17).

Colour: film palettes (teal and amber, deep blue, sodium orange), mixed in OKLab, with a fine
static grain. Mockups: `songs/_review/backgrounds/lights2/light_worlds.py` (review only).

## 1. Rain (`rain`): a rainy night through a window

**Layers**
- **Far:** the city out of focus. Coloured bokeh (amber, warm white, red, a little cyan and pink)
  along a street low in the frame, with reflections streaking down the wet road. Above, very dim
  and very soft window lights of far buildings.
- **Mid:** rain falling through the air, seen only where it passes in front of the lights.
- **Near:** the glass. A faint mist, drops that hold the street upside down, and streams that
  have run down and left beads.

**Frame:** dark and calm behind the lyrics in the middle; the street's colour fills the lower
third.

**Motion:** the rain falls, the lights breathe a little, and now and then a car's light washes
across the glass from one side.

**Song reaction:**
- Each sung word starts a drop running down the glass below it, clearing its own trail.
- Each new line brings a passing car's light.

**Songs:** longing, separation, rainy-day romance; also sad and lofi. Text theme in the mockup:
Lofi Minimal.

## 2. Fog (`fog`): light through fog

**Layers**
- **Far:** deep teal shadows and a low haze near the bottom.
- **Mid:** broad soft rays of warm gold light, falling diagonally through gaps in leaves from
  beyond the top left and crossing the whole frame.
- **Near:** slow drifting fog that catches the rays.

**Motion:** the fog drifts; the gaps in the leaves sway, so the rays shift slowly.

**Song reaction:**
- Each sung word brightens the rays a little, as if a cloud moved.
- A marked word opens a new ray.

**Songs:** calm and devotional romance, Sufi-romantic, sukoon. Text theme in the mockup:
Cinematic.

## 3. Drive (`drive`): a night drive

**Layers**
- **Far:** the city at the road's end under a deep blue sky.
- **Mid:** street lamps along both sides running to the vanishing point, tail lights ahead and
  oncoming headlights, all out of focus, reflected on the wet road.
- **Near:** the dark of the car, with a faint dashboard glow at the bottom.

**Motion:** the lamps flow past toward the viewer.

**Song reaction:**
- On each beat, a streetlight's amber wash rolls down through the frame, as if the car passed
  under a lamp.
- A marked word brings the slow anamorphic streak of an oncoming car.

**Songs:** romantic songs with a beat, travel and friendship. Text theme in the mockup:
Soft Romantic v2.

## Reusable for any lyric

Each look reads only:
- the song's length;
- the aligned word times;
- the beats and `drops.txt`;
- the `*marked*` words.

It never reads what the words mean. Small details (light positions, where streams run) are
seeded by the song folder's name.

## Build order

1. A moving sample of each look on `khidki_s2_em`, shown to the owner before any pipeline work.
   This is the lesson from the room: it was built in full before the owner saw it move.
2. Rain first, then fog, then drive, on the step 17 pipeline (`--bg`, the finished short with
   audio, the checks).

## Rejected on the way (H-032)

- **The sunlit room:** dim, nothing moving in the first second, props that looked like clip-art.
- **Flowing colour gradients:** a known pattern.
- **Lanterns, raindrops and fireworks as small lights** (`songs/_review/backgrounds/lights/`):
  the owner called them "Diwali wala, kids wala", and the lights poked the eye instead of being
  felt.
