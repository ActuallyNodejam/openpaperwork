"""Belgium, the Netherlands, Austria and Ireland (wave 8): each kind of mistake is built and seen caught.

    python3 -m unittest skills/e-invoice/tests/test_benelux_at_ie.py

Standard library only: no validator, no network. The tests that measure a printed page need Chromium
(the app's printer or Playwright) and pdftotext, and skip without them.
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
import ebinterface_create  # noqa: E402
import ubl_create  # noqa: E402
import einvoice_ids as ids  # noqa: E402
import einvoice_country as ec  # noqa: E402
import einvoice_page  # noqa: E402
import build_page  # noqa: E402

TEMPLATES = PACK / "templates"


def spec(name):
    return json.loads((TEMPLATES / name).read_text())


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


def printed(s, edit=None):
    """The page of an order printed in a folder of its own, the order beside it: (pdf, html text)."""
    folder = Path(tempfile.mkdtemp())
    (folder / "order.json").write_text(json.dumps(s, ensure_ascii=False))
    locale = build_page.page_locale_for(build_page.locale_of_order(s)[0])
    html = build_page.on_layout(build_page.paper_for(build_page.build(s, locale), locale), s)
    if edit:
        html = edit(html)
    (folder / "invoice.html").write_text(html)
    build_page.print_pdf(folder / "invoice.html", folder / "invoice.pdf", build_page.paper_of(locale))
    return folder / "invoice.pdf", html


def refused(test, s, words):
    with test.assertRaises(SystemExit) as caught:
        einvoice_create.document_xml(s)
    test.assertIn(words, str(caught.exception))


class Identifiers(unittest.TestCase):
    def test_check_digits(self):
        self.assertTrue(ids.be_enterprise_ok("0123.456.749"))
        self.assertFalse(ids.be_enterprise_ok("0123.456.748"))
        self.assertTrue(ids.be_enterprise_ok("0314.595.348"))          # the Crossroads Bank's own example
        self.assertTrue(ids.be_ogm_ok("+++010/8068/17183+++"))         # Febelfin's example
        self.assertFalse(ids.be_ogm_ok("+++010/8068/17184+++"))
        # The check digits are the remainder itself, 97 when it is 0; never 97 less the remainder.
        self.assertTrue(ids.be_ogm_ok("+++000/0000/09797+++"))
        self.assertFalse(ids.be_ogm_ok("+++000/0000/09700+++"))
        self.assertFalse(ids.be_ogm_ok("+++010/8068/17114+++"))        # 97 - 83, the enterprise number's rule
        self.assertTrue(ids.at_uid_ok("ATU10223006"))                  # the ministry's own sample (BMF, 2020)
        self.assertFalse(ids.at_uid_ok("ATU10223005"))
        self.assertTrue(ids.at_uid_ok("ATU13585627"))
        self.assertFalse(ids.at_uid_ok("ATU13585628"))
        self.assertTrue(ids.nl_vat_ok("NL123456782B01"))
        self.assertTrue(ids.nl_vat_ok("NL000099998B57"))              # Ondernemersplein's btw-id example
        self.assertTrue(ids.ie_vat_ok("IE1234567T"))
        self.assertTrue(ids.ie_vat_form("IE1Z23456A"))                # the old form
        self.assertFalse(ids.ie_vat_form("IE123456T"))

    def test_belgian_region_decides_the_language(self):
        self.assertEqual(ids.be_region_locale("2000")[0], "nl-BE")
        self.assertEqual(ids.be_region_locale("4000")[0], "fr-BE")
        self.assertEqual(ids.be_region_locale("4700")[0], "de-BE")
        self.assertEqual(ids.be_region_locale("1000")[0], "fr-BE")
        self.assertEqual(build_page.locale_of_order(spec("be-factuur-spec.json"))[0], "nl-BE")
        self.assertEqual(build_page.locale_of_order(spec("be-facture-spec.json"))[0], "fr-BE")
        self.assertEqual(build_page.locale_of_order(dict(spec("be-facture-spec.json"), language="nl"))[0], "nl-BE")

    def test_flanders_writes_dutch_at_home(self):
        """Decree of 19 July 1973 art. 5 § 1 and § 2/1: Dutch to a customer in Belgium whatever the order
        names; for a customer in another EU or EEA state the named language, beside the Dutch invoice."""
        home = dict(spec("be-factuur-spec.json"), language="fr")
        self.assertEqual(build_page.locale_of_order(home)[0], "nl-BE")
        self.assertEqual(einvoice_page.locale_of_order(home)[0], "nl-BE")
        self.assertIn("stays Dutch", " ".join(countries.refuse(home)[1]))
        abroad = dict(home, buyer=dict(home["buyer"], country="FR", postcode="59000", city="Lille"))
        abroad["buyer"].pop("register_number", None)
        self.assertEqual(build_page.locale_of_order(abroad)[0], "fr-BE")
        self.assertEqual(einvoice_page.locale_of_order(abroad)[0], "fr-BE")
        self.assertIn("§ 2/1", " ".join(countries.refuse(abroad)[1]))
        # Wallonia and Brussels are not under the Flemish decree: the named language stands.
        self.assertEqual(build_page.locale_of_order(dict(spec("be-facture-spec.json"), language="nl"))[0], "nl-BE")
        self.assertFalse(ids.be_dutch_at_home({"country": "NL", "postcode": "2000"}, {"country": "BE"}, "fr"))


class Files(unittest.TestCase):
    def test_each_country_gets_its_file(self):
        for name in ("be-factuur", "nl-factuur", "at-rechnung", "ie-vat-invoice"):
            self.assertEqual(countries.syntax_of(spec(name + "-spec.json")), "ubl", name)
        self.assertEqual(countries.syntax_of(spec("nl-si-ubl-spec.json")), "si-ubl")
        self.assertEqual(countries.syntax_of(spec("at-ebinterface-spec.json")), "ebinterface")

    def test_belgian_ubl(self):
        root = ET.fromstring(ubl_create.xml_bytes(spec("be-factuur-spec.json"))[0])
        seller = root.find("{*}AccountingSupplierParty/{*}Party")
        self.assertEqual((seller.find("{*}EndpointID").get("schemeID"), seller.find("{*}EndpointID").text),
                         ("0208", "0123456749"))
        self.assertEqual(seller.find("{*}PartyLegalEntity/{*}CompanyID").get("schemeID"), "0208")
        self.assertEqual(root.find("{*}PaymentMeans/{*}PaymentID").text, "202610120124")

    def test_dutch_ubl_and_si_ubl(self):
        root = ET.fromstring(ubl_create.xml_bytes(spec("nl-factuur-spec.json"))[0])
        legal = root.find("{*}AccountingSupplierParty/{*}Party/{*}PartyLegalEntity/{*}CompanyID")
        self.assertEqual((legal.text, legal.get("schemeID")), ("12345678", "0106"))
        data, summary, syntax = einvoice_create.document_xml(spec("nl-si-ubl-spec.json"))
        root = ET.fromstring(data)
        self.assertEqual(root.find("{*}CustomizationID").text, ubl_create.NLCIUS)
        self.assertIsNone(root.find("{*}AccountingSupplierParty/{*}Party/{*}PartyLegalEntity/{*}CompanyLegalForm"))

    def test_ebinterface(self):
        data, summary = ebinterface_create.xml_bytes(spec("at-ebinterface-spec.json"))
        root = ET.fromstring(data)
        ns = "{%s}" % ebinterface_create.NS
        self.assertEqual(root.get("DocumentType"), "Invoice")
        self.assertEqual(root.find(ns + "Biller/" + ns + "VATIdentificationNumber").text, "ATU12345675")
        self.assertEqual(root.find(ns + "InvoiceRecipient/" + ns + "OrderReference/" + ns + "OrderID").text, "4700000001")
        self.assertEqual(root.find(ns + "PayableAmount").text, summary["total_including_vat"])
        credit = dict(spec("at-rechnungskorrektur-spec.json"), syntax="ebinterface")
        root = ET.fromstring(ebinterface_create.xml_bytes(credit)[0])
        self.assertEqual(root.get("DocumentType"), "CreditMemo")
        self.assertEqual(root.find(ns + "RelatedDocument/" + ns + "InvoiceNumber").text, "RE-2026-0331")


class Refusals(unittest.TestCase):
    def test_belgium(self):
        s = spec("be-factuur-spec.json")
        s["seller"]["register_number"] = "0123.456.748"
        refused(self, s, "modulus 97")
        s = spec("be-factuur-spec.json")
        s["payment"]["reference"] = "+++202/6101/20125+++"
        refused(self, s, "structured communication")

    def test_netherlands(self):
        s = spec("nl-factuur-spec.json")
        s["seller"].pop("register_number")
        refused(self, s, "Handelsregisterwet 2007 art. 27")
        s = spec("nl-factuur-spec.json")
        s["payment"]["means_code"] = "1"
        refused(self, s, "NL-R-008")

    def test_austria(self):
        s = spec("at-rechnung-spec.json")
        s["buyer"].pop("vat_id")
        s["buyer"]["electronic_address"] = "9915:b"
        refused(self, s, "lit. b")
        s = spec("at-rechnung-spec.json")
        s["seller"]["vat_id"] = "ATU12345676"
        refused(self, s, "check digit")

    def test_ireland(self):
        s = spec("ie-credit-note-spec.json")
        s.pop("note")
        refused(self, s, "reg. 20(5)")
        s = spec("ie-vat-invoice-spec.json")
        s.pop("delivery_date")
        refused(self, s, "date the goods or services were supplied")
        s = spec("ie-credit-note-spec.json")
        s["buyer"].pop("vat_id")
        refused(self, s, "reg. 20(5)(d)")


class PageRules(unittest.TestCase):
    def text_of(self, name):
        s = spec(name)
        html = build_page.build(s, build_page.locale_of_order(s)[0])
        return s, ec.flat(build_page.unescape(__import__("re").sub(r"<[^>]+>", " ", html)))

    def test_each_rule_passes_its_starter_and_catches_a_gap(self):
        for name, fn, gap in (("be-factuur-spec.json", ec.be_invoice, "0123.456.749"),
                              ("nl-factuur-spec.json", ec.nl_invoice, "12345678"),
                              ("at-rechnung-spec.json", ec.at_invoice, "ATU12345675"),
                              ("ie-vat-invoice-spec.json", ec.ie_invoice, "IE1234567T")):
            s, text = self.text_of(name)
            ok, why = fn(s, text, None)
            self.assertTrue(ok, "%s: %s" % (name, why))
            ok, why = fn(s, text.replace(gap, "").replace(gap.replace(".", ""), ""), None)
            self.assertFalse(ok, name)

    def test_reverse_charge_mention(self):
        s, text = self.text_of("nl-factuur-spec.json")
        s["lines"][0].update(vat_category="AE", vat_rate=0)
        s["buyer"]["country"] = "BE"
        ok, why = ec.nl_invoice(s, text, None)
        self.assertFalse(ok)
        self.assertIn("reverse charge", why)

    def reverse(self, name):
        """The starter turned into a reverse charge, and its page."""
        s = spec(name)
        for l in s["lines"]:
            l.update(vat_category="AE", vat_rate=0)
        s["buyer"].setdefault("vat_id", "DE123456789")
        html = build_page.build(s, build_page.locale_of_order(s)[0])
        return s, ec.flat(build_page.unescape(__import__("re").sub(r"<[^>]+>", " ", html)))

    def test_fixed_mentions_belgium_and_the_netherlands(self):
        """Royal Decree no. 1 art. 5 § 1 9°bis and Wet OB art. 35a lid 1 m fix the words."""
        for name, fn, word in (("be-factuur-spec.json", ec.be_invoice, "Btw verlegd"),
                               ("be-facture-spec.json", ec.be_invoice, "Autoliquidation"),
                               ("nl-factuur-spec.json", ec.nl_invoice, "Btw verlegd")):
            s, text = self.reverse(name)
            self.assertIn(word, text, name)
            self.assertTrue(fn(s, text, None)[0], "%s: %s" % (name, fn(s, text, None)[1]))
            ok, why = fn(s, text.replace(word, "De afnemer is de btw verschuldigd"), None)
            self.assertFalse(ok, name)
            self.assertIn("reverse charge without its mention", why)
        german = dict(spec("be-factuur-spec.json"), seller=dict(spec("be-factuur-spec.json")["seller"], postcode="4700",
                                                                city="Eupen"))
        self.assertEqual(build_page.locale_of_order(german)[0], "de-BE")
        self.assertEqual(countries.REVERSE["de-BE"], "Steuerschuldnerschaft des Leistungsempfängers")

    def test_no_fixed_wording_in_austria_and_ireland(self):
        """UStG § 11 Abs. 1a and VAT Regulations 2010 reg. 20(2)(e) ask for a note and fix no words: any clear
        note that the customer owes the tax passes, and none at all fails."""
        s, text = self.reverse("ie-vat-invoice-spec.json")
        self.assertIn("Reverse charge applies", text)
        self.assertTrue(ec.ie_invoice(s, text, None)[0], ec.ie_invoice(s, text, None)[1])
        for note in ("VAT reverse-charge: see s. 16(3)", "The customer is liable to account for the VAT on this supply",
                     "VAT to be accounted for by the recipient"):
            ok, why = ec.ie_invoice(s, text.replace("Reverse charge applies", note), None)
            self.assertTrue(ok, "%s: %s" % (note, why))
        ok, why = ec.ie_invoice(s, text.replace("Reverse charge applies", "Thank you for your business"), None)
        self.assertFalse(ok)
        self.assertIn("reg. 20(2)(e)", why)
        s, text = self.reverse("at-rechnung-spec.json")
        word = "Steuerschuldnerschaft des Leistungsempfängers"
        self.assertIn(word, text)
        self.assertTrue(ec.at_invoice(s, text, None)[0], ec.at_invoice(s, text, None)[1])
        for note in ("Übergang der Steuerschuld auf den Leistungsempfänger", "Die Steuerschuld geht auf den Empfänger über",
                     "Reverse Charge"):
            ok, why = ec.at_invoice(s, text.replace(word, note), None)
            self.assertTrue(ok, "%s: %s" % (note, why))
        ok, why = ec.at_invoice(s, text.replace(word, "Vielen Dank"), None)
        self.assertFalse(ok)
        self.assertIn("§ 11 Abs. 1a", why)

    def test_irish_credit_note_names_the_customers_number(self):
        s, text = self.text_of("ie-credit-note-spec.json")
        self.assertTrue(ec.ie_invoice(s, text, None)[0], ec.ie_invoice(s, text, None)[1])
        number = s["buyer"]["vat_id"].replace(" ", "")
        ok, why = ec.ie_invoice(s, text.replace(number, ""), None)
        self.assertFalse(ok)
        self.assertIn("reg. 20(5)(d)", why)


class Layouts(unittest.TestCase):
    """An invoice sits on the seller country's letter layout; every number comes from skills/_shared/letter.py."""

    def css(self, lay):
        text = build_page.layout_css(lay)
        got = {}
        for name in ("field", "info"):
            m = re.search(r"\.%s\{left:([\d.]+)mm;top:([\d.]+)mm;width:([\d.]+)mm" % name, text)
            got[name] = tuple(float(x) for x in m.groups())
        return text, got

    def test_the_address_sits_at_the_layouts_own_place(self):
        letter = build_page.letter
        for lid, lay in letter.LAYOUTS.items():
            text, got = self.css(lay)
            wx, wy, ww, wh = lay["window"]
            ax, ay = lay["address_at"]
            self.assertEqual(got["field"][:2], (round(ax, 2), round(ay, 2)), lid)
            self.assertLessEqual(got["field"][0] + got["field"][2], wx + ww + 0.01, lid)   # inside the window
            ix, iy, iw = got["info"]
            page_w = letter.PAPER_MM[lay["paper"]][0]
            # The block never passes the text's right edge, the one the table ends on.
            self.assertLessEqual(ix + iw, page_w - lay["right"] + 0.01, lid)
            self.assertGreaterEqual(iw, 60, "%s: the information block is too narrow to read" % lid)
            if wx + ww / 2 > page_w / 2:
                self.assertLessEqual(ix + iw, wx, lid)                                # left of a window on the right
            elif lay["info"] == "above":
                # No room beside a #10 window: the block ends above it, at the right text margin.
                self.assertIn("translateY(-100%)", text, lid)
                self.assertLess(iy, wy, lid)
                self.assertAlmostEqual(ix + iw, page_w - lay["right"], places=1, msg=lid)
            else:
                self.assertGreaterEqual(ix, wx + ww, lid)                             # clear of the window

    def test_a_window_on_the_right_puts_the_block_on_the_left(self):
        letter = build_page.letter
        # An invented layout with its window in the right half, the way a Belgian envelope has it.
        lay = dict(letter.LAYOUTS["dk"], name="Invented: window on the right", window=(110, 45, 95, 40),
                   address_at=(118, 49))
        text, got = self.css(lay)
        self.assertEqual(got["info"][0], lay["left"])
        self.assertLess(got["info"][0] + got["info"][2], lay["window"][0])
        self.assertEqual(got["field"][0], 118)

    def test_the_information_block_keeps_to_the_text_width_on_form_b_too(self):
        letter = build_page.letter
        g = letter.GEOMETRY
        self.assertIn(".info{width:%smm}" % (210 - g["right"] - g["info_x"]), build_page.form_b_css())     # 65 mm, to 190
        s = spec("xrechnung-credit-note-spec.json")                                   # a German seller: Form B
        self.assertIsNone(build_page.layout_of(s)[1])
        html = build_page.on_layout(build_page.build(s, "de-DE"), s)
        for name in ("xrechnung-credit-note-spec.json", "nl-factuur-spec.json", "us-invoice-spec.json", "be-facture-spec.json"):
            s = spec(name)
            html = build_page.on_layout(build_page.build(s, build_page.locale_of_order(s)[0]), s)
            # Labels in a column as wide as the longest of them, none wrapping; values wrap in their own column.
            self.assertIn(".info dl{display:grid;grid-template-columns:max-content minmax(0,1fr)", html, name)
            self.assertIn(".info dt{width:auto;white-space:nowrap}", html, name)
            self.assertIn(".info dd{min-width:0;overflow-wrap:anywhere}", html, name)

    def test_an_email_address_breaks_after_its_at_sign_or_before_a_point(self):
        s = spec("at-rechnung-spec.json")
        html = build_page.build(s, "de-AT")
        self.assertIn("<dd>rechnung@<wbr>donau<wbr>.example</dd>", html)

    def test_the_contact_lines_are_a_group_of_their_own(self):
        """Carried from wave 8: the seller's contact has its own label column, so a short "E-Mail" is not
        pushed out by the longest label of the document's data."""
        s = spec("at-rechnungskorrektur-spec.json")
        html = build_page.build(s, "de-AT")
        block = re.search(r'<div class="info">(.*?)</div>\s*<script>', html, re.S).group(1)
        groups = re.findall(r"<dl>(.*?)</dl>", block, re.S)
        self.assertEqual(len(groups), 2)
        self.assertIn("Urspr. Rechnung vom", groups[0])
        self.assertNotIn("E-Mail", groups[0])
        self.assertEqual(re.findall(r"<dt>(.*?)</dt>", groups[1]), ["Ansprechperson", "Telefon", "E-Mail"])
        # One aligned column while the contact fits; its own, narrower one when a value would wrap.
        self.assertIn("if(own[1]<both)set(g[1],own[1])", html)
        self.assertIn("long.every(e=>over(e)<=1.08)", html)        # a near miss is set a little smaller, nothing moves
        self.assertLess(html.index("querySelectorAll('.info dl')"), html.index("document.querySelector('.info')"))
        bare = dict(s, seller={k: v for k, v in s["seller"].items() if k not in ("contact", "phone", "email")})
        self.assertEqual(len(re.findall(r"<dl>", build_page.build(bare, "de-AT"))), 1)
        self.assertNotIn("own[1]", build_page.build(bare, "de-AT"))

    def test_the_buyers_address_is_written_as_the_letter_writes_it(self):
        letter = build_page.letter
        for name, last in (("be-factuur-spec.json", ["9000 GENT"]), ("nl-factuur-spec.json", ["8011 AA  ZWOLLE"]),
                           ("uk-vat-invoice-spec.json", ["LEEDS", "LS1 1AA"]), ("ie-vat-invoice-spec.json", ["Cork", "T12 CD34"]),
                           ("fi-lasku-spec.json", ["33100 TAMPERE"]), ("at-rechnung-spec.json", ["8010 Graz"]),
                           ("us-invoice-spec.json", ["200 SAMPLE ST", "AUSTIN TX  78702"]),
                           ("xrechnung-credit-note-spec.json", ["00000 Beispielstadt"])):
            s = spec(name)
            lines = build_page.buyer_address(s)
            self.assertEqual(lines, letter.postal_lines(s["buyer"], s["seller"]["country"]), name)
            self.assertEqual(lines[-len(last):], last, name)
            html = build_page.build(s, build_page.page_locale_for(build_page.locale_of_order(s)[0]))
            self.assertIn('<div class="address">%s</div>' % "<br>".join(build_page.esc(x) for x in lines), html, name)
        abroad = spec("xrechnung-credit-note-spec.json")
        abroad["buyer"] = dict(abroad["buyer"], postcode="9000", city="Gent", country="BE")
        self.assertEqual(build_page.buyer_address(abroad)[-2:], ["9000 GENT", "BELGIUM"])   # abroad: the country last
        # The address in the layout's own line height, as the letter sets it, so a long one stays in the window.
        self.assertIn("line-height:4.1mm", build_page.layout_css(letter.LAYOUTS["ie"]))

    def test_the_country_rule_reads_a_town_in_capitals_as_the_town(self):
        buyer = spec("fi-lasku-spec.json")["buyer"]
        page = "Testi Tehdas Oy Koekuja 2 33100 TAMPERE"
        self.assertEqual(ec.address_on(page, buyer), [])
        self.assertEqual(ec.address_on(page.replace("TAMPERE", "TURKU"), buyer), ["city"])
        self.assertEqual(ec.address_on("Testi Tehdas Oy 33100 TAMPERE", buyer), ["street"])
        self.assertEqual(ec.address_on("TESTI TEHDAS OY Koekuja 2 33100 TAMPERE", buyer), ["name"])   # the name as written
        us = {"name": "Example Packaging Inc.", "street": "200 Sample St.", "city": "Austin, TX"}
        self.assertEqual(ec.address_on("Example Packaging Inc. 200 SAMPLE ST AUSTIN TX  78702", us), [])

    @unittest.skipUnless(can_print(), "no Chromium or pdftotext to measure a printed page with")
    def test_long_values_wrap_inside_the_block_and_nothing_passes_the_right_edge(self):
        letter = build_page.letter
        for name in ("xrechnung-credit-note-spec.json", "nl-creditnota-spec.json", "be-facture-spec.json",
                     "fi-hyvityslasku-spec.json", "us-invoice-spec.json"):
            s = copy.deepcopy(spec(name))
            contact = dict(s["seller"].get("contact") or {}, name="Maximiliane Beispiel-Musterfrau von und zu Probe",
                           email="debiteurenadministratie.facturen@voorbeeld-installatietechniek.example")
            s["seller"]["contact"] = contact
            pdf, html = printed(s)
            lay = einvoice_page.page_layout(pdf, s)
            buyer = s["buyer"]["name"]
            self.assertEqual(einvoice_page.din5008_problems(pdf, buyer, lay=lay, right_edge=True), [], name)
            words = einvoice_page.page_words(pdf)
            edge = letter.PAPER_MM[lay["paper"] if lay else "A4"][0] - (lay["right"] if lay else 20)
            self.assertLessEqual(max(w[2] for w in words), edge + 0.5, name)
            # Every label keeps to one line: each label's words share a baseline.
            for label in re.findall(r"<dt>(.*?)</dt>", html):
                toks = build_page.unescape(label).split()
                if len(toks) < 2:
                    continue
                firsts = [w for w in words if w[4] == toks[0]]
                self.assertTrue(any(any(o[4] == toks[-1] and abs(o[1] - f[1]) < 1 and o[0] > f[0] for o in words)
                                    for f in firsts), "%s: the label %r wraps" % (name, label))

    @unittest.skipUnless(can_print(), "no Chromium or pdftotext to measure a printed page with")
    def test_the_rule_catches_a_block_that_runs_past_the_right_edge(self):
        s = copy.deepcopy(spec("nl-factuur-spec.json"))
        s["seller"]["contact"] = dict(s["seller"].get("contact") or {},
                                      email="debiteurenadministratie.facturen@voorbeeld-installatietechniek.example")
        # The page as it was: a 34 mm label column in a block that ends 10 mm past the text, values that cannot wrap.
        old = ".info{display:flex;flex-direction:column;width:75mm}.info dl{display:block}.info div{display:flex}" \
              ".info dt{width:34mm;flex:none}.info dd{min-width:auto;overflow-wrap:normal}"
        pdf, _html = printed(s, edit=lambda h: h.replace("</style>", old + "</style>", 1).replace("<wbr>", ""))
        problems = einvoice_page.din5008_problems(pdf, s["buyer"]["name"], lay=einvoice_page.page_layout(pdf, s), right_edge=True)
        self.assertTrue(any("past the text's right edge" in p for p in problems), problems)
        ok, why = einvoice_page.check("EINV-PAGE-DIN5008", pdf, {}, "first")      # the order is beside the page
        self.assertFalse(ok, why)

    def test_the_new_countries_follow_their_layout_when_there_is_one(self):
        letter = build_page.letter
        for name, country in (("be-factuur", "BE"), ("nl-factuur", "NL"), ("at-rechnung", "AT"), ("ie-vat-invoice", "IE"),
                              ("no-faktura", "NO"), ("uk-vat-invoice", "GB"), ("us-invoice", "US")):
            s = json.loads((TEMPLATES / (name + "-spec.json")).read_text())
            lid, lay = build_page.layout_of(s)
            self.assertEqual(lay, letter.LAYOUTS.get(letter.COUNTRY_LAYOUT.get(country)), name)
            html = build_page.on_layout(build_page.build(s, build_page.locale_of_order(s)[0]), s)
            self.assertIn('content="%s"' % (lay["name"] if lay else "DIN 5008:2020 Form B"), html, name)


if __name__ == "__main__":
    unittest.main()
