"""A theme's frame on its background (spec 17): the look draws the background frame, and the
overlay is laid over it exactly as it is (same alpha, same colours), so the text is never redrawn
(red line 2). Also the legibility log (the lit text against the background around it, at least
3:1) and the finished short's output check.

A look whose frames do not depend on each other (`Scene.in_order` False) is drawn a few frames
ahead in worker processes, each with its own copy of the scene; the frames are the same bytes as
drawn in this process."""
from __future__ import annotations

import itertools
import os
import time
from collections import deque
from concurrent.futures import ProcessPoolExecutor
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable, Iterator

import numpy as np
from PIL import Image

from . import LYRIC_AREA, build_scene, paint

MIN_CONTRAST = 3.0   # WCAG AA for large text; the lyrics are 56-110 px
NEAR = 24            # legibility is measured this far around the text
INK = 16             # alpha that counts as drawn (the render checks' SAFE_ALPHA_MIN)
GAP = 200            # text this far apart is two blocks, measured apart (the title card, the lyrics)
WORKERS = int(os.environ.get("LYRIC_ENGINE_WORKERS",   # leave room for the theme and ffmpeg
                             max(1, min(4, (os.cpu_count() or 2) - 2))))


@dataclass
class Legibility:
    """Contrast of the text against the bright end of the background around it, per frame."""
    worst: tuple[int, float] | None = None
    failed: list[tuple[int, float]] = field(default_factory=list)
    draw_s: float = 0.0
    frames: int = 0

    def note(self, k: int, c: float) -> None:
        if self.worst is None or c < self.worst[1]:
            self.worst = (k, c)
        if c < MIN_CONTRAST:
            self.failed.append((k, c))


def ink_box(alpha: np.ndarray, least: int = INK) -> tuple[int, int, int, int] | None:
    """The bbox (x0, y0, x1, y1) of pixels with alpha >= least, or None."""
    ink = alpha >= least
    rows, cols = np.flatnonzero(ink.any(axis=1)), np.flatnonzero(ink.any(axis=0))
    if rows.size == 0:
        return None
    return int(cols[0]), int(rows[0]), int(cols[-1]) + 1, int(rows[-1]) + 1


def ink_bands(alpha: np.ndarray, least: int = INK, gap: int = GAP) -> list[tuple[int, int, int, int]]:
    """Each block of text on its own: rows of ink split where more than `gap` rows are empty, so
    the title card and the lyrics below it are two boxes, not one box over the frame between."""
    ink = alpha >= least
    rows = np.flatnonzero(ink.any(axis=1))
    if rows.size == 0:
        return []
    cuts = np.flatnonzero(np.diff(rows) > gap)
    boxes = []
    for a, b in zip(np.r_[0, cuts + 1], np.r_[cuts, rows.size - 1]):
        cols = np.flatnonzero(ink[rows[a]:rows[b] + 1].any(axis=0))
        boxes.append((int(cols[0]), int(rows[a]), int(cols[-1]) + 1, int(rows[b]) + 1))
    return boxes


def frame_contrast(bg: np.ndarray, text_rgb, box: tuple[int, int, int, int]) -> float:
    """Contrast of the theme's text colour with the 99th-percentile luminance of the background
    (uint8 sRGB) around the text: its ink box grown by NEAR px, inside the lyric area."""
    x0, y0 = max(box[0] - NEAR, LYRIC_AREA[0]), max(box[1] - NEAR, LYRIC_AREA[1])
    x1, y1 = min(box[2] + NEAR, LYRIC_AREA[2]), min(box[3] + NEAR, LYRIC_AREA[3])
    if x1 <= x0 or y1 <= y0:
        return float("inf")
    region = bg[y0:y1:2, x0:x1:2].astype(np.float32) / 255.0
    y = float(np.percentile(paint.luminance(region), 99))
    text = float(paint.luminance(np.asarray(text_rgb, np.float32) / 255.0))
    return paint.contrast(text, y)


def compose_frame(overlay: bytes, scene, k: int, text_rgb, log: Legibility, bg=None, ink=None) -> bytes:
    """The finished frame k as RGBA bytes (alpha 255): the look's background (told where the text
    is this frame, unless `bg` is already drawn; `ink` if already found) with the overlay laid over
    it as it is."""
    h, w = paint.H, paint.W
    alpha = np.frombuffer(overlay, np.uint8).reshape(h, w, 4)[..., 3]
    if ink is None:
        ink = ink_box(alpha)
    if bg is None:
        bg = scene.frame(k, ink)
    if ink:   # each block of text against the background around it (title card, lyrics)
        log.note(k, min(frame_contrast(bg, text_rgb, b) for b in ink_bands(alpha)))
    im = Image.fromarray(bg, "RGB").convert("RGBA")
    im.alpha_composite(Image.frombuffer("RGBA", (w, h), overlay, "raw", "RGBA", 0, 1))
    return im.tobytes()


_scene = None   # a worker's own scene


def _start(bg: tuple[str, str], facts) -> None:
    global _scene
    _scene = build_scene(bg, facts)


def _draw(k: int, ink=None) -> np.ndarray:
    return _scene.frame(k, ink)


def drawn_ahead(bg: tuple[str, str], facts, workers: int = WORKERS) -> Iterator[np.ndarray]:
    """The look's frames 0..n-1 in order (no text over them), drawn `workers` at a time in other
    processes, at most two per worker ahead of the reader (a frame is 6 MB)."""
    pool = ProcessPoolExecutor(workers, initializer=_start, initargs=(bg, facts))
    try:
        todo = iter(range(facts.n))
        ahead = deque(pool.submit(_draw, k) for k in itertools.islice(todo, 2 * workers))
        while ahead:
            frame = ahead.popleft().result()
            ahead.extend(pool.submit(_draw, k) for k in itertools.islice(todo, 1))
            yield frame
    finally:
        pool.shutdown(cancel_futures=True)


def with_background(frames: Iterable, scene, theme, log: Legibility, bg=None) -> Iterator[list]:
    """The theme's frames, each followed by its finished frame: the overlay's pieces go on to
    ffmpeg exactly as they came (spec AC3), stacked above the finished frame. With `bg` (the
    look's name) and a look that can be drawn out of order, the backgrounds are drawn in worker
    processes, a few frames ahead; each worker is told where the text is on its frame."""
    if bg is None or scene.in_order:
        for k, parts in enumerate(frames):
            pieces = list(parts)
            t0 = time.perf_counter()
            final = compose_frame(b"".join(pieces), scene, k, theme.text_rgb, log)
            log.draw_s += time.perf_counter() - t0
            log.frames += 1
            yield [*pieces, final]
        return
    h, w = paint.H, paint.W
    pool = ProcessPoolExecutor(WORKERS, initializer=_start, initargs=(bg, scene.facts))
    source = enumerate(frames)
    ahead: deque = deque()

    def pull() -> None:
        for k, parts in source:
            pieces = list(parts)
            overlay = b"".join(pieces)
            ink = ink_box(np.frombuffer(overlay, np.uint8).reshape(h, w, 4)[..., 3])
            ahead.append((k, pieces, overlay, ink, pool.submit(_draw, k, ink)))
            return

    try:
        for _ in range(2 * WORKERS):
            pull()
        while ahead:
            k, pieces, overlay, ink, future = ahead.popleft()
            pull()
            t0 = time.perf_counter()
            final = compose_frame(overlay, scene, k, theme.text_rgb, log, bg=future.result(), ink=ink)
            log.draw_s += time.perf_counter() - t0
            log.frames += 1
            yield [*pieces, final]
    finally:
        pool.shutdown(cancel_futures=True)


def final_checks(path: Path, n: int, theme, log: Legibility) -> list[str]:
    """ffprobe of the finished short (H.264 yuv420p, size, rate, every frame, audio), then the
    legibility log."""
    from ..render.check import _probe, _video_failures   # here: render imports this package
    info = _probe(path, count=True)
    fails = _video_failures(path.name, info, (theme.width, theme.height), theme.fps, n, audio=True)
    if "error" not in info and (info.get("codec") != "h264" or info["pix_fmt"] != "yuv420p"):
        fails.append(f"{path.name}: {info.get('codec')} {info['pix_fmt']}, expected h264 yuv420p")
    if log.failed:
        k, c = log.failed[0]
        fails.append(f"legibility: {len(log.failed)} frame(s) below {MIN_CONTRAST:g}:1 around the "
                     f"text; first: frame {k} ({c:.2f}:1)")
    return fails
