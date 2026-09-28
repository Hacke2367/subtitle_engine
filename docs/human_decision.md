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
