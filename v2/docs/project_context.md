# Project Context: V2, Voice to Subtitles

Kickoff interview: 2026-09-29 (H-101). Lives in `v2/` of the Kinetic Lyric Engine repository
(H-102); V1 (`../docs/project_context.md`: song + known lyrics → animated overlay) continues on
its own track and is not changed by this file. Items marked *(assumed)* were stated by Claude and not objected to;
the owner can overturn any of them.

## Problem

Creators who talk in Hinglish (Hindi-English mix) make long videos: podcasts, vlogs,
talking-head explainers, up to an hour. They need subtitles, and today every route is weak:

- Built-in captions fail on Hinglish. Instagram's auto-captions do not support Hindi. CapCut's
  auto-captions moved behind its Pro plan and handle mid-sentence Hindi-English switching poorly.
- Hinglish-specific tools exist (Kalakar, DesiCaptions, CapsAI, videocaptions.ai and others),
  but they are hosted, closed and paid monthly, and built mostly around short-form clips.
- Open-source caption tools are English-centric and aimed at burned-in animated captions for
  short clips, not a clean Hinglish subtitle file for a long video.
- Naive tools break subtitles in the wrong places (a phrase split across two cues, a cue that
  runs over the speaker's pause), so the creator fixes breaks by hand.

## Objective

**Milestone 1 (first working version):** a command on the owner's laptop turns a voice
recording of up to 60 minutes, spoken in Hinglish or English, into an `.srt` subtitle file:

- Text in Roman script throughout.
- One cue per sentence or phrase (not per word), timed to the voice.
- A break wherever the speaker pauses, and at sentence ends.
- An LLM decides where sentences end, where lines break, which words stay together, and the
  punctuation. It never changes the words.
- The transcript is editable; after a fix, the file is exported again without transcribing
  again (H-101: automatic first pass, edit afterwards).

**Milestone 2:** a local website on top of the same engine. The user runs it on their own
machine with their own API keys, opens it in a browser, uploads a voice file, reviews and
edits the subtitles, and downloads the `.srt`.

## Who it's for

Hinglish-speaking creators who edit their own long-form videos. The owner is the first user.
The project is open source (H-101), and users bring their own API keys.

## Scope

**In scope:**
- Input: a voice recording (audio only, no video), up to 60 minutes.
- Speech in Hinglish or English; output always in Roman script. Hindi that the transcription
  returns in Devanagari is converted to Roman.
- Long audio processed in parts, so the machine is never overloaded; the parts join with no word
  lost or repeated at a seam.
- Cues at sentence or phrase level, split at the speaker's pauses.
- LLM for sentence boundaries, line breaks and punctuation only.
- Output: `.srt`, importable into CapCut (desktop), Premiere Pro and DaVinci Resolve.
- Correction path: edit the transcript, re-export for free (no new transcription call).
- Milestone 2: local web UI (upload, review/edit, download).

**Out of scope:**
- Rendered or animated output: overlays, fonts, animation, theme choice, and the
  render-and-critique loop discussed before the kickoff. The owner chose a plain subtitle file;
  styling is applied in the video editor. V1's themes stay V1-only.
- Styled subtitle formats (`.ass`) and per-word or karaoke timing in the output.
- Emphasis (CAPS, emoji), LLM correction or rewriting of words, translation.
- Video upload or video processing.
- Devanagari output; languages other than Hinglish and English.
- A hosted public website, accounts, payments; anything SaaS.
- Speaker labels (who is speaking) *(assumed)*.
- Singing and songs *(assumed)*: V1 already covers songs with known lyrics.
- Live or realtime captions.

## Constraints

- **Machine:** Windows 11 laptop, i5-1235U, 8 GB RAM, no dedicated GPU (as V1). No heavy local
  speech model, so transcription runs through an API *(assumed; engine picked in the spec)*.
  Long audio in parts keeps memory bounded. V1 and V2 work runs in parallel on this machine:
  never run both tracks' heavy jobs (gate, full renders, long transcriptions) at once.
- **Money:** transcription and LLM cost per hour of audio. The owner pays during development;
  every user pays their own through their own keys. The owner already has an ElevenLabs account
  (used by V1).
- **Open source:** V2 must not depend on non-commercial model weights (V1's local aligner uses
  CC-BY-NC MMS_FA weights, V1's D-010), so anyone can use it *(assumed)*. Code licence: open item.
- **Roman script:** transcription engines often return Hindi words in Devanagari. Getting clean
  Roman Hinglish is the core risk and the first thing the spec must test.
- **Editors:** CapCut desktop imports SRT (and LRC, ASS) and styling is applied inside CapCut;
  DaVinci Resolve discards subtitle styling on import; Premiere has no native per-word highlight.
  Hence a plain `.srt`.
- **Secrets:** API keys live in `.env` (gitignored), never in code, fixtures or logs.

## What already exists that's close

- **Hosted Hinglish tools:** Kalakar (free plan for 2-minute videos, Creator ₹599/month, SRT
  export, claims 200,000+ users), DesiCaptions (accepts audio, exports SRT/VTT/ASS), CapsAI,
  videocaptions.ai, AutoCap, Captiq. Closed and paid; mostly short-form.
- **CapCut auto-captions:** Pro-only since 2025, weak on Hinglish code-switching.
- **Open source:** `francozanardi/pycaps` (MIT; CSS-styled animated captions, AI word tagger),
  `browser-use/video-use` (MIT; agent video editing with a render → self-check loop), Capite
  and `ai-video-captions` (MIT; preset animated captions). All English-centric and built around
  burned-in visuals; none produces Hinglish Roman SRT with meaning-aware breaks. The owner chose
  to build V2's own system (2026-09-29).
- **In this repo:** V1's ElevenLabs client (`src/lyric_engine/eleven.py`) and its flag /
  validation habits (`timing.py`) are patterns to copy, not import: V2 stays independent of V1's
  package so `v2/` can become its own repository (H-102).
- **Why not just use them:** open source and free with the user's own key, Roman Hinglish,
  hour-long audio, and breaks that follow meaning and pauses, together; and the owner wants to
  contribute to open source. The edge over hosted tools is narrower than under the earlier
  animated plan, so the success signal below has to prove it.

## Success signal

*(assumed thresholds; the spec confirms the numbers)*

1. A 60-minute Hinglish voice recording becomes an `.srt` on the owner's laptop without a crash,
   and every spoken word appears exactly once, including at the seams between parts.
2. Imported into CapCut, five spot checks spread across the hour show every cue appearing and
   leaving with the voice, with no drift.
3. On the same 10-minute clip, the owner compares V2's `.srt` with one hosted tool's free SRT
   export: V2's needs fewer hand fixes to its breaks, and contains no Devanagari.

## Red lines

1. **Never alter the spoken words.** The words, their spelling and their order match the
   transcript (including the user's own edits). The LLM only adds punctuation and breaks. Every
   word appears exactly once, including at the seams between parts.
2. **Never guess a timing.** Cue start and end times come from the audio. A stretch that cannot
   be timed is flagged and reported, never given an estimated time.
3. **Never overwrite the user's edits silently.** Running again keeps hand corrections, or
   refuses and says why.
4. **Keys and voice stay the user's.** API keys never reach code, the repo or logs; the voice
   is sent only to the services the user configured.

## Open items

- Code licence (MIT, Apache-2.0 or other): owner's call.
- Transcription engine and LLM provider: chosen in the first spec, tested on Roman Hinglish.
- Test audio from the owner: one 30–60 s Hinglish voice clip, and one long (30–60 min) recording.
