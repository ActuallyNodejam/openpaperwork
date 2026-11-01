"""Offline tests for the minutes of Belgium, the Netherlands, Austria and Ireland (wave 8): every starter
builds and passes its check, and each statute rule catches the gap it is written for and names its article.
Also the Danish rules, which the amending acts since LBK nr 331 of 2025 left as they were. Needs python-docx."""
import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
CHECKS = HERE.parent / "_checks"
sys.path.insert(0, str(HERE / "scripts"))
sys.path.insert(0, str(CHECKS))
import minutes_check as mc  # noqa: E402
import minutes_create as mk  # noqa: E402

RULES = ("MINUTES-HEAD", "MINUTES-OFFICERS", "MINUTES-MOTIONS", "MINUTES-TIMES", "MINUTES-SIGNED",
         "MINUTES-STATUTE", "MINUTES-LANGUAGE")
W8 = ("notulen-raad-van-bestuur-be", "notulen-algemene-vergadering-be", "pv-conseil-administration-be",
      "pv-assemblee-generale-be", "notulen-bestuursvergadering-nl", "notulen-algemene-vergadering-nl",
      "niederschrift-aufsichtsrat-at", "niederschrift-generalversammlung-at", "board-minutes-ie", "agm-minutes-ie")


def spec(name):
    return json.loads((HERE / "templates" / (name + ".spec.json")).read_text())


class Built:
    """Minutes built from a spec in a folder of their own, the spec beside them as a chat folder holds both."""

    def __init__(self, data, edit=None, beside=None):
        self.dir = Path(tempfile.mkdtemp())
        (self.dir / "spec.json").write_text(json.dumps(beside or data, ensure_ascii=False))
        self.path = self.dir / "minutes.docx"
        mk.write_docx(data, self.path)
        if edit:
            from docx import Document
            doc = Document(self.path)
            edit(doc)
            doc.save(self.path)

    def check(self, rule):
        return mc.check(rule, self.path, {}, "first")

    def text(self):
        return " ".join(mc.text_of(self.path))


def changed(name, **keys):
    data = copy.deepcopy(spec(name))
    for k, v in keys.items():
        if v is None:
            data.pop(k, None)
        else:
            data[k] = v
    return data


class Starters(unittest.TestCase):
    def test_every_wave_8_starter_passes_its_check(self):
        for name in W8:
            b = Built(spec(name))
            for rule in RULES:
                ok, why = b.check(rule)
                self.assertIsNot(ok, False, "%s %s: %s" % (name, rule, why))


class Belgium(unittest.TestCase):
    def test_board_cites_the_book_of_the_company_form(self):
        ok, why = Built(spec("notulen-raad-van-bestuur-be")).check("MINUTES-SIGNED")
        self.assertTrue(ok)
        self.assertIn("WVV art. 7:95", why)                       # an NV
        bv = changed("notulen-raad-van-bestuur-be", body="Dijleboord Drukkerij BV")
        self.assertIn("WVV art. 5:75", Built(bv).check("MINUTES-SIGNED")[1])
        cv = changed("notulen-raad-van-bestuur-be", body="Dijleboord Drukkerij CV")
        self.assertIn("WVV art. 6:63", Built(cv).check("MINUTES-SIGNED")[1])
        self.assertIn("CSA art. 7:95", Built(spec("pv-conseil-administration-be")).check("MINUTES-SIGNED")[1])

    def test_an_nv_has_a_raad_van_bestuur_and_a_bv_a_bestuursorgaan(self):
        self.assertIn("raad van bestuur", Built(spec("notulen-raad-van-bestuur-be")).text())
        bv = changed("notulen-raad-van-bestuur-be", body="Dijleboord Drukkerij BV")
        self.assertIn("vergadering van het bestuursorgaan", Built(bv).text())
        self.assertIn("conseil d'administration d'Ateliers Mosans SA", Built(spec("pv-conseil-administration-be")).text())

    def test_a_declared_conflict_of_interest_is_recorded_before_the_decision(self):
        b = Built(spec("notulen-raad-van-bestuur-be"))
        text = b.text()
        self.assertLess(text.index("strijdig belang"), text.index("Besluit:"))

        def drop(doc):
            for p in doc.paragraphs:
                if "strijdig belang" in p.text:
                    p._p.getparent().remove(p._p)
        ok, why = Built(spec("notulen-raad-van-bestuur-be"), edit=drop).check("MINUTES-STATUTE")
        self.assertFalse(ok)
        self.assertIn("WVV art. 7:96", why)

    def test_a_general_meeting_keeps_an_attendance_list(self):
        none = changed("notulen-algemene-vergadering-be", shareholders=None)
        ok, why = Built(none).check("MINUTES-STATUTE")
        self.assertFalse(ok)
        self.assertIn("WVV art. 5:90", why)
        attached = changed("notulen-algemene-vergadering-be", shareholders=None, shareholders_attached=True)
        self.assertTrue(Built(attached).check("MINUTES-STATUTE")[0])

    def test_the_whole_bureau_signs_a_general_meeting(self):
        ok, why = Built(spec("notulen-algemene-vergadering-be")).check("MINUTES-SIGNED")
        self.assertTrue(ok)
        self.assertIn("WVV art. 5:93", why)
        for who in ("Sofie Jacobs", "Tom Willems", "An Goossens"):
            self.assertIn(who, why)
        # The minutes were built without the vote counter; the spec beside them still names her.
        short = changed("notulen-algemene-vergadering-be", checkers=None)
        ok, why = Built(short, beside=spec("notulen-algemene-vergadering-be")).check("MINUTES-SIGNED")
        self.assertFalse(ok)
        self.assertIn("An Goossens", why)

    def test_technical_problems_online_are_mentioned(self):
        data = changed("pv-assemblee-generale-be", method="hybrid", incidents="la liaison vidéo a été coupée de 17 h 10 à 17 h 14")
        b = Built(data)
        self.assertIn("la liaison vidéo a été coupée", b.text())
        self.assertTrue(b.check("MINUTES-STATUTE")[0])

        def drop(doc):
            for p in doc.paragraphs:
                if "liaison vidéo" in p.text:
                    p._p.getparent().remove(p._p)
        ok, why = Built(data, edit=drop).check("MINUTES-STATUTE")
        self.assertFalse(ok)
        self.assertIn("CSA art. 5:89", why)


class Netherlands(unittest.TestCase):
    def test_boek_2_sets_nothing_for_a_board(self):
        ok, why = Built(spec("notulen-bestuursvergadering-nl")).check("MINUTES-STATUTE")
        self.assertIsNone(ok)
        self.assertIn("Boek 2 BW sets no contents", why)

    def test_a_general_meeting_records_every_resolution(self):
        ok, why = Built(spec("notulen-algemene-vergadering-nl")).check("MINUTES-STATUTE")
        self.assertTrue(ok)
        self.assertIn("BW art. 2:230 lid 4", why)                 # a BV
        nv = changed("notulen-algemene-vergadering-nl", body="Waddenlicht Installaties N.V.")
        self.assertIn("BW art. 2:120 lid 4", Built(nv).check("MINUTES-STATUTE")[1])

        def drop(doc):
            for p in doc.paragraphs:
                if "dividend uitgekeerd" in p.text:
                    p._p.getparent().remove(p._p)
        ok, why = Built(spec("notulen-algemene-vergadering-nl"), edit=drop).check("MINUTES-STATUTE")
        self.assertFalse(ok)
        self.assertIn("is not recorded", why)

    def test_dutch_words_dates_and_times(self):
        text = Built(spec("notulen-algemene-vergadering-nl")).text()
        for part in ("27 mei 2026", "16:00", "Notulist", "Besluit:"):
            self.assertIn(part, text)


class Austria(unittest.TestCase):
    def test_the_supervisory_board_chair_signs(self):
        ok, why = Built(spec("niederschrift-aufsichtsrat-at")).check("MINUTES-SIGNED")
        self.assertTrue(ok)
        self.assertIn("AktG § 92 (2)", why)                       # an AG
        gmbh = changed("niederschrift-aufsichtsrat-at", body="Traunufer Logistik GmbH")
        self.assertIn("GmbHG § 30g (2)", Built(gmbh).check("MINUTES-SIGNED")[1])

    def test_a_gmbh_general_meeting_states_the_day_of_recording(self):
        b = Built(spec("niederschrift-generalversammlung-at"))
        self.assertIn("Tag der Aufnahme", b.text())
        ok, why = b.check("MINUTES-STATUTE")
        self.assertTrue(ok)
        self.assertIn("GmbHG § 40", why)
        ok, why = Built(changed("niederschrift-generalversammlung-at", recorded=None)).check("MINUTES-STATUTE")
        self.assertFalse(ok)
        self.assertIn("GmbHG § 40 (2)", why)

    def test_an_ag_general_meeting_is_the_notarys_record(self):
        ag = changed("niederschrift-generalversammlung-at", body="Traunufer Logistik AG")
        b = Built(ag)
        self.assertIn("ordentliche Hauptversammlung", b.text())
        ok, why = b.check("MINUTES-STATUTE")
        self.assertIsNone(ok)
        self.assertIn("AktG § 120", why)

    def test_january_is_jaenner(self):
        self.assertIn("15. Jänner 2026", Built(changed("niederschrift-aufsichtsrat-at", date="2026-01-15")).text())


class Ireland(unittest.TestCase):
    def test_a_board_names_the_directors_present_and_its_quorum(self):
        ok, why = Built(spec("board-minutes-ie")).check("MINUTES-STATUTE")
        self.assertTrue(ok)
        self.assertIn("Companies Act 2014 s.166", why)
        ok, why = Built(changed("board-minutes-ie", present=None)).check("MINUTES-STATUTE")
        self.assertFalse(ok)
        self.assertIn("s.166(1)(b)", why)
        ok, why = Built(changed("board-minutes-ie", quorum=None)).check("MINUTES-STATUTE")
        self.assertFalse(ok)
        self.assertIn("quorum", why)

    def test_the_chairperson_signs_as_evidence(self):
        self.assertIn("s.166(3)", Built(spec("board-minutes-ie")).check("MINUTES-SIGNED")[1])
        self.assertIn("s.199(3)", Built(spec("agm-minutes-ie")).check("MINUTES-SIGNED")[1])

    def test_a_written_resolution_is_signed_by_every_director(self):
        b = Built(changed("board-minutes-ie", method="written"))
        ok, why = b.check("MINUTES-SIGNED")
        self.assertTrue(ok)
        self.assertIn("s.161(1)", why)
        for who in ("Niamh Gallagher", "Declan Walsh", "Sinéad Kelly"):
            self.assertIn(who, why)

    def test_irish_dates(self):
        self.assertIn("20 October 2026", Built(spec("board-minutes-ie")).text())


class Denmark(unittest.TestCase):
    """selskabsloven §§ 101 and 128 as LBK nr 331 of 20 March 2025 has them; the four acts that amended the
    law since (710 and 1648 and 1765 of 2025, 729 of 2026) do not touch either section."""

    def test_every_director_present_signs_the_board_protocol(self):
        ok, why = Built(spec("bestyrelsesprotokol")).check("MINUTES-SIGNED")
        self.assertTrue(ok)
        self.assertIn("selskabsloven § 128", why)

    def test_the_dirigent_signs_the_general_meeting(self):
        ok, why = Built(spec("generalforsamling-dk")).check("MINUTES-SIGNED")
        self.assertTrue(ok)
        self.assertIn("selskabsloven § 101 (3)", why)


if __name__ == "__main__":
    unittest.main()
