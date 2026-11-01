---
name: paper
description: "Research paper, article, or conference or journal submission as a finished PDF in IEEE, ACM or the person's template; every reference looked up, never from memory."
version: 0.1.0
license: Apache-2.0
platforms: [linux, macos, windows]
metadata:
  domain: academic
  version: "0.1.0"
workflows:
  - id: "paper"
    arguments: "paper"
    icon: "file-text"
    menu: "Artikel"
    menu_en: "Paper"
    gives: "En forskningsartikel som PDF i IEEE, ACM eller er mall, varje referens kontrollerad"
    gives_en: "A research paper as PDF in IEEE, ACM or your template, every reference looked up"
    takes: "Släpp utkastet och anteckningarna"
    takes_en: "Drop your draft and notes"
---

# Paper

Adapted from the `orx-paper` skill in alphaXiv OpenResearch (MIT): write a
real source file, start from the template, and never hand back a paper that
does not build. Use `literature-search` to find and check sources and
`academic-references` for the reference style.

The person asked for a paper. They get a PDF they can open and submit. They
never see LaTeX, a command, a log or a setup step, and you never ask them to
install anything. In your reply, speak about the paper: its layout, its
length, what is in it and what still needs their input.

## How to make one

1. Read the person's draft and notes, and the layout they name (Layouts, below).
2. Write `paper.json` in their folder: title, authors, abstract, keywords, sections and
   references, each reference with its record (key, authors, title, venue, year, doi or
   arxiv) and cited in the text as `\cite{key}`. The shape is at the top of
   `scripts/build_paper.py`.
3. Build it there:

       python3 <skill folder>/scripts/build_paper.py paper.json paper.tex --template ieee-conference --pdf

   `--template acm-sigconf` for ACM. It writes `paper.tex` and `paper.pdf` and finds the TeX
   engine itself, fetching it once when the computer has none. Never look for LaTeX yourself
   and never print the paper another way (reportlab, a Word export, HTML): a PDF without the
   builder's `paper.tex` beside it fails the check. To change the paper, change the JSON and
   build again.
4. With the person's own template, keep their `.tex` and build it with
   `python3 <skill folder>/build_paper.py paper.tex` (Build, below).
5. Run the pack check (The check is the finish line, below) and fix what it names.

## Rules

1. Write a real file, never an outline in chat. Deliver two files together
   in the folder the person asked for: `paper.pdf` and the `paper.tex` it was
   built from. A PDF handed over without its source cannot be revised or
   checked, so never copy only the PDF.
2. Template first. If the person supplied a template or class file, use it
   and keep its document class line, its package list and its section
   skeleton. Otherwise write the paper as a JSON of sections and build it
   with the builder ("Build it with the builder" below): it puts the
   starter's preamble in, and the check fails a paper it did not build.
   Never hand-fill the starter's .tex. Never restyle a
   publisher's layout by hand: margins, fonts and columns come from the class.
3. Never hand back a paper that does not build. Build, read the error, fix
   the source, build again.
4. Every reference is real. Take references from the person's material or
   from `literature-search`, never from memory. A reference you cannot
   confirm is left out and mentioned in your reply.
5. Every number comes from the person's material or a cited paper. A result
   that is not measured yet is written as not yet measured, never as a
   placeholder that reads as real.
6. Keep the person's caveats and limits.
7. The method says what the person's material says, and no more. A setting,
   a count, a procedure or a claim about the runs that the material does not
   state (how a check reached the model, a temperature, that runs were
   deterministic) is asked about, never filled in.
8. Copy each paper's DOI, arXiv id or URL from its record into its entry. The
   check looks each one up and fails an entry with no identifier or an author
   its record does not list.
9. A sentence about the field or about others' work ("recent work shows", "models like X often")
   cites its source in that sentence or the next. Without a source in the list, write only what the
   person's material says; the check fails an uncited claim.

## Layouts

| Asked for | Starter | Notes |
| --- | --- | --- |
| IEEE conference | `templates/ieee-conference/paper.tex` | Two columns, numbered references in order of first citation, Index Terms after the abstract |
| ACM conference | `templates/acm-sigconf/paper.tex` | Two columns, CCS Concepts and Keywords after the abstract, numbered references; acmart 2.20 ships beside it and the builder puts it next to the .tex |
| The person's own template | their file | One template supplied: use it without asking. Several: ask which. |
| No layout named | ask once, in plain words, which journal or conference it is for; if they do not know, use the IEEE conference starter |

## Blind review

When the paper is for review, or the person says blind, anonymous or
double-blind:

- IEEE: keep the starter's author block, "Anonymous Author(s)".
- ACM: keep `[sigconf,anonymous,review]`.
- No names, organisations, emails, grant numbers or acknowledgments
  anywhere, including the PDF's document properties.
- Refer to your own earlier work in the third person ("Lee et al. showed"),
  never "our earlier work".
- Tell the person the names were left out and how to get the named version.

## Build

```sh
python3 <skill folder>/build_paper.py paper.tex
```

The first paper on a computer needs the internet once and takes about a
minute while the layout files are fetched; later papers take seconds. Say so
in one plain sentence before the first build, for example "Putting the paper
into the conference layout, the first time takes about a minute."

It prints `ok`, the PDF path and the page count, or the first error with its
line and a hint. Fix that line and build again. Common causes:

| Message | Cause |
| --- | --- |
| Undefined control sequence | a command whose package is not loaded |
| Missing $ inserted | `_`, `^` or `%` in text; write `\_`, `\^{}`, `\%` |
| File not found | a figure or file that is not beside the paper |
| Citation undefined | a `\cite{key}` with no `\bibitem{key}` |

In text, escape `& % $ # _ { }` with a backslash. Use `--` for a number
range and ``` ``quotes'' ```.

If the build reports `no_engine`, say plainly that this computer cannot make
the PDF yet and offer the same paper as a Word file in the layout's page
setup. Do not pretend the paper is finished.

## Writing it

- Abstract first, one paragraph, no citations. Then Index Terms (IEEE) or
  CCS Concepts and Keywords (ACM). Then numbered sections, ending with the
  references. A submission always has its title, abstract and keywords, even
  when the person asked you to write only some sections: write a short
  abstract of what those sections say and never delete these from the
  starter.
- References go in the file's own reference block, one `\bibitem` per work,
  in order of first citation, written with `papers.py cite ieee <id>` or
  from the person's list. Cite with `\cite{key}`; several at once as
  `\cite{a,b}`.
- Journal names are italic (`\emph{}`), article titles in quotation marks
  for IEEE.
- A Conclusion that restates a finding cites it again, and never states it
  more strongly than the body did: an association stays an association and
  mixed evidence stays mixed.
- Keep each reference's title in the language and wording of its record,
  and take the year from the record, never from memory.
- Label every table and figure and refer to it by number, never "the table
  below". Reference only image files that exist.
- Respect the page limit the person or the venue gives. The build prints the
  page count; cut text, never shrink the font or margins.

## Before handing back

1. The build says `ok`, the page count is within the limit, and both
   `paper.pdf` and `paper.tex` are in the folder the person asked for.
2. Open the PDF text: no `[?]`, no `??`, no placeholder words from the
   starter (TITLE OF THE PAPER, TEXT, first keyword).
3. Every citation number has a reference and every reference is cited.
4. For blind review, search the PDF for each author name, organisation and
   email. None may appear.
5. Run `papers.py verify` on every DOI in the references.

On a revision, change what was asked everywhere it appears, rebuild, and
check the page count again.


## Build it with the builder

Build the PDF with scripts/build_paper.py against the starter in templates/, not with hand
rolled LaTeX. The starter carries the Times family for text and for math, which the paper checks
look for, and a hand built preamble is how a paper ends up in Computer Modern.

    python3 <skill folder>/scripts/build_paper.py paper.json paper.tex --template ieee-conference --pdf

It writes `paper.tex` and `paper.pdf` beside the JSON. `paper.json` holds the title, authors,
abstract, keywords, sections and references; `scripts/build_paper.py` shows its shape. Give each
reference its record from `literature-search` (key, authors, title, venue, year, doi or arxiv) and
cite it as `\cite{key}`. `--template acm-sigconf` for ACM. Never edit the .tex it writes: change
the JSON and build again.

## The engine ships with the app

The kit carries the pinned TeX engine and the package cache the templates need:

    Resources/tectonic/bin/tectonic          the engine, version pinned at build time
    Resources/tectonic/bundle            the packages, built at build time

Use those and set the cache to the shipped bundle, so a paper builds with no network:

    TECTONIC_CACHE_DIR="<resources>/tectonic/bundle" "<resources>/tectonic/tectonic" --outdir . paper.tex

Fall back to a system `tectonic` only when the bundled one is absent.

## The check is the finish line

Before you answer, run the pack check on what you produced:

    python3 <skill folder>/../_checks/packcheck.py paper <your output>

It prints one FAIL line per rule with the evidence. Fix what it names and run it again, at most
three times. The turn does not end on a fail: if it still fails after three tries, say plainly
which rules fail and what you tried, and leave the file in place. A clean run prints
"pack check clean".

## Say what passed, not more

Tell the person which checks the file passed and against which source and version. Never call the
file certified, compliant or approved, and give no legal, tax or accounting advice.
