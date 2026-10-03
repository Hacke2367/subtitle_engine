# Pending Work (V2)

Last updated: 2026-10-03 (light version built)

## WIP

`feature/v2-video-subs` (worktree `C:\subtitle_engine\.claude\worktrees\voice-subtitles`), cut
from `feature/voice-subtitles`, so it carries the V2 kickoff and scaffold as its first commit.
Branch holds the whole light version (spec 00) and is waiting on the owner's review; it has not
been merged into `dev`.

## Current focus

**Owner tries the signature overlay in CapCut.** The look is decided (H-107: signature, bold).
Every run now writes a plain `.srt` and the signature subtitles: `<name>.ass` and `<name>.mov`, a
transparent strip (the video's width, 420 px tall at 1080) with each word lit as it is said, for
the owner to place in CapCut (D-113).

Watch: `v2/voices/clip_01-9b5726/preview.mp4` (33 s Hindi); the file to drop into CapCut is
`v2/voices/clip_01-9b5726/clip_01.mov`. English: `v2/voices/03_dYSQ1NF1hvw_00.04.33-2542ea/`
and `v2/voices/clip_01-91c782/`.

Run it:

```
set ELEVENLABS_API_KEY=...        (or put it in v2/.env)
cd C:\subtitle_engine\.claude\worktrees\voice-subtitles\v2
C:/subtitle_engine/venv/Scripts/python -m voice_subs.cli subs "<video>.mp4" --preview
```

## Next up

1. **Owner:** drop `clip_01.mov` onto a video in CapCut desktop: is it transparent, in sync, and
   does it move and scale as wanted? If CapCut also reads QuickTime Animation, the overlay can
   shrink from ~138 MB to ~20 MB (spec 00b).
2. **Owner:** any hero word or spelling that reads wrong (H-106 for spellings).
3. **Owner:** code licence (H-103); own-voice and long recordings (H-104).
4. Then, in plan order: step 02 (an hour of audio in parts), step 05 (LLM breaks and
   punctuation).
