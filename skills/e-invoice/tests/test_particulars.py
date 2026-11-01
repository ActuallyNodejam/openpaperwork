"""A company's own particulars on its invoice (EINV-PARTICULARS): for every country the pack covers, a missing
particular is built and seen to fail, one the order declares unknown is seen to warn, and one the person's own
notes give and the page drops is seen to fail whatever the order declares.

    python3 -m unittest skills/e-invoice/tests/test_particulars.py

Standard library only: no validator, no network. Most tests read the page the builder writes as text; the
ones that run the pack check on a printed page need Chromium (the app's printer or Playwright) and pdftotext,
and skip without them.
"""
import contextlib
import copy
import html as html_lib
import io
import json
import re
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
PACK = HERE.parent
sys.path.insert(0, str(PACK / "scripts"))
sys.path.insert(0, str(PACK / "page"))
sys.path.insert(0, str(PACK.parent / "_checks"))
import countries  # noqa: E402
import einvoice_create  # noqa: E402
import einvoice_country as ec  # noqa: E402
import einvoice_external  # noqa: E402
import einvoice_particulars as part  # noqa: E402
import packcheck  # noqa: E402
import build_page  # noqa: E402

TEMPLATES = PACK / "templates"


def spec(name):
    return json.loads((TEMPLATES / (name + "-spec.json")).read_text())


def swedish():
    """The pack has no Swedish starter of its own: the plain one, sold by an aktiebolag."""
    s = spec("invoice")
    s["seller"].update(name="Exempel Tryck AB", legal_form="AB", street="Verkstadsgatan 7", postcode="417 07",
                       city="Göteborg", vat_id="SE556677889901", register_number="556677-8899",
                       registered_office="Göteborg")
    return s


def can_print():
    if not shutil.which("pdftotext"):
        return False
    if shutil.which("nodejam-print"):
        return True
    try:
        import playwright  # noqa: F401
        return True
    except ImportError:
        return False


def page_html(s):
    locale = build_page.page_locale_for(build_page.locale_of_order(s)[0])
    return build_page.on_layout(build_page.paper_for(build_page.build(s, locale), locale), s), locale


def page_text(s):
    """The words of the page the builder writes for an order, as a reader of the print would have them."""
    text = page_html(s)[0]
    text = re.sub(r"(?is)<(script|style|head)\b.*?</\1>", " ", text)
    text = re.sub(r"(?i)<(br|/p|/div|/li|/tr|/dd|/dt|/h\d|/td|/th)\b[^>]*>", "\n", text)
    return html_lib.unescape(re.sub(r"<[^>]+>", " ", text))


def judged(s, files=(), page=None):
    return part.judge(s, page_text(s) if page is None else page, files)


def without(s, *keys):
    s = copy.deepcopy(s)
    for key in keys:
        s["seller"].pop(key, None)
    return s


def unknown(s, *keys):
    s = without(s, *keys)
    s["seller"]["unknown"] = list(keys)
    return s


def notes_for(s, words):
    """The person's notes: the seller by name with the particular, the buyer in a paragraph of its own."""
    return [("notes.txt", "Invoice to write\n\nSeller: %s, %s\n%s\n\nCustomer: %s\n"
             % (s["seller"]["name"], s["seller"].get("city", ""), words, s["buyer"]["name"]))]


# country: (starter, the particular taken out, a word of its article, the person's notes that give it)
NUMBERED = {
    "FR": ("facture", "share_capital", "R123-238", "SAS au capital de 10 000 euros"),
    "BE": ("be-factuur", "register", "art. 2:20", "RPR Antwerpen, afdeling Antwerpen"),
    "NL": ("nl-factuur", "registered_office", "Burgerlijk Wetboek 2:186", "Statutair gevestigd te Utrecht"),
    "ES": ("es-factura", "register_number", "art. 24",
           "Inscrita en el Registro Mercantil de Madrid, tomo 0000, folio 000, hoja M-000000"),
    "IT": ("it-fattura", "share_capital", "art. 2250", "Capitale sociale 10.000,00 euro interamente versato"),
    "SE": (None, "registered_office", "28 kap. 5 §", "Styrelsens säte: Göteborg"),
    "AU": ("au-tax-invoice", "acn", "s 153", "ACN 000 000 000"),
}
NOT_ENFORCED = {"DE": ("xrechnung-credit-note", "35a"), "AT": ("at-rechnung", "UGB § 14"),
                "PL": ("pl-faktura", "art. 206"), "FI": ("fi-lasku", "244/2001"), "US": ("us-invoice", "federal")}
# country: (starter, what is cut from the page, a word of its article)
PRINTED_ONLY = {
    "NO": ("no-faktura", "Foretaksregisteret", "§ 5-1-2"),
    "DK": ("dk-faktura", "12345674", "§ 2, stk. 4"),
    "GB": ("uk-vat-invoice", "Example Studio Ltd", "reg. 24"),
    "IE": ("ie-vat-invoice", "Liffey Example Ltd", "s. 49"),
    "CA": ("ca-invoice", "Example Maple Software Inc.", "s. 10(5)"),
}


def order(cc):
    name = NUMBERED[cc][0]
    return spec(name) if name else swedish()


class Law(unittest.TestCase):
    def test_all_seventeen_countries_are_decided(self):
        """Every country the pack covers is either enforced under a named statute or named as not reaching
        an invoice; none is left to chance."""
        decided = set(part.LAW) | set(part.NOT_ON_INVOICES)
        self.assertEqual(decided, {"DE", "FR", "SE", "NO", "DK", "FI", "GB", "AU", "CA", "US", "BE", "NL", "AT",
                                   "IE", "ES", "IT", "PL"})
        self.assertEqual(set(NUMBERED) | set(PRINTED_ONLY), set(part.LAW))
        self.assertEqual(set(NOT_ENFORCED), set(part.NOT_ON_INVOICES))

    def test_the_rule_is_registered(self):
        owned = set(packcheck.SKILL_RULES["e-invoice"])
        for rule in part.RULES + ec.RULES + einvoice_external.RULES:
            self.assertIn(rule, owned, "%s is defined and the pack check never runs it" % rule)
        for rule in part.RULES:
            self.assertEqual(packcheck.MODULES.get(rule.split("-")[0]), "einvoice_page", rule)

    def test_where_the_statute_stops_at_letters_nothing_is_owed_on_an_invoice(self):
        for cc, (name, word) in NOT_ENFORCED.items():
            with self.subTest(cc):
                bare = without(spec(name), "register", "register_number", "registered_office", "share_capital",
                               "managing_directors")
                passed, why = judged(bare)
                self.assertIsNone(passed, why)
                self.assertIn(word, why)
                self.assertEqual(part.builder_warnings(bare), [])

    def test_a_form_the_statute_does_not_name_owes_nothing(self):
        sole = spec("facture")
        sole["seller"].update(name="Atelier Exemple", legal_form="EI")
        self.assertIsNone(judged(without(sole, "share_capital", "rcs"))[0])
        plain = swedish()
        plain["seller"].update(name="Example Seller Ltd", legal_form="")
        plain["seller"].pop("further", None)
        # No company statute is read for it; the F-skatt question for a Swedish seller is only ever a WARN.
        passed, why = judged(without(plain, "register_number", "registered_office"))
        self.assertTrue(passed and why.startswith("WARN") and "F-skatt" in why, why)

    def test_an_snc_states_no_capital(self):
        """Code de commerce R123-238 1° and 2° ask a société en nom collectif for its form, not its capital."""
        snc = without(spec("facture"), "share_capital")
        snc["seller"].update(name="Atelier Exemple SNC", legal_form="SNC")
        self.assertTrue(judged(snc)[0], judged(snc)[1])
        self.assertEqual([m for m in einvoice_create.refuse_french(snc)[0] if "share_capital" in m], [])


class Starters(unittest.TestCase):
    def test_every_starter_states_what_its_statute_asks(self):
        for path in sorted(TEMPLATES.glob("*-spec.json")):
            s = json.loads(path.read_text())
            with self.subTest(path.name):
                passed, why = judged(s)
                self.assertIsNot(passed, False, why)
                # A Swedish starter may carry the one F-skatt line a WARN: its status is the person's to give.
                self.assertFalse(str(why).startswith("WARN") and "F-skatt" not in str(why), why)
                self.assertEqual(part.builder_warnings(s), [])
                cc = part.country_of(s["seller"])
                if cc in part.LAW and part.form_of(s["seller"], cc):
                    self.assertTrue(passed, "%s: a company in %s is judged, not passed over" % (path.name, cc))


class Missing(unittest.TestCase):
    def test_a_missing_particular_fails_with_its_article(self):
        for cc, (_name, key, article, _notes) in NUMBERED.items():
            with self.subTest(cc):
                self.assertTrue(judged(order(cc))[0])
                passed, why = judged(without(order(cc), key))
                self.assertIs(passed, False, why)
                self.assertIn("seller.%s" % key, why)
                self.assertIn(article, why)
                self.assertIn('"unknown": ["%s"]' % key, why)
                self.assertIn("never make one up", why)

    def test_what_the_page_itself_drops_fails(self):
        """Where nothing can be left out of the order (a word the builder writes, a number the tax rules ask
        for too, the name), the page is cut instead."""
        for cc, (name, cut, article) in PRINTED_ONLY.items():
            with self.subTest(cc):
                s = spec(name)
                self.assertTrue(judged(s)[0], judged(s)[1])
                passed, why = judged(s, page=page_text(s).replace(cut, ""))
                self.assertIs(passed, False, why)
                self.assertIn(article, why)
                self.assertNotIn('"unknown"', why)

    def test_given_in_the_order_and_cut_from_the_page_fails(self):
        s = spec("it-fattura")
        page = page_text(s).replace("Registro delle Imprese di Milano", "")
        passed, why = judged(s, page=page)
        self.assertIs(passed, False)
        self.assertIn("not on the page", why)

    def test_an_australian_abn_that_ends_in_the_acn_stands_for_it(self):
        """s 153(2)(b): the ABN may stand for the ACN when its last nine digits are the ACN."""
        s = spec("au-tax-invoice")
        s["seller"].update(acn="345 678 012")              # the starter's ABN is 12 345 678 012
        page = re.sub(r"ACN[^\n]*", "", page_text(s))
        self.assertTrue(judged(s, page=page)[0])
        s["seller"].update(acn="000 000 000")
        self.assertIs(judged(s, page=page)[0], False)

    def test_liquidation_and_a_sole_shareholder_are_owed_when_they_are_so(self):
        for cc, words in (("IT", "In liquidazione"), ("FR", "Société en liquidation"), ("SE", "I likvidation"),
                          ("BE", "In vereffening"), ("ES", "En liquidación")):
            with self.subTest(cc):
                s = order(cc)
                s["seller"]["in_liquidation"] = True
                self.assertIn(words, page_text(s))
                self.assertTrue(judged(s)[0], judged(s)[1])
                passed, why = judged(s, page=page_text(s).replace(words, ""))
                self.assertIs(passed, False, why)
        norway = spec("no-faktura")
        norway["seller"]["in_liquidation"] = True
        self.assertIn("Under avvikling", page_text(norway))
        italy = spec("it-fattura")
        italy["seller"]["rea"].update(sole_shareholder=True, in_liquidation=True)
        text = page_text(italy)
        self.assertIn("unico socio", text)
        self.assertIn("In liquidazione", text)
        self.assertTrue(judged(italy)[0], judged(italy)[1])

    def test_spain_names_the_paid_up_capital_beside_the_subscribed(self):
        s = spec("es-factura")
        s["seller"]["share_capital"] = "3.000,00 euros"
        passed, why = judged(s)
        self.assertIs(passed, False)
        self.assertIn("paid_up_capital", why)
        s["seller"]["paid_up_capital"] = "3.000,00 euros"
        self.assertTrue(judged(s)[0], judged(s)[1])


class Unknown(unittest.TestCase):
    def test_a_declared_unknown_warns_and_prints_nothing(self):
        for cc, (_name, key, article, _notes) in NUMBERED.items():
            with self.subTest(cc):
                s = unknown(order(cc), key)
                passed, why = judged(s)
                self.assertIs(passed, True, why)
                self.assertTrue(why.startswith("WARN "), why)
                self.assertIn("not complete without it", why)
                self.assertIn(article, why)
                warnings = part.builder_warnings(s)
                self.assertEqual(len(warnings), 1, warnings)
                self.assertIn("declared unknown", warnings[0])

    def test_unknown_at_the_top_of_the_order_reads_the_same(self):
        s = without(spec("it-fattura"), "share_capital")
        s["unknown"] = ["share_capital"]
        self.assertTrue(judged(s)[1].startswith("WARN "))

    def test_the_page_prints_nothing_in_its_place(self):
        italy = unknown(spec("it-fattura"), "share_capital", "register", "register_number")
        text = page_text(italy)
        self.assertNotIn("Capitale sociale", text)
        self.assertNotIn("Registro delle Imprese", text)
        france = unknown(spec("facture"), "share_capital", "rcs")
        text = page_text(france)
        self.assertNotIn("capital", text.lower())
        self.assertNotIn("RCS", text)
        self.assertIn("SAS", text)

    def test_what_the_tax_rules_ask_for_too_cannot_be_declared_unknown(self):
        """The SIREN (CGI annexe II 242 nonies A) and the Danish CVR (momsbekendtgørelsen § 58) are not the
        company statute's alone; neither is the company's own name."""
        for name, key in (("facture", "siren"), ("dk-faktura", "cvr"), ("uk-vat-invoice", "name")):
            with self.subTest(name):
                s = unknown(spec(name), key)
                s["seller"].pop("vat_id", None)
                passed, why = judged(s)
                self.assertIs(passed, False, why)
                self.assertNotIn('"unknown": ["%s"]' % key, why)

    def test_the_french_builder_no_longer_refuses_a_capital_nobody_gave(self):
        """It refused, which left a model one way on: to make one up."""
        bare = without(spec("facture"), "share_capital", "rcs")
        missing = einvoice_create.refuse_french(bare)[0]
        self.assertEqual(len([m for m in missing if "never make one up" in m]), 2, missing)
        self.assertEqual(einvoice_create.refuse_french(unknown(spec("facture"), "share_capital", "rcs"))[0], [])

    def test_the_dutch_kvk_number_may_be_unknown_on_a_page_printed_alone(self):
        s = unknown(spec("nl-factuur"), "register_number")
        # Declared unknown, it is no stop: a warning names it, the page is written and the XML (not valid without it) is not.
        self.assertEqual([m for m in countries.refuse(s)[0] if "register_number" in m], [])
        self.assertTrue(any("seller.register_number is declared unknown" in w for w in countries.refuse(s)[1]))
        self.assertEqual(countries.xml_blocked(s), ["seller.register_number"])
        self.assertIsNone(einvoice_create.document_xml(s)[0])
        undeclared = without(spec("nl-factuur"), "register_number")
        self.assertIn("unknown", " ".join(countries.refuse(undeclared)[0]))
        ok, why = ec.nl_invoice(s, page_text(s), None)
        self.assertTrue(ok, why)
        self.assertTrue(judged(s)[1].startswith("WARN "))
        gone = without(spec("nl-factuur"), "register_number")
        self.assertFalse(ec.nl_invoice(gone, page_text(gone), None)[0])


class Notes(unittest.TestCase):
    def test_given_in_the_notes_and_dropped_fails_whatever_the_order_declares(self):
        for cc, (_name, key, _article, words) in NUMBERED.items():
            with self.subTest(cc):
                s = unknown(order(cc), key)
                files = notes_for(s, words)
                passed, why = judged(s, files)
                self.assertIs(passed, False, why)
                self.assertIn("notes.txt", why)
                self.assertIn("seller.%s" % key, why)
                self.assertIn("cannot be declared unknown", why)
                self.assertNotIn('"unknown": [', why)
                # The same notes and a page that states it: nothing to say.
                self.assertTrue(judged(order(cc), files)[0])

    def test_the_wave_nine_proof(self):
        """The run that passed every rule while it had dropped what the notes gave (2026-10-09)."""
        s = without(spec("it-fattura"), "register", "register_number", "share_capital", "registered_office", "rea")
        notes = [("notes.txt", "Fattura da fare (appunti)\n\n"
                  "Venditore: Esempio Stampa S.r.l., Via Esempio 12, 20121 Milano (MI), Italia.\n"
                  "Partita IVA e codice fiscale 01234567897, regime fiscale ordinario.\n"
                  "Registro delle Imprese di Milano Monza Brianza Lodi n. 01234567897, REA MI-0000000,\n"
                  "capitale sociale 10.000,00 euro interamente versato, più soci, non in liquidazione.\n\n"
                  "Cliente: %s, Corso Campione 8, 10121 Torino (TO), Italia.\n" % s["buyer"]["name"])]
        passed, why = judged(s, notes)
        self.assertIs(passed, False)
        for key in ("seller.register", "seller.register_number", "seller.share_capital"):
            self.assertIn(key, why)
        self.assertNotIn("liquidation", why)               # "non in liquidazione" is not a liquidation
        self.assertNotIn("sole shareholder", why)          # "più soci" is not a sole shareholder
        fixed = copy.deepcopy(s)
        fixed["seller"].update(register="Registro delle Imprese di Milano Monza Brianza Lodi",
                               register_number="01234567897", share_capital="10.000,00 euro i.v.")
        self.assertTrue(judged(fixed, notes)[0], judged(fixed, notes)[1])

    def test_liquidation_in_the_notes_and_not_on_the_page_fails(self):
        for cc, words in (("IT", "La società è in liquidazione."), ("SE", "Bolaget är i likvidation.")):
            with self.subTest(cc):
                passed, why = judged(order(cc), notes_for(order(cc), words))
                self.assertIs(passed, False, why)
                self.assertIn("in_liquidation", why)
        norway = spec("no-faktura")
        self.assertIs(judged(norway, notes_for(norway, "Selskapet er under avvikling."))[0], False)
        self.assertTrue(judged(norway, notes_for(norway, "Selskapet er ikke under avvikling."))[0])

    def test_the_customers_particulars_are_not_the_sellers(self):
        s = unknown(spec("it-fattura"), "share_capital")
        notes = [("notes.txt", "Venditore: %s, Milano.\n\nCliente: %s, capitale sociale 50.000,00 euro i.v., "
                  "Registro delle Imprese di Torino n. 09876543217.\n" % (s["seller"]["name"], s["buyer"]["name"]))]
        self.assertTrue(judged(s, notes)[1].startswith("WARN "))
        # One paragraph for both: only what stands between the seller's name and the customer's is the seller's.
        notes = [("notes.txt", "Venditore: %s, capitale sociale 10.000,00 euro. Cliente: %s, capitale sociale "
                  "50.000,00 euro.\n" % (s["seller"]["name"], s["buyer"]["name"]))]
        passed, why = judged(s, notes)
        self.assertIs(passed, False)
        self.assertIn("10.000,00", why)
        # A file that names neither says nothing of the seller.
        self.assertTrue(judged(s, [("other.txt", "capitale sociale 99.000,00 euro")])[1].startswith("WARN "))

    def test_the_order_and_the_pages_own_files_are_not_the_persons_notes(self):
        folder = Path(tempfile.mkdtemp())
        s = spec("it-fattura")
        (folder / "order.json").write_text(json.dumps(s, ensure_ascii=False))
        (folder / "case.json").write_text(json.dumps({"truth": s}, ensure_ascii=False))
        (folder / "invoice.html").write_text(page_html(s)[0])
        (folder / "invoice.xml").write_text("<x>capitale sociale 10.000,00</x>")
        (folder / "earlier.html").write_text(page_html(s)[0])              # another page a builder wrote
        (folder / ".hidden").mkdir()
        (folder / ".hidden" / "notes.txt").write_text("capitale sociale 1,00")
        (folder / "appunti.txt").write_text("Esempio Stampa S.r.l., capitale sociale 10.000,00 euro")
        self.assertEqual([name for name, _ in part.evidence_files(folder / "invoice.pdf")], ["appunti.txt"])
        other = Path(tempfile.mkdtemp())
        (other / "sub").mkdir()
        (other / "sub" / "azienda.md").write_text("Esempio Stampa S.r.l.")
        self.assertEqual([name for name, _ in part.evidence_files(folder / "invoice.pdf", str(other))],
                         ["sub/azienda.md"])


class CaseTruth(unittest.TestCase):
    """A library case carries a truth beside the page. It may say less than the order (it lists what it
    compares) or more (what the person's files give and a model left out)."""

    def beside(self, order, truth):
        folder = Path(tempfile.mkdtemp())
        (folder / "order.json").write_text(json.dumps(order, ensure_ascii=False))
        return part.source(folder / "invoice.pdf", {"truth": truth}, "first")

    def test_the_order_and_the_truth_are_read_together(self):
        order = spec("it-fattura")
        thin = {"doc": "invoice", "lines": order["lines"], "seller": {"name": order["seller"]["name"], "country": "IT"}}
        src, made_up = self.beside(order, thin)
        self.assertEqual(src["seller"]["register_number"], order["seller"]["register_number"])
        self.assertEqual(made_up, [])
        # The truth gives the capital and the model's order dropped it: it is still owed on the page.
        src, _ = self.beside(without(order, "share_capital"), dict(order, doc="invoice"))
        self.assertEqual(src["seller"]["share_capital"], order["seller"]["share_capital"])
        self.assertIs(part.judge(src, page_text(without(order, "share_capital")))[0], False)

    def test_a_particular_the_truth_lists_as_unknown_and_the_order_gives_was_made_up(self):
        truth = dict(unknown(spec("au-tax-invoice"), "acn"), doc="invoice")
        src, made_up = self.beside(spec("au-tax-invoice"), truth)
        self.assertEqual(made_up, ["acn"])
        src, made_up = self.beside(unknown(spec("au-tax-invoice"), "acn"), truth)
        self.assertEqual(made_up, [])
        self.assertTrue(part.judge(src, page_text(unknown(spec("au-tax-invoice"), "acn")))[1].startswith("WARN "))

    def test_a_truth_without_the_sellers_address_leaves_the_seat_to_the_tax_rules(self):
        s = spec("facture")
        for key in ("street", "postcode", "city"):
            s["seller"].pop(key)
        self.assertTrue(part.judge(s, page_text(spec("facture")))[0])


@unittest.skipUnless(can_print(), "needs Chromium and pdftotext")
class PackCheck(unittest.TestCase):
    """The whole road: a printed page, the order beside it, the person's notes, the pack check's own lines."""

    def folder(self, s, notes=None, where=None):
        folder = Path(tempfile.mkdtemp())
        (folder / "order.json").write_text(json.dumps(s, ensure_ascii=False))
        page, locale = page_html(s)
        (folder / "invoice.html").write_text(page)
        build_page.print_pdf(folder / "invoice.html", folder / "invoice.pdf", build_page.paper_of(locale))
        if notes:
            (where or folder).joinpath("notes.txt").write_text(notes)
        return folder / "invoice.pdf"

    def run_check(self, pdf, *more):
        out, argv = io.StringIO(), sys.argv
        sys.argv = ["packcheck.py", "e-invoice", str(pdf)] + list(more)
        try:
            with contextlib.redirect_stdout(out):
                code = packcheck.main()
        finally:
            sys.argv = argv
        lines = [line for line in out.getvalue().splitlines() if "EINV-PARTICULARS" in line]
        return code, lines, out.getvalue()

    NOTES = ("Venditore: Esempio Stampa S.r.l., Via Esempio 12, 20121 Milano.\n"
             "Registro delle Imprese di Milano n. 01234567897, capitale sociale 10.000,00 euro i.v.\n")

    def test_missing_fails_unknown_warns_and_the_notes_close_the_way_out(self):
        full = spec("it-fattura")
        code, lines, text = self.run_check(self.folder(full))
        self.assertEqual(lines, [], text)

        gone = without(full, "share_capital", "register", "register_number", "rea")
        code, lines, text = self.run_check(self.folder(gone))
        self.assertEqual(len(lines), 1, text)
        self.assertTrue(lines[0].startswith("FAIL EINV-PARTICULARS"), lines[0])
        self.assertIn("art. 2250", lines[0])
        self.assertEqual(code, 1)

        declared = unknown(full, "share_capital", "register", "register_number")
        declared["seller"].pop("rea")
        code, lines, text = self.run_check(self.folder(declared))
        self.assertEqual(len(lines), 1, text)
        self.assertTrue(lines[0].startswith("WARN EINV-PARTICULARS"), lines[0])
        self.assertNotIn("FAIL EINV-PARTICULARS", text)

        # The person's notes beside the page give them: the same order fails.
        code, lines, text = self.run_check(self.folder(declared, self.NOTES))
        self.assertTrue(lines and lines[0].startswith("FAIL EINV-PARTICULARS"), text)
        self.assertIn("notes.txt", lines[0])
        self.assertEqual(code, 1)

    def test_the_folder_named_with_in_is_the_one_read(self):
        declared = unknown(spec("it-fattura"), "share_capital")
        declared["seller"]["rea"].pop("share_capital")
        elsewhere = Path(tempfile.mkdtemp())
        pdf = self.folder(declared, self.NOTES, where=elsewhere)
        code, lines, text = self.run_check(pdf)
        self.assertTrue(lines and lines[0].startswith("WARN "), text)
        code, lines, text = self.run_check(pdf, "--in", str(elsewhere))
        self.assertTrue(lines and lines[0].startswith("FAIL "), text)
        self.assertIn("share_capital", lines[0])

    def test_a_printed_footer_that_wraps_is_still_read(self):
        """The Belgian register line and the Spanish entry run over two footer lines beside two other columns."""
        for name in ("be-factuur", "es-factura", "it-fattura", "facture", "nl-factuur", "au-tax-invoice"):
            with self.subTest(name):
                pdf = self.folder(spec(name))
                passed, why = part.check("EINV-PARTICULARS", pdf, {}, "first")
                self.assertIs(passed, True, why)


if __name__ == "__main__":
    unittest.main()
