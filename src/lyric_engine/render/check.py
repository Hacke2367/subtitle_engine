"""Output check (ffprobe + the theme's frame checks on the overlay) and render/report.md."""
from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from PIL import Image, ImageStat

from .. import layout
from ..theme import Theme
from . import focus
from .encode import _drain, _tail_text
from .timeline import LinePlan, _ceil_frame, _timed

if TYPE_CHECKING:
    from . import RenderResult

REPORT = "report.md"
ALPHA_PIX_FMTS = {"rgba", "argb", "bgra", "abgr", "rgba64le", "rgba64be"}
SYNC_ON_MIN, SYNC_DROP_MIN = 200, 100   # mean word alpha when on / required drop just before it
FILL_BEFORE_MAX, FILL_AFTER_MIN = 0.05, 0.95   # karaoke: filled share before start / at end
SAFE_ALPHA_MIN = 16                            # alpha that counts as drawn for the safe zone
_SAFE_LUT = [255 if v >= SAFE_ALPHA_MIN else 0 for v in range(256)]


# --- Output check ----------------------------------------------------------------------------
def _probe(path: Path, *, count: bool = False) -> dict:
    cmd = ["ffprobe", "-v", "error", *(["-count_frames"] if count else []), "-show_streams",
           "-of", "json", str(path)]
    proc = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    streams = json.loads(proc.stdout or "{}").get("streams", []) if proc.returncode == 0 else []
    video = next((s for s in streams if s.get("codec_type") == "video"), None)
    if video is None:
        return {"error": " | ".join(proc.stderr.strip().splitlines()[-3:]) or "no video stream"}
    return {"size": (video.get("width"), video.get("height")), "rate": video.get("r_frame_rate"),
            "frames": int(video.get("nb_read_frames", -1)), "pix_fmt": video.get("pix_fmt", ""),
            "codec": video.get("codec_name", ""),
            "audio": any(s.get("codec_type") == "audio" for s in streams)}


def _video_failures(name: str, info: dict, size: tuple[int, int], fps: int | None = None,
                    frames: int | None = None, audio: bool = False) -> list[str]:
    if "error" in info:
        return [f"{name}: unreadable ({info['error']})"]
    fails = []
    if info["size"] != size:
        got = "x".join(map(str, info["size"]))
        fails.append(f"{name}: size {got}, expected {size[0]}x{size[1]}")
    if fps is not None and info["rate"] != f"{fps}/1":
        fails.append(f"{name}: frame rate {info['rate']}, expected {fps}/1")
    if frames is not None and info["frames"] != frames:
        fails.append(f"{name}: {info['frames']} frames, expected {frames}")
    if info["audio"] != audio:
        fails.append(f"{name}: {'has an audio stream' if info['audio'] else 'no audio stream'}")
    return fails


@dataclass
class _Sample:
    label: str                          # names the word in failure messages
    box: tuple[int, int, int, int]      # the word at rest on the canvas
    ink: Image.Image                    # 255 where its pad-0 mask is solid, else 0
    on: int                             # frame where it must be solid
    before: int | None                  # frame where it must not be yet (None: reveal is frame 0)
    cut: bool                           # its line fades out before the reveal completes


def _sync_samples(lines: list[LinePlan], theme: Theme) -> list[_Sample]:
    rev = _ceil_frame(theme.reveal_s, theme.fps)
    samples = []
    for lp in lines:
        for wp in lp.words:
            if wp.reveal is None:
                continue
            ink = _ink(wp.text, layout.word_fonts(theme, lp.layout.font_size, wp.box.emphasis))
            if ink is None:
                continue
            # Solid from reveal + rev until the line starts fading (never earlier, D-013).
            b, on = wp.box, min(wp.reveal + rev, lp.fade_start - 1, lp.stop - 1)
            samples.append(_Sample(f'word {b.index} "{wp.text}" (line {lp.layout.line + 1})',
                                   (b.x, b.y, b.x + b.w, b.y + b.h), ink, on,
                                   wp.reveal - 1 if wp.reveal > 0 else None,
                                   on < wp.reveal + rev))
    return samples


def _focus_samples(result: RenderResult, lines: list, theme: Theme) -> list[_Sample]:
    """Focus themes: v1's samples, read only where the word is clean (focus.readable). Any other
    word becomes a note, never a silent pass (spec 08 §4.5)."""
    rev, samples = _ceil_frame(theme.reveal_s, theme.fps), []
    for fl in lines:
        for wp in fl.words:
            if wp.reveal is None:
                continue
            ink = _ink(wp.text, layout.word_fonts(theme, fl.layout.font_size, wp.box.emphasis))
            if ink is None:
                continue
            b, label = wp.box, f'word {wp.box.index} "{wp.text}" (line {fl.layout.line + 1})'
            on, before = wp.reveal + rev, (wp.reveal - 1 if wp.reveal > 0 else None)
            i0, i1, i2, i3 = ink.getbbox()   # the ink mask is the box's size, at its origin
            rect = (b.x + i0, b.y + i1, b.x + i2, b.y + i3)
            if not focus.readable(lines, fl, on, theme, rect) or (
                    before is not None and not focus.readable(lines, fl, before, theme, rect)):
                result.notes.append(f"{label}: its line left the current slot, or another line "
                                    "overlapped it, before it could be read (sung back to back)")
                continue
            samples.append(_Sample(label, (b.x, b.y, b.x + b.w, b.y + b.h), ink, on, before,
                                   False))
    return samples


def _ink(text: str, fonts: layout.FontSet) -> Image.Image | None:
    """255 where the word's pad-0 glyph mask is solid, else 0; None for a word with no ink."""
    mask = layout.word_mask(text, fonts)
    top = (mask.getextrema() or (0, 0))[1]   # 255 for any real glyph; a 0-px mask → None
    return None if top == 0 else mask.point(lambda v: 255 if v >= top else 0)


def _stream(cmd: list[str], frame_size: int, visit) -> tuple[int, str | None]:
    """Run an ffmpeg decode to raw frames on stdout; visit(k, data) per frame. Returns the frame
    count and, if ffmpeg failed, the tail of its stderr."""
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    reader, tail = _drain(proc.stderr)
    decoded = 0
    try:
        while len(data := proc.stdout.read(frame_size)) == frame_size:
            visit(decoded, data)
            decoded += 1
    finally:
        proc.stdout.close()
        code = proc.wait()
        reader.join()
        proc.stderr.close()
    return decoded, (_tail_text(tail) if code != 0 else None)


def check_outputs(result: RenderResult, lines: list, theme: Theme, n_frames: int) -> list[str]:
    """ffprobe checks of the three outputs, then the theme's frame checks on the decoded overlay:
    the alpha sync check, plus the safe zone if set (reveal, focus), or the karaoke, lofi or
    cinematic checks."""
    out, size = result.outputs, (theme.width, theme.height)
    overlay = _probe(out["overlay"])
    fails = _video_failures("overlay.mov", overlay, size, theme.fps)
    if "error" not in overlay and not (overlay["pix_fmt"].startswith("yuva")
                                       or overlay["pix_fmt"] in ALPHA_PIX_FMTS):
        fails.append(f"overlay.mov: pix_fmt {overlay['pix_fmt']} has no alpha")
    fails += _video_failures("overlay_green.mp4", _probe(out["green"], count=True), size,
                             theme.fps, n_frames)
    fails += _video_failures("preview.mp4", _probe(out["preview"]), theme.preview_size,
                             audio=True)
    if theme.motion == "lofi":   # here, not at the top: lofi_check imports this module
        from .lofi_check import lofi_checks
        return fails + lofi_checks(result, lines, theme, n_frames)
    if theme.motion == "cinematic":   # the same: cinematic_check imports this module
        from .cinematic_check import cinematic_checks
        return fails + cinematic_checks(result, lines, theme, n_frames)
    if theme.motion == "beatpop":     # the same: beatpop_check imports this module
        from .beatpop_check import beatpop_checks
        return fails + beatpop_checks(result, lines, theme, n_frames)
    if theme.motion == "phonk":       # the same: phonk_check imports this module
        from .phonk_check import phonk_checks
        return fails + phonk_checks(result, lines, theme, n_frames)
    check = _karaoke_checks if theme.motion == "karaoke" else _alpha_sync
    return fails + check(result, lines, theme, n_frames)


def _wanted(samples: list[_Sample]) -> dict[int, list[tuple[_Sample, str]]]:
    wanted: dict[int, list[tuple[_Sample, str]]] = {}
    for s in samples:
        wanted.setdefault(s.on, []).append((s, "on"))
        if s.before is not None:
            wanted.setdefault(s.before, []).append((s, "before"))
    return wanted


def _decode_cmd(path: Path, *video_args: str) -> list[str]:
    return ["ffmpeg", "-hide_banner", "-nostats", "-loglevel", "error", "-i", str(path),
            *video_args, "-fps_mode", "passthrough", "-f", "rawvideo", "-pix_fmt", "gray", "-"]


def _alpha_sync(result: RenderResult, lines: list[LinePlan], theme: Theme,
                n_frames: int, samples: list[_Sample] | None = None) -> list[str]:
    """Reveal and focus themes: the overlay's alpha plane decoded once; every timed word's ink is
    solid just after its reveal and absent just before it; the safe zone, if the theme has one.
    `samples`: the words to read, when the theme builds its own (lofi-typewriter)."""
    size, fails = (theme.width, theme.height), []
    if samples is None:
        samples = (_focus_samples(result, lines, theme) if theme.motion == "focus"
                   else _sync_samples(lines, theme))
    wanted, means = _wanted(samples), {}
    zone, outside = theme.safe_zone, []

    def visit(k: int, data: bytes) -> None:
        if k in wanted:
            frame = Image.frombytes("L", size, data)
            for s, kind in wanted[k]:
                means[s.label, kind] = ImageStat.Stat(frame.crop(s.box), s.ink).mean[0]
        if zone is not None and (box := _zone_box(data, size, zone)):
            outside.append((k, box))

    decoded, error = _stream(_decode_cmd(result.outputs["overlay"], "-vf",
                                         "alphaextract,format=gray"),
                             theme.width * theme.height, visit)
    if error is not None:
        return [f"overlay.mov: alpha decode failed: {error}"]
    if decoded != n_frames:   # the overlay's frame count, from this one full decode
        fails.append(f"overlay.mov: {decoded} frames, expected {n_frames}")

    for s in samples:
        if s.cut:   # sung too close to the next line to ever show fully: a note, not a sync error
            result.notes.append(f"{s.label}: the next line starts before its reveal completes, "
                                "so it never shows fully (sung back to back)")
            continue
        on, before = means.get((s.label, "on")), means.get((s.label, "before"))
        if on is None:
            fails.append(f"sync: {s.label}: never shown solid; sample frame {s.on} is outside "
                         "the overlay")
        elif on < SYNC_ON_MIN:
            fails.append(f"sync: {s.label}: mean alpha {on:.0f} at frame {s.on}, expected "
                         f">= {SYNC_ON_MIN} once revealed")
        elif before is not None and before > on - SYNC_DROP_MIN:
            fails.append(f"sync: {s.label}: mean alpha {before:.0f} at frame {s.before}, the "
                         f"frame before its reveal; expected <= {on - SYNC_DROP_MIN:.0f}")
    if outside:
        fails.append(_zone_failure(outside, zone))
    return fails


def _karaoke_checks(result: RenderResult, lines: list, theme: Theme, n_frames: int) -> list[str]:
    """Karaoke themes, one decode of one colour plane stacked on the alpha plane:
    fill sync (a word shows no accent the frame before its fill starts and is all accent on the
    frame its fill ends, both read with its line at rest) and the safe zone on every frame."""
    fails = []
    text, accent = theme.text_rgb, theme.accent_rgb
    c = max(range(3), key=lambda k: abs(text[k] - accent[k]))   # the channel that tells them apart
    span = text[c] - accent[c]
    if abs(span) < 64:
        return [f"fill: accent {accent} is too close to text colour {text} to check the fill"]
    samples = []
    for kl in lines:
        def at_rest(m: int, kl=kl) -> bool:
            return kl.rest <= m < kl.fade_start and (kl.handover is None or m <= kl.handover)
        for fw in kl.words:
            if fw.start is None:
                continue
            ink = _ink(fw.text, layout.word_fonts(theme, kl.layout.font_size, fw.box.emphasis))
            if ink is None:
                continue
            label = f'word {fw.box.index} "{fw.text}" (line {kl.layout.line + 1})'
            if not at_rest(fw.end):   # handed over mid-fill: its fill still runs on its own time
                result.notes.append(f"{label}: its line moved to the past slot before its fill "
                                    "finished (sung back to back)")
                continue
            b = fw.box
            samples.append(_Sample(label, (b.x, b.y, b.x + b.w, b.y + b.h), ink, fw.end,
                                   fw.start - 1 if fw.start > 0 and at_rest(fw.start - 1)
                                   else None, False))
    means, outside, decoded, error = _colour_alpha(result, theme, c, _wanted(samples))
    if error is not None:
        return [f"overlay.mov: colour decode failed: {error}"]
    if decoded != n_frames:
        fails.append(f"overlay.mov: {decoded} frames, expected {n_frames}")
    for s in samples:
        after, before = (means[s.label, kind][0] if (s.label, kind) in means else None
                         for kind in ("on", "before"))
        if after is None:
            fails.append(f"fill: {s.label}: frame {s.on}, where its fill ends, is outside the "
                         "overlay")
            continue
        if (f := (text[c] - after) / span) < FILL_AFTER_MIN:
            fails.append(f"fill: {s.label}: {f:.0%} filled at frame {s.on}, where its fill ends; "
                         "expected 100%")
        if before is not None and (f := (text[c] - before) / span) > FILL_BEFORE_MAX:
            fails.append(f"fill: {s.label}: {f:.0%} filled at frame {s.before}, the frame before "
                         "its fill starts; expected 0%")
    if outside:
        fails.append(_zone_failure(outside, theme.safe_zone))
    return fails


def _colour_alpha(result: RenderResult, theme: Theme, c: int,
                  wanted: dict[int, list[tuple[_Sample, str]]]
                  ) -> tuple[dict[tuple[str, str], tuple[float, float]], list, int, str | None]:
    """One decode of the overlay's colour plane c ("rgb"[c]) stacked on its alpha plane: per
    wanted (label, kind), the mean colour and alpha over the sample's ink; the frames drawing
    outside the safe zone; the decoded frame count; and ffmpeg's error tail, if it failed."""
    size, plane = (theme.width, theme.height), theme.width * theme.height
    zone, means, outside = theme.safe_zone, {}, []

    def visit(k: int, data: bytes) -> None:
        if k in wanted:
            colour = Image.frombytes("L", size, data[:plane])
            alpha = Image.frombytes("L", size, data[plane:])
            for s, kind in wanted[k]:
                means[s.label, kind] = (ImageStat.Stat(colour.crop(s.box), s.ink).mean[0],
                                        ImageStat.Stat(alpha.crop(s.box), s.ink).mean[0])
        if zone is not None and (box := _zone_box(memoryview(data)[plane:], size, zone)):
            outside.append((k, box))

    graph = f"[0:v]format=gbrap,extractplanes={'rgb'[c]}+a[c][a];[c][a]vstack"
    decoded, error = _stream(_decode_cmd(result.outputs["overlay"], "-filter_complex", graph),
                             2 * plane, visit)
    return means, outside, decoded, error


def _zone_box(alpha, size: tuple[int, int], zone: tuple[int, int, int, int]) -> tuple | None:
    """The bbox of drawn pixels (alpha >= SAFE_ALPHA_MIN) when it leaves the zone, else None."""
    box = Image.frombytes("L", size, alpha).point(_SAFE_LUT).getbbox()
    if box and (box[0] < zone[0] or box[1] < zone[1] or box[2] > zone[2] or box[3] > zone[3]):
        return box
    return None


def _zone_failure(outside: list[tuple[int, tuple]], zone: tuple[int, int, int, int]) -> str:
    k, box = outside[0]
    return (f"safe zone: {len(outside)} frame(s) draw outside x {zone[0]}-{zone[2]}, "
            f"y {zone[1]}-{zone[3]}; first: frame {k}, bbox {box}")


# --- Report ----------------------------------------------------------------------------------
def write_report(result: RenderResult, doc: dict, *, codec: str, theme: Theme,
                 encode_s: float, check_s: float, extra: list[str] = ()) -> Path:
    """render/report.md: outputs and sizes, frames, wall time, lines not shown, check results,
    then `extra` sections (a background's)."""
    lyric_lines = doc["lyrics"]["lines"]
    timed = sum(1 for w in doc["words"] if _timed(w))
    static = [w for w in doc["words"] if not _timed(w) and w["line"] not in result.skipped_lines]
    out = [f"# Render report: {doc['song']}", "",
           f"- Theme: {theme.name}; alpha codec: {codec}",
           f"- Frames: {result.frames} ({theme.width}x{theme.height}, {theme.fps} fps, "
           f"{result.frames / theme.fps:.2f} s)",
           f"- Wall time: {result.wall_s:.1f} s (frames + encode {encode_s:.1f} s, "
           f"output check {check_s:.1f} s)",
           f"- Flagged words rendered (--allow-flagged): "
           f"{sum(1 for w in doc['words'] if w['flagged'])}",
           f"- Emphasis words: {len(result.emphasis)}"
           + (": " + ", ".join(result.emphasis) if result.emphasis else ""),
           "", "## Outputs", "", "| Output | File | Size (MB) |", "|---|---|---|",
           *(f"| {key} | `{p.name}` | {p.stat().st_size / 1e6:.1f} |" if p.exists()
             else f"| {key} | `{p.name}` | missing |" for key, p in result.outputs.items()),
           "", "## Lines not shown", ""]
    out += ([f"- line {n + 1}: {lyric_lines[n]} (no timed word)" for n in result.skipped_lines]
            or ["None: every line has at least one timed word."])
    if static:
        out += ["", "Untimed words shown static with their line (never animated):", "",
                *(f'- word {w["i"]} "{w["text"]}" (line {w["line"] + 1})' for w in static)]
    frame_checks = (f"fill check of {timed} timed word(s) on the overlay's colour" if
                    theme.motion == "karaoke" else
                    f"typing check of {timed} timed word(s) on the overlay's alpha" if
                    theme.motion == "lofi" and theme.typewriter else
                    f"colour-state check of {timed} timed word(s) on the overlay's colour and "
                    "alpha" if theme.motion == "lofi" else
                    f"reveal check of {timed} timed word(s) on the overlay's colour and alpha" if
                    theme.motion == "cinematic" else
                    f"pop and pill check of {timed} timed word(s) and beat check of the line's "
                    "size, on the overlay's alpha" if theme.motion == "beatpop" else
                    f"light check of {timed} timed word(s) and beat check of the glow, on the "
                    "overlay's colour and alpha" if theme.motion == "phonk" else
                    f"sync check of {timed} timed word(s) on the overlay's alpha")
    frame_checks += "; safe-zone check of every frame." if theme.safe_zone else "."
    outputs = ("three outputs" if len(result.outputs) == 3
               else "four outputs (the finished short: codec, frames, audio, legibility)")
    out += ["", "## Output check", "", f"ffprobe checks of all {outputs}; {frame_checks}", ""]
    out += (["**pass**"] if not result.checks
            else ["**FAIL**", "", *(f"- {c}" for c in result.checks)])
    if extra:
        out += ["", *extra]
    if result.notes:
        out += ["", "## Notes", "", *(f"- {note}" for note in result.notes)]
    path = result.render_dir / REPORT
    path.write_text("\n".join(out) + "\n", encoding="utf-8")
    return path
