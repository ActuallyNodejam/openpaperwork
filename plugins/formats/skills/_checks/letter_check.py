#!/usr/bin/env python3
"""Checks for any document printed on the library's business letter (skills/_shared/letter.py).

  LETTER-DIN5008   The page sits on DIN 5008:2020 Form B. A PDF: the customer in the window
                   address field, the document's data in the information block, one 25 mm left
                   edge, amounts flush right; a letter's information block ends on the text's right
                   edge, 20 mm from the paper's, as an invoice's does. A Word file: margins of 25 mm
                   left, 20 mm right and a 45 mm letterhead. A workbook is not a letter and skips this.
                   A trade document sent from a country with a letter layout of its own stands on that
                   layout, as its invoice does, and is measured by TRADE-WINDOW instead.
  LETTER-COMPANY   When the seller is a company, the letter states its register number and
                   registered office (Directive (EU) 2017/1132 Art. 26), and a GmbH its managing
                   directors (GmbHG 35a); a Belgian company also RPR or RPM with its court (art.
                   2:20), an Austrian one its Firmenbuch court (UGB § 14), an Irish one every
                   director (Companies Act 2014 s.151(1)). A Spanish company states its Registro
                   Mercantil entry, and the paid-up capital beside the subscribed when it names its
                   capital (Código de Comercio art. 24); an Italian one the register office and number,
                   the capital paid up, a sole shareholder and liquidation (Codice civile art. 2250);
                   a Polish sp. z o.o. or S.A. the registry court, the KRS number, the NIP and the
                   share capital (Kodeks spółek handlowych arts. 206 and 374). When the files give
                   none of it, the rule skips and the reply must say what is missing.
  LETTER-PARTS     A business letter carries the parts DIN 5008 sets out, as its spec names them:
                   the subject, the salutation (when the letter has one), the closing and the
                   signatory's name.
  LETTER-WINDOW    A letter from Norway, Denmark, Finland, the United States, the United Kingdom,
                   Canada, Australia, Belgium, the Netherlands, Austria, Ireland, Spain, Italy or
                   Poland has its address inside the envelope window of the sender's country
                   (skills/_shared/letter.py LAYOUTS: on the right in Belgium, Spain, Italy and
                   Poland, 15 mm inside the window's left edge in Ireland, 10 mm inside it in Poland)
                   and nothing else in the window; in Word, the page, the margins and the address row
                   put it there.
  LETTER-ADDRESS   Such a letter writes the address the way the recipient's post office reads it
                   (USPS Publication 28, Canada Post, Australia Post, Royal Mail, Posten, Posti,
                   PostNord, bpost, PostNL, Österreichische Post, An Post, Correos, Poste Italiane,
                   Poczta Polska; the country in capitals on the last line abroad, UPU RL 123.3.3).
  LETTER-DATE      The letter's date is written out in its language's form (CLDR long: October 9,
                   2026; 9 October 2026; 9. oktober 2026; 9.10.2026 in Finnish; Montréal, le
                   9 octobre 2026; 9 oktober 2026 in Dutch; 9. Jänner 2026 in Austria; Madrid, 9 de
                   octubre de 2026; Milano, 9 ottobre 2026; Warszawa, 9 października 2026), or in DIN
                   5008's numeric form on a DIN 5008 letter.
  LETTER-FORM      The salutation and closing follow the variant: "Dear Ms. Berg:" and "Sincerely,"
                   in the United States, a comma after the closing in Canada, "Yours faithfully" after
                   "Dear Sir or Madam" and "Yours sincerely" to a named person in the United Kingdom
                   and Australia (no punctuation in Australia) and in Ireland, and in French "Objet :",
                   a salutation with a comma, a closing that repeats it and « » for quotation marks. In
                   Dutch a comma after the salutation and after the closing (the Netherlands), or after
                   the closing only when the salutation has one (Belgium; Taaladvies.net); in German a
                   comma or an exclamation mark after the salutation and no mark after the closing
                   (Amtliches Regelwerk der deutschen Rechtschreibung 2024, § 72). In Spanish a colon
                   after the salutation, never a comma, and a comma or a full stop after a closing with
                   no verb (Real Academia Española, Puntuación de saludos y despedidas en cartas y
                   correos electrónicos); in Polish a comma or an exclamation mark after the salutation
                   and no mark after the closing (Poradnia Językowa PWN, 2021). No Italian authority's
                   rule was found, so none is scripted for Italian.
  LETTER-PAGES     A Finnish letter numbers its pages in the head, the page count after the number
                   in brackets: 1 (2) (Kielitoimiston ohjepankki, Sivunumerointi, citing SFS 2487).
  LETTER-LANGUAGE  Every label, the footer's included, is in the letter's language.

check(rule_id, path, case, stage) -> (passed, evidence); passed is None when the rule does not
apply. Standard library only, pdftotext for PDFs.
"""
import html
import json
import re
import subprocess
import sys
import zipfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "_shared"))
import einvoice_page  # noqa: E402
import letter  # noqa: E402

TWIP_MM = 25.4 / 1440


def spec_beside(path):
    """The spec or order the document was built from: a JSON beside it with a seller and a buyer, or
    a letter's sender and recipient, which the rules read as the seller and the buyer."""
    # Its own spec first (run 9: a packing list was read as the commercial invoice beside it).
    stem = Path(path).stem
    for p in sorted(Path(path).parent.glob("*.json"), key=lambda p: (p.stem not in (stem, stem + ".spec", stem + "-spec", stem + "_spec"), p.name)):
        try:
            data = json.loads(p.read_text())
        except (ValueError, OSError):
            continue
        if isinstance(data, dict) and isinstance(data.get("sender"), dict) and isinstance(data.get("recipient"), dict):
            data = dict(data, seller=data["sender"], buyer=data["recipient"])
        if isinstance(data, dict) and isinstance(data.get("seller"), dict) and isinstance(data.get("buyer"), dict):
            return data
    return None


def text_of(path):
    path = Path(path)
    if path.suffix.lower() == ".pdf":
        return subprocess.run(["pdftotext", str(path), "-"], capture_output=True, text=True).stdout
    if path.suffix.lower() == ".docx":
        with zipfile.ZipFile(path) as z:
            parts = [n for n in z.namelist() if re.fullmatch(r"word/(document|header\d*|footer\d*)\.xml", n)]
            xml = " ".join(z.read(n).decode("utf-8", "replace") for n in parts)
        return html.unescape(re.sub(r"<[^>]+>", " ", xml.replace("</w:p>", "\n")))
    if path.suffix.lower() == ".xlsx":
        with zipfile.ZipFile(path) as z:
            xml = " ".join(z.read(n).decode("utf-8", "replace") for n in z.namelist() if n.startswith("xl/"))
        return html.unescape(re.sub(r"<[^>]+>", " ", xml))      # &#228; is ä
    return ""


def on_page(value, flat):
    """A footer column wraps a long registered office over two lines, and a PDF's text then reads the
    other columns between them: the value's words are looked for in order, with a short run of other text
    allowed between two of them."""
    value = re.sub(r"\s+", " ", str(value)).strip()
    if value in flat:
        return True
    words = [re.escape(w) for w in value.split(" ")]
    return len(words) > 2 and re.search(r"(?<!\w)" + r"(?:\s|\s.{0,120}?\s)".join(words) + r"(?!\w)", flat) is not None


def docx_margins(path):
    with zipfile.ZipFile(path) as z:
        xml = z.read("word/document.xml").decode("utf-8", "replace")
    m = re.search(r"<w:pgMar ([^>]*)/>", xml)
    if not m:
        return None
    attrs = dict(re.findall(r'w:(\w+)="(\d+)"', m.group(1)))
    return {k: int(v) * TWIP_MM for k, v in attrs.items()}


def window_letter(spec):
    """The builder's own reading of a letter spec for a window layout, or None (DIN 5008, or no letter)."""
    if not spec or not isinstance(spec.get("sender"), dict) or not isinstance(spec.get("recipient"), dict):
        return None
    lid, lay = letter.letter_layout(spec)
    if not lay:
        return None
    here = HERE.parent / "business-letter" / "scripts"
    if str(here) not in sys.path:
        sys.path.insert(0, str(here))
    try:
        import window_letter as wl
        return wl.WindowLetter({k: v for k, v in spec.items() if k not in ("seller", "buyer")})
    except (ImportError, ValueError):
        return None


def docx_layout(path):
    """Page size, margins, the first table's first row and how far its address cell starts from the left
    margin, in mm, read from the Word file."""
    with zipfile.ZipFile(path) as z:
        xml = z.read("word/document.xml").decode("utf-8", "replace")
    size = re.search(r'<w:pgSz[^>]*w:w="(\d+)"[^>]*w:h="(\d+)"', xml)
    m = docx_margins(path) or {}
    tbl = re.search(r"<w:tbl>.*?</w:tbl>", xml, re.S)
    row = re.search(r'<w:trHeight w:val="(\d+)" w:hRule="exact"/>', tbl.group(0)) if tbl else None
    first_tr = re.search(r"<w:tr[ >].*?</w:tr>", tbl.group(0), re.S) if tbl else None
    second = re.findall(r"<w:tr[ >].*?</w:tr>", tbl.group(0), re.S)[1:2] if tbl else []
    addr = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", second[0].replace("</w:p>", "\n"))).strip() if second else ""
    # The empty cells before the address move it right: on the right in Belgium, 9 mm in in Ireland.
    lead = 0.0
    for cell in re.findall(r"<w:tc>.*?</w:tc>", second[0], re.S) if second else []:
        if re.sub(r"<[^>]+>", "", cell).strip():
            break
        width = re.search(r'<w:tcW[^>]*w:w="(\d+)"', cell)
        lead += int(width.group(1)) * TWIP_MM if width else 0
    return {"size": (int(size.group(1)) * TWIP_MM, int(size.group(2)) * TWIP_MM) if size else None, "margins": m,
            "lead": lead,
            "row0": int(row.group(1)) * TWIP_MM if row and first_tr and row.group(0) in first_tr.group(0) else None,
            "address_text": addr}


def norm(s):
    return re.sub(r"\s+", " ", str(s).replace("\u00a0", " ")).strip()


def page_width_mm(path):
    """The width of a PDF's first page or of a Word file's page in mm, or None."""
    path = Path(path)
    if path.suffix.lower() == ".pdf":
        return einvoice_page.page_width(path)
    if path.suffix.lower() == ".docx":
        try:
            with zipfile.ZipFile(path) as z:
                size = re.search(r'<w:pgSz[^>]*w:w="(\d+)"', z.read("word/document.xml").decode("utf-8", "replace"))
        except (KeyError, OSError, zipfile.BadZipFile):
            return None
        return int(size.group(1)) * TWIP_MM if size else None
    return None


TRADE_TYPES = ("quotation", "order_confirmation", "delivery_note", "proforma_invoice", "purchase_order")


def sheet_layout(spec, path):
    """The country layout of a trade document (a spec whose "type", or a case's truth whose "doc", names
    one): its sender's country's, the one its invoice sits on, when the file is on that layout's own paper;
    None for DIN 5008 Form B and for anything that is not a trade document. spec: seller is the sender (a
    purchase order's parties are already turned round)."""
    if not spec or (spec.get("type") or spec.get("doc")) not in TRADE_TYPES or isinstance(spec.get("sender"), dict):
        return None
    _lid, lay = letter.letter_layout({"sender": spec.get("seller") or {}, "layout": spec.get("layout")})
    if not lay:
        return None
    width = page_width_mm(path)
    return lay if width is None or abs(width - letter.PAPER_MM[lay["paper"]][0]) <= 1.5 else None


def window_problems(pdf, lt):
    """The address lines inside the layout's window, nothing else in it; a list of problems."""
    wx, wy, ww, wh = lt.lay["window"]
    x0, y0, x1, y1 = letter.window_box(lt.lay)      # the window less what the operator keeps clear inside it
    words = einvoice_page.page_words(pdf)
    lines = lt.address()
    tokens = {t for line in lines for t in line.split()}
    problems = []
    for line in lines:
        toks = line.split()
        firsts = [w for w in words if w[4] == toks[0]]
        if not firsts:
            problems.append("the address line %r is not on page 1" % line)
            continue
        f = min(firsts, key=lambda w: abs(w[0] - wx) + abs(w[1] - (wy + wh / 2)))
        lasts = [w for w in words if w[4] == toks[-1] and abs(w[1] - f[1]) < 1.5 and w[0] >= f[0] - 0.1]
        last = max(lasts, key=lambda w: w[2]) if lasts else f
        if not (f[0] >= x0 - 0.5 and f[1] >= y0 - 0.5 and last[2] <= x1 + 0.5 and last[3] <= y1 + 0.5):
            problems.append("the address line %r sits at %.0f-%.0f mm across, %.0f-%.0f mm down, outside the window "
                            "(%.0f-%.0f across, %.0f-%.0f down)" % (line, f[0], last[2], f[1], last[3], x0, x1, y0, y1))
    stray = sorted({w[4] for w in words if w[0] >= wx and w[2] <= wx + ww and w[1] >= wy and w[3] <= wy + wh
                    and w[4] not in tokens})
    if stray:
        problems.append("something else shows in the window: %s" % " ".join(stray[:6]))
    return problems


def info_edge_problems(pdf):
    """A DIN 5008 letter's information block ends on the text's right edge: nothing in it, from 125 mm
    across and level with the address field, passes 190 mm (20 mm from the paper's edge)."""
    g = letter.GEOMETRY
    edge = letter.PAPER_MM["A4"][0] - g["right"]
    words = [w for w in einvoice_page.page_words(pdf)
             if w[0] >= g["info_x"] - 1 and g["info_y"] - 2 <= w[1] <= g["field_y"] + g["return_h"] + g["address_h"]]
    far = max(words, key=lambda w: w[2]) if words else None
    if far and far[2] > edge + 0.5:
        return ["the information block runs to %.1f mm across (%s); it ends on the text's right edge, %.0f mm" % (
            far[2], far[4], edge)]
    return []


# ---- the sender's own company law: a fail on a letter and a trade document, a question on four invoices ----
#
# Every statute the invoice rule reads (skills/_checks/einvoice_particulars.py, LAW and NOT_ON_INVOICES) names
# business letters and order forms. So a letter or a trade document whose sender is a company fails when a
# particular its law asks for is neither given nor declared unknown ("unknown": ["register_number"] in the
# sender, the invoice rule's way out: printed as nothing, warned about, never made up). The statutes of
# Germany, Austria, Poland and Finland stop at business letters, order forms and forms: on an INVOICE of such
# a company the same gap is a question (WARN), never a fail, and the message says whose reading it is.
INVOICE_READING = {
    "DE": "the IHK für Oberfranken Bayreuth reads an invoice as a business letter (Pflichtangaben auf "
          "Geschäftsbriefen, Stand April 2019: all outside written communication, invoices among its examples; "
          "read 2026-10-10)",
    "AT": "an invoice sent to a named recipient can be read as a Geschäftsbrief; no chamber or ministry page "
          "saying so was found on 2026-10-10, so this is a reading, not a published one",
    "PL": "an invoice can be read as a pismo handlowe; no chamber or ministry page saying so was found on "
          "2026-10-10, so this is a reading, not a published one",
    "FI": "an invoice can be read as a lomake (form); no chamber or ministry page saying so was found on "
          "2026-10-10, so this is a reading, not a published one",
}


def company_statute(seller):
    """The article that asks a company of this country to state its particulars on letters and order forms, as
    the invoice rule's tables cite it."""
    import einvoice_particulars as part
    cc = letter.country_code(seller.get("country"))
    if cc in part.LAW:
        return part.LAW[cc][0]
    if cc in part.NOT_ON_INVOICES and " name" in part.NOT_ON_INVOICES[cc]:
        return part.NOT_ON_INVOICES[cc].split(" name")[0]
    return "Directive (EU) 2017/1132 Art. 26"


def _spec_for(path, case, stage):
    truth = (case or {}).get("truth") or {}
    staged = truth.get(stage or "first") if isinstance(truth.get(stage or "first"), dict) else {}
    spec = spec_beside(path) or dict(truth, **staged)
    if spec.get("type") == "purchase_order" or spec.get("doc") == "purchase_order":
        spec = dict(spec, seller=spec.get("buyer") or {}, buyer=spec.get("seller") or {})
    return spec


SELLS = ("quotation", "order_confirmation", "proforma_invoice")


def f_tax_left_off(path, case, spec, seller):
    """A Swedish seller whose own files say it is approved for F-skatt has it on its quotations, order confirmations
    and pro formas too: a fact the person's files give is never left off the page (timed command run c04,
    2026-10-25: the person's company file said «Godkänd för F-skatt» and the quotation dropped it). With no file
    saying so the page is left alone; the invoice rule asks that question (einvoice_particulars.f_tax_warning)."""
    import einvoice_particulars as part
    if (spec.get("type") or spec.get("doc")) not in SELLS or letter.country_code(seller.get("country")) != "SE":
        return ""
    page = text_of(path) or ""
    if not page.strip() or part.F_TAX.search(page):
        return ""
    told = [name for name, text in part.evidence_files(path, (case or {}).get("folder") or "")
            if part.F_TAX.search(text or "")]
    if not told:
        return ""
    return ("the person's file %s says the seller is approved for F-skatt and this page does not: put «Godkänd för "
            "F-skatt» in the seller's \"further\", printed in its footer (a fact the person's files give is never "
            "left off)" % told[0])


def company_verdict(result, path, case, stage):
    """LETTER-COMPANY's last word: what the page check found, and what the sender's own law still asks for."""
    spec = _spec_for(path, case, stage)
    seller = spec.get("seller") or {}
    if not isinstance(seller, dict) or not seller or not letter.legal_form(seller):
        return result
    missing = letter.company_missing(seller)
    listed = []
    for holder in (spec, seller):
        value = holder.get("unknown") or []
        listed += [value] if isinstance(value, str) else list(value)
    unknown = {str(k).strip().split(".")[-1] for k in listed}
    owed = [m for m in missing if m.split(" ")[0] not in unknown]
    declared = [m for m in missing if m.split(" ")[0] in unknown]
    trade = spec.get("type") or spec.get("doc") in ("quotation", "order_confirmation", "delivery_note",
                                                     "proforma_invoice", "purchase_order")
    a_letter = isinstance(spec.get("sender"), dict) or (spec.get("subject") and spec.get("body"))
    cc = letter.country_code(seller.get("country"))
    if cc == "FI" and seller.get("business_id"):
        # A Finnish company's register number is its Y-tunnus, which an invoice's order carries as business_id.
        missing = [m for m in missing if m != "register_number"]
        owed = [m for m in owed if m != "register_number"]
    statute = company_statute(seller)
    passed, evidence = result if isinstance(result, tuple) else (result, "")
    if trade or a_letter:
        if owed:
            where = "sender" if a_letter else ("buyer" if spec.get("type") == "purchase_order" else "seller")
            return False, ("the sender is a company, and its letters and order forms state what this page does not "
                           "(%s): %s. Take each from the person's files and put it in \"%s\"; one the files do not give "
                           "is declared there with \"unknown\": [\"%s\"], printed as nothing, and said in your reply. "
                           "Never make one up" % (statute, ", ".join(owed), where, owed[0].split(" ")[0]))
        if passed is False:
            return result
        left_off = f_tax_left_off(path, case, spec, seller)
        if left_off:
            return False, left_off
        if declared:
            return True, ("WARN the data file declares unknown what the company's letters state (%s): %s. The page "
                          "does not carry them and is not complete without them; say so in your reply"
                          % (statute, ", ".join(declared)))
        return result
    if cc in INVOICE_READING and missing and passed is not False:
        return True, ("WARN a company's business letters and order forms state %s (%s), and this invoice does not. "
                      "The statute's words stop at letters and order forms; %s. Put them on the invoice from the "
                      "person's files, or say in your reply that the files do not give them. A question, not a "
                      "fault; never make one up" % (", ".join(missing), statute, INVOICE_READING[cc]))
    return result


def check(rule_id, path, case, stage):
    """Every LETTER- rule; LETTER-COMPANY's verdict also asks what the sender's own company law asks for."""
    result = _rules(rule_id, path, case, stage)
    if rule_id == "LETTER-COMPANY":
        return company_verdict(result, Path(path), case, stage)
    return result


def _rules(rule_id, path, case, stage):
    path = Path(path)
    truth = case.get("truth") or {}
    staged = truth.get(stage or "first") if isinstance(truth.get(stage or "first"), dict) else {}
    spec = spec_beside(path) or dict(truth, **staged)
    if spec.get("type") == "purchase_order" or spec.get("doc") == "purchase_order":
        # A purchase order is the buyer's letter to its supplier: the supplier is in the address field
        # and the company details in the footer are the buyer's.
        spec = dict(spec, seller=spec.get("buyer") or {}, buyer=spec.get("seller") or {})
    lt = window_letter(spec)
    if rule_id == "LETTER-DIN5008" and lt:
        return None, "laid out for %s; LETTER-WINDOW measures it" % lt.lay["name"]
    if rule_id == "LETTER-DIN5008" and sheet_layout(spec, path):
        return None, "laid out for %s; TRADE-WINDOW measures it" % sheet_layout(spec, path)["name"]
    if rule_id == "LETTER-DIN5008":
        kind = path.suffix.lower()
        if kind == ".pdf":
            buyer = (spec.get("buyer") or {}).get("name") or ""
            problems = einvoice_page.din5008_problems(path, buyer)
            if isinstance(spec.get("sender"), dict) and spec.get("subject"):
                problems += info_edge_problems(path)
            return (not problems, "; ".join(problems) or "laid out on DIN 5008 Form B")
        if kind == ".docx":
            m = docx_margins(path)
            if not m:
                return False, "no page margins in the document"
            bad = []
            if abs(m.get("left", 0) - 25) > 1:
                bad.append("left margin %.1f mm, DIN 5008 wants 25" % m.get("left", 0))
            if abs(m.get("right", 0) - 20) > 1:
                bad.append("right margin %.1f mm, DIN 5008 wants 20" % m.get("right", 0))
            if abs(m.get("top", 0) - 45) > 1:
                bad.append("letterhead %.1f mm, Form B wants 45" % m.get("top", 0))
            return (not bad, "; ".join(bad) or "Word margins on DIN 5008 Form B")
        return None, "a %s is not a letter; DIN 5008 does not apply" % kind
    if rule_id == "LETTER-COMPANY":
        seller = spec.get("seller") or {}
        if not seller or not letter.legal_form(seller):
            return None, "the seller is not a company, or not known"
        missing = letter.company_missing(seller)
        if letter.country_code(seller.get("country")) == "FR":
            # A French company: its SIREN (in any grouping) and "RCS" with the register's city (F31808).
            if not seller.get("siren"):
                return None, "the files give no SIREN; the reply must say %s are missing" % ", ".join(missing)
            flat = re.sub(r"\s+", " ", text_of(path))
            bare = re.sub(r"\s+", "", flat)
            absent = [] if re.sub(r"\D", "", str(seller["siren"])) in bare else ["SIREN %s" % seller["siren"]]
            absent += [v for v in (seller.get("rcs"), seller.get("legal_form")) if v and str(v) not in flat]
            return (not absent, "company details on the letter" if not absent else "not on the letter: %s" % ", ".join(absent))
        given = [seller.get(k) for k in ("registered_office", "register_number") if seller.get(k)]
        cc_s = letter.country_code(seller.get("country"))
        # Belgium (art. 2:20 5°: RPR or RPM and the court of the seat) and Austria (UGB § 14: the Firmenbuch
        # court) print the register itself beside the number; so do Spain (the Registro Mercantil, Código de
        # Comercio art. 24), Italy (the register office, Codice civile art. 2250) and Poland (the registry
        # court, KSH arts. 206 and 374).
        if cc_s in ("BE", "AT", "ES", "IT", "PL") and seller.get("register") and given:
            given.append(seller["register"])
        if cc_s in ("ES", "IT", "PL") and given:
            # The capital as the company states it (art. 24; art. 2250; arts. 206 § 1 pkt 4 and 374 § 1 pkt 4).
            given += [str(seller[k]) for k in ("share_capital", "paid_up_capital") if seller.get(k) not in (None, "")]
            given += [seller[k] for k in ("directed_by", "group") if seller.get(k)]     # art. 2497-bis; art. 206 § 1 pkt 5
        if not given:
            return None, "the files give no register details; the reply must say %s are missing" % ", ".join(missing)
        flat = re.sub(r"\s+", " ", text_of(path))
        absent = [v for v in given if not on_page(v, flat)]
        directors = seller.get("managing_directors") or []
        if isinstance(directors, str):
            directors = [directors]
        absent += [d for d in directors if d not in flat]
        low = flat.lower()
        if cc_s == "PL" and seller.get("vat_id") and re.sub(r"\D", "", str(seller["vat_id"])) not in re.sub(r"[\s-]", "", flat):
            absent.append("NIP %s (KSH art. 206 § 1 pkt 3)" % seller["vat_id"])
        if cc_s == "IT" and seller.get("sole_shareholder") and "unico socio" not in low:
            absent.append("that the company has a sole shareholder (unico socio, art. 2250)")
        if cc_s in ("IT", "ES") and seller.get("in_liquidation") and not re.search(r"liquidazione|liquidación", low):
            absent.append("that the company is in liquidation (%s)" % ("art. 2250" if cc_s == "IT" else "Código de Comercio art. 24"))
        return (not absent, "company details on the letter" if not absent else "not on the letter: %s" % ", ".join(absent))
    if rule_id == "LETTER-PARTS":
        closing = spec.get("closing") or (lt.spec["closing"] if lt else None)
        wanted = [("subject", spec.get("subject")), ("closing", closing),
                  ("signatory", (spec.get("signatory") or {}).get("name"))]
        if spec.get("salutation"):
            wanted.insert(1, ("salutation", spec["salutation"]))
        if not all(value for _, value in wanted):
            return None, "no letter spec beside the file names its parts"
        flat = re.sub(r"\s+", " ", text_of(path))
        if lt:
            flat, wanted = norm(flat), [(k, lt.spec.get(k, v) if k == "subject" else v) for k, v in wanted]
        absent = [part for part, value in wanted if re.sub(r"\s+", " ", str(value)).strip() not in flat]
        return (not absent, "%s in place" % ", ".join(k for k, _ in wanted) if not absent
                else "missing from the letter: %s" % ", ".join(absent))
    if rule_id in ("LETTER-WINDOW", "LETTER-ADDRESS", "LETTER-DATE", "LETTER-FORM", "LETTER-LANGUAGE", "LETTER-PAGES"):
        return letter_rules(rule_id, path, spec, lt)
    return None, "unknown rule"


def letter_rules(rule_id, path, spec, lt):
    kind = path.suffix.lower()
    if kind not in (".pdf", ".docx"):
        return None, "a %s is not a letter" % kind
    if not spec or not isinstance(spec.get("sender"), dict) or not isinstance(spec.get("recipient"), dict):
        return None, "no letter spec beside the file"
    flat = norm(text_of(path))
    if rule_id == "LETTER-WINDOW":
        if not lt:
            return None, "a DIN 5008 letter; LETTER-DIN5008 measures it"
        lay = lt.lay
        if kind == ".pdf":
            problems = window_problems(path, lt)
            return (not problems, "; ".join(problems) or "the address sits in the window of the %s" % lay["envelope"])
        d = docx_layout(path)
        bad = []
        W, H = letter.paper_size(lay)
        if not d["size"] or abs(d["size"][0] - W) > 1 or abs(d["size"][1] - H) > 1:
            bad.append("the page is not %s (%.0f x %.0f mm)" % (lay["paper"], W, H))
        m = d["margins"]
        for side in ("left", "right"):
            if abs(m.get(side, 0) - lay[side]) > 1:
                bad.append("%s margin %.1f mm, the layout wants %.1f" % (side, m.get(side, 0), lay[side]))
        x0, y0, x1, y1 = letter.window_box(lay)
        top = m.get("top", 0) + (d["row0"] or 0)
        if d["row0"] is None:
            bad.append("no fixed first row puts the address in the window; build it with letter_create.py")
        elif not (y0 - 0.5 <= top <= y1 - 15):
            bad.append("the address starts %.1f mm down; it may run %.0f-%.0f mm" % (top, y0, y1))
        across = m.get("left", 0) + d["lead"]
        if not (x0 - 0.5 <= across <= x0 + 10):
            bad.append("the address starts %.1f mm across; it may start at %.0f mm" % (across, x0))
        lines = lt.address()
        if not all(norm(x) in norm(d["address_text"]) for x in lines):
            bad.append("the address row does not hold the address")
        return (not bad, "; ".join(bad) or "Word page, margins and address row put the address in the window")
    if rule_id == "LETTER-ADDRESS":
        if not lt:
            return None, "a DIN 5008 letter; LETTER-DIN5008 measures the address field"
        lines = [norm(x) for x in lt.address()]
        pos, missing = 0, []
        for line in lines:
            at = flat.find(line, pos)
            if at < 0:
                missing.append(line)
            else:
                pos = at + len(line)
        return (not missing, "the address as the recipient's post office reads it" if not missing
                else "not written as the post office reads it, or out of order: %s" % " / ".join(missing[:3]))
    if rule_id == "LETTER-DATE":
        if lt:
            want = lt.date_line()
        else:
            loc, _ = letter.language(dict(spec, seller=spec["sender"], buyer=spec["recipient"]))
            want = letter.date(spec.get("date"), loc)
        return (norm(want) in flat, "the date reads %s" % want if norm(want) in flat
                else "the date is not written as %s" % want)
    if rule_id == "LETTER-FORM":
        if not lt:
            return None, "no variant rule for a DIN 5008 letter"
        s, loc, cc = lt.spec, lt.locale, lt.lay["country"]
        sal, close = norm(s.get("salutation") or ""), norm(s.get("closing") or "")
        bad = []
        if loc == "en-US":
            if not sal.endswith(":"):
                bad.append("a US business letter's salutation ends with a colon (Dear Ms. Berg:)")
            if not close.endswith(","):
                bad.append("the closing ends with a comma (Sincerely,)")
        elif loc == "en-CA":
            if not close.endswith(","):
                bad.append("the complimentary close ends with a comma (Sincerely,)")
        elif loc in ("en-GB", "en-AU", "en-IE"):
            unnamed = sal.lower().rstrip(",").strip() in ("dear sir or madam", "dear sir", "dear madam")
            want = "yours faithfully" if unnamed else "yours sincerely"
            if not close.lower().rstrip(",").startswith(want):
                bad.append("%r goes with %r" % (s.get("salutation"), want.capitalize()))
            if loc == "en-AU" and (sal.endswith(",") or close.endswith(",")):
                bad.append("the Style Manual sets salutation and closing with no punctuation")
        elif loc.startswith("fr"):
            if not re.search(r"\bObjet\s?:", flat):
                bad.append("the subject is introduced by Objet :")
            if not sal.endswith(","):
                bad.append("the salutation ends with a comma (Madame,)")
            term = sal.rstrip(",").strip()
            if term and term.lower() not in close.lower():
                bad.append("the closing sentence repeats the salutation (%s)" % term)
            if '"' in flat:
                bad.append("quotation marks are « » in French, not straight quotes")
        elif loc == "nl-NL":
            # Taaladvies.net: the Netherlands always writes a comma after the salutation, and one after the closing.
            if not sal.endswith(","):
                bad.append("a Dutch salutation ends with a comma (Geachte heer Jansen,)")
            if not close.endswith(","):
                bad.append("the closing ends with a comma (Met vriendelijke groet,)")
        elif loc == "nl-BE":
            # Taaladvies.net on the BIN standard: a comma after the closing when the salutation has one.
            if sal.endswith(",") and not close.endswith(","):
                bad.append("the salutation has a comma, so the closing takes one too (Met vriendelijke groeten,)")
        elif loc in ("de-AT", "de-DE"):
            # Amtliches Regelwerk 2024, § 72: a comma (seldom an exclamation mark) after the salutation, the
            # closing mostly without a mark.
            if not sal.endswith((",", "!")):
                bad.append("a German salutation ends with a comma (Sehr geehrte Frau Huber,)")
            if close.endswith((",", ".", "!")):
                bad.append("the closing carries no punctuation mark (Mit freundlichen Grüßen)")
        elif loc == "es-ES":
            # Real Academia Española, Puntuación de saludos y despedidas en cartas y correos electrónicos: a
            # colon after the salutation, never a comma; a closing with no verb takes a comma before the name
            # (a full stop also stands); one whose sentence the signature completes takes no mark.
            if not sal.endswith(":"):
                bad.append("a Spanish salutation ends with a colon, not a comma (Estimada señora Ferrer:)")
            verb = re.search(r"\b(saluda|saludan|saludo|saludamos|despide|despiden|despido|queda|quedan|quedo|quedamos|reciba|reciban)\b",
                             close.lower()) and not close.lower().startswith(("un ", "saludos"))
            if not verb and not close.endswith((",", ".")):
                bad.append("a closing with no verb ends with a comma (Atentamente,)")
        elif loc == "pl-PL":
            # Poradnia Językowa PWN, Interpunkcja zwrotów adresatywnych oraz pożegnalnych (2021): a comma
            # after the salutation (an exclamation mark also stands), no mark after the closing formula.
            if not sal.endswith((",", "!")):
                bad.append("a Polish salutation ends with a comma (Szanowna Pani Dyrektor,)")
            if close.endswith((",", ".")):
                bad.append("the closing formula carries no punctuation mark (Z poważaniem)")
        elif loc == "it-IT":
            return None, "no Italian authority's rule for the salutation and the closing was found; none is scripted"
        else:
            return None, "no punctuation convention is scripted for %s" % loc
        return (not bad, "; ".join(bad) or "salutation and closing as %s writes them" % loc)
    if rule_id == "LETTER-PAGES":
        if not lt or lt.lay["info"] != "fi":
            return None, "only the Finnish standard page numbers its pages this way"
        if kind == ".docx":
            with zipfile.ZipFile(path) as z:
                heads = " ".join(z.read(n).decode("utf-8", "replace") for n in z.namelist()
                                 if re.fullmatch(r"word/header\d*\.xml", n))
            fields = re.findall(r'w:instr="\s*(PAGE|NUMPAGES)\s*"', heads) + re.findall(r"<w:instrText[^>]*>\s*(PAGE|NUMPAGES)\b", heads)
            ok = "PAGE" in fields and "NUMPAGES" in fields and re.search(r"\(\s*(<[^>]+>\s*)*<w:fldSimple[^>]*NUMPAGES", heads) is not None
            return (ok, "the head carries the page number and the page count, 1 (2)" if ok
                    else "the head has no page number with the page count after it in brackets, 1 (2); build it with letter_create.py")
        info = subprocess.run(["pdfinfo", str(path)], capture_output=True, text=True).stdout
        found = re.search(r"Pages:\s+(\d+)", info)
        pages = int(found.group(1)) if found else 1
        missing = []
        for k in range(1, pages + 1):
            # The number stands in the head: the top 25 mm of the page, right of the middle.
            top = subprocess.run(["pdftotext", "-f", str(k), "-l", str(k), "-x", "300", "-y", "0", "-W", "300", "-H", "71",
                                  str(path), "-"], capture_output=True, text=True).stdout
            if "%d (%d)" % (k, pages) not in norm(top):
                missing.append("%d (%d)" % (k, pages))
        return (not missing, "every page carries its number and the page count, 1 (%d) to %d (%d)" % (pages, pages, pages)
                if not missing else "the head of the page lacks %s" % ", ".join(missing[:4]))
    if rule_id == "LETTER-LANGUAGE":
        here = HERE.parent / "business-letter" / "scripts"
        if str(here) not in sys.path:
            sys.path.insert(0, str(here))
        try:
            import window_letter as wl
            import letter_create as lc
        except ImportError:
            return None, "the letter builder is not beside the check"
        if lt:
            loc = lt.locale
        else:
            loc, _ = letter.language(dict(spec, seller=spec["sender"], buyer=spec["recipient"]))
        sets = {}
        for table in (lc.WORDS, wl.WORDS):
            for tag, words in table.items():
                sets.setdefault(tag, set()).update(v for k, v in words.items() if k != "closing" and "%" not in v)
        for tag, words in letter.COMPANY_WORDS.items():
            sets.setdefault(tag, set()).update(v for k, v in words.items() if v and k not in ("order", "join"))
        own = sets.get(loc, set()) | (sets.get("en-GB", set()) if loc.startswith("en") else set())
        values = norm(json.dumps(spec, ensure_ascii=False))
        foreign = {w for tag, ws in sets.items() if tag != loc for w in ws} - own
        # A foreign label inside one of the letter's own (Swedish Org.nr in Norwegian Org.nr.) is not foreign.
        foreign = {w for w in foreign if not any(w in o for o in own)}
        # "Data" is the date in Italian and Polish and an ordinary word in an English sentence.
        foreign -= {"Data"}
        found = sorted(w for w in foreign if len(w) > 2 and w not in values
                       and re.search(r"(?<![\w-])%s(?![\w-])" % re.escape(w), flat))
        return (not found, "labels in %s throughout" % loc if not found
                else "labels not in %s: %s" % (loc, ", ".join(found[:6])))
    return None, "unknown rule"


if __name__ == "__main__":
    for rule in ("LETTER-DIN5008", "LETTER-COMPANY", "LETTER-PARTS", "LETTER-WINDOW", "LETTER-ADDRESS",
                 "LETTER-DATE", "LETTER-FORM", "LETTER-LANGUAGE", "LETTER-PAGES"):
        print(rule, check(rule, sys.argv[1], {}, "first"))
