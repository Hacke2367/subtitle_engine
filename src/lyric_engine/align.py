"""Stage 1: song audio + lyrics.txt -> words.json via an alignment API or a local model.

Never renders. Never alters lyrics text. Words it cannot place are flagged, never estimated.
Bake-off of aligner variants: docs/specs/02_word_alignment.md, plan 02_word_alignment_impl.md.
"""
from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from . import timing
from .timing import Lyrics, RawWord


@dataclass(frozen=True)
class Variant:
    name: str
    engine: str                # "eleven" | "local"
    input: str                 # "raw" = original audio, "vocals" = isolated vocals
    min_score: float | None    # low_confidence threshold; None until calibrated (plan decision 6)


VARIANTS = (
    Variant("E-raw", "eleven", "raw", None),
    Variant("E-vocals", "eleven", "vocals", None),
    Variant("L-vocals", "local", "vocals", None),
)
DEFAULT_VARIANT: str | None = "L-vocals"   # owner-confirmed (D-009, H-010)
SETTINGS_VERSION = 2                 # bump when an engine changes enough to invalidate caches
AUDIO_EXTS = {".mp3", ".wav", ".m4a", ".flac", ".ogg", ".aac", ".mp4", ".mov", ".mkv", ".webm"}

Engine = Callable[[Path, list[str]], "tuple[list[RawWord], dict]"]


@dataclass
class RunResult:
    variant: Variant
    doc: dict | None = None
    error: str | None = None
    wall_s: float = 0.0
    reused: bool = False
    review_error: str | None = None   # words.json is fine, but the report/preview failed


def song_paths(song_dir: Path) -> tuple[Path, Path]:
    audio = [p for p in sorted(song_dir.glob("audio.*")) if p.suffix.lower() in AUDIO_EXTS]
    if len(audio) != 1:
        raise FileNotFoundError(f"{song_dir}: expected exactly one audio.<ext> file, found {len(audio)}")
    lyrics = song_dir / "lyrics.txt"
    if not lyrics.exists():
        raise FileNotFoundError(f"{song_dir}: lyrics.txt not found")
    return audio[0], lyrics


def probe_duration(audio: Path) -> float:
    proc = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                           "-of", "csv=p=0", str(audio)], capture_output=True, text=True)
    if proc.returncode != 0 or not proc.stdout.strip():
        raise RuntimeError(f"ffprobe could not read {audio.name}: {proc.stderr.strip()}")
    return float(proc.stdout.strip())


def _engine(name: str) -> Engine:
    # Lazy imports: the local engine pulls in torch, which E-variants and tests don't need.
    if name == "eleven":
        from . import eleven
        return eleven.align
    from . import local_aligner
    return local_aligner.align


def input_audio(song_dir: Path, variant: Variant, audio: Path, fresh: bool) -> Path:
    if variant.input == "raw":
        return audio
    from . import vocals
    return vocals.isolate_vocals(audio, song_dir / "work" / "vocals.wav", fresh=fresh)


def _cache_key(inp: Path, lyrics: Lyrics, variant: Variant) -> str:
    parts = f"{timing.sha256_file(inp)}|{lyrics.sha256}|{variant.name}|{SETTINGS_VERSION}"
    return hashlib.sha256(parts.encode()).hexdigest()


def _rounded(raw: list[RawWord]) -> list[RawWord]:
    # Rounded once, before caching, so words.json can be checked against raw.json exactly.
    def r(x: float | None, nd: int) -> float | None:
        return None if x is None else round(float(x), nd)
    return [RawWord(r(w.start, 3), r(w.end, 3), r(w.score, 4)) for w in raw]


def _load_cache(path: Path, key: str) -> list[RawWord] | None:
    if not path.exists():
        return None
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("key") != key:
        return None
    return [RawWord(*item) for item in data["raw"]]


def _redact(text: str) -> str:
    from . import eleven
    key = eleven.load_api_key()
    return eleven.redact(text, key) if key else text


def run_variant(song_dir: Path, variant: Variant, *, fresh: bool = False, artifacts: bool = True,
                engine: Engine | None = None) -> RunResult:
    """Align one variant into song_dir/bakeoff/<variant>/ (raw.json cache, words.json, review)."""
    result = RunResult(variant)
    out_dir = song_dir / "bakeoff" / variant.name
    t0 = time.perf_counter()
    try:
        audio, lyrics_path = song_paths(song_dir)
        lyrics = timing.read_lyrics(lyrics_path)            # rejects annotations before any engine runs
        inp = input_audio(song_dir, variant, audio, fresh)
        key = _cache_key(inp, lyrics, variant)
        raw_path = out_dir / "raw.json"
        raw = None if fresh else _load_cache(raw_path, key)
        if raw is None:
            align_fn = engine or _engine(variant.engine)
            # The local CTC engine can also anchor at line breaks (keeps an unwritten repeat
            # from dragging a line across it); the API takes plain text only.
            extra = {"lines": [li for _, li in lyrics.words]} if variant.engine == "local" else {}
            raw, native = align_fn(inp, [text for text, _ in lyrics.words], **extra)
            raw = _rounded(raw)
            out_dir.mkdir(parents=True, exist_ok=True)
            raw_path.write_text(json.dumps({"key": key, "variant": variant.name,
                                            "raw": [[w.start, w.end, w.score] for w in raw],
                                            "native": native}, ensure_ascii=False),
                                encoding="utf-8")
        else:
            result.reused = True

        words = timing.build_words(lyrics, raw)
        duration = probe_duration(audio)
        timing.apply_flags(words, duration, variant.min_score)
        aligner = {"variant": variant.name, "input": variant.input,
                   "settings": {"min_score": variant.min_score, "settings_version": SETTINGS_VERSION},
                   "reused_cache": result.reused}
        doc = timing.make_doc(song_dir.name, audio, duration, timing.sha256_file(audio), lyrics,
                              aligner, words)
        errors = timing.validate(doc)
        if errors:  # our own output must always validate; anything else is a bug, not a result
            raise AssertionError(f"built an invalid words.json: {errors[:3]}")
        timing.save_words(out_dir / "words.json", doc)
        result.doc = doc
    except Exception as exc:  # every failure becomes a named report row, never a silent skip
        result.error = _redact(f"{type(exc).__name__}: {exc}")
    result.wall_s = time.perf_counter() - t0

    if result.doc and artifacts:
        try:  # a review failure must not stop the other variants or lose this words.json
            from . import review
            review.write_run_report(result.doc, out_dir / "report.md", wall_s=result.wall_s,
                                    reused=result.reused)
            review.render_preview(result.doc, audio, out_dir / "preview.mp4", title=variant.name)
        except Exception as exc:
            result.review_error = _redact(f"{type(exc).__name__}: {exc}")
    return result


def verify_against_raw(variant_dir: Path) -> list[str]:
    """Red line 1 check: every time in words.json is exactly what the aligner returned."""
    doc = timing.load_words(variant_dir / "words.json")
    raw = json.loads((variant_dir / "raw.json").read_text(encoding="utf-8"))["raw"]
    if len(raw) != len(doc["words"]):
        return [f"raw.json has {len(raw)} words, words.json has {len(doc['words'])}"]
    return [f"word {w['i']} (\"{w['text']}\"): time {w['start']}-{w['end']} is not the aligner's "
            f"{r[0]}-{r[1]}"
            for w, r in zip(doc["words"], raw) if (w["start"], w["end"]) != (r[0], r[1])]


def _flagged(doc: dict) -> int:
    return sum(1 for w in doc["words"] if w["flagged"])


def bakeoff(song_dir: Path, *, fresh: bool = False) -> int:
    _, lyrics_path = song_paths(song_dir)
    timing.read_lyrics(lyrics_path)  # fail fast on unusable lyrics (LyricsError → exit 2 in cli)
    results = [run_variant(song_dir, v, fresh=fresh) for v in VARIANTS]

    from . import review
    review.write_comparison({r.variant.name: r.doc for r in results},
                            {r.variant.name: r.error for r in results if r.error},
                            song_dir / "bakeoff" / "comparison.md")
    print(f"{'variant':<10} {'status':<8} {'flagged':>8} {'wall s':>7}")
    for r in results:
        status = "error" if r.error else ("reused" if r.reused else "ok")
        flagged = f"{_flagged(r.doc)}/{len(r.doc['words'])}" if r.doc else "-"
        print(f"{r.variant.name:<10} {status:<8} {flagged:>8} {r.wall_s:>7.1f}")
        for problem in (r.error, r.review_error and f"review: {r.review_error}"):
            if problem:
                print(f"  {problem}")
    print(f"comparison: {song_dir / 'bakeoff' / 'comparison.md'}")
    return 0 if all(r.doc and not r.review_error for r in results) else 1


def align_song(song_dir: Path, *, variant: str | None = None, fresh: bool = False,
               overwrite: bool = False) -> int:
    """Normal use: default (or named) variant → song_dir/words.json, the file the owner edits."""
    name = variant or DEFAULT_VARIANT
    if name is None:
        print("error: no default aligner chosen yet; run bakeoff or pass --variant", file=sys.stderr)
        return 2
    target = song_dir / "words.json"
    if target.exists() and not overwrite:
        # It may hold the owner's hand corrections: never overwrite them silently.
        print(f"error: {target} exists (may contain your corrections); pass --overwrite "
              f"(the old file is kept as words.json.bak)", file=sys.stderr)
        return 2
    chosen = next((v for v in VARIANTS if v.name == name), None)
    if chosen is None:
        print(f"error: unknown aligner variant {name!r}", file=sys.stderr)
        return 2
    r = run_variant(song_dir, chosen, fresh=fresh, artifacts=False)
    if r.error:
        print(f"error: {r.error}", file=sys.stderr)
        return 1
    if target.exists():
        shutil.copyfile(target, target.with_name("words.json.bak"))
    shutil.copyfile(song_dir / "bakeoff" / chosen.name / "words.json", target)
    note = " (cached alignment reused)" if r.reused else ""
    print(f"{target}: {len(r.doc['words'])} words, {_flagged(r.doc)} flagged{note}")
    return 0
