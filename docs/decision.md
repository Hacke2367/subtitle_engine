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
| D-005 | Alpha candidates: ProRes 4444, PNG-in-MOV, qtrle     | Active |
| D-006 | Gate runs the alpha proof end to end                | Active |
| D-007 | Order flags judged against the last trusted word    | Active |
| D-008 | Editable install + stdlib unittest gate              | Active |
| D-009 | Provisional default aligner: L-vocals               | Active |
| D-010 | Local stack: torch 2.11 CPU, MMS_FA, htdemucs       | Active |
| D-011 | Step 03 stacked on unmerged step 02; codec open     | Active |
| D-012 | Balanced wrap; fallback fonts; Devanagari unshaped  | Active |
| D-013 | Fade waits for the last word; render subpackage     | Active |
| D-014 | Step 05 (workflow) before 04; stacked on step 03    | Active |
| D-015 | Stacked PRs merged top-down (#4→#3→#2→dev)          | Active |

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

### D-005 — Alpha candidates: ProRes 4444, PNG-in-MOV, qtrle
**Date:** 2026-09-26
**Context:** Spec 01 needs more than one alpha encoding family so one CapCut session finds a
working one.
**Decision:** Test `A_prores4444.mov` (yuva444p10le, 16-bit alpha, vendor apl0), `B_png.mov`
(rgba), `C_qtrle.mov` (argb), plus `G_green.mp4` (H.264 High, yuv420p, BT.709) for mobile.
HEVC-with-alpha is excluded.
**Why:** Three distinct families (ProRes, lossless PNG, RLE). HEVC alpha was probed on this
machine: "Loaded libx265 does not support alpha layer encoding". Measured sizes for a 3-minute
song: ProRes ~1.8 GB, PNG ~380 MB, qtrle ~310 MB, green mp4 ~13 MB.
**Supersedes:** —

### D-006 — Gate runs the alpha proof end to end
**Date:** 2026-09-26
**Context:** D-004 deferred gate commands until the first check existed; `scripts/alpha_proof.py`
is it.
**Decision:** `gate.commands` = `venv/Scripts/python scripts/alpha_proof.py` (renders, encodes,
checks; about 20 s; exit non-zero on any missing variant or failed check).
**Why:** Offline, self-contained, and it fails when it should (verified against a no-alpha,
149-frame clip: all four failures caught).
**Supersedes:** —

### D-007 — Order flags judged against the last trusted word
**Date:** 2026-09-26
**Context:** Plan 02 said `out_of_order` compares with the previous placed word "flagged or not".
Agent T found that an aligner jumping back two or more words then produces a doc `validate()`
rejects, so the whole variant would fail instead of reporting flagged words.
**Decision:** `apply_flags` compares with the nearest earlier placed **and unflagged** word, the
same rule `validate()` uses. A test proves a backward jump yields flags and a valid doc.
**Why:** Flag output must always validate; a bad stretch of alignment is a finding to report,
not a crash.
**Supersedes:** plan 02 §4 wording for `out_of_order`

### D-008 — Editable install + stdlib unittest gate
**Date:** 2026-09-26
**Context:** Step 02 adds the first importable package code and tests.
**Decision:** Minimal `pyproject.toml`, `pip install -e .` into `venv/`; tests use stdlib
`unittest` (`venv/Scripts/python -m unittest discover -s tests -t .`), added as the first gate
command before the alpha proof.
**Why:** No test-framework dependency; `python -m lyric_engine.cli` works from the repo root.
**Supersedes:** —

### D-009 — Provisional default aligner: L-vocals
**Date:** 2026-09-26
**Context:** The first bake-off on the 30 s clip (`songs/khidki`, lines 1–8, 27.0–57.0 s of the
full song): E-raw and E-vocals failed with HTTP 401, "missing the permission forced_alignment"
(no charge). L-vocals: 44/44 words placed, 0 flagged, 11.3 s. Its word starts match an
independent full-song run of the same model within 20 ms. The lowest scores (0.00–0.12) sit in
the repeated chorus lines 2–4.
**Decision:** `DEFAULT_VARIANT = "L-vocals"`, provisionally under H-008. `min_score` stays
disabled: there is no ground truth yet to calibrate it against.
**Why:** It is the only working variant, and its output is valid and stable. The owner still
confirms by watching `songs/khidki/bakeoff/L-vocals/preview.mp4` (AC10), and the E-variants are
re-run once the key has the permission.
**Supersedes:** —

### D-010 — Local stack: torch 2.11 CPU, MMS_FA, htdemucs
**Date:** 2026-09-26
**Context:** Agent L tried the plan-02 candidates on this laptop (Python 3.10, 8 GB RAM, no GPU).
**Decision:** `torch==2.11.0+cpu` and `torchaudio==2.11.0+cpu` (`pipelines.MMS_FA` +
`functional.forced_align`), and `demucs==4.0.1` (`htdemucs`, shifts=0). PyPI is the main index,
with the PyTorch CPU index as an extra index. MMS weights are loaded memory-mapped (peak 5.2 GB →
under 4 GB). The local engine also places a wildcard token between lyric lines (`lines=`), so an
unwritten repeat cannot drag a line across it; `SETTINGS_VERSION` is now 2.
**Why:** It installs and runs within the budget: the full 172 s song takes 116 s to separate and
50 s to align. Not tried: `ctc-forced-aligner` (pulls transformers plus a second 1.2 GB weight
copy) and `audio-separator`.
**Risk:** the MMS_FA weights are **CC-BY-NC 4.0 (non-commercial)**. That is fine for this personal
tool, but it conflicts with the SaaS "future vision" in project_context. A commercial version needs
a different aligner or licence. Recorded for the owner.
**Supersedes:** —

### D-011 — Step 03 stacked on unmerged step 02; codec left open
**Date:** 2026-09-26
**Context:** Step 02 is in Review (PR #2), and merging is owner-only. The owner is away (H-008) and
asked for work to continue. H-006 requires the CapCut test before step 03's spec, because the
output format depends on it.
**Decision:** `feature/soft-romantic-render` branches from `feature/word-alignment`, not `dev`.
Merge order: PR #2 first, then retarget step 03's PR to `dev`. The renderer's alpha codec is a
setting covering all three formats proven in step 01, plus the green mp4. The default is fixed only
after the owner's CapCut test, and step 03 can't be `Done` before that test.
**Why:** It keeps work moving without deciding what H-006 reserved for the test, and a stacked
branch avoids duplicating step 02's code.
**Supersedes:** —

### D-012 — Balanced wrap; per-run fallback fonts; Devanagari unshaped (known limit)
**Date:** 2026-09-26
**Context:** Agent Y built `layout.py`. Greedy wrap put "hai" alone on the second row of "Ek
chaand ka tukda rehta hai". Some fallback glyphs (emoji, Devanagari matras) rise above the primary
font's box. This Pillow build has no raqm, so it can't shape complex scripts.
**Decision:** (1) Rows are balanced: greedy's row count, but the split with the narrowest widest
row (brute force, ≤ 3 rows). (2) A fallback run whose ink would leave the primary ascent/descent
box is drawn at the largest size that fits, so masks share one height and baseline and never clip.
(3) Default-ignorable characters (ZWJ, VS16, …) are never drawn but stay in the text. (4) Emoji
render as single-colour text, and Segoe UI Symbol comes before Segoe UI Emoji. (5) **Known limit:**
Devanagari renders unshaped (`दिल` → `दलि`). V1 lyrics are romanized, so this isn't a problem
now. If Devanagari lyrics ever matter, it needs raqm (FriBiDi DLL) or another text engine.
**Why:** It is the better look for the owner's review, with no clipping, and it is honest about a
limit V1 doesn't hit.
**Supersedes:** plan 03 §4 "greedy-wrap" wording

### D-013 — Fade waits for the last word; look tuning; render split into a subpackage
**Date:** 2026-09-26
**Context:** Agent R's first real render of `songs/khidki` passed every check, with three
findings. Every line is ended by the next line (the singing is continuous), so under plan 03's
fade rule (`stop − 8`) each line's last word was solid for only 1–2 frames. Cream text on white
was low contrast. The glow ramped in faster than the text, a brief pink flash. `render.py` had
reached 578 lines, over the ~300-line split rule.
**Decision:**
(1) A line's fade never starts before its last word has fully revealed. When the next line comes
sooner, the fade shortens, down to a cut, which is spec 03 §5's "fade-out shortens" wording rather
than plan 03 §4's. A word the next line cuts off mid-reveal is reported as a **note**, not a sync
failure: its timing is right, the song is just sung back to back. Khidki has one: word 10 "hai".
(2) Theme: `shadow_alpha` 0.35 → 0.55, `shadow_radius` 6 → 7, `glow_in_s` 0.08 → 0.18.
(3) `render.py` became the `render/` package (`timeline`, `frames`, `encode`, `check`,
`__init__`), each module under 190 lines, with the public API unchanged.
(4) Agent R's plan deviations are accepted: words rise into place (the plan's sign was wrong);
all glows are drawn under all text; `WordPlan.text`; lines sorted by first frame; the overlay
frame count comes from the single alpha decode; frames are streamed as zero rows + band + zero
rows.
**Why:** The last word of every line has to be readable. The rest improves the look on real
backgrounds and follows the module-size rule.
**Supersedes:** plan 03 §4 fade_start formula and check sample frame

### D-014 — Step 05 (workflow) before step 04; stacked on step 03
**Date:** 2026-09-26
**Context:** After H-010 the owner chose "2" (workflow commands) and said "pahele tum karke, 2
kaam karo, /ship and /handoff". PRs #2 and #3 are not merged yet (no merge instruction).
**Decision:** Add plan step 05 (`clip` + `make`) and build it now. Step 04 (`.lrc` anchors) is
deferred: the plan made it optional, and the khidki clip aligned with 0 flags without it. The
step 05 branch is stacked on `feature/soft-romantic-render` (merge order: #2 → #3 → step 05). The
owner's instruction stands in for the spec approval stop.
**Why:** It cuts a short's manual work from 5 steps to 2 commands, which is the project's
success signal.
**Supersedes:** —

### D-015 — Stacked PRs merged top-down (#4 → #3 → #2 → dev)
**Date:** 2026-09-26
**Context:** The owner said "abhi merge karo". PRs #2, #3 and #4 are stacked (D-011, D-014), and the
project squash-merges. Squashing #2 into `dev` first would force a rebase + force-push of #3 and
#4, or a large conflict merge, because the squash commit shares no history with the stacked
branches.
**Decision:** Squash #4 into `feature/soft-romantic-render`, then #3 into `feature/word-alignment`,
then #2 into `dev`. There are no conflicts and no force-pushes. `dev` gets one squash commit for
steps 02+03+05. The per-step history stays in PRs #2/#3/#4 and in these docs. The merge is recorded
on the top branch, so it flows down into `dev`.
**Why:** It is the safest path for a stacked squash workflow. For later stacks, prefer merging each
PR before the next branch starts.
**Supersedes:** —
