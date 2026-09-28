# Background tools: research notes

Researched 2026-09-29 for H-023 (engine-made backgrounds matched to the song's vibe). Prices and
versions are as read on that date; re-check before paying for anything. "Tested here" means run
on the owner's laptop (i5-1235U, 8 GB RAM, Intel Iris Xe, Python 3.10, ffmpeg 8.0.1).

## 0. Decisive points

- A background is drawn by the engine, not bought as footage: procedural scenes cost nothing per
  song, can follow `beats.json`, and carry no footage licence.
- Two ways to draw a scene, both work on this laptop: numpy + PIL (the look sheet, section 1) and
  GPU shaders through `moderngl` (section 2). Shaders are far faster and look richer; numpy needs
  no new dependency.
- AI is for still art pieces (a couple, a city, a window), generated once and reused, a fraction
  of a rupee each. AI video for a whole short is too expensive (section 6).
- A scene's props must stay outside the theme's lyric block (safe zone x 60-960, y 380-1540).
  Pop Karaoke's block is the tallest: past line plus current line filled y 500-1420 in the test.

## 1. Look sheet (review only)

`songs/_review/backgrounds/bg_looks.py` draws four looks with numpy, PIL and scipy, which are
already installed: Silhouette, Space, Peaceful, 90s VHS. Soft layers (sky, nebula, mist, light
leaks) are drawn at 270x480 and enlarged; crisp layers (stars, birds, tree, cassette, tape text)
are drawn at full size. Beat pulses come from `beats.json`.

Measured here: 1,680 frames (four 14 s clips) took 8 min 16 s, about 0.3 s per frame with the
overlay composited and the mp4 encoded, so a 30 s short adds about 4.5 minutes. The 90s VHS clip
came out at 108 MB for 14 s (crf 19): per-frame tape noise is expensive to encode, and a platform
re-encode will smear it, so the product version needs lighter noise.

### Sheet 2: backgrounds the song drives

The owner found sheet 1's scenes fine but common (H-024). What a stock background under a song
cannot do, and this engine can: it knows when every word is sung, where that word sits on screen
(`laid_out_lines` with the theme's layout), the beats, and the marked words.
`songs/_review/backgrounds/ideas/bg_ideas.py` prototypes three looks built on that:

- **Lakeer:** a pen of light underlines each word while it is sung, swoops to the next word in
  the gap and circles a marked word; the line fades behind it like a light painting.
- **Boond:** a wave simulation (270x480 grid, rendered as a moving reflection); each word drops
  into it at its own place, held words keep dropping, the first marked word brings the moon out.
- **Rangoli:** rings of petals, dots, zigzags and diamonds drawn on the beats around the lyric
  block, finished on the last word; each marked word lights a diya.

Measured here: about 0.5 s per frame for each of the three, overlay and encode included, so a
30 s short takes about 7.5 minutes. Found while making Boond: a bright glint crossing Lofi's thin
text made it unreadable, so under the words only the dark side of a ripple shows.

Three ideas behind them, for any future look: react to the words (sync is satisfying to watch),
build towards a payoff on the last word (a reason to stay to the end, and an end frame that can
be the thumbnail), and take the imagery from the lyrics (Khidki's "shamaa" gave the diyas).

## 2. Libraries

| Library | Licence | State | On this laptop |
|---|---|---|---|
| [moderngl](https://github.com/moderngl/moderngl) | MIT | 5.12.0, active | Tested here: headless context works on Iris Xe; an fbm-noise shader at 1080x1920 with read-back to numpy ran at about 55 fps |
| [wgpu-shadertoy](https://github.com/pygfx/shadertoy) | BSD-2 | 0.2.0, small project | Tested here: needs `wgpu<0.23` and `glfw`; about 29 fps offscreen. Runs pasted Shadertoy code; the licence of each Shadertoy shader is its author's and was not verified |
| [ShaderFlow](https://github.com/BrokenSource/ShaderFlow) | AGPL-3.0 | 0.11.3, active | `pip install` failed: its `imgui-bundle` dependency has Windows wheels for Python 3.11-3.14 only. Ideas only |
| [DepthFlow](https://github.com/BrokenSource/DepthFlow) | AGPL-3.0 | 1.0.1, active | Still image to 2.5D parallax. Depends on ShaderFlow plus torch; would need its own Python 3.11 environment. Speed on Iris Xe not verified |
| [taichi](https://github.com/taichi-dev/taichi) | Apache-2.0 | 1.7.4 | Not tested; only useful for particle simulation |
| [vispy](https://github.com/vispy/vispy) | BSD | 0.17.0 | Needs a window toolkit; headless on Windows not verified. Skip |

## 3. VHS, CRT and film grain

- [ntsc-rs](https://ntsc.rs/docs/command-line-interface/): Apache-2.0 / ISC / MIT, v0.9.6. The
  Windows download includes `ntsc-rs-cli -i in -o out -p preset.json`. File in, file out; no
  documented pipe or Python binding.
- [zhuker/ntsc](https://github.com/zhuker/ntsc): Apache-2.0, numpy + cv2, not maintained since
  2019; speed not verified.
- ffmpeg 8.0.1 (installed) has `noise`, `chromashift`, `rgbashift`, `lagfun`, `curves`,
  `vignette`, `gblur`, `drawgrid`, `interlace`, and the `perlin` and `gradients` sources
  ([filter list](https://ffmpeg.org/ffmpeg-filters.html)). Recipe, not yet run:
  `noise=c0s=15:c0f=t,chromashift=cbh=3:crh=-3,rgbashift=rh=2:bh=-2,drawgrid=w=iw:h=2:t=1:c=black@0.3,curves=preset=vintage,vignette`

## 4. Silhouette and vector art that allows a monetised channel

- [Openclipart](https://openclipart.org/share): CC0, commercial use, no attribution.
- [FreeSVG](https://freesvg.org/): CC0.
- [Pixabay](https://pixabay.com/service/license-summary/) and
  [Pexels](https://www.pexels.com/license/): commercial use, no attribution; no resale of the
  unmodified file.
- SVG Repo (licence per item) and Vecteezy free: not verified.

## 5. AI image APIs (stills and cut-outs)

| Provider | Price per image | Notes |
|---|---|---|
| FLUX on [Replicate](https://replicate.com/pricing) | schnell $0.003, dev $0.025, 1.1-pro $0.04 | No alpha output; generate black on a flat colour and key by brightness |
| FLUX.2 dev on [fal](https://fal.ai/models/fal-ai/flux-2) | $0.012 per megapixel | Marked for commercial use. The owner's LyricTOimage project already uses fal |
| [Cloudflare Workers AI](https://developers.cloudflare.com/workers-ai/platform/pricing/) | 10,000 free neurons a day, flux-1-schnell included | |
| [Google Gemini image](https://ai.google.dev/gemini-api/docs/pricing) | $0.034 to $0.134 by model | 9:16 supported; no free tier; transparency not documented. Imagen is shut down on this API |
| [OpenAI image](https://developers.openai.com/api/docs/pricing) | about $0.006 / $0.053 / $0.211 (low / medium / high), from secondary sources | Transparent PNG supported, 1024x1536 portrait. Output ownership terms not verified |
| Stability | Core $0.03, Ultra $0.08, remove-background $0.05, from a secondary source | Official page did not load |

## 6. AI video APIs (short loops)

| Provider | Price | Notes |
|---|---|---|
| [Veo 3.1](https://ai.google.dev/gemini-api/docs/veo) | Lite $0.05/s (720p), $0.08/s (1080p); Fast $0.10-0.12/s; Standard $0.40/s | Clips of 4, 6 or 8 s; 9:16; first and last frame input |
| [Runway](https://docs.dev.runwayml.com/guides/pricing/) | gen4_turbo $0.05/s, gen4.5 $0.12/s | |
| [Kling 2.5 Turbo Pro on fal](https://fal.ai/models/fal-ai/kling-video/v2.5-turbo/pro/image-to-video) | $0.35 per 5 s, then $0.07/s | Official Kling API price not verified |
| [Luma Ray 3.2](https://lumalabs.ai/api/pricing) | 5 s at $0.15 / $0.30 / $1.20 (540p / 720p / 1080p) | |

Affordable only as one short clip looped under a whole short (about $0.40-0.65 per attempt).
Unique footage for a 30-60 s short costs $3-24 each. No API promises a seamless loop.

## 7. Proposed stack

1. Scenes drawn by the engine: numpy + PIL where that is enough, `moderngl` shaders where a look
   needs more (clouds, nebula, water, light).
2. Figures and objects as cut-outs: CC0 SVGs, or AI stills made once and kept in an asset folder.
3. Tape and film looks on the background only, never on the lyrics (red line 2 keeps the text
   as written; its legibility comes first).
