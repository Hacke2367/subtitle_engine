# Spec: Alpha Overlay Proof in CapCut
**Version:** 1.0.0 | **Component:** Output pipeline (render → CapCut)
**Status:** Ready for Review
**Plan step:** 01 (`docs/development_plan.md`) · **Branch:** `feature/alpha-overlay-proof`

## 1. Problem Statement

Everything the engine produces reaches the viewer through CapCut: the overlay is laid on top of
the owner's own background and song there. If CapCut shows a black box where the overlay should
be transparent, or leaves green behind after Chroma Key, every later step (alignment, layout,
animation) delivers something unusable. Whether CapCut desktop honours alpha in `.mov`, and which
encoding it accepts, is unverified. Mobile CapCut needs a green-screen mp4 instead (H-003: both
outputs are primary).

The riskiest pixels are exactly the ones Soft Romantic depends on: soft glow, fade-ins, and
anti-aliased text edges are all *partially* transparent. A chroma key cannot represent partial
transparency, and alpha that gets mishandled (straight vs premultiplied) shows up as dark or
bright fringes around them. This has to be known before the theme is designed around glow.

## 2. Objective

Prove, with a 5-second test clip, which output encoding(s) CapCut desktop and CapCut mobile
import cleanly, including the partially transparent pixels, and record the answer so step 03
builds on a known-good format.

## 3. Scope & Constraints

**Will Do:**
- Generate one 5-second test clip, 1080×1920, 30 fps, no audio, in these forms:
  - several alpha-channel `.mov` variants (different alpha-capable encodings, so one CapCut
    session can find one that works instead of one round-trip per guess);
  - one mp4 on a solid pure-green background, for CapCut mobile Chroma Key.
- Clip contents, identical in every variant (placeholder look, not the Soft Romantic design):
  - a static Hinglish line visible from frame 0 to the last frame (solid text, anti-aliased edges);
  - a word that fades in (partial opacity changing over time);
  - a word with a soft glow halo (partial transparency, fixed);
  - a word that moves or scales across the frame (alpha correct on every frame, not just one).
- One command that regenerates every clip from scratch, offline.
- An automated check of each clip's technical properties (Acceptance Criteria 2–4).
- A short results note per variant: file size, and that size extrapolated to a 3-minute song.
- Record the outcome of the owner's CapCut tests as a decision, and update
  `docs/project_context.md` / the plan if the outcome changes the output plan.

**Will NOT Do:**
- Word alignment, a real song, or any audio (audio sync is verified in step 03).
- Theme design: colours, fonts and motion in the clip are test placeholders.
- Layout, auto-wrap, pagination, emphasis markers.
- `.webm`, `.ass`, or any other format outside `.mov` with alpha and green mp4.
- Commit rendered clips to git.
- Pick the final render library for step 03. The generator only has to produce the test clips.

**Hard Rules:**
- No network or API calls.
- Rendered clips live in a gitignored location, never in a commit.
- Test text is original, not copyrighted lyrics.
- The green-screen clip's text and glow colours stay far from the key green, so any keying
  failure seen is caused by partial transparency, not by colour overlap.

**Assumption, owner may override:** 30 fps. If the owner's CapCut projects are 60 fps, the clip
follows that instead.

## 4. Core Design

One generator produces the same 150-frame animation once as RGBA frames. Those frames then
become every output:

- **Alpha variants:** the RGBA frames encoded into `.mov` with each candidate alpha-capable
  encoding. The exact candidate list is chosen in `/plan`; it must cover more than one encoding
  family.
- **Green variant:** the same RGBA frames composited over pure green (#00FF00), then encoded as a
  standard mp4 that phones play natively.

Because every output comes from one frame source, any difference seen in CapCut is caused by the
encoding, not the content.

A checker reads each output back and verifies resolution, frame rate, frame count, absence of an
audio track, presence of an alpha channel (alpha variants), and sampled pixel values on a known
frame.

**Owner test protocol**, part of the deliverable so the result is comparable:

- **Desktop:** import each alpha `.mov` into a CapCut desktop project with a background clip; check
  it once over a dark background and once over a bright one.
- **Mobile:** move the green mp4 to the phone as a file, not as a WhatsApp photo/video (those get
  recompressed). Apply Chroma Key in CapCut mobile, over a dark background and a bright one.
- **Record for each variant:** imports yes/no; background visible through transparent areas
  yes/no; black box yes/no; fringe around the glow or faded word yes/no; phone OS.
- **Optional data point:** also try the best alpha `.mov` in CapCut mobile. If it works there,
  green mp4 may not be needed.

## 5. Edge Cases & Error Handling

- **No alpha variant works in CapCut desktop:** do not start step 02. Record it as an owner
  decision (`human_decision.md`). The likely path is green mp4 for both desktop and mobile, which
  changes step 03's look, because glow and fades can't survive a chroma key cleanly. That trade-off
  is the owner's call, not a silent default.
- **Alpha works, but glow or fade shows dark or bright fringes:** this is an encoding / alpha-mode
  problem, not a CapCut limit. Try the remaining variants. If every variant fringes, record which
  pixels break and treat it as a blocker for the glow-based look.
- **Green mp4 keys out solid text cleanly, but glow or fades leave green tint or hard edges:**
  expected, because a chroma key can't represent partial transparency. Record how bad it looks. The
  owner decides whether mobile output accepts a harder-edged look (theme adapts for green output)
  or whether another route is needed. Not decided here.
- **A variant is huge** (e.g. several GB for a 3-minute song, by extrapolation): record it. If
  that variant is also the only one that works, flag it to the owner as a constraint before step
  03.
- **CapCut conforms or retimes the clip** (a different fps shows as a changed duration or stutter):
  record it. The final output's fps must then match the owner's CapCut project settings.
- **ffmpeg missing or lacking an encoder** needed for a candidate: the generator reports which
  variant could not be produced and continues with the others. It never silently skips one.
- **Phone transfer recompresses the green mp4:** the protocol requires transfer as a file. If
  recompression happened anyway, the test is repeated rather than recorded as a failure.

## 6. Acceptance Criteria

1. One command, run offline on this laptop, produces all alpha `.mov` variants plus the green mp4.
   Any variant that couldn't be produced is named in its output, never silently skipped.
2. Every output is 1080×1920, 30 fps, exactly 150 frames, and has no audio track, as verified by
   the automated check.
3. Every alpha variant carries an alpha channel. On a sampled frame, an empty corner pixel has
   alpha 0, a solid text pixel alpha 255, and a glow pixel alpha strictly between 0 and 255, as
   verified by the automated check.
4. In the green mp4, an empty corner pixel is within a small tolerance of #00FF00, and no text or
   glow colour used in the clip is within the keying range of that green, as verified by the
   automated check.
5. The results note lists each variant's file size and its 3-minute extrapolation.
6. The owner reports, for CapCut desktop, at least one alpha variant that imports with
   transparency: the background is visible over both dark and bright backgrounds, with no black box
   and no fringe around text, glow or faded word. **Or** the owner reports that none do, and that
   outcome is recorded per §5.
7. The owner reports, for CapCut mobile, whether the green mp4 keys out cleanly for solid text, and
   separately how glow and fades look after keying.
8. The outcome of 6 and 7 is recorded in `docs/decision.md` or `docs/human_decision.md`, and
   `docs/project_context.md` / `docs/development_plan.md` are updated if the output plan changed.
9. No rendered clip is tracked by git.

## 7. Dependencies

- ffmpeg 8.0.1 (on PATH).
- `venv/` (Python 3.10.11, currently empty). What goes into it is decided in `/plan`.
- The owner's time: one CapCut desktop session and one CapCut mobile session, about 15 minutes
  total.
