# Owner Decisions and Open Questions (V2)

`Status: pending` = waiting on the owner. Entries never move or get renumbered. V2 numbers from
H-101 so it never collides with V1's `../docs/human_decision.md` (H-0xx).

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

### H-101 — V2 scope: voice → Hinglish SRT, open source, own system
**Status:** decided
**Raised:** 2026-09-28
**Needed-before:** V2 `/scaffold` and first spec
**Context:** V2 runs beside the V1 track in the same repository. The owner first pitched voice
in, aesthetic animated subtitles out, with an LLM choosing style, emphasis and animation and a
render → LLM-critique loop, plus a website. Market check: hosted Hinglish caption tools exist
(Kalakar and others); open-source caption tools exist (pycaps, video-use, Capite) but are
English-centric and visual. `/kickoff` then reshaped it.
**Options:** Per question, as asked in the kickoff: wrong words: auto then edit / review first /
LLM fixes; core: SRT file / file + overlay / `.ass`; language: Hinglish + English Roman / Hinglish
only / Roman + Devanagari / any; LLM: breaks + punctuation / + emphasis / no LLM; milestone: CLI
then local web / local web now / hosted site.
**Recommendation:** the first option each time.
**Decision:** "hum apna system khud banayenge" (not built on pycaps); open source; "Auto, edit
baad mein"; output "sirf .txt jaisa kuch… wo usko video mein import kar lega", voice only (no
video: upload time); SRT core ("option 1 acha hai"), up to 1 hr of voice, processed in parts,
cues "per sentence", a break "jahan user ne pause liya"; Hinglish + English in Roman; LLM does
breaks + punctuation only; CLI first, local web after. Record: `docs/project_context.md`.
**Decided:** 2026-09-29

### H-102 — V2 structure: `v2/` subproject, standard tier, devsystem only
**Status:** decided
**Raised:** 2026-09-29
**Needed-before:** any V2 code
**Context:** `/scaffold`. V1's track had just removed V2 notes from its own tracking docs, and
devsystem reads its config from the session's launch folder only.
**Options:** Structure: (a) `v2/` subproject with its own package, docs and devsystem config,
(b) new modules inside `src/lyric_engine/` with shared docs, (c) a separate repository. Config:
standard tier, H-101's four red lines, empty gate until the first test / full tier now. Plugins:
devsystem only / devsystem + frontend-design.
**Recommendation:** (a); standard tier with an empty gate; devsystem only (frontend-design at
milestone 2).
**Decision:** "B: v2/ subproject", "Haan, aisa hi", "Sirf devsystem". V2 sessions launch from
`v2/`; V1 files are never touched from V2; `full` tier at the first public release.
**Decided:** 2026-09-29

### H-103 — Code licence
**Status:** pending
**Raised:** 2026-09-29
**Needed-before:** first public release (not blocking milestone 1)
**Context:** H-101 makes V2 open source. The licence decides what others may do with the code.
**Options:** (a) MIT: shortest, anyone may do anything, including closed commercial use.
(b) Apache-2.0: as permissive, plus an explicit patent grant; longer. (c) GPL-3.0: derivatives
must stay open source.
**Recommendation:** (a) MIT, the norm among the caption tools found (pycaps, video-use, Capite).
**Decision:**
**Decided:**

### H-104 — Test audio from the owner
**Status:** pending
**Raised:** 2026-09-29
**Needed-before:** spec 01 acceptance (transcription engine choice)
**Context:** The Roman-Hinglish risk can only be judged on the owner's real voice.
**Options:** —
**Recommendation:** one 30–60 s Hinglish voice clip first; one 30–60 min recording by step 02.
Recordings go in `v2/voices/` (gitignored).
**Decision:** Partly answered on 2026-10-03: the owner pointed at `C:\youtube_cut_shorts\out`
for test videos, and spec 00 was measured on two clips from there (33 s Hindi, 38 s English).
Still needed: the owner's own voice (their recording conditions are not a studio podcast), and a
30-60 min recording before step 02.
**Decided:**

### H-105 — Light version first: a 30–40 s video in, subtitles out
**Status:** decided
**Raised:** 2026-10-03
**Needed-before:** spec 00 and its branch
**Context:** H-101 settled V2 as voice in (no video, because of upload time) and an hour of
audio. The owner then asked for a light version first, and left the session to build it.
**Options:** —
**Recommendation:** —
**Decision:** "ye apna version2 ka light version hai, apna goal simple hai — mein input mein 30
ya 40 sec ka video dunga wo usme se audio extract karega — and mujhe wo subtitle dega. thats
it." Video in is allowed because the audio is extracted on the laptop with ffmpeg and only that
small audio file is uploaded, so H-101's upload-time reason does not apply. The hour-long path
(step 02) and the LLM step (05) stay in the plan, after this. Branch `feature/v2-video-subs`,
spec `docs/specs/00_video_to_srt.md`.
**Decided:** 2026-10-03

### H-106 — Is the rules romanization good enough, or should an LLM polish it?
**Status:** pending
**Raised:** 2026-10-03
**Needed-before:** step 05 (LLM breaks), and the first public release
**Context:** Scribe writes Hindi in Devanagari; `roman.py` rewrites it by rules (D-104). It is
right on the words it was tested on, but a few come out in a spelling the owner may not type:
`isilie` where most people write `isliye`, `dusri` for `doosri`, `jina` for `jeena`, `priy` for
`priya`. Sentences also start lowercase, because only the engine's English words carry capitals.
**Options:** (a) keep the rules as they are and fix the odd word in the transcript by hand;
(b) add spellings for the common words to the table as the owner spots them; (c) step 05's LLM
pass also fixes spelling and capitalization, which needs an LLM key (and would then have to be
checked word by word against the transcript, red line 1).
**Recommendation:** (b) now, (c) at step 05 — the owner marks the words that read wrong in the
first few videos, and those go into the table; the LLM decides breaks, punctuation and
capitalization once a key exists.
**Decision:**
**Decided:**

### H-107 — The signature subtitle style
**Status:** pending
**Raised:** 2026-10-03
**Needed-before:** making videos with the styled subtitles
**Context:** The owner asked for premium subtitles, a signature style and font, the spoken word
highlighted, so viewers do not skip ("tumne jo subtitle diya hai agar mein ye use karunga tou
log skip kar denge"). Built: three looks, side by side on the same clip
(`v2/voices/clip_01-9b5726/compare_styles.mp4`), spec `docs/specs/00b_styled_subtitles.md`.
**Options:** (a) `signature`: sans line brightening as said + one gold serif-italic hero word
per cue; (b) `ink`: each word turns gold as said; (c) `cinema`: words appear one by one, serif,
left-aligned.
**Recommendation:** (a) — the judge's own proposal after round one, and the only one that is not
a caption-app preset.
**Decision:**
**Decided:**

