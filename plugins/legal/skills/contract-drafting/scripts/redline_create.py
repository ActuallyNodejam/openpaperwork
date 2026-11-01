#!/usr/bin/env python3
"""Return the other side's Word file with our proposed edits as real tracked changes.

Usage: redline_create.py redline.json [out.docx]

{
  "source": "their-nda.docx",              # their file, beside this JSON; it is never changed
  "output": "their-nda-redline.docx",      # optional; else <source>-redline.docx
  "author": "Exempel Tryck AB",           # shown on every change in Word
  "date": "2026-11-03T09:00:00Z",          # optional; else now
  "edits": [
    {"find": "ten (10) years", "replace": "three (3) years", "comment": "Our prices change every year."},
    {"find": ", including any residual knowledge", "replace": ""},
    {"after": "its employees", "insert": " and professional advisers"},
    {"after_paragraph": "6.2 The Receiving Party shall", "paragraph": "6.3 The Receiving Party may keep ..."}
  ]
}

find/replace marks the words deleted and the new words inserted (an empty replace only deletes);
after/insert inserts words right after the anchor; after_paragraph/paragraph inserts a whole new
paragraph, styled like the one holding the anchor, after it. Every find and anchor must appear
exactly once in the document (add "occurrence": n to pick the n-th), and inside one paragraph. A
"comment" adds a Word comment on the change, for the other side to read: keep internal strategy
out of it.

Everything else in the file stays byte for byte as it was: only word/document.xml changes, and,
with comments, the comments part, its relationship and content type. Word, LibreOffice and Pages
show the changes for the other side to accept or reject. Prints a JSON summary. Needs lxml (comes
with python-docx).
"""
import copy
import datetime as dt
import json
import re
import sys
import zipfile
from pathlib import Path

from lxml import etree

WNS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
W = "{%s}" % WNS
XML_SPACE = "{http://www.w3.org/XML/1998/namespace}space"
COMMENTS_REL = "http://schemas.openxmlformats.org/officeDocument/2006/relationships/comments"
COMMENTS_CT = "application/vnd.openxmlformats-officedocument.wordprocessingml.comments+xml"
CONTENT = {"t": None, "tab": "\t", "br": "\n", "cr": "\n", "noBreakHyphen": "-", "softHyphen": ""}


def fail(msg):
    raise SystemExit(msg)


class Doc:
    def __init__(self, xml):
        self.root = etree.fromstring(xml)
        ids = [int(v) for el in self.root.iter() for k, v in el.attrib.items()
               if k == W + "id" and re.fullmatch(r"-?\d+", v or "")]
        self.next_id = max(ids + [0]) + 1
        self.comments = []

    def new_id(self):
        self.next_id += 1
        return str(self.next_id - 1)


def run_text(r):
    out = ""
    for ch in r:
        tag = ch.tag[len(W):] if ch.tag.startswith(W) else ""
        if tag == "t":
            out += ch.text or ""
        elif tag in CONTENT:
            out += CONTENT[tag]
    return out


def split_runs(p):
    """Give every run in the paragraph one piece of content, so a run can be cut at any letter."""
    for r in list(p.iter(W + "r")):
        if r.getparent().tag not in (W + "p", W + "hyperlink", W + "smartTag", W + "fldSimple"):
            continue
        content = [ch for ch in r if ch.tag != W + "rPr"]
        if len(content) <= 1:
            continue
        rpr = r.find(W + "rPr")
        parent, at = r.getparent(), r.getparent().index(r)
        parent.remove(r)
        for i, ch in enumerate(content):
            nr = etree.Element(W + "r")
            if rpr is not None:
                nr.append(copy.deepcopy(rpr))
            nr.append(ch)
            parent.insert(at + i, nr)


def editable_runs(p):
    """The runs whose text counts, in order: not inside a deletion, an insertion or a nested paragraph."""
    runs = []
    for r in p.iter(W + "r"):
        if next(r.iterancestors(W + "p")) is not p:
            continue
        if any(a.tag in (W + "del", W + "ins", W + "moveFrom", W + "moveTo") for a in r.iterancestors()):
            runs.append((r, run_text(r), False))
            continue
        runs.append((r, run_text(r), True))
    return runs


def paragraph_text(p):
    return "".join(t for _, t, _ in editable_runs(p))


def body_paragraphs(doc):
    body = doc.root.find(W + "body")
    return [p for p in body.iter(W + "p")]


def locate(doc, needle, occurrence=None):
    """(paragraph, start offset) of the needle; it must appear once, or the occurrence asked for."""
    hits = []
    for p in body_paragraphs(doc):
        text = paragraph_text(p)
        start = text.find(needle)
        while start >= 0:
            hits.append((p, start))
            start = text.find(needle, start + 1)
    if not hits:
        fail("%r is not in the document as one piece of text in one paragraph; copy it exactly" % needle[:80])
    if occurrence:
        if occurrence > len(hits):
            fail("%r appears %d times, not %d" % (needle[:60], len(hits), occurrence))
        return hits[occurrence - 1]
    if len(hits) > 1:
        fail("%r appears %d times; give more of the sentence, or \"occurrence\"" % (needle[:60], len(hits)))
    return hits[0]


def cut(p, offset):
    """Split the run at offset so a run boundary falls there; returns nothing."""
    pos = 0
    for r, text, ok in editable_runs(p):
        if pos < offset < pos + len(text):
            t = r.find(W + "t")
            if t is None or not ok:
                fail("an edit starts or ends inside a tab, a field or another tracked change; widen it")
            left, right = text[:offset - pos], text[offset - pos:]
            twin = copy.deepcopy(r)
            t.text = left
            t.set(XML_SPACE, "preserve")
            tt = twin.find(W + "t")
            tt.text = right
            tt.set(XML_SPACE, "preserve")
            r.addnext(twin)
            return
        pos += len(text)


def runs_between(p, start, end):
    out, pos = [], 0
    for r, text, ok in editable_runs(p):
        if start <= pos and pos + len(text) <= end and text:
            if not ok:
                fail("an edit touches text that is already a tracked change; accept or reject that first")
            out.append(r)
        pos += len(text)
    return out


def mark(tag, doc, author, date):
    el = etree.Element(W + tag)
    el.set(W + "id", doc.new_id())
    el.set(W + "author", author)
    el.set(W + "date", date)
    return el


def new_run(text, rpr):
    r = etree.Element(W + "r")
    if rpr is not None:
        r.append(copy.deepcopy(rpr))
    t = etree.SubElement(r, W + "t")
    t.text = text
    t.set(XML_SPACE, "preserve")
    return r


def delete_runs(doc, runs, author, date):
    dels = []
    for r in runs:
        d = mark("del", doc, author, date)
        r.addprevious(d)
        d.append(r)
        for t in r.findall(W + "t"):
            t.tag = W + "delText"
        for t in r.findall(W + "instrText"):
            t.tag = W + "delInstrText"
        dels.append(d)
    return dels


def comment_on(doc, first, last, text, author, date):
    cid = doc.new_id()
    start = etree.Element(W + "commentRangeStart")
    start.set(W + "id", cid)
    end = etree.Element(W + "commentRangeEnd")
    end.set(W + "id", cid)
    first.addprevious(start)
    last.addnext(end)
    ref = etree.Element(W + "r")
    rpr = etree.SubElement(ref, W + "rPr")
    etree.SubElement(rpr, W + "rStyle").set(W + "val", "CommentReference")
    etree.SubElement(ref, W + "commentReference").set(W + "id", cid)
    end.addnext(ref)
    doc.comments.append((cid, text, author, date))


def apply(doc, e, author, date):
    occ = e.get("occurrence")
    if "find" in e:
        if "replace" not in e:
            fail("an edit with \"find\" needs \"replace\" (empty to delete)")
        p, start = locate(doc, e["find"], occ)
        end = start + len(e["find"])
        cut(p, start)
        cut(p, end)
        runs = runs_between(p, start, end)
        rpr = runs[0].find(W + "rPr")
        dels = delete_runs(doc, runs, author, date)
        first = last = dels[0]
        last = dels[-1]
        if e["replace"]:
            ins = mark("ins", doc, author, date)
            ins.append(new_run(e["replace"], rpr))
            dels[-1].addnext(ins)
            last = ins
        if e.get("comment"):
            comment_on(doc, first, last, e["comment"], author, date)
        return "replaced" if e["replace"] else "deleted"
    if "after" in e:
        if not e.get("insert"):
            fail("an edit with \"after\" needs the words to \"insert\"")
        p, start = locate(doc, e["after"], occ)
        end = start + len(e["after"])
        cut(p, start)
        cut(p, end)
        runs = runs_between(p, start, end)
        if not runs:
            fail("could not place the insertion after %r" % e["after"][:60])
        anchor = runs[-1]
        ins = mark("ins", doc, author, date)
        ins.append(new_run(e["insert"], anchor.find(W + "rPr")))
        anchor.addnext(ins)
        if e.get("comment"):
            comment_on(doc, ins, ins, e["comment"], author, date)
        return "inserted"
    if "after_paragraph" in e:
        if not e.get("paragraph"):
            fail("an edit with \"after_paragraph\" needs the new \"paragraph\"")
        p, _ = locate(doc, e["after_paragraph"], occ)
        new = etree.Element(W + "p")
        ppr = p.find(W + "pPr")
        ppr = copy.deepcopy(ppr) if ppr is not None else etree.Element(W + "pPr")
        for old in ppr.findall(W + "rPr"):
            ppr.remove(old)
        for old in ppr.findall(W + "sectPr"):
            ppr.remove(old)
        rpr_mark = etree.SubElement(ppr, W + "rPr")
        rpr_mark.append(mark("ins", doc, author, date))      # the new paragraph's mark is inserted too
        new.append(ppr)
        first_run = next((r for r, t, ok in editable_runs(p) if ok and t.strip()), None)
        ins = mark("ins", doc, author, date)
        ins.append(new_run(e["paragraph"], first_run.find(W + "rPr") if first_run is not None else None))
        new.append(ins)
        p.addnext(new)
        if e.get("comment"):
            comment_on(doc, ins, ins, e["comment"], author, date)
        return "paragraph added"
    fail("each edit needs find/replace, after/insert or after_paragraph/paragraph: %s" % json.dumps(e)[:80])


def comments_part(doc, existing):
    if existing:
        root = etree.fromstring(existing)
    else:
        root = etree.Element(W + "comments", nsmap={"w": WNS})
    for cid, text, author, date in doc.comments:
        c = etree.SubElement(root, W + "comment")
        c.set(W + "id", cid)
        c.set(W + "author", author)
        c.set(W + "date", date)
        c.set(W + "initials", "".join(w[0] for w in author.split()[:3]).upper())
        p = etree.SubElement(c, W + "p")
        ppr = etree.SubElement(p, W + "pPr")
        etree.SubElement(ppr, W + "pStyle").set(W + "val", "CommentText")
        r = etree.SubElement(p, W + "r")
        rpr = etree.SubElement(r, W + "rPr")
        etree.SubElement(rpr, W + "rStyle").set(W + "val", "CommentReference")
        etree.SubElement(r, W + "annotationRef")
        p.append(new_run(text, None))
    return etree.tostring(root, xml_declaration=True, encoding="UTF-8", standalone=True)


def redline(spec, base):
    src = base / spec["source"]
    if not src.is_file():
        fail("their file %s is not beside the redline JSON" % spec["source"])
    if src.suffix.lower() != ".docx":
        fail("a redline needs their Word file (.docx); a PDF cannot carry tracked changes")
    author = str(spec.get("author") or "").strip()
    if not author:
        fail("give \"author\": the name the other side sees on each change")
    date = spec.get("date") or dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", date):
        date += "T00:00:00Z"
    if not spec.get("edits"):
        fail("no edits to make")
    with zipfile.ZipFile(src) as z:
        parts = [(i, z.read(i.filename)) for i in z.infolist()]
    names = {i.filename: data for i, data in parts}
    doc = Doc(names["word/document.xml"])
    for p in body_paragraphs(doc):
        split_runs(p)
    done = [apply(doc, e, author, date) for e in spec["edits"]]
    new = {"word/document.xml": etree.tostring(doc.root, xml_declaration=True, encoding="UTF-8", standalone=True)}
    if doc.comments:
        rels = names["word/_rels/document.xml.rels"].decode("utf-8")
        target = re.search(r'Type="%s"\s+Target="([^"]+)"' % re.escape(COMMENTS_REL), rels) or \
            re.search(r'Target="([^"]+)"\s+Type="%s"' % re.escape(COMMENTS_REL), rels)
        part = "word/" + target.group(1) if target else "word/comments.xml"
        new[part] = comments_part(doc, names.get(part))
        if not target:
            rid = "rId%d" % (max([int(x) for x in re.findall(r'Id="rId(\d+)"', rels)] + [0]) + 1)
            new["word/_rels/document.xml.rels"] = rels.replace(
                "</Relationships>", '<Relationship Id="%s" Type="%s" Target="comments.xml"/></Relationships>'
                % (rid, COMMENTS_REL)).encode("utf-8")
            ct = names["[Content_Types].xml"].decode("utf-8")
            if "/word/comments.xml" not in ct:
                new["[Content_Types].xml"] = ct.replace(
                    "</Types>", '<Override PartName="/word/comments.xml" ContentType="%s"/></Types>'
                    % COMMENTS_CT).encode("utf-8")
    return parts, new, done


def main(argv):
    if len(argv) not in (2, 3):
        print(__doc__.split("\n\n")[1])
        return 2
    spec_path = Path(argv[1])
    spec = json.loads(spec_path.read_text())
    # Nothing given is dropped: an unknown key or a value of the wrong shape stops the build here.
    here = Path(__file__).resolve().parent
    sys.path.insert(0, str(here.parent.parent / "_shared"))
    import spec_guard
    spec_guard.guard(spec, here.parent / "redline.fields.json", "redline's data file")
    if not spec.get("source"):
        fail("give \"source\": their Word file, beside this JSON")
    base = spec_path.parent
    out = Path(argv[2]) if len(argv) == 3 else base / (spec.get("output") or
                                                         Path(spec["source"]).stem + "-redline.docx")
    spec_guard.output_guard(out, __file__, "redline")
    if out.resolve() == (base / spec["source"]).resolve():
        fail("write the redline to a new file; their original stays as it is")
    parts, new, done = redline(spec, base)
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        seen = set()
        for info, data in parts:
            z.writestr(info, new.get(info.filename, data))
            seen.add(info.filename)
        for name, data in new.items():
            if name not in seen:
                z.writestr(name, data)
    print(json.dumps({"file": str(out), "source": spec["source"], "changes": done, "author": spec["author"],
                      "say": "Their file with our edits as tracked changes; everything else is as they sent it."},
                     ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
