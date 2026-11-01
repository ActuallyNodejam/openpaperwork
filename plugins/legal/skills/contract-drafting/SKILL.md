---
name: contract-drafting
description: "Agreements in Word: draft an NDA, DPA or cloud service agreement on Common Paper terms, or review the other side's and return tracked changes. Not legal advice."
version: 0.2.0
license: Apache-2.0
platforms: [linux, macos, windows]
metadata:
  domain: legal
  version: "0.2.0"
workflows:
  - id: "draft-agreement"
    arguments: "draft"
    icon: "file-text"
    menu: "Avtal"
    menu_en: "Agreement"
    gives: "Ett sekretessavtal, PUB-avtal eller molntjänstavtal i Word på Common Papers villkor"
    gives_en: "An NDA, DPA or cloud service agreement in Word on Common Paper's terms"
    takes: "Skriv en rad: ömsesidigt sekretessavtal med Exempel AB, Storgatan 12, 211 34 Malmö, under svensk lag"
    takes_en: "Write one line: a mutual NDA with Example Ltd, Storgatan 12, 211 34 Malmö, under English law"
  - id: "review-agreement"
    arguments: "review"
    icon: "file-text"
    menu: "Granska avtal"
    menu_en: "Review an agreement"
    gives: "Motpartens avtal tillbaka i Word med spårade ändringar"
    gives_en: "The other side's agreement back in Word with tracked changes"
    takes: "Släpp deras avtal och skriv vilken sida ni står på"
    takes_en: "Drop their agreement and say which side you are on"
---

# Contracts

Three jobs, each with one script and the same check:

| The person asks | Script | Result |
| --- | --- | --- |
| "Draft an NDA / a DPA / a SaaS agreement" | `scripts/agreement_create.py` | The agreement as Word: a Cover Page the parties fill in, then Common Paper's Standard Terms word for word |
| "Look at the NDA they sent us" | `scripts/review_create.py` | A review memo as Word: one verdict per checklist item, findings quoted from their text |
| "Send it back with our changes" | `scripts/redline_create.py` | Their own Word file with our edits as tracked changes they can accept or reject |

Run the check on every result and fix what it names, at most three times:
`python3 <skill folder>/../_checks/packcheck.py contract-drafting <file>`
Keep the JSON you built it from in the same folder; the check reads it.

## What this is, and is not

- The drafts use clause text written by a committee of lawyers (Common Paper), unchanged except
  where the standard file lists a change. Never write clause text of your own into the Standard
  Terms. Anything the parties agree differently goes on the Cover Page under Modifications, in
  their own words.
- The review reads the other side's paper against a checklist and quotes it. It never says the
  agreement is fine, compliant, lawful or ready to sign, and it rates no overall risk.
- Nothing here is legal advice. Say so in your reply, and suggest a lawyer reads the agreement
  before anyone signs.
- The governing law and the courts are always the parties' choice. Never fill them in, and never
  carry a default over from a template. One the person did not give stays open: list it in
  `"unknown"` (`["courts"]`), the Cover Page leaves its line empty for the parties, the check answers
  with a WARN, and the reply names it as theirs to agree before signing. A plain agreement
  (`clauses`) needs both; the script refuses it without them.

## Draft an agreement

1. Pick the standard: `common-paper-mutual-nda-1.0` (a mutual NDA), `common-paper-dpa-1.1` (a DPA
   that supplements a main agreement), `common-paper-csa-2.1` (a cloud or SaaS subscription).
   For anything else, write a plain agreement (step 5).
2. Start from `templates/nda.spec.json`, `dpa.spec.json` or `csa.spec.json`. See what a Cover
   Page needs: `python3 <skill folder>/scripts/agreement_create.py --fields common-paper-dpa-1.1`.
3. Fill the parties (name, registration number, address, who signs; for a DPA or CSA each party's
   `role`, Provider or Customer) and the `terms` from what the person gave you. A term given in a
   word takes its plain reading, said in the reply ("two years": the MNDA Term and the Term of
   Confidentiality, 2 years each). The law or the courts they did not give stay open in `"unknown"`;
   ask only for what the agreement cannot be drafted without (who the parties are). No placeholders.
4. Build: `python3 <skill folder>/scripts/agreement_create.py spec.json agreement.docx`. For the copy the
   parties sign, add `"copy": "signing"`: the Cover Page then shows no field help, only the terms.
5. A plain agreement in the parties' own words: give `clauses` instead of `standard` (see the
   script's help). Refer to another clause as `{ref:<clause id>}`; it becomes the number.

## Nothing given is left off

The three scripts stop before anything is laid out when the JSON holds a key they have no field for
or a value of another shape, and name the key (`spec.fields.json`, `review.fields.json` and
`redline.fields.json` beside this file list every key). `agreement_create.py` also refuses a term
the chosen standard's Cover Page does not have. What the parties agreed beyond the Cover Page goes
in `modifications`, in their own words. Never leave a fact out to make the error go away: put it
where the message says, or say in your reply what the page does not carry.

The check fails a heading with nothing under it (LEGAL-EMPTY, a house rule).

Run the check with `--in` and the working folder. It then reads the person's own files there and
asks, once and never as a fail (NOTES-FLOOR): which e-mail addresses, numbers, dates and amounts the
notes hold and the page does not, which of them the page carries changed. Answer the question once:
put each on the page as the notes have it, or say in your reply why it does not belong there. Never
change one to shorten the list.

Work in the working folder, the folder the person is working in: write the data file there, run the
script from there by its full path (`<skill folder>` is the folder this file is in) and give the
output a path there. The builder refuses an output path inside the library's own folder, where the
person never looks; hand back the path in the working folder.

Look for `company.json` in the working folder first: it holds the company's own particulars, written
once (name, address, VAT and register numbers, registered office, share capital, bank account). The
builder fills from it what the data file leaves out of the sender, stops when the two disagree, and
the check fails a page whose sender disagrees with it (COMPANY-FILE). When the folder has none and
the person gives their company's particulars, write it once: `python3 <skill folder>/../_shared/company.py
make company.json name="..." country=.. street="..." postcode=.. city=.. vat_id=..
register_number=..`; it says which particulars that country's company law still wants. One the files
do not give is declared with `unknown=<key>`, never made up.

## Review their agreement

1. Ask whose side the review is for if it is not clear (the method requires it): for an NDA the
   Disclosing Party, the Receiving Party or both; for a DPA the Provider or the Customer.
2. Read the whole document. Open `checklists/nda.json` or `checklists/dpa.json` and go through
   every item: its `general` text and the text for the person's side.
3. Write `review.json` (start from `templates/review.example.json`). Every checklist item gets
   exactly one verdict:
   - **Finding**: something to raise. Quote their words exactly (`quote`, or `quotes`; use `...`
     to skip text), say whether it is a `legal` issue or a `commercial` preference, what it means
     for the person, and a `proposed_change`. For a clause that is missing, quote the clause it
     belongs in.
   - **Acceptable**: nothing to raise; a short note.
   - **Not applicable**: the agreement has no such term; say so in the note.
   - **Missing information**: something the review needs is not there (a schedule, a linked
     policy, the main agreement); the note says what to ask for.
4. Build: `python3 <skill folder>/scripts/review_create.py review.json review.docx`. It refuses a quote it
   cannot find in their file.
5. In your reply, give the findings in a few lines and the items marked Missing information. Do not sum
   up the agreement as good or bad.

## Return their file with tracked changes

1. Only when the person wants the changes sent. Agree the edits with them first; findings make a
   good start.
2. Write `redline.json` (start from `templates/redline.example.json`): `source` (their .docx),
   `author` (the person's company), and `edits`:
   - `{"find": "...", "replace": "..."}` replaces words (an empty replace deletes them);
   - `{"after": "...", "insert": "..."}` adds words right after the anchor;
   - `{"after_paragraph": "...", "paragraph": "..."}` adds a new paragraph after the one holding
     the anchor;
   - `"comment"` on any edit adds a Word comment the other side will read: no internal strategy.
   Each find or anchor must appear exactly once, within one paragraph; copy it exactly.
3. Build: `python3 <skill folder>/scripts/redline_create.py redline.json`. Their original is never changed; the
   redline is a new file with everything else byte for byte as they sent it. A PDF cannot carry
   tracked changes: ask for their Word file.

## What the check reads

| Rule | Reads | Source |
| --- | --- | --- |
| LEGAL-PARTIES, -DATE, -TERMS, -XREF, -SIGN | parties with their numbers and addresses, the date, defined terms, the agreement's own cross-references, a signature block for each party | drafting practice; the library's own rules |
| LEGAL-LAW | a governing law with no placeholder, Cover Page law and courts filled in | drafting practice; the parties' choice |
| LEGAL-NDA | direction, the definition, the obligations, the four carve-outs, permitted disclosures, term, return or destruction, remedies, law and courts | Open Legal Products, mike-workflows (MIT) |
| LEGAL-DPA | subject matter, duration, nature and purpose, data types, data subjects and the processor's duties (a) to (h), including confidentiality for the people who process | GDPR Article 28(3) |
| LEGAL-VERDICT | every checklist item has one verdict; findings marked legal or commercial; the report shows them all | mike-workflows dpa-review coverage ledger (MIT) |
| LEGAL-QUOTE | every finding's quote is found word for word in their document and in the report | mike-workflows: quote and anchor findings to the supplied paper |
| LEGAL-WORDING | no verdict on the whole agreement (compliant, lawful, approved, safe or ready to sign) | the library's own rule |
| LEGAL-REDLINE | real tracked changes with author and date; every edit shown | the library's own rule |
| LEGAL-ORIGINAL | rejecting every change gives their text back exactly; their other parts untouched | the library's own rule |

## Sources

- Common Paper Mutual NDA 1.0, DPA 1.1 and Cloud Service Agreement 2.1 Standard Terms, by Common
  Paper, Inc., CC BY 4.0 (https://creativecommons.org/licenses/by/4.0/), in `standards/`. Each file
  records its repository, commit and every change; each agreement prints that notice at its end.
- Open Legal Products, mike-workflows, nda-review and dpa-review (MIT, Copyright (c) 2026 Mike), in
  `checklists/`.
