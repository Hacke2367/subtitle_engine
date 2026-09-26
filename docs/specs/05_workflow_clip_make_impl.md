# Plan: Workflow Commands (`clip`, `make`)
**Spec:** `docs/specs/05_workflow_clip_make.md` · **Branch:** `feature/workflow-clip-make`

## 1. Files
| Action | File | Reason |
|---|---|---|
| CREATE | `src/lyric_engine/workflow.py` | `ClipError`, `line_spans`, `plan_clip`, `clip_song`, `make` |
| MODIFY | `src/lyric_engine/cli.py` | `clip` and `make` subcommands |
| CREATE | `tests/test_workflow.py` | AC1 |
| MODIFY | docs | tracking |

## 2. Decisions
1. The cut is planned from **line spans** of the full song's aligner output, never from word times
   carried over. The clip is re-aligned on its own audio, which is more accurate on a short
   window, the same path the hand-made khidki clip took.
2. Pure `plan_clip(doc, a, b, duration)` returns the range and lines, so it is testable without
   audio. `clip_song` does the I/O.
3. The audio is cut losslessly to WAV with ffmpeg (`-ss/-to` after `-i`, sample-accurate), as for
   the hand-made clip.
4. `make` reuses `align.align_song` and `render.render`; no logic is duplicated.

## 3. Functions (`workflow.py`)
| Function | Behaviour |
|---|---|
| `line_spans(doc) -> dict[int, tuple[float, float] \| None]` | Per lyric line: (first start, last end) if every word is timed and unflagged, else None |
| `plan_clip(doc, a, b, duration) -> ClipPlan(start, end, lines, warnings)` | Selects lines entirely inside [a, b]. Snaps per spec §4 with `PRE_PAD_S = 0.3` and `POST_PAD_S = 1.0`, never past half the gap to a neighbouring line. Raises `ClipError` for no line, a flagged line inside or crossing the window, or a bad range. |
| `clip_song(source, a, b, out) -> ClipPlan` | Loads the source and runs `timing.validate` with lyrics and audio (refuse if stale or invalid). Refuses if `out` exists. `plan_clip`, then ffmpeg cut, then writes `lyrics.txt` (the source lines between the first and last selected line, verbatim, including blank lines) and `clip.json`. |
| `make(song, *, codec=None, allow_flagged=False) -> int` | No `words.json` → `align.align_song(song)`, and a non-zero result returns early. `words.json` present → validate with lyrics and audio: stale or invalid → print why and return 2, otherwise print "using existing words.json". Then `render` through the CLI's `_render`. |

## 4. Hard Boundaries
- [x] Clip lyrics are the source lines verbatim (red line 2). (The 27–57 s clip is byte-identical to the hand-made one.)
- [x] No word time is created or copied; only the cut points are chosen (red line 1). (Clips are re-aligned on their own audio.)
- [x] Never overwrites a folder or `words.json`. (Tested: an existing folder is refused; `make` keeps a valid `words.json`.)
- [x] Tests are offline; the audio cut is tested on a synthetic WAV.

## 5. Acceptance (runnable)
| # | Command | Pass |
|---|---|---|
| 1 | `venv/Scripts/python -m unittest discover -s tests -t .` | OK |
| 2 | `cli align songs/khidki_full` → `cli clip songs/khidki_full --from 27 --to 57 --out songs/khidki_c1` | lyrics == lines 1–8 |
| 3 | `cli clip songs/khidki_full --from 75 --to 89 --out songs/khidki_s2` → `cli make songs/khidki_s2` | `checks: pass` |
