#!/usr/bin/env python3
"""One way to work out a priced document's money: line discounts, document-level allowances, VAT, the amount
already paid and the amount due. The invoice builders (every XML syntax and the page), the trade-document
builder and the sums checks all read it, so the figures cannot drift apart.

The terms are EN 16931-1 (the European standard for the core invoice; the business term numbers are cited
here, the wording is our own):
  line discount     BG-27 line allowance: BT-136 the amount, BT-137 the amount it is worked out from, BT-138 the
                    percentage, BT-139 the reason. The order's line says "discount_percent" and/or
                    "discount_amount" (and "discount_reason").
  allowance         BG-20 allowance on the whole document: BT-92 amount, BT-93 base, BT-94 percentage, BT-95 VAT
                    category, BT-96 VAT rate, BT-97 reason. The order's "allowances" list.
  paid in advance   BT-113 paid amount; the order's "paid_amount" (and "paid_note", text for the page).
  amount due        BT-115 = grand total (BT-112) less the paid amount (BR-CO-16).
The arithmetic is BR-CO-10 (sum of line nets), BR-CO-11/12 (sums of allowances and charges), BR-CO-13 (total
without VAT = lines - allowances + charges), BR-CO-15 (total with VAT) and BR-CO-16 (amount due); cited by id.

Rounding: a line's amount is quantity x price, rounded half up to two decimals, less its discount. A discount
given as a percentage is the difference between that amount and the amount worked out with the percentage taken
off, so a line always closes to the cent. A discount given as an amount and a percentage together must agree.
Standard library only.
"""
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

CENT = Decimal("0.01")


def dec(x, what="a number"):
    try:
        return Decimal(str(x))
    except InvalidOperation:
        raise SystemExit("%s is not a number: %r" % (what, x))


def r2(x):
    return Decimal(str(x)).quantize(CENT, rounding=ROUND_HALF_UP)


def given(v):
    return v not in (None, "", [], {})


def line_amounts(l, index=0):
    """{base, discount, percent, net, reason} of one line: BT-137, BT-136, BT-138 (None unless the order gave a percentage) and the line net, with the
    base worked out as quantity x price. A discount that does not close stops the build."""
    where = "line %d" % index if index else "a line"
    x = dec(l.get("quantity") or 0, where + " quantity") * dec(l.get("unit_price") or 0, where + " unit_price")
    base = r2(x)
    pct = dec(l.get("discount_percent") or 0, where + " discount_percent")
    amt = l.get("discount_amount")
    if pct < 0 or pct > 100:
        raise SystemExit("%s: discount_percent %s is not between 0 and 100" % (where, pct))
    by_pct = base - r2(x * (1 - pct / 100))
    if given(amt):
        amt = r2(dec(amt, where + " discount_amount"))
        if amt < 0 or (base >= 0 and amt > base) or (base < 0 and -amt < base):
            raise SystemExit("%s: discount_amount %s is outside the line's amount %s (EN 16931-1 BR-41, BT-136)"
                             % (where, amt, base))
        if base < 0:
            amt = -amt
        if pct and abs(amt - by_pct) > CENT:
            raise SystemExit("%s: discount_percent %s of %s is %s but discount_amount is %s; the discount does not "
                             "close (BT-136, BT-138). Give one, or make them agree" % (where, pct, base, by_pct, amt))
        disc = amt
    else:
        disc = by_pct
    return dict(base=base, discount=disc, percent=pct if (disc and pct) else None, net=base - disc,
                reason=(l.get("discount_reason") or "").strip())


def settle(spec, lines, default_cat="S", where="the order"):
    """The money of a document. lines: [{"cat", "rate", "net"}] with Decimal nets, one per line, as the builder
    holds them. Returns a dict:
      groups     {(cat, rate): taxable amount after allowances}      (BT-116)
      tax        {(cat, rate): VAT}                                   (BT-117)
      allowances [{amount, base, percent, reason, code, cat, rate}]    (BG-20)
      line_total (BT-106), allowance_total (BT-107), basis (BT-109), tax_total (BT-110), grand (BT-112),
      paid (BT-113), due (BT-115)."""
    groups = {}
    for l in lines:
        key = (l["cat"], l["rate"])
        groups[key] = groups.get(key, Decimal(0)) + l["net"]
    line_total = sum((l["net"] for l in lines), Decimal(0))
    allowances = []
    raw = spec.get("allowances")
    if given(raw) and not isinstance(raw, list):
        raise SystemExit('"allowances" is a list of {"amount", "reason", "vat_rate"} (EN 16931-1 BG-20)')
    for n, a in enumerate(raw or [], 1):
        if not isinstance(a, dict):
            raise SystemExit('allowance %d: give an object {"amount": ..., "reason": ..., "vat_rate": ...}' % n)
        cat = str(a.get("vat_category") or "").upper() or None
        rate = a.get("vat_rate")
        if cat is None or not given(rate):
            options = [k for k in groups if (cat is None or k[0] == cat) and (not given(rate) or k[1] == dec(rate))]
            if len(options) != 1:
                raise SystemExit("allowance %d: the lines carry several VAT categories or rates, so the allowance must "
                                 'name its own "vat_rate" (and "vat_category") (EN 16931-1 BT-95, BT-96, BR-S-08)' % n)
            cat, rate = options[0]
        key = (cat, dec(rate))
        if key not in groups:
            raise SystemExit("allowance %d: no line is taxed %s %s%%, so there is nothing to take the allowance off "
                             "(BR-S-08)" % (n, key[0], key[1].normalize()))
        pct = dec(a.get("percent")) if given(a.get("percent")) else None
        base = r2(dec(a["base"], "allowance %d base" % n)) if given(a.get("base")) else (r2(groups[key]) if pct is not None else None)
        if given(a.get("amount")):
            amount = r2(dec(a["amount"], "allowance %d amount" % n))
            if pct is not None and base is not None and abs(r2(base * pct / 100) - amount) > CENT:
                raise SystemExit("allowance %d: %s %% of %s is %s but the amount is %s; the allowance does not close "
                                 "(BT-92, BT-93, BT-94)" % (n, pct.normalize(), base, r2(base * pct / 100), amount))
        elif pct is not None:
            amount = r2(base * pct / 100)
        else:
            raise SystemExit('allowance %d: give its "amount" (BT-92), or a "percent" (BT-94) of its base' % n)
        if amount <= 0:
            raise SystemExit("allowance %d: the amount must be above zero (BT-92); a credit goes in a credit note" % n)
        if pct is None:
            base = None          # a base without a percentage is refused by Peppol (PEPPOL-EN16931-R042)
        reason = (a.get("reason") or "").strip()
        code = str(a.get("reason_code") or "").strip()
        if not reason and not code:
            raise SystemExit("allowance %d: a reason (BT-97) or a reason code (BT-98) is required (BR-33)" % n)
        groups[key] -= amount
        if groups[key] < 0:
            raise SystemExit("allowance %d: more than the lines of that rate add up to" % n)
        allowances.append(dict(amount=amount, base=base, percent=pct, reason=reason, code=code, cat=key[0], rate=key[1]))
    tax = {k: r2(v * k[1] / 100) for k, v in groups.items()}
    allowance_total = sum((a["amount"] for a in allowances), Decimal(0))
    basis = line_total - allowance_total
    tax_total = sum(tax.values(), Decimal(0))
    grand = basis + tax_total
    paid = r2(dec(spec["paid_amount"], "paid_amount")) if given(spec.get("paid_amount")) else Decimal(0)
    if paid < 0 or paid > max(grand, Decimal(0)):
        raise SystemExit("paid_amount %s is not between 0 and the total %s: the amount due does not close "
                         "(EN 16931-1 BT-113, BT-115, BR-CO-16)" % (paid, grand))
    return dict(groups=groups, tax=tax, allowances=allowances, line_total=line_total, allowance_total=allowance_total,
                basis=basis, tax_total=tax_total, grand=grand, paid=paid, due=grand - paid)


# The words of a discount, a sum of lines, an amount paid in advance and an amount due (EN 16931-1 BG-27, BT-106,
# BT-113, BT-115), in every language the page writes. total_incl names the total with tax where the locale's own
# "total" word means "to pay" (it is used only on a page that also states an amount paid in advance).
WORDS = {
    "de-DE": {"discount": "Rabatt", "lines_sum": "Summe der Positionen", "paid": "Anzahlung", "due_pay": "Zu zahlen", "total_incl": "Gesamt"},
    "de-AT": {"discount": "Rabatt", "lines_sum": "Summe der Positionen", "paid": "Anzahlung", "due_pay": "Zu zahlen", "total_incl": "Gesamtbetrag"},
    "de-BE": {"discount": "Rabatt", "lines_sum": "Summe der Positionen", "paid": "Anzahlung", "due_pay": "Zu zahlen", "total_incl": "Gesamt"},
    "en-GB": {"discount": "Discount", "lines_sum": "Sum of lines", "paid": "Paid in advance", "due_pay": "Amount due", "total_incl": "Total"},
    "en-IE": {"discount": "Discount", "lines_sum": "Sum of lines", "paid": "Paid in advance", "due_pay": "Amount due", "total_incl": "Total incl. VAT"},
    "en-AU": {"discount": "Discount", "lines_sum": "Sum of lines", "paid": "Paid in advance", "due_pay": "Amount due", "total_incl": "Total incl. GST"},
    "en-CA": {"discount": "Discount", "lines_sum": "Sum of lines", "paid": "Paid in advance", "due_pay": "Amount due", "total_incl": "Total"},
    "en-US": {"discount": "Discount", "lines_sum": "Sum of lines", "paid": "Paid in advance", "due_pay": "Balance due", "total_incl": "Total"},
    "sv-SE": {"discount": "Rabatt", "lines_sum": "Summa rader", "paid": "Förskottsbetalt", "due_pay": "Att betala", "total_incl": "Totalt"},
    "da-DK": {"discount": "Rabat", "lines_sum": "Sum af linjer", "paid": "Forudbetalt", "due_pay": "Til betaling", "total_incl": "I alt"},
    "nb-NO": {"discount": "Rabatt", "lines_sum": "Sum linjer", "paid": "Forskuddsbetalt", "due_pay": "Å betale", "total_incl": "Totalt"},
    "fi-FI": {"discount": "Alennus", "lines_sum": "Rivien summa", "paid": "Ennakkoon maksettu", "due_pay": "Maksettava", "total_incl": "Yhteensä"},
    "fr-FR": {"discount": "Remise", "lines_sum": "Somme des lignes", "paid": "Acompte versé", "due_pay": "Net à payer", "total_incl": "Total TTC"},
    "fr-BE": {"discount": "Remise", "lines_sum": "Somme des lignes", "paid": "Acompte versé", "due_pay": "Total à payer", "total_incl": "Total TVAC"},
    "fr-CA": {"discount": "Remise", "lines_sum": "Somme des lignes", "paid": "Acompte versé", "due_pay": "Solde à payer", "total_incl": "Total"},
    "nl-NL": {"discount": "Korting", "lines_sum": "Som van de regels", "paid": "Vooruitbetaald", "due_pay": "Te betalen", "total_incl": "Totaal incl. btw"},
    "nl-BE": {"discount": "Korting", "lines_sum": "Som van de regels", "paid": "Vooruitbetaald", "due_pay": "Te betalen", "total_incl": "Totaal incl. btw"},
    "es-ES": {"discount": "Descuento", "lines_sum": "Suma de las líneas", "paid": "Pagado por adelantado", "due_pay": "Importe a pagar", "total_incl": "Total factura"},
    "it-IT": {"discount": "Sconto", "lines_sum": "Somma delle righe", "paid": "Acconto versato", "due_pay": "Importo da pagare", "total_incl": "Totale documento"},
    "pl-PL": {"discount": "Rabat", "lines_sum": "Suma pozycji", "paid": "Zapłacono z góry", "due_pay": "Pozostało do zapłaty", "total_incl": "Razem brutto"},
}
