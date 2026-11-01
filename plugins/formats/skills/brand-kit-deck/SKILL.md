---
name: brand-kit-deck
description: Build or revise a PowerPoint deck that follows a brand kit (fonts, palette, limits, footer), for example a kit.json file. Use whenever a deck must follow a brand kit or house style file.
license: Apache-2.0
metadata:
  domain: formats
  version: "0.1.0"
workflows:
  - id: "brand-deck"
    arguments: "deck"
    icon: "presentation"
    menu: "Presentation efter varumärket"
    menu_en: "Brand deck"
    gives: "En PowerPoint som följer er varumärkesmall"
    gives_en: "A PowerPoint deck that follows your brand kit"
    takes: "Släpp varumärkesmallen och underlaget"
    takes_en: "Drop the brand kit and your material"
---

# Build a deck from a brand kit

When the person gives a brand kit (fonts, a palette, limits, a footer), or a
kit file such as `kit.json`, build the deck with `scripts/pptx_from_kit.py`.
The kit owns the look, so you write only the words and the chart data.

```bash
python3 scripts/pptx_from_kit.py kit.json slides.json out.pptx
```

`slides.json` is `{"properties": {"title": ...}, "slides": [...]}`. Each
slide has a `role` (`title`, `content`, `chart` or `picture`), a `title`, and
`bullets`, a `subtitle`, a `chart` with `categories`, `series` and `alt`, or a
`picture` with `path` and `alt`. Run the script with `--help` for the full
shapes. It needs python-pptx.

- The script sets every font, colour, size and the footer from the kit, puts
  the title in the title placeholder, gives charts alternative text and
  palette colours, and names the deck. Do not restyle its output by hand.
- Put screenshots and photos in a `picture` slide. The script keeps the
  picture in its own area at its true proportions, beside the text. Never add
  a picture to the built file with your own code: it lands on top of the text.
- Body text is one size on every slide, set by the fullest slide. If it comes
  out small, shorten the longest slide and build again.
- Nothing decorative is drawn: no rule under the title, no shadow, no shape
  that carries no information, and titles in the regular weight. A kit may
  name a `logo` file, and ask for `"style": {"title_rule": true}` or
  `"bold_titles": true` when the company's own look has them.
- It stops with a list of slides to shorten when a slide is over the kit's
  word or paragraph limit or its text cannot fit at the minimum size. Rewrite
  those slides shorter, keeping every figure and date, and run it again.
- When the kit changes (a new accent colour, a removed slide), write the
  changed kit to a new kit file, change the slide list and rebuild. Do not
  patch colours in the old file.

## Check before you deliver

Run the check on the finished deck, with absolute paths, the kit file the deck
must follow and the number of slides asked for:

```bash
python3 scripts/check_file.py /absolute/path/deck.pptx --kit /absolute/path/kit.json --slides 6
```

It prints each rule with pass or fail and what it found, and exits 1 when a
rule fails. Fix what fails by changing `slides.json` or the kit file and
rebuilding, then run it again until every rule passes. When the
`openpaperwork-checks` server is connected, its `check_file` tool runs the
same check with `path`, `kit` and `slides`.
