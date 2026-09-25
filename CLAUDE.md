# CLAUDE.md

Kinetic Lyric Engine: a personal tool that turns a song's audio + its Hinglish lyrics into a
word-synced, transparent 9:16 lyric overlay for CapCut.

## Read first

- `docs/project_context.md` — what this is, V1 scope, out-of-scope list, red lines. Do not
  re-ask anything it already answers.
- `docs/development_plan.md` — ordered steps and their status board.
- `docs/pending_work.md` — current focus and next action.
- `docs/human_decision.md` — owner decisions and open questions (`H-`).
- `docs/decision.md` — Claude's reversible defaults (`D-`).
- `docs/reference/project_context.pdf` — the original Gemini blueprint. Much of it is
  deliberately out of V1 scope (see project_context.md); do not build from it directly.

## Architecture rule

`src/lyric_engine/` is one package of staged modules:

- `align.py`: audio + `lyrics.txt` → `words.json` (alignment API). Never renders.
- `timing.py`: owns the `words.json` format. The only thing align and render share.
- `theme.py`, `layout.py`, `render.py`: `words.json` → alpha `.mov` + green-screen mp4.
  `render.py` never calls the alignment API, so hand-edit + re-render stays free.
- `cli.py`: entry point, operating on one `songs/<song>/` folder.

Split a module into a subpackage only when it passes ~300 lines.

## Red lines (also in `.claude/devsystem.json`, checked by `/ship`)

1. Never guess a timing. An unaligned word is flagged and reported, never given an
   estimated timestamp.
2. Never alter the lyrics text. On-screen text matches `lyrics.txt` exactly: spelling,
   casing, line breaks.

## Environment

- Windows 11 laptop: i5-1235U, 8 GB RAM, Intel Iris Xe, no dedicated GPU. No heavy local
  models; rendering is CPU-only.
- Python 3.10.11 in `venv/` (`venv/Scripts/python`). ffmpeg 8.0.1 on PATH.
- Secrets go in `.env` (gitignored), never in code or fixtures.
- `songs/` is gitignored (audio, renders and lyrics are large/copyrighted); only
  `songs/example/lyrics.txt` is tracked, and it is original placeholder text.

## Working with the owner

- Owner-facing replies in Hinglish; docs and code in English.
- Ask only questions whose answer changes what gets built; state assumptions and let the
  owner object.
