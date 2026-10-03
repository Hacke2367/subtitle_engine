"""Styled subtitles: the cues as an `.ass` file, each word lit as it is said.

An `.srt` carries text and times only, so no editor can show a font or a word highlight from
it. An `.ass` (Advanced SubStation) file carries both, and libass (inside ffmpeg) draws it -
onto the video for a preview, or onto a transparent canvas for an overlay `.mov` the user drops
above the video in CapCut (D-107).

Every word moves through three looks: upcoming (not said yet), active (being said) and spoken.
The switch is timed from the word's own start in the transcript (red line 2), EARLY_MS ahead
because a highlight that lands with the sound already reads late; a word stays active until the
next one starts, so a short gap between words does not flicker. The words and their order are
exactly the cue's (red line 1). Nothing changes size while a line is read, so it never shifts:
a hero word is set larger from the moment its cue appears.

The signature look picks one hero word per cue (`hero_index`): the longest word that carries
meaning, set in a gold serif italic among the plain sans words.

Each cue is drawn as three layers that share one layout, so they line up exactly:
  0  halo  - a soft dark shade behind the words, so they read on any background
  1  glow  - a soft glow around the word being said (styles that have one)
  2  text  - the words themselves
"""
from __future__ import annotations

from dataclasses import dataclass

from .cues import LEANS_BACK, LEANS_FORWARD, Cue, core

WIDTH, HEIGHT = 1080, 1920         # the canvas styles are designed on (9:16)
FADE_IN_MS, FADE_OUT_MS = 120, 120  # a cue eases in and out, only across a real gap
WORD_IN_MS = 70                    # how fast a word lights up
WORD_OUT_MS = 140                  # and settles into "spoken"
EARLY_MS = 60                      # a word lights this much before it is heard
CLEAR = 255                        # alpha of something not drawn
HERO_MIN_LETTERS = 5
# Words too common to be a cue's hero, beyond the ones that lean on a neighbour (cues.py).
COMMON = frozenset("""main mujhe mujhko hum hamein humein aap tum tumhe tumko unhe unko inhe
    isko usko yahan wahan kahan jab tab ab abhi phir agar lekin magar kyunki kyonki isliye
    isilie nahin nahi kya kyon kaise kaun karna karne karta karti karte karein karenge kiya
    kiye hona hone hota hoti hote hua hui hue jana jaana jaata jaati jaate jaaen gaya gayi gaye
    aana aata aati aate aaya lagta lagti lagte laga rahna raha rahi rahe sakta sakti sakte
    bolta bolti bolte dena deta deti dete lena leta leti lete which would could should there
    their about going really thing things these those where while every being because before
    after again other""".split())


@dataclass(frozen=True)
class Hero:
    font: str
    scale: float           # its size against the line's
    colour: str            # "RRGGBB", in every state; it glows while said


@dataclass(frozen=True)
class Style:
    name: str
    font: str              # family name as libass sees it (voice_subs/fonts is passed to it)
    size: int              # font size on the 1080 x 1920 canvas
    line_chars: int        # a cue longer than this is set as two balanced lines
    upcoming: str          # "RRGGBB" of a word not said yet
    upcoming_alpha: int    # its opacity: 0 = solid, 255 = not shown until said
    active: str            # the word being said
    spoken: str            # a word already said
    glow: str | None       # glow around the word being said, or None
    glow_alpha: int
    glow_size: int
    halo_alpha: int        # the dark shade behind the words (255 = none)
    hero: Hero | None = None
    align: str = "center"  # or "left": a line that builds word by word grows from one edge
    tracking: float = 0.0  # extra letter spacing
    bottom: float = 0.30   # the last line sits this far up from the bottom of the frame
    about: str = ""


GOLD = "FFD37A"
STYLES = {
    # The signature: a quiet sans line that brightens as it is said, with one word that matters
    # set in a gold serif italic. No caption app does this mix; it suits a speaker who quotes.
    "signature": Style(
        name="signature", font="Instrument Sans SemiBold", size=66, line_chars=24,
        upcoming="FFFFFF", upcoming_alpha=110, active="FFFFFF", spoken="FFFFFF",
        glow=None, glow_alpha=150, glow_size=6, halo_alpha=115,
        hero=Hero(font="Instrument Serif", scale=1.3, colour=GOLD),
        about="Instrument Sans; the line brightens as it is said, one key word in gold serif"),
    # Clean karaoke: the line waits dim, each word lights gold with a soft glow as it is said.
    "ink": Style(
        name="ink", font="Instrument Sans SemiBold", size=68, line_chars=24,
        upcoming="FFFFFF", upcoming_alpha=102, active=GOLD, spoken="FFFFFF",
        glow=GOLD, glow_alpha=140, glow_size=6, halo_alpha=115,
        about="Instrument Sans; the line waits dim, each word lights gold as it is said"),
    # A film quote: nothing shows before it is said; the words arrive one by one, left-aligned
    # so the line grows from its edge, in an ivory serif.
    "cinema": Style(
        name="cinema", font="Instrument Serif", size=88, line_chars=20,
        upcoming="F6EEDF", upcoming_alpha=CLEAR, active="FFFFFF", spoken="F2E8D6",
        glow="FFF1D6", glow_alpha=150, glow_size=5, halo_alpha=125, align="left",
        tracking=0.5,
        about="Instrument Serif; words appear only as they are said, like a film quote"),
}
DEFAULT_STYLE = "signature"


def to_ass(cues: list[Cue], words: list[dict], style: Style,
           size: tuple[int, int] = (WIDTH, HEIGHT)) -> str:
    """The cues as an .ass file in this style. words = the timed words the cues were made from."""
    width, height = size
    scale = width / WIDTH
    lines = [_header(style, width, height)]
    queue = list(words)
    for i, cue in enumerate(cues):
        cue_words, queue = _take(cue, queue)
        start_cs, end_cs = _cs(cue.start), _cs(cue.end)
        # Fade only across a real gap: two cues back to back swap without a blink.
        fade_in = FADE_IN_MS if i == 0 or cue.start - cues[i - 1].end > 0.01 else 0
        fade_out = FADE_OUT_MS if i + 1 == len(cues) or cues[i + 1].start - cue.end > 0.01 \
            else 0
        for layer, text in _layers(cue_words, start_cs * 10, style, scale, fade_in, fade_out):
            lines.append(f"Dialogue: {layer},{_stamp(start_cs)},{_stamp(end_cs)},"
                         f"{LAYER_STYLES[layer]},,0,0,0,,{text}")
    return "\n".join(lines) + "\n"


LAYER_STYLES = {0: "Halo", 1: "Glow", 2: "Text"}


def hero_index(words: list[dict]) -> int | None:
    """The cue's hero word: its longest word that carries meaning, or None if none is long enough.

    Long, uncommon words are the content ones (experience, jindagi, koshish, tajurba); short and
    common words are grammar. A tie goes to the word said longer.
    """
    best, best_key = None, None
    for i, word in enumerate(words):
        letters = core(word["text"])
        if len(letters) < HERO_MIN_LETTERS or letters in COMMON or letters in LEANS_BACK \
                or letters in LEANS_FORWARD:
            continue
        key = (len(letters), float(word["end"]) - float(word["start"]))
        if best_key is None or key > best_key:
            best, best_key = i, key
    return best


def _take(cue: Cue, queue: list[dict]) -> tuple[list[dict], list[dict]]:
    """The words of this cue, from the front of the queue; checks they spell the cue exactly."""
    count = len(cue.text.split(" "))
    taken, rest = queue[:count], queue[count:]
    joined = " ".join(w["text"].strip() for w in taken)
    if joined != cue.text:
        raise ValueError(f"cue {cue.text!r} does not match its words {joined!r}")
    return taken, rest


def _layers(words: list[dict], start_ms: int, style: Style, scale: float, fade_in: int,
            fade_out: int) -> list[tuple[int, str]]:
    """The layers' text for one cue, as (layer, text with override tags)."""
    hero = hero_index(words) if style.hero else None
    second_line = _line_break(words, style.line_chars, hero, style.hero)
    hidden = style.upcoming_alpha >= CLEAR
    halo, glow, text = [], [], []
    for i, word in enumerate(words):
        on = _lit_at(word, start_ms)
        off = max(on + WORD_IN_MS, _lit_at(words[i + 1], start_ms)) if i + 1 < len(words) \
            else max(on + WORD_IN_MS, round(float(word["end"]) * 1000) - start_ms)
        lit, done = f"{on},{on + WORD_IN_MS}", f"{off},{off + WORD_OUT_MS}"
        sep = "" if i == 0 else ("\\N" if i == second_line else " ")
        said = _escape(word["text"].strip())
        # A hero word switches font and size for itself only; every layer does the same, so
        # the three layers keep one layout.
        is_hero = i == hero
        font_on = (f"\\fn{style.hero.font}\\i1\\fs{round(style.size * style.hero.scale * scale)}"
                   if is_hero else "")
        font_off = f"{{\\fn{style.font}\\i0\\fs{round(style.size * scale)}}}" if is_hero else ""
        upcoming, active, spoken = ((style.hero.colour,) * 3 if is_hero
                                    else (style.upcoming, style.active, style.spoken))
        glow_colour = style.hero.colour if is_hero else style.glow

        reveal = f"\\3a&HFF&\\t({lit},\\3a{_alpha(style.halo_alpha)})" if hidden else ""
        halo.append(f"{sep}{{{font_on}{reveal}}}{said}{font_off}" if font_on or reveal
                    else f"{sep}{said}")
        if glow_colour:
            glow.append(f"{sep}{{{font_on}\\3c{_colour(glow_colour)}\\3a&HFF&"
                        f"\\t({lit},\\3a{_alpha(style.glow_alpha)})\\t({done},\\3a&HFF&)}}"
                        f"{said}{font_off}")
        else:
            glow.append(f"{sep}{{{font_on}\\3a&HFF&}}{said}{font_off}")
        text.append(f"{sep}{{{font_on}\\1c{_colour(upcoming)}\\1a{_alpha(style.upcoming_alpha)}"
                    f"\\t({lit},\\1c{_colour(active)}\\1a&H00&)"
                    f"\\t({done},\\1c{_colour(spoken)})}}{said}{font_off}")

    fade = f"\\fad({fade_in},{fade_out})" if fade_in or fade_out else ""
    layers = []
    if style.halo_alpha < CLEAR:
        layers.append((0, f"{{{fade}\\blur14}}" + "".join(halo)))
    if style.glow or style.hero:
        layers.append((1, f"{{{fade}\\blur10}}" + "".join(glow)))
    layers.append((2, (f"{{{fade}}}" if fade else "") + "".join(text)))
    return layers


def _lit_at(word: dict, start_ms: int) -> int:
    """When the word lights up, in ms from its cue's start. Never 0: libass reads \\t(0,0,...)
    as "over the whole event", so a first word would never light (found by the video judge)."""
    return max(1, round(float(word["start"]) * 1000) - EARLY_MS - start_ms)


def _line_break(words: list[dict], line_chars: int, hero: int | None = None,
                hero_look: Hero | None = None) -> int | None:
    """Index of the word that starts line two: lines as even as possible, never splitting a
    word from the neighbour it leans on ("sach / mein", "ek / line")."""
    widths = [len(w["text"].strip()) * (hero_look.scale if i == hero and hero_look else 1)
              for i, w in enumerate(words)]
    total = sum(widths) + len(widths) - 1
    if total <= line_chars or len(words) < 2:
        return None
    best, best_cost, first = None, None, -1.0
    for i in range(1, len(words)):
        first += widths[i - 1] + 1
        cost = abs(first - (total - first - 1))
        if core(words[i]["text"]) in LEANS_BACK:
            cost += 100
        if core(words[i - 1]["text"]) in LEANS_FORWARD:
            cost += 100
        if best_cost is None or cost < best_cost:
            best, best_cost = i, cost
    return best


def _header(style: Style, width: int, height: int) -> str:
    scale = width / WIDTH
    size = round(style.size * scale)
    margin_v = round(height * style.bottom)
    margin_side = round((100 if style.align == "left" else 60) * scale)
    alignment = 1 if style.align == "left" else 2         # bottom-left / bottom-centre
    tracking = round(style.tracking * scale, 2)
    clear = "&HFF000000"

    # Format: Name, Font, Size, Primary, Secondary, Outline, Back, Bold, Italic, Underline,
    # StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment,
    # MarginL, MarginR, MarginV, Encoding
    def row(name: str, primary: str, outline: str, border: int) -> str:
        return (f"Style: {name},{style.font},{size},{primary},{clear},{outline},{clear},"
                f"0,0,0,0,100,100,{tracking},0,1,{round(border * scale)},0,"
                f"{alignment},{margin_side},{margin_side},{margin_v},1")

    return "\n".join([
        "[Script Info]",
        f"; voice-subs style: {style.name} - {style.about}",
        "ScriptType: v4.00+",
        f"PlayResX: {width}",
        f"PlayResY: {height}",
        "WrapStyle: 2",
        "ScaledBorderAndShadow: yes",
        "YCbCr Matrix: TV.709",
        "",
        "[V4+ Styles]",
        "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, "
        "BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, "
        "BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding",
        row("Halo", clear, _ass_colour("000000", style.halo_alpha), 9),
        row("Glow", clear, _ass_colour(style.glow or GOLD, CLEAR), style.glow_size),
        row("Text", _ass_colour(style.spoken, 0), clear, 0),
        "",
        "[Events]",
        "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text",
    ])


def _colour(rgb: str) -> str:
    """'RRGGBB' -> an override colour, &HBBGGRR& (ASS stores blue first)."""
    return f"&H{rgb[4:6]}{rgb[2:4]}{rgb[0:2]}&"


def _alpha(value: int) -> str:
    return f"&H{max(0, min(255, value)):02X}&"


def _ass_colour(rgb: str, alpha: int) -> str:
    """'RRGGBB' + opacity -> a style colour, &HAABBGGRR."""
    return f"&H{max(0, min(255, alpha)):02X}{rgb[4:6]}{rgb[2:4]}{rgb[0:2]}"


def _escape(text: str) -> str:
    """Braces would open an override block; libass reads \\{ and \\} as the characters."""
    return text.replace("{", "\\{").replace("}", "\\}")


def _cs(seconds: float) -> int:
    return max(0, round(seconds * 100))


def _stamp(cs: int) -> str:
    """H:MM:SS.cc, as ASS writes a time."""
    hours, cs = divmod(cs, 360_000)
    minutes, cs = divmod(cs, 6000)
    secs, cs = divmod(cs, 100)
    return f"{hours}:{minutes:02d}:{secs:02d}.{cs:02d}"
