# Decisions (Claude defaults, reversible) (V2)

Owner decisions and open questions live in `docs/human_decision.md`. V2 numbers from D-101 so it
never collides with V1's `../docs/decision.md`.

<!-- Entry template (used by /log_decision):
### D-NNN — <title>
**Date:** YYYY-MM-DD
**Context:** <what prompted this>
**Decision:** <what was decided>
**Why:** <reasoning>
**Supersedes:** <D-NNN, if any>
-->

## Index

| ID    | Title                                               | Status |
|-------|-----------------------------------------------------|--------|
| D-101 | V2 ids, package name, shared venv, no V1 imports    | Active |
| D-102 | Plan order: transcription risk first, LLM after a rules baseline | Active |
| D-103 | ElevenLabs Scribe as the transcription engine       | Active |
| D-104 | Romanization by rules in the engine, not by an LLM  | Active |
| D-105 | Cue rules: pause 0.45 s, 42 characters, 6 seconds   | Active |
| D-106 | One work folder per file; the transcript is the cache | Active |

### D-101 — V2 ids, package name, shared venv, no V1 imports
**Date:** 2026-09-29
**Context:** `/scaffold` after H-102 (`v2/` subproject beside the running V1 track).
**Decision:** V2 ids start at 101 (H-101, D-101, P-101). The package is `voice_subs`
(distribution `voice-subs`), a working name the owner can change before the first release.
V2 uses the repository's existing venv (V1's D-003, Python 3.10.11), installed with
`pip install -e .` from `v2/`. `voice_subs` never imports `lyric_engine`; useful V1 code is
copied and adapted. The gate stays empty until the first tested module (as V1's D-004).
**Why:** Two tracks write decisions at the same time, so shared numbers would collide at merge.
No V1 imports keep `v2/` splittable into its own open-source repository. One venv saves disk and
setup on the 8 GB laptop.
**Supersedes:** —

### D-102 — Plan order: transcription risk first, LLM after a rules baseline
**Date:** 2026-09-29
**Context:** Ordering `docs/development_plan.md`.
**Decision:** Step 01 is transcription to Roman Hinglish, because the project context names it
the core risk. Cues at pauses with plain rules and the `.srt` export (step 03) come before the
LLM (step 05).
**Why:** If no engine gives clean Roman Hinglish, the rest changes, so it is tested before
anything is built on it. A rules-only baseline gives the LLM step something to beat, so its
value (and cost) is measured, not assumed.
**Supersedes:** —

### D-103 — ElevenLabs Scribe as the transcription engine
**Date:** 2026-10-03
**Context:** Spec 00 needed one engine for Hinglish speech with word-level times, on a laptop
with 8 GB RAM and no GPU. The repository already holds an ElevenLabs key (V1 uses the same
account for forced alignment), and no other provider key exists.
**Decision:** `POST /v1/speech-to-text` with `model_id=scribe_v1`,
`timestamps_granularity=word`, stdlib HTTP, one call per run and no retry.
**Why:** Measured on a 33 s Hindi clip and a 38 s English one: language detected at 97-99%,
word times tight against the voice, Hindi written in Devanagari and English words in Latin, a
40 s clip uploaded as ~300 kB. Running a local model instead would mean a multi-GB download and
minutes of CPU per clip on this machine. One account, one key, one bill.
**Supersedes:** —

### D-104 — Romanization by rules in the engine, not by an LLM
**Date:** 2026-10-03
**Context:** Scribe returns Hindi in Devanagari, and the project context asks for Roman script
throughout. No LLM provider key is configured, and the owner was away, so no key could be asked
for.
**Decision:** `roman.py` transliterates Devanagari runs with a table plus the inherent-a rules
(drop it at the end of a word and mid-word before a vowel of its own; keep it in the first
syllable, after a nasal, and after a cluster). Latin is passed through untouched. The engine's
original stays in the transcript beside each word.
**Why:** No dependency, no second API call, offline, deterministic, and testable (see
`tests/test_roman.py`): `ghar`, `karta`, `karein`, `jindagi`, `prayaas`, `mushkil`, `gyaan`. It
is a transliteration, not a translation, so it cannot change a word. An LLM pass would spell
a few words more naturally (`isliye` for `isilie`, `doosri` for `dusri`) and could capitalize
sentences; that is step 05's job and needs the owner's key (H-106).
**Supersedes:** —

### D-105 — Cue rules: pause 0.45 s, 42 characters, 6 seconds
**Date:** 2026-10-03
**Context:** Spec 00 needed concrete numbers for where a cue breaks, with no owner to ask.
**Decision:** A new cue starts at a gap of 0.45 s or more, after a sentence end (`. ? ! ।`),
before a cue would pass 42 characters, or before it would run past 6 s. A cue shorter than 1 s
is held on screen up to 1 s, but never into the next cue or past the end of the audio.
**Why:** 0.45 s is a breath, not a word gap; 42 characters is the usual single subtitle line and
leaves room on a 9:16 screen; the hold stops a one-word cue from flashing. All four are
arguments on `to_cues`, so the owner's review can move any of them without touching the code.
**Supersedes:** —

### D-106 — One work folder per file; the transcript is the cache
**Date:** 2026-10-03
**Context:** Red line 3 (never overwrite the user's edits silently) and the wish not to pay for
a second call after fixing a word by hand.
**Decision:** Each source file gets `v2/voices/<name>-<id>/` (the id is a short hash of the
source's full path, because clips are often all called `clip_01.mp4`) holding `audio.mp3`,
`transcript.json`,
the `.srt` and (with `--preview`) `preview.mp4`. A re-run reuses a transcript whose stored
fingerprint matches the extracted audio; if it does not match, the run refuses and names
`--fresh` or `--work`. An existing `.srt` is never replaced without `--overwrite`.
**Why:** The hand-edited transcript is the valuable file, so it is the thing that is kept and
guarded. The fingerprint is a hash of the extracted audio, which ffmpeg produces identically
from the same source, so the check is stable across runs.
**Supersedes:** —
