"""`python -m voice_subs.cli subs <video-or-audio>` -> a Roman-script `.srt` beside it.

One command, four stages: ffmpeg pulls the audio out, Scribe transcribes it, `roman.py` writes
the Hindi words in Roman, `cues.py` groups them into cues and writes the file. The transcript is
kept, so fixing a word by hand and running again costs no API call (red line 3).
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from . import cues as cues_mod
from . import media, scribe, transcript

PACKAGE_ROOT = Path(__file__).resolve().parents[2]      # v2/
WORK_ROOT = PACKAGE_ROOT / "voices"                     # gitignored (red line 4)
AUDIO_NAME = "audio.mp3"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="voice-subs", description="A voice recording or video -> a Roman-script .srt")
    sub = parser.add_subparsers(dest="command", required=True)

    subs = sub.add_parser("subs", help="make subtitles for one video or audio file")
    subs.add_argument("source", type=Path, help="the video or audio file")
    subs.add_argument("--out", type=Path, default=None,
                      help="where to write the .srt (default: the work folder)")
    subs.add_argument("--lang", default=None, metavar="CODE",
                      help="force the spoken language, e.g. hin or eng (default: detect)")
    subs.add_argument("--work", type=Path, default=None,
                      help=f"work folder for the audio and transcript (default: {WORK_ROOT})")
    subs.add_argument("--fresh", action="store_true",
                      help="transcribe again, replacing the transcript and any hand edits")
    subs.add_argument("--devanagari", action="store_true",
                      help="keep the engine's own script instead of writing Hindi in Roman")
    subs.add_argument("--overwrite", action="store_true", help="replace an existing .srt")
    subs.add_argument("--preview", action="store_true",
                      help="also write preview.mp4, the video with the subtitles drawn on it")

    args = parser.parse_args(argv)
    try:
        return _subs(args)
    except (media.MediaError, scribe.ScribeError, transcript.TranscriptError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1


def _subs(args: argparse.Namespace) -> int:
    source = args.source.expanduser()
    if not source.is_file():
        raise media.MediaError(f"no such file: {source}")
    if source.suffix.lower() not in media.MEDIA_SUFFIXES:
        raise media.MediaError(f"{source.suffix or 'that file'} is not a video or audio file")

    work = (args.work or WORK_ROOT / _slug(source.stem)).expanduser()
    audio = work / AUDIO_NAME
    out = (args.out or work / f"{_slug(source.stem)}.srt").expanduser()
    if out.exists() and not args.overwrite:
        raise media.MediaError(f"{out} already exists; pass --overwrite to replace it")

    print(f"[1/4] audio  <- {source.name}")
    media.extract_audio(source, audio)
    seconds = media.duration(audio)
    fingerprint = media.fingerprint(audio)
    print(f"      {seconds / 60:.1f} min ({seconds:.1f} s), {audio.stat().st_size / 1e6:.1f} MB")

    data = _transcript(work, source, audio, seconds, fingerprint, args)

    timed = transcript.timed_words(data)
    cues = cues_mod.to_cues(timed, duration=seconds)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(cues_mod.to_srt(cues), encoding="utf-8")

    print(f"[4/4] subtitles -> {out}")
    _report(data, timed, cues)
    if args.preview:
        preview = media.burn_subtitles(source, out, work / "preview.mp4")
        print(f"      preview (review only) -> {preview}")
    return 0


def _transcript(work: Path, source: Path, audio: Path, seconds: float, fingerprint: str,
                args: argparse.Namespace) -> dict:
    """The transcript for this audio: the kept one if it fits, else one new call to the engine."""
    path = work / transcript.NAME
    if path.is_file() and not args.fresh:
        data = transcript.load(path)
        if not transcript.matches_audio(data, fingerprint):
            # Red line 3: a transcript may hold the user's own corrections.
            raise transcript.TranscriptError(
                f"{path} was made from different audio ({data['source'].get('name')!r}).\n"
                "  Pass --fresh to transcribe again (this replaces it, and any hand edits),\n"
                "  or --work DIR to keep both.")
        print(f"[2/4] transcript: reusing {path} ({len(data['words'])} words, edits kept)")
        print("[3/4] cues: from the kept transcript (no API call)")
        return data

    print(f"[2/4] transcript: one call to {scribe.MODEL}"
          f"{'' if not args.lang else f' (language {args.lang})'} ...")
    response = scribe.transcribe(audio, language=args.lang)
    data = transcript.from_scribe(response, source=source.name, audio=audio.name,
                                 duration=seconds, fingerprint=fingerprint,
                                 to_roman=not args.devanagari)
    transcript.save(data, path)
    print(f"[3/4] transcript -> {path}")
    return data


def _report(data: dict, timed: list[dict], cues: list[cues_mod.Cue]) -> None:
    engine = data.get("engine", {})
    language, confidence = engine.get("language"), engine.get("confidence")
    said = f"{language}" + (f" ({confidence:.0%} sure)" if isinstance(confidence, float) else "")
    print(f"      language {said}, script {engine.get('script')}, "
          f"{len(data['words'])} words, {len(cues)} cues")
    untimed = len(data["words"]) - len(timed)
    if untimed:
        print(f"      {untimed} word(s) had no timing and are not in the .srt (never guessed)")
    for flag in data.get("flags", []):
        print(f"      ! {flag}")
    if cues:
        print(f"      first cue: {cues[0].text[:60]!r}")


def _slug(stem: str) -> str:
    """A file name safe for a folder: the source's own name, with odd characters flattened."""
    kept = [c if (c.isalnum() or c in "-_.") else "-" for c in stem.strip()]
    return "".join(kept).strip("-.") or "clip"


if __name__ == "__main__":
    raise SystemExit(main())
