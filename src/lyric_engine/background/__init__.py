"""Engine-made backgrounds under a theme's lyrics (H-023, spec 17): a world with moods, chosen per
render with `--bg WORLD[:MOOD]`, drawn by code and written as a finished short with audio.

This module only knows names and song facts (no numpy), so the CLI can check `--bg` cheaply; the
drawing lives in the world modules (`room`), imported when a render needs one. A world reads the
song's length, aligned word times, the marked words' times and the folder name (its seed), never
what the words say, so any lyric works (owner's constraint, H-024)."""
from __future__ import annotations

import zlib
from dataclasses import dataclass

WORLDS = {"room": ("dusk",)}   # built moods; the first is the world's default
DESIGNED = {"room": ("morning", "dusk", "rain", "moonlit", "mist", "festival")}
FITS = {"room": {"soft-romantic", "soft-romantic-v2", "cinematic", "lofi-minimal",
                 "lofi-typewriter"}}
LYRIC_AREA = (60, 380, 960, 1540)   # x0, y0, x1, y1: the same in every mood (the safe zone)


@dataclass(frozen=True)
class SongFacts:
    name: str                       # the song folder's name ...
    seed: int                       # ... and the seed made from it
    duration: float
    n: int                          # frames
    fps: int
    last_line_s: float | None       # the last shown line's first timed word (words.json start)
    marks: tuple                    # ((start, label), ...) of timed *marked* words
    untimed_marks: tuple            # labels of marked words with no time (no gust: red line 1)


def parse_bg(text: str) -> tuple[str, str]:
    """'room' or 'room:dusk' → ('room', 'dusk'); ValueError naming the built choices."""
    world, _, mood = text.partition(":")
    built = ", ".join(f"{w} (moods: {', '.join(m)})" for w, m in WORLDS.items())
    if world not in WORLDS:
        raise ValueError(f"unknown background {world!r}; built: {built}")
    mood = mood or WORLDS[world][0]
    if mood not in WORLDS[world]:
        if mood in DESIGNED.get(world, ()):
            raise ValueError(f"{world}:{mood} is designed but not built yet (plan step 23); "
                             f"built: {', '.join(WORLDS[world])}")
        raise ValueError(f"unknown mood {mood!r} for {world}; built: {', '.join(WORLDS[world])}")
    return world, mood


def seed_of(name: str) -> int:
    """Stable across runs and machines (Python's hash() is not)."""
    return zlib.crc32(name.encode("utf-8"))


def song_facts(doc: dict, emphasis, duration: float, n: int, fps: int, name: str) -> SongFacts:
    timed = [w for w in doc["words"] if w["start"] is not None and w["end"] is not None]
    last_line_s = None
    if timed:
        last = max(w["line"] for w in timed)
        last_line_s = min(w["start"] for w in timed if w["line"] == last)
    marks, untimed = [], []
    for w in doc["words"]:
        if w["i"] in emphasis:
            label = f'"{w["text"]}" (line {w["line"] + 1})'   # for the report only
            if w["start"] is not None and w["end"] is not None:
                marks.append((w["start"], label))
            else:
                untimed.append(label)
    return SongFacts(name, seed_of(name), duration, n, fps, last_line_s, tuple(marks),
                     tuple(untimed))


def build_scene(bg: tuple[str, str], facts: SongFacts):
    """The world's scene for this song (numpy and the art load here)."""
    world, mood = bg
    from . import room   # the only world so far
    return room.Room(facts, room.MOODS[mood])


def fit_note(world: str, theme_name: str) -> str | None:
    if theme_name in FITS[world]:
        return None
    return (f"background: {theme_name} is outside the {world}'s range "
            f"({', '.join(sorted(FITS[world]))})")


def report_lines(bg: tuple[str, str], scene, theme_name: str, log) -> list[str]:
    """The report's Background section (only with --bg)."""
    world, mood = bg
    f = scene.facts
    note = fit_note(world, theme_name)
    lines = ["## Background", "",
             f"- World: {world}, mood {mood}" + (f" ({note})" if note else
                                                  f" ({theme_name} is in its range)"),
             f"- Seed {f.seed} (from the folder name `{f.name}`): {scene.picks.describe()}",
             f"- Lamp on at {f.last_line_s:.2f} s (the last shown line's first word)"
             if f.last_line_s is not None else "- No shown line: the lamp stays off",
             "- Gusts (marked words): " + (", ".join(f"{s:.2f} s {label}" for s, label in f.marks)
                                           or "none (no marked words)")]
    if f.untimed_marks:
        lines.append("- Marked but untimed, no gust: " + ", ".join(f.untimed_marks))
    if log.frames:
        lines.append(f"- Background drawing and compose: {1000 * log.draw_s / log.frames:.0f} ms "
                     f"per frame ({log.draw_s:.1f} s)")
    if log.worst:
        k, c = log.worst
        lines.append(f"- Legibility: lowest contrast {c:.2f}:1 at frame {k} "
                     f"(rule: at least 3:1 around the text); "
                     + ("pass" if not log.failed else f"{len(log.failed)} frame(s) below"))
    return lines
