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
from . import beatpop, cinematic, encode, focus, karaoke, lofi, phonk
from .card import build_card, card_checks, read_title, with_card
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


def load_beats_for_render(song_dir: Path, duration: float
                          ) -> tuple[list[float], list[float], list[str]]:
    """Beat Pop's and Phonk Neon's beat times (beats.json, computed once if missing: D-022), the
    drop times from drops.txt snapped to the nearest beat (H-019), and report notes; or a
    RenderError."""
    from .. import beats   # here: numpy, and librosa only if beats.json must be computed
    try:
        found = beats.ensure_beats(song_dir)
        drops = beats.read_drops(Path(song_dir) / beats.DROPS_FILE, duration)
    except beats.BeatsError as exc:
        raise RenderError(str(exc)) from None
    except ModuleNotFoundError as exc:
        raise RenderError(f"{exc.name} is not installed: "
                          "pip install -r requirements.txt") from None
    times, doc = found.doc["beats"], found.doc
    snapped = beats.snap([t for _, t in drops], times)
    notes = [f"beats: {doc['tempo_bpm']:g} BPM, {len(times)} beats "
             f"(beats.json {'reused' if found.reused else 'computed'})", *found.notes]
    if not times:
        notes.append("no beats: no bump or pulse" + ("; drops used as written" if drops else ""))
    notes += [f"drop {text} → {t:.2f} s" for (text, _), t in zip(drops, snapped)]
    return times, snapped, notes


# --- Render ----------------------------------------------------------------------------------
def render(song_dir: Path, *, codec: str | None = None, allow_flagged: bool = False,
           theme: Theme = SOFT_ROMANTIC, bg: tuple[str, str] | None = None,
           backdrop: bool = False) -> RenderResult:
    """songs/<song>/words.json -> render/<theme>/overlay.mov, overlay_green.mp4, preview.mp4,
    report.md (D-018: each theme in its own folder); with bg = (world, mood) also the finished
    short final_<world>_<mood>.mp4 (spec 17); with backdrop=True (needs bg) only the background,
    backdrop_<world>_<mood>.mp4: no lyrics drawn, no other output touched. Raises RenderError (or layout.LayoutError for a
    line that cannot be laid out)."""
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
    title = read_title(song_dir)
    card = build_card(title, theme, n) if title else None
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
    elif theme.motion in ("beatpop", "phonk"):
        beat_times, drop_times, notes = load_beats_for_render(song_dir, duration)
        lines, skipped = beatpop.plan_beatpop(doc, theme, n, emphasis=emphasis, beats=beat_times,
                                              drops=drop_times, ahead=theme.motion == "phonk")
        lines.notes[:0] = notes
        mod, cache = ((phonk, phonk.NeonCache()) if theme.motion == "phonk"
                      else (beatpop, beatpop.PopCache()))
        sprites, parts = mod.build_sprites(lines, theme), mod.frame_parts
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
    if backdrop and not bg:
        raise RenderError("a backdrop needs a background: pass bg")
    scene = None
    if bg:   # here: numpy and the world's art load only for a background
        from .. import background
        from ..background.compose import Legibility, final_checks, with_background
        scene = background.build_scene(bg, background.song_facts(
            doc, emphasis, duration, n, theme.fps, song_dir.name, background.word_boxes(lines)))
        if backdrop:
            from ..background.backdrop import write_backdrop
            return write_backdrop(scene, bg, render_dir, audio, theme, n, t0)
        outputs["final"] = render_dir / f"final_{bg[0]}_{bg[1]}.mp4"
        legibility = Legibility()
    _remove([*outputs.values(), render_dir / REPORT])   # a failed run must not leave old results
    t1 = time.perf_counter()
    frames = (parts(k, lines, sprites, theme, cache) for k in range(n))
    frames = with_card(frames, card, theme) if card else frames
    if scene:
        frames = with_background(frames, scene, theme, legibility, bg)
    _encode(_ffmpeg_cmd(theme, codec, audio, outputs), frames, outputs)
    encode_s = time.perf_counter() - t1
    result = RenderResult(render_dir, outputs, n, 0.0, skipped, [], emphasis=[
        f'"{w["text"]}" (line {w["line"] + 1})' for w in doc["words"] if w["i"] in emphasis])
    t2 = time.perf_counter()
    result.checks = check_outputs(result, lines, theme, n)
    if card:
        result.checks += card_checks(result, card, theme)
        result.notes.append(f'title card: "{" / ".join(card.lines)}", 0.0-'
                            f"{card.stop / theme.fps:.1f} s (title.txt)")
    elif title == []:
        result.notes.append("title.txt has no text: no title card")
    extra = []
    if scene:
        result.checks += final_checks(outputs["final"], n, theme, legibility)
        note = background.fit_note(bg[0], theme.name)
        result.notes += [note] if note else []
        result.notes += [f"background: marked but untimed, nothing happens for it: {label}"
                         for label in scene.facts.untimed_marks]
        extra = background.report_lines(bg, scene, theme.name, legibility)
    check_s = time.perf_counter() - t2
    result.wall_s = time.perf_counter() - t0
    write_report(result, doc, codec=codec, theme=theme, encode_s=encode_s, check_s=check_s,
                 extra=extra)
    return result
