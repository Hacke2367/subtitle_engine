"""Phonk Neon frame checks (spec docs/specs/13_phonk_neon_theme.md §4.6), on the decoded overlay.

Light sync: a timed word's ink is the unlit colour on the frame before its reveal frame and the
lit colour on it. Pulse sync: around steadily lit words the glow's alpha rises onto each beat
frame and not after it. One colour + alpha decode serves both and scans the safe zone. A word or
beat that cannot be read (its line not alone, at rest and unshaken) is a report note, never a
silent pass.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from PIL import Image, ImageDraw

from .. import layout
from ..theme import Theme
from . import phonk
from .beatpop import PopLine, Show
from .check import SYNC_ON_MIN, _colour_alpha, _ink, _Sample, _wanted, _zone_failure

if TYPE_CHECKING:
    from . import RenderResult

LIT_MIN, UNLIT_MAX = 0.75, 0.25   # lit share of a word's ink colour: its first sung frame / before
PULSE_RISE_MIN, PULSE_FALL_TOL = 1.0, 0.5   # mean alpha around lit words: onto a beat / after it
PULSE_PLAN_MIN = 0.1              # planned glow rise a beat needs to be read
REGION_MIN = 200                  # pixels a pulse read needs


def phonk_checks(result: RenderResult, show: Show, theme: Theme, n_frames: int) -> list[str]:
    """The plan's notes into the report, then one decode for the light and pulse reads and the
    safe zone."""
    result.notes += show.notes
    for pl in show.lines:
        result.notes += pl.notes
    lit, unlit = theme.text_rgb, theme.unlit_rgb
    c = max(range(3), key=lambda k: abs(lit[k] - unlit[k]))   # the channel that tells them apart
    span = lit[c] - unlit[c]
    words = _light_samples(result, show, theme)
    beats = _pulse_samples(result, show, theme, n_frames)
    means, outside, decoded, error = _colour_alpha(
        result, theme, c, _wanted(words + [s for trio in beats for s in trio]))
    if error is not None:
        return [f"overlay.mov: colour decode failed: {error}"]
    fails = [] if decoded == n_frames else [f"overlay.mov: {decoded} frames, expected {n_frames}"]
    for s in words:
        on, before = means.get((s.label, "on")), means.get((s.label, "before"))
        if on is None:
            fails.append(f"light: {s.label}: frame {s.on} is outside the overlay")
            continue
        if on[1] < SYNC_ON_MIN:
            fails.append(f"light: {s.label}: mean alpha {on[1]:.0f} at frame {s.on}, expected "
                         f">= {SYNC_ON_MIN}")
        if (f := (on[0] - unlit[c]) / span) < LIT_MIN:
            fails.append(f"light: {s.label}: {f:.0%} lit at frame {s.on}, its first sung frame; "
                         "expected 100%")
        if before is not None and (f := (before[0] - unlit[c]) / span) > UNLIT_MAX:
            fails.append(f"light: {s.label}: {f:.0%} lit at frame {s.before}, the frame before "
                         "it is sung; expected 0%")
    for trio in beats:
        a = [means.get((s.label, "on"), (0.0, 0.0))[1] for s in trio]
        if not (a[1] > a[0] + PULSE_RISE_MIN and a[2] <= a[1] + PULSE_FALL_TOL):
            fails.append(f"pulse: beat at frame {trio[1].on}: glow alpha {a[0]:.1f}, {a[1]:.1f}, "
                         f"{a[2]:.1f} on the frames before, of and after it; expected a rise onto "
                         "the beat and none after")
    if outside:
        fails.append(_zone_failure(outside, theme.safe_zone))
    return fails


def _light_samples(result: RenderResult, show: Show, theme: Theme) -> list[_Sample]:
    samples = []
    for pl in show.lines:
        for wp in pl.words:
            if wp.reveal is None:
                continue
            ink = _ink(wp.text, layout.word_fonts(theme, pl.layout.font_size, wp.box.emphasis))
            if ink is None:
                continue
            before = wp.reveal - 1 if wp.reveal > 0 else None
            bad = [m for m in (wp.reveal, before)
                   if m is not None and not phonk.readable(show, pl, m, theme)]
            if bad:
                result.notes.append(f"{pl.label(wp)}: its line was not at rest, unshaken and "
                                    f"alone on frame {bad[0]}, so its light was not read")
                continue
            b = wp.box
            samples.append(_Sample(pl.label(wp), (b.x, b.y, b.x + b.w, b.y + b.h), ink,
                                   wp.reveal, before, False))
    return samples


def _pulse_samples(result: RenderResult, show: Show, theme: Theme,
                   n_frames: int) -> list[list[_Sample]]:
    """Per readable beat b, three reads (b − 1, b, b + 1) of the region around its line's
    steadily lit words, away from any word whose light changes (plan §2.7)."""
    reads, shown = [], 0
    for b in show.beats:
        pl = next((pl for pl in show.lines if pl.enter <= b < pl.stop), None)
        if pl is None:
            continue
        shown += 1
        frames = (b - 1, b, b + 1)
        if (b < 1 or b + 1 >= n_frames
                or not all(phonk.readable(show, pl, m, theme) for m in frames)
                or phonk.pulse(show, b, theme) - phonk.pulse(show, b - 1, theme) < PULSE_PLAN_MIN):
            continue
        region = _region(pl, frames, theme)
        if region is not None:
            reads.append([_Sample(f"beat {b} ({m - b:+d})", *region, m, None, False)
                          for m in frames])
    if shown:
        result.notes.append(f"pulse check read {len(reads)} of {shown} beat(s) with a line on "
                            "screen (the rest: no steadily lit word, a word lighting nearby, or "
                            "the line entering, leaving or shaking)")
    return reads


def _region(pl: PopLine, frames: tuple[int, ...],
            theme: Theme) -> tuple[tuple[int, int, int, int], Image.Image] | None:
    """(box, mask) over the words lit on every frame, grown by 2 glow radii, minus the words
    whose light changes grown by 3; None when too small to read."""
    R = theme.glow_radius
    looks = [(wp, {phonk.word_level(wp, m) for m in frames}) for wp in pl.words]
    steady = [wp.box for wp, lv in looks if lv == {1.0}]
    changing = [wp.box for wp, lv in looks if len(lv) > 1]
    if not steady:
        return None
    x0, y0 = min(b.x for b in steady) - 2 * R, min(b.y for b in steady) - 2 * R
    x1 = max(b.x + b.w for b in steady) + 2 * R
    y1 = max(b.y + b.h for b in steady) + 2 * R
    mask = Image.new("L", (x1 - x0, y1 - y0), 0)
    draw = ImageDraw.Draw(mask)
    for boxes, r, fill in ((steady, 2 * R, 255), (changing, 3 * R, 0)):
        for b in boxes:
            draw.rectangle((b.x - r - x0, b.y - r - y0, b.x + b.w + r - x0 - 1,
                            b.y + b.h + r - y0 - 1), fill=fill)
    if mask.histogram()[255] < REGION_MIN:
        return None
    return (x0, y0, x1, y1), mask
