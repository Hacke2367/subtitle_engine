"""Soft Romantic theme parameters: palette, fonts, layout box, reveal and glow timings.

Initial values chosen under H-008 while the owner was away; the owner reviews them via
songs/<song>/render/preview.mp4 and tunes them here (spec docs/specs/03_soft_romantic_render.md).
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

FONTS = Path("C:/Windows/Fonts")


@dataclass(frozen=True)
class Theme:
    name: str
    # Canvas
    width: int = 1080
    height: int = 1920
    fps: int = 30
    # Type: first font that has a character draws it; none → render refuses (never tofu)
    font: Path = FONTS / "Candarab.ttf"
    fallback_fonts: tuple[Path, ...] = (FONTS / "seguisb.ttf", FONTS / "seguisym.ttf",
                                        FONTS / "Nirmala.ttc", FONTS / "seguiemj.ttf")
    font_size: int = 84
    min_font_size: int = 56
    font_step: int = 4
    # Layout box: one lyric line at a time, wrapped into rows
    max_width: int = 900          # 90 px side margins
    max_rows: int = 3
    anchor_y: float = 0.62        # block centre as a fraction of height, above platform UI
    row_spacing: float = 1.15     # row pitch as a multiple of (ascent + descent)
    # Colours (hues kept away from key green, spec 01 hard rule)
    text_rgb: tuple[int, int, int] = (255, 243, 230)       # warm cream
    glow_rgb: tuple[int, int, int] = (255, 150, 170)       # soft rose
    glow_radius: int = 16
    glow_boost: float = 1.8       # blurred-mask alpha multiplier, capped at 255
    shadow_rgb: tuple[int, int, int] = (40, 18, 30)
    shadow_alpha: float = 0.55     # readable on bright backgrounds too (D-013)
    shadow_radius: int = 7
    shadow_offset: tuple[int, int] = (0, 3)
    # Motion (seconds / pixels)
    lead_s: float = 0.05          # uniform display lead: text lands with the voice, not after
    reveal_s: float = 0.20        # fade-in + rise duration
    rise_px: int = 12
    glow_in_s: float = 0.18       # ~ reveal_s: no pink flash before the text lands
    glow_out_s: float = 0.30
    hold_s: float = 0.60          # line stays after its last word ends
    fade_out_s: float = 0.25
    # Outputs
    alpha_codec: str = "prores"   # provisional until the owner's CapCut test (H-006, D-011)
    key_green_hex: str = "0x00FF00"
    preview_bg_hex: str = "0x120E16"
    preview_size: tuple[int, int] = (540, 960)


SOFT_ROMANTIC = Theme("soft-romantic")
