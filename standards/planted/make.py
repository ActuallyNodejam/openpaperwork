#!/usr/bin/env python3
"""Build the planted-fault fixtures: one clean file per pack from its public starter, and the same file with one
fault planted in it, so the pack-grade test can show that each check fails a file that breaks its rule.

    python3 standards/planted/make.py            build every fixture and say what each check found
    python3 standards/planted/make.py --pack X   one pack

Run it where the builders' packages are installed (portable-pack/requirements.txt). It writes
standards/planted/<pack>/: spec.json, the clean file, one file per fault, and expect.json. A fault whose
expected rule does not fail stops the build, so a fixture is only written when the check really catches it.
CI never builds: it reads what this wrote (test_planted.py).
"""
from __future__ import annotations

import argparse
import copy
import json
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
SKILLS = ROOT / "skills"
PACKCHECK = SKILLS / "_checks" / "packcheck.py"


def packcheck(pack: str, folder: Path, name: str) -> tuple[int, str, set[str]]:
    out = subprocess.run([sys.executable, str(PACKCHECK), pack, str(folder / name)], cwd=folder,
                         capture_output=True, text=True, timeout=300)
    text = out.stdout + out.stderr
    return out.returncode, text, set(re.findall(r"^FAIL\s+(\S+)", text, re.M))


def edit_docx(src: Path, dst: Path, op: dict) -> None:
    """Change the built file the way a hand edit would: drop a paragraph, or replace words in one."""
    import docx

    doc = docx.Document(str(src))
    paragraphs = list(doc.paragraphs)
    for table in doc.tables:
        for row in table.rows:
            for cell in row.cells:
                paragraphs.extend(cell.paragraphs)
    hits = [p for p in paragraphs if op["find"] in p.text]
    if not hits:
        raise SystemExit("planted fault %s: %r is not in %s" % (op["id"], op["find"], src.name))
    for p in hits:
        if op.get("replace") is None:
            p._element.getparent().remove(p._element)
        else:
            text = p.text.replace(op["find"], op["replace"])
            for run in p.runs[1:]:
                run._element.getparent().remove(run._element)
            if p.runs:
                p.runs[0].text = text
            else:
                p.add_run(text)
    doc.save(str(dst))


def steps_of(plan: dict) -> list[list[str]]:
    """The commands that build the clean files, each a script under the pack and its arguments."""
    if "steps" in plan:
        return plan["steps"]
    return [["scripts/" + plan["builder"], "spec.json", plan["output"]]]


def build(pack: str, spec: dict, plan: dict, folder: Path) -> None:
    (folder / "spec.json").write_text(json.dumps(spec, indent=2, ensure_ascii=False) + "\n")
    for step in steps_of(plan):
        run = subprocess.run([sys.executable, str(SKILLS / pack / step[0]), *step[1:]],
                             cwd=folder, capture_output=True, text=True, timeout=300)
        if run.returncode != 0:
            raise SystemExit("%s: %s failed: %s" % (pack, step[0], (run.stderr or run.stdout).strip()[-400:]))
    for name in files_of(plan):
        if not (folder / name).is_file():
            raise SystemExit("%s: the build wrote no %s" % (pack, name))


def files_of(plan: dict) -> list[str]:
    return plan.get("files") or [plan["output"]]


def plant(src: Path, dst: Path, fault: dict) -> None:
    """A Word file is edited paragraph by paragraph; any other file as text, the first match only."""
    if src.suffix == ".docx":
        edit_docx(src, dst, fault)
        return
    text = src.read_text()
    new, n = re.subn(fault["find"], fault["replace"], text, count=1, flags=re.S)
    if not n:
        raise SystemExit("planted fault %s: %r is not in %s" % (fault["id"], fault["find"], src.name))
    dst.write_text(new)


def make(pack: str, plan: dict) -> dict:
    spec = json.loads((SKILLS / pack / "templates" / plan["template"]).read_text())
    spec.update(plan.get("spec", {}))
    files = files_of(plan)
    out = plan.get("check") or files[0]
    dest = HERE / pack
    with tempfile.TemporaryDirectory() as tmp:
        work = Path(tmp) / "clean"
        work.mkdir()
        build(pack, spec, plan, work)
        code, text, fails = packcheck(pack, work, out)
        if fails or code != 0:
            raise SystemExit("%s: the clean file does not pass its own check:\n%s" % (pack, text[-800:]))
        if dest.exists():
            shutil.rmtree(dest)
        dest.mkdir(parents=True)
        for name in ["spec.json", *files]:
            shutil.copy(work / name, dest / name)
        expect = {"pack": pack, "template": plan["template"], "clean": out, "files": ["spec.json", *files],
                  "faults": []}
        for fault in plan["faults"]:
            target = fault.get("file") or out
            name = "%s%s" % (fault["id"], Path(target).suffix)
            trial = Path(tmp) / fault["id"]
            shutil.copytree(work, trial)
            plant(work / target, trial / target, fault)
            code, text, fails = packcheck(pack, trial, out)
            if not fault["expect"]:
                print("  %-22s DISCOVER: fails %s" % (fault["id"], ", ".join(sorted(fails)) or "nothing"))
                continue
            missing = set(fault["expect"]) - fails
            if missing:
                raise SystemExit("%s/%s: expected %s to fail, the check failed %s:\n%s"
                                 % (pack, fault["id"], sorted(missing), sorted(fails) or "nothing", text[-800:]))
            shutil.copy(trial / target, dest / name)
            expect["faults"].append({"file": name, "replaces": target, "planted": fault["why"],
                                     "fails": sorted(fault["expect"]),
                                     "also_failed_when_made": sorted(fails - set(fault["expect"]))})
            print("  %-22s fails %s" % (fault["id"], ", ".join(sorted(fails))))
        (dest / "expect.json").write_text(json.dumps(expect, indent=2, ensure_ascii=False) + "\n")
    return expect


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--pack")
    args = parser.parse_args()
    plans = json.loads((HERE / "faults.json").read_text())
    for pack, plan in plans.items():
        if args.pack and pack != args.pack:
            continue
        print(pack)
        make(pack, plan)
    return 0


if __name__ == "__main__":
    sys.exit(main())
