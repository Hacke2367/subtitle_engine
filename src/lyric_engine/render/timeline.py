"""Timeline: the frame each word reveals and glows at, and when each line is on screen.

Every frame comes from that word's own words.json start/end minus the theme's uniform lead
(red line 1). Plan: docs/specs/03_soft_romantic_render_impl.md.
"""
from __future__ import annotations

import math
from dataclasses import dataclass

from .. import layout
from ..layout import LineLayout, WordBox
from ..theme import Theme


@dataclass
class WordPlan:
    box: WordBox
    reveal: int | None      # first frame of the reveal; None = untimed (static, allow_flagged only)
    end: int | None         # frame of the word's end (end − lead); glow holds until here
    text: str               # the words.json text; build_sprites asserts box.text == text


@dataclass
class LinePlan:
    layout: LineLayout
    first: int              # first visible frame
    stop: int               # first frame no longer visible (exclusive), ≤ next line's first
    fade_start: int         # line opacity falls linearly from here to 0 at `stop`
    words: list[WordPlan]


# --- Timeline --------------------------------------------------------------------------------
def _timed(w: dict) -> bool:
    return w["start"] is not None and w["end"] is not None


def _floor_frame(t: float, fps: int) -> int:
    # Rounded first: a ms time on an exact frame boundary must not floor one frame early.
    return math.floor(round(t * fps, 6))


def _ceil_frame(t: float, fps: int) -> int:
    return math.ceil(round(t * fps, 6))


def plan_timeline(doc: dict, theme: Theme, n_frames: int, layout_fn=None,
                  emphasis: frozenset[int] = frozenset()) -> tuple[list[LinePlan], list[int]]:
    """Shown lines in time order (layout, visible span, per-word frames), and the lines skipped
    because none of their words has a time. Only a word's own start/end sets its frames.
    `emphasis`: indexes of *marked* words, laid out bigger (H-013)."""
    layout_fn = layout_fn or layout.layout_line
    fps, lead = theme.fps, theme.lead_s
    by_line: dict[int, list[dict]] = {}
    for w in doc["words"]:
        by_line.setdefault(w["line"], []).append(w)
    plans, skipped = [], []
    for line in sorted(by_line):
        words = by_line[line]
        timed = [w for w in words if _timed(w)]
        if not timed:
            skipped.append(line)
            continue
        lay = layout_fn([(w["i"], w["text"]) for w in words], line, theme, emphasis=emphasis)
        want, got = [(w["i"], w["text"]) for w in words], [(b.index, b.text) for b in lay.words]
        if got != want:   # red line 2: the layout places exactly these words, verbatim, in order
            raise AssertionError(f"layout of line {line + 1} returned {got}, expected {want}")
        plan = []
        for w, box in zip(words, lay.words):
            if not _timed(w):
                plan.append(WordPlan(box, None, None, w["text"]))
                continue
            reveal = max(0, _floor_frame(w["start"] - lead, fps))
            plan.append(WordPlan(box, reveal, max(reveal, _floor_frame(w["end"] - lead, fps)),
                                 w["text"]))
        first = min(wp.reveal for wp in plan if wp.reveal is not None)
        natural = _ceil_frame(max(w["end"] for w in timed) + theme.hold_s, fps)
        plans.append(LinePlan(lay, first, natural, first, plan))
    # Time order equals lyric order unless an allowed flagged word jumps; sorting keeps even
    # that case to one line on screen.
    plans.sort(key=lambda lp: (lp.first, lp.layout.line))
    fade, rev = round(theme.fade_out_s * fps), _ceil_frame(theme.reveal_s, fps)
    for k, lp in enumerate(plans):
        nxt = plans[k + 1].first if k + 1 < len(plans) else n_frames
        lp.stop = min(lp.stop, nxt, n_frames)
        # Never dim a line before its last word has fully revealed (D-013): back-to-back sung
        # lines shorten the fade, down to a cut, instead of fading words mid-reveal.
        settled = max(wp.reveal for wp in lp.words if wp.reveal is not None) + rev
        lp.fade_start = min(lp.stop, max(lp.first, lp.stop - fade, settled))
    return plans, skipped


def _ramp(k: float, frames: float) -> float:
    return 1.0 if frames <= 0 else max(0.0, min(1.0, k / frames))


def word_state(wp: WordPlan, n: int, theme: Theme) -> tuple[float, float, float]:
    """(opacity, rise_px, glow) of a word at frame n. An untimed word is static: (1, 0, 0)."""
    if wp.reveal is None:
        return 1.0, 0.0, 0.0
    if n < wp.reveal:
        return 0.0, 0.0, 0.0
    p = _ramp(n - wp.reveal, theme.reveal_s * theme.fps)
    ease = p * p * (3 - 2 * p)                         # smoothstep
    glow_in = _ramp(n - wp.reveal, theme.glow_in_s * theme.fps)
    glow_out = 1.0 if n <= wp.end else 1.0 - _ramp(n - wp.end, theme.glow_out_s * theme.fps)
    return ease, theme.rise_px * (1 - ease), min(glow_in, glow_out)


def line_opacity(lp: LinePlan, n: int) -> float:
    if not lp.first <= n < lp.stop:
        return 0.0
    if n < lp.fade_start:
        return 1.0
    return (lp.stop - n) / (lp.stop - lp.fade_start)
