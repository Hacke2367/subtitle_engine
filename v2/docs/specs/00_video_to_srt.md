# Spec 00 — Light version: a short video → a Roman-script `.srt`

**Status:** built, waiting on the owner's review
**Branch:** `feature/v2-video-subs`
**Raised:** 2026-10-03 (owner, H-105)
**Covers:** the first slice of plan steps 01, 03 and 04, for one short file at a time.

## What the owner asked for

> "ye apna version2 ka light version hai, apna goal simple hai — mein input mein 30 ya 40 sec ka
> video dunga wo usme se audio extract karega — and mujhe wo subtitle dega. thats it."

So: a video in (not a voice file), subtitles out. One command, nothing else.

## What it does

`voice-subs subs <video>`:

1. **Audio** — ffmpeg pulls the sound track out of the video as 16 kHz mono mp3 (~300 kB for
   40 s). The video itself never leaves the machine; only this audio is uploaded (red line 4).
2. **Transcript** — one call to ElevenLabs Scribe (`scribe_v1`) with word-level times. The
   response is saved as `transcript.json`, V2's contract between stages.
3. **Roman** — Hindi words come back in Devanagari and English words in Latin; `roman.py`
   rewrites only the Devanagari, in the spelling a Hinglish speaker types. The engine's original
   is kept beside each word in the transcript, so a romanization can be checked by hand.
4. **Cues** — words are grouped into cues at the speaker's pauses, at sentence ends, and before
   a line gets too long or too slow to read. Times come from the words (red line 2).
5. **`.srt`** — written next to the transcript, ready to import into CapCut.

Options: `--out` (where the `.srt` goes), `--lang hin|eng` (skip detection), `--fresh`
(transcribe again), `--devanagari` (keep the engine's script), `--overwrite`, `--preview`
(a copy of the video with the subtitles burned in, to check the timing by eye — review only).

## Acceptance

1. A 30–40 s Hinglish video becomes an `.srt` with no crash, every spoken word in it once, in
   Roman script. **Met** (33 s clip, 94 words, 15 cues, no Devanagari in the `.srt`).
2. Cues follow the voice: spot checks on the burned-in preview show each cue arriving with the
   words. **Met** (frames at 8.8 s and 24.5 s).
3. Running the command again does not call the API, and never replaces a transcript made from
   other audio, or an existing `.srt`, without being asked. **Met** (tests in `tests/test_cli.py`).
4. An English clip works the same way, with the language detected. **Met** (38 s clip, 12 cues).

## Measured, 2026-10-03

33 s of Hindi speech (a podcast clip from `C:\youtube_cut_shorts\out`), language detected `hin`
at 99%:

```
1
00:00:00,220 --> 00:00:01,840
prayaas karne ka aur fail hone ka

2
00:00:02,380 --> 00:00:04,280
aur vo experience kisi na kisi quantity

3
00:00:04,320 --> 00:00:05,700
mein har field mein kaam aata hai.
```

Whole run: about 20 s for a 33 s clip, nearly all of it the one API call.

## Not in this version

- Long audio in parts (plan step 02): a single call carries a short clip; an hour needs the
  seams handled.
- LLM breaks and punctuation (step 05): the cue rules here are the baseline that step has to
  beat.
- Sentence case. The engine capitalizes the English words it writes; a romanized Hindi word
  starts lowercase. Capitalizing a cue's first word is a punctuation decision, so it belongs to
  step 05, not to a rule here.
- A word's own timing inside a cue (word-by-word highlighting). Out of V2's scope.
