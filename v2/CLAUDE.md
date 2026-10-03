# CLAUDE.md (V2)

V2 of the Kinetic Lyric Engine repository, "Voice Subs": a short Hinglish or English video (now
30-40 s; up to 60 min at milestone 1) → a Roman-script `.srt` and the owner's signature
subtitles, a transparent overlay strip with each word lit as it is said. Open source (H-101).
This folder is its own project (H-102): own package, docs and devsystem config.

## Scope of this folder

- **Launch V2 sessions from `v2/`.** devsystem reads `.claude/devsystem.json` from the launch
  folder only; launched from the repo root, it would track V1 instead.
- The root `../CLAUDE.md` also loads here. Its first section maps both systems; the rest is V1's:
  its commands, architecture, invariants and red lines (`lyrics.txt`, `words.json`, themes) do
  not apply to V2.
- A V1 track runs in parallel on the same repository. Never edit a file outside `v2/` from a V2
  session.
- `voice_subs` never imports `lyric_engine` (D-101), so `v2/` can become its own repository.

## Read first

- `docs/project_context.md`: problem, scope, out-of-scope list, success signal, red lines. Do
  not re-ask anything it already answers.
- `docs/development_plan.md` (ordered steps, status board), `docs/pending_work.md` (current
  focus, next action).
- `docs/human_decision.md` (owner decisions, open questions, from H-101) and `docs/decision.md`
  (Claude's reversible defaults, from D-101).
- `docs/specs/NN_*.md` (spec, WHAT) and `NN_*_impl.md` (plan, HOW) per plan step.

## Commands

Use the repository's venv (Python 3.10.11): `C:/subtitle_engine/venv/Scripts/python`. Install
once from `v2/`: `<python> -m pip install -e .` (an editable install points at the folder it was
run from; reinstall after the worktree merges).

```
<python> -m voice_subs.cli subs <video-or-audio> [--out F.srt] [--lang hin|eng] [--work DIR]
                                                 [--fresh] [--devanagari] [--overwrite] [--preview]
```

A 30-40 s video in, its subtitles out (specs 00, 00b). Everything for one file lands in
`voices/<name>-<id>/`, where the id keeps two files both called `clip_01.mp4` apart:
`audio.mp3`, `transcript.json`, `<name>.srt` (plain), `<name>.ass` and `<name>.mov` (the
signature subtitles on a transparent ProRes 4444 strip, each word lit as it is said: the file
the owner drops onto the video in CapCut and places themselves), and with `--preview` a
`preview.mp4` with the strip laid on the video (review only).
`--fresh` transcribes again (a billed call), `--devanagari` keeps the engine's own script.

- All tests (offline, no key, no audio): `<python> -m unittest discover -s tests -t .`
- One test: `<python> -m unittest tests.test_roman` or `... tests.test_cues.SrtTest`.
- Gate (`/gate`): the tests above. No linter is configured.
- `ELEVENLABS_API_KEY` is read from the environment, then `v2/.env`, then the repository root's
  `.env`. In this worktree the root `.env` is absent (gitignored files are not copied into a
  worktree), so set the variable or make a `v2/.env`.

## Architecture rule

`src/voice_subs/` is one package of staged modules that talk through one file,
`transcript.json`, owned by `transcript.py`, which also validates it (format in spec 00):

- `media.py`: ffmpeg. Video or audio → 16 kHz mono mp3; duration; a fingerprint of the audio;
  the transparent overlay strip (alpha by drawing on black and white, D-108); the preview.
  The only module that runs a subprocess.
- `scribe.py`: one POST to ElevenLabs Scribe (D-103), stdlib HTTP, no retry, key never logged.
- `roman.py`: Devanagari → Roman by rules (D-104). Latin is passed through untouched.
- `transcript.py`: the format, its validator, and the staleness check against the audio.
- `cues.py`: timed words → cues (D-105) with display times (D-109) → `.srt` text. No LLM
  (that is step 05). Owns the word lists for words that lean on a neighbour.
- `style.py`: cues + word times → the signature `.ass` for a strip (D-110, D-113): three layers
  per cue (halo, glow, text) sharing one layout; hero-word choice. Fonts (OFL) ship in
  `voice_subs/fonts/`.
- `cli.py`: the command above, and the red-line refusals (never overwrite a transcript or an
  `.srt` without being asked).

Split a module into a subpackage only when it passes ~300 lines.

## Red lines (also in `.claude/devsystem.json`, checked by `/ship`)

1. Never alter the spoken words. Words, spelling and order match the transcript (with the
   user's edits); the LLM only adds punctuation and breaks; every word appears exactly once,
   including at the seams between parts.
2. Never guess a timing. Cue times come from the audio; a stretch that cannot be timed is
   flagged and reported, never estimated.
3. Never overwrite the user's edits silently. A re-run keeps hand corrections, or refuses and
   says why.
4. Keys and voice stay the user's. API keys never reach code, the repo or logs; the voice goes
   only to the services the user configured.

## Environment

- Windows 11 laptop: i5-1235U, 8 GB RAM, no dedicated GPU. No heavy local models. Never run a
  heavy V2 job (gate, long transcription) while the V1 track runs its gate or a full render.
- Secrets in `.env` (gitignored). Voice recordings and their outputs go in `voices/`
  (gitignored), never in fixtures or commits.
- Python written through Bash heredocs loses one level of backslashes; edit code containing
  escapes with the Edit/Write tools.

## Working with the owner

- Owner-facing replies in Hinglish; docs and code in English.
- Ask only questions whose answer changes what gets built; state assumptions and let the owner
  object.
