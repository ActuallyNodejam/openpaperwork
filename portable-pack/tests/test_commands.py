"""The commands: one per base workflow a pack declares, in every plugin that carries the pack, named in the READMEs.

Run from the repository root: python3 -m unittest portable-pack/tests/test_commands.py
"""
import importlib.util
import json
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
spec = importlib.util.spec_from_file_location("build", ROOT / "scripts/build-portable-pack.py")
build = importlib.util.module_from_spec(spec)
spec.loader.exec_module(build)
LIBRARY = build.packs()
# The glyphs the starter cards draw (the whole-chain cards use the same set).
ICONS = {"workflow", "presentation", "bullet-list", "table", "checklist", "file-text"}


def flows():
    for pack, (domain, text) in LIBRARY.items():
        for flow in build.workflows(build.front_matter(text)):
            yield pack, domain, flow


class Commands(unittest.TestCase):
    def test_every_pack_that_names_its_kinds_declares_a_workflow(self):
        for pj in sorted((ROOT / "skills").glob("*/pack.json")):
            spec = json.loads(pj.read_text())
            pack = pj.parent.name
            if spec.get("retired") or not spec.get("asks") or pack not in LIBRARY:
                continue
            with self.subTest(pack=pack):
                self.assertTrue(build.workflows(build.front_matter(LIBRARY[pack][1])),
                                "skills/%s names kinds of file in pack.json but declares no workflows" % pack)

    def test_every_workflow_reads_in_swedish_and_english(self):
        for pack, _, flow in flows():
            with self.subTest(pack=pack, workflow=flow.get("id")):
                for key in ("id", "arguments", "menu", "menu_en", "gives", "gives_en", "takes", "takes_en"):
                    self.assertTrue(str(flow.get(key) or "").strip(), "no %s" % key)
                self.assertIn(flow.get("icon"), ICONS)

    def test_every_workflow_is_a_command_in_each_plugin_that_carries_its_pack(self):
        for pack, domain, flow in flows():
            for plugin in ("plugins/%s" % domain, "portable-pack"):
                with self.subTest(plugin=plugin, workflow=flow["id"]):
                    text = (ROOT / plugin / "commands" / ("%s.md" % flow["id"])).read_text()
                    self.assertIn("description: %s\n" % flow["gives_en"].rstrip("."), text)
                    self.assertIn("argument-hint: %s\n" % flow["takes_en"].rstrip("."), text)
                    self.assertIn("Load the %s skill" % pack, text)
                    self.assertIn("${CLAUDE_PLUGIN_ROOT}/skills/%s/SKILL.md" % pack, text)
                    self.assertTrue((ROOT / plugin / "skills" / pack / "SKILL.md").is_file())
                    self.assertIn("$ARGUMENTS", text)

    def test_the_readmes_name_every_command(self):
        top = (ROOT / "README.md").read_text()
        for pack, domain, flow in flows():
            with self.subTest(workflow=flow["id"]):
                self.assertIn("`/openpaperwork-%s:%s`" % (domain, flow["id"]),
                              (ROOT / "plugins" / domain / "README.md").read_text())
                self.assertRegex(top, r"\| %s \|[^\n]*`%s`" % (re.escape(build.TITLES[domain]), re.escape(flow["id"])))

    def test_every_pack_ships_the_floor_its_check_runs_on_an_office_file(self):
        for pack in LIBRARY:
            with self.subTest(pack=pack):
                files = build.needed([pack])
                self.assertIn("_checks/floor.py", files)
                self.assertIn("_checks/layout.py", files)

    def test_the_parser_reads_the_shape_the_app_reads(self):
        fm = ('name: x\nmetadata:\n  domain: sales\nworkflows:\n  - id: "quotation"\n    arguments: "quotation"\n'
              '    icon: file-text\n    menu: "Offert"\n    menu_en: "Quotation"\n    gives: "En offert"\n'
              '    gives_en: "A quotation"\n    takes: "Skriv en rad: 40 stolar"\n    takes_en: "Write one line: 40 chairs"\n'
              '  - id: "delivery-note"\n    menu_en: "Delivery note"\n')
        got = build.workflows(fm)
        self.assertEqual([f["id"] for f in got], ["quotation", "delivery-note"])
        self.assertEqual(got[0]["icon"], "file-text")
        self.assertEqual(got[0]["takes_en"], "Write one line: 40 chairs")
        self.assertEqual(build.workflows("name: x\n"), [])


if __name__ == "__main__":
    unittest.main()
