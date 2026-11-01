"""Depth 4, trade documents: nothing the data file gives is dropped. An unknown key, a value of the wrong
shape (notes as one string, an amount as text, a VAT rate written 0.2 for 20 percent) and a key this kind of
document has no place for stop the build by name (skills/_shared/spec_guard.py, spec.fields.json); the
sender's further particulars print in the footer. A house rule on the builder's own input. Needs python-docx."""
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


BUILDER = "scripts/trade_create.py"
sys.path.insert(0, str(HERE / "scripts"))
import trade_create as tc  # noqa: E402


class NothingDropped(unittest.TestCase):
    def test_every_starter_passes_the_guard(self):
        fields = spec_guard.load_fields(HERE / "spec.fields.json")
        for p in sorted((HERE / "templates").glob("*.json")):
            self.assertEqual(spec_guard.problems(json.loads(p.read_text()), fields), [], p.name)

    def test_every_starter_gives_nothing_its_kind_does_not_print(self):
        for p in sorted((HERE / "templates").glob("*.json")):
            self.assertEqual(tc.not_printed(json.loads(p.read_text())), [], p.name)

    def test_an_unknown_key_fails_with_its_name_and_where_it_can_go(self):
        data = spec("purchase-order.spec.json")
        data["buyer"]["contact"] = "Peter Lang, Fleet and Purchasing Manager"       # the measured run's own key
        rc, said, out = run(BUILDER, data, "po.docx")
        self.assertNotEqual(rc, 0)
        self.assertIn('unknown key \\"buyer.contact\\"', said)
        self.assertIn("references", said)
        self.assertFalse(out.exists(), "nothing is built on an error")

    def test_a_string_in_a_list_field_fails(self):
        data = spec("quotation.spec.json")
        data["notes"] = "Part deliveries are not accepted."                         # printed one letter a line before
        rc, said, out = run(BUILDER, data, "q.docx")
        self.assertNotEqual(rc, 0)
        self.assertIn("is one string", said)
        self.assertIn("one letter a line", said)
        self.assertFalse(out.exists())

    def test_a_rate_written_as_a_fraction_fails(self):
        data = spec("purchase-order.spec.json")
        for line in data["lines"]:
            line["vat_rate"] = 0.20                                                # 0.2 percent before; 20 was meant
        rc, said, out = run(BUILDER, data, "po.docx")
        self.assertNotEqual(rc, 0)
        self.assertIn("lines[0].vat_rate", said)
        self.assertIn("20 percent is 20, not 0.2", said)
        self.assertFalse(out.exists())

    def test_an_amount_given_as_text_fails(self):
        data = spec("quotation.spec.json")
        data["lines"][0]["unit_price"] = "1 890,00"
        rc, said, _ = run(BUILDER, data, "q.docx")
        self.assertNotEqual(rc, 0)
        self.assertIn("lines[0].unit_price", said)
        self.assertIn("as a number", said)

    def test_the_further_particulars_line_prints(self):
        data = spec("quotation.spec.json")
        data["seller"]["further"] = ["Approved for F-tax (godkänd för F-skatt)"]
        rc, said, out = run(BUILDER, data, "q.docx")
        self.assertEqual(rc, 0, said)
        self.assertIn("Approved for F-tax (godkänd för F-skatt)", words(out))

    def test_what_this_kind_of_document_does_not_print_is_an_error(self):
        data = spec("purchase-order.spec.json")
        data["bank"] = {"bank": "Example Bank", "iban": "GB00 EXAM 0000 0000 0000 00"}
        rc, said, _ = run(BUILDER, data, "po.docx")
        self.assertNotEqual(rc, 0)
        self.assertIn("bank", said)
        self.assertIn("not printed on a purchase order", said)
        data = spec("quotation.spec.json")
        data["packages"] = 3
        rc, said, _ = run(BUILDER, data, "q.docx")
        self.assertNotEqual(rc, 0)
        self.assertIn("packages", said)

    def test_the_recipients_own_details_are_not_silently_left_off(self):
        data = spec("quotation.spec.json")
        data["buyer"]["email"] = "inkop@exempel-kund.example"
        rc, said, _ = run(BUILDER, data, "q.docx")
        self.assertNotEqual(rc, 0)
        self.assertIn("buyer.email", said)
        self.assertIn("notes", said)


# ---- item 2: thin pages fail -----------------------------------------------------------------------------------
sys.path.insert(0, str(HERE.parent / "_checks"))
import thin_pages  # noqa: E402


def thin(rule, path):
    return thin_pages.check(rule, path, {"folder": ""}, "first")


def packcheck(skill, path):
    r = subprocess.run([sys.executable, str(HERE.parent / "_checks" / "packcheck.py"), skill, str(path)],
                       capture_output=True, text=True, cwd=Path(path).parent)
    return r.returncode, r.stdout + r.stderr


class ThinPages(unittest.TestCase):
    """TRADE-EMPTY, a house rule: a document to a town alone, or from a sender with no street, fails."""

    def test_every_starter_has_whole_addresses_and_lines_that_say_what_they_are(self):
        for p in sorted((HERE / "templates").glob("*.json")):
            rc, said, out = run(BUILDER, json.loads(p.read_text()), "doc.docx")
            self.assertEqual(rc, 0, said)
            ok, why = thin("TRADE-EMPTY", out)
            self.assertTrue(ok, "%s: %s" % (p.name, why))

    def test_an_address_holding_only_the_town_fails(self):
        data = spec("order-confirmation.spec.json")
        data["buyer"] = {"name": data["buyer"]["name"], "city": "Mannheim", "country": "DE"}
        rc, said, out = run(BUILDER, data, "ab.docx")
        self.assertEqual(rc, 0, said)
        ok, why = thin("TRADE-EMPTY", out)
        self.assertFalse(ok)
        self.assertIn("the street and number", why)
        self.assertIn('"buyer"', why)
        rc, said = packcheck("trade-documents", out)
        self.assertEqual(rc, 1)
        self.assertIn("FAIL TRADE-EMPTY", said)

    def test_a_sender_with_no_street_fails(self):
        data = spec("order-confirmation.spec.json")
        data["seller"].pop("street", None)
        rc, said, out = run(BUILDER, data, "ab.docx")
        self.assertEqual(rc, 0, said)
        ok, why = thin("TRADE-EMPTY", out)
        self.assertFalse(ok)
        self.assertIn("the sender's own address", why)

    def test_a_purchase_order_reads_the_supplier_as_the_recipient(self):
        data = spec("purchase-order.spec.json")
        data["seller"].pop("street", None)
        rc, said, out = run(BUILDER, data, "po.docx")
        self.assertEqual(rc, 0, said)
        ok, why = thin("TRADE-EMPTY", out)
        self.assertFalse(ok)
        self.assertIn('"seller"', why)


# ---- item 3: money is recomputed -------------------------------------------------------------------------------
sys.path.insert(0, str(HERE.parent / "_checks"))
import money_check  # noqa: E402


def money(rule, path):
    return money_check.check(rule, Path(path), {"folder": ""}, "first")


def built_with(data, name="doc.docx"):
    """A trade document written by the builder's own writer, past the guard: what a file made before the guard,
    or by another tool, looks like to the check."""
    folder = Path(tempfile.mkdtemp())
    (folder / "spec.json").write_text(json.dumps(data, ensure_ascii=False))
    out = folder / name
    tc.write_docx(data, out, tc.compute(data))
    return out


class Money(unittest.TestCase):
    """TRADE-SUMS (the arithmetic of EN 16931-1 BR-CO-10, -13, -14, -15 and -17, cited by id) and TRADE-RATE
    (a rate is one the seller's country has: tax_rates.json, each country with its source and the day read)."""

    def test_every_priced_starter_adds_up_and_carries_rates_its_country_has(self):
        for p in sorted((HERE / "templates").glob("*.json")):
            data = json.loads(p.read_text())
            rc, said, out = run(BUILDER, data, "doc.docx")
            self.assertEqual(rc, 0, said)
            for rule in ("TRADE-SUMS", "TRADE-RATE"):
                ok, why = money(rule, out)
                self.assertIn(ok, (True, None), "%s %s: %s" % (p.name, rule, why))
                self.assertFalse(str(why).startswith("WARN"), "%s %s: %s" % (p.name, rule, why))

    def test_the_table_names_its_source_and_the_day_it_was_read(self):
        table = money_check.TABLE
        self.assertRegex(table["read"], r"^\d{4}-\d{2}-\d{2}$")
        for code, entry in table["countries"].items():
            self.assertTrue(entry["rates"], code)
            self.assertIn("https://", table["sources"][entry["source"]], code)

    def test_a_rate_written_as_a_fraction_fails(self):
        # The measured run: a purchase order with VAT worked out at 0.2 percent, and a clean check.
        data = spec("purchase-order.spec.json")
        for line in data["lines"]:
            line["vat_rate"] = 0.2
        out = built_with(data)
        ok, why = money("TRADE-RATE", out)
        self.assertFalse(ok)
        self.assertIn("20 percent is written 20, not 0.2", why)
        rc, said = packcheck("trade-documents", out)
        self.assertEqual(rc, 1)
        self.assertIn("FAIL TRADE-RATE", said)

    def test_a_rate_the_country_does_not_have_fails_with_the_table_it_was_read_from(self):
        data = spec("purchase-order.spec.json")
        data["seller"]["country"] = "GB"                             # a British supplier charging Germany's rate
        data["lines"][0]["vat_rate"] = 19
        ok, why = money("TRADE-RATE", built_with(data))
        self.assertFalse(ok)
        self.assertIn("19 percent is not a VAT rate of GB, whose rates are 20, 5", why)
        self.assertIn("gov.uk/vat-rates", why)
        self.assertIn("Never pick a rate yourself", why)

    def test_a_rate_in_force_until_a_date_passes_with_a_question(self):
        data = spec("order-confirmation-fi.spec.json")
        data["lines"][0]["vat_rate"] = 14
        ok, why = money("TRADE-RATE", built_with(data))
        self.assertTrue(ok)
        self.assertTrue(why.startswith("WARN "), why)
        self.assertIn("until 31 December 2025", why)

    def test_the_united_states_has_no_national_list(self):
        data = spec("quotation-us.spec.json")
        data["lines"][0]["vat_rate"] = 8.875
        ok, why = money("TRADE-RATE", built_with(data))
        self.assertTrue(ok, why)

    def test_a_sum_that_does_not_follow_from_the_lines_fails(self):
        from docx import Document
        data = spec("quotation.spec.json")
        out = built_with(data)
        _lines, _vat, net, _tax, gross = tc.compute(data)
        doc = Document(out)
        page = tc.Page(data)
        hit = 0
        for table in doc.tables:
            for row in table.rows:
                for cell in row.cells:
                    for p in cell.paragraphs:
                        for r in p.runs:
                            if page.money(gross) in r.text:
                                r.text = r.text.replace(page.money(gross), page.money(gross + 100))
                                hit += 1
        self.assertTrue(hit, "the total including VAT was not found to edit")
        doc.save(out)
        ok, why = money("TRADE-SUMS", out)
        self.assertFalse(ok)
        self.assertIn("total including VAT", why)
        self.assertIn("never type a sum into the file", why)

    def test_a_delivery_note_shows_no_price_and_is_not_read(self):
        rc, said, out = run(BUILDER, spec("delivery-note.spec.json"), "dn.docx")
        self.assertEqual(rc, 0, said)
        self.assertIsNone(money("TRADE-SUMS", out)[0])


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
        self.refused(BUILDER, spec("quotation.spec.json"), "made-beside-the-pack.docx")

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
    """One company file: a quotation built from it carries the company's particulars and its bank account."""

    def bare(self):
        data = spec("quotation.spec.json")
        data["seller"] = {"name": "Exempel Tryck AB"}
        data.pop("bank", None)
        return data

    def test_the_quotation_takes_the_seller_and_the_bank_account_from_the_company_file(self):
        rc, said, out = in_company_folder(BUILDER, self.bare(), "offert.docx")
        self.assertEqual(rc, 0, said)
        text = words(out)
        for value in ("Verkstadsgatan 7", "SE556677889901", "556677-8899", "SE35 5000 0000 0549 1000 0003"):
            self.assertIn(value, text)
        ok, why = company_rule(out)
        self.assertTrue(ok, why)

    def test_a_data_file_that_says_something_else_stops_the_build(self):
        data = self.bare()
        data["seller"]["register_number"] = "556677-0000"
        rc, said, out = in_company_folder(BUILDER, data, "offert.docx")
        self.assertNotEqual(rc, 0)
        self.assertIn("seller.register_number", said)
        self.assertIn("company file", said)
        self.assertFalse(out.exists())

    def test_every_starters_own_sender_written_as_the_company_file_passes(self):
        fields = set(spec_guard.load_fields(HERE.parent / "_shared" / "company.fields.json")["fields"])
        for p in sorted((HERE / "templates").glob("*.json")):
            data = json.loads(p.read_text())
            role = "buyer" if data["type"] == "purchase_order" else "seller"
            own = {k: v for k, v in data[role].items() if k in fields}
            rc, said, out = in_company_folder(BUILDER, data, "doc.docx", own)
            self.assertEqual(rc, 0, "%s: %s" % (p.name, said))
            ok, why = company_rule(out)
            self.assertTrue(ok, "%s: %s" % (p.name, why))


# ---- item 8: the sender's own company law ----------------------------------------------------------------------
sys.path.insert(0, str(HERE.parent / "_checks"))
import letter_check as _lc  # noqa: E402


def company_law(path):
    return _lc.check("LETTER-COMPANY", Path(path), {"folder": ""}, "first")


class SendersCompanyLaw(unittest.TestCase):
    """LETTER-COMPANY on a trade document: a quotation and an order are order forms of their sender."""

    def test_a_quotation_without_the_sellers_register_number_fails_with_the_article(self):
        data = spec("quotation.spec.json")
        data["seller"].pop("register_number")
        rc, said, out = run(BUILDER, data, "offert.docx")
        self.assertEqual(rc, 0, said)
        ok, why = company_law(out)
        self.assertFalse(ok)
        self.assertIn("aktiebolagslagen", why)
        self.assertIn("register_number", why)
        self.assertIn('put it in "seller"', why)

    def test_a_purchase_order_is_its_buyers_letter(self):
        data = spec("purchase-order.spec.json")
        data["buyer"].pop("registered_office")
        rc, said, out = run(BUILDER, data, "order.docx")
        self.assertEqual(rc, 0, said)
        ok, why = company_law(out)
        self.assertFalse(ok)
        self.assertIn('put it in "buyer"', why)

    def test_a_quotation_keeps_the_f_skatt_line_the_persons_files_give(self):
        data = spec("quotation.spec.json")
        rc, said, out = run(BUILDER, data, "offert.docx")
        self.assertEqual(rc, 0, said)
        self.assertEqual(company_law(out)[0], True)                # no file says so: the page is left alone
        (out.parent / "foretaget.txt").write_text("Example Wholesale AB\nGodkänd för F-skatt\n")
        ok, why = company_law(out)
        self.assertFalse(ok)
        self.assertIn("foretaget.txt", why)
        self.assertIn('"further"', why)

    def test_the_f_skatt_line_in_further_passes(self):
        data = spec("quotation.spec.json")
        data["seller"]["further"] = ["Godkänd för F-skatt"]
        rc, said, out = run(BUILDER, data, "offert.docx")
        self.assertEqual(rc, 0, said)
        (out.parent / "foretaget.txt").write_text("Godkänd för F-skatt\n")
        self.assertIn("F-skatt", words(out))
        self.assertIn(company_law(out)[0], (True, None))

    def test_every_starter_states_what_its_senders_law_asks(self):
        for p in sorted((HERE / "templates").glob("*.json")):
            rc, said, out = run(BUILDER, json.loads(p.read_text()), "doc.docx")
            self.assertEqual(rc, 0, said)
            ok, why = company_law(out)
            self.assertIn(ok, (True, None), "%s: %s" % (p.name, why))
            self.assertFalse(str(why).startswith("WARN"), "%s: %s" % (p.name, why))



class PdfWithoutItsPage(unittest.TestCase):
    """A PDF whose .html is gone is never held to another locale's dates and amounts (timed command run c07)."""

    def test_an_english_pro_forma_without_its_page_skips_the_locale_rules(self):
        rc, said, out = run(BUILDER, spec("proforma-invoice-ie.spec.json"), "pf.pdf")
        self.assertEqual(rc, 0, said)
        out.with_suffix(".html").unlink()
        r = subprocess.run([sys.executable, str(HERE.parent / "_checks" / "packcheck.py"), "trade-documents", str(out)],
                           capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stdout)
        sys.path.insert(0, str(HERE.parent / "_checks"))
        import locale_floor
        import packcheck
        case = packcheck.case_for(out)
        ok, why = locale_floor.check("LOCALE-DATE", out, case, "first")
        self.assertIsNone(ok)
        self.assertIn("pf.html", why)


class NotGivenStaysOpen(unittest.TestCase):
    """A number or bank the files do not give is declared unknown, never a marker (timed command run c07)."""

    def test_a_pro_forma_with_no_number_or_bank_yet_is_built_and_says_so(self):
        data = spec("proforma-invoice.spec.json")
        data.pop("number")
        data.pop("bank", None)
        data["unknown"] = ["number", "bank"]
        rc, said, out = run(BUILDER, data, "pf.docx")
        self.assertEqual(rc, 0, said)
        told = json.loads(said.strip().splitlines()[-1])["warnings"]
        self.assertTrue(any("numbers it" in w for w in told), told)
        self.assertTrue(any("bank" in w for w in told), told)
        r = subprocess.run([sys.executable, str(HERE.parent / "_checks" / "packcheck.py"), "trade-documents", str(out)],
                           capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stdout)

    def test_a_marker_in_place_of_a_fact_stops_the_build(self):
        for key, value in (("number", "TBC"), ("number", "[number to be assigned]")):
            data = spec("proforma-invoice.spec.json")
            data[key] = value
            rc, said, out = run(BUILDER, data, "pf.docx")
            self.assertEqual(rc, 1, said)
            self.assertIn('"unknown"', json.loads(said)["error"])
        data = spec("proforma-invoice.spec.json")
        data["bank"] = {"bank": "TBC"}
        rc, said, out = run(BUILDER, data, "pf.docx")
        self.assertEqual(rc, 1, said)
        self.assertFalse(out.exists())

# ---- item 9: left open by the trade-layout work -------------------------------------------------------------
class FrenchForFrance(unittest.TestCase):
    """A French seller's documents are written in France's French, with its company line as its invoice prints it."""

    def test_a_french_sellers_quotation_is_a_devis_in_french(self):
        data = spec("devis-fr.spec.json")
        self.assertEqual(tc.language(data)[0], "fr-FR")
        data.pop("language")                                        # the seller's country alone decides
        self.assertEqual(tc.language(data)[0], "fr-FR")
        rc, said, out = run(BUILDER, data, "devis.docx")
        self.assertEqual(rc, 0, said)
        text = words(out)
        for word in ("Devis", "Numéro de devis", "Total HT", "Total TTC", "Montant HT", "Valable jusqu"):
            self.assertIn(word, text)
        for english in ("Quotation", "Total excluding VAT", "Net amount"):
            self.assertNotIn(english, text)

    def test_the_other_documents_have_frances_names(self):
        w = tc.WORDS["fr-FR"]["title"]
        self.assertEqual((w["purchase_order"], w["delivery_note"], w["proforma_invoice"]),
                         ("Bon de commande", "Bon de livraison", "Facture pro forma"))
        self.assertEqual(tc.WORDS["fr-BE"]["title"]["quotation"], "Offre de prix", "Belgium keeps its own")
        for row in tc.LABELS:
            self.assertIn("fr-FR", row)

    def test_the_footer_carries_the_french_company_line_and_the_rule_passes(self):
        rc, said, out = run(BUILDER, spec("devis-fr.spec.json"), "devis.docx")
        self.assertEqual(rc, 0, said)
        text = words(out).replace("\u00a0", " ").replace("\u202f", " ")
        self.assertIn("SAS au capital de 10 000 €", text)
        self.assertIn("RCS Lyon 000 000 018", text)
        ok, why = company_law(out)
        self.assertTrue(ok, why)
        rc, said = packcheck("trade-documents", out)
        self.assertEqual(rc, 0, said)

    def test_french_between_two_other_countries_is_frances_french(self):
        data = spec("quotation.spec.json")
        data["language"] = "fr"
        self.assertEqual(tc.language(data)[0], "fr-FR")
        data["buyer"]["country"] = "BE"
        self.assertEqual(tc.language(data)[0], "fr-BE")


class WorkbookWords(unittest.TestCase):
    """The locale rules read the words a workbook shows, never the packed bytes of its file."""

    def test_a_workbooks_text_is_its_strings(self):
        import locale_floor
        rc, said, out = run(BUILDER, spec("devis-fr.spec.json"), "devis.xlsx")
        self.assertEqual(rc, 0, said)
        text = locale_floor._text(out)
        self.assertIn("Total HT", text)
        self.assertNotIn("PK", text[:4])
        self.assertNotIn("1123.55", text, "a number cell is not text: the reader's program writes it out")
        rc, said = packcheck("trade-documents", out)
        self.assertEqual(rc, 0, said)

    def test_a_tariff_number_in_a_cell_is_not_an_amount(self):
        import locale_floor
        rc, said, out = run(BUILDER, spec("proforma-invoice.spec.json"), "proforma.xlsx")
        self.assertEqual(rc, 0, said)
        self.assertIn("8419.81", locale_floor._text(out))
        ok, why = locale_floor.check("LOCALE-NUMBER", out, {"locale": "sv-SE"}, "first")
        self.assertIsNone(ok, why)
        rc, said = packcheck("trade-documents", out)
        self.assertEqual(rc, 0, said)

    def test_an_amount_written_as_text_the_wrong_way_is_still_caught(self):
        import locale_floor
        data = spec("devis-fr.spec.json")
        data["notes"] = ["Frais de port : 12.50 EUR par colis, 25.00 EUR par palette."]
        rc, said, out = run(BUILDER, data, "devis.xlsx")
        self.assertEqual(rc, 0, said)
        ok, why = locale_floor.check("LOCALE-NUMBER", out, {"locale": "fr-FR"}, "first")
        self.assertIs(ok, False, why)


# ---- item 9: one company, one footer ------------------------------------------------------------------------
class OneFooter(unittest.TestCase):
    """A company's own address reads the same in the footer of its letter, its invoice and its trade document."""

    def test_the_town_line_has_one_form_per_country(self):
        line = lambda **p: tc.letter.town_line(p)  # noqa: E731
        self.assertEqual(line(city="Madrid", province="Madrid", postcode="28001", country="ES"), "28001 Madrid")
        self.assertEqual(line(city="Sabadell", province="Barcelona", postcode="08201", country="ES"), "08201 Sabadell (Barcelona)")
        self.assertEqual(line(city="Milano", province="mi", postcode="20121", country="IT"), "20121 Milano (MI)")
        self.assertEqual(line(city="Leeds", postcode="LS1 4BR", country="GB"), "Leeds LS1 4BR")
        self.assertEqual(line(city="Brisbane", state="QLD", postcode="4000", country="AU"), "Brisbane QLD 4000")
        self.assertEqual(line(city="Melbourne VIC", postcode="3000", country="AU"), "Melbourne VIC 3000")
        self.assertEqual(line(city="Austin, TX", state="TX", postcode="78701", country="US"), "Austin, TX 78701")
        self.assertEqual(line(city="Portland", state="OR", postcode="97204", country="US"), "Portland OR 97204")
        self.assertEqual(line(city="Jyväskylä", postcode="40100", country="FI"), "40100 Jyväskylä")
        self.assertEqual(line(city="Utrecht", postcode="3526 KM", country="NL"), "3526 KM Utrecht")

    def test_the_own_address_keeps_every_line_and_names_the_country_abroad(self):
        own = tc.letter.own_address
        it = {"name": "Esempio Imballaggi S.r.l.", "building": "Scala B", "street": "Via Esempio 21", "city": "Bologna",
              "province": "BO", "postcode": "40121", "country": "IT"}
        self.assertEqual(own(it), ["Esempio Imballaggi S.r.l.", "Scala B", "Via Esempio 21", "40121 Bologna (BO)"])
        self.assertEqual(own(it, "IT"), own(it))
        self.assertEqual(own(it, "DE")[-1], "ITALY")
        ie = {"name": "Liffey Example Ltd", "street": "Unit 4", "street2": "Example Business Park", "locality": "Ballymount",
              "city": "Dublin 24", "postcode": "D24 X2Y3", "country": "IE"}
        self.assertEqual(own(ie)[1:], ["Unit 4", "Example Business Park", "Ballymount", "Dublin 24 D24 X2Y3"])
        # the address field keeps the post office's own form
        self.assertEqual(tc.letter.postal_lines(it, "IT")[-1], "40121 BOLOGNA BO")

    def test_every_starters_footer_is_the_shared_own_address(self):
        for p in sorted((HERE / "templates").glob("*.json")):
            data = json.loads(p.read_text())
            want = tc.letter.own_address(tc.own(tc.sender(data)), tc.recipient(data).get("country"))
            self.assertEqual(tc.Page(data).footer()[0], want, p.name)
            self.assertFalse([x for x in want[1:-1] if x.isupper() and x.isalpha()], p.name)

    def test_one_spanish_company_one_footer_on_three_papers(self):
        company = {"name": "Ejemplo Imprenta S.L.", "street": "Calle del Ejemplo 12", "postcode": "28001", "city": "Madrid",
                   "province": "Madrid", "country": "ES"}
        quote = spec("quotation-es.spec.json")
        quote["seller"].update(company)
        carta = json.loads((HERE.parent / "business-letter/templates/carta-es.spec.json").read_text())
        carta["sender"].update(company)
        factura = json.loads((HERE.parent / "e-invoice/templates/es-factura-spec.json").read_text())
        factura["seller"].update(company)
        for builder, data, name in ((BUILDER, quote, "presupuesto.docx"),
                                    ("../business-letter/scripts/letter_create.py", carta, "carta.docx"),
                                    ("../e-invoice/page/build_page.py", factura, "factura.html")):
            rc, said, out = run(builder, data, name)
            self.assertEqual(rc, 0, said)
            text = words(out) if name.endswith(".docx") else _re6.sub(r"<[^>]+>", "\n", out.read_text())
            for line in tc.letter.own_address(company):
                self.assertIn(line, text, name)
        self.assertEqual(tc.Page(quote).footer()[0], tc.letter.own_address(company))


if __name__ == "__main__":
    unittest.main()
