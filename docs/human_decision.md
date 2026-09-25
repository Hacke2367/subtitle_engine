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
**Status:** pending
**Raised:** 2026-09-26
**Needed-before:** step 02 (word alignment)
**Context:** Step 02 needs per-word timings for known lyrics (forced alignment). No GPU, but the
owner accepts ~10 min per song, so a local CPU pipeline is viable alongside a paid API. The owner
likely has an ElevenLabs account already (used for TTS by `C:\MANIM_VIDEOS_CODE_TEMPALTE`).
Accuracy on sung, romanized Hindi is unknown for every option.
**Options:** ElevenLabs forced-alignment API (paid, easy) / local: vocal isolation + open
alignment model (free, slower, more setup)
**Recommendation:** try both on one real song in step 02's spec, keep whichever syncs better
**Decision:**
**Decided:**

### H-005 — Project plugins
**Status:** decided
**Raised:** 2026-09-26
**Needed-before:** scaffold
**Context:** `/scaffold` step 7. User-scope plugins: chisle, devsystem, frontend-design enabled;
mattpocock-skills disabled. This project has no UI.
**Decision:** "both yes": `.claude/settings.json` enables devsystem, disables frontend-design.
chisle left to the owner's user-level setting.
**Decided:** 2026-09-26
