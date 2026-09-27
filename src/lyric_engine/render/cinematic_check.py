"""Cinematic frame checks (spec docs/specs/10_cinematic_theme.md §4.6), on the decoded overlay.

Reveal sync: a timed word has no ink on the frame before its reveal frame, and is complete (solid
ink, all accent) once its blur-in completes and still on the frame before its end frame. A word
is read only where its block is at rest and alone (cinematic.readable); any other word becomes a
report note, never a silent pass. Plus the safe zone on every frame.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from .. import layout
from ..theme import Theme
from . import cinematic
from .check import (
    SYNC_DROP_MIN, SYNC_ON_MIN, _colour_alpha, _ink, _Sample, _wanted, _zone_failure,
)
from .lofi_check import STATE_CURRENT_MIN, STATE_SPAN_MIN

if TYPE_CHECKING:
    from . import RenderResult


def cinematic_checks(result: RenderResult, blocks: list[cinematic.Block], theme: Theme,
                     n_frames: int) -> list[str]:
    """The plan's notes (cuts, too-tall couplets) into the report, then one decode of the
    overlay's colour and alpha for the reveal sync and the safe zone."""
    for b in blocks:
        result.notes += b.notes
    text, accent = theme.text_rgb, theme.accent_rgb
    c = max(range(3), key=lambda k: abs(text[k] - accent[k]))   # the channel that tells them apart
    span = text[c] - accent[c]
    if abs(span) < STATE_SPAN_MIN:
        return [f"reveal: accent {accent} is too close to text colour {text} to check the reveal"]
    samples = _samples(result, blocks, theme)
    means, outside, decoded, error = _colour_alpha(result, theme, c, _wanted(samples))
    if error is not None:
        return [f"overlay.mov: colour decode failed: {error}"]
    fails = [] if decoded == n_frames else [f"overlay.mov: {decoded} frames, expected {n_frames}"]
    for s in samples:
        on, before = means.get((s.label, "on")), means.get((s.label, "before"))
        if on is None:
            fails.append(f"reveal: {s.label}: frame {s.on} is outside the overlay")
            continue
        if on[1] < SYNC_ON_MIN:
            fails.append(f"reveal: {s.label}: mean alpha {on[1]:.0f} at frame {s.on}, expected "
                         f">= {SYNC_ON_MIN} once complete")
        if (f := (text[c] - on[0]) / span) < STATE_CURRENT_MIN:
            fails.append(f"reveal: {s.label}: {f:.0%} accent at frame {s.on}; expected 100%")
        if before is not None and before[1] > on[1] - SYNC_DROP_MIN:
            fails.append(f"reveal: {s.label}: mean alpha {before[1]:.0f} at frame {s.before}, the "
                         f"frame before its reveal; expected <= {on[1] - SYNC_DROP_MIN:.0f} "
                         "(no ink)")
    if outside:
        fails.append(_zone_failure(outside, theme.safe_zone))
    return fails


def _samples(result: RenderResult, blocks: list[cinematic.Block], theme: Theme) -> list[_Sample]:
    """Per timed word with ink: complete (on), still current (held, when later) and before."""
    samples = []
    for b in blocks:
        for wp in b.words:
            if wp.reveal is None:
                continue
            ink = _ink(wp.text, layout.word_fonts(theme, b.font_size(wp), wp.box.emphasis))
            if ink is None:
                continue
            name = b.label(wp)
            on = wp.reveal + cinematic.blur_in_frames(wp, theme) - 1
            held = wp.end - 1 if wp.end - 1 > on else None
            before = wp.reveal - 1 if wp.reveal > 0 else None
            bad = [m for m in (on, held, before)
                   if m is not None and not cinematic.readable(blocks, b, m, theme)]
            if bad:
                result.notes.append(f"{name}: its block was leaving or another block was on "
                                    f"screen on frame {bad[0]}, so it was not read (sung back "
                                    "to back)")
                continue
            box = (wp.box.x, wp.box.y, wp.box.x + wp.box.w, wp.box.y + wp.box.h)
            samples.append(_Sample(name, box, ink, on, before, False))
            if held is not None:
                samples.append(_Sample(f"{name} (held)", box, ink, held, None, False))
    return samples
