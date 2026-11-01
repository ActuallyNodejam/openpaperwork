"""Offline tests for the employment statement: every template builds and passes its pack check, and each
country rule catches the gap it is written for. Needs python-docx."""
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
import statement_create as sc  # noqa: E402


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


def drop(*needles):
    """Remove every paragraph that contains one of the needles."""
    def edit(doc):
        for p in list(doc.paragraphs):
            if any(n in p.text for n in needles):
                p._element.getparent().remove(p._element)
    return edit


def append(text, style=None):
    def edit(doc):
        doc.add_paragraph(text, style=style)
    return edit


class Templates(unittest.TestCase):
    def test_every_template_passes_the_pack_check(self):
        for path in sorted((HERE / "templates").glob("*.spec.json")):
            with self.subTest(template=path.name):
                b = Built(json.loads(path.read_text()))
                r = subprocess.run([sys.executable, str(CHECKS / "packcheck.py"), "employment-statement", str(b.path)],
                                   capture_output=True, text=True)
                self.assertEqual(r.returncode, 0, r.stdout + r.stderr)

    def test_paper_and_language_follow_the_law(self):
        self.assertEqual(sc.locale_of(spec("offer-letter-ny")), "en-US")
        self.assertEqual(sc.locale_of(spec("declaration-emploi")), "fr-CA")
        self.assertEqual(sc.locale_of(spec("arbeidsavtale")), "nb-NO")
        self.assertEqual(sc.locale_of(spec("statement-au")), "en-AU")
        self.assertEqual(sc.locale_of(dict(spec("statement-uk"), language=None)), "en-GB")
        # Canadian French names the person in French (the English "Employee" had leaked in before wave 8).
        b = Built(spec("declaration-emploi"))
        self.assertTrue(any(t.startswith("Employé :") for _, t in ec.paragraphs(b.path)))


class CountryRules(unittest.TestCase):
    def test_norway_temporary_hire_and_probation(self):
        s = spec("arbeidsavtale")
        self.assertIs(Built(s).check("EMPLOY-NO-TEMP")[0], True)
        plain = dict(s, term={k: v for k, v in s["term"].items() if k != "kind"})
        self.assertIs(Built(plain, drop("Grunnlaget for den midlertidige")).check("EMPLOY-NO-TEMP")[0], False)
        long = dict(s, probation=dict(s["probation"], months=4))
        ok, why = Built(long).check("EMPLOY-PROBATION")
        self.assertIs(ok, False, why)
        self.assertIn("half", why)

    def test_norway_hours_and_breaks(self):
        s = spec("arbeidsavtale")
        self.assertIs(Built(s).check("EMPLOY-NO-HOURS")[0], True)
        self.assertIs(Built(s, drop("30 minutters pause")).check("EMPLOY-NO-HOURS")[0], False)

    def test_denmark_reference_and_deadline(self):
        s = spec("ansaettelsesbevis")
        self.assertIs(Built(s).check("EMPLOY-REFERENCE")[0], True)
        pointer = dict(s, job={"title": "Se overenskomsten"})
        self.assertIs(Built(pointer).check("EMPLOY-REFERENCE")[0], False)
        late = dict(s, given="2027-02-12")
        ok, why = Built(late).check("EMPLOY-DATES")
        self.assertIs(ok, False, why)

    def test_finland_fixed_term_ground_and_insurers(self):
        s = spec("selvitys-tyoehdoista")
        self.assertIs(Built(s, drop("Määräaikaisuuden peruste")).check("EMPLOY-FI-TEMP")[0], False)
        self.assertIs(Built(s, drop("Työtapaturma")).check("EMPLOY-ITEMS")[0], False)
        long = dict(s, probation=dict(s["probation"], months=6))
        self.assertIs(Built(long).check("EMPLOY-PROBATION")[0], False)

    def test_headings_in_one_language(self):
        s = spec("arbeidsavtale")
        self.assertIs(Built(s).check("EMPLOY-LANG")[0], True)
        self.assertIs(Built(s, append("Working hours", "Heading 2")).check("EMPLOY-LANG")[0], False)

    def test_united_states(self):
        s = spec("offer-letter-ny")
        self.assertIs(Built(s, drop("Fair Labor Standards Act")).check("EMPLOY-US-FLSA")[0], False)
        exempt = dict(s, flsa={"status": "exempt", "exemption": "administrative"})
        self.assertIs(Built(exempt).check("EMPLOY-US-FLSA")[0], False)
        self.assertIs(Built(dict(s, work_state="MT")).check("EMPLOY-US-ATWILL")[0], False)
        self.assertIs(Built(s, drop("Regular pay day")).check("EMPLOY-US-STATE")[0], False)
        self.assertIs(Built(s, append("Federal law requires this written offer letter.")).check("EMPLOY-US-WORDING")[0], False)
        ca = spec("offer-letter-ca")
        self.assertIs(Built(ca).check("EMPLOY-US-STATE")[0], True)
        self.assertIs(Built(ca, drop("Workers' compensation")).check("EMPLOY-US-STATE")[0], False)
        self.assertIsNone(Built(dict(ca, flsa={"status": "exempt", "exemption": "executive"}, pay=dict(
            ca["pay"], amount=98000, per="year"))).check("EMPLOY-US-STATE")[0])

    def test_canada_and_ontario(self):
        s = spec("employment-statement-ca")
        self.assertIs(Built(s, drop("Overtime rate")).check("EMPLOY-ITEMS")[0], False)
        self.assertIs(Built(s, drop("Income tax")).check("EMPLOY-ITEMS")[0], False)
        self.assertIs(Built(dict(s, given="2026-12-15")).check("EMPLOY-DATES")[0], False)
        on = spec("employment-information-on")
        self.assertIs(Built(dict(on, given="2026-11-05")).check("EMPLOY-DATES")[0], False)

    def test_australia(self):
        s = spec("statement-au")
        self.assertIs(Built(s, drop("Casual Employment Information Statement")).check("EMPLOY-AU-STATEMENTS")[0], False)
        fixed = dict(s, term={"type": "fixed", "end": "2029-12-31"})
        ok, why = Built(fixed).check("EMPLOY-DATES")
        self.assertIs(ok, False, why)
        self.assertIn("333E", why)

    def test_australia_renewal_follows_333e(self):
        s = dict(spec("statement-au"), start="2026-11-02")
        once = {"type": "fixed", "end": "2027-10-31", "renewal": {"times": 1, "latest_end": "2028-10-31"}}
        self.assertIs(Built(dict(s, term=once)).check("EMPLOY-DATES")[0], True)
        twice = dict(once, renewal={"times": 2, "latest_end": "2028-10-31"})
        ok, why = Built(dict(s, term=twice)).check("EMPLOY-DATES")
        self.assertIs(ok, False, why)
        self.assertIn("333E(1)(c)", why)
        long = dict(once, renewal={"times": 1, "latest_end": "2029-06-30"})
        ok, why = Built(dict(s, term=long)).check("EMPLOY-DATES")
        self.assertIs(ok, False, why)
        self.assertIn("333E(1)(b)", why)
        vague = {"type": "fixed", "end": "2027-10-31", "note": "The contract may be renewed by agreement."}
        ok, why = Built(dict(s, term=vague)).check("EMPLOY-DATES")
        self.assertIs(ok, False, why)
        self.assertIn("latest end", why)

    def test_united_kingdom_day_one_sick_pay(self):
        self.assertIn("first full day of sickness absence", spec("statement-uk")["sickness"])
        warn = sc.warnings_for(dict(spec("statement-uk"), start="2027-01-04"), "uk")
        self.assertTrue(any("trade union" in w for w in warn), warn)
        self.assertFalse(any("trade union" in w for w in sc.warnings_for(spec("statement-uk"), "uk")))

    def test_united_kingdom_disciplinary_note(self):
        s = spec("statement-uk")
        b = Built(s, drop("Disciplinary rules", "Disciplinary and dismissal", "Appeals against", "Grievances go",
                          "Further steps"))
        self.assertIs(b.check("EMPLOY-ITEMS")[0], False)

    def test_paper(self):
        s = spec("offer-letter-ny")

        def a4(doc):
            from docx.shared import Mm
            doc.sections[0].page_width, doc.sections[0].page_height = Mm(210), Mm(297)
        self.assertIs(locale_floor.check("LOCALE-PAPER", Built(s).path, {"locale": "en-US"}, "first")[0], True)
        self.assertIs(locale_floor.check("LOCALE-PAPER", Built(s, a4).path, {"locale": "en-US"}, "first")[0], False)



class Wave8(unittest.TestCase):
    """Belgium, the Netherlands, Austria and Ireland: each country's own item, deadline and probation rule."""

    def test_locale_and_region(self):
        self.assertEqual(sc.locale_of(spec("informations-be-fr")), "fr-BE")
        self.assertEqual(sc.locale_of(spec("informatie-be-nl")), "nl-BE")
        self.assertEqual(sc.locale_of(spec("opgave-nl")), "nl-NL")
        self.assertEqual(sc.locale_of(spec("dienstzettel-at")), "de-AT")
        self.assertEqual(sc.locale_of(spec("statement-ie")), "en-IE")
        self.assertEqual(sc.locale_of(dict(spec("informatie-be-nl"), language=None)), "nl-BE")    # Ghent
        self.assertEqual(sc.locale_of(dict(spec("informations-be-fr"), language=None)), "fr-BE")  # Liège
        ok, why = Built(dict(spec("informations-be-fr"), language="nl")).check("EMPLOY-BE-LANG")
        self.assertIs(ok, False, why)
        self.assertIn("French", why)
        brussels = dict(spec("informatie-be-nl"), place="Rue Royale 2, 1000 Bruxelles")
        self.assertIs(Built(brussels).check("EMPLOY-BE-LANG")[0], True)

    def test_belgium_first_day_probation_and_joint_committee(self):
        s = spec("informations-be-fr")
        ok, why = Built(dict(s, given="2026-11-03")).check("EMPLOY-DATES")
        self.assertIs(ok, False, why)
        self.assertIn("first day", why)
        ok, why = Built(dict(s, probation={"months": 1})).check("EMPLOY-PROBATION")
        self.assertIs(ok, False, why)
        self.assertIn("2014", why)
        ok, why = Built(dict(s, collective="Conventions conclues dans l'entreprise")).check("EMPLOY-ITEMS")
        self.assertIs(ok, False, why)
        self.assertIn("art. 5 4°", why)
        self.assertIs(Built(s, drop("Intervalles de repos")).check("EMPLOY-ITEMS")[0], False)

    def test_belgium_art_5_items_may_sit_in_the_work_rules(self):
        # Art. 5 binds the document only for a worker outside the work rules act of 8 April 1965: a section that
        # points to the work rules is complete, one that points nowhere or is missing is not.
        s = spec("informations-be-fr")
        rules = dict(s, collective="Voir le règlement de travail, annexe 2",
                     social_security="Voir le règlement de travail, article 3")
        b = Built(rules)
        self.assertIs(b.check("EMPLOY-ITEMS")[0], True, b.check("EMPLOY-ITEMS")[1])
        self.assertIs(b.check("EMPLOY-REFERENCE")[0], True, b.check("EMPLOY-REFERENCE")[1])
        nl = dict(spec("informatie-be-nl"), social_security="Zie het arbeidsreglement, artikel 3")
        self.assertIs(Built(nl).check("EMPLOY-ITEMS")[0], True)
        self.assertIs(Built(nl).check("EMPLOY-REFERENCE")[0], True)
        ok, why = Built(dict(s, social_security="Voir la convention d'entreprise")).check("EMPLOY-ITEMS")
        self.assertIs(ok, False, why)
        self.assertIn("art. 5 5°", why)
        ok, why = Built(s, drop("Institution de sécurité sociale", "Office national de sécurité sociale")
                        ).check("EMPLOY-ITEMS")
        self.assertIs(ok, False, why)
        self.assertIn("8 April 1965", why)

    def test_what_must_be_stated_is_not_given_by_reference(self):
        # Each law's own list of what a statement may give by pointing to a law or an agreement.
        for name, change, cite in (
                ("informations-be-fr", {"place": "Voir le contrat de travail"}, "7 October 2022"),
                ("opgave-nl", {"place": "Zie de arbeidsovereenkomst"}, "BW 7:655 (2)"),
                ("dienstzettel-at", {"collective": "Siehe Aushang im Betrieb, wo die Normen zur Einsicht aufliegen"},
                 "AVRAG § 2 (5)"),
                ("statement-ie", {"place": "See the contract of employment"}, "s. 3(3)")):
            with self.subTest(template=name):
                self.assertIs(Built(spec(name)).check("EMPLOY-REFERENCE")[0], True)
                ok, why = Built(dict(spec(name), **change)).check("EMPLOY-REFERENCE")
                self.assertIs(ok, False, why)
                self.assertIn(cite, why)
        # Austria lets the leave and the notice point to the law (§ 2 (5)), never the basic pay.
        at = spec("dienstzettel-at")
        self.assertIs(Built(dict(at, leave="Siehe § 2 Urlaubsgesetz")).check("EMPLOY-REFERENCE")[0], True)

    def test_netherlands_whether_items_probation_and_signature(self):
        s = spec("opgave-nl")
        self.assertIs(Built(s, drop("geen oproepovereenkomst")).check("EMPLOY-ITEMS")[0], False)
        with self.assertRaises(SystemExit):
            Built({k: v for k, v in s.items() if k != "on_call"})
        ok, why = Built(dict(s, probation={"months": 2})).check("EMPLOY-PROBATION")
        self.assertIs(ok, False, why)
        self.assertIn("7:652", why)
        short = dict(s, term={"type": "fixed", "end": "2027-05-31"})
        self.assertIs(Built(short).check("EMPLOY-PROBATION")[0], False)
        self.assertIs(Built(dict(s, term={"type": "permanent"}, probation={"months": 2})).check("EMPLOY-PROBATION")[0], True)
        self.assertIs(Built(dict(s, given="2026-12-09")).check("EMPLOY-DATES")[0], False)
        self.assertIs(Built(s, drop("Voor de werkgever")).check("EMPLOY-SIGNED")[0], False)

    def test_austria_month_probation_insurers_and_kv(self):
        s = spec("dienstzettel-at")
        ok, why = Built(dict(s, probation={"months": 2})).check("EMPLOY-PROBATION")
        self.assertIs(ok, False, why)
        self.assertIn("1158", why)
        self.assertIs(Built(s, drop("Betriebliche Vorsorgekasse:")).check("EMPLOY-ITEMS")[0], False)
        self.assertIs(Built(dict(s, collective="Kollektivvertrag für Angestellte der Metallindustrie")).check(
            "EMPLOY-ITEMS")[0], False)
        self.assertIs(Built(s, drop("Sitz des Unternehmens")).check("EMPLOY-ITEMS")[0], False)

    def test_ireland_core_terms_and_minimum_wage_note(self):
        s = spec("statement-ie")
        self.assertIs(Built(s, drop("per normal working day")).check("EMPLOY-IE-CORE")[0], False)
        self.assertIs(Built(s, drop("Pay reference period")).check("EMPLOY-IE-CORE")[0], False)
        self.assertIs(Built(s, drop("National Minimum Wage Act 2000 the employee")).check("EMPLOY-ITEMS")[0], False)
        ok, why = Built(dict(s, given="2026-11-09")).check("EMPLOY-DATES")
        self.assertIs(ok, False, why)
        self.assertIn("five days", why.replace("5 calendar days", "five days"))
        self.assertIs(Built(dict(s, probation={"months": 9})).check("EMPLOY-PROBATION")[0], False)
        with self.assertRaises(SystemExit):
            Built(dict(s, pay={k: v for k, v in s["pay"].items() if k != "reference_period"}))

    def test_ireland_signed_and_dated_and_the_registered_agreements(self):
        s = spec("statement-ie")
        self.assertIs(Built(s).check("EMPLOY-SIGNED")[0], True)
        ok, why = Built(s, drop("For the employer")).check("EMPLOY-SIGNED")
        self.assertIs(ok, False, why)
        self.assertIn("s. 3(4)", why)
        undated = Built(s, drop("Date of this statement"))       # a file someone took the date out of
        (undated.dir / "spec.json").write_text(json.dumps({k: v for k, v in s.items() if k != "given"}))
        ok, why = undated.check("EMPLOY-SIGNED")
        self.assertIs(ok, False, why)
        self.assertIn("not dated", why)
        # s. 3(1)(fa): a registered employment agreement or employment regulation order is named with (m)
        text = " ".join(t for _, t in ec.paragraphs(Built(s).path))
        self.assertIn("registered employment agreement or employment regulation order", text)
        self.assertIn("s. 3(1)(fa), (m)", ec.ref("collective", "ie"))

    def test_netherlands_month_limit_names_the_collective_agreement(self):
        ok, why = Built(dict(spec("opgave-nl"), probation={"months": 2})).check("EMPLOY-PROBATION")
        self.assertIs(ok, False, why)
        self.assertIn("7:652 (7)", why)

    def test_a_section_stays_on_one_page(self):
        from docx import Document
        doc = Document(Built(spec("informations-be-fr")).path)
        body = [p for p in doc.paragraphs if not p.style.name.startswith(("Heading", "Title"))]
        kept = [p.paragraph_format.keep_with_next for p in body]
        self.assertTrue(any(kept))
        # the last line under a heading is free to end the page
        for p, nxt in zip(doc.paragraphs, doc.paragraphs[1:]):
            if nxt.style.name.startswith("Heading") and not p.style.name.startswith(("Heading", "Title")):
                self.assertFalse(p.paragraph_format.keep_with_next, p.text)


if __name__ == "__main__":
    unittest.main()
