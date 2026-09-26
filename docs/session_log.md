# Session Log

Newest first. At most six lines per entry: Did, Decisions, Open, Next.

## 2026-09-26 (5): styling research (no code)
**Did:** owner asked for aesthetics research only. Four parallel research agents (short-form styles, Hinglish/fonts/palettes, PIL animation primitives, CapCut limits + open source) plus local benchmarks → `docs/research/lyric_aesthetics.md`. Verified locally: per-word effects cost ~1 ms, Pillow has no raqm in this venv (Devanagari shaping wrong), ffmpeg's libass renders ASS onto a transparent ProRes canvas.
**Decisions:** none. H-011 raised (which styles first; recommendation Soft Romantic v2 → Karaoke Fill → Minimal Lowercase).
**Open:** H-009, H-011; nothing committed (research doc and these entries are uncommitted on `dev`).
**Next:** owner answers H-009 and H-011, then plan step 06 → `/start_work` → `/spec`.

## 2026-09-26 (4): merged steps 02, 03, 05
**Did:** merged the stacked PRs top-down, #4 → #3 → #2 → `dev` (D-015).
**Decisions:** D-015.
**Open:** H-009; the first new theme; a different song end to end; rotating the API key.
**Next:** plan the styling phase (step 06) once H-009 and the first theme are decided.

## 2026-09-26 (3): owner validated V1; step 05 workflow commands
**Did:** recorded the owner's check (H-010: sync, look and CapCut OK; L-vocals and ProRes defaults confirmed). Built step 05: `clip` (whole lines, snapped cut, verbatim lyrics) and `make` (align if needed, then render); PR #4, stacked on #3. Clip 27–57 is byte-identical to the hand-made one; stanza 2 went clip → make, 0 flags, checks pass.
**Decisions:** H-010, D-014 (step 05 before 04; stacked).
**Open:** merging #2 → #3 → #4; H-009 emphasis; a different song end to end; rotating the API key.
**Next:** owner merges the stacked PRs in order; then styling (H-009 emphasis, then new themes as a logged scope change).

## 2026-09-26 (2): steps 01–03 built, owner away (H-008)
**Did:** step 01 merged (PR #1). Step 02 alignment bake-off (PR #2): L-vocals 44/44 on the 30 s khidki clip, E-variants blocked by the key permission. Step 03 renderer (PR #3, stacked): the first real overlay passed every check in 33.7 s. Used 5 parallel agents.
**Decisions:** H-004 (option c), H-006, H-007 (30 s prototype), H-008 (autonomy); D-005…D-013. H-009 is pending (emphasis syntax).
**Open:** merging PRs #2 and #3; ElevenLabs `forced_alignment` permission; look review of `preview.mp4`; the CapCut import test (fixes the default codec); H-009; rotating the API key.
**Next:** owner reviews `songs/khidki/render/preview.mp4`, then does the CapCut test, then merges #2 and retargets and merges #3. Step 04 (`.lrc` anchors) only if real songs drift.

## 2026-09-26
**Did:** `/kickoff` → `docs/project_context.md`; `/scaffold` → option B layout, standard-tier docs, `.claude/devsystem.json`, `CLAUDE.md`, git init.
**Decisions:** H-001, H-002, H-005; D-001–D-004. Corrected H-004: local CPU alignment is viable, not API-only.
**Open:** H-003 (CapCut desktop/mobile), H-004 (alignment provider); blank `knietic_lyric.pdf`.
**Next:** `/start_work` → step 01 alpha overlay proof → `/spec`.
