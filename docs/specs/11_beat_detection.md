# Spec: Beat Detection
**Version:** 1.0.0 | **Component:** new beat stage (`beats.json`), command line, click-track preview
**Status:** Approved by owner 2026-09-28 ("continue"), including the §7 choices. AC10: the owner
chose to merge on the objective check (plan as-built note) without listening first ("Merge + step 12
shuru", 2026-09-28); the preview stays in `songs/khidki_full/` for a later listen.
**Plan step:** 11 (`docs/development_plan.md`) · **Branch:** `feature/beat-detection` · **Decisions:** H-018, H-012, D-022 (amends D-001), D-017, D-002

## 1. Problem Statement

The two themes after this step move with the music, not only with the voice: Beat Pop (step 12)
pops words and shakes on drops, Phonk Neon (step 13) pulses its glow (research §3 shortlist 5
and 6). The engine only knows when each word is sung (`words.json`, from the vocals). Nothing in
it knows where the beat is, so neither theme can be built. Research §10 F left beat data as its
own step; H-018 picked `librosa` and a separate `beats.json`.

## 2. Objective

`beats songs/<song>` writes the song's tempo and beat times to `songs/<song>/beats.json` and a
click-track preview whose clicks land on the kick and snare by ear; every later run, including a
render that needs beats, reuses that file until the audio changes.

## 3. Scope & Constraints

**Will Do:**
- A beat stage: song audio → tempo (BPM) and a list of beat times, computed locally with
  `librosa` (H-018) on the full mix (`audio.wav|mp3`, the same file `align` uses).
- Store them in `songs/<song>/beats.json` beside `words.json` (D-022), readable JSON, times in
  seconds from t=0 of the audio (the overlay's clock), rounded to milliseconds.
- One call that returns a song's beats: reuse `beats.json` while it matches the audio, otherwise
  compute and save it. The `beats` command uses it now; beat themes (steps 12-13) will use it at
  render time, so a missing file costs one detection and every later render is free.
- A new command: `beats songs/<song> [--fresh] [--bpm N]`. It prints the tempo, the beat count and
  any notes, and writes a click-track preview (the song with a short click on every beat) next to
  `beats.json`.
- `--bpm N`: a tempo hint for when detection lands on half or double the real tempo, the usual
  failure. The hint used is recorded in `beats.json`.
- No beats inside a silent stretch of the audio (§4.3).
- Add `librosa` and its dependencies to `requirements.txt`, pinned, as the torch stack is.
- Unit tests on synthetic audio (click tracks, silence), offline, no song files.
- `CLAUDE.md`: the new command, the new module and the second contract.

**Will NOT Do:**
- Create, move or read any word timing. The beat stage never reads `lyrics.txt` or `words.json`
  and never writes `words.json` (red line 1).
- Use beats in any theme. No existing theme changes; its frames stay pixel-identical. Beat Pop
  (step 12) is the first consumer.
- Onset times, beat strengths, downbeats (bar starts), drops or a loudness envelope. No theme
  consumes them yet; step 12 or 13 adds what it needs as a new `beats.json` version (a rebuild
  costs seconds). Downbeats would need a different library (H-018 option b).
- Follow tempo changes inside a song: `librosa` tracks one tempo per song. A song whose tempo
  changes shows it in the preview; fixing that is future work.
- Detect on the isolated vocals or a drum stem (demucs).
- Run beat detection from `align`, `clip` or `make`, or copy beats into a clip. A clip folder gets
  its own `beats.json` from its own audio when first needed, as its words are re-aligned on its
  own audio (spec 05).
- A report file, a visual (video) preview, or a GUI for correcting beats.

**Hard Rules:**
- **Red line 1:** beats are decoration input only. They never create, move or fill in a word
  timing, and a flagged word stays flagged whatever the beats say.
- **Never discard the owner's work:** a `beats.json` the owner edited by hand is used as-is while
  it is valid for the audio; an invalid one is reported, never silently overwritten. Only
  `--fresh`, `--bpm` or changed audio replace it.
- Commands that do not need beats (`align`, `clip`, `render` of the six current themes,
  `validate`, `bakeoff`) never import `librosa` or its dependencies, so they stay as fast as today.
- Local and free: no network, no API call, CPU only (i5-1235U, 8 GB).

## 4. Core Design

### 4.1 Data flow

```
audio.wav|mp3 ──► beat stage (librosa) ──► beats.json ──► (steps 12-13) beat themes
                                   └────► beats_preview (song + clicks, review only)
lyrics.txt + audio ──► align ──► words.json ──► render      (unchanged; no link to beats)
```

Two contracts between stages from now on (D-022): `words.json` (owned by `timing.py`, may hold
hand corrections) and `beats.json` (owned by the new beat module, a cache that can always be
rebuilt). The beat module shares only `align.song_paths` and the audio hash helper with the rest.

### 4.2 `beats.json` (conceptual; exact field names in `/plan`)

| Field | Meaning |
|---|---|
| format version | bumped when a later step adds fields; an older file is rebuilt |
| song | folder name |
| audio | file name, sha256, duration in seconds |
| detector | library name and version, the `--bpm` hint used (or none) |
| tempo | detected BPM (0 when no steady beat was found) |
| beats | ascending beat times in seconds, 3 decimals, each within [0, duration] |

A file is **valid for the song** when its version is current, its audio hash matches the song's
audio, and its beats are numbers, strictly ascending, within [0, duration].

### 4.3 Detection rules

- One tempo for the whole song; beats follow the song's pulse, including through quiet passages
  that still have music.
- A **silent stretch** (near-digital silence, threshold set in `/plan`) longer than two beat
  periods gets no beats, so nothing pulses in a dead stop before a drop or in leading/trailing
  silence.
- With `--bpm N`, beats are tracked at about N BPM.
- No steady beat at all (silence, a cappella, free-time intro-only clip): an empty beat list, tempo
  0, a printed note. This is a result, not an error, and it is saved so later renders do not
  retry.

### 4.4 The reuse call and the command

- Reuse call (for the command and future renders): valid file → return it, detector not run.
  No file, or a file whose audio hash or version is stale → detect, save, return (with a note
  saying why it was rebuilt). An invalid file (bad JSON, unsorted, out of range) → stop with an
  error naming the problem and suggesting `beats --fresh`; the file is left untouched.
- `beats songs/<song>`: runs the reuse call, then writes `beats_preview` (the song with a click
  on each beat; an audio file any player plays, format in `/plan`). If the file was reused and a
  preview already exists, the preview is kept. Prints: tempo, beat count, first and last beat,
  reused or computed, notes.
- `--fresh`: detect again even if the file is valid (overwrites hand edits, by request).
- `--bpm N`: detect again with the hint (implies `--fresh`).

### 4.5 Test song

`songs/khidki_full` (2:52, the full song in hand). If its drums are too soft to judge by ear, the
owner adds a beat-heavy song (Punjabi / party, which step 12 needs anyway) and AC10 runs on it.

## 5. Edge Cases & Error Handling

| Situation | Behaviour |
|---|---|
| No audio or two audio files in the folder | Same error as `align` (shared `song_paths`), nothing written |
| Audio cannot be decoded | Error naming the file; nothing written |
| `librosa` not installed | Only commands that need beats fail, with the install line; everything else works |
| Silence or no steady beat | Empty beats, tempo 0, note; file saved; exit 0 |
| Silent stretch mid-song | No beats inside it (§4.3) |
| Tempo detected at half / double | Audible in the preview; rerun with `--bpm N` |
| Tempo changes mid-song | Beats drift in that section; audible in the preview; out of scope (§3) |
| Very short clip (a few seconds) | Few or no beats; a note if none; not an error |
| Audio replaced (hash differs) | Rebuilt, with a note; old hand edits are meaningless for new audio |
| Older format version | Rebuilt, with a note |
| Hand-edited, still valid | Used as-is by the command and by renders |
| Hand-edited, invalid | Error naming the problem, file untouched, exit non-zero |
| `--bpm` zero, negative or not a number | Argument error before any work |
| Preview cannot be written (ffmpeg fails) | `beats.json` stays saved; the error is reported; exit non-zero |
| `words.json` missing, stale or flagged | Irrelevant: the beat stage never reads it |

## 6. Acceptance Criteria

1. `beats songs/<song>` on a folder with audio writes `beats.json` with every §4.2 field and a
   click-track preview, and prints tempo, beat count, first and last beat, and "computed".
2. Synthetic 120 BPM click track (tests): after the first second, every click has a beat within
   ±50 ms, no beat is farther than 50 ms from a click, and the tempo is within 2% of 120.
3. Synthetic click track with 3 s of silence in the middle: no beat between 0.25 s after the last
   click before the gap and 0.25 s before the first click after it.
4. Silent audio: empty beat list, tempo 0, a note, exit 0, file saved.
5. A second run with no flags does not run the detector (tests: detector not called), prints
   "reused", and leaves `beats.json` byte-identical.
6. Changed audio, `--fresh`, or an older version each rebuild the file; `--bpm 60` on the 120 BPM
   click track gives beats about 1.0 s apart (every other click) and records the hint.
7. A valid hand-edited `beats.json` is returned as-is; an unsorted, out-of-range or unparseable
   one gives an error naming the problem, exit non-zero, and the file is byte-identical after.
8. Red line 1: running `beats` leaves `words.json` byte-identical (or absent if it was absent),
   and all existing theme render tests pass unchanged.
9. Importing the command line and rendering an existing theme does not load `librosa`
   (`librosa` not in `sys.modules`).
10. By ear (owner): on the test song (§4.5), the preview's clicks land on the kick and snare
    across the whole song, and a second `beats` run reports "reused". The cold run on the full
    song finishes within 60 s on this laptop.
11. `requirements.txt` pins `librosa` and its new dependencies; a fresh
    `pip install -r requirements.txt` into the existing venv succeeds; `/gate` passes.

## 7. Choices made for the owner (object to any before `/plan`)

- **Beats and tempo only.** Onsets, beat strength, downbeats and drops wait for the theme that
  uses them (steps 12-13); adding a field is a version bump and a rebuild of seconds. The plan's
  original "beat and onset times" is narrowed on purpose: no consumer, no way to judge onsets by
  ear yet.
- **Full mix, not a drum stem**: kick and snare are in the mix, and demucs costs minutes per song.
- **Render computes a missing `beats.json` once** (D-022): no extra command before a beat theme,
  and it stays free after. Only the `beats` command writes the preview.
- **`--bpm` is the one correction path**, plus hand edits to `beats.json`, which are kept while
  valid. The project's rule that automatic results need a correction path (project_context)
  applies to beats too.
- **No beats in silence**: a pulse or flash in a dead stop looks like a mistake; the beat tracker
  on its own would keep ticking through it.
- **A clip computes its own beats** from its own audio, as it re-aligns its own words (spec 05),
  not a slice of the full song's.
