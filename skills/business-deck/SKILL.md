---
name: business-deck
description: "Business deck, slides or presentation as a PDF, PowerPoint on ask: board update, proposal, sales or investor deck, laid out and checked by script."
version: 0.3.0
license: Apache-2.0
platforms: [linux, macos, windows]
metadata:
  domain: marketing
  version: "0.3.0"
workflows:
  - id: "deck"
    arguments: "deck"
    icon: "presentation"
    menu: "Presentation"
    menu_en: "Deck"
    gives: "En presentation som PDF, och PowerPoint om ni vill"
    gives_en: "A deck as PDF, and PowerPoint when you want it"
    takes: "Släpp underlaget, eller skriv en rad: styrelseuppdatering för tredje kvartalet"
    takes_en: "Drop the material, or write one line: a board update for the third quarter"
---

# Business deck

Use this when someone asks for a deck to decide on or to report with: a board or management update,
a proposal, a business case, a steering-group or sales deck. The person gets a PDF that reads like
a consulting deck: the file they send, print and present from, with real text, bookmarks for the
sections and every chart drawn from their figures. When they ask for slides they can change, they
also get the same deck as a PowerPoint file that stays theirs to edit: every chart and table is
native, every text sits in a layout placeholder, and the look is the slide master's.

You never lay out a page. You decide the story and write it as data; `scripts/deck_build.py` builds
the deck; the pack check tells you what to fix.

## What is handed back

- **The PDF, always.** `<name>.pdf` is the deck. It is made the same way on every computer, inside
  the app with nothing else installed.
- **The PowerPoint file, when the person asks for one to edit.** Words like "editable", "PowerPoint",
  "Keynote", "Google Slides", "slides I can change", "a template for the team" mean: build with
  `--editable` and hand back `<name>.pptx` beside the PDF. An ask that names no format ("make me
  a deck for the board") gets the PDF alone. Set `"editable": true` in the data when the person
  wants the editable file every time.
- **A person with neither PowerPoint nor Keynote** loses nothing: the PDF is the deck. The
  `.pptx`, when they have one, also opens in Keynote, LibreOffice and Google Slides.
- The two files are one deck from one description. They are laid out on the same positions and
  each passes the same rules on its own pages; they are not pixel for pixel the same, because
  PowerPoint breaks a line where it likes.

## The loop

1. **Plan the story before the first page.** Write the answer in one sentence: what the reader
   gets, or must decide. Split the support into two to five sections. From eight pages on a deck
   opens with a cover, an executive summary (one block a section) and an agenda, marks its sections,
   and closes on next steps with an owner and a date each. Naming the page's `section` marks it: the
   name runs along the top of the page. Use one short name a section, the same word for word in the
   agenda's `items`, in the summary's blocks and as the `section` of every page of that section,
   the next-steps page included. A divider page of its own is for a deck of twenty pages or more.
   Give each page one message.
2. **Read a sample, then write the data** as `<name>.deck.json` in the person's folder. The two
   samples show the shape of every key: `templates/board-update.deck.json` (a board update: summary,
   charts, key figures, a table, a comparison, a process, a timeline, next steps) and
   `templates/proposal.deck.json` (a proposal: a problem, options compared, a 2x2 matrix, a quote, a
   price table, a figure, a plan, an appendix). Every word on a page comes from your file: the
   builder writes no label of its own. Use only figures and names the person gave you; where the
   notes do not say something a page needs, leave that piece out and say so when you hand back.
3. **Build**, in the person's folder, beside the data:

   ```bash
   python3 <skill folder>/scripts/deck_build.py "<name>.deck.json" "<name>.pdf"
   ```

   It writes the PDF and says how many pages. Add `--editable` when the person asked for slides to
   edit: it writes `<name>.pptx` beside the PDF. The editable file is presented from, so every page then
   needs `notes`: two or three sentences the presenter says aloud on that page, in the deck's language,
   that open with the page's point and say nothing the page and the person's notes do not carry. The
   builder refuses an editable deck with a page that has none. If it stops with `refused:`, the line says which
   page and key to fix.
4. **Run the check and fix the data**, never the file:

   ```bash
   python3 <skill folder>/../_checks/packcheck.py business-deck "<name>.pdf"
   ```

   It prints one FAIL line a rule with the slide, what is wrong and where the rule comes from. Fix
   the data, build again, at most three times; if a rule still fails, say plainly which and what you
   tried. "pack check clean" with the number of rules passed is the only pass. A WARN line is a
   question: answer it by changing the data, or say why it stands. When you built the editable file
   too, run the same check on `<name>.pptx`.
5. **Look at the pages.**
   `python3 <skill folder>/scripts/deck_look.py "<name>.pdf" look --sheet look/sheet.jpg` writes one
   picture a page and one sheet of all of them into a new folder inside `look` and prints each path;
   read only the paths it prints, never a sheet from an older run. Read them as images: a page that stops half way
   down, a chart that does not say what its title says, a title that wraps badly. Delete the `look`
   folder before you hand back.
6. **Hand back** the PDF, and the PowerPoint file when you built one, named as the person named the
   deck. Keep the data file beside it so the deck can be changed later. The reply is at most three
   short lines, plain sentences, no list and no headings: where the deck is, what it holds, which
   preset you built in, and anything on a page the person's notes did not give you. Never paste the
   deck's pages into the chat.

On a PDF every page rule is measured on the printed pages: where each line of text really breaks,
how full the page really is, the size and colour every letter is really set in. Nothing is
estimated. A PDF made any other way (exported by hand, printed from another tool) carries no
description of its pages and the check says so; build the deck from its data.

Inside the app the scripts need nothing: the app's own browser engine prints the pages. Elsewhere
they need Python 3.10 or later with `pypdf`, `pypdfium2` and `Pillow` (and `python-pptx` for the
editable file) and a headless browser for printing; where `python3` lacks them, the builder and
the check run themselves through `uv` when it is installed (it fetches the packages into its own
cache and touches nothing of the system), and the builder names the one line that installs the
browser if it is missing. Without uv they stop and name the one `pip install` line.

## How a page is written

- **The title is the page's message, as a sentence, without a closing full stop.** "Churn in small
  accounts doubled in a year", not "Churn" and not "Customer overview". The builder takes one
  closing full stop off a title, so every page reads the same; a cover or closing statement that
  is a full sentence keeps its own.
- **Labels are in sentence case**, as the titles are: a section is "Solution options", not
  "Solution Options". The check asks about a label set in Title Case; a name keeps its capitals. A statement heading tells the reader the point before
  they read the page (US plain language guidelines, "Add useful headings"; UK Government Analysis
  Function, charts: the headline title gives the chart's message). A script cannot prove a title
  has a verb in every language: it checks length (six to eighteen words in the standard preset),
  lines, that no two titles are the same and that the title is not just the name of a kind of page.
  The sentence is yours to write.
- **One message a page, one exhibit a page.** A second chart means a second page.
- **Every chart names its measure, its unit and its period once**, in the line above it (`measure`,
  `unit`, `period`), and its source under it (`source`, written in full: "Source: management
  accounts, 30 September 2026"). Tables and figures carry a source the same way.
- **Label the marks, not a legend.** Up to four series are named beside their marks; values are
  printed on the bars. Text stays horizontal. Bars start at zero; no 3D; no pie with more than five
  parts. A line shows change: its scale starts just under its lowest value unless the data comes
  near zero, no value axis is drawn, and both ends of every line carry their values. Use `column`
  for amounts a period (revenue by quarter) and `line` for a rate that moves (a share, a ratio).
- **One highlight, on what the title is about.** Name it in `highlight` (a category, a series, a
  table row's first cell, a comparison's option, a matrix's quadrant) and every other mark stays
  grey. If the title does not name the highlighted thing, one of the two is wrong.
- **The takeaway is one sentence**, at most three lines where it stands beside the exhibit; the
  points under it carry the detail.
- **A chart earns its place.** Fewer than three values are key figures, not a chart, and a chart
  that only repeats the figures printed beside it goes.
- **A table is as tall as its rows.** Numbers and their headings are right-aligned by the builder;
  write one precision down a column and put the unit in the heading or in a unit column, never in
  every cell.
- **Next steps have an owner and a date.** Give the three column headings in the deck's language.
- Alternative text for a chart or a picture (`alt`) says what kind of thing it is, the data and the
  takeaway in at most 250 characters (CFPB data visualization guidelines).

## Page types

| `type` | What it is for | Its keys |
| --- | --- | --- |
| `cover` | The answer, the deck's name, who it is for and the date | `title`, `subtitle`, `meta` (up to three `key` and `value` pairs; one is the date) |
| `summary` | The executive summary: three to five blocks, one a section | `blocks`: `section` (a section's name, as in the agenda), `lead`, `points` |
| `agenda` | The sections in order | `items`: `name`, `text` |
| `section` | A divider page before a section; asked for only from twenty pages on | `title` |
| `chart` | One chart with its takeaway | `kind` (column, bar, line, stacked), `measure`, `unit`, `period`, `categories`, `series` (`name`, `values`), `highlight`, `decimals`, `takeaway`, `points`, `alt`, `source` |
| `figures` | Two to four key figures, never a chart of them | `figures`: `label`, `value` (as it is said, with its sign: "78%", "18.4"), `unit` (of what: "EUR million", "of revenue"), `period`, `note`; `takeaway`, `source` |
| `comparison` | Two or three options on the same rows | `options`, `rows`: `label`, `values` (one an option); `highlight`, `source` |
| `table` | A table of figures | `head` (one line: what the table shows, with its unit), `columns` (the headings, one a column), `rows` (lists of cells, as text), `highlight`, `takeaway`, `points`, `source` |
| `matrix` | A 2x2: items placed on two axes, one quadrant the message | `x` and `y` (each `name`, `low`, `high`), `quadrants` (`top_left`, `top_right`, `bottom_left`, `bottom_right`), `items` (`name`, `x`, `y`), `highlight`, `takeaway`, `points`, `source` |
| `figure` | One picture, or one page of a real file, as the exhibit | `image` (a PNG or JPEG beside the data), `caption`, `alt`, `takeaway`, `points`, `source` |
| `quote` | One sentence somebody said | `quote`, `name`, `role`, `source` |
| `process` | Three to six steps in order | `steps`: `name`, `detail`; `takeaway` |
| `timeline` | Three to six dated steps on one line | `steps`: `when`, `what`, `detail` |
| `text` | A statement and the points that carry it | `statement`, `points`: `point`, `detail` |
| `next-steps` | Actions with their owner and date | `columns` (three headings), `steps`: `action`, `detail`, `owner`, `date` |
| `closing` | What is asked, and whom to reach | `title`, `contact` (lines), `small` |
| `appendix` | The divider that opens the appendix; every page after it is a backup page | `title`, `mark` |

Every page takes `title`, and content pages take `section` (the section's name, shown in the
running line) and `notes` (speaker notes: what the presenter says on that page; every page of an
editable deck has them, and a PDF never carries them). The deck takes `title` (it names the file and runs along
every page in one line of small print, so keep it to about forty characters: "Board update, third
quarter 2026"), `organisation`, `language`, `density` and `editable` (true writes the PowerPoint
file beside the PDF on every build). Leave `organisation` out when the folder holds a
`company.json`: the builder takes the company's name from it. A figure, a date or an e-mail address
on a page comes from the person's files; the check asks about one that is nowhere in them. The builder refuses a key it does not know and names the ones
it does.

### The four that need a word more

- **`matrix`.** `x` runs left to right and `y` bottom to top; `low` and `high` are the words at the
  ends ("Little", "Much"). An item's `x` and `y` are its place along each axis from 0 (the low end)
  to 1 (the high end), so `"x": 0.2, "y": 0.9` is top left. Name all four quadrants, place two to
  eight items, and set `highlight` to the name of the one quadrant the page is about. The title
  names that quadrant or an item in it.
- **`figure`.** The picture is a file in the same folder as the data: a photograph, a screenshot,
  or one page of a document saved as a PNG. It is shown whole, at its own proportions, never
  cropped or stretched; a file under about 110 pixels for each inch it is shown at fails as
  blurred. `caption` says in a line what the picture is (the title says what it means), `alt` says
  what it shows for a reader who cannot see it, `source` says where it comes from.
- **`quote`.** One sentence of six to thirty words, as it was said, with its quotation marks if you
  want them (the builder adds none). `name` is who said it and `role` what they are to the reader
  ("Office manager, Riverside"). Nothing else goes on the page, and a deck holds one quote page.
  Quote only what the person's notes quote.
- **`appendix`.** Put it after the closing page. Every page after it is a backup page: any content
  page (chart, table, text and so on), numbered A1, A2 under the first letter of the appendix's
  title (or `mark`), with the appendix's name in its running line. Backup pages stand outside the
  storyline (no summary block, no agenda line, no section of their own) and inside every other
  rule: a message as the title, a source, fit, fill, type, contrast.

## Density

How much a page carries is a preset of numbers in `density.json`, and the check reads every bound
from the preset the deck was built in.

- `standard` (the default): a deck read at a desk. Supporting detail (`points`, `detail`, `note`)
  is on the page.
- `sparse`: a deck a speaker stands beside. Larger type and wider margins; each piece's detail goes
  into the speaker notes, and a chart or table takes the full width with its takeaway under it. A
  PDF has no speaker notes: the builder says how many pieces of detail it kept off the pages, and
  they are in the editable file. For a deck that is only read, build in `standard`. A
  table of six or seven rows stays whole; a table or list continues on a next page only when its
  rows do not fit at that size, the title counting them (1/2), (2/2), and never so that a page is
  left with fewer than four rows. Write the data once; it builds in either.
- `full`: closest to a consulting page read at a desk: smaller type, more rows a page.

Choose with `--density sparse`, or `"density": "sparse"` in the data. Write for the preset: a
sparse page holds at most 90 words, a standard page 120. A page whose content stops in its upper
half, a table of two rows or a closing page of one line fails the fill rule in either.

## The look

The look is one file, `look.json`: inks, the face, the type scale for each preset, letter spacing
for large type, margins, the logo and where the running line sits. The scale has a step for each
job: display for the cover and the closing statement, headline for a quote, title for every content
page, lead for a statement or takeaway inside the body (one step under the title), body, and small
print. Both outputs read this one file. A company's own look is another such file, passed with
`--look`; the page types, the grid and every rule stay as they are, and a company whose colleagues
edit every deck sets `output.editable` in its look so the PowerPoint file is always written. The open default is one ink on white with a dark cover and closing
page, one system-safe face at normal weight and no accent: the highlight is full ink against greys.

## Where the rules come from

- UK Government Analysis Function, [Data visualisation: charts](https://analysisfunction.civilservice.gov.uk/policy-store/data-visualisation-charts/)
  and [tables](https://analysisfunction.civilservice.gov.uk/policy-store/data-visualisation-tables/),
  Open Government Licence v3.0.
- Urban Institute, [Data Visualization Style Guide](https://urbaninstitute.github.io/graphics-styleguide/), Apache-2.0.
- US federal plain language guidelines, [Add useful headings](https://github.com/GSA/plainlanguage.gov/blob/main/_pages/guidelines/organize/add-useful-headings.md), public domain.
- Section508.gov, [Create accessible presentations](https://www.section508.gov/create/presentations/), public domain.
- CFPB design system, [data visualization guidelines](https://cfpb.github.io/design-system/guidelines/data-visualization-guidelines), CC0.
- W3C, [WCAG 2.2](https://www.w3.org/TR/WCAG22/): contrast 4.5:1 for text, 3:1 for large text and for chart marks; nothing told by colour alone; words for every picture.
- [open-design](https://github.com/nexu-io/open-design), the simple-deck checklist and layouts, Apache-2.0: one quote a deck with one attribution, no placeholder text, a close that asks for something.
- The business-chart conventions of [IBCS](https://www.ibcs.com/standards/) and of published
  consulting decks are followed in our own words: a message on top, a named unit and period, one
  notation, no decoration, a 2x2 on two named axes, backup pages behind the close.

## Pitfalls

- A page that fails the fill rule is half empty: add what the person's notes give in support of
  the title, or use a page type that holds less (three numbers are `figures`, not a `table`), or
  fold the page into its neighbour. Never pad a page with sentences the notes do not carry.
- Do not shrink text to make it fit; cut words or split the page. The check knows each preset's
  smallest size.
- Keep the person's words: names of products, teams and places as they wrote them, and every
  figure from their own data. Never invent a quote, a source or a number to fill a page, not as an
  estimate and not with "about": a figure the notes do not give stays off the page. Give the
  source as the notes give it.
- Edit the data and build again. A change made by hand in the file is lost at the next build.
- Do not make the PDF another way (an export from the PowerPoint file, a print from a browser):
  the builder's PDF is the one the check can read, and the one with bookmarks, a title and a
  language.
- When you copy a sample to start from, its figure page names a picture that sits beside the
  sample; a deck without a picture of its own drops that page.
