"""Step 01 alpha overlay proof: can CapCut import our transparent / green-screen overlays?

Renders one 5-second 1080x1920 test clip (static line, glowing word, fading word, moving word)
as a PNG sequence, encodes it into several alpha .mov variants plus a green-screen mp4, checks
every output against the source frames, and writes out/01_alpha_proof/results.md with the owner's
CapCut test checklist.

Usage:
    venv/Scripts/python scripts/alpha_proof.py              # render + encode + check
    venv/Scripts/python scripts/alpha_proof.py --check-only # re-check existing outputs

Spec: docs/specs/01_alpha_overlay_proof.md   Plan: docs/specs/01_alpha_overlay_proof_impl.md
Exit code: 0 all good, 1 a variant is missing or failed a check, 2 environment problem.
"""
from __future__ import annotations

import argparse
import colorsys
import json
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass, field
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

# --- Geometry / timing -----------------------------------------------------------------------
W, H, FPS, N_FRAMES = 1080, 1920, 30, 150
FADE_END_FRAME = 74          # fade word reaches full opacity here (2.5 s)
SAMPLE_FRAME = 100           # every element present, fade complete

# --- Paths -----------------------------------------------------------------------------------
REPO = Path(__file__).resolve().parent.parent
OUT_DIR = REPO / "out" / "01_alpha_proof"
FRAMES_DIR = OUT_DIR / "frames"
FRAME_PATTERN = "f_%03d.png"
FONT_CANDIDATES = (Path("C:/Windows/Fonts/segoeuib.ttf"), Path("C:/Windows/Fonts/arialbd.ttf"))

# --- Look (placeholder, not the Soft Romantic design). Hues stay far from the key green. -------
WHITE = (255, 255, 255)
PINK_GLOW = (255, 120, 180)
PEACH = (255, 190, 140)
LAVENDER = (200, 170, 255)
PALETTE = {"white": WHITE, "pink_glow": PINK_GLOW, "peach": PEACH, "lavender": LAVENDER}
GLOW_RADIUS = 18
KEY_GREEN_HEX = "0x00FF00"

# --- Check tolerances ------------------------------------------------------------------------
CORNER = (4, 4)
ALPHA_EMPTY_MAX = 2
ALPHA_SOLID_MIN = 253
GLOW_SRC_RANGE = (60, 190)   # source alpha range a glow sample point is picked from
GLOW_ALPHA_TOL = 12
GREEN_TOL = 24               # R,B <= this and G >= 255 - this counts as key green
KEY_HUE_BAND = (80.0, 160.0)  # degrees; saturated colours in this band would key out
KEY_SAT_MIN = 0.25
LARGE_BYTES_3MIN = 2 * 1024**3
SCALE_3MIN = 180 / (N_FRAMES / FPS)

ALPHA_PIX_FMTS = {"rgba", "argb", "bgra", "abgr", "rgba64le", "rgba64be"}
BT709_TAGS = ("-colorspace", "bt709", "-color_primaries", "bt709", "-color_trc", "bt709",
              "-color_range", "tv")
TO_BT709 = "scale=out_color_matrix=bt709:out_range=tv"


@dataclass(frozen=True)
class Variant:
    key: str
    filename: str
    encoder: str
    vf: str              # filter chain after the frame input ("" = none)
    args: tuple[str, ...]
    alpha: bool          # True -> alpha checks; False -> green-screen checks
    green: bool = False  # True -> composited over key green before vf


@dataclass
class Result:
    variant: Variant
    status: str = "ok"   # ok | encoder_missing | encode_failed
    path: Path | None = None
    size_bytes: int = 0
    error: str = ""
    failures: list[str] = field(default_factory=list)


VARIANTS = (
    Variant("A_prores4444", "A_prores4444.mov", "prores_ks", f"{TO_BT709},format=yuva444p10le",
            ("-c:v", "prores_ks", "-profile:v", "4444", "-alpha_bits", "16", "-vendor", "apl0",
             *BT709_TAGS), alpha=True),
    Variant("B_png", "B_png.mov", "png", "", ("-c:v", "png", "-pix_fmt", "rgba"), alpha=True),
    Variant("C_qtrle", "C_qtrle.mov", "qtrle", "", ("-c:v", "qtrle", "-pix_fmt", "argb"),
            alpha=True),
    Variant("G_green", "G_green.mp4", "libx264", f"{TO_BT709},format=yuv420p",
            ("-c:v", "libx264", "-preset", "slow", "-crf", "16", "-profile:v", "high",
             "-movflags", "+faststart", *BT709_TAGS), alpha=False, green=True),
)


# --- Frame generation --------------------------------------------------------------------------
def load_font(size: int) -> ImageFont.FreeTypeFont:
    # Never ImageFont.load_default(): a bitmap font has no anti-aliased edges to test.
    for path in FONT_CANDIDATES:
        if path.exists():
            return ImageFont.truetype(str(path), size)
    raise SystemExit(f"no font found; tried: {', '.join(map(str, FONT_CANDIDATES))}")


def _text_mask(text: str, font: ImageFont.FreeTypeFont, pad: int) -> Image.Image:
    left, top, right, bottom = font.getbbox(text)
    mask = Image.new("L", (right - left + 2 * pad, bottom - top + 2 * pad), 0)
    ImageDraw.Draw(mask).text((pad - left, pad - top), text, font=font, fill=255)
    return mask


def _solid(colour: tuple[int, int, int], alpha: Image.Image) -> Image.Image:
    # Solid colour + separate alpha = straight alpha with no dark edge pixels. Drawing text
    # straight onto a transparent RGBA canvas would blend edge RGB toward black.
    layer = Image.new("RGBA", alpha.size, (*colour, 255))
    layer.putalpha(alpha)
    return layer


def text_sprite(text: str, font: ImageFont.FreeTypeFont, fill: tuple[int, int, int]) -> Image.Image:
    return _solid(fill, _text_mask(text, font, pad=4))


def glow_sprite(text: str, font: ImageFont.FreeTypeFont, fill: tuple[int, int, int],
                glow: tuple[int, int, int], radius: int) -> Image.Image:
    mask = _text_mask(text, font, pad=3 * radius)
    halo = mask.filter(ImageFilter.GaussianBlur(radius)).point(lambda a: min(255, a * 2))
    return Image.alpha_composite(_solid(glow, halo), _solid(fill, mask))


def _centred(sprite: Image.Image, cy: int) -> tuple[int, int, int, int]:
    w, h = sprite.size
    return ((W - w) // 2, cy - h // 2, w, h)


def build_sprites() -> tuple[dict[str, Image.Image], dict[str, tuple[int, int, int, int]]]:
    sprites = {
        "static": text_sprite("tum paas ho to", load_font(110), WHITE),
        "glow": glow_sprite("roshan", load_font(150), WHITE, PINK_GLOW, GLOW_RADIUS),
        "fade": text_sprite("dil", load_font(150), PEACH),
        "moving": text_sprite("naya", load_font(140), LAVENDER),
    }
    layout = {
        "static": _centred(sprites["static"], 700),
        "glow": _centred(sprites["glow"], 950),
        "fade": _centred(sprites["fade"], 1200),
    }
    return sprites, layout


def render_frame(i: int, sprites: dict[str, Image.Image],
                 layout: dict[str, tuple[int, int, int, int]]) -> Image.Image:
    frame = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    for name in ("static", "glow"):
        frame.alpha_composite(sprites[name], dest=layout[name][:2])

    opacity = min(1.0, i / FADE_END_FRAME)
    if opacity > 0:
        fade = sprites["fade"].copy()
        fade.putalpha(fade.getchannel("A").point(lambda a: round(a * opacity)))
        frame.alpha_composite(fade, dest=layout["fade"][:2])

    t = i / (N_FRAMES - 1)
    base = sprites["moving"]
    scale = 0.6 + 0.6 * t
    moving = base.resize((round(base.width * scale), round(base.height * scale)), Image.LANCZOS)
    x = round(60 + (W - 120 - moving.width) * t)
    frame.alpha_composite(moving, dest=(x, 1450 - moving.height // 2))
    return frame


def write_frames(sprites, layout) -> None:
    if OUT_DIR.exists():
        shutil.rmtree(OUT_DIR)  # only ever out/01_alpha_proof: stale outputs must not be re-checked
    FRAMES_DIR.mkdir(parents=True)
    for i in range(N_FRAMES):
        render_frame(i, sprites, layout).save(FRAMES_DIR / (FRAME_PATTERN % i), compress_level=1)


# --- ffmpeg ------------------------------------------------------------------------------------
def _run(cmd: list[str]) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")


def require_tools() -> None:
    missing = [tool for tool in ("ffmpeg", "ffprobe") if shutil.which(tool) is None]
    if missing:
        raise SystemExit(f"{'/'.join(missing)} not found on PATH")


def encoder_available(name: str) -> bool:
    out = _run(["ffmpeg", "-hide_banner", "-h", f"encoder={name}"])
    return f"Encoder {name} [" in out.stdout


def encode(v: Variant) -> Result:
    result = Result(v, path=OUT_DIR / v.filename)
    if not encoder_available(v.encoder):
        result.status, result.error = "encoder_missing", f"ffmpeg has no '{v.encoder}' encoder"
        return result

    cmd = ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
           "-framerate", str(FPS), "-i", str(FRAMES_DIR / FRAME_PATTERN)]
    if v.green:
        cmd += ["-filter_complex",
                f"color=c={KEY_GREEN_HEX}:s={W}x{H}:r={FPS}[bg];"
                f"[bg][0:v]overlay=shortest=1:format=rgb,{v.vf}"]
    elif v.vf:
        cmd += ["-vf", v.vf]
    cmd += [*v.args, "-frames:v", str(N_FRAMES), "-an", str(result.path)]

    proc = _run(cmd)
    if proc.returncode != 0:
        result.status = "encode_failed"
        result.error = " | ".join(proc.stderr.strip().splitlines()[-3:])
    else:
        result.size_bytes = result.path.stat().st_size
    return result


# --- Checks ------------------------------------------------------------------------------------
def probe(path: Path) -> dict:
    proc = _run(["ffprobe", "-v", "error", "-count_frames", "-show_streams", "-of", "json",
                 str(path)])
    streams = json.loads(proc.stdout or "{}").get("streams", [])
    video = next((s for s in streams if s.get("codec_type") == "video"), {})
    return {
        "width": video.get("width"),
        "height": video.get("height"),
        "r_frame_rate": video.get("r_frame_rate"),
        "nb_read_frames": int(video.get("nb_read_frames", -1)),
        "pix_fmt": video.get("pix_fmt", ""),
        "has_audio": any(s.get("codec_type") == "audio" for s in streams),
    }


def decoded_frame(path: Path, index: int) -> Image.Image:
    with tempfile.TemporaryDirectory() as tmp:
        png = Path(tmp) / "frame.png"
        proc = _run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", str(path),
                     "-vf", f"select=eq(n\\,{index})", "-fps_mode", "passthrough",
                     "-frames:v", "1", "-pix_fmt", "rgba", str(png)])
        if proc.returncode != 0 or not png.exists():
            raise RuntimeError(f"could not decode frame {index} of {path.name}: {proc.stderr.strip()}")
        with Image.open(png) as img:
            return img.convert("RGBA")


def _first_pixel(alpha: Image.Image, box: tuple[int, int, int, int], lo: int, hi: int) -> tuple[int, int]:
    x0, y0, w, h = box
    for idx, a in enumerate(alpha.crop((x0, y0, x0 + w, y0 + h)).get_flattened_data()):
        if lo <= a <= hi:
            return (x0 + idx % w, y0 + idx // w)
    raise RuntimeError(f"no pixel with alpha {lo}..{hi} in box {box}")


def pick_sample_points(src: Image.Image, layout) -> dict[str, tuple[int, int]]:
    alpha = src.getchannel("A")
    return {
        "corner": CORNER,
        "solid": _first_pixel(alpha, layout["static"], 255, 255),
        "glow": _first_pixel(alpha, layout["glow"], *GLOW_SRC_RANGE),
    }


def check_variant(r: Result, src: Image.Image, points: dict[str, tuple[int, int]]) -> None:
    info = probe(r.path)
    expected = {"width": W, "height": H, "r_frame_rate": f"{FPS}/1", "nb_read_frames": N_FRAMES}
    for key, want in expected.items():
        if info[key] != want:
            r.failures.append(f"{key}: expected {want}, got {info[key]}")
    if info["has_audio"]:
        r.failures.append("has an audio stream")

    frame = decoded_frame(r.path, SAMPLE_FRAME)
    if r.variant.alpha:
        pix_fmt = info["pix_fmt"]
        if not (pix_fmt.startswith("yuva") or pix_fmt in ALPHA_PIX_FMTS):
            r.failures.append(f"no alpha channel (pix_fmt={pix_fmt})")
        corner_a = frame.getpixel(points["corner"])[3]
        solid_a = frame.getpixel(points["solid"])[3]
        glow_a = frame.getpixel(points["glow"])[3]
        glow_src = src.getpixel(points["glow"])[3]
        if corner_a > ALPHA_EMPTY_MAX:
            r.failures.append(f"empty corner alpha {corner_a} (want <= {ALPHA_EMPTY_MAX})")
        if solid_a < ALPHA_SOLID_MIN:
            r.failures.append(f"solid text alpha {solid_a} (want >= {ALPHA_SOLID_MIN})")
        if not 0 < glow_a < 255 or abs(glow_a - glow_src) > GLOW_ALPHA_TOL:
            r.failures.append(f"glow alpha {glow_a} (source {glow_src}, tol {GLOW_ALPHA_TOL})")
    else:
        red, green, blue, _ = frame.getpixel(points["corner"])
        if red > GREEN_TOL or blue > GREEN_TOL or green < 255 - GREEN_TOL:
            r.failures.append(f"corner not key green: {(red, green, blue)}")


def check_palette() -> list[str]:
    failures = []
    for name, (r, g, b) in PALETTE.items():
        hue, sat, _ = colorsys.rgb_to_hsv(r / 255, g / 255, b / 255)
        if sat >= KEY_SAT_MIN and KEY_HUE_BAND[0] <= hue * 360 <= KEY_HUE_BAND[1]:
            failures.append(f"{name} {(r, g, b)} is inside the key-green hue band")
    return failures


# --- Results -----------------------------------------------------------------------------------
OWNER_CHECKLIST = """\
## Owner test (spec section 4)

**CapCut desktop** - import each `.mov` (A, B, C) over a background clip. Check it once over a
dark background and once over a bright one.

**CapCut mobile** - move `G_green.mp4` to the phone *as a file* (Drive / USB / "send as
document"), never as a WhatsApp photo/video, which re-compresses it. Apply Chroma Key, and check
over dark and bright backgrounds. Optional: also try the best `.mov` on mobile.

| Variant | Where | Imports? | Background shows through? | Black box? | Fringe on glow / fade? | Notes |
|---|---|---|---|---|---|---|
| A_prores4444 | desktop | | | | | |
| B_png | desktop | | | | | |
| C_qtrle | desktop | | | | | |
| G_green | mobile (OS: ) | | | | | |

Expected on G_green: solid text should key out cleanly. The glow and the fading word are
partially transparent, which a chroma key cannot represent, so some green tint or hard edge
around them is expected. Judge whether it is acceptable; it is not a CapCut bug. Colour at edges
is also softened by 4:2:0 encoding, which phones need.
"""


def write_results(results: list[Result], palette_failures: list[str]) -> None:
    rows = []
    for r in results:
        mb = r.size_bytes / 1e6
        mb_3min = mb * SCALE_3MIN
        large = " LARGE" if r.size_bytes * SCALE_3MIN > LARGE_BYTES_3MIN else ""
        checks = ("pass" if not r.failures else "FAIL: " + "; ".join(r.failures)) \
            if r.status == "ok" else r.error
        rows.append(f"| {r.variant.key} | {r.status} | {mb:.1f} | {mb_3min:.0f}{large} | {checks} |")
    palette = "pass" if not palette_failures else "FAIL: " + "; ".join(palette_failures)

    table = "\n".join([
        "| Variant | Status | MB (5 s) | MB (3 min, est.) | Checks |",
        "|---|---|---|---|---|",
        *rows,
    ])
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / "results.md").write_text(
        f"# Alpha proof results\n\n{table}\n\npalette: {palette}\n\n{OWNER_CHECKLIST}",
        encoding="utf-8")
    print(table)
    print(f"palette: {palette}")
    print(f"results: {OUT_DIR / 'results.md'}")


# --- Entry point -------------------------------------------------------------------------------
def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--check-only", action="store_true", help="re-check existing outputs")
    args = parser.parse_args(argv)

    try:
        require_tools()
        sprites, layout = build_sprites()
    except SystemExit as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    if args.check_only:
        if not FRAMES_DIR.exists():
            print("error: no frames; run without --check-only first", file=sys.stderr)
            return 2
        results = []
        for v in VARIANTS:
            path = OUT_DIR / v.filename
            r = Result(v, path=path)
            if path.exists():
                r.size_bytes = path.stat().st_size
            else:
                r.status, r.error = "encode_failed", "file missing"
            results.append(r)
    else:
        write_frames(sprites, layout)
        results = [encode(v) for v in VARIANTS]

    with Image.open(FRAMES_DIR / (FRAME_PATTERN % SAMPLE_FRAME)) as img:
        src = img.convert("RGBA")
    points = pick_sample_points(src, layout)
    for r in results:
        if r.status == "ok":
            check_variant(r, src, points)

    palette_failures = check_palette()
    write_results(results, palette_failures)
    all_ok = all(r.status == "ok" and not r.failures for r in results) and not palette_failures
    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())
