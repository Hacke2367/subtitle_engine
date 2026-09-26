"""Workflow commands: `clip` a portion of an aligned song into a new song folder, and make sure a
song folder is aligned before rendering (`make`).

The cut is chosen from line spans the aligner produced for the full song; the clip is then
re-aligned on its own audio. No word time is created or copied (red line 1), and the clip's
lyrics are the source lines verbatim (red line 2). Spec docs/specs/05_workflow_clip_make.md.
"""
from __future__ import annotations

import json
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

from . import align, timing

PRE_PAD_S = 0.3     # at most this much audio before the first selected word, when snapping
POST_PAD_S = 1.0    # at most this much after the last one (the line holds on screen meanwhile)
LONG_EDGE_S = 3.0   # warn when the clip keeps more than this before the first / after the last word


class ClipError(ValueError):
    """The requested clip cannot be cut cleanly; the message says why and what to do."""


@dataclass
class ClipPlan:
    start: float
    end: float
    lines: list[int]          # selected lyric line indexes of the source, in order
    warnings: list[str]


def line_spans(doc: dict) -> dict[int, tuple[float, float] | None]:
    """Per lyric line: (first start, last end) when every word is timed and unflagged, else None."""
    by_line: dict[int, list[dict]] = {}
    for w in doc["words"]:
        by_line.setdefault(w["line"], []).append(w)
    spans = {}
    for line, words in by_line.items():
        trusted = all(w["start"] is not None and w["end"] is not None and not w["flagged"]
                      for w in words)
        spans[line] = (min(w["start"] for w in words), max(w["end"] for w in words)) if trusted else None
    return spans


def plan_clip(doc: dict, a: float, b: float, duration: float) -> ClipPlan:
    """Lines lying entirely inside [a, b], and a cut that never splits a line (spec §4)."""
    if a < 0 or a >= b:
        raise ClipError(f"--from must be >= 0 and before --to (got {a:g} to {b:g} s)")
    if a >= duration:
        raise ClipError(f"--from {a:g} s is past the end of the song ({duration:.1f} s)")
    b = min(b, duration)
    spans = line_spans(doc)
    inside = [n for n, s in sorted(spans.items()) if s and a <= s[0] and s[1] <= b]
    if not inside:
        near = [f"line {n + 1} ({s[0]:.1f}-{s[1]:.1f} s)" for n, s in sorted(spans.items())
                if s and s[1] > a - 5 and s[0] < b + 5]
        raise ClipError(f"no whole lyric line lies inside {a:g}-{b:g} s"
                        + (f"; nearby: {', '.join(near)}" if near else ""))
    first, last = inside[0], inside[-1]
    for n in range(first, last + 1):   # a gap in the selection would drop a sung line
        if n in spans and n not in inside:
            why = ("has a flagged or untimed word; fix it in the full song's words.json first"
                   if spans[n] is None else "is not inside the range")
            raise ClipError(f"line {n + 1} (between the selected lines) {why}")
    before = max((n for n in spans if n < first), default=None)   # nearest lyric lines outside,
    after = min((n for n in spans if n > last), default=None)     # skipping blank stanza lines
    for n, where in ((before, "before"), (after, "after")):
        if n is not None and spans[n] is None:
            raise ClipError(f"line {n + 1} (just {where} the clip) has a flagged or untimed word, "
                            "so the cut can't be checked against it; fix it in words.json first")

    first_start, last_end = spans[first][0], spans[last][1]
    prev_end = max((s[1] for n, s in spans.items() if s and n < first), default=0.0)
    next_start = min((s[0] for n, s in spans.items() if s and n > last), default=duration)
    # Keep the owner's edge when it falls in the gap next to the selection (an intro can stay);
    # otherwise a neighbouring line crosses it, so cut inside the gap instead.
    start = a if a >= prev_end else first_start - min(PRE_PAD_S, (first_start - prev_end) / 2)
    end = b if b <= next_start else last_end + min(POST_PAD_S, (next_start - last_end) / 2)
    start, end = max(0.0, start), min(duration, end)
    warnings = []
    if first_start - start > LONG_EDGE_S:
        warnings.append(f"{first_start - start:.1f} s of audio before the first lyric word: any "
                        "singing there that is not in lyrics.txt will confuse alignment")
    if end - last_end > LONG_EDGE_S:
        warnings.append(f"{end - last_end:.1f} s of audio after the last lyric word: same caveat")
    return ClipPlan(round(start, 3), round(end, 3), inside, warnings)


def clip_song(source: Path, a: float, b: float, out: Path) -> ClipPlan:
    """Cut [a, b] of an aligned song into a new song folder: audio.wav, lyrics.txt, clip.json."""
    audio, lyrics_path = align.song_paths(source)
    words_path = source / "words.json"
    if not words_path.exists():
        raise ClipError(f"{source} has no words.json; run `align {source}` first")
    try:
        doc = timing.load_words(words_path)
    except ValueError as exc:
        raise ClipError(f"{words_path} is not valid JSON: {exc}") from None
    errors = timing.validate(doc, lyrics_path, audio)
    if errors:
        raise ClipError(f"{words_path} cannot be used ({errors[0]}); "
                        f"run `align {source} --overwrite` if the lyrics or audio changed")
    if out.exists():
        raise ClipError(f"{out} already exists; choose another --out (nothing is overwritten)")
    plan = plan_clip(doc, a, b, align.probe_duration(audio))

    out.mkdir(parents=True)
    proc = subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-i", str(audio),
                           "-ss", f"{plan.start:.3f}", "-to", f"{plan.end:.3f}",
                           "-c:a", "pcm_s16le", str(out / "audio.wav")],
                          capture_output=True, text=True)
    if proc.returncode != 0:
        shutil.rmtree(out)   # our own fresh folder: leave nothing half-made
        raise ClipError(f"ffmpeg could not cut the audio: {proc.stderr.strip()[-300:]}")
    try:   # from lyrics.txt, not words.json: its lines keep the *emphasis* markers (H-009)
        source_lines = timing.read_lyrics(lyrics_path).lines
    except timing.LyricsError as exc:
        shutil.rmtree(out)
        raise ClipError(str(exc)) from None
    lines = source_lines[plan.lines[0]:plan.lines[-1] + 1]   # verbatim, stanza breaks kept
    (out / "lyrics.txt").write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    (out / "clip.json").write_text(json.dumps({
        "source": str(source), "requested": [a, b], "start_s": plan.start, "end_s": plan.end,
        "lines": [n + 1 for n in plan.lines], "warnings": plan.warnings}, indent=2) + "\n",
        encoding="utf-8", newline="\n")
    return plan


def ensure_aligned(song_dir: Path) -> int:
    """make's first half: align when there is no words.json; keep a valid one (it may hold the
    owner's hand corrections); refuse a stale or invalid one. Returns an exit code."""
    words_path = song_dir / "words.json"
    if not words_path.exists():
        return align.align_song(song_dir)
    audio, lyrics_path = align.song_paths(song_dir)
    try:
        errors = timing.validate(timing.load_words(words_path), lyrics_path, audio)
    except ValueError as exc:
        errors = [f"not valid JSON: {exc}"]
    if errors:
        print(f"error: {words_path} cannot be used:\n  " + "\n  ".join(errors)
              + f"\nIf the lyrics or audio changed, run `align {song_dir} --overwrite`.",
              file=sys.stderr)
        return 2
    print(f"{words_path}: using the existing alignment (hand corrections kept)")
    return 0
