#!/usr/bin/env python3
"""Checks for a purchase order: the buyer's order to its supplier, carrying the fields of the OASIS UBL 2.1
Order document, printed on the library's business letter as Word, Excel or PDF.

  TRADE-PO-HEAD       It names itself a purchase order with its number, and gives its issue date (UBL
                      cbc:ID and cbc:IssueDate), the buyer and the seller (cac:BuyerCustomerParty,
                      cac:SellerSupplierParty) and the currency of its amounts (cbc:DocumentCurrencyCode).
  TRADE-PO-LINES      Every line is on it with its quantity, unit price and line amount (cac:OrderLine with
                      its Quantity, Price and LineExtensionAmount), and the line amount is the quantity times
                      the unit price less any discount, rounded half up to two decimals.
  TRADE-PO-TOTAL      The total excluding VAT is the sum of the line amounts (cac:AnticipatedMonetaryTotal);
                      where VAT is charged, VAT once per rate on the sum of that rate's lines and the total
                      including VAT.
  TRADE-PO-DELIVERY   The requested delivery date and the delivery address are on it (cac:Delivery with its
                      RequestedDeliveryPeriod and DeliveryAddress).
  TRADE-PO-INCOTERMS  When the goods cross a border, the delivery term is an Incoterms 2020 rule followed by a
                      named place and the words Incoterms 2020 (cac:DeliveryTerms), the one the parties
                      agreed; FAS, FOB, CFR and CIF only for goods that go by sea.
  TRADE-PO-QUOTE      When the order answers a quotation, it names the quotation's number
                      (cac:QuotationDocumentReference).
  TRADE-INCOTERMS     Any other trade document whose spec agrees a delivery term prints it as the rule, its
                      named place and Incoterms 2020 (ICC Incoterms 2020, INCO-1).

check(rule_id, path, case, stage) -> (passed, evidence); passed is None when the rule does not apply: the
file is not a purchase order, the goods stay in one country, or no quotation is answered. What the
order should say comes from the case's truth when it describes a purchase order, else from the spec beside
the file ("type": "purchase_order"). Standard library only; pdftotext reads a PDF.

A drafting check of what the order states. It never picks a delivery term, a price or a date for the
person, and it is not legal or tax advice.
"""
import json
import re
import subprocess
import sys
import zipfile
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from pathlib import Path
from xml.etree import ElementTree as ET

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "_shared"))
import doc_amounts  # noqa: E402

W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
S = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
TOL = Decimal("0.006")
RULES_ANY = ("EXW", "FCA", "CPT", "CIP", "DAP", "DPU", "DDP")
RULES_SEA = ("FAS", "FOB", "CFR", "CIF")
OLD_RULES = ("DAT", "DAF", "DES", "DEQ", "DDU")
PO_WORDS = re.compile(r"purchase\s+order|bestellung|inköpsorder|beställning|indkøbsordre|bestilling|innkjøpsordre|"
                      r"ostotilau|bon de commande|inkooporder|pedido de compra|orden de compra|ordine d'acquisto|"
                      r"zamówieni", re.I)
DELIVER_WORDS = re.compile(r"deliver(y)?\s+(to|address)|lieferanschrift|lieferadresse|leveransadress|"
                           r"leveringsadresse|leverera till|levering til|toimitusosoite|adresse de livraison|ship to|"
                           r"afleveradres|dirección de entrega|indirizzo di consegna|adres dostawy", re.I)
QUOTE_LABEL = re.compile(r"quot|angebot|offert|tilbud|tarjou|soumission|presupuesto|preventivo|ofert", re.I)
MONTHS = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October",
          "November", "December"]
COUNTRY_NAMES = {"germany": "DE", "deutschland": "DE", "austria": "AT", "österreich": "AT", "sweden": "SE",
                 "sverige": "SE", "denmark": "DK", "danmark": "DK", "united kingdom": "GB", "uk": "GB",
                 "great britain": "GB", "england": "GB", "ireland": "IE", "france": "FR", "netherlands": "NL",
                 "norway": "NO", "norge": "NO", "finland": "FI", "italy": "IT", "spain": "ES", "poland": "PL",
                 "belgium": "BE", "switzerland": "CH", "schweiz": "CH", "czech republic": "CZ", "czechia": "CZ",
                 "estonia": "EE", "latvia": "LV", "lithuania": "LT", "portugal": "PT", "united states": "US",
                 "usa": "US", "suomi": "FI", "canada": "CA", "australia": "AU", "españa": "ES", "espana": "ES",
                 "italia": "IT", "polska": "PL", "nederland": "NL", "belgië": "BE", "belgique": "BE", "éire": "IE"}


def r2(x):
    return Decimal(str(x)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def squash(s):
    return re.sub(r"[\s  ]+", " ", s).strip()


def country_code(value):
    s = str(value or "").strip()
    if len(s) == 2 and s.isalpha():
        return s.upper()
    return COUNTRY_NAMES.get(s.lower(), "")


# ---- reading the document --------------------------------------------------------------------

def _parse_one(t):
    t = t.strip(".,'")
    if not t:
        return set()
    if "," in t and "." in t:
        forms = {t.replace(",", "") if t.rfind(".") > t.rfind(",") else t.replace(".", "").replace(",", ".")}
    elif "," in t:
        forms = {t.replace(",", ".") if re.search(r",\d{1,2}$", t) else t.replace(",", ""), t.replace(",", "")}
    elif t.count(".") > 1:
        forms = {t.replace(".", "")}
    elif re.fullmatch(r"\d{1,3}\.\d{3}", t):
        # 4.000 is four thousand where a point groups the thousands (German, Dutch, Spanish, Italian) and
        # four where it is the decimal sign: both readings, as a comma gets above.
        forms = {t, t.replace(".", "")}
    else:
        forms = {t}
    out = set()
    for f in forms:
        try:
            out.add(Decimal(f))
        except InvalidOperation:
            pass
    return out


def numbers(text):
    """Every amount a piece of text can be read as: 1 234,50, 1.234,50 and 1,234.50 all give 1234.50."""
    out = set()
    for tok in re.findall(r"\d[\d   .,']*", text):
        parts = [x for x in re.split(r"[   ']+", tok) if x.strip(".,")]
        for i, part in enumerate(parts):
            out |= _parse_one(part)
            if re.fullmatch(r"\d{1,3}", part):          # a space as the thousands separator: 38 500,00
                joined, j = part, i + 1
                while j < len(parts) and re.fullmatch(r"\d{3}(?:[.,]\d+)?[.,]?", parts[j]):
                    joined += parts[j]
                    out |= _parse_one(joined)
                    if not parts[j].isdigit():
                        break
                    j += 1
    return out


def has(nums, value):
    value = Decimal(str(value))
    return any(abs(n - value) <= TOL for n in nums)


class Doc:
    """rows: one string per table row, paragraph, sheet row or text line, in reading order."""

    def __init__(self, path):
        path = Path(path)
        self.kind = path.suffix.lower().lstrip(".")
        self.rows, self.title = [], ""
        if self.kind == "docx":
            with zipfile.ZipFile(path) as z:
                names = z.namelist()
                parts = ["word/document.xml"] + sorted(n for n in names if re.fullmatch(r"word/(header|footer)\d*\.xml", n))
                for part in parts:
                    self._docx(ET.fromstring(z.read(part)))
                if "docProps/core.xml" in names:
                    m = re.search(r"<dc:title>(.*?)</dc:title>", z.read("docProps/core.xml").decode("utf-8", "replace"), re.S)
                    self.title = m.group(1) if m else ""
        elif self.kind == "xlsx":
            self._xlsx(path)
        elif self.kind == "pdf":
            p = subprocess.run(["pdftotext", "-layout", str(path), "-"], capture_output=True, text=True, timeout=120)
            if p.returncode:
                raise ValueError("not a readable PDF: %s" % p.stderr.strip()[:120])
            self.rows = [re.sub(r" {2,}", " | ", l.strip()) for l in p.stdout.splitlines() if l.strip()]
            info = subprocess.run(["pdfinfo", str(path)], capture_output=True, text=True).stdout
            m = re.search(r"^Title:\s*(.*)$", info, re.M)
            self.title = m.group(1).strip() if m else ""
        else:
            raise ValueError("a %s is not a document this check reads" % path.suffix)
        self.rows = [squash(r) for r in self.rows if squash(r)]
        self.flat = " \n ".join(self.rows)
        self.nums = numbers(self.flat)

    def _docx(self, root):
        body = root.find(W + "body") if root.find(W + "body") is not None else root

        def para(p):
            return "".join(t.text or "" if t.tag == W + "t" else " " for t in p.iter() if t.tag in (W + "t", W + "tab", W + "br"))

        def walk(el):
            for child in el:
                if child.tag == W + "p":
                    self.rows.append(para(child))
                elif child.tag == W + "tbl":
                    for tr in child.findall(W + "tr"):
                        self.rows.append(" | ".join(" ".join(para(p) for p in tc.iter(W + "p")) for tc in tr.findall(W + "tc")))
                elif child.tag in (W + "sdt", W + "sdtContent"):
                    walk(child)
        walk(body)

    def _xlsx(self, path):
        with zipfile.ZipFile(path) as z:
            names = z.namelist()
            shared = []
            if "xl/sharedStrings.xml" in names:
                for si in ET.fromstring(z.read("xl/sharedStrings.xml")).findall(S + "si"):
                    shared.append("".join(t.text or "" for t in si.iter(S + "t")))
            if "docProps/core.xml" in names:
                m = re.search(r"<dc:title>(.*?)</dc:title>", z.read("docProps/core.xml").decode("utf-8", "replace"), re.S)
                self.title = m.group(1) if m else ""
            for sheet in sorted(n for n in names if re.fullmatch(r"xl/worksheets/sheet\d+\.xml", n)):
                for row in ET.fromstring(z.read(sheet)).iter(S + "row"):
                    cells = []
                    for c in row.findall(S + "c"):
                        kind, v = c.get("t"), c.find(S + "v")
                        if kind == "s" and v is not None:
                            cells.append(shared[int(v.text)])
                        elif kind == "inlineStr":
                            cells.append("".join(t.text or "" for t in c.iter(S + "t")))
                        elif v is not None and v.text is not None:
                            cells.append(v.text)       # a formula's saved result is its value
                    if cells:
                        self.rows.append(" | ".join(cells))

    def rows_with(self, needle):
        return [(i, r) for i, r in enumerate(self.rows) if needle.lower() in r.lower()]


def date_forms(iso):
    y, m, d = (int(x) for x in iso.split("-"))
    mon = MONTHS[m - 1]
    return [iso, "%02d.%02d.%d" % (d, m, y), "%d.%d.%d" % (d, m, y), "%d.%02d.%d" % (d, m, y),      # 5.03.2026: Polish
            "%02d/%02d/%d" % (d, m, y), "%d/%d/%d" % (d, m, y),
            "%02d-%02d-%d" % (d, m, y), "%d %s %d" % (d, mon, y), "%d %s %d" % (d, mon[:3], y), "%s %d, %d" % (mon, d, y)]


def has_date(doc, iso):
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", str(iso or "")):
        return bool(iso) and str(iso).lower() in doc.flat.lower()
    low = doc.flat.lower()
    return any(f.lower() in low for f in date_forms(iso))


# ---- what the order should say ----------------------------------------------------------------

def spec_beside(path):
    path = Path(path).resolve()
    for base in (path.parent, path.parent.parent):
        for p in sorted(base.glob("*.json")):
            try:
                data = json.loads(p.read_text())
            except (ValueError, OSError):
                continue
            if isinstance(data, dict) and data.get("type") == "purchase_order" and data.get("lines"):
                return data
    return None


def order_data(path, case, stage):
    t = (case or {}).get("truth") or {}
    if t.get("doc") == "purchase_order" or t.get("type") == "purchase_order":
        staged = t.get(stage or "first")
        return dict({k: v for k, v in t.items() if k not in ("first", "revision")},
                    **(staged if isinstance(staged, dict) else {}))
    return spec_beside(path)


def expected(data):
    """(lines, vat per rate, total without VAT, VAT, total with VAT): a line is quantity x price less its
    discount, the allowances on the document come off the taxable amounts (EN 16931-1 BG-27, BG-20, BR-CO-13,
    BR-CO-15); skills/_shared/doc_amounts.py is the one calculator."""
    lines = []
    for i, l in enumerate(data.get("lines") or [], 1):
        a = doc_amounts.line_amounts(dict(l, unit_price=l.get("unit_price", 0)), i)
        lines.append(dict(l, net=a["net"], disc=a["discount"], rate=Decimal(str(l.get("vat_rate") or 0))))
    m = doc_amounts.settle(data, [dict(cat="S", rate=l["rate"], net=l["net"]) for l in lines])
    vat = {rate: (m["groups"][("S", rate)], m["tax"][("S", rate)]) for rate in {l["rate"] for l in lines}}
    return lines, vat, m["basis"], m["tax_total"], m["grand"]


def settlement(data):
    """The settlement of doc_amounts for the data file: sum of lines, allowances, amount paid, amount due."""
    lines = [dict(cat="S", rate=Decimal(str(l.get("vat_rate") or 0)),
                  net=doc_amounts.line_amounts(dict(l, unit_price=l.get("unit_price", 0)))["net"])
             for l in data.get("lines") or []]
    return doc_amounts.settle(data, lines)


def line_rows(doc, l):
    rows = doc.rows_with(l["code"]) if l.get("code") else []
    if not rows:
        rows = doc.rows_with(" ".join(str(l.get("description") or l.get("name") or "").split()[:3]))
    if not rows and doc.kind == "pdf":
        # A description the PDF wraps (a discount column narrows it): the row its first word is on, when that
        # row and the two under it carry the next words.
        want = [w.lower() for w in str(l.get("description") or l.get("name") or "").split()[:3]]
        for i, r in enumerate(doc.rows):
            if want and want[0] in r.lower() and all(w in " ".join(doc.rows[i:i + 3]).lower() for w in want):
                rows = [(i, r)]
                break
    out = []
    for i, r in rows:
        nxt = doc.rows[i + 1] if doc.kind == "pdf" and i + 1 < len(doc.rows) else ""
        out.append((i, r + " " + nxt))
    return out


def fails(bad, ok):
    return (not bad), (ok if not bad else "; ".join(bad[:6]) + (" (+%d more)" % (len(bad) - 6) if len(bad) > 6 else ""))


# ---- the rules -------------------------------------------------------------------------------

def po_head(doc, t):
    bad = []
    number = str(t.get("number") or "")
    if not number:
        bad.append("the order data gives no purchase order number")
    elif not any(PO_WORDS.search(r) and number.lower() in r.lower() for r in doc.rows + [doc.title]):
        bad.append("nothing names it a purchase order with its number %s" % number)
    if t.get("issue_date") and not has_date(doc, t["issue_date"]):
        bad.append("issue date %s missing" % t["issue_date"])
    for role in ("buyer", "seller"):
        name = (t.get(role) or {}).get("name")
        if not name:
            bad.append("the order data gives no %s" % role)
        elif name.lower() not in doc.flat.lower():
            bad.append("%s %r missing" % (role, name))
    cur = t.get("currency")
    if not cur:
        bad.append("the order data gives no currency")
    elif not re.search(r"\b%s\b" % re.escape(cur), doc.flat):
        bad.append("currency %s not stated" % cur)
    return fails(bad, "a purchase order %s of %s from %s to %s in %s" % (
        number, t.get("issue_date"), (t.get("buyer") or {}).get("name"), (t.get("seller") or {}).get("name"), cur))


def po_lines(doc, t):
    try:
        lines = expected(t)[0]
    except SystemExit as exc:
        return False, "the amounts do not close: %s" % exc
    if not lines:
        return False, "the order has no lines"
    bad = []
    for l in lines:
        name = l.get("code") or str(l.get("description") or l.get("name"))[:25]
        rows = line_rows(doc, l)
        if not rows:
            bad.append("line %s missing" % name)
            continue
        want = [("quantity", l["quantity"]), ("unit price", l.get("unit_price", 0)), ("line amount", l["net"])]
        missing = []
        for _, r in rows:
            nums = numbers(r.replace(l.get("code") or "\0", " "))
            missing = [k for k, v in want if not has(nums, v)]
            if not missing:
                break
        if missing:
            bad.append("line %s: %s not on its row (quantity %s x unit price %s%s = %s)" % (
                name, ", ".join(missing), l["quantity"], l.get("unit_price", 0),
                (" less %s %%" % l.get("discount_percent") if l.get("discount_percent") else
                 " less %s" % l.get("discount_amount") if l.get("discount_amount") else ""), l["net"]))
    return fails(bad, "%d lines, each quantity x unit price = its amount" % len(lines))


def po_total(doc, t):
    try:
        lines, vat, net, tax, gross = expected(t)
        m = settlement(t)
    except SystemExit as exc:
        return False, "the amounts do not close: %s" % exc
    bad = []
    for n, al in enumerate(m["allowances"], 1):
        if not has(doc.nums, al["amount"]):
            bad.append("allowance %d (%s) of %s not stated" % (n, al["reason"] or al["code"], al["amount"]))
    if m["allowances"] and not has(doc.nums, m["line_total"]):
        bad.append("the sum of the lines %s not stated (EN 16931-1 BT-106)" % m["line_total"])
    if m["paid"]:
        if not has(doc.nums, m["paid"]):
            bad.append("the amount paid in advance %s not stated (BT-113)" % m["paid"])
        if not has(doc.nums, m["due"]):
            bad.append("the amount due %s (the total %s less %s paid) not stated (BT-115, BR-CO-16)" % (m["due"], gross, m["paid"]))
    if not has(doc.nums, net):
        bad.append("total excluding VAT %s (the sum of the line amounts) not stated" % net)
    for rate, (base, amount) in sorted(vat.items(), reverse=True):
        if rate > 0 and not has(doc.nums, amount):
            bad.append("VAT %s %% on %s = %s not stated" % (rate.normalize(), base, amount))
    if tax > 0 and not has(doc.nums, gross):
        bad.append("total including VAT %s not stated" % gross)
    return fails(bad, "total %s, the sum of the lines%s" % (net, "; VAT %s, %s with VAT" % (tax, gross) if tax else ""))


def po_delivery(doc, t):
    bad = []
    when = t.get("requested_delivery_date")
    if not when:
        bad.append("the order data gives no requested delivery date (UBL Delivery/RequestedDeliveryPeriod); "
                   "ask the person for it")
    elif not has_date(doc, when):
        bad.append("requested delivery date %s missing" % when)
    where = t.get("deliver_to") or t.get("buyer") or {}
    city = str(where.get("city") or "")
    labelled = [i for i, r in enumerate(doc.rows) if DELIVER_WORDS.search(r)]
    if not city:
        bad.append("the order data gives no delivery address")
    elif not any(city.lower() in " ".join(doc.rows[i:i + 3]).lower() for i in labelled):
        bad.append("no delivery address with %s under a delivery label" % city)
    elif where.get("street") and str(where["street"]).lower() not in doc.flat.lower():
        bad.append("delivery street %s missing" % where["street"])
    return fails(bad, "requested for %s, delivered to %s" % (when, ", ".join(x for x in (where.get("street"), city) if x)))


def po_incoterms(doc, t):
    seller = country_code((t.get("seller") or {}).get("country"))
    dest = country_code((t.get("deliver_to") or {}).get("country")) or country_code((t.get("buyer") or {}).get("country"))
    if not seller or not dest:
        return None, "the order data does not give both countries, so it cannot tell whether the goods cross a border"
    if seller == dest:
        return None, "the goods stay in %s; no Incoterms rule is owed" % seller
    term = t.get("delivery_terms") or t.get("incoterm") or {}
    m = re.search(r"\b(%s)\b[\s,:(-]*([^|\n]{2,70}?)[\s,;(-]*Incoterms\s?[®(R)]{0,3}\s?2020" % "|".join(RULES_ANY + RULES_SEA), doc.flat)
    if not m:
        found = re.findall(r"\b(?:%s)\b[^|\n]{0,50}" % "|".join(RULES_ANY + RULES_SEA + OLD_RULES), doc.flat)
        if not term:
            # A delivery term is the person's agreement: the file is handed back without one and the reply says so.
            return True, ("WARN the goods go from %s to %s and the order states no delivery term: an Incoterms 2020 rule and "
                          "a named place are the person's to agree with the supplier, never picked for them; say in your "
                          "reply that the order does not give one" % (seller, dest))
        return False, 'expected "%s %s, Incoterms 2020"; found %r' % (
            str(term.get("rule", "")).upper(), term.get("place"), [f[:60] for f in found[:3]] or "no delivery term")
    rule, place = m.group(1), m.group(2)
    bad = []
    old = [r for r in OLD_RULES if re.search(r"\b%s\b" % r, doc.flat)]
    if old:
        bad.append("%s is not an Incoterms 2020 rule" % ", ".join(old))
    if term:
        if str(term.get("rule", "")).upper() != rule:
            bad.append("the term reads %s, the agreed rule is %s" % (rule, str(term.get("rule", "")).upper()))
        if term.get("place") and str(term["place"]).split(",")[0].strip().lower() not in place.lower():
            bad.append("named place %s missing after %s" % (term["place"], rule))
    if rule in RULES_SEA and str(t.get("transport") or "road") not in ("sea", "inland waterway"):
        bad.append("%s is for sea and inland waterway only; these goods go by %s" % (rule, t.get("transport") or "road"))
    return fails(bad, "%s to %s: %s" % (seller, dest, m.group(0)[:80]))


def quotation_of(t):
    if t.get("quotation"):
        return str(t["quotation"])
    for r in t.get("references") or []:
        if isinstance(r, dict) and QUOTE_LABEL.search(str(r.get("label") or "")):
            return str(r.get("value") or "")
    return ""


def po_quote(doc, t):
    number = quotation_of(t)
    if not number:
        return None, "the order answers no quotation"
    if number.lower() not in doc.flat.lower():
        return False, "the quotation %s the order answers is not named on it" % number
    return True, "names quotation %s" % number


RULES = {"TRADE-PO-HEAD": po_head, "TRADE-PO-LINES": po_lines, "TRADE-PO-TOTAL": po_total,
         "TRADE-PO-DELIVERY": po_delivery, "TRADE-PO-INCOTERMS": po_incoterms, "TRADE-PO-QUOTE": po_quote}


def any_incoterms(path, case, stage):
    """TRADE-INCOTERMS: a quotation, order confirmation, pro forma or delivery note whose spec agrees a delivery
    term prints it as the builder does, the rule followed by its named place and "Incoterms 2020" (ICC
    Incoterms 2020, INCO-1). The builder never writes one without a place; this catches the page that lost it
    after. A purchase order has its own rule, TRADE-PO-INCOTERMS."""
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import trade_check
    if order_data(path, case, stage):
        return None, "a purchase order: TRADE-PO-INCOTERMS checks its delivery term"
    spec = trade_check.spec_of(path, case, stage) or {}
    term = spec.get("delivery_terms") or {}
    rule = str(term.get("rule") or "").upper()
    if not rule:
        return None, "the document agrees no delivery term"
    try:
        doc = Doc(path)
    except (OSError, ValueError, KeyError, zipfile.BadZipFile, ET.ParseError) as e:
        return False, "unreadable file: %s" % e
    place = str(term.get("place") or "").split(",")[0].strip()
    m = re.search(r"\b%s\b[\s,:(-]*([^|\n]{0,70}?)[\s,;(-]*Incoterms\s?[®(R)]{0,3}\s?2020" % re.escape(rule), doc.flat)
    if not m:
        return False, 'expected "%s %s, Incoterms 2020" on the page; no %s term with its year was found' % (rule, place, rule)
    if not m.group(1).strip(" ,;"):
        return False, "%s has no named place before Incoterms 2020; the agreed place is %s" % (rule, place or "not given")
    if place and place.lower() not in m.group(1).lower():
        return False, "%s names %r, the agreed place is %s" % (rule, m.group(1).strip(" ,;"), place)
    return True, m.group(0)[:80]


def check(rule_id, path, case, stage):
    if rule_id == "TRADE-INCOTERMS":
        return any_incoterms(path, case, stage)
    if rule_id in ("TRADE-LANG", "TRADE-BLOCK", "TRADE-WINDOW"):
        # Any trade document's labels and page, not only a purchase order's: its own module (trade_check.py).
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        import trade_check
        return trade_check.check(rule_id, path, case, stage)
    if rule_id not in RULES:
        return None, "unknown rule %s" % rule_id
    data = order_data(path, case, stage)
    if not data:
        return None, "not a purchase order: no purchase order spec beside the file"
    try:
        doc = Doc(path)
    except (OSError, ValueError, KeyError, zipfile.BadZipFile, ET.ParseError) as e:
        return False, "unreadable file: %s" % e
    try:
        return RULES[rule_id](doc, data)
    except (KeyError, InvalidOperation, ValueError) as e:
        return False, "the order data is incomplete: %s" % e


if __name__ == "__main__":
    for rule in RULES:
        ok, why = check(rule, sys.argv[1], {}, "first")
        print(json.dumps({"rule": rule, "passed": ok, "evidence": why}, ensure_ascii=False))
