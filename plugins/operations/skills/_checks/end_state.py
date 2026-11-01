"""The end-state gate under every pack check: the file on disk is judged, never what the chat said about it.

    judge(path, since_ms=None) -> [(rule, evidence)]   an empty list means the file stands

It uses the standard library only, so it runs where a pack's own dependencies (python-docx, openpyxl,
python-pptx, PyMuPDF) are missing, and it runs before any pack rule: a file that does not hold anything
must fail, not be skipped as "could not check" and not pass a floor that has nothing to measure (a
0-byte workbook once came back from every-file as "clean: 1 rules passed").

OUTPUT-EMPTY        no bytes, no text, no slides or cells, no page: nothing was written.
OUTPUT-UNOPENABLE   the name says Word, Excel, PowerPoint, PDF, SVG or PNG and the bytes are not one that opens.
OUTPUT-PLACEHOLDER  it opens, and all it holds is filler (lorem ipsum, "your text here", "[insert ...]",
                    a title and nothing else).
OUTPUT-STALE        the file was last changed before this request began (NODEJAM_TURN_STARTED, in
                    milliseconds, or --since): it is a file that was there already, not this turn's work.

    open_gaps(path) -> [marker]   the gaps left for the person ("[TO CONFIRM: ...]", "[TBD]"), which the pack
                                  check fails as OUTPUT-OPEN-GAP after its own rules have run: the file is
                                  well made and not yet finished (a real run, 2026-10-13: a UK statement with
                                  thirteen "[TO CONFIRM" gaps passed all 24 rules).
"""
import os
import re
import struct
import zipfile
import zlib
from pathlib import Path
from xml.etree import ElementTree as ET

W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
A = "{http://schemas.openxmlformats.org/drawingml/2006/main}"
S = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"

MAIN_PART = {".docx": "word/document.xml", ".xlsx": "xl/workbook.xml", ".pptx": "ppt/presentation.xml"}
TEXTUAL = (".html", ".htm", ".tex", ".md", ".txt", ".csv", ".xml", ".json")

# A finished file never carries these, however much else it holds.
FILLER = re.compile(r"lorem ipsum|your (?:body )?(?:text|title|name|content) (?:goes )?here|insert (?:your )?(?:text|title|content|"
                    r"name)(?: here)?|\[insert[^\]]*\]|click to (?:add|edit)|type (?:your )?(?:text|here)|"
                    r"\bplaceholder\b|\bxxx+\b", re.I)
# A gap left for the person in square brackets, in the languages the library writes: a finished file holds none.
# Requirement specs write their open items as (TBD-1) and (TBR-1), in round brackets, and are not caught.
GAP = re.compile(r"\[\s*(?:to\s+(?:be\s+)?confirm(?:ed)?|confirm|tbd|tbc|todo|to\s+do|fill\s+in|missing|"
                 r"zu\s+best\u00e4tigen|zu\s+erg\u00e4nzen|offen|\u00e0\s+confirmer|\u00e0\s+compl\u00e9ter|"
                 r"att\s+bekr\u00e4fta|fyll\s+i|por\s+confirmar|da\s+confermare|te\s+bevestigen|\?+)"
                 r"(?=[\s:.,\]\u2026-])[^\]]{0,300}\]", re.I)
# The same gap with its words last: "[minute-taker to be confirmed]", "[signatory TBC]" (a real run, 2026-10-13).
GAP_LAST = re.compile(r"\[[^\[\]]{1,120}?\s(?:to\s+be\s+confirmed|to\s+confirm|tbc|tbd|missing)\s*\]", re.I)
# A bracket that holds only the name of a field: "[date]" in a requirements spec's date and history (a timed run,
# 2026-10-25), "[Name]" on a signature line.
GAP_FIELD = re.compile(r"\[\s*(?:date|datum|dato|name|namn|navn|nom|signature|underskrift|unterschrift|address|"
                       r"adress|adresse|company|f\u00f6retag|firma|amount|belopp|betrag|montant)\s*\]", re.I)
# Words that make a page look like it holds something when it holds a heading and nothing else.
BARE = re.compile(r"\b(?:todo|tbd|untitled|document|sheet\d*|slide\s*\d*|title|new)\b", re.I)


def since_ms(given=None):
    """When the request began, in epoch milliseconds: the argument, else the app's NODEJAM_TURN_STARTED, else 0."""
    for value in (given, os.environ.get("NODEJAM_TURN_STARTED")):
        try:
            if value and float(value) > 0:
                return float(value)
        except (TypeError, ValueError):
            continue
    return 0.0


def judge(path, since=None):
    path = Path(path)
    began = since_ms(since)
    try:
        stat = path.stat()
    except OSError:
        return [("OUTPUT-MISSING", "no %s beside the check" % path.name)]
    if stat.st_size == 0:
        return [("OUTPUT-EMPTY", "%s has no bytes: nothing was written to it. A reply that says the work is "
                                 "done is not the work; write the file, then check it." % path.name)]
    if began and stat.st_mtime * 1000 < began:
        return [("OUTPUT-STALE", "%s was last changed before this request began: it is a file that was there "
                                 "already, not work this turn did. Make the change in the file itself." % path.name)]
    kind = path.suffix.lower()
    try:
        if kind in MAIN_PART:
            return office(path, kind)
        if kind == ".pdf":
            return pdf(path)
        if kind == ".svg":
            return svg(path)
        if kind == ".png":
            return png(path)
        if kind in TEXTUAL:
            return plain(path)
    except (OSError, zipfile.BadZipFile, ET.ParseError, KeyError, ValueError, UnicodeError, zlib.error,
            struct.error) as exc:
        return [("OUTPUT-UNOPENABLE", "%s does not open as %s: %s" % (path.name, kind[1:], str(exc)[:80]))]
    return []


def text_of(path):
    """The words a reader sees in the file, for the kinds the gate reads; empty when it cannot read them."""
    path = Path(path)
    kind = path.suffix.lower()
    try:
        if kind in MAIN_PART:
            with zipfile.ZipFile(path) as z:
                names = z.namelist()
                if kind == ".docx":
                    parts = [n for n in names if re.fullmatch(r"word/(?:document|header\d*|footer\d*)\.xml", n)]
                    return " ".join(t.text or "" for n in parts for t in ET.fromstring(z.read(n)).iter(W + "t"))
                if kind == ".pptx":
                    parts = [n for n in names if re.fullmatch(r"ppt/slides/slide\d+\.xml", n)]
                    return " ".join(t.text or "" for n in parts for t in ET.fromstring(z.read(n)).iter(A + "t"))
                if "xl/sharedStrings.xml" in names:
                    return " ".join(t.text or "" for t in ET.fromstring(z.read("xl/sharedStrings.xml")).iter(S + "t"))
                return ""
        if kind == ".pdf":
            try:
                import pymupdf as fitz
            except ImportError:
                import fitz
            with fitz.open(path) as doc:
                return " ".join(page.get_text() for page in doc)
        if kind == ".svg":
            return " ".join((el.text or "") for el in ET.fromstring(path.read_bytes()).iter())
        if kind in TEXTUAL:
            text = path.read_text(encoding="utf-8", errors="replace")
            return re.sub(r"(?is)<(script|style|head)\b.*?</\1>|<[^>]+>", " ", text) if kind in (".html", ".htm") else text
    except Exception:                    # the gate itself has judged whether the file opens
        return ""
    return ""


def open_gaps(path):
    """Each distinct gap left for the person, in the order the file holds them."""
    seen = []
    text = " ".join(text_of(path).split())
    for m in sorted(list(GAP.finditer(text)) + list(GAP_LAST.finditer(text)) + list(GAP_FIELD.finditer(text)),
                    key=lambda m: m.start()):
        if m.group(0) not in seen:
            seen.append(m.group(0))
    return seen


def words(text):
    return re.findall(r"\w+", text, re.UNICODE)


def real_words(text):
    """The words left once filler and bare headings are taken away."""
    return words(BARE.sub(" ", FILLER.sub(" ", text)))


def verdict(path, text, extra=0, what="text"):
    """Empty when there is nothing at all; placeholder when only filler is there; else clean."""
    if not words(text) and not extra:
        return [("OUTPUT-EMPTY", "%s opens and holds no %s: nothing was written in it." % (path.name, what))]
    if FILLER.search(text) or (len(real_words(text)) < 3 and not extra):
        return [("OUTPUT-PLACEHOLDER", "%s holds only filler (%s). Write the real content." %
                 (path.name, " ".join(text.split())[:60] or "nothing readable"))]
    return []


def office(path, kind):
    with zipfile.ZipFile(path) as z:
        if z.testzip() is not None or MAIN_PART[kind] not in z.namelist():
            return [("OUTPUT-UNOPENABLE", "%s is not a whole %s file" % (path.name, kind[1:]))]
        ET.fromstring(z.read(MAIN_PART[kind]))
        names = z.namelist()
        if kind == ".docx":
            root = ET.fromstring(z.read("word/document.xml"))
            text = " ".join(t.text or "" for t in root.iter(W + "t"))
            pictures = sum(1 for _ in root.iter(W + "drawing")) + sum(1 for _ in root.iter(W + "pict"))
            return verdict(path, text, pictures)
        if kind == ".pptx":
            slides = sorted(n for n in names if re.fullmatch(r"ppt/slides/slide\d+\.xml", n))
            if not slides:
                return [("OUTPUT-EMPTY", "%s has no slides." % path.name)]
            text, pictures = [], 0
            for n in slides:
                root = ET.fromstring(z.read(n))
                text += [t.text or "" for t in root.iter(A + "t")]
                pictures += sum(1 for el in root.iter() if el.tag.endswith("}pic") or el.tag.endswith("}graphicFrame"))
            return verdict(path, " ".join(text), pictures, "text or picture on any slide")
        return sheet(path, z, names)


def sheet(path, z, names):
    sheets = [n for n in names if re.fullmatch(r"xl/worksheets/sheet\d+\.xml", n)]
    if not sheets:
        return [("OUTPUT-EMPTY", "%s has no sheet." % path.name)]
    strings = []
    if "xl/sharedStrings.xml" in names:
        strings = ["".join(t.text or "" for t in si.iter(S + "t"))
                   for si in ET.fromstring(z.read("xl/sharedStrings.xml")).iter(S + "si")]
    cells, numbers, text = 0, 0, []
    for n in sheets:
        for c in ET.fromstring(z.read(n)).iter(S + "c"):
            v, f, inline = c.find(S + "v"), c.find(S + "f"), c.find(S + "is")
            if inline is not None:
                value = "".join(t.text or "" for t in inline.iter(S + "t"))
            elif v is not None and (v.text or "") != "":
                value = strings[int(v.text)] if c.get("t") == "s" and v.text.isdigit() and int(v.text) < len(strings) \
                    else v.text
            elif f is not None:
                value = "formula"
            else:
                continue
            if str(value).strip() == "":
                continue
            cells += 1
            if c.get("t") in ("s", "inlineStr", "str"):
                text.append(str(value))
            else:
                numbers += 1
    if cells == 0:
        return [("OUTPUT-EMPTY", "%s opens and has no cell with anything in it." % path.name)]
    joined = " ".join(text)
    if not numbers and (FILLER.search(joined) or len(real_words(joined)) < 2):
        return [("OUTPUT-PLACEHOLDER", "%s holds only filler (%s)." % (path.name, joined[:60]))]
    return []


def plain(path):
    text = path.read_text(encoding="utf-8", errors="replace")
    if path.suffix.lower() in (".html", ".htm"):
        text = re.sub(r"(?is)<(script|style|head)\b.*?</\1>|<[^>]+>", " ", text)
    elif path.suffix.lower() == ".tex":
        text = re.sub(r"\\(?:documentclass|usepackage|begin|end)\b(?:\[[^\]]*\])?(?:\{[^}]*\})?", " ", text)
    return verdict(path, text)


def _has_page(data):
    """A page object in the PDF's own bytes, or inside one of its compressed object streams."""
    if re.search(rb"/Type\s*/Page\b(?!s)", data):
        return True
    import zlib
    for m in re.finditer(rb"<<[^<>]*/Type\s*/ObjStm\b[^<>]*>>\s*stream\r?\n", data):
        end = data.find(b"endstream", m.end())
        try:
            inner = zlib.decompressobj().decompress(data[m.end():end if end > 0 else None])
        except zlib.error:
            continue
        if re.search(rb"/Type\s*/Page\b(?!s)", inner):
            return True
    return False


def pdf(path):
    data = path.read_bytes()
    if not data.startswith(b"%PDF-"):
        return [("OUTPUT-UNOPENABLE", "%s is not a PDF inside (no %%PDF- header)" % path.name)]
    try:
        import pymupdf as fitz            # the app's own Python ships it
    except ImportError:
        try:
            import fitz
        except ImportError:
            fitz = None
    if fitz is None:
        # Without a PDF reader the file is held to the cheap truth: a trailer, and at least one page object.
        if b"%%EOF" not in data[-2048:] or not _has_page(data):
            return [("OUTPUT-UNOPENABLE", "%s has no whole page structure" % path.name)]
        return []
    with fitz.open(stream=data, filetype="pdf") as doc:
        if doc.page_count == 0:
            return [("OUTPUT-EMPTY", "%s has no pages." % path.name)]
        text = " ".join(page.get_text() for page in doc)
        extra = sum(len(page.get_images()) + len(page.get_drawings()) for page in doc)
    return verdict(path, text, extra, "text, picture or drawing on any page")


SVG_SHAPES = ("rect", "path", "line", "polyline", "polygon", "circle", "ellipse", "image", "use")


def svg(path):
    """A drawing: it parses as SVG and holds a shape or words; words that are only filler are a placeholder."""
    root = ET.fromstring(path.read_bytes())
    if not root.tag.endswith("svg"):
        return [("OUTPUT-UNOPENABLE", "%s is not an SVG inside (its root is <%s>)" % (path.name, root.tag.split("}")[-1]))]
    text = " ".join((el.text or "") for el in root.iter() if el.tag.split("}")[-1] not in ("title", "desc", "style"))
    shapes = sum(1 for el in root.iter() if el.tag.split("}")[-1] in SVG_SHAPES
                 and not (el.tag.endswith("rect") and el.get("width") == "100%"))
    if not words(text) and not shapes:
        return [("OUTPUT-EMPTY", "%s opens and draws nothing: no shape and no text." % path.name)]
    if FILLER.search(text) or re.search(r"\[(?:diagram|type|one sentence)[^\]]*\]", text, re.I):
        return [("OUTPUT-PLACEHOLDER", "%s holds only filler (%s). Write the real content." %
                 (path.name, " ".join(text.split())[:60]))]
    return []


def png(path):
    """A picture: a whole PNG whose pixels are not one flat colour (a blank capture is how one usually fails)."""
    data = path.read_bytes()
    if not data.startswith(b"\x89PNG\r\n\x1a\n") or data[12:16] != b"IHDR":
        return [("OUTPUT-UNOPENABLE", "%s is not a PNG inside" % path.name)]
    width, height, depth, colour = struct.unpack(">IIBB", data[16:26])
    if width == 0 or height == 0:
        return [("OUTPUT-EMPTY", "%s has no pixels." % path.name)]
    chunks, at = [], 8
    while at + 8 <= len(data):
        size, name = struct.unpack(">I4s", data[at:at + 8])
        if name == b"IDAT":
            chunks.append(data[at + 8:at + 8 + size])
        if name == b"IEND":
            break
        at += 12 + size
    raw = zlib.decompress(b"".join(chunks))
    channels = {0: 1, 2: 3, 3: 1, 4: 2, 6: 4}.get(colour)
    if depth != 8 or not channels:
        return []                       # an unusual layout opens; the flat-colour test is for the common ones
    stride = width * channels
    if len(raw) < height * (stride + 1):
        return [("OUTPUT-UNOPENABLE", "%s is cut short: its pixels end early" % path.name)]
    prev, first = bytearray(stride), None
    for row in range(height):
        start = row * (stride + 1)
        kind, line = raw[start], bytearray(raw[start + 1:start + 1 + stride])
        for i in (range(stride) if kind else ()):
            a = line[i - channels] if i >= channels else 0
            b, c = prev[i], (prev[i - channels] if i >= channels else 0)
            if kind == 1:
                line[i] = (line[i] + a) & 255
            elif kind == 2:
                line[i] = (line[i] + b) & 255
            elif kind == 3:
                line[i] = (line[i] + (a + b) // 2) & 255
            elif kind == 4:
                p = a + b - c
                pa, pb, pc = abs(p - a), abs(p - b), abs(p - c)
                line[i] = (line[i] + (a if pa <= pb and pa <= pc else b if pb <= pc else c)) & 255
        first = first if first is not None else bytes(line[:channels])
        if bytes(line) != first * width:
            return []
        prev = line
    return [("OUTPUT-EMPTY", "%s is one flat colour: nothing was drawn or captured." % path.name)]
