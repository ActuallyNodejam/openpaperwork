#!/usr/bin/env python3
"""The business letter for Norway, Denmark, Finland, the United States, the United Kingdom, Canada (English
and French), Australia, Belgium (Dutch and French), the Netherlands, Austria, Ireland, Spain, Italy and
Poland: the sender's country picks the paper and the envelope window
(skills/_shared/letter.py LAYOUTS), the recipient's post office the address (letter.postal_lines), the
letter's language the words, the date and the closing. letter_create.py hands a spec here when the
sender's country (or the spec's "layout") is one of those; Germany, Sweden and the rest stay on DIN 5008.

Where each convention comes from:
- United States: full block (every line on the left edge), the date written out (October 9, 2026),
  "Dear Ms. Berg:" with a colon and "Sincerely," with a comma (US Navy Correspondence Manual SECNAV
  M-5216.5, the business letter; public domain), the address on USPS Publication 28.
- Canada: the same page in English; the complimentary close capitalised and followed by a comma
  (Translation Bureau, Writing Tips Plus, cited). In French the OQLF's parts of a letter (cited): the
  place and date (Montréal, le 9 octobre 2026), "Objet :" in bold, a salutation with a comma, and a
  closing sentence that repeats it (Veuillez agréer, Madame, ...); « » with no-break spaces.
- United Kingdom and Australia: dates as 9 October 2026 (GOV.UK style guide, OGL v3; the Style Manual),
  "Yours sincerely" to a named person and "Yours faithfully" after "Dear Sir or Madam" (Australian
  Government Style Manual, emails and letters, cited), no punctuation after either in Australia.
- Norway, Denmark: the subject in bold with no label, the references and the date beside or under the
  address, "Med vennlig hilsen" / "Med venlig hilsen".
- Finland: SFS 2487's columns, 23 mm apart from the 20 mm margin: the date in the fifth column of the
  head, the text from the second column, labels such as Liitteet on the margin; the date 9.10.2026;
  "Ystävällisin terveisin". The page number with the page count after it in brackets, 1 (2), in the last
  column of the head on every page (Kielitoimiston ohjepankki, Sivunumerointi, citing SFS 2487).
- Belgium: the address on the right (bpost), a reference line under it with the labels in small letters
  (uw kenmerk, ons kenmerk, datum), the subject in bold with no label, and a comma after the closing only
  when the salutation has one (Taaladvies.net on the BIN standard NBN Z 01-002, which is paid and was not
  read). In French the letter the pack already writes: the place and date, "Objet :", a closing sentence
  that repeats the salutation.
- Netherlands: the references and the date in a line under the address, "Betreft:" before the subject, a
  comma after the salutation and after "Met vriendelijke groet," (Taaladvies.net, Opmaak van een zakelijke
  brief in Nederland).
- Austria: the references beside the address, the subject in bold with no label, a comma after the
  salutation and no mark after "Mit freundlichen Grüßen" (Amtliches Regelwerk der deutschen Rechtschreibung
  2024, § 72, CC BY 4.0), Jänner for January (CLDR de-AT), Beilagen for enclosures.
- Ireland: the United Kingdom's page with An Post's address: every element on its own line, the Eircode
  last. No Irish authority's rule for salutations was found; "Yours sincerely" and "Yours faithfully" as
  in the United Kingdom.
- Spain: the address on the right (Correos), the place and the date with a comma between them (Madrid,
  9 de octubre de 2026), "Asunto:" before the subject, a colon after the salutation, never a comma, and a
  comma after a closing with no verb, "Atentamente," (Real Academia Española, Puntuación de saludos y
  despedidas en cartas y correos electrónicos, and the Diccionario panhispánico de dudas, coma; cited).
- Italy: the address on the right (Poste Italiane), the place and the date (Milano, 9 ottobre 2026),
  "Oggetto:" before the subject, "Distinti saluti". No Italian authority's rule for the punctuation of
  the salutation and the closing was found; the check scripts none.
- Poland: the address on the right (Poczta Polska), the place and the date (Warszawa, 9 października
  2026), "Dotyczy:" before the subject, a comma (or an exclamation mark) after the salutation and no mark
  after "Z poważaniem" (Poradnia Językowa PWN, Interpunkcja zwrotów adresatywnych oraz pożegnalnych,
  2021; cited).
"""
import re
from pathlib import Path

import letter

FONT = "Arial"
INK, MUTED = "#12100E", "#6B6259"
# SFS 2487 sets its columns 23 mm apart from the 20 mm margin; the page number stands in the last one.
FI_PAGE_COLUMN = 161

WORDS = {
    "nb-NO": {"date": "Dato", "yours": "Deres ref.", "ours": "Vår ref.", "contact": "Saksbehandler", "phone": "Telefon",
              "email": "E-post", "enclosures": "Vedlegg", "vat_id": "Org.nr.", "closing": "Med vennlig hilsen"},
    "da-DK": {"date": "Dato", "yours": "Deres ref.", "ours": "Vores ref.", "contact": "Kontaktperson", "phone": "Telefon",
              "email": "E-mail", "enclosures": "Bilag", "vat_id": "CVR-nr.", "closing": "Med venlig hilsen"},
    "fi-FI": {"date": "Päiväys", "yours": "Viitteenne", "ours": "Viitteemme", "contact": "Yhteyshenkilö", "phone": "Puhelin",
              "email": "Sähköposti", "enclosures": "Liitteet", "vat_id": "ALV-nro", "closing": "Ystävällisin terveisin"},
    "en-US": {"date": "Date", "yours": "Your reference", "ours": "Our reference", "contact": "Contact", "phone": "Phone",
              "email": "Email", "enclosures": "Enclosures", "vat_id": "EIN", "closing": "Sincerely,"},
    "en-CA": {"date": "Date", "yours": "Your reference", "ours": "Our reference", "contact": "Contact", "phone": "Phone",
              "email": "Email", "enclosures": "Enclosures", "vat_id": "GST/HST No.", "closing": "Sincerely,"},
    "en-GB": {"date": "Date", "yours": "Your ref", "ours": "Our ref", "contact": "Contact", "phone": "Phone",
              "email": "Email", "enclosures": "Enclosures", "vat_id": "VAT number", "closing": "Yours sincerely"},
    "en-AU": {"date": "Date", "yours": "Your ref", "ours": "Our ref", "contact": "Contact", "phone": "Phone",
              "email": "Email", "enclosures": "Enclosures", "vat_id": "ABN", "closing": "Yours sincerely"},
    "fr-CA": {"date": "Date", "yours": "Votre référence", "ours": "Notre référence", "contact": "Personne-ressource",
              "phone": "Téléphone", "email": "Courriel", "enclosures": "Pièces jointes", "vat_id": "No TPS",
              "subject": "Objet", "closing": "Veuillez agréer, %s, mes salutations distinguées."},
}
WORDS["fr-FR"] = dict(WORDS["fr-CA"], contact="Contact", vat_id="N° TVA")
# Wave 8. "enclosure_one" is the label when a single thing is enclosed.
WORDS["en-IE"] = WORDS["en-GB"]
WORDS["nl-NL"] = {"date": "Datum", "yours": "Uw kenmerk", "ours": "Ons kenmerk", "contact": "Contactpersoon",
                  "phone": "Telefoon", "email": "E-mail", "enclosures": "Bijlagen", "enclosure_one": "Bijlage",
                  "vat_id": "Btw-nummer", "subject": "Betreft", "closing": "Met vriendelijke groet,"}
# Belgium's reference line carries its labels in small letters (Taaladvies.net on the BIN standard).
WORDS["nl-BE"] = {"date": "datum", "yours": "uw kenmerk", "ours": "ons kenmerk", "contact": "contactpersoon",
                  "phone": "telefoon", "email": "e-mail", "enclosures": "Bijlagen", "enclosure_one": "Bijlage",
                  "vat_id": "BTW", "closing": "Met vriendelijke groeten"}
WORDS["fr-BE"] = dict(WORDS["fr-CA"], contact="Personne de contact", email="E-mail", enclosures="Annexes",
                      enclosure_one="Annexe", vat_id="TVA")
WORDS["de-AT"] = {"date": "Datum", "yours": "Ihr Zeichen", "ours": "Unser Zeichen", "contact": "Kontakt",
                  "phone": "Telefon", "email": "E-Mail", "enclosures": "Beilagen", "enclosure_one": "Beilage",
                  "vat_id": "UID-Nr.", "closing": "Mit freundlichen Grüßen"}
WORDS["de-DE"] = dict(WORDS["de-AT"], enclosures="Anlagen", enclosure_one="Anlage", vat_id="USt-IdNr.")
# Wave 9. PLACE_DATE: the locales that write the sender's town before the date, with a comma between them.
WORDS["es-ES"] = {"date": "Fecha", "yours": "Su referencia", "ours": "Nuestra referencia", "contact": "Contacto",
                  "phone": "Teléfono", "email": "Correo electrónico", "enclosures": "Anexos", "enclosure_one": "Anexo",
                  "vat_id": "NIF", "subject": "Asunto", "closing": "Atentamente,"}
WORDS["it-IT"] = {"date": "Data", "yours": "Vostro riferimento", "ours": "Nostro riferimento", "contact": "Referente",
                  "phone": "Telefono", "email": "E-mail", "enclosures": "Allegati", "enclosure_one": "Allegato",
                  "vat_id": "Partita IVA", "subject": "Oggetto", "closing": "Distinti saluti"}
WORDS["pl-PL"] = {"date": "Data", "yours": "Wasz znak", "ours": "Nasz znak", "contact": "Osoba kontaktowa",
                  "phone": "Telefon", "email": "E-mail", "enclosures": "Załączniki", "enclosure_one": "Załącznik",
                  "vat_id": "NIP", "subject": "Dotyczy", "closing": "Z poważaniem"}
PLACE_DATE = ("es-ES", "it-IT", "pl-PL")
# The salutation to someone whose name the writer does not know, by language.
UNNAMED = ("dear sir or madam", "dear sir", "dear madam", "madame, monsieur", "to whom it may concern")
NORDIC = ("nb-NO", "da-DK", "fi-FI")


def _esc(s):
    return str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def guillemets(text):
    """French quotation marks with no-break spaces for straight double quotes (OQLF)."""
    return re.sub(r'"([^"]+)"', "« \\1 »", str(text))


class WindowLetter:
    def __init__(self, spec):
        self.lid, self.lay = letter.letter_layout(spec)
        if not self.lay:
            raise ValueError("not a window letter: DIN 5008 Form B writes this one")
        self.locale, self.why = letter.letter_locale(spec)
        if self.locale not in WORDS:
            # A language these pages have no words for (Swedish or German from Oslo): the sender's own.
            self.why += "; written in %s, the sender's language, since %s has no words here" % (
                letter.NEW_LOCALE[self.lay["country"]], self.locale)
            self.locale = letter.NEW_LOCALE[self.lay["country"]]
        self.w = WORDS[self.locale]
        needed = ["date", "sender", "recipient", "subject", "body", "signatory"]
        if self.locale not in NORDIC:
            needed.append("salutation")
        missing = [k for k in needed if not spec.get(k)]
        if missing:
            raise ValueError("the spec needs %s" % ", ".join(missing))
        self.spec = dict(spec)
        self.spec.setdefault("closing", self.closing())
        if self.locale.startswith("fr"):
            self.spec["body"] = [guillemets(p) for p in spec["body"]]
            self.spec["subject"] = guillemets(spec["subject"])

    # -- the parts --------------------------------------------------------------------------------
    def closing(self):
        sal = str(self.spec.get("salutation") if hasattr(self, "spec") else "").strip()
        c = self.w["closing"]
        if self.locale == "nl-BE":
            # Belgium: a comma after the closing when the salutation has one, none when it has none.
            return c + ("," if sal.endswith(",") else "")
        if self.locale in ("en-GB", "en-AU", "en-IE"):
            # Yours faithfully after "Dear Sir or Madam", Yours sincerely to a named person.
            return "Yours faithfully" if sal.lower().rstrip(",").strip() in UNNAMED else "Yours sincerely"
        if "%s" in c:
            # OQLF: the closing repeats the salutation's term of address (Madame, Monsieur, Madame, Monsieur).
            term = sal.rstrip(",").strip() or "Madame, Monsieur"
            term = re.sub(r"^(Bonjour|Cher|Chère)\s+", "", term)
            return c % term
        return c

    def date(self, value=None):
        value = self.spec["date"] if value is None else value
        return letter.long_date(value, self.locale) if re.match(r"^\d{4}-\d{2}-\d{2}$", str(value)) else str(value)

    def date_line(self):
        if self.locale.startswith("fr"):
            # OQLF: the place, then "le" and the date, no full stop.
            city = (self.spec["sender"].get("city") or "").strip()
            return ("%s, le %s" % (city, self.date())) if city else "Le %s" % self.date()
        if self.locale in PLACE_DATE:
            # Spain, Italy, Poland: the place, a comma, the date (Diccionario panhispánico de dudas, coma).
            city = (self.spec["sender"].get("city") or "").strip()
            return ("%s, %s" % (city, self.date())) if city else self.date()
        return self.date()

    def address(self):
        return letter.postal_lines(self.spec["recipient"], self.spec["sender"].get("country"))

    def refs(self):
        out = []
        for x in self.spec.get("references", []):
            label = self.w.get(x.get("kind")) or x.get("label") or ""
            out.append((label, self.date(x["value"])))
        return out

    def contact_rows(self):
        c, w = self.spec.get("contact") or {}, self.w
        return [(k, v) for k, v in ((w["contact"], c.get("name")), (w["phone"], c.get("phone")), (w["email"], c.get("email"))) if v]

    def info_rows(self):
        return self.refs() + self.contact_rows() + [(self.w["date"], self.date_line())]

    def own_sender(self):
        """The sender with a country to write its address by: its own, else the layout's."""
        s = self.spec["sender"]
        return dict(s, country=s.get("country") or self.lay["country"])

    def letterhead(self):
        # The town line the footer prints, and the company's invoice and trade document (letter.town_line).
        s = self.spec["sender"]
        return " · ".join(x for x in (s.get("street"), letter.town_line(self.own_sender()), s.get("phone"), s.get("web")) if x)

    def footer(self):
        # The first column is the company's own address, the one its invoice and its trade document print.
        s = self.spec["sender"]
        who = letter.own_address(self.own_sender(), (self.spec.get("recipient") or {}).get("country"))
        tax = (["%s %s" % (self.w["vat_id"], s["vat_id"])] if s.get("vat_id") else []) + letter.company_lines(s, self.locale)
        tax += letter.further_lines(s)
        reach = [s.get("email"), s.get("phone"), s.get("web")]
        return [[x for x in col if x] for col in (who, tax, reach)]

    def sign(self):
        g = self.spec["signatory"]
        return [g["name"]] + ([g["role"]] if g.get("role") else [])

    def subject_text(self):
        if self.w.get("subject"):
            # French sets a no-break space before the colon (Objet : ...); Dutch sets none (Betreft: ...).
            return "%s%s%s" % (self.w["subject"], "\u00a0: " if self.locale.startswith("fr") else ": ", self.spec["subject"])
        return self.spec["subject"]

    def subject_after_salutation(self):
        # The United Kingdom, Ireland and Australia put the heading under "Dear ..."; the rest above it.
        return self.lay["country"] in ("GB", "AU", "IE")

    def enclosures_label(self):
        one = len(self.spec.get("enclosures") or []) == 1
        return self.w.get("enclosure_one", self.w["enclosures"]) if one else self.w["enclosures"]


# ---- PDF ------------------------------------------------------------------------------------------

PAGE_TOP, PAGE_FOOT = 25, 30   # mm kept clear at the top of a following page and above the foot of every page


def page_count(pdf):
    """The pages of a PDF Chromium printed, counted from its page objects (standard library only)."""
    try:
        return max(1, len(re.findall(rb"/Type\s*/Page(?![A-Za-z])", Path(pdf).read_bytes())))
    except OSError:
        return 1


def write_pdf(spec, out):
    """Print the letter. A Finnish letter (SFS 2487) numbers its pages 1 (2) in the last column of the
    head, so it is printed once to count its pages and, when there is more than one, again with the
    numbers on every page."""
    lt = WindowLetter(spec)
    how = _print(lt, out, 1)
    pages = page_count(out)
    if lt.lay["info"] == "fi" and pages > 1:
        how = _print(lt, out, pages)
    return how


def _print(lt, out, pages):
    s, lay = lt.spec, lt.lay
    W, H = letter.paper_size(lay)
    wx, wy, ww, wh = lay["window"]
    ax, ay = lay["address_at"]
    tx = lay["text_x"]
    parts = []
    sal = '<p class="sal">%s</p>' % _esc(s["salutation"]) if s.get("salutation") else ""
    subj = '<h1>%s</h1>' % _esc(lt.subject_text())
    parts += [sal, subj] if lt.subject_after_salutation() else [subj, sal]
    parts += ['<p>%s</p>' % _esc(p) for p in s["body"]]
    # The closing, the room to sign, the name and the enclosures stay on one page.
    end = ['<p class="close">%s</p>' % _esc(s["closing"]),
           '<p class="sign">%s</p>' % "<br>".join(_esc(x) for x in lt.sign())]
    if s.get("enclosures"):
        if lay["info"] == "fi":
            end.append('<div class="encl fi"><b>%s</b><span>%s</span></div>' % (
                _esc(lt.enclosures_label()), "<br>".join(_esc(x) for x in s["enclosures"])))
        else:
            end.append('<p class="encl"><b>%s</b><br>%s</p>' % (_esc(lt.enclosures_label()), "<br>".join(_esc(x) for x in s["enclosures"])))
    parts.append('<div class="end">%s</div>' % "".join(end))
    blocks = []
    if lay["info"] == "above":
        rows = lt.refs()
        blocks.append('<div class="dateline" style="left:%smm;top:%smm">%s%s</div>' % (
            lay["left"], lay["date_at"], _esc(lt.date_line()),
            "".join('<div class="ref"><span>%s</span> %s</div>' % (_esc(k), _esc(v)) for k, v in rows)))
    elif lay["info"] == "right":
        blocks.append('<dl class="info" style="left:125mm;top:%smm;width:%smm">%s</dl>' % (
            ay, W - 125 - lay["right"],
            "".join("<div><dt>%s</dt><dd>%s</dd></div>" % (_esc(k), letter.keep(v)) for k, v in lt.info_rows())))
    elif lay["info"] == "refline":
        # The Norwegian reference line: their reference, ours and the date in three columns under the
        # address, the case officer's name and how to reach them on the row below.
        cols = (lt.refs() + [(lt.w["date"], lt.date_line())])[:3]
        cols += [("", "")] * (3 - len(cols)) + lt.contact_rows()
        blocks.append('<div class="refline" style="left:%smm;right:%smm;top:%smm">%s</div>' % (
            lay["left"], lay["right"], wy + wh + 4,
            "".join("<div><dt>%s</dt><dd>%s</dd></div>" % (_esc(k), letter.keep(v)) for k, v in cols)))
    elif lay["info"] == "fi":
        blocks.append('<div class="fihead" style="left:%smm;top:15mm">%s</div>' % (lay["left"] + 92, _esc(lt.date_line())))
        # SFS 2487: the page number and the page count, 1 (2), in the last column of the head on every page.
        for k in range(pages):
            blocks.append('<div class="fihead pageno" style="left:%smm;top:%.1fmm">%d (%d)</div>' % (
                lay["left"] + FI_PAGE_COLUMN, k * H + 15, k + 1, pages))
        rows = lt.refs() + lt.contact_rows()
        blocks.append('<div class="firefs" style="left:%smm;top:%smm">%s</div>' % (
            lay["left"], wy + wh + 4,
            "".join('<div><dt>%s</dt><dd>%s</dd></div>' % (_esc(k), letter.keep(v)) for k, v in rows)))
    # A token with a hyphen stays on one line and an e-mail address breaks only after its @ (letter.keep).
    foot = "".join("<div>%s</div>" % "<br>".join(letter.keep(x) for x in col) for col in lt.footer())
    css = """
@page{size:%(W).1fmm %(H).1fmm;margin:0}
*{box-sizing:border-box;margin:0;padding:0}
html,body{width:%(W).1fmm}
body{position:relative;min-height:%(H).1fmm;font-family:"Helvetica Neue",Helvetica,Arial,sans-serif;color:%(ink)s;font-size:10pt;line-height:1.4}
.head{position:absolute;left:%(left)smm;right:%(right)smm;top:14mm}
.head .name{font-size:15pt;font-weight:700;letter-spacing:-.2px}
.head .from{font-size:7.5pt;color:%(muted)s;margin-top:1mm}
.addr{position:absolute;left:%(ax)smm;top:%(ay)smm;width:%(aw).1fmm;font-size:10pt;line-height:%(line)smm}
.dateline{position:absolute;font-size:10pt}
.dateline .ref{font-size:8.5pt;color:%(ink)s;margin-top:1mm}
.dateline .ref span{color:%(muted)s}
.info{position:absolute;display:grid;grid-template-columns:max-content 1fr;column-gap:3mm;font-size:8.5pt;line-height:1.5}
.info div{display:contents}
.info dt{color:%(muted)s}
.info dd{min-width:0;overflow-wrap:anywhere}
.refline{position:absolute;display:grid;grid-template-columns:1fr 1fr 1fr;gap:2.5mm 4mm;border-top:0.2mm solid #D9D1C7;padding-top:1.5mm}
.refline dt{font-size:7.5pt;color:%(muted)s}
.refline dd{font-size:9pt}
.fihead{position:absolute;font-size:10pt}
.firefs{position:absolute;width:%(fiw)smm}
.firefs div{display:flex;font-size:9pt;line-height:1.5}
.firefs dt{width:23mm;flex:none;color:%(muted)s}
.body{padding:%(body_y)smm %(right)smm 0 %(tx)smm}
.flow{width:100%%;border-collapse:collapse}
.flow td{padding:0;border:0}
.flow .top{height:%(page_top)smm}
.flow .foot{height:%(page_foot)smm}
.end{break-inside:avoid}
h1{font-size:11pt;font-weight:700;margin:0 0 5mm}
.sal{margin-bottom:4mm}
.body p{font-size:10pt;margin-bottom:3.5mm}
.body p.close{margin-top:5mm;margin-bottom:0}
.body p.sign{margin-top:15mm}
.encl{margin-top:6mm;font-size:9.5pt}
.encl.fi{display:flex;margin-left:-%(indent)smm}
.encl.fi b{width:%(indent)smm;flex:none;font-weight:700}
footer{position:fixed;left:%(left)smm;right:%(right)smm;bottom:8mm;border-top:0.2mm solid #E3DCD3;padding-top:2.5mm;
 display:grid;grid-template-columns:1fr 1.6fr 1fr;gap:5mm;font-size:7pt;line-height:1.45;color:%(muted)s}
""" % {"W": W, "H": H, "ink": INK, "muted": MUTED, "left": lay["left"], "right": lay["right"], "ax": ax, "ay": ay,
       "aw": letter.window_box(lay)[2] - ax, "line": lay["line"], "body_y": lay["body_y"], "tx": tx, "indent": tx - lay["left"], "fiw": W - lay["left"] - lay["right"],
       "page_top": PAGE_TOP, "page_foot": PAGE_FOOT}
    # The text starts a little under whichever ends lower: the address, the date or the reference block.
    # It runs in a table whose head and foot rows are empty and repeat on every printed page, so a second
    # page starts %(page_top)s mm down and no page runs into the footer.
    script = """<script>
const mm=96/25.4;let low=%(body_y)s*mm-8*mm;
for(const e of document.querySelectorAll('.addr,.dateline,.info,.refline,.firefs')){low=Math.max(low,e.offsetTop+e.offsetHeight)}
document.querySelector('.body').style.paddingTop=(low+8*mm-%(page_top)s*mm)+'px';
</script>""" % {"body_y": lay["body_y"], "page_top": PAGE_TOP}
    html = """<!doctype html><html lang="%(lang)s"><head><meta charset="utf-8">
<meta name="generator" content="nodejam-letter-builder">
<meta name="layout" content="%(layout)s">
<title>%(title)s</title><style>%(css)s</style></head><body>
<div class="head"><div class="name">%(name)s</div><div class="from">%(from)s</div></div>
<div class="addr">%(addr)s</div>
%(blocks)s
<section class="body"><table class="flow"><thead><tr><td><div class="top"></div></td></tr></thead>
<tfoot><tr><td><div class="foot"></div></td></tr></tfoot>
<tbody><tr><td>%(body)s</td></tr></tbody></table></section>
<footer>%(foot)s</footer>
%(script)s
</body></html>
""" % {"lang": lt.locale, "layout": _esc(lay["name"]), "title": _esc(s["subject"]), "css": css, "name": _esc(s["sender"]["name"]),
       "from": _esc(lt.letterhead()), "addr": "<br>".join(_esc(x).replace("  ", "&nbsp; ") for x in lt.address()),
       "blocks": "\n".join(blocks), "body": "".join(parts), "foot": foot, "script": script}
    page = Path(out).with_suffix(".html")
    page.write_text(html)
    return letter.print_letter(page, out, lay["paper"])


# ---- Word -----------------------------------------------------------------------------------------

WORD_TOP = 30   # mm: the letterhead sits in the page header above this line on every page


def write_docx(spec, out):
    from docx import Document
    from docx.enum.table import WD_ROW_HEIGHT_RULE, WD_CELL_VERTICAL_ALIGNMENT
    from docx.oxml import OxmlElement
    from docx.oxml.ns import qn
    from docx.shared import Mm, Pt, RGBColor
    lt = WindowLetter(spec)
    s, lay = lt.spec, lt.lay
    W, H = letter.paper_size(lay)
    wx, wy, ww, wh = lay["window"]
    ax, ay = lay["address_at"]
    usable = W - lay["left"] - lay["right"]
    doc = Document()
    sec = doc.sections[0]
    sec.page_width, sec.page_height = Mm(W), Mm(H)
    sec.left_margin, sec.right_margin = Mm(lay["left"]), Mm(lay["right"])
    sec.top_margin, sec.bottom_margin = Mm(WORD_TOP), Mm(30)
    sec.header_distance, sec.footer_distance = Mm(14), Mm(8)
    for style in doc.styles:
        if style.type == 1 and style.font is not None:
            style.font.name = FONT
            rpr = style.element.get_or_add_rPr()
            fonts = rpr.find(qn("w:rFonts"))
            if fonts is None:
                fonts = OxmlElement("w:rFonts")
                rpr.append(fonts)
            for attr in ("w:ascii", "w:hAnsi", "w:eastAsia", "w:cs"):
                fonts.set(qn(attr), FONT)
    doc.styles["Normal"].font.size = Pt(10)
    doc.styles["Normal"].paragraph_format.space_after = Pt(0)
    doc.core_properties.title = s["subject"]
    doc.core_properties.language = lt.locale
    doc.core_properties.author = s["signatory"]["name"]
    doc.core_properties.category = "letter: %s" % lay["name"]

    def run(p, text, bold=False, size=None, grey=False):
        r = p.add_run(text)
        r.bold = bold
        if size:
            r.font.size = Pt(size)
        if grey:
            r.font.color.rgb = RGBColor(0x6B, 0x62, 0x59)
        return r

    def bare(table):
        pr = table._tbl.tblPr
        borders = OxmlElement("w:tblBorders")
        for edge in ("top", "left", "bottom", "right", "insideH", "insideV"):
            e = OxmlElement("w:%s" % edge)
            e.set(qn("w:val"), "nil")
            borders.append(e)
        pr.append(borders)
        mar = OxmlElement("w:tblCellMar")
        for edge in ("left", "right", "top", "bottom"):
            e = OxmlElement("w:%s" % edge)
            e.set(qn("w:w"), "0")
            e.set(qn("w:type"), "dxa")
            mar.append(e)
        pr.append(mar)
        lay_ = OxmlElement("w:tblLayout")
        lay_.set(qn("w:type"), "fixed")
        pr.append(lay_)
        table.autofit = False

    def grid(table, widths):
        for i, wd in enumerate(widths):
            table.columns[i].width = Mm(wd)
            for cell in table.columns[i].cells:
                cell.width = Mm(wd)

    def para(text="", before=0, after=0, indent=0, bold=False, size=None):
        p = doc.add_paragraph()
        pf = p.paragraph_format
        pf.space_before, pf.space_after = Mm(before), Mm(after)
        if indent:
            pf.left_indent = Mm(indent)
        if text:
            run(p, text, bold=bold, size=size)
        return p

    if lay["info"] == "fi":
        # SFS 2487: the date in the head, in the fifth column (92 mm from the margin).
        # and the page number with the page count, 1 (2), in the last column (161 mm), on every page.
        ht = sec.header.add_table(rows=1, cols=3, width=Mm(usable))
        bare(ht)
        grid(ht, (92, FI_PAGE_COLUMN - 92, usable - FI_PAGE_COLUMN))
        head = ht.cell(0, 0).paragraphs[0]
        run(ht.cell(0, 1).paragraphs[0], lt.date_line(), size=10)
        number = ht.cell(0, 2).paragraphs[0]
        for instr, after in (("PAGE", " ("), ("NUMPAGES", ")")):
            fld = OxmlElement("w:fldSimple")
            fld.set(qn("w:instr"), instr)
            r = run(number, "1", size=10)
            fld.append(r._r)
            number._p.append(fld)
            run(number, after, size=10)
        hp = ht.cell(0, 0).add_paragraph()
        sec.header.paragraphs[0].paragraph_format.line_spacing = Pt(1)
    else:
        head = sec.header.paragraphs[0]
        hp = sec.header.add_paragraph()
    run(head, s["sender"]["name"], bold=True, size=15)
    run(hp, lt.letterhead(), size=7.5, grey=True)

    # The address in the envelope window: a first row as tall as the space above it, then the address.
    info_w = W - 125 - lay["right"] if lay["info"] == "right" else 0
    addr_w = letter.window_box(lay)[2] - ax
    lead = ax - lay["left"]                      # an empty column first when the address starts further in
    addr_w = min(addr_w, usable - max(lead, 0))  # a table wider than the text area is squeezed, and the address moves
    cols = ([lead] if lead > 0.5 else []) + [addr_w]
    at = len(cols) - 1
    rest = usable - sum(cols) - info_w
    cols += ([rest] if rest > 0.5 else []) + ([info_w] if info_w else [])
    top = doc.add_table(rows=2, cols=len(cols))
    bare(top)
    grid(top, cols)
    top.rows[0].height, top.rows[0].height_rule = Mm(ay - WORD_TOP), WD_ROW_HEIGHT_RULE.EXACTLY
    top.rows[1].height, top.rows[1].height_rule = Mm(wy + wh - ay), WD_ROW_HEIGHT_RULE.AT_LEAST
    first = top.cell(0, 0)
    if lay["info"] == "above":
        p = first.paragraphs[0]
        p.paragraph_format.space_before = Mm(lay["date_at"] - WORD_TOP)
        run(p, lt.date_line())
        for k, v in lt.refs():
            q = first.add_paragraph()
            run(q, k + " ", size=8.5, grey=True)
            run(q, v, size=8.5)
    addr = top.cell(1, at)
    for i, line in enumerate(lt.address()):
        p = addr.paragraphs[0] if i == 0 else addr.add_paragraph()
        p.paragraph_format.line_spacing = Mm(lay["line"])
        run(p, line)
    if info_w:
        cell = top.cell(1, len(cols) - 1)
        rows = lt.info_rows()
        block = cell.add_table(rows=len(rows), cols=2)
        bare(block)
        # The label column is as wide as the longest label needs (8.5 pt type), the values take the rest.
        label_w = max(12, min(23, 1.6 * max(len(k) for k, _ in rows) + 2))
        grid(block, (label_w, info_w - label_w))
        for i, (k, v) in enumerate(rows):
            run(block.cell(i, 0).paragraphs[0], k, size=8.5, grey=True)
            run(block.cell(i, 1).paragraphs[0], str(v), size=8.5)
        cell.paragraphs[0].paragraph_format.line_spacing = Pt(1)

    indent = lay["text_x"] - lay["left"]
    if lay["info"] == "refline":
        rows = [(lt.refs() + [(lt.w["date"], lt.date_line())])[:3]]
        if lt.contact_rows():
            rows.append(lt.contact_rows())
        for n, cols_ in enumerate(rows):
            t = doc.add_table(rows=2, cols=3)
            bare(t)
            grid(t, (usable / 3,) * 3)
            if n == 0:
                t.rows[0].cells[0].paragraphs[0].paragraph_format.space_before = Mm(4)
            for i, (k, v) in enumerate(cols_[:3]):
                p = t.cell(0, i).paragraphs[0]
                p.paragraph_format.space_before = Mm(4 if n == 0 else 2)
                run(p, k, size=7.5, grey=True)
                run(t.cell(1, i).paragraphs[0], v, size=9)
    elif lay["info"] == "fi":
        rows = lt.refs() + lt.contact_rows()
        if rows:
            t = doc.add_table(rows=len(rows), cols=2)
            bare(t)
            grid(t, (indent, usable - indent))
            for i, (k, v) in enumerate(rows):
                p = t.cell(i, 0).paragraphs[0]
                if i == 0:
                    p.paragraph_format.space_before = Mm(4)
                    t.cell(i, 1).paragraphs[0].paragraph_format.space_before = Mm(4)
                run(p, k, size=9, grey=True)
                run(t.cell(i, 1).paragraphs[0], v, size=9)

    gap = 8
    sal = (s.get("salutation"), 0, 4) if s.get("salutation") else None
    subj = (lt.subject_text(), 0, 5)
    seq = [sal, subj] if lt.subject_after_salutation() else [subj, sal]
    seq = [x for x in seq if x]
    for n, (text, b, a) in enumerate(seq):
        para(text, before=gap if n == 0 else 0, after=a, indent=indent, bold=(text == lt.subject_text()), size=11 if text == lt.subject_text() else None)
    for text in s["body"]:
        para(text, after=3.5, indent=indent)
    para(s["closing"], before=1.5, after=15, indent=indent)
    for line in lt.sign():
        para(line, indent=indent)
    if s.get("enclosures"):
        if lay["info"] == "fi":
            t = doc.add_table(rows=1, cols=2)
            bare(t)
            grid(t, (indent, usable - indent))
            p = t.cell(0, 0).paragraphs[0]
            p.paragraph_format.space_before = Mm(6)
            run(p, lt.enclosures_label(), bold=True, size=9.5)
            for i, x in enumerate(s["enclosures"]):
                q = t.cell(0, 1).paragraphs[0] if i == 0 else t.cell(0, 1).add_paragraph()
                if i == 0:
                    q.paragraph_format.space_before = Mm(6)
                run(q, x, size=9.5)
        else:
            p = para(before=6)
            run(p, lt.enclosures_label(), bold=True, size=9.5)
            for x in s["enclosures"]:
                q = para()
                run(q, x, size=9.5)

    foot = sec.footer.add_table(rows=1, cols=3, width=Mm(usable))
    bare(foot)
    # The middle column carries the company details and is the widest, as on the PDF (1 : 1.6 : 1).
    foot_w = (usable / 3.6, usable * 1.6 / 3.6, usable / 3.6)
    grid(foot, foot_w)
    for i, col in enumerate(lt.footer()):
        cell = foot.cell(0, i)
        cell.width = Mm(foot_w[i])
        for j, line in enumerate(col):
            run(cell.paragraphs[0] if j == 0 else cell.add_paragraph(), line, size=7, grey=True)
    doc.save(out)
    return "python-docx"
