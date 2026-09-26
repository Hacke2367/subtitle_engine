"""Local CPU forced alignment: known lyrics words -> per-word times (torchaudio MMS_FA + CTC).

The words are placed, never transcribed. Each word is normalize()d (timing.py) and spelled in the
model's lowercase Latin alphabet. wav2vec2 emissions of the audio are computed window by window,
so RAM stays bounded, and torchaudio's CTC forced_align places the whole token sequence in order.
A `star` token (matches any audio) before the first word, after the last and, when line indexes
are given, between lines absorbs singing the lyrics don't cover (intro, a repeat that isn't
written out, extra verses), so the words are not stretched over it. Lines stay contiguous.

Returns times only, 1:1 with the input words (red line 2). A word with nothing to align gets no
time (red line 1); nothing is interpolated.

Plan: docs/specs/02_word_alignment_impl.md section 4 (agent L).
"""
from __future__ import annotations

import subprocess
from pathlib import Path

from lyric_engine.timing import RawWord, normalize

MODEL = "torchaudio MMS_FA"      # wav2vec2 CTC aligner: 1,130 languages, romanized (uroman) text
WEIGHTS_FILE = "mms_fa_ctc_alignment_mling_uroman.pt"  # 1.18 GB, own name in the torch.hub cache
SAMPLE_RATE = 16_000
HOP = 320                        # samples per emission frame (the conv stack's total stride)
RECEPTIVE = 400                  # samples one frame sees
FRAME_S = HOP / SAMPLE_RATE      # 0.02 s
WINDOW_S = 30                    # audio per model call (~0.5 GB of activations at 30 s)
CONTEXT_S = 2                    # extra audio on each side of a window, dropped after the model
# MMS_FA's alphabet; index = emission column. Checked against torchaudio when the model loads.
LABELS = ("-", "a", "i", "e", "n", "o", "u", "t", "s", "r", "m", "k", "l", "d", "g", "h", "y",
          "b", "p", "w", "c", "v", "j", "z", "f", "'", "q", "x")
BLANK = 0
STAR = len(LABELS)               # column added by get_model(with_star=True): matches any audio
_TOKEN = {c: i for i, c in enumerate(LABELS) if i != BLANK}


def align(audio: Path, words: list[str], *,
          lines: list[int] | None = None) -> tuple[list[RawWord], dict]:
    """(start, end, score) for each of `words` in `audio`, 1:1. RawWord(None, None, None) = not
    placed. Times are seconds rounded to 3 decimals; score = mean probability of the word's
    tokens (0..1). `lines` (optional, the line index of each word, as in Lyrics.words) adds a
    star between lines; recommended whenever the lyrics may not cover every sung repeat.
    Raises RuntimeError when the audio can't be decoded, the model can't load or run, or the
    audio is too short for the text.
    """
    if lines is not None and len(lines) != len(words):
        raise ValueError(f"{len(lines)} line indexes for {len(words)} words")
    tokens = tokenize(words)
    native = {"model": MODEL, "frame_s": FRAME_S, "window_s": WINDOW_S, "context_s": CONTEXT_S,
              "star": "edges" if lines is None else "edges+lines", "n_frames": 0,
              "n_tokens": sum(map(len, tokens)), "unplaced": sum(1 for t in tokens if not t)}
    if not native["n_tokens"]:
        return [RawWord(None, None, None) for _ in words], native
    emission = _emissions(_decode(Path(audio)))
    native["n_frames"] = int(emission.shape[0])
    return place(emission, tokens, lines), native


def tokenize(words: list[str]) -> list[list[int]]:
    """Token ids per word: normalize(), then the characters the model knows. [] = can't place."""
    return [[_TOKEN[c] for c in normalize(w) if c in _TOKEN] for w in words]


def place(emission, tokens: list[list[int]], lines: list[int] | None = None) -> list[RawWord]:
    """Force-align all non-empty token lists, in order, on `emission` (frames x columns, log-probs;
    the last column is the star). A star goes first, last and, given `lines`, between lines.

    One RawWord per entry of `tokens`; an empty entry is left out of the alignment and gets None.
    """
    import torch
    import torchaudio.functional as F

    flat, previous = [STAR], None
    for word, line in zip(tokens, lines if lines is not None else [0] * len(tokens)):
        if not word:
            continue
        if previous is not None and line != previous:
            flat.append(STAR)
        flat += word
        previous = line
    flat.append(STAR)
    needed = len(flat) + sum(a == b for a, b in zip(flat, flat[1:]))  # CTC: repeats need a blank
    if emission.shape[0] < needed:
        raise RuntimeError(f"audio too short for the lyrics: {emission.shape[0]} frames, "
                           f"{needed} needed")
    path, scores = F.forced_align(emission[None], torch.tensor([flat], dtype=torch.int32),
                                  blank=BLANK)
    spans = [s for s in F.merge_tokens(path[0], scores[0].exp(), blank=BLANK)  # mean probability
             if s.token != STAR]

    raw, k = [], 0
    for word in tokens:
        if not word:
            raw.append(RawWord(None, None, None))
            continue
        mine, k = spans[k:k + len(word)], k + len(word)
        raw.append(RawWord(round(mine[0].start * FRAME_S, 3), round(mine[-1].end * FRAME_S, 3),
                           round(sum(s.score for s in mine) / len(mine), 3)))
    return raw


def _emissions(wave):
    """Log-probabilities (frames, len(LABELS) + 1) of a 16 kHz mono tensor, window by window.

    Window starts are multiples of HOP, so window frame j is global frame start // HOP + j, and
    the concatenation is exactly what one pass over the whole file would index.
    """
    import torch

    n = wave.numel()
    total = (n - RECEPTIVE) // HOP + 1 if n >= RECEPTIVE else 0
    if total <= 0:
        raise RuntimeError("audio too short to align (under 25 ms)")
    model = _load_model()
    win, ctx = WINDOW_S * SAMPLE_RATE, CONTEXT_S * SAMPLE_RATE
    parts = []
    try:
        with torch.inference_mode():
            for start in range(0, n, win):
                keep = min(win // HOP, total - start // HOP)
                if keep <= 0:
                    break
                lo = max(0, start - ctx)
                out, _ = model(wave[lo:min(n, start + win + ctx)][None])
                skip = (start - lo) // HOP
                parts.append(out[0, skip:skip + keep].clone())
    except (RuntimeError, MemoryError) as exc:
        raise RuntimeError(f"{MODEL} failed on the audio; if this is out of memory, close other "
                           f"programs or lower local_aligner.WINDOW_S: {exc}") from exc
    return torch.cat(parts)


def _load_model():
    import torch
    import torch.utils.serialization
    from torchaudio.pipelines import MMS_FA

    if tuple(MMS_FA.get_labels(star=None)) != LABELS:
        raise RuntimeError("torchaudio's MMS_FA alphabet no longer matches local_aligner.LABELS")
    # Memory-map the weights file instead of reading a private copy of it: peak commit drops from
    # ~5.2 GB to ~3.7 GB. Scoped, because other torch.load callers (demucs) may not support mmap.
    load_config = torch.utils.serialization.config.load
    previous, load_config.mmap = load_config.mmap, True
    try:
        return MMS_FA.get_model(with_star=True,
                                dl_kwargs={"file_name": WEIGHTS_FILE, "weights_only": True})
    except Exception as exc:  # network, cache or checkpoint problem
        raise RuntimeError(f"could not load {MODEL} (the first run downloads 1.2 GB into "
                           f"{torch.hub.get_dir()}): {exc}") from exc
    finally:
        load_config.mmap = previous


def _decode(audio: Path):
    """ffmpeg -> mono float32 tensor at 16 kHz, starting at the file's first sample."""
    import torch

    cmd = ["ffmpeg", "-hide_banner", "-nostdin", "-loglevel", "error", "-i", str(audio),
           "-vn", "-ac", "1", "-ar", str(SAMPLE_RATE), "-f", "f32le", "-"]
    try:
        proc = subprocess.run(cmd, capture_output=True)
    except FileNotFoundError as exc:
        raise RuntimeError("ffmpeg not found on PATH") from exc
    if proc.returncode != 0 or not proc.stdout:
        err = proc.stderr.decode("utf-8", errors="replace").strip()[-300:] or "no audio stream"
        raise RuntimeError(f"ffmpeg could not decode {audio.name}: {err}")
    return torch.frombuffer(bytearray(proc.stdout), dtype=torch.float32)
