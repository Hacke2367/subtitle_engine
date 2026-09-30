"""The look on its own, with no lyrics drawn: a background video to put lyrics on in CapCut (or
anywhere). Two ways, the same look code:

- with a song (`write_backdrop`, called by render with `backdrop=True`): the look follows this
  song's aligned words (marked words, the last line), and the video carries the song's audio;
- without one (`make_generic`): only a length; the look runs with no words, so nothing reacts to
  lyrics, and the payoff comes at 85% of the length. No audio unless one is given.

Frames are drawn the same way as in a finished short (worker processes for looks that allow it)."""
from __future__ import annotations

import time
from pathlib import Path

from . import DEFAULT_CENTRE, SongFacts, build_scene, seed_of
from .compose import drawn_ahead

FPS = 30


def _cmd(size: str, fps: int, audio: Path | None, out: Path) -> list[str]:
    from ..render.encode import BT709_TAGS, TO_BT709
    cmd = ["ffmpeg", "-hide_banner", "-nostats", "-loglevel", "error", "-y", "-f", "rawvideo",
           "-pix_fmt", "rgb24", "-s", size, "-framerate", str(fps), "-i", "-"]
    if audio:
        cmd += ["-i", str(audio)]
    cmd += ["-vf", f"{TO_BT709},format=yuv420p", "-map", "0:v"]
    cmd += ["-map", "1:a:0", "-c:a", "aac", "-b:a", "192k"] if audio else ["-an"]
    return cmd + ["-c:v", "libx264", "-preset", "medium", "-crf", "18", "-profile:v", "high",
                  "-movflags", "+faststart", *BT709_TAGS, str(out)]


def _frames(bg: tuple[str, str], scene):
    """The look's frames 0..n-1, every one with no text over it (ink None)."""
    if scene.in_order:
        for k in range(scene.facts.n):
            yield scene.frame(k, None)
    else:
        yield from drawn_ahead(bg, scene.facts)


def _write(bg, scene, audio: Path | None, out: Path) -> None:
    from ..render.encode import _encode
    from .paint import H, W
    out.unlink(missing_ok=True)
    _encode(_cmd(f"{W}x{H}", scene.facts.fps, audio, out), ([f] for f in _frames(bg, scene)),
            {"backdrop": out})


def write_backdrop(scene, bg: tuple[str, str], render_dir: Path, audio: Path, theme, n: int, t0: float):
    """render(..., backdrop=True): render/<theme>/backdrop_<look>_<mood>.mp4, the song's audio
    in full, from t = 0. Returns the render's result (checks: the file's ffprobe)."""
    from ..render import RenderResult
    from .compose import Legibility, final_checks
    out = render_dir / f"backdrop_{bg[0]}_{bg[1]}.mp4"
    _write(bg, scene, audio, out)
    checks = final_checks(out, n, theme, Legibility())       # the file only: no text, no legibility
    notes = [f"background only: no lyrics drawn; {scene.describe()}"]
    return RenderResult(render_dir, {"backdrop": out}, n, time.perf_counter() - t0, [], checks,
                        notes=notes)


def make_generic(bg: tuple[str, str], seconds: float, out: Path, name: str = "generic",
                 audio: Path | None = None) -> Path:
    """A song-independent background of `seconds`; `name` seeds what varies (same name, same
    video)."""
    n = round(seconds * FPS)
    if n < 1:
        raise ValueError("seconds must be at least one frame")
    facts = SongFacts(name, seed_of(name), n / FPS, n, FPS, (), (), None, DEFAULT_CENTRE, (), None)
    _write(bg, build_scene(bg, facts), audio, out)
    return out
