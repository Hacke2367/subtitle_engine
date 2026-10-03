# Pending Work (V2)

Last updated: 2026-10-03 (light version built)

## WIP

`feature/v2-video-subs` (worktree `C:\subtitle_engine\.claude\worktrees\voice-subtitles`), cut
from `feature/voice-subtitles`, so it carries the V2 kickoff and scaffold as its first commit.
Branch holds the whole light version (spec 00) and is waiting on the owner's review; it has not
been merged into `dev`.

## Current focus

**Owner review of the light version.** `voice-subs subs <video>` turns a 30-40 s video into a
Roman-script `.srt` (H-105, spec `docs/specs/00_video_to_srt.md`). Built and measured on two
clips; 35 tests pass offline.

Try it:

```
set ELEVENLABS_API_KEY=...        (or put it in v2/.env)
cd C:\subtitle_engine\.claude\worktrees\voice-subtitles\v2
C:/subtitle_engine/venv/Scripts/python -m voice_subs.cli subs "<video>.mp4" --preview
```

Everything lands in `v2/voices/<name>-<id>/`: `audio.mp3`, `transcript.json`, the `.srt`, and with
`--preview` a `preview.mp4` with the subtitles burned in to check the timing by eye.

Already made, ready to watch (`voices/` is gitignored, so these exist only in the worktree):
`v2/voices/clip_01-9b5726/preview.mp4` (33 s Hindi, 15 cues),
`v2/voices/03_dYSQ1NF1hvw_00.04.33-2542ea/preview.mp4` (38 s English, 12 cues) and
`v2/voices/clip_01-91c782/preview.mp4` (40 s English, 24 cues).

## Next up

1. **Owner:** watch the two previews and say what reads wrong — a cue that breaks in the wrong
   place, a word spelled in a way you would not type (H-106), a cue too fast or too slow.
   The four cue numbers (D-105) are arguments, so any of them moves in one line.
2. **Owner:** the romanization question (H-106) and the code licence (H-103).
3. Then, in plan order: step 02 (an hour of audio in parts, exact seams), then step 05 (the LLM
   decides breaks and punctuation, beating the rules baseline this branch set).
4. Owner: a 30-60 min recording, needed by step 02, and a clip of the owner's own voice (H-104).
