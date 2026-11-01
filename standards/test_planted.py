"""Pack grade: each check fails a file that breaks its rule.

For every pack under standards/planted, the clean file built from the pack's public starter passes its own check,
and every file with one planted fault fails, naming the rule the fault breaks (expect.json). A check that passes
everything cannot pass this test. Builds nothing: make.py wrote the files where the builders are installed.

    python3 -m unittest -v standards/test_planted.py
    python3 standards/test_planted.py --coverage     which of each pack's rules a planted fault trips

Needs the packs' Python packages (portable-pack/requirements.txt); no model, no account, no network.
"""
import json
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
PLANTED = HERE / "planted"
PACKCHECK = HERE.parent / "skills" / "_checks" / "packcheck.py"


def packs():
    return sorted(p for p in PLANTED.iterdir() if (p / "expect.json").is_file())


def run_check(pack, folder, name):
    out = subprocess.run([sys.executable, str(PACKCHECK), pack, str(folder / name)], cwd=folder,
                         capture_output=True, text=True, timeout=300)
    text = out.stdout + out.stderr
    return out.returncode, text, set(re.findall(r"^FAIL\s+(\S+)", text, re.M))


def in_folder(pack_folder, expect, fault=None):
    """The clean files as a chat folder holds them, the spec beside them; a fault's file in place of the one it
    replaces."""
    folder = Path(tempfile.mkdtemp())
    for name in expect.get("files") or ["spec.json", expect["clean"]]:
        shutil.copy(pack_folder / name, folder / name)
    if fault:
        shutil.copy(pack_folder / fault["file"], folder / (fault.get("replaces") or expect["clean"]))
    return folder


class PlantedFaults(unittest.TestCase):
    def test_there_are_planted_faults(self):
        self.assertTrue(packs(), "no pack under standards/planted has an expect.json")

    def test_every_clean_file_passes_its_own_check(self):
        for folder in packs():
            expect = json.loads((folder / "expect.json").read_text())
            with self.subTest(pack=expect["pack"]):
                work = in_folder(folder, expect)
                try:
                    code, text, fails = run_check(expect["pack"], work, expect["clean"])
                finally:
                    shutil.rmtree(work)
                self.assertEqual(fails, set(), text[-600:])
                self.assertEqual(code, 0, text[-600:])

    def test_every_planted_fault_fails_the_rule_it_breaks(self):
        for folder in packs():
            expect = json.loads((folder / "expect.json").read_text())
            self.assertTrue(expect["faults"], "%s has no planted fault" % expect["pack"])
            for fault in expect["faults"]:
                with self.subTest(pack=expect["pack"], fault=fault["file"]):
                    work = in_folder(folder, expect, fault)
                    try:
                        code, text, fails = run_check(expect["pack"], work, expect["clean"])
                    finally:
                        shutil.rmtree(work)
                    missing = set(fault["fails"]) - fails
                    self.assertFalse(missing, "%s (%s) should fail %s; the check said:\n%s"
                                     % (fault["file"], fault["planted"], sorted(missing), text[-600:]))
                    self.assertNotEqual(code, 0)


def coverage():
    """Which of each pack's rules at least one planted fault trips. A rule nothing trips is not yet shown to fail."""
    sys.path.insert(0, str(PACKCHECK.parent))
    import packcheck
    for folder in packs():
        expect = json.loads((folder / "expect.json").read_text())
        rules = list(packcheck.SKILL_RULES.get(expect["pack"], []))
        tripped = {r for f in expect["faults"] for r in f["fails"]}
        print("%-22s %2d of %2d rules tripped by a planted fault: %s" % (
            expect["pack"], len(tripped & set(rules)), len(rules), ", ".join(sorted(tripped))))
        untested = [r for r in rules if r not in tripped]
        if untested:
            print("%-22s not yet: %s" % ("", ", ".join(untested)))


if __name__ == "__main__":
    if "--coverage" in sys.argv:
        coverage()
    else:
        unittest.main()
