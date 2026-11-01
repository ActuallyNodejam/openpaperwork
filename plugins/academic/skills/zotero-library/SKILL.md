---
name: zotero-library
description: "Read the person's own Zotero library on this computer: collections, references, notes and attached PDFs."
version: 0.1.0
license: Apache-2.0
platforms: [linux, macos, windows]
metadata:
  domain: academic
  version: "0.1.0"
---

# Zotero library

Use when the person mentions Zotero, "my library", "my references", "my
collection" or a collection by name, or asks to cite, list or summarise
papers they have already saved.

Zotero keeps the whole library in a folder on the person's computer. Read it
from there. There is nothing to connect, no key and no sign-in, and you never
ask the person to set anything up or export anything.

## Rules

1. Read only. Never change, move or delete anything in the Zotero folder.
   To add a paper to Zotero, tell the person which papers to add; they do
   that in Zotero.
2. The library is the source of truth for the person's references. Take
   authors, year, title, journal, volume, pages and DOI from the record,
   never from memory, and leave out what the record does not have.
3. If the record looks wrong or incomplete (no year, a title in capitals, a
   missing DOI), say so and offer to check it with `literature-search`
   rather than silently fixing it.
4. Speak in plain words. The person never sees a key, a path or JSON; name a
   paper by its authors, year and title.

## The tool

`zotero.py` sits beside this file.

```sh
python3 <skill folder>/zotero.py where
python3 <skill folder>/zotero.py collections
python3 <skill folder>/zotero.py items --collection "<name>"
python3 <skill folder>/zotero.py items --tag "<tag>"
python3 <skill folder>/zotero.py search "<words>" [--collection "<name>"]
python3 <skill folder>/zotero.py item <key> [<key> ...]
```

- `collections` lists every collection with its path and how many works it
  holds. A collection includes its sub-collections.
- `items` and `search` return title, authors, year, venue, volume, issue,
  pages, doi, type, tags, collections and the attached files.
- `item` adds the abstract, the person's own notes and every stored field.
- Attached PDFs are ordinary files at the `files` paths; read them with the
  `pdf` skill when the person asks what a paper says.
- A collection name can be given loosely; if nothing matches, the tool
  lists the collections so you can ask which one they meant.

## What it cannot do

- It reads the library on this computer only. A library that lives only on
  zotero.org or on another computer is not here.
- A group library is included only if Zotero has synced it to this computer.
- If `where` reports no library, say that Zotero does not seem to be
  installed on this computer and ask the person for a reference list or
  file instead.

## Using the references

Format reference lists and citations with `academic-references`, and write
papers with `paper`. Before handing back, check that every work the person
asked for is in the list exactly once and that nothing was added from
outside their library unless they asked for it.
