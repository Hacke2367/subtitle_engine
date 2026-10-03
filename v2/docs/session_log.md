# Session Log (V2)

Newest first. At most six lines per entry: Did, Decisions, Open, Next.

## 2026-10-03 (2) - styled subtitles: a signature look, words lit as said

- Did: `style.py` (.ass, 3 layers per cue) + transparent ProRes overlay (`media.render_overlay`),
  `--style`; fonts Instrument Sans/Serif (OFL); cue display timing; line breaks that keep
  phrases; plate on bright clips; hero words; judged in rounds by `video-judge`; spec 00b.
- Decisions: D-107 (.ass + overlay .mov), D-108 (alpha by black/white matting: ffmpeg's alpha
  mode squared opacity), D-109 (lead/hold, no blink), D-110 (signature + hero word),
  D-111 (plate), D-112 (even cue splits, scraps joined).
- Open: H-107 (owner picks the style); overlay not yet tried in CapCut.
- Next: owner watches `voices/clip_01-9b5726/compare_styles.mp4`.

## 2026-10-03 - light version: a short video -> a Roman .srt

- Did: built `voice_subs` end to end on `feature/v2-video-subs` (media, scribe, roman,
  transcript, cues, cli) + 35 offline tests; measured on a 33 s Hindi clip and a 38 s English
  clip from `C:\youtube_cut_shorts\out`; spec `docs/specs/00_video_to_srt.md`.
- Decisions: H-105 (light version, video in); D-103 Scribe, D-104 rules romanization,
  D-105 cue numbers, D-106 work folder + transcript cache.
- Open: H-106 (romanization good enough?), H-103 (licence), H-104 (owner's own voice, long file).
- Next: owner watches `v2/voices/clip_01/preview.mp4`, then step 02 (long audio) or step 05 (LLM).
