# Plan: Alpha Overlay Proof in CapCut
**Spec:** `docs/specs/01_alpha_overlay_proof.md` (v1.0.0, approved 2026-09-26)
**Branch:** `feature/alpha-overlay-proof`

## 1. Files

| Action | File | Reason |
|---|---|---|
| CREATE | `scripts/alpha_proof.py` | Generator + encoder + checker + results note, one command (spec AC1). |
| CREATE | `requirements.txt` | Pin `pillow==12.3.0`, the one Python dependency. |
| MODIFY | `.gitignore` | Add `out/`; rendered clips never committed (spec Hard Rule, AC9). |
| MODIFY | `.claude/devsystem.json` | Add the proof run as `gate.commands` (D-004: first check → gate gets its command). |
| MODIFY | `docs/decision.md` | D-005 (candidate encodings, HEVC-alpha excluded), D-006 (gate command). Owner's CapCut outcome later (AC8). |
| MODIFY | `docs/development_plan.md`, `docs/pending_work.md` | Status and next action. |
| — | `src/lyric_engine/*` | **Untouched.** Step 03 ports the winning encoder arguments into `render.py`; the proof does not pre-empt that design. |

## 2. Architecture Decisions

1. **Standalone script in `scripts/`, not in `src/lyric_engine/`.** Spec: "do not pick the final
   render library for step 03". Rejected: implementing `render.py` now, because it would lock the
   render design before step 03's spec exists.
2. **Pillow draws the frames.** It needs anti-aliased text, a blur for the glow, and per-pixel
   reads for the checker. Rejected: ffmpeg `drawtext` (a glow needs a fragile split/blur/merge
   graph, and there is no easy way to know which pixels to sample); MoviePy (a heavier dependency,
   and choosing it is step 03's call).
3. **One PNG sequence on disk is the single frame source** (spec §4). Every variant encodes from
   the same 150 files. Rejected: piping raw frames to ffmpeg once per variant (renders 4×, leaves
   no source to inspect or check against).
4. **Alpha candidates, three encoding families** (spec §4 "more than one encoding family"):
   - `A_prores4444.mov`: ProRes 4444, `yuva444p10le`, 16-bit alpha, vendor `apl0`. The editor
     industry default for alpha.
   - `B_png.mov`: PNG-in-MOV, `rgba`. Lossless, straight alpha, RGB (no colour matrix).
   - `C_qtrle.mov`: QuickTime Animation (RLE), `argb`. Lossless, oldest and most widely read
     alpha codec.

   Rejected: **HEVC with alpha.** Probed on this machine: `Loaded libx265 does not support alpha
   layer encoding`. Also rejected: VP9 `.webm` (spec Will NOT Do).
5. **Green mp4 = the same PNGs overlaid on `color=0x00FF00` in ffmpeg, H.264 High, `yuv420p`.**
   Phones decode it natively. Rejected: `yuv444p` (keys a little cleaner, but many phone decoders
   cannot play High 4:4:4). Known cost: 4:2:0 softens colour at edges. The results note says so,
   so the owner does not read it as a CapCut fault.
6. **YUV outputs tagged BT.709** (`-colorspace/-color_primaries/-color_trc bt709`,
   `-color_range tv`, scale `out_color_matrix=bt709`). Untagged HD video is guessed at by editors,
   and colours shift. PNG/qtrle are RGB and need no tag.
7. **Glow = a solid glow-colour layer whose alpha is the blurred text mask.** Blurring an RGBA
   image mixes the black of transparent pixels into the halo and creates a dark fringe. This way,
   any fringe seen in CapCut comes from CapCut or the encoding, not from the generator (spec §1).
8. **The checker decodes each output and compares it to the source PNG at sample points picked
   from the source.** Rejected: hard-coded pixel coordinates, because font rasterisation can move
   glyph edges.
9. **Non-zero exit when any variant is missing, fails to encode, or fails a check.** That makes
   the script usable as the gate, and a missing variant can never pass silently (AC1).

## 3. Data Structures

```
Variant (frozen dataclass)
  key: str            e.g. "A_prores4444"; results + filename stem          → AC1 naming
  filename: str       e.g. "A_prores4444.mov"                               → .mov/.mp4 only (Will NOT Do)
  encoder: str        ffmpeg encoder name, checked before use               → edge: missing encoder
  args: tuple[str,...] codec/pix_fmt/colour args after the input            → decision 4-6
  alpha: bool         True → alpha checks (AC3); False → green checks (AC4)
  green: bool         True → built with the green overlay filter graph

Result (dataclass)
  variant: Variant
  status: str         "ok" | "encoder_missing" | "encode_failed"            → AC1 "never silently skipped"
  path: Path | None
  size_bytes: int     0 unless produced                                     → AC5
  error: str          last ffmpeg stderr lines when encode_failed
  failures: list[str] check failures, empty = pass                          → AC2-4

LAYOUT: dict[str, Box]   sprite name → (x, y, w, h) placement, filled by build_sprites()
                         used by render_frame() and pick_sample_points()    → one geometry source
```

Constants (top of file): `W=1080, H=1920, FPS=30, N_FRAMES=150`, `SAMPLE_FRAME=100`,
`OUT_DIR = repo/out/01_alpha_proof`, `FRAMES_DIR = OUT_DIR/frames`,
`FONT_CANDIDATES = [C:/Windows/Fonts/segoeuib.ttf, C:/Windows/Fonts/arialbd.ttf]`,
`KEY_GREEN = (0,255,0)`, `LARGE_BYTES_3MIN = 2 GiB`, tolerances (§5).

Palette (placeholder look; hues far from 120°, per the spec Hard Rule):

| Element | Text (original, from `songs/example`) | Colour | Behaviour |
|---|---|---|---|
| static line | "tum paas ho to" | white 255,255,255 | visible every frame, y≈700 |
| glow word | "roshan" | white text, pink glow 255,120,180, radius 18 | fixed, y≈950 |
| fade word | "dil" | peach 255,190,140 | alpha 0→255 over frames 0–74, then holds, y≈1200 |
| moving word | "naya" | lavender 200,170,255 | x moves left→right, scale 0.6→1.2 over 150 frames, y≈1450 |

## 4. Function Specifications

| Function | Signature | Purpose / behaviour | Raises / calls |
|---|---|---|---|
| `main` | `(argv: list[str] \| None) -> int` | Parses `--check-only`; runs the §5 flow; returns the exit code. | calls everything below |
| `require_tools` | `() -> None` | `shutil.which` for ffmpeg + ffprobe. | `SystemExit(2, "ffmpeg/ffprobe not found on PATH")` |
| `load_font` | `(size: int) -> ImageFont.FreeTypeFont` | First existing `FONT_CANDIDATES`. **Never** `load_default()`, because a bitmap font has no anti-aliasing and would void the edge test. | `SystemExit(2, "no font found; tried: …")` |
| `text_sprite` | `(text, font, fill) -> Image` | Tight RGBA image of anti-aliased text on transparent. | — |
| `glow_sprite` | `(text, font, fill, glow, radius) -> Image` | Mask → GaussianBlur → solid `glow` layer with the blurred alpha → text composited on top. Padding = 3×radius. | `text_sprite` |
| `build_sprites` | `() -> dict[str, Image]` | Builds 4 sprites once (the glow blur is not repeated per frame); fills `LAYOUT`. | `load_font`, sprite fns |
| `render_frame` | `(i: int, sprites) -> Image` | Transparent 1080×1920; pastes static and glow; fade = sprite with alpha scaled by `min(1, i/74)`; moving = sprite resized by scale(i), placed at x(i). | `Image.alpha_composite` |
| `write_frames` | `() -> None` | Clears `OUT_DIR` (only it), writes `frames/f_000.png … f_149.png`. | `render_frame` |
| `encoder_available` | `(name: str) -> bool` | `ffmpeg -hide_banner -h encoder=<name>`; False if the output contains "is not recognized" / "Unknown encoder". | `subprocess.run` |
| `encode` | `(v: Variant) -> Result` | Missing encoder → `encoder_missing`. Otherwise runs ffmpeg: input `-framerate 30 -i frames/f_%03d.png`; `-frames:v 150 -an -y`; `v.args`; the green variant adds the overlay `-filter_complex`. Non-zero exit → `encode_failed` + stderr tail. | `encoder_available`, `subprocess.run` |
| `probe` | `(path) -> dict` | `ffprobe -count_frames -show_streams -of json` → width, height, r_frame_rate, nb_read_frames, pix_fmt, has_audio. | `subprocess.run` |
| `decoded_frame` | `(path, index) -> Image` | `ffmpeg -vf select=eq(n\,index) -frames:v 1 -pix_fmt rgba` to a temp PNG, loaded as RGBA. | `subprocess.run` |
| `pick_sample_points` | `(src: Image) -> dict[str,(x,y)]` | `corner`=(4,4); `solid`= first pixel (row-major) in the static-line box with alpha 255; `glow`= first pixel in the glow box with 60 ≤ alpha ≤ 190. | `RuntimeError("sample point not found: <name>")`, a generator bug |
| `check_variant` | `(r: Result, src, points) -> None` | Fills `r.failures` per §5 tolerances. | `probe`, `decoded_frame` |
| `check_palette` | `() -> list[str]` | Every palette colour: HSV saturation < 0.25 **or** hue outside 80°–160°. | `colorsys` |
| `write_results` | `(results, palette_failures) -> None` | Writes `OUT_DIR/results.md`: a table of variant, status, MB, MB for 3 min (×36, `LARGE` flag above the threshold), check result; the owner checklist from spec §4; a note that glow/fade on the green variant is expected to key imperfectly. Prints the same table. | — |

## 5. Logic Flow

**`main`**
1. `require_tools()`.
2. If not `--check-only`: `write_frames()`. If `--check-only` and `FRAMES_DIR` is missing → exit 2
   with "run without --check-only first".
3. For each `VARIANTS` entry: if not `--check-only` → `encode(v)`; else build the `Result` from the
   existing file (a missing file → `encode_failed`, "file missing").
4. `src = Image.open(frames/f_100.png)`; `points = pick_sample_points(src)`.
5. For each `Result` with status `ok`: `check_variant`.
6. `palette_failures = check_palette()`.
7. `write_results(...)`.
8. Return 0 if every result is `ok` with no failures and `palette_failures` is empty; else 1.

**`check_variant` tolerances**
1. Probe: width 1080, height 1920, `r_frame_rate == "30/1"`, `nb_read_frames == 150`, no audio
   stream. Each mismatch is a failure line (`"frames: expected 150, got 149"`).
2. If `alpha`: `pix_fmt` starts with `yuva` or is in {`rgba`,`argb`,`bgra`,`abgr`,`rgba64le`,`rgba64be`},
   else `"no alpha channel (pix_fmt=…)"`. Decoded frame 100: corner α ≤ 2; solid α ≥ 253;
   glow 0 < α < 255 **and** |α − source α| ≤ 12.
3. If `green`: decoded frame 100 corner RGB has R ≤ 24, G ≥ 230, B ≤ 24.

**`encode` (green variant filter graph)**
`color=c=0x00FF00:s=1080x1920:r=30[bg];[bg][0:v]overlay=shortest=1:format=auto,format=yuv420p`,
then libx264 `-preset slow -crf 16 -profile:v high -movflags +faststart` + BT.709 tags.

## 6. Edge Case Implementation Map

| Spec edge case | Mechanism | Location |
|---|---|---|
| No alpha variant works in CapCut desktop | Process, not code: the owner's result → `human_decision.md` entry; step 02 does not start | results.md checklist; AC8 |
| Glow/fade fringes | The generator cannot cause them (decision 7); three alpha storage paths to compare | `glow_sprite`; `VARIANTS` |
| Green keys solid text but not glow/fade | Expected; stated in results.md so it is judged, not mistaken for a bug | `write_results` |
| Variant huge for 3 min | Size ×36 column, `LARGE` flag above 2 GiB | `write_results` |
| CapCut retimes the clip | Constant 30/1 frame rate checked; owner records any stutter or duration change | `check_variant` step 1; checklist |
| ffmpeg / encoder missing | `require_tools` exit 2; `encoder_missing` status + non-zero exit | `require_tools`, `encode` |
| Phone recompression | Checklist tells the owner to transfer as a file | `write_results` |
| Font missing | Exit 2 naming the tried paths; never a bitmap fallback | `load_font` |
| Stale outputs from an earlier run | `OUT_DIR` is cleared at the start of a full run | `write_frames` |

## 7. File Layout: `scripts/alpha_proof.py`

1. Module docstring: purpose, usage (`venv/Scripts/python scripts/alpha_proof.py [--check-only]`),
   spec link.
2. Imports (stdlib, then Pillow).
3. Constants: geometry/timing, paths, fonts, palette, green, sample frame, tolerances, size flag.
4. `Variant`, `Result` dataclasses; the `VARIANTS` tuple.
5. Frame generation: `load_font`, `text_sprite`, `glow_sprite`, `build_sprites`, `render_frame`,
   `write_frames`.
6. ffmpeg helpers: `require_tools`, `encoder_available`, `encode`.
7. Checks: `probe`, `decoded_frame`, `pick_sample_points`, `check_variant`, `check_palette`.
8. Results: `write_results`.
9. `main`, `if __name__ == "__main__": sys.exit(main())`.

## 8. Dependencies

- stdlib: `argparse, colorsys, dataclasses, json, pathlib, shutil, subprocess, sys, tempfile`.
- Pillow 12.3.0 (`Image, ImageDraw, ImageFont, ImageFilter`), installed into `venv/`.
- ffmpeg/ffprobe 8.0.1 on PATH, with `prores_ks`, `png`, `qtrle`, `libx264` (all verified present).
- Fonts: `C:/Windows/Fonts/segoeuib.ttf` (present), `arialbd.ttf` (present).
- Module deps: none. The script imports nothing from `src/`, and `src/` imports nothing from `scripts/`.
- Conflicts with existing code: none (stubs only). `.gitignore` gains one line.

## 9. Hard Boundaries

- [ ] Never write or delete outside `out/01_alpha_proof/`.
- [ ] No network calls.
- [ ] Never commit anything under `out/`.
- [ ] Never fall back to `ImageFont.load_default()`.
- [ ] Never skip a variant silently; every variant appears in the output with a status.
- [ ] No text other than the original placeholder words above.
- [ ] No palette colour within the green keying range.
- [ ] Do not touch `src/lyric_engine/`.

## 10. Acceptance Criteria (runnable)

| # | Command | Pass |
|---|---|---|
| 1 | `venv/Scripts/python scripts/alpha_proof.py` | exit 0; printed table has 4 rows, `A_prores4444`, `B_png`, `C_qtrle`, `G_green`, each `ok` |
| 2 | `ffprobe -v error -count_frames -select_streams v:0 -show_entries stream=width,height,r_frame_rate,nb_read_frames -of csv=p=0 out/01_alpha_proof/<file>` for each file; `ffprobe -v error -select_streams a -show_entries stream=index -of csv=p=0 <file>` | `1080,1920,30/1,150`; audio query prints nothing |
| 3 | script output, alpha rows | `checks: pass` for A, B, C (corner α 0, solid α 255, glow partial, within ±12 of source) |
| 4 | script output, green row + palette line | `checks: pass` for G; `palette: pass` |
| 5 | `cat out/01_alpha_proof/results.md` | one row per variant with MB and a 3-minute MB column |
| 6 | owner: CapCut desktop, protocol in results.md | ≥1 alpha variant clean over dark and bright backgrounds, **or** "none" recorded per spec §5 |
| 7 | owner: CapCut mobile, green mp4 + Chroma Key | solid-text verdict and glow/fade verdict reported |
| 8 | `grep -n "CapCut" docs/decision.md docs/human_decision.md` | an entry recording the outcome of 6 and 7 |
| 9 | `git ls-files out` / `git check-ignore -q out/01_alpha_proof/A_prores4444.mov && echo ignored` | empty / `ignored` |
