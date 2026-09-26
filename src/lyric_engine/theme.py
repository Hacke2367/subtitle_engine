"""Every theme's look numbers: palette, fonts, layout box, motion timings. `THEMES` is the set
`render --theme` picks from.

Soft Romantic: values chosen under H-008, tuned by the owner via
songs/<song>/render/soft-romantic/preview.mp4 (spec docs/specs/03_soft_romantic_render.md).
Pop Karaoke: start values from spec docs/specs/07_pop_karaoke_theme.md §4.5.
"""
from __future__ import annotations

import colorsys
from dataclasses import dataclass, fields
from pathlib import Path

FONTS = Path("C:/Windows/Fonts")
REPO_FONTS = Path(__file__).resolve().parents[2] / "fonts"   # bundled OFL fonts (D-018)
EMPHASIS_MIN, EMPHASIS_MAX = 1.5, 2.0   # marked word size / line font size (H-013)
KEY_HUE, KEY_HUE_TOL, KEY_SAT_MIN = 120, 15, 0.5   # colours the green-screen output would key out
MOTIONS = ("reveal", "karaoke")


def _near_key_green(rgb: tuple[int, int, int]) -> bool:
    h, s, _ = colorsys.rgb_to_hsv(*(v / 255 for v in rgb))
    return abs(h * 360 - KEY_HUE) <= KEY_HUE_TOL and s > KEY_SAT_MIN


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
    # Emphasis (*word*, H-009): a marked word is drawn this many times its line's font size, for
    # as long as the line is on screen; the layout makes room for it (H-013, spec 06)
    emphasis_scale: float = 1.5
    # Motion family: "reveal" = words fade and rise in as sung, glow (Soft Romantic);
    # "karaoke" = the line is shown ahead and colour fills each word as sung (Pop Karaoke)
    motion: str = "reveal"
    center_x: int = 540           # rows are centred on this x
    safe_zone: tuple[int, int, int, int] | None = None   # x0, y0, x1, y1 every frame stays in
    # Karaoke only (spec 07): fill, legibility layer, line life cycle
    accent_rgb: tuple[int, int, int] | None = None     # colour a sung word fills with
    stroke_rgb: tuple[int, int, int] | None = None
    stroke_frac: float = 0.0      # stroke width as a fraction of the word's own size
    fill_soft_px: int = 8         # width of the fill's soft edge
    preroll_s: float = 0.5        # a line appears this long before its first word's fill
    enter_s: float = 0.28         # entrance and hand-over duration
    enter_scale: float = 0.94     # entrance starts at this scale
    past_scale: float = 0.8       # the past line, above the current one
    past_opacity: float = 0.4
    past_gap_px: int = 40         # past line bottom to current line top
    # Outputs
    alpha_codec: str = "prores"   # owner-confirmed in CapCut (H-010)
    key_green_hex: str = "0x00FF00"
    preview_bg_hex: str = "0x120E16"
    preview_size: tuple[int, int] = (540, 960)

    def __post_init__(self) -> None:
        # Owner rule (H-013): a marked word is 1.5x to 2x its line's other words, never less
        # (it would read as the same size) and never more.
        if not EMPHASIS_MIN <= self.emphasis_scale <= EMPHASIS_MAX:
            raise ValueError(f"theme {self.name}: emphasis_scale {self.emphasis_scale} is outside "
                             f"{EMPHASIS_MIN}-{EMPHASIS_MAX} (H-013)")
        if self.motion not in MOTIONS:
            raise ValueError(f"theme {self.name}: motion {self.motion!r} is not one of {MOTIONS}")
        if self.motion == "karaoke" and (self.accent_rgb is None or self.stroke_rgb is None):
            raise ValueError(f"theme {self.name}: a karaoke theme needs accent_rgb and stroke_rgb")
        for f in fields(self):   # styling rules: the green-screen output would key these out
            value = getattr(self, f.name)
            if f.name.endswith("_rgb") and value is not None and _near_key_green(value):
                raise ValueError(f"theme {self.name}: {f.name} {value} is too close to the key "
                                 "green (hue 120); the green-screen output would key it out")


SOFT_ROMANTIC = Theme("soft-romantic")

POP_KARAOKE = Theme(
    "pop-karaoke", motion="karaoke",
    font=REPO_FONTS / "Poppins-SemiBold.ttf", font_size=96, min_font_size=64,
    max_width=860, center_x=510, safe_zone=(60, 380, 960, 1540),
    text_rgb=(255, 255, 255), accent_rgb=(255, 46, 136), stroke_rgb=(11, 11, 20),
    stroke_frac=0.04, shadow_rgb=(0, 0, 0), shadow_alpha=0.5, shadow_radius=4,
    shadow_offset=(0, 3), hold_s=1.0, fade_out_s=0.2)

THEMES = {t.name: t for t in (SOFT_ROMANTIC, POP_KARAOKE)}
