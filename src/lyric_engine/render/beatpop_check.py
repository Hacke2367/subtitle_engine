"""Beat Pop frame checks (spec docs/specs/12_beat_pop_theme.md §4.7) on the overlay's alpha.

Pop sync: a timed word has no ink the frame before it is sung, ink on that frame, and is complete
once its pop ends. Pill sync: its pill is there on that frame while it is sung, and gone the
frame before it is sung and on its end frame. Beat sync: around each readable beat, the line's
drawn width on b − 1, b and b + 1 matches the plan's (bump, pops and pills). Everything is read at
the line's frame geometry (bump, shake), and only where the line is alone and not leaving
(beatpop.readable); anything else is a report note, never a silent pass. Plus the safe zone on
every frame.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from PIL import Image, ImageChops, ImageFilter, ImageStat

from .. import layout
from ..theme import Theme
from . import beatpop
from .check import (
    _SAFE_LUT, SYNC_DROP_MIN, SYNC_ON_MIN, _decode_cmd, _ink, _stream, _zone_failure,
)
from .karaoke import _block, stroke_px

if TYPE_CHECKING:
    from . import RenderResult

SOLID = 128                               # alpha that counts as ink for the pop reads
POP_BEFORE_MAX, POP_ON_MIN = 0.02, 0.25   # solid pixels in the word's box / its ink at rest
BEAT_TOL, BEAT_READ_MIN = 4, 6            # px: drawn vs planned line width; planned rise to read
_SOLID_LUT = [255 if v >= SOLID else 0 for v in range(256)]


@dataclass
class _Read:
    label: str
    kind: str                 # "before", "on", "complete", "pill on", "pill off"
    frame: int
    mask: Image.Image         # 255 where it is read, at the frame's geometry
    pos: tuple[int, int]      # its top-left on the frame
    ref: int = 0              # before / on: the word's solid ink pixels at rest


def beatpop_checks(result: RenderResult, show: beatpop.Show, theme: Theme,
                   n_frames: int) -> list[str]:
    """The plan's notes into the report, then one alpha decode for the pop, pill and beat reads
    and the safe zone."""
    result.notes += show.notes
    for pl in show.lines:
        result.notes += pl.notes
    reads = _word_reads(result, show, theme)
    beats = _beat_reads(result, show, theme, n_frames)
    wanted: dict[int, list[_Read]] = {}
    for r in reads:
        wanted.setdefault(r.frame, []).append(r)
    widths_at = {m for b in beats for m in (b - 1, b, b + 1)}
    size, zone = (theme.width, theme.height), theme.safe_zone
    values: dict[tuple[str, str], float] = {}
    widths: dict[int, int] = {}
    outside: list[tuple[int, tuple]] = []

    def visit(k: int, data: bytes) -> None:
        frame = Image.frombytes("L", size, data)
        for r in wanted.get(k, ()):
            box = (*r.pos, r.pos[0] + r.mask.width, r.pos[1] + r.mask.height)
            crop = frame.crop(box)
            if r.kind in ("before", "on"):
                solid = crop.point(_SOLID_LUT)
                values[r.label, r.kind] = ImageStat.Stat(solid, r.mask).sum[0] / 255
            else:
                values[r.label, r.kind] = ImageStat.Stat(crop, r.mask).mean[0]
        if zone is None and k not in widths_at:
            return
        bbox = frame.point(_SAFE_LUT).getbbox()
        if k in widths_at:
            widths[k] = bbox[2] - bbox[0] if bbox else 0
        if zone is not None and bbox and (bbox[0] < zone[0] or bbox[1] < zone[1]
                                          or bbox[2] > zone[2] or bbox[3] > zone[3]):
            outside.append((k, bbox))

    decoded, error = _stream(_decode_cmd(result.outputs["overlay"], "-vf",
                                         "alphaextract,format=gray"),
                             theme.width * theme.height, visit)
    if error is not None:
        return [f"overlay.mov: alpha decode failed: {error}"]
    fails = [] if decoded == n_frames else [f"overlay.mov: {decoded} frames, expected {n_frames}"]
    fails += _judge_words(reads, values)
    for b, planned in beats.items():
        got = [widths.get(m) for m in (b - 1, b, b + 1)]
        if any(w is None or abs(w - p) > BEAT_TOL for w, p in zip(got, planned)):
            fails.append(f"beat: frame {b}: line width {' → '.join(map(str, got))} px, planned "
                         f"{' → '.join(str(round(p)) for p in planned)} (bump on the beat)")
    if outside:
        fails.append(_zone_failure(outside, zone))
    return fails


def _judge_words(reads: list[_Read], values: dict[tuple[str, str], float]) -> list[str]:
    fails = []
    for r in reads:
        v = values.get((r.label, r.kind))
        if v is None:
            fails.append(f"pop: {r.label}: frame {r.frame} is outside the overlay")
        elif r.kind == "before" and v > POP_BEFORE_MAX * r.ref:
            fails.append(f"pop: {r.label}: ink on frame {r.frame}, the frame before it is sung")
        elif r.kind == "on" and v < POP_ON_MIN * r.ref:
            fails.append(f"pop: {r.label}: no ink on frame {r.frame}, where it is sung")
        elif r.kind == "complete" and v < SYNC_ON_MIN:
            fails.append(f"pop: {r.label}: mean alpha {v:.0f} on frame {r.frame}, expected >= "
                         f"{SYNC_ON_MIN} once its pop is over")
        elif r.kind == "pill on" and v < SYNC_ON_MIN:
            fails.append(f"pill: {r.label}: no pill on frame {r.frame}, while it is sung")
    for r in reads:
        on = values.get((r.label, "pill on"))
        v = values.get((r.label, r.kind))
        if r.kind == "pill off" and on is not None and v is not None and v > on - SYNC_DROP_MIN:
            fails.append(f"pill: {r.label}: pill on frame {r.frame}, outside its span")
    return fails


# --- Reads -------------------------------------------------------------------------------------
def _place(show: beatpop.Show, pl: beatpop.PopLine, m: int, theme: Theme, mask: Image.Image,
           xy: tuple[int, int], erode: bool) -> tuple[Image.Image, tuple[int, int]]:
    """A rest-position mask moved to frame m's line geometry (scale about the line centre, shake),
    with transformed()'s rounding; eroded 1 px when every pixel of it must be solid."""
    scale, dx, dy, _ = (beatpop.line_state(show, pl, m, theme) if m >= pl.enter
                        else (1.0, 0, 0, 1.0))
    if scale != 1.0:
        mask = mask.resize((max(1, round(mask.width * scale)), max(1, round(mask.height * scale))),
                           Image.NEAREST)
    top, bottom = _block(pl.layout)
    cx, cy = theme.center_x, (top + bottom) / 2
    pos = (round(cx + dx + (xy[0] - cx) * scale), round(cy + dy + (xy[1] - cy) * scale))
    return (mask.filter(ImageFilter.MinFilter(3)) if erode else mask), pos


def _pill_only(wp, fonts: layout.FontSet, theme: Theme) -> Image.Image:
    """255 where only the word's pill can be: its pill minus its outline grown by 2 px, at rest,
    the size of its box."""
    pill = beatpop.pill_mask(fonts, wp.box, 0, theme).point(lambda v: 255 if v >= 250 else 0)
    outline = layout.word_mask(wp.text, fonts, 0, stroke=stroke_px(theme, fonts.size))
    grown = outline.filter(ImageFilter.MaxFilter(5)).point(lambda v: 255 if v else 0)
    return ImageChops.subtract(pill, grown)


def _word_reads(result: RenderResult, show: beatpop.Show, theme: Theme) -> list[_Read]:
    """Per timed word with ink: before, on, complete, and the pill on / off reads, each where its
    line is readable; a word that cannot be read that way becomes one note."""
    reads = []
    for pl in show.lines:
        for wp in pl.words:
            if wp.reveal is None:
                continue
            fonts = layout.word_fonts(theme, pl.layout.font_size, wp.box.emphasis)
            ink = _ink(wp.text, fonts)
            if ink is None:
                continue
            label, xy = pl.label(wp), (wp.box.x, wp.box.y)
            done = wp.reveal + beatpop.pop_frames(wp, theme) - 1
            wanted = [("on", wp.reveal), ("complete", done)]
            if wp.reveal > 0:
                wanted += [("before", wp.reveal - 1), ("pill off", wp.reveal - 1)]
            if done < wp.end:
                wanted.append(("pill on", done))
                if wp.end < pl.leave:
                    wanted.append(("pill off", wp.end))
            bad = [m for _, m in wanted if not beatpop.readable(show, pl, m)]
            if bad:
                result.notes.append(f"{label}: its line was leaving or another line was on "
                                    f"screen on frame {bad[0]}, so it was not read")
                continue
            box = Image.new("L", ink.size, 255)
            ref = ImageStat.Stat(ink).sum[0] / 255
            pill = _pill_only(wp, fonts, theme)
            for kind, m in wanted:
                source, erode = ((box, False) if kind in ("before", "on") else
                                 (ink, True) if kind == "complete" else (pill, kind == "pill on"))
                mask, pos = _place(show, pl, m, theme, source, xy, erode)
                reads.append(_Read(label, kind, m, mask, pos, round(ref)))
    return reads


def _extents(show: beatpop.Show, theme: Theme) -> dict[int, tuple[tuple[float, float], ...]]:
    """Per word: its drawn x-extent at rest on the frame (alpha >= SAFE_ALPHA_MIN), as (plain:
    shadow, stroke and glyph; sung: pill and glyph), from the renderer's own sprites."""
    boxes = {wp.box.index: wp.box for pl in show.lines for wp in pl.words}
    out = {}
    for index, (shadow, outline, glyph, pill, pad) in beatpop.build_sprites(show, theme).items():
        def span(*masks, left=boxes[index].x - pad):
            xs = [bb for m in masks if (bb := m.point(_SAFE_LUT).getbbox())]
            return left + min(b[0] for b in xs), left + max(b[2] for b in xs)
        out[index] = (span(shadow, outline, glyph), span(pill, glyph))
    return out


def _planned_width(show: beatpop.Show, pl: beatpop.PopLine, m: int, theme: Theme,
                   ext: dict) -> float:
    """The line's drawn width on frame m by the plan: each drawn word's extent at its pop scale
    (about its box centre), the whole times the line's scale."""
    lo, hi = float("inf"), float("-inf")
    for wp in pl.words:
        look = beatpop.word_look(pl, wp, m, theme)
        if look is None:
            continue
        q, sung = look
        left, right = ext[wp.box.index][sung]
        c = wp.box.x + wp.box.w / 2
        lo, hi = min(lo, c + (left - c) * q), max(hi, c + (right - c) * q)
    return (hi - lo) * beatpop.line_state(show, pl, m, theme)[0] if hi > lo else 0.0


def _beat_reads(result: RenderResult, show: beatpop.Show, theme: Theme,
                n_frames: int) -> dict[int, tuple[float, float, float]]:
    """Beat frames that can be read, with the planned widths on b − 1, b, b + 1: the line alone
    and not leaving on the three, and a planned width rise on b of BEAT_READ_MIN px or more. The
    others are counted in one note."""
    read, skipped, ext = {}, 0, None
    for b in show.beats:
        pl = next((pl for pl in show.lines if pl.enter <= b < pl.stop), None)
        if pl is None:
            continue
        frames = (b - 1, b, b + 1)
        if (b - 1 < pl.enter or b + 1 >= n_frames
                or not all(beatpop.readable(show, pl, m) for m in frames)):
            skipped += 1
            continue
        ext = ext or _extents(show, theme)
        planned = tuple(_planned_width(show, pl, m, theme, ext) for m in frames)
        if planned[1] - planned[0] < BEAT_READ_MIN:
            skipped += 1
            continue
        read[b] = planned
    if skipped:
        result.notes.append(f"beat check: {skipped} of {skipped + len(read)} beats with a line on "
                            "screen not read (next to a line change, or too narrow to show)")
    return read
