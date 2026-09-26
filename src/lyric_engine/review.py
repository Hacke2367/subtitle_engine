"""Review-only bake-off artifacts: the preview video, the per-variant run report, the comparison.

None of this is a product output (spec 02 §3). Nothing here creates or moves a word time: the
preview only pads how long a line stays on screen, and every word it shows is a word text from
words.json, which comes from lyrics.txt (red lines 1 and 2).
"""
from __future__ import annotations

import json
import math
import subprocess
from dataclasses import dataclass
from pathlib import Path

from .timing import MOSTLY_FLAGGED, REASONS, Word, flag_summary

# --- Preview: ASS burned onto a black 540x960 video with the song (plan §2.7) -------------------
PLAY_W, PLAY_H, FPS = 540, 960, 25
LINE_POS = r"\pos(270,480)"     # on every lyric event, so the two layers overlap exactly
LINE_PAD_S = 0.25               # a line appears up to this early and stays up to this late
WHITE, RED, YELLOW = "&HFFFFFF&", "&H0000FF&", "&H00FFFF&"   # ASS override colours are BGR
HIDDEN, SHOWN = "&HFF&", "&H00&"
PREVIEW_ASS = "preview.ass"     # fixed name, so the ffmpeg filter argument never needs escaping
ASS_HEADER = """\
[Script Info]
; Review preview only (spec 02), not a product output.
Title: {title}
ScriptType: v4.00+
PlayResX: {w}
PlayResY: {h}

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, \
Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, \
Alignment, MarginL, MarginR, MarginV, Encoding
Style: Lyric,Arial,40,&H00FFFFFF,&H00FFFFFF,&H00000000,&H00000000,-1,0,0,0,100,100,0,0,1,2,0,5,\
30,30,0,1
Style: Info,Arial,22,&H00BBBBBB,&H00BBBBBB,&H00000000,&H00000000,0,0,0,0,100,100,0,0,1,1,0,7,\
12,12,12,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text"""
LOWEST_N = 10                   # lowest-score words listed in a run report


@dataclass
class Disagreement:
    index: int
    text: str
    line: int
    starts: dict[str, float | None]   # variant -> start (None = not placed)
    earliest: float
    spread: float                     # latest start - earliest start, s


def write_ass(doc: dict, out_ass: Path, *, title: str) -> None:
    """Preview subtitles. Per line with a placed word: the whole line on layer 0, flagged words
    red. Per placed, non-flagged word: the same text on layer 1 with only that word visible, in
    yellow, until the next placed word starts (or its own end). Unplaced lines show nothing.
    """
    duration = float(doc["audio"]["duration_s"])
    events = [_dialogue(0, 0, duration, "Info", rf"{{\an7\pos(12,12)}}{_escape(title)}")]
    events += [_dialogue(0, s, min(s + 1, duration), "Info",
                         rf"{{\an9\pos(528,12)}}{s // 60:02d}:{s % 60:02d}")
               for s in range(math.ceil(duration))]

    lines: dict[int, list[dict]] = {}
    for w in doc["words"]:
        lines.setdefault(w["line"], []).append(w)
    shown = []                        # (first time, last time, words) per line with a placed word
    for words in lines.values():
        times = [t for w in words if _placed(w) for t in (w["start"], w["end"])]
        if times:
            shown.append((min(times), max(times), words))
    shown.sort(key=lambda item: item[0])
    spans = _padded([(lo, hi) for lo, hi, _ in shown])
    for (start, end), (_, _, words) in zip(spans, shown):
        events.append(_dialogue(0, start, end, "Lyric", _line_text(words)))
        events += _highlights(words)
    _write(out_ass, [ASS_HEADER.format(title=title, w=PLAY_W, h=PLAY_H), *events])


def render_preview(doc: dict, audio: Path, out_mp4: Path, *, title: str) -> Path:
    """Low-res review video: the preview.ass burned onto black, with the song's audio."""
    out_mp4 = Path(out_mp4).resolve()
    out_ass = out_mp4.with_name(PREVIEW_ASS)
    write_ass(doc, out_ass, title=title)
    duration = float(doc["audio"]["duration_s"])
    cmd = ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
           "-f", "lavfi", "-i", f"color=c=black:s={PLAY_W}x{PLAY_H}:r={FPS}:d={duration:.3f}",
           "-i", str(Path(audio).resolve()),
           "-map", "0:v", "-map", "1:a:0",   # the canvas, even if the audio file has a video
           "-vf", f"ass={PREVIEW_ASS}",       # relative to cwd: no "C:" escaping in the filter
           "-c:v", "libx264", "-preset", "veryfast", "-crf", "28", "-pix_fmt", "yuv420p",
           "-c:a", "aac", "-shortest", str(out_mp4)]
    try:
        proc = subprocess.run(cmd, cwd=out_ass.parent, capture_output=True, text=True,
                              encoding="utf-8", errors="replace")
    except FileNotFoundError as exc:
        raise RuntimeError("ffmpeg not found on PATH") from exc
    if proc.returncode != 0:
        tail = " | ".join(proc.stderr.strip().splitlines()[-5:])
        raise RuntimeError(f"ffmpeg preview failed for {out_mp4.name}: {tail}")
    return out_mp4


def write_run_report(doc: dict, out_md: Path, *, wall_s: float, reused: bool,
                     cost_note: str | None = None) -> None:
    """One variant's run: timing, cache reuse, every flagged word, the lowest-score words."""
    words = _words(doc)
    summary = flag_summary(words)
    aligner = doc["aligner"]
    out = [f"# Run report: {aligner['variant']}", ""]
    if summary["mostly_flagged"]:
        out += [f"> **Warning: {summary['share']:.0%} of the words are flagged** (limit "
                f"{MOSTLY_FLAGGED:.0%}). The lyrics probably don't match this audio (another "
                "version, missing or extra lines, trimmed audio). Don't use this words.json as "
                "a result.", ""]
    out += [f"- Song: `{doc['song']}`, audio `{doc['audio']['file']}` "
            f"({doc['audio']['duration_s']:.3f} s)",
            f"- Aligner: {aligner['variant']} on the {aligner['input']} audio, settings "
            f"`{json.dumps(aligner.get('settings', {}))}`",
            f"- Wall time: {wall_s:.1f} s",
            f"- Reused cached aligner result: {'yes' if reused else 'no'}"]
    if cost_note:
        out.append(f"- Cost: {cost_note}")
    out += ["", "## Flags", "",
            f"{summary['flagged']} of {summary['total']} words flagged ({summary['share']:.1%}).",
            "", "| Reason | Words |", "|---|---|",
            *(f"| {r} | {summary['by_reason'][r]} |" for r in REASONS),
            "", "## Flagged words", "",
            *_word_table([w for w in words if w.flagged], empty="No flagged words.")]
    lowest = sorted((w for w in words if w.score is not None),
                    key=lambda w: (w.score, w.index))[:LOWEST_N]
    out += ["", f"## {LOWEST_N} lowest-score words", "",
            "A low score can mean a spelling the aligner doesn't expect. The lyrics are never "
            "respelled automatically.", "",
            *_word_table(lowest, empty="The aligner reported no scores.")]
    _write(out_md, out)


def write_comparison(docs: dict[str, dict | None], errors: dict[str, str], out_md: Path, *,
                     top_n: int = 10) -> None:
    """A row per variant (docs: variant -> doc, or None if it produced nothing; errors: variant
    -> reason), then the top_n moments where the variants' start times differ most."""
    produced = {name: doc for name, doc in docs.items() if doc is not None}
    out = ["# Aligner bake-off: comparison", "",
           "| Variant | Result | Flagged | Report |", "|---|---|---|---|"]
    for name in dict.fromkeys([*docs, *errors]):
        doc = docs.get(name)
        if doc is None:
            out.append(f"| {name} | error: {_md(errors.get(name, 'no result'))} | - | - |")
            continue
        s = flag_summary(_words(doc))
        result = "ok, reused" if doc["aligner"].get("reused_cache") else "ok"
        if name in errors:
            result += f"; {_md(errors[name])}"
        warn = " **mostly flagged**" if s["mostly_flagged"] else ""
        out.append(f"| {name} | {result} | {s['flagged']} of {s['total']} ({s['share']:.0%})"
                   f"{warn} | [report]({name}/report.md) |")

    out += ["", "## Top disagreements", ""]
    rows = _disagreements(produced, top_n)
    if len(produced) < 2:
        out.append("Fewer than two variants produced a result, so there is nothing to compare.")
    elif not rows:
        out.append("No word was placed by two or more variants.")
    else:
        names = list(produced)
        out += ["Where the variants' start times differ most: scrub to these moments in the "
                "previews first. Times in seconds; `-` = not placed.", "",
                f"| At | i | Word | Line | {' | '.join(names)} | Spread (s) |",
                "|---" * (len(names) + 5) + "|"]
        out += [f"| {_mmss(r.earliest)} | {r.index} | {_md(r.text)} | {r.line + 1} | "
                f"{' | '.join(_sec(r.starts.get(n)) for n in names)} | {r.spread:.3f} |"
                for r in rows]
    _write(out_md, out)


# --- Preview helpers -----------------------------------------------------------------------------
def _placed(w: dict) -> bool:
    return w["start"] is not None and w["end"] is not None


def _padded(spans: list[tuple[float, float]]) -> list[tuple[float, float]]:
    """Pad each time-sorted (first, last) line span by LINE_PAD_S, clamped at 0. Neighbouring
    pads stop at the middle of the gap, so two lines never share the screen unless their words do.
    """
    out = []
    for k, (lo, hi) in enumerate(spans):
        start, end = lo - LINE_PAD_S, hi + LINE_PAD_S
        if k > 0:
            start = min(lo, max(start, (spans[k - 1][1] + lo) / 2))
        if k + 1 < len(spans):
            end = max(hi, min(end, (hi + spans[k + 1][0]) / 2))
        out.append((max(0.0, start), end))
    return out


def _line_text(words: list[dict], current: int | None = None) -> str:
    """The line as ASS text: the base layer (flagged words red), or only word `current`, yellow.
    Same text either way, so libass wraps both alike and the yellow word lands on the white one.
    """
    parts = []
    for k, w in enumerate(words):
        text = _escape(w["text"])
        if current is None:
            parts.append(rf"{{\c{RED}}}{text}{{\c{WHITE}}}" if w["flagged"] else text)
        else:
            parts.append(rf"{{\alpha{SHOWN}\c{YELLOW}}}{text}{{\alpha{HIDDEN}}}"
                         if k == current else text)
    prefix = rf"{{{LINE_POS}}}" if current is None else rf"{{{LINE_POS}\alpha{HIDDEN}}}"
    return prefix + " ".join(parts)


def _highlights(words: list[dict]) -> list[str]:
    """Layer-1 events of one line. Flagged or unplaced words are never lit (untrusted times)."""
    placed = [k for k, w in enumerate(words) if _placed(w)]
    events = []
    for n, k in enumerate(placed):
        w = words[k]
        if not w["flagged"]:
            nxt = words[placed[n + 1]]["start"] if n + 1 < len(placed) else w["end"]
            end = nxt if nxt > w["start"] else w["end"]    # a flagged next word may start earlier
            events.append(_dialogue(1, w["start"], end, "Lyric", _line_text(words, k)))
    return events


def _escape(text: str) -> str:
    """Literal text in ASS: "{" would open an override block and "\\N" would break the line."""
    return text.replace("\\", "\\\N{WORD JOINER}").replace("{", "\\{").replace("}", "\\}")


def _dialogue(layer: int, start: float, end: float, style: str, text: str) -> str:
    return f"Dialogue: {layer},{_ass_time(start)},{_ass_time(end)},{style},,0,0,0,,{text}"


def _ass_time(t: float) -> str:
    """H:MM:SS.cc (ASS has centisecond resolution)."""
    cs = max(0, round(t * 100))
    return f"{cs // 360000}:{cs // 6000 % 60:02d}:{cs // 100 % 60:02d}.{cs % 100:02d}"


# --- Report helpers ------------------------------------------------------------------------------
def _words(doc: dict) -> list[Word]:
    return [Word(w["i"], w["text"], w["line"], w["start"], w["end"], w["score"], w["flagged"],
                 list(w["reasons"])) for w in doc["words"]]


def _disagreements(docs: dict[str, dict], top_n: int) -> list[Disagreement]:
    """Words at least two variants placed, by start-time spread (largest first), top_n of them."""
    starts: dict[int, dict[str, float | None]] = {}
    info: dict[int, tuple[str, int]] = {}
    for name, doc in docs.items():
        for w in doc["words"]:
            starts.setdefault(w["i"], {})[name] = w["start"]
            info.setdefault(w["i"], (w["text"], w["line"]))
    rows = []
    for i, per_variant in starts.items():
        known = [s for s in per_variant.values() if s is not None]
        if len(known) >= 2:
            rows.append(Disagreement(i, *info[i], per_variant, min(known),
                                     round(max(known) - min(known), 3)))
    rows.sort(key=lambda r: (-r.spread, r.index))
    return rows[:top_n]


def _word_table(words: list[Word], *, empty: str) -> list[str]:
    if not words:
        return [empty]
    return ["| i | Text | Line | Start | End | Score | Reasons |", "|---|---|---|---|---|---|---|",
            *(f"| {w.index} | {_md(w.text)} | {w.line + 1} | {_sec(w.start)} | {_sec(w.end)} | "
              f"{'-' if w.score is None else f'{w.score:.3g}'} | {', '.join(w.reasons) or '-'} |"
              for w in words)]


def _md(text: str) -> str:
    """Safe inside a markdown table cell."""
    return " ".join(text.split()).replace("|", "\\|")


def _sec(t: float | None) -> str:
    return "-" if t is None else f"{t:.3f}"


def _mmss(t: float) -> str:
    """mm:ss.s, rounded to the tenth first so 59.96 reads 01:00.0, not 00:60.0."""
    tenths = round(abs(t) * 10)
    return f"{'-' if t < 0 else ''}{tenths // 600:02d}:{tenths % 600 // 10:02d}.{tenths % 10}"


def _write(path: Path, lines: list[str]) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
