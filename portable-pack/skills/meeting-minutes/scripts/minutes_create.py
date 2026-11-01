#!/usr/bin/env python3
"""Write meeting minutes or a company's board or general-meeting minutes as Word, from a JSON spec.

Usage: minutes_create.py spec.json minutes.docx

Spec (templates/ has one for each kind and country):
{
  "language": "en",                      # en, sv, nb, da, fi, nl, de, es, it, pl or fr; "fr" writes Canadian
                                          # French, Belgian French when the country is BE
  "country": "GB",                        # the law the company is under: SE NO DK FI GB US CA AU BE NL AT
                                          # IE ES IT PL; leave out for a club, an association or a school meeting
  "body": "Example Analytics Ltd",      # who met
  "company_number": "01234567",           # the register number, printed under the title
  "meeting": "board",                     # board, annual general, extraordinary general, general, or a
                                          # club's regular, special or adjourned meeting
  "method": "meeting",                    # meeting, video, hybrid or written (Norway asks for it)
  "number": "7/2026",                     # minutes number; numbered in sequence for a Nordic board
  "date": "2026-10-14", "start": "18:30", "end": "20:05", "place": "...",
  "chair": "...", "secretary": "...", "checkers": ["..."],
  "present": ["..."],                     # for a board: the directors present; they sign in NO and DK
  "signers": ["...", "..."],              # Norway: the two directors a board of five or more picks to sign
  "in_attendance": ["... (CEO)"],         # others there who are not members
  "absent": ["..."],
  "quorum": true,                         # say a quorum was present
  "previous_minutes": "approved",         # approved, approved as corrected, or leave out
  "shareholders": [{"name": "...", "shares": 600, "votes": 600, "by": "proxy name"}],  # general meetings
  "items": [
    {"title": "...", "notes": "Optional: what was reported, in one or two sentences.",
     "motions": [{"text": "that ...", "mover": "...", "result": "adopted", "votes": {"for": 9, "against": 2, "abstained": 1}}],
     "decisions": ["that ...", {"text": "that ...", "for": ["A", "B"], "against": ["C"]}],
     "dissent": [{"name": "...", "text": "against the new lease"}],
     "conflict": [{"name": "...", "text": "she owns the building the company would rent"}]}   # Belgium
  ],
  "recorded": "2026-10-21",               # Austria, a GmbH's general meeting: the day the resolutions were
                                          # entered in the Niederschrift (GmbHG § 40)
  "incidents": "...",                     # Belgium: technical problems that kept shareholders from taking
                                          # part or voting online
  "notary": "...",                        # Austria, an AG's general meeting: the notary who records it
  "convened": {"date": "2026-10-01", "how": "..."},   # Spain: the day and the way the meeting was called
  "universal": true,                      # Spain: a junta universal, every member there and agreed to meet
  "represented": [{"name": "...", "by": "..."}],     # Spain, a board: the directors another director stood for
  "total_shares": 3000,                   # Spain: the company's shares in all, for the share of capital present
  "minutes_approved": {"date": "...", "how": "..."},  # Spain: when the acta was not approved at the meeting's end
  "voting": "...",                        # Italy: how the votes were cast (voto palese per alzata di mano)
  "shareholders_attached": true,          # the attendance list is attached, not written in
  "organ": "supervisory",                 # Poland: the supervisory board (rada nadzorcza), not the management board
  "titles": {"chair": "Presidenta", "secretary": "Secretario"},  # the chair's and the secretary's own titles
  "notice_approved": true,                # Norway, a general meeting: the notice and the agenda were approved
  "notes": ["Notice of the meeting was given to every director on 1 October 2026."]
                                          # a fact about the meeting as a whole that has no field of its own: one
                                          # line each, printed as written before the first item of business
}
Every key the builder reads is in spec.fields.json beside SKILL.md. A key that is not there, or a value of another
shape, stops the build with the key's name (skills/_shared/spec_guard.py): nothing given is left off the page.
An item's "notes" may be one string or a list of paragraphs. "previous_minutes" in other words than "approved" or
"approved as corrected" is printed as written.
A decision may carry its count: {"text": "...", "votes": {"for": 3, "against": 0, "abstained": 0}}, or
"unanimous": true, or the names in "for", "against" and "abstained".

Where each part comes from:
- What minutes record: Robert's Rules of Order Revised (1915), section 60, public domain: the kind of
  meeting, the body, the date and place, the chair and secretary, the previous minutes, every main
  motion with its mover and its result, counted votes, the time of adjournment, and the secretary's
  signature. What was said is left out; what was done is kept.
- Sweden: aktiebolagslagen 8 kap. 24 och 26 §§ (board), 7 kap. 48 § (general meeting).
- Norway: aksjeloven § 6-29 (board: time and place, the participants, how the board dealt with the
  matter, the decisions, who voted for and against when not unanimous, signed by every director who
  took part, or by two a board of five or more picks; a dissent recorded on request) and § 5-16
  (general meeting: the time and form of the meeting, each decision with the vote, the list of
  shareholders put in or attached, signed by the chair and one person the meeting picks).
- Denmark: selskabsloven § 128 (board: a protocol signed by every director present; a dissent
  recorded on request) and § 101 (general meeting: a protocol signed by the dirigent).
- Finland: osakeyhtiölaki 6 luku 6 § (board: the chair and at least one director the board picks
  sign, a dissent recorded, minutes numbered in sequence) and 5 luku 23 § (general meeting: the
  voting list put in or attached, the decisions and votes, signed by the chair and one minutes
  checker the meeting elects).
- United Kingdom: Companies Act 2006 s.248 and s.355 (minutes kept ten years), s.249 and s.356
  (minutes signed by the chair are evidence); Model Articles (private) art. 11 (quorum).
- United States: Delaware General Corporation Law § 142(a) (an officer records the proceedings),
  § 141(b) (quorum); the minutes themselves on Robert's Rules (1915) section 60.
- Canada: Canada Business Corporations Act s.20 (minutes kept), s.117 (written resolutions kept with
  them), s.114 (quorum); English and French.
- Australia: Corporations Act 2001 s.251A (minutes recorded within one month and signed by the chair
  within a reasonable time).
- Belgium: Code des sociétés et des associations / Wetboek van vennootschappen en verenigingen: the
  board's minutes signed by the chair and any director who asks (art. 5:75 BV/SRL, 6:63 CV/SC, 7:95
  NV/SA), a director's conflict of interest recorded in them (art. 5:76, 6:64, 7:96); an attendance list
  at every general meeting (art. 5:90, 6:76, 7:138), its minutes signed by the bureau and any
  shareholder who asks (art. 5:93, 6:79, 7:141), and the technical problems that kept people from
  taking part online (art. 5:89, 6:75, 7:137). Dutch and French.
- Netherlands: Burgerlijk Wetboek Boek 2 art. 2:230 lid 4 (BV) and 2:120 lid 4 (NV): the board keeps a
  record of the resolutions the general meeting adopts. Boek 2 sets no contents for a board's minutes.
- Austria: the supervisory board's Niederschrift, signed by its chair or the deputy (AktG § 92 (2),
  GmbHG § 30g (2)); a GmbH's general meeting, its resolutions entered in a Niederschrift without
  delay and a copy, with the day they were entered, sent to every shareholder (GmbHG § 40). An AG's
  general meeting is recorded by a notary (AktG § 120); this script writes no notarial record.
- Ireland: Companies Act 2014 s.166 (a board's minutes: the directors present, every resolution,
  signed by the chairperson as evidence), s.160(6) (quorum), s.161 (a written resolution signed by
  every director) and s.199 (a general meeting's proceedings and resolutions).
- Spain: Ley de Sociedades de Capital art. 250 (a board's acta signed by the chair and the secretary),
  art. 192 (the list of those attending, inside the acta in an S.L.), art. 202 (every resolution in an
  acta, approved by the junta at its end or within fifteen days by the chair and two members) and art. 203
  (a notary's acta); Reglamento del Registro Mercantil art. 97 (what the acta states: date and place, how
  and when the meeting was called, who came and with what share of the capital, a summary, the
  resolutions and their votes, the approval), art. 98 (the list of those attending) and art. 99 (signed
  by the secretary with the chair's visto bueno). Art. 97.3: asked for registration in the Registro
  Mercantil.
- Italy: Codice civile art. 2375 (the verbale of an S.p.A.'s assembly: signed by the chair and the
  secretary or the notary, the date, who took part and the capital each stood for, how the votes were
  cast and their result, who was for, abstained or dissented; an extraordinary assembly's by a notary),
  arts. 2371 and 2479-bis (the chair's findings on the meeting's constitution and the votes go in the
  verbale), arts. 2421 and 2478 (the books). The code sets no contents for a board's verbale.
- Poland: Kodeks spółek handlowych art. 248 (a sp. z o.o.'s shareholders' meeting: signed by those
  present or at least by the chair and the minute-taker; that it was properly called and can resolve,
  the resolutions, the votes for each and the objections; the attendance list attached), art. 208(1)
  and art. 376 (the management board: the agenda, the members present, the votes on each resolution, a
  dissenting opinion, signed at least by the member who chaired), arts. 222 § 2 and 391 § 2 (the
  supervisory board follows the same) and art. 421 (an S.A.'s general meeting is recorded by a notary).
- Dates and times: Unicode CLDR for the language (skills/_shared/letter.py); a time is 18.30 in the
  Nordic languages, 18 h 30 in Canadian French, 18:30 in Dutch, German, Belgian French, Italian, Polish
  and English, 9:05 in Spanish.
Prints a JSON summary. Needs python-docx.
"""
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / "_shared"))
import letter  # noqa: E402
import company  # noqa: E402
import spec_guard  # noqa: E402

FONT = "Arial"
INK, MUTED, RULE = (0x12, 0x10, 0x0E), (0x6B, 0x62, 0x59), "C9C1B8"

EN = {
    "kind": {"regular": "regular meeting", "special": "special meeting", "adjourned": "adjourned meeting",
             "annual general": "annual general meeting", "extraordinary general": "general meeting",
             "general": "general meeting", "board": "board meeting"},
    "title": "Minutes of the %(kind)s of %(body)s",
    "title_board": "Minutes of a meeting of the board of directors of %(body)s",
    "number": "Minutes no.", "company_number": "Company number", "date": "Date", "time": "Time", "place": "Place",
    "method": "Held as", "methods": {"meeting": "a meeting", "video": "a video meeting", "hybrid": "a meeting, some by video",
                                      "written": "written resolutions"},
    "chair": "Chair", "secretary": "Secretary", "checkers": "Minutes checked by", "present": "Present",
    "present_board": "Directors present", "in_attendance": "In attendance", "absent": "Absent",
    "previous": {"approved": "The minutes of the previous meeting were read and approved.",
                 "approved as corrected": "The minutes of the previous meeting were read and approved as corrected."},
    "moved": "%(mover)s moved %(text)s.", "result": {"adopted": "Adopted", "lost": "Lost", "withdrawn": "Withdrawn"},
    "votes": "%(for)s for, %(against)s against, %(abstained)s abstained",
    "decided": "Resolved %s.", "voted_for": "For: %s.", "voted_against": "Against: %s.",
    "dissent": "%(name)s asked that their dissent be recorded: %(text)s.",
    "opened": "The chair opened the meeting at %s.", "adjourned": "The meeting was adjourned at %s.",
    "quorum": "The chair confirmed that a quorum was present.",
    "shareholders": "Members present or represented", "sh_cols": ("Member", "Shares", "Votes", "Represented by"),
    "item": "%d.",
    "sign_secretary": "Secretary", "sign_chair": "Chair", "sign_checker": "Checked by", "approved": "Approved on",
    "sign_record": "Signed as a correct record, chair", "sign_director": "Director",
    "conflict": "%(name)s declared a conflict of interest: %(text)s.",
}

WORDS = {
    "en-GB": EN,
    "sv-SE": {
        "kind": {"regular": "ordinarie möte", "special": "extra möte", "adjourned": "fortsatt möte",
                 "annual general": "årsstämma", "extraordinary general": "extra bolagsstämma",
                 "general": "bolagsstämma", "board": "styrelsemöte"},
        "title": "Protokoll fört vid %(kind)s i %(body)s",
        "number": "Protokoll nr", "company_number": "Org.nr", "date": "Datum", "time": "Tid", "place": "Plats",
        "method": "Form", "methods": {"meeting": "möte", "video": "videomöte", "hybrid": "möte, delvis per video",
                                       "written": "per capsulam"},
        "chair": "Ordförande", "secretary": "Protokollförare", "checkers": "Justerare", "present": "Närvarande",
        "present_board": "Närvarande ledamöter", "in_attendance": "Övriga närvarande", "absent": "Frånvarande",
        "previous": {"approved": "Föregående protokoll lästes upp och godkändes.",
                     "approved as corrected": "Föregående protokoll lästes upp och godkändes med rättelser."},
        "moved": "%(mover)s föreslog %(text)s.", "result": {"adopted": "Bifölls", "lost": "Avslogs", "withdrawn": "Drogs tillbaka"},
        "votes": "%(for)s för, %(against)s emot, %(abstained)s avstod",
        "decided": "Beslutades %s.", "voted_for": "För röstade: %s.", "voted_against": "Emot röstade: %s.",
        "dissent": "%(name)s anmälde reservation: %(text)s.",
        "opened": "Ordföranden öppnade mötet kl. %s.", "adjourned": "Mötet avslutades kl. %s.",
        "quorum": "Styrelsen konstaterades vara beslutför.",
        "shareholders": "Röstlängd", "sh_cols": ("Aktieägare", "Aktier", "Röster", "Ombud"),
        "item": "§ %d",
        "sign_secretary": "Vid protokollet", "sign_chair": "Justeras, ordförande", "sign_checker": "Justeras",
        "approved": "Godkänt den", "sign_record": "Justeras, ordförande", "sign_director": "Ledamot",
    },
    "nb-NO": {
        "kind": {"regular": "ordinært møte", "special": "ekstraordinært møte", "adjourned": "fortsatt møte",
                 "annual general": "ordinær generalforsamling", "extraordinary general": "ekstraordinær generalforsamling",
                 "general": "generalforsamling", "board": "styremøte"},
        "title": "Protokoll fra %(kind)s i %(body)s",
        "number": "Møte nr.", "company_number": "Org.nr.", "date": "Dato", "time": "Tid", "place": "Sted",
        "method": "Behandlingsmåte", "method_general": "Møteform", "methods": {"meeting": "Møte", "video": "Videomøte", "hybrid": "Møte, delvis på video",
                                                  "written": "Skriftlig behandling"},
        "chair": "Møteleder", "secretary": "Protokollfører", "checkers": "Medundertegner", "present": "Til stede",
        "present_board": "Til stede fra styret", "in_attendance": "Ellers til stede", "absent": "Forfall",
        "previous": {"approved": "Protokollen fra forrige møte ble godkjent.",
                     "approved as corrected": "Protokollen fra forrige møte ble godkjent med rettelser."},
        "moved": "%(mover)s foreslo %(text)s.", "result": {"adopted": "Vedtatt", "lost": "Ikke vedtatt", "withdrawn": "Trukket"},
        "votes": "%(for)s for, %(against)s mot, %(abstained)s avsto",
        "decided": "Vedtak: %s.", "voted_for": "For stemte: %s.", "voted_against": "Mot stemte: %s.",
        "unanimous": "Vedtaket var enstemmig.",
        "dissent": "%(name)s ba om å få sin oppfatning protokollert: %(text)s.",
        "opened": "Møtet ble åpnet kl. %s.", "adjourned": "Møtet ble hevet kl. %s.",
        "quorum": "Styret var beslutningsdyktig.",
        "shareholders": "Fortegnelse over møtende aksjeeiere", "sh_cols": ("Aksjeeier", "Aksjer", "Stemmer", "Møtt ved"),
        "item": "Sak %d",
        "notice_approved": "Innkallingen og dagsordenen ble godkjent.",
        "opening_general": ["Åpning av møtet og opptak av fortegnelse over møtende aksjeeiere",
                            "Valg av møteleder og en person til å medundertegne protokollen",
                            "Godkjenning av innkalling og dagsorden"],
        "sign_secretary": "Protokollfører", "sign_chair": "Møteleder", "sign_checker": "Medundertegner",
        "approved": "Godkjent den", "sign_record": "Møteleder", "sign_director": "Styremedlem",
        "sign_board_chair": "Styreleder",
    },
    "da-DK": {
        "kind": {"regular": "ordinært møde", "special": "ekstraordinært møde", "adjourned": "fortsat møde",
                 "annual general": "ordinær generalforsamling", "extraordinary general": "ekstraordinær generalforsamling",
                 "general": "generalforsamling", "board": "bestyrelsesmøde"},
        "title": "Protokol for %(kind)s i %(body)s",
        "number": "Møde nr.", "company_number": "CVR-nr.", "date": "Dato", "time": "Tid", "place": "Sted",
        "method": "Mødeform", "methods": {"meeting": "Fysisk møde", "video": "Videomøde", "hybrid": "Møde, delvis på video",
                                           "written": "Skriftlig behandling"},
        "chair": "Mødeleder", "chair_general": "Dirigent", "secretary": "Referent", "checkers": "Medunderskriver",
        "present": "Til stede", "present_board": "Til stede fra bestyrelsen", "in_attendance": "Desuden deltog",
        "absent": "Afbud",
        "previous": {"approved": "Protokollen fra forrige møde blev godkendt.",
                     "approved as corrected": "Protokollen fra forrige møde blev godkendt med rettelser."},
        "moved": "%(mover)s foreslog %(text)s.", "result": {"adopted": "Vedtaget", "lost": "Forkastet", "withdrawn": "Trukket tilbage"},
        "votes": "%(for)s for, %(against)s imod, %(abstained)s undlod at stemme",
        "decided": "Beslutning: %s.", "voted_for": "For stemte: %s.", "voted_against": "Imod stemte: %s.",
        "dissent": "%(name)s ønskede sin mening indført i protokollen: %(text)s.",
        "opened": "Mødet blev åbnet kl. %s.", "adjourned": "Mødet blev hævet kl. %s.",
        "quorum": "Bestyrelsen var beslutningsdygtig.",
        "shareholders": "Fortegnelse over fremmødte kapitalejere", "sh_cols": ("Kapitalejer", "Kapitalandele", "Stemmer", "Fuldmægtig"),
        "item": "Punkt %d",
        "opening_general": ["Valg af dirigent"],
        "sign_secretary": "Referent", "sign_chair": "Mødeleder", "sign_checker": "Medunderskriver",
        "approved": "Godkendt den", "sign_record": "Dirigent", "sign_director": "Bestyrelsesmedlem",
        "sign_board_chair": "Formand",
    },
    "fi-FI": {
        "kind": {"regular": "kokous", "special": "ylimääräinen kokous", "adjourned": "jatkokokous",
                 "annual general": "varsinainen yhtiökokous", "extraordinary general": "ylimääräinen yhtiökokous",
                 "general": "yhtiökokous", "board": "hallituksen kokous"},
        # Finnish inflects the company's name; the title names the meeting and sets the company after a dash.
        "title_fi": {"regular": "Kokouksen", "special": "Ylimääräisen kokouksen", "adjourned": "Jatkokokouksen",
                     "annual general": "Varsinaisen yhtiökokouksen", "extraordinary general": "Ylimääräisen yhtiökokouksen",
                     "general": "Yhtiökokouksen", "board": "Hallituksen kokouksen"},
        "title": "%(kind)s pöytäkirja – %(body)s",
        "number": "Pöytäkirja nro", "company_number": "Y-tunnus", "date": "Aika", "time": "Kellonaika", "place": "Paikka",
        "method": "Kokoustapa", "methods": {"meeting": "Kokous", "video": "Videokokous", "hybrid": "Kokous, osin etäyhteydellä",
                                             "written": "Kirjallinen menettely"},
        "chair": "Puheenjohtaja", "secretary": "Sihteeri", "checkers": "Pöytäkirjantarkastaja", "present": "Läsnä",
        "present_board": "Läsnä hallituksesta", "in_attendance": "Muut läsnäolijat", "absent": "Poissa",
        "previous": {"approved": "Edellisen kokouksen pöytäkirja hyväksyttiin.",
                     "approved as corrected": "Edellisen kokouksen pöytäkirja hyväksyttiin korjattuna."},
        "moved": "%(mover)s ehdotti, %(text)s.", "result": {"adopted": "Hyväksyttiin", "lost": "Hylättiin", "withdrawn": "Peruttiin"},
        "votes": "%(for)s puolesta, %(against)s vastaan, %(abstained)s tyhjää",
        "decided": "Päätös: %s.", "voted_for": "Puolesta äänestivät: %s.", "voted_against": "Vastaan äänestivät: %s.",
        "dissent": "%(name)s ilmoitti eriävän mielipiteensä: %(text)s.",
        "opened": "Puheenjohtaja avasi kokouksen klo %s.", "adjourned": "Puheenjohtaja päätti kokouksen klo %s.",
        "quorum": "Kokous todettiin laillisesti koolle kutsutuksi ja päätösvaltaiseksi.",
        "shareholders": "Ääniluettelo", "sh_cols": ("Osakkeenomistaja", "Osakkeita", "Ääniä", "Edustaja"),
        "item": "%d §",
        "opening_board": ["Kokouksen avaus", "Laillisuus ja päätösvaltaisuus", "Pöytäkirjantarkastajan valinta"],
        "opening_general": ["Kokouksen avaus", "Kokouksen puheenjohtajan ja sihteerin valinta",
                            "Pöytäkirjantarkastajan valinta", "Kokouksen laillisuus ja päätösvaltaisuus",
                            "Läsnäolijoiden toteaminen ja ääniluettelon vahvistaminen"],
        "sign_secretary": "Sihteeri", "sign_chair": "Puheenjohtaja", "sign_checker": "Pöytäkirjantarkastaja",
        "approved": "Hyväksytty", "sign_record": "Puheenjohtaja", "sign_director": "Hallituksen jäsen",
    },
    "fr-CA": {
        "kind": {"regular": "réunion ordinaire", "special": "réunion extraordinaire", "adjourned": "réunion ajournée",
                 "annual general": "assemblée annuelle des actionnaires", "extraordinary general": "assemblée extraordinaire des actionnaires",
                 "general": "assemblée des actionnaires", "board": "réunion du conseil d'administration"},
        "title": "Procès-verbal de %(kind)s de %(body)s",
        "number": "Procès-verbal no", "company_number": "Numéro de société", "date": "Date", "time": "Heure", "place": "Lieu",
        "method": "Forme", "methods": {"meeting": "réunion", "video": "visioconférence", "hybrid": "réunion, en partie par visioconférence",
                                        "written": "résolutions écrites"},
        "chair": "Présidence", "secretary": "Secrétaire", "checkers": "Vérification", "present": "Personnes présentes",
        "present_board": "Administrateurs présents", "in_attendance": "Assistent également", "absent": "Personnes absentes",
        "previous": {"approved": "Le procès-verbal de la réunion précédente est adopté.",
                     "approved as corrected": "Le procès-verbal de la réunion précédente est adopté tel que modifié."},
        "moved": "%(mover)s propose %(text)s.", "result": {"adopted": "Adoptée", "lost": "Rejetée", "withdrawn": "Retirée"},
        "votes": "%(for)s pour, %(against)s contre, %(abstained)s abstentions",
        "decided": "Il est résolu %s.", "voted_for": "Pour : %s.", "voted_against": "Contre : %s.",
        "dissent": "%(name)s demande que sa dissidence soit consignée : %(text)s.",
        "opened": "La séance est ouverte à %s.", "adjourned": "La séance est levée à %s.",
        "quorum": "La présidence constate que le quorum est atteint.",
        "shareholders": "Actionnaires présents ou représentés", "sh_cols": ("Actionnaire", "Actions", "Voix", "Représenté par"),
        "item": "%d.",
        "sign_secretary": "Secrétaire de la réunion", "sign_chair": "Présidence de la réunion", "sign_checker": "Vérification",
        "approved": "Approuvé le", "sign_record": "Présidence de la réunion", "sign_director": "Administrateur",
    },
}
# English for the United States, Canada and Australia: the words of en-GB, the dates of each country.
for _tag in ("en-US", "en-CA", "en-AU"):
    WORDS[_tag] = EN

# Wave 8: Dutch (the Netherlands and Belgium), Belgian French and Austrian German. Times as CLDR writes
# them for these languages (HH:mm).
NL = {
    "kind": {"regular": "vergadering", "special": "buitengewone vergadering", "adjourned": "voortgezette vergadering",
             "annual general": "jaarlijkse algemene vergadering", "extraordinary general": "buitengewone algemene vergadering",
             "general": "algemene vergadering", "board": "bestuursvergadering"},
    "title": "Notulen van de %(kind)s van %(body)s",
    "number": "Notulen nr.", "company_number": "KvK-nummer", "date": "Datum", "time": "Tijd", "place": "Plaats",
    "method": "Vorm", "methods": {"meeting": "vergadering", "video": "videovergadering", "hybrid": "vergadering, deels per video",
                                   "written": "besluitvorming buiten vergadering"},
    "chair": "Voorzitter", "secretary": "Notulist", "checkers": "Medeondertekenaars", "present": "Aanwezig",
    "present_board": "Aanwezige bestuurders", "in_attendance": "Verder aanwezig", "absent": "Afwezig",
    "previous": {"approved": "De notulen van de vorige vergadering worden goedgekeurd.",
                 "approved as corrected": "De notulen van de vorige vergadering worden met wijzigingen goedgekeurd."},
    "moved": "%(mover)s stelt voor %(text)s.", "result": {"adopted": "Aangenomen", "lost": "Verworpen", "withdrawn": "Ingetrokken"},
    "votes": "%(for)s voor, %(against)s tegen, %(abstained)s onthoudingen",
    "decided": "Besluit: %s.", "voted_for": "Voor stemden: %s.", "voted_against": "Tegen stemden: %s.",
    "dissent": "%(name)s laat aantekenen: %(text)s.",
    "conflict": "%(name)s meldt een tegenstrijdig belang: %(text)s.",
    "opened": "De voorzitter opent de vergadering om %s uur.", "adjourned": "De voorzitter sluit de vergadering om %s uur.",
    "quorum": "De voorzitter stelt vast dat de vergadering geldige besluiten kan nemen.",
    "shareholders": "Aanwezige en vertegenwoordigde aandeelhouders",
    "sh_cols": ("Aandeelhouder", "Aandelen", "Stemmen", "Gevolmachtigde"),
    "item": "%d.",
    "sign_secretary": "Notulist", "sign_chair": "Voorzitter", "sign_checker": "Medeondertekenaar",
    "approved": "Vastgesteld op", "sign_record": "Voorzitter", "sign_director": "Bestuurder",
}
WORDS["nl-NL"] = NL
WORDS["nl-BE"] = dict(
    NL, kind=dict(NL["kind"], board="vergadering van het bestuursorgaan",
                  **{"annual general": "gewone algemene vergadering"}),
    kind_board_nv="vergadering van de raad van bestuur",
    company_number="Ondernemingsnummer", secretary="Secretaris", checkers="Stemopnemers",
    conflict="%(name)s deelt mee een strijdig belang van vermogensrechtelijke aard te hebben: %(text)s.",
    shareholders="Aanwezigheidslijst", incidents="Technische problemen bij de deelname op afstand",
    sign_secretary="Secretaris", sign_checker="Stemopnemer")
WORDS["fr-BE"] = dict(
    WORDS["fr-CA"],
    kind={"regular": "réunion ordinaire", "special": "réunion extraordinaire", "adjourned": "réunion ajournée",
          "annual general": "assemblée générale ordinaire", "extraordinary general": "assemblée générale extraordinaire",
          "general": "assemblée générale", "board": "réunion de l'organe d'administration"},
    kind_board_nv="réunion du conseil d'administration",
    number="Procès-verbal n°", company_number="Numéro d'entreprise", checkers="Scrutateurs",
    present="Présents", absent="Excusés",
    decided="Décision : %s.",
    conflict="%(name)s déclare avoir un intérêt opposé de nature patrimoniale : %(text)s.",
    shareholders="Liste de présences", incidents="Problèmes techniques lors de la participation à distance",
    sign_secretary="Secrétaire", sign_chair="Présidence", sign_checker="Membre du bureau",
    sign_record="Présidence")
DE = {
    "kind": {"regular": "Sitzung", "special": "außerordentliche Sitzung", "adjourned": "fortgesetzte Sitzung",
             "annual general": "ordentliche Generalversammlung", "extraordinary general": "außerordentliche Generalversammlung",
             "general": "Generalversammlung", "board": "Sitzung des Aufsichtsrats"},
    # An Aktiengesellschaft's general meeting is the Hauptversammlung.
    "kind_ag": {"annual general": "ordentliche Hauptversammlung", "extraordinary general": "außerordentliche Hauptversammlung",
                "general": "Hauptversammlung"},
    "title": "Niederschrift über die %(kind)s der %(body)s",
    "number": "Niederschrift Nr.", "company_number": "Firmenbuchnummer", "date": "Datum", "time": "Zeit", "place": "Ort",
    "method": "Form", "methods": {"meeting": "Sitzung", "video": "Videokonferenz", "hybrid": "Sitzung, teilweise per Video",
                                   "written": "schriftliche Stimmabgabe"},
    "chair": "Vorsitz", "secretary": "Schriftführung", "checkers": "Mitunterzeichnung", "present": "Anwesend",
    "present_board": "Anwesende Mitglieder", "in_attendance": "Weiters anwesend", "absent": "Entschuldigt",
    "previous": {"approved": "Die Niederschrift der letzten Sitzung wird genehmigt.",
                 "approved as corrected": "Die Niederschrift der letzten Sitzung wird mit Berichtigungen genehmigt."},
    "moved": "%(mover)s stellt den Antrag, %(text)s.", "result": {"adopted": "Angenommen", "lost": "Abgelehnt", "withdrawn": "Zurückgezogen"},
    "votes": "%(for)s dafür, %(against)s dagegen, %(abstained)s Enthaltungen",
    "decided": "Beschluss: %s.", "voted_for": "Dafür stimmten: %s.", "voted_against": "Dagegen stimmten: %s.",
    "dissent": "%(name)s gibt zu Protokoll: %(text)s.",
    "conflict": "%(name)s legt einen Interessenkonflikt offen: %(text)s.",
    "opened": "Beginn um %s Uhr.", "adjourned": "Ende um %s Uhr.",
    "quorum": "Die Beschlussfähigkeit wird festgestellt.",
    "shareholders": "Anwesende und vertretene Gesellschafter", "sh_cols": ("Gesellschafter", "Anteile", "Stimmen", "Vertreten durch"),
    "item": "%d.",
    "recorded": "Tag der Aufnahme", "notary": "Notarielle Niederschrift",
    "sign_secretary": "Schriftführung", "sign_chair": "Vorsitz", "sign_checker": "Mitunterzeichnung",
    "approved": "Genehmigt am", "sign_record": "Vorsitz", "sign_director": "Mitglied",
}
WORDS["de-AT"] = DE
WORDS["de-DE"] = DE
WORDS["en-IE"] = EN

# Wave 9: Spanish, Italian and Polish. Times as CLDR 48 writes them (H:mm in Spanish, HH:mm in Italian and
# Polish). The words follow each statute's own: acta, junta, consejo, V.º B.º (Reglamento del Registro
# Mercantil art. 99); verbale, assemblea, presidente, segretario (Codice civile art. 2375); protokół,
# zgromadzenie wspólników, zarząd, zdanie odrębne, sprzeciw (Kodeks spółek handlowych arts. 208(1) and 248).
WORDS["es-ES"] = {
    "kind": {"regular": "reunión ordinaria", "special": "reunión extraordinaria", "adjourned": "reunión aplazada",
             "annual general": "junta general ordinaria", "extraordinary general": "junta general extraordinaria",
             "general": "junta general", "board": "reunión del consejo de administración"},
    "title": "Acta de la %(kind)s de %(body)s",
    "number": "Acta n.º", "company_number": "NIF", "date": "Fecha", "time": "Hora", "place": "Lugar",
    "method": "Forma", "methods": {"meeting": "reunión presencial", "video": "videoconferencia",
                                    "hybrid": "reunión presencial y por videoconferencia", "written": "por escrito y sin sesión"},
    "chair": "Presidencia", "secretary": "Secretaría", "checkers": "Interventores", "present": "Asistentes",
    "present_board": "Consejeros asistentes", "in_attendance": "Asisten también", "absent": "Ausentes",
    "convened": "Convocatoria", "represented": "Representados", "by": "por", "notary": "Notario",
    "previous": {"approved": "Se aprueba el acta de la reunión anterior.",
                 "approved as corrected": "Se aprueba el acta de la reunión anterior con las correcciones señaladas."},
    "moved": "%(mover)s propone %(text)s.", "result": {"adopted": "Aprobada", "lost": "Rechazada", "withdrawn": "Retirada"},
    "votes": "%(for)s a favor, %(against)s en contra, %(abstained)s abstenciones",
    "decided": "Acuerdo: %s.", "voted_for": "Votan a favor: %s.", "voted_against": "Votan en contra: %s.",
    "voted_abstained": "Se abstienen: %s.",
    "tally": "Votos a favor: %(for)s; en contra: %(against)s; abstenciones: %(abstained)s.",
    "unanimous_n": "Acuerdo adoptado por unanimidad, con %s votos a favor.",
    "dissent": "%(name)s solicita que conste en acta su oposición: %(text)s.",
    "conflict": "%(name)s comunica una situación de conflicto de interés: %(text)s.",
    "opened": "Se abre la sesión a las %s horas.", "adjourned": "Se levanta la sesión a las %s horas.",
    "quorum": "La presidencia declara válidamente constituida la junta.",
    "quorum_board": "La presidencia declara válidamente constituido el consejo.",
    "universal": "Junta universal: los socios, presentes o representados, reúnen la totalidad del capital social y aceptan por "
                 "unanimidad la celebración de la junta y su orden del día.",
    "agenda": "Orden del día",
    "attendance": "Asisten en persona %(own)s socios, con el %(own_pct)s %% del capital social, y por representación %(proxy)s, "
                  "con el %(proxy_pct)s %%.",
    "attached": "La lista de asistentes se adjunta al acta como anexo firmado por la secretaría, con el visto bueno de la presidencia.",
    "approved_end": "El acta se aprueba por unanimidad al término de la reunión.",
    "approved_later": "El acta se aprueba el %(date)s, %(how)s.",
    "shareholders": "Lista de asistentes", "sh_cols": ("Socio", "Participaciones", "Votos", "Representado por"),
    "sh_cols_sa": ("Accionista", "Acciones", "Votos", "Representado por"),
    "item": "%d.",
    "sign_secretary": "Secretaría", "sign_chair": "V.º B.º Presidencia", "sign_checker": "Interventor",
    "approved": "Aprobada el", "sign_record": "V.º B.º Presidencia", "sign_director": "Consejero", "sign_member": "Socio",
}
WORDS["it-IT"] = {
    "kind": {"regular": "riunione", "special": "riunione straordinaria", "adjourned": "riunione aggiornata",
             "annual general": "assemblea ordinaria", "extraordinary general": "assemblea straordinaria",
             "general": "assemblea", "board": "riunione del consiglio di amministrazione"},
    "title": "Verbale %(kind)s di %(body)s",
    "number": "Verbale n.", "company_number": "Codice fiscale", "date": "Data", "time": "Ora", "place": "Luogo",
    "method": "Modalità", "methods": {"meeting": "riunione in presenza", "video": "videoconferenza",
                                       "hybrid": "in presenza e in videoconferenza", "written": "consultazione scritta"},
    "chair": "Presidente", "secretary": "Segretario", "checkers": "Scrutatori", "present": "Presenti",
    "present_board": "Amministratori presenti", "in_attendance": "Assistono inoltre", "absent": "Assenti",
    "notary": "Notaio",
    "previous": {"approved": "Il verbale della riunione precedente è approvato.",
                 "approved as corrected": "Il verbale della riunione precedente è approvato con le correzioni indicate."},
    "moved": "%(mover)s propone %(text)s.", "result": {"adopted": "Approvata", "lost": "Respinta", "withdrawn": "Ritirata"},
    "votes": "%(for)s favorevoli, %(against)s contrari, %(abstained)s astenuti",
    "decided": "Si delibera %s.", "voted_for": "Favorevoli: %s.", "voted_against": "Contrari: %s.",
    "voted_abstained": "Astenuti: %s.",
    "tally": "Esito della votazione: %(for)s voti favorevoli, %(against)s contrari, %(abstained)s astenuti.",
    "unanimous_n": "La delibera è approvata all'unanimità, con %s voti favorevoli.",
    "dissent": "%(name)s chiede che sia riassunta a verbale la propria dichiarazione: %(text)s.",
    "conflict": "%(name)s dà notizia di un proprio interesse nell'operazione: %(text)s.",
    "opened": "Il presidente apre la seduta alle ore %s.", "adjourned": "Il presidente dichiara chiusa la seduta alle ore %s.",
    "quorum": "Il presidente verifica la regolarità della costituzione, accerta l'identità e la legittimazione dei presenti e "
              "dichiara l'assemblea validamente costituita.",
    "quorum_board": "Il presidente constata la presenza della maggioranza degli amministratori in carica.",
    "voting": "Modalità di voto",
    "attached": "L'elenco dei partecipanti, con il capitale rappresentato da ciascuno, è allegato al verbale.",
    "shareholders": "Elenco dei partecipanti", "sh_cols": ("Socio", "Azioni", "Voti", "Rappresentato da"),
    "sh_cols_srl": ("Socio", "Quota (euro)", "Voti", "Rappresentato da"),
    "item": "%d.",
    "sign_secretary": "Il segretario", "sign_chair": "Il presidente", "sign_checker": "Scrutatore",
    "approved": "Approvato il", "sign_record": "Il presidente", "sign_director": "Amministratore",
}
WORDS["pl-PL"] = {
    "kind": {"regular": "zebranie", "special": "zebranie nadzwyczajne", "adjourned": "zebranie kontynuowane",
             "annual general": "zwyczajne zgromadzenie wspólników", "extraordinary general": "nadzwyczajne zgromadzenie wspólników",
             "general": "zgromadzenie wspólników", "board": "posiedzenie zarządu"},
    # Polish inflects the meeting's name after "Protokół z" and leaves the company's name alone after "spółki".
    "title_pl": {"regular": "z zebrania", "special": "z zebrania nadzwyczajnego", "adjourned": "z kontynuowanego zebrania",
                 "annual general": "ze zwyczajnego zgromadzenia wspólników",
                 "extraordinary general": "z nadzwyczajnego zgromadzenia wspólników",
                 "general": "ze zgromadzenia wspólników", "board": "z posiedzenia zarządu"},
    "title_pl_sa": {"annual general": "ze zwyczajnego walnego zgromadzenia", "extraordinary general": "z nadzwyczajnego walnego zgromadzenia",
                    "general": "z walnego zgromadzenia"},
    "title_pl_supervisory": "z posiedzenia rady nadzorczej",
    "title": "Protokół %(kind)s spółki %(body)s", "title_club": "Protokół %(kind)s – %(body)s",
    "number": "Protokół nr", "company_number": "KRS", "date": "Data", "time": "Godzina", "place": "Miejsce",
    "method": "Tryb", "methods": {"meeting": "posiedzenie stacjonarne", "video": "wideokonferencja",
                                   "hybrid": "posiedzenie stacjonarne z udziałem zdalnym", "written": "tryb pisemny"},
    "chair": "Przewodniczący", "secretary": "Protokolant", "checkers": "Współpodpisujący", "present": "Obecni",
    "present_board": "Obecni członkowie", "present_supervisory": "Obecni członkowie",
    "in_attendance": "Ponadto obecni", "absent": "Nieobecni", "notary": "Notariusz",
    "previous": {"approved": "Protokół z poprzedniego posiedzenia został przyjęty.",
                 "approved as corrected": "Protokół z poprzedniego posiedzenia został przyjęty z poprawkami."},
    "moved": "%(mover)s zgłasza wniosek, %(text)s.", "result": {"adopted": "Przyjęto", "lost": "Odrzucono", "withdrawn": "Wycofano"},
    "votes": "%(for)s za, %(against)s przeciw, %(abstained)s wstrzymujących się",
    "decided": "Uchwała: %s.", "voted_for": "Za głosowali: %s.", "voted_against": "Przeciw głosowali: %s.",
    "voted_abstained": "Wstrzymali się: %s.",
    "tally": "Głosy za: %(for)s, przeciw: %(against)s, wstrzymujące się: %(abstained)s.",
    "unanimous_n": "Uchwałę powzięto jednogłośnie, liczba głosów za: %s.",
    "dissent": "%(name)s zgłasza zdanie odrębne: %(text)s.",
    "dissent_general": "%(name)s zgłasza sprzeciw: %(text)s.",
    "conflict": "%(name)s ujawnia sprzeczność interesów: %(text)s.",
    "opened": "Posiedzenie otwarto o godz. %s.", "adjourned": "Posiedzenie zamknięto o godz. %s.",
    "opened_general": "Zgromadzenie otwarto o godz. %s.", "adjourned_general": "Zgromadzenie zamknięto o godz. %s.",
    "quorum": "Przewodniczący stwierdza prawidłowość zwołania zgromadzenia wspólników i jego zdolność do powzięcia uchwał.",
    "quorum_board": "Przewodniczący stwierdza zdolność do podejmowania uchwał.",
    "agenda": "Porządek obrad",
    "attached": "Lista obecności z podpisami uczestników zgromadzenia stanowi załącznik do protokołu.",
    "shareholders": "Lista obecności", "sh_cols": ("Wspólnik", "Udziały", "Głosy", "Pełnomocnik"),
    "item": "%d.",
    "sign_secretary": "Protokolant", "sign_chair": "Przewodniczący", "sign_checker": "Współpodpisujący",
    "approved": "Zatwierdzono dnia", "sign_record": "Przewodniczący", "sign_director": "Członek zarządu",
}

# Who abstained and that a decision was unanimous, in the languages whose minutes had no line for them (Spain,
# Italy and Poland count the votes; their own words stand): what the data file gives is never dropped.
for _lang, _abstained, _unanimous in (
        ("en", "Abstained: %s.", "The resolution was passed unanimously."),
        ("sv", "Avstod från att rösta: %s.", "Beslutet var enhälligt."),
        ("nb", "Avsto fra å stemme: %s.", "Vedtaket var enstemmig."),
        ("da", "Undlod at stemme: %s.", "Beslutningen var enstemmig."),
        ("fi", "Äänestämästä pidättyivät: %s.", "Päätös oli yksimielinen."),
        ("fr", "Abstentions : %s.", "La résolution est adoptée à l'unanimité."),
        ("nl", "Onthielden zich van stemming: %s.", "Het besluit is met algemene stemmen genomen."),
        ("de", "Enthaltungen: %s.", "Der Beschluss wurde einstimmig gefasst."),
        ("es", "Se abstienen: %s.", "El acuerdo se adopta por unanimidad."),
        ("it", "Astenuti: %s.", "La delibera è approvata all'unanimità."),
        ("pl", "Wstrzymali się: %s.", "Uchwałę podjęto jednogłośnie.")):
    for _loc, _w in WORDS.items():
        if _loc.startswith(_lang):
            _w.setdefault("voted_abstained", _abstained)
            _w.setdefault("unanimous", _unanimous)

# A key the minutes of one country print and the others have no line for: given where it has none, it is
# an error that says so, never a silent drop. key -> the word the language must have for it.
BY_LANGUAGE = {"convened": "convened", "recorded": "recorded", "notary": "notary", "represented": "represented",
               "universal": "universal", "voting": "voting", "incidents": "incidents",
               "shareholders_attached": "attached", "minutes_approved": "approved_end",
               "notice_approved": "notice_approved"}


def not_printed(spec):
    """Keys the data file gives that this language's or this kind of minutes has no line for."""
    loc = locale_of(spec)
    w = WORDS[loc]
    cc, kind = country_of(spec, loc), kind_of(spec)
    company = bool(cc) and kind in ("board", "general")
    out = []
    for key, word in BY_LANGUAGE.items():
        if spec.get(key) in (None, "", [], {}, False):
            continue
        if not w.get(word):
            out.append('"%s" has no line in %s minutes' % (key, loc))
        elif key == "universal" and kind != "general":
            out.append('"universal" is printed for a general meeting only')
        elif key in ("shareholders_attached", "minutes_approved") and not company:
            out.append('"%s" is printed for a company\'s board or general meeting only (give "country")' % key)
        elif key == "shareholders_attached" and spec.get("shareholders"):
            out.append('"shareholders_attached" is not printed when "shareholders" lists them in the minutes')
    return out


LANG_LOCALE = {"sv": "sv-SE", "nb": "nb-NO", "no": "nb-NO", "nn": "nb-NO", "da": "da-DK", "fi": "fi-FI", "fr": "fr-CA",
               "nl": "nl-NL", "de": "de-DE", "es": "es-ES", "it": "it-IT", "pl": "pl-PL"}
# A language two of the library's countries write: the country picks the variant.
LANG_COUNTRY = {("fr", "BE"): "fr-BE", ("nl", "BE"): "nl-BE", ("de", "AT"): "de-AT"}
COUNTRY_EN = {"US": "en-US", "CA": "en-CA", "AU": "en-AU", "IE": "en-IE"}
COUNTRY_OF = {"sv-SE": "SE", "nb-NO": "NO", "da-DK": "DK", "fi-FI": "FI", "fr-CA": "CA", "nl-NL": "NL", "nl-BE": "BE",
              "fr-BE": "BE", "de-AT": "AT", "en-IE": "IE", "es-ES": "ES", "it-IT": "IT", "pl-PL": "PL"}
REQUIRED = ("body", "meeting", "date", "chair", "secretary", "items")
GENERAL = ("annual general", "extraordinary general", "general")


def locale_of(spec):
    lang = str(spec.get("language") or "en").lower()
    base = lang.split("-")[0]
    named = letter.country_code(spec.get("country")) or (lang.split("-")[1].upper() if "-" in lang else "")
    if (base, named) in LANG_COUNTRY:
        return LANG_COUNTRY[(base, named)]
    if base in LANG_LOCALE:
        return LANG_LOCALE[base]
    if lang in ("en-us", "en-ca", "en-au", "en-ie"):
        return lang[:3] + lang[3:].upper()
    return COUNTRY_EN.get(country_of(spec, "en-GB"), "en-GB")


def country_of(spec, loc=None):
    """The law the company is under: the spec's country, else the language's own country; none for a club."""
    named = letter.country_code(spec.get("country"))
    if named:
        return named
    if spec.get("meeting") not in ("board",) + GENERAL:
        return ""
    return COUNTRY_OF.get(loc or locale_of(spec), "")


def kind_of(spec):
    m = spec.get("meeting")
    return "general" if m in GENERAL else m


def form_of(spec):
    """The company's legal form, as the spec names it or as its name ends: BV, NV, SRL, SA, GmbH, AG."""
    form = str(spec.get("legal_form") or letter.legal_form({"name": spec.get("body") or ""}) or "")
    if not form:
        # A form the shared list does not carry (a Belgian CV): the last word of the name, when it is one.
        last = str(spec.get("body") or "").split()[-1:] or [""]
        form = last[0] if last[0].replace(".", "").upper() in BE_BOOK else ""
    return form.replace(".", "").strip()


# Belgium: the book of the Code des sociétés et des associations / Wetboek van vennootschappen en
# verenigingen a company's form falls under, and that book's articles on minutes.
BE_BOOK = {"BV": "5", "SRL": "5", "BVBA": "5", "SPRL": "5", "CV": "6", "SC": "6", "NV": "7", "SA": "7"}
BE_ARTICLES = {
    "5": {"board": "5:75", "conflict": "5:76", "list": "5:90", "general": "5:93", "remote": "5:89"},
    "6": {"board": "6:63", "conflict": "6:64", "list": "6:76", "general": "6:79", "remote": "6:75"},
    "7": {"board": "7:95", "conflict": "7:96", "list": "7:138", "general": "7:141", "remote": "7:137"},
}


def be_article(spec, what):
    """The article of the Belgian code for this company's form, or all three when the form is not known."""
    book = BE_BOOK.get(form_of(spec).upper())
    code = "CSA" if locale_of(spec).startswith("fr") else "WVV"
    if book:
        return "%s art. %s" % (code, BE_ARTICLES[book][what])
    return "%s art. %s" % (code, ", ".join(BE_ARTICLES[b][what] for b in ("5", "6", "7")))


def at_law(spec, what):
    """The Austrian provision: the Aktiengesetz for an AG, the GmbH-Gesetz for a GmbH or a FlexCo."""
    ag = form_of(spec).upper() in ("AG", "SE")
    if what == "board":
        return "AktG § 92 (2)" if ag else "GmbHG § 30g (2)"
    return "AktG § 120" if ag else "GmbHG § 40"


def bare_form(spec):
    """The legal form with no points or spaces, in capitals: SL, SA, SRL, SPA, SPZOO."""
    return form_of(spec).replace(" ", "").upper()


def voters(spec):
    """How many votes a unanimous decision carried: the directors present and represented at a board, the
    votes on the attendance list at a general meeting."""
    if kind_of(spec) == "board":
        return len(spec.get("present") or []) + len(spec.get("represented") or [])
    return sum(int(r.get("votes", r.get("shares") or 0) or 0) for r in spec.get("shareholders") or [])


def tally_lines(spec, d, w, loc):
    """Spain, Italy, Poland: the count of the vote on a decision (Reglamento del Registro Mercantil art. 97.1
    7.ª, Codice civile art. 2375, Kodeks spółek handlowych arts. 208(1) and 248 § 2), and who voted which
    way when the spec names them."""
    out = []
    names = {k: d[k] for k in ("for", "against", "abstained") if isinstance(d.get(k), list)}
    v = d.get("votes")
    if not v and names and kind_of(spec) == "board":
        v = {k: len(names.get(k) or []) for k in ("for", "against", "abstained")}     # one vote a head
    if v:
        full = {"for": 0, "against": 0, "abstained": 0}
        full.update(v)
        out.append(("para", w["tally"] % {k: letter.number(n, loc) for k, n in full.items()}))
    elif d.get("unanimous") and voters(spec):
        out.append(("para", w["unanimous_n"] % letter.number(voters(spec), loc)))
    elif d.get("unanimous"):
        out.append(("para", w["unanimous"]))          # no count to give: the word alone
    if names.get("for") and (names.get("against") or names.get("abstained")):
        out.append(("para", w["voted_for"] % ", ".join(names["for"])))
    if names.get("against"):
        out.append(("para", w["voted_against"] % ", ".join(names["against"])))
    if names.get("abstained"):
        out.append(("para", w["voted_abstained"] % ", ".join(names["abstained"])))
    return out


def attendance(spec, w, loc):
    """Spain (Reglamento del Registro Mercantil art. 97.1 4.ª): how many members with a vote came in person
    and how many by proxy, and the share of the capital each group holds."""
    rows = spec.get("shareholders") or []
    total = float(spec.get("total_shares") or 0)
    own = [r for r in rows if not r.get("by")]
    proxy = [r for r in rows if r.get("by")]

    def pct(group):
        if not total:
            return "…"
        return letter.number(round(100.0 * sum(float(r.get("shares") or 0) for r in group) / total, 2), loc)
    return w["attendance"] % {"own": len(own), "proxy": len(proxy), "own_pct": pct(own), "proxy_pct": pct(proxy)}


def notarial(spec, loc=None):
    """(law, why) when the statute has a notary record this meeting, so that this script's file is a working
    record only; None otherwise."""
    cc, kind, form = country_of(spec, loc), kind_of(spec), bare_form(spec)
    if cc == "ES" and kind == "general" and spec.get("notary"):
        return ("LSC art. 203", "a notary called to the junta draws up its acta, which needs no approval and no signature of "
                                "the chair and the secretary (Reglamento del Registro Mercantil arts. 101 to 103)")
    if cc == "IT" and spec.get("meeting") == "extraordinary general":
        return ("Codice civile art. 2375", "the verbale of an extraordinary assembly is drawn up by a notary")
    if cc == "PL" and kind == "general" and form in ("SA", "PSA"):
        return ("KSH art. 421 § 1", "a notary draws up the protocol of a joint-stock company's general meeting")
    return None


def pl_law(spec, what):
    """The article of the Kodeks spółek handlowych for this company and organ."""
    sa = bare_form(spec) in ("SA", "PSA")
    if what == "general":
        return "KSH art. 421" if sa else "KSH art. 248"
    if spec.get("organ") == "supervisory":
        return "KSH art. 391 § 2 and art. 376" if sa else "KSH art. 222 § 2 and art. 208(1)"
    return "KSH art. 376" if sa else "KSH art. 208(1)"


def clock(value, locale):
    """18:30 in English (6:30 p.m. in the United States); 18.30 in Swedish, Norwegian, Danish and Finnish (Språkrådet, Kotus); 18 h 30
    in Canadian French (Office québécois de la langue française)."""
    h, m = re.match(r"^(\d{1,2})[:.](\d{2})$", str(value)).groups()
    if locale == "fr-CA":
        return "%d h" % int(h) if m == "00" else "%d h %s" % (int(h), m)
    if locale in ("sv-SE", "nb-NO", "da-DK", "fi-FI"):
        return "%s.%s" % (h.zfill(2), m)
    if locale == "es-ES":
        return "%d:%s" % (int(h), m)               # CLDR es short time, H:mm
    # Dutch, German, Belgian French and English: HH:mm (CLDR short time for nl, nl-BE, fr-BE, de-AT, en-IE).
    if locale == "en-US":
        # GPO Style Manual 12.9: 2:30 p.m., the twelve-hour clock with a.m. and p.m.
        hh = int(h)
        return "%d:%s %s" % (hh % 12 or 12, m, "a.m." if hh < 12 else "p.m.")
    return "%s:%s" % (h.zfill(2), m)


def date_of(value, loc):
    """The minutes' date: ISO in Swedish (as before), else the language's long form (letter.long_date)."""
    if loc == "sv-SE":
        return letter.date(value, loc)
    return letter.long_date(value, loc)


def colon(loc):
    # French sets a no-break space before a colon (OQLF, Banque de dépannage linguistique).
    return " : " if loc.startswith("fr") else ": "


def signers(spec, loc):
    """(role, name) for every signature the law or the rules ask for, in order."""
    w = WORDS[loc]
    cc, kind = country_of(spec, loc), kind_of(spec)
    chair, sec = spec["chair"], spec["secretary"]
    checkers = list(spec.get("checkers", []))
    out = []
    if cc in ("NO", "DK") and kind == "board":
        # aksjeloven § 6-29 (1), selskabsloven § 128: every director who took part signs; in Norway a
        # board of five or more that met may pick two of them instead.
        directors = spec.get("present") or [chair]
        if cc == "NO" and len(directors) >= 5 and len(spec.get("signers") or []) >= 2:
            directors = list(spec["signers"])
        for d in directors:
            out.append((w.get("sign_board_chair", w["sign_chair"]) if d == chair else w["sign_director"], d))
        if sec not in directors:
            out.append((w["sign_secretary"], sec))
        return out
    if cc == "NO" and kind == "general":
        # aksjeloven § 5-16 (2): the chair and one person the meeting picks among those present.
        return [(w["sign_chair"], chair)] + [(w["sign_checker"], c) for c in checkers] + \
               ([(w["sign_secretary"], sec)] if sec not in [chair] + checkers else [])
    if cc == "DK" and kind == "general":
        # selskabsloven § 101: the dirigent signs.
        return [(w["sign_record"], chair)] + ([(w["sign_secretary"], sec)] if sec != chair else [])
    if cc == "FI":
        # osakeyhtiölaki 6:6 (board) and 5:23 (general meeting): the chair and at least one checker.
        out = [(w["sign_chair"], chair)] + [(w["sign_checker"], c) for c in checkers]
        return out + ([(w["sign_secretary"], sec)] if sec not in [chair] + checkers else [])
    if cc == "SE" or loc == "sv-SE":
        out = [(w["sign_secretary"], sec), (w["sign_chair"], chair)]
        return out + [(w["sign_checker"], c) for c in checkers]
    if cc in ("GB", "AU") and kind in ("board", "general"):
        # Companies Act 2006 s.249 and s.356; Corporations Act 2001 s.251A(2): the chair signs.
        return [(w["sign_record"], chair)] + ([(w["sign_secretary"], sec)] if sec != chair else [])
    if cc == "CA" and kind in ("board", "general"):
        return [(w["sign_chair"], chair), (w["sign_secretary"], sec)]
    if cc == "IE" and kind in ("board", "general"):
        if kind == "board" and spec.get("method") == "written":
            # Companies Act 2014 s.161(1): a resolution in writing signed by all the directors.
            return [(w["sign_director"], d) for d in (spec.get("present") or [chair])]
        # s.166(3) and s.199(3): signed by the chairperson, the minutes are evidence of the proceedings.
        return [(w["sign_record"], chair)] + ([(w["sign_secretary"], sec)] if sec != chair else [])
    if cc == "BE" and kind == "board":
        # art. 5:75, 6:63, 7:95: the chair signs, and the directors who ask to (signers).
        out = [(w["sign_chair"], chair)] + [(w["sign_director"], d) for d in spec.get("signers") or [] if d != chair]
        return out + ([(w["sign_secretary"], sec)] if sec not in [n for _, n in out] else [])
    if cc == "BE" and kind == "general":
        # art. 5:93, 6:79, 7:141: the members of the bureau sign (chair, secretary, vote counters).
        out = [(w["sign_chair"], chair)] + ([(w["sign_secretary"], sec)] if sec != chair else [])
        return out + [(w["sign_checker"], c) for c in checkers if c not in (chair, sec)]
    titles = spec.get("titles") or {}
    if cc == "ES" and kind in ("board", "general"):
        # Reglamento del Registro Mercantil art. 99.3 (and LSC art. 250 for a board): the secretary signs, with
        # the visto bueno of whoever chaired; a junta universal's members sign after their names (art. 97.1
        # 4.ª); the two members who approve an acta with the chair (LSC art. 202.2) sign too.
        out = [(titles.get("secretary") or w["sign_secretary"], sec),
               ("V.º B.º %s" % titles["chair"] if titles.get("chair") else w["sign_chair"], chair)]
        out += [(w["sign_checker"], c) for c in checkers if c not in (chair, sec)]
        if kind == "general" and spec.get("universal"):
            out += [(w["sign_member"], r["name"]) for r in spec.get("shareholders") or [] if r.get("name") not in (chair, sec)]
        return out
    if cc == "IT" and kind in ("board", "general"):
        # Codice civile art. 2375: the chair and the secretary sign an assembly's verbale; a board's follows it.
        return [(titles.get("chair") or w["sign_chair"], chair)] + ([(titles.get("secretary") or w["sign_secretary"], sec)] if sec != chair else [])
    if cc == "PL" and kind in ("board", "general"):
        # KSH art. 248 § 1: those present, or at least the chair and the minute-taker; art. 208(1) and 376:
        # at least the member who chaired the meeting. Other members who sign go in "signers".
        out = [(titles.get("chair") or w["sign_chair"], chair)] + ([(titles.get("secretary") or w["sign_secretary"], sec)] if sec != chair else [])
        return out + [(w["sign_director"] if kind == "board" else w["sign_checker"], n) for n in spec.get("signers") or []
                      if n not in (chair, sec)]
    if cc in ("NL", "AT") and kind in ("board", "general"):
        # AktG § 92 (2), GmbHG § 30g (2): the supervisory board's chair (or deputy) signs. Boek 2 BW and
        # GmbHG § 40 name no signer; the chair and the minute-taker sign, as the articles usually say.
        out = [(w["sign_chair"], chair)] + ([(w["sign_secretary"], sec)] if sec != chair else [])
        return out + [(w["sign_checker"], c) for c in checkers if c not in (chair, sec)]
    # Robert's Rules (1915) section 60, and a US corporation's secretary (DGCL § 142(a)).
    out = [(w["sign_secretary"], sec), ("%s ____________  %s" % (w["approved"], w["sign_chair"]), chair)]
    return out + [(w["sign_checker"], c) for c in checkers]


def lines(spec):
    """The minutes as (style, text) pairs, the one source for the file and for the check."""
    loc = locale_of(spec)
    w = WORDS[loc]
    cc, kind = country_of(spec, loc), kind_of(spec)
    meeting = spec["meeting"]
    sep = colon(loc)
    if loc == "fi-FI":
        title = w["title"] % {"kind": w["title_fi"].get(meeting, meeting.capitalize()), "body": spec["body"]}
    elif loc in ("fr-CA", "fr-BE"):
        k = w["kind"].get(meeting, meeting)
        if loc == "fr-BE" and meeting == "board" and BE_BOOK.get(form_of(spec).upper()) == "7":
            k = w["kind_board_nv"]                      # a société anonyme has a conseil d'administration
        title = w["title"] % {"kind": ("l'" if k[0] in "aeéiou" else "la ") + k, "body": spec["body"]}
        if spec["body"][:1].lower() in "aeéèiouy":
            title = title.replace(" de " + spec["body"], " d'" + spec["body"])       # de + a vowel elides
    elif loc == "nl-BE" and meeting == "board" and BE_BOOK.get(form_of(spec).upper()) == "7":
        title = w["title"] % {"kind": w["kind_board_nv"], "body": spec["body"]}      # an NV has a raad van bestuur
    elif loc.startswith("de") and kind == "general" and form_of(spec).upper() in ("AG", "SE"):
        title = w["title"] % {"kind": w["kind_ag"].get(meeting, meeting), "body": spec["body"]}
    elif loc == "it-IT":
        k = w["kind"].get(meeting, meeting)
        title = w["title"] % {"kind": ("dell'" if k[:1] in "aeiou" else "della ") + k, "body": spec["body"]}
    elif loc == "pl-PL":
        forms = dict(w["title_pl"])
        if bare_form(spec) in ("SA", "PSA"):
            forms.update(w["title_pl_sa"])              # an S.A. has a walne zgromadzenie
        if spec.get("organ") == "supervisory":
            forms["board"] = w["title_pl_supervisory"]
        # The legal form stays on one line of the title (sp. z o.o. with no-break spaces).
        body = re.sub(r"sp\. ?z ?o\.o\.", "sp.\u00a0z\u00a0o.o.", spec["body"])
        title = (w["title"] if cc else w["title_club"]) % {"kind": forms.get(meeting, meeting), "body": body}
    elif loc.startswith("en") and meeting == "board" and cc:
        title = w["title_board"] % {"body": spec["body"]}
    else:
        title = w["title"] % {"kind": w["kind"].get(meeting, meeting), "body": spec["body"]}
    out = [("title", title)]
    facts = []
    if spec.get("company_number"):
        facts.append((w["company_number"], spec["company_number"]))
    if spec.get("number"):
        facts.append((w["number"], spec["number"]))
    span = ""
    if spec.get("start"):
        span = clock(spec["start"], loc) + ("–" + clock(spec["end"], loc) if spec.get("end") else "")
    if loc == "fi-FI":
        facts.append((w["date"], date_of(spec["date"], loc) + (" klo " + span if span else "")))
    else:
        facts.append((w["date"], date_of(spec["date"], loc)))
        if span:
            facts.append((w["time"], span))
    if spec.get("place"):
        facts.append((w["place"], spec["place"]))
    if spec.get("convened") and w.get("convened"):
        # Reglamento del Registro Mercantil art. 97.1 2.ª: the day and the way the meeting was called.
        c = spec["convened"]
        facts.append((w["convened"], c if isinstance(c, str) else ", ".join(
            x for x in (date_of(c["date"], loc) if c.get("date") else "", str(c.get("how") or "")) if x)))
    if spec.get("recorded") and w.get("recorded"):
        # GmbHG § 40: the day the resolutions were entered in the Niederschrift, which every copy states.
        facts.append((w["recorded"], date_of(spec["recorded"], loc)))
    if spec.get("notary") and w.get("notary"):
        facts.append((w["notary"], spec["notary"]))
    if spec.get("method") or (cc == "NO" and kind in ("board", "general")):
        # aksjeloven § 6-29 asks how the board dealt with the matter, § 5-16 the form of the meeting.
        label = w.get("method_general", w["method"]) if kind == "general" else w["method"]
        facts.append((label, w["methods"].get(spec.get("method") or "meeting", spec.get("method"))))
    titles = spec.get("titles") or {}
    chair_label = titles.get("chair") or (w.get("chair_general", w["chair"]) if kind == "general" else w["chair"])
    facts += [(chair_label, spec["chair"]), (titles.get("secretary") or w["secretary"], spec["secretary"])]
    if spec.get("checkers"):
        facts.append((w["checkers"], ", ".join(spec["checkers"])))
    if spec.get("present"):
        board_label = w.get("present_supervisory") if spec.get("organ") == "supervisory" and w.get("present_supervisory") else w["present_board"]
        facts.append((board_label if kind == "board" and cc else w["present"], ", ".join(spec["present"])))
    if spec.get("represented") and w.get("represented"):
        # Reglamento del Registro Mercantil art. 97.1 4.ª: the members another member stands for.
        facts.append((w["represented"], ", ".join("%s (%s %s)" % (r["name"], w["by"], r["by"]) for r in spec["represented"])))
    if spec.get("in_attendance"):
        facts.append((w["in_attendance"], ", ".join(spec["in_attendance"])))
    if spec.get("absent"):
        facts.append((w["absent"], ", ".join(spec["absent"])))
    out += [("fact", "%s%s%s" % (k, sep, v)) for k, v in facts]

    opening = w.get("opening_general" if kind == "general" else "opening_%s" % kind) if cc else None
    n = 0
    # Facts about the meeting as a whole that have no field of their own, as written.
    free = [("para", str(t)) for t in spec.get("notes") or [] if str(t).strip()]
    if opening:
        out += free
        # The opening business a Nordic meeting records as items of its own (osakeyhtiölaki 5:23 and
        # 6:6, aksjeloven § 5-12 and § 5-16, selskabsloven § 101): who leads, who checks, the quorum.
        for title_ in opening:
            low = title_.lower()
            under = []
            if title_ == opening[0] and spec.get("start"):
                under.append(("para", w["opened"] % clock(spec["start"], loc)))
            if ("puheenjohtaja" in low or "møteleder" in low or "dirigent" in low) and kind == "general":
                under.append(("para", "%s%s%s." % (chair_label, sep, spec["chair"])))
            if ("tarkastaja" in low or "medundertegne" in low) and spec.get("checkers"):
                under.append(("para", "%s%s%s." % (w["checkers"], sep, ", ".join(spec["checkers"]))))
            if ("päätösvaltaisuus" in low or "laillisuus" in low) and spec.get("quorum"):
                under.append(("para", w["quorum"]))
            if "innkalling" in low and spec.get("notice_approved") and w.get("notice_approved"):
                under.append(("para", w["notice_approved"]))
            if ("ääniluettelo" in low or "fortegnelse" in low) and spec.get("shareholders"):
                under.append(("shareholders", ""))
            if not under:
                continue          # a heading with nothing under it is not printed: the data gives nothing for it
            n += 1
            out.append(("item", "%s  %s" % (w["item"] % n, title_)))
            out += under
        if spec.get("shareholders") and ("shareholders", "") not in out:
            # No opening item of this country takes the list (Denmark's is the dirigent's election alone): the
            # list the data file gives is printed under its own heading, never left off.
            out.append(("heading", w["shareholders"]))
            out.append(("shareholders", ""))
    else:
        company = bool(cc) and kind in ("board", "general")
        if spec.get("start"):
            opened = w.get("opened_general") if kind == "general" and w.get("opened_general") else w["opened"]
            out.append(("para", opened % clock(spec["start"], loc)))
        if spec.get("universal") and w.get("universal") and kind == "general":
            out.append(("para", w["universal"]))
        if spec.get("quorum"):
            out.append(("para", w["quorum_board"] if kind == "board" and cc and w.get("quorum_board") else w["quorum"]))
        if w.get("agenda") and company:
            # The agenda: Reglamento del Registro Mercantil art. 97.1 3.ª, KSH arts. 208(1) and 376.
            out.append(("para", "%s%s%s." % (w["agenda"], sep, "; ".join(
                "%d. %s" % (i + 1, it["title"]) for i, it in enumerate(spec["items"])))))
        if spec.get("shareholders"):
            out.append(("heading", w["shareholders"]))
            out.append(("shareholders", ""))
            if w.get("attendance") and company:
                out.append(("para", attendance(spec, w, loc)))
        elif spec.get("shareholders_attached") and w.get("attached") and company:
            out.append(("para", w["attached"]))
        if spec.get("voting") and w.get("voting"):
            # Codice civile art. 2375: how the votes were cast.
            out.append(("para", "%s%s%s." % (w["voting"], sep, str(spec["voting"]).rstrip("."))))
        out += free
    if spec.get("previous_minutes") in w["previous"]:
        out.append(("para", w["previous"][spec["previous_minutes"]]))
    elif str(spec.get("previous_minutes") or "").strip():
        # In the person's own words (the date of the meeting they record, who signed them): as written.
        out.append(("para", str(spec["previous_minutes"]).strip()))
    for item in spec["items"]:
        n += 1
        out.append(("item", "%s  %s" % (w["item"] % n, item["title"])))
        notes = item.get("notes") or []
        out += [("para", str(t)) for t in ([notes] if isinstance(notes, str) else notes) if str(t).strip()]
        for d in item.get("conflict", []):
            # Belgium (art. 5:76, 6:64, 7:96): the director's declaration and explanation go in the minutes,
            # before the decision the others take.
            form = w.get("conflict") or "%(name)s: %(text)s."
            out.append(("para", form % {"name": d["name"], "text": d["text"].rstrip(".")}))
        for m in item.get("motions", []):
            text = w["moved"] % {"mover": m["mover"], "text": m["text"].rstrip(".")}
            result = w["result"].get(m.get("result", ""), m.get("result", ""))
            if m.get("votes"):
                v = {"for": 0, "against": 0, "abstained": 0}
                v.update(m["votes"])
                result += " (%s)" % (w["votes"] % v)
            out.append(("para", "%s %s." % (text, result)))
        for d in item.get("decisions", []):
            d = d if isinstance(d, dict) else {"text": d}
            out.append(("decision", w["decided"] % d["text"].rstrip(".")))
            if w.get("tally") and cc and kind in ("board", "general"):
                out += tally_lines(spec, d, w, loc)
                continue
            if d.get("against") or d.get("abstained"):
                # aksjeloven § 6-29 (1): when the board is not unanimous, who voted for and against; who did
                # not vote is named too when the data file names them.
                if d.get("for"):
                    out.append(("para", w["voted_for"] % ", ".join(d["for"])))
                if d.get("against"):
                    out.append(("para", w["voted_against"] % ", ".join(d["against"])))
                if d.get("abstained"):
                    out.append(("para", w["voted_abstained"] % ", ".join(d["abstained"])))
            elif d.get("unanimous") and w.get("unanimous"):
                out.append(("para", w["unanimous"]))
        for d in item.get("dissent", []):
            form = w.get("dissent_general") if kind == "general" and w.get("dissent_general") else w["dissent"]
            out.append(("para", form % {"name": d["name"], "text": d["text"].rstrip(".")}))
    if spec.get("incidents") and w.get("incidents"):
        # Belgium (art. 5:89, 6:75, 7:137): technical problems that hindered taking part or voting online.
        out.append(("para", "%s%s%s." % (w["incidents"], sep, str(spec["incidents"]).rstrip("."))))
    if w.get("approved_end") and cc and kind in ("board", "general") and not notarial(spec, loc):
        # Reglamento del Registro Mercantil art. 97.1 8.ª and art. 99: the acta's approval, and its day and
        # manner when it was not approved as the meeting ended.
        a = spec.get("minutes_approved")
        if isinstance(a, dict) and a.get("date"):
            out.append(("para", w["approved_later"] % {"date": date_of(a["date"], loc), "how": str(a.get("how") or "").rstrip(".")}))
        else:
            out.append(("para", w["approved_end"]))
    if spec.get("end"):
        closed = w.get("adjourned_general") if kind == "general" and w.get("adjourned_general") else w["adjourned"]
        out.append(("para", closed % clock(spec["end"], loc)))
    out += [("sign", "%s|%s" % s) for s in signers(spec, loc)]
    return out


def write_docx(spec, out):
    from docx import Document
    from docx.enum.table import WD_TABLE_ALIGNMENT
    from docx.oxml import OxmlElement
    from docx.oxml.ns import qn
    from docx.shared import Mm, Pt, RGBColor
    missing = [k for k in REQUIRED if not spec.get(k)]
    if missing:
        raise SystemExit("the spec needs %s" % ", ".join(missing))
    loc = locale_of(spec)
    w = WORDS[loc]
    # The paper of the country whose letters the library prints: US Letter in the United States and Canada.
    cc = country_of(spec, loc) or {"en-US": "US", "en-CA": "CA", "fr-CA": "CA"}.get(loc, "")
    paper = letter.paper_size(letter.LAYOUTS.get(letter.COUNTRY_LAYOUT.get(cc, ""), None))
    doc = Document()
    sec = doc.sections[0]
    sec.page_width, sec.page_height = Mm(paper[0]), Mm(paper[1])
    sec.left_margin = sec.right_margin = Mm(25)
    sec.top_margin, sec.bottom_margin = Mm(20), Mm(22)
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
            for theme in ("w:asciiTheme", "w:hAnsiTheme", "w:eastAsiaTheme", "w:cstheme"):
                fonts.attrib.pop(qn(theme), None)
    normal = doc.styles["Normal"]
    normal.font.size = Pt(10.5)
    normal.font.color.rgb = RGBColor(*INK)
    normal.paragraph_format.space_after = Pt(6)
    normal.paragraph_format.line_spacing = 1.15
    for name, size, before, after in (("Heading 1", 16, 0, 10), ("Heading 2", 11.5, 12, 4), ("Heading 3", 10.5, 10, 4)):
        st = doc.styles[name]
        st.font.size, st.font.bold, st.font.italic = Pt(size), True, False
        st.font.color.rgb = RGBColor(*INK)
        st.paragraph_format.space_before, st.paragraph_format.space_after = Pt(before), Pt(after)
        st.paragraph_format.keep_with_next = True
    parts = lines(spec)
    doc.core_properties.title = parts[0][1]
    doc.core_properties.language = loc
    doc.core_properties.author = spec["secretary"]
    sep = colon(loc)

    def borders(table, rule_top=False, rule_bottom=False):
        pr = table._tbl.tblPr
        b = OxmlElement("w:tblBorders")
        for edge in ("top", "left", "bottom", "right", "insideH", "insideV"):
            e = OxmlElement("w:%s" % edge)
            on = (edge == "top" and rule_top) or (edge == "bottom" and rule_bottom)
            e.set(qn("w:val"), "single" if on else "nil")
            if on:
                e.set(qn("w:sz"), "4")
                e.set(qn("w:color"), RULE)
            b.append(e)
        pr.append(b)
        lay = OxmlElement("w:tblLayout")
        lay.set(qn("w:type"), "fixed")
        pr.append(lay)

    def widths(table, mm):
        table.autofit = False
        for i, wd in enumerate(mm):
            table.columns[i].width = Mm(wd)
            for cell in table.columns[i].cells:
                cell.width = Mm(wd)

    def cell_text(cell, text, size=10, grey=False, bold=False, align=None):
        p = cell.paragraphs[0]
        p.paragraph_format.space_after = Pt(1)
        p.paragraph_format.space_before = Pt(1)
        if align:
            p.alignment = align
        r = p.add_run(str(text))
        r.font.size, r.bold = Pt(size), bold
        if grey:
            r.font.color.rgb = RGBColor(*MUTED)
        return p

    usable = paper[0] - 50
    facts = [t for s, t in parts if s == "fact"]
    signs = [t.split("|", 1) for s, t in parts if s == "sign"]
    i = 0
    while i < len(parts):
        style, text = parts[i]
        if style == "title":
            doc.add_heading(text, level=1)
            # The facts sit in one quiet table under the title: label left, value beside it.
            t = doc.add_table(rows=len(facts), cols=2)
            borders(t, rule_top=True, rule_bottom=True)
            widths(t, (42, usable - 42))
            for r, fact in enumerate(facts):
                k, v = fact.split(sep, 1)
                # The label carries its colon, so the cell reads as "Date: 14 October 2026" in any text view.
                cell_text(t.cell(r, 0), k + sep.rstrip(), size=9, grey=True)
                cell_text(t.cell(r, 1), v, size=10)
            doc.add_paragraph().paragraph_format.space_after = Pt(2)
            i += 1 + len(facts)
            continue
        if style == "item":
            doc.add_heading(text, level=2)
        elif style == "heading":
            doc.add_heading(text, level=3)
        elif style == "shareholders":
            rows = spec.get("shareholders") or []
            t = doc.add_table(rows=len(rows) + 1, cols=4)
            borders(t, rule_top=True, rule_bottom=True)
            widths(t, (usable - 84, 26, 26, 32))
            from docx.enum.text import WD_ALIGN_PARAGRAPH as A
            form = bare_form(spec)
            heads = w.get("sh_cols_sa") if form in ("SA", "SAU") and w.get("sh_cols_sa") else (
                w.get("sh_cols_srl") if form in ("SRL", "SRLS") and w.get("sh_cols_srl") else w["sh_cols"])
            for c, head in enumerate(heads):
                cell_text(t.cell(0, c), head, size=8.5, grey=True, align=A.RIGHT if c in (1, 2) else None)
            for r, row in enumerate(rows, 1):
                vals = [row.get("name", ""), letter.number(row.get("shares", 0), loc) if row.get("shares") is not None else "",
                        letter.number(row.get("votes", row.get("shares", 0)), loc) if row.get("votes", row.get("shares")) is not None else "",
                        row.get("by", "")]
                for c, v in enumerate(vals):
                    cell_text(t.cell(r, c), v, size=9.5, align=A.RIGHT if c in (1, 2) else None)
            doc.add_paragraph().paragraph_format.space_after = Pt(0)
        elif style == "decision":
            p = doc.add_paragraph()
            p.add_run(text).bold = True
        elif style == "para":
            doc.add_paragraph(text)
        elif style == "sign":
            # Signatures two to a row, a line to sign on, the name under it and the role under that.
            t = doc.add_table(rows=(len(signs) + 1) // 2, cols=2)
            t.alignment = WD_TABLE_ALIGNMENT.LEFT
            borders(t)
            widths(t, (usable / 2, usable / 2))
            for k, (role, name) in enumerate(signs):
                cell = t.cell(k // 2, k % 2)
                p = cell.paragraphs[0]
                p.paragraph_format.space_before = Pt(30)
                p.paragraph_format.space_after = Pt(8)
                p.paragraph_format.line_spacing = 1.1
                r = p.add_run("_" * 34)
                r.font.color.rgb = RGBColor(*MUTED)
                r.add_break()
                n = p.add_run(name)
                n.bold = True
                n.add_break()
                g = p.add_run(role)
                g.font.size = Pt(9)
                g.font.color.rgb = RGBColor(*MUTED)
            i = len(parts)
            continue
        i += 1
    doc.save(out)


def main(argv):
    if len(argv) != 3:
        print(__doc__.split("\n\n")[1])
        return 2
    spec = json.loads(Path(argv[1]).read_text())
    out = Path(argv[2])
    if out.suffix.lower() != ".docx":
        raise SystemExit("output must end in .docx")
    # Nothing given is dropped: an unknown key or a value of the wrong shape stops the build here.
    spec_guard.guard(spec, HERE.parent / "spec.fields.json", "minutes data file")
    spec_guard.output_guard(out, __file__, "minutes")
    # The company's own particulars, written once in the person's folder: what the data file leaves out.
    company.apply(spec, argv[1], "meeting-minutes")
    missing = [k for k in REQUIRED if not spec.get(k)]
    if missing:
        raise SystemExit("the spec needs %s" % ", ".join(missing))
    lost = not_printed(spec)
    if lost:
        raise SystemExit("the minutes data file holds what these minutes have no line for; nothing was built:\n  - %s\n"
                         "Write each as a line of the top-level \"notes\", in the minutes' language, or take the "
                         "key out and say in your reply what was left off." % "\n  - ".join(lost))
    write_docx(spec, out)
    loc = locale_of(spec)
    summary = {"file": str(out), "language": loc, "law": country_of(spec, loc) or "none (a club or association)",
               "items": len(spec["items"]), "motions": sum(len(i.get("motions", [])) for i in spec["items"]),
               "signatures": [n for _, n in signers(spec, loc)]}
    if country_of(spec, loc) == "AT" and kind_of(spec) == "general" and form_of(spec).upper() in ("AG", "SE"):
        summary["say"] = ("An Aktiengesellschaft's general meeting is valid only as a notary records it (AktG § 120); "
                          "this file is a working record, not that Niederschrift. Say so in your reply.")
    by_notary = notarial(spec, loc)
    if by_notary:
        summary["say"] = "%s: %s; this file is a working record, not the notary's. Say so in your reply." % by_notary
    print(json.dumps(summary, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
