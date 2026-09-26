# Project Context: Kinetic Lyric Engine

Working folder name: `subtitle_engine`. Blueprint codename: "The Lyric Engine".
Kickoff interview: 2026-09-26.

## Problem

The owner makes romantic / good-vibe Hinglish lyric shorts (9:16) for their own
YouTube / Instagram channel and edits them in CapCut. Word-synced, animated lyric text is
what makes viewers stop and watch, but producing it by hand in CapCut is slow, and CapCut's
built-in caption templates look generic.

Existing auto-caption tools (CapCut auto-captions, Submagic, Captions.app) are built for
spoken audio. On sung lyrics over a beat, and especially on romanized Hindi, their
transcription and timing fall apart.

## Objective

First working version: given a song's audio file plus its Hinglish lyrics as text, produce a
transparent 9:16 overlay video (1080×1920, full song length, starting at t=0) in one theme
(Soft Romantic) with word-level sync, that the owner drops on top of their own background in
CapCut.

Word timings live in a human-readable file the owner can correct by hand, followed by a
re-render that does not redo alignment.

**First milestone, before any animation work:** a 5-second test overlay imports into CapCut
with transparency intact. If that fails, the output plan changes.

## Who it's for

The owner only, as a personal tool for their own channel. It is standalone: any song works,
and it is not tied to LyricTOimage or any other project on this machine. SaaS or use by other
creators is a future vision, not V1.

## Scope

**In scope:**
- Input: song audio (or video) + `lyrics.txt` written by the owner, in romanized Hindi (Hinglish)
- Word-level timing by aligning the known lyrics to the audio (alignment, not transcription)
- Optional owner-provided line-level timings (`.lrc` or tapped) used as anchors to improve
  word alignment
- Human-editable timing file, and re-render from it without re-aligning
- One theme, **Soft Romantic**: warm/pastel palette, gentle reveal, soft glow on the current
  word, no shake/glitch. Exact look is decided in `/spec`, not here.
- Emphasis words marked by hand by the owner in `lyrics.txt` as `*word*` (H-009)
- **V1.1 (H-011, scope change):** a second theme, **Pop Karaoke**: left-to-right fill on the
  sung word, bold sans, white plus one accent. Look details in its `/spec`.
- Two primary outputs, both 1080×1920, song length, starting at t=0 (H-003):
  `.mov` with alpha channel for CapCut desktop, and a solid-green-background mp4 for CapCut
  mobile (Chroma Key)
- Auto-wrap / max words per line so text fits 9:16
- Font fallback for characters the theme font lacks (the blueprint's "Tofu" problem)

**Out of scope (V1):**
- Transcription (audio without lyrics); spoken / voiceover content
- `.ass` or any subtitle-file output (CapCut cannot read styled subtitles)
- AI stylist / LLM auto-tagging; the custom tag markup (`<glow>`, `<shake>`, `<glitch>`, ...)
- Themes other than Soft Romantic and Pop Karaoke (Phonk, Lofi/Vaporwave, Minimalist Cinematic)
  until the owner picks the next one
- Finished video export (background + audio + text in one file)
- SaaS, multi-user, web UI, YouTube-channel marketing
- Fast preview mode (nice-to-have only; owner accepts up to ~10 min render per song)

## Constraints

- **Machine:** Windows 11 laptop, i5-1235U, 8 GB RAM, Intel Iris Xe, no dedicated GPU.
  Alignment can run either as a paid API (e.g. ElevenLabs, small cost per song) or locally on
  CPU (vocal isolation + an open alignment model: free, slower, more setup); the ~10 min
  per-song budget makes both viable. Rendering is CPU-only.
- **Render time:** up to ~10 minutes per song is acceptable. Quality over speed, but total
  effort must stay far below manual CapCut animation.
- **Language:** romanized Hindi is the hardest case for word-level alignment. Automatic
  results will need occasional hand correction; the correction path above is a requirement,
  not a nice-to-have.
- **Editor:** CapCut, both desktop and mobile (H-003). Neither imports styled `.ass`. Desktop
  is expected to honour alpha in `.mov` (unverified until step 01); mobile does not reliably,
  hence the green-screen mp4. `.webm` alpha is unreliable in both.
- **Money:** no LLM cost in V1. Alignment API cost per song is small. Owner already has an
  ElevenLabs account (used by the MANIM project; assumed).
- **Skills:** owner works in Python (several existing projects).

## What already exists that's close

- `C:\MANIM_VIDEOS_CODE_TEMPALTE\src\captions\` has an ASS renderer, word chunking, and a
  "karaoke" mode that splits time equally across words instead of using real word timestamps,
  plus an ElevenLabs client. Its chunking/wrapping logic is a reuse candidate; its timing
  approach and `.ass` output do not fit this project.
- `C:\LyricTOimage` generates 9:16 background visuals for lyric shorts; text is still added by
  hand in CapCut. Complementary (this engine is the missing text layer), but this project must
  not depend on it.
- Commercial tools (CapCut auto-captions and templates, Submagic, Captions.app) are
  speech-oriented, generic-looking, and weak on sung Hinglish lyrics.
- The owner's Gemini blueprint (`docs/reference/project_context.pdf`) describes 3 modules,
  12+ tags, 4 themes. V1 here is a deliberate cut of it: alignment instead of transcription,
  one theme, no AI stylist, no `.ass`. (`docs/reference/knietic_lyric.pdf` is blank;
  re-export it if it held anything.)

## Success signal

The owner plays the rendered overlay against the song: every word lights up exactly when it
is sung, by eye and ear, with no visible drift across the whole song. And producing it took
far less effort than hand-animating in CapCut. Retention / view duration on published shorts
is the eventual signal, not a V1 gate.

## Red lines

1. **Never guess a timing.** If a word cannot be aligned, flag it and report it. Never
   silently insert an estimated timestamp. A mis-synced overlay destroys the premium feel
   that is the whole point of the project.
2. **Never alter the lyrics text.** What the owner wrote in `lyrics.txt` appears on screen
   exactly: spelling, casing, line breaks. If the aligner does not recognise a word, the text
   stays and only its timing is flagged. One exception (H-009): asterisks around a word
   (`*word*`) mark emphasis and are never drawn.

## Open items

- Confirm the ElevenLabs account is active, or name the alignment provider you prefer.
