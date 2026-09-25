# Decisions (Claude defaults, reversible)

Owner decisions and open questions live in `docs/human_decision.md`.

<!-- Entry template (used by /log_decision):
### D-NNN — <title>
**Date:** YYYY-MM-DD
**Context:** <what prompted this>
**Decision:** <what was decided>
**Why:** <reasoning>
**Supersedes:** <D-NNN, if any>
-->

## Index

| ID    | Title                                              | Status |
|-------|----------------------------------------------------|--------|
| D-001 | `words.json` is the only contract between stages    | Active |
| D-002 | `songs/` is gitignored except the example lyrics    | Active |
| D-003 | Keep the existing venv (Python 3.10.11)             | Active |
| D-004 | Gate commands empty until the first tested module   | Active |

### D-001 — `words.json` is the only contract between stages
**Date:** 2026-09-26
**Context:** Option B layout (H-001) splits alignment and rendering into separate modules.
**Decision:** `align.py` writes `words.json`; `render.py` reads it. `render.py` never calls the
alignment API and `align.py` never renders. `timing.py` owns the format.
**Why:** The owner corrects timings by hand and re-renders; that loop only stays cheap if
rendering cannot trigger alignment. It also gives red line #1 one place to live: flagged words
are visible in `words.json`.
**Supersedes:** —

### D-002 — `songs/` is gitignored except the example lyrics
**Date:** 2026-09-26
**Context:** Per-song folders hold audio, rendered overlays and third-party lyrics.
**Decision:** Ignore `songs/*`; track only `songs/example/lyrics.txt` (original placeholder text).
**Why:** Audio and `.mov` files are large, and song audio/lyrics are copyrighted.
**Supersedes:** —

### D-003 — Keep the existing venv (Python 3.10.11)
**Date:** 2026-09-26
**Context:** `venv/` already existed (Python 3.10.11, empty); system Python is 3.12.
**Decision:** Use the existing venv.
**Why:** Nothing planned needs 3.11+; recreating it gains nothing. Revisit if a dependency does.
**Supersedes:** —

### D-004 — Gate commands empty until the first tested module
**Date:** 2026-09-26
**Context:** `/gate` runs `gate.commands` from `.claude/devsystem.json`; there is no code yet.
**Decision:** Leave `gate.commands` empty; add the test command in the step that adds the first
test.
**Why:** A gate listing commands that do not exist yet would fail or lie.
**Supersedes:** —
