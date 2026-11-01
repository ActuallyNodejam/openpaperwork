---
name: literature-search
description: "Find and read real research papers and back claims with them: sources, studies, evidence, a literature review, checking or completing a reference."
version: 0.1.0
license: Apache-2.0
platforms: [linux, macos, windows]
metadata:
  domain: academic
  version: "0.1.0"
---

# Literature search

Adapted from the `orx-lit-review` skill in alphaXiv OpenResearch (MIT). The
retrieval loop and the citation rules are theirs; the tool, the sources and
the plain-words output are ours. The claim check, its spans and the
reference graph are ported from scholar-mcp by Gonzalo Gorbalan (MIT). Use
`academic-references` for the reference style and `paper` to write the paper.

The person asked a question in plain words. They never see a command, an
identifier or JSON. Do the search yourself and answer with what the papers
say and a short list of sources they can click.

## Rules

1. Never cite from memory. A paper is cited only if it came back from a
   search or lookup in this session, and its details are copied from that
   record. A fabricated citation is worse than no citation.
2. Read before you rely. A title and abstract are enough to list a paper.
   To state what a paper found, read its abstract at least, and its full
   text when the claim is specific and an open copy exists.
3. Never invent an identifier, a DOI, a page number or a quotation.
4. Do the retrieval yourself. Do not hand it to a sub-agent.
5. If a source is down, say which one and carry on with the others.

## The tool

`papers.py` sits beside this file. It needs no login and no key.

```sh
python3 <skill folder>/papers.py search openalex "<query>"
python3 <skill folder>/papers.py search pubmed "<biomedical query>"
python3 <skill folder>/papers.py search arxiv "<query>"
python3 <skill folder>/papers.py paper <DOI | W id | PMID | arXiv id | link>
python3 <skill folder>/papers.py cite apa|ieee|bibtex <id> [<id> ...]
python3 <skill folder>/papers.py verify <DOI> [<DOI> ...]
python3 <skill folder>/papers.py check <id> "<claim>" ["<exact quote>"]
python3 <skill folder>/papers.py refs <id>
python3 <skill folder>/papers.py cited-by <id> [--limit N]
```

- `openalex` covers journals and conferences in every field, with citation
  counts. Start here unless the topic is clearly one of the next two.
- `pubmed` covers medicine, health and life science. It accepts PubMed field
  tags such as `[ti]` and `[mh]`.
- `arxiv` covers preprints in computing, maths, physics and statistics.
- Every search returns the same fields: source, id, title, abstract, date,
  authors, venue, doi, citations, url.
- `cite` builds the reference from the index record, so names, year, volume
  and pages are never typed by hand. Check the title's capitals afterwards.
- `cite` takes the year from Crossref's print issue when Crossref holds the
  DOI, since an index's year is often the earlier online-first year.
- `verify` confirms a DOI exists and returns its registered title and year.
- `check` returns the sentences a finding can be judged against, each with
  its field (`abstract` or `full_text`) and exact `start_char` and
  `end_char`. Full text comes from arXiv's HTML page or Europe PMC when the
  paper has one; otherwise only the abstract is searched and
  `full_text_note` says so. With a quote, `quote_found` says whether it is
  in the text word for word (spaces and curly quotes evened out) and where.
  It never decides the status; you do, with the `judge` questions it returns.
- `refs` lists the works a paper cites; `cited-by` lists the works that cite
  it, most cited first (25 unless `--limit` says otherwise). Both go
  through OpenAlex. An arXiv id is matched by its exact title
  (`matched_by: title`); an empty reference list means OpenAlex has none,
  not that the paper cites nothing.

Date and ranking controls, the same on every source:

```sh
... search openalex "<query>" --after 2020-01-01 --prioritize recency
... search openalex "<query>" --before 2012-01-01 --prioritize historical
... search pubmed "<query>" --limit 20
```

`--after` and `--before` are inclusive dates. Do not invent a cut-off just to
favour newer work. `--prioritize` is `default`, `recency` (the person asked
for new or latest), `historical` (seminal or foundational) or `popular`
(most cited; only when they ask about influence).

## The search loop

### Set up

1. Build one short query in the person's own words. Do not pad it with
   general terms and never guess what an acronym stands for.
2. Rate how hard the search is from 1 to 10. That sets the number of
   follow-up rounds: 1 to 3 gets none, 4 to 7 gets one, 8 to 10 gets two.
3. Fix one date window and one priority for the whole request. Every later
   call keeps them.

### Run and rank

1. Pick the sources that fit. Query two at once when the topic sits between
   fields. PubMed and arXiv are for their own fields, not a ritual.
2. Keep every result set that came back, even if another call failed.
3. Remove duplicates: same id, then same DOI, then same title. PubMed and
   OpenAlex overlap heavily; prefer the record with the DOI and the abstract.
4. If the first results cover the question, stop and rank 5 to 15 papers by
   how well they fit the question. Fewer strong papers beat a padded list.
5. Otherwise spend at most the follow-up rounds you set. One round goes
   after one named gap: a method, a population, a venue, a missing angle.
   Never spend a round rephrasing a search you already ran.
6. Keep only papers that came back from a call in this session.

To widen a search from a paper that fits well, follow its `refs` for the
work it builds on and `cited-by` for the work that followed. Each list
counts as a search call: rank and de-duplicate it with the rest.

For "find papers" or "what should I read", return the ranked list and stop.
When the person needs a comparison, a synthesis or a section of writing,
finish the search first, then read the 3 to 5 papers that carry the argument
with `paper <id>`, and open the `open_access_url` when the abstract is not
enough.

## Writing the answer

- Lead with what the papers say, in plain words, then the sources.
- State each finding with its limits: sample, design, self-reported or
  measured, correlational or experimental.
- Each finding you state rests on a span from `check`, judged in this order:
  1. Does the span support the finding directly, without stretching it?
     Fully is `supported`; in part is `partial`, and say which part holds.
  2. Only if not: does the span contradict it? Yes is `contradicted`;
     otherwise `unsupported`.
  Drop every unsupported and contradicted finding, or say plainly that the
  paper does not back it. The person never sees the status words.
- Say plainly when the evidence is thin, mixed or missing.
- Quote only text you read, exactly, and cite straight after the quote.
- List sources as full references in the style in use, each with its link:
  `https://doi.org/<doi>` when there is a DOI, otherwise the record's `url`.
- Tell the person which papers you only saw as abstracts.

## Before handing back

Run `verify` on every DOI in the reference list. Remove or fix any that is
not found, and never keep a reference you could not confirm.

Run `check` on every quotation alongside `verify`. A quote with
`quote_found: false` is fixed from a returned span or taken out.
