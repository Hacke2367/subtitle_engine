"""The signature subtitles: the cues as an `.ass` file, each word lit as it is said.

An `.srt` carries text and times only, so no editor can show a font or a word highlight from
it. An `.ass` (Advanced SubStation) file carries both, and libass (inside ffmpeg) draws it onto
a transparent strip: the overlay `.mov` the owner drops onto the video in CapCut and places
wherever they want (D-107, D-113). Where the subtitles sit is the owner's call, so the strip is
just tall enough for two lines, with the text centred in it.

The look (owner's pick, H-107): Instrument Sans Bold; a cue waits dim and brightens word by
word as it is said; about every other cue one hero word - the word that carries the line - is
set in Instrument Serif Italic, larger, and turns gold with a soft glow when said.

Each word switches at its own start time from the transcript (red line 2), EARLY_MS ahead
because a highlight that lands with the sound already reads late; a word stays lit until the
next one starts, so a short gap does not flicker. The words and their order are exactly the
cue's (red line 1). Nothing changes size while a line is read, so it never shifts: a hero word
is set larger from the moment its cue appears.

Each cue is drawn as three layers that share one layout, so they line up exactly:
  0  halo  - a soft dark shade behind the words, so they read on any background
  1  glow  - a soft gold glow around the hero word while it is said
  2  text  - the words themselves
"""
from __future__ import annotations

import math
from dataclasses import dataclass

from .cues import LEANS_BACK, LEANS_FORWARD, Cue, core, leans_back, leans_forward

WIDTH = 1080                       # the strip is designed at this width and scaled to the video
STRIP_HEIGHT = 420                 # two lines, a larger hero word, and room for halo and glow
FONT, SIZE = "Instrument Sans", 66                 # bold (owner: "thoda aur bold")
HERO_FONT, HERO_SCALE = "Instrument Serif", 1.3    # italic; it has no bold, so none is faked
LINE_CHARS = 24                    # a cue longer than this is set as two balanced lines
DIM_ALPHA = 110                    # a word not said yet: ~57% white
GOLD = "FFD37A"
GLOW_ALPHA, GLOW_SIZE = 150, 6
HALO_ALPHA = 115                   # the shade behind the words: black at 55%
FADE_IN_MS, FADE_OUT_MS = 120, 120  # a cue eases in and out, only across a real gap
WORD_IN_MS = 70                    # how fast a word lights up
WORD_OUT_MS = 140                  # and settles
EARLY_MS = 60                      # a word lights this much before it is heard
HERO_MIN_LETTERS = 4                # shorter only if code-like: MP4, MPV
HERO_GAP_S = 3.0                   # at most one hero word in this long: a gold word every line
HERO_REPEAT_S = 10.0               # is no longer special, nor is the same word twice in a row
HERO_MIN_CUE_S = 1.0               # no hero in a cue too short to read it
HERO_SPACE = 4                     # extra px each side of a hero word: italic crowds its neighbours
# Words too common to be a cue's hero, beyond the ones that lean on a neighbour (cues.py):
# pronouns, conjunctions, common verbs and adverbs, Hinglish and English.
COMMON = frozenset("""main mujhe mujhko hum hamein humein aap tum tumhe tumko unhe unko inhe
    isko usko yahan wahan kahan jab tab ab abhi phir agar lekin magar kyunki kyonki isliye
    isilie nahin nahi kya kyon kaise kaun karna karne karta karti karte karein karenge kiya
    kiye hona hone hota hoti hote hua hui hue jana jaana jaata jaati jaate jaaen gaya gayi gaye
    aana aata aati aate aaya lagta lagti lagte laga rahna raha rahi rahe sakta sakti sakte
    bolta bolti bolte dena deta deti dete lena leta leti lete aksar hamesha kabhi sirf bilkul
    shayad zaroor jaldi baat wahi yahi sach sachmuch
    which would could should there their about going really thing things these those where
    while every being because before after again other always whenever however wherever
    whatever inside outside already still even never ever just only also much many more some
    any each another then when what without within onto upon over under using used make made
    want need know think doing getting click select open close press choose change install
    show see come get put set use like said says okay yeah guys all have has had able end time
    part told tell say does done did myself yourself itself himself herself themselves
    ourselves oneself people someone something anything everything nothing here yours well
    back down last next little lots right left good great best better same different away
    around through stuff ways kind sort pretty quite enough during until since though although
    whether either both such own cannot cant dont wont didnt doesnt isnt arent wasnt""".split())


def to_ass(cues: list[Cue], words: list[dict], width: int = WIDTH) -> str:
    """The cues as an .ass file for a strip `width` wide (the video's width).

    words = the timed words the cues were made from.
    """
    scale = width / WIDTH
    lines = [_header(width, strip_height(width), scale)]
    queue, per_cue = list(words), []
    for cue in cues:
        cue_words, queue = _take(cue, queue)
        per_cue.append(cue_words)
    heroes = pick_heroes(cues, per_cue)
    for i, (cue, cue_words) in enumerate(zip(cues, per_cue)):
        start_cs, end_cs = _cs(cue.start), _cs(cue.end)
        # Fade only across a real gap: two cues back to back swap without a blink.
        fade_in = FADE_IN_MS if i == 0 or cue.start - cues[i - 1].end > 0.01 else 0
        fade_out = FADE_OUT_MS if i + 1 == len(cues) or cues[i + 1].start - cue.end > 0.01 \
            else 0
        for layer, name, text in _layers(cue_words, start_cs * 10, scale, heroes[i],
                                         fade_in, fade_out):
            lines.append(f"Dialogue: {layer},{_stamp(start_cs)},{_stamp(end_cs)},"
                         f"{name},,0,0,0,,{text}")
    return "\n".join(lines) + "\n"


def strip_height(width: int) -> int:
    """The overlay strip's height for a video this wide (even, as video encoders want)."""
    return 2 * round(STRIP_HEIGHT * width / WIDTH / 2)


def pick_heroes(cues: list[Cue], per_cue: list[list[dict]]) -> list[int | None]:
    """Each cue's hero word (its index in the cue), or None.

    A hero is a word that carries the line: not grammar, not a common verb or adverb. Among a
    cue's candidates the best is a code-like word (MP4, MPV), then the longest (long words are
    the rare ones: experience, organisms, tajurba), then one said only once in the clip, then
    the one said longest. At most one hero every HERO_GAP_S, never the same word twice within
    HERO_REPEAT_S, and none in a cue too short to read it: a gold word on every line stops
    being special. The clip's best words are placed first and the rest fit around them (a weak
    early word never blocks a strong later one); the last cue's word goes first of all, as the
    clip's payoff. A cue whose best word does not fit gets no hero rather than a weaker one.
    """
    counts: dict[str, int] = {}
    for word in (w for cue_words in per_cue for w in cue_words):
        counts[core(word["text"])] = counts.get(core(word["text"]), 0) + 1
    best = []                                   # each cue's best candidate, if it has one
    for c, (cue, cue_words) in enumerate(zip(cues, per_cue)):
        candidates = [(_hero_rank(w, counts), i) for i, w in enumerate(cue_words)
                      if _can_be_hero(w["text"])]
        if candidates and cue.end - cue.start >= HERO_MIN_CUE_S:
            rank, i = max(candidates)
            best.append(((c == len(cues) - 1, *rank), c, i))
    heroes: list[int | None] = [None] * len(cues)
    placed: list[tuple[float, str]] = []
    for _, c, i in sorted(best, reverse=True):
        at, key = float(per_cue[c][i]["start"]), core(per_cue[c][i]["text"])
        if all(abs(at - t) >= (HERO_REPEAT_S if k == key else HERO_GAP_S) for t, k in placed):
            heroes[c] = i
            placed.append((at, key))
    return heroes


def _can_be_hero(text: str) -> bool:
    letters = core(text)
    if letters in COMMON or letters in LEANS_BACK or letters in LEANS_FORWARD:
        return False
    if len(letters) < HERO_MIN_LETTERS and not _code_like(text):
        return False
    return not (len(letters) > 5 and letters.endswith("ly"))   # adverbs: currently, extremely


def _code_like(text: str) -> bool:
    """MP4, MPV, 2024: a code or a number is the word a viewer is looking for."""
    text = text.strip(".,!?;:'\"")
    return any(c.isdigit() for c in text) or (len(text) > 1 and text.isupper())


def _hero_rank(word: dict, counts: dict[str, int]) -> tuple:
    letters = core(word["text"])
    return (_code_like(word["text"]), len(letters), counts.get(letters, 0) == 1,
            float(word["end"]) - float(word["start"]))


def _take(cue: Cue, queue: list[dict]) -> tuple[list[dict], list[dict]]:
    """The words of this cue, from the front of the queue; checks they spell the cue exactly."""
    count = len(cue.text.split(" "))
    taken, rest = queue[:count], queue[count:]
    joined = " ".join(w["text"].strip() for w in taken)
    if joined != cue.text:
        raise ValueError(f"cue {cue.text!r} does not match its words {joined!r}")
    return taken, rest


def _layers(words: list[dict], start_ms: int, scale: float, hero: int | None, fade_in: int,
            fade_out: int) -> list[tuple[int, str, str]]:
    """The layers for one cue, as (layer, style name, text with override tags)."""
    second_line = _line_break(words, LINE_CHARS, hero)
    wide = round(HERO_SPACE * scale, 2)
    halo, glow, text = [], [], []
    for i, word in enumerate(words):
        on = _lit_at(word, start_ms)
        off = max(on + WORD_IN_MS, _lit_at(words[i + 1], start_ms)) if i + 1 < len(words) \
            else max(on + WORD_IN_MS, round(float(word["end"]) * 1000) - start_ms)
        lit, done = f"{on},{on + WORD_IN_MS}", f"{off},{off + WORD_OUT_MS}"
        # The space on either side of a hero word is widened; every word resets the spacing.
        if i == 0:
            sep = ""
        elif i == second_line:
            sep = "\\N"
        elif hero is not None and hero in (i, i - 1):
            sep = f"{{\\fsp{wide}}} "
        else:
            sep = " "
        said = _escape(word["text"].strip())
        # A hero word switches font and size for itself only; every layer does the same, so
        # the layers keep one layout.
        is_hero = i == hero
        font_on = (f"\\fn{HERO_FONT}\\b0\\i1\\fs{round(SIZE * HERO_SCALE * scale)}"
                   if is_hero else "") + "\\fsp0"
        font_off = f"{{\\fn{FONT}\\b1\\i0\\fs{round(SIZE * scale)}}}" if is_hero else ""
        # A hero waits dim like any word (a dim gold reads khaki), then turns gold when said.
        lit_colour = GOLD if is_hero else "FFFFFF"

        halo.append(f"{sep}{{{font_on}}}{said}{font_off}")
        glow.append(f"{sep}{{{font_on}\\3a&HFF&"
                    + (f"\\t({lit},\\3a{_alpha(GLOW_ALPHA)})\\t({done},\\3a&HFF&)"
                       if is_hero else "") + f"}}{said}{font_off}")
        text.append(f"{sep}{{{font_on}\\1c&HFFFFFF&\\1a{_alpha(DIM_ALPHA)}"
                    f"\\t({lit},\\1c{_colour(lit_colour)}\\1a&H00&)}}{said}{font_off}")

    fade = f"\\fad({fade_in},{fade_out})" if fade_in or fade_out else ""
    layers = [(0, "Halo", f"{{{fade}\\blur14}}" + "".join(halo))]
    if hero is not None:
        layers.append((1, "Glow", f"{{{fade}\\blur10}}" + "".join(glow)))
    layers.append((2, "Text", (f"{{{fade}}}" if fade else "") + "".join(text)))
    return layers


def _lit_at(word: dict, start_ms: int) -> int:
    """When the word lights up, in ms from its cue's start. Never 0: libass reads \\t(0,0,...)
    as "over the whole event", so a first word would never light (found by the video judge)."""
    return max(1, round(float(word["start"]) * 1000) - EARLY_MS - start_ms)


def _line_break(words: list[dict], line_chars: int, hero: int | None = None) -> int | None:
    """Index of the word that starts line two: lines as even as possible, never splitting a
    word from the neighbour it leans on ("sach / mein", "ek / line"), never one word alone."""
    widths = [len(w["text"].strip()) * (HERO_SCALE if i == hero else 1)
              for i, w in enumerate(words)]
    total = sum(widths) + len(widths) - 1
    # A little over is still one line: "mushkil kaam nahin hai." beats "mushkil kaam / nahin hai."
    if total <= line_chars * 1.12 or len(words) < 2:
        return None
    best, best_cost, first = None, None, -1.0
    for i in range(1, len(words)):
        first += widths[i - 1] + 1
        cost = abs(first - (total - first - 1))
        if leans_back(words[i]["text"]):
            cost += 100
        if leans_forward(words[i - 1]["text"]):
            cost += 100
        if i in (1, len(words) - 1):
            cost += 100                         # one word alone on a line: "the editing / app"
        if best_cost is None or cost < best_cost:
            best, best_cost = i, cost
    return best


def _header(width: int, height: int, scale: float) -> str:
    size = round(SIZE * scale)
    clear = "&HFF000000"

    # Format: Name, Font, Size, Primary, Secondary, Outline, Back, Bold, Italic, Underline,
    # StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment,
    # MarginL, MarginR, MarginV, Encoding. Alignment 5: centred in the strip.
    def row(name: str, primary: str, outline: str, border: int) -> str:
        return (f"Style: {name},{FONT},{size},{primary},{clear},{outline},{clear},"
                f"-1,0,0,0,100,100,0,0,1,{round(border * scale)},0,5,"
                f"{round(40 * scale)},{round(40 * scale)},0,1")

    return "\n".join([
        "[Script Info]",
        "; voice-subs signature subtitles",
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
        row("Halo", clear, _ass_colour("000000", HALO_ALPHA), 9),
        row("Glow", clear, _ass_colour(GOLD, 255), GLOW_SIZE),
        row("Text", _ass_colour("FFFFFF", 0), clear, 0),
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
