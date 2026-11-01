---
name: social-poster
description: "Trade-fair or event poster, Instagram square or story, thank-you or save-the-date card, and the caption, from a brand's own logo, photos and words."
version: 0.10.0
platforms: [linux, macos]
license: Apache-2.0
metadata:
  domain: marketing
  version: "0.5.1"
workflows:
  - id: "poster"
    arguments: "poster"
    icon: "presentation"
    menu: "Affisch"
    menu_en: "Poster"
    gives: "En mäss- eller eventaffisch som PNG och PDF av er egen logotyp, era bilder och ord"
    gives_en: "A fair or event poster as PNG and PDF from your own logo, photos and words"
    takes: "Släpp logotypen och bilderna, eller skriv en rad: en affisch för Ystad Summer Fair, Stortorget, Ystad, 8 augusti 2026"
    takes_en: "Drop the logo and photos, or write one line: a poster for the Ystad Summer Fair, Stortorget, Ystad, 8 August 2026"
---

# Fair poster

One turn from the ask to the files. The person names a fair; you fill the slots
from what they said and from the folder, run one script, and reply with the PNG and
PDF, plus the MP4 and GIF when the look moves. The layout is fixed in `poster.html` and the picture is the
folder's approved anchor recoloured by arithmetic. Nothing here calls an image
or video model, and nothing is invented: a date, a hall or a claim you were not
given is left off the page and named in the reply.

`SKILL` is this file's folder. The folder the person points at (`KIT`) holds the
brand's own facts: marks, anchors, fonts and three small files. It is theirs,
never edit it. **This skill carries no brand of its own**: no mark, colour,
claim line or fair list lives here, so the same skill serves any brand whose
folder has this shape.

## The folder it expects

| Path | What it is |
| --- | --- |
| `poster.json` | The brand's poster facts: `wordmark` (the file every poster uses), `claim` (the house line when the ask gives none), and the names of the other files |
| `looks.json` | The looks. Each is one approved anchor clip plus the page's tokens: ground, ink, scrims, and which of the brand's own posters it copies. A photo look (`"photo": true`) has no anchor: each fair's own photo is its picture. A light look (`"wash": true`) is white paper washed with the fair's colour: the plate's white stays white and its darkest tone is the colour itself. `cropY` (0 top, 1 foot) says which part of a tall plate a wider canvas shows |
| `fairs.json` | The brand's calendar: the name it uses for a fair, city, country, venue, hall, zone, booth, area, dates, look and colour, for a photo look the fair's `photo` (with `photoTop` when only the top of it may show), `moving`, the look its moving version takes, and `colours`, the fair's colour in a look other than its own (`{"<look>": "#RRGGBB"}`) |
| `marks/` | The wordmark, the certification strip and the fair and product marks, with a `manifest.json` naming each |
| `anchors/` | One approved looping clip per look, 9:16, a clean plate with no text |
| `photos/` | For a photo look: one photo per fair city, with `credits.json` naming the photographer, the page and the licence |
| `fonts/` | The house faces as `.woff2`, with their licences |

## A folder that is not a poster kit

Most folders hold a company's words and maybe a logo, not this shape. Then, in the same turn:

1. Write the caption from the folder's own words and the ask, and hand it over.
2. When the folder has their logo and a photo (the stand, the product or the fair's city), start a kit
   from them and make the poster from it, the same turn:

       python3 SKILL/plain_kit.py --logo "<their logo>" --photo "<their photo>"

   It writes `poster-kit` beside the photo, takes the poster's colour from the photo and turns a dark
   logo white; then run `poster.py --kit "<that poster-kit>"` as below. Add `--claim` only with a line
   the folder or the ask gives word for word. The ask still needs the fair, its city and its dates; a
   fair mark only when the folder has the fair's own logo.
3. Without a logo or a photo, say in one plain line which of the two the person can drop into the
   folder, and that the poster follows from them. Never name poster.json, looks.json, anchors or any
   file of this skill's own, and never offer to draw or generate a picture.

## The laws

1. One turn, no plan to approve. Ask nothing when the ask and the folder answer
   it. Take the documented defaults and say them in one line of the reply.
2. Never invent a fact. A missing date, hall or booth leaves its slot off the
   page and is named in the reply. A fact the folder gives goes on the page as
   the folder writes it: stand B:14 stays B:14. The claim line is the folder's own, never a
   new promise, and never a number we cannot source.
3. The layout is fixed. Never edit `poster.html` to make copy fit: write less,
   or leave an optional slot out. The script refuses copy over a slot's limit.
4. Never a new render. A fair's background is its look's anchor recoloured into
   the fair's colour by `poster.py`. Reuse the loop when it already exists in
   the folder. A photo look is a still poster, PNG and PDF only, the way the brand
   posts its city photos: the fair's own photo from `photos/`, part of its
   colour kept under the fair's, and nothing moves it (no push-in, no pan, no
   sliding words). A moving poster comes from a look whose loop really moves. A
   city with no photo in the folder gets no photo poster, and you say so.
5. The folder's own marks only. Use the version the look calls for, and never a
   mark the folder does not have.
6. Run the check before you reply, and read the picture yourself. A green check
   is not a look; open the PNG against the brand's own poster of that look
   before you hand it over.

## The ask, in the person's words

A fair poster ask names a fair and its dates. Fill this JSON and save it beside
the poster as `fair.json`. Leave out every key the folder's calendar row already
holds: the row writes the dates, hall and booth the way the brand writes them,
and a value typed again drifts from it:

```json
{
  "fair": "<the fair's name, as the brand writes it>",
  "city": "<city>",
  "country": "<country>",
  "venue": "<the venue line, in the brand's own capitals>",
  "year": "2026",
  "dates": "13-14 October",
  "booth": "Hall 3 A12",
  "colour": "#RRGGBB",
  "mark": "<the fair's mark file in marks/>",
  "marks": ["<the certification strip or partner marks>"],
  "claim": "<the house line, when the ask gives none>"
}
```

- `headline` defaults to `See you soon in <city>`, `venue` to `<city>,
  <country>`. Give them only when the person words them differently.
- `moving: true` asks for the fair's moving version: the look the calendar row
  names under `moving` (or the ask's own `look`), in the row's colour, written
  beside the still poster as `<fair>-<year>-moving-<canvas>` with its MP4 and GIF.
  Make it for the post and the story in one run (`--canvas 4x5,9x16`); the A4
  sheet is print.
  With a `look` it is the same fair in another of the folder's moving looks, in the
  colour the row holds for that look under `colours`, else the row's own.
  A look with dark words on a light plate turns the marks dark by itself.
- `marks` (the certification strip) when the person asks for it or the brand's
  own notes put it on that look. A look
  with `"marks": false` (and `"claim": false`) copies posts that carry none, so
  the script keeps them off its page.
- `cue` defaults to `VISIT US AT` when there is a booth, nothing when there is
  not. An empty optional slot leaves its row off the page.
- `look` picks one of the folder's looks. Leave it out unless the person names
  one: the fair's own look, colour, venue, hall, booth and dates come from
  `KIT/fairs.json` when the fair is one the brand has shown at before.
- `colour` is the fair's colour, always `#RRGGBB`. It comes from the calendar
  for a fair already there, and from the person for a new one.
- `mark` is the fair's file in `KIT/marks/`. `marks` is the certification strip
  or up to six partner marks from the same folder.

## The turn

```sh
python3 SKILL/poster.py --kit "KIT" --fair "fair.json"                     # 4:5, the post
python3 SKILL/poster.py --kit "KIT" --fair "fair.json" --canvas 4x5,9x16   # the post and the story, one run
python3 SKILL/check.py "<the poster folder>" --colour "#RRGGBB"
```

Run it once per fair, naming every size the ask wants in that one run
(`--canvas 4x5,9x16`, or `--all-canvases`), and leave `--out` off. A later run
for another size of the same ask adds it to the folder and to its manifest;
nothing made before is lost and nothing needs merging by hand. The script writes straight into
`KIT/posters/<fair>-<year>` (a moving version into `...-moving`, another look
into `...-<look>`) and keeps its own scratch in that folder's `.work`. Never
build a poster somewhere else first to copy it over: a film takes minutes, so
building twice doubles the wait, and `check.py` finds the brand folder from the
poster folder's place inside it. Only `fair.json` belongs in the work area the
app gives you.

`poster.py` writes the poster folder: `<fair>-<year>-4x5.png`, its PDF, the
moving `<fair>-<year>-4x5-motion.mp4` and `.gif`, the recoloured `-loop.mp4` the
folder keeps for reuse, and the manifest beside them; a photo look writes the
PNG and PDF only. Add `--all-canvases` for
the post, the story, the square and the A4 sheet in one run.

Then:

1. Read `check.py`'s lines. Fix what it fails; it names the slot or the file.
2. Open the PNG (and the GIF, on a moving look) yourself and read them against the brand's own
   poster of that look (the look's `reference` line says which one it is).
3. Reply with the files and one line per open gap, in plain words. For a moving
   version hand over the MP4 and the GIF, the files that were asked for; its
   PNG and PDF are only its still. Never a progress note, never a plan.

## A change to posters already made

Each poster folder keeps `<fair>-<year>.json` (a moving version `...-moving.json`,
another look `...-<look>.json`). Its `ask` is the JSON that poster was made from
and `canvases` the sizes it has. Copy the ask, make the one change the person
asked for, and run the script again for the same sizes. Do this for every poster
folder of that fair when they say "all" of them. Never search the disk for an
earlier `fair.json`, and never read outside the folder and the work area: a
change needs nothing else.

## A thank-you after the fair

The same page, posted after the fair. Add `"thanks": true` to the fair's ask and
run `poster.py` as for the announcement:

```json
{"fair": "<the fair>", "city": "<city>", "year": "2026", "thanks": true}
```

- The headline becomes `Thank you, <city>`; give `headline` only when the person
  words it differently.
- The dates stay. The hall and booth are left off, because nobody is asked to
  visit any more; give `booth` only when the person wants it there.
- It is written to its own folder, `<fair>-<year>-thanks`, so it never replaces
  the announcement. With `"moving": true` it moves, in `...-thanks-moving`.
- On a photo look the person may have their own photo of the fair. When they
  give one, save it into the folder's `photos/` and name it in the ask as
  `"photo": "photos/<file>"`; it is toned into the fair's colour like the city
  photo. Without one the fair's own photo is used.
- Never a visitor count, a number of leads or a result nobody gave.

## The season's agenda

One card with every show of a season, grouped by month: the brand's mark and the
word Agenda on top, the season as the title, and one row per show with its days,
city, name, hall and booth. Fill `agenda.json` and run the second script:

```json
{"season": "Fall 2026", "year": "2026", "fairs": ["Shanghai", "Paris", "Munich"]}
```

```sh
python3 SKILL/agenda.py --kit "KIT" --agenda "agenda.json" --all-canvases
python3 SKILL/check.py "KIT/posters/agenda-<season>"
```

- `fairs` names the shows by city, in any order; the script reads each one's
  name, dates, hall and booth from the calendar and sorts them by date. Leave
  `fairs` out for every show the calendar holds for that year.
- A show the calendar does not hold is an object with its own words:
  `{"name": "...", "city": "...", "country": "...", "dates": "3-5 Nov", "hall": "Hall 2", "booth": "B14"}`.
  A show with no dates is left off the card and named in the output: say so in
  the reply. A show with no booth has an empty corner, never a guessed one.
- The card's paper, ink and accent are the folder's own (`poster.json`,
  `"agenda"`). It holds twelve shows at most. The script sizes the type to the
  number of shows; never edit `agenda.html`.
- "Save the Date" is the same card with `"word": "Save the Date"`.

## A caption with the poster

When the person asks for the caption, or the folder's own notes say every post
carries one, write it after the poster is made and checked, as plain text beside
the poster: `<fair>-<year>-caption.txt` (a thank-you's is
`<fair>-<year>-thanks-caption.txt`). Write it in the brand's own voice from the
folder's notes. Say the dates and where to find the stand the way the poster
says them, and state no share, count, year or result that is not on the poster,
in the ask or in the folder's claims (`poster.json`, `claim` and `claims`). A
talk's hour the person gave may stand. Then run `check.py` on the poster folder
again: it reads the caption and fails a share or a count nobody gave, missing
dates or a missing stand. Hand the caption back with the poster.

## Several fairs, or every size, in one ask

Each size of a moving look takes under a minute, so one fair with
`--all-canvases` takes about three; a photo look's still takes under a minute. Run one fair per command, in the foreground, with the shell's
timeout off (`0`); never put a poster run in the background. For several fairs,
run them one after another in the same turn, check each as it lands, and reply
once, when the last one is done and checked. A status note while posters are
still being made ends the turn with nothing handed over.

"Every format", "all four formats" or "every size" means the four canvases
(`--all-canvases`) in the fair's own look, and nothing more. A moving version is
made only when the ask says moving, animated, GIF or MP4. Take that without
asking and say it in one line of the reply.

## What the script decides and what you do

The script: the canvas, the crop, the tint (three stops, or a wash on a light look), the frame count,
the loop's seam, the MP4 and the GIF (about eight frames a second, kept under
15 MB so it can be posted), and every slot's length limit; for a photo
look also how much of the photo's own colour stays, and that it makes no MP4 or GIF. You: the
look when the person asks for one, the fair's mark, the words, and the read of
the picture. When a fair is new, its colour comes from the person; do not invent
one and do not reuse another fair's without asking in one line.

## Limits it holds itself to

Every program it runs has a hard time limit: ten minutes for one encode, three
minutes for one print, thirty minutes for the whole film pass. The film's frame
count and length are read back and must match the loop's before the files are
handed over. A still image is never looped into a clip without a stated length,
which is the shape that once left four encodes running for hours on the box.

## Where things live

- `poster.html` the fixed layout, ported from the old app's social pack 0.3
  `templates/event.html` and its `.social-fair-*` rules. Never edited.
- `colourway.py` the three-stop tint, ported from the old app's
  recolour service, and the wash a light
  look takes. Never edited for one fair.
- `poster.py` the turn's one command. `check.py` the scripted checks.
- `agenda.html` the agenda card's fixed layout, ported from the same pack's
  `templates/agenda.html`; `agenda.py` fills it from the calendar. A thank-you
  is `poster.html` with its own headline, as the old pack's `thanks.html` was
  the event page with its own words.
- `KIT/README.md` the folder the person points the app at, in their words.
