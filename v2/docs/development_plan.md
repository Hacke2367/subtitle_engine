# Development Plan: V2, Voice to Subtitles

Source of truth for WHAT and WHY: `docs/project_context.md`. This file orders the work (D-102).
Steps run in order. Each gets a spec in `docs/specs/NN_<slug>.md` before any code. Paths here are
relative to `v2/`. The owner can reorder any step before it starts.

## Status board

| #  | Step                                              | Branch                          | Status      |
|----|---------------------------------------------------|---------------------------------|-------------|
| 00 | Light version: a 30–40 s video → a Roman `.srt`   | `feature/v2-video-subs`         | Built, owner review |
| 00b | Styled subtitles: signature look, word highlight | `feature/v2-video-subs`        | Built, owner picks a style |
| 01 | Voice → transcript: Roman Hinglish, word times    | `feature/v2-transcribe`         | Done in 00 for one short file |
| 02 | Hour-long audio in parts, exact seams             | `feature/v2-long-audio`         | Not started |
| 03 | Cues at pauses → `.srt` (rules only)              | `feature/v2-srt-export`         | Done in 00 |
| 04 | Edit the transcript, re-export for free           | `feature/v2-edit-reexport`      | Done in 00 |
| 05 | LLM: sentence ends, line breaks, punctuation      | `feature/v2-llm-breaks`         | Not started |
| 06 | Milestone 1 proof (the success signal)            | `docs/v2-milestone1-proof`      | Not started |
| 07 | Local web UI (milestone 2)                        | `feature/v2-local-web`          | Not started |

## Steps

**00 Light version (added 2026-10-03, H-105).** One command for one short video: audio out with
ffmpeg, one Scribe call, Devanagari rewritten in Roman, cues at pauses, an `.srt`. Spec:
`docs/specs/00_video_to_srt.md`. It settles the transcript format, the engine choice and the cue
rules, so steps 01, 03 and 04 are done for a single short file; what is left of them is the long
recording (step 02) and whatever the owner's review of the output asks for.

**00b Styled subtitles (added 2026-10-03, H-107).** The owner wants premium subtitles with a
signature font and the spoken word highlighted, added in their own editor. `--style` writes an
`.ass` and a transparent overlay `.mov` per look (D-107, D-108); three looks, judged by the
`video-judge` agent and reworked once. Spec: `docs/specs/00b_styled_subtitles.md`.

**01 Voice → transcript.** Pick the transcription engine by testing candidates on the owner's
clip (H-104): Roman output for Hindi words, word-level times, cost per hour. Output is the
transcript file, V2's one contract between stages; its format is settled here.

**02 Hour-long audio in parts.** A 60-minute recording is processed in parts with bounded memory,
and the parts join with every word exactly once (red line 1).

**03 Cues at pauses → `.srt`.** One cue per sentence or phrase, split at the speaker's pauses,
timed from the audio (red line 2), by plain rules. Imports into CapCut. This is the baseline
step 05 must beat.

**04 Edit and re-export.** The user fixes words in the transcript; export runs again without a
new transcription call and never overwrites the edits silently (red line 3).

**05 LLM breaks.** The LLM decides sentence ends, line breaks, words that stay together, and
punctuation, and cannot change a word (checked, red line 1). Compared against step 03's output.

**06 Milestone 1 proof.** The three checks in the project context's success signal, written up
as a report.

**07 Local web UI.** Upload a voice file, review and edit the subtitles, download the `.srt`;
runs on the user's machine with their own keys. Enable the `frontend-design` plugin here (H-102).
