"""Lofi frame checks (spec docs/specs/09_lofi_minimal_theme.md §4.6), on the decoded overlay.

lofi-minimal: colour-state sync (a word shows no accent, and is dim, on the frame before it turns
current; it is all accent once its fade-in completes and still on the frame before its end).
lofi-typewriter: typing sync on the alpha (no ink the frame before its first letter; all of its
ink once its last letter has faded in). Both scan the safe zone. A word is read only where its
line is at rest and alone; any other word becomes a report note, never a silent pass.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from .. import layout
from ..theme import Theme
from . import lofi
from .check import (
    SYNC_DROP_MIN, SYNC_ON_MIN, _alpha_sync, _colour_alpha, _ink, _Sample, _wanted, _zone_failure,
)
from .timeline import _ceil_frame

if TYPE_CHECKING:
    from . import RenderResult

STATE_CURRENT_MIN, STATE_BEFORE_MAX = 0.75, 0.25   # accent share when current / when upcoming
STATE_SPAN_MIN = 32   # colour levels text and accent must differ by in one channel to be read


def lofi_checks(result: RenderResult, lines: list[lofi.LofiLine], theme: Theme,
                n_frames: int) -> list[str]:
    """The plan's notes (cuts, words typed whole) into the report, then the theme's check."""
    for ll in lines:
        result.notes += ll.notes
    if theme.typewriter:
        return _alpha_sync(result, lines, theme, n_frames,
                           samples=_typing_samples(result, lines, theme))
    return _state_checks(result, lines, theme, n_frames)


def _read(result: RenderResult, lines: list[lofi.LofiLine], ll: lofi.LofiLine, label: str,
          frames: tuple[int | None, ...], theme: Theme) -> bool:
    """Whether every frame the word is read on is readable; if not, a note says why."""
    bad = [m for m in frames if m is not None and not lofi.readable(lines, ll, m, theme)]
    if bad:
        result.notes.append(f"{label}: its line was not at rest and alone on frame {bad[0]}, so "
                            "it was not read (sung back to back)")
    return not bad


def _box(wp) -> tuple[int, int, int, int]:
    b = wp.box
    return b.x, b.y, b.x + b.w, b.y + b.h


def _typing_samples(result: RenderResult, lines: list[lofi.LofiLine],
                    theme: Theme) -> list[_Sample]:
    fade, samples = _ceil_frame(theme.letter_fade_s, theme.fps), []
    for ll in lines:
        for wp in ll.words:
            if wp.reveal is None:
                continue
            ink = _ink(wp.text, layout.word_fonts(theme, ll.layout.font_size, wp.box.emphasis))
            if ink is None:
                continue
            name = lofi.label(wp, ll.layout)
            on = ll.letters[wp.box.index][-1] + fade
            before = wp.reveal - 1 if wp.reveal > 0 else None
            if _read(result, lines, ll, name, (on, before), theme):
                samples.append(_Sample(name, _box(wp), ink, on, before, False))
    return samples


def _state_checks(result: RenderResult, lines: list[lofi.LofiLine], theme: Theme,
                  n_frames: int) -> list[str]:
    text, accent = theme.text_rgb, theme.accent_rgb
    c = max(range(3), key=lambda k: abs(text[k] - accent[k]))   # the channel that tells them apart
    span = text[c] - accent[c]
    if abs(span) < STATE_SPAN_MIN:
        return [f"state: accent {accent} is too close to text colour {text} to check the "
                "colour states"]
    fade_in, samples = _ceil_frame(theme.current_in_s, theme.fps), []
    own = set()   # marked words in their own colour (emphasis_rgb): only their alpha is checked
    for ll in lines:
        for wp in ll.words:
            if wp.reveal is None:
                continue
            ink = _ink(wp.text, layout.word_fonts(theme, ll.layout.font_size, wp.box.emphasis))
            if ink is None:
                continue
            name = lofi.label(wp, ll.layout)
            on = wp.reveal + min(fade_in, wp.end - wp.reveal)
            held = wp.end - 1 if wp.end - 1 > on else None
            before = wp.reveal - 1 if wp.reveal > 0 else None
            if not _read(result, lines, ll, name, (on, held, before), theme):
                continue
            samples.append(_Sample(name, _box(wp), ink, on, before, False))
            if held is not None:
                samples.append(_Sample(f"{name} (held)", _box(wp), ink, held, None, False))
            if wp.box.emphasis and theme.emphasis_rgb is not None:
                own |= {name, f"{name} (held)"}

    means, outside, decoded, error = _colour_alpha(result, theme, c, _wanted(samples))
    if error is not None:
        return [f"overlay.mov: colour decode failed: {error}"]
    fails = [] if decoded == n_frames else [f"overlay.mov: {decoded} frames, expected {n_frames}"]
    for s in samples:
        on, before = means.get((s.label, "on")), means.get((s.label, "before"))
        if on is None:
            fails.append(f"state: {s.label}: frame {s.on} is outside the overlay")
            continue
        if on[1] < SYNC_ON_MIN:
            fails.append(f"state: {s.label}: mean alpha {on[1]:.0f} at frame {s.on}, expected "
                         f">= {SYNC_ON_MIN} while current")
        if s.label not in own and (f := (text[c] - on[0]) / span) < STATE_CURRENT_MIN:
            fails.append(f"state: {s.label}: {f:.0%} current colour at frame {s.on}; expected "
                         "100%")
        if before is None:
            continue
        if s.label not in own and (f := (text[c] - before[0]) / span) > STATE_BEFORE_MAX:
            fails.append(f"state: {s.label}: {f:.0%} current colour at frame {s.before}, the "
                         "frame before it turns current; expected 0%")
        if before[1] > on[1] - SYNC_DROP_MIN:
            fails.append(f"state: {s.label}: mean alpha {before[1]:.0f} at frame {s.before}, the "
                         f"frame before it turns current; expected <= {on[1] - SYNC_DROP_MIN:.0f}"
                         " (upcoming is dim)")
    if outside:
        fails.append(_zone_failure(outside, theme.safe_zone))
    return fails
