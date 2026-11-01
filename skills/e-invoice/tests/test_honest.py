"""Depth 4, invoices: nothing the order's data file gives is dropped. An unknown key and a value of the wrong
shape (an amount as text, a VAT rate written 0.2 for 20 percent) stop both builders by name
(skills/_shared/spec_guard.py, spec.fields.json); the seller's further particulars print in the footer and the
order's note on every page. A house rule on the builder's own input. The page is built as HTML: no printer needed."""
import copy
import json
import subprocess
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE.parent / "_shared"))
import spec_guard  # noqa: E402


def spec(name):
    return json.loads((HERE / "templates" / name).read_text())


def run(builder, data, out_name, *extra):
    """Build in a folder of its own, the data file beside the output as a chat folder holds both.
    Returns (exit code, what the builder printed, the output path)."""
    folder = Path(tempfile.mkdtemp())
    (folder / "spec.json").write_text(json.dumps(data, ensure_ascii=False))
    r = subprocess.run([sys.executable, str(HERE / builder), str(folder / "spec.json"), str(folder / out_name), *extra],
                       capture_output=True, text=True, cwd=folder)
    return r.returncode, r.stdout + r.stderr, folder / out_name


def words(path):
    """Every word a Word file shows: body, tables, headers and footers."""
    import re
    out = []
    with zipfile.ZipFile(path) as z:
        for name in z.namelist():
            if re.match(r"word/(document|header\d*|footer\d*)\.xml$", name):
                xml = z.read(name).decode("utf-8", "replace")
                xml = re.sub(r"</w:p>", "\n", xml)
                out.append(re.sub(r"<[^>]+>", "", xml))
    return "\n".join(out).replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">").replace("&quot;", '"')


BUILDER = "page/build_page.py"


def page(path):
    import html
    import re
    return html.unescape(re.sub(r"<[^>]+>", " ", Path(path).read_text()))


class NothingDropped(unittest.TestCase):
    def test_a_number_in_another_countrys_field_stops_the_build(self):
        # Timed command run c01 (2026-10-25): a Swedish buyer's org.nr as "org_number" printed nowhere.
        sys.path.insert(0, str(HERE / "scripts"))
        import countries
        for p in sorted((HERE / "templates").glob("*.json")):
            self.assertEqual(countries.misplaced_numbers(json.loads(p.read_text())), [], p.name)
        data = spec("se-faktura-rabatt-forskott-spec.json")
        data["buyer"]["org_number"] = data["buyer"].pop("register_number", None) or "556000-3104"
        rc, said, out = run(BUILDER, data, "faktura.pdf")
        self.assertNotEqual(rc, 0, said)
        self.assertIn("buyer.register_number", said)
        self.assertFalse(out.exists())

    def test_every_starter_passes_the_guard(self):
        fields = spec_guard.load_fields(HERE / "spec.fields.json")
        for p in sorted((HERE / "templates").glob("*.json")):
            self.assertEqual(spec_guard.problems(json.loads(p.read_text()), fields), [], p.name)

    def test_an_unknown_key_fails_with_its_name_and_where_it_can_go(self):
        data = spec("it-fattura-spec.json")
        data["seller"]["sole_shareholder_line"] = "Società con unico socio"
        rc, said, out = run(BUILDER, data, "fattura.html")
        self.assertNotEqual(rc, 0)
        self.assertIn('unknown key "seller.sole_shareholder_line"', said)
        self.assertIn('"seller.further"', said)
        self.assertFalse(out.exists(), "nothing is built on an error")

    def test_the_xml_builder_refuses_it_too(self):
        data = spec("invoice-spec.json")
        data["date_of_supply"] = "2026-10-05"
        rc, said, out = run("scripts/einvoice_create.py", data, "invoice.xml")
        self.assertNotEqual(rc, 0)
        self.assertIn('unknown key "date_of_supply"', said)
        self.assertIn('"delivery_date"', said)
        self.assertFalse(out.exists())

    def test_a_string_in_a_list_field_fails(self):
        data = spec("invoice-spec.json")
        data["seller"]["further"] = "Registered with the Example Trade Board"
        rc, said, out = run(BUILDER, data, "invoice.html")
        self.assertNotEqual(rc, 0)
        self.assertIn('"seller.further" is one string', said)
        self.assertFalse(out.exists())

    def test_a_rate_written_as_a_fraction_fails(self):
        data = spec("uk-vat-invoice-spec.json")
        data["lines"][0]["vat_rate"] = 0.2
        rc, said, out = run(BUILDER, data, "invoice.html")
        self.assertNotEqual(rc, 0)
        self.assertIn("lines[0].vat_rate", said)
        self.assertIn("20 percent is 20, not 0.2", said)

    def test_an_amount_given_as_text_fails(self):
        data = spec("uk-vat-invoice-spec.json")
        data["lines"][0]["unit_price"] = "120.00"
        rc, said, _ = run(BUILDER, data, "invoice.html")
        self.assertNotEqual(rc, 0)
        self.assertIn("lines[0].unit_price", said)

    def test_the_further_particulars_line_prints(self):
        for name in ("invoice-spec.json", "uk-vat-invoice-spec.json", "facture-spec.json"):   # the three footers
            data = spec(name)
            data["seller"]["further"] = ["Member of the Example Trade Association, no. 4471"]
            rc, said, out = run(BUILDER, data, "invoice.html")
            self.assertEqual(rc, 0, said)
            self.assertIn("Member of the Example Trade Association, no. 4471", page(out), name)

    def test_the_orders_note_is_on_the_page(self):
        data = spec("uk-vat-invoice-spec.json")
        data["note"] = "Second of three instalments under the agreement of 1 June 2026."
        rc, said, out = run(BUILDER, data, "invoice.html")
        self.assertEqual(rc, 0, said)
        self.assertIn("Second of three instalments under the agreement of 1 June 2026.", page(out))
        data = spec("uk-credit-note-spec.json")                     # a credit note's reason was left off the page
        rc, said, out = run(BUILDER, data, "credit.html")
        self.assertEqual(rc, 0, said)
        self.assertIn(data["note"], page(out))


# ---- item 3: money is recomputed -------------------------------------------------------------------------------
sys.path.insert(0, str(HERE.parent / "_checks"))
import money_check  # noqa: E402


def money(rule, path):
    return money_check.check(rule, Path(path), {"folder": ""}, "first")


def packcheck(skill, path):
    r = subprocess.run([sys.executable, str(HERE.parent / "_checks" / "packcheck.py"), skill, str(path)],
                       capture_output=True, text=True, cwd=Path(path).parent)
    return r.returncode, r.stdout + r.stderr


def page_with(data, name="invoice.html"):
    rc, said, out = run(BUILDER, data, name)
    assert rc == 0, said
    return out


class Money(unittest.TestCase):
    """EINV-SUMS (an invoice page adds up as printed: EN 16931-1 BR-CO-10, -13, -15 and -17, cited by id) and
    EINV-RATE (a rate is one the seller's country has, or the buyer's for a sale taxed there)."""

    def test_every_starter_adds_up_as_printed_and_carries_rates_its_country_has(self):
        for p in sorted((HERE / "templates").glob("*.json")):
            data = json.loads(p.read_text())
            data.setdefault("exchange_rate", 11.5) if p.name == "invoice-spec.json" else None
            out = page_with(data)
            for rule in ("EINV-SUMS", "EINV-RATE"):
                ok, why = money(rule, out)
                self.assertTrue(ok, "%s %s: %s" % (p.name, rule, why))
                self.assertFalse(str(why).startswith("WARN"), "%s %s: %s" % (p.name, rule, why))

    def test_a_rate_the_sellers_country_does_not_have_fails(self):
        data = spec("facture-spec.json")
        out = page_with(data)
        data["lines"][0]["vat_rate"] = 19                           # Germany's rate on a French invoice
        (out.parent / "spec.json").write_text(json.dumps(data, ensure_ascii=False))
        ok, why = money("EINV-RATE", out)
        self.assertFalse(ok)
        self.assertIn("19 percent is not a VAT rate of FR, whose rates are 20, 10, 5.5, 2.1", why)
        self.assertIn("europa.eu", why)

    def test_a_rate_written_as_a_fraction_fails(self):
        data = spec("uk-vat-invoice-spec.json")
        out = page_with(data)
        data["lines"][0]["vat_rate"] = 0.2
        (out.parent / "spec.json").write_text(json.dumps(data, ensure_ascii=False))
        ok, why = money("EINV-RATE", out)
        self.assertFalse(ok)
        self.assertIn("20 percent is written 20, not 0.2", why)

    def test_the_buyers_countrys_rate_passes_for_a_sale_taxed_there(self):
        data = spec("invoice-spec.json")
        data.setdefault("exchange_rate", 11.5)
        out = page_with(data)
        seller = money_check._country(data["seller"])
        other = next(c for c in ("FR", "DE", "SE") if c != seller)
        data["buyer"]["country"] = other
        rate = money_check.TABLE["countries"][other]["rates"][0]
        for line in data["lines"]:
            line["vat_rate"] = rate
        (out.parent / "spec.json").write_text(json.dumps(data, ensure_ascii=False))
        ok, why = money("EINV-RATE", out)
        self.assertTrue(ok, why)

    def test_a_page_that_does_not_add_up_fails_line_by_line(self):
        import re
        data = spec("uk-vat-invoice-spec.json")
        out = page_with(data)
        text = out.read_text()
        sums = re.search(r"<table class=['\"]sum['\"]><tbody>(.*?)</tbody></table>", text, re.S).group(1)
        first = re.findall(r"<td class='n'>(.*?)</td>", sums)[0]
        broken = text.replace("<td class='n'>%s</td>" % first, "<td class='n'>%s</td>" % first.replace("0", "9", 1), 1)
        self.assertNotEqual(broken, text)
        out.write_text(broken)
        ok, why = money("EINV-SUMS", out)
        self.assertFalse(ok)
        self.assertIn("never edit a sum on the page", why)

    def test_the_tax_is_the_rate_of_the_total_without_tax(self):
        import re
        data = spec("uk-vat-invoice-spec.json")
        out = page_with(data)
        text = out.read_text()
        sums = re.search(r"<table class=['\"]sum['\"]><tbody>(.*?)</tbody></table>", text, re.S)
        cells = re.findall(r"<td class='n'>(.*?)</td>", sums.group(1))
        self.assertGreaterEqual(len(cells), 3)
        table = money_check.page_tables(out)
        net, tax, due = (money_check._amount(c, table[0]) for c in (cells[0], cells[1], cells[-1]))
        self.assertEqual(net + tax, due)
        self.assertEqual(money_check.page_sums(out, data), [])

    def test_the_pack_runs_both_rules(self):
        sys.path.insert(0, str(HERE.parent / "_checks"))
        import packcheck as pc
        for rule in ("EINV-SUMS", "EINV-RATE"):
            self.assertIn(rule, pc.SKILL_RULES["e-invoice"])
            self.assertEqual(pc.RULE_MODULES[rule], "money_check")


# ---- item 4: the notes floor -----------------------------------------------------------------------------------
sys.path.insert(0, str(HERE.parent / "_checks"))
import notes_floor  # noqa: E402


def floor(path):
    return notes_floor.check("NOTES-FLOOR", Path(path), {"folder": ""}, "first")


def with_notes(builder, data, name, notes):
    """Build in a folder that also holds the person's notes, as a chat folder does."""
    rc, said, out = run(builder, data, name)
    assert rc == 0, said
    (out.parent / "notes.txt").write_text(notes)
    return out


IT_NOTES = """Da fatturare oggi
Emittente: {name}, P. IVA {vat}.
Iscritta al Registro delle Imprese di Padova, REA PD-000001.
Capitale sociale euro 50.000,00 i.v.
Fattura numero {number}.
"""


class NotesFloor(unittest.TestCase):
    """NOTES-FLOOR on invoices: the register number, the capital and the invoice number as the notes give them."""

    def italian(self):
        data = spec("it-fattura-spec.json")
        for key in ("rea", "share_capital", "register", "register_number", "sole_shareholder"):
            data["seller"].pop(key, None)
        data["seller"]["unknown"] = ["register", "register_number", "share_capital", "registered_office"]
        notes = IT_NOTES.format(name=data["seller"]["name"], vat=data["seller"].get("vat_id", ""), number=data["number"])
        return data, notes

    def test_the_rea_and_the_capital_the_notes_hold_are_asked_about(self):
        # The measured run: REA, share capital and the sole-shareholder line left off, and a clean check.
        data, notes = self.italian()
        rc, said, out = run(BUILDER, data, "fattura.html")
        self.assertEqual(rc, 0, said)
        (out.parent / "notes.txt").write_text(notes)
        ok, why = floor(out)
        self.assertTrue(ok, "a question, never a fail")
        self.assertTrue(why.startswith("WARN "), why)
        self.assertIn("«PD-000001»", why)
        self.assertIn("«50.000,00»", why)

    def test_a_renumbered_invoice_is_asked_about(self):
        # The measured run: "2026-A-0158" in the notes printed as number 0158, series A.
        data = spec("es-factura-spec.json")
        data["number"], data["series"] = "0158", "A"
        rc, said, out = run(BUILDER, data, "factura.html")
        self.assertEqual(rc, 0, said)
        (out.parent / "notes.txt").write_text("Factura n.º 2026-A-0158, fecha 9 de octubre de 2026.\n")
        ok, why = floor(out)
        self.assertTrue(ok)
        self.assertIn("«2026-A-0158»", why)


# ---- item 6: the file lands in the person's folder -------------------------------------------------------------
import os as _os  # noqa: E402
import re as _re6  # noqa: E402


class InThePersonsFolder(unittest.TestCase):
    """A house rule on the builders: an output path inside the library's own folder is refused, and the message
    names the working folder; every example in SKILL.md runs the builder from the working folder."""

    def refused(self, builder, data, name):
        folder = Path(tempfile.mkdtemp())
        (folder / "spec.json").write_text(json.dumps(data, ensure_ascii=False))
        target = HERE / "templates" / name                         # beside the pack, where nobody looks
        env = dict(_os.environ, CLAUDE_PROJECT_DIR=str(folder))
        env.pop("OLDPWD", None)
        r = subprocess.run([sys.executable, str(HERE / builder), str(folder / "spec.json"), str(target)],
                           capture_output=True, text=True, cwd=HERE / "templates", env=env)
        try:
            said = r.stdout + r.stderr
            self.assertNotEqual(r.returncode, 0, builder)
            self.assertIn("inside the library's own folder", said, builder)
            self.assertIn(str(folder.resolve()), said, "the working folder is named")
            self.assertFalse(target.exists(), "nothing is written beside the pack")
        finally:
            if target.exists():
                target.unlink()

    def test_an_output_path_inside_the_library_is_refused_and_the_working_folder_named(self):
        self.refused(BUILDER, spec("uk-vat-invoice-spec.json"), "made-beside-the-pack.html")
        self.refused("scripts/einvoice_create.py", spec("uk-vat-invoice-spec.json"), "made-beside-the-pack.xml")

    def test_every_example_in_skill_md_runs_the_builder_from_the_working_folder(self):
        text = (HERE / "SKILL.md").read_text()
        runs = _re6.findall(r"python3? [^\n`]*?(?:_create|build_page)\.py[^\n`]*", text)
        self.assertTrue(runs)
        for line in runs:
            self.assertRegex(line, r"^python3 <skill folder>/(scripts|page)/", line)
        self.assertIn("Work in the working folder", text)


# ---- item 7: a company's facts are written once ---------------------------------------------------------------
sys.path.insert(0, str(HERE.parent / "_checks"))
import company  # noqa: E402
import company_check  # noqa: E402

COMPANY = {"name": "Exempel Tryck AB", "street": "Verkstadsgatan 7", "postcode": "417 07", "city": "Göteborg",
           "country": "SE", "vat_id": "SE556677889901", "register_number": "556677-8899",
           "registered_office": "Göteborg", "email": "order@exempeltryck.example", "phone": "031-000 00 00",
           "payment": {"bank": "Exempelbanken", "iban": "SE35 5000 0000 0549 1000 0003", "bic": "ESSESESS"}}


def in_company_folder(builder, data, name, company_file=None):
    """Build in a folder that holds the company file, as the person's folder does."""
    folder = Path(tempfile.mkdtemp())
    (folder / "company.json").write_text(json.dumps(company_file or COMPANY, ensure_ascii=False))
    (folder / "spec.json").write_text(json.dumps(data, ensure_ascii=False))
    r = subprocess.run([sys.executable, str(HERE / builder), str(folder / "spec.json"), str(folder / name)],
                       capture_output=True, text=True, cwd=folder)
    return r.returncode, r.stdout + r.stderr, folder / name


def company_rule(path):
    return company_check.check("COMPANY-FILE", Path(path), {"folder": ""}, "first")


class CompanyFile(unittest.TestCase):
    """One company file: an invoice built from it carries the same particulars as the letter and the quotation."""

    def test_an_invoice_whose_order_names_only_the_seller_is_the_same_page_as_the_whole_order(self):
        fields = set(spec_guard.load_fields(HERE.parent / "_shared" / "company.fields.json")["fields"])
        for name in ("uk-vat-invoice-spec.json", "it-fattura-spec.json", "invoice-spec.json"):
            whole = spec(name)
            whole.setdefault("exchange_rate", 11.5) if name == "invoice-spec.json" else None
            rc, said, full = run(BUILDER, whole, "invoice.html")
            self.assertEqual(rc, 0, said)
            own = {k: v for k, v in whole["seller"].items() if k in fields}
            bare = copy.deepcopy(whole)
            bare["seller"] = {k: v for k, v in whole["seller"].items() if k not in own or k == "name"}
            rc, said, out = in_company_folder(BUILDER, bare, "invoice.html", own)
            self.assertEqual(rc, 0, "%s: %s" % (name, said))
            self.assertEqual(page(out), page(full), name)
            ok, why = company_rule(out)
            self.assertTrue(ok, "%s: %s" % (name, why))

    def test_the_payment_details_come_from_the_company_file(self):
        whole = spec("uk-vat-invoice-spec.json")
        known = spec_guard.load_fields(HERE.parent / "_shared" / "company.fields.json")["fields"]["payment"]
        ours = {k: v for k, v in whole["payment"].items() if k in known}        # the account, not this invoice's reference
        own = {"name": whole["seller"]["name"], "country": whole["seller"]["country"], "payment": ours}
        bare = copy.deepcopy(whole)
        bare["payment"] = {k: v for k, v in whole["payment"].items() if k not in ours}
        rc, said, out = in_company_folder(BUILDER, bare, "invoice.html", own)
        self.assertEqual(rc, 0, said)
        rc, said, full = run(BUILDER, whole, "invoice.html")
        self.assertEqual(page(out), page(full))

    def test_an_order_that_says_another_vat_number_stops_both_builders(self):
        whole = spec("uk-vat-invoice-spec.json")
        own = {"name": whole["seller"]["name"], "country": whole["seller"]["country"], "vat_id": "GB000000000"}
        for builder, name in ((BUILDER, "invoice.html"), ("scripts/einvoice_create.py", "invoice.xml")):
            rc, said, out = in_company_folder(builder, whole, name, own)
            self.assertNotEqual(rc, 0, builder)
            self.assertIn("seller.vat_id", said, builder)
            self.assertFalse(out.exists(), builder)


# ---- item 8: the sender's own company law ----------------------------------------------------------------------
sys.path.insert(0, str(HERE.parent / "_checks"))
import letter_check as _lc  # noqa: E402


def company_law(path):
    return _lc.check("LETTER-COMPANY", Path(path), {"folder": ""}, "first")


def _prints():
    import shutil
    if not shutil.which("pdftotext"):
        return False
    try:
        import playwright  # noqa: F401
        return True
    except ImportError:
        return bool(shutil.which("nodejam-print"))


@unittest.skipUnless(_prints(), "no printer for the page (Chromium) or no pdftotext")
class SendersCompanyLaw(unittest.TestCase):
    """LETTER-COMPANY on an invoice of a German, Austrian, Polish or Finnish company: a question, never a fail."""

    def invoice_without(self, name, *keys):
        data = spec(name)
        for key in keys:
            data["seller"].pop(key, None)
        rc, said, out = run(BUILDER, data, "invoice.pdf", "--no-facturx")
        self.assertEqual(rc, 0, said)
        return out

    def test_a_german_invoice_without_the_register_is_asked_about_and_the_reading_is_named(self):
        out = self.invoice_without("xrechnung-credit-note-spec.json", "register", "register_number", "managing_directors")
        ok, why = company_law(out)
        self.assertTrue(ok, "never a fail: %s" % why)
        self.assertTrue(why.startswith("WARN "), why)
        self.assertIn("GmbHG § 35a", why)
        self.assertIn("IHK für Oberfranken Bayreuth", why)
        self.assertIn("A question, not a fault", why)

    def test_an_austrian_invoice_is_asked_about_and_told_no_published_reading_was_found(self):
        out = self.invoice_without("at-rechnung-spec.json", "register", "register_number")
        ok, why = company_law(out)
        self.assertTrue(ok, why)
        self.assertTrue(why.startswith("WARN "), why)
        self.assertIn("UGB § 14", why)
        self.assertIn("no chamber or ministry page", why)

    def test_the_four_countries_starters_carry_no_question(self):
        for name in ("xrechnung-credit-note-spec.json", "at-rechnung-spec.json", "pl-faktura-spec.json", "fi-lasku-spec.json"):
            out = self.invoice_without(name)
            ok, why = company_law(out)
            self.assertIn(ok, (True, None), "%s: %s" % (name, why))
            self.assertFalse(str(why).startswith("WARN"), "%s: %s" % (name, why))


# ---- item 9: left open by the trade-layout work -------------------------------------------------------------
class OneLayoutArithmetic(unittest.TestCase):
    """The invoice page moves onto a country's window layout with the shared letter's own arithmetic, not a copy."""

    def test_the_page_calls_the_shared_layout(self):
        sys.path.insert(0, str(HERE / "page"))
        sys.path.insert(0, str(HERE.parent / "_shared"))
        import inspect
        import build_page
        import letter
        self.assertIn("letter.layout_css(lay, INFO_GRID)", inspect.getsource(build_page.layout_css))
        self.assertIn("letter.on_layout(html, lay, INFO_GRID)", inspect.getsource(build_page.on_layout))
        for lid, lay in letter.LAYOUTS.items():
            self.assertEqual(build_page.layout_css(lay), letter.layout_css(lay, build_page.INFO_GRID), lid)


# ---- item 9: one company, one footer ------------------------------------------------------------------------
class OneFooter(unittest.TestCase):
    """The invoice page writes the seller's own address as the company's letter and trade document do."""

    def test_the_footers_first_column_is_the_shared_own_address(self):
        import html
        import re
        sys.path.insert(0, str(HERE.parent / "_shared"))
        import letter
        flat = lambda s: html.unescape(re.sub(r"<[^>]+>", "", s)).replace("\u00a0", " ").strip()  # noqa: E731
        for name in ("es-factura-spec.json", "it-fattura-spec.json", "uk-vat-invoice-spec.json", "us-invoice-spec.json",
                     "au-tax-invoice-spec.json", "nl-factuur-spec.json", "fi-lasku-spec.json", "ie-vat-invoice-spec.json",
                     "pl-faktura-spec.json", "facture-spec.json"):
            data = spec(name)
            rc, said, out = run(BUILDER, data, "page.html")
            self.assertEqual(rc, 0, said)
            foot = re.search(r"<footer[^>]*>\s*<div[^>]*>(.*?)</div>", out.read_text(), re.S)
            self.assertTrue(foot, name)
            want = letter.own_address(data["seller"], (data.get("buyer") or {}).get("country"))
            self.assertEqual([flat(x) for x in re.split(r"<br\s*/?>", foot.group(1))], [x.replace("\u00a0", " ") for x in want], name)


if __name__ == "__main__":
    unittest.main()
