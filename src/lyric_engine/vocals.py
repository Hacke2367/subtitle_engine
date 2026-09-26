"""Vocal isolation: song audio -> a vocals-only WAV on the same timeline (Demucs htdemucs, CPU).

Word times measured on the vocals are used against the original audio, so the output keeps the
input's timeline: the same samples ffmpeg decodes from the input, at 44.1 kHz stereo, one output
sample per input sample. The result is cached: a JSON sidecar next to the WAV records the
source's sha256 and the model, and a matching sidecar means the WAV is reused.

Plan: docs/specs/02_word_alignment_impl.md section 4 (agent L).
"""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
import wave
from pathlib import Path

MODEL = "htdemucs"   # Demucs v4 hybrid transformer; ~80 MB of weights, cached by torch.hub
SHIFTS = 0           # no random time shifts, so the same audio always gives the same stem
OVERLAP = 0.25       # between the model's 7.8 s segments; RAM stays bounded by one segment


def isolate_vocals(audio: Path, out_wav: Path, *, fresh: bool = False) -> Path:
    """Write the vocals stem of `audio` to `out_wav` (16-bit PCM WAV) and return its path.

    Reused when the sidecar `out_wav.with_suffix(".json")` matches the audio's sha256 and the
    model, unless `fresh`. Raises RuntimeError when the audio can't be decoded or the model
    can't load or run (including out of memory).
    """
    audio, out_wav = Path(audio), Path(out_wav)
    sidecar = out_wav.with_suffix(".json")
    stamp = {"source_sha256": _sha256(audio), "model": MODEL}
    if not fresh and out_wav.exists() and _read_json(sidecar) == stamp:
        return out_wav

    vocals, rate = _separate(audio)
    out_wav.parent.mkdir(parents=True, exist_ok=True)
    sidecar.unlink(missing_ok=True)  # a half-written WAV must never look cached
    _write_wav(out_wav, vocals, rate)
    sidecar.write_text(json.dumps(stamp, indent=2) + "\n", encoding="utf-8")
    return out_wav


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def _read_json(path: Path) -> dict | None:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def _separate(audio: Path):
    """(vocals as float32 array of shape (channels, n), sample rate)."""
    import torch  # heavy imports only when a separation actually runs
    from demucs.apply import apply_model
    from demucs.pretrained import get_model

    try:
        model = get_model(MODEL)
    except Exception as exc:  # network, cache or checkpoint problem
        raise RuntimeError(f"could not load the Demucs model {MODEL!r} (the first run downloads "
                           f"~80 MB into {torch.hub.get_dir()}): {exc}") from exc
    model.eval()

    mix = torch.from_numpy(_decode(audio, model.samplerate, model.audio_channels))
    ref = mix.mean(0)
    mean, std = ref.mean(), ref.std() + 1e-8  # the normalisation demucs' own CLI applies
    try:
        with torch.inference_mode():
            sources = apply_model(model, ((mix - mean) / std)[None], shifts=SHIFTS,
                                  split=True, overlap=OVERLAP, progress=False)[0]
    except (RuntimeError, MemoryError) as exc:
        raise RuntimeError(f"vocal isolation of {audio.name} failed ({MODEL}); if this is out "
                           f"of memory, close other programs and retry: {exc}") from exc
    vocals = sources[model.sources.index("vocals")] * std + mean
    return vocals.numpy(), model.samplerate


def _decode(audio: Path, rate: int, channels: int):
    """ffmpeg -> float32 array (channels, n) at `rate`, starting at the file's first sample."""
    import numpy as np

    cmd = ["ffmpeg", "-hide_banner", "-nostdin", "-loglevel", "error", "-i", str(audio),
           "-vn", "-ac", str(channels), "-ar", str(rate), "-f", "f32le", "-"]
    try:
        proc = subprocess.run(cmd, capture_output=True)
    except FileNotFoundError as exc:
        raise RuntimeError("ffmpeg not found on PATH") from exc
    if proc.returncode != 0 or not proc.stdout:
        err = proc.stderr.decode("utf-8", errors="replace").strip()[-300:] or "no audio stream"
        raise RuntimeError(f"ffmpeg could not decode {audio.name}: {err}")
    return np.frombuffer(proc.stdout, dtype="<f4").reshape(-1, channels).T.copy()


def _write_wav(path: Path, samples, rate: int) -> None:
    import numpy as np

    peak = float(np.abs(samples).max(initial=0.0))
    if peak > 1.0:
        samples = samples / (1.01 * peak)  # rescale rather than clip, as demucs does
    pcm = np.round(samples.T * 32767).astype("<i2")  # interleaved frames
    tmp = path.with_name(path.name + ".part")
    with wave.open(str(tmp), "wb") as w:
        w.setnchannels(samples.shape[0])
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes(pcm.tobytes())
    os.replace(tmp, path)
