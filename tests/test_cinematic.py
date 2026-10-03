"""render/cinematic.py (Cinematic; spec 10): theme rules, stanza pairing and couplet stacking,
blur-in and colour looks, the one-block life cycle, frames, italic lean, the CLI choice, and a
short end-to-end render with the reveal and safe-zone checks.

Timeline tests use hand-made layouts (no drawing). Frame and render tests use the bundled
Cormorant Garamond Medium Italic and a short real ffmpeg encode (qtrle, the fast codec).
"""
from __future__ import annotations

import contextlib
import hashlib
import io
import string
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path

from PIL import Image

from lyric_engine import cli, render, timing
from lyric_engine.layout import LineLayout, WordBox, font_set, layout_line, word_mask
from lyric_engine.render import cinematic
from lyric_engine.render.cinematic import (
    REST, Block, CinematicCache, block_state, couplet_groups, plan_cinematic, word_look,
)
from lyric_engine.render.check import _ink
from lyric_engine.render.frames import LEVELS
from lyric_engine.render.karaoke import sprite_pad
from lyric_engine.render.timeline import WordPlan
from lyric_engine.theme import CINEMATIC as THEME, DEFAULT_THEME, THEMES
from tests.test_karaoke import low_layout
from tests.test_render import make_song, word

R, H, X, S = 15, 60, 24, 24   # blur-in, hold, exit, gold-to-ivory frames at 30 fps (spec §4.5)
W, HT = THEME.width, THEME.height
HALO = sprite_pad(THEME)


def t(frame: int) -> float:
    """A time that lands exactly on this frame after the 0.05 s lead."""
    return frame / 30 + 0.05


def doc_of(*spans, lyric=None):
    """One word per non-blank lyric line, in order; a span is (first, last) frame or None
    (untimed). Default lyric: one line per span, one stanza."""
    lyric = lyric or [f"w{k}" for k in range(len(spans))]
    lines = [k for k, text in enumerate(lyric) if text.strip()]
    words = [word(k, lyric[li], li, *((None, None) if sp is None else (t(sp[0]), t(sp[1]))))
             for k, (li, sp) in enumerate(zip(lines, spans))]
    return {"lyrics": {"lines": lyric}, "words": words}


def singles(*spans):
    """Every span its own stanza, so each shows as a single block."""
    lyric = [x for k in range(len(spans)) for x in (f"w{k}", "")]
    return doc_of(*spans, lyric=lyric)


def plan(doc, layout_fn=low_layout, n_frames=900):
    return plan_cinematic(doc, THEME, n_frames, layout_fn=layout_fn)


def tall_layout(words, line, theme, emphasis=frozenset(), size=None):
    """One 600 px tall box per word: a single fits the safe zone, a couplet does not."""
    return LineLayout(line, size or theme.font_size, tuple(
        WordBox(i, text, 200 + 120 * k, 800, 100, 600) for k, (i, text) in enumerate(words)))


def block_layout(h):
    def fn(words, line, theme, emphasis=frozenset(), size=None):
        return LineLayout(line, size or theme.font_size, tuple(
            WordBox(i, text, 200 + 120 * k, 1000, 100, h) for k, (i, text) in enumerate(words)))
    return fn


SIZED_CALLS = []


def sized_layout(words, line, theme, emphasis=frozenset(), size=None):
    """Line 0 fits at 96 px, line 1 only at 80 px; records the re-layouts."""
    if size is not None:
        SIZED_CALLS.append((line, size))
    size = size or (96 if line == 0 else 80)
    return LineLayout(line, size, tuple(
        WordBox(i, text, 200 + 120 * k, 1000, 100, 80) for k, (i, text) in enumerate(words)))


def wp(reveal, end):
    return WordPlan(WordBox(0, "w", 0, 0, 10, 10), reveal, end, "w")


def blk(line_first=0):
    return Block((), [], {0: 0}, {0: line_first}, line_first, 0, 0)


def visible(blocks, n):
    return [b for b in blocks if block_state(b, n, THEME)[0] > 0]


def frame(n, blocks, sprites, cache=None):
    return b"".join(bytes(p) for p in cinematic.frame_parts(n, blocks, sprites, THEME,
                                                             cache or CinematicCache()))


class ThemeTest(unittest.TestCase):
    def test_listed_beside_the_others_and_default_unchanged(self):
        self.assertIs(THEMES["cinematic"], THEME)
        self.assertEqual(DEFAULT_THEME, "soft-romantic-v2")
        self.assertEqual(THEME.motion, "cinematic")
        self.assertTrue(THEME.font.is_file(), THEME.font)

    def test_guards(self):
        with self.assertRaisesRegex(ValueError, "cinematic theme needs accent_rgb"):
            replace(THEME, accent_rgb=None)
        for name in ("blur_px", "couplet_gap", "couplet_max_gap_s"):
            with self.subTest(name), self.assertRaisesRegex(ValueError, f"{name} .* negative"):
                replace(THEME, **{name: -1})


class CoupletTest(unittest.TestCase):  # AC3
    def test_groups_pair_inside_stanzas(self):
        self.assertEqual(couplet_groups(["a", "b", "", "c", "d", "e"]), [(0, 1), (3, 4), (5,)])
        self.assertEqual(couplet_groups(["a", "  ", "b", "c", ""]), [(0,), (2, 3)])
        self.assertEqual(couplet_groups([]), [])

    def test_stanza_lines_become_couplets(self):
        blocks, _ = plan(doc_of((10, 40), (50, 80), (100, 130)))
        self.assertEqual([[lay.line for lay in b.lines] for b in blocks], [[0, 1], [2]])
        self.assertEqual([b.name for b in blocks], ["lines 1-2", "line 3"])

    def test_pairs_split_past_the_gap_or_out_of_order(self):
        # couplet_max_gap_s 4 s = 120 frames between line 1's last end and line 2's first reveal
        self.assertEqual(len(plan(doc_of((10, 40), (160, 190)))[0]), 1)
        self.assertEqual(len(plan(doc_of((10, 40), (161, 190)))[0]), 2)
        self.assertEqual(len(plan(doc_of((50, 80), (10, 40)))[0]), 2)

    def test_a_skipped_lines_partner_is_a_single(self):
        blocks, skipped = plan(doc_of((10, 40), None))
        self.assertEqual(skipped, [1])
        self.assertEqual([b.name for b in blocks], ["line 1"])

    def test_too_tall_couplet_shows_as_singles_with_a_note(self):
        blocks, _ = plan(doc_of((10, 40), (50, 80)), layout_fn=tall_layout)
        self.assertEqual([b.name for b in blocks], ["line 1", "line 2"])
        self.assertEqual(blocks[0].notes, ["lines 1-2: shown one at a time (couplet taller than "
                                           "the safe zone)"])

    def test_couplet_shares_the_smaller_size(self):
        SIZED_CALLS.clear()
        blocks, _ = plan(doc_of((10, 40), (50, 80)), layout_fn=sized_layout)
        self.assertEqual([lay.font_size for lay in blocks[0].lines], [80, 80])
        self.assertEqual(SIZED_CALLS, [(0, 80)])

    def test_stacking_gap_centre_and_zone(self):
        fonts = font_set(THEME, THEME.font_size)
        h = fonts.ascent + fonts.descent
        pitch = round(h * THEME.row_spacing)
        gap = pitch - h + round(THEME.couplet_gap * pitch)
        a, b = plan(doc_of((10, 40), (50, 80)))[0][0].lines
        top = round(THEME.anchor_y * HT - (80 + gap + 80) / 2)
        self.assertEqual((a.words[0].y, b.words[0].y), (top, top + 80 + gap))
        self.assertEqual(a.words[0].x, 200)   # only moved vertically

    def test_block_moves_up_to_keep_its_bottom_in_the_zone(self):
        a, b = plan(doc_of((10, 40), (50, 80)), layout_fn=block_layout(400))[0][0].lines
        self.assertEqual(b.words[0].y + 400, 1540 - HALO)
        self.assertGreaterEqual(a.words[0].y, 380 + HALO)


class RevealTest(unittest.TestCase):  # AC4
    def test_blur_in_then_gold_then_ivory(self):
        w, b = wp(30, 60), blk()
        self.assertIsNone(word_look(b, w, 29, THEME))
        level, r, ml = word_look(b, w, 30, THEME)
        self.assertTrue(0 < level < LEVELS and r > 0 and ml == LEVELS)
        looks = [word_look(b, w, n, THEME) for n in range(30, 30 + R)]
        self.assertEqual(looks, sorted(looks, key=lambda k: (k[0], -k[1])))   # sharper each frame
        for n in range(30 + R - 1, 61):
            self.assertEqual(word_look(b, w, n, THEME), (LEVELS, 0, LEVELS), n)
        self.assertTrue(0 < word_look(b, w, 60 + S // 2, THEME)[2] < LEVELS)
        self.assertEqual(word_look(b, w, 60 + S, THEME), (LEVELS, 0, 0))

    def test_short_words_are_complete_by_their_end(self):
        b = blk()
        for end in (30, 31, 33, 44):
            with self.subTest(end=end):
                w = wp(30, end)
                self.assertGreater(word_look(b, w, 30, THEME)[0], 0)
                self.assertEqual(word_look(b, w, end, THEME), (LEVELS, 0, LEVELS))

    def test_untimed_word_is_sharp_ivory_from_its_lines_first_frame(self):
        b, w = blk(line_first=40), WordPlan(WordBox(0, "w", 0, 0, 10, 10), None, None, "w")
        self.assertIsNone(word_look(b, w, 39, THEME))
        for n in (40, 41, 100, 5000):
            self.assertEqual(word_look(b, w, n, THEME), (LEVELS, 0, 0))

    def test_line_two_waits_for_its_own_words(self):
        (block,), _ = plan(doc_of((10, 40), (50, 80)))
        second = block.words[1]
        self.assertEqual(block.enter, 10)
        self.assertIsNone(word_look(block, second, 49, THEME))
        self.assertIsNotNone(word_look(block, second, 50, THEME))


class BlockTest(unittest.TestCase):  # AC5
    def test_one_block_at_a_time_and_the_frame_before_each_is_empty(self):
        for spans in (((10, 40), (160, 190), (200, 230), (243, 260), (262, 300)),
                      ((0, 30), (29, 60), (100, 130))):
            blocks, _ = plan(singles(*spans))
            for n in range(900):
                self.assertLessEqual(len(visible(blocks, n)), 1, (spans, n))
            for prev, b in zip(blocks, blocks[1:]):
                self.assertGreaterEqual(prev.leave, min(prev.last_end, b.first_cur))
                if not prev.notes:   # a cut leaves the old block there; it says so
                    self.assertEqual(visible(blocks, b.first_cur - 1), [])

    def test_hold_early_leave_shrink_and_cut(self):
        E = 40
        last = plan(singles((10, E)))[0][0]                       # hold, then the blur-out
        self.assertEqual((last.leave, last.stop), (E + H, E + H + X))
        early = plan(singles((10, E), (E + 41, 120)))[0][0]      # A = 40 >= X: leaves early
        self.assertEqual((early.leave, early.stop), (E + 40 - X, E + 40))
        shrink = plan(singles((10, E), (E + 11, 120)))[0][0]     # A = 10: exit shrinks
        self.assertEqual((shrink.leave, shrink.stop), (E, E + 10))
        cut, nxt = plan(singles((10, E), (E + 2, 120)))[0]        # A = 1: a cut
        self.assertEqual((cut.leave, cut.stop, nxt.enter), (E + 2, E + 2, E + 2))
        self.assertIn("cut, not faded", cut.notes[0])

    def test_back_to_back_gap_and_a_first_word_at_zero(self):
        a, b = plan(singles((0, 40), (30, 80)))[0]
        self.assertEqual((a.enter, a.stop), (0, 30))
        self.assertTrue(any("are not shown (sung back to back)" in n for n in a.notes))
        a, b = plan(singles((10, 40), (400, 430)))[0]              # instrumental gap: empty screen
        self.assertEqual(a.stop, 40 + H + X)
        self.assertEqual(visible([a, b], 300), [])

    def test_block_state(self):
        b = plan(singles((10, 40)))[0][0]
        self.assertEqual(block_state(b, 9, THEME), (0.0, 0.0))
        self.assertEqual(block_state(b, 10, THEME), REST)
        self.assertEqual(block_state(b, b.leave - 1, THEME), REST)
        mid = block_state(b, b.leave + X // 2, THEME)
        self.assertTrue(0 < mid[0] < 1 and 0 < mid[1] < THEME.blur_px)
        self.assertEqual(block_state(b, b.stop, THEME), (0.0, 0.0))


class FramesTest(unittest.TestCase):  # AC8, plan §2.9
    def real(self, *words, n_frames=300, theme=THEME):
        doc = {"lyrics": {"lines": ["dekha hai"]}, "words": list(words)}
        blocks, _ = plan_cinematic(doc, theme, n_frames)
        return blocks, cinematic.build_sprites(blocks, theme)

    def test_nothing_before_the_first_word_and_exact_colours_at_rest(self):
        blocks, sprites = self.real(word(0, "dekha", 0, t(40), t(80)))
        box = blocks[0].words[0].box
        self.assertEqual(frame(39, blocks, sprites), bytes(W * HT * 4))
        ink = _ink("dekha", font_set(THEME, blocks[0].lines[0].font_size))

        def solid_colours(n):
            img = Image.frombytes("RGBA", (W, HT), frame(n, blocks, sprites))
            crop = img.crop((box.x, box.y, box.x + box.w, box.y + box.h))
            return {crop.getpixel((x, y)) for y in range(box.h) for x in range(box.w)
                    if ink.getpixel((x, y))}

        self.assertLess(max(p[3] for p in solid_colours(40)), 255)            # still blurred
        self.assertEqual(solid_colours(40 + R - 1), {(*THEME.accent_rgb, 255)})   # gold
        self.assertEqual(solid_colours(80 + S), {(*THEME.text_rgb, 255)})         # ivory

    def test_a_blurring_neighbour_never_darkens_gold_ink(self):
        """Every shadow under every glyph: at shadow_radius 16 (a tuning away) the next word's
        shadow reaches this word's ink; at the start value 8 it does not reach it at all."""
        wide = replace(THEME, shadow_radius=16)
        blocks, sprites = self.real(word(0, "dekha", 0, t(10), t(60)),
                                    word(1, "hai", 0, t(41), t(70)), theme=wide)
        box = blocks[0].words[0].box
        ink = _ink("dekha", font_set(wide, blocks[0].lines[0].font_size))
        img = Image.frombytes("RGBA", (W, HT), b"".join(bytes(p) for p in cinematic.frame_parts(
            50, blocks, sprites, wide, CinematicCache())))
        crop = img.crop((box.x, box.y, box.x + box.w, box.y + box.h))
        self.assertEqual({crop.getpixel((x, y)) for y in range(box.h) for x in range(box.w)
                          if ink.getpixel((x, y))}, {(*THEME.accent_rgb, 255)})

    def test_cache_gives_identical_frames(self):
        blocks, sprites = self.real(word(0, "dekha", 0, t(20), t(40)),
                                    word(1, "hai", 0, t(45), t(90)))
        cache = CinematicCache()
        for n in (19, 20, 25, 34, 44, 46, 60, 90, 120, 160, 175, 60, 20):
            self.assertEqual(frame(n, blocks, sprites, cache), frame(n, blocks, sprites), n)

    def test_drawn_text_must_be_the_words_json_text(self):
        blocks, _ = self.real(word(0, "dekha", 0, t(10), t(20)))
        bad = [replace(blocks[0], words=[replace(blocks[0].words[0], text="Dekha")])]
        with self.assertRaisesRegex(AssertionError, "words.json text"):
            cinematic.build_sprites(bad, THEME)


def lean(size: int) -> tuple[dict[int, float], dict[int, float]]:
    """Per row (from the baseline): the widest ink past any character's advance on the right, and
    before its origin on the left."""
    fonts, pad, right, left = font_set(THEME, size), 100, {}, {}
    for ch in string.ascii_letters + string.digits + ".,!?'":
        mask, advance = word_mask(ch, fonts, pad), fonts.advance(ch)
        for y in range(mask.height):
            box = mask.crop((0, y, mask.width, y + 1)).getbbox()
            if box:
                row = y - pad - fonts.ascent
                right[row] = max(right.get(row, -pad), box[2] - pad - advance)
                left[row] = max(left.get(row, -pad), pad - box[0])
    return right, left


class ItalicTest(unittest.TestCase):  # spec §5: a leaning letter never touches the next word
    def test_lean_is_narrower_than_the_word_gap(self):
        """Any two characters on either side of a word gap, each plain or marked (1.5x, 2x),
        sharing a baseline: on no row does ink cross the gap (plan §2.11)."""
        for base, scale in ((THEME.min_font_size, 2.0), (THEME.font_size, 1.5),
                            (THEME.font_size, 2.0)):
            sizes = (base, round(base * scale))
            leans = {s: lean(s) for s in sizes}
            worst = max(leans[a][0][y] + leans[b][1][y] for a in sizes for b in sizes
                        for y in leans[a][0].keys() & leans[b][1].keys())
            self.assertLess(worst, font_set(THEME, base).space, (base, scale))


class CinematicRenderTest(unittest.TestCase):  # AC1, AC6
    def test_render_passes_its_checks_and_they_are_not_vacuous(self):
        with tempfile.TemporaryDirectory() as tmp:
            song = make_song(Path(tmp), lyrics="mere saamne\nwaali khidki\n",
                             times=((0.3, 0.7), (0.8, 1.4), (2.6, 3.0), (3.1, 3.9)),
                             duration=5.0)
            words_sha = hashlib.sha256((song / "words.json").read_bytes()).hexdigest()
            result = render.render(song, codec="qtrle", theme=THEME)
            self.assertEqual(result.checks, [])
            self.assertEqual(result.notes, [])   # every word read, nothing cut
            self.assertEqual(result.render_dir, song / "render" / "cinematic")
            report = (result.render_dir / "report.md").read_text("utf-8")
            self.assertIn("Theme: cinematic", report)
            self.assertIn("reveal check of 4 timed word(s)", report)
            self.assertEqual(hashlib.sha256((song / "words.json").read_bytes()).hexdigest(),
                             words_sha)

            blocks, _ = plan_cinematic(timing.load_words(song / "words.json"), THEME,
                                       result.frames)
            self.assertEqual(len(blocks), 1)   # one couplet
            late = [replace(b, words=[replace(w, reveal=w.reveal + 10, end=w.end + 10)
                                      for w in b.words]) for b in blocks]
            fails = render.check_outputs(result, late, THEME, result.frames)
            self.assertTrue(any(f.startswith("reveal:") for f in fails), fails)
            tight = replace(THEME, safe_zone=(60, 380, 960, 1150))   # cuts through the text
            fails = render.check_outputs(result, blocks, tight, result.frames)
            self.assertTrue(any(f.startswith("safe zone:") for f in fails), fails)


class CliThemeTest(unittest.TestCase):  # AC1
    def test_cinematic_is_offered(self):
        with tempfile.TemporaryDirectory() as tmp:
            song = make_song(Path(tmp), times=((0.3, 0.6), (1.2, 1.6)))
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(cli.main(["make", str(song), "--theme", "cinematic",
                                           "--codec", "qtrle"]), 0)
            self.assertEqual([p.name for p in (song / "render").iterdir()], ["cinematic"])


class RomanticClassicsTest(unittest.TestCase):  # H-041: romantic-soft, classic-sher
    def test_listed_with_their_fonts(self):
        for name in ("romantic-soft", "classic-sher"):
            with self.subTest(name):
                self.assertEqual(THEMES[name].motion, "cinematic")
                self.assertTrue(THEMES[name].font.is_file(), THEMES[name].font)
        self.assertFalse(THEMES["romantic-soft"].couplets)

    def test_couplets_off_shows_every_line_alone(self):
        doc = doc_of((10, 40), (50, 80))
        self.assertEqual(len(plan(doc)[0]), 1)
        blocks, _ = plan_cinematic(doc, replace(THEME, couplets=False), 900, layout_fn=low_layout)
        self.assertEqual([b.name for b in blocks], ["line 1", "line 2"])

    def test_short_word_blur_in_floor_and_the_block_waits_for_it(self):
        slow = replace(THEME, reveal_min_s=0.3)   # 9 frames
        self.assertEqual(cinematic.blur_in_frames(wp(10, 11), THEME), 1)
        self.assertEqual(cinematic.blur_in_frames(wp(10, 11), slow), 9)
        self.assertEqual(cinematic.blur_in_frames(wp(10, 40), slow), R)   # reveal_s still caps
        block = plan_cinematic(doc_of((10, 11)), slow, 900, layout_fn=low_layout)[0][0]
        self.assertEqual((block.last_end, block.settled), (11, 18))

    def test_left_aligned_rows_share_one_edge(self):
        theme = THEMES["romantic-soft"]
        lay = layout_line([(k, w) for k, w in enumerate("Mere saamne waali khidki mein".split())],
                          0, theme)
        rows = {}
        for b in lay.words:
            rows.setdefault(b.y, []).append(b.x)
        self.assertGreater(len(rows), 1)
        self.assertEqual({min(xs) for xs in rows.values()},
                         {theme.center_x - theme.max_width // 2})
        with self.assertRaisesRegex(ValueError, "align 'right'"):
            replace(theme, align="right")


if __name__ == "__main__":
    unittest.main()
