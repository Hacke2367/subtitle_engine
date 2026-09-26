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
