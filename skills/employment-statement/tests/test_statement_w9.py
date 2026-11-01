"""Offline tests for wave 9 of the employment statement: Spain (Real Decreto 723/2026), Italy (D.Lgs. 152/1997
art. 1) and Poland (Kodeks pracy art. 29). Every starter builds and passes its pack check, and each rule catches
the gap it is written for. Needs python-docx."""
import copy
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
CHECKS = HERE.parent / "_checks"
sys.path.insert(0, str(HERE / "scripts"))
sys.path.insert(0, str(CHECKS))
import employment_check as ec  # noqa: E402
import locale_floor  # noqa: E402
import packcheck  # noqa: E402
import statement_create as sc  # noqa: E402

ES, IT, PL = "informacion-es", "informazioni-it", "informacja-pl"


def spec(name):
    return json.loads((HERE / "templates" / (name + ".spec.json")).read_text())


class Built:
    """A statement built from a spec in its own folder, with the spec beside it as a chat folder holds both."""

    def __init__(self, data, edit=None):
        self.dir = Path(tempfile.mkdtemp())
        (self.dir / "spec.json").write_text(json.dumps(data, ensure_ascii=False))
        self.path = self.dir / "statement.docx"
        sc.write_docx(data, self.path)
        if edit:
            from docx import Document
            doc = Document(self.path)
            edit(doc)
            doc.save(self.path)

    def check(self, rule):
        return ec.check(rule, self.path, {}, "first")

    def text(self):
        return " ".join(t for _, t in ec.paragraphs(self.path))


def drop(*needles):
    """Remove every paragraph that contains one of the needles."""
    def edit(doc):
        for p in list(doc.paragraphs):
            if any(n in p.text for n in needles):
                p._element.getparent().remove(p._element)
    return edit


def append(text):
    def edit(doc):
        doc.add_paragraph(text)
    return edit


def with_(data, **changes):
    """A deep copy of a spec with keys changed; a dotted key changes one field of a nested object."""
    out = copy.deepcopy(data)
    for key, value in changes.items():
        if "__" in key:
            a, b = key.split("__", 1)
            out[a] = dict(out.get(a) or {}, **{b: value})
        else:
            out[key] = value
    return out


class Starters(unittest.TestCase):
    def test_each_starter_passes_every_rule_and_the_pack_check(self):
        for name, locale in ((ES, "es-ES"), (IT, "it-IT"), (PL, "pl-PL")):
            with self.subTest(template=name):
                b = Built(spec(name))
                self.assertEqual(sc.locale_of(spec(name)), locale)
                for rule in ec.RULES:
                    ok, why = b.check(rule)
                    self.assertIsNot(ok, False, "%s %s: %s" % (name, rule, why))
                self.assertIs(b.check("EMPLOY-LANG")[0], True)
                self.assertIs(locale_floor.check("LOCALE-PAPER", b.path, {"locale": locale}, "first")[0], True)
                run = subprocess.run([sys.executable, str(CHECKS / "packcheck.py"), "employment-statement", str(b.path)],
                                     capture_output=True, text=True, cwd=b.dir)
                self.assertEqual(run.returncode, 0, run.stdout)
                self.assertIn("pack check clean", run.stdout)

    def test_the_pack_check_runs_every_rule_the_module_defines(self):
        # A merge once dropped three of them from the list; the pack check then never ran them.
        listed = packcheck.SKILL_RULES["employment-statement"]
        self.assertEqual([r for r in ec.RULES if r not in listed], [])

    def test_money_dates_and_units_in_each_language(self):
        self.assertIn("Salario base: 1.850 € brutos al mes.", Built(spec(ES)).text())
        self.assertIn("La relación laboral comienza el 2/11/2026.", Built(spec(ES)).text())
        self.assertIn("Retribuzione iniziale: 1.850 € lordi al mese.", Built(spec(IT)).text())
        self.assertIn("Wynagrodzenie zasadnicze: 8 500 zł brutto miesięcznie.", Built(spec(PL)).text().replace(" ", " "))
        self.assertIn("Dzień rozpoczęcia pracy: 2.11.2026.", Built(spec(PL)).text())
        # Polish counts in three forms: 1 miesiąc, 3 miesiące, 6 miesięcy, 22 miesiące, 12 miesięcy
        forms = sc.PL["unit"]["month"]
        self.assertEqual([sc.plural(n, forms) for n in (1, 3, 6, 22, 12)],
                         ["miesiąc", "miesiące", "miesięcy", "miesiące", "miesięcy"])
        self.assertEqual(sc.plural(2, sc.ES["unit"]["month"]), "meses")

    def test_a_statement_read_without_its_spec_still_knows_its_law(self):
        for name, law in ((ES, "es"), (IT, "it"), (PL, "pl")):
            b = Built(spec(name))
            (b.dir / "spec.json").unlink()
            ok, why = b.check("EMPLOY-ITEMS")
            self.assertIs(ok, True, why)
            self.assertIn(ec.LAW_NAME[law], why)


class Spain(unittest.TestCase):
    """Real Decreto 723/2026, de 9 de septiembre, in force 5 October 2026 (it repealed Real Decreto 1659/1998)."""

    def test_the_information_is_due_before_the_employment_begins(self):
        ok, why = Built(with_(spec(ES), given="2026-11-03")).check("EMPLOY-DATES")       # the day after the start
        self.assertIs(ok, False, why)
        self.assertIn("art. 7.1", why)
        self.assertIn("before the employment begins", why)
        self.assertIs(Built(with_(spec(ES), given="2026-11-02")).check("EMPLOY-DATES")[0], True)

    def test_the_items_of_article_3_2(self):
        s = spec(ES)
        for needles, cite in ((("Grupo profesional:",), "art. 3.2 e)"),
                              (("Sistemas algorítmicos", "No procede: la empresa no utiliza"), "art. 3.2 k)"),
                              (("Modificación de las condiciones", "Por acuerdo escrito o conforme a los artículos 39"), "art. 3.2 q)")):
            ok, why = Built(s, drop(*needles)).check("EMPLOY-ITEMS")
            self.assertIs(ok, False, why)
            self.assertIn(cite, why)
        # g) 1.º: the daily, the weekly and the annual working time
        ok, why = Built(with_(s, hours__standard="40 horas semanales")).check("EMPLOY-ITEMS")
        self.assertIs(ok, False, why)
        self.assertIn("g) 1.º", why)
        self.assertIn("annual", why)
        # l): the harassment protocol whatever the size, so never "not applicable"
        ok, why = Built(with_(s, equality="La empresa no cuenta con plan de igualdad")).check("EMPLOY-ITEMS")
        self.assertIs(ok, False, why)
        self.assertIn("art. 3.2 l)", why)
        ok, why = Built(s, drop("protocolo frente al acoso sexual")).check("EMPLOY-ITEMS")
        self.assertIs(ok, False, why)
        # p): the managing body or the mutual
        ok, why = Built(with_(s, social_security="La empresa cotiza por la persona trabajadora")).check("EMPLOY-ITEMS")
        self.assertIs(ok, False, why)
        self.assertIn("art. 3.2 p)", why)
        with self.assertRaises(SystemExit):          # the builder asks for what the law always asks for
            Built({k: v for k, v in s.items() if k != "equality"})
        with self.assertRaises(SystemExit):
            Built(with_(s, job={"title": "Oficial de preimpresión"}))

    def test_a_temporary_contract_names_its_cause(self):
        s = with_(spec(ES), term={"type": "fixed", "end": "2027-10-31",
                                  "basis": "incremento ocasional e imprevisible de pedidos de la campaña de otoño"})
        self.assertIs(Built(s).check("EMPLOY-ITEMS")[0], True, Built(s).check("EMPLOY-ITEMS")[1])
        with self.assertRaises(SystemExit):
            Built(with_(spec(ES), term={"type": "fixed", "end": "2027-10-31"}))
        ok, why = Built(s, drop("Causa de la contratación temporal")).check("EMPLOY-ITEMS")
        self.assertIs(ok, False, why)
        self.assertIn("art. 3.2 d)", why)

    def test_what_article_3_3_lets_a_statement_give_by_reference(self):
        s = spec(ES)
        hours = "Conforme al artículo 34 del Estatuto de los Trabajadores y al artículo 20 del convenio colectivo aplicable"
        b = Built(with_(s, hours=hours))
        self.assertIs(b.check("EMPLOY-ITEMS")[0], True, b.check("EMPLOY-ITEMS")[1])
        self.assertIs(b.check("EMPLOY-REFERENCE")[0], True)
        ok, why = Built(with_(s, pay="Según las tablas salariales del convenio colectivo aplicable, grupo profesional 3")
                        ).check("EMPLOY-PAY")
        self.assertIs(ok, True, why)
        self.assertIn("art. 3.3", why)
        # a pointer that names no law and no agreement is no reference
        self.assertIs(Built(with_(s, pay="Según lo hablado en la entrevista")).check("EMPLOY-PAY")[0], False)
        # the job, the workplace and the agreement itself are always stated
        for change in ({"job": "Véase el contrato de trabajo"}, {"collective": "Véase el tablón de anuncios"}):
            data = with_(s, **change)
            if "job" in change:
                data["job"] = {"title": change["job"], "group": "grupo profesional 3"}
            ok, why = Built(data).check("EMPLOY-REFERENCE")
            self.assertIs(ok, False, why)
            self.assertIn("art. 3.3", why)

    def test_probation_follows_article_14(self):
        s = spec(ES)
        ok, why = Built(with_(s, probation={"months": 7})).check("EMPLOY-PROBATION")
        self.assertIs(ok, False, why)
        self.assertIn("art. 14.1", why)
        agreed = {"months": 7, "conditions": "duración fijada por el artículo 12 del convenio colectivo aplicable"}
        self.assertIs(Built(with_(s, probation=agreed)).check("EMPLOY-PROBATION")[0], True)
        short = with_(s, term={"type": "fixed", "end": "2027-02-28", "basis": "sustitución de una persona con reserva de puesto"})
        ok, why = Built(short).check("EMPLOY-PROBATION")                      # two months in a four-month contract
        self.assertIs(ok, False, why)
        self.assertIn("one month", why)
        self.assertIs(Built(with_(short, probation={"months": 1})).check("EMPLOY-PROBATION")[0], True)

    def test_probation_without_an_agreement_is_held_to_article_14(self):
        s = spec(ES)
        ok, why = Built(with_(s, probation={"months": 3, "conditions": "ambas partes realizan las experiencias"})).check(
            "EMPLOY-PROBATION")
        self.assertIs(ok, False, why)
        self.assertIn("2 months", why)
        small = {"months": 3, "conditions": "la empresa tiene menos de veinticinco trabajadores"}
        self.assertIs(Built(with_(s, probation=small)).check("EMPLOY-PROBATION")[0], True)
        self.assertIs(Built(with_(s, probation=dict(small, months=4))).check("EMPLOY-PROBATION")[0], False)
        titled = {"months": 6, "conditions": "la persona trabajadora es técnico titulado"}
        self.assertIs(Built(with_(s, probation=titled)).check("EMPLOY-PROBATION")[0], True)
        loose = {"months": 6, "conditions": "según el convenio"}           # "convenio" alone names no agreement
        self.assertIs(Built(with_(s, probation=loose)).check("EMPLOY-PROBATION")[0], False)

    def test_the_collective_agreement_is_identified(self):
        s = spec(ES)
        self.assertIs(Built(s).check("EMPLOY-AGREEMENT")[0], True)
        for key, word in (("code", "code"), ("published", "bulletin"), ("validity", "validity")):
            col = {k: v for k, v in s["collective"].items() if k != key}
            ok, why = Built(with_(s, collective=col)).check("EMPLOY-AGREEMENT")
            self.assertIs(ok, False, why)
            self.assertIn(word, why)
            self.assertIn("art. 3.2 o)", why)
        self.assertIs(Built(with_(s, collective="Convenio colectivo de artes gráficas")).check("EMPLOY-AGREEMENT")[0], False)
        self.assertIsNone(Built(with_(s, collective=None)).check("EMPLOY-AGREEMENT")[0])     # none applies: said so

    def test_work_abroad_over_four_weeks(self):
        s = spec(ES)
        abroad = {"countries": ["Portugal"], "from": "2027-03-01", "to": "2027-04-25", "currency": "EUR",
                  "benefits": "dietas de 45 € por día y alojamiento a cargo de la empresa",
                  "repatriation": "la empresa paga el viaje de vuelta al terminar el trabajo"}
        self.assertIs(Built(with_(s, abroad=abroad)).check("EMPLOY-ABROAD")[0], True,
                      Built(with_(s, abroad=abroad)).check("EMPLOY-ABROAD")[1])
        ok, why = Built(with_(s, abroad=dict(abroad, to="2027-03-21"))).check("EMPLOY-ABROAD")
        self.assertIsNone(ok)
        self.assertIn("art. 4.3", why)
        ok, why = Built(with_(s, abroad=abroad), drop("Repatriación:")).check("EMPLOY-ABROAD")
        self.assertIs(ok, False, why)
        self.assertIn("RD 723/2026 art. 4", why)


class Italy(unittest.TestCase):
    """Decreto legislativo 26 maggio 1997, n. 152, art. 1 as in force from 28 June 2026."""

    def test_seven_days_for_what_the_contract_did_not_give(self):
        ok, why = Built(with_(spec(IT), given="2026-11-12")).check("EMPLOY-DATES")      # ten days after the start
        self.assertIs(ok, False, why)
        self.assertIn("art. 1 c. 3", why)
        self.assertIs(Built(with_(spec(IT), given="2026-11-09")).check("EMPLOY-DATES")[0], True)

    def test_the_bodies_that_receive_the_contributions(self):
        ok, why = Built(with_(spec(IT), social_security="Il datore di lavoro versa i contributi dovuti")).check("EMPLOY-ITEMS")
        self.assertIs(ok, False, why)
        self.assertIn("art. 1 c. 1 r)", why)
        pointer = "Si applica la legge 8 agosto 1995, n. 335, per la previdenza obbligatoria"
        self.assertIs(Built(with_(spec(IT), social_security=pointer)).check("EMPLOY-ITEMS")[0], True)

    def test_what_comma_5_bis_lets_a_statement_give_by_reference(self):
        s = spec(IT)
        self.assertIs(Built(s).check("EMPLOY-REFERENCE")[0], True)          # leave and notice point to the law already
        ok, why = Built(with_(s, pay="Secondo le tabelle retributive del contratto collettivo applicato, quarto livello")
                        ).check("EMPLOY-PAY")
        self.assertIs(ok, True, why)
        self.assertIn("c. 5-bis", why)
        hours = "Si applica l'articolo 3 del decreto legislativo 8 aprile 2003, n. 66, e il contratto collettivo applicato"
        self.assertIs(Built(with_(s, hours=hours)).check("EMPLOY-ITEMS")[0], True)
        ok, why = Built(with_(s, place="Vedi il contratto individuale di lavoro")).check("EMPLOY-REFERENCE")
        self.assertIs(ok, False, why)
        self.assertIn("c. 5-bis", why)
        # the pay itself still needs its period and its method when it is written out
        self.assertIs(Built(s, drop("Modalità di pagamento:")).check("EMPLOY-PAY")[0], False)

    def test_probation_follows_article_7_of_the_2022_decree(self):
        s = spec(IT)
        ok, why = Built(with_(s, probation={"months": 7})).check("EMPLOY-PROBATION")
        self.assertIs(ok, False, why)
        self.assertIn("art. 7 c. 1", why)
        four = with_(s, term={"type": "fixed", "end": "2027-02-28"})          # under six months
        ok, why = Built(with_(four, probation={"months": 1})).check("EMPLOY-PROBATION")
        self.assertIs(ok, False, why)
        self.assertIn("fifteen", why)
        self.assertIs(Built(with_(four, probation={"weeks": 2})).check("EMPLOY-PROBATION")[0], True)
        nine = with_(s, term={"type": "fixed", "end": "2027-07-31"})          # over six, under twelve months
        ok, why = Built(with_(nine, probation={"months": 2})).check("EMPLOY-PROBATION")
        self.assertIs(ok, False, why)
        self.assertIn("thirty", why)
        self.assertIs(Built(with_(nine, probation={"months": 1})).check("EMPLOY-PROBATION")[0], True)

    def test_the_collective_agreement_names_its_parties_and_its_cnel_code(self):
        s = spec(IT)
        self.assertIs(Built(s).check("EMPLOY-AGREEMENT")[0], True)
        no_code = {k: v for k, v in s["collective"].items() if k != "code"}
        ok, why = Built(with_(s, collective=no_code)).check("EMPLOY-AGREEMENT")
        self.assertIs(ok, False, why)
        self.assertIn("q-bis)", why)
        # q-bis) is for private employers only
        public = Built(with_(s, collective=no_code), append("Il datore di lavoro è una pubblica amministrazione."))
        self.assertIs(public.check("EMPLOY-AGREEMENT")[0], True, public.check("EMPLOY-AGREEMENT")[1])
        no_parties = {k: v for k, v in s["collective"].items() if k != "parties"}
        ok, why = Built(with_(s, collective=no_parties)).check("EMPLOY-AGREEMENT")
        self.assertIs(ok, False, why)
        self.assertIn("art. 1 c. 1 q)", why)
        self.assertTrue(any("q-bis" in w for w in sc.warnings_for(with_(s, collective=no_code), "it")))
        self.assertEqual(sc.warnings_for(s, "it"), [])

    def test_a_posting_is_informed_whatever_its_length_a_mission_over_four_weeks(self):
        s = spec(IT)
        abroad = {"countries": ["Francia"], "from": "2027-03-01", "to": "2027-03-14", "currency": "EUR",
                  "benefits": "indennità di trasferta di 50 € al giorno",
                  "repatriation": "il viaggio di rientro è a carico del datore di lavoro"}
        ok, why = Built(with_(s, abroad=abroad)).check("EMPLOY-ABROAD")                   # a mission of two weeks
        self.assertIsNone(ok)
        self.assertIn("art. 2 c. 2", why)
        posted = dict(abroad, posted={"host_pay": "il salario minimo francese del settore",
                                      "website": "https://travail-emploi.gouv.fr"})
        ok, why = Built(with_(s, abroad=posted)).check("EMPLOY-ABROAD")                   # a posting of two weeks
        self.assertIs(ok, True, why)


class Poland(unittest.TestCase):
    """Kodeks pracy art. 29: the contract's own terms (§ 1) and the information (§ 3), art. 25 for the trial period."""

    def test_the_contracts_own_terms_are_stated(self):
        s = spec(PL)
        self.assertIs(Built(s).check("EMPLOY-PL-CONTRACT")[0], True)
        for needles, word in ((("Umowa o pracę zawarta dnia",), "date the contract was concluded"),
                              (("Wymiar czasu pracy:",), "wymiar czasu pracy"),
                              (("Umowa o pracę na czas nieokreślony",), "type of contract")):
            ok, why = Built(s, drop(*needles)).check("EMPLOY-PL-CONTRACT")
            self.assertIs(ok, False, why)
            self.assertIn(word, why)
            self.assertIn("art. 29 § 1", why)
        ok, why = Built(with_(s, job="Zgodnie z art. 22 Kodeksu pracy")).check("EMPLOY-PL-CONTRACT")
        self.assertIs(ok, False, why)
        self.assertIn("pointer", why)
        for key in ("contract_date",):
            with self.assertRaises(SystemExit):
                Built({k: v for k, v in s.items() if k != key})
        with self.assertRaises(SystemExit):
            Built(with_(s, hours={k: v for k, v in s["hours"].items() if k != "basis"}))
        self.assertIsNone(Built(spec(ES)).check("EMPLOY-PL-CONTRACT")[0])

    def test_seven_days_from_admission_to_work(self):
        ok, why = Built(with_(spec(PL), given="2026-11-12")).check("EMPLOY-DATES")
        self.assertIs(ok, False, why)
        self.assertIn("art. 29 § 3 pkt 1", why)
        self.assertIs(Built(with_(spec(PL), given="2026-11-09")).check("EMPLOY-DATES")[0], True)

    def test_work_regulations_or_what_the_law_asks_without_them(self):
        s = spec(PL)
        ok, why = Built(with_(s, rules="Pracodawca nie ustalił regulaminu pracy")).check("EMPLOY-ITEMS")
        self.assertIs(ok, False, why)
        self.assertIn("pkt 1 m)", why)
        self.assertIn("night time", why)
        full = ("Pracodawca nie ustalił regulaminu pracy. Wynagrodzenie wypłaca się raz w miesiącu, do 10. dnia następnego "
                "miesiąca, przelewem. Pora nocna obejmuje godziny od 22:00 do 6:00. Przybycie i obecność w pracy "
                "pracownik potwierdza podpisem na liście obecności; nieobecność usprawiedliwia się u przełożonego "
                "najpóźniej drugiego dnia")
        self.assertIs(Built(with_(s, rules=full)).check("EMPLOY-ITEMS")[0], True, Built(with_(s, rules=full)).check("EMPLOY-ITEMS")[1])
        ok, why = Built(with_(s, rules="Zasady organizacji pracy ustala przełożony")).check("EMPLOY-ITEMS")
        self.assertIs(ok, False, why)
        with self.assertRaises(SystemExit):
            Built({k: v for k, v in s.items() if k != "rules"})

    def test_working_time_gives_the_norm_the_breaks_and_the_rest_or_the_provisions(self):
        s = spec(PL)
        ok, why = Built(s, drop("Przerwy w pracy:", "Odpoczynek dobowy")).check("EMPLOY-ITEMS")
        self.assertIs(ok, False, why)
        self.assertIn("pkt 1 a) to d)", why)
        pointers = dict(s["hours"], norm="zgodnie z art. 129 Kodeksu pracy", breaks="zgodnie z art. 134 Kodeksu pracy",
                        rest_days="zgodnie z art. 132 i 133 Kodeksu pracy")
        self.assertIs(Built(with_(s, hours=pointers)).check("EMPLOY-ITEMS")[0], True)

    def test_pay_is_a_term_of_the_contract_and_the_trial_period_has_three_months(self):
        s = spec(PL)
        # when and how it is paid is for the work regulations; the amount and its components are for the contract
        self.assertIs(Built(s, drop("Wypłata wynagrodzenia:", "Sposób wypłaty:")).check("EMPLOY-PAY")[0], True)
        ok, why = Built(with_(s, pay="Zgodnie z regulaminem wynagradzania obowiązującym u pracodawcy")).check("EMPLOY-REFERENCE")
        self.assertIs(ok, False, why)
        self.assertIn("art. 29 § 3(1)", why)
        self.assertIs(Built(s).check("EMPLOY-REFERENCE")[0], True)          # leave and notice point to the code
        ok, why = Built(with_(s, probation={"months": 4})).check("EMPLOY-PROBATION")
        self.assertIs(ok, False, why)
        self.assertIn("art. 25 § 2", why)
        three = Built(with_(s, probation={"months": 3}))
        self.assertIs(three.check("EMPLOY-PROBATION")[0], True, three.check("EMPLOY-PROBATION")[1])
        self.assertIn("Okres próbny: 3 miesiące od dnia rozpoczęcia pracy.", three.text())
        self.assertIn("Umowa o pracę na okres próbny", three.text())

    def test_work_abroad_over_four_weeks(self):
        abroad = {"countries": ["Niemcy"], "from": "2027-03-01", "to": "2027-03-14", "currency": "EUR",
                  "benefits": "diety zgodnie z przepisami o podróżach służbowych",
                  "repatriation": "pracodawca zapewnia powrót do kraju i pokrywa jego koszt"}
        ok, why = Built(with_(spec(PL), abroad=abroad)).check("EMPLOY-ABROAD")
        self.assertIsNone(ok)
        self.assertIn("art. 29(1) § 2", why)
        long = Built(with_(spec(PL), abroad=dict(abroad, to="2027-04-25")))
        self.assertIs(long.check("EMPLOY-ABROAD")[0], True, long.check("EMPLOY-ABROAD")[1])
        self.assertIn("(8 tygodni)", long.text())


if __name__ == "__main__":
    unittest.main()
