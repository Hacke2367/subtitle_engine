# Plan: Beat Detection
**Spec:** `docs/specs/11_beat_detection.md` (v1.0.0, approved by owner 2026-09-28)
**Branch:** `feature/beat-detection` · **Decisions:** H-018, D-022, D-001, D-002
**Work split:** one developer, in the build order of §11 (no agents).

> **As built (2026-09-28), where it differs from the text below:**
> - `BeatsResult` also carries `audio: Path`, so `cli._beats` passes it to `write_preview`
>   without a second `song_audio` lookup.
> - `stale_reason` never raises: a non-dict, or a version that is not an older int, falls through
>   to `problems`, which reports `"not a JSON object"` / `"version 9 is not one this engine
>   writes (1)"`. Same outcome as §5.2 steps 1-2 (`BeatsError`, file untouched), one code path.
> - `cli._bpm` reads `MIN_BPM` / `MAX_BPM` from `beats` (no librosa: it loads only inside
>   `detect` / `write_preview`); `_beats` also catches `ModuleNotFoundError` around the preview.
> - Measured: `beats songs/khidki_full --fresh` 15.8 s wall in a fresh process (numba cache warm),
>   143.55 BPM, 410 beats; second run `(reused)`. `tests.test_beats` 25 tests, 14 s; a disabled
>   silence mask fails `test_silent_gap`, hop 512 fails `test_click_track`. Gate: 283 tests OK,
>   alpha proof passes.

Numbers below come from a spike on this laptop (2026-09-28, scratchpad, not committed): librosa
0.11.0 installed into `venv/`, synthetic click tracks and `songs/khidki_full` (172 s mp3).

| Spike result | Value |
|---|---|
| First `beat_track` ever (numba compiles, then caches in site-packages) | 33 s, once |
| Later processes: import + first call | 0.1 s + 4.5 s |
| `khidki_full`: ffmpeg decode + detection (warm) | 0.8 s + 1.3 s; 143.55 BPM, 410 beats |
| 120 BPM clicks, `hop_length` 512 (default) | 117.45 BPM; first and last click missed |
| 120 BPM clicks, `hop_length` 256 | 120.19 BPM; every click matched, worst 19 ms |
| Clicks with 3.5 s of silence in the middle | librosa puts 6 beats in the silence; the §5.5 mask removes all 6 |
| 10 s of digital silence | tempo 0, no beats, no exception |
| `bpm=60` on 120 BPM clicks | beats 1.0 s apart (every other click) |
| `khidki_full` quietest 1 % of RMS frames | 0.026 (≈ −32 dBFS): no silent stretch, the mask changes nothing |

## 1. Files

| Action | File | Reason |
|---|---|---|
| CREATE | `src/lyric_engine/beats.py` | the beat stage: decode, detect, silence mask, `beats.json` read/write/validate, reuse call, click preview |
| MODIFY | `src/lyric_engine/align.py` | `song_audio(song_dir)` split out of `song_paths`, so beats never needs `lyrics.txt` |
| MODIFY | `src/lyric_engine/timing.py` | `_is_num` → `is_num` (public; beats validates numbers the same way) |
| MODIFY | `src/lyric_engine/cli.py` | `beats` command, `_bpm` argument type, `_beats` printer, docstring |
| MODIFY | `requirements.txt` | `librosa==0.11.0` block + its pinned transitive dependencies |
| CREATE | `tests/test_beats.py` | detection, reuse, rebuild, hand edits, preview, CLI, import isolation |
| MODIFY | `CLAUDE.md` | command, song-folder files, `beats.py` in the architecture, second contract |
| MODIFY | `docs/decision.md` | D-023: the plan's exact numbers (§2.2-2.5) |
| MODIFY | `docs/development_plan.md`, `docs/pending_work.md`, `docs/session_log.md` | status, resume point, session |

`render/`, `theme.py`, `layout.py`, `review.py`, `workflow.py`, `eleven.py`, `local_aligner.py`,
`vocals.py`: no change. `songs/` stays gitignored (D-002), so `beats.json` and the preview are
never committed.

## 2. Architecture Decisions

1. **A new flat module `beats.py`, a peer of `align.py`.** D-022 makes `beats.json` a second
   contract with its own owner module, as `timing.py` owns `words.json`. Rejected: inside
   `align.py` (alignment concerns, 231 lines, and re-align must not touch beats: spec §3) or
   `review.py` (bake-off review only, 295 lines).
2. **Decode with ffmpeg to mono float32 at 22 050 Hz through a pipe, not `librosa.load`.**
   `AUDIO_EXTS` accepts `.m4a/.aac/.mp4/.mov/.mkv/.webm`, which `soundfile` cannot read, and
   librosa's audioread fallback is deprecated. ffmpeg is already the project's decoder (probe,
   clip, preview) and resamples in the same step. Rejected: `librosa.load` (format gaps, a second
   resampler).
3. **`hop_length = 256`, not the default 512.** Spike: 512 read 120 BPM as 117.45 (fails AC2's
   2 %) and trimmed the first and last click; 256 gave 120.19 with every click within 19 ms.
   Cost: 1.3 s on a full song.
4. **`--bpm N` passes `bpm=N` (a fixed tempo), not `start_bpm` (a prior).** A correction must be
   obeyed; a prior can be overridden by the same octave error it is meant to fix.
5. **Silence mask (spec §4.3): RMS frames of 2048 samples at hop 256; a frame is silent below
   −50 dBFS; a run of silent frames longer than 2 beat periods (`2 × 60 / tempo`) removes every
   beat inside it.** −50 dBFS is near-digital silence: a quiet verse or a reverb tail stays
   above it (khidki_full's quietest 1 % is −32 dBFS). Rejected: an onset-strength threshold (a
   sparse vocal passage has weak onsets but is still music with a pulse).
6. **Reuse rule: a file is reused when its `version` is current, its `audio.sha256` matches, and
   `problems()` is empty. Detector settings (hop, library version, `bpm_hint`) never make it
   stale.** Spec §4.4: a render (no hint) must reuse a file made with `--bpm`, and hand edits
   survive. Rejected: `align._cache_key`'s settings-in-the-key approach, which would drop the
   owner's `--bpm` fix on the next render.
7. **Stale is checked before invalid.** Changed audio or an older version rebuilds even a
   hand-broken file (its beats belong to other audio or an old format); only a file that is
   current *and* broken is an error. A version that is not an integer, or newer than
   `BEATS_VERSION`, is an error (the file was not made by this engine).
8. **`beats.json` is written with `json.dumps(indent=2)`: one beat per line**, the easiest shape
   to hand-edit. Loaded as `utf-8-sig`, like `load_words` (an editor may add a BOM).
9. **The preview mixes the original audio file (full quality) with a click track synthesised by
   `librosa.clicks` at 22 050 Hz and piped to ffmpeg as raw f32le; output AAC in
   `beats_preview.m4a`.** Audio only, as the spec's check is by ear; ~4 MB per song. Rejected: a
   video (spec §3 Will NOT), WAV (30-60 MB per song).
10. **`beats.py` returns data; `cli._beats` prints**, as `cli._render` does. Future renders call
    `beats.ensure_beats` directly and print its notes their own way.
11. **librosa is imported inside `detect` and `write_preview` only; `cli.py` imports `beats`
    inside `_beats` only.** Spec Hard Rule: nothing else loads librosa, numba, scipy, sklearn or
    soundfile (checked today: none of them is in `sys.modules` after importing `cli`, `render`,
    `workflow`, `align`, `review`).
12. **`align.song_audio` split out of `song_paths`**: the same audio lookup and error message
    (spec §5), without requiring `lyrics.txt`, which the beat stage never reads.

## 3. Data Structures

### 3.1 `beats.json` (key order = order on disk)

| Key | Type | Enforces |
|---|---|---|
| `version` | int, `BEATS_VERSION` = 1 | older → rebuild; newer / not int → error (§2.7) |
| `song` | str, folder name | readability |
| `audio.file` | str, e.g. `audio.mp3` | readability |
| `audio.duration_s` | number > 0, decoded samples / 22050, 3 decimals | beat range check |
| `audio.sha256` | hex str | staleness (§2.6) |
| `detector.library` / `.version` | `"librosa"`, `librosa.__version__` | provenance only |
| `detector.sample_rate` / `.hop_length` | 22050 / 256 | provenance only |
| `detector.bpm_hint` | number or null | records `--bpm` (spec §3) |
| `created` | ISO time, seconds | as `words.json` |
| `tempo_bpm` | number ≥ 0, 2 decimals; 0 when no beats | spec §4.3 |
| `beats` | list of numbers, 3 decimals, strictly ascending, each in [0, `duration_s`] | spec §4.2 |

### 3.2 `beats.py`

- `BEATS_FILE = "beats.json"`, `PREVIEW_FILE = "beats_preview.m4a"`, `BEATS_VERSION = 1`
- `SR = 22050`, `HOP = 256`, `RMS_FRAME = 2048`, `SILENT_DBFS = -50.0`, `SILENT_MIN_BEATS = 2`
- `MIN_BPM, MAX_BPM = 30, 300` (the `--bpm` range)
- `CLICK_HZ = 1500`, `CLICK_S = 0.05`, `CLICK_GAIN = 0.5`, `SONG_GAIN = 0.8` (mix headroom)
- `class BeatsError(ValueError)`: a user-facing problem (undecodable audio, invalid file).
- `@dataclass(frozen=True) Detection`: `tempo: float`, `beats: list[float]`,
  `silent: list[tuple[float, float]]` (the stretches that removed at least one beat, seconds).
- `@dataclass BeatsResult`: `path: Path`, `doc: dict`, `reused: bool`, `notes: list[str]`.

## 4. Function Specifications

### `align.py`
- `song_audio(song_dir: Path) -> Path`: the one `audio.<ext>` with an ext in `AUDIO_EXTS`.
  Raises `FileNotFoundError("<dir>: expected exactly one audio.<ext> file, found N")` (today's
  text). `song_paths` calls it, then checks `lyrics.txt` as now.

### `timing.py`
- `is_num(x) -> bool`: the renamed `_is_num`, body unchanged; its four call sites renamed.

### `beats.py`
- `decode(audio: Path) -> np.ndarray`: runs `ffmpeg -v error -i <audio> -map 0:a:0 -f f32le
  -ac 1 -ar 22050 pipe:1`, returns `np.frombuffer(..., float32)`. Raises `BeatsError`:
  `"ffmpeg not found on PATH"`, `"cannot decode <name>: <last stderr line>"`, `"<name> has no
  audio samples"`.
- `detect(y: np.ndarray, sr: int = SR, bpm: float | None = None) -> Detection`: §5.1. Pure: no
  files. Lazy-imports librosa.
- `make_doc(song: str, audio: Path, sha: str, duration_s: float, det: Detection,
  bpm: float | None) -> dict`: the §3.1 document.
- `save_beats(path: Path, doc: dict) -> None`: `json.dumps(doc, indent=2) + "\n"`, utf-8, `\n`.
- `load_beats(path: Path) -> dict`: `json.loads(read_text("utf-8-sig"))`; `JSONDecodeError` →
  `BeatsError("<path>: not valid JSON at line L, column C: <msg>; fix it or run
  beats <song> --fresh")`.
- `stale_reason(doc, sha: str) -> str | None`: §5.2 steps 1-3.
- `problems(doc) -> list[str]`: §5.2 step 4.
- `ensure_beats(song_dir: Path, *, fresh: bool = False, bpm: float | None = None) ->
  BeatsResult`: the reuse call, §5.3. Raises `BeatsError`, `FileNotFoundError`.
- `write_preview(audio: Path, doc: dict, out: Path) -> Path`: §5.4. Raises `RuntimeError`
  (`"ffmpeg not found on PATH"`, `"ffmpeg preview failed for <name>: <tail>"`), as
  `review.render_preview`.

### `cli.py`
- `_bpm(text: str) -> float`: argparse type. Not a float, or outside 30-300 →
  `ArgumentTypeError("not a tempo: '<text>' (use a BPM between 30 and 300)")`.
- `_beats(song: Path, fresh: bool, bpm: float | None) -> int`: §5.5.
- `main`: subparser `beats` (`song_dir`, `--fresh`, `--bpm` with `type=_bpm`), dispatched before
  `_validate`. `FileNotFoundError` is caught by the existing handler (exit 2).

## 5. Logic Flow

### 5.1 `detect`
1. `tempo, t = librosa.beat.beat_track(y=y, sr=sr, hop_length=HOP, units="time", **({"bpm":
   bpm} if bpm else {}))`; `tempo = float(np.atleast_1d(tempo)[0])`.
2. If `t` is empty: return `Detection(0.0, [], [])`.
3. `rms = librosa.feature.rms(y=y, frame_length=RMS_FRAME, hop_length=HOP)[0]`; silent where
   `rms < 10 ** (SILENT_DBFS / 20)`. Runs of silent frames longer than
   `ceil(SILENT_MIN_BEATS × 60 / tempo × sr / HOP)` frames → spans `(start × HOP / sr,
   end × HOP / sr)`. Drop every beat inside a span; keep the spans that dropped one.
4. Round beats to 3 decimals and drop a repeat (cannot happen at 11.6 ms per frame; guards the
   strictly-ascending rule). If nothing is left, tempo becomes 0 (spec §4.3).
5. Return `Detection(round(tempo, 2), beats, spans)`; with a hint, librosa returns the hint as
   the tempo.

### 5.2 Validity of a loaded `doc`
1. Not a dict → invalid: `"beats.json: not a JSON object"`.
2. `version` not an int (bool excluded), or `> BEATS_VERSION` → `BeatsError("beats.json: version
   <v> is not one this engine writes; run beats <song> --fresh")`. `< BEATS_VERSION` → stale:
   `"older format (version <v>)"`.
3. `audio` not a dict or `audio.sha256 != sha` → stale: `"audio changed"`.
4. `problems`: `audio.duration_s` not `is_num` or ≤ 0; `tempo_bpm` not `is_num` or < 0; `beats`
   not a list; first non-number (`"beats[i] is not a number"`); first out of range
   (`"beats[i] = x is outside 0-<duration> s"`); first not strictly ascending (`"beats[i] = x is
   not after beats[i-1] = y"`). Returns every message found, each check at most once.

### 5.3 `ensure_beats`
1. `audio = align.song_audio(song_dir)`; `path = song_dir / BEATS_FILE`; `sha =
   timing.sha256_file(audio)`; `notes = []`.
2. If `path` exists and not `fresh` and `bpm is None`:
   - `doc = load_beats(path)` (may raise); `reason = stale_reason(doc, sha)` (may raise).
   - If `reason` is None: `probs = problems(doc)`; if `probs` → `BeatsError("beats.json is not
     valid:\n  " + "\n  ".join(probs) + "\nfix it or run beats <song> --fresh")`, file untouched;
     else → `BeatsResult(path, doc, reused=True, notes=[])`.
   - Else `notes.append(f"{reason}: beats rebuilt")`.
3. `y = decode(audio)`; `det = detect(y, SR, bpm)`; `duration = round(len(y) / SR, 3)`.
4. Notes: `bpm` → `"tempo hint: <bpm> BPM"`; no beats → `"no steady beat found: beats.json has
   no beats"`; each span → `"no beats in silence <a>-<b> s"`.
5. `doc = make_doc(song_dir.name, audio, sha, duration, det, bpm)`; `save_beats(path, doc)`;
   return `BeatsResult(path, doc, reused=False, notes)`.

### 5.4 `write_preview`
1. `clicks = librosa.clicks(times=doc["beats"], sr=SR, length=round(duration × SR),
   click_freq=CLICK_HZ, click_duration=CLICK_S) × CLICK_GAIN`, as little-endian float32 bytes
   (zeros when there are no beats).
2. `ffmpeg -hide_banner -loglevel error -y -i <audio> -f f32le -ar 22050 -ac 1 -i pipe:0
   -filter_complex "[0:a:0]volume=0.8[s];[1:a]volume=1[c];[s][c]amix=inputs=2:duration=first:
   normalize=0[a]" -map "[a]" -c:a aac -b:a 160k <out>`, clicks on stdin.
3. `FileNotFoundError` → `RuntimeError("ffmpeg not found on PATH")`; non-zero exit →
   `RuntimeError` with the last 5 stderr lines. Return `out`.

### 5.5 `cli._beats`
1. `from . import beats`. `result = beats.ensure_beats(song, fresh=fresh, bpm=bpm)`;
   `BeatsError` → `error: <msg>` on stderr, return 2.
2. `preview = song / beats.PREVIEW_FILE`. If `not result.reused or not preview.exists()`:
   `write_preview(audio, result.doc, preview)`; `RuntimeError` → remember it.
3. Print:
   ```
   beats.json: <path> (computed|reused)
   preview: <preview>
   tempo: 143.55 BPM  beats: 410  first: 0.093 s  last: 171.317 s
   note: <each note>
   ```
   With no beats the third line is `tempo: 0 BPM  beats: 0`. On a preview error the `preview:`
   line is replaced by `error: <msg>` on stderr and the exit code is 1; otherwise 0.

## 6. Edge Case Implementation Map

| Spec §5 case | Mechanism | Location |
|---|---|---|
| No / two audio files | `song_audio` raises `FileNotFoundError`; `main` prints, exit 2; nothing written | `align.song_audio`, `cli.main` |
| Undecodable audio | ffmpeg non-zero or no samples → `BeatsError`; raised before `save_beats` | `beats.decode` |
| librosa not installed | `ModuleNotFoundError` from the lazy import, only in `beats` paths; `_beats` catches it → `error: librosa is not installed: pip install -r requirements.txt`, exit 2 | `beats.detect`, `cli._beats` |
| Silence / no steady beat | empty `Detection`, tempo 0, note; file saved; exit 0 | `detect` §5.1.2, `ensure_beats` §5.3.4 |
| Silent stretch mid-song | RMS mask | `detect` §5.1.3 |
| Half / double tempo | `--bpm` → `bpm=` | `cli._bpm`, `detect` |
| Tempo change mid-song | not handled (spec §3); audible in the preview | — |
| Very short clip | same path; note if no beats | `detect` |
| Audio replaced | `stale_reason` → `"audio changed"` → rebuild + note | §5.2.3 |
| Older format | `stale_reason` → rebuild + note | §5.2.2 |
| Hand-edited, valid | reused as-is | §5.3.2 |
| Hand-edited, invalid | `BeatsError` with every problem, file untouched, exit 2 | `problems`, §5.3.2 |
| `--bpm` 0 / negative / text | `_bpm` → argparse error, exit 2, before any work | `cli._bpm` |
| Preview fails | `beats.json` already saved; `error:` + exit 1 | `cli._beats` §5.5.3 |
| `words.json` missing / stale / flagged | never opened | `beats.py` has no reference to it |

## 7. File Layout

`beats.py`, in order: module docstring (what `beats.json` is, D-022, red line 1: decoration only,
no word timing); imports (stdlib, `numpy`, `from . import align, timing`); constants (§3.2);
`BeatsError`, `Detection`, `BeatsResult`; `ensure_beats` (the entry point, first); `decode`;
`detect`; `make_doc`, `save_beats`, `load_beats`; `stale_reason`, `problems`; `write_preview`.
Target ≤ 200 lines.

`tests/test_beats.py`: helpers (`clicks(times, dur)` via `librosa.clicks`, `write_wav(path, y)`
via stdlib `wave` as 16-bit PCM, `song_dir(tmp, y)`), then `DetectTest`, `EnsureTest`,
`HandEditTest`, `PreviewTest`, `CliBeatsTest`, `ImportIsolationTest`.

## 8. Dependencies

- `beats.py` imports: `json`, `math`, `subprocess`, `datetime`, `dataclasses`, `pathlib`,
  `numpy`; `align` (`song_audio`), `timing` (`sha256_file`, `is_num`); librosa lazily.
- `cli.py` → `beats` (lazy). Nothing else imports `beats` in this step; steps 12-13 will call
  `beats.ensure_beats` from their renderer.
- `requirements.txt`: new block after the torch block, then the new transitive pins merged
  alphabetically into the existing list, versions from `pip freeze` (installed during the spike):
  `audioread, certifi, cffi, charset-normalizer, decorator, idna, joblib, lazy_loader,
  llvmlite, msgpack, numba, packaging, platformdirs, pooch, pycparser, requests, scikit-learn,
  scipy, soundfile, soxr, threadpoolctl, urllib3`. `numpy==2.2.6` stays (numba 0.67 accepts it).
- Conflicts: none. `song_paths`' behaviour and message are unchanged; `is_num` is a rename with
  four call sites, all in `timing.py`.
- Not built yet: any consumer of `beats.json` (step 12).

## 9. Hard Boundaries

- [x] `beats.py` never reads `lyrics.txt` or `words.json`, never calls `timing.read_lyrics`,
  `load_words` or `save_words`, and writes only `beats.json` and `beats_preview.m4a`.
- [x] No word timing is created, moved or filled from beats (red line 1).
- [x] An invalid, current `beats.json` is never overwritten without `--fresh` or `--bpm`.
- [x] No network, no API call; CPU only.
- [x] librosa, numba, scipy, sklearn, soundfile are never imported at module top by `cli`,
  `align`, `timing`, `workflow`, `review` or `render`.
- [x] No theme, renderer or render check changes; existing render tests pass untouched.
- [x] `clip`, `make`, `align`, `render` never call `ensure_beats` in this step.

## 10. Acceptance Criteria (runnable)

`$PY` = `venv/Scripts/python`.

1. **Command:** `$PY -m lyric_engine.cli beats songs/khidki_full --fresh` → exit 0, prints
   `beats.json: ... (computed)`, `preview: ...beats_preview.m4a`, `tempo: <n> BPM  beats: <n>
   first: ... last: ...`; `beats.json` has every §3.1 key. Unit: `$PY -m unittest
   tests.test_beats -k CliBeats` → `OK`.
2. **Accuracy:** `$PY -m unittest tests.test_beats -k test_click_track` → `OK` (120 BPM clicks
   for 20 s: every click after 1 s has a beat within ±50 ms, no beat is farther than 50 ms from
   a click, tempo within 2 % of 120).
3. **Silent gap:** `-k test_silent_gap` → `OK` (clicks to 9.5 s, silence, clicks from 13.0 s: no
   beat in 9.75-12.75 s; one `silent` span reported).
4. **Silence:** `-k test_silence` → `OK` (tempo 0, no beats, no exception; through
   `ensure_beats`: file saved, note present).
5. **Reuse:** `-k test_reuse` → `OK` (second `ensure_beats` with `detect` patched: not called,
   `reused` True, file bytes identical). Real: a second `beats songs/khidki_full` prints
   `(reused)`.
6. **Rebuild:** `-k Rebuild` → `OK` (new audio bytes → rebuilt + `"audio changed"` note;
   `fresh=True` → detect called; `version: 0` → rebuilt + `"older format"`; `bpm=60` on the
   120 BPM clicks → median gap 1.0 ± 0.05 s, `bpm_hint` 60).
7. **Hand edits:** `-k HandEdit` → `OK` (a beat removed → returned as-is, detect not called;
   unsorted, out-of-range, `"x"` in `beats`, truncated JSON, `version: 9` → `BeatsError`
   naming the problem, file bytes identical).
8. **Red line 1:** `-k test_words_untouched` → `OK` (a `words.json` in the folder is
   byte-identical after `ensure_beats`; without one, none is created). Full suite: `$PY -m
   unittest discover -s tests -t .` → `OK`.
9. **Import isolation:** `-k ImportIsolation` → `OK` (a subprocess imports `lyric_engine.cli`,
   `.render`, `.workflow`, `.align`, `.review`; none of `librosa`, `numba`, `scipy`, `sklearn`,
   `soundfile` is in `sys.modules`).
10. **By ear (owner):** plays `songs/khidki_full/beats_preview.m4a`; the clicks sit on the kick
    and snare across the song (if the tempo is doubled or halved: rerun with `--bpm`, then
    judge). If the drums are too soft to judge, the same on a beat-heavy song the owner adds.
    Time: the AC1 command (a fresh process) finishes in ≤ 60 s, measured with `time`.
11. **Install + gate:** `$PY -m pip install -r requirements.txt --dry-run` prints no `Would
    install` line; `/gate` → unit tests `OK`, alpha proof passes.

## 11. Build order

1. `requirements.txt` pins from `pip freeze` (librosa is already in `venv/` from the spike) →
   AC11 dry run.
2. `align.song_audio`, `timing.is_num` rename → `tests.test_align`, `tests.test_timing` `OK`.
3. `beats.detect` + `DetectTest` (AC2, AC3, AC4, bpm part of AC6).
4. Document, validity, `ensure_beats` + `EnsureTest`, `HandEditTest` (AC4-AC8).
5. `write_preview` + `PreviewTest` (m4a exists, ffprobe duration within 0.1 s of the audio).
6. `cli` `beats` + `CliBeatsTest` (incl. `--bpm 0` → exit 2), `ImportIsolationTest` (AC9).
7. Real runs: AC1, AC5, AC10 timing on `khidki_full`; D-023 in `decision.md` (§2.2-2.5
   numbers); `CLAUDE.md`; gate; `/ship`; ask the owner for AC10 by ear.
