"""Title card: spec docs/specs/15_title_card.md, plan *_impl.md.

songs/<song>/title.txt (one or two lines, drawn exactly as written) shows at the top of the frame
for the first card_s seconds, in the theme's own font, colours and legibility layer (H-021). The
theme's frame stream passes through `with_card`: frames inside the card's span get the faded card
on top, later frames pass through untouched, and with no title.txt nothing is wrapped at all.
"""
from __future__ import annotations

import math
from collections.abc import Iterable, Iterator
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

from PIL import Image, ImageChops, ImageFilter, ImageStat

from .. import layout
from ..theme import Theme
from .check import _SAFE_LUT, SYNC_ON_MIN, _decode_cmd, _stream
from .encode import RenderError
from .frames import LEVELS, _scaled, _solid
from .karaoke import stroke_px

if TYPE_CHECKING:
    from . import RenderResult

TITLE_FILE = "title.txt"


@dataclass
class Card:
    lines: list[str]
    image: Image.Image            # every layer at full opacity
    pos: tuple[int, int]          # its top-left on the frame
    ink: Image.Image              # 255 where a glyph is solid, the image's size (for the check)
    fade_in: int                  # frames
    stop: int                     # first frame without the card
    fade_out: int
    clashes: list[int] = field(default_factory=list)   # frames with lyric ink under the card
    _faded: dict[int, Image.Image] = field(default_factory=dict)

    def level(self, k: int) -> int:
        """Opacity at frame k in 1/LEVELS steps: fades in from frame 0, out by `stop`."""
        if k >= self.stop:
            return 0
        x = min(1.0, (k + 1) / self.fade_in, (self.stop - k) / self.fade_out)
        return max(1, round(x * LEVELS))

    @property
    def hold(self) -> int:
        """A frame in the middle of the full-opacity span (the check reads it)."""
        return min(self.stop - 1, (self.fade_in + self.stop - self.fade_out) // 2)

    def faded(self, level: int) -> Image.Image:
        if level == LEVELS:
            return self.image
        if level not in self._faded:
            img = self.image.copy()
            img.putalpha(_scaled(img.getchannel("A"), level / LEVELS))
            self._faded[level] = img
        return self._faded[level]


def read_title(song_dir: Path) -> list[str] | None:
    """title.txt's lines as written, with surrounding spaces and blank lines dropped; None when
    there is no file. More than two lines is refused."""
    path = Path(song_dir) / TITLE_FILE
    if not path.exists():
        return None
    try:
        text = path.read_text(encoding="utf-8-sig")
    except (OSError, UnicodeDecodeError) as exc:
        raise RenderError(f"{path}: cannot read it as UTF-8 text: {exc}") from None
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    if len(lines) > 2:
        raise RenderError(f"{path}: {len(lines)} lines; a title card has one or two")
    return lines


def card_pad(theme: Theme) -> int:
    """Room around a card glyph for its stroke, shadow and glow."""
    reach = (stroke_px(theme, theme.font_size) + 3 * theme.shadow_radius
             + max(abs(v) for v in theme.shadow_offset))
    return max(reach, 3 * theme.glow_radius if theme.card_glow else 0)


def build_card(lines: list[str], theme: Theme, n_frames: int) -> Card:
    """The card image and its span. Size card_scale × font_size, shrunk until every line fits
    the safe zone (or the layout box) about center_x, rows at the theme's row pitch."""
    pad = card_pad(theme)
    x0, _, x1, _ = theme.safe_zone or (theme.center_x - theme.max_width // 2, 0,
                                       theme.center_x + theme.max_width // 2, 0)
    width = 2 * min(x1 - theme.center_x, theme.center_x - x0) - 2 * pad
    size = round(theme.card_scale * theme.font_size)
    while True:
        fonts = layout.font_set(theme, size)
        widest = max(lines, key=fonts.advance)
        if fonts.advance(widest) <= width:
            break
        if size <= theme.card_min_size:
            raise RenderError(f'title.txt: "{widest}" is too wide for the title card even at '
                              f"{size} px; shorten it or split it over two lines")
        size = max(theme.card_min_size, size - theme.font_step)
    pitch = round(theme.row_spacing * (fonts.ascent + fonts.descent))
    stroke = stroke_px(theme, size)
    rows = []
    for r, text in enumerate(lines):
        glyph = layout.word_mask(text, fonts, pad)
        outline = layout.word_mask(text, fonts, pad, stroke=stroke) if stroke else glyph
        layers = []
        if theme.card_glow:   # Phonk Neon: its glow under its dark rim (D-025)
            bloom = _scaled(glyph.filter(ImageFilter.GaussianBlur(theme.glow_radius)),
                            theme.glow_boost)
            layers.append(_solid(theme.glow_rgb, _scaled(bloom, theme.card_glow)))
        shadow = Image.new("L", glyph.size, 0)
        shadow.paste(_scaled(outline.filter(ImageFilter.GaussianBlur(theme.shadow_radius)),
                             theme.shadow_alpha), theme.shadow_offset)
        layers.append(_solid(theme.shadow_rgb, shadow))
        if stroke and theme.stroke_rgb is not None:
            layers.append(_solid(theme.stroke_rgb, outline))
        layers.append(_solid(theme.text_rgb, glyph))
        x = round(theme.center_x - (glyph.width - 2 * pad) / 2) - pad
        rows.append((layers, glyph, x, theme.card_top + r * pitch - pad))
    left, top = min(x for *_, x, _ in rows), min(y for *_, y in rows)
    right = max(x + g.width for _, g, x, _ in rows)
    bottom = max(y + g.height for _, g, _, y in rows)
    image = Image.new("RGBA", (right - left, bottom - top), (0, 0, 0, 0))
    ink = Image.new("L", image.size, 0)
    for layers, glyph, x, y in rows:
        for layer in layers:
            image.alpha_composite(layer, dest=(x - left, y - top))
        at = (x - left, y - top, x - left + glyph.width, y - top + glyph.height)
        ink.paste(ImageChops.lighter(ink.crop(at), glyph.point(lambda v: 255 if v == 255 else 0)),
                  at)
    fps = theme.fps
    return Card(lines, image, (left, top), ink, max(1, math.ceil(theme.card_in_s * fps)),
                min(n_frames, math.ceil(theme.card_s * fps)),
                max(1, math.ceil(theme.card_out_s * fps)))


def with_card(frames: Iterable[list], card: Card, theme: Theme) -> Iterator[list]:
    """The theme's frames with the faded card on top while it shows. Lyric ink (alpha >= 16)
    under the card's rectangle is logged in card.clashes. Later frames pass through as they are."""
    size = (theme.width, theme.height)
    box = (*card.pos, card.pos[0] + card.image.width, card.pos[1] + card.image.height)
    for k, parts in enumerate(frames):
        level = card.level(k)
        if level == 0:
            yield parts
            continue
        frame = Image.frombytes("RGBA", size, b"".join(bytes(p) for p in parts))
        if frame.getchannel("A").crop(box).point(_SAFE_LUT).getbbox():
            card.clashes.append(k)
        frame.alpha_composite(card.faded(level), dest=card.pos)
        yield [frame.tobytes()]


def card_checks(result: RenderResult, card: Card, theme: Theme) -> list[str]:
    """Clashes with the lyrics, then the card on the decoded overlay at its hold frame."""
    fails = []
    if card.clashes:
        fails.append(f"card: lyrics drawn under the title card on {len(card.clashes)} frame(s); "
                     f"first: frame {card.clashes[0]}")
    box = (*card.pos, card.pos[0] + card.image.width, card.pos[1] + card.image.height)
    size, seen = (theme.width, theme.height), {}

    def visit(k: int, data: bytes) -> None:
        if k == card.hold:
            alpha = Image.frombytes("L", size, data).crop(box)
            seen["mean"] = ImageStat.Stat(alpha, card.ink).mean[0]

    _, error = _stream(_decode_cmd(result.outputs["overlay"], "-vf", "alphaextract,format=gray",
                                   "-frames:v", str(card.hold + 1)), size[0] * size[1], visit)
    if error is not None:
        return fails + [f"overlay.mov: alpha decode failed: {error}"]
    if seen.get("mean", 0.0) < SYNC_ON_MIN:
        fails.append(f"card: mean alpha {seen.get('mean', 0.0):.0f} over the title card at frame "
                     f"{card.hold}, expected >= {SYNC_ON_MIN}")
    return fails
