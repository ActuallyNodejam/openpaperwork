#!/usr/bin/env python3
"""Page against XML for an EN 16931 invoice: every value on the page traces to the
XML, nothing appears on the page that the XML does not carry, and every mandatory
value reaches the page. Standard library only; pdftotext for the page text.

  python3 einvoice_page.py invoice.pdf invoice.xml

Rules:
  EINV-PAGE-TRACE     every token on the page (numbers, dates, IBAN, VAT ids, codes)
                      appears among the XML's values
  EINV-PAGE-NO-EXTRA  a field label on the page only when the XML carries that data
  EINV-PAGE-COMPLETE  invoice number, dates, currency, parties, lines, totals, the
                      VAT breakdown and the payment account all reach the page
"""


import json
import re
import html
import re
import subprocess
import sys
from pathlib import Path
from xml.etree import ElementTree as ET

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "_shared"))
import doc_amounts  # noqa: E402

# The rule code lives in the skills tree, so a pack's check runs where the pack runs. When this file
# sits in a checkout it can also see the rest of the repository (the library's own check modules load
# these files from here); inside a sandbox only the skills tree is there, and the rules that need
# more say so instead of failing the file.
def _repo_root():
    here = Path(__file__).resolve()
    for parent in here.parents:
        if (parent / "standards/checks").is_dir():
            return parent
    for parent in here.parents:
        if (parent / "skills").is_dir():
            return parent
    return here.parents[2]


ROOT = _repo_root()



UNIT_WORDS = {"pcs", "pce", "pc", "stk", "st", "stck", "piece", "pieces", "unit", "units", "ea"}


IDENTIFIER = re.compile(r"\b[A-Z]{2}\d{2}(?:\s?[A-Z0-9]{4}){2,}\b"      # IBAN
                        r"|\b[A-Z]{2}\d{6,}\b"                  # VAT id
                        r"|\b(?:INV|RE|PO|REF)[-\s]?\d[\w-]*\b"   # document references
                        r"|\b\d{6,}\b", re.I)                  # long digit runs are identifiers


def _page_text(path):
    """The page text with identifiers removed: an IBAN is not a printed figure."""
    raw = _flat_text(path) if "_flat_text" in globals() else None
    if raw is None:
        raw = path.read_text(errors="ignore") if path.suffix != ".pdf" else ""
    return IDENTIFIER.sub(" ", raw)

# The words a credit note goes by on the page, in the languages the pack writes and its neighbours.
CREDIT_WORDS = re.compile(r"gutschrift|rechnungskorrektur|credit note|kreditnota|kreditfaktura|"
                          r"creditnota|creditfactuur|avoir|nota di credito|nota de cr[eé]dito|"
                          r"faktura korygująca|hyvityslasku|adjustment note|note de cr[ée]dit|credit memo|"
                          r"factura rectificativa|korekta", re.I)

LABELS = {
    "delivery address": ("DeliveryTradeParty", "ShipToTradeParty"),
    "notes": ("IncludedNote",),
    "bic": ("BICID",),
    "reference": ("InvoiceReferencedDocument", "BuyerOrderReferencedDocument"),
    "purchase order": ("BuyerOrderReferencedDocument",),
    "order number": ("BuyerOrderReferencedDocument",),
    "discount": ("AppliedTradeAllowanceCharge",),
    "contact": ("DefinedTradeContact",),
    "phone": ("TelephoneUniversalCommunication",),
    "email": ("URIUniversalCommunication",),
}


def page_text(pdf):
    """Read the page by position: words -> lines -> segments split on wide x gaps ->
    segments clustered into columns, so side-by-side blocks never interleave. Returns
    the list of column texts and the whole page text."""
    out = subprocess.run(["pdftotext", "-bbox", str(pdf), "-"], capture_output=True, text=True).stdout
    words = []
    for m in re.finditer(r'<word xMin="([\d.]+)" yMin="([\d.]+)" xMax="([\d.]+)" yMax="([\d.]+)">(.*?)</word>', out):
        words.append((float(m.group(2)), float(m.group(1)), float(m.group(3)), html.unescape(m.group(5))))
    if not words:
        return [], ""
    lines = {}
    for y, x0, x1, t in words:
        lines.setdefault(round(y / 4) * 4, []).append((x0, x1, t))
    segs = []
    for y, ws in sorted(lines.items()):
        ws.sort()
        cur = [ws[0]]
        for a, b in zip(ws, ws[1:]):
            if b[0] - a[1] > 12:
                segs.append((y, cur))
                cur = []
            cur.append(b)
        segs.append((y, cur))
    cols = []
    for y, ws in sorted(segs):
        x0 = ws[0][0]
        parts = []
        for w in ws:
            if parts and parts[-1][-1] in ",." and w[2][:1].isdigit():
                parts[-1] = parts[-1] + w[2]          # 245, and 00 are one number
            else:
                parts.append(w[2])
        seg = " ".join(parts)
        for c in cols:
            if abs(c["x"] - x0) < 24:
                c["parts"].append((y, seg))
                break
        else:
            cols.append({"x": x0, "parts": [(y, seg)]})
    texts = [" ".join(t for _, t in sorted(c["parts"])) for c in cols]
    return texts, " ".join(texts)


def xml_values(path):
    raw = Path(path).read_text()
    root = ET.fromstring(raw)
    values = set()
    for el in root.iter():
        if el.text and el.text.strip():
            values.add(el.text.strip())
    return raw, root, values


def norm(s):
    return re.sub(r"\s+", " ", s).strip()


def money_variants(v):
    out = {v, v.rstrip("0").rstrip("."), v.replace(".", ","), v.replace(".", ",").rstrip("0").rstrip(",")}
    return {o for o in out if o}


def main():
    pdf, xml = sys.argv[1], sys.argv[2]
    columns, page = page_text(pdf)
    raw, root, values = xml_values(xml)
    flat = norm(page)
    flat_ns = re.sub(r"\s+", "", flat)      # an IBAN in groups is one string
    coltexts = [norm(c) for c in columns]
    results = []

    # TRACE: tokens on the page must exist in the XML
    tokens = set(re.findall(r"\d[\d.,]*\d|\d", flat))
    tokens |= set(re.findall(r"[A-Z]{2}\d{6,}", flat))          # VAT ids
    tokens |= set(re.findall(r"[A-Z]{2}\d{2}[A-Z0-9]{10,}", flat))  # IBAN
    missing = [t for t in sorted(tokens) if not any(v in values or v.replace(",", ".") == t.replace(",", ".")
                                            for v in values)]
    results.append(("EINV-PAGE-TRACE", not missing,
                    "all %d tokens trace to the XML" % len(tokens) if not missing
                    else "not in the XML: %s" % ", ".join(missing[:6])))

    # NO-EXTRA: a label only when the XML carries that data
    extra = []
    low = flat.lower()
    for label, hints in LABELS.items():
        if label in low and not any(h in raw for h in hints):
            extra.append(label)
    results.append(("EINV-PAGE-NO-EXTRA", not extra,
                    "no field appears without data" if not extra else "page shows: %s" % ", ".join(extra)))

    # COMPLETE: the mandatory values reach the page
    want = []
    number = root.find(".//{*}ExchangedDocument/{*}ID")
    if number is not None:
        want.append(("invoice number", number.text))
    for tag, label in (("IssueDateTime", "issue date"), ("DueDateDateTime", "due date")):
        el = root.find(".//{*}" + tag)
        if el is not None:
            s = el.find(".//{*}DateTimeString")
            if s is not None and s.text and len(s.text) == 8:
                want.append((label, "%s-%s-%s" % (s.text[:4], s.text[4:6], s.text[6:])))
    for el in root.iter():
        if el.tag.endswith("DueDateDateTime"):
            s = el.find(".//{*}DateTimeString")
            if s is not None and s.text and len(s.text) == 8:
                want.append(("due date", "%s-%s-%s" % (s.text[:4], s.text[4:6], s.text[6:])))
    for name in ("Name",):
        for el in root.findall(".//{*}SellerTradeParty/{*}" + name) + root.findall(".//{*}BuyerTradeParty/{*}" + name):
            want.append(("party name", el.text))
    for el in root.iter():
        if el.tag.endswith("GrandTotalAmount") or el.tag.endswith("TaxBasisTotalAmount") or el.tag.endswith("TaxTotalAmount"):
            if el.text:
                want.append((el.tag.split("}")[-1], el.text))
    iban = root.find(".//{*}PayeePartyCreditorFinancialAccount/{*}IBANID")
    if iban is not None:
        want.append(("IBAN", iban.text))

    def on_page(label, value):
        """The full string, exactly, inside one column's own reading. No prefix fallback."""
        for v in money_variants(value):
            forms = amount_forms(v)
            if (any(f in c for c in coltexts for f in forms)
                    or any(f in flat for f in forms)
                    or any(re.sub(r"\s+", "", f) in flat_ns
                           for f in forms if len(re.sub(r"\s+", "", f)) >= 8)):
                return True
        return False

    absent = [label for label, value in want if value and not on_page(label, value)]
    # An account without an IBAN (a Swedish Bankgiro number) prints with its own hyphens: held by its digits.
    account = root.find(".//{*}PayeePartyCreditorFinancialAccount/{*}ProprietaryID")
    if account is not None and account.text and account.text not in re.sub(r"\D", "", flat):
        absent.append("account")
    results.append(("EINV-PAGE-COMPLETE", not absent,
                    "all %d mandatory values on the page" % len(want) if not absent
                    else "missing from the page: %s" % ", ".join(sorted(set(absent))[:6])))

    failed = 0
    for rule, ok, why in results:
        print(json.dumps({"rule": rule, "passed": ok, "evidence": why}))
        failed += 0 if ok else 1
    return 1 if failed else 0



# ---- the grader entry the file-task runner calls -------------------------------

def amount_forms(v):
    """2150,00, 2.150,00, 1234.56 and 1,234.56: every way one amount may be written."""
    m = re.match(r"^(\d{1,3}(?:[.,]\d{3})+|\d+)([,.])(\d{2})$", v)
    if not m:
        return [v]
    whole, sep, cents = m.groups()
    plain = re.sub(r"[.,]", "", whole)
    other = "." if sep == "," else ","
    grouped_whole, w = "", plain
    while len(w) > 3:
        grouped_whole = other + w[-3:] + grouped_whole
        w = w[:-3]
    spaced = w + grouped_whole.replace(other, " ")
    return list(dict.fromkeys([v, plain + sep + cents, w + grouped_whole + sep + cents,
                               spaced + "," + cents, spaced + "." + cents]))


EXPECTED_VAT_LABEL = {"de-DE": "USt-IdNr.", "en-GB": "VAT ID", "sv-SE": "Momsreg.nr", "da-DK": "Momsnr.", "fr-FR": "N° TVA",
                      "fi-FI": "ALV-tunniste", "nb-NO": "Org.nr.", "nl-NL": "Btw-id", "nl-BE": "Btw-nr.",
                      "fr-BE": "N° TVA", "de-BE": "MwSt.-Nr.", "de-AT": "UID-Nr.", "en-IE": "VAT No.",
                      "es-ES": "NIF", "it-IT": "P. IVA", "pl-PL": "NIP"}
# Other labels a page in the language may give a VAT number: a British seller's page follows VAT Notice
# 700/21 (VAT registration no.), a customer's number is the customer's VAT no.
OTHER_VAT_LABELS = {"en-GB": ("VAT registration no.", "VAT no."), "da-DK": ("CVR-nr.",), "nb-NO": ("MVA",)}
REVERSE_WORDS = re.compile(r"steuerschuldnerschaft des leistungsempf|reverse charge|omvänd betalningsskyldighet|"
                           r"omvendt betalingspligt|autoliquidation|btw verlegd|übergang der steuerschuld|"
                           r"verlegging van heffing|inversi[oó]n del sujeto pasivo|inversione contabile|"
                           r"odwrotne obciążenie", re.I)
NATIONAL_CURRENCY = {"SE": "SEK", "DK": "DKK", "PL": "PLN", "CZ": "CZK", "HU": "HUF", "RO": "RON", "NO": "NOK", "GB": "GBP"}
# Sellers whose invoices are pages only, in their own currency; no national-currency mention is owed.
PAGE_ONLY = ("AU", "CA", "US", "NZ")


def vat_label_problems(path, case):
    """Every VAT id on the page carries the label the page's own language uses."""
    _columns, text = page_text(path)
    locale = (case or {}).get("locale") or ""
    if not locale:
        _order, data = order_beside(Path(path).resolve())
        if data is not None:
            locale, _why = locale_of_order(data)
    label = EXPECTED_VAT_LABEL.get(locale)
    if not label:
        return None, None
    bad = []
    labels = [label.lower()] + [x.lower() for x in OTHER_VAT_LABELS.get(locale, ())]
    for vat in dict.fromkeys(re.findall(r"\b[A-Z]{2}[0-9]{8,12}\b", text)):
        for line in text.splitlines():
            if vat in line:
                if not any(x in line.lower() for x in labels):
                    bad.append(vat)
                break
    return bad, label


def locale_of_order(src):
    """The locale the order itself asks for: the same table the page builder uses."""
    table = {"DE": "de-DE", "AT": "de-AT", "DK": "da-DK", "SE": "sv-SE", "GB": "en-GB", "IE": "en-IE", "FR": "fr-FR",
             "NO": "nb-NO", "FI": "fi-FI", "AU": "en-AU", "CA": "en-CA", "US": "en-US", "NL": "nl-NL",
             "ES": "es-ES", "IT": "it-IT", "PL": "pl-PL"}
    known = ("de-DE", "en-GB", "sv-SE", "da-DK", "fr-FR", "nb-NO", "fi-FI", "en-AU", "en-CA", "fr-CA", "en-US",
             "nl-NL", "nl-BE", "fr-BE", "de-BE", "de-AT", "en-IE", "es-ES", "it-IT", "pl-PL")
    named = str(src.get("language") or (src.get("buyer") or {}).get("language") or "").strip().lower()
    if named:
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        import einvoice_ids
        if einvoice_ids.be_dutch_at_home(src.get("seller"), src.get("buyer"), named):
            # The builder's own rule: Flanders writes Dutch to a customer in Belgium (decree of 19 July 1973
            # art. 5 § 1).
            return "nl-BE", "the seller's region in Belgium, Flanders, where an invoice to a customer in Belgium is in Dutch"
        regions = [str(((src.get(p) or {}).get("country")) or "").upper() for p in ("seller", "buyer")]
        speak = [tag for tag in known if tag.lower() == named or tag.split("-")[0] == named.split("-")[0]]
        for region in regions:
            for tag in speak:
                if tag.split("-")[1] == region:
                    return tag, "the customer's language %s" % named
        if speak:
            return speak[0], "the customer's language %s" % named
    for party in ("seller", "buyer"):
        country = str(((src.get(party) or {}).get("country")) or "").upper()
        if country == "BE":
            # A Belgian seller writes its region's language (the page builder reads the same postcode).
            sys.path.insert(0, str(Path(__file__).resolve().parent))
            import einvoice_ids
            tag, region = einvoice_ids.be_region_locale((src.get(party) or {}).get("postcode"))
            return tag, "the %s's region in Belgium, %s" % (party, region)
        if country in table:
            return table[country], "the %s's country %s" % (party, country)
        if country:
            return "en-GB", "the %s's country %s, which the page writes in English" % (party, country)
    return "en-GB", "no country in the order"


def order_beside(path):
    """The order the page was built from: in its folder, or up in the task folder."""
    for base in (path.parent, path.parent.parent, path.parent.parent.parent):
        for candidate in sorted(base.rglob("*.json")):
            # Never an order in a dot folder: `npx skills add` puts the packs in the task folder's .agents/skills/,
            # and their templates are orders for other countries (Cursor run of 2026-11-01, held to Austria).
            if any(part.startswith(".") or part == "node_modules" for part in candidate.relative_to(base).parts[:-1]):
                continue
            try:
                data = json.loads(candidate.read_text())
            except Exception:
                continue
            if not isinstance(data, dict) or not data.get("lines"):
                continue
            # The order is the file with the parties country in it: a spec without one cannot say
            # which language the page should be in, and judging the page by it would pass anything.
            if ((data.get("buyer") or {}).get("country") or (data.get("seller") or {}).get("country")):
                return candidate, data
    return None, None


def page_locale(path):
    """The language the page itself is in: the builder writes it on the html element."""
    html = path if path.suffix.lower() in (".html", ".htm") else path.with_suffix(".html")
    if html.is_file():
        found = re.search(r'<html[^>]*\blang="([^"]+)"', html.read_text(errors="ignore"))
        if found:
            return found.group(1)
    return ""


def locale_disagreement(path):
    """Empty when the page is in the order's language, else both locales, or None when unknowable."""
    path = Path(path).resolve()
    _order, data = order_beside(path)
    if data is None:
        return None
    wanted, why = locale_of_order(data)
    got = page_locale(path)
    if not got:
        got = "en-GB" if re.search(r"\bInvoice\b", page_text(path)[1]) else ""
    if not got:
        return None
    if got.split("-")[0] != wanted.split("-")[0]:
        return "the order is %s (%s) and the page is written in %s" % (wanted, why, got)
    return ""



PT_MM = 25.4 / 72
RAW_CODES = re.compile(r"\b(C62|HUR|KGM|MTR|LTR|DAY|H87|XPP|ZZ)\b")


def page_words(pdf):
    """Every word on the first page with its box in millimetres: (x0, y0, x1, y1, text)."""
    out = subprocess.run(["pdftotext", "-bbox", "-f", "1", "-l", "1", str(pdf), "-"],
                         capture_output=True, text=True).stdout
    return [(float(a) * PT_MM, float(b) * PT_MM, float(c) * PT_MM, float(d) * PT_MM, html.unescape(t))
            for a, b, c, d, t in re.findall(
                r'<word xMin="([\d.]+)" yMin="([\d.]+)" xMax="([\d.]+)" yMax="([\d.]+)">(.*?)</word>', out)]


def page_width(pdf):
    """The first page's width in millimetres (210 for A4, 215.9 for Letter)."""
    out = subprocess.run(["pdftotext", "-bbox", "-f", "1", "-l", "1", str(pdf), "-"],
                         capture_output=True, text=True).stdout
    found = re.search(r'<page width="([\d.]+)"', out)
    return float(found.group(1)) * PT_MM if found else 210.0


def din5008_problems(pdf, buyer_name, number=None, lay=None, right_edge=False):
    """A German page against DIN 5008:2020 Form B geometry: the buyer in the window address
    field, the invoice data in the information block, one left edge for the text, amounts set
    flush right, and no raw code where a word belongs. Returns a list of problems.

    lay: a country letter layout (skills/_shared/letter.py LAYOUTS), when the page sits on one: the buyer
    then sits inside that layout's window, the text on its left edge, the information block right of it.

    right_edge: an invoice page keeps everything, the information block included, inside the text's right
    margin, the edge its table ends on (20 mm on Form B, the layout's own otherwise)."""
    words = page_words(pdf)
    if not words:
        return ["no text on the page"]
    problems = []
    if right_edge:
        edge_r = page_width(pdf) - (lay["right"] if lay else 20)
        past = [w for w in words if w[2] > edge_r + 0.5]
        if past:
            far = max(past, key=lambda w: w[2])
            problems.append("%r runs to %.0f mm across, past the text's right edge at %.0f mm, where the table ends"
                            % (far[4], far[2], edge_r))
    first = (buyer_name or "").split()[:1]
    hits = [w for w in words if first and w[4] == first[0]]
    if lay:
        wx, wy, ww, wh = lay["window"]
        c = lay.get("clear") or 0
        edge = lay["left"]
        if not any(wx + c - 0.5 <= w[0] and w[2] <= wx + ww - c + 0.5 and wy + c - 0.5 <= w[1] and w[3] <= wy + wh - c + 0.5
                   for w in hits):
            problems.append("the buyer %r is not inside the %s window (%.0f-%.0f mm across, %.0f-%.0f mm down)"
                            % (buyer_name, lay["name"].split(":")[0], wx + c, wx + ww - c, wy + c, wy + wh - c))
        page_w = (lay.get("page_mm") or (210, 297))[0]
        where = "beside"
        if wx + ww / 2 > page_w / 2:
            # A window on the right (Belgium): the information block is on the left, up to the window.
            beside = [w for w in words if w[2] <= wx - c and wy - 1 <= w[1] <= wy + 50]
        elif lay.get("info") == "above":
            # Where the country's letter writes its reference block above the address (the United States,
            # Canada), the invoice's block is at the top right and ends above the window.
            where = "above"
            beside = [w for w in words if w[0] >= page_w / 2 and w[3] <= wy + 0.5 and w[1] >= 3]
            if any(w[0] >= page_w / 2 and wy + 0.5 < w[3] <= wy + wh and w[0] < wx + ww for w in words):
                problems.append("the information block runs into the %s window" % lay["name"].split(":")[0])
        else:
            info_from = min(124, wx + ww + c + 2)
            beside = [w for w in words if w[0] >= info_from and wy - 1 <= w[1] <= wy + 50]
        if not beside:
            problems.append("nothing in the information block %s the window" % where)
        body_top = max(95, wy + wh)
    else:
        edge = 25
        if not any(20 <= w[0] <= 105 and 62 <= w[1] <= 90 for w in hits):
            problems.append("the buyer %r is not in the address field (20-105 mm across, 62.7-90 mm down)" % buyer_name)
        if not any(w[0] >= 124 and 50 <= w[1] <= 100 for w in words):
            problems.append("nothing in the information block (from 125 mm across, 50 mm down)")
        body_top = 95
    body = [w for w in words if body_top <= w[1] <= 265]
    lines = {}
    for w in body:
        lines.setdefault(round(w[1] / 2), []).append(w)
    # A cell that wraps in the table (a description on two lines) starts under its own column on the
    # line above: that is the table, not a second left edge. The line above is looked for on the whole
    # page, so a value of the information block that wraps across the top of the text (a block left of a
    # Belgian window can run that low) is read as the block's own column too.
    every = {}
    for w in words:
        every.setdefault(round(w[1] / 2), []).append(w)
    keys = sorted(lines)
    def wrapped(i):
        x = min(lines[keys[i]])[0]
        above = [k for k in every if 0 < keys[i] - k <= 4]
        return any(abs(w[0] - x) <= 1.5 for k in above for w in every[k])
    starts = sorted({round(min(lines[k])[0]) for i, k in enumerate(keys)
                     if min(lines[k])[0] < 60 and not (min(lines[k])[0] > edge + 1.5 and wrapped(i))})
    if not starts or abs(starts[0] - edge) > 1.5:
        problems.append("the text does not start on the %g mm edge (first at %s mm)" % (round(edge, 1), (starts[:1] or ["none"])[0]))
    stray = [x for x in starts if edge + 1.5 < x < 60]
    if stray:
        problems.append("more than one left edge in the text: %s mm" % ", ".join(str(x) for x in stray[:4]))
    # Amounts in the table and the totals end on the right edge; a mention written as a sentence
    # (Moms i SEK 6 020,00 SEK) is text, not a column, and is not measured.
    last = [(max(ws, key=lambda w: w[2]), ws) for ws in lines.values() if max(w[2] for w in ws) > 120]
    # A French amount ends in its euro sign (2 970,00 €); a sentence that ends in 40 € is not a column.
    rights = sorted({round(w[2]) for w, ws in last
                     if re.search(r"\d,\d\d", w[4]) or re.search(r"^[£$€]\d[\d,]*\.\d\d$", w[4])
                     or w[4] in ("EUR", "SEK", "USD", "GBP", "CHF", "NOK", "DKK", "AUD", "CAD")
                     or (w[4] in ("€", "$") and any(re.search(r"\d,\d\d$", o[4]) for o in ws))})
    if len(rights) > 1 and max(rights) - min(rights) > 1:
        problems.append("amounts are not flush right on one edge: %s mm" % ", ".join(str(r) for r in rights[:5]))
    codes = sorted({w[4] for w in words if RAW_CODES.fullmatch(w[4])})
    if codes:
        problems.append("a code where a word belongs: %s" % ", ".join(codes))
    return problems


def page_layout(pdf, order):
    """The country letter layout the page claims (its html's layout meta) and the seller's country gives,
    from skills/_shared/letter.py; None for DIN 5008 Form B."""
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "_shared"))
    try:
        import letter
    except ImportError:
        return None
    _lid, lay = letter.letter_layout({"sender": (order or {}).get("seller") or {}, "layout": (order or {}).get("layout")})
    return dict(lay, page_mm=letter.PAPER_MM[lay["paper"]]) if lay else None


# ---- a case whose truth is the order itself -------------------------------------------------------
# The first page case lists what the page shows ("values", "labels"). Every country case is written the
# other way: its truth is the order (seller, buyer, the lines of each stage), the way a person's file gives
# it. The trace rules read that order then: what may be on the page is what the order says and what the
# invoice arithmetic makes of it, and a label may appear when the order carries its data.

# Numbers in the fixed legal sentences the builder itself prints, which no order carries: the French 40 euro
# recovery indemnity and the statutory rate's 10 points (Code de commerce D441-5, L441-10), the date of the
# Italian stamp-duty decree (DM 17 giugno 2014).
BUILDER_NUMBERS = {"FR": ("40", "10"), "IT": ("17", "2014")}


def described_order(case, stage):
    """The order a case describes for a stage, or None when its truth is not an order."""
    t = (case or {}).get("truth") or {}
    staged = t.get(stage or "first")
    order = dict({k: v for k, v in t.items() if k not in ("first", "revision", "page")},
                 **(staged if isinstance(staged, dict) else {}))
    return order if order.get("lines") and isinstance(order.get("seller"), dict) else None


def _date_forms(iso):
    m = re.fullmatch(r"(\d{4})-(\d{2})-(\d{2})", iso)
    if not m:
        return []
    y, mo, d = m.groups()
    days, months = {d, str(int(d))}, {mo, str(int(mo))}
    return [y, iso] + sorted(days | months) + ["%s.%s.%s" % (a, b, y) for a in days for b in months]


def order_truth(order):
    """(values, labels, identifiers) of an order: every number and string it carries, the figures the
    invoice arithmetic derives from them (each line's net, the taxable amount and the tax per rate, the
    totals, the tax in the national currency, a Canadian or US sales tax), each date in the forms a page
    writes it; the labels its data allows; and the digits of its long numbers, which a page may regroup
    (999 999 999, 0123.456.749, +++123/4567/89012+++)."""
    from decimal import Decimal, ROUND_HALF_UP
    r2 = lambda x: Decimal(str(x)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    values, pools = [], []

    def walk(v):
        if isinstance(v, dict):
            for x in v.values():
                walk(x)
        elif isinstance(v, list):
            for x in v:
                walk(x)
        elif isinstance(v, bool) or v is None:
            return
        elif isinstance(v, (int, float)):
            plain = format(Decimal(str(v)).normalize(), "f")
            values.extend([plain, plain.replace(".", ","), "%.2f" % v, ("%.2f" % v).replace(".", ",")])
            whole = plain.split(".")[0].lstrip("-")
            if len(whole) > 3:
                # A whole number printed in groups of three (1 500 units).
                head = len(whole) % 3 or 3
                groups = [whole[:head]] + [whole[i:i + 3] for i in range(head, len(whole), 3)]
                values.extend(groups + [".".join(groups), ",".join(groups)])       # 1 500, 1.500 or 1,500
        else:
            text = str(v)
            values.append(text)
            values.extend(_date_forms(text.strip()))
            digits = re.sub(r"\D", "", text)
            if len(digits) >= 8:
                pools.append(digits)
    walk(order)
    lines = order.get("lines") or []
    net_of = lambda l: doc_amounts.line_amounts(l)["net"]
    figures, groups = [], {}
    for l in lines:
        net = net_of(l)
        full = r2(Decimal(str(l.get("quantity") or 0)) * Decimal(str(l.get("unit_price") or 0)))
        figures += [net, full, full - net]
        key = (str(l.get("vat_category") or "S").upper(), Decimal(str(l.get("vat_rate") or 0)))
        groups[key] = groups.get(key, Decimal(0)) + net
    net_total = sum((net_of(l) for l in lines), Decimal(0))
    if not order.get("taxes"):
        # Allowances on the whole document and an amount paid in advance (EN 16931-1 BG-20, BT-113, BT-115): the
        # page prints their amounts, the sum of lines, the taxable amounts after them and the amount due.
        m = doc_amounts.settle(order, [dict(cat=k[0], rate=k[1], net=b) for k, b in
                                       [((str(l.get("vat_category") or "S").upper(), Decimal(str(l.get("vat_rate") or 0))), net_of(l))
                                        for l in lines]])
        groups = m["groups"]
        net_total = m["basis"]
        figures += [m["line_total"], m["allowance_total"], m["paid"], m["due"]] + [a["amount"] for a in m["allowances"]] \
            + [a["base"] for a in m["allowances"] if a["base"] is not None]
        figures += [Decimal(str(a["percent"])) for a in m["allowances"] if a["percent"] is not None]
    taxed = lambda l: l.get("taxable") is None or (bool(l.get("taxable")) and str(l.get("taxable")).lower()
                                                    not in ("false", "no", "0", "exempt"))
    if order.get("taxes"):
        # Canada and the United States: each tax once on the taxable lines (or on the lines it names).
        base = sum((net_of(l) for l in lines if taxed(l)), Decimal(0))
        taxes = []
        for t in order["taxes"]:
            b = base if not t.get("lines") else sum((net_of(l) for i, l in enumerate(lines, 1) if i in t["lines"]), Decimal(0))
            taxes.append(r2(b * Decimal(str(t.get("rate") or 0)) / 100))
            figures += [b, taxes[-1]]
        tax_total = sum(taxes, Decimal(0))
    else:
        vats = {k: r2(b * k[1] / 100) for k, b in groups.items()}
        tax_total = sum(vats.values(), Decimal(0))
        figures += list(groups.values()) + list(vats.values())
    figures += [net_total, tax_total, net_total + tax_total]
    if order.get("exchange_rate"):
        rate = Decimal(str(order["exchange_rate"]))
        figures += [r2(f * rate) for f in list(figures)]
    for f in figures:
        values.extend([str(r2(f)), str(r2(f)).replace(".", ",")] if f else ["0.00", "0,00"])
    values.extend(BUILDER_NUMBERS.get(str(order["seller"].get("country") or "").upper(), ()))
    pay = order.get("payment") or {}
    contact = order["seller"].get("contact") if isinstance(order["seller"].get("contact"), dict) else {}
    ordered = bool(order.get("order_reference"))
    labels = {"delivery address": bool(order.get("delivery_address")), "notes": bool(order.get("note")),
              "bic": bool(pay.get("bic")),
              "reference": bool(ordered or order.get("preceding_invoice") or order.get("buyer_reference")
                                or pay.get("reference") or pay.get("kid")),
              "purchase order": ordered, "order number": ordered,
              "discount": any(l.get("discount_percent") or l.get("discount_amount") for l in lines) or bool(order.get("allowances"))
                          or bool(order.get("early_payment_discount")),
              "contact": bool(contact.get("name") or order["seller"].get("contact_name")),
              "phone": bool(contact.get("phone") or order["seller"].get("phone")),
              "email": bool(contact.get("email") or order["seller"].get("email"))}
    return values, labels, pools


def check(rule_id, path, case, stage):
    """check(rule_id, path, case, stage) -> (passed, evidence), for grade.py.

    The page is compared against the case's truth for that stage: values that must
    appear, and labels that may appear only when the truth carries that data. A truth
    that is the order itself (a country case) is read as order_truth() reads it.
    """
    if rule_id in ("EINV-FACTURX", "EINV-PDFA", "EINV-KOSIT", "EINV-FR-CTC", "EINV-PEPPOL", "EINV-FINVOICE",
                   "EINV-SI-UBL", "EINV-EBINTERFACE", "EINV-FACTURAE", "EINV-FATTURAPA", "EINV-KSEF"):
        # The file as other systems take it in: the Factur-X PDF and the official validators.
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        import einvoice_external
        return einvoice_external.check(rule_id, path, case, stage)
    if rule_id == "EINV-PARTICULARS":
        # What the seller's own company law puts on its invoice (skills/_checks/einvoice_particulars.py).
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        import einvoice_particulars
        return einvoice_particulars.check(rule_id, path, case, stage)
    truth = case.get("truth") or {}
    if stage and isinstance(truth.get(stage), dict) and "values" in truth[stage]:
        truth = truth[stage]          # a stage can move a date; the revision does
    elif isinstance(truth.get("page"), dict):
        truth = truth["page"]
    values = truth.get("values") or []
    labels_ok = truth.get("labels") or {}
    listed = "values" in truth or "labels" in truth
    order_pools = None
    if not listed and rule_id in ("EINV-PAGE-TRACE", "EINV-PAGE-NO-EXTRA", "EINV-PAGE-COMPLETE"):
        described = described_order(case, stage)
        if described is None:
            return None, "the case's truth neither lists the page's values nor describes an order; nothing to compare"
        values, labels_ok, order_pools = order_truth(described)
    columns, page = page_text(path)
    flat = norm(page)
    coltexts = [norm(c) for c in columns]

    # A unit must reach the page, but its spelling is the page's: C62 is Stk on a German
    # Rechnung and pcs on an English invoice. The loose words in UNIT_WORDS ("st", "unit", "ea")
    # are left out here so a column header cannot stand in for a unit.
    UNIT_ALIASES = ("pcs", "pce", "pc", "stk", "stck", "stueck", "piece", "pieces")

    def on_page(value):
        """The full string, in every written form of an amount, inside one column."""
        if str(value).strip().lower() in UNIT_ALIASES:
            return any(re.search(r"\b%s\b" % w, c, re.I) for c in list(coltexts) + [flat]
                       for w in UNIT_ALIASES)
        for v in money_variants(value):
            forms = amount_forms(str(v))
            if any(f in c for c in coltexts for f in forms) or any(f in flat for f in forms):
                return True
        return False

    if rule_id == "EINV-VAT-LABEL":
        bad, label = vat_label_problems(path, case)
        if bad is None:
            return None, "the locale of this case has no VAT label to check"
        if bad:
            return False, "no label on %s; a page in this language writes %s %s" % (
                ", ".join(bad[:3]), label, bad[0])
        return True, "every VAT id carries its label"

    if rule_id == "EINV-LOCALE-ORDER":
        problem = locale_disagreement(path)
        if problem is None:
            return None, "no order in the folder to compare the page with"
        if problem:
            return False, problem
        return True, "the page is in the order's own language"

    if rule_id == "EINV-PAGE-KIND":
        # A case that grades the XML still owes a page: read the PDF beside it, never the XML as text.
        if Path(path).suffix.lower() == ".xml" and Path(path).with_suffix(".pdf").is_file():
            path = Path(path).with_suffix(".pdf")
            flat = norm(page_text(path)[1])
        _, order = order_beside(Path(path))
        order, full = order or {}, case.get("truth") or {}
        code = str(full.get("type_code") or order.get("type_code") or "").strip()
        preceding = full.get("preceding_invoice") or order.get("preceding_invoice")
        credit = full.get("doc") == "credit_note" or code == "381" or (bool(preceding) and not code)
        if not credit and not preceding:
            return None, "an invoice that corrects nothing; no document type to name"
        problems = []
        if credit and not CREDIT_WORDS.search(flat):
            problems.append("the page never calls itself a credit note")
        if preceding and str(preceding) not in flat:
            problems.append("the invoice it corrects, %s, is not on the page" % preceding)
        return (not problems, "; ".join(problems) or "a credit note naming %s" % preceding)
    if rule_id == "EINV-PAGE-DIN5008":
        pdf = Path(path).with_suffix(".pdf") if Path(path).suffix.lower() != ".pdf" else Path(path)
        if not pdf.is_file():
            return None, "no printed page to measure"
        _, order = order_beside(pdf)
        buyer = ((order or {}).get("buyer") or {}).get("name") or ((case.get("truth") or {}).get("buyer") or {}).get("name") or ""
        lay = page_layout(pdf, order or case.get("truth") or {})
        problems = din5008_problems(pdf, buyer, lay=lay, right_edge=True)
        return (not problems, "; ".join(problems) or ("laid out on %s" % lay["name"] if lay else "laid out on DIN 5008 Form B"))
    if rule_id == "EINV-PAGE-MENTIONS":
        pdf = Path(path).with_suffix(".pdf") if Path(path).suffix.lower() != ".pdf" else Path(path)
        if not pdf.is_file():
            return None, "no printed page to read"
        _, order = order_beside(pdf)
        order = order or {}
        text = norm(page_text(pdf)[1])
        cats = {str(l.get("vat_category") or "S").upper() for l in order.get("lines") or []}
        truth_cat = (case.get("truth") or {}).get("vat_category")
        if isinstance(truth_cat, dict):
            truth_cat = truth_cat.get(stage or "first")
        if truth_cat:
            cats.add(str(truth_cat).upper())
        problems, owed = [], 0
        if "AE" in cats:
            owed += 1
            if not REVERSE_WORDS.search(text):
                problems.append("a reverse-charge invoice without the mention Reverse charge (Art. 226(11a))")
        cur = str(order.get("currency") or "").upper()
        seller_cc = str((order.get("seller") or {}).get("country") or "").upper()
        national = cur if seller_cc in PAGE_ONLY else NATIONAL_CURRENCY.get(seller_cc, "EUR")
        if cur and cur != national and not cats <= {"AE", "E", "K", "G", "Z"}:
            owed += 1
            if national not in text:
                problems.append("an invoice in %s without its VAT in %s (Art. 230)" % (cur, national))
        if not owed:
            return None, "no mention owed: no reverse charge and the national currency"
        return (not problems, "; ".join(problems) or "the mentions the VAT Directive requires are on the page")
    if rule_id == "EINV-PAGE-TRACE":
        allowed = set()
        for v in values:
            for form in amount_forms(norm(v)):
                allowed |= set(re.findall(r"\d[\d.,]*\d|\d", form))
        tokens = set(re.findall(r"\d[\d.,]*\d|\d", IDENTIFIER.sub(" ", flat)))
        extra = sorted(t for t in tokens if t not in allowed and t.rstrip(".") not in allowed)
        if order_pools is not None:
            # A long number of the order printed in groups (an org number, a payment reference) or with
            # points in it is still that number: its digits run inside the number's own.
            regrouped = lambda t: len(re.sub(r"\D", "", t)) >= 2 and any(re.sub(r"\D", "", t) in p for p in order_pools)
            extra = [t for t in extra if not regrouped(t)]
            if extra and Path(path).suffix.lower() == ".pdf":
                # The page reader joins a number to the one after a comma ("Calle 12, 28001 Madrid" reads
                # 12,28001). Where the page itself does not print the token in one piece, it is taken
                # apart again and each part must trace.
                printed = norm(subprocess.run(["pdftotext", "-layout", str(path), "-"], capture_output=True, text=True).stdout)
                parts = lambda t: [x for x in re.split(r"[.,]", t) if x]
                joined = lambda t: t not in printed and len(parts(t)) > 1 and all(
                    x in allowed or regrouped(x) for x in parts(t))
                extra = [t for t in extra if not joined(t)]
        return (not extra, "every number traces to the case data" if not extra
                else "not in the data: %s" % ", ".join(extra[:6]))
    if rule_id == "EINV-PAGE-NO-EXTRA":
        bad = [label for label in LABELS if label in flat.lower() and not labels_ok.get(label)]
        return (not bad, "no field without data" if not bad else "page shows: %s" % ", ".join(bad))
    if rule_id == "EINV-PAGE-COMPLETE":
        if order_pools is not None:
            # An order is not a list of what must be printed (its codes and switches are not): the
            # country's own rule (NO-CONTENT, AT-INVOICE, ES-INVOICE ...) reads what the law asks for.
            return None, "the case describes the order; the seller country's own rule reads what must be on the page"
        missing = [v for v in values if not on_page(v)]
        return (not missing, "every expected value is on the page" if not missing
                else "missing: %s" % ", ".join(missing[:6]))
    return None, "unknown rule"

if __name__ == "__main__":
    sys.exit(main())
