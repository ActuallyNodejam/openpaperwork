"""Spain, Italy and Poland (wave 9): each kind of mistake is built and seen caught.

    python3 -m unittest skills/e-invoice/tests/test_es_it_pl.py

Standard library only: no validator, no network. The tests that read a printed page need Chromium (the
app's printer or Playwright) and pdftotext, and skip without them.
"""
import copy
import json
import re
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from xml.etree import ElementTree as ET

HERE = Path(__file__).resolve().parent
PACK = HERE.parent
sys.path.insert(0, str(PACK / "scripts"))
sys.path.insert(0, str(PACK / "page"))
sys.path.insert(0, str(PACK.parent / "_checks"))
import countries  # noqa: E402
import einvoice_create  # noqa: E402
import facturae_create  # noqa: E402
import fatturapa_create  # noqa: E402
import fetch_validators  # noqa: E402
import ksef_create  # noqa: E402
import einvoice_ids as ids  # noqa: E402
import einvoice_country as ec  # noqa: E402
import einvoice_external  # noqa: E402
import einvoice_page  # noqa: E402
import packcheck  # noqa: E402
import build_page  # noqa: E402
import format as page_format  # noqa: E402

TEMPLATES = PACK / "templates"
STARTERS = ("es-factura", "es-factura-rectificativa", "it-fattura", "it-nota-di-credito", "pl-faktura",
            "pl-faktura-korygujaca")


def spec(name):
    return json.loads((TEMPLATES / (name + "-spec.json")).read_text())


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


def printed(s, edit=None, with_xml=False, case=None):
    """The page of an order printed in a folder of its own, the order beside it (and the national file when
    asked): (pdf, html text)."""
    folder = Path(tempfile.mkdtemp())
    (folder / "order.json").write_text(json.dumps(s, ensure_ascii=False))
    html, locale = page_html(s)
    if edit:
        html = edit(html)
    (folder / "invoice.html").write_text(html)
    build_page.print_pdf(folder / "invoice.html", folder / "invoice.pdf", build_page.paper_of(locale))
    if with_xml:
        (folder / "invoice.xml").write_bytes(einvoice_create.document_xml(s)[0])
    if case is not None:
        (folder / "case.json").write_text(json.dumps(case, ensure_ascii=False))
    return folder / "invoice.pdf", html


def refused(test, s, words):
    with test.assertRaises(SystemExit) as caught:
        einvoice_create.document_xml(s)
    test.assertIn(words, str(caught.exception))


def xml_of(s):
    data, summary, syntax = einvoice_create.document_xml(s)
    return ET.fromstring(data), summary, syntax


def texts(root, name):
    return [(el.text or "").strip() for el in root.iter() if el.tag.split("}")[-1] == name]


class Identifiers(unittest.TestCase):
    def test_forms_and_check_characters(self):
        for good in ("B12345674", "ESB12345674", "A99999997", "12345678Z", "X1234567L", "ES-B-12345674"):
            self.assertTrue(ids.es_nif_form(good) and ids.es_nif_ok(good), good)
        self.assertTrue(ids.es_nif_form("B12345675"))                  # the form holds, the control character does not
        self.assertFalse(ids.es_nif_ok("B12345675"))
        self.assertFalse(ids.es_nif_form("B1234567"))                  # eight characters
        self.assertFalse(ids.es_nif_form("I12345674"))                 # I is no legal-form key (Orden EHA/451/2008 art. 3)
        self.assertTrue(ids.es_nif_person("12345678Z"))
        self.assertFalse(ids.es_nif_person("B12345674"))
        self.assertTrue(ids.it_piva_form("IT01234567897") and ids.it_piva_ok("IT01234567897"))
        self.assertTrue(ids.it_piva_form("01234567890"))
        self.assertFalse(ids.it_piva_ok("01234567890"))
        self.assertFalse(ids.it_piva_form("IT0123456789"))
        self.assertTrue(ids.it_cf_form("RSSMRA80A01H501U") and ids.it_cf_form("01234567897"))
        self.assertTrue(ids.pl_nip_form("PL 123-456-32-18") and ids.pl_nip_ok("1234563218"))
        self.assertTrue(ids.pl_nip_ok("9876543210"))
        self.assertTrue(ids.pl_nip_form("1234563219"))
        self.assertFalse(ids.pl_nip_ok("1234563219"))
        self.assertFalse(ids.pl_nip_form("0234563218"))                # FA(3)'s own pattern: no leading zero
        self.assertEqual(ids.pl_nip_text("PL1234563218"), "123-456-32-18")

    def test_a_check_digit_that_does_not_hold_warns_and_never_refuses(self):
        """None of the three formulas was read from an official text, so the form refuses and the digit warns."""
        for name, wrong in (("es-factura", "ESB12345675"), ("it-fattura", "IT01234567890"), ("pl-faktura", "PL1234563219")):
            s = spec(name)
            s["seller"]["vat_id"] = wrong
            missing, warnings = countries.refuse(s)
            self.assertEqual(missing, [], name)
            self.assertTrue(any("check" in w and wrong in w for w in warnings), (name, warnings))
        for name, bad in (("es-factura", "ESB1234567"), ("it-fattura", "IT0123456789"), ("pl-faktura", "PL123456321")):
            s = spec(name)
            s["seller"]["vat_id"] = bad
            self.assertTrue(any("seller.vat_id" in m for m in countries.refuse(s)[0]), name)


class Files(unittest.TestCase):
    def test_each_country_gets_its_national_file(self):
        roots = {"es-factura": ("facturae", "{%s}Facturae" % facturae_create.NS),
                 "it-fattura": ("fatturapa", "{%s}FatturaElettronica" % fatturapa_create.NS),
                 "pl-faktura": ("ksef", "{%s}Faktura" % ksef_create.NS)}
        for name, (syntax, tag) in roots.items():
            root, summary, got = xml_of(spec(name))
            self.assertEqual((got, root.tag), (syntax, tag), name)
            self.assertEqual(einvoice_external.syntax_of_xml(ET.tostring(root)), syntax, name)
            self.assertIn(syntax, einvoice_external.BESIDE)
        # The EN 16931 syntaxes stay one word away.
        self.assertEqual(xml_of(dict(spec("es-factura"), syntax="cii"))[2], "cii")

    def test_no_file_claims_what_the_pack_does_not_do(self):
        root, summary, _ = xml_of(spec("es-factura"))
        self.assertFalse([el for el in root.iter() if el.tag.endswith("}Signature")])       # unsigned, and it says so
        self.assertIs(summary["signed"], False)
        self.assertTrue(any("not signed" in w and "XAdES" in w for w in summary["warnings"]))
        for name, where in (("it-fattura", "Sistema di Interscambio"), ("pl-faktura", "Krajowy System e-Faktur")):
            root, summary, _ = xml_of(spec(name))
            self.assertIs(summary["sent"], False)
            self.assertTrue(any("not sent" in w and where in w for w in summary["warnings"]), name)
        self.assertEqual(texts(xml_of(spec("pl-faktura"))[0], "NrKSeF"), [])                 # no KSeF number of its own

    def test_spanish_invoice_and_rectifying_invoice(self):
        root, summary, _ = xml_of(spec("es-factura"))
        self.assertEqual(texts(root, "InvoiceClass"), ["OO"])
        self.assertEqual(texts(root, "InvoiceSeriesCode"), ["A"])
        self.assertEqual(texts(root, "TaxIdentificationNumber"), ["B12345674", "A99999997"])
        self.assertEqual((summary["total_excluding_vat"], summary["total_vat"], summary["total_including_vat"]),
                         ("4036.00", "748.96", "4784.96"))
        self.assertEqual(texts(root, "InvoiceTotal"), ["4784.96"])
        root, summary, _ = xml_of(spec("es-factura-rectificativa"))
        # Real Decreto 1619/2012 art. 15.5: the rectification itself, with its sign.
        self.assertEqual(texts(root, "InvoiceClass"), ["OR"])
        self.assertEqual(texts(root, "Quantity"), ["-200.00"])
        self.assertEqual(texts(root, "InvoiceTotal"), ["-445.28"])
        self.assertEqual(summary["total_including_vat"], "-445.28")
        corrective = next(el for el in root.iter() if el.tag == "Corrective")
        self.assertEqual([corrective.findtext(k) for k in ("InvoiceNumber", "InvoiceSeriesCode", "ReasonCode", "ReasonDescription",
                                                           "CorrectionMethod", "InvoiceIssueDate")],
                         ["2026-0142", "A", "16", "Base imponible", "02", "2026-10-09"])

    def test_spain_refuses_what_only_the_person_can_give(self):
        s = spec("es-factura")
        refused(self, dict(s, buyer={k: v for k, v in s["buyer"].items() if k != "vat_id"}), "art. 6.1 d 3.º")
        refused(self, dict(s, seller={k: v for k, v in s["seller"].items() if k != "province"}), "seller.province")
        r = spec("es-factura-rectificativa")
        refused(self, {k: v for k, v in r.items() if k != "series"}, "art. 6.1 a 2.º")
        refused(self, {k: v for k, v in r.items() if k != "correction"}, "correction.reason_code")
        refused(self, {k: v for k, v in r.items() if k != "preceding_invoice"}, "preceding_invoice")
        exempt = copy.deepcopy(s)
        exempt["lines"][0].update(vat_category="E", vat_rate=0)
        refused(self, exempt, "art. 6.1 j")

    def test_italian_invoice_and_credit_note(self):
        root, summary, _ = xml_of(spec("it-fattura"))
        self.assertEqual(root.get("versione"), "FPR12")
        self.assertEqual(texts(root, "TipoDocumento"), ["TD01"])
        self.assertEqual(texts(root, "CodiceDestinatario"), ["ABC1234"])
        self.assertEqual(texts(root, "RegimeFiscale"), ["RF01"])
        self.assertEqual(texts(root, "ImportoTotaleDocumento"), ["4819.52"])
        self.assertEqual(texts(root, "EsigibilitaIVA"), ["I", "I"])
        root, summary, _ = xml_of(spec("it-nota-di-credito"))
        self.assertEqual(texts(root, "TipoDocumento"), ["TD04"])                 # the type carries the sign
        self.assertEqual(texts(root, "ImportoTotaleDocumento"), ["448.96"])
        linked = next(el for el in root.iter() if el.tag == "DatiFattureCollegate")
        self.assertEqual((linked.findtext("IdDocumento"), linked.findtext("Data")), ("2026/118", "2026-10-09"))

    def test_italy_split_payment_stamp_duty_and_public_buyer(self):
        s = spec("it-fattura")
        pa = copy.deepcopy(s)
        pa.update(public_buyer=True, split_payment=True)
        pa["buyer"]["recipient_code"] = "UFABCD"
        root, _, _ = xml_of(pa)
        self.assertEqual(root.get("versione"), "FPA12")
        self.assertEqual(set(texts(root, "EsigibilitaIVA")), {"S"})
        self.assertEqual(texts(root, "ImportoPagamento"), ["4036.00"])           # the customer pays the net alone
        self.assertIn(countries.IT_SPLIT, page_html(pa)[0])
        refused(self, dict(pa, buyer=dict(pa["buyer"], recipient_code="ABC1234")), "six characters")
        stamped = copy.deepcopy(s)
        for l in stamped["lines"]:
            l.update(vat_category="E", vat_rate=0, nature="N4", exemption_reason="Operazione esente, art. 10 DPR 633/1972")
        self.assertTrue(any("imposta di bollo" in w for w in countries.refuse(stamped)[1]))
        stamped["stamp_duty"] = 2
        root, _, _ = xml_of(stamped)
        self.assertEqual((texts(root, "BolloVirtuale"), texts(root, "ImportoBollo")), (["SI"], ["2.00"]))
        self.assertEqual(set(texts(root, "Natura")), {"N4"})
        self.assertIn(countries.IT_STAMP, page_html(stamped)[0])

    def test_italy_refuses_what_only_the_person_can_give(self):
        s = spec("it-fattura")
        refused(self, dict(s, seller={k: v for k, v in s["seller"].items() if k != "tax_regime"}), "seller.tax_regime")
        refused(self, dict(s, buyer={k: v for k, v in s["buyer"].items() if k != "vat_id"}), "art. 21 comma 2 f")
        consumer = dict(s, buyer=dict({k: v for k, v in s["buyer"].items() if k not in ("vat_id", "recipient_code")},
                                      tax_code="RSSMRA80A01H501U"))
        root, summary, _ = xml_of(consumer)
        self.assertEqual(texts(root, "CodiceDestinatario"), ["0000000"])
        self.assertTrue(any("0000000" in w for w in summary["warnings"]))
        untaxed = copy.deepcopy(s)
        untaxed["lines"][0].update(vat_category="AE", vat_rate=0)
        refused(self, untaxed, "line 1 nature")
        untaxed["lines"][0]["nature"] = "N6.3"
        root, _, _ = xml_of(untaxed)
        self.assertIn("N6.3", texts(root, "Natura"))
        self.assertIn("Inversione contabile", page_html(untaxed)[0])

    def test_polish_invoice_and_correcting_invoice(self):
        root, summary, _ = xml_of(spec("pl-faktura"))
        code = next(el for el in root.iter() if el.tag.endswith("}KodFormularza"))
        self.assertEqual((code.get("kodSystemowy"), code.get("wersjaSchemy"), code.text), ("FA (3)", "1-0E", "FA"))
        self.assertEqual(texts(root, "RodzajFaktury"), ["VAT"])
        self.assertEqual(texts(root, "NIP"), ["1234563218", "9876543210"])
        self.assertEqual([texts(root, k) for k in ("P_13_1", "P_14_1", "P_13_3", "P_14_3", "P_15")],
                         [["14730.00"], ["3387.90"], ["2480.00"], ["124.00"], ["20721.90"]])
        self.assertEqual([texts(root, k) for k in ("P_16", "P_18", "P_18A")], [["2"], ["2"], ["2"]])
        root, summary, _ = xml_of(spec("pl-faktura-korygujaca"))
        # Art. 106j ust. 2 pkt 5: the correction itself, with its sign; pkt 2a: the corrected invoice's KSeF number.
        self.assertEqual(texts(root, "RodzajFaktury"), ["KOR"])
        self.assertEqual((texts(root, "P_8B"), texts(root, "P_13_1"), texts(root, "P_15")), (["-200"], ["-1580.00"], ["-1943.40"]))
        self.assertEqual(texts(root, "NrKSeFFaKorygowanej"), ["1234563218-20261009-000000-000000-00"])
        self.assertEqual(texts(root, "NrFaKorygowanej"), ["FV/2026/10/118"])

    def test_poland_mentions_and_categories(self):
        s = spec("pl-faktura")
        root, _, _ = xml_of(dict(s, split_payment=True, cash_method=True))
        self.assertEqual([texts(root, k) for k in ("P_16", "P_18A")], [["1"], ["1"]])
        html = page_html(dict(s, split_payment=True, cash_method=True))[0]
        self.assertIn("Mechanizm podzielonej płatności", html)
        self.assertIn("Metoda kasowa", html)
        # Over 15 000 zł the order has to say whether annex 15 applies (art. 106e ust. 1 pkt 18a).
        silent = {k: v for k, v in s.items() if k != "split_payment"}
        self.assertTrue(any("15 000 zł" in w for w in countries.refuse(silent)[1]))
        self.assertFalse(any("15 000 zł" in w for w in countries.refuse(s)[1]))
        abroad = copy.deepcopy(s)
        abroad["buyer"].update(country="DE", vat_id="DE123456789", postcode="10115", city="Berlin")
        for l in abroad["lines"]:
            l.update(vat_category="AE", vat_rate=0)
        root, _, _ = xml_of(abroad)
        self.assertEqual((texts(root, "KodUE"), texts(root, "NrVatUE"), texts(root, "PrefiksPodatnika")), (["DE"], ["123456789"], ["PL"]))
        self.assertEqual((set(texts(root, "P_12")), texts(root, "P_18")), ({"np II"}, ["1"]))
        self.assertIn("Odwrotne obciążenie", page_html(abroad)[0])
        home = copy.deepcopy(s)
        for l in home["lines"]:
            l.update(vat_category="AE", vat_rate=0)
        self.assertEqual(set(texts(xml_of(home)[0], "P_12")), {"oo"})

    def test_poland_refuses_what_only_the_person_can_give(self):
        s = spec("pl-faktura")
        refused(self, dict(s, buyer={k: v for k, v in s["buyer"].items() if k != "vat_id"}), "art. 106e ust. 1 pkt 5")
        odd = copy.deepcopy(s)
        odd["lines"][0]["vat_rate"] = 21
        refused(self, odd, "FA(3) takes 23, 22, 8, 7, 5, 4 or 3")
        k = spec("pl-faktura-korygujaca")
        refused(self, {a: b for a, b in k.items() if a != "preceding_ksef_number"}, "art. 106j ust. 2")
        outside = dict({a: b for a, b in k.items() if a != "preceding_ksef_number"}, preceding_outside_ksef=True)
        self.assertEqual(texts(xml_of(outside)[0], "NrKSeFN"), ["1"])
        euro = dict(s, currency="EUR")
        refused(self, euro, "exchange_rate")
        root, _, _ = xml_of(dict(euro, exchange_rate=4.25))
        self.assertEqual(texts(root, "P_14_1W"), ["14398.58"])                    # art. 106e ust. 11: the tax in złoty


class Page(unittest.TestCase):
    def test_language_follows_the_seller(self):
        for name, locale in (("es-factura", "es-ES"), ("it-fattura", "it-IT"), ("pl-faktura", "pl-PL")):
            self.assertEqual(build_page.locale_of_order(spec(name))[0], locale)
            self.assertEqual(einvoice_page.locale_of_order(spec(name))[0], locale)
            self.assertIn('lang="%s"' % locale, page_html(spec(name))[0])

    def test_numbers_and_dates_in_the_locale_tables_forms(self):
        """One number form per locale across the library: the table's, which groups every thousand."""
        self.assertEqual(page_format.money(1234.56, "es-ES"), "1.234,56")
        self.assertEqual(page_format.money(-1234.56, "it-IT"), "-1.234,56")
        self.assertEqual(page_format.money(12345.67, "pl-PL").replace("\u00a0", " "), "12 345,67")
        self.assertEqual(page_format.number(1500, "es-ES"), "1.500")
        self.assertEqual((page_format.date("2026-10-09", "es-ES"), page_format.date("2026-10-09", "it-IT"),
                          page_format.date("2026-10-09", "pl-PL")), ("9/10/2026", "09/10/2026", "9.10.2026"))

    def test_a_line_without_a_unit_is_counted_in_ones(self):
        """A French case's page once printed None in the unit column."""
        s = spec("es-factura")
        del s["lines"][0]["unit"]
        html = page_html(s)[0]
        self.assertNotIn("None", html)
        self.assertEqual(build_page.unit_word(None, "es-ES"), "ud.")
        self.assertEqual(build_page.unit_word(None, "fr-FR"), "pce")

    def test_pages_carry_their_countrys_words(self):
        html = page_html(spec("es-factura"))[0]
        for words in ("Factura 2026-0142", "<dt>Serie</dt><dd>A</dd>", "NIF B12345674", "4.784,96 €", "IVA 21 % sobre 3.456,00",
                      "30 días fecha factura"):
            self.assertIn(words, html)
        html = page_html(spec("es-factura-rectificativa"))[0]
        for words in ("Factura rectificativa 2026-0009", "<dt>Factura rectificada</dt><dd>2026-0142</dd>", ">-200<", "-445,28 €",
                      "Total rectificación", "Motivo de la rectificación: Devolución de 200 catálogos",
                      "<dt>NIF del cliente</dt><dd>A99999997</dd>"):
            self.assertIn(words, html)
        html = page_html(spec("it-nota-di-credito"))[0]
        for words in ("Nota di credito 2026/NC-9", "<dt>Fattura di riferimento</dt><dd>2026/118</dd>", "P. IVA IT01234567897",
                      "448,96 €", "REA MI-0000000", "Causale: Reso di 200 cataloghi", "<dd>IT09876543217</dd>",
                      "Registro delle Imprese di Milano n. 01234567897", "Capitale sociale: 10.000,00 euro i.v."):
            self.assertIn(words, html)
        self.assertNotIn("-448,96", html)                                         # TD04: positive amounts
        html = page_html(spec("pl-faktura-korygujaca"))[0].replace("\u00a0", " ")
        for words in ("Faktura korygująca FK/2026/10/9", "Numer KSeF faktury korygowanej: 1234563218-20261009-000000-000000-00",
                      "NIP 123-456-32-18", "-1 943,40 zł", "Razem korekta", "Przyczyna korekty: Zwrot 200 katalogów",
                      "<dt>NIP nabywcy</dt><dd>987-654-32-10</dd>"):
            self.assertIn(words, html)
        self.assertIn("20 721,90 zł", page_html(spec("pl-faktura"))[0].replace("\u00a0", " "))


class Checks(unittest.TestCase):
    def test_every_rule_the_check_modules_define_is_registered(self):
        """The wave 8 country rules were once dropped from the pack check by a merge and nothing noticed."""
        owned = set(packcheck.SKILL_RULES["e-invoice"])
        import einvoice_particulars
        for rule in ec.RULES + einvoice_external.RULES + einvoice_particulars.RULES:
            self.assertIn(rule, owned, "%s is defined and the pack check never runs it" % rule)
        for rule in ec.RULES:
            self.assertEqual(packcheck.MODULES.get(rule.split("-")[0]), "einvoice_country", rule)
        for rule in einvoice_external.RULES:
            self.assertEqual(packcheck.MODULES.get(rule.split("-")[0]), "einvoice_page", rule)

    def test_a_date_is_found_in_the_form_its_locale_prints(self):
        """A Spanish page writes 30/9/2026 and a Polish one 5.09.2026: the supply date was not found in September."""
        self.assertTrue(ec.has_date("Fecha de operación 30/9/2026", "2026-09-30"))
        self.assertTrue(ec.has_date("Data sprzedaży 5.09.2026", "2026-09-05"))
        self.assertFalse(ec.has_date("Fecha de operación 30/9/2026", "2026-09-03"))
        self.assertEqual((page_format.date("2026-09-30", "es-ES"), page_format.date("2026-09-05", "pl-PL")),
                         ("30/9/2026", "5.09.2026"))
        import credit_note_check
        self.assertIn("30/9/2026", credit_note_check.date_forms("2026-09-30"))

    def test_the_scenarios_name_the_installed_schemas(self):
        for rule, (syntax, scen, folder, must, env, mount, label, opts) in einvoice_external.NATIONAL.items():
            root = ET.parse(PACK / "validators" / scen).getroot()
            locations = [el.text for el in root.iter() if el.tag.endswith("}location")]
            self.assertTrue(any(x.startswith(mount + "/") for x in locations), scen)
            self.assertTrue(any(name.startswith(folder + "/") for name, _url, _sha, _kind in fetch_validators.PINS), folder)
            self.assertEqual(einvoice_external.national(rule, PACK / "templates" / "nothing.pdf")[0], None)
        self.assertTrue(all(len(sha) == 64 for _n, _u, sha, _k in fetch_validators.PINS))

    def test_the_polish_copy_changes_the_addresses_and_the_counts_only(self):
        work = Path(tempfile.mkdtemp())
        (work / "ksef-fa3").mkdir()
        body = ('<xsd:schema><xsd:import schemaLocation="%sStrukturyDanych_v10-0E.xsd"/><xsd:element name="FaWiersz" '
                'maxOccurs="10000"/><xsd:element name="DaneKontaktowe" maxOccurs="3"/></xsd:schema>' % fetch_validators.KSEF_TYPES)
        for n in ("schemat.xsd", "StrukturyDanych_v10-0E.xsd", "ElementarneTypyDanych_v10-0E.xsd", "KodyKrajow_v10-0E.xsd"):
            (work / "ksef-fa3" / n).write_text(body)
        fetch_validators.localise_ksef(work)
        strict, fast = ((work / "ksef-fa3" / d / "schemat.xsd").read_text() for d in ("strict", "offline"))
        self.assertEqual(strict, body.replace(fetch_validators.KSEF_TYPES, ""))
        self.assertEqual(fast, strict.replace('maxOccurs="10000"', 'maxOccurs="unbounded"'))
        self.assertEqual((work / "ksef-fa3" / "schemat.xsd").read_text(), body)          # as fetched

    @unittest.skipUnless(can_print(), "no Chromium or pdftotext to read a printed page with")
    def test_the_starters_pass_their_countrys_rule(self):
        for name in STARTERS:
            s = spec(name)
            pdf, _ = printed(s, with_xml=True)
            rule = {"es": "ES-INVOICE", "it": "IT-INVOICE", "pl": "PL-INVOICE"}[name[:2]]
            ok, why = ec.check(rule, pdf, {}, "first")
            self.assertTrue(ok, "%s: %s" % (name, why))
            for other in ("ES-INVOICE", "IT-INVOICE", "PL-INVOICE"):
                if other != rule:
                    self.assertIsNone(ec.check(other, pdf, {}, "first")[0])
            for check in ("EINV-VAT-LABEL", "EINV-LOCALE-ORDER", "EINV-PAGE-DIN5008", "EINV-PAGE-KIND"):
                got, why = einvoice_page.check(check, pdf, {}, "first")
                self.assertIsNot(got, False, "%s %s: %s" % (name, check, why))

    @unittest.skipUnless(can_print(), "no Chromium or pdftotext to read a printed page with")
    def test_each_rule_catches_what_it_reads(self):
        def drop(*words):
            def edit(h):
                for w in words:
                    h = h.replace(w, "")
                return h
            return edit
        cases = (
            ("es-factura", {}, drop("B12345674"), "ES-INVOICE", "art. 6.1 d"),
            ("es-factura", {}, drop("<dd>A</dd>"), "ES-INVOICE", "art. 6.1 a"),
            ("es-factura", {"lines": [dict(spec("es-factura")["lines"][0], vat_category="AE", vat_rate=0)]},
             drop("Inversión del sujeto pasivo"), "ES-INVOICE", "art. 6.1 m"),
            ("es-factura-rectificativa", {}, drop("2026-0142"), "ES-INVOICE", "does not name invoice"),
            ("it-fattura", {}, drop("IT09876543217"), "IT-INVOICE", "art. 21 comma 2 f"),
            ("es-factura", {}, drop("A99999997"), "ES-INVOICE", "the recipient's NIF"),
            ("pl-faktura", {}, drop("987-654-32-10"), "PL-INVOICE", "art. 106e ust. 1 pkt 5"),
            ("it-fattura", {"split_payment": True}, drop("Scissione dei pagamenti"), "IT-INVOICE", "art. 17-ter"),
            ("it-fattura", {"stamp_duty": True}, drop(countries.IT_STAMP), "IT-INVOICE", "DM 17 giugno 2014"),
            ("pl-faktura", {}, drop("123-456-32-18"), "PL-INVOICE", "art. 106e ust. 1 pkt 4"),
            ("pl-faktura", {"split_payment": True}, drop("Mechanizm podzielonej płatności"), "PL-INVOICE", "pkt 18a"),
            ("pl-faktura-korygujaca", {}, drop("1234563218-20261009-000000-000000-00"), "PL-INVOICE", "art. 106j ust. 2 pkt 2a"),
        )
        for name, change, edit, rule, words in cases:
            s = dict(spec(name), **change)
            pdf, _ = printed(s, edit=edit)
            ok, why = ec.check(rule, pdf, {}, "first")
            self.assertFalse(ok, "%s %s passed without %s" % (name, rule, words))
            self.assertIn(words, why, name)

    @unittest.skipUnless(can_print(), "no Chromium or pdftotext to read a printed page with")
    def test_the_file_beside_the_page_is_read_too(self):
        s = spec("it-nota-di-credito")
        pdf, _ = printed(s, with_xml=True)
        xml = pdf.with_suffix(".xml")
        xml.write_text(xml.read_text().replace("TD04", "TD01"))
        ok, why = ec.check("IT-INVOICE", pdf, {}, "first")
        self.assertFalse(ok)
        self.assertIn("TipoDocumento is TD01, not TD04", why)
        s = dict(spec("pl-faktura"), split_payment=True)
        pdf, _ = printed(s, with_xml=True)
        xml = pdf.with_suffix(".xml")
        xml.write_text(re.sub(r"<P_18A>1</P_18A>", "<P_18A>2</P_18A>", xml.read_text()))
        ok, why = ec.check("PL-INVOICE", pdf, {}, "first")
        self.assertFalse(ok)
        self.assertIn("P_18A", why)


class OrderShapedTruth(unittest.TestCase):
    """Carried from wave 8: a case whose truth is the order itself. The trace rules failed every such page."""

    def case(self, name):
        s = spec(name)
        staged = {"lines": s.pop("lines")}
        return {"id": "t", "truth": dict(s, first=staged, revision=staged)}

    def test_the_order_is_read_as_the_truth(self):
        case = self.case("pl-faktura")
        order = einvoice_page.described_order(case, "first")
        self.assertEqual(len(order["lines"]), 3)
        values, labels, pools = einvoice_page.order_truth(order)
        for figure in ("11850.00", "14730.00", "3387.90", "20721.90", "9.10.2026", "23"):
            self.assertIn(figure, values)
        self.assertTrue(labels["email"] and labels["bic"] and labels["purchase order"])
        self.assertFalse(labels["discount"] or labels["notes"] or labels["delivery address"])
        self.assertIn("1234563218", pools)
        self.assertIsNone(einvoice_page.described_order({"truth": {"header": {}, "vat_category": "S"}}, "first"))

    @unittest.skipUnless(can_print(), "no Chromium or pdftotext to read a printed page with")
    def test_a_correct_country_page_passes_and_an_invented_figure_does_not(self):
        for name in ("es-factura", "it-fattura", "pl-faktura-korygujaca", "at-rechnung", "no-faktura", "fi-lasku"):
            case = self.case(name)
            pdf, _ = printed(spec(name), case=case)
            for rule in ("EINV-PAGE-TRACE", "EINV-PAGE-NO-EXTRA"):
                ok, why = einvoice_page.check(rule, pdf, case, "first")
                self.assertTrue(ok, "%s %s: %s" % (name, rule, why))
            self.assertIsNone(einvoice_page.check("EINV-PAGE-COMPLETE", pdf, case, "first")[0])
        case = self.case("es-factura")
        pdf, _ = printed(spec("es-factura"), case=case,
                         edit=lambda h: h.replace("</section>", "<p>Recargo 31,77 Notes: ver anexo</p></section>", 1))
        ok, why = einvoice_page.check("EINV-PAGE-TRACE", pdf, case, "first")
        self.assertFalse(ok)
        self.assertIn("31,77", why)
        ok, why = einvoice_page.check("EINV-PAGE-NO-EXTRA", pdf, case, "first")
        self.assertFalse(ok)
        self.assertIn("notes", why)
        nothing = {"truth": {"header": {}, "vat_category": "S"}}
        self.assertIsNone(einvoice_page.check("EINV-PAGE-TRACE", pdf, nothing, "first")[0])


if __name__ == "__main__":
    unittest.main()
