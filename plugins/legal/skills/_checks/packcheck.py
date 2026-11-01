#!/usr/bin/env python3
"""The pack check a core skill runs on its own output before it answers.

    python3 skills/_checks/packcheck.py <skill> <output-file> [--stage first|revision]

Skills and the rules they own:

    e-invoice        the EU invoice pack: page completeness, trace, totals, VAT, locale floor; a credit
                     note's type, the invoice it amends, its signs and VAT groups; XRechnung's German rules;
                     the Factur-X / ZUGFeRD PDF (XML inside, PDF/A-3) and, where installed, veraPDF and
                     the KoSIT validator; a French seller's mentions (CGI annexe II 242 nonies A, Code de
                     commerce L441-9) and the FNFE-MPE BR-FR rules; Peppol BIS Billing 3.0 UBL and Finvoice
                     3.0 through the official rules where installed; the Norwegian, Danish, Finnish, UK,
                     Australian, Canadian and US invoice contents (NO-, DK-, FI-, UK-, AU-, CA-, US-); the
                     Belgian, Dutch, Austrian and Irish ones (BE-, NL-, AT-, IE-), SI-UBL 2.0 and
                     ebInterface 6.1 through their official artefacts where installed; the Spanish, Italian
                     and Polish ones (ES-, IT-, PL-), Facturae 3.2.2, FatturaPA 1.2.3 and the KSeF structure
                     FA(3) through their official schemas where installed; the particulars a company's
                     own law puts on its invoice (EINV-PARTICULARS: register and number, seat, legal
                     form, share capital, liquidation, by the statute of each of the 17 countries),
                     which fail when missing, warn when the order declares one unknown, and fail when
                     the person's own files give one the page dropped
    paper            the LaTeX paper: the Times family, no introduction heading, citations covered
    docx             the APA report: same academic rules plus reference placement
    academic-references  a reference list in APA 7 or Vancouver (ICMJE, NLM Citing Medicine): the APA
                     rules on an author-date list, the VANC- rules on a numbered one; each set
                     stands aside on the other's list
    trade-documents  quotations, order confirmations, delivery notes, pro formas and purchase orders on
                     the business letter; a purchase order's head, lines, total, delivery and Incoterms;
                     every label in the document's language, the information block inside the text's
                     right edge with one line per label, and the paper its locale writes on; the address
                     in the envelope window of the country the document is sent from, as its letter and
                     its invoice have it
    requirements-spec  a requirements specification on NASA SE Handbook Appendix C, ISO/IEC Directives Part 2
                     clause 7 and the SI Brochure: ids, shall/will/should, vague words, TBD/TBR owners,
                     verification, units
    html-deck        the house deck: pages, type floor, accent, trace. A deck.json is built first.
    business-deck    a business deck as an editable PowerPoint file, on the UK Government Analysis Function's
                     chart and table guidance, the Urban Institute style guide, the US plain language and
                     Section 508 material, CFPB and WCAG 2.2: a message as every title, one exhibit a page,
                     the storyline, next steps, sources, no placeholder, honest and labelled charts, one
                     highlight, tables as tall as their rows, a 2x2 matrix, a figure, a quote, an appendix of
                     backup pages, text fit, fill, words, type, contrast, grid and
                     the file's accessibility basics, every density bound read from the deck's preset
    business-letter  the letter on DIN 5008 Form B, or on the page and envelope window of a Norwegian,
                     Danish, Finnish, US, UK, Canadian, Australian, Belgian, Dutch, Austrian, Irish,
                     Spanish, Italian or Polish
                     sender: page, window, address, parts, salutation and closing, date, one language,
                     a Finnish letter's page numbers, company details
    contract-drafting  an agreement's structure, never its merits: parties, date, terms, cross-references,
                     governing law, signatures, an NDA's elements, GDPR Art. 28(3) for a DPA; a review of
                     the other side's paper: one verdict per checklist item, quotes found in the document,
                     no verdict on the whole; a redline: real tracked changes, the original untouched
    meeting-minutes  minutes on Robert's Rules (1915) section 60 and a company's board or general meeting
                     on its statute (Sweden, Norway, Denmark, Finland, UK, US, Canada, Australia, Belgium,
                     the Netherlands, Austria, Ireland, Spain, Italy, Poland): head, officers, motions,
                     times, signatures, what
                     the statute asks, one language
    xlsx             any workbook, on the UK government spreadsheet rules and the FAST Standard: no
                     merged or hidden cells, headings, numbers as numbers, no outside links, no
                     volatile functions, no assumption typed into a formula
    employment-statement  the written statement of employment terms on Directive (EU) 2019/1152,
                     ERA 1996 ss.1-3, LAS 6 c §, arbeidsmiljøloven § 14-6, the Danish lov 501/2023 § 3,
                     työsopimuslaki 2:4 §, the Canada Labour Code 253.2, Ontario O. Reg. 285/01 s. 1.2 and
                     the Fair Work Act 2009, and a US offer letter (FLSA, NY 195(1), Cal. 2810.5); the
                     Belgian law of 7 October 2022, BW 7:655, the Austrian Dienstzettel (AVRAG § 2) and the
                     Irish Terms of Employment (Information) Act 1994; Spain's Real Decreto 723/2026, Italy's
                     D.Lgs. 152/1997 art. 1 and Poland's Kodeks pracy art. 29: particulars, dates, probation,
                     pay, work abroad, language, signature, the collective agreement, paper
    annual-accounts  a smaller Swedish company's annual report on årsredovisningslagen (1995:1554) and
                     Directive 2013/34/EU, K2 cited: parts, pages, unit, comparatives, sums, balance, the
                     year's result, equity, disposition, notes, signatures
    every-file       the floor any Word, Excel or PowerPoint file meets, whatever made it: fonts,
                     overflow, contrast, formula results, titles and alternative text, covered text
    diagram          a diagram on diagram-design (github.com/cathrynlavery/diagram-design, MIT): its accessible SVG
                     contract and single-file safety and its connector and label geometry, through its own
                     scripts ported unchanged; no web address; nothing past the edge, every text inside its box,
                     nothing on top of anything else, contrast, the complexity budget of its type, arrow labels of
                     14 characters, and the PDF, SVG and PNG made from the page they stand beside

The end state, before any rule (skills/_checks/end_state.py, standard library only): the check judges the file on
disk, never what the chat said about it. OUTPUT-MISSING (nothing was written), OUTPUT-EMPTY (no bytes, no text, no
cell, no slide, no page), OUTPUT-UNOPENABLE (not the kind its name says), OUTPUT-PLACEHOLDER (lorem ipsum, "your text
here", a heading and nothing else) and OUTPUT-STALE (last changed before the request began: NODEJAM_TURN_STARTED in
milliseconds, or --since; the app's pack check sets it) each fail the file with exit 1, and no pack rule runs on it.
After the pack's rules, OUTPUT-OPEN-GAP fails a file that still holds a gap left for the person ("[TO CONFIRM: ...]",
"[TBD]", "[?]"): well made, not finished. Tests: skills/_checks/tests/test_end_state.py (the four cases for every pack
and kind, and the gaps).

House rules every pack shares (defect checks, none taken from a standard; skills/_checks/thin_pages.py): a page
that is well formed and thin does not pass. MINUTES-EMPTY: every item of business has something recorded under
it. LETTER-EMPTY and TRADE-EMPTY: a body, lines that say what they are, and an address a postman can deliver to
(addressee, street, town, postcode), the sender's own included on a trade document. EMPLOY-EMPTY and LEGAL-EMPTY:
no heading stands alone.

Money (skills/_checks/money_check.py): TRADE-SUMS reads a quotation, an order confirmation and a pro forma invoice
as TRADE-PO-LINES and TRADE-PO-TOTAL read a purchase order, with the same calculator: each line amount is quantity
times price less the discount, the totals add up, VAT once per rate. EINV-SUMS reads an invoice page as printed:
lines, total without tax, tax and amount due add up (EN 16931-1 BR-CO-10, -13, -14, -15 and -17, cited by id).
TRADE-RATE and EINV-RATE: a VAT rate is one the seller's country has (tax_rates.json, each country with its source
and the day it was read) or the buyer's for a sale taxed there; a rate written as a fraction (0.2 for 20 percent)
fails; Canada and the United States have no national list and are not checked.

The notes floor (skills/_checks/notes_floor.py), a question and never a fail: NOTES-FLOOR reads the person's own
files in the folder named with --in (else the folder the file is in; never the page, never a builder's data file)
and lists the hard tokens the notes hold and the page does not (e-mail addresses, IBANs, phone, tax and register
numbers, document numbers, dates, amounts), names a token the page carries a few characters off as changed, and,
for a letter and minutes, lists a figure the data file's text carries that is nowhere in the notes and does not
follow from figures that stand together there. It prints one WARN line, which the Stop hook and the app's pack
check send back once; it does not run when the folder holds no notes.

The company file (skills/_shared/company.py, skills/_checks/company_check.py): when the person's folder holds a
company.json, the company's own particulars written once, COMPANY-FILE fails a page of that company whose data
file says something else than the file does, or that does not carry the company's name and numbers as the file
gives them. It does not apply without the file or to another company's page.

A rule about fit, width, a window, fill or the number of pages (LAYOUT_RULES below) ends its FAIL line with what
may change (the type size inside its floor, the wrapping, where a line stands, an abbreviation the post office
allows) and the sentence "Never change a name, an address or a number to make it fit."

Exit code 0 means every rule that ran passed, and at least one ran; a WARN line on a clean run names
what the reply must say (a particular the order declares unknown). Exit code 1 prints one FAIL line per
rule with the evidence the model needs to fix it, and is what the skill loops on: fix, run again, at
most three times, then say plainly which rules still fail. Exit code 3 with a last line that begins
"pack check not checked:" means no rule could run (a dependency the machine lacks, a file that could
not be read): nothing was checked, which is neither a pass nor a fault in the file, and the reply says so.
A last line that begins "pack check not applicable:" (exit code 0) means none of the pack's rules
applies to this file (the Word skill's reference rules on a letter): the pack has nothing to say about
it, and nobody is told anything.
"""
import argparse
import json
import os
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import end_state  # noqa: E402  (a plain import: the plugin build finds a check's modules by its import lines)

SKILL_RULES = {
    "e-invoice": ["EINV-PAGE-COMPLETE", "EINV-PAGE-NO-EXTRA", "EINV-PAGE-TRACE", "EINV-VAT-LABEL",
                  "EINV-LOCALE-ORDER", "EINV-PAGE-KIND", "EINV-PAGE-DIN5008", "EINV-PAGE-MENTIONS", "LETTER-COMPANY",
                  "EINV-PARTICULARS",
                  "LOCALE-PAPER",
                  "LOCALE-DATE", "LOCALE-NUMBER", "LOCALE-CURRENCY",
                  "INV-CREDIT-TYPE", "INV-CREDIT-REF", "INV-CREDIT-SIGN", "INV-CREDIT-VAT", "INV-XRECHNUNG",
                  "EINV-FACTURX", "EINV-PDFA", "EINV-KOSIT", "EINV-FR-CTC",
                  "FR-SELLER", "FR-BUYER", "FR-PAYMENT", "FR-MENTIONS",
                  "EINV-PEPPOL", "EINV-FINVOICE", "NO-SELLER", "NO-CONTENT", "DK-INVOICE", "FI-INVOICE",
                  "FI-PAYMENT", "UK-VAT-INVOICE", "AU-TAX-INVOICE", "CA-GST-HST", "US-SALES-TAX",
                  "EINV-SI-UBL", "EINV-EBINTERFACE", "BE-INVOICE", "NL-INVOICE", "AT-INVOICE", "IE-VAT-INVOICE",
                  "EINV-FACTURAE", "EINV-FATTURAPA", "EINV-KSEF", "ES-INVOICE", "IT-INVOICE", "PL-INVOICE",
                  "EINV-SUMS", "EINV-RATE", "NOTES-FLOOR", "COMPANY-FILE"],
    "paper": ["PAPER-FONTS", "PAPER-CITE-COVER", "PAPER-REF-RECORD", "PAPER-CLAIM-CITE"],
    "docx": ["APA-NO-INTRO", "APA-REFS-NEW-PAGE", "APA-REF-CITED", "DOCX-FONT", "DOCX-TABLE", "DOCX-NUMBERS",
             "DOCX-MONTHS"],
    "academic-references": ["APA-NO-INTRO", "APA-REFS-NEW-PAGE", "APA-REF-CITED",
                            "VANC-ORDER", "VANC-MARKS", "VANC-LIST", "VANC-CITED", "VANC-ONCE",
                            "VANC-AUTHORS", "VANC-JOURNAL", "VANC-DATE", "VANC-ONLINE"],
    "trade-documents": ["LETTER-DIN5008", "LETTER-COMPANY", "LOCALE-PAPER", "LOCALE-DATE", "LOCALE-NUMBER",
                        "TRADE-PO-HEAD", "TRADE-PO-LINES", "TRADE-PO-TOTAL", "TRADE-PO-DELIVERY",
                        "TRADE-PO-INCOTERMS", "TRADE-PO-QUOTE", "TRADE-INCOTERMS", "TRADE-LANG", "TRADE-BLOCK", "TRADE-WINDOW",
                        "TRADE-EMPTY", "TRADE-SUMS", "TRADE-RATE", "NOTES-FLOOR", "COMPANY-FILE"],
    "requirements-spec": ["REQ-ID", "REQ-VERB", "REQ-ONE", "REQ-VAGUE", "REQ-NEGATIVE", "REQ-TBD", "REQ-VERIFY",
                          "UNITS-SPACE", "UNITS-SYMBOL", "NOTES-FLOOR"],
    "html-deck": ["DECK-PAGES", "DECK-TYPE", "DECK-ACCENT", "DECK-TRACE", "DECK-BOUNDS", "NOTES-FLOOR"],
    "business-deck": ["BDECK-TITLE", "BDECK-ONE-IDEA", "BDECK-STORYLINE", "BDECK-NEXT-STEPS", "BDECK-SOURCE",
                      "BDECK-PLACEHOLDER", "BDECK-CHART-HEAD", "BDECK-CHART-LABELS", "BDECK-CHART-HONEST",
                      "BDECK-CHART-EARNS", "BDECK-HIGHLIGHT", "BDECK-TABLE", "BDECK-FIT", "BDECK-FILL", "BDECK-WORDS",
                      "BDECK-TYPE", "BDECK-CONTRAST", "BDECK-GRID", "BDECK-FILE", "BDECK-MATRIX", "BDECK-FIGURE",
                      "BDECK-QUOTE", "BDECK-APPENDIX", "NOTES-FLOOR"],
    "business-letter": ["LETTER-DIN5008", "LETTER-WINDOW", "LETTER-ADDRESS", "LETTER-PARTS", "LETTER-FORM",
                        "LETTER-DATE", "LETTER-LANGUAGE", "LETTER-PAGES", "LETTER-COMPANY", "LOCALE-PAPER", "LOCALE-DATE",
                        "LETTER-EMPTY", "NOTES-FLOOR", "COMPANY-FILE"],
    "contract-drafting": ["LEGAL-PARTIES", "LEGAL-DATE", "LEGAL-TERMS", "LEGAL-XREF", "LEGAL-LAW", "LEGAL-SIGN",
                          "LEGAL-NDA", "LEGAL-DPA", "LEGAL-VERDICT", "LEGAL-QUOTE", "LEGAL-WORDING",
                          "LEGAL-REDLINE", "LEGAL-ORIGINAL", "LEGAL-EMPTY", "NOTES-FLOOR", "COMPANY-FILE"],
    "meeting-minutes": ["MINUTES-HEAD", "MINUTES-OFFICERS", "MINUTES-MOTIONS", "MINUTES-TIMES", "MINUTES-SIGNED",
                        "MINUTES-STATUTE", "MINUTES-LANGUAGE", "MINUTES-EMPTY", "NOTES-FLOOR", "COMPANY-FILE"],
    "xlsx": ["SHEET-MERGED", "SHEET-HIDDEN", "SHEET-EMPTY", "SHEET-HEADINGS", "SHEET-NUMBERS", "SHEET-LINKS",
             "SHEET-VOLATILE", "SHEET-HARDCODED"],
    "employment-statement": ["EMPLOY-ITEMS", "EMPLOY-DATES", "EMPLOY-PROBATION", "EMPLOY-PAY",
                             "EMPLOY-ABROAD", "EMPLOY-LANG", "EMPLOY-REFERENCE", "EMPLOY-NO-TEMP", "EMPLOY-NO-HOURS",
                             "EMPLOY-FI-TEMP", "EMPLOY-US-ATWILL", "EMPLOY-US-FLSA", "EMPLOY-US-STATE",
                             "EMPLOY-US-WORDING", "EMPLOY-AU-STATEMENTS", "EMPLOY-IE-CORE", "EMPLOY-SIGNED",
                             "EMPLOY-BE-LANG", "EMPLOY-AGREEMENT", "EMPLOY-PL-CONTRACT", "LOCALE-PAPER",
                             "EMPLOY-EMPTY", "NOTES-FLOOR", "COMPANY-FILE"],
    "annual-accounts": ["ANNUAL-PARTS", "ANNUAL-PAGES", "ANNUAL-AMOUNTS", "ANNUAL-YEARS", "ANNUAL-SUMS", "ANNUAL-BALANCE",
                        "ANNUAL-RESULT", "ANNUAL-EQUITY", "ANNUAL-DISPOSITION", "ANNUAL-NOTES", "ANNUAL-SIGNED",
                        "NOTES-FLOOR"],
    "every-file": ["FLOOR-FONT", "FLOOR-OVERFLOW", "FLOOR-CONTRAST", "FLOOR-FORMULA", "FLOOR-META",
                   "FLOOR-OVERLAP"],
    "diagram": ["DIAG-CONTRACT", "DIAG-OFFLINE", "DIAG-GEOMETRY", "DIAG-BOUNDS", "DIAG-FIT", "DIAG-OVERLAP",
                "DIAG-CONTRAST", "DIAG-BUDGET", "DIAG-LABEL", "DIAG-EXPORT", "DIAG-PNG"],
}

MODULES = {
    "EINV": "einvoice_page",
    "LOCALE": "locale_floor",
    "PAPER": "academic_style",
    "APA": "academic_style",
    "VANC": "academic_style",
    "REQ": "requirements_check",
    "UNITS": "requirements_check",
    "DECK": "housedeck",
    "BDECK": "business_deck",
    "EMPLOY": "employment_check",
    "ANNUAL": "annual_accounts_check",
    "LETTER": "letter_check",
    "FLOOR": "floor",
    "SHEET": "sheet_check",
    "MINUTES": "minutes_check",
    "LEGAL": "legal_check",
    "INV": "credit_note_check",
    "FR": "fr_invoice_check",
    "TRADE": "purchase_order_check",
    "DIAG": "diagram_check",
    # The house look of a Word file made from scratch (docx_house.py).
    "DOCX": "docx_house",
    # The floor under every pack: what the person's notes hold and the page does not, as a question (WARN).
    "NOTES": "notes_floor",
    # One record of the company in the person's folder (company.json), every page in step with it.
    "COMPANY": "company_check",
    # The e-invoice pack's country rules (waves 6 and 7): Norway, Denmark, Finland, the UK, Australia,
    # Canada and the United States.
    "NO": "einvoice_country", "DK": "einvoice_country", "FI": "einvoice_country", "UK": "einvoice_country",
    "AU": "einvoice_country", "CA": "einvoice_country", "US": "einvoice_country",
    # Wave 8 (Belgium, the Netherlands, Austria, Ireland) and wave 9 (Spain, Italy, Poland).
    "BE": "einvoice_country", "NL": "einvoice_country", "AT": "einvoice_country", "IE": "einvoice_country",
    "ES": "einvoice_country", "IT": "einvoice_country", "PL": "einvoice_country",
}


# A rule kept in a module of its own, whatever its prefix: the house rules that a page is not thin
# (skills/_checks/thin_pages.py), which every pack shares.
RULE_MODULES = {"MINUTES-EMPTY": "thin_pages", "LETTER-EMPTY": "thin_pages", "TRADE-EMPTY": "thin_pages",
                "EMPLOY-EMPTY": "thin_pages", "LEGAL-EMPTY": "thin_pages",
                # Money recomputed where it is printed, and a tax rate that its country has (money_check.py).
                "TRADE-SUMS": "money_check", "TRADE-RATE": "money_check",
                "EINV-SUMS": "money_check", "EINV-RATE": "money_check"}


def shared_module(name):
    """A module of rules every pack shares, imported by its own name: a plugin is built from this folder with
    exactly the files its packs import, found by reading the import lines, and a name in a table is not one. A
    module routed in RULE_MODULES needs its line here."""
    if name == "thin_pages":
        import thin_pages
        return thin_pages
    if name == "money_check":
        import money_check
        return money_check
    return __import__(name)


# A rule about fit, width, a window, fill or the number of pages never invites changing a fact. In a real run
# (2026-10-10) a rule said an e-mail address ran 1 mm past the edge, and the agent replaced the sender's address
# with a shorter one it made up. So the FAIL line of every such rule ends with what MAY change and with one
# sentence. A house rule on the checks' own words. rule -> what may change.
NEVER_TO_FIT = "Never change a name, an address or a number to make it fit."
_BLOCK = ("What may change: the builder sets the type size, never under its floor, and where a value wraps; a long "
          "value may stand on another line of the page (the footer, the text, a note), and a label may take a "
          "shorter word.")
_WINDOW = ("What may change: an address line may be shortened only as the recipient's post office itself abbreviates "
           "(its own short forms for street, building and region), a line may wrap, and a line the window has no "
           "room for may stand elsewhere on the page.")
_FIT = ("What may change: the type size down to the floor the pack sets, where the text wraps, the width of its "
        "column or box, or the text set over two boxes or pages.")
_FILL = ("What may change: how the content is spread over the pages (a page split, two joined, an exhibit moved) "
         "and the type size inside its floor.")
LAYOUT_RULES = {"DIAG-BOUNDS": _FIT, "DIAG-FIT": _FIT, "DIAG-OVERLAP": _FIT, "LETTER-DIN5008": _BLOCK, "EINV-PAGE-DIN5008": _BLOCK, "TRADE-BLOCK": _BLOCK,
                "LETTER-WINDOW": _WINDOW, "TRADE-WINDOW": _WINDOW,
                "FLOOR-OVERFLOW": _FIT, "FLOOR-OVERLAP": _FIT, "BDECK-FIT": _FIT, "DECK-BOUNDS": _FIT,
                "BDECK-FILL": _FILL, "BDECK-GRID": _FILL, "DECK-PAGES": _FILL}


# The check's last line is what the model reads right before it writes between steps; after a fail or a pass
# it wrote "Two rules failed: ..." and "The check passed on the table fix" (app runs 2026-10-12).
QUIET = "The person does not see this: write nothing about the check or your fixes between steps."


def layout_tail(rule, evidence):
    """The FAIL text of a rule, ending as a layout rule's must."""
    may = LAYOUT_RULES.get(rule)
    text = str(evidence)
    if not may or text.rstrip().endswith(NEVER_TO_FIT):
        return text
    return "%s%s %s %s" % (text.rstrip(), "" if text.rstrip().endswith((".", "!", "?")) else ".", may, NEVER_TO_FIT)


def numbers_in(value, out):
    """Every number in a data file, as written, so a trace check has something to compare with."""
    if isinstance(value, dict):
        for v in value.values():
            numbers_in(v, out)
    elif isinstance(value, list):
        for v in value:
            numbers_in(v, out)
    elif isinstance(value, (int, float)):
        out.append(str(value))
        out.append(("%.2f" % value).rstrip("0").rstrip("."))
    elif isinstance(value, str):
        out.append(value)
    return out


def case_for(output: Path) -> dict:
    """The truth the rules need: a case.json beside the output, or the data file it came from."""
    side = output.parent / "case.json"
    if side.is_file():
        return json.loads(side.read_text())

    truth = {"values": [], "pages": None}
    for other in sorted(output.parent.glob("*.json")):
        if other.resolve() == output.resolve():
            continue
        try:
            data = json.loads(other.read_text())
        except Exception:
            continue
        truth["values"].extend(numbers_in(data, []))
        if isinstance(data, dict) and isinstance(data.get("pages"), list) and truth["pages"] is None:
            truth["pages"] = len(data["pages"])
    # The accents the deck may use: the ones the brief names, or the house accent alone.
    house = ["#c2410c", "#d9480f", "#ad3a0b", "#f08c4a"]
    named = []
    for doc in sorted(output.parent.glob("*.md")):
        named.extend(h.lower() for h in re.findall(r"#[0-9a-fA-F]{6}", doc.read_text(errors="ignore")))
    truth["accents"] = sorted(set(named)) or house
    # No case.json means no case locale: the page's own language, which the builder writes on the
    # html element, stands in for it, so an English page is held to en-GB and a Swedish one to sv-SE.
    found = {"truth": truth}
    page = output.with_suffix(".html")
    if page.is_file():
        lang = re.search(r'<html[^>]*\blang="([^"]+)"', page.read_text(errors="ignore"))
        if lang:
            found["locale"] = lang.group(1)
    elif output.suffix.lower() == ".pdf":
        # A printed PDF carries no language of its own (Chromium writes no /Lang). With the page it was printed
        # from gone, the locale rules say they could not read it rather than hold the page to another locale's
        # forms (timed command run c07, 2026-10-25: an en-GB pro forma held to dd.MM.yyyy once its .html was removed).
        found["locale_unread"] = page.name
    elif output.suffix.lower() in (".docx", ".xlsx") and output.is_file():
        # Word and Excel carry the document's language in their core properties (dc:language).
        import zipfile
        try:
            with zipfile.ZipFile(output) as z:
                core = z.read("docProps/core.xml").decode("utf-8", "replace")
            lang = re.search(r"<dc:language[^>]*>([^<]+)</dc:language>", core)   # openpyxl writes xmlns on it
            if lang:
                found["locale"] = lang.group(1)
        except (KeyError, zipfile.BadZipFile):
            pass
    return found


# skill -> (the mark its builder writes, the command that writes it, the file that carries it, the
# needle that must appear in that file)
STAMP = {
    "html-deck": ("nodejam-deck-builder",
                  "python3 skills/html-deck/scripts/build_deck.py <your deck>.json %s",
                  ".html", 'name="generator" content="%s"'),
    "e-invoice": ("nodejam-page-builder",
                  "python3 skills/e-invoice/page/build_page.py <source>.json %s --locale <locale>",
                  ".html", 'name="generator" content="%s"'),
    "paper": ("nodejam-paper-builder",
              "python3 skills/paper/build_paper.py <your paper>.json (it writes %s and the .tex beside it)",
              ".tex", "%% %s"),
}



def built_with_the_builder(skill, output):
    """The file must come from its builder: the builder writes a mark, a hand-written file has none.

    Nothing is added to the customer's file. For a page printed to PDF the HTML the builder wrote
    sits beside it, a deck's HTML is itself the artifact, and a paper's .tex sits beside its PDF.
    """
    entry = STAMP.get(skill)
    if not entry:
        return []
    mark, command, suffix, needle = entry
    carried = output if output.suffix.lower() == suffix else output.with_suffix(suffix)
    wanted = needle % mark
    if not carried.is_file():
        return [("BUILT-BY-BUILDER",
                 "no %s beside %s; build it with: %s"
                 % (carried.name, output.name, command % output.name))]
    if skill == "paper" and wanted in carried.read_text(errors="ignore"):
        # The mark alone can be typed in; the builder's preamble, the starter's to the byte, cannot drift.
        text = carried.read_text(errors="ignore")
        starters = sorted((HERE.parent / "paper" / "templates").glob("*/paper.tex"))
        fronts = [s.read_text().split("\\begin{document}")[0] for s in starters]
        if fronts and not any(text.startswith(mark_line + "\n" + f) for f in fronts
                              for mark_line in ("% " + mark,)):
            return [("BUILT-BY-BUILDER",
                     "%s carries the mark but not the starter's preamble; rebuild it with: %s"
                     % (carried.name, command % output.name))]
    if wanted not in carried.read_text(errors="ignore"):
        return [("BUILT-BY-BUILDER",
                 "%s carries no builder mark; rebuild it with: %s"
                 % (carried.name, command % output.name))]
    return []


def recognises_its_own(skill, output, folder=""):
    """The pack's own evidence, read from its folder: the rule the runner used to guess at."""
    output = Path(output).resolve()
    pack = HERE.parent / skill / "pack.json"
    if not pack.is_file():
        return True
    try:
        rule = json.loads(pack.read_text()).get("recognises")
    except Exception:
        return True
    if not rule:
        return True
    wanted = rule.get("file") or "*"
    keys = rule.get("has") or []
    # A key the evidence must not carry: a trade document's spec has lines and a number like an
    # invoice's, and its "type" says it is not one.
    without = rule.get("without") or []
    stem = wanted.replace("*", "").lower()
    # "also": a second file the pack's own route leaves, claimed with no keys (a paper's hand-filled .tex)
    also = str(rule.get("also") or "").replace("*", "").lower()
    roots = [Path(folder).resolve()] if folder else [output.parent, output.parent.parent]
    seen = []
    for root in roots:
        for base, dirs, files in os.walk(root):
            dirs[:] = [d for d in dirs if not d.startswith(".") or d == ".work"]
            if len(Path(base).relative_to(root).parts) > 2:
                dirs[:] = []
                continue
            for name in files:
                if also and name.lower().endswith(also):
                    return True
                if stem and not name.lower().endswith(stem):
                    continue
                path = Path(base) / name
                seen.append(str(path))
                if not keys and not without:
                    return True
                try:
                    data = json.loads(path.read_text())
                except Exception:
                    continue
                if isinstance(data, dict) and all(key in data for key in keys) \
                        and not any(key in data for key in without):
                    return True
    return False


def declared(skill):
    """The rules and check modules a pack names in its own pack.json ("rules", "modules"), so a pack kept
    outside the shared library carries its rules with it and this file names no such pack."""
    try:
        pack = json.loads((HERE.parent / skill / "pack.json").read_text())
    except Exception:
        return [], {}
    return list(pack.get("rules") or []), dict(pack.get("modules") or {})


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("skill")
    ap.add_argument("output")
    ap.add_argument("--stage", default="first")
    ap.add_argument("--in", dest="folder", default="",
                    help="the folder the person is working in, where the pack's evidence is")
    ap.add_argument("--since", default="",
                    help="when the request began, in epoch milliseconds (the app sets NODEJAM_TURN_STARTED): a "
                         "file last changed before then is not this turn's work")
    ap.add_argument("--if-claimed", action="store_true",
                    help="run only when the pack's own evidence is in the folder: used when the "
                         "turn did not load this pack")
    a = ap.parse_args()
    own_rules, own_modules = declared(a.skill)
    # A private pack keeps its check modules with it, never in this shared folder (the edition copies it).
    if own_modules:
        for extra in (HERE.parent / a.skill, HERE.parent / a.skill / "scripts"):
            if extra.is_dir() and str(extra) not in sys.path:
                sys.path.insert(0, str(extra))
    rules = SKILL_RULES.get(a.skill) or own_rules
    if not rules:
        ap.error("no pack named %s: it is not in the shared list and its pack.json names no rules" % a.skill)

    output = Path(a.output)
    # The turn's end checks an Office file on the every-file floor as well as on its own pack, so the check a
    # chat runs before it replies does too: clean here is clean there (run 2026-10-15: the xlsx check passed,
    # the floor at the end found notes that did not fit their rows, and the chat wrote a second reply).
    if a.skill != "every-file" and output.suffix.lower() in (".docx", ".xlsx", ".pptx"):
        rules = list(rules) + [rule for rule in SKILL_RULES["every-file"] if rule not in rules]
    if a.if_claimed and not recognises_its_own(a.skill, output, a.folder):
        return 0
    if not output.is_file():
        entry = STAMP.get(a.skill)
        make = " build it with: %s" % (entry[1] % output.name) if entry else ""
        print("FAIL %-18s no %s beside the check.%s" % ("OUTPUT-MISSING", output.name, make))
        return 1
    if not output.is_file():
        print("FAIL output: %s does not exist" % output)
        return 2

    # The end state first, whatever the pack: a file that holds nothing, does not open, holds only filler or was
    # there before the request is red here, and no rule below is asked to judge it (a reply that says "done" is
    # not a file; a 0-byte workbook once passed the every-file floor as clean).
    hollow = end_state.judge(output, a.since)
    if hollow:
        for rule, evidence in hollow:
            print("FAIL %-18s %s" % (rule, evidence))
        print("1 of 1 end-state rules failed; fix this and run the check again. %s" % QUIET)
        return 1

    case = case_for(output)
    # The folder the check was told about with --in: a rule that compares the page with the person's own
    # files (EINV-PARTICULARS) reads them there, and beside the page when no folder was named.
    case["folder"] = a.folder
    # Rules that compare the file with the case's own truth can only run where that truth is: beside
    # the output as case.json. Anywhere else they would fail a file that is right, so they say so.
    truth_rules = {"EINV-PAGE-COMPLETE", "EINV-PAGE-NO-EXTRA", "EINV-PAGE-TRACE",
                   "DECK-TRACE", "DECK-ACCENT", "DECK-PAGES"}
    has_truth = (output.parent / "case.json").is_file()
    skipped, warned = [], []
    failures, checked = [], 0
    unable = []         # the rules that could not run here, as against the ones that do not apply to this file
    for rule in rules:
        if rule in truth_rules and not has_truth:
            skipped.append((rule, "the case's truth is not in this folder (no case.json)"))
            continue
        prefix = rule.split("-")[0]
        try:
            module = shared_module(RULE_MODULES[rule]) if rule in RULE_MODULES else \
                __import__(MODULES.get(prefix) or own_modules[prefix])
        except ImportError as exc:
            # A dependency this machine lacks (python-docx, PyMuPDF): the rule cannot run, and that is said,
            # never passed over. One of our own check modules missing is a broken install and stays loud.
            if exc.name in set(MODULES.values()) | set(own_modules.values()) | set(RULE_MODULES.values()):
                raise
            skipped.append((rule, "could not check: %s" % str(exc)[:90]))
            unable.append(skipped[-1])
            continue
        try:
            result = module.check(rule, output, case, a.stage)
        except Exception as exc:                                  # a rule that cannot read the file
            skipped.append((rule, "could not check: %s" % str(exc)[:90]))
            unable.append(skipped[-1])
            continue
        if isinstance(result, tuple) and not result[0] and isinstance(result[1], str) \
                and ("could not" in result[1] or "not measured" in result[1]):
            skipped.append((rule, result[1][:90]))
            if "could not" in result[1]:
                unable.append(skipped[-1])
            continue
        passed, evidence = result if isinstance(result, tuple) else (result, "")
        checked += 1
        if passed is False:
            failures.append((rule, evidence))
        elif passed and isinstance(evidence, str) and evidence.startswith("WARN "):
            warned.append((rule, evidence[5:]))                   # passes, and the reply must say so

    failures.extend(built_with_the_builder(a.skill, output))
    gaps = end_state.open_gaps(output)
    if gaps:
        # Well made and not finished: the person still has to answer these. Never take a marker out to pass;
        # ask, fill and rebuild, or hand the file back as a draft that lists each gap.
        failures.append(("OUTPUT-OPEN-GAP", "%d gap%s left for the person, first %s. Ask for each, fill it in and "
                         "build again; until they answer, hand it back as a draft and list the gaps. Never take a "
                         "marker out to pass." % (len(gaps), "" if len(gaps) == 1 else "s", gaps[0][:90])))

    for rule, evidence in skipped:
        print("SKIP %-18s %s" % (rule, evidence))
    for rule, evidence in failures:
        print("FAIL %-18s %s" % (rule, layout_tail(rule, evidence)))
    for rule, evidence in warned:
        print("WARN %-18s %s" % (rule, evidence))
    if failures:
        print("%d of %d rules failed; fix these and run the check again. %s" % (len(failures), checked, QUIET))
        return 1
    if checked == 0 and unable:
        # Zero rules run is not clean (a deck's real run, 2026-10-10: every rule was skipped and the last
        # line read "pack check clean: 0 rules passed"). The line below is what the Stop hook and the app's
        # pack check read as "could not check": said once to the agent, never a pass, never a loop.
        more = " and %d more skipped" % (len(skipped) - 1) if len(skipped) > 1 else ""
        print("pack check not checked: none of the %d rules could run on %s (%s %s%s). Nothing here says the "
              "file is right or wrong: do not call it checked, and say in the reply that the check could not "
              "run and why." % (len(rules), output.name, unable[0][0], unable[0][1], more))
        return 3
    if checked == 0:
        # No rule could have run because none applies: the Word skill's reference rules on a letter, the
        # rules that need a case's own truth outside a case. That is not "could not check" (first real
        # runs with the line above, 2026-10-10: every letter and every set of minutes was called unchecked
        # because the Word skill's three reference rules had nothing to measure), and it is not clean either.
        why = "%s %s" % skipped[0] if skipped else "the pack names no rule"
        print("pack check not applicable: none of the %d rules applies to %s (%s). This pack has nothing to "
              "say about the file." % (len(rules), output.name, why))
        return 0
    print("pack check clean: %d rules passed. %s" % (checked, QUIET))
    return 0


if __name__ == "__main__":
    sys.exit(main())
