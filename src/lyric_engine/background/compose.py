"""A theme's frame on its background (spec 17 §4.4): the lyrics' ink casts a shadow by blocking
part of each light, and its colours take a bounded tint of that light. The overlay's alpha is used
as it is, so the text is never redrawn (red line 2). Also the legibility log (§4.5) and the
finished short's output check."""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable, Iterator

import numpy as np
from PIL import Image, ImageChops
from scipy import ndimage

from . import LYRIC_AREA, paint

MIN_CONTRAST = 3.0   # WCAG AA for large text; the lyrics are 56-110 px (spec 4.5)
NEAR = 24            # legibility is measured this far around the text
INK = 16             # alpha that counts as drawn (the render checks' SAFE_ALPHA_MIN)


@dataclass
class Legibility:
    """Contrast of the lit text against the background's bright end in the lyric area, per frame."""
    worst: tuple[int, float] | None = None
    failed: list[tuple[int, float]] = field(default_factory=list)
    draw_s: float = 0.0
    frames: int = 0

    def note(self, k: int, c: float) -> None:
        if self.worst is None or c < self.worst[1]:
            self.worst = (k, c)
        if c < MIN_CONTRAST:
            self.failed.append((k, c))


def frame_contrast(scene, light_rgb: np.ndarray, text_rgb, tint: np.ndarray,
                   box: tuple[int, int, int, int]) -> float:
    """Contrast of the theme's text colour (lit) with the 99th-percentile background luminance
    behind the text (its ink box grown by NEAR px, inside the lyric area), before the text's own
    shadows: the worst case."""
    x0, y0, x1, y1 = (max(box[0] - NEAR, LYRIC_AREA[0]), max(box[1] - NEAR, LYRIC_AREA[1]),
                      min(box[2] + NEAR, LYRIC_AREA[2]), min(box[3] + NEAR, LYRIC_AREA[3]))
    if x1 <= x0 or y1 <= y0:
        return float("inf")
    hs = (slice(y0 // 2, max(y0 // 2 + 1, y1 // 2)), slice(x0 // 2, max(x0 // 2 + 1, x1 // 2)))
    region = scene.albedo_half[hs] * light_rgb[hs]
    y = float(np.percentile(paint.luminance(region), 99))
    text = float(paint.luminance(np.asarray(text_rgb, np.float32) / 255.0 * tint))
    return paint.contrast(text, y)


def _ink_box(alpha: np.ndarray, least: int) -> tuple[int, int, int, int] | None:
    """The bbox (x0, y0, x1, y1) of pixels with alpha >= least, or None."""
    ink = alpha >= least
    rows, cols = np.flatnonzero(ink.any(axis=1)), np.flatnonzero(ink.any(axis=0))
    if rows.size == 0:
        return None
    return int(cols[0]), int(rows[0]), int(cols[-1]) + 1, int(rows[-1]) + 1


def _grow(box: tuple, margin: int, w: int, h: int) -> tuple[int, int, int, int]:
    """box grown by margin, clamped to the frame, on even edges (for the half-size light)."""
    return (max(0, box[0] - margin) & ~1, max(0, box[1] - margin) & ~1,
            min(w, box[2] + margin + 1) & ~1, min(h, box[3] + margin + 1) & ~1)


def compose_frame(overlay: bytes, scene, k: int, text_rgb, log: Legibility) -> bytes:
    """The finished frame k as RGBA bytes (alpha 255): the background lit by scene.light(k), the
    lyrics' shadows cut out of each light, the overlay laid over it with its colours tinted."""
    w, h = scene.size
    ov = np.frombuffer(overlay, np.uint8).reshape(h, w, 4)
    L = scene.light(k)
    light = (L.sun + L.air)[..., None] * L.sun_rgb
    light += L.ambient
    if L.lamp is not None:
        light += L.lamp[..., None] * L.lamp_rgb
    alpha = ov[..., 3]
    drawn = _ink_box(alpha, 1)   # everything the overlay draws: composed below as it is
    ink = _ink_box(alpha, INK) if drawn else None
    if ink:
        log.note(k, frame_contrast(scene, light, text_rgb, L.tint, ink))
    shadows = [(L.sun, L.sun_rgb, L.sun_shadow)]
    if L.lamp is not None:
        shadows.append((L.lamp, L.lamp_rgb, L.lamp_shadow))
    reach = max(abs(v) for _, _, (dx, dy, _) in shadows for v in (dx, dy))
    box = _grow(drawn, int(reach) + 8 * scene.look.shadow_soft + 4, w, h) if drawn else None
    if box:
        x0, y0, x1, y1 = box
        cast0 = paint.down2(alpha[y0:y1, x0:x1].astype(np.float32) / 255.0)
        hs = (slice(y0 // 2, y1 // 2), slice(x0 // 2, x1 // 2))
        for term, rgb, (dx, dy, strength) in shadows:
            cast = ndimage.shift(cast0, (dy / 2, dx / 2), order=1, mode="constant")
            cast = paint.soft(cast, scene.look.shadow_soft) * strength
            light[hs] -= (term[hs] * cast)[..., None] * rgb

    # full size in 8-bit C ops (PIL): the light (clipped at 1: highlights burn out) upscaled,
    # times the albedo
    light *= 255.0
    light += 0.5
    np.clip(light, 0.0, 255.0, out=light)
    half = np.empty((*light.shape[:2], 4), np.uint8)
    half[..., :3] = light
    half[..., 3] = 255
    up = Image.fromarray(half, "RGBA").resize((w, h), Image.BILINEAR)
    bg = ImageChops.multiply(scene.albedo_img, up)
    if L.glow > 0:
        gx0, gy0, glow = scene.glow
        gbox = (gx0, gy0, gx0 + glow.shape[1], gy0 + glow.shape[0])
        g = np.empty((*glow.shape[:2], 4), np.uint8)
        g[..., :3] = np.clip(glow * (255 * L.glow) + 0.5, 0, 255)
        g[..., 3] = 0
        bg.paste(ImageChops.add(bg.crop(gbox), Image.fromarray(g, "RGBA")), gbox)
    if drawn:   # the overlay as it is, only its colours tinted: straight alpha over the room
        region = Image.frombuffer("RGBA", (w, h), overlay, "raw", "RGBA", 0, 1).crop(drawn)
        tint = Image.new("RGBA", region.size, (*(int(round(255 * c)) for c in L.tint), 255))
        bg.alpha_composite(ImageChops.multiply(region, tint), dest=drawn[:2])
    return bg.tobytes()


def with_background(frames: Iterable, scene, theme, log: Legibility) -> Iterator[list]:
    """The theme's frames, each followed by its finished frame: the overlay's pieces go on to
    ffmpeg exactly as they came (spec AC3), stacked above the finished frame."""
    for k, parts in enumerate(frames):
        pieces = list(parts)
        t0 = time.perf_counter()
        final = compose_frame(b"".join(pieces), scene, k, theme.text_rgb, log)
        log.draw_s += time.perf_counter() - t0
        log.frames += 1
        yield [*pieces, final]


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
        fails.append(f"legibility: {len(log.failed)} frame(s) below {MIN_CONTRAST:g}:1 in the "
                     f"lyric area; first: frame {k} ({c:.2f}:1)")
    return fails
