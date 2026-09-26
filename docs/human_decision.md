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
