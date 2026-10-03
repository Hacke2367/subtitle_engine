# Spec 00b — Signature subtitles: each word lit as it is said

**Status:** built; owner picked the look (H-107); overlay not yet tried in CapCut
**Branch:** `feature/v2-video-subs`
**Raised:** 2026-10-03 (owner, H-107)
**Builds on:** spec 00 (the transcript, its word times, and the cues)

## What the owner asked for

> "ye subtitle ko ashetatic banao and audio ke sath sync ho … font choto ho ache ho … premium
> font use karo, jab wo words aa raha hai tou thoda sa uspe highlight bhi ho … apne ko ek
> signature style and font chaiye — tumne jo subtitle diya hai agar mein ye use karunga tou log
> skip kar denge."

Then, after seeing three looks side by side:

> "signature style final karo — just font ko thoda aur bold karo. and tum jagha kyu select kar
> rahe ho?? kyuki tum mujhe just subtitle dogo mein manually usko capcut mein edit karunga
> jidher chaiye udar rakhunga."

## What it does

`voice-subs subs <video> [--preview]` writes, in the work folder:

- `<name>.srt` — plain, as in spec 00.
- `<name>.ass` — the signature subtitles as a file.
- `<name>.mov` — the same, on a **transparent strip**: the video's width, 420 px tall at 1080
  wide (two lines and a hero word with room for the glow), the text centred in it. ProRes 4444
  with alpha, the video's frame rate, from 0:00 to the end. The owner drops it on the track above
  the video in CapCut and places it where they want (D-113); an `.srt` cannot carry a font or a
  highlight, and CapCut does not play an `.ass` file's per-word timed effects or layers.
- `preview.mp4` with `--preview` — the video with that same strip laid on it, two thirds of the
  way down: review only.

The look: **Instrument Sans Bold**, 66 px at 1080 wide. A cue waits at ~57% white and brightens
word by word as it is said. About every other cue, one hero word — the word that carries the
line — is set in **Instrument Serif Italic** at 1.3×; it waits dim like the rest, then turns gold
(#FFD37A) with a soft glow when said. Two balanced lines at most (~24 characters each), never
splitting a word from the one it leans on ("sach mein", "ek line", "your screen") and never
leaving one word alone on a line; a soft dark halo behind the text so it reads on any
background.

Hero words (D-110): not grammar, common verbs or adverbs; code-like words first (MP4, MPV), then
the longest (the rare ones), then a word said once in the clip; at most one every 3 s, never the
same within 10 s; placed best-first across the clip, the last line's word first (its payoff).
On the test clip: experience, Maturity, priy, mushkil, koshish, line, tajurba.

## Timing (applies to the `.srt` too)

- A cue appears 100 ms before its first word; a word lights 60 ms before it is heard.
- Back-to-back cues swap with no gap and no fade, so nothing blinks.
- A cue stays until the next one, or 0.4 s into a silence (a blank under 0.35 s is closed);
  at least 1.2 s on screen; the last cue stays to the end of the clip (at most 4 s).
- A long sentence is cut into even cues at its best seams, and a scrap of one or two words
  joins its neighbour (D-112).
- The words' own times are never moved (red line 2); only the display around them.

## Acceptance

1. The signature renders on the 33 s Hindi clip with no word changed (checked on every layer)
   and every word lit at its own time. **Met.**
2. The overlay over a picture looks the same as the subtitles drawn on it directly. **Met**
   (D-108; `tests/test_style.py`).
3. Every round's fixes from the independent judge are in: no blink between cues, the last word
   never cut off, the first word of a cue always lights, no line or cue split inside a phrase,
   no scraps, a hero on about half the cues, the best words kept. **Met.**
4. The owner picks the look. **Met: signature, bolder (H-107).**
5. The overlay drops into CapCut transparent and in sync. **Open: owner to try.**

## How the look was chosen

Three looks (`signature`, `ink`: each word turns gold; `cinema`: words appear one by one in a
serif) went through four rounds of the `video-judge` agent (independent of the builder's view),
starting from a fourth look, a "pill" box, that it rated the most generic on Reels. `signature`
was its own proposal after round one, and its final verdict: 7/10 on a dark talking-head clip,
"ruk ke dekhega: haan". The owner picked it, asked for a bolder body, and took the placement for
themselves; `ink`, `cinema` and the automatic plate for bright clips (D-111) were then removed
(D-113).

## Not in this version

- A background behind the text on bright clips. The halo is all there is; on a whiteboard the
  owner places the strip over a darker area, or adds a shape behind it in CapCut. (The automatic
  plate was removed with the fixed position it was measured at.)
- The owner choosing the hero word by hand. If the rule's picks read wrong, a mark in the
  transcript is the next step.
- A quote mode for a recited sher.
- A smaller overlay file: QuickTime Animation (qtrle) measured 20 MB against ProRes's 138 MB
  for the 33 s strip, lossless, but only ProRes has been used in CapCut so far (V1). Worth
  switching if CapCut reads qtrle.
