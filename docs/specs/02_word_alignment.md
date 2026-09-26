# Spec: Word Alignment → `words.json`
**Version:** 1.1.0 | **Component:** Stage 1: alignment (`align.py`, `timing.py`)
**Status:** Approved (H-007). 1.1.0: prototype on a ~30 s clip
**Plan step:** 02 (`docs/development_plan.md`) · **Branch:** `feature/word-alignment`

## 1. Problem Statement

The overlay can only light up each word when it is sung if the engine knows the start and end
time of every word. The owner already has the lyrics text, so this is forced alignment (placing
known words in the audio), not transcription. Two things make it hard:

- **Sung, romanized Hindi (Hinglish).** Most alignment models expect English or Devanagari, and
  singing stretches, bends and repeats syllables in ways speech does not.
- **Music under the voice.** Instruments confuse the aligner, and older mixes (the test song is
  from 1968) blend vocals and orchestra tightly.

No aligner is known to handle this well. H-004 settles it empirically: run the ElevenLabs
forced-alignment API and a local CPU pipeline on one real song, and keep whichever syncs better.
Everything after this step (layout, animation, the correction loop) reads the resulting
`words.json`, so its format and its honesty about uncertain words (red line 1) have to be right
here.

## 2. Objective

For one real Hinglish song, produce a `words.json` with a start and end time for every word of
`lyrics.txt`, word text identical to `lyrics.txt`, and every uncertain word flagged. The owner
picks the better aligner from a side-by-side comparison, and that aligner becomes the engine's
default.

## 3. Scope & Constraints

**Will Do:**
- **`words.json` format + validator** (owned by `timing.py`, D-001): the word list, per-word
  timing, confidence, flags, and a link to the exact `lyrics.txt` and audio it was made from.
- **Lyrics reading:** split `lyrics.txt` into lines and words, keeping the original text of every
  word verbatim (case, spelling, attached punctuation) and the line structure, blank lines included.
- **Aligner variants** behind one common interface, each producing a `words.json`:
  - `E-raw`: ElevenLabs forced alignment on the original audio;
  - `E-vocals`: ElevenLabs forced alignment on isolated vocals;
  - `L-vocals`: local CPU pipeline (vocal isolation + an open multilingual forced-alignment model)
    on isolated vocals.
- **Vocal isolation** of the song, done once and reused by both `*-vocals` variants.
- **Flagging** of every word whose timing can't be trusted (§4 rules), with a reason per word.
- **Bake-off command:** runs all variants on one song folder and produces, per variant, its
  `words.json`, a run report, and a review preview video. It also writes one comparison report.
- **Review preview** per variant: low-resolution video with the song's audio, showing the current
  line with the current word highlighted and flagged words marked. It exists so the owner can judge
  sync by eye and ear. It is not a product output.
- **`align` command** for normal use: one song folder → `words.json` with the default aligner.
- **Cache:** raw aligner results are kept, so re-running reports or previews never re-bills the
  API or re-runs slow local models unless explicitly asked.
- **Automated tests** for the logic that needs no audio: lyrics reading, `words.json` round trip
  and validation, flag rules.

**Will NOT Do:**
- Transcription, or guessing lyrics from audio.
- Line-level anchors / `.lrc` input (step 04).
- The real overlay: themes, layout, animation, alpha output (step 03). The preview is plain and
  review-only.
- A UI for correcting timings. Correction = editing `words.json` by hand; the validator catches
  mistakes.
- Keep both aligners as runtime options after the bake-off. The loser is removed from the engine
  and stays in git history.
- Support for annotations inside `lyrics.txt` (`(x2)`, `[chorus]`, `[music]`).
- Commit any song audio, lyrics, aligner output or preview.

**Hard Rules:**
- **Red line 1:** never estimate a timing. No interpolation from neighbours, no even spacing, no
  default durations. A word the aligner could not place has no time and is flagged. A low-confidence
  word keeps the aligner's own time, is flagged, and is never silently "fixed".
- **Red line 2:** never alter the lyrics text. Word texts in `words.json`, read in order, reproduce
  `lyrics.txt`'s words exactly. If an aligner works better on a transformed copy of the text
  (normalised, punctuation stripped, transliterated), that copy is internal to the aligner and
  maps back 1:1 to the original words.
- The API key comes only from `.env` / the environment. It is never printed, logged, or written to
  any file the tool produces.
- Audio is sent to ElevenLabs only by an explicit bake-off or `align` run, never by tests or the gate.
- The gate and tests run offline, with no song files and no API key.
- Everything the tool writes for a song stays inside that song's folder (gitignored, D-002).

## 4. Core Design

**Data flow**

```
songs/<song>/ audio + lyrics.txt
   │
   ├─ read lyrics → words (original text, line index)
   ├─ vocal isolation (once, cached) ──────────────┐
   │                                               │
   ├─ E-raw    : ElevenLabs(audio, text)           │
   ├─ E-vocals : ElevenLabs(vocals, text)  ◄───────┤
   └─ L-vocals : local aligner(vocals, text) ◄─────┘
          │  raw result (cached)
          ▼
   map back 1:1 to original words → apply flag rules → validate → words.json
          │
          ├─ run report  (flag list, duration, cost/credits if known)
          ├─ preview.mp4 (review only)
          └─ comparison report (bake-off only)
```

**Aligner interface (conceptual):** input = audio path + the original word list; output = for each
word, a start, an end and a confidence, or "not placed". Every variant goes through the same
mapping, flagging and validation, so the variants differ only in the aligner itself.

**Flag rules** (thresholds are tuned in `/plan` and against the test song; the reasons are fixed).
A word is flagged when:
- `not_placed`: the aligner returned no timing for it;
- `low_confidence`: its confidence is below the variant's threshold;
- `bad_duration`: its end ≤ start, or its duration is implausibly long for one sung word;
- `out_of_order`: it starts before the previous word starts, or overlaps it by more than a small
  margin;
- `out_of_bounds`: it lies partly or fully outside the audio's duration.

A flagged word keeps whatever the aligner gave it (possibly nothing), plus its reasons. The owner
can fix the times by hand and clear the flag. The validator then checks the result.

**Comparison report (bake-off):** for each variant, the words flagged, the pipeline time, and the
API cost/credits if reported. Across variants, the moments where their start times disagree the
most, so the owner knows which timestamps to scrub to in the previews first.

**Choosing:** the owner watches the previews (starting at the disagreement hotspots) and names the
winner. That choice is recorded in `human_decision.md`, and the `align` command's default becomes
that variant.

## 5. Data Schema: `words.json` (conceptual; exact field names in `/plan`)

- **Header:** format version; song folder name; the audio file's name, duration and content hash;
  `lyrics.txt`'s content hash and its lines verbatim (blank lines included); the aligner variant
  and its settings; when it was made.
- **Words, in order:** index; original text; line index; start; end (seconds, or empty if not
  placed); confidence; flagged; reasons.
- Laid out so a human can edit it in a text editor: one word per line, readable numbers.
- Content hashes make stale files detectable: if `lyrics.txt` or the audio changed after alignment,
  `words.json` no longer matches and says so.

## 6. Edge Cases & Error Handling

- **`lyrics.txt` has annotations** (`(x2)`, `[chorus]`, …): stop before aligning, name the line,
  and ask for repeats written out in full. Never strip them automatically (red line 2).
- **`lyrics.txt` doesn't match the audio** (a different version, missing or extra lines, trimmed
  audio with untrimmed lyrics): the aligner still returns something, and the flag rules and
  confidence expose it. If more than a set share of words is flagged, the run report says the
  lyrics probably don't match the audio instead of presenting a mostly-flagged file as a result.
- **Spelling choices** ("ukhda" vs "ukada", "rehta" vs "raheta") can change alignment quality. The
  tool never changes them. The run report lists the lowest-confidence words so the owner can decide
  whether to respell.
- **Non-lexical singing not in the lyrics** (humming, "la la", alaap), and long instrumental
  gaps: nothing is invented for them. Words next to them that get pulled out of place are caught by
  the flag rules.
- **ElevenLabs key missing, network down, or API error:** the E-variants report "skipped" or
  "failed" with the reason (never the key); the L-variant still runs; the bake-off exits non-zero
  and the report names every variant that didn't produce a result.
- **Local pipeline too slow or out of memory on this laptop** (8 GB RAM): the run fails with a clear
  message rather than hanging. Processing in pieces, if needed, is a `/plan` concern. The time
  budget is §7.
- **Audio in a video file** (`.mp4`), or an unusual format: accepted if ffmpeg can read it;
  otherwise a clear error naming the file.
- **Re-running:** cached raw results are reused and reported as reused. A "fresh" option forces
  new API / model runs.
- **`words.json` edited by hand into an invalid state** (text changed, times out of order, a
  flag cleared with no time): the validator rejects it with the exact word index and problem.
- **Characters outside plain Latin letters** (digits, apostrophes, emoji): kept verbatim on screen.
  Aligner-internal handling is a `/plan` concern, and a word the aligner can't place is flagged
  like any other.

## 7. Performance & Cost Targets

- Whole bake-off for a ~4–5 minute song: finishes on this laptop without running out of memory.
  The L-variant takes ≤ 10 minutes (the owner's per-song budget), vocal isolation included.
- ElevenLabs: exactly one API call per E-variant per run; the cache prevents repeat charges.
- The run report states each variant's wall time and any cost/credit figure the API returns.

## 8. Acceptance Criteria

1. The automated tests pass offline with no song files and no API key: lyrics reading; `words.json`
   round trip; validator rejections (text changed, out-of-order times, flag cleared without a time,
   stale hash); each flag reason fires on a crafted input.
2. Reading `songs/example/lyrics.txt` and joining the word texts per line reproduces every
   non-blank line's words exactly, and the line count including blank lines matches.
3. A `lyrics.txt` containing `(x2)` or `[chorus]` is rejected before any aligner runs, with the
   line number in the message.
4. On the owner's test song, the bake-off produces for each of E-raw, E-vocals and L-vocals a
   `words.json` that passes the validator, **or** a report line naming why that variant produced
   none.
5. In every produced `words.json`, the word texts in order equal the words of `lyrics.txt` exactly
   (red line 2).
6. No produced `words.json` contains a word time that did not come from the aligner (red line 1).
   Checked by comparing each file with its cached raw aligner output.
7. Each run report lists every flagged word with its index, text, line and reason(s). The
   comparison report lists the top disagreement moments across variants.
8. A second bake-off run on the same song makes no API call and re-runs no model; the report says
   the results were reused.
9. The API key string appears in no file the tool wrote (scan of the song folder and the logs).
10. The owner watches the previews, names the variant that syncs better, and it is recorded in
    `docs/human_decision.md`. The `align` command then uses it by default and produces a valid
    `words.json` for the test song.
11. No song audio, lyrics, aligner output or preview is tracked by git.

## 9. Dependencies

- **Owner:** the test song "Mere Samne Wali Khidki Mein" (`songs/khidki_full/`: 2:52 mp3 + the
  owner's lyrics). Per H-007 the bake-off runs on a ~30 s clip (`songs/khidki/`), cut from where the
  singing starts and ending at a line boundary; its `lyrics.txt` holds exactly the lines sung in the
  clip, verbatim. An ElevenLabs API key in `.env` (present).
- **Existing:** ffmpeg 8.0.1, the Python 3.10.11 venv, Pillow (preview frames if needed).
- **New, chosen in `/plan`:** a vocal-isolation model and a local forced-alignment model that run
  on CPU and accept romanized text or a lossless transform of it. Feasibility note: torchaudio's
  `forced_align` was kept in 2.10 after being slated for removal (pytorch/audio#3902). The model
  bundles around it must be verified in `/plan`.
- **External:** ElevenLabs `POST /v1/forced-alignment`. It takes an audio file + plain text and
  returns per-word `text`/`start`/`end`/`loss`. Hindi is listed as supported; the docs don't say
  whether romanized text works. That is exactly what E-variants test.

## 10. Security & Privacy

- The song audio goes to a third party (ElevenLabs) for the E-variants; that's the owner's decision
  (H-004). Nothing else leaves the machine.
- The API key is read from `.env` (gitignored) and never echoed. Error messages from the API are
  reported with any key-like content removed.
