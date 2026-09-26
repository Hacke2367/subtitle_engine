# Plan: Word Alignment → `words.json`
**Spec:** `docs/specs/02_word_alignment.md` (v1.1.0, approved via H-007)
**Branch:** `feature/word-alignment`
**Work split:** three parallel agents with disjoint files (T, E, L), plus the integrator. §1 names each file's owner.

## 1. Files

| Action | File | Owner | Reason |
|---|---|---|---|
| CREATE | `pyproject.toml` | integrator | `pip install -e .` so `lyric_engine` imports in the CLI and tests. |
| MODIFY | `src/lyric_engine/timing.py` | **T** | Lyrics reader, `words.json` model/IO/validator, flag rules (D-001: owns the format). |
| CREATE | `tests/test_timing.py` | **T** | AC1–3. |
| CREATE | `src/lyric_engine/eleven.py` | **E** | ElevenLabs forced-alignment client + 1:1 mapping (stdlib HTTP). |
| CREATE | `src/lyric_engine/review.py` | **E** | Preview video (ASS burn-in), run report, comparison report. |
| CREATE | `tests/test_eleven.py`, `tests/test_review.py` | **E** | Mapping, redaction, multipart, disagreement maths; no network. |
| CREATE | `src/lyric_engine/vocals.py` | **L** | Vocal isolation, cached. |
| CREATE | `src/lyric_engine/local_aligner.py` | **L** | Local CPU CTC forced alignment. |
| MODIFY | `requirements.txt` | **L** only | Pin the local-pipeline dependencies. |
| MODIFY | `src/lyric_engine/align.py` | integrator | Variant table, cache, orchestration (`run_variant`, `bakeoff`, `align_song`, `verify_against_raw`). |
| MODIFY | `src/lyric_engine/cli.py` | integrator | `bakeoff`, `align`, `validate` commands. |
| CREATE | `tests/test_align.py` | integrator | Cache reuse (AC8) and raw-vs-words check (AC6) with fake engines. |
| MODIFY | `.claude/devsystem.json`, `.gitignore`, `CLAUDE.md`, docs | integrator | Unit-test gate command, `*.egg-info/`, module list, decisions. |

## 2. Architecture Decisions

1. **One aligner contract, 1:1 with the lyrics words:** `align(audio: Path, words: list[str]) -> (list[RawWord], native: dict)`.
   Aligners never return text, only times per input index, so red line 2 holds by construction.
2. **Flagging and validation live only in `timing.py`**, so every variant is judged by the same rules (spec §4).
3. **Cache = `raw.json` per variant**, keyed by sha256(input audio bytes) + sha256(`lyrics.txt`) + variant name +
   `SETTINGS_VERSION`. `words.json` is always rebuilt from `raw.json`. That makes AC6 checkable and prevents
   re-billing (AC8). Times are rounded to 3 decimals *before* caching, so the equality checks are exact.
4. **Stdlib HTTP for ElevenLabs** (`urllib` + a hand-built multipart body) and a 5-line `.env` reader, instead of
   `requests`/`python-dotenv` for a single endpoint. No retry: one call per variant per run (spec §7).
5. **ElevenLabs score = `1/(1+loss)`** (higher is better, monotonic; the loss scale is undocumented). **Local score** =
   mean posterior probability of the word's tokens (0..1).
6. **`low_confidence` thresholds start disabled (`min_score=None`)** and are calibrated on the clip. Run reports always
   list the 10 lowest-scoring words. The structural flags (`not_placed`, `bad_duration`, `out_of_order`,
   `out_of_bounds`) are active from day one.
7. **Preview = ASS subtitles burned onto a black 540×960 video with the audio** (libass is present in this ffmpeg build).
   It's fast and review-only.
8. **Local stack chosen by agent L** against these criteria: installs on Python 3.10 CPU-only, peak RAM ≤ 5 GB, handles
   romanized Latin text. Candidates: vocals via Demucs `htdemucs` (or `audio-separator`); alignment via torchaudio's
   MMS_FA bundle (if the pinned torchaudio still ships it) or the `ctc-forced-aligner` package. The choice is recorded
   as a D- entry.
9. **Tests use stdlib `unittest`.** No pytest dependency.
10. **The test clip is cut by the integrator with ffmpeg** (lossless WAV) at line boundaries. This is a one-off; no clip
    feature (YAGNI).

## 3. Data Structures (`timing.py`)

```python
WORDS_VERSION = 1
REASONS = ("not_placed", "low_confidence", "bad_duration", "out_of_order", "out_of_bounds")
MAX_WORD_S = 6.0        # a single sung word longer than this is implausible
OVERLAP_TOL_S = 0.10    # allowed overlap with the previous placed word
BOUNDS_TOL_S = 0.05     # allowed overshoot past the audio end
MOSTLY_FLAGGED = 0.30   # above this share → "lyrics probably don't match audio"

class LyricsError(ValueError): ...

@dataclass
class Lyrics:
    path: Path
    sha256: str                     # of the file's bytes
    lines: list[str]                # verbatim, newline stripped, blank lines kept as ""
    words: list[tuple[str, int]]    # (verbatim token from line.split(), line index)

@dataclass
class RawWord:                      # aligner output, 1:1 with Lyrics.words
    start: float | None
    end: float | None
    score: float | None

@dataclass
class Word:
    index: int
    text: str
    line: int
    start: float | None
    end: float | None
    score: float | None
    flagged: bool = False
    reasons: list[str] = field(default_factory=list)
```

`words.json` (the doc is a plain dict; exact keys):

```json
{
  "version": 1,
  "song": "khidki",
  "audio":  {"file": "audio.wav", "duration_s": 30.125, "sha256": "…"},
  "lyrics": {"file": "lyrics.txt", "sha256": "…", "lines": ["Mere saamne waali khidki mein", "…", ""]},
  "aligner": {"variant": "L-vocals", "input": "vocals", "settings": {}, "reused_cache": false},
  "created": "2026-09-26T19:00:00",
  "words": [
    {"i": 0, "text": "Mere", "line": 0, "start": 1.234, "end": 1.61, "score": 0.93, "flagged": false, "reasons": []}
  ]
}
```

On disk the header is indented 2 spaces and each word object sits on its own line (hand-editable).

## 4. Function Specifications

**`timing.py` (T)**

| Function | Behaviour | Raises |
|---|---|---|
| `sha256_file(path) -> str` | hex digest of bytes | — |
| `read_lyrics(path) -> Lyrics` | UTF-8 (BOM tolerated). Any of `()[]{}` on a line → error naming line N (1-based) and asking for repeats written out. No words at all → error. | `LyricsError` |
| `normalize(word) -> str` | lowercase, keep only `[a-z0-9']`; helper for aligners | — |
| `build_words(lyrics, raw) -> list[Word]` | zip 1:1, text/line from lyrics, times/score from raw | `ValueError` if lengths differ |
| `apply_flags(words, duration_s, min_score) -> None` | clears then sets `reasons` in `REASONS` order; `flagged = bool(reasons)`. `not_placed`: start or end None. `low_confidence`: min_score set and score not None and score < min_score. `bad_duration`: end ≤ start or end − start > MAX_WORD_S. `out_of_order`: vs previous *placed* word: start < prev.start or start < prev.end − OVERLAP_TOL_S. `out_of_bounds`: start < 0 or end > duration_s + BOUNDS_TOL_S. | — |
| `flag_summary(words) -> dict` | `{"total", "flagged", "share", "by_reason": {…}, "mostly_flagged": share > MOSTLY_FLAGGED}` | — |
| `make_doc(song, audio_path, duration_s, audio_sha, lyrics, aligner, words) -> dict` | builds the §3 dict; `created` = local ISO seconds | — |
| `save_words(path, doc)` / `load_words(path) -> dict` | layout per §3 / `json.load` | — |
| `validate(doc, lyrics_path=None, audio_path=None) -> list[str]` | Returns errors (empty = valid): version; word texts + line indexes == tokens of `doc.lyrics.lines`; `i` contiguous from 0; reasons ⊆ REASONS; not flagged → numeric start/end with 0 ≤ start < end ≤ duration + BOUNDS_TOL_S; flagged → reasons non-empty; placed non-flagged starts non-decreasing; stale lyrics/audio via sha256 when paths are given. Each message starts `word <i> ("<text>"):` when it concerns a word. | — |

**`eleven.py` (E)**

| Function | Behaviour | Raises |
|---|---|---|
| `load_api_key(env_path=REPO/".env") -> str \| None` | `ELEVENLABS_API_KEY` from the environment first, then the `.env` line | — |
| `redact(text, key) -> str` | replaces the key with `<redacted>` | — |
| `align(audio, words, *, api_key=None, timeout_s=300) -> (list[RawWord], dict)` | POST multipart `file` + `text` (= `" ".join(words)`) to `https://api.elevenlabs.io/v1/forced-alignment`. Parse `words` from the response, drop whitespace-only entries. Equal count → map by index. Otherwise → sequential match on `normalize()`, with unmatched → `RawWord(None, None, None)`. Times rounded to 3 dp; score `1/(1+loss)`. native = the full response + `{"mapping": "index" \| "sequential", "unmatched": n}` | `ElevenLabsError` (no key; HTTP ≥ 400 with the redacted body[:300]; network error; bad JSON) |

**`vocals.py` (L)**

| Function | Behaviour | Raises |
|---|---|---|
| `isolate_vocals(audio, out_wav, *, fresh=False) -> Path` | vocals stem as WAV with the **same timeline and duration as the input** (±1 frame). Cache sidecar `out_wav.with_suffix(".json")` = `{"source_sha256", "model"}`; reused when it matches and not `fresh`. | `RuntimeError` with a clear message on model or memory failure |

**`local_aligner.py` (L)**

| Function | Behaviour | Raises |
|---|---|---|
| `align(audio, words) -> (list[RawWord], dict)` | 16 kHz mono; emissions (chunked if needed for RAM); CTC forced alignment of the `normalize()`d words. Words that normalise to `""` → `RawWord(None, None, None)` and are excluded from the token sequence. Times rounded to 3 dp; score = mean token probability. native = `{"model", "frame_s", "n_tokens", …}` (small). | `RuntimeError` |

**`review.py` (E)**

| Function | Behaviour |
|---|---|
| `write_ass(doc, out_ass, *, title)` | PlayRes 540×960. Per line, a base event (layer 0) from the first placed word start − 0.25 s to the last placed word end + 0.25 s, with all words white and flagged words red. Per placed, non-flagged word, a layer 1 event over [start, next placed word start or end]: the same text at the same `\pos`, only that word visible (others `\alpha&HFF&`), in highlight colour. Title (variant name) top-left. A per-second `mm:ss` clock event top-right. |
| `render_preview(doc, audio, out_mp4, *, title) -> Path` | ffmpeg: `color=black:s=540x960:r=25` for the audio duration + audio, `-vf ass=<name>` run with `cwd` = the `.ass` folder (avoids escaping `C:`), libx264 veryfast crf 28 + aac, `-shortest`. |
| `write_run_report(doc, out_md, *, wall_s, reused, cost_note=None)` | variant, wall time, reused yes/no, flag summary, a table of every flagged word (i, text, line+1, start, end, score, reasons), the 10 lowest-score words, a mostly-flagged warning. |
| `write_comparison(docs, errors, out_md, *, top_n=10)` | a row per variant (produced / error, flagged count). Disagreements: for each word index with ≥2 variants having a start, spread = max − min; the top_n by spread, with time `mm:ss.s` of the earliest start, the word, each variant's start. |

**`align.py` (integrator)**

```python
@dataclass(frozen=True)
class Variant:
    name: str; engine: str; input: str; min_score: float | None
VARIANTS = (Variant("E-raw", "eleven", "raw", None),
            Variant("E-vocals", "eleven", "vocals", None),
            Variant("L-vocals", "local", "vocals", None))
DEFAULT_VARIANT: str | None = None   # set after the owner's bake-off choice (AC10)
SETTINGS_VERSION = 1
```

`song_paths(song_dir)` (exactly one `audio.*` + `lyrics.txt`) · `probe_duration(audio)` ·
`input_audio(song_dir, variant, fresh)` · `run_variant(song_dir, variant, *, fresh=False) -> RunResult(doc, error,
wall_s, reused)` · `verify_against_raw(variant_dir) -> list[str]` · `bakeoff(song_dir, *, fresh=False) -> int` ·
`align_song(song_dir, *, variant=None, fresh=False) -> int`.

**`cli.py`:** `python -m lyric_engine.cli bakeoff|align|validate …`.

## 5. Logic Flow

**`run_variant`**
1. `lyrics = read_lyrics`. On `LyricsError`, fail before any aligner runs (AC3).
2. `inp` = the original audio, or `isolate_vocals(audio, song/work/vocals.wav)`.
3. `key = sha256(sha(inp) + lyrics.sha256 + name + SETTINGS_VERSION)`. If `bakeoff/<name>/raw.json` has this key and
   not `fresh`, reuse it. Otherwise call the engine, round, and write `raw.json {"key", "raw": [[s, e, score], …],
   "native"}`.
4. `words = build_words`, then `apply_flags(words, probe_duration(audio), min_score)`, then `make_doc`.
   `validate(doc)` must be empty (a non-empty result is a bug and raises), then `save_words`.
5. Write the run report and the preview. Engine errors → `RunResult(error=…)`, with the API key redacted.

**`bakeoff`**
Runs every variant (vocals isolated once, shared) → `comparison.md`. Prints a status table. Exits 0 only if every
variant produced a valid `words.json`.

## 6. Edge Case Implementation Map

| Spec edge case | Mechanism | Where |
|---|---|---|
| Annotations in lyrics | bracket check, error with line number | `timing.read_lyrics` |
| Lyrics/audio mismatch | flags + `mostly_flagged` warning | `timing.flag_summary`, `review.write_run_report` |
| Spelling hurts alignment | 10 lowest-score words listed | `review.write_run_report` |
| Non-lexical singing / gaps | nothing invented; neighbours caught by the flags | `timing.apply_flags` |
| Key missing / network / API error | `ElevenLabsError` → variant error row; L still runs; exit 1 | `eleven.align`, `align.bakeoff` |
| Local too slow / out of memory | chunked emissions; clear `RuntimeError` | `local_aligner`, `vocals` |
| Video or odd audio format | ffmpeg decode to WAV before the models; clear error | `vocals`, `local_aligner` |
| Re-run | `raw.json` key reuse; `--fresh` | `align.run_variant` |
| Hand-edited invalid `words.json` | `validate` with word index | `timing.validate`, `cli validate` |
| Non-letter characters | `normalize` → `""` → `not_placed` | `timing.normalize`, aligners |

## 7. File Layout (song folder, all gitignored)

```
songs/<song>/audio.<ext>, lyrics.txt        owner input
songs/<song>/words.json                     align output (default variant)
songs/<song>/work/vocals.wav (+ .json)      cache
songs/<song>/bakeoff/<variant>/raw.json, words.json, report.md, preview.ass, preview.mp4
songs/<song>/bakeoff/comparison.md
```

Module layout: docstring → imports → constants → dataclasses → public functions → private helpers.

## 8. Dependencies

- stdlib only for `timing`, `eleven`, `review`, `align`, `cli`, and the tests.
- ffmpeg 8.0.1 with libass (`ass` filter verified) for `review` and audio decoding.
- L: torch (CPU wheel) + torchaudio and/or `ctc-forced-aligner`, plus demucs or `audio-separator`, pinned in
  `requirements.txt`.
- Module deps: `align` → `timing`, `eleven`, `vocals`, `local_aligner`, `review`. `eleven`/`local_aligner`/`review` →
  `timing` (types, `normalize`) only. `timing` → stdlib only.
- Conflicts: the `timing.py`/`align.py`/`cli.py` stubs are replaced (docstrings kept in spirit).

## 9. Hard Boundaries

- [x] No word time that did not come from an aligner (red line 1); no interpolation or default durations anywhere. (Checked: `eleven._match_in_order` leaves unmatched words None; `local_aligner.place` takes times from CTC spans only; `cli validate` → `verify_against_raw` passes on the real run.)
- [x] Word text always from `lyrics.txt`; aligners return times only (red line 2). (`build_words`; `validate --song` passes.)
- [x] The API key is never printed, logged or written; errors are redacted. (A scan of songs/, src/, tests/, docs/ and out/ found no key; the 401 output shows none.)
- [x] Tests and the gate never touch the network, song files or the API key. (`urlopen` mocked; `.env` path and env var patched in test_eleven and test_align.)
- [x] Nothing written outside the song folder, except `requirements.txt` (L) and code. (By design, model weights download to `~/.cache/torch/hub`, D-010.)
- [x] One API call per E-variant per run; no retry loop.
- [x] Parallel agents edit only the files they own (§1) and run no git write commands. (L also added the optional `tests/test_local_aligner.py`.)

## 10. Acceptance Criteria (runnable)

| # | Command | Pass |
|---|---|---|
| 1–3 | `venv/Scripts/python -m unittest discover -s tests -t .` | OK. Covers round trip, validator rejections, each flag reason, example-lyrics reproduction, `(x2)`/`[chorus]` rejection with the line number. |
| 4 | `venv/Scripts/python -m lyric_engine.cli bakeoff songs/khidki` | a status table with E-raw, E-vocals, L-vocals, each `ok` or with a named error; every produced `words.json` passes `cli validate` |
| 5–6 | `venv/Scripts/python -m lyric_engine.cli validate songs/khidki/bakeoff/<v>/words.json --song songs/khidki` | `valid`; includes `verify_against_raw` (times equal `raw.json` exactly) |
| 7 | open `bakeoff/<v>/report.md`, `bakeoff/comparison.md` | flagged list per variant; top-10 disagreement moments |
| 8 | run `bakeoff` twice | second run: every variant `reused`, no engine call (`tests/test_align.py` proves the no-call path with a fake engine) |
| 9 | `python -c` scan of `songs/khidki` + stdout logs for the key string | not found |
| 10 | owner's choice → `human_decision.md`; `DEFAULT_VARIANT` set; `cli align songs/khidki` | valid `songs/khidki/words.json` |
| 11 | `git ls-files songs` | only `songs/example/lyrics.txt` |
