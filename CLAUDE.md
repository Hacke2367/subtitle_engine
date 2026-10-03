# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Two systems in this repository

| | V1 Kinetic Lyric Engine | V2 Voice Subs |
|---|---|---|
| Does | song audio + Hinglish lyrics → word-synced lyric overlay, finished shorts | 30-40 s video → Roman `.srt` + signature word-lit overlay strip |
| Lives in | repo root: `src/lyric_engine/`, `docs/`, `songs/`, `fonts/` | `v2/`: `src/voice_subs/`, `docs/`, `voices/` (PR #17 until merged) |
| Guide | this file | `v2/CLAUDE.md` (this file also loads there; its V1 parts do not apply) |
| Ids | H-0xx, D-0xx | H-1xx, D-1xx |

Shared: `venv/`, ffmpeg, `ELEVENLABS_API_KEY` in `.env`. Nothing else: no imports across
(V2 D-101), separate docs and tracking. A session works on one system; launch V2 sessions from
`v2/`. `.trash/` (gitignored) holds moved-out files; its README says where each came from.

Everything below is V1. Kinetic Lyric Engine: a personal tool that turns a song's audio + its
Hinglish lyrics into a word-synced, transparent 9:16 lyric overlay for CapCut.

## Read first

- `docs/project_context.md` — what this is, V1 scope, out-of-scope list, red lines. Do not
  re-ask anything it already answers.
- `docs/development_plan.md` — ordered steps and their status board.
- `docs/pending_work.md` — current focus and next action.
- `docs/human_decision.md` — owner decisions and open questions (`H-`).
- `docs/decision.md` — Claude's reversible defaults (`D-`).
- `docs/specs/NN_*.md` (spec, WHAT) and `NN_*_impl.md` (plan, HOW) per plan step.
- `docs/research/lyric_aesthetics.md` — styling research behind the V1.1+ theme steps.
- `docs/backgrounds/*.md` — owner-approved background direction per song type (H-023 onward).
- `docs/reference/project_context.pdf` — the original Gemini blueprint. Much of it is
  deliberately out of V1 scope (see project_context.md); do not build from it directly.

## Commands

Package installed with `pip install -e .`; always use `venv/Scripts/python`.

```
python -m lyric_engine.cli align songs/<song> [--variant NAME] [--fresh] [--overwrite]
python -m lyric_engine.cli clip songs/<full-song> --from 0:27 --to 0:57 [--out songs/<clip>]
python -m lyric_engine.cli make songs/<song> [--theme NAME] [--bg rain]   # align if needed, render
python -m lyric_engine.cli render songs/<song> [--theme NAME] [--codec prores|png|qtrle]
                               [--allow-flagged] [--bg WORLD[:MOOD]]
python -m lyric_engine.cli validate songs/<song>/words.json --song songs/<song>
python -m lyric_engine.cli bakeoff songs/<song> [--fresh]   # compare aligner variants
python -m lyric_engine.cli beats songs/<song> [--fresh] [--bpm N]   # beats.json + click preview
python -m lyric_engine.cli hook songs/<song> [--seconds 30] [--cut] [--pick N]   # find the mukhda
```

- `--theme`: `soft-romantic-v2` (default, spec 08), `soft-romantic` (v1), `pop-karaoke`,
  `lofi-minimal`, `lofi-typewriter` (spec 09), `cinematic` (spec 10), `beat-pop` (spec 12),
  `phonk-neon` (spec 13), `romantic-soft`, `classic-sher` (D-038), `romantic-line` and
  `classic-line` (line-level, D-041). Without `--theme`, `--bg LOOK` picks the look's own style
  (`theme.LOOK_THEMES`: romantic looks -> `romantic-line`, classics -> `classic-line`).
- `--bg`: an engine-made background and a finished short with audio (spec 17): `rain`, `fog`,
  `milan` (`docs/backgrounds/romantic_lights.md`, H-034 to H-036), `khaali`, `aakhri` (sad,
  `docs/backgrounds/sad_*.md`), `chaand` (`romantic_chaand.md`), `jaali` (Sufi, `sufi_jaali.md`),
  `rail`, `talkies` or `ghata` (classics, `classics_*.md`). Anything else is refused. A look = a
  module in `background/` named like the look with `Scene(facts)`, plus a line in `WORLDS`.
- `backdrop`: only the background, no lyrics drawn, for adding lyrics in CapCut:
  `backdrop songs/<song> --bg LOOK` (follows the song's words, has its audio) or
  `backdrop --seconds 60 --bg LOOK [--out F]` (no song, no reactions).
- All tests: `venv/Scripts/python -m unittest discover -s tests -t .`
- One module / class / test: `venv/Scripts/python -m unittest tests.test_timing`,
  `... tests.test_timing.EmphasisTest`, or `... tests.test_render -k Emphasis`.
- Gate (`/gate`, from `.claude/devsystem.json`): the unit tests, then
  `venv/Scripts/python scripts/alpha_proof.py`. No linter is configured.
- Tests are offline and need no song files, but layout/render tests use the real fonts in
  `C:/Windows/Fonts` and `fonts/` (bundled Poppins, Cormorant Garamond, Anton, Pirata One; OFL)
  and a short real ffmpeg encode.

A song folder: `songs/<song>/` holds `audio.wav|mp3`, `lyrics.txt`, `words.json`,
`render/<theme>/` (outputs + `report.md`, one folder per theme: D-018; with `--bg` also
`final_<world>_<mood>.mp4`), `bakeoff/<variant>/`
(`raw.json` aligner cache), `beats.json` + `beats_preview.m4a` (step 11), `drops.txt` (optional,
owner-written drop times for Beat Pop and Phonk Neon), `title.txt` (optional, the title card's
one or two lines, drawn as written; `clip` copies it) and, for a clip, `clip.json`.

## Architecture rule

`src/lyric_engine/` is one package of staged modules:

- `align.py`: audio + `lyrics.txt` → `words.json`; aligner variants, `raw.json` cache, bake-off.
  Engines: `eleven.py` (ElevenLabs forced-alignment API, stdlib HTTP), `local_aligner.py` +
  `vocals.py` (CPU models, imported lazily: torch). `review.py`: preview videos + reports
  (review only, not product output). Never renders the overlay.
- `timing.py`: owns the `words.json` format, lyrics reader (incl. `*word*` emphasis markers),
  flag rules, validator. The only thing align and render share.
- `beats.py`: audio → `beats.json` (tempo + beat times, librosa, imported lazily; D-022, the
  second contract). `ensure_beats` reuses a file valid for the audio (hand edits kept), else
  detects and saves. Never reads `lyrics.txt` / `words.json`; beats are decoration only.
- `theme.py` (all look numbers; `THEMES`, and `motion` picks the renderer), `layout.py`
  (fonts with cmap fallback, tracking, balanced wrap), `render/` (`timeline` → `frames`, or
  `karaoke` for Pop Karaoke, or `focus` for Soft Romantic v2: v1's word frames plus a past-line
  stack, or `lofi` for both lofi themes: one line, colour states or typewriter, checked by
  `lofi_check`, or `cinematic`: couplets per stanza, per-word blur-in, checked by
  `cinematic_check`, or `beatpop`: words pop in as sung on a pill, the line bumps on beats and
  shakes on drops, checked by `beatpop_check`, or `phonk`: Beat Pop's plan with the line shown
  ahead unlit, words flicker on as sung, glow pulses on beats, RGB split on drops, checked by
  `phonk_check`; lofi, cinematic, beatpop and phonk share `lifecycle` (one block on screen at a
  time)
  → `card` (title card on the first ~3 s, only with `title.txt`) → one-pass `encode` →
  `check`): `words.json` → `render/<theme>/overlay.mov`
  (alpha) + `overlay_green.mp4` + `preview.mp4` (with audio, review).
  Never calls the alignment API, so hand-edit + re-render stays free.
- `background/` (spec 17, imported only with `--bg`: numpy, scipy): `__init__` (look names,
  `parse_bg`, song facts: length, aligned word times and places, marked words, the lyric block,
  the folder name as seed; never the words' meaning), `paint` (shared art tools and the finishing
  pass every look shares), `rain`, `fog`, `milan` (one `Scene` per look, ported from its approved
  sample: D-033; milan's frames must come in order), `compose` (the overlay laid over as it is;
  legibility log; the finished short's check). Wraps the frame stream after `card`.
- `workflow.py`: `clip` (cut an aligned song at whole-line boundaries into a new song folder,
  lyrics copied verbatim) and `make` (keeps a valid `words.json`, since it may hold hand
  corrections; refuses a stale one).
- `hook.py`: full song -> its main part (the earliest sung stretch that repeats, from the vocals
  stem; cuts on pauses so lines stay whole) -> `hook_preview.mp3`, and with `--cut` `audio.wav`
  (the full song kept as `full.<ext>`). Picks a range only, never a word's time.
- `cli.py`: the commands above.

Split a module into a subpackage only when it passes ~300 lines.

Invariants that span files (tests and runtime asserts depend on them):

- `words.json` is marker-free: word `text` and `lyrics.lines` have the `*` markers stripped.
  Emphasis is read from the current `lyrics.txt` at render time, and staleness compares
  marker-free lines, so adding or moving markers never needs a re-align (H-009, H-013).
- The mask that measures a word in `layout.py` is the mask `frames.py` draws; `build_sprites`
  and `plan_timeline` assert box size and text against `words.json` (red line 2).
- A marked word is drawn at `emphasis_scale` × its line's font size; `Theme` refuses a scale
  outside 1.5–2.0 (owner rule H-013). Get a word's fonts via `layout.word_fonts`.
- Frames are drawn once and streamed as raw RGBA into one ffmpeg process that writes all three
  outputs (with `--bg`, each frame is the overlay stacked above its finished frame and a fourth
  output is written; the overlay's bytes are untouched: D-028). A line with no marked word must stay pixel-identical when layout code changes.

## Red lines (also in `.claude/devsystem.json`, checked by `/ship`)

1. Never guess a timing. An unaligned word is flagged and reported, never given an
   estimated timestamp.
2. Never alter the lyrics text. On-screen text matches `lyrics.txt` exactly: spelling,
   casing, line breaks. One exception (H-009): `*word*` marks emphasis; the asterisks are
   never drawn.

## Environment

- Windows 11 laptop: i5-1235U, 8 GB RAM, Intel Iris Xe, no dedicated GPU. No heavy local
  models; rendering is CPU-only.
- Python 3.10.11 in `venv/` (`venv/Scripts/python`). ffmpeg 8.0.1 on PATH.
- Secrets go in `.env` (gitignored), never in code or fixtures.
- `songs/` is gitignored (audio, renders and lyrics are large/copyrighted); only
  `songs/example/lyrics.txt` is tracked, and it is original placeholder text.
- Python written through Bash heredocs here loses one level of backslashes (`\\n` became a
  real newline). Edit code containing escapes with the Edit/Write tools.

## Working with the owner

- Owner-facing replies in Hinglish; docs and code in English.
- Ask only questions whose answer changes what gets built; state assumptions and let the
  owner object.
- Owner rule: whenever you have a better idea than the owner's, say so plainly, with the reason,
  before building theirs. Their examples are a starting point, not the limit.
- Owner rule: when the owner asks you to think ("socho") or asks for an idea, look at it from
  several different perspectives before answering: the viewer scrolling (what stops them in the
  first second), the artist or cinematographer (light, depth, composition), the song's own
  emotion, what other channels already do (and avoid it), and what only this engine can do (it
  knows every word's time). Bring clearly different options, not variations of the first thought.
- Owner rule (2026-10-01): keep the system simple. The goal is about 3 templates (background
  looks) per song type, and the owner adds any song of that type on them. Lyric styling must work
  for any lyrics, never for one song's (khidki is only a test clip). Lyric-style work changes the
  lyric themes only, not the templates. No new inputs, files, flags or layers unless the gain is
  clear; when unsure, pick the simpler option and say what was left out.
- Judging a finished short: use the `video-judge` agent (`.claude/agents/video-judge.md`), a
  strict critic independent of Claude's own view; the engine's checks only prove legibility.
- Owner rule (2026-10-01): every fix must be better than what it replaces. Show the old and the
  new on the same clip, side by side, before shipping; if the new one is not clearly better, keep
  the old one. The old theme or look stays until the owner approves the new one.
