"""Offline tests for the minutes of Spain, Italy and Poland (wave 9): every starter builds and passes its
check, each statute rule catches the gap it is written for and names its article, and where the statute
sets nothing or hands the record to a notary the rule says so and passes nothing. Needs python-docx."""
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
W9 = ("acta-consejo-es", "acta-junta-general-es", "verbale-assemblea-it", "verbale-consiglio-it",
      "protokol-zgromadzenia-wspolnikow-pl", "protokol-zarzadu-pl")


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


def drop(text):
    """An edit that empties every paragraph holding the text, in the body and in the tables."""
    def edit(doc):
        paras = list(doc.paragraphs) + [p for t in doc.tables for row in t.rows for c in row.cells for p in c.paragraphs]
        for p in paras:
            if text in p.text:
                for r in p.runs:
                    r.text = ""
    return edit


class Starters(unittest.TestCase):
    def test_every_wave_9_starter_passes_its_check(self):
        for name in W9:
            b = Built(spec(name))
            for rule in RULES:
                ok, why = b.check(rule)
                self.assertIsNot(ok, False, "%s %s: %s" % (name, rule, why))
            self.assertTrue(b.check("MINUTES-SIGNED")[0], name)

    def test_the_starters_use_placeholder_companies(self):
        for name in W9:
            s = spec(name)
            self.assertTrue(s["body"].split()[0] in ("Ejemplo", "Esempio", "Przykład"), name)
            for row in s.get("shareholders") or []:
                self.assertNotEqual(row["name"], s["body"])

    def test_titles_dates_and_times(self):
        self.assertEqual(mk.lines(spec("acta-consejo-es"))[0][1], "Acta de la reunión del consejo de administración de Ejemplo Imprenta S.A.")
        self.assertEqual(mk.lines(spec("acta-junta-general-es"))[0][1], "Acta de la junta general ordinaria de Ejemplo Imprenta S.L.")
        self.assertEqual(mk.lines(spec("verbale-assemblea-it"))[0][1], "Verbale dell'assemblea ordinaria di Esempio Stampa S.p.A.")
        self.assertEqual(mk.lines(spec("verbale-consiglio-it"))[0][1], "Verbale della riunione del consiglio di amministrazione di Esempio Stampa S.p.A.")
        # The legal form keeps to one line of the title: no-break spaces inside sp. z o.o.
        self.assertEqual(mk.lines(spec("protokol-zgromadzenia-wspolnikow-pl"))[0][1],
                         "Protokół ze zwyczajnego zgromadzenia wspólników spółki Przykład Druk sp.\u00a0z\u00a0o.o.")
        self.assertEqual(mk.lines(spec("protokol-zarzadu-pl"))[0][1], "Protokół z posiedzenia zarządu spółki Przykład Druk sp.\u00a0z\u00a0o.o.")
        self.assertTrue(Built(spec("protokol-zarzadu-pl")).check("MINUTES-HEAD")[0])
        supervisory = changed("protokol-zarzadu-pl", organ="supervisory")
        self.assertIn("z posiedzenia rady nadzorczej", mk.lines(supervisory)[0][1])
        self.assertEqual(mk.clock("9:05", "es-ES"), "9:05")                       # CLDR es H:mm
        self.assertEqual(mk.clock("9:05", "it-IT"), "09:05")
        self.assertEqual(mk.clock("9:05", "pl-PL"), "09:05")
        self.assertIn("14 de octubre de 2026", Built(spec("acta-consejo-es")).text())
        self.assertIn("14 października 2026", Built(spec("protokol-zarzadu-pl")).text())

    def test_the_law_is_the_companys_country(self):
        self.assertEqual(mk.country_of({"language": "es", "meeting": "board"}), "ES")
        self.assertEqual(mk.country_of({"language": "it", "meeting": "general"}), "IT")
        self.assertEqual(mk.country_of({"language": "pl", "meeting": "board"}), "PL")
        self.assertEqual(mk.country_of({"language": "es", "meeting": "regular"}), "")   # a club: no statute


class Spain(unittest.TestCase):
    def test_board_is_signed_by_the_secretary_with_the_chairs_visto_bueno(self):
        b = Built(spec("acta-consejo-es"))
        ok, why = b.check("MINUTES-SIGNED")
        self.assertTrue(ok, why)
        self.assertIn("LSC art. 250", why)
        self.assertIn("V.º B.º Presidencia", b.text())
        own = changed("acta-consejo-es", titles={"chair": "Presidenta", "secretary": "Secretario"})
        self.assertIn("V.º B.º Presidenta", Built(own).text())
        ok, why = Built(spec("acta-consejo-es"), edit=drop("V.º B.º")).check("MINUTES-SIGNED")
        self.assertFalse(ok)
        self.assertIn("Elena Robles", why)

    def test_board_states_what_the_register_rules_ask(self):
        ok, why = Built(spec("acta-consejo-es")).check("MINUTES-STATUTE")
        self.assertTrue(ok, why)
        self.assertIn("RRM art. 97", why)
        ok, why = Built(changed("acta-consejo-es", convened=None)).check("MINUTES-STATUTE")
        self.assertFalse(ok)
        self.assertIn("97.1 2.ª", why)
        ok, why = Built(changed("acta-consejo-es", place=None)).check("MINUTES-STATUTE")
        self.assertFalse(ok)
        self.assertIn("97.1 1.ª", why)
        bare = changed("acta-consejo-es")
        bare["items"][0]["decisions"] = ["aprobar el presupuesto de 2027 tal como se ha presentado"]
        ok, why = Built(bare).check("MINUTES-STATUTE")
        self.assertFalse(ok)
        self.assertIn("97.1 7.ª", why)

    def test_board_counts_those_represented_in_a_unanimous_vote(self):
        text = Built(spec("acta-consejo-es")).text()
        self.assertIn("Acuerdo adoptado por unanimidad, con 4 votos a favor.", text)   # three present, one represented
        self.assertIn("Votos a favor: 3; en contra: 1; abstenciones: 0.", text)
        self.assertIn("Pablo Ortega (por Elena Robles)", text)
        self.assertIn("Nuria Campos solicita que conste en acta su oposición", text)

    def test_the_approval_of_the_acta_is_recorded(self):
        b = Built(spec("acta-consejo-es"))
        self.assertIn("El acta se aprueba por unanimidad al término de la reunión.", b.text())
        later = changed("acta-junta-general-es", checkers=["Javier Soler", "Nuria Campos"],
                        minutes_approved={"date": "2026-06-25", "how": "por la presidencia y dos socios interventores"})
        b = Built(later)
        self.assertIn("El acta se aprueba el 25 de junio de 2026, por la presidencia y dos socios interventores.", b.text())
        self.assertTrue(b.check("MINUTES-STATUTE")[0])
        self.assertIn("Nuria Campos", b.check("MINUTES-SIGNED")[1] + b.text())
        ok, why = Built(spec("acta-consejo-es"), edit=drop("El acta se aprueba")).check("MINUTES-STATUTE")
        self.assertFalse(ok)
        self.assertIn("art. 99", why)

    def test_a_limited_companys_acta_holds_the_list_of_those_attending(self):
        b = Built(spec("acta-junta-general-es"))
        ok, why = b.check("MINUTES-STATUTE")
        self.assertTrue(ok, why)
        self.assertIn("LSC arts. 192 and 202", why)
        self.assertIn("Asisten en persona 2 socios, con el 70 % del capital social, y por representación 1, con el 30 %.", b.text())
        attached = changed("acta-junta-general-es", shareholders=None, shareholders_attached=True)
        ok, why = Built(attached).check("MINUTES-STATUTE")
        self.assertFalse(ok)                                   # an S.L.'s list goes inside the acta
        self.assertIn("LSC art. 192.3", why)
        sa = changed("acta-junta-general-es", body="Ejemplo Imprenta S.A.", shareholders=None, shareholders_attached=True)
        sa["items"] = [dict(i, decisions=[dict(d, votes={"for": 3000, "against": 0, "abstained": 0}) for d in i["decisions"]]) for i in sa["items"]]
        ok, why = Built(sa).check("MINUTES-STATUTE")
        self.assertTrue(ok, why)                               # an S.A. may attach it (RRM art. 98)
        ok, why = Built(changed("acta-junta-general-es", total_shares=None)).check("MINUTES-STATUTE")
        self.assertFalse(ok)
        self.assertIn("97.1 4.ª", why)

    def test_a_junta_universal_needs_no_call_and_every_member_signs(self):
        universal = changed("acta-junta-general-es", universal=True, convened=None)
        b = Built(universal)
        self.assertTrue(b.check("MINUTES-STATUTE")[0], b.check("MINUTES-STATUTE")[1])
        ok, why = b.check("MINUTES-SIGNED")
        self.assertTrue(ok, why)
        self.assertIn("Ejemplo Inversiones S.L.", why)
        self.assertIn("Junta universal", b.text())

    def test_a_notary_at_the_junta_takes_the_record(self):
        notary = changed("acta-junta-general-es", notary="Notario de Madrid (nombre en el requerimiento)")
        ok, why = Built(notary).check("MINUTES-STATUTE")
        self.assertIsNone(ok)
        self.assertIn("LSC art. 203", why)
        self.assertNotIn("El acta se aprueba", Built(notary).text())


class Italy(unittest.TestCase):
    def test_an_spa_assembly_follows_article_2375(self):
        b = Built(spec("verbale-assemblea-it"))
        ok, why = b.check("MINUTES-STATUTE")
        self.assertTrue(ok, why)
        self.assertIn("2375", why)
        ok, why = b.check("MINUTES-SIGNED")
        self.assertTrue(ok, why)
        self.assertIn("Codice civile art. 2375", why)
        text = b.text()
        self.assertIn("Modalità di voto: voto palese per alzata di mano.", text)
        self.assertIn("La delibera è approvata all'unanimità, con 100.000 voti favorevoli.", text)
        self.assertIn("Esito della votazione: 90.000 voti favorevoli, 0 contrari, 10.000 astenuti.", text)
        self.assertIn("Astenuti: Giorgio Sala.", text)

    def test_what_2375_asks_and_the_spec_lacks(self):
        ok, why = Built(changed("verbale-assemblea-it", voting=None)).check("MINUTES-STATUTE")
        self.assertFalse(ok)
        self.assertIn("how the votes were cast", why)
        nobody = changed("verbale-assemblea-it")
        del nobody["items"][1]["decisions"][0]["abstained"]
        ok, why = Built(nobody).check("MINUTES-STATUTE")
        self.assertFalse(ok)
        self.assertIn("who abstained", why)
        ok, why = Built(changed("verbale-assemblea-it", quorum=None)).check("MINUTES-STATUTE")
        self.assertFalse(ok)
        self.assertIn("art. 2371", why)
        ok, why = Built(changed("verbale-assemblea-it", shareholders=None)).check("MINUTES-STATUTE")
        self.assertFalse(ok)
        self.assertIn("capital each stands for", why)
        attached = changed("verbale-assemblea-it", shareholders=None, shareholders_attached=True)
        attached["items"] = [dict(i, decisions=[dict(d, votes={"for": 100000, "against": 0, "abstained": 0}, unanimous=None) for d in i["decisions"]])
                             for i in attached["items"]]
        for i in attached["items"]:
            for d in i["decisions"]:
                d.pop("abstained", None)
        b = Built(attached)
        self.assertTrue(b.check("MINUTES-STATUTE")[0], b.check("MINUTES-STATUTE")[1])
        self.assertIn("è allegato al verbale", b.text())

    def test_an_extraordinary_assembly_is_a_notarys(self):
        extra = changed("verbale-assemblea-it", meeting="extraordinary general")
        ok, why = Built(extra).check("MINUTES-STATUTE")
        self.assertIsNone(ok)
        self.assertIn("drawn up by a notary", why)
        self.assertEqual(mk.notarial(extra)[0], "Codice civile art. 2375")

    def test_the_code_sets_nothing_for_a_board(self):
        b = Built(spec("verbale-consiglio-it"))
        ok, why = b.check("MINUTES-STATUTE")
        self.assertIsNone(ok)
        self.assertIn("sets no contents for a board's verbale", why)
        self.assertTrue(b.check("MINUTES-SIGNED")[0])           # the secretary's line, as any minutes
        self.assertIn("Esito della votazione: 2 voti favorevoli, 1 contrari, 0 astenuti.", b.text())

    def test_an_srl_assembly_follows_2479_bis(self):
        srl = changed("verbale-assemblea-it", body="Esempio Stampa S.r.l.", voting=None)
        b = Built(srl)
        ok, why = b.check("MINUTES-STATUTE")
        self.assertTrue(ok, why)
        self.assertIn("2479-bis", why)
        ok, why = Built(changed("verbale-assemblea-it", body="Esempio Stampa S.r.l.", quorum=None)).check("MINUTES-STATUTE")
        self.assertFalse(ok)
        self.assertIn("2479-bis", why)


class Poland(unittest.TestCase):
    def test_a_shareholders_meeting_follows_article_248(self):
        b = Built(spec("protokol-zgromadzenia-wspolnikow-pl"))
        ok, why = b.check("MINUTES-STATUTE")
        self.assertTrue(ok, why)
        self.assertIn("KSH art. 248", why)
        ok, why = b.check("MINUTES-SIGNED")
        self.assertTrue(ok, why)
        self.assertIn("KSH art. 248 § 1", why)
        text = b.text()
        self.assertIn("Przewodniczący stwierdza prawidłowość zwołania zgromadzenia wspólników i jego zdolność do powzięcia uchwał.", text)
        self.assertIn("Uchwałę powzięto jednogłośnie, liczba głosów za: 100.", text)
        self.assertIn("Głosy za: 90, przeciw: 10, wstrzymujące się: 0.", text)
        self.assertIn("Katarzyna Lis zgłasza sprzeciw", text)

    def test_what_248_asks_and_the_spec_lacks(self):
        ok, why = Built(changed("protokol-zgromadzenia-wspolnikow-pl", quorum=None)).check("MINUTES-STATUTE")
        self.assertFalse(ok)
        self.assertIn("properly called", why)
        ok, why = Built(changed("protokol-zgromadzenia-wspolnikow-pl", shareholders=None)).check("MINUTES-STATUTE")
        self.assertFalse(ok)
        self.assertIn("attendance list", why)
        attached = changed("protokol-zgromadzenia-wspolnikow-pl", shareholders=None, shareholders_attached=True)
        attached["items"][0]["decisions"] = [{"text": "zatwierdzić sprawozdanie finansowe spółki za rok obrotowy 2025",
                                              "votes": {"for": 100, "against": 0, "abstained": 0}}]
        b = Built(attached)
        self.assertTrue(b.check("MINUTES-STATUTE")[0], b.check("MINUTES-STATUTE")[1])
        self.assertIn("stanowi załącznik do protokołu", b.text())
        plain = changed("protokol-zgromadzenia-wspolnikow-pl")
        plain["items"][1]["decisions"] = ["przeznaczyć zysk netto za rok 2025 w całości na kapitał zapasowy"]
        ok, why = Built(plain).check("MINUTES-STATUTE")
        self.assertFalse(ok)
        self.assertIn("votes on each resolution", why)

    def test_a_management_board_follows_article_208_1(self):
        b = Built(spec("protokol-zarzadu-pl"))
        ok, why = b.check("MINUTES-STATUTE")
        self.assertTrue(ok, why)
        self.assertIn("KSH art. 208(1)", why)
        text = b.text()
        self.assertIn("Porządek obrad: 1. Budżet na rok 2027; 2. Zakup cyfrowej maszyny drukującej.", text)
        self.assertIn("Marek Zając zgłasza zdanie odrębne", text)
        self.assertIn("Głosy za: 2, przeciw: 1, wstrzymujące się: 0.", text)
        ok, why = b.check("MINUTES-SIGNED")
        self.assertTrue(ok, why)
        self.assertIn("Agnieszka Sowa", why)
        ok, why = Built(changed("protokol-zarzadu-pl", present=None)).check("MINUTES-STATUTE")
        self.assertFalse(ok)
        self.assertIn("members present", why)
        ok, why = Built(spec("protokol-zarzadu-pl"), edit=drop("Porządek obrad")).check("MINUTES-STATUTE")
        self.assertFalse(ok)
        self.assertIn("porządek obrad", why)

    def test_the_article_follows_the_form_and_the_organ(self):
        sa = changed("protokol-zarzadu-pl", body="Przykład Druk S.A.")
        self.assertEqual(mk.pl_law(sa, "board"), "KSH art. 376")
        self.assertEqual(mk.pl_law(dict(sa, organ="supervisory"), "board"), "KSH art. 391 § 2 and art. 376")
        self.assertEqual(mk.pl_law(changed("protokol-zarzadu-pl", organ="supervisory"), "board"), "KSH art. 222 § 2 and art. 208(1)")
        self.assertIn("Obecni członkowie:", Built(changed("protokol-zarzadu-pl", organ="supervisory")).text())

    def test_a_joint_stock_companys_general_meeting_is_a_notarys(self):
        sa = changed("protokol-zgromadzenia-wspolnikow-pl", body="Przykład Druk S.A.")
        b = Built(sa)
        ok, why = b.check("MINUTES-STATUTE")
        self.assertIsNone(ok)
        self.assertIn("KSH art. 421", why)
        self.assertIn("z walnego zgromadzenia", mk.lines(dict(sa, meeting="general"))[0][1])


class Language(unittest.TestCase):
    def test_every_label_is_in_the_minutes_language(self):
        for name in W9:
            ok, why = Built(spec(name)).check("MINUTES-LANGUAGE")
            self.assertTrue(ok, "%s: %s" % (name, why))

    def test_a_foreign_label_is_caught(self):
        def relabel(doc):
            for t in doc.tables:
                for row in t.rows:
                    for c in row.cells:
                        for p in c.paragraphs:
                            if p.text.strip() == "Lugar:":
                                p.runs[0].text = "Luogo:"
        ok, why = Built(spec("acta-consejo-es"), edit=relabel).check("MINUTES-LANGUAGE")
        self.assertFalse(ok)
        self.assertIn("Luogo", why)

    def test_motions_read_in_each_language(self):
        for name, mover, text in (("acta-consejo-es", "Javier Soler", "aplazar la decisión"),
                                  ("verbale-consiglio-it", "Luca Marchetti", "di rinviare la decisione"),
                                  ("protokol-zarzadu-pl", "Marek Zając", "aby odroczyć decyzję")):
            s = spec(name)
            s["items"][1]["motions"] = [{"text": text, "mover": mover, "result": "lost", "votes": {"for": 1, "against": 2}}]
            ok, why = Built(s).check("MINUTES-MOTIONS")
            self.assertTrue(ok, "%s: %s" % (name, why))


if __name__ == "__main__":
    unittest.main()
