# Session Log

Newest first. At most six lines per entry: Did, Decisions, Open, Next.

## 2026-09-27 (16): step 10 Cinematic built and merged (PR #9)
**Did:** `/start_work` step 10 → spec (owner: couplets, words blur in as sung = H-017; "yes") → plan → build: `render/cinematic.py` (stanza couplets, per-word blur-in, gold→ivory), `render/cinematic_check.py` (reveal sync), life cycle moved to `render/lifecycle.py` (lofi byte-identical), `layout_line(size=)`, Cormorant Garamond Medium Italic bundled (static instance). Gate green (258 tests, alpha proof); other five themes byte-identical to `dev`; all checks pass with no notes on the three khidki songs (~26 s vs v1 20.9 s). Owner approved the preview → [PR #9](https://github.com/Hacke2367/subtitle_engine/pull/9) squash-merged.
**Decisions:** H-017, D-021.
**Open:** nothing on step 10. No CHANGELOG in this repo (as before).
**Next:** `/start_work` step 11 beat detection → `/spec` (library and where beats live are the owner's calls).

## 2026-09-27 (15): step 09 merged (PR #8)
**Did:** owner said "mrge karo" → AC11 (look) taken as approved; merge recorded, [PR #8](https://github.com/Hacke2367/subtitle_engine/pull/8) squash-merged into `dev`.
**Decisions:** none new.
**Open:** nothing on step 09. No CHANGELOG in this repo (as before).
**Next:** `/start_work` step 10 Cinematic → `/spec`.

## 2026-09-27 (14): step 09 Lofi Minimal + Lofi Typewriter built
**Did:** `/start_work` step 09 → spec (owner: line shows ahead, typewriter as its own theme = H-016; "yes") → plan → build: `layout` tracking (units), `render/lofi.py` (one line, upcoming/current/sung colour states, typewriter bands), `render/lofi_check.py` (colour-state and typing sync), Poppins Light bundled, test song `khidki_s2_lofi` (lowercase copy, aligned locally: timings identical). Gate green (232 tests, alpha proof). Other themes byte-identical to `dev` (every 10th frame). All checks pass with no notes on `khidki_s2`, `khidki_s2_em`, `khidki_s2_lofi`, full `khidki_full` (357 s / 240 s).
**Decisions:** H-016, D-020; spec 09 v1.0.1 (short word's fade-in fits its span).
**Open:** [PR #8](https://github.com/Hacke2367/subtitle_engine/pull/8) in review; owner's look approval (AC11).
**Next:** owner watches `songs/khidki_s2_lofi/render/lofi-*/preview.mp4` → `theme.py` tweaks if asked → merge on the owner's word.

## 2026-09-27 (13): step 08 merged (PR #7)
**Did:** owner said "merge pr, kuch changes nhi karna hai" → merge recorded, PR #7 squash-merged into `dev`.
**Decisions:** none new. Owner confirmed the ElevenLabs key is rotated (dropped from the waiting list).
**Open:** nothing on step 08. No CHANGELOG in this repo (as before).
**Next:** `/start_work` step 09 Lofi Minimal → `/spec`.

## 2026-09-27 (12): step 08 Soft Romantic v2 built and shipped for review (PR #7), handoff
**Did:** `/start_work` step 08 → spec (owner "yes", incl. §7) → plan → build: `render/focus.py` (v1's word frames via shared `timeline.word_plans`; past line moves up, dims 40%, shrinks 85%, blurs 6 px via shared `karaoke.transformed`; glow breath on words ≥ 1 s; safe zone x 60-960). v1 + Pop Karaoke frames byte-identical to `dev`. Gate green (203 tests, alpha proof); `khidki_s2`, `khidki_s2_em`, full `khidki_full` pass with no notes (full song 235.6 s). Owner preferred v2 → CLI default flipped.
**Decisions:** H-014 (no waiting next line; v2 beside v1), H-015 (v2 is the default), D-019 (hand-over rule; sync reads the word's ink rect).
**Open:** PR #7 waits for the owner's "merge". Optional: split `render/check.py` (~330) / `render/karaoke.py` (~310), past the ~300-line guideline.
**Next:** `/merge_pr 7` on the owner's word → `/start_work` step 09 (Lofi Minimal) → `/spec`.

## 2026-09-27 (11): step 07 merged (PR #6)
**Did:** owner said "merge" → AC10 (look) taken as approved; merge recorded, PR #6 squash-merged into `dev`.
**Decisions:** none new.
**Open:** nothing on step 07. No CHANGELOG in this repo (as before).
**Next:** `/start_work` step 08 Soft Romantic v2 → `/spec`.

## 2026-09-27 (10): step 07 Pop Karaoke built and shipped for review (PR #6), handoff
**Did:** `/start_work` step 07 → spec (owner "yes", incl. §7 choices) → plan → build: `render/karaoke.py` (line shown ahead, per-word fill on its own frames, past-line slot), `--theme` on `render`/`make`, `render/<theme>/` folders, fill-sync + safe-zone checks, key-green guard, Poppins bundled. Soft Romantic frames byte-identical to `dev`. Gate green (186 tests, alpha proof); `khidki_s2`, `khidki_s2_em`, full `khidki_full` render with checks passing (full song 271 s).
**Decisions:** D-018 (per-theme folders, bundled Poppins). Spec v1.0.1: a leaving past line finishes its fade as the new line enters (max two lines). Entrance fades in with smoothstep (hand-over overlap fix).
**Open:** spec 07 AC10, the owner's look approval; then merge PR #6.
**Next:** owner watches `songs/khidki_s2_em/render/pop-karaoke/preview.mp4` → `theme.py` tweaks if asked → `/merge_pr 6` on "merge" → `/start_work` step 08.

## 2026-09-26 (9): step 06 shipped and merged (PR #5), handoff
**Did:** `/init` refreshed `CLAUDE.md` (commands, song folder, cross-file invariants). `/ship`: gate green, all 11 spec 06 ACs pass, PR #5 (incl. session (6)'s roadmap docs). Owner said merge → squash-merged into `dev`.
**Decisions:** H-013 approved at 1.5x (owner "ok").
**Open:** nothing on step 06. No CHANGELOG in this repo (earlier merges kept none).
**Next:** `/start_work` step 07 Pop Karaoke → `/spec`.

## 2026-09-26 (8): step 06 revised: marked words 1.5x-2x (H-013)
**Did:** owner found the 1.06x swell too subtle; replaced it with a permanent size rule: marked word = `emphasis_scale` (1.5-2.0, enforced by `Theme`) times its line's font size, laid out with room (shared baseline, taller row). Swell code removed. Unmarked songs still pixel-identical to `dev`; 1.5x and 2x previews rendered, checks pass.
**Decisions:** H-013; spec 06 v1.1.0.
**Open:** owner merges step 06's PR (shipped at 1.5x after the owner's "ok"). `/init` refreshed `CLAUDE.md`.
**Next:** merge → `/start_work` step 07 Pop Karaoke.

## 2026-09-26 (7): step 06 emphasis words built
**Did:** H-009/H-011 logged, spec + plan 06 (owner approved), built it (3598a65): `*word*` reader, marker-free words.json, markers-only edits not stale, clip keeps markers, Soft Romantic swell. Gate green (157 tests). Unmarked `khidki`/`khidki_s2` frames pixel-identical to `dev`; `khidki_s2_em` (3 marks) renders, checks pass, `words.json` untouched, no slower.
**Decisions:** H-009, H-011, D-016; spec 06 v1.0.1 (brief word settles after its own end).
**Open:** owner look (AC10); `/ship` not run (not pushed); session (6)'s doc edits still uncommitted.
**Next:** owner approves the swell → `/ship` → merge → step 07 Pop Karaoke.

## 2026-09-26 (6): styling roadmap saved (no code)
**Did:** saved the research roadmap: plan steps 08–14 plus shared styling rules in `development_plan.md`, the V1.1 scope in `project_context.md`. Left spec 06 alone, since another session is working on it.
**Decisions:** H-012 (owner builds every researched style), D-017 (order of steps 08–14).
**Open:** these doc edits are uncommitted on `feature/emphasis-markers`; step 08 needs the owner to re-approve next-line ghosting (H-010) or it ships without it.
**Next:** step 06 → step 07 → steps 08–13 in order.

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
