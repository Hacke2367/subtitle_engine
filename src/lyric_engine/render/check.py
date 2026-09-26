"""Output check (ffprobe + a per-word sync check on the overlay's alpha) and render/report.md."""
from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from PIL import Image, ImageStat

from .. import layout
from ..theme import Theme
from .encode import _drain, _tail_text
from .timeline import LinePlan, _ceil_frame, _timed

if TYPE_CHECKING:
    from . import RenderResult

REPORT = "report.md"
ALPHA_PIX_FMTS = {"rgba", "argb", "bgra", "abgr", "rgba64le", "rgba64be"}
SYNC_ON_MIN, SYNC_DROP_MIN = 200, 100   # mean word alpha when on / required drop just before it


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
            fonts = layout.word_fonts(theme, lp.layout.font_size, wp.box.emphasis)
            mask = layout.word_mask(wp.text, fonts)
            top = (mask.getextrema() or (0, 0))[1]   # 255 for any real glyph; a 0-px mask → None
            if top == 0:
                continue
            # Solid from reveal + rev until the line starts fading (never earlier, D-013).
            b, on = wp.box, min(wp.reveal + rev, lp.fade_start - 1, lp.stop - 1)
            samples.append(_Sample(f'word {b.index} "{wp.text}" (line {lp.layout.line + 1})',
                                   (b.x, b.y, b.x + b.w, b.y + b.h),
                                   mask.point(lambda v, top=top: 255 if v >= top else 0), on,
                                   wp.reveal - 1 if wp.reveal > 0 else None,
                                   on < wp.reveal + rev))
    return samples


def check_outputs(result: RenderResult, lines: list[LinePlan], theme: Theme,
                  n_frames: int) -> list[str]:
    """ffprobe checks of the three outputs, then a sync check on the overlay's alpha plane (decoded
    once): every timed word's ink is solid just after its reveal and absent just before it."""
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

    samples = _sync_samples(lines, theme)
    wanted: dict[int, list[tuple[_Sample, str]]] = {}
    for s in samples:
        wanted.setdefault(s.on, []).append((s, "on"))
        if s.before is not None:
            wanted.setdefault(s.before, []).append((s, "before"))
    means: dict[tuple[str, str], float] = {}
    cmd = ["ffmpeg", "-hide_banner", "-nostats", "-loglevel", "error", "-i", str(out["overlay"]),
           "-vf", "alphaextract,format=gray", "-fps_mode", "passthrough",
           "-f", "rawvideo", "-pix_fmt", "gray", "-"]
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    reader, tail = _drain(proc.stderr)
    decoded, frame_size = 0, theme.width * theme.height
    try:
        while len(data := proc.stdout.read(frame_size)) == frame_size:
            if decoded in wanted:
                frame = Image.frombytes("L", size, data)
                for s, kind in wanted[decoded]:
                    means[s.label, kind] = ImageStat.Stat(frame.crop(s.box), s.ink).mean[0]
            decoded += 1
    finally:
        proc.stdout.close()
        code = proc.wait()
        reader.join()
        proc.stderr.close()
    if code != 0:
        return fails + [f"overlay.mov: alpha decode failed: {_tail_text(tail)}"]
    if decoded != n_frames:   # the overlay's frame count, from this one full decode
        fails.append(f"overlay.mov: {decoded} frames, expected {n_frames}")

    for s in samples:
        if s.cut:   # sung too close to the next line to ever show fully: a note, not a sync error
            result.notes.append(f"{s.label}: the next line starts before its reveal completes, "
                                "so it never shows fully (sung back to back)")
            continue
        on, before = means.get((s.label, "on")), means.get((s.label, "before"))
        why = ""
        if on is None:
            fails.append(f"sync: {s.label}: never shown solid; sample frame {s.on} is outside "
                         f"the overlay{why}")
        elif on < SYNC_ON_MIN:
            fails.append(f"sync: {s.label}: mean alpha {on:.0f} at frame {s.on}, expected "
                         f">= {SYNC_ON_MIN} once revealed{why}")
        elif before is not None and before > on - SYNC_DROP_MIN:
            fails.append(f"sync: {s.label}: mean alpha {before:.0f} at frame {s.before}, the "
                         f"frame before its reveal; expected <= {on - SYNC_DROP_MIN:.0f}")
    return fails


# --- Report ----------------------------------------------------------------------------------
def write_report(result: RenderResult, doc: dict, *, codec: str, theme: Theme,
                 encode_s: float, check_s: float) -> Path:
    """render/report.md: outputs and sizes, frames, wall time, lines not shown, check results."""
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
    out += ["", "## Output check", "",
            f"ffprobe checks of all three outputs; sync check of {timed} timed word(s) on the "
            "overlay's alpha.", ""]
    out += (["**pass**"] if not result.checks
            else ["**FAIL**", "", *(f"- {c}" for c in result.checks)])
    if result.notes:
        out += ["", "## Notes", "", *(f"- {note}" for note in result.notes)]
    path = result.render_dir / REPORT
    path.write_text("\n".join(out) + "\n", encoding="utf-8")
    return path
