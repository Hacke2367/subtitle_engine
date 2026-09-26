"""Command-line entry point for a songs/<song>/ folder.

    python -m lyric_engine.cli bakeoff songs/<song> [--fresh]
    python -m lyric_engine.cli align songs/<song> [--variant NAME] [--fresh] [--overwrite]
    python -m lyric_engine.cli validate songs/<song>/words.json [--song songs/<song>]
    python -m lyric_engine.cli render songs/<song> [--theme NAME] [--codec prores|png|qtrle]
                                      [--allow-flagged]
    python -m lyric_engine.cli clip songs/<full-song> --from 0:27 --to 0:57 [--out songs/<clip>]
    python -m lyric_engine.cli make songs/<song> [--theme NAME] [--codec ...] [--allow-flagged]
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from . import align, timing
from .theme import THEMES


def _validate(path: Path, song: Path | None) -> int:
    try:
        doc = timing.load_words(path)
    except json.JSONDecodeError as exc:  # a hand-edit typo: point at it instead of a traceback
        print(f"{path}: not valid JSON at line {exc.lineno}, column {exc.colno}: {exc.msg}")
        return 1
    audio_path, lyrics_path = align.song_paths(song) if song else (None, None)
    errors = timing.validate(doc, lyrics_path, audio_path)
    if (path.parent / "raw.json").exists():   # machine output: times must be the aligner's own
        errors += align.verify_against_raw(path.parent)
    print("valid" if not errors else "\n".join(errors))
    return 0 if not errors else 1


def _render(song: Path, codec: str | None, allow_flagged: bool, theme: str) -> int:
    from . import layout, render   # lazy: fonts/Pillow only when rendering
    try:
        result = render.render(song, codec=codec, allow_flagged=allow_flagged,
                               theme=THEMES[theme])
    except (render.RenderError, layout.LayoutError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    for name, path in result.outputs.items():
        print(f"{name}: {path}")
    print(f"frames: {result.frames}  wall: {result.wall_s:.1f} s")
    print("emphasis: " + (", ".join(result.emphasis) or "none"))
    if result.skipped_lines:
        print("not shown (no timed word): lines " + ", ".join(str(n + 1) for n in result.skipped_lines))
    for note in result.notes:
        print(f"note: {note}")
    print("checks: pass" if not result.checks
          else "checks: FAIL\n  " + "\n  ".join(result.checks))
    return 0 if not result.checks else 1


def _seconds(text: str) -> float:
    """27, 27.5, 0:27 or 1:05.5 -> seconds."""
    try:
        parts = [float(p) for p in text.split(":")]
    except ValueError:
        raise argparse.ArgumentTypeError(f"not a time: {text!r} (use 27, 0:27 or 1:05.5)") from None
    if len(parts) > 2 or any(p < 0 for p in parts):
        raise argparse.ArgumentTypeError(f"not a time: {text!r} (use 27, 0:27 or 1:05.5)")
    return parts[0] * 60 + parts[1] if len(parts) == 2 else parts[0]


def _clip(song: Path, start: float, end: float, out: Path | None) -> int:
    from . import workflow
    out = out or song.parent / f"{song.name}_{int(start)}-{int(end)}"
    try:
        plan = workflow.clip_song(song, start, end, out)
    except workflow.ClipError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    print(f"{out}: {plan.end - plan.start:.1f} s ({plan.start:.2f}-{plan.end:.2f} s of "
          f"{song.name}), lyric lines {plan.lines[0] + 1}-{plan.lines[-1] + 1}")
    for warning in plan.warnings:
        print(f"warning: {warning}")
    print(f"next: python -m lyric_engine.cli make {out}")
    return 0


def _make(song: Path, codec: str | None, allow_flagged: bool, theme: str) -> int:
    from . import workflow
    code = workflow.ensure_aligned(song)
    return code if code != 0 else _render(song, codec, allow_flagged, theme)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="lyric_engine")
    sub = parser.add_subparsers(dest="cmd", required=True)
    b = sub.add_parser("bakeoff", help="run every aligner variant and compare them")
    b.add_argument("song_dir", type=Path)
    b.add_argument("--fresh", action="store_true", help="ignore cached aligner results")
    a = sub.add_parser("align", help="align with the default (or named) variant → words.json")
    a.add_argument("song_dir", type=Path)
    a.add_argument("--variant", choices=[v.name for v in align.VARIANTS])
    a.add_argument("--fresh", action="store_true")
    a.add_argument("--overwrite", action="store_true", help="replace an existing words.json")
    v = sub.add_parser("validate", help="check a words.json (and staleness against its song)")
    v.add_argument("words_json", type=Path)
    v.add_argument("--song", type=Path)
    r = sub.add_parser("render", help="words.json → overlay.mov + overlay_green.mp4 + preview.mp4")
    r.add_argument("song_dir", type=Path)
    r.add_argument("--theme", choices=list(THEMES), default="soft-romantic",
                   help="look of the overlay; outputs go to render/<theme>/ (default: soft-romantic)")
    r.add_argument("--codec", choices=["prores", "png", "qtrle"],
                   help="alpha codec for overlay.mov (default: theme's, provisional until CapCut test)")
    r.add_argument("--allow-flagged", action="store_true",
                   help="render despite flagged words; untimed ones are shown static, never animated")
    c = sub.add_parser("clip", help="cut whole lyric lines of an aligned song into a new song folder")
    c.add_argument("song_dir", type=Path, help="an aligned full song (has words.json)")
    c.add_argument("--from", dest="start", type=_seconds, required=True, help="e.g. 27 or 0:27")
    c.add_argument("--to", dest="end", type=_seconds, required=True, help="e.g. 57 or 0:57")
    c.add_argument("--out", type=Path, help="new song folder (default: <song>_<from>-<to>)")
    m = sub.add_parser("make", help="align (if not done yet) and render a song folder")
    m.add_argument("song_dir", type=Path)
    m.add_argument("--theme", choices=list(THEMES), default="soft-romantic")
    m.add_argument("--codec", choices=["prores", "png", "qtrle"])
    m.add_argument("--allow-flagged", action="store_true")
    args = parser.parse_args(argv)

    try:
        if args.cmd == "bakeoff":
            return align.bakeoff(args.song_dir, fresh=args.fresh)
        if args.cmd == "align":
            return align.align_song(args.song_dir, variant=args.variant, fresh=args.fresh,
                                    overwrite=args.overwrite)
        if args.cmd == "render":
            return _render(args.song_dir, args.codec, args.allow_flagged, args.theme)
        if args.cmd == "clip":
            return _clip(args.song_dir, args.start, args.end, args.out)
        if args.cmd == "make":
            return _make(args.song_dir, args.codec, args.allow_flagged, args.theme)
        return _validate(args.words_json, args.song)
    except (timing.LyricsError, FileNotFoundError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
