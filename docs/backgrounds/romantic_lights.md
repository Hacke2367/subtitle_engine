# Background: romantic light looks (rain, fog, milan)

**Status:** all three romantic looks are final from their moving samples: rain (H-034), fog
(H-035) and milan (H-036). Milan replaced the dropped drive look. All three are built into the
engine (`--bg rain|fog|milan`, spec 17 v2, D-033), ported from the approved samples; the owner
judges the engine's shorts. They replace the sunlit room (`romantic_room.md`), which the owner
rejected after it was built.

## The owner's rules (H-032), for every background from now on

1. **The light is felt, never poking the eye.** Large soft light, haze, rays and washes. No
   small hot points, no sparkles, nothing festive or childish (no fireworks, lanterns or diyas as
   decoration).
2. **The whole screen is used.** One lit scene from top to bottom, not a cluster in one corner.
3. **Real depth.** At least three layers (far, mid, near), each with its own blur and haze, and
   in motion each moves at its own speed.
4. **The lyrics stay the clearest thing** ("lyric clearly dikhna chaiye"). Behind the text the
   frame is calmer and darker, with a soft scrim if needed (the 3:1 rule of spec 17); a bold
   theme beats a thin one on a busy look.

Colour: film palettes (teal and amber, deep blue, sodium orange), mixed in OKLab, with a fine
static grain. Mockups: `songs/_review/backgrounds/lights2/light_worlds.py` (review only).

## 1. Rain (`rain`): slow colourless rain; colour rises where it lands

**Status:** final, approved by the owner on 2026-09-29 from its moving sample, with a few soft
clouds added: "ye video ko final kardo and just aasman mein thode cloud add kardo, and kuch bhi
mat change karna" (H-034). The approved sample is `songs/_review/backgrounds/lights2/rain_final.mp4`,
made by `rain3_video.py`; the engine's version must match it.

Two tries were dropped after their moving samples (H-032):
- **A rainy window with a defocused city.** "isko drop kardo, ek real ashettic barish kaishi
  hoti hai wo banao ... usme halki si chamak rahegi ... lyric clearly dikhna chaiye".
- **Rain in a streetlight's cone at night.** "rain ko slowly girwa and usme ka colour hata do,
  jab wo jamin pe niche gire tab usme (jamin) se ek colur nikle. and rain ko thoda naturally
  banao - and theme dark mat rakho puri tarha se thoda sa light theme do".

**Layers**
- **Far:** a soft overcast evening, lighter than night: grey-blue sky with a few soft clouds
  drifting slowly high up, mist on the horizon, a faint tree line far away.
- **Mid:** slow, colourless rain. Each drop has its own depth: far drops are small and slow and
  land near the horizon; near drops are bigger and softer and land low in the frame. The rain
  sways a little in the wind.
- **Near:** wet ground that mirrors the sky and the trees. Where a drop lands, a faint ripple
  spreads and a soft pastel colour (rose, peach, lilac, teal, gold) rises out of the ground and
  fades.

**Frame:** a gentle scrim behind the lyrics; a bold theme (Soft Romantic v2).

**Song reaction:** each sung word lands a bigger bloom of colour on the ground below it; a marked
word lands the biggest, in rose.

**Songs:** longing, separation, rainy-day romance; also sad and lofi.
Sample: `songs/_review/backgrounds/lights2/rain3_video.py`.

## 2. Fog (`fog`): moonlight and shadow through fog

2026-10-02 (D-040): the title card's rows are calmed for its first ~3 s (`paint.title_calm`),
since the rays were brightest right behind it.

**Status:** final, approved by the owner on 2026-09-29 from its moving sample, in the
"moonlight" palette (H-035). The owner asked for a different, peaceful colour combination and a
slightly darker theme than the first gold version ("thoda diffrent colur combo try karo light and
jo thoda peacfully ho ... thoda dark theme try karo ekdum thoda"), then picked moonlight from
four (moonlight, lavender, mint, dawn): "chaandni wala final kardo".
- Approved sample: `songs/_review/backgrounds/lights2/fog_final.mp4`.
- Made by `fog_video.py full moonlight`.
- The engine's version must match it.

Palette (moonlight):
- base: deep navy `#040a16` → `#050b1b` → `#010206`;
- source glow: `#e2eaff`;
- rays: silver-blue `#b9ccff`;
- scatter: `#46699e`.

The owner's notes on the first moving sample: "usme thoda shading do, and jo neecha ka hissa hai
usko dark rakho. and jaha se fog niklta hai waha light halka sa jyada rakho and neeche aate hue
thoda kam. bas aisa feel ho ki ha ye shadow hai ek fog hai."

**Layers**
- **Far:** deep navy shadows. The lower part of the frame falls into darkness, like ground in
  shadow.
- **Mid:** broad soft rays of silver-blue moonlight falling diagonally through gaps in leaves from
  beyond the top left. They are brightest where the light comes in and fade as they come down,
  with darker shadow between them.
- **Near:** slow wisps of fog drifting across, glowing where a ray catches them and darkening the
  air where they sit in shadow.

**Frame:** a gentle scrim behind the lyrics (Cinematic text).

**Motion:** the fog drifts; the gaps in the leaves sway, so the rays shift slowly.

**Song reaction:**
- Each sung word brightens the rays a little, as if a cloud moved.
- A marked word opens a new ray that stays.

**Songs:** calm and devotional romance, Sufi-romantic, sukoon.
Sample: `songs/_review/backgrounds/lights2/fog_video.py` (argument `full moonlight`).

## 3. Milan (`milan`): drifting dots that light up where they meet

**Status:** final, approved by the owner on 2026-09-29 from its moving sample: "ok isko final
karo" (H-036). Two rounds of the owner's notes shaped it:
- "puri theme ko thoda dark hi vibe dena hum dots ke takrane se jo light aaygi uska feel denge
  and ek dum halka sa na dark border dena";
- "dots ko thoda bada and clearly visibe banao, lekin usme lighting mat do jab wo takrye tabhi
  lighting aaye".
Approved sample: `songs/_review/backgrounds/lights2/milan_final.mp4`, made by
`milan_video.py full`. The engine's version must match it.

The drive look (a night drive, twice) was dropped: "ye template ko drop kardo, iski jagha kuch
aur socho". In its place the owner proposed: "background mein dots slowly randomly ida udar ja
rahe hai, and jab bhi apas mein takra rahe hai tou ek halki si light chhod rahe hai. ek dum
force fully dots move ho rahe hai, aisa na feel ho". Claude kept the idea ("jab do milte hain,
roshni hoti hai" suits romance) and added three things: a natural wander, meetings timed to the
marked words, and memories of the meetings.

**Layers**
- **Far:** an almost black night with a very faint plum haze, a light dark border round the
  frame, and a few small matte dots drifting slowly.
- **Mid:** bigger matte dots, clearly visible (cream, pale gold, pale rose) and giving no light
  of their own. Each is on a smooth random wander: its velocity changes slowly and never jerks,
  so nothing looks pushed. When two meet, they linger a moment and light up, a soft warm light
  blooms where they met and fades, and a faint memory of it stays for a long while.
- There is no near layer. Big blurred dots would have been light of their own, and the only
  light is where dots meet.

**Frame:** dark; a gentle scrim behind the lyrics (Soft Romantic v2).

**Song reaction:**
- On each marked word, two dots near that word drift together and meet just as it is sung, with
  a warmer bloom. In the engine they meet 130 px below the lyrics, under the word: the sample's
  "just above the word" put the meeting behind Soft Romantic v2's past line and failed the
  legibility rule (D-033).
- Behind the text on screen, dots and their light dim (engine only, D-033), so the lyrics stay
  clear when a dot drifts behind them.
- By the end of the song the frame holds the faint memories of every meeting.

**Songs:** romantic of every kind; meeting, longing, togetherness.
Sample: `songs/_review/backgrounds/lights2/milan_video.py` (argument `full`).

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
2. Build all three into the engine on the step 17 pipeline (`--bg`, the finished short with audio,
   the checks): rain, then fog, then milan. Each engine render must look like its approved sample
   in `songs/_review/backgrounds/lights2/`. Done 2026-09-29 (D-033).

## Rejected on the way (H-032)

- **The sunlit room:** dim, nothing moving in the first second, props that looked like clip-art.
- **Flowing colour gradients:** a known pattern.
- **Lanterns, raindrops and fireworks as small lights** (`songs/_review/backgrounds/lights/`):
  the owner called them "Diwali wala, kids wala", and the lights poked the eye instead of being
  felt.
