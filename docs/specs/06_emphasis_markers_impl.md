# Plan: Emphasis Words (`*word*`)
**Spec:** `docs/specs/06_emphasis_markers.md` (v1.0.1, approved by owner 2026-09-26)
**Branch:** `feature/emphasis-markers` · **Decisions:** H-009, D-016
**Work split:** one developer, in the build order of §11 (small change, no agents).

> **Revision 1.1 (H-013, spec v1.1.0).** The owner found the 1.06x swell too subtle and set a
> rule: a marked word is 1.5x-2x its line's other words, permanently. That supersedes every swell
> part of this plan (§2.4-2.7, §2.9, `swell()`, `SWELL_STEP`, the scaled sprite cache, the scaled
> sync geometry, `swell` / `swell_out_s`). What was built instead:
> - `theme.py`: `emphasis_scale = 1.5`; `Theme.__post_init__` refuses a value outside
>   `EMPHASIS_MIN`-`EMPHASIS_MAX` (1.5-2.0).
> - `layout.py`: `WordBox.emphasis` (defaulted field); `word_fonts(theme, size, emphasis)` gives
>   `font_set(theme, round(size * emphasis_scale))` for a marked word; `layout_line(...,
>   emphasis=)` measures marked words at that size for the wrap; `_place` gives each row the
>   height of its tallest word and one shared baseline, with the plain row gap between rows, so a
>   line without marks is placed exactly as before.
> - `render/timeline.py`: `plan_timeline(..., emphasis=)` passes the set to `layout_fn`.
>   `render/frames.py` and `render/check.py` take each word's fonts from `word_fonts`, so the
>   drawn mask, the layout box and the sync check agree. No animation change.
> - Tests: `tests.test_layout -k Emphasis` (rule, ratio after shrink, baseline, no overlap,
>   unmarked identical) and `tests.test_render -k Emphasis` (end to end, report, malformed marker).

## 1. Files

| Action | File | Reason |
|---|---|---|
| MODIFY | `src/lyric_engine/timing.py` | marker grammar, marker-free words, `Lyrics.emphasis`, markers-only staleness, marker-free `lyrics.lines` in new docs |
| MODIFY | `src/lyric_engine/workflow.py` | `clip_song` copies lines from the source `lyrics.txt` (keeps markers) |
| MODIFY | `src/lyric_engine/theme.py` | `swell`, `swell_out_s` |
| MODIFY | `src/lyric_engine/render/timeline.py` | `WordPlan.emphasis`, `plan_timeline(..., emphasis=)`, `swell()` |
| MODIFY | `src/lyric_engine/render/frames.py` | scaled sprite cache, centre-preserving placement |
| MODIFY | `src/lyric_engine/render/check.py` | sync sample uses the swelled geometry; report lists emphasis words |
| MODIFY | `src/lyric_engine/render/__init__.py` | read markers in `load_for_render`; pass emphasis; `RenderResult.emphasis` |
| MODIFY | `src/lyric_engine/cli.py` | print the emphasis words after a render |
| MODIFY | `tests/test_timing.py`, `tests/test_align.py`, `tests/test_workflow.py`, `tests/test_render.py` | AC1, AC2, AC5, AC7, AC8; two `load_for_render` unpack sites |
| MODIFY | `docs/*` tracking | plan/pending/session log/decisions |

`align.py`, `eleven.py`, `local_aligner.py`, `layout.py`, `review.py`: **no change**. They get the
marker-free words from `Lyrics.words` and `words.json`.

## 2. Architecture Decisions

1. **`lyrics.txt` is the only source of emphasis; `words.json` stays marker-free** (spec §3,
   §4.3). Rejected: an `"emphasis"` field per word. A markers-only edit would then make
   `words.json` out of date and need a refresh command, and a hand-edited `words.json` could
   disagree with `lyrics.txt`.
2. **Staleness compares marker-free lines, not the file hash** (spec §4.4). `lyrics.sha256` is
   still written (the file's bytes, markers included) and still required by the validator, but
   it only chooses the wording of the error. Rejected: hashing the marker-free text. That changes
   what `lyrics.sha256` means and makes every existing `words.json` look stale.
3. **Marker grammar is one regex, used by the reader, the stripper and the validator** (spec
   §4.1). A token is marked iff it fully matches `\*([^\s*](?:\S*[^\s*])?)\*`. Any other token
   that starts or ends with `*` is malformed. An asterisk inside a word is lyric text. This keeps
   one definition, like `_tokens` today.
4. **The swell scales the finished sprite** (text + shadow + glow), quantised to
   `SWELL_STEP = 0.004` and cached per (word, kind, step) in `FadeCache`, which is dropped per
   line. Rejected: re-rasterising the word at a bigger font size per frame (slow, and the mask
   would no longer be the one layout measured). Pillow premultiplies RGBA inside `resize`, so the
   straight-alpha sprites get no dark fringes.
5. **Scale 1.0 takes today's code path unchanged.** No resize and the same cache keys' pixels,
   so unmarked songs are pixel-identical (AC3).
6. **The swell's shape comes only from the word's own frames** (red line 1). It eases in over
   `reveal_s` from `reveal`, holds to `end`, and settles over `swell_out_s` after `end`, like
   `glow_out_s`. A word sung for less than `reveal_s` peaks lower, in proportion. The settle may
   run while the next word reveals, the same way the glow fade does today; it never reads the
   next word's time. (This is the spec v1.0.1 wording of the "very brief word" row.)
7. **Separate `swell()` function instead of widening `word_state()`**. `word_state` keeps its
   3-tuple, used in `frames.py` and asserted in `tests/test_render.py`.
8. **`load_for_render` reads `lyrics.txt` first** with `timing.read_lyrics`, so a malformed
   marker gets the reader's message and hint, not a misleading "stale" from `validate`.
9. **The sync check samples the swelled geometry at its `on` frame** (same quantised factor,
   same resize), so a word that is mid-swell at `reveal + rev` is measured where it is drawn.

## 3. Data Structures

`timing.py`
- `Lyrics` gets `emphasis: frozenset[int] = field(default_factory=frozenset)`: the indexes into
  `words` of marked words. It is last and defaulted, so the constructor stays compatible
  (contract comment).
- `Lyrics.lines`: unchanged meaning, the file's lines **verbatim, markers included** (used by
  `clip`).
- `Lyrics.words`: `(text, line)` with **marker-free** text (aligners, `build_words`, spec §4.2).
- `_MARKED = re.compile(r"\*([^\s*](?:\S*[^\s*])?)\*")`. Matched per token (`fullmatch`).
- `_MARKED_IN_LINE = re.compile(r"(?<!\S)\*([^\s*](?:\S*[^\s*])?)\*(?!\S)")`. The same pattern
  bounded by whitespace, for stripping a whole line while keeping its spacing.
- `MARKER_HINT = "Wrap one whole word, punctuation inside: *dil,*. Mark each word on its own: *tere* *bina*."`

`words.json` (no version bump, `WORDS_VERSION` stays 1): `lyrics.lines` in new docs is the
marker-free lines; `words[i].text` is marker-free. Old docs have no markers, so they are already
in this form.

`theme.py` (`Theme`, in the Motion block):
- `swell: float = 1.06`: peak scale of a marked word (spec: about 1.06×).
- `swell_out_s: float = 0.35`: settle back to 1.0 after the word's end.

`render/timeline.py`
- `WordPlan` gets `emphasis: bool = False` (last field, defaulted; existing constructions keep
  working).

`render/frames.py`
- `SWELL_STEP = 0.004` (15 steps up to 1.06).
- `FadeCache.images` keys become `(word, kind, level, step)`; `step` is 0 for unscaled.
- `FadeCache.scaled_images: dict[tuple[int, str, int], Image.Image]`, keyed (word, kind, step),
  cleared with `images` when the visible line changes.

`render/__init__.py`
- `RenderResult` gets `emphasis: list[str] = field(default_factory=list)`: labels
  `'"dil" (line 2)'` in word order, for the report and the CLI.

## 4. Function Specifications

**timing.py**
- `_marker(token: str) -> tuple[str, bool] | None`: `(inner, True)` if it fully matches
  `_MARKED`; `None` if it starts or ends with `*` otherwise (malformed); else `(token, False)`.
- `strip_markers(lines: list[str]) -> list[str]`: `_MARKED_IN_LINE.sub(r"\1", line)` per line.
  Malformed tokens are left as they are, so callers check `marker_problems` first.
- `marker_problems(lines: list[str]) -> list[str]`: one entry per line with a malformed token:
  `line 3: *tere bina* (cannot read: *tere, bina*)`. `[]` = fine.
- `read_lyrics(path) -> Lyrics`: after the bracket check, `bad = marker_problems(lines)`. If any,
  raise `LyricsError(f"{path.name} has emphasis markers it cannot read:", *bad, MARKER_HINT,
  "Lyrics are never edited automatically.")`. Then `words = _tokens(strip_markers(lines))` and
  `emphasis = frozenset(i for i, (tok, _) in enumerate(_tokens(lines)) if _marker(tok)[1])`.
  Stripping never adds or removes a token (the inside is non-empty and has no whitespace), so
  the indexes line up.
- `make_doc(...)`: `"lines": strip_markers(lyrics.lines)`. Nothing else changes.
- `validate(doc, lyrics_path, audio_path) -> list[str]`: for the lyrics file (see §5.2).
  Docstring updated: markers-only edits are not stale.
- `_tokens(lines)`: unchanged (still the single definition of "the words"; callers pass
  marker-free lines).

**workflow.py**
- `clip_song(...)`: after `validate` passes,
  `lines = timing.read_lyrics(lyrics_path).lines[first:last + 1]`, replacing the `doc["lyrics"]["lines"]`
  slice. `LyricsError` cannot happen there (validate passed, so no malformed markers), but it
  is mapped to `ClipError(str(exc))` anyway, because `read_lyrics` can raise.

**render/timeline.py**
- `plan_timeline(doc, theme, n_frames, layout_fn=None, emphasis: frozenset[int] = frozenset())`:
  sets `WordPlan.emphasis = w["i"] in emphasis` for timed and untimed words alike.
- `swell(wp: WordPlan, n: int, theme: Theme) -> float`: see §5.3. It is 1.0 whenever the word is
  not emphasised, untimed, or before its reveal.

**render/frames.py**
- `swell_step(scale: float) -> int`: `round((scale - 1) / SWELL_STEP)`. Shared with `check.py`.
- `scale_sprite(img: Image.Image, step: int) -> Image.Image`: `img.resize((round(w·f),
  round(h·f)), Image.BICUBIC)` with `f = 1 + step·SWELL_STEP`. Shared with `check.py`.
- `FadeCache.scaled(sprite, key: tuple[int, str, int]) -> Image.Image`: cached `scale_sprite`.
- `FadeCache.faded(sprite, level, key)`: the key gains the step. No other change.
- `_frame_parts(...)`: per word, `step = swell_step(swell(wp, n, theme))`. If `step == 0`, the
  path is unchanged. Else both sprites go through `cache.scaled`, and
  `pos = (box.x − pad − (w1 − w0) // 2, box.y − pad − (h1 − h0) // 2 + round(rise))`.

**render/check.py**
- `_sync_samples(lines, theme)`: for a word with `step = swell_step(swell(wp, on, theme)) > 0`,
  build the ink from `layout.word_mask(text, fonts, pad)` (the drawn sprite's mask, `pad = 3 ·
  glow_radius`), threshold it, `scale_sprite` it, and set `box` to the scaled sprite rect at the
  §4 position (no rise: `on ≥ reveal + rev`, when the rise is done). Unscaled words: unchanged.
- `write_report(...)`: a line after "Flagged words rendered": `- Emphasis words:
  N: "dil" (line 2), ...` or `- Emphasis words: none`.

**render/__init__.py**
- `load_for_render(song_dir, *, allow_flagged) -> tuple[dict, Path, frozenset[int]]`: after
  `song_paths`, `lyrics_obj = timing.read_lyrics(lyrics)`; `LyricsError` becomes
  `RenderError(str(exc))`. Then as today. Returns `lyrics_obj.emphasis` too.
- `render(...)`: passes `emphasis` to `plan_timeline`; fills `result.emphasis` from `doc["words"]`.

**cli.py**
- `_render`: after the frames line, `emphasis: "dil" (line 2), ...` or `emphasis: none`.

## 5. Logic Flow

**5.1 Reading `lyrics.txt`** (`read_lyrics`)
1. Decode (as today); on failure → `LyricsError` (not UTF-8).
2. If there are brackets → `LyricsError` (as today).
3. If `marker_problems(lines)` is non-empty → `LyricsError` (the lines + `MARKER_HINT`).
4. `clean = strip_markers(lines)`; `words = _tokens(clean)`; if empty → `LyricsError`
   (no words).
5. `emphasis` from the raw tokens (§4). Return `Lyrics(path, sha, lines, words, emphasis)`.

**5.2 Validating against `lyrics.txt`** (`validate`, the lyrics branch of the existing loop)
1. Read the bytes; on `OSError` → `cannot read ...` (as today).
2. `file_lines = data.decode("utf-8-sig", "replace").splitlines()`.
3. If `marker_problems(file_lines)` → one error per problem, `f"{name} {problem}"`, plus
   `MARKER_HINT`, and `continue` (the file cannot be compared).
4. If `strip_markers(file_lines) != lines` (the doc's): if the sha differs → `stale: {name}
   changed after this words.json was made; re-run align` (the existing text, minus the hash
   detail); else → `lyrics.lines differ from {name}; they must be its lines without the
   emphasis asterisks`.
5. Else: valid, whatever the sha says (markers-only edit, or line endings).

Audio staleness: unchanged (sha only).

**5.3 `swell(wp, n, theme)`**
1. If `not wp.emphasis` or `wp.reveal is None` or `n < wp.reveal` → `1.0`.
2. `ease(k, frames) = smoothstep(_ramp(k, frames))` (the `word_state` smoothstep).
3. `rin = theme.reveal_s · fps`, `rout = theme.swell_out_s · fps`.
4. If `n ≤ wp.end` → `amount = ease(n − reveal, rin)`.
5. Else `amount = ease(wp.end − reveal, rin) · (1 − ease(n − wp.end, rout))`.
6. Return `1 + (theme.swell − 1) · amount`.

**5.4 Rendering a frame** (`_frame_parts`): as today, and per word the step from §4. The band's
top and bottom already come from every layer's position and height, so bigger sprites are
covered. `alpha_composite` needs `x ≥ 0`: the smallest `box.x − pad` is 90 − 48 = 42 px with
defaults, and the largest shift is `(900 + 96) · 0.06 / 2 ≈ 30` px, so it stays ≥ 12. A unit test
pins this (§6).

## 6. Edge Case Implementation Map

| Spec edge case | Mechanism | Location |
|---|---|---|
| `*dil*` → `dil`, emphasised | `_MARKED` fullmatch | `timing._marker`, `read_lyrics` |
| `*dil,*` → `dil,`, emphasised | the inside may end in punctuation | `_MARKED` |
| `*dil*,` `*dil` `dil*` `**dil**` `*` `**` → error | starts/ends with `*`, no fullmatch | `timing.marker_problems` → `LyricsError` |
| `*tere bina*` → error with the per-word hint | tokens `*tere`, `bina*` malformed; `MARKER_HINT` | same |
| `f**k` literal | does not start/end with `*` | `_marker` → `(token, False)` |
| Markers edited after align: valid, no re-align | marker-free comparison | `timing.validate` §5.2 step 4-5 |
| Letters changed: stale | clean lines differ, sha differs | `timing.validate` §5.2 step 4 |
| Malformed marker added after align | reader error before validate | `render.load_for_render`; `validate` §5.2 step 3 for `validate` / `make` / `clip` |
| Flagged, untimed marked word | `reveal is None` → 1.0 | `timeline.swell` step 1 |
| Very brief marked word | peak = `ease(end − reveal)`; settle from own end | `timeline.swell` step 5 |
| Old `words.json`, no markers | no markers → same lines; step 0 path | `validate`; `_frame_parts` |
| Every word on a line marked | each word's own `swell` | `_frame_parts` |
| Clip of a marked song keeps markers | lines from `read_lyrics(...).lines` | `workflow.clip_song` |
| Sprite pushed left of the canvas | defaults keep `x ≥ 12`; test pins it | `tests/test_render.py` |

## 7. File Layout (no new source files)

- `timing.py`, section "Lyrics, flags, words.json IO and validation": `_ANNOTATION_CHARS`,
  `_MARKED`, `_MARKED_IN_LINE`, `MARKER_HINT`, `_WORD_KEYS`, then `_marker`, `strip_markers`,
  `marker_problems`, `read_lyrics`, ... (the rest in today's order).
- `timeline.py`: `WordPlan`, `LinePlan`, timeline helpers, `plan_timeline`, `_ramp`,
  `word_state`, **`swell`**, `line_opacity`.
- `frames.py`: `LEVELS`, **`SWELL_STEP`**, `_solid`, `_scaled`, `build_sprites`, **`swell_step`,
  `scale_sprite`**, `_LUTS`, `FadeCache` (+ `scaled`), `_zero_frame`, `_frame_parts`,
  `compose_frame`.
- Tests: new cases go in the existing test files, in a `class ...EmphasisTest` per file.

## 8. Dependencies

- Imports: `re` (already in `timing.py`), `Image.BICUBIC` (Pillow, installed). No new package.
- `check.py` imports `swell_step`, `scale_sprite` from `frames` and `swell` from `timeline`.
  There is no cycle: `frames` imports `timeline`, never `check`.
- **Conflicts with existing code, to change:**
  - `render/__init__.py:52`: the stale-prefix test still works (`stale:` and `lyrics.lines differ`
    are kept as prefixes).
  - `tests/test_render.py:194` and `:204` unpack `load_for_render` as a 2-tuple; they become
    3-tuples.
  - `tests/test_timing.py::test_lines_edited_inside_words_json` asserts `"lyrics.lines"` in the
    error. The new message keeps that prefix.
  - `workflow.clip_song:119` reads `doc["lyrics"]["lines"]`, which becomes marker-free. It must
    read `lyrics.txt` instead (AC7).
- `align.py` `_cache_key` still uses `lyrics.sha256`: a markers-only edit followed by a
  deliberate `align --fresh/--overwrite` re-runs the engine. That is accepted, since the spec only
  requires that no re-align is **needed**.

## 9. Hard Boundaries

- [ ] Never draw, send to an aligner, or store in `words[i].text` an asterisk that is part of a
      marker.
- [ ] Never change any other character of the lyrics: no trimming, no case change, no
      punctuation moves.
- [ ] Never auto-fix a malformed marker; report the line and stop.
- [ ] Never read another word's time for the swell; untimed → no swell.
- [ ] Never move a word's layout position or re-wrap for emphasis; scale about the sprite
      centre only.
- [ ] Never change the pixels of a frame where every word has `swell == 1.0`.
- [ ] Never write to `words.json` from `render`, `validate` or `clip`.
- [ ] No emphasis field in `words.json`; no `WORDS_VERSION` bump.

## 10. Acceptance Criteria (runnable)

`PY=venv/Scripts/python`. Unit tests run from the repo root.

1. **Marker rules**: `$PY -m unittest tests.test_timing -k Emphasis` → `OK`; one case per §6
   marker row (text + emphasis, or `LyricsError` naming the line).
2. **Aligners never see `*`**: `$PY -m unittest tests.test_align -k Emphasis` → `OK`. The
   `FakeEngine` records the words it got; a marked lyrics file gives words with no `*`, and the
   ElevenLabs request text is `" ".join` of those same words.
3. **Old songs untouched**:
   - `$PY -m lyric_engine.cli validate songs/khidki/words.json --song songs/khidki` → `valid`;
     same for `songs/khidki_s2`.
   - Frame hashes: `git worktree add <scratch>/dev_tree dev`; run
     `<scratch>/frame_hashes.py songs/khidki_s2` once with `PYTHONPATH=<scratch>/dev_tree/src`
     (it writes `dev.json`) and once without (`branch.json`). It hashes `compose_frame` bytes
     for every 30th frame. `fc dev.json branch.json` → no differences.
4. **Markers-only edit is free**: copy `songs/khidki_s2/{audio.wav,lyrics.txt,words.json}` to
   `songs/khidki_s2_em/`, add 3 markers to its `lyrics.txt`, note `sha256sum words.json`.
   `validate` → `valid`; `$PY -m lyric_engine.cli render songs/khidki_s2_em` → exit 0, `checks: pass`,
   `emphasis:` lists the 3 words; `sha256sum words.json` unchanged. Then change one letter of a
   word in a temp copy's `lyrics.txt` → `validate` prints `stale:`.
5. **Swell on exactly the marked words**: `$PY -m unittest tests.test_render -k Emphasis` → `OK`.
   A synthetic 4-word line is rendered with `compose_frame` for every frame, once without and
   once with word 1 marked. Every differing pixel lies inside word 1's peak-scaled sprite rect, and
   only on frames in `[reveal, end + ceil(swell_out_s·fps)]`. Word 1's peak-scaled glyph bbox
   does not intersect words 0 and 2's glyph bboxes. Pixels where a neighbour's text sprite alpha
   is 255 are identical in both renders. The `x ≥ 0` margin is also pinned (§5.4).
6. **Text**: covered by AC1 (marker-free `words[i].text` from `make_doc`) plus the existing
   `build_sprites` / `plan_timeline` red-line assertions (a mismatch raises `AssertionError`).
7. **Clip**: `$PY -m unittest tests.test_workflow -k Emphasis` → `OK` (the synthetic source gets
   markers; the clip's `lyrics.txt` has them on the copied lines).
8. **Flagged**: in `tests.test_render -k Emphasis`, `swell()` of an untimed marked `WordPlan`
   is `1.0` at every frame.
9. **Speed**: render `songs/khidki_s2` and `songs/khidki_s2_em` on the branch. The wall time in
   `render/report.md` of the second is ≤ 1.10 × the first.
10. **Look**: the owner watches `songs/khidki_s2_em/render/preview.mp4` and approves, or asks
    for `swell` / `swell_out_s` changes in `theme.py`.
11. **Gate**: `/gate` → unit tests `OK`, alpha proof passes.

## 11. Build order

1. AC3 baseline first: the worktree + `dev.json`, before any source edit.
2. `timing.py` + its tests (AC1, AC6) → `align` test (AC2) → `workflow.py` + test (AC7).
3. `theme.py`, `timeline.py`, `frames.py`, `check.py`, `render/__init__.py`, `cli.py` + render
   tests (AC5, AC8).
4. Real runs: AC3 hashes, AC4, AC9; then the gate; then `/ship` and ask the owner for AC10.
