# Background: romantic, "Chaand ka ghoonghat" (`chaand`)

**Status:** final (H-040: the owner handed the approval to Claude, who approved it after a last
check of the finished shorts). Built into the engine (`--bg chaand`) from a moving sample an agent
made from the still (critic 6/10, H-038) and the critic's fixes. Module
`src/lyric_engine/background/chaand.py`.

## The idea

A full moon behind a veil of high cloud, a ghoonghat. The song lifts the veil: the viewer waits for
the moon's face to show, and it does on the last line.

## Layers

- **Far:** a deep navy sky, the moon (cream, soft, connected maria, never a hot point) and its
  aureole.
- **Mid:** the veil, a textured high-cloud sheet lit silver from the moon, with a lit, arched,
  folded hem; below it a calm dark cloud bank (the lyrics sit on it).
- **Near:** mango/neem crowns with forking trunks along the bottom, a far grove, mist between
  rows; a faint moon-facing sheen.

## Motion and song reaction

- Clouds drift at three speeds, the trees sway a hair, the aureole breathes with the veil.
- Every timed word: the hem lifts a little and settles (a breath).
- Every marked word: a peek, higher each time (0.27, 0.38, 0.49 of the full lift, capped 0.62).
- Last line (or 85% of the length with no words): the full lift over 2.6 s along the cloud shapes;
  it stays open to the end.

- 2026-10-02 (D-040): the moon stays dim behind the veil until ~2.8 s and then comes out, so a
  title card (which sits over the moon) reads.

## Known issues (agent's report)

- With few marked words the peeks are subtle; the payoff reads mainly in the last 3 s.
- Tree crowns are smooth domes, a stylised painting; mid-row trunks thin; the bottom is a flat blue
  mist.
- Peak memory not measured.

Sample: `songs/_review/backgrounds/templates/romantic/chaand_sample.mp4` (review only).
