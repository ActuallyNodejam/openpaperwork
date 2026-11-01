"""Offline tests for the letters of Belgium, the Netherlands, Austria and Ireland (wave 8), the envelope
windows as the postal operators publish their zones, and the Finnish page number. Needs python-docx; the
PDF tests need Chromium (the app's printer or Playwright) and skip without it."""
import copy
import json
import re
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
import locale_floor  # noqa: E402
import window_letter as wl  # noqa: E402

RULES = ("LETTER-DIN5008", "LETTER-WINDOW", "LETTER-ADDRESS", "LETTER-PARTS", "LETTER-FORM", "LETTER-DATE",
         "LETTER-LANGUAGE", "LETTER-PAGES", "LETTER-COMPANY")
W8 = ("brief-be", "lettre-be", "brief-nl", "brief-at", "letter-ie")


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

    def __init__(self, data, kind="docx", edit=None):
        self.dir = Path(tempfile.mkdtemp())
        (self.dir / "spec.json").write_text(json.dumps(data, ensure_ascii=False))
        self.path = self.dir / ("letter." + kind)
        (wl.write_docx if kind == "docx" else wl.write_pdf)(data, self.path)
        if edit:
            edit(self.path)

    def check(self, rule):
        return lc.check(rule, self.path, {}, "first")


def rewrite(path, part, change):
    """Rewrite one part of a Word file."""
    tmp = Path(str(path) + ".tmp")
    with zipfile.ZipFile(path) as src, zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as dst:
        for item in src.infolist():
            data = src.read(item.filename)
            if item.filename == part:
                data = change(data.decode("utf-8")).encode("utf-8")
            dst.writestr(item, data)
    tmp.replace(path)


class Starters(unittest.TestCase):
    def test_every_wave_8_starter_passes_as_word(self):
        for name in W8:
            b = Built(spec(name))
            for rule in RULES:
                ok, why = b.check(rule)
                self.assertIsNot(ok, False, "%s %s: %s" % (name, rule, why))

    @unittest.skipUnless(can_print(), "no Chromium to print with")
    def test_every_wave_8_starter_passes_as_pdf(self):
        for name in W8:
            b = Built(spec(name), "pdf")
            for rule in RULES:
                ok, why = b.check(rule)
                self.assertIsNot(ok, False, "%s %s: %s" % (name, rule, why))
            self.assertTrue(b.check("LETTER-WINDOW")[0], name)


class Windows(unittest.TestCase):
    """The rectangles as the operators' zones allow them (WINDOW_SOURCES names what was read)."""

    def test_every_country_the_pack_covers_names_its_window_source(self):
        for cc in ("DE", "SE", "DK", "NO", "FI", "US", "CA", "GB", "AU", "BE", "NL", "AT", "IE"):
            status, source = letter.WINDOW_SOURCES[cc]
            self.assertIn(status, ("confirmed", "partly", "zone", "unconfirmed"))
            self.assertTrue(source)
        for cc in ("SE", "DK"):
            self.assertEqual(letter.WINDOW_SOURCES[cc][0], "unconfirmed")
            self.assertIn("not confirmed against a PostNord document", letter.WINDOW_SOURCES[cc][1])

    def test_belgium_window_is_on_the_right_and_clear_of_the_indexing_zone(self):
        x0, y0, x1, y1 = letter.window_box(letter.LAYOUTS["be"])
        self.assertGreater(x0, 105)                 # the right half of an A4 sheet
        self.assertLessEqual(x1, 229 - 15 - 4)      # 15 mm from the envelope's right edge, 4 mm inside the window
        self.assertLessEqual(y1, 114 - 30)          # above the 30 mm indexing zone of a 114 mm envelope
        self.assertGreaterEqual(y0, 40 + 4)         # under the 40 mm franking zone

    def test_uk_window_is_18_mm_from_the_bottom(self):
        wx, wy, ww, wh = letter.LAYOUTS["uk"]["window"]
        self.assertEqual((wx, ww, wh), (19, 90, 35))
        self.assertEqual(110 - (wy + wh), 18)       # Royal Mail: at least 18 mm from the bottom of a DL envelope
        self.assertNotIn("90 x 45", letter.LAYOUTS["uk"]["envelope"])

    def test_finnish_address_stays_out_of_36_to_40_mm(self):
        lay = letter.LAYOUTS["fi"]
        self.assertGreaterEqual(letter.window_box(lay)[1], 40)      # Posti's window opens 40 mm down
        self.assertLessEqual(letter.window_box(lay)[3], 66)         # the SFS 2487 field ends 66 mm down
        self.assertGreaterEqual(lay["address_at"][1], 40)

    def test_irish_text_keeps_15_mm_from_the_windows_left_edge(self):
        lay = letter.LAYOUTS["ie"]
        x0, y0, x1, y1 = letter.window_box(lay)
        self.assertEqual(x0 - lay["window"][0], 15)
        self.assertEqual(y0 - lay["window"][1], 5)
        self.assertGreaterEqual(lay["address_at"][0], x0)
        self.assertLessEqual(lay["line"], 4 + 3.6)   # An Post: 2 to 4 mm between lines of 10 pt type

    def test_austrian_address_has_the_posts_5_mm_quiet_zone(self):
        lay = letter.LAYOUTS["at"]
        self.assertEqual(letter.window_box(lay), (25, 59, 105, 90))

    def test_a_document_block_goes_beside_the_window(self):
        x, y, w = letter.info_box(letter.LAYOUTS["be"])
        self.assertLess(x + w, letter.LAYOUTS["be"]["window"][0])   # left of a right-hand window
        x, y, w = letter.info_box(letter.LAYOUTS["nl"])
        self.assertGreaterEqual(x, 125)
        self.assertGreater(w, 40)

    def test_word_puts_the_belgian_address_on_the_right(self):
        b = Built(spec("brief-be"))
        ok, why = b.check("LETTER-WINDOW")
        self.assertTrue(ok, why)
        d = lc.docx_layout(b.path)
        self.assertAlmostEqual(d["margins"]["left"] + d["lead"], 115, delta=1)

        def narrow(xml):                            # the empty 90 mm column made 20 mm: the address slides left
            return re.sub(r'w:w="51\d\d"', 'w:w="1134"', xml)
        b = Built(spec("brief-be"), edit=lambda p: rewrite(p, "word/document.xml", narrow))
        ok, why = b.check("LETTER-WINDOW")
        self.assertFalse(ok)
        self.assertIn("across", why)

    @unittest.skipUnless(can_print(), "no Chromium to print with")
    def test_a_din_letter_address_is_outside_the_belgian_window(self):
        b = Built(spec("brief-be"), "pdf")
        self.assertTrue(b.check("LETTER-WINDOW")[0])
        words = lc.einvoice_page.page_words(b.path)
        first = [w for w in words if w[4] == "Hageland"]
        self.assertTrue(first and first[0][0] >= 114)


class Addresses(unittest.TestCase):
    def test_belgium(self):
        r = {"name": "Hageland Fietsatelier BV", "street": "Diestsestraat 88 bus 2", "postcode": "3000", "city": "Leuven", "country": "BE"}
        self.assertEqual(letter.postal_lines(r, "BE"), ["Hageland Fietsatelier BV", "Diestsestraat 88 bus 2", "3000 LEUVEN"])
        self.assertEqual(letter.postal_lines(r, "NL")[-1], "BELGIUM")

    def test_netherlands(self):
        r = {"name": "Voorbeeld Distributie B.V.", "street": "Kanaalweg 41", "postcode": "9601aa", "city": "Hoogezand", "country": "NL"}
        self.assertEqual(letter.postal_lines(r, "NL")[-1], "9601 AA  HOOGEZAND")       # two spaces, capitals
        abroad = {"name": "X GmbH", "street": "Hauptstraße 1", "postcode": "80331", "city": "München", "country": "DE"}
        self.assertEqual(letter.postal_lines(abroad, "NL")[-2:], ["80331  MÜNCHEN", "GERMANY"])

    def test_austria(self):
        r = {"name": "Gemeinde Seefelden", "street": "Dorfplatz 1/2", "postcode": "6100", "city": "Seefelden", "country": "AT"}
        self.assertEqual(letter.postal_lines(r, "AT")[-1], "6100 Seefelden")
        abroad = {"name": "X GmbH", "street": "Hauptstraße 1", "postcode": "80331", "city": "München", "country": "DE"}
        self.assertEqual(letter.postal_lines(abroad, "AT")[-2:], ["80331 MÜNCHEN", "DEUTSCHLAND"])

    def test_ireland(self):
        r = {"name": "Example Freight Limited", "street": "12 Bridge Street", "city": "Westport", "county": "Co. Mayo",
             "postcode": "f28 x2y4", "country": "IE"}
        self.assertEqual(letter.postal_lines(r, "IE"),
                         ["Example Freight Limited", "12 Bridge Street", "Westport", "Co Mayo", "F28 X2Y4"])
        dublin = {"name": "X Ltd", "street": "1 Sample Street", "city": "Dublin 2", "postcode": "D02 AB12", "country": "IE"}
        self.assertEqual(letter.postal_lines(dublin, "IE")[-2:], ["Dublin 2", "D02 AB12"])
        self.assertEqual(letter.postal_lines(dublin, "GB")[-1], "IRELAND")

    def test_an_address_out_of_order_fails(self):
        def swap(path):
            rewrite(path, "word/document.xml", lambda x: x.replace("9601 AA  HOOGEZAND", "Hoogezand 9601AA"))
        ok, why = Built(spec("brief-nl"), edit=swap).check("LETTER-ADDRESS")
        self.assertFalse(ok)
        self.assertIn("9601 AA HOOGEZAND", why)


class Languages(unittest.TestCase):
    def test_the_sender_picks_the_variant(self):
        pick = lambda **s: letter.letter_locale(s)[0]
        self.assertEqual(pick(language="nl", sender={"country": "BE"}, recipient={}), "nl-BE")
        self.assertEqual(pick(language="nl", sender={"country": "NL"}, recipient={}), "nl-NL")
        self.assertEqual(pick(language="fr", sender={"country": "BE"}, recipient={}), "fr-BE")
        self.assertEqual(pick(language="fr", sender={"country": "CA"}, recipient={}), "fr-CA")
        self.assertEqual(pick(language="de", sender={"country": "AT"}, recipient={}), "de-AT")
        self.assertEqual(pick(language="en", sender={"country": "IE"}, recipient={}), "en-IE")
        self.assertEqual(pick(sender={"country": "AT"}, recipient={}), "de-AT")

    def test_a_belgian_postcode_picks_the_language_when_none_is_named(self):
        self.assertEqual(letter.belgian_language("5000"), "fr-BE")       # Namur
        self.assertEqual(letter.belgian_language("3000"), "nl-BE")       # Leuven
        self.assertEqual(letter.belgian_language("9000"), "nl-BE")       # Gent
        self.assertEqual(letter.belgian_language("1000"), "nl-BE")       # Brussels: name the language
        loc, why = letter.letter_locale({"sender": {"country": "BE", "postcode": "4000"}, "recipient": {}})
        self.assertEqual(loc, "fr-BE")
        self.assertIn("name the language", why)

    def test_dates(self):
        self.assertEqual(letter.long_date("2026-10-09", "nl-NL"), "9 oktober 2026")
        self.assertEqual(letter.long_date("2026-03-09", "nl-BE"), "9 maart 2026")
        self.assertEqual(letter.long_date("2026-10-09", "fr-BE"), "9 octobre 2026")
        self.assertEqual(letter.long_date("2026-01-09", "de-AT"), "9. Jänner 2026")
        self.assertEqual(letter.long_date("2026-01-09", "de-DE"), "9. Januar 2026")
        self.assertEqual(letter.long_date("2026-10-09", "en-IE"), "9 October 2026")
        self.assertTrue(locale_floor.long_date_rx("de-AT").search("Wien, 9. Jänner 2026"))
        self.assertTrue(locale_floor.long_date_rx("nl-NL").search("9 oktober 2026"))

    def test_the_date_line(self):
        self.assertEqual(wl.WindowLetter(spec("lettre-be")).date_line(), "Namur, le 9 octobre 2026")
        self.assertEqual(wl.WindowLetter(spec("brief-at")).date_line(), "9. Oktober 2026")
        ok, why = Built(changed("brief-at", date="2026-01-09")).check("LETTER-DATE")
        self.assertTrue(ok)
        self.assertIn("9. Jänner 2026", why)

    def test_labels(self):
        self.assertEqual(wl.WindowLetter(spec("brief-nl")).subject_text(), "Betreft: offerte voor ledverlichting in 24 kantoren")
        self.assertEqual(wl.WindowLetter(spec("brief-be")).subject_text(), "Offerte voor uw voorjaarscatalogus 2027")
        self.assertTrue(wl.WindowLetter(spec("lettre-be")).subject_text().startswith("Objet : "))
        self.assertEqual(wl.WindowLetter(spec("brief-nl")).enclosures_label(), "Bijlage")       # one enclosure
        self.assertEqual(wl.WindowLetter(spec("brief-at")).enclosures_label(), "Beilagen")
        self.assertEqual(wl.WindowLetter(spec("lettre-be")).enclosures_label(), "Annexe")

    def test_a_french_company_line_sets_a_no_break_space_before_the_colon(self):
        lines = letter.company_lines(spec("lettre-be")["sender"], "fr-BE")
        # The same no-break space the letter's "Objet\u00a0:" has, so the colon never starts a line.
        self.assertEqual(lines[0], "Siège\u00a0: Rue des Brasseurs 21, 5000 Namur")
        self.assertTrue(wl.WindowLetter(spec("lettre-be")).subject_text().startswith("Objet\u00a0: "))
        self.assertIn("RPM Liège, division Namur", lines)
        self.assertEqual(letter.company_lines(spec("brief-be")["sender"], "nl-BE")[0], "Zetel: Vaartstraat 14, 3000 Leuven")


class Form(unittest.TestCase):
    def test_closings_the_builder_writes(self):
        self.assertEqual(wl.WindowLetter(spec("brief-nl")).spec["closing"], "Met vriendelijke groet,")
        self.assertEqual(wl.WindowLetter(spec("brief-be")).spec["closing"], "Met vriendelijke groeten,")
        bare = changed("brief-be", salutation="Geachte mevrouw Jacobs")
        self.assertEqual(wl.WindowLetter(bare).spec["closing"], "Met vriendelijke groeten")
        self.assertEqual(wl.WindowLetter(spec("brief-at")).spec["closing"], "Mit freundlichen Grüßen")
        self.assertEqual(wl.WindowLetter(spec("letter-ie")).spec["closing"], "Yours sincerely")
        unnamed = changed("letter-ie", salutation="Dear Sir or Madam")
        self.assertEqual(wl.WindowLetter(unnamed).spec["closing"], "Yours faithfully")
        self.assertEqual(wl.WindowLetter(spec("lettre-be")).spec["closing"], "Veuillez agréer, Madame, mes salutations distinguées.")

    def test_the_netherlands_writes_a_comma_after_salutation_and_closing(self):
        self.assertTrue(Built(spec("brief-nl")).check("LETTER-FORM")[0])
        ok, why = Built(changed("brief-nl", salutation="Geachte heer Jansen")).check("LETTER-FORM")
        self.assertFalse(ok)
        self.assertIn("salutation ends with a comma", why)
        ok, why = Built(changed("brief-nl", closing="Met vriendelijke groet")).check("LETTER-FORM")
        self.assertFalse(ok)
        self.assertIn("closing ends with a comma", why)

    def test_belgium_pairs_the_commas(self):
        self.assertTrue(Built(spec("brief-be")).check("LETTER-FORM")[0])
        self.assertTrue(Built(changed("brief-be", salutation="Geachte mevrouw Jacobs")).check("LETTER-FORM")[0])
        ok, why = Built(changed("brief-be", closing="Met vriendelijke groeten")).check("LETTER-FORM")
        self.assertFalse(ok)
        self.assertIn("the closing takes one too", why)

    def test_german_closing_carries_no_mark(self):
        self.assertTrue(Built(spec("brief-at")).check("LETTER-FORM")[0])
        self.assertTrue(Built(changed("brief-at", salutation="Sehr geehrte Frau Mag. Huber!")).check("LETTER-FORM")[0])
        ok, why = Built(changed("brief-at", closing="Mit freundlichen Grüßen,")).check("LETTER-FORM")
        self.assertFalse(ok)
        self.assertIn("no punctuation mark", why)
        ok, why = Built(changed("brief-at", salutation="Sehr geehrte Frau Mag. Huber")).check("LETTER-FORM")
        self.assertFalse(ok)

    def test_ireland_follows_sincerely_and_faithfully(self):
        ok, why = Built(changed("letter-ie", salutation="Dear Sir or Madam", closing="Yours sincerely")).check("LETTER-FORM")
        self.assertFalse(ok)
        self.assertIn("Yours faithfully", why)

    def test_belgian_french_keeps_the_french_letter(self):
        ok, why = Built(changed("lettre-be", closing="Cordialement")).check("LETTER-FORM")
        self.assertFalse(ok)
        self.assertIn("repeats the salutation", why)

    def test_a_registered_office_that_wraps_in_the_footer_is_still_found(self):
        office = "Unit 4, Ballymount Business Park, Dublin 24"
        wrapped = "Registered office: Unit 4, Ballymount Business Park, sales@liffey.example Dublin 24 Company number 654321"
        self.assertTrue(lc.on_page(office, wrapped))
        self.assertFalse(lc.on_page(office, "Registered office: Unit 4, Ballymount Business Park, Cork"))
        self.assertFalse(lc.on_page("Dublin 24", "Dublin road 24"))          # two words must stand together

    def test_company_details_of_a_belgian_and_an_irish_company(self):
        self.assertTrue(Built(spec("brief-be")).check("LETTER-COMPANY")[0])
        self.assertTrue(Built(spec("letter-ie")).check("LETTER-COMPANY")[0])
        no_court = copy.deepcopy(spec("brief-be"))
        no_court["sender"]["register"] = "Leuven"
        self.assertIn("register (RPR or RPM and the court of the seat)", letter.company_missing(no_court["sender"]))
        no_directors = copy.deepcopy(spec("letter-ie"))
        del no_directors["sender"]["managing_directors"]
        self.assertTrue(any("managing_directors" in m for m in letter.company_missing(no_directors["sender"])))


class FinnishPages(unittest.TestCase):
    """SFS 2487 as Kielitoimiston ohjepankki describes it: the page count after the page number, 4 (7)."""

    def test_word_head_carries_the_page_number_and_count(self):
        b = Built(spec("letter-fi"))
        ok, why = b.check("LETTER-PAGES")
        self.assertTrue(ok, why)

        def strip(path):
            for part in [n for n in zipfile.ZipFile(path).namelist() if n.startswith("word/header")]:
                rewrite(path, part, lambda x: x.replace('w:instr="NUMPAGES"', 'w:instr="DATE"'))
        ok, why = Built(spec("letter-fi"), edit=strip).check("LETTER-PAGES")
        self.assertFalse(ok)
        self.assertIn("1 (2)", why)

    def test_only_the_finnish_page_is_numbered_this_way(self):
        self.assertIsNone(Built(spec("brief-nl")).check("LETTER-PAGES")[0])

    @unittest.skipUnless(can_print(), "no Chromium to print with")
    def test_a_two_page_pdf_numbers_both_pages(self):
        long = changed("letter-fi", body=spec("letter-fi")["body"] * 7)
        b = Built(long, "pdf")
        self.assertEqual(wl.page_count(b.path), 2)
        ok, why = b.check("LETTER-PAGES")
        self.assertTrue(ok, why)
        self.assertIn("1 (2) to 2 (2)", why)
        self.assertTrue(b.check("LETTER-WINDOW")[0])

    @unittest.skipUnless(can_print(), "no Chromium to print with")
    def test_a_long_din_5008_letter_keeps_clear_of_the_footer_too(self):
        """The DIN 5008 sheet (skills/_shared/letter.py sheet_html: German and Swedish letters, trade
        documents, invoices) breaks over pages the way the window letters do."""
        import letter_create as lcr
        base = spec("letter")                                        # a Swedish sender: DIN 5008 Form B
        long = dict(base, body=base["body"] * 7)
        folder = Path(tempfile.mkdtemp())
        out = folder / "letter.pdf"
        lcr.write_pdf(long, out)
        self.assertGreaterEqual(wl.page_count(out), 2)
        foot = 297 - letter.PAGE_FOOT + 1
        first = [w for w in lc.einvoice_page.page_words(out) if w[4] in ("Thank", "From", "If")]
        self.assertTrue(first)
        self.assertLessEqual(max(w[3] for w in first), foot)        # page 1 ends above the footer's room
        import subprocess
        raw = subprocess.run(["pdftotext", "-bbox", "-f", "2", "-l", "2", str(out), "-"], capture_output=True, text=True).stdout
        tops = [float(y) * 25.4 / 72 for y in re.findall(r'<word xMin="[\d.]+" yMin="([\d.]+)"', raw)]
        self.assertTrue(tops)
        self.assertGreaterEqual(min(tops), letter.PAGE_TOP - 1)     # page 2 starts under an empty head
        self.assertIn('<div class="end">', (folder / "letter.html").read_text())   # closing and signature stay together

    @unittest.skipUnless(can_print(), "no Chromium to print with")
    def test_a_long_letter_keeps_clear_of_the_footer_on_every_page(self):
        long = changed("brief-nl", body=spec("brief-nl")["body"] * 6)
        b = Built(long, "pdf")
        self.assertGreaterEqual(wl.page_count(b.path), 2)
        words = lc.einvoice_page.page_words(b.path)                 # page 1
        body = [w for w in words if w[4] in ("Hartelijk", "Deze", "De")]
        self.assertTrue(body)
        self.assertLessEqual(max(w[3] for w in body), 297 - wl.PAGE_FOOT + 1)


if __name__ == "__main__":
    unittest.main()
