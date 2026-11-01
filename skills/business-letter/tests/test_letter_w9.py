"""Offline tests for the letters of Spain, Italy and Poland (wave 9): the window on the right inside each
operator's published zone, the address as Correos, Poste Italiane and Poczta Polska read it, the place and
date, the salutation and closing, the company particulars of Código de Comercio art. 24, Codice civile
art. 2250 and Kodeks spółek handlowych arts. 206 and 374; and the DIN 5008 letter on the one rule every
letter and invoice follows (postal_lines, the information block ending on the text's right edge). Needs
python-docx; the PDF tests need Chromium (the app's printer or Playwright) and skip without it."""
import copy
import json
import shutil
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
CHECKS = HERE.parent / "_checks"
sys.path.insert(0, str(HERE / "scripts"))
sys.path.insert(0, str(HERE.parent / "_shared"))
sys.path.insert(0, str(CHECKS))
import letter  # noqa: E402
import letter_check as lc  # noqa: E402
import letter_create as lcr  # noqa: E402
import locale_floor  # noqa: E402
import window_letter as wl  # noqa: E402

RULES = ("LETTER-DIN5008", "LETTER-WINDOW", "LETTER-ADDRESS", "LETTER-PARTS", "LETTER-FORM", "LETTER-DATE",
         "LETTER-LANGUAGE", "LETTER-PAGES", "LETTER-COMPANY")
W9 = ("carta-es", "lettera-it", "pismo-pl")


def can_print():
    if shutil.which("nodejam-print"):
        return True
    try:
        import playwright  # noqa: F401
        return True
    except ImportError:
        return False


def spec(name):
    return json.loads((HERE / "templates" / (name + ".spec.json")).read_text())


def changed(name, **keys):
    data = copy.deepcopy(spec(name))
    data.update(keys)
    return data


class Built:
    """A letter built from a spec in a folder of its own, the spec beside it as a chat folder holds both."""

    def __init__(self, data, kind="docx", din=False):
        self.dir = Path(tempfile.mkdtemp())
        (self.dir / "spec.json").write_text(json.dumps(data, ensure_ascii=False))
        self.path = self.dir / ("letter." + kind)
        mod = lcr if din else wl
        (mod.write_docx if kind == "docx" else mod.write_pdf)(data, self.path)

    def check(self, rule):
        return lc.check(rule, self.path, {}, "first")


class Starters(unittest.TestCase):
    def test_every_wave_9_starter_passes_as_word(self):
        for name in W9:
            b = Built(spec(name))
            for rule in RULES:
                ok, why = b.check(rule)
                self.assertIsNot(ok, False, "%s %s: %s" % (name, rule, why))
            self.assertTrue(b.check("LETTER-WINDOW")[0], name)
            self.assertTrue(b.check("LETTER-COMPANY")[0], name)

    @unittest.skipUnless(can_print(), "no Chromium to print with")
    def test_every_wave_9_starter_passes_as_pdf(self):
        for name in W9:
            b = Built(spec(name), "pdf")
            for rule in RULES:
                ok, why = b.check(rule)
                self.assertIsNot(ok, False, "%s %s: %s" % (name, rule, why))
            self.assertTrue(b.check("LETTER-WINDOW")[0], name)

    def test_the_starters_name_no_real_looking_company(self):
        for name, word in (("carta-es", "Ejemplo"), ("lettera-it", "Esempio"), ("pismo-pl", "Przykład")):
            s = spec(name)
            self.assertTrue(s["sender"]["name"].startswith(word) and s["recipient"]["name"].startswith(word), name)
            self.assertNotEqual(s["sender"]["name"], s["recipient"]["name"])
            self.assertTrue(s["sender"]["email"].endswith(".example"))


class Windows(unittest.TestCase):
    """Each operator publishes the zone the address must stay in, none a window position."""

    def test_each_country_names_what_was_read(self):
        for cc in ("ES", "IT", "PL"):
            status, text = letter.WINDOW_SOURCES[cc]
            self.assertEqual(status, "zone")
            self.assertIn("exact window position not published", text)
            self.assertIn(letter.COUNTRY_LAYOUT[cc], letter.LAYOUTS)

    def test_the_window_is_on_the_right_inside_every_zone(self):
        # On a DL envelope (110 x 220 mm) with the sheet at its top-left: Correos lets the address run from
        # 140 mm from the right edge (80 mm across) and from 40 mm down to 15 mm above the bottom (95 mm);
        # Poste Italiane 140 mm from the corner and 15 mm from the edges; Poczta Polska the same field,
        # a window at least 15 mm from the right edge.
        for lid in ("es", "it", "pl"):
            wx, wy, ww, wh = letter.LAYOUTS[lid]["window"]
            self.assertGreater(wx + ww / 2, 105, lid)                 # the right half of the sheet
            self.assertGreaterEqual(wx, 220 - 140, lid)
            self.assertLessEqual(wx + ww, 220 - 15, lid)
            self.assertGreaterEqual(wy, 40, lid)
            self.assertLessEqual(wy + wh, 110 - 15, lid)

    def test_poland_keeps_10_mm_around_the_address_and_5_on_the_right(self):
        lay = letter.LAYOUTS["pl"]
        wx, wy, ww, wh = lay["window"]
        x0, y0, x1, y1 = letter.window_box(lay)
        self.assertEqual((x0 - wx, y0 - wy, wx + ww - x1, wy + wh - y1), (10, 10, 5, 10))
        self.assertGreaterEqual(y1 - lay["address_at"][1], 5 * lay["line"])     # five address lines fit

    def test_italy_keeps_5_mm_above_and_below_and_15_on_the_left(self):
        lay = letter.LAYOUTS["it"]
        wx, wy, ww, wh = lay["window"]
        x0, y0, x1, y1 = letter.window_box(lay)
        self.assertEqual((x0 - wx, y0 - wy, wy + wh - y1), (15, 5, 5))

    def test_spain_shows_the_address_in_the_115_x_225_envelope_too(self):
        # That envelope's window, mirrored the same way, opens 115-205 mm across and 55-100 mm down.
        x0, y0, x1, y1 = letter.window_box(letter.LAYOUTS["es"])
        self.assertTrue(x0 >= 115 and y0 >= 55 and x1 <= 205 and y1 <= 100)

    def test_an_invoice_block_goes_left_of_the_window(self):
        for lid in ("es", "it", "pl"):
            x, y, w = letter.info_box(letter.LAYOUTS[lid])
            self.assertEqual((x, y), (25, 50), lid)
            self.assertLessEqual(x + w, letter.LAYOUTS[lid]["window"][0] - 5, lid)

    def test_word_puts_the_address_in_the_window(self):
        for name in W9:
            b = Built(spec(name))
            d = lc.docx_layout(b.path)
            lay = letter.letter_layout(spec(name))[1]
            x0, y0, x1, y1 = letter.window_box(lay)
            self.assertGreaterEqual(d["margins"]["left"] + d["lead"], x0 - 0.5, name)
            self.assertGreaterEqual(d["margins"]["top"] + d["row0"], y0 - 0.5, name)

    @unittest.skipUnless(can_print(), "no Chromium to print with")
    def test_an_address_too_tall_for_the_window_fails(self):
        s = spec("pismo-pl")
        s["recipient"].update(name="Przykład Księgarnia Naukowa i Antykwariat Wzorcowy sp. z o.o.", street2="budynek C, wejście od podwórza",
                              street="ul. Bardzo Długiej Nazwy Przykładowej Ulicy Wzorcowej 114 lok. 23")
        ok, why = Built(s, "pdf").check("LETTER-WINDOW")
        self.assertFalse(ok)
        self.assertIn("outside the window", why)

    @unittest.skipUnless(can_print(), "no Chromium to print with")
    def test_a_hyphen_in_the_footer_does_not_end_a_line(self):
        # The Registro Mercantil entry ends in "hoja M-000000"; broken after the hyphen it reads back as M000000.
        b = Built(spec("carta-es"), "pdf")
        self.assertIn("M-000000", lc.text_of(b.path))
        self.assertIn("white-space:nowrap", letter.keep("hoja M-000000"))
        self.assertIn("@</span><wbr>", letter.keep("info@ejemplo-imprenta.example"))


class Addresses(unittest.TestCase):
    def test_spain(self):
        got = letter.postal_lines(spec("carta-es")["recipient"], "ES")
        self.assertEqual(got, ["Ejemplo Papelería S.L.", "Sra. Lucía Ferrer", "Avenida de la Muestra 45, 2.º B",
                               "46000 VALENCIA", "VALENCIA"])                 # the province on its own line

    def test_italy(self):
        r = dict(spec("lettera-it")["recipient"], building="Scala B, int. 4", street="Via G. Mazzini, 12")
        got = letter.postal_lines(r, "IT")
        # The building above the street; the street and the locality in capitals with no punctuation.
        self.assertEqual(got[2:], ["Scala B, int. 4", "VIA G MAZZINI 12", "40100 BOLOGNA BO"])
        abroad = letter.postal_lines({"name": "Beispiel Druck GmbH", "street": "Musterweg 10", "postcode": "78464",
                                      "city": "Konstanz", "country": "DE"}, "IT")
        self.assertEqual(abroad[1:], ["MUSTERWEG 10", "78464 KONSTANZ", "GERMANIA"])

    def test_poland(self):
        got = letter.postal_lines(dict(spec("pismo-pl")["recipient"], postcode="30000"), "PL")
        self.assertEqual(got[-1], "30-000 KRAKÓW")                             # XX-XXX, the locality in capitals
        abroad = letter.postal_lines({"name": "Beispiel Druck GmbH", "street": "Musterweg 10", "postcode": "78464",
                                      "city": "Konstanz", "country": "DE"}, "PL")
        self.assertEqual(abroad[-2:], ["78464 KONSTANZ", "NIEMCY"])            # the country's name in Polish

    def test_an_address_out_of_order_fails(self):
        def swap(path):
            with zipfile.ZipFile(path) as z:
                xml = z.read("word/document.xml").decode("utf-8")
            self.assertIn("46000 VALENCIA", xml)
        b = Built(spec("carta-es"))
        swap(b.path)
        wrong = changed("carta-es")
        wrong["recipient"]["province"] = "Alicante"                            # the file says VALENCIA
        (b.dir / "spec.json").write_text(json.dumps(wrong, ensure_ascii=False))
        ok, why = b.check("LETTER-ADDRESS")
        self.assertFalse(ok)
        self.assertIn("ALICANTE", why)


class Languages(unittest.TestCase):
    def test_the_sender_picks_the_language(self):
        for cc, loc in (("ES", "es-ES"), ("IT", "it-IT"), ("PL", "pl-PL")):
            self.assertEqual(letter.letter_locale({"sender": {"country": cc}, "recipient": {}})[0], loc)
        self.assertEqual(letter.letter_locale({"language": "es", "sender": {"country": "GB"}, "recipient": {}})[0], "es-ES")

    def test_dates(self):
        self.assertEqual(letter.long_date("2026-10-09", "es-ES"), "9 de octubre de 2026")
        self.assertEqual(letter.long_date("2026-01-01", "it-IT"), "1 gennaio 2026")
        self.assertEqual(letter.long_date("2026-10-09", "pl-PL"), "9 października 2026")
        self.assertEqual(letter.date("2026-10-09", "es-ES"), "9/10/2026")
        self.assertEqual(letter.date("2026-10-09", "it-IT"), "09/10/2026")
        self.assertEqual(letter.date("2026-10-09", "pl-PL"), "9.10.2026")
        for loc, text in (("es-ES", "9 de octubre de 2026"), ("it-IT", "9 ottobre 2026"), ("pl-PL", "9 października 2026")):
            self.assertTrue(locale_floor.long_date_rx(loc).search(text), loc)

    def test_the_date_line_names_the_place(self):
        self.assertEqual(wl.WindowLetter(spec("carta-es")).date_line(), "Madrid, 9 de octubre de 2026")
        self.assertEqual(wl.WindowLetter(spec("lettera-it")).date_line(), "Milano, 9 ottobre 2026")
        self.assertEqual(wl.WindowLetter(spec("pismo-pl")).date_line(), "Warszawa, 9 października 2026")

    def test_labels(self):
        self.assertEqual(wl.WindowLetter(spec("carta-es")).subject_text(), "Asunto: Presupuesto para su catálogo de primavera de 2027")
        self.assertTrue(wl.WindowLetter(spec("lettera-it")).subject_text().startswith("Oggetto: "))
        self.assertTrue(wl.WindowLetter(spec("pismo-pl")).subject_text().startswith("Dotyczy: "))
        english = changed("carta-es", language="en-GB", salutation="Dear Ms Ferrer,")
        b = Built(spec("carta-es"))
        (b.dir / "spec.json").write_text(json.dumps(english, ensure_ascii=False))
        ok, why = b.check("LETTER-LANGUAGE")                                   # a Spanish page against an English spec
        self.assertFalse(ok)
        self.assertIn("Fecha", why)


class Form(unittest.TestCase):
    def test_closings_the_builder_writes(self):
        self.assertEqual(wl.WindowLetter(spec("carta-es")).spec["closing"], "Atentamente,")
        self.assertEqual(wl.WindowLetter(spec("lettera-it")).spec["closing"], "Distinti saluti")
        self.assertEqual(wl.WindowLetter(spec("pismo-pl")).spec["closing"], "Z poważaniem")

    def test_spanish_takes_a_colon_after_the_salutation(self):
        ok, why = Built(changed("carta-es", salutation="Estimada señora Ferrer,")).check("LETTER-FORM")
        self.assertFalse(ok)
        self.assertIn("colon", why)
        ok, why = Built(changed("carta-es", closing="Atentamente")).check("LETTER-FORM")
        self.assertFalse(ok)
        self.assertIn("comma", why)
        # A closing whose sentence the signature completes takes no mark.
        self.assertTrue(Built(changed("carta-es", closing="Le saluda atentamente")).check("LETTER-FORM")[0])
        self.assertTrue(Built(changed("carta-es", closing="Un cordial saludo.")).check("LETTER-FORM")[0])

    def test_polish_takes_a_comma_and_no_mark_after_the_closing(self):
        self.assertTrue(Built(spec("pismo-pl")).check("LETTER-FORM")[0])
        self.assertTrue(Built(changed("pismo-pl", salutation="Szanowna Pani!")).check("LETTER-FORM")[0])
        ok, why = Built(changed("pismo-pl", closing="Z poważaniem,")).check("LETTER-FORM")
        self.assertFalse(ok)
        self.assertIn("no punctuation", why)
        ok, why = Built(changed("pismo-pl", salutation="Szanowna Pani")).check("LETTER-FORM")
        self.assertFalse(ok)

    def test_italian_has_no_scripted_rule(self):
        ok, why = Built(spec("lettera-it")).check("LETTER-FORM")
        self.assertIsNone(ok)
        self.assertIn("no Italian authority", why)


class Company(unittest.TestCase):
    def test_spain_asks_for_the_register_entry(self):
        s = spec("carta-es")["sender"]
        self.assertEqual(letter.company_missing(s), [])
        self.assertEqual(letter.company_missing(dict(s, register="", register_number="")), ["register", "register_number"])
        # Art. 24: a company that names its capital names the subscribed and the paid-up capital.
        self.assertTrue(any("paid_up_capital" in m for m in letter.company_missing(dict(s, share_capital="60.000 euros"))))
        lines = letter.company_lines(dict(s, share_capital="60.000 euros", paid_up_capital="15.000 euros"), "es-ES")
        self.assertIn("Registro Mercantil de Madrid, tomo 00000, folio 000, hoja M-000000", lines)
        self.assertIn("Capital suscrito: 60.000 euros", lines)
        self.assertIn("Capital desembolsado: 15.000 euros", lines)

    def test_italy_asks_for_the_paid_up_capital_of_an_srl(self):
        s = spec("lettera-it")["sender"]
        self.assertEqual(letter.company_missing(s), [])
        self.assertTrue(any("share_capital" in m for m in letter.company_missing(dict(s, share_capital=""))))
        snc = dict(s, name="Esempio Stampa S.n.c.", share_capital="")
        self.assertEqual(letter.company_missing(snc), [])                       # the capital rule names S.p.A., S.a.p.a., S.r.l.
        lines = letter.company_lines(dict(s, sole_shareholder=True, directed_by="Esempio Holding S.p.A."), "it-IT")
        self.assertIn("Registro delle Imprese di Milano Monza Brianza Lodi n. 00000000000", lines)
        self.assertIn("Società con unico socio", lines)
        self.assertIn("Società soggetta all'attività di direzione e coordinamento di Esempio Holding S.p.A.", lines)

    def test_poland_asks_for_court_krs_nip_and_capital(self):
        s = spec("pismo-pl")["sender"]
        self.assertEqual(letter.company_missing(s), [])
        bare = {"name": "Przykład Druk S.A.", "country": "PL", "registered_office": "Warszawa"}
        missing = letter.company_missing(bare)
        for key in ("register", "register_number", "vat_id (NIP)", "share_capital"):
            self.assertIn(key, missing)
        self.assertTrue(any("paid_up_capital" in m for m in missing))           # art. 374 § 1 pkt 4, an S.A. only
        self.assertFalse(any("paid_up_capital" in m for m in letter.company_missing(dict(s, share_capital=""))))
        lines = letter.company_lines(s, "pl-PL")
        self.assertEqual(lines[:2], ["Siedziba: Warszawa", "KRS 0000000000"])
        self.assertIn("Kapitał zakładowy: 50 000,00 zł", lines)

    def test_the_check_finds_the_particulars_on_the_page(self):
        for name in W9:
            ok, why = Built(spec(name)).check("LETTER-COMPANY")
            self.assertTrue(ok, "%s: %s" % (name, why))
        # A page built without the capital, read against a spec that states it.
        s = spec("lettera-it")
        thin = copy.deepcopy(s)
        del thin["sender"]["share_capital"]
        b = Built(thin)
        (b.dir / "spec.json").write_text(json.dumps(s, ensure_ascii=False))
        ok, why = b.check("LETTER-COMPANY")
        self.assertFalse(ok)
        self.assertIn("50.000,00 euro i.v.", why)
        sole = copy.deepcopy(s)
        sole["sender"]["sole_shareholder"] = True
        (b.dir / "spec.json").write_text(json.dumps(dict(sole, sender=dict(sole["sender"])), ensure_ascii=False))
        self.assertIn("unico socio", b.check("LETTER-COMPANY")[1])

    def test_legal_forms(self):
        for name, form in (("Ejemplo Imprenta S.L.", "S.L."), ("Ejemplo Imprenta S.L.U.", "S.L.U."), ("Ejemplo Imprenta S.A.U.", "S.A.U."),
                           ("Esempio Stampa S.r.l.", "S.r.l."), ("Esempio Stampa S.p.A.", "S.p.A."), ("Esempio Stampa S.a.p.a.", "S.a.p.a."),
                           ("Przykład Druk sp. z o.o.", "sp. z o.o."), ("Przykład Druk S.A.", "S.A.")):
            self.assertEqual(letter.legal_form({"name": name}), form, name)


class DinLetter(unittest.TestCase):
    """The DIN 5008 letter (a German or Swedish sender) on the rule every letter and invoice follows."""

    def test_the_address_is_written_as_the_post_office_reads_it(self):
        s = spec("letter")                                                       # Gothenburg to Edinburgh
        got = lcr.Letter(s).address()
        self.assertEqual(got, letter.postal_lines(s["recipient"], "SE"))
        self.assertEqual(got[-3:], ["EDINBURGH", "EH6 6NP", "UNITED KINGDOM"])
        home = dict(s, recipient={"name": "Exempel Rådgivning AB", "street": "Storgatan 1", "postcode": "411 01",
                                  "city": "Göteborg", "country": "SE"})
        self.assertEqual(lcr.Letter(home).address()[-1], "411 01 Göteborg")      # no country line at home

    def test_the_information_block_ends_on_the_texts_right_edge(self):
        self.assertEqual(letter.info_width(), 65)
        self.assertIn(".info{width:65mm}", letter.info_css())
        b = Built(spec("letter"), din=True)
        with zipfile.ZipFile(b.path) as z:
            xml = z.read("word/document.xml").decode("utf-8")
        import re
        grid = [int(x) for x in re.findall(r'<w:gridCol w:w="(\d+)"/>', xml.split("</w:tblGrid>")[0])]
        self.assertAlmostEqual(sum(grid) * 25.4 / 1440, 165, delta=1)            # 25 mm to 190 mm, no further
        for rule in ("LETTER-DIN5008", "LETTER-PARTS", "LETTER-DATE", "LETTER-LANGUAGE", "LETTER-COMPANY"):
            self.assertIsNot(b.check(rule)[0], False, rule)

    @unittest.skipUnless(can_print(), "no Chromium to print with")
    def test_a_pdf_block_stays_inside_the_margin(self):
        s = spec("letter")
        b = Built(s, "pdf", din=True)
        ok, why = b.check("LETTER-DIN5008")
        self.assertTrue(ok, why)
        self.assertEqual(lc.info_edge_problems(b.path), [])
        words = lc.einvoice_page.page_words(b.path)
        block = [w for w in words if w[0] >= 124 and 48 <= w[1] <= 90]
        self.assertTrue(block)
        self.assertLessEqual(max(w[2] for w in block), 190.5)
        # Six address lines stay inside the 27.3 mm address zone (62.7 to 90 mm down).
        town = [w for w in words if w[4] == "KINGDOM"]
        self.assertTrue(town)
        self.assertLessEqual(town[0][3], 90.5)
        # A page whose block runs past the margin fails, with the measure.
        wide = (b.dir / "letter.html").read_text().replace(letter.info_css(), ".info{width:75mm}.info dd{white-space:nowrap}")
        long = wide.replace("karin@exempel-tryck.example", "karin.lind.customer.manager@exempel-tryck.example")
        (b.dir / "letter.html").write_text(long)
        letter.print_pdf(b.dir / "letter.html", b.path)
        ok, why = b.check("LETTER-DIN5008")
        self.assertFalse(ok)
        self.assertIn("text's right edge", why)


if __name__ == "__main__":
    unittest.main()
