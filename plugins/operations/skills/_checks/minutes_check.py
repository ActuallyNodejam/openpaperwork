#!/usr/bin/env python3
"""Checks for meeting minutes, from Robert's Rules of Order Revised (1915) section 60, public domain,
and for a company's board and general meeting from the statute of its country, outside copyright or
under an open licence: aktiebolagslagen 8 kap. 24-26 §§ (URL 9 §), aksjeloven §§ 6-29 and 5-16
(åndsverkloven § 14), selskabsloven §§ 128 and 101 (ophavsretsloven § 9), osakeyhtiölaki 6:6 and 5:23
(tekijänoikeuslaki 9 §), Companies Act 2006 ss.248-249 and 355-356 and the Model Articles (OGL v3),
Delaware General Corporation Law §§ 141 and 142, the Canada Business Corporations Act ss.20, 114 and
117 (Reproduction of Federal Law Order) and the Corporations Act 2001 s.251A (CC BY 4.0); and, wave 8,
the Belgian Code des sociétés et des associations / Wetboek van vennootschappen en verenigingen
(arts. 5:75, 5:76, 5:89, 5:90, 5:93 and their twins in books 6 and 7; official acts are outside
copyright, Code de droit économique art. XI.172), Burgerlijk Wetboek Boek 2 arts. 2:120 and 2:230
(Auteurswet art. 11), the Austrian Aktiengesetz §§ 92 and 120 and GmbH-Gesetz §§ 30g and 40
(Urheberrechtsgesetz § 7) and the Irish Companies Act 2014 ss.160, 161, 166 and 199 (Oireachtas (Open
Data) PSI Licence, CC BY 4.0); and, wave 9, the Spanish Ley de Sociedades de Capital arts. 192, 202, 203
and 250 and Reglamento del Registro Mercantil arts. 97 to 103 (legal texts are outside copyright, Ley de
Propiedad Intelectual art. 13), the Italian Codice civile arts. 2371, 2375, 2421, 2478 and 2479-bis
(official acts, legge 633/1941 art. 5) and the Polish Kodeks spółek handlowych arts. 208(1), 222, 248,
376, 391 and 421 (normative acts, ustawa o prawie autorskim art. 4).

  MINUTES-HEAD      The minutes name the body that met, the kind of meeting and the date.
  MINUTES-OFFICERS  The chair and the secretary are named.
  MINUTES-MOTIONS   Every main motion is recorded with its mover and its result.
  MINUTES-TIMES     The time the meeting opened and the time it was adjourned.
  MINUTES-SIGNED    The secretary signs; a company's minutes carry the signatures its law asks for:
                    every director present (Norway, Denmark), the chair and a checker (Finland, a
                    Norwegian general meeting), the dirigent (a Danish general meeting), the chair
                    (United Kingdom, Australia, Ireland; a Belgian board; an Austrian supervisory
                    board), the bureau (a Belgian general meeting), every director (an Irish written
                    resolution), and in Sweden the chair and checker justerar. In Spain the secretary
                    with the chair's visto bueno, and every member at a junta universal; the chair and
                    the secretary of an Italian S.p.A.'s assembly; in Poland the chair and the
                    minute-taker of a shareholders' meeting and the member who chaired a board.
  MINUTES-STATUTE   What the law asks a company's minutes to hold besides: in Norway the time and
                    place, the participants, how the board dealt with the matter and who voted for
                    and against a split decision; the shareholders' list at a Norwegian or Finnish
                    general meeting; the number in sequence on a Finnish or Swedish board's minutes;
                    a recorded dissent; the quorum where the board may act only with one. In Belgium
                    the attendance list of a general meeting and a director's declared conflict of
                    interest; in the Netherlands every resolution a general meeting adopts; in Austria
                    the day a GmbH's resolutions were entered in the Niederschrift; in Ireland the
                    directors present. In Spain the place, how and when the meeting was called, who
                    came (the list of those attending inside an S.L.'s acta), the share of the capital
                    present, the votes on each resolution and the acta's approval; at an Italian
                    S.p.A.'s assembly who took part with what capital, how the votes were cast, their
                    result and who dissented or abstained, and the chair's findings; in Poland that the
                    shareholders' meeting was properly called and can resolve, the votes for each
                    resolution, the attendance list, and for a board the agenda, the members present
                    and the votes. A rule cites the article it enforces; where a statute sets
                    nothing (a Dutch or Italian board) or has a notary record the meeting (an Austrian
                    AG, an Italian extraordinary assembly, a Polish S.A., a Spanish junta a notary was
                    called to) it says so and passes nothing.
  MINUTES-LANGUAGE  Labels, headings and signature roles are all in the minutes' language.

With a minutes spec beside the file (skills/meeting-minutes) every rule compares the file with it;
without one, the head, the times and the signature are read from the text alone.
check(rule_id, path, case, stage) -> (passed, evidence); passed is None when the rule does not apply.
"""
import html
import importlib.util
import json
import re
import sys
import zipfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "_shared"))
import letter  # noqa: E402

RESULTS = {"adopted": ("adopted", "carried", "bifölls", "antogs", "vedtatt", "vedtaget", "hyväksyttiin", "adoptée",
                       "aangenomen", "angenommen", "aprobada", "approvata", "przyjęto"),
           "lost": ("lost", "rejected", "avslogs", "ikke vedtatt", "forkastet", "hylättiin", "rejetée", "verworpen",
                    "abgelehnt", "rechazada", "respinta", "odrzucono"),
           "withdrawn": ("withdrawn", "drogs tillbaka", "trukket", "peruttiin", "retirée", "ingetrokken",
                         "zurückgezogen", "retirada", "ritirata", "wycofano")}
SECRETARY = ("secretary", "vid protokollet", "protokollförare", "sekreterare", "protokollfører", "referent",
             "sihteeri", "secrétaire", "notulist", "secretaris", "schriftführ", "secretar", "segretari", "protokolant")
CHECKED = ("justeras",)
KINDS = ("meeting", "möte", "stämma", "sammanträde", "møte", "møde", "generalforsamling", "kokous", "kokouks",
         "yhtiökokou", "réunion", "assemblée", "vergadering", "sitzung", "versammlung",
         "reunión", "junta", "riunione", "assemblea", "zebrani", "zgromadzeni", "posiedzeni")
MONTHS = ("january|february|march|april|may|june|july|august|september|october|november|december|"
          "januari|februari|mars|maj|juni|juli|augusti|oktober|"
          "januar|februar|marts|mai|desember|"
          "janvier|février|avril|juin|juillet|août|septembre|octobre|novembre|décembre|"
          "maart|mei|augustus|jänner|märz|dezember")
DATE = re.compile(r"\b(\d{4}-\d{2}-\d{2}|\d{1,2}\.\d{1,2}\.\d{4}|(%s) \d{1,2}, \d{4}|\d{1,2}(er)?\.? (%s) \d{4})\b"
                  % (MONTHS, MONTHS), re.I)
TIME = re.compile(r"\b([01]?\d|2[0-3])(?:[:.]| h )([0-5]\d)\b")
GENERAL = ("annual general", "extraordinary general", "general")


def builder():
    """The minutes builder beside this check, for its locales and words; None outside the skills tree."""
    path = HERE.parent / "meeting-minutes" / "scripts" / "minutes_create.py"
    if not path.is_file():
        return None
    spec = importlib.util.spec_from_file_location("_minutes_builder", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def spec_beside(path):
    for p in sorted(Path(path).parent.glob("*.json")):
        try:
            data = json.loads(p.read_text())
        except (ValueError, OSError):
            continue
        if isinstance(data, dict) and isinstance(data.get("items"), list) and data.get("meeting"):
            return data
    return None


def text_of(path):
    with zipfile.ZipFile(path) as z:
        xml = z.read("word/document.xml").decode("utf-8", "replace")
    paras = re.findall(r"<w:p[ >].*?</w:p>", xml, re.S)
    return [re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", "", p.replace("<w:br/>", " ")))).strip() for p in paras]


def norm(s):
    return re.sub(r"\s+", " ", str(s).replace(" ", " ")).strip().lower()


def times_of(value):
    h, m = re.match(r"^(\d{1,2})[:.](\d{2})$", str(value)).groups()
    out = {"%s:%s" % (h, m), "%s.%s" % (h, m), "%s:%s" % (h.zfill(2), m), "%s.%s" % (h.zfill(2), m)}
    # The United States writes 6:30 p.m. (GPO Style Manual); Canadian French 18 h 30, and 18 h for the hour.
    out.add("%d:%s %s" % (int(h) % 12 or 12, m, "a.m." if int(h) < 12 else "p.m."))
    out.add("%d h %s" % (int(h), m))
    if m == "00":
        out.add("%d h" % int(h))
    return out


def locale_and_law(spec, flat):
    """(locale, country, kind) for the minutes: the builder's own reading of the spec when it is here."""
    b = builder()
    if spec and b:
        loc = b.locale_of(spec)
        return loc, b.country_of(spec, loc), b.kind_of(spec)
    sv = bool(spec and str(spec.get("language", "")).lower().startswith("sv")) or "protokoll fört" in flat
    loc = "sv-SE" if sv else "en-GB"
    kind = (spec or {}).get("meeting")
    return loc, ("SE" if sv and kind == "board" else ""), ("general" if kind in GENERAL else kind)


def date_forms(value, loc):
    forms = {norm(value), norm(letter.date(value, loc))}
    if hasattr(letter, "long_date"):
        forms.add(norm(letter.long_date(value, loc)))
    return forms


def statute_signers(spec, cc, kind):
    """(law, [names that must sign], problem) for a company's minutes; law None when no statute names signers."""
    chair, present = spec.get("chair"), list(spec.get("present") or [])
    checkers = list(spec.get("checkers") or [])
    written = spec.get("method") == "written"
    if cc in ("NO", "DK") and kind == "board":
        law = "aksjeloven § 6-29 (1)" if cc == "NO" else "selskabsloven § 128"
        names = present or [chair]
        if cc == "NO" and len(names) >= 5 and len(spec.get("signers") or []) >= 2:
            names = list(spec["signers"])
        return law, names, None
    if cc == "NO" and kind == "general":
        return "aksjeloven § 5-16 (2)", [chair] + checkers, (None if checkers else
                "the meeting picks at least one person among those present to sign with the chair (checkers)")
    if cc == "DK" and kind == "general":
        return "selskabsloven § 101 (3)", [chair], None
    if cc == "FI" and kind in ("board", "general"):
        law = "osakeyhtiölaki 6:6" if kind == "board" else "osakeyhtiölaki 5:23"
        needs_checker = kind == "general" or len(present) > 1
        return law, [chair] + checkers, (None if checkers or not needs_checker else
                                         "the chair signs with at least one checker the %s picks (checkers)"
                                         % ("board" if kind == "board" else "meeting"))
    if cc in ("GB", "AU") and kind in ("board", "general"):
        law = {"GB": "Companies Act 2006 s.249 and s.356", "AU": "Corporations Act 2001 s.251A(2)"}[cc]
        return law, [chair], None
    if cc in ("US", "CA") and kind == "board" and written:
        law = "DGCL § 141(f)" if cc == "US" else "CBCA s.117(1)"
        return law, present, None
    b = builder()
    if cc == "IE" and kind == "board" and written:
        # A resolution in writing signed by all the directors is as valid as one passed at a meeting.
        return "Companies Act 2014 s.161(1)", present or [chair], None
    if cc == "IE" and kind in ("board", "general"):
        return "Companies Act 2014 %s" % ("s.166(3)" if kind == "board" else "s.199(3)"), [chair], None
    if cc == "BE" and kind == "board" and b:
        # The chair signs, and the directors who ask to.
        return b.be_article(spec, "board"), [chair], None
    if cc == "BE" and kind == "general" and b:
        # The members of the bureau sign: the chair, the secretary and the vote counters.
        bureau = [chair] + [n for n in [spec.get("secretary")] + checkers if n and n != chair]
        return b.be_article(spec, "general"), bureau, None
    if cc == "AT" and kind == "board" and b:
        # The supervisory board's Niederschrift is signed by its chair or the deputy who chaired.
        return b.at_law(spec, "board"), [chair], None
    if cc in ("ES", "IT", "PL") and kind in ("board", "general") and b and not b.notarial(spec):
        secretary = spec.get("secretary")
        both = [chair] + ([secretary] if secretary and secretary != chair else [])
        if cc == "ES":
            # The secretary signs with the visto bueno of whoever chaired; at a junta universal every member
            # signs after their name.
            if kind == "board":
                return "LSC art. 250 and RRM art. 99.3", both, None
            if spec.get("universal"):
                rows = [r.get("name") for r in spec.get("shareholders") or [] if r.get("name")]
                return "RRM arts. 97.1 4.ª and 99.3", both + [n for n in rows if n not in both], (
                    None if rows else "a junta universal's acta names everyone there, each followed by a signature; "
                                      "the spec gives no shareholders")
            return "RRM art. 99.3", both, None
        if cc == "IT" and kind == "general" and b.bare_form(spec) in ("SPA", "SAPA"):
            return "Codice civile art. 2375", both, None
        if cc == "PL" and kind == "general":
            # Those present sign, or at least the chair and whoever drew up the protocol.
            return "KSH art. 248 § 1", both, None
        if cc == "PL" and kind == "board":
            # At least the member who chaired the meeting or ordered the vote.
            return b.pl_law(spec, "board"), [chair], None
    return None, [], None


def southern(spec, cc, kind, form, loc, b, has, decisions, bad):
    """What the Spanish, Italian and Polish statutes ask a company's minutes to hold; appends to bad and
    returns the law the evidence names. Each line cites the article it enforces."""
    w = b.WORDS.get(loc) or {}
    rows = spec.get("shareholders") or []

    def counted(d, heads=False):
        return bool(d.get("votes")) or (bool(d.get("unanimous")) and b.voters(spec) > 0) or (
            heads and any(isinstance(d.get(k), list) for k in ("for", "against")))

    def votes(law, heads=False):
        for d in decisions:
            if not counted(d, heads):
                bad.append("%s asks for the votes on each resolution; %r gives none (votes, or unanimous with %s)" % (
                    law, d["text"][:40], "the members present" if heads else "the votes on the attendance list"))
            elif w.get("tally"):
                missing = [t for _, t in b.tally_lines(spec, d, w, loc) if not has(t)]
                if missing:
                    bad.append("the vote on %r is not on the minutes (%s)" % (d["text"][:40], missing[0][:70]))

    def listed(law, inside=False):
        if not rows and (inside or not spec.get("shareholders_attached")):
            bad.append("%s; the spec gives none (shareholders%s)" % (law, "" if inside else ", or shareholders_attached"))
        missing = [r.get("name") for r in rows if not has(r.get("name", ""))]
        if missing:
            bad.append("not on the attendance list: %s" % ", ".join(missing[:3]))

    def quorum(law, what):
        if not spec.get("quorum"):
            bad.append("%s has the minutes state %s (quorum: true)" % (law, what))
        elif w.get("quorum") and not has(w["quorum_board"] if kind == "board" and w.get("quorum_board") else w["quorum"]):
            bad.append("%s: that %s is not on the minutes" % (law, what))

    if cc == "ES":
        rrm = "Reglamento del Registro Mercantil art. 97.1"
        if not spec.get("place"):
            bad.append("%s 1.ª asks for the place of the meeting; the spec gives none" % rrm)
        elif not has(spec["place"]):
            bad.append("the place is not given (%s 1.ª)" % rrm)
        universal = kind == "general" and spec.get("universal")
        if not universal:
            c = spec.get("convened")
            if not c:
                bad.append("%s 2.ª asks for the day and the way the meeting was called; the spec gives none (convened)" % rrm)
            elif isinstance(c, dict) and c.get("date") and not any(d in has.flat for d in date_forms(c["date"], loc)):
                bad.append("the day the meeting was called is not on the minutes (%s 2.ª)" % rrm)
        if kind == "board":
            if not spec.get("present"):
                bad.append("%s 4.ª asks for the names of the members who came; the spec gives none (present)" % rrm)
            for who in list(spec.get("present") or []) + [r.get("name") for r in spec.get("represented") or []]:
                if who and not has(who):
                    bad.append("the member %s is not named (%s 4.ª)" % (who, rrm))
            votes("%s 7.ª" % rrm, heads=True)
        else:
            if form in ("SL", "SLU", "SRL") or universal:
                listed("LSC art. 192.3 puts the list of those attending inside a limited company's acta" if not universal
                       else "%s 4.ª has a junta universal's acta name everyone there" % rrm, inside=True)
            else:
                listed("%s keeps the list of those attending at the head of the acta or attached to it" % rrm.replace("97.1", "98"))
            if rows and not spec.get("total_shares"):
                bad.append("%s 4.ª asks for the share of the capital those present and represented hold; the spec gives "
                           "no total_shares to work it out" % rrm)
            elif rows and w.get("attendance") and not has(b.attendance(spec, w, loc)):
                bad.append("how many came in person and by proxy, with their share of the capital, is not on the minutes (%s 4.ª)" % rrm)
            votes("%s 7.ª" % rrm)
        if w.get("approved_end"):
            a = spec.get("minutes_approved")
            want = (w["approved_later"] % {"date": b.date_of(a["date"], loc), "how": str(a.get("how") or "").rstrip(".")}
                    if isinstance(a, dict) and a.get("date") else w["approved_end"])
            if not has(want):
                bad.append("the acta's approval is not recorded (%s 8.ª and art. 99)" % rrm)
        return "LSC art. 250 and RRM art. 97" if kind == "board" else "LSC arts. 192 and 202 and RRM arts. 97 to 99"
    if cc == "IT":
        if form in ("SPA", "SAPA"):
            law = "Codice civile art. 2375"
            listed("%s has the verbale name those taking part and the capital each stands for, in it or attached" % law)
            if not spec.get("voting"):
                bad.append("%s asks how the votes were cast; the spec gives none (voting)" % law)
            elif not has(str(spec["voting"]).rstrip(".")):
                bad.append("how the votes were cast is not on the minutes (%s)" % law)
            votes(law)
            for d in decisions:
                v = d.get("votes") or {}
                if (v.get("against") or v.get("abstained")) and not (isinstance(d.get("against"), list) or isinstance(d.get("abstained"), list)
                                                                      or d.get("voters_attached")):
                    bad.append("%s has the verbale let one tell who was for, who abstained and who dissented; %r names "
                               "nobody (against, abstained, or voters_attached)" % (law, d["text"][:40]))
                for k in ("against", "abstained"):
                    for who in d.get(k) if isinstance(d.get(k), list) else []:
                        if not has(who):
                            bad.append("%s is not named among those who %s (%s)" % (who, "dissented" if k == "against" else "abstained", law))
            quorum("Codice civile art. 2371", "the chair's findings on the assembly's constitution and on who was there")
            return "Codice civile arts. 2371 and 2375"
        law = "Codice civile art. 2479-bis"
        quorum(law, "the chair's findings on the assembly's constitution and on who was there")
        votes(law)
        return law
    law = b.pl_law(spec, "general" if kind == "general" else "board")
    if kind == "general":
        quorum("KSH art. 248 § 2", "that the meeting was properly called and can adopt resolutions")
        votes("KSH art. 248 § 2")
        listed("KSH art. 248 § 2 attaches the attendance list with the signatures of those taking part")
        if not rows and spec.get("shareholders_attached") and w.get("attached") and not has(w["attached"]):
            bad.append("that the attendance list is attached is not on the minutes (KSH art. 248 § 2)")
        return law
    if w.get("agenda") and not has(w["agenda"]):
        bad.append("%s asks for the agenda (porządek obrad); it is not on the minutes" % law)
    if not spec.get("present"):
        bad.append("%s asks for the names of the members present; the spec gives none (present)" % law)
    for who in spec.get("present") or []:
        if not has(who):
            bad.append("the member %s is not named as present (%s)" % (who, law))
    votes(law, heads=True)
    return law


def check(rule_id, path, case, stage):
    path = Path(path)
    if path.suffix.lower() != ".docx":
        return None, "minutes are checked as Word files"
    paras = text_of(path)
    flat = norm(" ".join(paras))
    truth = case.get("truth") or {}
    spec = spec_beside(path) or (truth if truth.get("items") else None)
    loc, cc, kind = locale_and_law(spec, flat)
    sv = loc == "sv-SE"
    if rule_id == "MINUTES-HEAD":
        bad = []
        if spec:
            if norm(spec["body"]) not in flat:
                bad.append("the body %r is not named" % spec["body"])
            if not any(d in flat for d in date_forms(spec["date"], loc)):
                bad.append("the date %s is not given" % spec["date"])
        elif not DATE.search(flat):
            bad.append("no date")
        if not any(k in flat for k in KINDS):
            bad.append("the kind of meeting is not said")
        return (not bad, "; ".join(bad) or "body, kind of meeting and date are given")
    if rule_id == "MINUTES-OFFICERS":
        if not spec:
            return None, "no minutes spec beside the file names the officers"
        bad = [who for who in (spec["chair"], spec["secretary"]) if norm(who) not in flat]
        return (not bad, "chair and secretary named" if not bad else "not named: %s" % ", ".join(bad))
    if rule_id == "MINUTES-MOTIONS":
        if not spec:
            return None, "no minutes spec beside the file lists the motions"
        bad, n = [], 0
        for item in spec["items"]:
            for m in item.get("motions", []):
                n += 1
                words = RESULTS.get(m.get("result", ""), (m.get("result", ""),))
                found = [p for p in paras if norm(m["mover"]) in norm(p) and any(w in norm(p) for w in words)]
                if not found:
                    bad.append("%s's motion %r without its mover and result" % (m["mover"], m["text"][:40]))
                elif m.get("votes"):
                    want = [str(m["votes"].get(k)) for k in ("for", "against") if m["votes"].get(k) is not None]
                    if not any(all(re.search(r"\b%s\b" % v, p) for v in want) for p in found):
                        bad.append("%s's motion without its vote count" % m["mover"])
        if not n:
            return None, "no motions"
        return (not bad, "; ".join(bad[:3]) or "%d motions with mover and result" % n)
    if rule_id == "MINUTES-TIMES":
        if spec and spec.get("start") and spec.get("end"):
            bad = [t for t in (spec["start"], spec["end"]) if not any(x in flat for x in times_of(t))]
            return (not bad, "opened and adjourned times given" if not bad else "times missing: %s" % ", ".join(bad))
        found = TIME.findall(flat)
        return (len(found) >= 2, "two times found" if len(found) >= 2 else "the opening and adjournment times are not both given")
    if rule_id == "MINUTES-SIGNED":
        tail = norm(" ".join(paras[-12:]))
        lines_ = [norm(p) for p in paras if "____" in p]
        signed = " | ".join(lines_) or tail
        bad = []
        law, names, problem = statute_signers(spec, cc, kind) if spec else (None, [], None)
        if law:
            if problem:
                bad.append("%s: %s" % (law, problem))
            for who in names:
                if norm(who) not in signed:
                    bad.append("%s asks %s to sign; there is no signature line with the name" % (law, who))
            if not lines_:
                bad.append("no signature lines")
            return (not bad, "; ".join(bad) or "signed as %s asks: %s" % (law, ", ".join(names)))
        if not any(k in signed or k in tail for k in SECRETARY):
            bad.append("no signature line for the secretary")
        if spec and norm(spec["secretary"]) not in (signed + " " + tail):
            bad.append("the secretary's name is not under the signature")
        if sv and spec and spec.get("meeting") == "board":
            if not any(k in tail for k in CHECKED):
                bad.append("a board's minutes are checked (justeras) by the chair, aktiebolagslagen 8:24")
            for who in [spec["chair"]] + list(spec.get("checkers", [])):
                if norm(who) not in tail:
                    bad.append("%s does not check the minutes" % who)
        return (not bad, "; ".join(bad) or "signed as the rules ask")
    if rule_id == "MINUTES-STATUTE":
        if not spec or not cc or kind not in ("board", "general"):
            return None, "not a company's board or general meeting under a statute the library covers"
        bad, law = [], {"NO": "aksjeloven", "DK": "selskabsloven", "FI": "osakeyhtiölaki", "SE": "aktiebolagslagen",
                        "GB": "Companies Act 2006", "US": "DGCL", "CA": "CBCA", "AU": "Corporations Act 2001",
                        "BE": "the Belgian companies code", "NL": "Boek 2 BW", "AT": "the Austrian company law",
                        "IE": "Companies Act 2014", "ES": "the Ley de Sociedades de Capital",
                        "IT": "the Codice civile", "PL": "the Kodeks spółek handlowych"}.get(cc, cc)
        b = builder()
        form = b.form_of(spec).upper() if b else ""
        if cc == "NL" and kind == "board":
            return None, "Boek 2 BW sets no contents for a board's minutes; the company's articles do"
        if cc == "AT" and kind == "general" and form in ("AG", "SE"):
            return None, ("AktG § 120: a notary records an Aktiengesellschaft's general meeting; this file is not "
                          "that Niederschrift, so nothing in it is checked against the statute")
        if cc in ("ES", "IT", "PL") and b:
            by_notary = b.notarial(spec)
            if by_notary:
                return None, "%s: %s; this file is not that record, so nothing in it is checked against the statute" % by_notary
            if cc == "IT" and kind == "board":
                return None, ("the Codice civile sets no contents for a board's verbale; arts. 2421 and 2478 ask only "
                              "that it be entered in the company's book")

        def has(value):
            return norm(value) in flat
        has.flat = flat

        decisions = [d if isinstance(d, dict) else {"text": d} for i in spec["items"] for d in i.get("decisions", [])]
        for d in decisions:
            if not has(d["text"].rstrip(".")):
                bad.append("the decision %r is not recorded" % d["text"][:50])
        for i in spec["items"]:
            for d in i.get("dissent", []):
                if not (has(d["name"]) and has(d["text"].rstrip("."))):
                    bad.append("%s's dissent is not recorded, as %s lets a director ask" % (d["name"], law))
        if cc == "NO" and kind == "board":
            # § 6-29 (1): time and place, the participants, how the matter was dealt with, the decisions,
            # and who voted for and against when the board was split.
            for what, value in (("the place", spec.get("place")), ("the start time", spec.get("start"))):
                if not value:
                    bad.append("aksjeloven § 6-29 asks for %s; the spec gives none" % what)
            if spec.get("place") and not has(spec["place"]):
                bad.append("the place is not given")
            if "behandlingsmåte" not in flat:
                bad.append("aksjeloven § 6-29 asks how the board dealt with the matter (Behandlingsmåte)")
            for who in spec.get("present") or []:
                if not has(who):
                    bad.append("the participant %s is not named" % who)
            for d in decisions:
                if d.get("against") and not all(has(n) for n in list(d.get("against")) + list(d.get("for") or [])):
                    bad.append("a split decision names who voted for and against (§ 6-29 (1))")
        if cc in ("NO", "FI") and kind == "general":
            # aksjeloven § 5-16 (1), osakeyhtiölaki 5:23: the list of shareholders goes in or is attached.
            rows = spec.get("shareholders") or []
            if not rows and not spec.get("shareholders_attached"):
                bad.append("%s puts the list of shareholders present in the minutes or attaches it; the spec gives "
                           "none (shareholders, or shareholders_attached)" % ("aksjeloven § 5-16" if cc == "NO" else "osakeyhtiölaki 5:23"))
            missing = [r.get("name") for r in rows if not has(r.get("name", ""))]
            if missing:
                bad.append("not in the shareholders' list: %s" % ", ".join(missing[:3]))
            if cc == "NO" and "møteform" not in flat:
                bad.append("aksjeloven § 5-16 asks for the form of the meeting (Møteform)")
        if cc in ("FI", "SE") and kind == "board":
            # osakeyhtiölaki 6:6, aktiebolagslagen 8:26: minutes numbered in sequence.
            if not spec.get("number"):
                bad.append("%s numbers the board's minutes in sequence; the spec gives no number" % law)
            elif not has(spec["number"]):
                bad.append("the minutes number %s is not on the minutes" % spec["number"])
        if cc == "BE" and b:
            if kind == "general":
                # art. 5:90, 6:76, 7:138: an attendance list is kept at every general meeting.
                rows = spec.get("shareholders") or []
                if not rows and not spec.get("shareholders_attached"):
                    bad.append("%s keeps an attendance list at every general meeting; the spec gives none "
                               "(shareholders, or shareholders_attached)" % b.be_article(spec, "list"))
                missing = [r.get("name") for r in rows if not has(r.get("name", ""))]
                if missing:
                    bad.append("not on the attendance list: %s" % ", ".join(missing[:3]))
                # art. 5:89, 6:75, 7:137: technical problems that hindered taking part online are mentioned.
                if spec.get("incidents") and not has(str(spec["incidents"]).rstrip(".")):
                    bad.append("%s asks the minutes to mention the technical problems; they are not there"
                               % b.be_article(spec, "remote"))
            for i in spec["items"]:
                for d in i.get("conflict", []):
                    # art. 5:76, 6:64, 7:96: the director's declaration and explanation go in the minutes.
                    if not (has(d["name"]) and has(d["text"].rstrip("."))):
                        bad.append("%s's conflict of interest is not recorded (%s)" % (d["name"], b.be_article(spec, "conflict")))
            law = b.be_article(spec, "general" if kind == "general" else "board")
        if cc == "NL" and kind == "general":
            # The board keeps a record of the resolutions the general meeting adopts (the loop above).
            law = "BW art. 2:120 lid 4" if form == "NV" else "BW art. 2:230 lid 4"
        if cc == "AT" and b:
            law = b.at_law(spec, kind)
            if kind == "general":
                # GmbHG § 40: resolutions entered without delay; every copy states the day they were entered.
                if not spec.get("recorded"):
                    bad.append("GmbHG § 40 (2) has the copy sent to every shareholder state the day the resolutions "
                               "were entered in the Niederschrift; the spec gives none (recorded)")
                elif not any(d in flat for d in date_forms(spec["recorded"], loc)):
                    bad.append("the day the resolutions were entered in the Niederschrift is not on it (GmbHG § 40)")
        if cc in ("ES", "IT", "PL") and b:
            law = southern(spec, cc, kind, form.replace(" ", ""), loc, b, has, decisions, bad)
        if cc == "IE" and kind == "board":
            # s.166(1)(b): the names of the directors present at each meeting of the directors.
            law = "Companies Act 2014 s.166"
            if not spec.get("present"):
                bad.append("Companies Act 2014 s.166(1)(b) asks for the names of the directors present; the spec gives none (present)")
            for who in spec.get("present") or []:
                if not has(who):
                    bad.append("the director %s is not named as present (s.166(1)(b))" % who)
        if cc == "IE" and kind == "general":
            law = "Companies Act 2014 s.199"
        if cc in ("GB", "US", "CA", "AU", "IE") and kind == "board" and spec.get("method") != "written":
            # The board may act only with a quorum: Model Articles art. 11, DGCL § 141(b), CBCA s.114(2),
            # Corporations Act s.248F, Companies Act 2014 s.160(6). The minutes say it was there.
            if not spec.get("quorum"):
                bad.append("say whether a quorum was present (quorum: true); the board may act only with one")
            elif "quorum" not in flat:
                bad.append("the quorum is not recorded")
        return (not bad, "; ".join(bad[:4]) or "what %s asks the minutes to hold is there" % law)
    if rule_id == "MINUTES-LANGUAGE":
        b = builder()
        if not b or not spec:
            return None, "no minutes spec and builder to read the language from"
        own = b.WORDS.get(loc) or {}

        def labels(words):
            out = set()
            for k, v in words.items():
                if isinstance(v, str) and "%" not in v and len(v) < 40:
                    out.add(norm(v))
                elif isinstance(v, dict):
                    out |= {norm(x) for x in v.values() if isinstance(x, str) and "%" not in x and len(x) < 40}
                elif isinstance(v, (list, tuple)):
                    out |= {norm(x) for x in v if isinstance(x, str) and len(x) < 60}
            return out
        mine = labels(own)
        theirs = set()
        for tag, words in b.WORDS.items():
            if words is not own:
                theirs |= labels(words)
        theirs -= mine
        values = norm(json.dumps(spec, ensure_ascii=False))
        theirs = {t for t in theirs if t and t not in values and len(t) > 2}
        found = []
        for p in paras:
            q = norm(p).rstrip(":").strip()
            if len(q) > 60:
                continue
            for t in theirs:
                if q == t or ("____" in p and q.endswith(" " + t)):
                    found.append(p.strip())
        return (not found, "labels in %s throughout" % loc if not found
                else "labels not in %s: %s" % (loc, "; ".join(sorted(set(found))[:4])))
    return None, "unknown rule"


if __name__ == "__main__":
    for rule in ("MINUTES-HEAD", "MINUTES-OFFICERS", "MINUTES-MOTIONS", "MINUTES-TIMES", "MINUTES-SIGNED",
                 "MINUTES-STATUTE", "MINUTES-LANGUAGE"):
        print(rule, check(rule, sys.argv[1], {}, "first"))
