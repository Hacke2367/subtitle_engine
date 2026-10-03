# Pending Work (V2)

Last updated: 2026-10-03 (light version built)

## WIP

`feature/v2-video-subs` (worktree `C:\subtitle_engine\.claude\worktrees\voice-subtitles`), cut
from `feature/voice-subtitles`, so it carries the V2 kickoff and scaffold as its first commit.
Branch holds the whole light version (spec 00) and is waiting on the owner's review; it has not
been merged into `dev`.

## Current focus

**Owner picks the signature subtitle style (H-107).** On top of the light version (spec 00:
video → Roman `.srt`), `--style` now draws premium subtitles with each word lit as it is said,
as a transparent overlay `.mov` to drop above the video in CapCut (spec 00b). Three looks:
`signature` (recommended: sans line + a gold serif-italic hero word on about every other cue),
`ink`, `cinema`. Judged in rounds by the `video-judge` agent; every round's fixes are in. Its
verdict: signature ready on dark talking-head clips (7/10, "ruk ke dekhega: haan"); on bright
backgrounds (whiteboard, white UI) readable now, with a per-line plate it calls
closed-caption-like (5/10): work in progress.

Watch first: `v2/voices/clip_01-9b5726/compare_styles.mp4` (old plain `.srt` vs the three looks,
same clip). Signature on English: `v2/voices/03_dYSQ1NF1hvw_00.04.33-2542ea/preview_signature.mp4`
(whiteboard), `v2/voices/clip_01-91c782/preview_signature.mp4` (screen recording).

Try it:

```
set ELEVENLABS_API_KEY=...        (or put it in v2/.env)
cd C:\subtitle_engine\.claude\worktreesoice-subtitles2
C:/subtitle_engine/venv/Scripts/python -m voice_subs.cli subs "<video>.mp4" --style signature --preview
```

Everything lands in `v2/voices/<name>-<id>/`: `audio.mp3`, `transcript.json`, the `.srt`,
`<name>.signature.ass`, `<name>.signature.mov` (the overlay: drag it onto the track above the
video in CapCut, at 0:00) and `preview_signature.mp4`. `voices/` is gitignored.

## Next up

1. **Owner:** watch `compare_styles.mp4` and pick the signature (H-107); say which hero words
   read wrong, and whether the text should be bigger or smaller.
2. **Owner:** drop one overlay `.mov` into CapCut above its video and confirm it lines up and
   stays transparent (V1 proved the codec; this overlay has not been tried in CapCut yet).
3. **Owner:** romanization (H-106), code licence (H-103), own-voice and long recordings (H-104).
4. Then, in plan order: step 02 (an hour of audio in parts), step 05 (LLM breaks and
   punctuation, and maybe hero-word choice).
