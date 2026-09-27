# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

Kinetic Lyric Engine: a personal tool that turns a song's audio + its Hinglish lyrics into a
word-synced, transparent 9:16 lyric overlay for CapCut.

## Read first

- `docs/project_context.md` — what this is, V1 scope, out-of-scope list, red lines. Do not
  re-ask anything it already answers.
- `docs/development_plan.md` — ordered steps and their status board.
- `docs/pending_work.md` — current focus and next action.
- `docs/human_decision.md` — owner decisions and open questions (`H-`).
- `docs/decision.md` — Claude's reversible defaults (`D-`).
- `docs/specs/NN_*.md` (spec, WHAT) and `NN_*_impl.md` (plan, HOW) per plan step.
- `docs/research/lyric_aesthetics.md` — styling research behind the V1.1+ theme steps.
- `docs/reference/project_context.pdf` — the original Gemini blueprint. Much of it is
  deliberately out of V1 scope (see project_context.md); do not build from it directly.

## Commands

Package installed with `pip install -e .`; always use `venv/Scripts/python`.

```
python -m lyric_engine.cli align songs/<song> [--variant NAME] [--fresh] [--overwrite]
python -m lyric_engine.cli clip songs/<full-song> --from 0:27 --to 0:57 [--out songs/<clip>]
python -m lyric_engine.cli make songs/<song> [--theme NAME]   # align if needed, then render
python -m lyric_engine.cli render songs/<song> [--theme NAME] [--codec prores|png|qtrle]
                               [--allow-flagged]
python -m lyric_engine.cli validate songs/<song>/words.json --song songs/<song>
python -m lyric_engine.cli bakeoff songs/<song> [--fresh]   # compare aligner variants
```

- `--theme`: `soft-romantic-v2` (default, spec 08), `soft-romantic` (v1), `pop-karaoke`,
  `lofi-minimal`, `lofi-typewriter` (spec 09), `cinematic` (spec 10).
- All tests: `venv/Scripts/python -m unittest discover -s tests -t .`
- One module / class / test: `venv/Scripts/python -m unittest tests.test_timing`,
  `... tests.test_timing.EmphasisTest`, or `... tests.test_render -k Emphasis`.
- Gate (`/gate`, from `.claude/devsystem.json`): the unit tests, then
  `venv/Scripts/python scripts/alpha_proof.py`. No linter is configured.
- Tests are offline and need no song files, but layout/render tests use the real fonts in
  `C:/Windows/Fonts` and `fonts/` (bundled Poppins and Cormorant Garamond, OFL) and a short
  real ffmpeg encode.

A song folder: `songs/<song>/` holds `audio.wav|mp3`, `lyrics.txt`, `words.json`,
`render/<theme>/` (outputs + `report.md`, one folder per theme: D-018), `bakeoff/<variant>/`
(`raw.json` aligner cache) and, for a clip, `clip.json`.

## Architecture rule

`src/lyric_engine/` is one package of staged modules:

- `align.py`: audio + `lyrics.txt` → `words.json`; aligner variants, `raw.json` cache, bake-off.
  Engines: `eleven.py` (ElevenLabs forced-alignment API, stdlib HTTP), `local_aligner.py` +
  `vocals.py` (CPU models, imported lazily: torch). `review.py`: preview videos + reports
  (review only, not product output). Never renders the overlay.
- `timing.py`: owns the `words.json` format, lyrics reader (incl. `*word*` emphasis markers),
  flag rules, validator. The only thing align and render share.
- `theme.py` (all look numbers; `THEMES`, and `motion` picks the renderer), `layout.py`
  (fonts with cmap fallback, tracking, balanced wrap), `render/` (`timeline` → `frames`, or
  `karaoke` for Pop Karaoke, or `focus` for Soft Romantic v2: v1's word frames plus a past-line
  stack, or `lofi` for both lofi themes: one line, colour states or typewriter, checked by
  `lofi_check`, or `cinematic`: couplets per stanza, per-word blur-in, checked by
  `cinematic_check`; lofi and cinematic share `lifecycle` (one block on screen at a time)
  → one-pass `encode` → `check`): `words.json` → `render/<theme>/overlay.mov`
  (alpha) + `overlay_green.mp4` + `preview.mp4` (with audio, review).
  Never calls the alignment API, so hand-edit + re-render stays free.
- `workflow.py`: `clip` (cut an aligned song at whole-line boundaries into a new song folder,
  lyrics copied verbatim) and `make` (keeps a valid `words.json`, since it may hold hand
  corrections; refuses a stale one).
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
  outputs. A line with no marked word must stay pixel-identical when layout code changes.

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
