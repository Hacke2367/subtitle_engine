"""Stage 2: words.json + theme + layout -> alpha .mov overlay + green-screen mp4 (both primary, H-003).

Never calls the alignment API: editing words.json by hand and re-rendering must stay free.
Frames are drawn once and streamed as raw RGBA into ONE ffmpeg process that writes all three
outputs (plan docs/specs/03_soft_romantic_render_impl.md). Every reveal and glow frame comes from
that word's own words.json time minus the theme's uniform lead (red line 1), and every drawn string
is the words.json text (red line 2). Everything written goes to songs/<song>/render/<theme>/ (D-018).
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from pathlib import Path

from .. import align, layout, timing
from ..theme import SOFT_ROMANTIC, Theme
from . import cinematic, encode, focus, karaoke, lofi
from .check import REPORT, check_outputs, write_report
from .encode import ALPHA_CODECS, OUTPUTS, RenderError, _encode, _ffmpeg_cmd, _remove
from .frames import FadeCache, _frame_parts, build_sprites, compose_frame
from .timeline import LinePlan, WordPlan, _ceil_frame, line_opacity, plan_timeline, word_state


@dataclass
class RenderResult:
    render_dir: Path
    outputs: dict[str, Path]        # "overlay", "green", "preview"
    frames: int
    wall_s: float
    skipped_lines: list[int]        # lines with no timed word (not shown)
    checks: list[str]               # output-check failures; [] = pass
    notes: list[str] = field(default_factory=list)   # not failures, e.g. words sung back to back
    emphasis: list[str] = field(default_factory=list)   # '"dil" (line 2)' per *marked* word


# --- Input -----------------------------------------------------------------------------------
def load_for_render(song_dir: Path, *,
                    allow_flagged: bool) -> tuple[dict, Path, frozenset[int]]:
    """The song's validated words.json doc, audio path and *emphasised* word indexes (read from
    lyrics.txt, the only place emphasis lives: H-009), or a RenderError saying what to fix."""
    song_dir = Path(song_dir)
    try:
        audio, lyrics = align.song_paths(song_dir)
    except FileNotFoundError as exc:
        raise RenderError(str(exc)) from None
    try:   # before validate: a malformed marker gets the reader's hint, not a "stale"
        emphasis = timing.read_lyrics(lyrics).emphasis
    except timing.LyricsError as exc:
        raise RenderError(str(exc)) from None
    path = song_dir / "words.json"
    if not path.exists():
        raise RenderError(f"{path} not found; run `align {song_dir}` first")
    try:
        doc = timing.load_words(path)
    except ValueError as exc:   # JSON syntax or encoding error from a hand edit
        raise RenderError(f"{path} is not valid JSON: {exc}") from None
    errors = timing.validate(doc, lyrics, audio)
    if errors:
        stale = any(e.startswith(("stale:", "lyrics.lines differ")) for e in errors)
        hint = (f"The lyrics or audio changed after alignment: run `align {song_dir} --overwrite` "
                "(the old words.json is kept as words.json.bak)." if stale
                else "Fix these in words.json by hand, then render again.")
        raise RenderError("\n".join([f"{path} cannot be rendered:", *(f"  {e}" for e in errors),
                                     hint]))
    flagged = [w for w in doc["words"] if w["flagged"]]
    if flagged and not allow_flagged:
        raise RenderError("\n".join([
            f"{path} has {len(flagged)} flagged word(s):",
            *(f'  word {w["i"]} "{w["text"]}" (line {w["line"] + 1}): {", ".join(w["reasons"])}'
              for w in flagged),
            'Fix their times in words.json by hand (numeric start and end, "flagged": false, '
            '"reasons": []), or pass --allow-flagged: timed flagged words then animate at the '
            "aligner's time, and untimed ones are shown static with their line."]))
    return doc, audio, emphasis


# --- Render ----------------------------------------------------------------------------------
def render(song_dir: Path, *, codec: str | None = None, allow_flagged: bool = False,
           theme: Theme = SOFT_ROMANTIC) -> RenderResult:
    """songs/<song>/words.json -> render/<theme>/overlay.mov, overlay_green.mp4, preview.mp4,
    report.md (D-018: each theme in its own folder). Raises RenderError (or layout.LayoutError
    for a line that cannot be laid out)."""
    t0 = time.perf_counter()
    song_dir = Path(song_dir)
    codec = codec or theme.alpha_codec
    if codec not in encode.ALPHA_CODECS:
        raise RenderError(f"unknown codec {codec!r}; choose one of: {', '.join(encode.ALPHA_CODECS)}")
    doc, audio, emphasis = load_for_render(song_dir, allow_flagged=allow_flagged)
    try:
        duration = align.probe_duration(audio)
    except (RuntimeError, OSError) as exc:
        raise RenderError(str(exc)) from None
    n = _ceil_frame(duration, theme.fps)
    if theme.motion == "karaoke":
        lines, skipped = karaoke.plan_karaoke(doc, theme, n, emphasis=emphasis)
        sprites, cache, parts = (karaoke.build_sprites(lines, theme), karaoke.LineCache(),
                                 karaoke.frame_parts)
    elif theme.motion == "focus":
        lines, skipped = focus.plan_focus(doc, theme, n, emphasis=emphasis)
        sprites, cache, parts = build_sprites(lines, theme), focus.FocusCache(), focus.frame_parts
    elif theme.motion == "lofi":
        lines, skipped = lofi.plan_lofi(doc, theme, n, emphasis=emphasis)
        sprites, cache, parts = lofi.build_sprites(lines, theme), lofi.LofiCache(), lofi.frame_parts
    elif theme.motion == "cinematic":
        lines, skipped = cinematic.plan_cinematic(doc, theme, n, emphasis=emphasis)
        sprites, cache, parts = (cinematic.build_sprites(lines, theme), cinematic.CinematicCache(),
                                 cinematic.frame_parts)
    else:
        lines, skipped = plan_timeline(doc, theme, n, emphasis=emphasis)
        sprites, cache, parts = build_sprites(lines, theme), FadeCache(), _frame_parts

    render_dir = song_dir / "render" / theme.name
    render_dir.mkdir(parents=True, exist_ok=True)
    outputs = {key: render_dir / name for key, name in OUTPUTS.items()}
    _remove([*outputs.values(), render_dir / REPORT])   # a failed run must not leave old results
    t1 = time.perf_counter()
    _encode(_ffmpeg_cmd(theme, codec, audio, outputs),
            (parts(k, lines, sprites, theme, cache) for k in range(n)), outputs)
    encode_s = time.perf_counter() - t1
    result = RenderResult(render_dir, outputs, n, 0.0, skipped, [], emphasis=[
        f'"{w["text"]}" (line {w["line"] + 1})' for w in doc["words"] if w["i"] in emphasis])
    t2 = time.perf_counter()
    result.checks = check_outputs(result, lines, theme, n)
    check_s = time.perf_counter() - t2
    result.wall_s = time.perf_counter() - t0
    write_report(result, doc, codec=codec, theme=theme, encode_s=encode_s, check_s=check_s)
    return result
