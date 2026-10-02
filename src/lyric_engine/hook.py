"""Find a song's main part: the stretch that repeats most (in a Hindi film song the mukhda, sung
again after every antara) and is sung loud, with each cut moved to the quietest moment nearby so
no word is split. Audio only (librosa, and Demucs for the vocals stem, both imported lazily): it picks a range to
cut, never a word's time. `hook songs/<song>` suggests, writes `hook_preview.mp3`; `--cut` writes the clip as
`audio.wav` (the full song is kept as `full.<ext>`), ready for lyrics.txt and `make`."""
from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from .align import AUDIO_EXTS
from .beats import SR, decode

STEP_S = 0.5          # analysis resolution
MIN_GAP_S = 20.0      # a repeat this close is the same passage, not a repeat
INTRO_S = 3.0         # a cut never starts inside the first seconds
SNAP_S = 1.5          # each cut moves to the quietest point within this
SING = 0.15           # the vocals stem is singing above this share of its loudest
FINE_S = 0.02         # the fine loudness step (hop 441 at 22.05 kHz)
MIN_SUNG = 0.7        # a stretch must be sung for at least this share of its length
EARLY = 1.0          # the earlier a stretch, the better (the mukhda comes first)
PREVIEW = "hook_preview.mp3"


@dataclass
class Hook:
    start: float
    end: float
    score: float       # 0..1: how strongly it repeats elsewhere, weighted by loudness


def source_audio(song_dir: Path) -> Path:
    """The full song: full.<ext> if a cut was already made, else the folder's one audio.<ext>."""
    for name in ("full", "audio"):
        found = [p for p in sorted(song_dir.glob(f"{name}.*")) if p.suffix.lower() in AUDIO_EXTS]
        if len(found) == 1:
            return found[0]
    raise FileNotFoundError(f"{song_dir}: put the song in as audio.mp3 (or full.mp3)")


def find_hooks(y: np.ndarray, voice: np.ndarray, seconds: float = 30.0, top: int = 3) -> list[Hook]:
    """The best `top` stretches of about `seconds`, best first, at least a clip apart. `voice` is
    the vocals stem on the same timeline: a stretch must be mostly sung, and the earliest sung
    stretch that repeats later wins (in a film song that is the mukhda)."""
    import librosa
    hop = 512
    per = max(1, round(STEP_S * SR / hop))
    chroma = librosa.feature.chroma_stft(y=y, sr=SR, hop_length=hop)
    rms = librosa.feature.rms(y=y, hop_length=hop)[0]
    vrms = librosa.feature.rms(y=voice, hop_length=hop)[0]
    n = min(chroma.shape[1], rms.size, vrms.size) // per
    c = chroma[:, :n * per].reshape(12, n, per).mean(2)
    c /= np.linalg.norm(c, axis=0, keepdims=True) + 1e-9
    energy = rms[:n * per].reshape(n, per).mean(1)
    v = vrms[:n * per].reshape(n, per).mean(1)
    singing = (v > SING * v.max()).astype(np.float64)
    L, gap = round(seconds / STEP_S), round(MIN_GAP_S / STEP_S)
    if n < L + 1:
        return [Hook(0.0, len(y) / SR, 0.0)]
    sim = c.T @ c
    rep = np.zeros(n - L + 1)
    for lag in range(gap, n - L + 1):   # mean similarity of each window with the window `lag` later
        d = np.concatenate(([0.0], np.cumsum(np.diagonal(sim, lag))))
        m = (d[L:] - d[:-L]) / L
        k = m.size
        rep[:k] = np.maximum(rep[:k], m)                     # it repeats later
        rep[lag:lag + k] = np.maximum(rep[lag:lag + k], m)   # it repeats something earlier
    sung = np.convolve(singing, np.ones(L) / L, "valid")
    loud = np.convolve(energy, np.ones(L) / L, "valid")
    base = np.median(rep)
    r = np.clip((rep - base) / (rep.max() - base + 1e-9), 0, 1)
    starts = np.arange(n - L + 1)
    score = r * (0.6 + 0.4 * loud / (loud.max() + 1e-9)) - EARLY * starts / n
    score[(starts * STEP_S < INTRO_S) | (sung < MIN_SUNG)] = -1
    picks: list[int] = []
    for i in np.argsort(-score):
        if score[i] < 0 or len(picks) == top:
            break
        if all(abs(i - j) >= L for j in picks):
            picks.append(int(i))
    if not picks:
        return [Hook(0.0, min(seconds, len(y) / SR), 0.0)]
    fine = _quietness(voice)
    active = fine > SING * fine.max()
    hooks = []
    for i in picks:
        start = _phrase_start(i * STEP_S, active, fine)
        hooks.append(Hook(start, _phrase_end(start + seconds, active, fine), float(max(score[i], 0))))
    return hooks


def _quietness(y: np.ndarray) -> np.ndarray:
    """Loudness every 20 ms, smoothed over 100 ms."""
    import librosa
    rms = librosa.feature.rms(y=y, frame_length=1024, hop_length=441)[0]
    return np.convolve(rms, np.ones(5) / 5, "same")


def _gaps(active: np.ndarray, min_s: float) -> list[tuple[float, float]]:
    """Stretches of at least min_s with no singing, as (start, end) seconds."""
    x = np.concatenate(([0], (~active).astype(np.int8), [0]))
    edges = np.flatnonzero(np.diff(x))
    return [(a * FINE_S, b * FINE_S) for a, b in zip(edges[::2], edges[1::2])
            if (b - a) * FINE_S >= min_s]


def _phrase_start(t: float, active: np.ndarray, fine: np.ndarray) -> float:
    """Just before the first real sung line from t - 4 s on, less a breath. A short sound left
    alone by long pauses (a hum, a spoken word) is not a line: a run of singing counts when it
    lasts 4 s or is followed by a pause shorter than 1.5 s, as lines inside a verse are."""
    gaps = _gaps(active, 0.3)
    ends = [0.0, *(b for _, b in gaps)]                  # where each run of singing starts
    nexts = [a for a, _ in gaps] + [len(active) * FINE_S]
    for run_start in ends:
        if not t - 4 <= run_start <= t + 15:
            continue
        run_end = min((a for a in nexts if a > run_start), default=len(active) * FINE_S)
        pause = next(((b - a) for a, b in gaps if a >= run_end - 1e-6), 0.0)
        if run_end - run_start >= 4 or pause < 1.5:
            return round(max(0.0, run_start - 0.25), 2)
    return _snap(t, fine)


def _phrase_end(t: float, active: np.ndarray, fine: np.ndarray) -> float:
    """Where the singing stops after the last whole line near t: the first pause of 1 s or more
    (between sections; lines inside one are a breath apart) from t - 4 s on, plus a ring-out."""
    near = [a for a, b in _gaps(active, 1.0) if t - 4 <= a <= t + 8]
    if not near:
        return _snap(t, fine)
    return round(min(near) + 0.5, 2)


def _snap(t: float, fine: np.ndarray) -> float:
    """t moved to the quietest 20 ms frame within SNAP_S (a breath or a gap between lines)."""
    a, b = max(0, round((t - SNAP_S) / FINE_S)), min(fine.size, round((t + SNAP_S) / FINE_S) + 1)
    if b <= a:
        return round(t, 2)
    return round((a + int(np.argmin(fine[a:b]))) * FINE_S, 2)


def clock(t: float) -> str:
    return f"{int(t // 60)}:{t % 60:04.1f}"


def _ffmpeg(args: list[str]) -> None:
    proc = subprocess.run(["ffmpeg", "-v", "error", "-y", *args], capture_output=True, text=True)
    if proc.returncode != 0:
        raise RuntimeError(f"ffmpeg failed: {proc.stderr.strip()[-300:]}")


def write_clip(src: Path, hook: Hook, out: Path, preview: bool) -> None:
    """The stretch as a preview mp3 (soft fades, for listening) or as the song's audio.wav."""
    dur = hook.end - hook.start
    if preview:
        _ffmpeg(["-ss", f"{hook.start:.2f}", "-t", f"{dur:.2f}", "-i", str(src), "-af",
                 f"afade=in:d=0.3,afade=out:st={max(dur - 0.8, 0):.2f}:d=0.8", "-q:a", "4", str(out)])
    else:
        _ffmpeg(["-ss", f"{hook.start:.2f}", "-t", f"{dur:.2f}", "-i", str(src), "-ac", "2",
                 "-ar", "44100", "-c:a", "pcm_s16le", str(out)])


def suggest(song_dir: Path, seconds: float = 30.0, cut: bool = False, pick: int = 1) -> int:
    from .vocals import isolate_vocals   # Demucs on the CPU, cached in work/: ~1-3 min a song
    src = source_audio(song_dir)
    voice = decode(isolate_vocals(src, song_dir / "work" / "vocals_full.wav"))
    hooks = find_hooks(decode(src), voice, seconds)
    best = hooks[0]
    print(f"main part: {clock(best.start)} - {clock(best.end)} ({best.end - best.start:.1f} s), "
          f"score {best.score:.2f}")
    for k, h in enumerate(hooks[1:], 2):
        print(f"choice {k}: {clock(h.start)} - {clock(h.end)} ({h.end - h.start:.1f} s), "
              f"score {h.score:.2f}")
    chosen = hooks[min(pick, len(hooks)) - 1]
    write_clip(src, chosen, song_dir / PREVIEW, preview=True)
    print(f"preview (choice {pick}): {song_dir / PREVIEW}")
    if not cut:
        print(f"next: hook {song_dir} --cut" + (f" --pick {pick}" if pick != 1 else ""))
        return 0
    if src.stem == "audio":   # keep the full song beside the clip
        full = src.with_name("full" + src.suffix)
        src.rename(full)
        src = full
    other = [p.name for p in song_dir.glob("audio.*") if p.suffix.lower() != ".wav"]
    if other:   # only our own audio.wav is ever replaced
        raise FileExistsError(f"{song_dir}: {', '.join(other)} is in the way of the cut; move it out")
    write_clip(src, chosen, song_dir / "audio.wav", preview=False)
    print(f"cut: {song_dir / 'audio.wav'} ({clock(chosen.start)} - {clock(chosen.end)}); "
          f"full song kept as {src.name}. Next: lyrics.txt with only these lines, then make")
    return 0
