---
name: requirements-spec
description: "Requirements specification (kravspecifikation) as Word, English or Swedish: numbered shall statements with rationale and verification, TBDs and SI units, checked."
version: 0.1.0
license: Apache-2.0
platforms: [linux, macos, windows]
metadata:
  domain: engineering
  version: "0.1.0"
workflows:
  - id: "requirements"
    arguments: "requirements"
    icon: "bullet-list"
    menu: "Kravspecifikation"
    menu_en: "Requirements"
    gives: "En kravspecifikation i Word med numrerade skall-krav och verifiering"
    gives_en: "A requirements specification in Word with numbered shall statements and verification"
    takes: "Släpp anteckningarna eller skriv vad som ska byggas"
    takes_en: "Drop your notes or say what is to be built"
---

# Requirements specification

Use this when someone asks for a requirements specification, a product or system spec, a
technical specification to send for quotes, or a kravspecifikation, from notes, a brief or an
email. One script writes the document, so your attention goes to the requirements themselves.

## How to make it

1. Read the notes and the brief. Ask nothing they already say; a value nobody has decided is a TBD,
   not a question. The author, the approver and the history's author are people the notes name;
   when they name none, leave them empty. Never the account's email, the agent's name or a guess:
   who owns the system later did not approve the spec.
2. Write a small spec file (JSON). Start from `templates/requirements.spec.json` in English or
   `templates/kravspecifikation.spec.json` in Swedish. The spec's `date` and the first history row's
   date are the day you write it, today, as YYYY-MM-DD; never a bracket such as `[date]`.
3. Build the document:

```bash
python3 <skill folder>/scripts/requirements_create.py spec.json requirements.docx
```

4. Run the pack check and fix what it names:
   `python3 <skill folder>/../_checks/packcheck.py requirements-spec <your output>`

## Nothing given is left off

`requirements_create.py` stops before anything is laid out when the spec holds a key it has no field
for or a value of another shape, and names the key (`spec.fields.json` beside this file lists every
key). Context and assumptions that are no requirement go in `facts`, one statement each. Never leave
a fact out to make the error go away: put it where the message says, or say in your reply what the
page does not carry.

Run the check with `--in` and the working folder. It then reads the person's own files there and
asks, once and never as a fail (NOTES-FLOOR): which e-mail addresses, numbers, dates and amounts the
notes hold and the page does not, which of them the page carries changed. Answer the question once:
put each on the page as the notes have it, or say in your reply why it does not belong there. Never
change one to shorten the list.

Work in the working folder, the folder the person is working in: write the data file there, run the
script from there by its full path (`<skill folder>` is the folder this file is in) and give the
output a path there. The builder refuses an output path inside the library's own folder, where the
person never looks; hand back the path in the working folder.

## How a requirement is written

From NASA's Systems Engineering Handbook (NASA/SP-2016-6105 Rev 2), Appendix C, "How to Write a Good
Requirement", a US Government work in the public domain:

- "shall" marks a requirement, "will" a fact or an assumption, "should" a goal. Facts go under
  context and assumptions, goals in their own list, requirements in the requirement tables.
- One requirement per statement, in the form "The <product> shall <do or be> <value with tolerance>".
  Say what is needed, not how to build it, and not who does what (that belongs in the order or the
  statement of work).
- Every requirement has an id of its own: letters, a hyphen and a number, such as `PS-001`. Never
  reuse or renumber an id; a dropped requirement keeps its id retired.
- Every requirement has a rationale and names how it is verified: test, analysis, inspection or
  demonstration.
- State it positively: "The guard shall stay locked while the belt runs", not "shall not open".
- No ambiguous or unverifiable words: as appropriate, etc., and/or, but not limited to, adequate,
  sufficient, user-friendly, easy, fast, quickly, safe, robust, flexible, small, large, portable,
  light-weight, minimize, maximize, when required, if required. Give a number with its tolerance or a
  condition someone can check.
- A value not yet decided is TBD; a best estimate still to be confirmed is TBR, which is better.
  Mark it in the statement (`(TBR-1)`) and list it in `tbd` with what closes it, who resolves it
  and by when, both from the notes. A date the notes do not give stays empty and the document says
  it is to be agreed; never a date of your own, and never the go-live date as a TBD's.

The verbal forms follow the ISO/IEC Directives, Part 2 (2021), clause 7: shall for a requirement,
should for a recommendation, may for a permission, can for a possibility, and never "must" in place
of shall. In Swedish: ska, bör, får, kan; "kommer att" for a fact.

## Values and units

From the SI Brochure, 9th edition (BIPM, CC BY 4.0), section 5, and NIST SP 811 (2008), public domain:

- A space between the number and the unit symbol: `5 kg`, `20 °C`, `5 %`, `230 V`; no space before
  the degree of an angle (`30°`). The script makes that space a no-break space.
- The unit's own symbol, unchanged in the plural and with no full stop: kg, kN, MPa, s, min, h, L;
  never Kg, kgs, sec, hr, hrs, mins, cc or amps.
- At most one solidus (`m/s²`, not `m/s/s`), and never a symbol mixed with a unit name (`km/h` or
  "kilometres per hour", not "km per hour").

Write ids, values and units in the spec exactly as they should read; the script does not correct them.

## What the check reads

A requirement is a row of a table whose heading row names the statement column (Requirement, Goal,
Krav, Mål), with the id in the first cell, or a paragraph that begins with its id. Quote a word when
you only mention it (“shall”), or the check reads it as a requirement with no id.

## Sources

- NASA Systems Engineering Handbook, NASA/SP-2016-6105 Rev 2, Appendix C:
  https://www.nasa.gov/seh/appendix-c-how-to-write-a-good-requirement
- ISO/IEC Directives, Part 2 (2021), clause 7, verbal forms: https://www.iso.org/directives-and-policies.html
- The SI Brochure, 9th edition (BIPM, CC BY 4.0): https://www.bipm.org/en/publications/si-brochure
- NIST Special Publication 811 (2008 edition): https://www.nist.gov/pml/special-publication-811

## Say what passed, not more

Tell the person which checks the document passed and against which source. This is a drafting check:
never call the document or the product compliant, certified or approved; it is approved when the
people named sign it off.
