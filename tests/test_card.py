"""render/card.py (title card; spec 15): title.txt reader, card build and fade, the frame wrapper
and its clash log, the checks, clip copying title.txt, and a short end-to-end render.

Card tests use the real theme fonts; the render test uses a short real ffmpeg encode (qtrle).
"""
from __future__ import annotations

import tempfile
import unittest
from dataclasses import replace
from pathlib import Path
from unittest import mock

from PIL import Image

from lyric_engine import render, workflow
from lyric_engine.render import card as card_mod
from lyric_engine.render.card import TITLE_FILE, build_card, card_checks, read_title, with_card
from lyric_engine.render.encode import RenderError
from lyric_engine.render.frames import LEVELS, _zero_frame
from lyric_engine.theme import BEAT_POP, PHONK_NEON, SOFT_ROMANTIC as THEME, THEMES
from tests.test_render import make_song
from tests.test_workflow import make_source

LINES = ["♪ Mere Saamne Wali Khidki Mein", "Kishore Kumar | Padosan"]


def title(folder: Path, text: str) -> Path:
    (folder / TITLE_FILE).write_text(text, encoding="utf-8")
    return folder


class ReadTitleTest(unittest.TestCase):  # AC6
    def test_lines_as_written(self):
        with tempfile.TemporaryDirectory() as tmp:
            d = Path(tmp)
            self.assertIsNone(read_title(d))
            title(d, "﻿  ♪ Khidki | KISHORE kumar  \n\n  Padosan\n")
            self.assertEqual(read_title(d), ["♪ Khidki | KISHORE kumar", "Padosan"])
            title(d, "\n  \n")
            self.assertEqual(read_title(d), [])
            title(d, "a\nb\nc\n")
            with self.assertRaisesRegex(RenderError, "3 lines"):
                read_title(d)


class BuildCardTest(unittest.TestCase):  # AC3, AC4
    def test_draws_the_file_text_exactly(self):
        drawn = []
        real = card_mod.layout.word_mask

        def recording(text, fonts, pad=0, stroke=0):
            drawn.append(text)
            return real(text, fonts, pad, stroke)
        with mock.patch.object(card_mod.layout, "word_mask", recording):
            for theme in (THEME, BEAT_POP, PHONK_NEON):   # plain, stroked, glowing
                drawn.clear()
                build_card(LINES, theme, 900)
                self.assertEqual(set(drawn), set(LINES), theme.name)

    def test_fits_the_zone_and_sits_at_the_top(self):
        for theme in THEMES.values():
            c = build_card(LINES, theme, 900)
            x, y = c.pos
            box = c.image.getchannel("A").point(lambda v: 255 if v >= 16 else 0).getbbox()
            zone = theme.safe_zone or (60, 380, 1020, 1540)
            self.assertGreaterEqual(x + box[0], zone[0], theme.name)
            self.assertLessEqual(x + box[2], zone[2], theme.name)
            self.assertGreaterEqual(y + box[1], zone[1], theme.name)
            self.assertLess(y + box[3], 700, theme.name)

    def test_too_wide_shrinks_then_refuses(self):
        wide = build_card(["Mere Saamne Wali Khidki Mein Ek Chaand Ka Tukda"], THEME, 900)
        normal = build_card(["Khidki"], THEME, 900)
        self.assertLess(wide.image.height, normal.image.height)
        with self.assertRaisesRegex(RenderError, "too wide"):
            build_card(["x" * 200], THEME, 900)

    def test_fades_in_holds_and_is_gone_by_card_s(self):
        c = build_card(["Khidki"], THEME, 900)   # 30 fps: in 9 frames, gone at 90, out 15
        self.assertEqual((c.fade_in, c.stop, c.fade_out), (9, 90, 15))
        levels = [c.level(k) for k in range(100)]
        self.assertTrue(0 < levels[0] < levels[4] < LEVELS)
        self.assertEqual(levels[8:75], [LEVELS] * 67)
        self.assertTrue(LEVELS > levels[80] > levels[89] > 0)
        self.assertEqual(levels[90:], [0] * 10)
        self.assertEqual(c.level(c.hold), LEVELS)
        self.assertEqual(build_card(["Khidki"], THEME, 40).stop, 40)   # a short song


class WithCardTest(unittest.TestCase):  # AC5
    def test_composes_while_shown_logs_clashes_passes_the_rest(self):
        c = build_card(["Khidki"], THEME, 900)
        zero = _zero_frame(THEME.width, THEME.height)
        clash = bytearray(zero)
        x, y = c.pos
        at = ((y + 5) * THEME.width + x + 5) * 4
        clash[at:at + 4] = b"\xff\xff\xff\xff"   # one lyric pixel under the card
        frames = [[zero]] * 3 + [[bytes(clash)]] + [[zero]] * 96
        out = list(with_card(iter(frames), c, THEME))
        self.assertEqual(c.clashes, [3])
        self.assertIs(out[95], frames[95])   # after the card: untouched
        held = Image.frombytes("RGBA", (THEME.width, THEME.height), out[c.hold][0])
        self.assertEqual(held.crop((x, y, x + c.image.width, y + c.image.height)).tobytes(),
                         c.image.tobytes())


class CardRenderTest(unittest.TestCase):  # AC1
    def test_render_shows_the_card_and_its_checks_are_not_vacuous(self):
        with tempfile.TemporaryDirectory() as tmp:
            song = make_song(Path(tmp), duration=4.0, times=((1.0, 1.5), (2.0, 2.6)))
            title(song, "♪ Khidki | Kishore Kumar\n")
            result = render.render(song, codec="qtrle", theme=THEME)
            self.assertEqual(result.checks, [])
            self.assertIn('title card: "♪ Khidki | Kishore Kumar", 0.0-3.0 s (title.txt)',
                          result.notes)
            c = build_card(["♪ Khidki | Kishore Kumar"], THEME, result.frames)
            moved = replace(c, pos=(c.pos[0], c.pos[1] + 600))   # read where the card is not
            self.assertTrue(any(f.startswith("card: mean alpha")
                                for f in card_checks(result, moved, THEME)))
            c.clashes = [7]
            self.assertIn("card: lyrics drawn under the title card on 1 frame(s); first: frame 7",
                          card_checks(result, c, THEME))

    def test_empty_title_file_is_a_note(self):
        with tempfile.TemporaryDirectory() as tmp:
            song = title(make_song(Path(tmp)), "\n")
            result = render.render(song, codec="qtrle", theme=THEME)
            self.assertIn("title.txt has no text: no title card", result.notes)


class ClipTitleTest(unittest.TestCase):  # AC7
    def test_clip_copies_title_txt(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = title(make_source(Path(tmp)), "♪ Khidki | Kishore Kumar\n")
            workflow.clip_song(source, 3.5, 5.8, Path(tmp) / "clip")
            self.assertEqual((Path(tmp) / "clip" / TITLE_FILE).read_bytes(),
                             (source / TITLE_FILE).read_bytes())


if __name__ == "__main__":
    unittest.main()
