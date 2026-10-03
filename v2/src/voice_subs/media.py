"""A video or audio file -> the one mono audio file the transcription engine is sent.

ffmpeg does the extraction, so a video never leaves the machine: only this small audio file is
uploaded (red line 4). 16 kHz mono is what speech models want, and it keeps a 40-second clip
around 300 kB.
"""
from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path

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


def burn_subtitles(source: Path, srt: Path, dest: Path) -> Path:
    """A preview copy of the video with the subtitles drawn on it, to check the timing by eye.

    Review only: the product is the `.srt`, which the user imports into their own editor.
    """
    source, srt, dest = Path(source).resolve(), Path(srt).resolve(), Path(dest).resolve()
    dest.parent.mkdir(parents=True, exist_ok=True)
    # ffmpeg's filter syntax treats ':' and '\' as its own punctuation, so the subtitle file is
    # named relative to its folder instead, with ffmpeg run from there.
    _run(["ffmpeg", "-nostdin", "-v", "error", "-y", "-i", str(source),
          # force_style's own commas must stay inside quotes, or ffmpeg reads them as filters.
          "-vf", f"subtitles={srt.name}:force_style='FontName=Arial,Fontsize=16,"
                 f"Outline=1,MarginV=60'",
          "-c:a", "copy", "-preset", "veryfast", str(dest)], cwd=srt.parent)
    if not dest.is_file() or dest.stat().st_size == 0:
        raise MediaError(f"ffmpeg wrote no preview for {source.name}")
    return dest


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
