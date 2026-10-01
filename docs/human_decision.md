# Owner Decisions and Open Questions

`Status: pending` = waiting on the owner. Entries never move or get renumbered.

<!-- Entry template (used by /log_decision):
### H-NNN — <title>
**Status:** pending | decided
**Raised:** YYYY-MM-DD
**Needed-before:** <what this blocks>
**Context:** <the situation>
**Options:** <the choices, if known>
**Recommendation:** <if any>
**Decision:**
**Decided:**
-->

### H-001 — Project structure: one package, staged modules (option B)
**Status:** decided
**Raised:** 2026-09-26
**Needed-before:** scaffold
**Context:** `/scaffold` offered A (flat scripts), B (one package, staged modules talking only
through `words.json`), C (two separate tools).
**Decision:** "yes, option B, git init bhi kar do"
**Decided:** 2026-09-26

### H-002 — Tracking tier: standard
**Status:** decided
**Raised:** 2026-09-26
**Needed-before:** scaffold
**Context:** Ongoing solo development, personal tool.
**Decision:** Accepted the proposed `standard` tier.
**Decided:** 2026-09-26

### H-003 — CapCut desktop or mobile?
**Status:** decided
**Raised:** 2026-09-26
**Needed-before:** step 01 (alpha overlay proof)
**Context:** Desktop CapCut imports `.mov` with alpha; mobile CapCut does not, and would need the
green-screen mp4 + Chroma Key path as the main output instead of the fallback.
**Options:** desktop / mobile / both
**Recommendation:** desktop (assumed during kickoff)
**Decision:** "both". Alpha `.mov` (desktop) and green-screen mp4 (mobile, Chroma Key) are both
primary outputs; neither is a fallback.
**Decided:** 2026-09-26

### H-004 — Alignment provider
**Status:** decided
**Raised:** 2026-09-26
**Needed-before:** step 02 (word alignment)
**Context:** Step 02 needs per-word timings for known lyrics (forced alignment). No GPU, but the
owner accepts ~10 min per song, so a local CPU pipeline is viable alongside a paid API. The owner
likely has an ElevenLabs account already (used for TTS by `C:\MANIM_VIDEOS_CODE_TEMPALTE`).
Accuracy on sung, romanized Hindi is unknown for every option.
**Options:** ElevenLabs forced-alignment API (paid, easy) / local: vocal isolation + open
alignment model (free, slower, more setup)
**Recommendation:** try both on one real song in step 02's spec, keep whichever syncs better
**Decision:** "we can go with c": run both the ElevenLabs forced-alignment API and a local CPU
pipeline on one real song, and keep whichever syncs better. Test song: "Mere Samne Wali Khidki
Mein" (owner provides audio + lyrics).
**Decided:** 2026-09-26

### H-005 — Project plugins
**Status:** decided
**Raised:** 2026-09-26
**Needed-before:** scaffold
**Context:** `/scaffold` step 7. User-scope plugins: chisle, devsystem, frontend-design enabled;
mattpocock-skills disabled. This project has no UI.
**Decision:** "both yes": `.claude/settings.json` enables devsystem, disables frontend-design.
chisle left to the owner's user-level setting.
**Decided:** 2026-09-26

### H-006 — Move past step 01 before the CapCut import test
**Status:** decided
**Raised:** 2026-09-26
**Needed-before:** step 02
**Context:** Step 01's automated checks (AC1–5, AC9) pass. AC6–8 need the owner to import the
clips into CapCut desktop and mobile.
**Decision:** "abhi kiya hum ye maan ke chal sakte hai, ki capcut ka test pass hogya hai, and abhi
aage ka kaam chalu karte hai, mein baad mein import karke check karlunga." Treat step 01 as passed;
the owner runs the CapCut test later. Step 02 is output-format independent, so that is safe. The
test must be done **before step 03's spec**, because the renderer's output format depends on it.
**Decided:** 2026-09-26

### H-007 — Prototype on a 30-second clip; spec 02 approved
**Status:** decided
**Raised:** 2026-09-26
**Needed-before:** step 02 plan
**Context:** The test song file is 2:52. The owner pasted lyrics for the mukhda and the first
antara; the paste's first line was cut off mid-bracket ("Ek chaand ka tukda rehta hai) -(x2)").
**Decision:** "abhi prototype mein hum sirf 30 sec ka subtitle banyenge" and "isko likh do - and
aage ka kaam tum sambhalo". The bake-off runs on a ~30 s clip cut at line boundaries from where
the singing starts. Spec 02 is approved with that change. The lyrics are saved to
`songs/khidki_full/lyrics.txt` as authorised by the owner, with these formatting changes:
`(x2)` expanded, the cut-off first line restored as "Mere saamne waali khidki mein" (the owner's own
spelling from later in the paste), and blank lines between single lines removed (two stanzas kept).
**Decided:** 2026-09-26

### H-008 — Owner away: Claude continues autonomously
**Status:** decided
**Raised:** 2026-09-26
**Needed-before:** everything after step 02's integration
**Context:** The owner is unavailable while the bake-off and later steps run.
**Decision:** "agent ke khatam hote hi aage ka kaam bhi continue kardena mein avilable nhi hu,
isliye khud ka descion lena and kaam continue rakhna-- and agar aisa kuch hai jisme mera
permission chaiye tou usko pending mein rakh ke aage badhte raho." Claude makes reversible
decisions itself (logged as D- entries) and keeps working. Anything that needs the owner goes to
`pending_work.md` under "Waiting on the owner", and work continues around it. Still owner-only:
merging PRs (needs an explicit instruction), the CapCut import test (H-006), and final
confirmation of the bake-off winner by watching the previews (a provisional pick by objective
criteria is allowed).
**Decided:** 2026-09-26

### H-009 — How should emphasis words be marked?
**Status:** decided
**Raised:** 2026-09-26
**Needed-before:** emphasis styling in the renderer (step 03 ships without it)
**Context:** project_context puts "emphasis words marked by hand in `lyrics.txt`" in V1 scope. Red
line 2 says on-screen text matches `lyrics.txt` exactly, and the lyrics reader rejects brackets. A
marker inside `lyrics.txt` would be text that never appears on screen, so any option here touches
a red line. That makes it the owner's call.
**Options:** (a) `*word*` in `lyrics.txt`: asterisks mean emphasis and are never drawn, a documented
exception to red line 2; alignment ignores them. (b) `"emphasis": true` per word in `words.json`,
set by hand; lyrics stay pure, but a re-alignment needs the flag carried over. (c) No emphasis in V1.
**Recommendation:** (a). It is set once per song, survives re-alignment, and is obvious in a
text editor.
**Decision:** (a) `*word*` in `lyrics.txt`. The asterisks mark emphasis and are never drawn; this
is the one documented exception to red line 2 (project_context.md, CLAUDE.md, devsystem.json).
Alignment ignores them. Built in plan step 06.
**Decided:** 2026-09-26

### H-010 — Owner validated the first overlay
**Status:** decided
**Raised:** 2026-09-26
**Needed-before:** calling V1's base done; merging PRs #2 and #3
**Context:** H-008 left three checks to the owner: the aligner choice (D-009, provisional), the
Soft Romantic look, and the CapCut import (H-006, which fixes the default codec, D-011).
**Decision:** "maine check kar liya hai sab kuch shi hai". Sync by ear, look, and CapCut import are
all OK. L-vocals is confirmed as the default aligner (D-009), and ProRes 4444 `overlay.mov` is
confirmed as the default alpha codec (D-011). The look is kept as rendered, with no change such as
ghosting upcoming words. The ElevenLabs E-variants become optional: re-run them only if a song
aligns badly locally.
**Decided:** 2026-09-26

### H-011 — Which styles come first in V1.1?
**Status:** decided
**Raised:** 2026-09-26
**Needed-before:** plan step 06 (styling) and its `/spec`
**Context:** `docs/research/lyric_aesthetics.md` (2026-09-26) surveyed short-form lyric styles,
Hinglish conventions, fonts, palettes, CapCut's native limits and what the CPU/PIL pipeline can
animate. Findings that shape the choice: the "high-effort" look comes from per-word timing,
restraint and finish, not from more motion; six candidate themes all fit the current renderer;
Phonk / Beat Pop / Neon need a beat-onset list that `words.json` does not carry; Devanagari
lyrics would need a shaper (libass or harfbuzz), Latin Hinglish does not.
**Options:** (a) Soft Romantic v2 (blur-focus line stack, duration-following glow, one emphasis
move) → Karaoke Fill (pop) → Minimal Lowercase (lofi / sad status); no new inputs. (b) Start
with a beat-driven theme (Phonk or Beat Pop); needs a beat-detection step first. (c) Cinematic
Ivory (ghazal serif) as the second theme instead of Karaoke Fill.
**Recommendation:** (a). Three themes from the same alignment, the first one upgrades what the
owner already validated (H-010), and beat data becomes its own later step.
**Decision:** Pop Karaoke (the research's Karaoke Fill) is the first new theme; it becomes plan
step 07, after emphasis (step 06). The owner chose it from Pop karaoke / Phonk / Lofi / Minimal.
That question did not list Soft Romantic v2, so its place, and the order of later themes, is
still open; ask after step 07.
**Decided:** 2026-09-26

### H-012 — Build every researched style after Pop Karaoke
**Status:** decided
**Raised:** 2026-09-26
**Needed-before:** plan steps 08–14
**Context:** H-011 picked only the first new theme and left the rest open. After reading the
research (`docs/research/lyric_aesthetics.md`), the owner answered for the whole list.
**Decision:** "mein follow ke sath in sabhi ko bhi build kardunga": all researched styles get
built, one after another, after step 07: Soft Romantic v2, Lofi Minimal, Cinematic, beat
detection, Beat Pop, Phonk Neon, and Devanagari shaping when a song needs it. Save it in the plan
and context. The order is Claude's default (D-017); the owner can change it before any step starts.
**Decided:** 2026-09-26

### H-013 — Marked words are 1.5x-2x their line's other words, permanently
**Status:** decided
**Raised:** 2026-09-26
**Needed-before:** approving step 06's look (spec 06 AC10)
**Context:** The first build gave a marked word a 1.06x swell while sung (research §2: restraint).
On the `khidki_s2_em` preview the owner found it looked almost the same as every other word.
**Decision:** "mark words normal words se 2x ho ya 1.5x ho ... mostly permanent solution use
karo". A marked word is drawn 1.5x to 2x its line's font size for as long as the line is on
screen, and the layout makes room for it. The rule is enforced in `theme.py`: `emphasis_scale`
must be 1.5-2.0 (default 1.5 until the owner picks from the 1.5x and 2x previews). The swell is
dropped. Spec 06 v1.1.0. The owner then said "ok ab ship kardo" without asking for 2x, so
1.5x ships as the default (AC10); `emphasis_scale` can be raised up to 2.0 any time.
**Decided:** 2026-09-26

### H-014 — Soft Romantic v2: no waiting next line; v2 sits beside v1
**Status:** decided
**Raised:** 2026-09-27
**Needed-before:** spec 08 (Soft Romantic v2)
**Context:** Plan step 08 left two calls to the owner: whether the research's blurred "waiting
next line" ships (H-010 kept "no ghosting"), and whether v2 replaces v1 or sits beside it.
**Options:** Next line: (a) keep H-010, upcoming words stay hidden until sung; (b) show the next
line blurred at low opacity below the current one. v1: (a) v2 is a new theme beside v1; (b) v2
takes over the `soft-romantic` name.
**Recommendation:** (a) and (a).
**Decision:** Next line: "Nahi, H-010 hi rahe". No waiting next line; only the current line and
the dimmed, blurred past line above it. v1 vs v2: "Saath mein, alag naam". v2 ships as a new
theme `soft-romantic-v2`; v1 stays pixel-identical and stays the default until the owner prefers
v2 (spec 08).
**Decided:** 2026-09-27

### H-015 — Soft Romantic v2 becomes the default theme
**Status:** decided
**Raised:** 2026-09-27
**Needed-before:** shipping step 08 (spec 08 AC10)
**Context:** The owner compared the v2 and v1 previews of `khidki_s2_em` (H-014 kept v1 as the
default until then).
**Decision:** "yes v2". `render` and `make` now default to `soft-romantic-v2`
(`theme.DEFAULT_THEME`); v1 stays available as `--theme soft-romantic`.
**Decided:** 2026-09-27

### H-016 — Lofi Minimal: the line shows ahead; typewriter is its own theme
**Status:** decided
**Raised:** 2026-09-27
**Needed-before:** spec 09 (Lofi Minimal)
**Context:** Plan step 09 lists sung / current / upcoming colour states, which means showing a line
before its words are sung. H-010 and H-014 kept upcoming words hidden in Soft Romantic. The plan
also lists an optional typewriter without saying how it is picked.
**Options:** Upcoming: (a) the whole line shows ahead, dim, and each word changes colour as it is
sung; (b) words appear only when sung, as Soft Romantic. Typewriter: (a) a separate theme
`lofi-typewriter`; (b) a `theme.py` switch, off by default; (c) skip it in step 09.
**Recommendation:** (a) and (a).
**Decision:** "Line pehle dim dikhe" and "Alag theme lofi-typewriter". In `lofi-minimal` the line
shows ahead in a dim upcoming state (this theme only; H-010 and H-014 still hold for Soft
Romantic). The typewriter ships as a second theme, `lofi-typewriter`, picked with `--theme`.
**Decided:** 2026-09-27

### H-017 — Cinematic: couplets (sher), words appear as sung
**Status:** decided
**Raised:** 2026-09-27
**Needed-before:** spec 10 (Cinematic)
**Context:** Plan step 10 names a blur-in reveal but not what the screen holds. Research §9 says
ghazal edits use "generous line spacing, poem-like centring", and the test song's four lines are
two couplets. Lofi Minimal (H-016) shows its line ahead; Soft Romantic does not (H-010, H-014).
**Options:** Layout: (a) couplets: a stanza's lines in pairs, the first stays while the second
reveals below it, then both leave together; (b) one line at a time, as Lofi. Reveal: (a) a word is
hidden until sung, then blurs into focus; (b) rack focus: the line shows ahead dim and blurred,
each word pulls into focus as sung.
**Recommendation:** (a) and (a).
**Decision:** "Sher (couplet)" and "Jab gaaye jaayein". Lines of a stanza (blank lines in
`lyrics.txt` split stanzas) show in pairs, 1+2, 3+4; a leftover line shows alone. No word shows
before it is sung; each blurs in on its own time.
**Decided:** 2026-09-27

### H-018 — Beat detection: librosa, beats in their own `beats.json`
**Status:** decided
**Raised:** 2026-09-27
**Needed-before:** spec 11 (beat detection)
**Context:** Plan step 11 leaves the library and the storage open. `aubio` has no Windows wheel
on PyPI (source only, needs an MSVC build) and is GPL-3.0. D-001 makes `words.json` the only
contract between stages.
**Options:** Library: (a) `librosa` (wheels for every dependency; beats, onsets, tempo; no
downbeats), (b) `beat_this` (neural, torch, beats + downbeats, GitHub install, weights licence to
check), (c) try both and keep the better, (d) own numpy code. Storage: (a) a separate
`songs/<song>/beats.json`, (b) inside `words.json`.
**Recommendation:** (a) and (a).
**Decision:** "librosa (Recommended)" and "Alag beats.json (Recommended)".
**Decided:** 2026-09-27

### H-019 — Beat Pop: line bump on every beat, owner-written drops, words pop as sung, mustard pill
**Status:** decided
**Raised:** 2026-09-28
**Needed-before:** spec 12 (Beat Pop)
**Context:** Plan step 12 names word pops, a highlight pill and an optional shake on drops, and
says pops "land on the beat". Red line 1 keeps every word on its own aligned time, so beats can
only drive decoration. `beats.json` (step 11) has beats, no drops.
**Options:** Beat motion: (a) the on-screen line bumps ~5% on every beat, pill with it, (b) the
same on every other beat, (c) only the pill pulses, (d) nothing, beats only for drops. Drops:
(a) the owner writes times in `songs/<song>/drops.txt`, each snapped to the nearest beat,
(b) auto-detected from loudness, (c) no shake in this step. Words: (a) each pops in
(`easeOutBack`) as sung, nothing shown ahead, (b) the line shows ahead dim and each word pops to
full as sung. Pill: (a) mustard `#FFC107` with the sung word in black, (b) red `#E53935` with the
word in white.
**Recommendation:** (a), (a), (a), (a).
**Decision:** "Line bump har beat", "Main times likhunga", "Gaate hi pop", "Mustard pill, kaala
word".
**Decided:** 2026-09-28

### H-020 — Phonk Neon: Pirata One, purple, RGB split on drops, neon-sign word lighting; faster flow
**Status:** decided
**Raised:** 2026-09-28
**Needed-before:** spec 13 (Phonk Neon)
**Context:** Plan step 13 leaves the display face (blackletter or wide bold), the glow colour and
the drop effect to the owner; words must still appear only at their own aligned time (red line 1)
and keep the casing of `lyrics.txt` (red line 2). A look sheet (`songs/phonk_neon_looks.png`)
showed three OFL faces, four colours and two drop effects. The owner also wanted a faster flow.
**Options:** Font: (a) Pirata One (readable blackletter), (b) UnifrakturCook (heavy blackletter,
"k" reads as "f"), (c) Russo One (wide bold). Colour: (a) purple `#BE46FF`, (b) hot pink, (c)
cyan, (d) red. Drop: (a) RGB split + shake, (b) white flash + shake, (c) both + shake. Words:
(a) the line shows as a dim unlit tube and each word flickers on and stays lit as sung, (b) each
word flickers on as sung, nothing ahead, (c) the whole line lit, the sung word brighter.
Flow: after these answers Claude writes spec, plan and code in one run with no approval stop
between them; the owner approves the finished look.
**Recommendation:** (a), (a), (a), (a); the one-run flow.
**Decision:** "A Pirata One", "Purple", "RGB split + shake", "Neon sign: dim → jalta hai"; the
one-run flow was stated and not objected to.
**Decided:** 2026-09-28

### H-021 — Title card: top of the frame for the first ~3 s, in each theme's own look
**Status:** decided
**Raised:** 2026-09-29
**Needed-before:** spec 15 (Title card)
**Context:** The owner picked the title card as the next step after step 13. Claude stated the
text source up front: `songs/<song>/title.txt`, drawn exactly as written (one or two lines, any
separator, emoji or film name); no file, no card; `clip` copies it. Not objected to.
**Options:** Placement: (a) top, fade in and out over the first ~3 s, (b) top, the whole video,
(c) centre, during the intro before the first lyric line. Look: (a) each theme's own font, colours
and legibility layer, smaller, (b) one common white sans card for every theme.
**Recommendation:** (a), (a).
**Decision:** "Upar, shuru ke ~3 s", "Har theme ka apna".
**Decided:** 2026-09-29

### H-022 — North star: the lyric styling itself is the content
**Status:** decided
**Raised:** 2026-09-29
**Needed-before:** any work after V1 (styling variety, backgrounds)
**Context:** With V1 complete, the owner stated what the channel is for. The shorts must be
watchable for the lyric styling alone: the song plays, the words are so well made that people
just watch. Money comes from ad revenue and sponsors, so the measures are followers and watch
time. The owner wants variety in colours and fonts, and something other channels do not have.
**Decision:** "hum apne lyrics style quality ke bharose ek content bana sake, aisa chaiye ki log
addictive ho jaye ... jab wo screen pe play hoga background mein song chalega tou log just
dekhe usko."
**Decided:** 2026-09-29

### H-023 — Backgrounds: engine-made scenes matched to the song's vibe (scope change: finished video)
**Status:** decided
**Raised:** 2026-09-29
**Needed-before:** spec for the background step
**Context:** The owner wants a background that is not the usual image or stock video under a
song ("sab log song lagake video upload kar rahe hai, apne ko kuch alag chaiye"). V1 only makes
a transparent overlay; a background means the engine renders the finished short (background +
text + audio), which `project_context.md` lists as out of scope for V1.
**Options:** Claude first offered (a) an abstract audio-reactive background in the theme's
palette, (b) the lyrics themselves as the background, (c) both, (d) overlay only. The owner
turned these down for scenes that carry a vibe.
**Decision:** "aisa background socho jo different types of song hai uspe suit ho sake, and songs
ka apna ek vibe hota hai wo match ho sake. ex: ek silhouette type kuch, space type kuch, ek
peaceful types, ek 90s type kuch, anything. agar tumhe uske liye custom code, koi tool use karna
pade tou karenge: koi python library, koi ai generation tool etc"
**Decided:** 2026-09-29

### H-024 — Which background looks to build first
**Status:** decided
**Raised:** 2026-09-29
**Needed-before:** spec for the background step
**Context:** Two look sheets for H-023, review only, on `khidki_s2_em` with lyrics and audio,
drawn with numpy and PIL (tool research: `docs/research/background_tools.md`).
Sheet 1, `songs/_review/backgrounds/` (`bg_looks.py`): the owner's four example vibes as scenes.
Owner's verdict: "background acha tou hai, and har type ke songs se category se match bhi hoga.
but tumne tou wahi kiya jo maine example mein bola tha ... is type ke background tou most common
hai. creativity banao ... user ki perspective se socho, ek artist ki perspective se socho."
Sheet 2, `songs/_review/backgrounds/ideas/` (`bg_ideas.py`): backgrounds the song itself drives.
Each reads every word's time and on-screen box (from `words.json` and the theme's layout), the
beats and the `*marked*` words, which a stock background under a song cannot do.
Found while making them: a scene's props must stay outside the theme's lyric block; Pop
Karaoke's block (past line plus current line) is too tall to leave room for a cassette.
**Options:** Sheet 1, scenes by vibe: (a) Silhouette, (b) Space, (c) Peaceful, (d) 90s VHS.
Sheet 2, song-driven: (e) Lakeer: a pen of light underlines each word as it is sung, swoops to
the next and circles a marked word; (f) Boond: each word falls into still water as a drop at
its own place, held words keep dropping, the first marked word brings the moon out; (g) Rangoli:
a rangoli drawn ring by ring on the beats around the lyric block, finished on the last word, a
diya lit by each marked word.
**Recommendation:** Song-driven first ((e)–(g)); sheet 1's scenes later as settings those
behaviours run in.
**Decision:** None of the seven: "mujhe ek bhi background acha nhi laga ... songs se match hona
chaiye ... song ke vibe se. tou hum abhi romantic songs pe kaam karenge." Claude then proposed,
for romantic songs, a sunlit empty room: warm wall, jaali and money-plant shadows, dust in the
light, a dupatta on a chair; the lyrics sit in the sunlight and cast a faint shadow on the wall;
the light moves from gold to rose to dusk over the song and a small lamp comes on at the last
line. Owner: "mujhe tumhara ye idea kafi pasand aaya." Constraint: "background re-usable rahena
chaiye, uspe kal ko mein koi bhi lyric laga pau."
**Decided:** 2026-09-29

### H-025 — Romantic room: one room with moods, or several backgrounds
**Status:** decided
**Raised:** 2026-09-29
**Needed-before:** spec for the room background
**Context:** H-024 picked the sunlit room for romantic songs; the owner asked whether it covers
every romantic vibe or needs more backgrounds, and it must take any lyric.
**Options:** (a) one room with a set of moods (time of day, weather, light colour, props) picked
per song like a theme; the lyric area on the wall stays in the same place in every mood;
(b) separate backgrounds per vibe.
**Recommendation:** (a) with six moods: morning (new love), golden afternoon to dusk (longing,
the default), rainy evening (heartbreak), moonlit night (intimate), misty winter morning (calm
love), festival night (wedding and celebration). The room only reads song length, word times and
beats, never the words themselves, so any lyric fits. Small seeded changes per video (plant,
curtain print, props) keep repeats fresh. Out of its range: fast party or dance romance, which
stays with Beat Pop / Phonk Neon.
**Decision:** (a), the six moods as recommended: "ok, tou chalo romantic type song ke liye
background final hogya hai, isko ek .md file mein save kro." Saved as
`docs/backgrounds/romantic_room.md`.
**Decided:** 2026-09-29

### H-026 — Hip-hop background: the truck's back, one truck with moods
**Status:** decided
**Raised:** 2026-09-29
**Needed-before:** spec for the truck background
**Context:** Second song type after romantic (H-025). Claude proposed the back of a hand-painted
truck on a highway: bars in the centre panel where a truck carries its painted line, the truck
bouncing on the beats, a horn and headlight flash on punchlines, smoke on drops; five moods;
alternatives were a Mumbai local's window at night and a rapper's notebook.
**Decision:** "ok hip-hop final, save karo, next song type pe chalo." Saved as
`docs/backgrounds/hiphop_truck.md`.
**Decided:** 2026-09-29

### H-027 — Party and dance background: the baraat's lights, one baraat with moods
**Status:** decided
**Raised:** 2026-09-29
**Needed-before:** spec for the baraat background
**Context:** Third song type, picked by Claude because the romantic room leaves out fast party
and dance songs. Claude proposed a night baraat: paper-cut silhouettes of light-bearers and the
band, glowing lamps bouncing on the beats, a rocket on marked words, anaar fountains on drops,
the lyrics in the open sky; five moods; alternatives were a fair's giant wheel and the view up
from a shamiana dance floor. Claude also suggested one art style across all backgrounds (not
objected to), and posting one genre family (romantic) on the channel first while the engine
covers the rest (no answer yet).
**Decision:** "ok party final, save karo, next song type pe chalo." Saved as
`docs/backgrounds/party_baraat.md`.
**Decided:** 2026-09-29

### H-028 — Sufi and devotional background: the lamp in the niche, one lamp with moods
**Status:** decided
**Raised:** 2026-09-29
**Needed-before:** spec for the lamp background
**Context:** Fourth song type, picked by Claude. Claude proposed one world for both Sufi and
devotional songs: a clay lamp in an arched niche of an old wall, incense smoke, a golden moth
circling closer line by line and entering the flame on the last line; the lyrics lit by the
flame; no images of gods, holy books or saints; five moods; alternatives were a dervish's whirl
seen from above and a white cloth taking on colour line by line.
**Decision:** "ok, i like thats save it." Saved as `docs/backgrounds/sufi_chiraag.md`.
**Decided:** 2026-09-29

### H-029 — Song types still without a background
**Status:** decided
**Raised:** 2026-09-29
**Needed-before:** the next background discussion
**Context:** Four worlds are approved (H-025 to H-028), none built. Several other song types are
already covered by those worlds' moods: romantic heartbreak and lofi / slowed songs (room: rainy
evening, moonlit night), indie and acoustic (room), ghazal (lamp or the room at night), phonk
(truck, night highway), Holi and festival songs (baraat, room).
**Options:** Still without a world: (a) motivational (gym, sport, struggle), (b) journey:
friendship, travel and life songs, (c) mother and family, including vidaai, (d) patriotic,
seasonal (26 January, 15 August); optional (e) old classics as an "old times" mood of the room.
**Recommendation:** Build the romantic room's default mood first and design the rest after it,
since the first build will teach things every design needs (look, text integration, render
time). Then design order (b), (a), (c), with (d) before 26 January 2027.
**Decision:** Design every type before building: "nhi baki ke types bhi final karte hai. abhi
sirf motivational and safar ke background ko batao, baki ke 3 pending mein daal do." Now: (a)
and (b). Waiting: (c) mother and family, (d) patriotic, (e) old classics.
**Decided:** 2026-09-29

### H-030 — Motivational background: the blacksmith's forge, one forge with moods
**Status:** decided
**Raised:** 2026-09-29
**Needed-before:** spec for the forge background
**Context:** Fifth song type (H-029). Claude proposed a blacksmith's forge in the dark: a hammer
(only its shadow) strikes the red-hot iron on every beat with a burst of sparks, the iron takes
shape line by line and is quenched in steam on the last line ("tap ke hi sona kundan banta hai");
five moods; alternatives were a stepwell climbed one step per beat and a 4 AM study desk.
**Decision:** The owner left the pick to Claude: "ok, tumhe jo best lagta hai usko save kardo
and next session ki tayri hum in sabhi ko next session mein banyenge." Claude's pick: the forge.
Saved as `docs/backgrounds/motivational_forge.md`.
**Decided:** 2026-09-29

### H-031 — Journey background: the train's open door, one train with moods
**Status:** decided
**Raised:** 2026-09-29
**Needed-before:** spec for the train background
**Context:** Sixth song type (H-029): friendship, travel and life songs. Claude proposed the view
from a moving train's open door: poles passing on every beat, birds rising on marked words, a
tunnel and a river bridge on a drop, the sea on the last line; five moods; alternatives were
kite flying from a rooftop ("kai po che") and a painted travel journal.
**Decision:** Left to Claude, as in H-030. Claude's pick: the train door. Saved as
`docs/backgrounds/journey_train.md`. The owner also said all the approved backgrounds are to be
built from the next session on.
**Decided:** 2026-09-29

### H-032 — Romantic backgrounds: the room is out; three light looks (rain, fog, drive)
**Status:** decided
**Raised:** 2026-09-29
**Needed-before:** the step 17 rebuild
**Context:** The room was built (step 17, PR #16). The owner watched the finished short and
rejected it: "ye aisa background tha jis mein 1 sec mein skip kardu". Claude's own read:
- the frame was dim;
- nothing moved in the first second;
- the drawn props looked like clip-art;
- and the process was wrong: the whole pipeline was built before the owner saw a 10-second
  sample.
The owner then asked for a rare motion background with great colours. Claude's first answer,
flowing gradients, was a known pattern, and the owner called that out. The owner refined it:
small lights that react to the beat or the words, and a look that depends on the song type.
Mockups of lanterns, raindrops and fireworks as small lights were rejected ("ye diwali wagera
wala look mat do kids wala"). Three full-frame light worlds followed
(`songs/_review/backgrounds/lights2/`).
**Decision:** Rules for every background: "pura frame dekho screen ka ... overall screen use Karo.
Just remember one rule -- light feel hona chaiye na ki aankho ko chube", and, on the rain
mockup, "depth nhi hai, jaihse lag raha hai sab surface level pe hi hai". Final pick: "ok, ab ek
kaam karte hai ye 3 theme ko final karte hai, romantic type vibe ke liye". Saved as
`docs/backgrounds/romantic_lights.md`; the room's file is marked rejected.
**Decided:** 2026-09-29

### H-033 — The other five backgrounds under H-032's rules
**Status:** pending
**Raised:** 2026-09-29
**Needed-before:** step 18
**Context:** The hip-hop truck, party baraat, Sufi lamp, motivational forge and journey train
(H-026 to H-031) were designed the way the room was: painted scenes with props. The baraat also
uses rockets and anaar fountains. H-032's rules point away from that: felt light, the whole
screen, depth, nothing festive or childish.
**Options:**
- (a) Redesign each as a light world under H-032's rules before its step.
- (b) Build them as designed.
- (c) Decide per world when its step comes.
**Recommendation:** (a), after the romantic looks are built, since seeing them move will show
what works.

### H-034 — The rain look is final
**Status:** decided
**Raised:** 2026-09-29
**Needed-before:** building the rain look into the engine (step 17)
**Context:** Rain samples on `khidki_s2_em` (H-032).
- The first, a rainy window with a defocused city: "isko drop kardo ... lyric clearly dikhna
  chaiye".
- The second, rain in a streetlight's cone at night: "rain ko slowly girwa and usme ka colour
  hata do, jab wo jamin pe niche gire tab usme (jamin) se ek colur nikle ... theme dark mat rakho
  puri tarha se thoda sa light theme do".
- The third: slow colourless rain on a soft overcast evening, where colour rises out of the wet
  ground as each drop lands and each sung word lands a bigger bloom.
**Decision:** "ok ab ek kaam karo ye video ko final kardo and just aasman mein thode cloud add
kardo, and kuch bhi mat change karna". A few soft drifting clouds were added and nothing else
changed. Final sample: `songs/_review/backgrounds/lights2/rain_final.mp4`; described in
`docs/backgrounds/romantic_lights.md`.
**Decided:** 2026-09-29

### H-035 — The fog look is final, in moonlight
**Status:** decided
**Raised:** 2026-09-29
**Needed-before:** building the fog look into the engine (step 17)
**Context:** Fog samples on `khidki_s2_em` (H-032):
- First, gold light through fog. The owner asked for shading, a dark lower part, and more
  light where the fog comes in, fading lower down: "bas aisa feel ho ki ha ye shadow hai ek fog
  hai".
- That version became the base. The owner then asked for a different, peaceful colour
  combination and a slightly darker theme.
- Four palettes were shown as stills: moonlight, lavender, mint, dawn. Moonlight and lavender
  were shown as videos.
**Decision:** "chaandni wala final kardo, and baki ke delete kardo". The other samples were moved
to `songs/_review/_trash/fog_drafts/`. Final sample:
`songs/_review/backgrounds/lights2/fog_final.mp4`; described in
`docs/backgrounds/romantic_lights.md`.
**Decided:** 2026-09-29

### H-036 — The third romantic look: drive dropped, milan (the owner's idea) final
**Status:** decided
**Raised:** 2026-09-29
**Needed-before:** building the romantic looks into the engine (step 17)
**Context:** The drive look had two tries:
- first down the road ahead;
- then through the side window, which the owner asked to make "ekdum dark", with the top light
  "bahut chota" and the bottom only a soft blur.
The owner then dropped it: "ye template ko drop kardo, iski jagha kuch aur socho". The owner
proposed drifting dots that leave a faint light where they collide, moving "not forcefully". The
owner asked for Claude's idea if theirs did not work. Claude kept the owner's idea, since meeting
and light suits romance, and added three things:
- a smooth random wander;
- meetings timed to the marked words, near the word;
- faint memories of each meeting.
**Decision:** after "thoda dark hi vibe ... ek dum halka sa na dark border" and "dots ko thoda
bada and clearly visibe banao, lekin usme lighting mat do jab wo takrye tabhi lighting aaye":
"ok isko final karo". Final sample: `songs/_review/backgrounds/lights2/milan_final.mp4`;
described in `docs/backgrounds/romantic_lights.md`. The drive tries are in
`songs/_review/_trash/drive_drafts/`.
**Decided:** 2026-09-29

### H-037 — Sad songs: which idea, and where the images come from
**Status:** decided
**Raised:** 2026-09-29
**Needed-before:** the sad-song background
**Context:** The owner rejected the dot concepts for sad songs ("ye template hi bekar hai ... ye
kiya tum kachra idea de rahe ho"). The owner allowed images ("tum image wagera bhi use kar sakte
ho") and asked for ideas from several perspectives, now a CLAUDE.md rule.
**Options:**
- (1) "Khaali jagah": an empty place that once held two people, with a slow 2.5D push-in; cold
  and grey, turning warm for a moment on each marked word; the streetlight goes out on the last
  line.
- (2) "Purani tasveer": an old faded photo that bleaches away over the song.
- (3) "Aakhri train": an empty station at night; a train's light passes on the beat.
Image source:
- (a) AI stills, via a fal key in `.env`, about ₹1–3 each;
- (b) free stock (Pexels, Pixabay).
**Recommendation:** (1) with (a).
**Decision:** The owner has no AI subscription: "ye image tum hi banao". Images are drawn by code
(night, fog, light, silhouettes). Of three drawn scenes the owner picked (1), "Khaali jagah":
"first image ko final karo". An empty bench under a streetlight in the rain; for a moment warm on
each marked word; the light goes out on the last line. Stills:
`songs/_review/backgrounds/sad/khaali_jagah_final.png` (present) and
`khaali_jagah_yaad_final.png` (the memory moment), drawn by `sad_scenes.py`. The owner asked for
two more sad ideas "couple wagera pe".
**Decided:** 2026-09-29

### H-038 — Which template ideas to draw for each song type
**Status:** decided
**Raised:** 2026-09-29
**Needed-before:** stills and moving samples for the next song types
**Context:** The owner asked for background agents to find 3 templates per song type, each
questioned hard before it is returned. The types:
- romantic and sad again;
- hip-hop, party, Sufi, motivational, journey, family, patriotic and old classics.
33 ideas came back, reviewed by Claude, in `docs/backgrounds/template_ideas.md`.
**Options:** the 3 per type in that document.
**Recommendation (★):**
- Taaron ka jaal (hip-hop); Naachta fawaara (party); Jaali se subah (Sufi);
- Seedhi dar seedhi (motivational); Pahadi raasta (journey); Jaagti khidki (family);
- Dharti ki lehar (patriotic); Purani Talkies (classics);
- Chaand ka ghoonghat (romantic); Aakhri patta (sad).
Also one cloth test before any dupatta, saree or veil idea is chosen, and one moving sample
before any idea with animated human shadows.
**Decision:** the owner took the picks as proposed ("template final hai") and asked for them to be
built: Khaali jagah and Aakhri patta (sad), Chaand ka ghoonghat (romantic), Rail ki Seeti
(classics), Taaron ka jaal (hip-hop), Jaali se subah (sufi), Shamiyane ki parchhaiyan (party),
Parchhaiyan (family). Journey, motivational and patriotic wait (all rated 5 or lower).
**Decided:** 2026-10-01

### H-039 — Rain in the engine: a calmer patch behind the lyrics?
**Status:** decided
**Raised:** 2026-09-29
**Needed-before:** merging step 17 (PR #16)
**Context:** The approved rain video was finalized with "kuch bhi mat change karna". In the
engine, the legibility check (3:1 around the text, D-030) failed on it: where the second lyric
row sits near the bright horizon mist, the contrast falls to 2.4:1 (187 of 420 frames on
`khidki_s2_em`). Thin rain streaks are not the cause; the broad brightness near the horizon is.
**Options:**
- A: the calmer patch (engine default now): the dark patch behind the lyrics is half, not a
  third, and reaches lower; the rest of the frame is unchanged. Lowest contrast about 3.2:1.
- B: exactly as approved; the check's minimum for rain is lowered to 2.4:1, recorded here.
**Recommendation:** A. The owner's first note on rain was "lyric clearly dikhna chaiye"; the
change is only behind the text and the frame stays light. Comparison stills:
`songs/_review/backgrounds/lights2/rain_calm_compare.png`.
**Decision:** A, the calmer patch. The owner handed the call to Claude on 2026-10-01 ("tumhe jo best lage usko final karo"); Claude kept A for the owner's first rain note, "lyric clearly dikhna chaiye".
**Decided:** 2026-10-01

### H-040 — The owner hands the look approval to Claude
**Status:** decided
**Raised:** 2026-10-01
**Needed-before:** merging step 17 (PR #16)
**Context:** Six looks were built (rain, fog, milan, khaali, aakhri, chaand) and waited for the
owner's approval (spec 17 AC11). The owner: "tumhe jo best lage usko final karo, and ek baar last
check karo ki sab acha bana haina".
**Options:** approve all six; approve the four from owner-seen samples and hold aakhri and chaand.
**Decision:** Claude approved all six after a last check of every finished short (frames at the
start, middle, last line and end; every check passes, lowest contrast 3.15:1 or more). Known
issues stay recorded in each look's doc (aakhri: spiky bare twigs, a smudge-like near leaf; chaand:
smooth tree domes, subtle peeks with few marks) and are the first fixes if the owner objects on
seeing them.
**Decided:** 2026-10-01


### H-041 — Keep the system simple; lyric fixes stay generic
**Status:** decided
**Raised:** 2026-10-01
**Needed-before:** any lyric-style fix for romantic and classics songs
**Context:** A frame-by-frame review of `soft-romantic-v2` and `cinematic` on the khidki_30s
finals found why the lyrics feel "forceful" (bold font, pink per-word glow, 0.2 s pops, a jerky
hand-over, a smudged past line, the first word hanging alone at the left, and more). Claude
proposed new romantic and classics lyric themes.
**Decision:** "ye system ko complex mat karo, simple rakho". The goal is about 3 templates per
song type, with any song of that type added on them. Lyric fixes change only the lyric themes,
never the templates, and must work for any lyrics, not just khidki. Saved as an owner rule in
`CLAUDE.md`. Claude dropped three proposals as extra complexity (glow colour taken from the
background, breath-based line breaks, a held-word swell) and assumes: left-aligned lines (H-010
kept, no ghosted upcoming words) and emphasis kept at 1.5x (H-013 kept). Building waits for the
owner's go-ahead.
**Decided:** 2026-10-01

### H-042 — Romantic and classics lyric themes approved
**Status:** decided
**Raised:** 2026-10-01
**Needed-before:** using the new lyric themes for videos
**Context:** Samples of `romantic-soft` (on chaand) and `classic-sher` (on rail), each beside
`soft-romantic-v2` on the same clip: `songs/_review/lyric_fix/*_pehle_vs_ab.mp4` (D-038).
**Decision:** "acha laga, dono themes pakki karo aur commit kardo". Both themes ship as built.
The old themes stay; `soft-romantic-v2` stays the default.
**Decided:** 2026-10-01
