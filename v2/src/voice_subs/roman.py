"""Devanagari -> Roman, in the spelling a Hinglish speaker types.

The transcription engine writes Hindi words in Devanagari and English words in Latin
(scribe_v1, measured 2026-10-03), but the project context asks for Roman script throughout.
Only Devanagari runs are changed; anything already in Latin is passed through untouched, so
an English word keeps the engine's own spelling (red line 1: the words never change, only the
script they are written in, and the Devanagari original is kept in the transcript).

A transliteration, not a translation. The hard part is Hindi's inherent "a": `घर` is written
with two consonants and sounds "ghar", not "ghara". The rules below (`_drop_inherent`) are the
usual three: drop it at the end of a word, drop it mid-word when the next consonant carries a
vowel of its own, never drop it in the first syllable or right after a nasal sign.
"""
from __future__ import annotations

# Independent vowels (a vowel that starts a word).
VOWELS = {
    "अ": "a", "आ": "aa", "इ": "i", "ई": "i", "उ": "u", "ऊ": "u", "ऋ": "ri",
    "ए": "e", "ऐ": "ai", "ओ": "o", "औ": "au", "ऍ": "e", "ऑ": "o",
}
# Matras (a vowel written on a consonant). "" is the inherent a, added by the caller.
MATRAS = {
    "ा": "aa", "ि": "i", "ी": "i", "ु": "u", "ू": "u",
    "ृ": "ri", "ॅ": "e", "ॆ": "e", "े": "e", "ै": "ai",
    "ॉ": "o", "ॊ": "o", "ो": "o", "ौ": "au",
}
CONSONANTS = {
    "क": "k", "ख": "kh", "ग": "g", "घ": "gh", "ङ": "n",
    "च": "ch", "छ": "chh", "ज": "j", "झ": "jh", "ञ": "n",
    "ट": "t", "ठ": "th", "ड": "d", "ढ": "dh", "ण": "n",
    "त": "t", "थ": "th", "द": "d", "ध": "dh", "न": "n",
    "प": "p", "फ": "ph", "ब": "b", "भ": "bh", "म": "m",
    "य": "y", "र": "r", "ल": "l", "ळ": "l", "व": "v",
    "श": "sh", "ष": "sh", "स": "s", "ह": "h",
    # Nukta letters: sounds Hindi borrowed, each written with its own Roman letter.
    "क़": "q", "ख़": "kh", "ग़": "g", "ज़": "z", "झ़": "zh", "ड़": "r", "ढ़": "rh",
    "फ़": "f", "य़": "y",
}
DIGITS = {chr(0x966 + n): str(n) for n in range(10)}
SIGNS = {"।": ".", "॥": ".", "ॐ": "om", "ः": "h", "॒": "", "॑": ""}
VIRAMA = "्"
ANUSVARA = "ं"      # the dot above: a nasal sound
CANDRABINDU = "ँ"
NUKTA = "़"
LABIALS = set("पफबभम")   # a nasal before these sounds like "m" (sampark), else "n" (jindagi)
DEVANAGARI = range(0x900, 0x980)


def has_devanagari(text: str) -> bool:
    return any(ord(c) in DEVANAGARI for c in text)


def romanize(text: str) -> str:
    """text with every Devanagari run rewritten in Roman; Latin, digits, punctuation kept."""
    out: list[str] = []
    run: list[str] = []
    for char in text:
        if ord(char) in DEVANAGARI:
            run.append(char)
        else:
            if run:
                out.append(_romanize_run("".join(run)))
                run = []
            out.append(char)
    if run:
        out.append(_romanize_run("".join(run)))
    return "".join(out)


def _romanize_run(word: str) -> str:
    """One run of Devanagari characters (letters and their signs) in Roman."""
    units = _units(word.replace("ज्ञ", "ग्य"))      # gyaan, as it is said, not jnaan
    pieces = []
    for i, unit in enumerate(units):
        pieces.append(_render(unit, i, units))
    return "".join(pieces)


class _Unit(dict):
    """One written letter: a consonant with its vowel and nasal, or a vowel, or a sign."""


def _units(word: str) -> list[_Unit]:
    units: list[_Unit] = []
    i = 0
    while i < len(word):
        char = word[i]
        if char == NUKTA:                       # a nukta typed separately after its letter
            if units and units[-1].get("cons"):
                base = units[-1]["char"] + NUKTA
                units[-1]["cons"] = CONSONANTS.get(base, units[-1]["cons"])
            i += 1
            continue
        if char in CONSONANTS:
            unit = _Unit(kind="cons", char=char, cons=CONSONANTS[char], vowel=None,
                         virama=False, nasal="")
            i += 1
            while i < len(word):
                nxt = word[i]
                if nxt == NUKTA:
                    unit["cons"] = CONSONANTS.get(char + NUKTA, unit["cons"])
                elif nxt == VIRAMA:
                    unit["virama"] = True
                elif nxt in MATRAS:
                    unit["vowel"] = MATRAS[nxt]
                elif nxt in (ANUSVARA, CANDRABINDU):
                    unit["nasal"] = nxt
                elif nxt == "ः":
                    unit["nasal"] = "h"
                else:
                    break
                i += 1
            units.append(unit)
            continue
        if char in VOWELS:
            unit = _Unit(kind="vowel", char=char, text=VOWELS[char], nasal="")
            i += 1
            while i < len(word) and word[i] in (ANUSVARA, CANDRABINDU, NUKTA):
                if word[i] != NUKTA:
                    unit["nasal"] = word[i]
                i += 1
            units.append(unit)
            continue
        text = DIGITS.get(char, SIGNS.get(char))
        if text is None:
            text = ""                           # an unmapped Devanagari sign is dropped
        units.append(_Unit(kind="sign", char=char, text=text, nasal=""))
        i += 1
    return units


def _render(unit: _Unit, i: int, units: list[_Unit]) -> str:
    if unit["kind"] != "cons":
        return unit["text"] + _nasal(unit, i, units)
    vowel = unit["vowel"]
    if unit["virama"]:
        vowel = ""
    elif vowel is None:
        vowel = "" if _drop_inherent(i, units) else "a"
    elif vowel == "aa" and _is_last(i, units):
        vowel = "a"                             # word-final: "karta", not "kartaa"
    elif vowel == "e" and unit["nasal"] in (ANUSVARA, CANDRABINDU):
        vowel = "ei"                            # "mein", not "men"
    return unit["cons"] + vowel + _nasal(unit, i, units)


def _nasal(unit: _Unit, i: int, units: list[_Unit]) -> str:
    """The nasal sign after a letter: "m" before p/ph/b/bh/m, else "n"; "h" for visarga."""
    nasal = unit["nasal"]
    if not nasal:
        return ""
    if nasal == "h":
        return "h"
    nxt = units[i + 1] if i + 1 < len(units) else None
    if nxt is not None and nxt["kind"] == "cons" and nxt["char"] in LABIALS:
        return "m"
    return "n"


def _is_last(i: int, units: list[_Unit]) -> bool:
    """Is this the last letter of the word? (A trailing sign, such as a danda, is not one.)"""
    return not any(u["kind"] in ("cons", "vowel") for u in units[i + 1:])


def _drop_inherent(i: int, units: list[_Unit]) -> bool:
    """Is this consonant's inherent "a" silent? (ghar, karta — not ghara, kartaa.)"""
    if _is_last(i, units):
        return True                             # last letter of the word: ghar
    if i == 0:
        return False                            # never the first syllable: karen, not kren
    prev = units[i - 1]
    if prev["nasal"]:
        return False                            # after a nasal: jindagi, not jindgi
    if prev["kind"] == "cons" and prev["virama"]:
        return False                            # second half of a cluster: prayaas, not pryaas
    nxt = units[i + 1]
    if nxt["kind"] != "cons" or nxt["virama"]:
        return False
    # Mid-word, and the next consonant carries a vowel of its own: karta, bolta, karne.
    return nxt["vowel"] is not None
