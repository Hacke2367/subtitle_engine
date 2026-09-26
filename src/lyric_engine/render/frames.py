"""Sprites (text + shadow, glow blurred once per word) and frame compositing, straight alpha."""
from __future__ import annotations

from functools import lru_cache

from PIL import Image, ImageFilter

from .. import layout
from ..theme import Theme
from .timeline import LinePlan, line_opacity, word_state

LEVELS = 32   # faded sprite copies are cached at 1/32 opacity steps


# --- Sprites and frames ----------------------------------------------------------------------
def _solid(rgb: tuple[int, int, int], alpha: Image.Image) -> Image.Image:
    # Solid colour + separate alpha = straight alpha with no dark edge pixels (step 01 fix).
    layer = Image.new("RGBA", alpha.size, (*rgb, 255))
    layer.putalpha(alpha)
    return layer


def _scaled(mask: Image.Image, k: float) -> Image.Image:
    return mask.point([min(255, round(v * k)) for v in range(256)])


Sprites = dict[int, tuple[Image.Image, Image.Image, int]]   # word index -> (text, glow, pad)


def build_sprites(lines: list[LinePlan], theme: Theme) -> Sprites:
    """Per word index: (text sprite, glow sprite, pad). Both are the word's mask padded by pad,
    drawn at (box.x − pad, box.y − pad). The blurs happen here, once per word."""
    pad = 3 * theme.glow_radius
    sprites = {}
    for lp in lines:
        fonts = None
        for wp in lp.words:
            box = wp.box
            if wp.text != box.text:   # red line 2, checked where the string is drawn
                raise AssertionError(f"word {box.index}: layout text {box.text!r} is not the "
                                     f"words.json text {wp.text!r}")
            if fonts is None:
                fonts = layout.font_set(theme, lp.layout.font_size)
            mask = layout.word_mask(wp.text, fonts, pad)
            if mask.size != (box.w + 2 * pad, box.h + 2 * pad):   # measured mask == drawn mask
                raise AssertionError(f"word {box.index} {wp.text!r}: drawn mask {mask.size} does "
                                     f"not match its layout box {box.w}x{box.h} + pad {pad}")
            blurred = mask.filter(ImageFilter.GaussianBlur(theme.shadow_radius))
            shadow = Image.new("L", mask.size, 0)
            shadow.paste(_scaled(blurred, theme.shadow_alpha), theme.shadow_offset)
            text = Image.alpha_composite(_solid(theme.shadow_rgb, shadow),
                                         _solid(theme.text_rgb, mask))
            halo = _scaled(mask.filter(ImageFilter.GaussianBlur(theme.glow_radius)),
                           theme.glow_boost)
            sprites[box.index] = (text, _solid(theme.glow_rgb, halo), pad)
    return sprites


_LUTS = [[(v * k + LEVELS // 2) // LEVELS for v in range(256)] for k in range(LEVELS + 1)]


class FadeCache:
    """Faded sprite copies of the line on screen, keyed (word, kind, level). Dropped when the
    visible line changes, so memory stays at one line's worth."""

    def __init__(self) -> None:
        self.line: LinePlan | None = None
        self.images: dict[tuple[int, str, int], Image.Image] = {}

    def faded(self, sprite: Image.Image, level: int, key: tuple[int, str, int]) -> Image.Image:
        if level >= LEVELS:
            return sprite
        img = self.images.get(key)
        if img is None:
            img = sprite.copy()
            img.putalpha(sprite.getchannel("A").point(_LUTS[level]))
            self.images[key] = img
        return img


@lru_cache(maxsize=2)
def _zero_frame(width: int, height: int) -> bytes:
    return bytes(width * height * 4)


def _frame_parts(n: int, lines: list[LinePlan], sprites: Sprites, theme: Theme,
                 cache: FadeCache | None = None) -> list:
    """Frame n as bytes-like pieces: the zero frame above and below, the drawn rows between.
    Streaming the pieces avoids building a full 8 MB frame per frame."""
    zero = _zero_frame(theme.width, theme.height)
    lp = next((lp for lp in lines if lp.first <= n < lp.stop), None)
    line_op = line_opacity(lp, n) if lp else 0.0
    if line_op <= 0:
        return [zero]
    if cache is None:
        cache = FadeCache()
    elif cache.line is not lp:
        cache.line, cache.images = lp, {}
    glows, texts = [], []
    for wp in lp.words:
        opacity, rise, glow = word_state(wp, n, theme)
        text_img, glow_img, pad = sprites[wp.box.index]
        # A revealing word starts rise px below its resting place and settles upwards.
        pos = (wp.box.x - pad, wp.box.y - pad + round(rise))
        for out, kind, img, f in ((glows, "glow", glow_img, glow),
                                  (texts, "text", text_img, opacity)):
            level = min(LEVELS, round(f * line_op * LEVELS))
            if level > 0:
                out.append((cache.faded(img, level, (wp.box.index, kind, level)), pos))
    layers = glows + texts   # every glow under every text: no glow tints a neighbour's letters
    if not layers:
        return [zero]
    top = max(0, min(y for _, (_, y) in layers))
    bottom = min(theme.height, max(y + img.height for img, (_, y) in layers))
    if top >= bottom:
        return [zero]
    band = Image.new("RGBA", (theme.width, bottom - top), (0, 0, 0, 0))
    for img, (x, y) in layers:
        band.alpha_composite(img, dest=(x, y - top))
    row, view = theme.width * 4, memoryview(zero)
    return [view[:top * row], band.tobytes(), view[bottom * row:]]


def compose_frame(n: int, lines: list[LinePlan], sprites: Sprites, theme: Theme,
                  cache: FadeCache | None = None) -> bytes:
    """Frame n as RGBA bytes (the shared all-zero frame when nothing is visible)."""
    parts = _frame_parts(n, lines, sprites, theme, cache)
    return parts[0] if len(parts) == 1 else b"".join(parts)
