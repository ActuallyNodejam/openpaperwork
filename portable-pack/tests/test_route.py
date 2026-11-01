"""The prompt-time hint: an ask that names a kind of file a pack makes gets one line naming the skill.

Run from the repository root: python3 -m unittest portable-pack/tests/test_route.py
The asks are in route-asks.json beside this file: every kind of file in every language its pack serves, and
ordinary asks that must get no hint.
"""
import json
import os
import subprocess
import sys
import time
import unittest
from pathlib import Path

PACK = Path(__file__).resolve().parent.parent
HOOK = PACK / "hooks" / "pack_route.py"
sys.path.insert(0, str(PACK / "hooks"))
import pack_route  # noqa: E402

ASKS = json.loads((Path(__file__).resolve().parent / "route-asks.json").read_text(encoding="utf-8"))
ROUTES = pack_route.load()
LANGUAGES = ("en", "de", "fr", "nl", "sv", "nb", "da", "fi", "es", "it", "pl")


def run(data, env=None, raw=None):
    p = subprocess.run([sys.executable, str(HOOK)], input=raw if raw is not None else json.dumps(data),
                       capture_output=True, text=True, env={**os.environ, **(env or {})})
    return p.returncode, p.stdout.strip(), p.stderr.strip()


class TheTable(unittest.TestCase):
    def test_every_ask_gets_the_skills_it_names_in_order(self):
        self.assertGreaterEqual(len(ASKS["asks"]), 40)
        wrong = []
        for row in ASKS["asks"]:
            found = pack_route.asked(row["ask"], ROUTES)
            skills = [route["skill"] for route, _ in found]
            if skills != row["skills"]:
                wrong.append("%r: %s, not %s" % (row["ask"], skills, row["skills"]))
            elif "kinds" in row and sorted(found[0][1]) != sorted(row["kinds"]):
                wrong.append("%r: kinds %s, not %s" % (row["ask"], found[0][1], row["kinds"]))
        self.assertEqual(wrong, [])

    def test_an_ordinary_ask_gets_nothing(self):
        self.assertGreaterEqual(len(ASKS["ordinary"]), 20)
        hinted = {ask: pack_route.hint(ask, ROUTES) for ask in ASKS["ordinary"]}
        self.assertEqual({ask: line for ask, line in hinted.items() if line}, {})

    def test_every_kind_is_asked_for_in_every_language_its_pack_serves(self):
        """The asks cover the table: each kind, in each language the table gives it words in, is the first kind
        some ask is matched to through a word of that language."""
        missing = []
        for r, route in enumerate(ROUTES):
            for k, kind in enumerate(route["kinds"]):
                for language in kind["words"]:
                    only = [dict(route, kinds=[dict(kind, words={language: kind["words"][language]},
                                                    weak={language: (kind.get("weak") or {}).get(language, [])})])]
                    if not any(pack_route.asked(row["ask"], only) for row in ASKS["asks"] if route["skill"] in row["skills"]):
                        missing.append("%s, %s, %s" % (route["skill"], kind["kind"], language))
        self.assertEqual(missing, [])

    def test_the_table_holds_only_languages_the_hook_knows_the_endings_of(self):
        for route in ROUTES:
            for kind in route["kinds"]:
                for group in ("words", "weak", "with", "unless", "not_after"):
                    self.assertLessEqual(set(kind.get(group) or {}), set(LANGUAGES), (route["skill"], group))
                    self.assertLessEqual(set(kind.get(group) or {}), set(pack_route.ENDINGS))

    def test_the_line_names_the_kind_the_skill_and_a_file(self):
        self.assertEqual(
            pack_route.hint("Schreib bitte die Rechnung für Beispiel Druck GmbH.", ROUTES),
            "If this ask is for an invoice, load the e-invoice skill before writing anything: it lays the file out "
            "and checks it. Hand back a file, not text in the chat." + pack_route.FOLDER)
        both = pack_route.hint("Write a letter to the customer and attach the invoice for October.", ROUTES)
        self.assertEqual(
            both, "If this ask is for a letter, load the business-letter skill before writing anything; if it is for "
                  "an invoice, load the e-invoice skill instead. Each lays its file out and checks it. Hand back a "
                  "file, not text in the chat." + pack_route.FOLDER)
        self.assertEqual(both.count("\n"), 0)

    def test_endings_and_accents(self):
        for ask in ("fakturę", "FAKTURĘ", "fakture", "brevet", "Rechnungen", "laskun", "fatture", "albaran",
                    "proces-verbal", "Auftragsbestatigung", "protokol z zebrania", "följesedeln", "foljesedel"):
            self.assertTrue(pack_route.asked(ask, ROUTES), ask)
        for ask in ("Rechnungswesen", "Abrechnung", "Berechnung", "letterhead", "newsletter", "lettering", "briefing",
                    "orderly", "offering", "fatturato", "laskuvarjo", "invoicing platform", "decking"):
            self.assertEqual(pack_route.asked(ask, ROUTES), [], ask)

    def test_a_weak_word_needs_a_second_signal(self):
        self.assertEqual(pack_route.hint("give me a brief summary", ROUTES), "")
        self.assertIn("business-letter", pack_route.hint("Schreib einen Brief an die Firma", ROUTES))
        self.assertIn("business-letter", pack_route.hint("a brief letter to the landlord", ROUTES))
        self.assertEqual(pack_route.hint("list the files", ROUTES), "")
        self.assertIn("business-letter", pack_route.hint("Napisz list do urzędu", ROUTES))
        self.assertEqual(pack_route.hint("in order to", ROUTES), "")
        self.assertEqual(pack_route.hint("ten minutes ago", ROUTES), "")
        self.assertIn("meeting-minutes", pack_route.hint("type up the minutes of the AGM", ROUTES))

    def test_a_longer_match_of_another_kind_wins(self):
        names = lambda ask: [(route["skill"], kinds) for route, kinds in pack_route.asked(ask, ROUTES)]
        self.assertEqual(names("a pro forma invoice for customs"), [("trade-documents", ["a pro forma invoice"])])
        self.assertEqual(names("the offer letter for Sam"), [("employment-statement", ["the written terms of employment"])])
        self.assertEqual(names("fattura proforma"), [("trade-documents", ["a pro forma invoice"])])
        self.assertEqual(names("the invoice, and a pro forma invoice too")[0][0], "e-invoice")


class TheHook(unittest.TestCase):
    def test_claude_code_gets_the_line_as_additional_context(self):
        code, out, err = run({"session_id": "s", "cwd": "/tmp", "hook_event_name": "UserPromptSubmit",
                              "prompt": "Prepara la fattura per questo lavoro."})
        self.assertEqual((code, err), (0, ""))
        answer = json.loads(out)
        self.assertEqual(list(answer), ["hookSpecificOutput"])
        self.assertEqual(answer["hookSpecificOutput"]["hookEventName"], "UserPromptSubmit")
        self.assertTrue(answer["hookSpecificOutput"]["additionalContext"].startswith(
            "If this ask is for an invoice, load the e-invoice skill before writing anything"))

    def test_no_match_prints_nothing(self):
        self.assertEqual(run({"hook_event_name": "UserPromptSubmit", "prompt": "list the files"}), (0, "", ""))
        self.assertEqual(run({"hook_event_name": "UserPromptSubmit", "prompt": ""}), (0, "", ""))
        self.assertEqual(run({"hook_event_name": "UserPromptSubmit"}), (0, "", ""))

    def test_nothing_it_is_given_can_block_an_ask(self):
        for raw in ("", "not json", "[1, 2]", '{"prompt": 7}', '{"prompt": ["invoice"]}', "null"):
            self.assertEqual(run(None, raw=raw), (0, "", ""), raw)
        # A table that is gone or broken is no table.
        self.assertEqual(pack_route.load(PACK / "hooks" / "no-such-file.json"), [])
        self.assertEqual(pack_route.hint("the invoice", []), "")

    def test_a_bounce_that_comes_back_as_a_prompt_and_a_command_are_no_ask(self):
        self.assertEqual(pack_route.hint("A pack check is not clean (try 1 of 3):\n\ne-invoice (invoice.pdf): FAIL", ROUTES), "")
        self.assertEqual(pack_route.hint("/invoice", ROUTES), "")

    def test_inside_the_app_the_hook_stands_down_because_the_app_gives_the_line(self):
        data = {"hook_event_name": "UserPromptSubmit", "prompt": "Make the invoice."}
        self.assertEqual(run(data, env={"OPENPAPERWORK_APP": "1"}), (0, "", ""))
        self.assertNotEqual(run(data, env={"OPENPAPERWORK_APP": ""})[1], "")

    def test_it_costs_nothing_a_person_notices(self):
        long = "Please make the invoice for this job. " + "The notes follow. " * 2000
        started = time.perf_counter()
        for _ in range(20):
            pack_route.hint(long, ROUTES)
        self.assertLess((time.perf_counter() - started) / 20, 0.05)
        # The whole hook, Python's start included, on an ordinary ask.
        times = []
        for _ in range(5):
            started = time.perf_counter()
            run({"hook_event_name": "UserPromptSubmit", "prompt": "Schreib die Rechnung für Beispiel Druck GmbH."})
            times.append(time.perf_counter() - started)
        self.assertLess(sorted(times)[2], 0.5)

    def test_the_hook_imports_nothing_beyond_the_standard_library(self):
        text = HOOK.read_text(encoding="utf-8")
        imported = {line.split()[1].split(".")[0] for line in text.splitlines() if line.startswith(("import ", "from "))}
        self.assertLessEqual(imported, {"json", "os", "sys", "unicodedata", "pathlib"})


if __name__ == "__main__":
    unittest.main()
