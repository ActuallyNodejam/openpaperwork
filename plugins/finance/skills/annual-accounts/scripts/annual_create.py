#!/usr/bin/env python3
"""Write the annual report (årsredovisning) of a smaller Swedish limited company as Word, in Swedish or English.

Usage: annual_create.py spec.json arsredovisning.docx

Spec (templates/ has a consultancy with a profit and a cleaning company with a loss and a shareholder contribution):
{
  "language": "sv",                       # "en" for English
  "company": {"name": "...", "org_number": "556000-0000", "seat": "the town of the registered office"},
  "year":  {"start": "2025-01-01", "end": "2025-12-31"},
  "prior": {"start": "2024-01-01", "end": "2024-12-31"},     # or "first_year": true for a company's first year
  "report": {"business": "what the company does", "events": "significant events during the year",
             "earlier_years": [{"year": "2023", "net_sales": 0, "result_after_financial": 0, "solidity": 0},
                               {"year": "2022", ...}]},   # K2 5.5: the year and the three before it; with
                                                          # last year unknown its net sales and result go here too
  "income":  {"net_sales": [this year, last year], "other_external": [-310000, -298000], ...},
  "balance": {"equipment": [cur, prior], "trade_receivables": [...], "share_capital": [25000, 25000],
              "retained": [null, 412300], ...},   # null this year: worked out from last year and the changes below
  "equity_changes": {"dividend_paid": 0, "shareholder_contribution": 0, "new_share_capital": 0,
                     "new_share_premium": 0},
  "disposition": {"dividend": 0},         # the rest is carried forward
  "fixed_assets": {"equipment": {"opening_cost": [c, p], "additions": [c, p], "disposals_cost": [c, p],
                                 "opening_depreciation": [c, p], "depreciation": [c, p],
                                 "disposals_depreciation": [c, p]}},
  "principles": ["Inventarier skrivs av linjärt över fem år."],
  "employees": [2, 2],
  "pledged": [{"label": "Företagsinteckningar", "amounts": [200000, 200000]}],    # or [] for none
  "contingent": [],
  "events_after": "a significant event after the year end, or leave it out",
  "notes": [{"title": "...", "text": "...", "attach": "lt_credit"}],
  "unknown": ["prior", "signing.date"],  # what the company has not given yet (UNKNOWN below): left empty, never made up
  "signing": {"place": "Umeå", "date": "2026-03-18",
              "board": [{"name": "...", "role": "Styrelseledamot, verkställande direktör"}],
              "auditor": null}               # or {"name": "...", "firm": "...", "date": "..."}
}

Amounts are whole kronor. Income is positive, costs negative, as the income statement prints them.
Line keys are listed in INCOME and BALANCE below; a line that is zero in both years is left out.

Where each part comes from:
- The parts and their order, comparatives, signatures and date: årsredovisningslagen (1995:1554) 2 kap. 1 §,
  2 kap. 7 §, 3 kap. 5 §; Swedish statute, outside copyright (upphovsrättslagen 9 §).
- The lines of the balance sheet and income statement: ÅRL bilaga 1 and 2 (3 kap. 3 §), abridged as a smaller
  company may (3 kap. 4 §); Directive 2013/34/EU Art. 9(5), 10, 13 and 14, Annexes III and V, reused under
  Commission Decision 2011/833/EU.
- The management report: ÅRL 6 kap. 1 and 2 §§ (significant events, changes in equity, the disposition of profit).
- The notes: ÅRL 5 kap. 4, 8, 14, 15, 20 and 22 §§; Directive 2013/34/EU Art. 16(1).
- Bokföringsnämnden's general advice BFNAR 2016:10 (K2) is cited, never copied: chapters 3 to 5 and 18 on
  the form, the layouts, the management report and the notes. The wording and layout here are our own.
The script writes what the spec says and adds up what it lays out. It never values an asset, works out tax
or says whether a dividend may be paid. Prints a JSON summary with any warnings. Needs python-docx.
"""
import datetime as dt
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / "_shared"))
import letter  # noqa: E402
import spec_guard  # noqa: E402

FONT = "Arial"
MINUS = "\u2212"
# Column widths in mm on a 166 mm text width: every statement and note puts its amounts in the same columns.
LABEL, NOTE, AMOUNT = 94, 14, 29
TAX_SHARE = 0.206    # Swedish corporate tax since 2021: untaxed reserves count 79.4 percent as equity

# (Swedish, English, children): a child is a group like this or a line (key, Swedish, English).
INCOME = [
    ("Rörelseintäkter", "Operating income", [
        ("net_sales", "Nettoomsättning", "Net sales"),
        ("inventory_change", "Förändring av varulager", "Change in inventories"),
        ("own_work", "Aktiverat arbete för egen räkning", "Own work capitalised"),
        ("other_operating_income", "Övriga rörelseintäkter", "Other operating income")]),
    ("Rörelsekostnader", "Operating expenses", [
        ("raw_materials", "Råvaror och förnödenheter", "Raw materials and consumables"),
        ("goods", "Handelsvaror", "Goods for resale"),
        ("other_external", "Övriga externa kostnader", "Other external expenses"),
        ("personnel", "Personalkostnader", "Personnel costs"),
        ("depreciation", "Av- och nedskrivningar av materiella och immateriella anläggningstillgångar",
         "Depreciation and impairment of tangible and intangible fixed assets"),
        ("other_operating_expenses", "Övriga rörelsekostnader", "Other operating expenses")]),
    ("=", "Rörelseresultat", "Operating profit or loss"),
    ("Finansiella poster", "Financial items", [
        ("interest_income", "Övriga ränteintäkter och liknande resultatposter", "Interest income and similar items"),
        ("interest_expense", "Räntekostnader och liknande resultatposter", "Interest expense and similar items")]),
    ("=", "Resultat efter finansiella poster", "Profit or loss after financial items"),
    ("Bokslutsdispositioner", "Appropriations", [
        ("tax_allocation_change", "Förändring av periodiseringsfonder", "Change in tax allocation reserves"),
        ("excess_depreciation_change", "Förändring av överavskrivningar", "Change in excess depreciation")]),
    ("=", "Resultat före skatt", "Profit or loss before tax"),
    (None, None, [("tax", "Skatt på årets resultat", "Tax on profit for the year")]),
    ("=", "Årets resultat", "Profit or loss for the year"),
]
COSTS = {"raw_materials", "goods", "other_external", "personnel", "depreciation", "other_operating_expenses",
         "interest_expense"}

ASSETS = ("Tillgångar", "Assets", [
    ("Anläggningstillgångar", "Fixed assets", [
        ("Immateriella anläggningstillgångar", "Intangible fixed assets", [
            ("development", "Balanserade utgifter för utvecklingsarbeten och liknande arbeten",
             "Capitalised development expenditure"),
            ("licences", "Koncessioner, patent, licenser, varumärken samt liknande rättigheter",
             "Concessions, patents, licences, trademarks and similar rights"),
            ("goodwill", "Goodwill", "Goodwill")]),
        ("Materiella anläggningstillgångar", "Tangible fixed assets", [
            ("buildings", "Byggnader och mark", "Land and buildings"),
            ("machinery", "Maskiner och andra tekniska anläggningar", "Plant and machinery"),
            ("equipment", "Inventarier, verktyg och installationer", "Equipment, tools and installations")]),
        ("Finansiella anläggningstillgångar", "Financial fixed assets", [
            ("securities", "Andra långfristiga värdepappersinnehav", "Other long-term securities"),
            ("long_receivables", "Andra långfristiga fordringar", "Other long-term receivables")])]),
    ("Omsättningstillgångar", "Current assets", [
        ("Varulager m.m.", "Inventories", [
            ("raw_stock", "Råvaror och förnödenheter", "Raw materials and consumables"),
            ("finished_goods", "Färdiga varor och handelsvaror", "Finished goods and goods for resale")]),
        ("Kortfristiga fordringar", "Current receivables", [
            ("trade_receivables", "Kundfordringar", "Trade receivables"),
            ("tax_receivable", "Aktuella skattefordringar", "Current tax assets"),
            ("other_receivables", "Övriga fordringar", "Other receivables"),
            ("prepaid", "Förutbetalda kostnader och upplupna intäkter", "Prepaid expenses and accrued income")]),
        ("Kortfristiga placeringar", "Short-term investments", [
            ("short_investments", "Övriga kortfristiga placeringar", "Other short-term investments")]),
        ("Kassa och bank", "Cash and bank", [
            ("cash", "Kassa och bank", "Cash and bank balances")])])])
EQUITY = ("Eget kapital", "Equity", [
    ("Bundet eget kapital", "Restricted equity", [
        ("share_capital", "Aktiekapital", "Share capital"),
        ("revaluation_fund", "Uppskrivningsfond", "Revaluation reserve"),
        ("reserve_fund", "Reservfond", "Statutory reserve"),
        ("development_fund", "Fond för utvecklingsutgifter", "Fund for development expenditure")]),
    ("Fritt eget kapital", "Unrestricted equity", [
        ("share_premium", "Överkursfond", "Share premium reserve"),
        ("retained", "Balanserat resultat", "Retained earnings"),
        ("result", "Årets resultat", "Profit or loss for the year")])])
LIABILITIES = ("Eget kapital och skulder", "Equity and liabilities", [
    EQUITY,
    ("Obeskattade reserver", "Untaxed reserves", [
        ("tax_allocation_reserves", "Periodiseringsfonder", "Tax allocation reserves"),
        ("excess_depreciation", "Ackumulerade överavskrivningar", "Accumulated excess depreciation")]),
    ("Avsättningar", "Provisions", [("provisions", "Övriga avsättningar", "Other provisions")]),
    ("Långfristiga skulder", "Non-current liabilities", [
        ("lt_credit", "Skulder till kreditinstitut", "Liabilities to credit institutions"),
        ("lt_shareholder", "Skulder till aktieägare", "Liabilities to shareholders"),
        ("lt_other", "Övriga skulder", "Other liabilities")]),
    ("Kortfristiga skulder", "Current liabilities", [
        ("st_credit", "Skulder till kreditinstitut", "Liabilities to credit institutions"),
        ("advances", "Förskott från kunder", "Advances from customers"),
        ("trade_payables", "Leverantörsskulder", "Trade payables"),
        ("tax_liabilities", "Aktuella skatteskulder", "Current tax liabilities"),
        ("st_other", "Övriga skulder", "Other liabilities"),
        ("accrued", "Upplupna kostnader och förutbetalda intäkter", "Accrued expenses and deferred income")])])
EQUITY_KEYS = ["share_capital", "revaluation_fund", "reserve_fund", "development_fund", "share_premium",
               "retained", "result"]
FREE_KEYS = ["share_premium", "retained", "result"]
UNTAXED = ["tax_allocation_reserves", "excess_depreciation"]

WORDS = {
    "sv": {
        "title": "Årsredovisning för %s", "org": "Org.nr %s", "year": "Räkenskapsåret %s – %s",
        "intro_ceo": "Styrelsen och verkställande direktören för %s avger följande årsredovisning.",
        "intro": "Styrelsen för %s avger följande årsredovisning.",
        "unit": "Alla belopp anges i hela kronor (kr) om inget annat sägs.",
        "report": "Förvaltningsberättelse", "business": "Verksamheten", "seat": "Bolaget har sitt säte i %s.",
        "first": "Detta är bolagets första räkenskapsår.",
        "events": "Väsentliga händelser under räkenskapsåret", "no_events": "Inga väsentliga händelser har inträffat under räkenskapsåret.",
        "overview": "Flerårsöversikt", "net_sales": "Nettoomsättning",
        "after_fin": "Resultat efter finansiella poster", "solidity": "Soliditet (%)",
        "solidity_def": "Soliditet: eget kapital och obeskattade reserver (med avdrag för uppskjuten skatt) i procent av balansomslutningen.",
        "changes": "Förändringar i eget kapital", "opening": "Belopp vid årets ingång",
        "agm": "Disposition enligt årsstämmans beslut", "dividend_paid": "Utdelning",
        "contribution": "Erhållet aktieägartillskott", "issue": "Nyemission", "year_result": "Årets resultat",
        "closing": "Belopp vid årets utgång", "total": "Totalt",
        "disposition": "Resultatdisposition", "funds": "Till årsstämmans förfogande står följande medel:",
        "proposal": "Styrelsen föreslår att medlen disponeras så att:",
        "dividend": "Utdelning till aktieägarna", "forward": "Balanseras i ny räkning", "sum": "Summa",
        "income": "Resultaträkning", "balance": "Balansräkning", "note": "Not", "notes": "Noter",
        "sum_of": "Summa %s",
        "principles": "Redovisningsprinciper",
        "principles_text": "Årsredovisningen är upprättad enligt årsredovisningslagen (1995:1554) och Bokföringsnämndens allmänna råd BFNAR 2016:10 Årsredovisning i mindre företag (K2).",
        "employees": "Medelantal anställda", "employees_row": "Medelantalet anställda",
        "pledged": "Ställda säkerheter", "contingent": "Eventualförpliktelser", "none": "Inga.",
        "events_after": "Väsentliga händelser efter räkenskapsårets slut",
        "fa": [("opening_cost", "Ingående anskaffningsvärden"), ("additions", "Inköp"),
               ("disposals_cost", "Försäljningar och utrangeringar"),
               ("=cost", "Utgående ackumulerade anskaffningsvärden"),
               ("opening_depreciation", "Ingående avskrivningar"),
               ("disposals_depreciation", "Återförda avskrivningar på sålda och utrangerade tillgångar"),
               ("depreciation", "Årets avskrivningar"), ("=depr", "Utgående ackumulerade avskrivningar"),
               ("=book", "Utgående redovisat värde")],
        "sign": "Underskrifter", "signed": "%s den %s", "auditor": "Vår revisionsberättelse har lämnats den %s.",
        "auditor_role": "Auktoriserad revisor", "item": "Post",
    },
    "en": {
        "title": "Annual report for %s", "org": "Corporate identity number %s", "year": "Financial year %s to %s",
        "intro_ceo": "The board of directors and the managing director of %s present the annual report below.",
        "intro": "The board of directors of %s presents the annual report below.",
        "unit": "All amounts are in whole Swedish kronor (SEK) unless otherwise stated.",
        "report": "Management report", "business": "The business", "seat": "The company's registered office is in %s.",
        "first": "This is the company's first financial year.",
        "events": "Significant events during the financial year",
        "no_events": "No significant events took place during the financial year.",
        "overview": "Multi-year overview", "net_sales": "Net sales",
        "after_fin": "Profit or loss after financial items", "solidity": "Equity ratio (%)",
        "solidity_def": "Equity ratio: equity and untaxed reserves (less deferred tax) as a percentage of total assets.",
        "changes": "Changes in equity", "opening": "Opening balance",
        "agm": "Appropriation as resolved by the annual general meeting", "dividend_paid": "Dividend",
        "contribution": "Shareholder contribution received", "issue": "New share issue",
        "year_result": "Profit or loss for the year", "closing": "Closing balance", "total": "Total",
        "disposition": "Proposed appropriation of profit",
        "funds": "The following funds are at the disposal of the annual general meeting:",
        "proposal": "The board proposes that the funds be appropriated as follows:",
        "dividend": "Dividend to the shareholders", "forward": "Carried forward", "sum": "Total",
        "income": "Income statement", "balance": "Balance sheet", "note": "Note", "notes": "Notes",
        "sum_of": "Total %s",
        "principles": "Accounting policies",
        "principles_text": "The annual report has been prepared under the Swedish Annual Accounts Act (1995:1554) and the Swedish Accounting Standards Board's general advice BFNAR 2016:10 Annual reports in smaller companies (K2).",
        "employees": "Average number of employees", "employees_row": "Average number of employees",
        "pledged": "Pledged assets", "contingent": "Contingent liabilities", "none": "None.",
        "events_after": "Significant events after the end of the financial year",
        "fa": [("opening_cost", "Opening cost"), ("additions", "Additions"),
               ("disposals_cost", "Disposals and retirements"), ("=cost", "Closing accumulated cost"),
               ("opening_depreciation", "Opening depreciation"),
               ("disposals_depreciation", "Depreciation reversed on disposals and retirements"),
               ("depreciation", "Depreciation for the year"), ("=depr", "Closing accumulated depreciation"),
               ("=book", "Closing carrying amount")],
        "sign": "Signatures", "signed": "%s, %s", "auditor": "Our audit report was submitted on %s.",
        "auditor_role": "Authorised public accountant", "item": "Item",
    },
}


def lang_of(spec):
    return "en" if str(spec.get("language") or "sv").lower().startswith("en") else "sv"


# What the company may not have given yet. Each one the data file declares ("unknown": [...]) is left empty on the
# page and named in the warnings, so the draft is built and the person sees what is still open; nothing is made up.
UNKNOWN = {
    "prior": "last year's figures, so last year's column is empty",
    "report.earlier_years": "the years before last year in the multi-year overview",
    "report.events": "the significant events of the year, so the management report leaves them empty",
    "signing.date": "the date the board signs, left on a line",
}


def pair(value):
    """[this year, last year] as numbers; a missing year is None."""
    if value is None:
        return [None, None]
    if isinstance(value, (int, float)):
        return [value, None]
    v = list(value) + [None, None]
    return [v[0], v[1]]


def leaves(node):
    if len(node) == 3 and isinstance(node[2], list):
        for child in node[2]:
            yield from leaves(child)
    else:
        yield node


class Report:
    def __init__(self, spec):
        self.spec = spec
        self.lang = lang_of(spec)
        self.w = WORDS[self.lang]
        self.loc = "sv-SE" if self.lang == "sv" else "en-GB"
        self.first = bool(spec.get("first_year"))
        self.unknown = list(spec.get("unknown") or [])
        wrong = [k for k in self.unknown if k not in UNKNOWN]
        if wrong:
            raise SystemExit('"unknown" holds %s; what may be unknown: %s' % (", ".join(wrong), ", ".join(UNKNOWN)))
        self.no_prior = "prior" in self.unknown and not self.first
        self.blank = self.first or self.no_prior          # no figure in last year's column
        if self.no_prior:
            given = ["%s.%s" % (part, k) for part in ("income", "balance") for k, v in (spec.get(part) or {}).items()
                     if pair(v)[1] is not None]
            given += ["fixed_assets.%s.%s" % (a, k) for a, rows in (spec.get("fixed_assets") or {}).items()
                      for k, v in rows.items() if pair(v)[1] is not None]
            if given:
                raise SystemExit('"unknown" holds "prior", and the data file gives last year\'s figure for %s. Either '
                                 'last year is known and "prior" comes out of "unknown", or what you have for it (net '
                                 'sales, the result after financial items) goes in report.earlier_years, the '
                                 'multi-year overview' % ", ".join(given))
        self.warnings = ["not given yet and left empty: %s; name it in your reply" % UNKNOWN[k] for k in self.unknown]
        self.income = {k: pair(v) for k, v in (spec.get("income") or {}).items()}
        for k, (c, p) in self.income.items():
            if k in COSTS and any(x is not None and x > 0 for x in (c, p)):
                raise SystemExit("income.%s is a cost: write it as a negative number" % k)
        self.results = self.work_out_results()
        self.balance = {k: pair(v) for k, v in (spec.get("balance") or {}).items()}
        self.fixed = self.fixed_asset_notes()
        self.equity_rows = self.work_out_equity()
        self.notes = self.number_notes()

    # ---- numbers ----------------------------------------------------------------------------------
    def work_out_results(self):
        """The result rows of the income statement, each the sum of every line above it."""
        out, run = {}, [0, 0]
        for node in INCOME:
            if node[0] == "=":
                out[node[1]] = list(run)
                continue
            for key, *_ in leaves(node):
                c, p = self.income.get(key, [None, None])
                run = [run[0] + (c or 0), run[1] + (p or 0)]
        out["result"] = list(run)
        return out

    def fixed_asset_notes(self):
        out = {}
        for key, rows in (self.spec.get("fixed_assets") or {}).items():
            v = {k: pair(rows.get(k)) for k, _ in WORDS["sv"]["fa"] if not k.startswith("=")}
            col = lambda i, *ks: sum((v[k][i] or 0) for k in ks)  # noqa: E731
            cost = [col(i, "opening_cost", "additions", "disposals_cost") for i in (0, 1)]
            depr = [col(i, "opening_depreciation", "disposals_depreciation", "depreciation") for i in (0, 1)]
            v["=cost"], v["=depr"] = cost, depr
            v["=book"] = [cost[0] + depr[0], cost[1] + depr[1]]
            if self.no_prior:
                v = {k: [x[0], None] for k, x in v.items()}
            out[key] = v
            if key not in self.balance:
                self.balance[key] = list(v["=book"])
            elif self.balance[key] != v["=book"]:
                self.warnings.append("balance.%s is %s but its note's carrying amount is %s"
                                     % (key, self.balance[key], v["=book"]))
        return out

    def work_out_equity(self):
        """Fill this year's equity from last year's and the year's changes; return the changes table."""
        ch = self.spec.get("equity_changes") or {}
        res_c, res_p = self.results["result"]
        given = self.balance.get("result")
        if given and given != [res_c, res_p]:
            self.warnings.append("balance.result %s is not the income statement's %s" % (given, [res_c, res_p]))
        else:
            self.balance["result"] = [res_c, res_p]
        prior = {k: (self.balance.get(k, [None, None])[1] or 0) for k in EQUITY_KEYS}
        if self.blank:
            prior = {k: 0 for k in EQUITY_KEYS}
        moves = []
        if prior["result"]:
            moves.append((self.w["agm"], {"retained": prior["result"], "result": -prior["result"]}))
        if ch.get("dividend_paid"):
            moves.append((self.w["dividend_paid"], {"retained": -ch["dividend_paid"]}))
        if ch.get("shareholder_contribution"):
            moves.append((self.w["contribution"], {"retained": ch["shareholder_contribution"]}))
        if ch.get("new_share_capital") or ch.get("new_share_premium"):
            moves.append((self.w["issue"], {"share_capital": ch.get("new_share_capital", 0),
                                            "share_premium": ch.get("new_share_premium", 0)}))
        for other in ch.get("other") or []:
            moves.append((other["label"], {other["column"]: other["amount"]}))
        moves.append((self.w["year_result"], {"result": res_c}))
        if self.no_prior:
            # Last year's balance sheet is not given: the year opens at this year's equity less the year's changes.
            for k in EQUITY_KEYS:
                cur = self.balance.get(k, [None, None])[0]
                if cur is not None:
                    prior[k] = cur - sum(m.get(k, 0) for _, m in moves)
        closing = dict(prior)
        for _, m in moves:
            for k, a in m.items():
                closing[k] += a
        for k in EQUITY_KEYS:
            cur = self.balance.get(k, [None, None])
            if cur[0] is None:
                if closing[k] or cur[1]:
                    self.balance[k] = [closing[k], cur[1]]
            elif cur[0] != closing[k]:
                self.warnings.append("balance.%s this year is %s; last year's %s and the changes give %s"
                                     % (k, cur[0], prior[k], closing[k]))
        cols = [k for k in EQUITY_KEYS if prior[k] or closing[k]]
        # With last year unknown, last year's result is not known apart from the retained earnings it went into.
        opening = {k: prior[k] for k in cols if not (self.no_prior and k == "result" and not prior[k])}
        rows = [(self.w["opening"], opening)] if not self.first else []
        rows += [(label, m) for label, m in moves]
        rows.append((self.w["closing"], {k: closing[k] for k in cols}))
        return cols, rows

    def value(self, key):
        return self.balance.get(key, [None, None])

    def group_sum(self, node, i):
        return sum((self.value(k)[i] or 0) for k, *_ in leaves(node))

    def present(self, node):
        return any(any(x for x in self.value(k)) for k, *_ in leaves(node))

    def free_equity(self):
        return sum((self.value(k)[0] or 0) for k in FREE_KEYS)

    # ---- notes --------------------------------------------------------------------------------------
    def number_notes(self):
        """(title, kind, payload, attach) in the order the statements first point at them, numbered."""
        w, s = self.w, self.spec
        notes = [(w["principles"], "principles", s.get("principles") or [], None)]
        attached = []
        if s.get("employees") is not None:
            attached.append((w["employees"], "employees", pair(s["employees"]), "personnel"))
        for key in self.fixed:
            label = next(x for x in leaves(ASSETS) if x[0] == key)
            attached.append((label[1] if self.lang == "sv" else label[2], "fixed", self.fixed[key], key))
        for extra in s.get("notes") or []:
            attached.append((extra["title"], "text", extra.get("text", ""), extra.get("attach")))
        order = [k for node in INCOME if node[0] != "=" for k, *_ in leaves(node)]
        order += [k for k, *_ in leaves(ASSETS)] + [k for k, *_ in leaves(LIABILITIES)]
        rank = lambda n: order.index(n[3]) if n[3] in order else len(order)  # noqa: E731
        notes += sorted(attached, key=rank)
        notes.append((w["pledged"], "amounts", s.get("pledged") or [], None))
        notes.append((w["contingent"], "amounts", s.get("contingent") or [], None))
        if s.get("events_after"):
            notes.append((w["events_after"], "text", s["events_after"], None))
        return [(n + 1,) + note for n, note in enumerate(notes)]

    def note_for(self, key):
        for n, _title, _kind, _payload, attach in self.notes:
            if attach == key:
                return str(n)
        return ""

    # ---- text ---------------------------------------------------------------------------------------
    def amount(self, v):
        """Whole kronor: a space between thousands in Swedish, a comma in English, a true minus sign."""
        return "" if v is None else letter.money(v, self.loc, 0).replace("-", MINUS)

    def years(self, balance):
        y, p = self.spec["year"], self.spec.get("prior") or {}
        if balance:
            return [y["end"], p.get("end", "")]
        return ["%s –\n%s" % (y["start"], y["end"]), "%s –\n%s" % (p["start"], p["end"]) if p else ""]

    def statement(self, nodes, balance):
        """Rows (label, note, this year, last year, kind) of a statement."""
        rows = []

        def walk(node, depth):
            if not self.present(node) if balance else not any(
                    any(self.income.get(k, [None, None])) for k, *_ in leaves(node)):
                return
            head, children = (node[0] if self.lang == "sv" else node[1]), node[2]
            if head:
                rows.append((head, "", "", "", "head"))
            for child in children:
                if len(child) == 3 and isinstance(child[2], list):
                    walk(child, depth + 1)
                else:
                    key, sv, en = child
                    c, p = (self.value(key) if balance else self.income.get(key, [None, None]))
                    if not any((c, p)):
                        continue
                    rows.append((sv if self.lang == "sv" else en, self.note_for(key), self.amount(c or 0),
                                 "" if self.blank else self.amount(p or 0), "line"))
            if head:
                cur = self.group_sum(node, 0) if balance else sum(
                    (self.income.get(k, [0, 0])[0] or 0) for k, *_ in leaves(node))
                pri = self.group_sum(node, 1) if balance else sum(
                    (self.income.get(k, [0, 0])[1] or 0) for k, *_ in leaves(node))
                rows.append((self.w["sum_of"] % (head[0].lower() + head[1:]), "", self.amount(cur),
                             "" if self.blank else self.amount(pri), "sum"))

        if balance:
            for node in nodes:
                walk(node, 0)
            return rows
        appropriations = any(any(self.income.get(k, [None, None])) for k in
                             ("tax_allocation_change", "excess_depreciation_change"))
        for node in nodes:
            if node[0] == "=":
                if node[1] == "Resultat före skatt" and not appropriations:
                    continue
                c, p = self.results[node[1]] if node[1] != "Årets resultat" else self.results["result"]
                rows.append((node[1] if self.lang == "sv" else node[2], "", self.amount(c),
                             "" if self.blank else self.amount(p), "result"))
            else:
                walk(node, 0)
        return rows

    def overview(self):
        y, p = self.spec["year"], self.spec.get("prior") or {}
        label = lambda per: per["end"][:4] if per["start"][:4] == per["end"][:4] else "%s/%s" % (  # noqa: E731
            per["start"][:4], per["end"][2:4])
        cols = [label(y)] + ([] if self.blank else [label(p)])
        after = self.results["Resultat efter finansiella poster"]
        sales = self.income.get("net_sales", [0, 0])
        sol = []
        for i in range(len(cols)):
            assets = self.group_sum(ASSETS, i)
            eq = self.group_sum(EQUITY, i) + (1 - TAX_SHARE) * sum((self.value(k)[i] or 0) for k in UNTAXED)
            sol.append(round(100 * eq / assets) if assets else 0)
        rows = [[self.w["net_sales"]] + [self.amount(sales[i] or 0) for i in range(len(cols))],
                [self.w["after_fin"]] + [self.amount(after[i]) for i in range(len(cols))],
                [self.w["solidity"]] + [str(sol[i]) for i in range(len(cols))]]
        earlier = (self.spec.get("report") or {}).get("earlier_years") or []
        for e in earlier:
            cols.append(str(e["year"]))
            rows[0].append(self.amount(e.get("net_sales", 0)))
            rows[1].append(self.amount(e.get("result_after_financial", 0)))
            rows[2].append(str(e.get("solidity", "")))
        # BFNAR 2016:10 punkt 5.5: the year and the three before it, and a comment when net sales vary by more
        # than 30 percent between the years. A younger company has fewer years: a question, never a made-up figure.
        if len(cols) < 4 and not self.first:
            self.warnings.append("the multi-year overview has %d years; K2 (BFNAR 2016:10 punkt 5.5) asks for the year "
                                 "and the three before it: ask for report.earlier_years, or say the company is younger"
                                 % len(cols))
        series = [(cols[0], sales[0] or 0)] + ([] if self.blank else [(cols[1], sales[1] or 0)]) + \
            [(str(e["year"]), e.get("net_sales", 0) or 0) for e in earlier]
        for (y1, a), (y0, b) in zip(series, series[1:]):
            if b and abs(a - b) > 0.3 * abs(b):
                self.warnings.append("net sales moved %d percent from %s to %s; K2 (BFNAR 2016:10 punkt 5.5) asks the "
                                     "management report to comment on it: ask the company why"
                                     % (round(100 * (a - b) / abs(b)), y0, y1))
        return [[""] + cols] + rows


def _border(cell, edge, size=4):
    from docx.oxml import OxmlElement
    from docx.oxml.ns import qn
    tcpr = cell._tc.get_or_add_tcPr()
    borders = tcpr.find(qn("w:tcBorders"))
    if borders is None:
        borders = OxmlElement("w:tcBorders")
        tcpr.append(borders)
    b = OxmlElement("w:%s" % edge)
    for k, v in (("w:val", "single"), ("w:sz", str(size)), ("w:space", "0"), ("w:color", "000000")):
        b.set(qn(k), v)
    borders.append(b)


def add_table(doc, rows, widths, kinds=None, right_from=1, header=True, rule_from=None, keep_after=False):
    """A table laid out like a Swedish annual report: the column header over a thin rule, amounts
    right-aligned in fixed columns, group headings in italics, subtotals and totals in bold under a thin
    rule over their amounts. Rows never split and the table keeps to one page."""
    from docx.enum.table import WD_TABLE_ALIGNMENT
    from docx.enum.text import WD_ALIGN_PARAGRAPH
    from docx.oxml import OxmlElement
    from docx.oxml.ns import qn
    from docx.shared import Mm, Pt
    kinds = kinds or (["header"] if header else []) + ["line"] * (len(rows) - (1 if header else 0))
    rule_from = right_from if rule_from is None else rule_from
    t = doc.add_table(rows=len(rows), cols=len(rows[0]))
    t.autofit = False
    t.alignment = WD_TABLE_ALIGNMENT.LEFT
    for c, width in enumerate(widths[:len(rows[0])]):
        t.columns[c].width = Mm(width)     # the grid: what LibreOffice and Word lay the columns out by
    for r, row in enumerate(rows):
        kind = kinds[r]
        tr = t.rows[r]._tr
        trpr = tr.get_or_add_trPr()
        trpr.append(OxmlElement("w:cantSplit"))
        if kind == "header":
            trpr.append(OxmlElement("w:tblHeader"))
        for c, text in enumerate(row):
            cell = t.cell(r, c)
            cell.width = Mm(widths[c])
            p = cell.paragraphs[0]
            p.paragraph_format.space_before = Pt(5 if kind == "group" and r > 1 else 10 if kind == "text" and r
                                                 else 1)
            p.paragraph_format.space_after = Pt(1)
            p.paragraph_format.keep_with_next = r < len(rows) - 1
            lines = str(text).split("\n")
            for n, line in enumerate(lines):
                run = p.add_run(line)
                run.bold = kind in ("sum", "result")
                run.italic = kind == "group"
                if n < len(lines) - 1:
                    run.add_break()
            if c >= right_from:
                p.alignment = WD_ALIGN_PARAGRAPH.RIGHT
            if kind == "header":
                _border(cell, "bottom")
            elif kind in ("sum", "result") and c >= rule_from and str(text).strip():
                _border(cell, "top")
    gap = doc.add_paragraph()
    gap.paragraph_format.space_after = Pt(2)
    gap.paragraph_format.keep_with_next = keep_after
    return t


def _field(paragraph, instr, shown):
    """A Word field (PAGE, NUMPAGES) with the value shown until the reader's program fills it in."""
    from docx.oxml import OxmlElement
    from docx.oxml.ns import qn
    for kind, text in (("begin", None), ("instr", instr), ("separate", None), ("text", shown), ("end", None)):
        run = paragraph.add_run()
        if kind == "instr":
            el = OxmlElement("w:instrText")
            el.set(qn("xml:space"), "preserve")
            el.text = " %s " % text
        elif kind == "text":
            el = OxmlElement("w:t")
            el.text = text
        else:
            el = OxmlElement("w:fldChar")
            el.set(qn("w:fldCharType"), kind)
        run._r.append(el)


def _no_style_tabs(paragraph):
    """Clear the Header style's centre and right tabs, so the one tab goes to the right margin."""
    from docx.oxml import OxmlElement
    from docx.oxml.ns import qn
    ppr = paragraph._p.get_or_add_pPr()
    tabs = ppr.find(qn("w:tabs"))
    if tabs is None:
        tabs = OxmlElement("w:tabs")
        ppr.append(tabs)
    for pos in ("4680", "9360", "4536", "9072"):
        t = OxmlElement("w:tab")
        t.set(qn("w:val"), "clear")
        t.set(qn("w:pos"), pos)
        tabs.append(t)


def running_header(doc, name, org_line):
    """Every page after the first: the company and its organisation number, and "2 (6)" at the right."""
    from docx.enum.text import WD_TAB_ALIGNMENT
    from docx.shared import Mm, Pt
    sec = doc.sections[0]
    sec.different_first_page_header_footer = True
    sec.header_distance = Mm(10)
    width = sec.page_width - sec.left_margin - sec.right_margin
    hp = sec.header.paragraphs[0]
    _no_style_tabs(hp)
    hp.paragraph_format.tab_stops.add_tab_stop(width, WD_TAB_ALIGNMENT.RIGHT)
    hp.add_run(name)
    hp.add_run("\t")
    _field(hp, "PAGE", "2")
    hp.add_run(" (")
    _field(hp, "NUMPAGES", "6")
    hp.add_run(")")
    second = sec.header.add_paragraph(org_line)
    second.paragraph_format.space_after = Pt(0)
    for p in sec.header.paragraphs:
        for run in p.runs:
            run.font.size = Pt(9)


def write_docx(spec, out):
    from docx import Document
    from docx.oxml.ns import qn
    from docx.shared import Mm, Pt, RGBColor
    need = [k for k in ("company", "year", "income", "balance", "signing") if not spec.get(k)]
    need += ["company.%s" % k for k in ("name", "org_number") if not (spec.get("company") or {}).get(k)]
    unknown = spec.get("unknown") or []
    if not spec.get("first_year") and not spec.get("prior") and "prior" not in unknown:
        need.append("prior (or \"first_year\": true)")
    if spec.get("signing") and not ((spec["signing"].get("date") or "signing.date" in unknown)
                                    and spec["signing"].get("board")):
        need.append("signing.date and signing.board")
    if need:
        raise SystemExit("the spec needs %s" % ", ".join(need))
    r = Report(spec)
    w, lang = r.w, r.lang
    co = spec["company"]
    doc = Document()
    sec = doc.sections[0]
    sec.page_width, sec.page_height = Mm(210), Mm(297)
    sec.left_margin = sec.right_margin = Mm(22)
    sec.top_margin, sec.bottom_margin = Mm(25), Mm(20)
    for style in doc.styles:
        if style.type == 1 and style.font is not None:
            style.font.name = FONT
            rpr = style.element.get_or_add_rPr()
            fonts = rpr.find(qn("w:rFonts"))
            if fonts is not None:
                for attr in ("w:ascii", "w:hAnsi", "w:eastAsia", "w:cs"):
                    fonts.set(qn(attr), FONT)
                for attr in ("w:asciiTheme", "w:hAnsiTheme", "w:eastAsiaTheme", "w:cstheme"):
                    if fonts.get(qn(attr)) is not None:
                        del fonts.attrib[qn(attr)]
    doc.styles["Normal"].font.size = Pt(10)
    for name, size, before in (("Heading 1", 18, 0), ("Heading 2", 14, 0), ("Heading 3", 11, 10)):
        st = doc.styles[name]
        st.font.size, st.font.bold, st.font.italic = Pt(size), name != "Heading 1", False
        st.font.color.rgb = RGBColor(0, 0, 0)
        st.paragraph_format.space_before, st.paragraph_format.space_after = Pt(before), Pt(6)
        st.paragraph_format.keep_with_next = True
    org_line = w["org"] % co["org_number"]
    running_header(doc, co["name"], org_line)
    para = lambda text: doc.add_paragraph(text)  # noqa: E731

    def part(title):
        """A main part: always on a page of its own."""
        h = doc.add_heading(title, level=2)
        h.paragraph_format.page_break_before = True
        return h

    board = spec["signing"]["board"]
    ceo = any("verkställande" in str(b.get("role", "")).lower() or "managing director" in str(b.get("role", "")).lower()
              for b in board)
    title = w["title"] % co["name"]
    doc.core_properties.title = title
    doc.core_properties.language = r.loc
    doc.core_properties.author = co["name"]

    # Page 1: what the report is, then the management report.
    doc.add_heading(title, level=1)
    para(org_line).paragraph_format.space_after = Pt(0)
    para(w["year"] % (spec["year"]["start"], spec["year"]["end"]))
    p = para((w["intro_ceo"] if ceo else w["intro"]) % co["name"])
    p.paragraph_format.space_before = Pt(14)
    para(w["unit"]).paragraph_format.space_after = Pt(16)
    rep = spec.get("report") or {}
    doc.add_heading(w["report"], level=2)
    doc.add_heading(w["business"], level=3)
    para(str(rep.get("business", "")).strip() + ((" " + w["seat"] % co["seat"]) if co.get("seat") else "")
         + (" " + w["first"] if r.first else ""))
    doc.add_heading(w["events"], level=3)
    para(rep.get("events") or ("" if "report.events" in r.unknown else w["no_events"]))
    doc.add_heading(w["overview"], level=3)
    ov = r.overview()
    add_table(doc, ov, [166 - AMOUNT * (len(ov[0]) - 1)] + [AMOUNT] * (len(ov[0]) - 1))
    para(w["solidity_def"]).runs[0].font.size = Pt(8.5)

    doc.add_heading(w["changes"], level=3)
    cols, rows = r.equity_rows
    labels = {k: (sv if lang == "sv" else en) for k, sv, en in leaves(EQUITY)}
    table = [[""] + [labels[k] for k in cols] + [w["total"]]]
    for label, m in rows:
        table.append([label] + [r.amount(m.get(k, 0)) if k in m else "" for k in cols]
                     + [r.amount(sum(m.values()))])
    n = len(cols) + 1
    add_table(doc, table, [166 - 24 * n] + [24] * n,
              kinds=["header"] + ["line"] * (len(table) - 2) + ["sum"])

    doc.add_heading(w["disposition"], level=3)
    # One table, so the funds and the proposal stay on one page together.
    funds = [(labels[k], r.value(k)[0]) for k in FREE_KEYS if r.value(k)[0]]
    total = sum(v for _, v in funds)
    disp = spec.get("disposition") or {}
    dividend = disp.get("dividend") or 0
    forward = disp.get("carried_forward", total - dividend)
    prop = ([(w["dividend"], dividend)] if dividend else []) + [(w["forward"], forward)]
    rows = [[w["funds"], ""]] + [[lab, r.amount(v)] for lab, v in funds] + [[w["sum"], r.amount(total)]]
    rows += [[w["proposal"], ""]] + [[lab, r.amount(v)] for lab, v in prop]
    rows += [[w["sum"], r.amount(sum(v for _, v in prop))]]
    kinds = ["text"] + ["line"] * len(funds) + ["sum"] + ["text"] + ["line"] * len(prop) + ["sum"]
    if disp.get("statement"):          # the board's own statement on the dividend stays with the proposal
        rows.append([disp["statement"], ""])
        kinds.append("text")
    add_table(doc, rows, [166 - AMOUNT, AMOUNT], kinds=kinds)
    if dividend > r.free_equity():
        r.warnings.append("the dividend %s is larger than the unrestricted equity %s" % (dividend, r.free_equity()))

    def statement_table(srows, balance):
        head = [w["item"], w["note"]] + r.years(balance)[:1 if r.first else 2]
        table = [head] + [[a, b, c] + ([] if r.first else [d]) for a, b, c, d, _ in srows]
        kinds = ["header"] + [{"head": "group"}.get(k, k) for *_, k in srows]
        add_table(doc, table, [LABEL, NOTE, AMOUNT, AMOUNT][:len(head)], kinds=kinds, rule_from=2)

    part(w["income"])
    statement_table(r.statement(INCOME, False), False)
    # The balance sheet: assets on one page, equity and liabilities on the next.
    part(w["balance"])
    statement_table(r.statement([ASSETS], True), True)
    part(w["balance"])
    statement_table(r.statement([LIABILITIES], True), True)

    part(w["notes"])
    yrs = r.years(True)
    span = 1 if r.first else 2
    note_widths = [166 - AMOUNT * span, AMOUNT, AMOUNT]
    for n, title, kind, payload, _attach in r.notes:
        doc.add_heading("%s %d %s" % (w["note"], n, title), level=3)
        if kind == "principles":
            para(w["principles_text"])
            for line in payload:
                para(line)
        elif kind == "employees":
            add_table(doc, [["", yrs[0][:4]] + ([] if r.first else [yrs[1][:4]]),
                            [w["employees_row"], str(payload[0])]
                            + ([] if r.first else ["" if payload[1] is None else str(payload[1])])],
                      note_widths)
        elif kind == "fixed":
            table, kinds = [[""] + yrs[:span]], ["header"]
            for k, label in w["fa"]:
                c, p = payload[k]
                if k.startswith("=") or c or p:
                    table.append([label, r.amount(c or 0)] + ([] if r.first else
                                                              ["" if r.blank else r.amount(p or 0)]))
                    kinds.append("sum" if k.startswith("=") else "line")
            add_table(doc, table, note_widths, kinds=kinds)
        elif kind == "amounts":
            if not payload:
                para(w["none"])
            else:
                table = [[""] + yrs[:span]]
                for item in payload:
                    c, p = pair(item.get("amounts"))
                    table.append([item["label"], r.amount(c or 0)] + ([] if r.first else
                                                                     [r.amount(p if r.no_prior else p or 0)]))
                add_table(doc, table, note_widths)
        else:
            para(str(payload))

    s = spec["signing"]
    part(w["sign"])
    date = s.get("date") or "_" * 16     # declared unknown: dated by hand when the board signs
    para(w["signed"] % (s.get("place", ""), date) if s.get("place") else date)
    sig = doc.add_table(rows=(len(board) + 1) // 2, cols=2)
    sig.autofit = False
    for i, b in enumerate(board):
        cell = sig.cell(i // 2, i % 2)
        cell.width = Mm(83)
        p = cell.paragraphs[0]
        p.paragraph_format.space_before = Pt(34)
        p.add_run("_" * 32 + "\n")
        p.add_run(b["name"])
        if b.get("role"):
            p.add_run("\n" + b["role"])
    a = s.get("auditor")
    if a:
        p = para(w["auditor"] % (a.get("date") or date))
        p.paragraph_format.space_before = Pt(24)
        p = doc.add_paragraph()
        p.paragraph_format.space_before = Pt(34)
        p.add_run("_" * 32 + "\n")
        p.add_run(a["name"])
        p.add_run("\n" + (a.get("role") or w["auditor_role"]) + (", " + a["firm"] if a.get("firm") else ""))
    doc.save(out)
    return r


def line_keys(*trees):
    """The keys of the lines a layout has (INCOME, ASSETS, LIABILITIES): what the data file may give there."""
    out = set()
    for tree in trees:
        for node in (tree if isinstance(tree, list) else [tree]):
            out |= {leaf[0] for leaf in leaves(node) if leaf[0] and leaf[0] != "="}
    return out


def not_printed(spec):
    """Lines the data file gives that the layouts do not have: each would be left off the page and out of the
    sums, so each is an error by name."""
    out = []
    for part, known in (("income", line_keys(INCOME)), ("balance", line_keys(ASSETS, LIABILITIES))):
        for key in spec.get(part) or {}:
            if key not in known and not str(key).startswith("_"):
                out.append('"%s.%s" is not a line of the %s; its lines are: %s'
                           % (part, key, "income statement" if part == "income" else "balance sheet",
                              ", ".join(sorted(known))))
    assets = line_keys(ASSETS)
    for key in spec.get("fixed_assets") or {}:
        if key not in assets and not str(key).startswith("_"):
            out.append('"fixed_assets.%s" is not an asset line of the balance sheet' % key)
    return out


def main(argv):
    if len(argv) != 3:
        print(__doc__.split("\n\n")[1])
        return 2
    spec = json.loads(Path(argv[1]).read_text())
    out = Path(argv[2])
    if out.suffix.lower() != ".docx":
        raise SystemExit("output must end in .docx")
    # Nothing given is dropped: an unknown key, a value of the wrong shape or a line the layouts do not have
    # stops the build here.
    spec_guard.guard(spec, HERE.parent / "spec.fields.json", "annual report's data file")
    spec_guard.output_guard(out, __file__, "annual report")
    lost = not_printed(spec)
    if lost:
        raise SystemExit("the annual report's data file holds lines this report cannot print; nothing was built:\n"
                         "  - %s\nUse the layout's own line for each amount (a cost that has no line of its own "
                         "belongs to the nearest one, and a note can say what it holds), never leave an amount out."
                         % "\n  - ".join(lost))
    r = write_docx(spec, out)
    for i, year in enumerate(("this year", "last year")[:1 if r.blank else 2]):
        a, el = r.group_sum(ASSETS, i), r.group_sum(LIABILITIES, i)
        if a != el:
            r.warnings.append("%s total assets %s and equity and liabilities %s differ by %s; ask which figure is "
                              "wrong, never plug the gap" % (year, a, el, a - el))
    print(json.dumps({"file": str(out), "language": r.lang, "result": r.results["result"],
                      "total_assets": [r.group_sum(ASSETS, 0), r.group_sum(ASSETS, 1)],
                      "equity_and_liabilities": [r.group_sum(LIABILITIES, 0), r.group_sum(LIABILITIES, 1)],
                      "notes": len(r.notes), "warnings": r.warnings}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
