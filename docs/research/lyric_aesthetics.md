# Lyric overlay aesthetics: research notes

Date: 2026-09-26. Research only, nothing built. Input for the V1.1 styling phase
(`pending_work.md` "Next up" 1, H-011). Four web-research passes plus local measurements on
this laptop, marked **[local]**. Vendor claims with no study behind them are marked (vendor).
Owner's bar: a viewer should feel "bahut mehnat lagi hogi" on every overlay.

## 0. Decisive points

1. **CapCut cannot do this.** Its text presets animate a text block as one object; per-word
   timing means one clip per word, attributes copied by hand, timed by ear. Auto lyrics fails on
   Hinglish ("dropped matras, split conjuncts", code-switching "not reliably") and rewrites text.
   Instagram's own lyric sticker (Karaoke / Typewriter / Billboard) is the baseline every viewer
   has seen. The "high-effort" impression must come from per-word behaviour, restraint and
   finish, not from more motion.
2. **Premium is timing and restraint, not effects.** Text lands with the voice; ease-out in,
   ease-in out; overshoot at most 5-10%; only 3-5 hook words per song get an emphasis move; one
   type treatment, palette and motion per song; the past line dims and blurs, the next line
   waits. Over-animation is the most common amateur tell.
3. **Everything six candidate themes need runs in the current PIL sprite pipeline** at 1-3 ms
   per word per frame **[local]**. ProRes encode alone is ~33 ms/frame, so Python has ~40-50 ms
   per frame inside the 10-minute budget. No GPU, no new renderer.
4. **Two real gaps in the current stack:** Devanagari shaping (this venv's Pillow wheel has no
   raqm, so conjuncts and matras render wrong; Latin Hinglish is unaffected) and beat sync (no
   onset data in `words.json`). libass through ffmpeg shapes Devanagari correctly and renders to
   a transparent ProRes canvas **[local, verified]**; it is a viable second route for
   karaoke-family themes.
5. **Fonts:** OFL families with Latin and Devanagari in one file remove the fallback problem:
   Poppins, Anek Devanagari, Tiro Devanagari Hindi, Yatra One, Kalam, Baloo 2, Eczar, Teko.

## 1. The bar: what CapCut and the platforms already give

- CapCut text animation: In / Out / Loop slots per layer (Typewriter, Fade, Fold, Flip-up,
  Bounce, Blur, Glitch, Wave, Scale-up, Dissolve, Trail, Flicker, Ink print, Flutter, ...).
  Keyframes only on position / scale / rotation / opacity of the whole block. No per-character
  or per-word authoring inside a preset.
- Auto lyrics (One word / Multiple / Overlay): line or phrase blocks, handles dragged to fix
  timing; ~20 languages; Hindi/Hinglish unreliable. Auto-caption "word highlight" styles are
  transcription-driven, lock fonts/colours in some presets, and drift after transcript edits.
- Community templates are photo-slot plus line-level lyrics. Popular families: Spotify player
  card (title + artist + progress bar), Apple Music lyric look (big bold lines over blurred
  art), "Lyrics Card" (rounded card), slow-mo / velocity ("Self Aware Slowmo" 592K views),
  shake / beat edits, minimalist lowercase ("Doubt"). Hindi template pages use the same
  mechanics with romantic / devotional imagery and three named text looks: "white glow text",
  "neon text", "bold Hindi fonts".
- Gaps the engine owns: per-word timing on typed Hinglish; per-word emphasis on the sung word
  (fill / glow / scale / blur-others); exact text (red line 2); restyle without re-timing; one
  consistent style across songs.
- "Text behind the subject" (rotoscope) is the strongest single pro signal but is a CapCut-side
  operation (auto cutout on the footage layer). Document as a workflow tip, not engine work.

## 2. Premium signals (amateur vs pro)

**Timing**
- Text lands exactly with the voice; late or lingering text "feels off". One vendor suggests
  landing ~0.2 s early ("priming"); treat as an A/B hypothesis (current `lead_s` = 0.05).
- Not every line animated equally: motion follows the emotional spikes, verse quiet, chorus
  swells. Hard-sync ~60-70% of beats and leave rests.
- Reveal 0.3-0.8 s; fades 200-500 ms; per-character stagger 30-60 ms (snappy) or 80-120 ms
  (thoughtful); a whole line readable within ~1 s; settled text must read on a 6-inch phone at
  arm's length, 50% brightness.
- Phrase grouping (UIST 2023, Ma et al., derived from the top-100 lyric videos): a phrase is
  words sung closely together; long text splits into lines of consistent length; the sung word
  is highlighted; sequential phrases sit near each other. Guideline-following renders scored
  6.80/7 readability vs 6.28 baseline (p < 0.05). The current balanced wrap already does most of
  this; phrase-by-pause grouping is the missing piece.

**Motion**
- Asymmetric easing: ease-out on entry, ease-in on exit; linear reads "robotic". Overshoot
  105-110% then settle. Anticipation and follow-through only on emphasis words.
- Secondary micro-motion, one at a time: slow drift or scale on the held line, glow "breath" on
  a held note, tracking (letter-spacing) expand on entry. Never all at once.
- Semantic, not decorative: choose which words earn scale, weight or position. Consistency:
  pick one type treatment, palette and motion, reuse for the whole song.

**Typography**
- At most two fonts; contrast weights within one family (bold chorus / light verse). Sans
  survives motion better; display faces only for 1-2 words per screen; wide tracking on small
  lowercase reads "editorial".
- Size at 1080x1920: 44 px minimum; 48-64 px typical captions; lyric lines 96-125 px (5-6.5% of
  height) with the hero word larger; 20-28 characters per line, 1-2 lines. Current theme: 84 px,
  up to 3 rows.
- Contrast >= 4.5:1 through stroke, shadow or a scrim. Drop shadow alone fails on bright
  footage. The overlay sits on arbitrary footage, so the `.mov` must carry its own legibility
  layer (the current shadow is a start; a soft scrim option is the next step).

**Finish**
- Depth: duplicate text at 92-95% scale, 60-70% opacity, offset 2-5 px.
- Film grain, vignette and light leaks belong to the footage in CapCut, not to a transparent
  overlay (they would alter alpha and fight CapCut's own grade).

## 3. Style catalogue and candidate themes

| Style (industry name) | Look | Active word / motion | Type, colour | Mood | Fits pipeline |
|---|---|---|---|---|---|
| Karaoke fill (Apple Music) | one big active line, past line dimmed and blurred | left-to-right fill on the sung word; active line spring-scales; blur on inactive lines | bold sans, white on dark | any, pop | yes |
| Spotify UI | scrolling list, current line bright | line-level highlight, fan clones add per-word glow | bold sans, white / grey | aesthetic, lofi | yes |
| Blur-in / soft focus | words resolve from blur | blur radius to 0 with opacity up; inactive lines stay blurred | light sans, cream | romantic, R&B, ballads | yes (nearest premium neighbour of Soft Romantic) |
| Word pop / scale | each word springs in | easeOutBack entrance, overshoot 105-110% | bold sans | upbeat pop | yes |
| Typewriter | letters appear in sequence | character stagger 30-120 ms, caret | mono / grotesque, often outline-only | indie, storytelling, sad lofi | Latin only (Devanagari needs a shaper) |
| Glow pulse / neon | coloured bloom pulsing on beat | glow intensity from beat / bass | pink, blue, purple on dark | synthwave, night pop | needs beat onsets |
| Hormozi bold | 1-3 ALL-CAPS words, huge, stroked | word pops as spoken, one keyword coloured | Montserrat Black / Anton, yellow keyword | talking head, gym, rap | yes, but wrong for romantic |
| Handwritten / write-on | script drawn on | stroke reveal by mask | Caveat, Kalam | acoustic, love songs | partial (mask sweep, not true stroke order) |
| Glitch / phonk edit | blackletter or wide bold, RGB split, scan lines | beat shake, zoom burst, white flash on the drop | Fraktur, white on black | phonk, gym | needs beat onsets |
| Y2K chrome | bubble / chrome / liquid type | bouncy scale, holographic gradients | lime, hot pink, chrome | hyperpop | gradient fill yes, liquid no |
| Lofi minimal lowercase | small lowercase, lots of air | slow fade and rise, long holds | DM Sans / Poppins lowercase, wide tracking | lofi, sad, aesthetic pages | yes |
| Cinematic minimal (Anti-Hero pattern) | small unhurried type inside the scene | "type follows the vocal", earns attention by timing | light grotesque or serif, muted | prestige, singer-songwriter | yes |
| Indian lyrical status | black screen or one photo, centred lines | fade / rise, long holds, floral stickers | Devanagari or roman, warm gradients | Bollywood romantic, WhatsApp status | yes |

Blueprint names mapped: Phonk/Aggressive = phonk edit (beat data required); Lofi/Vaporwave =
lofi minimal lowercase with pastel palette (grain lives in the footage); Pop/Dynamic Karaoke =
karaoke fill / Apple Music stack; Minimalist Cinematic = the Anti-Hero pattern.

**Recommended V1.1 shortlist** (each theme = a `theme.py` value set plus one or two new
primitives; no new inputs for the first three):

1. **Soft Romantic v2**: keep the base; add the blur-focus stack (past line dims and blurs out,
   next line waits blurred at low opacity), glow that follows the word's own duration, a slow
   glow breath on held notes, and exactly one emphasis move (scale to 1.05 or tracking expand)
   on hand-marked words (H-009). New primitives: sprite blur cache, line stack.
2. **Karaoke Fill (Pop)**: left-to-right fill on the sung word, active line scales 1.00 to
   1.04 with a spring, past line dims; Poppins SemiBold; white plus one accent. New primitives:
   fill sweep, quantised scale cache.
3. **Minimal Lowercase (lofi / sad / black-screen status)**: Poppins Light or DM Sans lowercase,
   wide tracking, slow fade and rise, long holds, optional typewriter, sung / current / upcoming
   colour states. New primitives: typewriter (Latin), colour states.
4. **Cinematic Ivory (ghazal, slow ballads)**: Tiro Devanagari Hindi or Cormorant Garamond
   Italic, ivory and antique gold, blur-in reveal, very slow, no glow. New primitive: blur-in.
5. **Beat Pop (Punjabi / party / rap)**: Anton or Bebas Neue with Anek Devanagari, white plus
   mustard or red, 4-6 px stroke, easeOutBack word pops, highlight pill, optional shake on the
   drop. Needs a beat onset list (new input).
6. **Neon (phonk / night pop)**: saturated text with same-hue glow pulsing to the beat. Needs
   beat onsets or an amplitude envelope.

Build order 1, 2, 3 (no new inputs), then 4; 5 and 6 only after beat data exists.

## 4. Primitive library (feasible today, PIL level)

Rule that makes it all cheap: build per-word sprites once (mask to colour plus alpha), transform
sprites (small), composite with C-level `alpha_composite` / `paste`, never touch a full frame in
numpy per frame.

Costs **[local]**, 1080x1920 canvas, ~700x160 word sprite:

| Operation | Cost |
|---|---|
| word sprite GaussianBlur r=16 (L) | 0.9 ms |
| word sprite resize x1.15 BICUBIC / LANCZOS | 0.6-1.0 ms |
| word sprite rotate 3 deg BICUBIC | 3 ms |
| opacity via `point()` + `putalpha` | 0.45 ms |
| karaoke sweep (crop + paste by mask) | 0.6 ms |
| stroke_width=4 draw at 84 px | +1 ms |
| `alpha_composite` one sprite onto frame | 0.4 ms |
| `frame.copy()` / `tobytes()` | 3 / 6.6 ms |
| full-frame GaussianBlur (constant in radius) | 18-60 ms (once per frame at most, never per word) |
| numpy full-frame "over" | 114-130 ms (never) |
| current render, 900 frames incl. encode | 29 s, ~32 ms/frame |
| ProRes 4444 encode alone | ~33 ms/frame on ~8 threads |

| Primitive | Implementation | Per-frame cost |
|---|---|---|
| Fade + rise (have) | opacity ramp, integer y offset at paste | ~0 |
| Karaoke fill / wipe | two sprites (base, hot) sharing the mask; `w = int(sw * p)`; paste `hot.crop((0,0,w,h))` with the same crop as mask; soft edge = 1-D ramp multiplied into the hot alpha (same idea as ASS `\kf`) | ~1 ms |
| Scale pop | `resize` around the anchor; quantise scale to ~24 levels in 1.00-1.25 and cache | 0 cached |
| Blur-in / focus | radius ramps ~12 to 0 with ease-out; cache 8-12 radius levels per word | 0 cached |
| Typewriter / per-glyph stagger | glyph x without breaking kerning: `x_i = font.getlength(text[:i+1]) - font.getlength(text[i])`; per-glyph sprites with delay `i * stagger`. Latin only. | one-time |
| Slide / small rotation | offset at paste; `rotate(deg, BICUBIC, expand=True)` cached at ~10 angles | 0 cached |
| Glow pulse | glow at 3-4 radii precomputed; per frame scale glow alpha by `0.5 + 0.5 * pulse(t)` | <1 ms |
| Colour states (sung / current / upcoming) | keep the L mask; `Image.merge("RGBA", (R, G, B, mask))` or cross-fade two colour sprites | 0.4 ms |
| Tracking expand | re-layout the row with a wider space, or per-glyph sprites sliding out from centre | one-time |
| Fake motion blur | average N shifted copies of the sprite along the motion vector, or `ImageFilter.Kernel` 1xN | 2-5 ms per moving sprite |
| Gradient fill | `Image.merge("RGBA", (gR, gG, gB, mask))` from a `linear_gradient` built once; animated sweep = shift the gradient | 0.4 ms |
| Stroke | `ImageDraw.text(..., stroke_width=n, stroke_fill=...)` | +1 ms one-time |
| Backplate / pill | `ImageDraw.rounded_rectangle` on a sprite-sized RGBA, blurred once | one-time |
| 3-D extrude | 6-10 darkened mask copies at (i, i) offsets under the face | one-time |
| Inactive line dim + blur (Apple stack) | prev / next line sprites at opacity 0.3-0.5, blur r=2-4, scale 0.9 | 0 cached |
| Line scroll | line sprites move with eased y; 3 pastes per frame | ~1 ms |
| Highlight bar | rounded-rect sprite whose x / width interpolate between word boxes, easeOutCubic 120-180 ms | 0.5 ms |
| Emoji | `embedded_color=True` with `seguiemj.ttf` renders colour glyphs offline **[local]** | 5 ms one-time |

Performance rules: quantise every animated parameter and cache at line-build time so per-frame
work is pastes only; keep one persistent canvas and clear only the union bbox of last frame's
sprites (a `frame.copy()` costs more than the pastes); reuse identical frame bytes while a line
is held; blur sprites, never words on the frame; opacity via a precomputed LUT. ffmpeg filters
available in this build for global treatments only: `fade=...:alpha=1`, `gblur`, `tmix` (motion
blur), `overlay`, `zoompan`, `drawtext` with `t` expressions.

## 5. Easing and timing defaults

```
easeOutCubic   = 1 - (1 - x) ** 3
easeOutQuint   = 1 - (1 - x) ** 5
easeOutExpo    = 1 if x == 1 else 1 - 2 ** (-10 * x)
easeOutBack    : c1 = 1.70158; c3 = c1 + 1;  1 + c3 * (x - 1) ** 3 + c1 * (x - 1) ** 2   (~10% overshoot)
easeOutElastic : c4 = 2 * pi / 3;  2 ** (-10 * x) * sin((10 * x - 0.75) * c4) + 1
easeInOutCubic = 4 * x ** 3 if x < 0.5 else 1 - (-2 * x + 2) ** 3 / 2
spring (underdamped): x(t) = 1 - exp(-z*w*t) * (cos(wd*t) + z / sqrt(1 - z*z) * sin(wd*t)),
        w = sqrt(k/m), z = c / (2*sqrt(k*m)), wd = w * sqrt(1 - z*z)
        designer mapping: m = 1, k = (2*pi/T)**2, c = (1 - bounce) * 4*pi/T, T = perceived duration
```

- Material: enter 225 ms, exit 195 ms, cap 400 ms; decelerate curve in, accelerate curve out;
  "never use the same easing for both". NN/g: 100-400 ms practical; 500 ms and up "starts to
  feel like a drag"; entering slightly longer than exiting.
- Suggested engine defaults: word enter 200-280 ms `easeOutQuint` (`easeOutBack` for pop
  themes); active-word hit 80-120 ms in, 200-300 ms out; line exit 150-200 ms accelerate or
  fade; word hold = its aligned duration, never shortened or stretched (the visual must not
  imply timing that is not in `words.json`, red line 1).

## 6. Fonts

Devanagari coverage verified from google/fonts metadata or the foundry README. All Google Fonts
entries are SIL OFL.

| Family | Devanagari | Mood | On this machine |
|---|---|---|---|
| Poppins (ITF) | yes, 9 weights, conjuncts | modern / clean default; most recommended lyric font | no (download) |
| Anek Devanagari (Ek Type) | yes, variable wght 100-800, wdth 75-125 | condensed hype, Punjabi / rap | no |
| Tiro Devanagari Hindi | yes, Regular + Italic, book serif | elegant, cinematic, ghazal | no |
| Eczar | yes, wght 400-800, high contrast | editorial, cinematic | no |
| Rozha One | yes, display serif | romantic-dramatic titles, hero word | no |
| Yatra One | yes, brush poster | Bollywood-poster hero word, title card | no |
| Kalam | yes, handwriting 300/400/700 | lofi, diary | no |
| Baloo 2 | yes, rounded heavy | party, friendly | no |
| Teko / Khand / Rajdhani | yes, condensed | rap, sports, "bold modern Hindi" | no |
| Hind / Mukta / Noto Sans Devanagari | yes, UI sans | safe body sans | no |
| Noto Nastaliq Urdu / Gulzar | Nastaliq (Urdu) | ghazal script | no |
| Mukta Mahee / Baloo Paaji 2 / Anek Gurmukhi | Gurmukhi | Punjabi hook lines | no |
| Latin only: Cormorant Garamond, Playfair Display, DM Serif Display, Fraunces, Instrument Serif | pair with Tiro Devanagari or Rozha One | romantic serif | no |
| Latin only: Great Vibes, Dancing Script, Sacramento | pair with Amita or Kalam | scripts, slow songs only ("harder to read quickly") | no |
| Latin only: Montserrat, Inter, DM Sans, Space Grotesk | pair with Hind / Anek | modern, lofi editorial, synth | Montserrat Regular + Bold (user fonts) |
| Latin only: Bebas Neue, Anton, Oswald | pair with Teko / Anek wdth 75 | bold hype; Anton "reads on busy backgrounds" | no |
| Latin only: Caveat, Permanent Marker | pair with Kalam | handwritten, grunge | no |
| Windows-bundled | Nirmala UI (all Indic), Mangal, Kokila, Aparajita, Utsaah | Devanagari fallback | yes |
| Windows-bundled Latin | Candara (current), Segoe UI Light-Black, Bahnschrift (condensed variable), Georgia, Constantia, Impact, Gabriola, Segoe Script | ready now | yes |

Rules: two fonts maximum, contrasted (sans + handwritten, bold + light, display + neutral).
Emoji: Segoe UI Emoji (COLR) renders offline in Pillow; a Noto Color Emoji swap only for a
different emoji style. Pillow font fallback already covers mixed runs; one-file Latin+Devanagari
families make the fallback a no-op.

## 7. Palettes by mood (text / accent or active / shadow-glow / backplate)

Hue 120 green is banned (chroma key, spec 01). Nearest safe "greens": teal `#1FB8A6`, lime-yellow
`#E8FF47`.

1. Black-screen sad: `#F2F2F2` / white glow 50% / shadow `#000000` 60% / backplate `#000000`
   40-60%; secondary grey `#9CA3AF`.
2. Romantic warm (current family): `#FFF3E0` / amber `#FFB74D` or rose `#F48FB1` / shadow
   `#3E1F0F` 60% / backplate `#1A0B08` 55%.
3. Lofi pastel: `#F5EFE6` / blush `#F7C6D0` or lavender `#C9B8FF` / soft glow 30% / backplate
   `#2B2A33` 50%.
4. Party neon: white / hot pink `#FF2E88`, cyan `#00E5FF` or yellow `#FFD60A` with same-hue glow
   40-60% / backplate `#0B0B14` 60%.
5. Bhajan / devotional: cream `#FFF8E7` / saffron `#FF9933` or marigold `#F4B400` / gold
   `#D4AF37` glow / backplate maroon `#7A1F1F` 60%.
6. Punjabi hype: white / mustard `#FFC107` or red `#E53935` / 4 px stroke `#000000`; backplate
   optional.
7. Cinematic / ghazal: ivory `#EDE6D6` / antique gold `#C9A66B` / shadow `#000000` 70% /
   backplate `#0F0F0F` 65%.
8. Rap / street: white / `#FF3B30` or `#FFEB3B` / heavy stroke `#000000` 5-6 px, no backplate.

Glow recipe for "white glow text": blurred copy 8-20 px behind the sharp text at 50-70%
(current: glow_radius 16, glow_boost 1.8).

## 8. Layout and legibility at 1080x1920

- Platform UI: Reels top ~108-220 px (username), bottom 300-400 px (caption, audio), left 60,
  right 100-120 px (action rail). Shorts safe rect about 900x1160 centred (x 90-990,
  y 380-1540). Conservative union for both: **x 60-960, y 380-1540**. Feed shows Reels cropped to
  4:5 (y 285-1635 visible), which the union satisfies.
- Text centre at 58-70% of height (current `anchor_y` 0.62 is inside the band). Keep lyrics in
  the middle 65% of the frame.
- Size: lyric lines 96-125 px, hero word larger; 20-28 characters per line, 1-2 lines; 44 px
  absolute minimum. Test on a phone at 50% brightness.
- Legibility stack: background box is the most reliable (70-80% black, ~21:1); 3-4 px black
  stroke on white (~12:1) plus light shadow is the standard social combo; scale stroke with size
  (about 4-6% of em). Shadow alone is not enough on bright frames.

## 9. Hinglish and Indian conventions

- Hinglish (roman) is "the default language of engagement" on Reels; Devanagari "signals
  authenticity". Premium hybrid: romanized body with one Devanagari hero word or title in a
  display face (Yatra One, Rozha One). Bhajan and shayari edits flip to majority Devanagari.
- Title / credit card "Song | Singer" (Bollywood adds the film) at the start or persistent at
  the top; the singer name is a discovery keyword.
- Emoji grammar, one per card: music note beside the title, heart or wilted rose on romantic vs
  sad lines, fire on Punjabi / rap drops, folded hands on bhajans.
- Sad status: black screen or desaturated footage, single-line reveals, long holds, "slowed +
  reverb" tag. Party: word-by-word pops on the beat. Punjabi: warm vintage grade, golden hour,
  bold type, Gurmukhi hook mixed with roman lyrics. Ghazal: ivory and gold, Nastaliq feel,
  generous line spacing, poem-like centring.

## 10. Technical routes

**A. PIL sprites (current), default.** Everything in section 4 fits. Themes 1-4 need only
`theme.py` values plus a few primitives in `render/frames.py` and `render/timeline.py`.

**B. ASS / libass through ffmpeg.** Verified on this machine **[local]**: the ffmpeg build has
libass, libfreetype, libharfbuzz; rendering onto a transparent canvas works:

```
ffmpeg -f lavfi -i "color=c=black@0.0:s=1080x1920:r=30:d=<dur>,format=rgba,subtitles=f=lyrics.ass:alpha=1,unpremultiply=inplace=1" -c:v prores_ks -profile:v 4444 -pix_fmt yuva444p10le out.mov
```

Output had 256 alpha levels (real anti-aliasing) and 94% fully transparent pixels. Gotcha: RGB
comes out premultiplied (edge pixels dark); `unpremultiply=inplace=1` restores straight alpha.
libass shaped Devanagari correctly (half forms, i-matra reordering) where Pillow did not. Tags:
`\k \kf \ko` (centiseconds; `\kf` = left-to-right sweep from `\2c` to `\1c`), `\t([t1,t2,][accel,]tags)`
animating `\fs \fscx \fscy \fsp \frz \bord \shad \blur \1c..\4c \alpha \clip`, `\fad`, `\fade`,
`\move` (constant speed), `\blur`, `\an`, `\pos`, fonts via `fontsdir`. Limits: no real easing
curves (only the `\t` accel exponent), no per-glyph stagger without one event per glyph. One
ffmpeg process, no Python frame loop: probably the fastest path for karaoke-family themes.
`words.json` stays the single source and the ASS file is a pure function of it, so both red lines
hold.

**C. uharfbuzz + freetype-py** (both have win_amd64 wheels, ~200 lines): shape to glyph ids and
offsets, rasterise per glyph, paste into PIL. Gives correct Devanagari clusters and per-glyph
masks (per-glyph stagger). Only if Devanagari lyrics arrive.

**D. Pillow shaping caveat.** Pillow wheels since 8.2 include raqm but need `fribidi.dll` on the
DLL path on Windows; this venv reports `raqm False`, so `layout_engine=RAQM`, `features` and
`direction` are silently ignored. Fix options: drop an MSYS2 / conda-forge `fribidi.dll` into
`venv\Scripts` (unverified), wait for Pillow PR #9926 (static raqm in wheels, open), or route B / C.

**E. Rejected:** skia-python (real paths, gradients, shaping via skparagraph, but a rewrite of
`layout.py` and `frames.py`); Remotion / Motion Canvas (headless Chrome, Node, heavy on 8 GB);
Manim (LaTeX / Cairo, wrong tool); moviepy 2 TextClip (thin Pillow wrapper, no gain);
pillow-simd (no Windows wheels); pilmoji (network fetch of Twemoji).

**F. Beat data.** Themes 5 and 6 need a beat or onset list that `words.json` does not carry.
Not researched here; candidates are `librosa.beat.beat_track` (pulls numba) or `aubio`. Treat
as its own step with its own spec.

## 11. Open-source references worth reading

- videokar (MIT): all look in one TOML, alignment cached, "restyling never costs another
  alignment run"; Pillow frames with supersampled AA to ProRes 4444. Same split as `theme.py`.
- protoke (MIT): `words.json` to ASS; stable reading pages of 1-5 lines; motion modes Still /
  Ambient (drift + edge glow) / Party Hard (beat colour shifts); portrait 1080x1920.
- aikaraoke: three word states, yellow current / white upcoming / grey sung.
- captions.js (MIT): 26 presets (Karaoke, Focus Box, Neon Pulse, Cinema, Old Money, ...), 10
  animations, one `renderFrame()` shared by preview and export.
- AI.Lyrics / LyricWave: cleanest preset taxonomy. TEXT (Fade, Smooth / Blur / Mask Reveal, Slide,
  Scale, Pop, Bounce, Typewriter, Letter / Word / Tracking Reveal), DYNAMIC (Beat Pulse, Impact
  Scale, Shake, Flash, Glitch, Elastic, Rotation Tilt, Wave, Floating Ambient), KARAOKE (Word
  Highlight, Progressive Liquid Fill, Active Word Scale Bounce, Active Word Neon Glow, Pill Badge).
- applemusic-like-lyrics (AGPL-3.0, ideas only): mask-image word reveal, additive glow, blur and
  scale of non-active lines, spring physics, syllable-level "melisma" emphasis on held notes.
- PupCaps (Apache-2.0): CSS-styled captions rendered to a MOV alpha overlay, then composited;
  proves the overlay-into-editor workflow.
- Caption Plug preset names as a vocabulary: Karaoke Fill, Underline Sweep, Wave Ride, Ghost
  Echo, Spotlight Focus, Blur Focus, Lyric Bar, Beast Pop, Neon Sign, Mask Rise, Letter Cascade,
  Heartbeat, Jelly Squash, Clean Fade.
- captacity (MIT): parameter list worth mirroring (font, size, colour, stroke width / colour,
  shadow strength / blur, highlight_current_word, word_highlight_color, line_count, padding).
- Karaoke-Music-Vid-Generator: an LLM picks phrase and line breaks (out of V1 scope, noted).

## 12. Proposed decisions for the owner (H-011)

1. Which themes first. Recommendation: Soft Romantic v2, then Karaoke Fill, then Minimal
   Lowercase. No new inputs, all three reuse the alignment. Beat-driven themes (Beat Pop, Neon)
   wait for beat data.
2. Theme model: keep the `theme.py` dataclass; add per-theme animation choices (entry, active
   word, line stack, legibility layer) as named presets. The blueprint's tag markup stays out of
   scope; the hand-marked emphasis word (H-009) maps to the theme's single emphasis move.
3. Devanagari: defer until a song needs it, then route B (libass) or C (harfbuzz).
4. A legibility layer option (soft scrim or stroke) in every theme, since the overlay must
   survive bright CapCut footage.

## Sources

Styles, motion, engagement
- https://arxiv.org/abs/2308.14922 (UIST 2023 lyric video design guidelines)
- https://dev.to/vimu_kale_4b5058f002ff8b1/how-apple-music-maps-audio-to-lyrics-the-engineering-behind-real-time-lyric-sync-4fin
- https://trydemotion.com/blog/text-animation-secrets
- https://trydemotion.com/blog/kinetic-typography-secrets
- https://www.svgator.com/blog/kinetic-typography-a-guide-to-text-in-motion/
- https://www.moonb.io/blog/kinetic-typography
- https://www.designrush.com/best-designs/video/trends/8-25-seconds-to-impress-typography-animation-examples-that-maximize-viewer-retention
- https://pixflow.net/blog/top-video-editing-trends-2025/
- https://www.epitrite.com/blog/best-fonts-for-lyric-videos
- https://premieregal.com/blog/2021/10/4/how-to-create-text-for-lyric-video
- https://www.premiumbeat.com/blog/create-lyric-videos-after-effects/
- https://ogtemplate.com/capcuttemplates/lyrics-capcut-templates/
- https://techcrunch.com/2019/06/06/instagram-lyrics/
- https://www.ascynd.io/en/blog/why-hormozi-captions-get-more-views (vendor)
- https://www.aividgenie.com/blog/caption-styles-that-boost-engagement (vendor)
- https://www.3playmedia.com/blog/captions-increase-viewership-for-facebook-video-ads/
- https://www.itnavideo.com/blog/caption-font-size-guide-reels
- https://www.opus.pro/blog/youtube-shorts-caption-subtitle-best-practices

Hinglish, fonts, palettes, safe zones
- https://www.capcut.com/explore/hindi-lyrics-template (451 to the fetcher; search snippet)
- https://www.pippit.ai/templates/hindi-sad-lofi-song-lyrics-templates
- https://www.pippit.ai/templates/hindi-song-black-screen-song-lyrics
- https://capcuttemplate.co.in/punjabi-songs-capcut-template/
- https://hindifontstyle.co.in/blog/best-hindi-fonts
- https://github.com/itfoundry/poppins
- https://github.com/google/fonts (METADATA.pb for tirodevanagarihindi, anekdevanagari, baloo2, yatraone, eczar, kalam)
- https://fonts.google.com/noto/specimen/Noto+Nastaliq+Urdu
- https://learn.microsoft.com/en-us/typography/font-list/nirmala-ui
- https://blitzcutai.com/blog/caption-background-vs-outline-vs-shadow
- https://recapo.ai/blog/best-caption-styles-for-shorts/
- https://kreatli.com/guides/instagram-reels-safe-zone
- https://postplanify.com/tools/youtube-shorts-safe-zone-checker
- https://www.jnanamrit.com/2025/08/08/the-growing-preference-for-roman-script-in-writing-hindi/

CapCut limits, commercial catalogues
- https://capcutguide.com/capcut-text-animation/
- https://capcutguide.com/capcut-word-by-word-captions/
- https://capcutguide.com/capcut-lyrics-templates/
- https://autoae.online/blog/how-to-do-text-animation-in-capcut-pc
- https://lyrc.studio/blog/how-to-make-a-lyric-video-on-capcut
- https://www.videocaptions.ai/blog/capcut-hindi-captions-not-working
- https://www.captionplug.com/presets
- https://invideo.io/make/lyric-video-maker/
- https://www.kapwing.com/templates/subtitles
- https://support.veed.io/en/articles/12000003-how-to-use-dynamic-subtitles

Implementation
- https://easings.net/ (formulas: github.com/ai/easings.net src/easings.yml)
- https://m3.material.io/styles/motion/easing-and-duration/tokens-specs
- https://m1.material.io/motion/duration-easing.html
- https://www.nngroup.com/articles/animation-duration/
- https://www.kvin.me/posts/effortless-ui-spring-animations
- https://pillow.readthedocs.io/en/stable/reference/ImageFilter.html
- https://pillow.readthedocs.io/en/stable/reference/ImageFont.html
- https://pillow.readthedocs.io/en/stable/installation/building-from-source.html (raqm / fribidi on Windows)
- https://github.com/python-pillow/Pillow/pull/9926
- https://ayosec.github.io/ffmpeg-filters-docs/8.0/Filters/Video/subtitles.html
- https://github.com/SubtitleEdit/subtitleedit/issues/9705 (transparent ASS export chain)
- https://aegisub.org/docs/latest/ass_tags/
- https://pypi.org/project/uharfbuzz/ , https://pypi.org/project/freetype-py/
- https://github.com/kyamagu/skia-python

Open source
- https://github.com/MatteoAdamo82/videokar
- https://github.com/snepssen/protoke
- https://github.com/nomadkaraoke/karaoke-gen
- https://github.com/krharilal-tech/aikaraoke
- https://github.com/maskin25/captions.js
- https://github.com/Nikhil0-1/AI.Lyrics
- https://github.com/amll-dev/applemusic-like-lyrics
- https://github.com/hosuaby/PupCaps
- https://github.com/unconv/captacity
- https://github.com/vshukla7/remotion-captions-themes
- https://github.com/danielrosehill/Karaoke-Music-Vid-Generator
