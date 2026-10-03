# Spec 00b — Styled subtitles: a signature look, each word lit as it is said

**Status:** built, waiting on the owner's pick of a style
**Branch:** `feature/v2-video-subs`
**Raised:** 2026-10-03 (owner, H-107)
**Builds on:** spec 00 (the transcript, its word times, and the cues)

## What the owner asked for

> "ye subtitle ko ashetatic banao and audio ke sath sync ho … font choto ho ache ho … premium
> font use karo, jab wo words aa raha hai tou thoda sa uspe highlight bhi ho … apne ko ek
> signature style and font chaiye — tumne jo subtitle diya hai agar mein ye use karunga tou log
> skip kar denge."

And earlier: "tum mujhe sirf subtitle do, add mein kar lunga" — the owner adds them in their
own editor.

## What it does

`voice-subs subs <video> --style signature|ink|cinema|all [--preview]`, on top of the `.srt`:

- `<name>.<style>.ass` — the styled subtitles as a file.
- `<name>.<style>.mov` — the same, alone on a transparent canvas (ProRes 4444 with alpha, the
  video's size and frame rate). Dropped on the track above the video in CapCut, it lines up
  from 0:00. This is the file the owner adds (D-107); an `.srt` cannot carry a font or a
  highlight, and CapCut does not read `.ass`.
- `preview_<style>.mp4` with `--preview` — burned in, to judge by eye.

Every word goes upcoming → being said → said, switched at its own start time from the
transcript. The three looks:

| Style | Look |
|-------|------|
| `signature` (default pick) | Instrument Sans SemiBold, 66 px. The cue waits at ~57% white and brightens word by word. One hero word per cue — the longest word that carries meaning — is set in Instrument Serif Italic at 1.3×, in gold (#FFD37A), and glows while said. |
| `ink` | Instrument Sans SemiBold, 68 px. The cue waits at 60%; the word being said turns gold with a soft glow, then white. |
| `cinema` | Instrument Serif, 88 px, ivory, left-aligned. Nothing shows before it is said; words arrive one by one. A quote look. |

All three: two balanced lines at most (~24 characters each), never splitting a word from the
one it leans on ("sach mein", "ek line"); a soft dark halo so they read on any background; the
block sits 30% up from the bottom, clear of faces and of a clip's own bottom caption box.

## Timing (applies to the `.srt` too)

- A cue appears 100 ms before its first word; a word lights 60 ms before it is heard.
- Back-to-back cues swap with no gap and no fade, so nothing blinks.
- A cue stays until the next one, or 0.4 s into a silence; at least 1.2 s on screen; the last
  cue stays to the end of the clip (at most 4 s).
- The words' own times are never moved (red line 2); only the display around them.

## Acceptance

1. Each style renders on the 33 s Hindi clip with no word changed (checked by tests on every
   layer) and every word lit at its own time. **Met.**
2. The overlay `.mov` over the video looks the same as the burned-in preview. **Met**: pixels
   off by more than 24 levels fell from 1.2% to 0.03% after D-108.
3. The fixes the independent judge asked for in round one are in: no blink between cues, the
   last word never cut off, the first word of a cue always lights, no line split inside a
   phrase. **Met** (tests in `tests/test_cues.py`, `tests/test_style.py`).
4. The owner picks one style as the signature. **Open (H-107).**

## How the looks were chosen

Round one (ink with Poppins, cinema, and a "pill" box behind the spoken word) went to the
`video-judge` agent. Its verdict: ink was the best base but read like a caption app's karaoke
preset; pill was the most generic look on Reels and had a bug; cinema had the most character
but is a quote look, not captions; none was a signature. Its proposal — a small sans body with
one hero word in a serif italic, in gold — became `signature`. Pill was dropped.

## Not in this version

- The owner choosing the hero word by hand. The rule picks the longest meaningful word; a word
  list (`style.COMMON`) keeps grammar and common verbs out. If its picks read wrong, a manual
  mark in the transcript is the next step.
- A quote mode (switching to the cinema look when the speaker recites a sher). It needs a way
  to know a quote is being said; left out until the signature itself is approved.
- Burned-in final videos. The product is the overlay; previews are for review.
