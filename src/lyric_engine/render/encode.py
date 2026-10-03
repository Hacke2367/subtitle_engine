"""One ffmpeg process: raw RGBA frames on stdin -> alpha .mov, green mp4, preview with audio."""
from __future__ import annotations

import collections
import subprocess
import threading
from pathlib import Path

from ..theme import Theme

TO_BT709 = "scale=out_color_matrix=bt709:out_range=tv"
BT709_TAGS = ["-colorspace", "bt709", "-color_primaries", "bt709", "-color_trc", "bt709",
              "-color_range", "tv"]
ALPHA_CODECS = {   # D-005 formats proven in step 01: (filter chain, encoder args); file overlay.mov
    "prores": (f"{TO_BT709},format=yuva444p10le",
               ["-c:v", "prores_ks", "-profile:v", "4444", "-alpha_bits", "16", "-vendor", "apl0",
                *BT709_TAGS]),
    "png": ("format=rgba", ["-c:v", "png"]),
    "qtrle": ("format=argb", ["-c:v", "qtrle"]),
}
OUTPUTS = {"overlay": "overlay.mov", "green": "overlay_green.mp4", "preview": "preview.mp4"}


class RenderError(RuntimeError):
    """The song cannot be rendered as it is; the message says what to fix."""


# --- ffmpeg ----------------------------------------------------------------------------------
def _drain(stream) -> tuple[threading.Thread, collections.deque]:
    """Read a pipe on a thread (no deadlock however much ffmpeg prints); keep the tail."""
    tail: collections.deque = collections.deque(maxlen=30)
    thread = threading.Thread(target=lambda: tail.extend(stream), daemon=True)
    thread.start()
    return thread, tail


def _tail_text(tail: collections.deque, lines: int = 5) -> str:
    text = b"".join(tail).decode("utf-8", "replace").strip()
    return " | ".join(text.splitlines()[-lines:]) or "no error output"


def _remove(paths) -> None:
    for p in paths:
        Path(p).unlink(missing_ok=True)


def _ffmpeg_cmd(theme: Theme, codec: str, audio: Path, outputs: dict[str, Path]) -> list[str]:
    """The overlay's three outputs; with outputs["final"] (a background, spec 17) each input frame
    is the overlay stacked above its finished frame, and the finished short is a fourth output."""
    size, fps = f"{theme.width}x{theme.height}", theme.fps
    pw, ph = theme.preview_size
    vf, args = ALPHA_CODECS[codec]
    final = outputs.get("final")
    head = ([f"[0:v]split=2[top][bot]",
             f"[top]crop={theme.width}:{theme.height}:0:0,split=3[a][g][p]",
             f"[bot]crop={theme.width}:{theme.height}:0:{theme.height},{TO_BT709},"
             "format=yuv420p[fin]"]
            if final else ["[0:v]split=3[a][g][p]"])
    graph = ";".join([
        *head,
        f"[a]{vf}[alpha]",
        f"color=c={theme.key_green_hex}:s={size}:r={fps}[gbg]",
        f"[gbg][g]overlay=shortest=1:format=rgb,{TO_BT709},format=yuv420p[green]",
        f"color=c={theme.preview_bg_hex}:s={size}:r={fps}[pbg]",
        f"[pbg][p]overlay=shortest=1:format=rgb,"
        f"scale={pw}:{ph}:out_color_matrix=bt709:out_range=tv,format=yuv420p[prev]",
    ])
    in_size = f"{theme.width}x{2 * theme.height}" if final else size
    cmd = ["ffmpeg", "-hide_banner", "-nostats", "-loglevel", "error", "-y",
           "-f", "rawvideo", "-pix_fmt", "rgba", "-s", in_size, "-framerate", str(fps), "-i", "-",
           "-i", str(audio), "-filter_complex", graph,
           "-map", "[alpha]", *args, "-an", str(outputs["overlay"]),
           "-map", "[green]", "-c:v", "libx264", "-preset", "medium", "-crf", "16",
           "-profile:v", "high", "-movflags", "+faststart", *BT709_TAGS, "-an",
           str(outputs["green"]),
           "-map", "[prev]", "-map", "1:a:0", "-c:v", "libx264", "-preset", "veryfast",
           "-crf", "26", *BT709_TAGS, "-c:a", "aac", "-b:a", "128k", "-shortest",
           str(outputs["preview"])]
    if final:   # upload-ready: every frame kept (no -shortest), audio in full
        cmd += ["-map", "[fin]", "-map", "1:a:0", "-c:v", "libx264", "-preset", "medium",
                "-crf", "18", "-profile:v", "high", "-movflags", "+faststart", *BT709_TAGS,
                "-c:a", "aac", "-b:a", "192k", str(final)]
    return cmd


def _encode(cmd: list[str], frames, outputs: dict[str, Path]) -> None:
    """Stream frames (iterables of bytes-like pieces) to ffmpeg's stdin, close it, then wait.
    On any failure ffmpeg is stopped and partial outputs are deleted."""
    try:
        proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.DEVNULL,
                                stderr=subprocess.PIPE)
    except FileNotFoundError:
        raise RenderError("ffmpeg not found on PATH") from None
    reader, tail = _drain(proc.stderr)
    fed = False
    try:
        for parts in frames:
            try:
                for part in parts:
                    proc.stdin.write(part)
            except OSError:   # ffmpeg exited early; its stderr says why
                break
        else:
            fed = True
    except BaseException:   # a bug or Ctrl+C while drawing
        proc.kill()
        raise
    finally:
        try:
            proc.stdin.close()   # end of input: ffmpeg finishes the files and exits
        except OSError:
            fed = False
        code = proc.wait()
        reader.join()
        proc.stderr.close()
        if not fed or code != 0:   # never leave a half-written output behind
            _remove(outputs.values())
    if not fed or code != 0:
        raise RenderError(f"ffmpeg failed (exit code {code}): {_tail_text(tail)}")
