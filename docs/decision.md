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
| D-001 | `words.json` is the only contract between stages    | Amended by D-022 |
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
| D-016 | Emphasis (06) before Pop Karaoke (07), own branches | Active |
| D-017 | Order of styling steps 08–14                        | Active |
| D-018 | Theme outputs in `render/<theme>/`; Poppins bundled | Active |
| D-019 | v2 hand-over rule and sync readability (step 08)    | Active |
| D-020 | Lofi line timing on frames; tracking units (step 09) | Active |
| D-021 | Cinematic: first ink, couplet placement, life cycle | Active |
| D-022 | Beats live in `beats.json` beside `words.json`      | Active |
| D-023 | Beat detection numbers: ffmpeg decode, hop 256, -50 dBFS | Active |
| D-024 | Beat Pop: bump/shake math, pill geometry, width check | Active |

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

### D-016 — Emphasis (step 06) before Pop Karaoke (step 07), separate branches
**Date:** 2026-09-26
**Context:** H-009 chose `*word*` emphasis and H-011 chose Pop Karaoke as the first new theme.
Emphasis is V1 scope that step 03 shipped without; the new theme is a V1.1 scope change.
**Decision:** Step 06 adds `*word*` parsing and one emphasis move to Soft Romantic. Step 07 adds
Pop Karaoke and theme selection. Each gets its own branch off `dev`, merged before the next starts.
**Why:** Emphasis touches the lyrics reader and a red line, so it is reviewed on its own; Pop
Karaoke then reuses it. Separate, sequential branches avoid another stacked merge (D-015).
**Supersedes:** —

### D-017 — Order of styling steps 08–14
**Date:** 2026-09-26
**Context:** H-012: the owner builds every researched style after step 07 but set no order.
**Decision:** 08 Soft Romantic v2 → 09 Lofi Minimal → 10 Cinematic → 11 Beat detection →
12 Beat Pop → 13 Phonk Neon; 14 Devanagari shaping is deferred until a song needs it. One branch
per step off `dev`, merged before the next starts (as D-016).
**Why:** Themes that need no new input come first and reuse the alignment. Soft Romantic v2
upgrades the theme the owner's romantic channel uses most. Primitives accumulate: 07 brings the
fill and scale cache, 08 the blur cache that 10's blur-in reuses. Beat detection is a new input,
so it gets its own step before the two beat-driven themes. Latin Hinglish needs no shaper.
**Supersedes:** —

### D-018 — Theme outputs in `render/<theme>/`; Poppins SemiBold bundled in `fonts/`
**Date:** 2026-09-27
**Context:** Step 07 adds a second theme and a `--theme` choice per render. Spec 07 §7 proposed
these defaults; the owner approved the spec ("yes").
**Decision:** Every render writes to `songs/<song>/render/<theme-name>/` (Soft Romantic too, in
`render/soft-romantic/`), so themes never overwrite each other. Outputs of older runs directly in
`render/` are left alone. Pop Karaoke's font, Poppins SemiBold (SIL OFL 1.1), lives in `fonts/`
with its `OFL.txt` and is found relative to `theme.py`.
**Why:** Eight themes are planned (H-012); side-by-side folders make comparing them free. A
bundled font renders identically on any machine and keeps the tests offline; OFL allows
redistribution with the licence.
**Supersedes:** —

### D-019 — v2 hand-over rule and sync readability (step 08)
**Date:** 2026-09-27
**Context:** Spec 08 §4.2 says a line clears if the next line does not start within `hold` of
its last word. Built literally, a line fading out of the current slot can meet the next line's
first word there. The v2 sync check also skipped every line's first word when it tested a wide
margin around the word's whole box.
**Decision:** A line hands over when the move would start before a clear could finish
(`next first − lead ≤ last end + hold + exit fade`, Pop Karaoke's rule), so it can stay up to
0.5 s past `hold`. The v2 sync check reads a word only where no other line's moved block covers
the word's ink rectangle; any word it cannot read is a report note.
**Why:** Two lines never overlap in the current slot. On `khidki_s2` and `khidki_s2_em`, every
timed word is now read by the check (no notes), instead of the first words being skipped.
**Supersedes:** —

### D-020 — Lofi line timing on frames; tracking units (step 09)
**Date:** 2026-09-27
**Context:** Spec 09 §4.2 sets the one-line life cycle in words; plan 09 made it exact.
**Decision:** Between a line's last word and the next line's first current frame `F`, the frames
are split as exit then entrance, and frame `F − 1` is kept clean: the next `lofi-minimal` line is
already at rest there, and in `lofi-typewriter` no other line is on screen. Too few frames for
both: they shrink in proportion; under two frames: a cut, with a report note. A typewriter line
never leaves before its last letter has faded in. Tracking splits a word into units: each Latin
letter of the primary font is one; any other run (fallback font, non-Latin) stays whole.
**Why:** The check can then read every first word's "before" frame, so `khidki_s2`,
`khidki_s2_em` and `khidki_s2_lofi` pass with no notes. Whole non-Latin units keep emoji sequences
and Devanagari from being pulled apart by tracking.
**Supersedes:** —

### D-021 — Cinematic: first ink on the reveal frame, couplet placement, shared life cycle (step 10)
**Date:** 2026-09-27
**Context:** Spec 10 (§4.2-4.4, AC4) asks for ink on the frame of `start − lead`, couplets that
never move once shown, and Lofi Typewriter's block rules; plan 10 made them exact.
**Decision:** A word's blur-in runs `p = (n − reveal + 1) / fi`, `fi = max(1, min(0.5 s, end −
reveal))`, so it has ink on its reveal frame and is complete by its end frame (the other themes
still start at opacity 0 on theirs). Both lines of a couplet are laid out at the smaller of their
fitted sizes when the block starts; the block is centred on `anchor_y` and moved up only as far as
`sprite_pad` (27 px) inside y 1540 needs; taller than the safe zone → two singles and a note.
Every sprite and the block canvas are padded `sprite_pad + 3·blur_px`, so no blur is clipped. The
one-at-a-time life cycle lives in `render/lifecycle.py`, called by Lofi and Cinematic. The font is
a static wght-500 instance of Google Fonts' Cormorant Garamond Italic variable file (fontTools).
**Why:** The check can read every word's first frame and complete frame; a couplet's first line
stays still; one copy of the life-cycle arithmetic (Lofi frames byte-identical after the move).
**Supersedes:** —

### D-022 — Beats live in `beats.json` beside `words.json` (step 11)
**Date:** 2026-09-27
**Context:** H-018: beat data is a new input for the beat themes (steps 12-13), stored beside
`words.json`, not inside it. D-001 said `words.json` is the only contract between stages.
**Decision:** Two contracts. `words.json` (lyrics → timings, owned by `timing.py`, may hold hand
corrections) and `beats.json` (audio → beat and onset times, computed locally, a cache that can
always be rebuilt). Rendering never calls the alignment API (D-001 unchanged there); computing
beats is local and free, so a render may compute a missing `beats.json` once and reuse it.
**Why:** Re-aligning must not wipe beats, recomputing beats must never touch a hand-corrected
`words.json`, and the `words.json` validator stays as it is.
**Supersedes:** amends D-001 (the "only contract" part).

### D-023 — Beat detection numbers: ffmpeg decode, hop 256, −50 dBFS silence (step 11)
**Date:** 2026-09-28
**Context:** Spec 11 left the silence threshold, the frame size and the preview format to the plan;
plan 11 (§2.2-2.5, §2.9) fixed them from a spike on this laptop.
**Decision:** Audio is decoded by ffmpeg to mono float32 at 22 050 Hz (every `AUDIO_EXTS` format).
`beat_track` runs at `hop_length` 256; `--bpm` passes a fixed tempo (`bpm=`), not a prior. A run of
RMS frames (2048 samples) below −50 dBFS longer than two beat periods loses every beat inside it.
A file is stale only on changed audio or an older `version`; detector settings never invalidate it,
so a `--bpm` fix and hand edits survive renders. The preview is the original audio plus 1.5 kHz
clicks, AAC in `beats_preview.m4a`.
**Why:** Hop 512 read a 120 BPM click track as 117.45 BPM and dropped its first and last click; 256
gave 120.19 with every click within 19 ms (1.3 s on a full song). librosa keeps the pulse going
through a dead stop (6 beats in 3.5 s of silence); −50 dBFS is near-digital silence, and
`khidki_full`'s quietest 1 % of frames sit at −32 dBFS, so real music is untouched.
**Supersedes:** —

### D-024 — Beat Pop: bump and shake math, pill geometry, planned-width beat check (step 12)
**Date:** 2026-09-28
**Context:** Spec 12 (§4.2, §4.5, §4.7) sets the pop, pill, bump and shake in words; plan 12 and
the build made them exact.
**Decision:** Beats and drops take the words' lead (frame `floor((t − lead)·fps)`). Bump: peak
`bump_scale` on the beat frame, `1 + 0.05·(1 − d/5)²` after. Drop: peak `drop_scale` and a fixed
8-step shake table, both × `(1 − d/15)²`. Line scale is `max(bump, drop)`, not their product (a
drop sits on a beat). The pill spans the font's cap top to descender bottom, ± `pill_pad`·size
(9 px at 110 px), corner radius 0.2 × its height, drawn at 4× and reduced. A sung word has no
stroke or shadow (the pill is its legibility layer, and a stroke stuck out of the round ends).
Layout box 700 px about x 510, `anchor_y` 0.60, `min_font_size` 64 (a 2x word in a 58-character
line needs it). The beat check compares the drawn line width on b − 1, b, b + 1 with the width the
plan gives (pops and pills included), ±4 px, where the planned rise is ≥ 6 px.
**Why:** Peaks land on the beat and the drop, the drop never outgrows the safe-zone margin, and the
pill never touches a neighbour (17 px clear). A check that skipped every beat near a pop read 6
of 32 beats on `khidki_s2`; the planned width reads 30 of 32.
**Supersedes:** —

### D-025 — Phonk Neon: no beat bump, dark rim over the glow, flicker, pulse and split math (step 13)
**Date:** 2026-09-28
**Context:** Spec 13 §4.4 and §7 left the exact look and the check reads to Claude; H-020 set the
font, colour, drop effect and neon-sign lighting.
**Decision:** Beats pulse the glow only (`bump_scale` 1.0): strength `0.55 + 0.45·(1 − d/9)²`,
quantised to 1/32, one value per frame for every lit word. Flicker `(1, 0.2, 1, 0.5, 1)` from the
reveal frame, cut to the word's span. Drop: Beat Pop's shake with a 1.06× peak, plus red/cyan
copies of the cores at ∓`12·(1 − d/8)²` px. Layers: glow (wide 18 px + tight 6 px blur,
screened, ×1.5), then a dark rim (the 4% stroke outline, 2 px blur, 85% black), then the split
copies, then the cores (lit `#E1A5FF`, unlit `#582476`). The line comes in 0.5 s ahead with a
0.2 s fade (Beat Pop's plan with `ahead=True`). Checks: light sync on the blue channel (lit vs
unlit); pulse sync on the mean alpha around steadily lit words, away from any word that changes.
**Why:** A soft black halo under the glow left lit words the least legible state on bright
footage (light core on a light sky); the rim over the glow fixes that and keeps the bloom on dark
footage. A bump would make Phonk a recoloured Beat Pop. The pulse read covers 26 of 32 beats on
`khidki_s2`.
**Supersedes:** —

### D-026 — Title card: numbers, layer order, clash check; Beat Pop reads widths below it (step 15)
**Date:** 2026-09-29
**Context:** Spec 15 left the card's size, place and checks to Claude; H-021 set top, ~3 s, each
theme's own look.
**Decision:** Card size 0.5 × the theme's `font_size` (shrunk by `font_step` to 28 px for a wide
line), first row's box top at y 420, rows at the theme's row pitch, centred on `center_x`, kept
inside the safe zone (or the layout box) minus the layer pad. Fade in 0.3 s from frame 0, gone at
3.0 s after a 0.5 s fade out. Layers: glow (Phonk Neon only, at `pulse_low`), shadow of the
stroke outline (or the glyph), stroke (if `stroke_rgb`), glyph in `text_rgb`: the theme's resting
word look, no sung-state accent. Any lyric ink (alpha ≥ 16) under the card's rectangle while it
shows fails the render check. Beat Pop's beat check reads the line width from 100 px above the
line's top word box down, so the card never counts as line width.
**Why:** At y 420 the card clears every theme's lyrics on the test songs (highest lyric ink:
Pop Karaoke's past line, y 501, on `khidki_s2_em`, after the card is gone); a clash on another
song is a check failure, not a silent overlap. Pixel-identical frames without `title.txt`.
**Supersedes:** —

### D-027 — Where background directions and prototypes live
**Date:** 2026-09-29
**Context:** The owner approved a background direction per song type (H-025 to H-031) and asked
for each to be saved as a .md file; the look prototypes shown on the way were rejected (H-024).
**Decision:** One file per world in `docs/backgrounds/<world>.md`, each with the same sections
(principles, the viewer's-eye walkthrough, moods, reuse rules, avoid list, build order, notes
for the spec); alternatives go in the H- entry, not the file. Tool research in
`docs/research/background_tools.md`. The rejected prototypes (`bg_looks.py`, `bg_ideas.py` and
their videos) stay in the gitignored `songs/_review/backgrounds/`, review only.
**Why:** The direction files are what each background step's spec starts from, so they are
tracked; the prototypes were never product code and the owner turned them down.
**Supersedes:** —

### D-028 — Backgrounds: one ffmpeg process, overlay stacked above the finished frame (step 17)
**Date:** 2026-09-29
**Context:** Spec 17 adds a finished short (`final_<world>_<mood>.mp4`) next to the overlay's three
outputs, which must stay exactly as they are without and with `--bg` (spec 17 AC2, AC3).
**Decision:** With `--bg`, every frame piped to ffmpeg is 1080×3840 RGBA: the theme's overlay
bytes, untouched, above the finished frame. The graph splits and crops; the top half runs through
today's three chains, the bottom half to H.264 (crf 18, AAC 192k, faststart, no `-shortest`).
Without `--bg` the command string is the same as before.
**Why:** Keeps CLAUDE.md's one-process design and makes AC3 hold by construction (verified: the
overlay's frame hashes equal `dev`'s). A second ffmpeg process would add a second writer, error
path and cleanup for no gain.
**Supersedes:** —

### D-029 — Backgrounds: light at half size, full size in 8-bit PIL ops (step 17)
**Date:** 2026-09-29
**Context:** The 10-minute target for a 60 s short (spec 17 AC10); a first float32 pipeline took
about 250 ms per frame for the room alone.
**Decision:** Every light term (ambient, the jaali patch with leaves and curtain, dust, steam,
the lamp) and the lyrics' shadows are summed at 540×960 in float; the sum is clipped at 1,
upscaled once as RGBA and multiplied by the full-size albedo with `ImageChops.multiply`; the
tinted overlay goes on with `alpha_composite`. Blurs use `scipy.ndimage` (already installed; PIL
cannot blur float images). numpy and scipy are now direct requirements.
**Why:** Light is soft, so half size shows nothing; the 8-bit C ops cut the room to about 100 ms
per frame (145 ms measured inside a real render), about 0.19 s per frame with the overlay and all
four encodes. `moderngl` stays the fallback if a later world needs more.
**Supersedes:** —

### D-030 — Backgrounds: the lyrics' shadow blocks light; legibility measured around the text (step 17)
**Date:** 2026-09-29
**Context:** Spec 17 §4.4 (lyrics cast a shadow without changing the text) and §4.5 (legibility).
**Decision:** The overlay's alpha, shifted away from each light and softened, removes a share of
that light (sun 70%, lamp 70%), so the shadow is the wall's own colour, lengthens and fades with
the sun, and is cast by the lamp at the end. The text's RGB is multiplied by a tint in [0.9, 1]
per channel; its alpha is never touched. Legibility: 99th-percentile background luminance around
the text (ink box + 24 px, inside the lyric area) against the lit text colour, at least 3:1, on
every frame with text.
**Why:** No extra shadow rules per light, and red line 2 holds by construction. The first rule,
over the whole lyric area, failed on the lamp's glow at the bottom-left corner where no lyric sits,
which would have banned the ending; the spec was changed before any approval.
**Supersedes:** —

### D-031 — Backgrounds: props drawn by code, seeded by the folder name (step 17)
**Date:** 2026-09-29
**Context:** `docs/backgrounds/romantic_room.md` left props open (AI stills, CC0 art or code).
**Decision:** Everything is drawn by code (PIL at 2× with soft form shading and a contact shadow
on the wall); the room's story is mostly light and shadow (the jaali's chakri pattern, a money
plant vine, a sheer curtain). The seed is `zlib.crc32(folder name)`; it picks the plant's side,
the curtain's print, the prop (chai glass with steam, radio, letter) and the dupatta's colour.
The wall, window and jaali never change.
**Why:** Free, the same hand-made look in every world, and re-rendering a song keeps its room.
AI stills stay the fallback if the owner finds the drawn props weak.
**Supersedes:** —
