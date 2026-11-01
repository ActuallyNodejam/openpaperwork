#!/usr/bin/env python3
r"""Build the paper from a JSON of sections, using the starter preamble so the fonts are its own.

    python3 build_paper.py paper.json paper.tex [--template ieee-conference] [--pdf]

The starter preamble carries the Times family for text and math. A hand-written preamble is how a
paper comes out in Computer Modern, which is what one rep in three did, so the pack writes the
preamble and the model writes only the words.

paper.json:
{
  "title": "...", "authors": [{"name": "...", "affiliation": "..."}],
  "abstract": "...", "keywords": ["..."],
  "sections": [{"heading": "Introduction", "paragraphs": ["...", "..."]}],
  "references": [{"key": "yao2023", "authors": ["Yao, S.", "Zhao, J."], "title": "...", "venue": "Proc. ICLR",
                  "year": 2023, "arxiv": "2210.03629"}]
}
Cite a reference in a paragraph with \cite{its key}. A plain string in "references" is keyed ref1, ref2 in
order, and an entry written as \bibitem{key} ... keeps its own key.
"""
import argparse
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

SKILL = Path(__file__).resolve().parents[1]

MARK = "% nodejam-paper-builder"


def preamble(template):
    src = SKILL / "templates" / template / "paper.tex"
    if not src.is_file():
        raise SystemExit("no starter at %s" % src)
    text = src.read_text()
    cut = text.find("\\begin{document}")
    if cut < 0:
        raise SystemExit("%s has no \\begin{document}" % src)
    return text[:cut]


def ieee_reference(ref):
    """A reference from its record (authors, title, venue, year, doi, arxiv or url), in IEEE form."""
    def esc(s):
        return re.sub(r"(?<!\\)([&%#])", r"\\\1", str(s))
    names = []
    for a in ref.get("authors") or []:
        a = str(a).strip()
        last, first = ([x.strip() for x in a.split(",", 1)] if "," in a
                       else (a.split()[-1], " ".join(a.split()[:-1])) if a.split() else ("", ""))
        given = " ".join(w if re.fullmatch(r"(?:[A-Z]\.-?)+", w) else w[0] + "." for w in first.split() if w)
        names.append(("%s~%s" % (given, last)) if given else last)
    if len(names) > 6:
        names = names[:1] + ["et al."]
        who = " ".join(names)
    elif len(names) > 2:
        who = ", ".join(names[:-1]) + ", and " + names[-1]
    else:
        who = " and ".join(names)
    rest = []
    if ref.get("venue"):
        rest.append(("in \\emph{%s}" if re.search(r"Proc|Conf|Workshop", str(ref["venue"])) else "\\emph{%s}")
                    % esc(ref["venue"]))
    if ref.get("year"):
        rest.append(str(ref["year"]))
    if ref.get("doi"):
        rest.append("doi: %s" % ref["doi"])
    elif ref.get("arxiv"):
        rest.append("arXiv:%s" % str(ref["arxiv"]).replace("arXiv:", ""))
    elif ref.get("url"):
        rest.append("\\url{%s}" % ref["url"])
    head = "%s, ``%s,''" % (who, esc(ref.get("title", ""))) if who else "``%s,''" % esc(ref.get("title", ""))
    return (head + " " + ", ".join(rest) + ".") if rest else head.rstrip(",'") + ".''"


def body(spec, template="ieee-conference"):
    out = ["\\begin{document}", "\\title{%s}" % spec.get("title", "Paper")]
    if template == "acm-sigconf":
        # acmart takes the authors, abstract and keywords before \\maketitle; 2.x refuses an abstract after it.
        for a in spec.get("authors") or [{"name": "Author"}]:
            out.append("\\author{%s}" % a.get("name", ""))
            if a.get("affiliation"):
                out.append("\\affiliation{\\institution{%s}}" % a["affiliation"])
        if spec.get("abstract"):
            out += ["\\begin{abstract}", spec["abstract"], "\\end{abstract}"]
        if spec.get("keywords"):
            out.append("\\keywords{%s}" % ", ".join(spec["keywords"]))
        out.append("\\maketitle")
    else:
        for a in spec.get("authors") or [{"name": "Author"}]:
            out.append("\\author{%s%s}" % (a.get("name", ""),
                                           ("\\\\" + a["affiliation"]) if a.get("affiliation") else ""))
        out += ["\\maketitle"]
        if spec.get("abstract"):
            out += ["\\begin{abstract}", spec["abstract"], "\\end{abstract}"]
        if spec.get("keywords"):
            out.append("\\begin{IEEEkeywords}%s\\end{IEEEkeywords}" % ", ".join(spec["keywords"]))
    for s in spec.get("sections") or []:
        out.append("\\section{%s}" % s.get("heading", "Section"))
        out += [p for p in (s.get("paragraphs") or [])]
    if spec.get("references"):
        out.append("\\begin{thebibliography}{99}")
        for i, ref in enumerate(spec["references"], 1):
            if isinstance(ref, dict):
                out.append("\\bibitem{%s} %s" % (ref.get("key") or "ref%d" % i,
                                                 ref.get("text") or ieee_reference(ref)))
            elif str(ref).lstrip().startswith("\\bibitem"):
                out.append(str(ref).strip())
            else:
                out.append("\\bibitem{ref%d} %s" % (i, ref))
        out.append("\\end{thebibliography}")
    out.append("\\end{document}")
    return "\n".join(out)


def engine():
    """The engine on this computer, else tectonic fetched once into the cache (engine.py)."""
    sys.path.insert(0, str(SKILL))
    from engine import engine as find_engine

    _, path = find_engine()
    if not path:
        return None, None
    # An offline kit ships its TeX packages in a bundle beside the engine.
    return Path(path), Path(path).parent.parent / "bundle"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("spec")
    ap.add_argument("out")
    ap.add_argument("--template", default="ieee-conference")
    ap.add_argument("--pdf", action="store_true")
    a = ap.parse_args()

    spec = json.loads(Path(a.spec).read_text())
    # The mark says the starter built it, the same way the page and the deck carry theirs.
    tex = MARK + "\n" + preamble(a.template) + "\n" + body(spec, a.template) + "\n"
    out = Path(a.out)
    out.write_text(tex)
    # A class the starter ships (acmart.cls) goes beside the .tex, so it wins over an older one in the TeX distribution.
    for cls in sorted((SKILL / "templates" / a.template).glob("*.cls")):
        shutil.copyfile(cls, out.parent / cls.name)
    fonts = "mathptmx" in tex or "Times" in tex or "ptm" in tex
    print("%s -> %s (template %s, Times in the preamble: %s)" % (a.spec, out, a.template, fonts))

    if a.pdf:
        eng, bundle = engine()
        if eng is None:
            print("no TeX engine and none could be fetched (offline?); leaving the .tex")
            return
        env = {"HOME": str(Path.home()), "PATH": "/usr/bin:/bin"}
        if bundle and bundle.is_dir():
            env["TECTONIC_CACHE_DIR"] = str(bundle)
        r = subprocess.run([str(eng), "--outdir", str(out.parent), out.name],
                           capture_output=True, text=True, cwd=str(out.parent), env=env)
        pdf = out.with_suffix(".pdf")
        lost = sorted(set(re.findall(r'Missing character: There is no .*? \("([0-9A-Fa-f]+)\)', r.stdout + r.stderr)))
        if lost:
            print("the font has no glyph for %s; the PDF drops it. Write it the TeX way (--- for an em dash) and build again"
                  % ", ".join("U+%04X %s" % (int(c, 16), chr(int(c, 16))) for c in lost))
            sys.exit(1)
        print("pdf:", pdf.is_file(), pdf.stat().st_size if pdf.is_file() else (r.stderr or "")[-120:])


if __name__ == "__main__":
    main()
