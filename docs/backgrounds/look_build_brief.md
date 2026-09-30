# How to build the next background look (the proven flow)

Used for khaali, aakhri and chaand (2026-10-01). One look ≈ 30 min of an agent's wall time for the
sample plus ~30 min to move it into the engine and check it. Two agents at a time is the most this
8 GB laptop takes (they render too).

## 1. An agent makes the moving sample

Give a general-purpose agent a brief with these parts (copy the briefs of khaali/aakhri/chaand from
the session of 2026-10-01 if they are at hand; this is their skeleton):

- **Read first:** `docs/backgrounds/romantic_lights.md` (owner's rules H-032 at the top), the
  engine looks in `src/lyric_engine/background/` (use `paint.py`), frames of the approved samples
  (`songs/_review/backgrounds/lights2/*_final.mp4`, `sad/khaali_jagah_sample.mp4`), the idea's
  still `songs/_review/backgrounds/templates/<type>/<slug>_{mid,end}.png`, its still script
  `templates/<type>/draw.py`, the critic's notes in `templates/_results.json`
  (`recheck:<type>`, else `review:<type>`), and the spec in `ideas_all.json`.
- **Build** `songs/_review/backgrounds/templates/<type>/<look>.py` with `class Scene`:
  - `Scene(facts)` keeps `self.facts = facts` (the engine's report and workers read it);
  - `look`, `in_order` (False: `frame(k)` a pure function of k and facts, so workers can draw it);
  - `describe()`;
  - `frame(k, ink=None)` → (1920, 1080, 3) uint8.
  Imports: numpy, scipy, PIL, stdlib and `from lyric_engine.background import paint as P` only.
  Static art once in `__init__` (≤ ~8 full-size float32 arrays; float16 or quarter size where
  possible); ≤ 1.5 s per frame.
- **Song reaction** from facts only: `words` (start, marked, cx, cy), `marks`, `line_starts`,
  `last_line_s` (else 0.85 × duration), `lyric_box`, `block_centre`. Must also work with no
  words (the `backdrop --seconds` mode). Never read what the words say.
- **Legibility:** a calm patch behind `lyric_box`; the sample must have 0 frames below 3:1.
- **Test** with `songs/_review/backgrounds/run_scene.py <file> --stills 30,120,225,330,411`
  and `--video <sample>.mp4` (real overlay, prints the 3:1 result); `--no-words` for the song-free
  mode. Look at every still; iterate until ~7.5/10.
- **Constraints:** write only in its own templates folder, no git, one python process at a time.

## 2. Move it into the engine

1. Copy to `src/lyric_engine/background/<look>.py`; change the import to `from . import paint as P`.
2. Add `"<look>": ("<mood>",)` to `WORLDS` in `background/__init__.py`; the CLI help list in
   `cli.py` (`--bg` help).
3. `run_scene.py src/lyric_engine/background/<look>.py --stills ...` (stills go to
   `songs/_review/backgrounds/_stills/`).
4. Tests: `tests.test_background.EveryLookTest` covers every look in `WORLDS` (draws, `.facts`,
   pure frames); add a look test only for special behaviour.
5. Real render: `render songs/khidki_30s --theme soft-romantic-v2 --bg <look>` → checks pass.
6. A doc `docs/backgrounds/<type>_<look>.md` (status, idea, layers, reaction, known issues);
   CLAUDE.md's `--bg` list.

## Next looks (H-038 picks, in this order)

| Look | Type | Test song | Watch out |
|---|---|---|---|
| Rail ki Seeti | classics | khidki | engine front not a face; woman in saree with pallu |
| Taaron ka jaal | hip-hop | a beat song (owner) | floor not a canal; beat reaction needs `beats.json` |
| Jaali se subah | sufi | khidki | 30 s/frame now: cache the static hall first |
| Shamiyane ki parchhaiyan | party | a beat song (owner) | dancers' shadows not puppet-like |
| Parchhaiyan | family | khidki | shadows as shade, not black paint; maa with pallu |

Beat looks need facts with beat times: add them to `SongFacts` (from `beats.ensure_beats`) when the
first beat look is built.
