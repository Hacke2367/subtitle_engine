# Video plan: 20 shorts (10 romantic, 10 classics)

Picked by Claude on 2026-10-01 for the owner's first 20 videos. Each song goes on the template
whose idea it matches; the lyric style comes with the template (D-041: romantic looks use
`romantic-line`, classics `classic-line`), so no `--theme` is needed.

Fastest way per song (2026-10-02):
1. `songs/<name>/`: `audio.mp3` cut to the best-known 30-60 s (usually the mukhda) and
   `lyrics.txt` with only those lines, one sung line per line. Aligning a short clip is quick.
2. Mark 2-3 hero words with `*word*` (the looks' best moments happen on them).
3. `title.txt`: song name on line 1, `Singer | Film (Year)` on line 2.
4. `make songs/<name> --bg <template>`; the finished short is
   `songs/<name>/render/<style>/final_<template>_<mood>.mp4` (overlay.mov is next to it).

## Romantic (style `romantic-line`)

| # | Song (film, year, singer) | Template | Why this template |
|---|---|---|---|
| 1 | Barsaat Ki Dhun (single, 2021, Jubin Nautiyal) | `rain` | a rain song; colour rises where the rain lands |
| 2 | Baarish (Yaariyan, 2014, Mohammed Irfan) | `rain` | rain as longing, slow and soft |
| 3 | Tum Se Hi (Jab We Met, 2007, Mohit Chauhan) | `rain` | "tum se hi din hota hai": colour coming into a grey day |
| 4 | Tum Hi Ho (Aashiqui 2, 2013, Arijit Singh) | `fog` | deep, aching love; moonlight and shadow through fog |
| 5 | Agar Tum Saath Ho (Tamasha, 2015, Alka Yagnik, Arijit Singh) | `fog` | love about to be lost; the dark, misty look holds the pain |
| 6 | Raabta (Agent Vinod, 2012, Arijit Singh) | `milan` | "raabta" is the look itself: two lights meet and glow |
| 7 | Kesariya (Brahmastra, 2022, Arijit Singh) | `milan` | two people drawn together; the meeting lights carry it |
| 8 | Tum Mile (Tum Mile, 2009, Neeraj Shridhar) | `milan` | "tum mile": the moment of meeting |
| 9 | Chand Sifarish (Fanaa, 2006, Shaan, Kailash Kher) | `chaand` | a moon song; the veil lifts off the moon |
| 10 | Chaand Baaliyan (single, Aditya A) | `chaand` | moon imagery, soft night mood |

## Classics (style `classic-line`)

| # | Song (film, year, singer) | Template | Why this template |
|---|---|---|---|
| 1 | Gaadi Bula Rahi Hai (Dost, 1974, Kishore Kumar) | `rail` | a train song; the train leaves on the last line |
| 2 | Mere Sapno Ki Rani (Aradhana, 1969, Kishore Kumar) | `rail` | the most famous train song of the era |
| 3 | Hai Apna Dil To Awara (Solva Saal, 1958, Hemant Kumar) | `rail` | sung on a train at night |
| 4 | Lag Jaa Gale (Woh Kaun Thi?, 1964, Lata Mangeshkar) | `talkies` | the golden-era film song itself; the show ends as the song ends |
| 5 | Chaudhvin Ka Chand Ho (Chaudhvin Ka Chand, 1960, Mohammed Rafi) | `talkies` | a black-and-white classic; `chaand` also fits (a moon song) |
| 6 | Pal Pal Dil Ke Paas (Blackmail, 1973, Kishore Kumar) | `talkies` | a hall favourite; warm and intimate |
| 7 | Tere Bina Zindagi Se Koi (Aandhi, 1975, Kishore Kumar, Lata Mangeshkar) | `talkies` | quiet, cinematic longing |
| 8 | Rimjhim Gire Sawan (Manzil, 1979, Kishore Kumar / Lata Mangeshkar) | `ghata` | the monsoon song; the rain arrives on the last line |
| 9 | Pyar Hua Ikrar Hua (Shree 420, 1955, Lata Mangeshkar, Manna Dey) | `ghata` | the famous rain-and-umbrella duet |
| 10 | Megha Chhaye Aadhi Raat (Sharmilee, 1971, Lata Mangeshkar) | `ghata` | "megha chhaye": dark clouds at midnight |

Spread: romantic 3 rain, 2 fog, 3 milan, 2 chaand; classics 3 rail, 4 talkies, 3 ghata, so no
template repeats too often in a row. Post them mixed (romantic, classic, romantic ...).

## Template verdicts (khidki reel, 2026-10-02)

Judged on the khidki mukhda (30 s, three `*marked*` words, title card) rendered on every template
(`songs/_review/khidki_reel/`). Hook = what the first second gives a scroller (motion and
brightness of the opening); all seven pass the engine's legibility check.

| Template | Hook | Lyrics | Background | Payoff | Score |
|---|---|---|---|---|---|
| `chaand` | moon hidden, comes out at ~3 s | clean, *chaand* big in blush | calm moon night | veil lifts off | 7.5 |
| `ghata` | clouds roll, warm horizon (motion 0.42) | gold sher over dark clouds, very clear | dramatic monsoon sky | rain on the last line | 7.5 |
| `rain` | strongest: rain from frame 0 (motion 1.78, brightest) | a little washed out on grey | soft rain, colour glows | none | 7 |
| `talkies` | "old cinema" reads at once, title on the screen | clear | film shots change per line | curtain closes, lights up | 7 |
| `rail` | dim, still (motion 0.16) | clear sher, gold *chaand* | detailed period station | the train leaves | 7 |
| `fog` | moonlight rays, dreamy | very clear | rays, black lower third | none | 6.5 |
| `milan` | weakest: near-black first frame | clearest (white on black) | sparse dots, warm glows on marks | none | 6 |

Lessons for the 20 videos: mark 2-3 words in `lyrics.txt` (the looks' best moments only happen on
marked words); always add `title.txt`; match the template to the song's own image (the khidki
lyric "chaand" made `chaand` the best fit); start the clip right where the best-known line begins.
