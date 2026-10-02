# Video plan: 20 shorts (10 romantic, 10 classics)

Picked by Claude on 2026-10-01 for the owner's first 20 videos. Each song goes on the template
whose idea it matches; the lyric theme is `romantic-soft` for romantic songs and `classic-sher`
for classics (D-038). Use the song's best-known 30-60 s (usually the mukhda) as the clip:
`clip songs/<full-song> --from M:SS --to M:SS`, then `make songs/<clip> --theme ... --bg ...`.

## Romantic (`--theme romantic-soft`)

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

## Classics (`--theme classic-sher`)

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
