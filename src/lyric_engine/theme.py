"""Every theme's look numbers: palette, fonts, layout box, motion timings. `THEMES` is the set
`render --theme` picks from.

Soft Romantic: values chosen under H-008, tuned by the owner via
songs/<song>/render/soft-romantic/preview.mp4 (spec docs/specs/03_soft_romantic_render.md).
Pop Karaoke: start values from spec docs/specs/07_pop_karaoke_theme.md §4.5.
Soft Romantic v2: v1's look plus spec docs/specs/08_soft_romantic_v2.md §4.4.
Lofi Minimal / Lofi Typewriter: start values from spec docs/specs/09_lofi_minimal_theme.md §4.5.
Cinematic: start values from spec docs/specs/10_cinematic_theme.md §4.5.
Beat Pop: start values from spec docs/specs/12_beat_pop_theme.md §4.5, plan §2.12 / §3.1.
Phonk Neon: start values from spec docs/specs/13_phonk_neon_theme.md §4.4, plan §2.8.
"""
from __future__ import annotations

import colorsys
import math
from dataclasses import dataclass, fields, replace
from pathlib import Path

FONTS = Path("C:/Windows/Fonts")
REPO_FONTS = Path(__file__).resolve().parents[2] / "fonts"   # bundled OFL fonts (D-018)
EMPHASIS_MIN, EMPHASIS_MAX = 1.5, 2.0   # marked word size / line font size (H-013)
KEY_HUE, KEY_HUE_TOL, KEY_SAT_MIN = 120, 15, 0.5   # colours the green-screen output would key out
MOTIONS = ("reveal", "karaoke", "focus", "lofi", "cinematic", "beatpop", "phonk")


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
    tracking: float = 0.0         # extra space between letters, × the word's own size (0 = none)
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
    # "karaoke" = the line is shown ahead and colour fills each word as sung (Pop Karaoke);
    # "focus" = reveal, plus the finished line dims and blurs above the next (Soft Romantic v2);
    # "lofi" = one line shown ahead, dim; each word turns to the accent as sung, then settles
    # (Lofi Minimal), or types in letter by letter (typewriter=True);
    # "cinematic" = couplets; each word blurs into focus in the accent as sung, then settles;
    # "beatpop" = one line; each word pops in as sung on a pill, the line bumps on the beats;
    # "phonk" = one line shown ahead unlit; each word flickers on as sung, glow pulses on beats
    motion: str = "reveal"
    center_x: int = 540           # rows are centred on this x
    align: str = "center"         # "left": every row starts at center_x − max_width // 2, so a
    #                               line sung word by word grows from one fixed left edge
    safe_zone: tuple[int, int, int, int] | None = None   # x0, y0, x1, y1 every frame stays in
    # Karaoke only (spec 07): fill, legibility layer, line life cycle. Lofi reuses accent_rgb
    # (a word's current colour), preroll_s (before its first word turns current) and enter_s.
    accent_rgb: tuple[int, int, int] | None = None     # colour a sung word fills with
    stroke_rgb: tuple[int, int, int] | None = None
    stroke_frac: float = 0.0      # stroke width as a fraction of the word's own size
    fill_soft_px: int = 8         # width of the fill's soft edge
    preroll_s: float = 0.5        # a line appears this long before its first word's fill
    enter_s: float = 0.28         # entrance and hand-over duration (focus: hand-over only)
    enter_scale: float = 0.94     # entrance starts at this scale
    past_scale: float = 0.8       # the past line, above the current one (karaoke and focus)
    past_opacity: float = 0.4
    past_gap_px: int = 40         # past line bottom to current line top
    # Focus only (spec 08): past-line blur, hand-over lead, glow breath on held words
    past_blur_px: float = 6.0     # the past line's blur radius once it has moved up
    handover_lead_s: float = 0.2  # the move starts this long before the next line's first word
    breath_min_s: float = 1.0     # a word held this long (its own frames) breathes
    breath_low: float = 0.65      # glow strength at the bottom of a breath
    breath_period_s: float = 2.0  # one breath
    # Lofi only (spec 09): colour states, exit, typewriter. rise_px is its entrance rise.
    upcoming_opacity: float = 0.35   # a word not sung yet, in text_rgb
    current_in_s: float = 0.12    # fade into the accent from the word's start frame
    sung_in_s: float = 0.4        # fade back to text_rgb from its end frame
    exit_rise_px: int = 10        # a leaving line rises this much more while it fades
    typewriter: bool = False      # letters type in inside the word's own span; nothing shown ahead
    type_stagger_s: float = 0.06  # at most this between letters (less if the word is short)
    letter_fade_s: float = 0.1
    # Cinematic only (spec 10): blur-in / blur-out, couplets. Reuses reveal_s (blur-in),
    # accent_rgb (current), sung_in_s (to text_rgb), hold_s and fade_out_s (blur-out).
    blur_px: float = 10.0         # blur-in start radius and blur-out end radius
    couplet_gap: float = 0.5      # extra space between a couplet's two lines, × row pitch
    couplet_max_gap_s: float = 4.0   # a pair sung further apart shows as two singles
    couplets: bool = True         # False: every line shows alone
    reveal_min_s: float = 0.0     # a short word's blur-in lasts at least this, even past its end
    # Beat Pop only (spec 12): pill, pop, beat bump, drop shake, exit. Reuses reveal_s (pop),
    # stroke_rgb / stroke_frac, hold_s and fade_out_s (exit).
    pill_rgb: tuple[int, int, int] | None = None        # the pill behind the word being sung
    pill_text_rgb: tuple[int, int, int] | None = None   # that word's colour on the pill
    pill_pad: float = 0.08        # pill margin around the word's ink, × the word's size
    pop_scale: float = 0.6        # a word pops in from this scale (easeOutBack to 1)
    bump_scale: float = 1.05      # line scale on a beat frame ...
    bump_s: float = 0.15          # ... back to 1 over this
    drop_scale: float = 1.12      # line scale on a drop frame ...
    shake_px: int = 14            # ... shaking this far at most ...
    shake_s: float = 0.5          # ... both settling over this
    exit_scale: float = 0.95      # a leaving line shrinks to this while it fades
    # Phonk Neon only (spec 13): unlit tube, beat pulse, drop split. Reuses text_rgb (lit core),
    # glow_*, stroke_frac + shadow_* (the dark rim over the glow), preroll_s / enter_s,
    # drop_scale / shake_*, hold_s, fade_out_s.
    unlit_rgb: tuple[int, int, int] | None = None       # a word not sung yet (no glow)
    pulse_low: float = 0.55       # glow strength at rest; 1.0 on a beat frame ...
    pulse_s: float = 0.3          # ... back to rest over this
    split_px: int = 12            # drop: red copy this far left, cyan this far right ...
    split_s: float = 0.25         # ... closing over this
    split_left_rgb: tuple[int, int, int] = (255, 30, 60)
    split_right_rgb: tuple[int, int, int] = (0, 225, 255)
    # Title card (spec 15, H-021): songs/<song>/title.txt at the top for the first card_s, in the
    # theme's font, text_rgb, shadow and stroke; card_glow > 0 adds its glow at that strength
    card_scale: float = 0.5       # card size × font_size ...
    card_min_size: int = 28       # ... shrunk down to this for a wide line, then refused
    card_top: int = 420           # the first row's box top
    card_s: float = 3.0           # gone by this
    card_in_s: float = 0.3
    card_out_s: float = 0.5
    card_glow: float = 0.0
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
        if self.align not in ("center", "left"):
            raise ValueError(f"theme {self.name}: align {self.align!r} is not center or left")
        if self.motion not in MOTIONS:
            raise ValueError(f"theme {self.name}: motion {self.motion!r} is not one of {MOTIONS}")
        if self.motion == "karaoke" and (self.accent_rgb is None or self.stroke_rgb is None):
            raise ValueError(f"theme {self.name}: a karaoke theme needs accent_rgb and stroke_rgb")
        if self.motion in ("lofi", "cinematic") and self.accent_rgb is None:
            raise ValueError(f"theme {self.name}: a {self.motion} theme needs accent_rgb "
                             "(current colour)")
        if ((self.motion == "phonk" or self.motion == "lofi" and not self.typewriter)
                and round(self.preroll_s * self.fps) <= math.ceil(self.enter_s * self.fps)):
            raise ValueError(f"theme {self.name}: preroll_s must be longer than enter_s, so a line "
                             "is at rest before its first word turns current")
        if self.motion == "beatpop":
            if None in (self.stroke_rgb, self.pill_rgb, self.pill_text_rgb):
                raise ValueError(f"theme {self.name}: a beatpop theme needs stroke_rgb, pill_rgb "
                                 "and pill_text_rgb")
            if not (0 < self.pop_scale <= 1 and 0 < self.exit_scale <= 1
                    and self.bump_scale >= 1 and self.drop_scale >= 1):
                raise ValueError(f"theme {self.name}: pop_scale and exit_scale must be in (0, 1], "
                                 "bump_scale and drop_scale at least 1")
        if self.motion == "phonk":
            if self.unlit_rgb is None:
                raise ValueError(f"theme {self.name}: a phonk theme needs unlit_rgb")
            if not (0 <= self.pulse_low <= 1 and self.bump_scale >= 1 and self.drop_scale >= 1):
                raise ValueError(f"theme {self.name}: pulse_low must be in [0, 1], bump_scale and "
                                 "drop_scale at least 1")
        for name in ("tracking", "blur_px", "couplet_gap", "couplet_max_gap_s", "pill_pad",
                     "bump_s", "shake_px", "shake_s", "pulse_s", "split_px", "split_s",
                     "card_glow", "reveal_min_s"):
            if getattr(self, name) < 0:
                raise ValueError(f"theme {self.name}: {name} {getattr(self, name)} is negative")
        for f in fields(self):   # styling rules: the green-screen output would key these out
            value = getattr(self, f.name)
            if f.name.endswith("_rgb") and value is not None and _near_key_green(value):
                raise ValueError(f"theme {self.name}: {f.name} {value} is too close to the key "
                                 "green (hue 120); the green-screen output would key it out")


SOFT_ROMANTIC = Theme("soft-romantic")

# v1's look; 820 px keeps the glow (~29 px past a glyph) inside x 60-960 (plan 08 §2.8)
SOFT_ROMANTIC_V2 = Theme(
    "soft-romantic-v2", motion="focus",
    max_width=820, center_x=510, safe_zone=(60, 380, 960, 1540),
    enter_s=0.35, past_scale=0.85, past_opacity=0.4, past_gap_px=40, hold_s=1.0, fade_out_s=0.3)

POP_KARAOKE = Theme(
    "pop-karaoke", motion="karaoke",
    font=REPO_FONTS / "Poppins-SemiBold.ttf", font_size=96, min_font_size=64,
    max_width=860, center_x=510, safe_zone=(60, 380, 960, 1540),
    text_rgb=(255, 255, 255), accent_rgb=(255, 46, 136), stroke_rgb=(11, 11, 20),
    stroke_frac=0.04, shadow_rgb=(0, 0, 0), shadow_alpha=0.5, shadow_radius=4,
    shadow_offset=(0, 3), hold_s=1.0, fade_out_s=0.2)

# 860 px centred on 510 keeps the soft shadow inside x 60-960 (plan 09 §3.1)
LOFI_MINIMAL = Theme(
    "lofi-minimal", motion="lofi",
    font=REPO_FONTS / "Poppins-Light.ttf", font_size=76, min_font_size=52, tracking=0.10,
    max_width=860, center_x=510, safe_zone=(60, 380, 960, 1540),
    text_rgb=(245, 239, 230), accent_rgb=(247, 198, 208),
    shadow_rgb=(43, 42, 51), shadow_alpha=0.5, shadow_radius=6, shadow_offset=(0, 2),
    enter_s=0.6, preroll_s=0.9, rise_px=20, hold_s=1.5, fade_out_s=0.5)

LOFI_TYPEWRITER = replace(LOFI_MINIMAL, name="lofi-typewriter", typewriter=True)

# 800 px centred on 510 leaves ~50 px for shadow, blur and italic lean inside x 60-960
# (plan 10 §2.13); ivory #EDE6D6, antique gold #C9A66B (research §7 palette 7)
CINEMATIC = Theme(
    "cinematic", motion="cinematic",
    font=REPO_FONTS / "CormorantGaramond-MediumItalic.ttf", font_size=96, min_font_size=64,
    max_width=800, center_x=510, safe_zone=(60, 380, 960, 1540),
    text_rgb=(237, 230, 214), accent_rgb=(201, 166, 107),
    shadow_rgb=(0, 0, 0), shadow_alpha=0.7, shadow_radius=8, shadow_offset=(0, 3),
    reveal_s=0.5, sung_in_s=0.8, hold_s=2.0, fade_out_s=0.8, blur_px=10.0)

# 700 px about 510, anchor 0.60: the line at the drop's 1.12x plus the shake and a popping edge
# word stays inside x 60-960, y 380-1540 (plan 12 §2.12); research §7 palette 6 (Punjabi hype)
BEAT_POP = Theme(
    "beat-pop", motion="beatpop",
    font=REPO_FONTS / "Anton-Regular.ttf", font_size=110, min_font_size=64,
    max_width=700, center_x=510, anchor_y=0.60, safe_zone=(60, 380, 960, 1540),
    text_rgb=(255, 255, 255), stroke_rgb=(0, 0, 0), stroke_frac=0.05,
    pill_rgb=(255, 193, 7), pill_text_rgb=(0, 0, 0),
    shadow_rgb=(0, 0, 0), shadow_alpha=0.4, shadow_radius=4, shadow_offset=(0, 3),
    reveal_s=0.25, hold_s=0.8, fade_out_s=0.2)

# Beat Pop's box (700 px about 510, anchor 0.60): its worst side keeps the 1.06x drop, the shake,
# the split and the glow (≤ 31 px past a glyph) inside x 60-960 (plan 13 §2.8); H-020 look
PHONK_NEON = Theme(
    "phonk-neon", motion="phonk",
    font=REPO_FONTS / "PirataOne-Regular.ttf", font_size=100, min_font_size=64,
    max_width=700, center_x=510, anchor_y=0.60, safe_zone=(60, 380, 960, 1540),
    text_rgb=(225, 165, 255), unlit_rgb=(88, 36, 118), glow_rgb=(190, 70, 255),
    glow_radius=18, glow_boost=1.5, stroke_frac=0.04,
    shadow_rgb=(0, 0, 0), shadow_alpha=0.85, shadow_radius=2, shadow_offset=(0, 1),
    preroll_s=0.5, enter_s=0.2, hold_s=0.8, fade_out_s=0.25,
    bump_scale=1.0, drop_scale=1.06, card_glow=0.55)

# Romantic and classics songs (H-041): Cinematic's motion (one block at a time, words blur in as
# sung, the block blurs out) at a slower, softer pace, lines left-aligned so a line sung word by
# word grows from one edge. Light type, no glow; the sung word is tinted, then settles.
ROMANTIC_SOFT = Theme(
    "romantic-soft", motion="cinematic", couplets=False, align="left",
    font=REPO_FONTS / "Poppins-Light.ttf", font_size=76, min_font_size=56,
    max_width=820, center_x=510, safe_zone=(60, 380, 960, 1540),
    text_rgb=(246, 239, 230), accent_rgb=(242, 196, 196),   # ivory, blush
    shadow_rgb=(8, 8, 18), shadow_alpha=0.6, shadow_radius=10, shadow_offset=(0, 3),
    lead_s=0.15, reveal_s=0.5, reveal_min_s=0.3, sung_in_s=1.0, hold_s=2.0, fade_out_s=0.8,
    blur_px=6.0, card_scale=0.8)   # a title card that reads on a phone: the first 3 s are the hook

# Cinematic's couplets (sher), smaller so a usual line fits one row and a sher stays two rows
CLASSIC_SHER = replace(
    CINEMATIC, name="classic-sher", align="left", font_size=72, min_font_size=60, max_width=820,
    text_rgb=(241, 230, 208), accent_rgb=(214, 178, 112),   # old paper, antique gold
    shadow_rgb=(20, 12, 6), shadow_alpha=0.65, shadow_radius=10,
    lead_s=0.15, reveal_min_s=0.3, sung_in_s=1.0, fade_out_s=0.8, blur_px=8.0, card_scale=0.8)

THEMES = {t.name: t for t in (SOFT_ROMANTIC, SOFT_ROMANTIC_V2, POP_KARAOKE, LOFI_MINIMAL,
                              LOFI_TYPEWRITER, CINEMATIC, BEAT_POP, PHONK_NEON, ROMANTIC_SOFT,
                              CLASSIC_SHER)}
DEFAULT_THEME = SOFT_ROMANTIC_V2.name   # the owner preferred v2 over v1 (spec 08 AC10)
