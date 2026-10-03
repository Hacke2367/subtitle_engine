# Decisions (Claude defaults, reversible) (V2)

Owner decisions and open questions live in `docs/human_decision.md`. V2 numbers from D-101 so it
never collides with V1's `../docs/decision.md`.

<!-- Entry template (used by /log_decision):
### D-NNN — <title>
**Date:** YYYY-MM-DD
**Context:** <what prompted this>
**Decision:** <what was decided>
**Why:** <reasoning>
**Supersedes:** <D-NNN, if any>
-->

## Index

| ID    | Title                                               | Status |
|-------|-----------------------------------------------------|--------|
| D-101 | V2 ids, package name, shared venv, no V1 imports    | Active |
| D-102 | Plan order: transcription risk first, LLM after a rules baseline | Active |
| D-103 | ElevenLabs Scribe as the transcription engine       | Active |
| D-104 | Romanization by rules in the engine, not by an LLM  | Active |
| D-105 | Cue rules: pause 0.45 s, 42 characters, 6 seconds   | Active (display times: D-109) |
| D-106 | One work folder per file; the transcript is the cache | Active |
| D-107 | Styled subtitles ship as an .ass file and a transparent overlay .mov | Active |
| D-108 | The overlay's alpha comes from drawing twice, on black and on white | Active |
| D-109 | Cue display times: lead 0.1 s, hold to the next cue, no blink | Active |
| D-110 | Three looks; the signature sets a hero word in gold serif | Active |
| D-111 | Over a bright picture, a soft dark plate replaces the halo | Superseded by D-113 |
| D-112 | Cues: runs cut evenly at the best seams; scraps join a neighbour | Active |
| D-113 | Signature only, bold, on a transparent strip the owner places | Active |

### D-101 — V2 ids, package name, shared venv, no V1 imports
**Date:** 2026-09-29
**Context:** `/scaffold` after H-102 (`v2/` subproject beside the running V1 track).
**Decision:** V2 ids start at 101 (H-101, D-101, P-101). The package is `voice_subs`
(distribution `voice-subs`), a working name the owner can change before the first release.
V2 uses the repository's existing venv (V1's D-003, Python 3.10.11), installed with
`pip install -e .` from `v2/`. `voice_subs` never imports `lyric_engine`; useful V1 code is
copied and adapted. The gate stays empty until the first tested module (as V1's D-004).
**Why:** Two tracks write decisions at the same time, so shared numbers would collide at merge.
No V1 imports keep `v2/` splittable into its own open-source repository. One venv saves disk and
setup on the 8 GB laptop.
**Supersedes:** —

### D-102 — Plan order: transcription risk first, LLM after a rules baseline
**Date:** 2026-09-29
**Context:** Ordering `docs/development_plan.md`.
**Decision:** Step 01 is transcription to Roman Hinglish, because the project context names it
the core risk. Cues at pauses with plain rules and the `.srt` export (step 03) come before the
LLM (step 05).
**Why:** If no engine gives clean Roman Hinglish, the rest changes, so it is tested before
anything is built on it. A rules-only baseline gives the LLM step something to beat, so its
value (and cost) is measured, not assumed.
**Supersedes:** —

### D-103 — ElevenLabs Scribe as the transcription engine
**Date:** 2026-10-03
**Context:** Spec 00 needed one engine for Hinglish speech with word-level times, on a laptop
with 8 GB RAM and no GPU. The repository already holds an ElevenLabs key (V1 uses the same
account for forced alignment), and no other provider key exists.
**Decision:** `POST /v1/speech-to-text` with `model_id=scribe_v1`,
`timestamps_granularity=word`, stdlib HTTP, one call per run and no retry.
**Why:** Measured on a 33 s Hindi clip and a 38 s English one: language detected at 97-99%,
word times tight against the voice, Hindi written in Devanagari and English words in Latin, a
40 s clip uploaded as ~300 kB. Running a local model instead would mean a multi-GB download and
minutes of CPU per clip on this machine. One account, one key, one bill.
**Supersedes:** —

### D-104 — Romanization by rules in the engine, not by an LLM
**Date:** 2026-10-03
**Context:** Scribe returns Hindi in Devanagari, and the project context asks for Roman script
throughout. No LLM provider key is configured, and the owner was away, so no key could be asked
for.
**Decision:** `roman.py` transliterates Devanagari runs with a table plus the inherent-a rules
(drop it at the end of a word and mid-word before a vowel of its own; keep it in the first
syllable, after a nasal, and after a cluster). Latin is passed through untouched. The engine's
original stays in the transcript beside each word.
**Why:** No dependency, no second API call, offline, deterministic, and testable (see
`tests/test_roman.py`): `ghar`, `karta`, `karein`, `jindagi`, `prayaas`, `mushkil`, `gyaan`. It
is a transliteration, not a translation, so it cannot change a word. An LLM pass would spell
a few words more naturally (`isliye` for `isilie`, `doosri` for `dusri`) and could capitalize
sentences; that is step 05's job and needs the owner's key (H-106).
**Supersedes:** —

### D-105 — Cue rules: pause 0.45 s, 42 characters, 6 seconds
**Date:** 2026-10-03
**Context:** Spec 00 needed concrete numbers for where a cue breaks, with no owner to ask.
**Decision:** A new cue starts at a gap of 0.45 s or more, after a sentence end (`. ? ! ।`),
before a cue would pass 42 characters, or before it would run past 6 s. A cue shorter than 1 s
is held on screen up to 1 s, but never into the next cue or past the end of the audio.
**Why:** 0.45 s is a breath, not a word gap; 42 characters is the usual single subtitle line and
leaves room on a 9:16 screen; the hold stops a one-word cue from flashing. All four are
arguments on `to_cues`, so the owner's review can move any of them without touching the code.
**Supersedes:** —

### D-106 — One work folder per file; the transcript is the cache
**Date:** 2026-10-03
**Context:** Red line 3 (never overwrite the user's edits silently) and the wish not to pay for
a second call after fixing a word by hand.
**Decision:** Each source file gets `v2/voices/<name>-<id>/` (the id is a short hash of the
source's full path, because clips are often all called `clip_01.mp4`) holding `audio.mp3`,
`transcript.json`,
the `.srt` and (with `--preview`) `preview.mp4`. A re-run reuses a transcript whose stored
fingerprint matches the extracted audio; if it does not match, the run refuses and names
`--fresh` or `--work`. An existing `.srt` is never replaced without `--overwrite`.
**Why:** The hand-edited transcript is the valuable file, so it is the thing that is kept and
guarded. The fingerprint is a hash of the extracted audio, which ffmpeg produces identically
from the same source, so the check is stable across runs.
**Supersedes:** —

### D-107 — Styled subtitles ship as an .ass file and a transparent overlay .mov
**Date:** 2026-10-03
**Context:** The owner asked for premium subtitles with a font of their own and the spoken word
highlighted (H-107), to add in their own editor. An `.srt` carries text and times only, so no
editor can show a font or a per-word highlight from it; an `.ass` can carry both, but CapCut
does not play its per-word timed transforms or layers.
**Decision:** `--style NAME` writes the cues as an `.ass` file (fonts, colours, and per-word
`	` transforms timed from each word's own start) and renders it with libass onto a transparent
canvas as a ProRes 4444 `.mov` the size and frame rate of the source video, to drop on the track
above it. The `.srt` is still written. Fonts are OFL files shipped in `voice_subs/fonts/`.
**Why:** libass is already inside ffmpeg, so the look costs no renderer of our own; the overlay
is the one format that carries a styled, word-timed subtitle into CapCut, and its codec is the
one V1 proved CapCut reads with transparency (V1 D-005). The `.ass` stays useful for players and
editors that read it.
**Supersedes:** —

### D-108 — The overlay's alpha comes from drawing twice, on black and on white
**Date:** 2026-10-03
**Context:** ffmpeg's own transparent mode (`ass=...:alpha=1`) was measured squaring a half-clear
pixel's opacity: a dim word at 45% came out at 20%, so over the video the overlay looked much
darker than the same subtitles burned in.
**Decision:** `render_overlay` draws the `.ass` on an opaque black and an opaque white canvas and
reads the true opacity from their difference (on black a pixel is colour x alpha, on white that
plus (1 - alpha) x 255), then divides the colour back out. All in one ffmpeg filter graph.
**Why:** It is exact for anything libass draws, whatever the layers and blurs, and was measured:
over the same frames, pixels that differ from the burned-in preview by more than 24 levels fell
from 1.2% to 0.03% (H.264 noise). `tests/test_style.py` holds a dim word to its 45%.
**Supersedes:** —

### D-109 — Cue display times: lead 0.1 s, hold to the next cue, no blink
**Date:** 2026-10-03
**Context:** The `video-judge` agent found every style blinking at each back-to-back cue (each
fading out and the next fading in, 1-2 empty frames), the last word of a cue fading while still
being said, and the final line (the speaker's sher) gone 3.5 s before the clip ended.
**Decision:** A cue appears 0.1 s before its first word (never over the previous cue's last
word); stays until the next cue if the gap is under 0.4 s, else 0.4 s into the silence; at
least 1.2 s on screen; the last cue stays up to 4 s, to the end of the clip. Styled cues fade
only across a real gap. A length break moves one word back rather than strand a postposition
or a determiner. Applies to the `.srt` too. Supersedes D-105's 1.0 s hold and 0.05 s gap.
**Why:** Text that arrives with the voice reads late; text that leaves with the last syllable
reads cut. These are display times around the words' audio times, which stay untouched (red
line 2): the highlight still follows each word exactly.
**Supersedes:** part of D-105

### D-110 — Three looks; the signature sets a hero word in gold serif
**Date:** 2026-10-03
**Context:** H-107. Round one (Poppins ink, cinema, a "pill" box) was judged competent but not
a signature; pill was the most common look on Reels and was dropped.
**Decision:** `signature` (default): Instrument Sans SemiBold body, brightening as said, and one
hero word in Instrument Serif Italic at 1.3x, gold #FFD37A, with 4 px more space on each side
(an italic crowds its neighbours; 10 px read as a double space). The hero waits dim white like any word (a dim gold read
khaki) and turns gold when said. Round 2 of the judge found a hero in 43 of 53 cues, so it
stopped being special, and picks like adverbs and repeats; now: candidates are words of 4+
letters (or code-like: MP4, MPV) that are not grammar, common verbs or adverbs (`style.COMMON`,
-ly words); best = code-like, then longest (long words are the rare ones), then said once in
the clip; at most one hero every 3 s, never the same word within 10 s, none in a cue under 1 s,
and if a cue's best word is held back the cue gets none rather than a weaker one. Heroes are
placed best-first across the whole clip, the last cue's first of all (round 3: placing them in
time order let "prayaas" block "experience" and "jindagi" block the closing "tajurba"). Result
on the three test clips: 7 of 15 (experience, Maturity, priy, mushkil, koshish, line, tajurba),
6 of 11 and 8 of 23 cues. `ink` and `cinema`
stay as alternatives. Fonts: Instrument Sans (static SemiBold instanced from the OFL variable
font with fontTools) and Instrument Serif, both OFL, shipped in `voice_subs/fonts/`.
**Why:** A hero chosen by duration alone picked verbs (aata, lagta, karein); by length it picks
content words (prayaas, sher, mushkil, koshish, tajurba; confuse, organisms, conception, crude;
recording, folder, dropdown, MPV). A frequency list would rank rarity better but is a large
dependency for one ranking; length is the stand-in. The sans + serif-italic mix
is not a caption-app preset, and the one gold word gives a scrolling eye an anchor per line.
Instrument Sans and Serif are one design family, so the mix looks intended.
**Supersedes:** —

### D-111 — Over a bright picture, a soft dark plate replaces the halo
**Date:** 2026-10-03
**Context:** Judge round 2: on a whiteboard (the Watts clip) white and gold text washed out and
dim words vanished; a halo is not enough there.
**Decision:** `media.band_light` reads a 54x96 grey copy of the video at 5 fps and takes the
90th-percentile level of the band the text sits in (middle 80% wide) for each cue's time. If any
cue is above 0.72, the whole clip's layer 0 is a plate instead of a halo (round 3: switching
mid-clip read as a glitch): libass's opaque box (border style 3, drawn per glyph so it hugs
each line), black at 62%, padded 26 px sideways and not at all vertically (two lines' plates
then meet without a darker overlap band), blurred 6; on a plate a word not said yet is 75%
white instead of 57%. Measured:
the Watts clip is 1.00 throughout, the tutorial 0.27 until its last four cues (0.89-0.98), the
Hindi clip at most 0.63, so only the bright cues get one.
**Why:** The plate appears only on clips that need it, so the dark-clip look stays as it was.
The judge rates per-line plates as closed-caption-like; one rounded plate per cue would need the
text measured, and is the next step if bright clips matter to the owner. The
90th percentile, not the mean, because one bright button behind half the words is enough to
wash them out.
**Supersedes:** —

### D-112 — Cues: runs cut evenly at the best seams; scraps join a neighbour
**Date:** 2026-10-03
**Context:** Judge round 2: greedy filling left scraps ("aata hai." alone for 0.6 s, "this."),
split phrases ("kisi na kisi |", "your | screen"), and a 40-280 ms blink where a pause of
0.4-0.85 s left a blank between a fade-out and a fade-in.
**Decision:** Words are first cut into runs at sentence ends and pauses. A run too long for one
cue is cut into the fewest cues that fit, by a small dynamic programme: pieces as even as
possible, a cut beside a word that leans on its neighbour costs 400 (Hinglish postpositions,
light verbs and object pronouns lean back; determiners, subject pronouns, conjunctions,
prepositions, -ly intensifiers and English function words lean forward; `cues.leans_back` /
`leans_forward`, also used for the line break inside a cue),
a comma or a breath helps. A scrap (under 3 words or 0.9 s) joins the neighbour on its own
sentence's side if within 1 s and the result still fits (48 characters, 6 s). A blank under
0.35 s between cues is closed.
**Why:** Even pieces read at an even pace, and the viewer never meets a two-word flash or a
line that ends on "the". Every word still appears once, in order (tested).
**Supersedes:** the greedy fill in D-105

### D-113 — Signature only, bold, on a transparent strip the owner places
**Date:** 2026-10-03
**Context:** H-107: the owner picked `signature`, asked for a bolder font, and said placement is
theirs ("jidher chaiye udar rakhunga").
**Decision:** One look. The body is Instrument Sans Bold (a static 700 instance of the OFL
variable font, as the SemiBold was); the hero word stays Instrument Serif Italic, which has no
bold, so none is faked (`\b0` on it). The overlay is no longer the full frame with the text 30%
up: it is a strip the video's width and 420 px tall at 1080 wide, the text centred in it, so it
carries no position. It is made on every run (no `--style`); the preview lays that same strip on
the video. Removed: `ink`, `cinema`, `--style`, and the automatic plate (D-111), which measured
the picture's light where the engine had put the text and so no longer knows where the text
will be.
**Why:** The owner's own words; and one look, one command, fewer moving parts. The strip renders
in ~30 s for a 33 s clip (three full-frame looks took ~4 min).
**Supersedes:** D-111; the three-look part of D-110
