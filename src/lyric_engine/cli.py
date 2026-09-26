"""Command-line entry point for a songs/<song>/ folder.

    python -m lyric_engine.cli bakeoff songs/<song> [--fresh]
    python -m lyric_engine.cli align songs/<song> [--variant NAME] [--fresh] [--overwrite]
    python -m lyric_engine.cli validate songs/<song>/words.json [--song songs/<song>]
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from . import align, timing


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
    args = parser.parse_args(argv)

    try:
        if args.cmd == "bakeoff":
            return align.bakeoff(args.song_dir, fresh=args.fresh)
        if args.cmd == "align":
            return align.align_song(args.song_dir, variant=args.variant, fresh=args.fresh,
                                    overwrite=args.overwrite)
        return _validate(args.words_json, args.song)
    except (timing.LyricsError, FileNotFoundError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
