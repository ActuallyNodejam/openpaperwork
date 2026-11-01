"""The library gate: every guideline names where its rules come from and on what terms, every
pack the app checks points at a check that exists, and every plugin text names the countries its
packs cover. Shape from the Citation Style Language styles
repo, whose tests refuse a style without its documentation link or its licence.

    python3 -m unittest standards/test_library.py
"""
import json
import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GUIDELINES = sorted((ROOT / "standards/guidelines").glob("*/*/guidelines.json"))
# Our own house rules claim no outside standard, so they carry no outside link.
HOUSE = {"openpaperwork", "house-deck", "house-drafting", "house-honest"}


class Library(unittest.TestCase):
    def test_every_guideline_names_its_source_and_terms(self):
        self.assertTrue(GUIDELINES)
        for path in GUIDELINES:
            name = "/".join(path.parts[-3:-1])
            g = json.loads(path.read_text())
            for key in ("issuer", "version", "date", "status", "source", "license"):
                self.assertTrue(g.get(key), "%s has no %s" % (name, key))
            if g["issuer"] not in HOUSE:
                link = g.get("link") or json.dumps(g["source"])
                self.assertIn("https://", link, "%s has no https link to its official source" % name)
            self.assertTrue(g.get("rules"), "%s has no rules" % name)
            ids = [rule.get("id") for rule in g["rules"]]
            self.assertEqual(len(ids), len(set(ids)), "%s repeats a rule id" % name)

    def test_every_pack_the_app_checks_has_a_check(self):
        DOMAINS = {"finance", "sales", "legal", "hr", "operations", "marketing", "engineering", "academic", "formats"}
        sys.path.insert(0, str(ROOT / "skills/_checks"))
        import packcheck
        packs = sorted((ROOT / "skills").glob("*/pack.json"))
        self.assertTrue(packs)
        for path in packs:
            pack = json.loads(path.read_text())
            # A pack marked "library": false is the app's own and stays out of the library.
            if pack.get("library") is False:
                continue
            self.assertIn(pack.get("domain"), DOMAINS, "%s names no department" % path)
            # A pack.json that only names the department turns on no check in the app.
            if not pack.get("check") and not pack.get("hands_back"):
                continue
            self.assertTrue(pack.get("hands_back"), "%s hands back nothing" % path)
            match = re.search(r"packcheck\.py (\S+) \{file\}", pack.get("check", ""))
            self.assertTrue(match, "%s has no packcheck command" % path)
            self.assertIn(match.group(1), packcheck.SKILL_RULES, "%s names an unknown pack" % path)
            for rule in packcheck.SKILL_RULES[match.group(1)]:
                self.assertIn(rule.split("-")[0], packcheck.MODULES, "%s: %s has no module" % (path, rule))

    @unittest.skipUnless((ROOT / "scripts/build-portable-pack.py").is_file(), "the plugins are built where they ship")
    def test_every_plugin_text_names_the_countries_its_packs_cover(self):
        """The plugin and marketplace texts are written by hand and drifted once. The countries the
        library covers are one list in scripts/build-portable-pack.py (COUNTRIES, and each pack's row
        in PACK_COUNTRIES); the everything text is built from it. This fails when a text names a country
        its department's packs do not cover or misses one they do, and when a pack's own starters or
        tables contradict its row."""
        import importlib.util
        path = ROOT / "scripts/build-portable-pack.py"
        spec = importlib.util.spec_from_file_location("build_portable_pack", path)
        build = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(build)
        names = build.COUNTRIES
        rows = {pack: set(codes.split()) for pack, codes in build.PACK_COUNTRIES.items()}
        library = build.packs()
        # A text may say "a Swedish company" for Sweden.
        of = {"DE": "German", "FR": "French", "SE": "Swedish", "NO": "Norwegian", "DK": "Danish", "FI": "Finnish",
              "GB": "British", "US": "American", "CA": "Canadian", "AU": "Australian", "BE": "Belgian", "NL": "Dutch",
              "AT": "Austrian", "IE": "Irish", "ES": "Spanish", "IT": "Italian", "PL": "Polish"}

        def said(text):
            return {code for code, name in names.items()
                    if re.search(r"\b(%s|%s)\b" % (re.escape(name.replace("the ", "")), of[code]), text)}

        # What a starter says about itself, in the words the packs use: an ISO code, the country in the
        # document's own language, or the law the statement follows.
        local = {"sverige": "SE", "sweden": "SE", "norge": "NO", "danmark": "DK", "suomi": "FI", "germany": "DE",
                 "deutschland": "DE", "france": "FR", "united kingdom": "GB", "uk": "GB", "us": "US", "canada": "CA",
                 "australia": "AU", "belgique": "BE", "belgië": "BE", "nederland": "NL", "österreich": "AT",
                 "ireland": "IE", "españa": "ES", "italia": "IT", "polska": "PL"}
        laws = {"uk": "GB", "on": "CA", "eu": None}
        tables = {"trade-documents": ["_checks/trade_words.json"]}

        def code(value):
            value = str(value or "").strip()
            return value.upper() if value.upper() in names else local.get(value.lower())

        def covered(pack):
            starters = set()
            for f in sorted((ROOT / "skills" / pack / "templates").glob("*.json")):
                data = json.loads(f.read_text())
                if not isinstance(data, dict):
                    continue
                issuer = "buyer" if f.name.startswith("purchase-order") else "seller"
                said_here = [data.get("country")] + [(data.get(k) or {}).get("country") for k in (issuer, "sender")
                                                    if isinstance(data.get(k), dict)]
                law = str(data.get("law") or "").lower()
                if law:
                    said_here.append(laws.get(law, law.upper()))
                starters |= {code(v) for v in said_here if v} - {None}
            files = [p for p in (ROOT / "skills" / pack).rglob("*")
                     if p.is_file() and p.suffix in (".py", ".json", ".md") and "tests" not in p.parts]
            files += [ROOT / "skills" / rel for rel in tables.get(pack, [])]
            text = "\n".join(p.read_text(errors="ignore") for p in files)
            return starters, {tag for tag in re.findall(r"\b[a-z]{2}-([A-Z]{2})\b", text) if tag in names}

        for pack, codes in sorted(rows.items()):
            self.assertIn(pack, library, "PACK_COUNTRIES names %s, which is not a pack" % pack)
            self.assertTrue(codes <= set(names), "%s: a code that is not in COUNTRIES" % pack)
            starters, tags = covered(pack)
            self.assertFalse(starters - codes, "%s has a starter for %s, which its row does not name"
                             % (pack, sorted(starters - codes)))
            self.assertFalse(codes - starters - tags, "%s: nothing in the pack covers %s"
                             % (pack, sorted(codes - starters - tags)))
        for domain, text in build.DOMAINS.items():
            want = set().union(*[rows.get(pack, set()) for pack, (d, _) in library.items() if d == domain])
            self.assertEqual(said(text), want, "the %s text and its packs disagree on %s"
                             % (domain, sorted(said(text) ^ want)))
        everything = set().union(*rows.values())
        self.assertEqual(said(build.EVERYTHING_TEXT), everything)
        self.assertEqual(everything, set(names), "COUNTRIES and the packs' rows disagree")
        # The operations text says the minutes' countries against the letters': "the same countries",
        # or "the same countries except ..." naming exactly the ones the minutes pack lacks.
        same = re.search(r"for the same countries(?: except ([^,]+))?,", build.DOMAINS["operations"])
        if same:
            self.assertEqual(said(same.group(1) or ""), rows["business-letter"] - rows["meeting-minutes"],
                             "the operations text and the minutes pack disagree")
            self.assertFalse(rows["meeting-minutes"] - rows["business-letter"])


if __name__ == "__main__":
    unittest.main()
