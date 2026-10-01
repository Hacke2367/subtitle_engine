"""Engine-made backgrounds under a theme's lyrics (H-023, spec 17): a look chosen per render with
`--bg LOOK[:MOOD]`, drawn by code and written as a finished short with audio.

This module only knows names and song facts (no numpy), so the CLI can check `--bg` cheaply; the
drawing lives in the look modules, imported when a render needs one. A look reads the song's
length, aligned word times and their places on screen, the marked words, line starts and the
folder name (its seed), never what the words say, so any lyric works (owner's constraint, H-024).
The looks are the owner-approved romantic ones (docs/backgrounds/romantic_lights.md, H-034 to
H-036); each must look like its approved sample.

A look's module has a `Scene(facts)` with `describe()` (a line for the report) and
`frame(k, ink)`: frame k as (H, W, 3) uint8 sRGB, where `ink` is the box of the text drawn over
that frame (x0, y0, x1, y1), or None."""
from __future__ import annotations

import importlib
import zlib
from dataclasses import dataclass

# A look is a module of this package with the same name and a `Scene(facts)` (see below); first
# mood = default. Adding a look = its file + one line here.
WORLDS = {"rain": ("evening",), "fog": ("moonlight",), "milan": ("night",), "khaali": ("night",),
          "chaand": ("night",), "aakhri": ("dusk",), "jaali": ("dawn",),
          "rail": ("night",)}
DESIGNED: dict[str, tuple[str, ...]] = {}
SOFT = {"soft-romantic", "soft-romantic-v2", "cinematic", "lofi-minimal", "lofi-typewriter",
        "romantic-soft", "classic-sher"}
FITS = {look: SOFT for look in WORLDS}   # the themes each look is made for
LYRIC_AREA = (60, 380, 960, 1540)   # x0, y0, x1, y1: where lyrics may sit (the themes' safe zone)
DEFAULT_CENTRE = (540.0, 1150.0)


@dataclass(frozen=True)
class SongFacts:
    name: str                       # the song folder's name ...
    seed: int                       # ... and the seed made from it
    duration: float
    n: int                          # frames
    fps: int
    words: tuple                    # ((start, marked, cx, cy), ...) of timed words, in time order
    line_starts: tuple              # first timed word of each shown line
    last_line_s: float | None       # the last shown line's first timed word
    lyric_centre: tuple             # (x, y) centre of the lyric block on screen
    untimed_marks: tuple            # labels of marked words with no time (nothing happens: red line 1)
    lyric_box: tuple | None = None  # (x0, y0, x1, y1) around every word's box, None without boxes

    @property
    def starts(self) -> list[float]:
        return [w[0] for w in self.words]

    @property
    def marks(self) -> list[tuple]:
        return [w for w in self.words if w[1]]

    @property
    def block_centre(self) -> tuple[float, float]:
        """The centre of the lyric block (every word's box), or the default place without boxes."""
        if self.lyric_box is None:
            return DEFAULT_CENTRE
        x0, y0, x1, y1 = self.lyric_box
        return (x0 + x1) / 2, (y0 + y1) / 2


def parse_bg(text: str) -> tuple[str, str]:
    """'rain' or 'rain:evening' -> ('rain', 'evening'); ValueError naming the built choices."""
    world, _, mood = text.partition(":")
    built = ", ".join(f"{w} ({'/'.join(m)})" for w, m in WORLDS.items())
    if world not in WORLDS:
        raise ValueError(f"unknown background {world!r}; built: {built}")
    mood = mood or WORLDS[world][0]
    if mood not in WORLDS[world]:
        if mood in DESIGNED.get(world, ()):
            raise ValueError(f"{world}:{mood} is designed but not built yet; "
                             f"built: {', '.join(WORLDS[world])}")
        raise ValueError(f"unknown mood {mood!r} for {world}; built: {', '.join(WORLDS[world])}")
    return world, mood


def seed_of(name: str) -> int:
    """Stable across runs and machines (Python's hash() is not)."""
    return zlib.crc32(name.encode("utf-8"))


def word_boxes(lines) -> dict:
    """{words.json index: WordBox} from any theme's render plan (every plan's lines carry
    `.words` whose items have `.box`)."""
    boxes = {}
    for line in getattr(lines, "lines", lines):   # Beat Pop's plan (Show) keeps its lines inside
        for wp in getattr(line, "words", ()):
            box = getattr(wp, "box", None)
            if box is not None:
                boxes.setdefault(box.index, box)
    return boxes


def song_facts(doc: dict, emphasis, duration: float, n: int, fps: int, name: str,
               boxes: dict | None = None) -> SongFacts:
    boxes = boxes or {}
    words, untimed, line_first = [], [], {}
    for w in doc["words"]:
        marked = w["i"] in emphasis
        if w["start"] is None or w["end"] is None:
            if marked:
                untimed.append(f'"{w["text"]}" (line {w["line"] + 1})')   # for the report only
            continue
        box = boxes.get(w["i"])
        cx, cy = ((box.x + box.w / 2, box.y + box.h / 2) if box is not None else DEFAULT_CENTRE)
        words.append((w["start"], marked, cx, cy))
        line_first[w["line"]] = min(line_first.get(w["line"], w["start"]), w["start"])
    words.sort(key=lambda x: x[0])
    block = None
    if boxes:
        block = (min(b.x for b in boxes.values()), min(b.y for b in boxes.values()),
                 max(b.x + b.w for b in boxes.values()), max(b.y + b.h for b in boxes.values()))
    centre = ((block[0] + block[2]) / 2, (block[1] + block[3]) / 2 - 90) if block else DEFAULT_CENTRE
    last = line_first[max(line_first)] if line_first else None
    return SongFacts(name, seed_of(name), duration, n, fps, tuple(words),
                     tuple(sorted(line_first.values())), last, centre, tuple(untimed), block)


def build_scene(bg: tuple[str, str], facts: SongFacts):
    """The look's scene for this song (numpy and the art load here)."""
    world, _mood = bg
    return importlib.import_module(f".{world}", __package__).Scene(facts)


def fit_note(world: str, theme_name: str) -> str | None:
    if theme_name in FITS[world]:
        return None
    return (f"background: {theme_name} is outside the {world} look's range "
            f"({', '.join(sorted(FITS[world]))})")


def report_lines(bg: tuple[str, str], scene, theme_name: str, log) -> list[str]:
    """The report's Background section (only with --bg)."""
    world, mood = bg
    f = scene.facts
    note = fit_note(world, theme_name)
    lines = ["## Background", "",
             f"- Look: {world}, mood {mood}" + (f" ({note})" if note else f" ({theme_name} fits)"),
             f"- Seed {f.seed} (from the folder name `{f.name}`)",
             f"- {scene.describe()}",
             f"- Words {len(f.words)}, marked {len(f.marks)}, lines {len(f.line_starts)}"]
    if f.untimed_marks:
        lines.append("- Marked but untimed, nothing happens for them: " + ", ".join(f.untimed_marks))
    if log.frames:
        lines.append(f"- Background drawing and compose: {1000 * log.draw_s / log.frames:.0f} ms "
                     f"per frame ({log.draw_s:.1f} s)")
    if log.worst:
        k, c = log.worst
        lines.append(f"- Legibility: lowest contrast {c:.2f}:1 at frame {k} "
                     f"(rule: at least 3:1 around the text); "
                     + ("pass" if not log.failed else f"{len(log.failed)} frame(s) below"))
    return lines
