"""Beat stage: song audio -> tempo and beat times in songs/<song>/beats.json (spec 11).

beats.json is the second contract between stages (D-022), beside words.json: detected locally from
the full mix, reused while it matches the audio (hand edits included), rebuilt when the audio or
the format changes. Beats are decoration input only: nothing here reads lyrics.txt or words.json,
and no word timing is ever created or moved from a beat (red line 1). librosa is imported lazily,
so commands that need no beats never load it (plan §2.11).
"""
from __future__ import annotations

import json
import math
import subprocess
from dataclasses import dataclass
from datetime import datetime
from importlib import metadata
from pathlib import Path

import numpy as np

from . import align, timing

BEATS_FILE = "beats.json"
PREVIEW_FILE = "beats_preview.m4a"
BEATS_VERSION = 1              # bump when a field is added; older files are rebuilt
SR = 22050                     # decode rate, mono float32 from ffmpeg (plan §2.2)
HOP = 256                      # 11.6 ms frames; 512 read 120 BPM as 117 (plan §2.3)
RMS_FRAME = 2048
SILENT_DBFS = -50.0            # near-digital silence (plan §2.5)
SILENT_MIN_BEATS = 2           # a silent run longer than this many beat periods gets no beats
MIN_BPM, MAX_BPM = 30, 300     # the --bpm range
CLICK_HZ, CLICK_S, CLICK_GAIN = 1500, 0.05, 0.5
SONG_GAIN = 0.8                # headroom for the song + click mix


class BeatsError(ValueError):
    """A problem the owner can fix: undecodable audio, an invalid beats.json."""


@dataclass(frozen=True)
class Detection:
    tempo: float                          # BPM; 0 when there are no beats
    beats: list[float]                    # seconds, 3 decimals, strictly ascending
    silent: list[tuple[float, float]]     # silent stretches that removed at least one beat


@dataclass
class BeatsResult:
    path: Path
    audio: Path
    doc: dict
    reused: bool
    notes: list[str]


def ensure_beats(song_dir: Path, *, fresh: bool = False, bpm: float | None = None) -> BeatsResult:
    """The song's beats: beats.json reused while it is valid for the audio, else detected and saved.

    `fresh` or a `bpm` hint always detects again. A current but invalid file (a broken hand edit)
    raises BeatsError and is left untouched; a stale one (other audio, older format) is rebuilt.
    """
    song_dir = Path(song_dir)
    audio = align.song_audio(song_dir)
    path = song_dir / BEATS_FILE
    sha = timing.sha256_file(audio)
    notes = []
    if path.exists() and not fresh and bpm is None:
        doc = load_beats(path)
        reason = stale_reason(doc, sha)
        if reason is None:
            found = problems(doc)
            if found:
                raise BeatsError(f"{path} is not valid:\n  " + "\n  ".join(found)
                                 + f"\nfix it or run: beats {song_dir} --fresh")
            return BeatsResult(path, audio, doc, reused=True, notes=[])
        notes.append(f"{reason}: beats rebuilt")
    y = decode(audio)
    det = detect(y, SR, bpm)
    if bpm is not None:
        notes.append(f"tempo hint: {bpm:g} BPM")
    if not det.beats:
        notes.append("no steady beat found: beats.json has no beats")
    notes += [f"no beats in silence {a:.2f}-{b:.2f} s" for a, b in det.silent]
    doc = make_doc(song_dir.name, audio, sha, round(len(y) / SR, 3), det, bpm)
    save_beats(path, doc)
    return BeatsResult(path, audio, doc, reused=False, notes=notes)


def decode(audio: Path) -> np.ndarray:
    """The audio as mono float32 at SR, decoded by ffmpeg (every format in AUDIO_EXTS)."""
    cmd = ["ffmpeg", "-hide_banner", "-loglevel", "error", "-i", str(audio), "-map", "0:a:0",
           "-f", "f32le", "-ac", "1", "-ar", str(SR), "pipe:1"]
    try:
        proc = subprocess.run(cmd, capture_output=True)
    except FileNotFoundError as exc:
        raise BeatsError("ffmpeg not found on PATH") from exc
    if proc.returncode != 0:
        last = proc.stderr.decode("utf-8", "replace").strip().splitlines()[-1:]
        raise BeatsError(f"cannot decode {Path(audio).name}: {' '.join(last)}")
    y = np.frombuffer(proc.stdout, dtype="<f4")
    if not y.size:
        raise BeatsError(f"{Path(audio).name} has no audio samples")
    return y


def detect(y: np.ndarray, sr: int = SR, bpm: float | None = None) -> Detection:
    """Beats of one mono signal (plan §5.1): one tempo for the song, no beat in a silent stretch."""
    import librosa
    tempo, times = librosa.beat.beat_track(y=y, sr=sr, hop_length=HOP, units="time",
                                           **({"bpm": bpm} if bpm else {}))
    tempo = float(np.atleast_1d(tempo)[0])
    if not len(times):
        return Detection(0.0, [], [])
    # librosa keeps the pulse going through a dead stop; a run of silent frames longer than
    # SILENT_MIN_BEATS beat periods loses every beat inside it
    rms = librosa.feature.rms(y=y, frame_length=RMS_FRAME, hop_length=HOP)[0]
    silent = np.concatenate(([0], (rms < 10 ** (SILENT_DBFS / 20)).astype(np.int8), [0]))
    edges = np.flatnonzero(np.diff(silent))
    min_run = math.ceil(SILENT_MIN_BEATS * 60 / tempo * sr / HOP)
    keep = np.ones(len(times), dtype=bool)
    spans = []
    for start, end in zip(edges[::2], edges[1::2]):
        a, b = start * HOP / sr, end * HOP / sr
        inside = (times >= a) & (times < b)
        if end - start > min_run and inside.any():
            keep &= ~inside
            spans.append((round(a, 2), round(b, 2)))
    beats = sorted({round(float(t), 3) for t in times[keep]})
    return Detection(round(tempo, 2) if beats else 0.0, beats, spans)


def make_doc(song: str, audio: Path, sha: str, duration_s: float, det: Detection,
             bpm: float | None) -> dict:
    """The beats.json document (plan §3.1). Its key order is the key order on disk."""
    return {
        "version": BEATS_VERSION,
        "song": song,
        "audio": {"file": Path(audio).name, "duration_s": duration_s, "sha256": sha},
        "detector": {"library": "librosa", "version": metadata.version("librosa"),
                     "sample_rate": SR, "hop_length": HOP, "bpm_hint": bpm},
        "created": datetime.now().isoformat(timespec="seconds"),
        "tempo_bpm": det.tempo,
        "beats": det.beats,
    }


def save_beats(path: Path, doc: dict) -> None:
    """One beat per line: the easiest shape to hand-edit."""
    Path(path).write_text(json.dumps(doc, indent=2) + "\n", encoding="utf-8", newline="\n")


def load_beats(path: Path) -> dict:
    # utf-8-sig: a text editor may add a BOM when the owner hand-edits the file
    try:
        return json.loads(Path(path).read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError as exc:
        raise BeatsError(f"{path}: not valid JSON at line {exc.lineno}, column {exc.colno}: "
                         f"{exc.msg}\nfix it or run: beats {Path(path).parent} --fresh") from None


def stale_reason(doc, sha: str) -> str | None:
    """Why a file belongs to other audio or an older format (so it is rebuilt), else None."""
    if not isinstance(doc, dict):
        return None
    version, audio = doc.get("version"), doc.get("audio")
    if isinstance(version, int) and not isinstance(version, bool) and version < BEATS_VERSION:
        return f"older format (version {version})"
    if isinstance(audio, dict) and isinstance(audio.get("sha256"), str) and audio["sha256"] != sha:
        return "audio changed"
    return None


def problems(doc) -> list[str]:
    """What makes a current file unusable (plan §5.2), each check reported at most once."""
    if not isinstance(doc, dict):
        return ["not a JSON object"]
    found = []
    version = doc.get("version")
    if version != BEATS_VERSION or isinstance(version, bool):
        found.append(f"version {version!r} is not one this engine writes ({BEATS_VERSION})")
    audio = doc["audio"] if isinstance(doc.get("audio"), dict) else {}
    if not isinstance(audio.get("sha256"), str):
        found.append("audio.sha256 is missing")
    duration = audio.get("duration_s")
    if not (timing.is_num(duration) and duration > 0):
        found.append("audio.duration_s is not a positive number")
        duration = None
    tempo = doc.get("tempo_bpm")
    if not (timing.is_num(tempo) and tempo >= 0):
        found.append("tempo_bpm is not a number >= 0")
    beats = doc.get("beats")
    if not isinstance(beats, list):
        return found + ["beats is not a list"]
    bad = next((i for i, t in enumerate(beats) if not timing.is_num(t)), None)
    if bad is not None:
        return found + [f"beats[{bad}] is not a number"]
    out = next((i for i, t in enumerate(beats) if duration and not 0 <= t <= duration), None)
    if out is not None:
        found.append(f"beats[{out}] = {beats[out]} is outside 0-{duration} s")
    back = next((i for i in range(1, len(beats)) if beats[i] <= beats[i - 1]), None)
    if back is not None:
        found.append(f"beats[{back}] = {beats[back]} is not after beats[{back - 1}] = "
                     f"{beats[back - 1]}")
    return found


def write_preview(audio: Path, doc: dict, out: Path) -> Path:
    """Review only: the song with a click on every beat, as AAC audio (plan §5.4)."""
    import librosa
    n = round(doc["audio"]["duration_s"] * SR)
    clicks = (librosa.clicks(times=doc["beats"], sr=SR, length=n, click_freq=CLICK_HZ,
                             click_duration=CLICK_S) * CLICK_GAIN
              if doc["beats"] else np.zeros(n))
    cmd = ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", str(audio),
           "-f", "f32le", "-ar", str(SR), "-ac", "1", "-i", "pipe:0",
           "-filter_complex",
           f"[0:a:0]volume={SONG_GAIN}[s];[s][1:a]amix=inputs=2:duration=first:normalize=0[a]",
           "-map", "[a]", "-c:a", "aac", "-b:a", "160k", str(out)]
    try:
        proc = subprocess.run(cmd, input=clicks.astype("<f4").tobytes(), capture_output=True)
    except FileNotFoundError as exc:
        raise RuntimeError("ffmpeg not found on PATH") from exc
    if proc.returncode != 0:
        tail = " | ".join(proc.stderr.decode("utf-8", "replace").strip().splitlines()[-5:])
        raise RuntimeError(f"ffmpeg preview failed for {Path(out).name}: {tail}")
    return Path(out)
