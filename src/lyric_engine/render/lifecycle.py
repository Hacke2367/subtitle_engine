"""One item on screen at a time: when each shown line (Lofi, spec 09 §4.2) or block (Cinematic,
spec 10 §4.3) enters, rests, leaves and stops, on frames (D-020).

Items come in time order and carry `first_cur` (first frame a word of it is sung), `last_end`,
`settled` (it never leaves before this), `words` (WordPlans), `notes`, `name` and `label(wp)`;
`schedule` sets `enter`, `rest`, `leave` and `stop`. Word frames are never moved (red line 1).
"""
from __future__ import annotations

from ..theme import Theme
from .timeline import _ceil_frame


def schedule(items: list, theme: Theme, n_frames: int, ahead: bool) -> None:
    """ahead: the item shows before its first word (an entrance over enter_s, starting preroll_s
    ahead); otherwise it appears on its first word's frame. Hold hold_s, exit fade_out_s."""
    fps, tw = theme.fps, not ahead
    Ein = 0 if tw else _ceil_frame(theme.enter_s, fps)
    P = 0 if tw else round(theme.preroll_s * fps)
    H, X = _ceil_frame(theme.hold_s, fps), round(theme.fade_out_s * fps)
    for k, ll in enumerate(items):
        if k == 0:   # the first item: preroll ahead, or at rest from frame 0 when sung at once
            if tw:
                ll.enter = ll.rest = ll.first_cur
            elif ll.first_cur - 1 - Ein < 0:
                ll.enter = ll.rest = 0
            else:
                ll.enter = max(0, ll.first_cur - P)
                ll.rest = ll.enter + Ein
        E = ll.settled
        if k + 1 == len(items):
            ll.stop = E + H + X
            ll.leave = ll.stop - X
            continue
        # Frames between this item's last word and the next item's first current frame F; the
        # frame F − 1 is kept clean for the next item (at rest, or alone): D-020.
        nxt = items[k + 1]
        F = nxt.first_cur
        A = F - 1 - E
        if A >= X + Ein:   # hold, or leave early: as late as the next item's entrance allows
            ll.stop = min(E + H + X, F - 1 - Ein)
            ll.leave = ll.stop - X
            nxt.enter = F if tw else max(F - P, ll.stop)
            nxt.rest = F if tw else nxt.enter + Ein
        elif A >= 2:       # too close for both: exit and entrance shrink in proportion
            x = A if tw else min(A - 1, max(1, round(A * X / (X + Ein))))
            ll.leave, ll.stop = E, E + x
            nxt.enter = F if tw else ll.stop
            nxt.rest = F if tw else F - 1
        else:              # a cut: the old item goes and the next one is at rest on one frame
            ll.leave = ll.stop = F
            nxt.enter = nxt.rest = F
            gap = F - ll.last_end
            ll.notes.append(f"{ll.name}: cut, not faded (the next line starts "
                            + (f"{gap} frame(s) after" if gap > 0 else "before")
                            + " its last word ends)")
            ll.notes += [f"{ll.label(wp)}: its last {wp.end - F + 1} frame(s) are not "
                         "shown (sung back to back)"
                         for wp in ll.words if wp.end is not None and wp.end >= F]
    for ll in items:
        ll.stop = min(ll.stop, n_frames)
        ll.rest = min(ll.rest, ll.stop)
        ll.enter = min(ll.enter, ll.rest)
        ll.leave = min(ll.leave, ll.stop)
