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

| # | Song | Folder `songs/...` | Template | Hero words to mark | First 4 |
|---|---|---|---|---|---|
| 1 | Barsaat Ki Dhun (Jubin Nautiyal | Single (2021)) | `barsaat_ki_dhun` | `rain` | barsaat, dhun | yes |
| 2 | Baarish (Mohammed Irfan | Yaariyan (2014)) | `baarish` | `rain` | baarish |  |
| 3 | Tum Se Hi (Mohit Chauhan | Jab We Met (2007)) | `tum_se_hi` | `rain` | din, shaam |  |
| 4 | Tum Hi Ho (Arijit Singh | Aashiqui 2 (2013)) | `tum_hi_ho` | `fog` | wajood, tum |  |
| 5 | Agar Tum Saath Ho (Alka Yagnik, Arijit Singh | Tamasha (2015)) | `agar_tum_saath_ho` | `fog` | saath |  |
| 6 | Raabta (Arijit Singh | Agent Vinod (2012)) | `raabta` | `milan` | raabta |  |
| 7 | Kesariya (Arijit Singh | Brahmastra (2022)) | `kesariya` | `milan` | kesariya, ishq |  |
| 8 | Tum Mile (Neeraj Shridhar | Tum Mile (2009)) | `tum_mile` | `milan` | mile |  |
| 9 | Chand Sifarish (Shaan, Kailash Kher | Fanaa (2006)) | `chand_sifarish` | `chaand` | chand, sifarish | yes |
| 10 | Chaand Baaliyan (Aditya A | Single) | `chaand_baaliyan` | `chaand` | chaand, baaliyan |  |

## Classics (style `classic-line`)

| # | Song | Folder `songs/...` | Template | Hero words to mark | First 4 |
|---|---|---|---|---|---|
| 1 | Gaadi Bula Rahi Hai (Kishore Kumar | Dost (1974)) | `gaadi_bula_rahi_hai` | `rail` | gaadi, seeti |  |
| 2 | Mere Sapno Ki Rani (Kishore Kumar | Aradhana (1969)) | `mere_sapno_ki_rani` | `rail` | rani |  |
| 3 | Hai Apna Dil To Awara (Hemant Kumar | Solva Saal (1958)) | `hai_apna_dil_to_awara` | `rail` | awara, dil |  |
| 4 | Lag Jaa Gale (Lata Mangeshkar | Woh Kaun Thi? (1964)) | `lag_jaa_gale` | `talkies` | gale, raat | yes |
| 5 | Chaudhvin Ka Chand Ho (Mohammed Rafi | Chaudhvin Ka Chand (1960)) | `chaudhvin_ka_chand` | `talkies` | chand, aaftaab |  |
| 6 | Pal Pal Dil Ke Paas (Kishore Kumar | Blackmail (1973)) | `pal_pal_dil_ke_paas` | `talkies` | dil, paas |  |
| 7 | Tere Bina Zindagi Se Koi (Kishore Kumar, Lata Mangeshkar | Aandhi (1975)) | `tere_bina_zindagi_se` | `talkies` | zindagi, shikwa |  |
| 8 | Rimjhim Gire Sawan (Kishore Kumar | Manzil (1979)) | `rimjhim_gire_sawan` | `ghata` | rimjhim, sawan | yes |
| 9 | Pyar Hua Ikrar Hua (Lata Mangeshkar, Manna Dey | Shree 420 (1955)) | `pyar_hua_ikrar_hua` | `ghata` | pyar, ikrar |  |
| 10 | Megha Chhaye Aadhi Raat (Lata Mangeshkar | Sharmilee (1971)) | `megha_chhaye_aadhi_raat` | `ghata` | megha, raat |  |

Each folder already has `title.txt`; add `audio.mp3` (the 30-60 s clip) and `lyrics.txt`
(only those lines). Mark one occurrence of each hero word, `*word*`, ideally in different lines;
if a word is not in the clip, mark another strong word from it (a noun or the emotional word).
Template reasons: rain songs on `rain`, aching love on `fog`, meeting on `milan`, moon songs on
`chaand`; train songs on `rail`, the golden-era film song on `talkies`, monsoon songs on `ghata`.

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
