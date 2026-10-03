"""ffmpeg: a video or audio file -> the mono audio the transcription engine is sent; the
styled subtitles drawn onto a transparent strip (overlay .mov); and a preview of the two.

ffmpeg does the extraction, so a video never leaves the machine: only this small audio file is
uploaded (red line 4). 16 kHz mono is what speech models want, and it keeps a 40-second clip
around 300 kB.
"""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
from pathlib import Path

FONTS_DIR = Path(__file__).resolve().parent / "fonts"   # the subtitles' fonts (OFL), shipped here
SAMPLE_RATE = 16_000
BITRATE = "64k"
MEDIA_SUFFIXES = {".mp4", ".mov", ".mkv", ".webm", ".avi", ".m4v", ".wav", ".mp3", ".m4a",
                  ".aac", ".flac", ".ogg", ".opus", ".wma"}


class MediaError(RuntimeError):
    """ffmpeg is missing, or the file has no audio this tool can read."""


def extract_audio(source: Path, dest: Path) -> Path:
    """Write source's audio to dest as 16 kHz mono mp3 (overwritten if it exists)."""
    source, dest = Path(source), Path(dest)
    if not source.is_file():
        raise MediaError(f"no such file: {source}")
    dest.parent.mkdir(parents=True, exist_ok=True)
    _run(["ffmpeg", "-nostdin", "-v", "error", "-y", "-i", str(source), "-vn", "-ac", "1",
          "-ar", str(SAMPLE_RATE), "-c:a", "libmp3lame", "-b:a", BITRATE, str(dest)])
    if not dest.is_file() or dest.stat().st_size == 0:
        raise MediaError(f"ffmpeg wrote no audio from {source.name} (does it have a sound track?)")
    return dest


def preview(source: Path, overlay: Path, dest: Path, at: float = 0.66) -> Path:
    """The video with the overlay laid on it, its middle `at` of the way down: review only.

    It shows the overlay file itself, exactly as the owner will drop it in CapCut; where it
    sits there is the owner's call, so `at` is only a stand-in.
    """
    source, overlay, dest = Path(source), Path(overlay), Path(dest)
    dest.parent.mkdir(parents=True, exist_ok=True)
    _run(["ffmpeg", "-nostdin", "-v", "error", "-y", "-i", str(source), "-i", str(overlay),
          "-filter_complex", f"[0:v][1:v]overlay=x=(W-w)/2:y=H*{at}-h/2:format=auto",
          "-c:a", "copy", "-preset", "veryfast", str(dest)])
    if not dest.is_file() or dest.stat().st_size == 0:
        raise MediaError(f"ffmpeg wrote no preview for {source.name}")
    return dest


def render_overlay(ass: Path, dest: Path, size: tuple[int, int], fps: float,
                   seconds: float) -> Path:
    """The styled subtitles alone on a transparent strip: a ProRes 4444 .mov with alpha.

    The owner drops it on the track above the video in CapCut, where they want. Same codec as the
    lyric engine's overlay, which CapCut was proven to read with its transparency (V1 D-005).
    """
    ass, dest = Path(ass).resolve(), Path(dest).resolve()
    dest.parent.mkdir(parents=True, exist_ok=True)
    width, height = size
    # ffmpeg's own transparent mode (ass=...:alpha=1) squares a half-clear pixel's opacity
    # (measured: a word at 45% came out at 20%). So the subtitles are drawn twice, on black and
    # on white, and the true opacity is read from the difference: on black a pixel is
    # colour x alpha, on white it is that plus (1 - alpha) x 255.
    canvas = f"s={width}x{height}:r={fps:g}:d={seconds:.3f},format=gbrp"
    draw = _subtitle_filter(ass)
    graph = (f"color=c=black:{canvas},{draw},split[b1][b2];"
             f"color=c=white:{canvas},{draw}[w];"
             "[w][b1]blend=all_expr='255-(A-B)',extractplanes=g[a];"
             "[b2][a]alphamerge,unpremultiply=inplace=1,"
             "scale=out_color_matrix=bt709:out_range=tv,format=yuva444p10le[out]")
    _run(["ffmpeg", "-nostdin", "-v", "error", "-y", "-filter_complex", graph, "-map", "[out]",
          "-c:v", "prores_ks", "-profile:v", "4444", "-alpha_bits", "16", "-vendor", "apl0",
          "-colorspace", "bt709", "-color_primaries", "bt709", "-color_trc", "bt709",
          "-color_range", "tv", str(dest)], cwd=ass.parent)
    if not dest.is_file() or dest.stat().st_size == 0:
        raise MediaError(f"ffmpeg wrote no overlay for {ass.name}")
    return dest


def video_format(path: Path) -> tuple[tuple[int, int], float] | None:
    """((width, height), frames per second) of the file's video, or None for audio only."""
    out = _run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
                "stream=width,height,avg_frame_rate", "-of", "json", str(Path(path))])
    streams = json.loads(out or "{}").get("streams") or []
    if not streams or not streams[0].get("width"):
        return None
    stream = streams[0]
    num, _, den = str(stream.get("avg_frame_rate", "30/1")).partition("/")
    try:
        fps = float(num) / float(den or 1)
    except (ValueError, ZeroDivisionError):
        fps = 30.0
    return (int(stream["width"]), int(stream["height"])), (fps if fps > 0 else 30.0)


def _subtitle_filter(subs: Path) -> str:
    """The ffmpeg filter that draws this subtitle file, for ffmpeg run from the file's folder.

    ffmpeg's filter syntax treats ':' and '\\' as its own punctuation, so the files are named
    relative to that folder rather than by a Windows path with a drive letter.
    """
    try:
        fonts = os.path.relpath(FONTS_DIR, subs.parent).replace("\\", "/")
    except ValueError:                      # another drive: no relative path exists
        fonts = str(FONTS_DIR).replace("\\", "/").replace(":", "\\:")
    return f"ass={subs.name}:fontsdir={fonts}"


def duration(path: Path) -> float:
    """Length in seconds, from ffprobe."""
    out = _run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                "-of", "json", str(Path(path))])
    try:
        return float(json.loads(out)["format"]["duration"])
    except (ValueError, KeyError, TypeError) as exc:
        raise MediaError(f"ffprobe gave no duration for {Path(path).name}") from exc


def fingerprint(path: Path) -> str:
    """A short hash of the file, so a re-run can tell the same audio from a different one."""
    digest = hashlib.sha1()
    with open(path, "rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()[:16]


def _run(command: list[str], cwd: Path | None = None) -> str:
    try:
        done = subprocess.run(command, capture_output=True, text=True, check=False, cwd=cwd)
    except FileNotFoundError as exc:
        raise MediaError(f"{command[0]} is not on PATH") from exc
    if done.returncode != 0:
        detail = (done.stderr or done.stdout or "").strip().splitlines()
        raise MediaError(f"{command[0]} failed: {detail[-1] if detail else done.returncode}")
    return done.stdout
