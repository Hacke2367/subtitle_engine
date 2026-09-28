"""Phonk Neon motion: spec docs/specs/13_phonk_neon_theme.md, plan *_impl.md.

One lyric line at a time, shown ahead as an unlit tube (Beat Pop's plan, ahead=True). Each word
flickers on from its own reveal frame and stays lit (H-020); the lit words' glow pulses on every
beat, and the line splits red / cyan and shakes on each owner-written drop. Word frames come only
from timeline.word_plans (red line 1): beats and drops change glow, split and position, never
when a word lights. Every drawn string goes through frames.checked_mask (red line 2).
"""
from __future__ import annotations

from bisect import bisect_right

from PIL import Image, ImageChops, ImageFilter

from ..layout import word_fonts, word_mask
from ..theme import Theme
from .beatpop import PopLine, Show, accent
from .frames import LEVELS, _scaled, _solid, band_parts, checked_mask
from .karaoke import ease_in_quad, ease_out_cubic, sprite_pad, stroke_px, transformed
from .timeline import WordPlan, _ceil_frame

# Neon ignition, one step per frame from the reveal frame: full on the first (the light check
# reads it), then dips; cut to the word's span, so it is lit at rest by its end frame (plan §2.2)
FLICKER = (1.0, 0.2, 1.0, 0.5, 1.0)

PSprites = dict[int, tuple[Image.Image, Image.Image, Image.Image, int]]
# word index -> (rim, glow, glyph: "L" masks, one colour each; pad)


class NeonCache:
    """The visible line's rim layer and canvas origin, word cores per light level, the layers
    for the last light levels, the last image and the last drawn layer. Dropped when the visible
    line changes (one line at a time)."""

    def __init__(self) -> None:
        self.line: int | None = None
        self.rim: tuple[Image.Image, int, int] | None = None
        self.cores: dict[tuple[int, float], Image.Image] = {}
        self.lit: tuple[tuple, Image.Image, Image.Image, Image.Image] | None = None
        self.image: tuple[tuple, Image.Image] | None = None
        self.layer: tuple[tuple, Image.Image, tuple[int, int]] | None = None


# --- Timeline ----------------------------------------------------------------------------------
def word_level(wp: WordPlan, n: int) -> float:
    """A word's light at frame n while its line shows: 0 unlit, 1 lit (plan §2.2). An untimed
    word is never lit."""
    if wp.reveal is None or n < wp.reveal:
        return 0.0
    k = n - wp.reveal
    return FLICKER[k] if k < min(len(FLICKER), wp.end - wp.reveal) else 1.0


def _since(frames: list[int], n: int) -> int | None:
    i = bisect_right(frames, n) - 1
    return None if i < 0 else n - frames[i]


def pulse(show: Show, n: int, theme: Theme) -> float:
    """Glow strength at frame n: 1.0 on a beat frame, easing back to pulse_low (plan §2.3)."""
    D = max(1, _ceil_frame(theme.pulse_s, theme.fps))
    d = _since(show.beats, n)
    x = 0.0 if d is None or d >= D else (1 - d / D) ** 2
    return round((theme.pulse_low + (1 - theme.pulse_low) * x) * LEVELS) / LEVELS


def split(show: Show, n: int, theme: Theme) -> int:
    """Drop split at frame n, px: split_px on a drop frame, closing to 0 (plan §2.3)."""
    S = max(1, _ceil_frame(theme.split_s, theme.fps))
    d = _since(show.drops, n)
    return 0 if d is None or d >= S else round(theme.split_px * (1 - d / S) ** 2)


def line_state(show: Show, pl: PopLine, n: int, theme: Theme) -> tuple[float, int, int, float]:
    """(scale, dx, dy, opacity) of the line at frame n; opacity 0 when it is not on screen. The
    drop's punch and shake come from beatpop.accent (bump_scale 1: beats never scale)."""
    if not pl.enter <= n < pl.stop:
        return 1.0, 0, 0, 0.0
    scale, dx, dy = accent(show, n, theme)
    if n < pl.rest:
        return scale, dx, dy, ease_out_cubic((n - pl.enter) / (pl.rest - pl.enter))
    if n < pl.leave:
        return scale, dx, dy, 1.0
    return scale, dx, dy, 1.0 - ease_in_quad((n - pl.leave) / max(1, pl.stop - pl.leave))


def readable(show: Show, pl: PopLine, m: int, theme: Theme) -> bool:
    """Whether the check can read line pl on frame m: at rest, unshaken, and alone."""
    return (pl.rest <= m < pl.leave and accent(show, m, theme) == (1.0, 0, 0)
            and not any(o is not pl and o.enter <= m < o.stop for o in show.lines))


# --- Sprites -----------------------------------------------------------------------------------
def pad_px(theme: Theme) -> int:
    """One pad for every sprite: the wide glow's blur, the rim, and the split's shift."""
    return max(3 * theme.glow_radius, sprite_pad(theme), theme.split_px)


def glow_mask(glyph: Image.Image, theme: Theme) -> Image.Image:
    """A wide bloom and a tight one, screened: a saturated edge with a soft reach (plan §2.5)."""
    wide = _scaled(glyph.filter(ImageFilter.GaussianBlur(theme.glow_radius)), theme.glow_boost)
    tight = _scaled(glyph.filter(ImageFilter.GaussianBlur(max(1, theme.glow_radius // 3))),
                    theme.glow_boost)
    return ImageChops.screen(wide, tight)


def build_sprites(show: Show, theme: Theme) -> PSprites:
    """Per word: dark rim (its stroke outline, softened), glow and glyph masks, coloured at
    draw time."""
    pad, sprites = pad_px(theme), {}
    for pl in show.lines:
        for wp in pl.words:
            fonts = word_fonts(theme, pl.layout.font_size, wp.box.emphasis)
            glyph = checked_mask(wp.text, wp.box, fonts, pad)
            outline = word_mask(wp.text, fonts, pad, stroke=stroke_px(theme, fonts.size))
            rim = Image.new("L", glyph.size, 0)
            rim.paste(_scaled(outline.filter(ImageFilter.GaussianBlur(theme.shadow_radius)),
                              theme.shadow_alpha), theme.shadow_offset)
            sprites[wp.box.index] = (rim, glow_mask(glyph, theme), glyph, pad)
    return sprites


# --- Frames ------------------------------------------------------------------------------------
def _spot(wp: WordPlan, pad: int, x0: int, y0: int) -> tuple[int, int]:
    return wp.box.x - pad - x0, wp.box.y - pad - y0


def _lighter(canvas: Image.Image, mask: Image.Image, at: tuple[int, int]) -> None:
    box = (*at, at[0] + mask.width, at[1] + mask.height)
    canvas.paste(ImageChops.lighter(canvas.crop(box), mask), box)


def _rim(pl: PopLine, sprites: PSprites, theme: Theme,
          cache: NeonCache) -> tuple[Image.Image, int, int]:
    """The line's rim layer (every word, lit or not) and its canvas origin on the frame."""
    if cache.rim is None:
        pad = sprites[pl.words[0].box.index][3]
        x0 = min(wp.box.x for wp in pl.words) - pad
        y0 = min(wp.box.y for wp in pl.words) - pad
        x1 = max(wp.box.x + wp.box.w for wp in pl.words) + pad
        y1 = max(wp.box.y + wp.box.h for wp in pl.words) + pad
        mask = Image.new("L", (x1 - x0, y1 - y0), 0)
        for wp in pl.words:
            _lighter(mask, sprites[wp.box.index][0], _spot(wp, pad, x0, y0))
        cache.rim = (_solid(theme.shadow_rgb, mask), x0, y0)
    return cache.rim


def _lit(pl: PopLine, sprites: PSprites, levels: tuple[float, ...], theme: Theme,
         cache: NeonCache) -> tuple[Image.Image, Image.Image, Image.Image]:
    """For these light levels: the glow mask (each lit word's glow × its level), the cores (each
    word's glyph from unlit_rgb to text_rgb by its level) and the cores' alpha."""
    if cache.lit is not None and cache.lit[0] == levels:
        return cache.lit[1], cache.lit[2], cache.lit[3]
    rim, x0, y0 = cache.rim
    glow = Image.new("L", rim.size, 0)
    cores = Image.new("RGBA", rim.size, (0, 0, 0, 0))
    for wp, level in zip(pl.words, levels):
        _, wglow, glyph, pad = sprites[wp.box.index]
        at = _spot(wp, pad, x0, y0)
        if level > 0:
            _lighter(glow, _scaled(wglow, level), at)
        core = cache.cores.get((wp.box.index, level))
        if core is None:
            rgb = tuple(round(u + (t - u) * level) for u, t in zip(theme.unlit_rgb, theme.text_rgb))
            core = cache.cores[wp.box.index, level] = _solid(rgb, glyph)
        cores.alpha_composite(core, dest=at)
    cache.lit = (levels, glow, cores, cores.getchannel("A"))
    return glow, cores, cache.lit[3]


def line_image(pl: PopLine, sprites: PSprites, show: Show, n: int, theme: Theme,
               cache: NeonCache) -> tuple[Image.Image, int, int]:
    """The line at frame n on one canvas, and its top-left on the frame: glow × pulse, the dark
    rim (legible on bright footage), the red and cyan copies of the cores shifted by the split,
    then the cores (plan §2.6)."""
    rim, x0, y0 = _rim(pl, sprites, theme, cache)
    levels = tuple(word_level(wp, n) for wp in pl.words)
    key = (levels, pulse(show, n, theme) if any(levels) else 0.0, split(show, n, theme))
    if cache.image is None or cache.image[0] != key:
        glow, cores, alpha = _lit(pl, sprites, levels, theme, cache)
        img = Image.new("RGBA", rim.size, (0, 0, 0, 0))
        if key[1] > 0:
            img.alpha_composite(_solid(theme.glow_rgb, _scaled(glow, key[1])))
        img.alpha_composite(rim)
        if s := key[2]:
            img.alpha_composite(_solid(theme.split_left_rgb, alpha), source=(s, 0))
            img.alpha_composite(_solid(theme.split_right_rgb, alpha), dest=(s, 0))
        img.alpha_composite(cores)
        cache.image = (key, img)
    return cache.image[1], x0, y0


def frame_parts(n: int, show: Show, sprites: PSprites, theme: Theme, cache: NeonCache) -> list:
    """Frame n as bytes-like pieces (frames.band_parts): the one visible line, shaken and faded
    while it enters and leaves."""
    pl = next((pl for pl in show.lines if pl.enter <= n < pl.stop), None)
    if pl is None:
        return band_parts([], theme)
    if cache.line != pl.layout.line:
        cache.__init__()
        cache.line = pl.layout.line
    scale, dx, dy, opacity = line_state(show, pl, n, theme)
    level = min(LEVELS, round(opacity * LEVELS))
    if level <= 0:
        return band_parts([], theme)
    img, x0, y0 = line_image(pl, sprites, show, n, theme, cache)
    lkey = (cache.image[0], scale, dx, dy, level)
    if cache.layer is None or cache.layer[0] != lkey:
        layer, pos = transformed(img, x0, y0, pl.layout, scale, dy, level, theme, dx=dx)
        cache.layer = (lkey, layer, pos)
    return band_parts([(cache.layer[1], cache.layer[2])], theme)
