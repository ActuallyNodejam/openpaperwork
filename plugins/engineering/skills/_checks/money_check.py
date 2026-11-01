#!/usr/bin/env python3
"""Money is recomputed wherever it is printed, and a tax rate is a rate its country has.

  TRADE-SUMS  A quotation, an order confirmation and a pro forma invoice: every line is on the page with its
              quantity, unit price and line amount, the line amount is the quantity times the unit price less
              any discount (rounded half up to two decimals), the total excluding VAT is the sum of the line
              amounts, VAT is calculated once per rate on the sum of that rate's lines, and the total including
              VAT is the two added. The arithmetic of EN 16931-1 (business rules BR-CO-10, BR-CO-13, BR-CO-14,
              BR-CO-15 and BR-CO-17, cited by id), which the trade builder follows; on a trade document it is
              this library's own rule. A purchase order has had it since wave 7 (TRADE-PO-LINES,
              TRADE-PO-TOTAL); this rule reads the other priced documents with the same calculator
              (purchase_order_check.expected) and the same reader.
  TRADE-RATE  Every VAT rate on a trade document is a rate the seller's country has (tax_rates.json: the rates
  EINV-RATE   as each country's tax authority or the European Union publishes them, with the source and the day
              it was read), or the buyer's country's for a sale taxed there. A rate written as a fraction (0.2
              where 20 percent is meant) fails. A rate that was in force until a date passes with a question.
              Canada and the United States have no national list and are not checked.
  EINV-SUMS   An invoice page adds up as printed: each line's amount is its quantity times its unit price (less
              the discount the order gives the line), the lines add up to the total without tax, and that
              total and the tax rows add up to the amount due; with one rate on the invoice, the tax is that
              rate of the total without tax. Read from the page the builder wrote, in the page's own number
              forms, so it holds for every country, the ones outside EN 16931 included (Australia, Canada, the
              United States). EN 16931-1 BR-CO-10, BR-CO-13, BR-CO-15 and BR-CO-17, cited by id.

check(rule_id, path, case, stage) -> (passed, evidence); passed is None when the rule does not apply.
A drafting check of sums and rates as printed. It is not tax advice, and it never says which rate a supply takes.
Standard library only.
"""
import html as _html
import json
import re
import sys
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "_shared"))
import doc_amounts  # noqa: E402
TABLE = json.loads((HERE / "tax_rates.json").read_text())
TOL = Decimal("0.006")
PRICED = ("quotation", "order_confirmation", "proforma_invoice")


def r2(x):
    return Decimal(str(x)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def _country(party):
    import letter
    return letter.country_code((party or {}).get("country"))


def _text(d):
    return format(d.normalize(), "f")


# ---- the rate ------------------------------------------------------------------------------------------

def source_of(code):
    entry = TABLE["countries"].get(code) or {}
    return TABLE["sources"].get(entry.get("source"), "")


def rate_problems(lines, seller, buyer=None):
    """(what fails, what is asked about) for the VAT rates of a document's lines."""
    home, away = _country(seller), _country(buyer)
    fails, asks, seen = [], [], set()
    for i, l in enumerate(lines or [], 1):
        if not isinstance(l, dict) or l.get("vat_rate") in (None, ""):
            continue
        try:
            rate = Decimal(str(l["vat_rate"]))
        except InvalidOperation:
            fails.append("line %d: the rate %r is not a number" % (i, l["vat_rate"]))
            continue
        if rate == 0 or rate in seen:
            continue
        seen.add(rate)
        if 0 < rate < 1:
            fails.append("line %d: the rate is written %s, which is %s percent. A rate is a percentage: 20 percent is "
                         "written 20, not 0.2. Write the rate the person's notes give and build again"
                         % (i, _text(rate), _text(rate)))
            continue
        if rate < 0 or rate >= 100:
            fails.append("line %d: %s percent is not a tax rate" % (i, _text(rate)))
            continue
        entry = TABLE["countries"].get(home)
        if not entry:
            continue                       # no national list (Canada, the United States, a country not covered)
        here = {Decimal(str(r)) for r in entry["rates"]}
        there = {Decimal(str(r)) for r in (TABLE["countries"].get(away) or {}).get("rates", [])} if away != home else set()
        if rate in here or rate in there:
            continue
        note = (entry.get("other") or {}).get(_text(rate))
        if note:
            asks.append("line %d: %s percent is %s. Say in your reply which it is" % (i, _text(rate), note))
            continue
        fails.append("line %d: %s percent is not a %s rate of %s, whose rates are %s (%s). Take the rate from the "
                     "person's notes; if the notes give this rate, say so in your reply and name the scheme it "
                     "belongs to. Never pick a rate yourself"
                     % (i, _text(rate), entry["tax"], home, ", ".join(_text(Decimal(str(r))) for r in entry["rates"]),
                        source_of(home)))
    return fails, asks


def _rate_result(fails, asks, ok):
    if fails:
        return False, "; ".join(fails + asks)
    if asks:
        return True, "WARN " + "; ".join(asks)
    return True, ok


# ---- an invoice page as printed ------------------------------------------------------------------------

def _amount(text, decimal):
    """The amount a cell prints, in the page's own number form, or None."""
    t = _html.unescape(re.sub(r"<[^>]+>", " ", text)).replace("−", "-")
    m = re.search(r"\d[\d\s  .,']*", t)
    if not m:
        return None
    tok = m.group(0).rstrip("   .,'")
    if decimal == ",":
        tok = re.sub(r"[\s  .']", "", tok).replace(",", ".")
    else:
        tok = re.sub(r"[\s  ,']", "", tok)
    try:
        value = Decimal(tok)
    except InvalidOperation:
        return None
    return -value if "-" in t[:m.start()] else value


def page_tables(page):
    """(decimal sign, [line cells], [(label, amount text)]) of an invoice page the builder wrote, or None."""
    text = Path(page).read_text(errors="ignore")
    lang = re.search(r'<html[^>]*\blang="([^"]+)"', text)
    # The table of lines is the one whose head row holds column heads (th), with or without a class of its own
    # (the sheet's own wrapper table has none); the totals are the table of class "sum".
    lines = re.search(r"<table(?:\s+class=['\"][\w \-]*['\"])?>\s*<thead>\s*<tr>\s*<th\b.*?</thead>\s*<tbody>(.*?)</tbody>\s*</table>", text, re.S)
    sums = re.search(r"<table\s+class=['\"]sum['\"]>\s*<tbody>(.*?)</tbody>\s*</table>", text, re.S)
    if not (lang and lines and sums):
        return None
    import letter
    decimal = letter._entry(lang.group(1))["number"]["decimal"]
    rows = [re.findall(r"<td[^>]*>(.*?)</td>", r, re.S) for r in re.findall(r"<tr[^>]*>(.*?)</tr>", lines.group(1), re.S)]
    totals = [re.findall(r"<td[^>]*>(.*?)</td>", r, re.S) for r in re.findall(r"<tr[^>]*>(.*?)</tr>", sums.group(1), re.S)]
    return decimal, [r for r in rows if len(r) >= 5], [t for t in totals if len(t) == 2]


def sum_classes(page):
    """The class list of each two-cell row of the totals table, in order (build_page.py marks a row's kind)."""
    text = Path(page).read_text(errors="ignore")
    m = re.search(r"<table\s+class=['\"]sum['\"]>\s*<tbody>(.*?)</tbody>\s*</table>", text, re.S)
    out = []
    for tr in re.finditer(r"<tr([^>]*)>(.*?)</tr>", m.group(1) if m else "", re.S):
        if len(re.findall(r"<td[^>]*>", tr.group(2))) == 2:
            c = re.search(r"class=['\"]([^'\"]*)", tr.group(1))
            out.append(c.group(1).split() if c else [])
    return out


def page_sums(page, order):
    """What does not add up on an invoice page, read as printed."""
    read = page_tables(page)
    if not read:
        return None
    decimal, rows, totals = read
    amt = lambda cell: _amount(cell, decimal)  # noqa: E731
    bad, nets = [], []
    given = [l for l in (order or {}).get("lines") or [] if isinstance(l, dict)]
    same = len(given) == len(rows)
    for i, cells in enumerate(rows):
        net = amt(cells[-1])
        if net is None:
            continue
        nets.append(net)
        src = given[i] if same else {}
        if src.get("net") not in (None, ""):
            continue                           # the order states this line's amount itself
        try:
            # The order's own quantity and price where the page was built from it line for line: a price
            # printed to two decimals hides the rest. Else the figures as printed.
            qty = Decimal(str(src["quantity"])) if src.get("quantity") not in (None, "") else amt(cells[1])
            price = Decimal(str(src["unit_price"])) if src.get("unit_price") not in (None, "") else amt(cells[3])
            discount = Decimal(str(src.get("discount_percent") or 0))
        except InvalidOperation:
            continue
        if qty is None or price is None:
            continue
        # The line's amount is quantity x price less its discount, a percentage and/or an amount (EN 16931-1
        # BG-27, BT-136, BT-138; BR-CO-10 sums them).
        try:
            want = doc_amounts.line_amounts(dict(discount_percent=src.get("discount_percent"),
                                                 discount_amount=src.get("discount_amount"),
                                                 quantity=abs(qty), unit_price=abs(price)), i + 1)["net"]
        except SystemExit as exc:
            bad.append(str(exc))
            continue
        slack = TOL if same else TOL + abs(qty) * Decimal("0.005")
        if abs(abs(net) - want) > slack:
            bad.append("line %d: %s x %s%s is %s; the page prints %s" % (
                i + 1, _text(abs(qty)), _text(abs(price)), (" less %s %%" % _text(discount) if discount else (" less %s" % src.get("discount_amount") if src.get("discount_amount") else "")), want, net))
    if len(totals) < 2 or not nets:
        return bad
    values = [amt(v) for _, v in totals]
    if any(v is None for v in values):
        return bad
    line_sum = sum(nets, Decimal(0))
    cls = sum_classes(page)
    if len(cls) == len(values) and any("net" in c for c in cls):
        # The rows carry their kind (build_page.py): the sum of the lines and the document's allowances when
        # there are any (BR-CO-11, BR-CO-13), the total without tax, the tax rows, the total with tax, and an
        # amount paid in advance with the amount due (BR-CO-15, BR-CO-16).
        by = lambda k: [v for v, c in zip(values, cls) if k in c]  # noqa: E731
        net_total = by("net")[0]
        first = [i for i, c in enumerate(cls) if "net" in c][0]
        totals_at = [i for i, c in enumerate(cls) if "total" in c]
        taxes = [v for v, c in zip(values[first + 1:totals_at[0]], cls[first + 1:totals_at[0]])] if totals_at else []
        total = values[totals_at[0]] if totals_at else None
        allowed = sum(by("allow"), Decimal(0))
        if by("linesum"):
            if abs(line_sum - by("linesum")[0]) > TOL:
                bad.append("the lines add up to %s and the sum of lines reads %s" % (line_sum, by("linesum")[0]))
            if abs(by("linesum")[0] + allowed - net_total) > TOL:
                bad.append("the sum of lines %s less the allowances %s is %s; the total without tax reads %s (BR-CO-13)"
                           % (by("linesum")[0], -allowed, by("linesum")[0] + allowed, net_total))
        elif abs(line_sum - net_total) > TOL:
            bad.append("the lines add up to %s and the total without tax reads %s" % (line_sum, net_total))
        if total is not None and abs(net_total + sum(taxes, Decimal(0)) - total) > TOL:
            bad.append("the total without tax %s and the tax %s add up to %s; the page reads %s"
                       % (net_total, " + ".join(str(t) for t in taxes) or "0", net_total + sum(taxes, Decimal(0)), total))
        if by("due") and total is not None:
            paid = sum((abs(v) for v in by("paid")), Decimal(0))
            if abs(total - paid - by("due")[0]) > TOL:
                bad.append("the total %s less %s paid in advance is %s; the amount due reads %s (BR-CO-16)"
                           % (total, paid, total - paid, by("due")[0]))
        net_total, due = net_total, (by("due") or [total])[0]
        taxes = taxes
    else:
        if len(values) >= 3 and values[-1] == values[-2]:
            values = values[:-1]                   # a total and the same amount again as the balance due
        net_total, due, taxes = values[0], values[-1], values[1:-1]
        if abs(line_sum - net_total) > TOL:
            bad.append("the lines add up to %s and the total without tax reads %s" % (line_sum, net_total))
        if abs(net_total + sum(taxes, Decimal(0)) - due) > TOL:
            bad.append("the total without tax %s and the tax %s add up to %s; the page reads %s"
                       % (net_total, " + ".join(str(t) for t in taxes) or "0", net_total + sum(taxes, Decimal(0)), due))
    rates = set()
    for l in given:
        try:
            if str(l.get("vat_category") or "S").upper() == "S" and l.get("vat_rate") not in (None, ""):
                rates.add(Decimal(str(l["vat_rate"])))
        except InvalidOperation:
            pass
    if same and len(rates) == 1 and len(taxes) == 1 and not (order or {}).get("taxes") \
            and all(str(l.get("vat_category") or "S").upper() == "S" for l in given):
        rate = rates.pop()
        want = r2(abs(net_total) * rate / 100)
        if abs(abs(taxes[0]) - want) > TOL:
            bad.append("the tax reads %s; %s percent of %s is %s" % (taxes[0], _text(rate), net_total, want))
    return bad


# ---- the rules -----------------------------------------------------------------------------------------

def check(rule_id, path, case, stage):
    path = Path(path)
    if rule_id in ("TRADE-SUMS", "TRADE-RATE"):
        import purchase_order_check as po
        import trade_check
        spec = trade_check.spec_of(path, case, stage)
        if not spec:
            return None, "no trade document data file beside the file"
        if spec.get("type") == "delivery_note":
            return None, "a delivery note shows no price"
        if rule_id == "TRADE-RATE":
            fails, asks = rate_problems(spec.get("lines"), spec.get("seller"), spec.get("buyer"))
            return _rate_result(fails, asks, "every VAT rate is a rate the seller's country has")
        if spec.get("type") not in PRICED:
            return None, "a purchase order's sums are read by TRADE-PO-LINES and TRADE-PO-TOTAL"
        try:
            doc = po.Doc(path)
        except (ValueError, OSError) as exc:
            return None, "could not read the file: %s" % str(exc)[:80]
        ok_l, why_l = po.po_lines(doc, spec)
        ok_t, why_t = po.po_total(doc, spec)
        if ok_l and ok_t:
            return True, "%s; %s" % (why_l, why_t)
        return False, ("%s. Every amount is worked out by the builder from the quantities, prices and rates in the "
                       "data file: put the figures of the person's notes there and build again; never type a sum "
                       "into the file" % "; ".join(w for ok, w in ((ok_l, why_l), (ok_t, why_t)) if not ok))
    if rule_id in ("EINV-RATE", "EINV-SUMS"):
        import einvoice_page
        _where, order = einvoice_page.order_beside(path)
        if not order or order.get("type"):
            order = None
        if rule_id == "EINV-RATE":
            if not order:
                return None, "no order beside the page to read the rates from"
            fails, asks = rate_problems(order.get("lines"), order.get("seller"), order.get("buyer"))
            return _rate_result(fails, asks, "every VAT rate is a rate the seller's country has")
        page = path if path.suffix.lower() == ".html" else path.with_suffix(".html")
        if not page.is_file():
            return None, "no page beside %s to read the sums from" % path.name
        bad = page_sums(page, order)
        if bad is None:
            return None, "the page has no table of lines and totals this rule can read"
        if not bad:
            return True, "the page adds up as printed: lines, total without tax, tax and amount due"
        return False, ("%s. The builder works every amount out from the order's quantities, prices and rates: put "
                       "the figures of the person's notes in the order and build again; never edit a sum on the page"
                       % "; ".join(bad[:6]))
    return None, "no such rule"
