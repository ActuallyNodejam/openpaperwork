#!/usr/bin/env python3
"""Write a written statement of the terms of employment as Word from a JSON spec.

Usage: statement_create.py spec.json statement.docx

Spec (templates/ has one for each law below):
{
  "law": "uk",                       # whose list it follows (see LAWS below)
  "language": "en",                  # en, sv, nb, da, fi, fr, nl, de, es, it or pl; left out, the law's own
                                     #   (Belgium: the region's, from the workplace's postcode)
  "given": "2026-11-02",             # the date the statement is given
  "employer": {"name": "...", "number": "Company number ...", "address": "...", "signatory": "Name, title",
               "operating_name": "...", "phone": "..."},     # operating_name: a trade or "doing business as" name
  "worker": {"name": "...", "address": "..."},
  "place": "the workplace's address",  # or {"various": true, "note": "..."} or {"free": true}
  "job": {"title": "...", "description": "..."},
  "start": "2026-11-02", "continuous_from": "2026-11-02",       # continuous_from: UK, defaults to start
  "term": {"type": "permanent"},     # or {"type": "fixed", "end": "2027-01-10", "kind": "vikariat", "basis": "...",
                                     #     "note": "..."}, or {"type": "fixed", "expected": "until ..."};
                                     # US {"type": "at-will"}; Australia "full-time", "part-time" or "casual",
                                     # or a fixed term with "renewal": {"times": 1, "latest_end": "2028-06-30"}
  "agency": null,                    # or {"user_undertakings": ["..."]}
  "probation": {"months": 6, "conditions": "..."},           # or {"weeks": 4, ...}, or null
  "training": null, "leave": "...", "termination": "...",
  "pay": {"amount": 13.0, "currency": "GBP", "per": "hour", "paid": "weekly, every Friday",
          "method": "bank transfer to the worker's account", "overtime_rate": "...", "other_pay": "...",
          "components": [{"name": "Sunday premium", "text": "GBP 1.50 an hour on top for hours worked on a Sunday"}]},
  "hours": {"pattern": "fixed", "standard": "...", "overtime": "...", "shifts": "...", "schedule_notice": "..."},
        # or {"pattern": "variable", "guaranteed": "...", "extra_pay": "...", "reference": "...", "notice": "...",
        #     "cancellation": "..."}
  "collective": null, "social_security": "...", "sickness": "...", "pension": "...", "benefits": "...",
  "other_leave": "...", "disciplinary": {...},                  # UK: ERA s.1(4)(d)(iia) and s.3
  "breaks": "...", "special_hours": null,                       # Norway: arbeidsmiljøloven 14-6 (1) k and l
  "insurance": {"pension": "...", "accident": "..."},           # Finland: työsopimuslaki 2:4 § 3 mom. 15
  "qualifications": "...", "deductions": "...", "expenses": "...",   # Canada: CLSR 3.1 (g), (l), (m)
  "contact": {"address": "...", "phone": "...", "names": ["..."]},  # Ontario: O. Reg. 285/01 s. 1.2 (2) 2
  "flsa": {"status": "non-exempt"},  # US: or {"status": "exempt", "exemption": "administrative"}
  "work_state": "NY", "state_notice": {...},                    # US: New York or California pay notice
  "award": "...", "super": "...",                               # Australia
  "on_call": false, "pension": false,                           # Netherlands: BW 7:655 (1) o and j, always answered
  "grading": "...", "insurance": {"social_insurer": "...", "bv_kasse": "..."},   # Austria: AVRAG § 2 (2) 7 and 13
  "hours": {"per_day": "8", "per_week": "39", "schedule": "...", "breaks": "...", "rest_days": "..."},
        # per_day and per_week: Ireland's s.3(1A)(e); schedule, breaks and rest days: Belgium's art. 4 § 2 8° a)
  "pay": {"reference_period": "..."},                           # Ireland: the National Minimum Wage Act pay reference period
  "tips": "...",                                                # Ireland: s.3(1A)(f), where the Payment of Wages Act applies
  "job": {"group": "..."},                                      # Spain: art. 3.2 e), the professional group; Italy: d)
  "algorithms": null, "equality": "...", "changes": "...",      # Spain: Real Decreto 723/2026 art. 3.2 k), l) and m), q)
  "collective": {"name": "...", "code": "...", "published": "...", "validity": "...", "parties": "..."},
        # Spain: art. 3.2 o), the code, the bulletin and date, the validity; Italy: q) the signatories, q-bis) the CNEL code
  "contract_date": "2026-10-26", "rules": "...",                # Poland: art. 29 § 1 and § 3 pkt 1 m) (regulamin pracy)
  "hours": {"basis": "pełny etat", "norm": "..."},              # Poland: art. 29 § 1 pkt 4 and § 3 pkt 1 a)
  "abroad": null                     # or {"countries": ["Poland"], "from": "...", "to": "...", "currency": "SEK",
                                     #     "benefits": "...", "repatriation": "...", "certificates": "...",
                                     #     "posted": {"host_pay": "...", "allowances": "...", "website": "..."}}
}

LAWS, and where each one's list comes from:
  eu  Directive (EU) 2019/1152 Art. 4(2) (a) to (o), EUR-Lex CELEX 32019L1152, Commission Decision 2011/833/EU
  uk  Employment Rights Act 1996 ss.1 to 3, Open Government Licence v3.0
  se  lagen (1982:80) om anställningsskydd 6 c §, outside copyright (upphovsrättslagen 9 §)
  no  arbeidsmiljøloven (LOV-2005-06-17-62) §§ 14-5, 14-6 and 14-7, as in force from 1 July 2024 (lov 15 des 2023
      nr. 88); outside copyright (åndsverkloven § 14)
  dk  lov nr. 501 af 16. maj 2023 om ansættelsesbeviser og visse arbejdsvilkår §§ 3, 4 and 6; outside copyright
      (ophavsretsloven § 9)
  fi  työsopimuslaki (55/2001) 1 luku 4 § and 2 luku 4 §, Finlex consolidated text; outside copyright
      (tekijänoikeuslaki 9 §)
  us  an offer letter: no federal law asks for one. The Fair Labor Standards Act's overtime rule (29 U.S.C. 207(a)(1))
      and exemptions (29 U.S.C. 213(a)(1), 29 CFR part 541), and the state pay notices of New York Labor Law
      § 195(1) and California Labor Code § 2810.5; US public law
  ca  Canada Labour Code s. 253.2 and Canada Labour Standards Regulations s. 3.1 (a) to (m), reproduced under the
      Reproduction of Federal Law Order; English and French
  on  Ontario Regulation 285/01 s. 1.2 under the Employment Standards Act, 2000 (© King's Printer for Ontario, 2024)
  au  Fair Work Act 2009 (Cth) ss. 125, 125B, 333E and 333K for the information statements and fixed terms, s. 323
      for pay; restated, nothing copied
  be  loi du 7 octobre 2022 / wet van 7 oktober 2022 (Directive (EU) 2019/1152), arts. 4 to 6, in French or Dutch
      by region (Flemish decree of 19 July 1973, French Community decree of 30 June 1982); Justel, outside copyright
      (Code de droit économique art. XI.172 § 2)
  nl  Burgerlijk Wetboek Boek 7 art. 655 (and 652 for probation), wetten.overheid.nl, outside copyright
      (Auteurswet art. 11)
  at  Arbeitsvertragsrechts-Anpassungsgesetz (AVRAG) § 2, as amended by BGBl. I Nr. 11/2024: the Dienstzettel;
      RIS, outside copyright (UrhG § 7)
  ie  Terms of Employment (Information) Act 1994 ss. 3, 3A, 4 and 6D, as amended by S.I. No. 686 of 2022: the core
      terms within five days (s. 3(1A)), the rest within a month (s. 3(1)); Oireachtas (Open Data) PSI Licence
  es  Real Decreto 723/2026, de 9 de septiembre, arts. 3, 4, 6 and 7 (in force 5 October 2026; it develops
      Estatuto de los Trabajadores art. 8.5 and repealed Real Decreto 1659/1998): the information is due before
      the employment begins; BOE consolidated text, informative only (Ley de Propiedad Intelectual art. 13)
  it  decreto legislativo 26 maggio 1997, n. 152 arts. 1 and 2 as in force from 28 June 2026 (D.Lgs. 104/2022,
      D.L. 48/2023, D.L. 62/2026); Normattiva, outside copyright (legge 633/1941 art. 5)
  pl  Kodeks pracy art. 29 § 1 (the contract's own terms, repeated here) and § 3 (the information, within 7 days
      of admission to work), art. 29(1) for work abroad; ISAP, outside copyright (ustawa o prawie autorskim art. 4)
- An item that does not apply is written "Not applicable" with the reason (ERA s.2(1) asks the same).
- Dates and numbers: Unicode CLDR for the language and market (skills/_shared/letter.py); paper A4, or US Letter in
  the United States and Canada.
- Every key the builder reads is in spec.fields.json beside SKILL.md. A key that is not there, a value of another
  shape, or an item the chosen law's list has no heading for stops the build with the key's name
  (skills/_shared/spec_guard.py): nothing given is left off the page. A term that has no field of its own goes in
  "further": ["one line each"], printed under a last heading before the signatures; a particular of the employer
  (its registered office, a second number) in "employer": {"further": ["..."]}, printed with the parties.
The script writes what the spec says. It never works out a notice period, holiday days, a minimum wage or an
overtime rate. Prints a JSON summary. Needs python-docx.
"""
import datetime as dt
import json
import sys
from decimal import Decimal
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / "_shared"))
import letter  # noqa: E402
import company  # noqa: E402
import spec_guard  # noqa: E402

FONT = "Arial"
EU_ORDER = ["parties", "place", "job", "start", "term", "agency", "probation", "training", "leave", "termination",
            "pay", "hours", "collective", "social"]
LAWS = {
    "eu": {"order": EU_ORDER, "lang": "en"},
    "se": {"order": EU_ORDER, "lang": "sv"},
    "uk": {"order": ["parties", "start", "job", "place", "term", "probation", "pay", "hours", "leave", "other_leave",
                     "sickness", "pension", "benefits", "termination", "collective", "training", "disciplinary"],
           "lang": "en"},
    # arbeidsmiljøloven § 14-6 (1) a to q, in the law's order
    "no": {"order": ["parties", "place", "job", "start", "term", "probation", "leave", "termination", "pay", "hours",
                     "breaks", "special_hours", "overtime", "collective", "agency", "training", "social"],
           "lang": "nb"},
    # ansættelsesbevisloven § 3, stk. 2, nr. 1 to 15
    "dk": {"order": ["parties", "place", "job", "start", "term", "agency", "probation", "leave", "termination", "pay",
                     "hours", "training", "collective", "social"], "lang": "da"},
    # työsopimuslaki 2:4 § 3 mom. 1 to 15
    "fi": {"order": ["parties", "start", "term", "probation", "place", "job", "pay", "hours", "agency", "training",
                     "leave", "termination", "collective", "insurer"], "lang": "fi"},
    "us": {"order": ["parties", "job", "start", "place", "term", "classification", "pay", "hours", "leave", "benefits",
                     "conditions"], "lang": "en"},
    # Canada Labour Standards Regulations 3.1 (a) to (m)
    "ca": {"order": ["parties", "job", "place", "start", "term", "probation", "qualifications", "training", "hours",
                     "pay", "deductions", "expenses"], "lang": "en"},
    # O. Reg. 285/01 s. 1.2 (2) 1 to 6, with the job and start date
    "on": {"order": ["parties", "contact", "job", "start", "place", "pay", "hours"], "lang": "en"},
    "au": {"order": ["parties", "job", "place", "start", "term", "probation", "award", "pay", "hours", "leave",
                     "termination", "super", "statements"], "lang": "en"},
    # loi du 7 octobre 2022 art. 4 § 2 1° to 9°, then art. 5 1° to 5°
    "be": {"order": ["parties", "place", "job", "start", "term", "pay", "probation", "hours", "training", "leave",
                     "termination", "collective", "social"], "lang": "fr"},
    # BW 7:655 lid 1 a to s
    "nl": {"order": ["parties", "place", "job", "start", "term", "leave", "termination", "pay", "hours", "pension",
                     "collective", "agency", "on_call", "probation", "training", "social"], "lang": "nl"},
    # AVRAG § 2 (2) Z 1 to 15
    "at": {"order": ["parties", "start", "term", "termination", "place", "grading", "job", "pay", "leave", "hours",
                     "collective", "insurer", "probation", "training"], "lang": "de"},
    # Terms of Employment (Information) Act 1994 s. 3(1A) (a) to (k), then s. 3(1) (fa) to (q)
    "ie": {"order": ["parties", "place", "job", "start", "term", "probation", "pay", "hours", "leave", "sickness",
                     "pension", "termination", "collective", "training", "agency", "social", "minimum_wage"],
           "lang": "en"},
    # Real Decreto 723/2026 art. 3.2 a) to q)
    "es": {"order": ["parties", "start", "term", "place", "job", "pay", "hours", "leave", "probation", "training",
                     "agency", "algorithms", "equality", "termination", "collective", "social", "changes"], "lang": "es"},
    # D.Lgs. 152/1997 art. 1 c. 1 a) to s)
    "it": {"order": ["parties", "place", "job", "start", "term", "agency", "probation", "training", "leave",
                     "termination", "pay", "hours", "collective", "social", "algorithms"], "lang": "it"},
    # Kodeks pracy art. 29 § 1 (the contract's terms), then § 3 pkt 1 a) to m) and pkt 2
    "pl": {"order": ["parties", "term", "job", "place", "pay", "hours", "start", "probation", "leave", "termination",
                     "training", "collective", "rules", "social"], "lang": "pl"},
}
EXTRA = ["agency", "social", "sickness", "pension", "benefits"]   # written beyond the law's list when the spec gives them
# The heading over "further", the terms the data file gives that no item of the law's list holds.
FURTHER_HEAD = {"en": "Further particulars", "sv": "Övriga uppgifter", "nb": "Øvrige opplysninger",
                "da": "Øvrige oplysninger", "fi": "Muut tiedot", "fr": "Autres informations",
                "nl": "Overige gegevens", "de": "Weitere Angaben", "es": "Otros datos",
                "it": "Altre informazioni", "pl": "Pozostałe informacje"}
# Keys that are not items of a list and are read under one law only.
ONE_LAW = {"continuous_from": ("uk",), "tips": ("ie",), "contract_date": ("pl",), "flsa": ("us",),
           "work_state": ("us",), "state_notice": ("us",)}
LOCALE = {"sv": "sv-SE", "nb": "nb-NO", "no": "nb-NO", "nn": "nb-NO", "da": "da-DK", "fi": "fi-FI", "fr": "fr-CA",
          "nl": "nl-NL", "de": "de-DE", "es": "es-ES", "it": "it-IT", "pl": "pl-PL"}
LAW_LOCALE = {("be", "fr"): "fr-BE", ("be", "nl"): "nl-BE", ("nl", "nl"): "nl-NL", ("at", "de"): "de-AT",
              ("ie", "en"): "en-IE"}
EN_LOCALE = {"us": "en-US", "ca": "en-CA", "on": "en-CA", "au": "en-AU", "ie": "en-IE"}
MONTHS = {"en": ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October",
                 "November", "December"],
          "fr": ["janvier", "février", "mars", "avril", "mai", "juin", "juillet", "août", "septembre", "octobre",
                 "novembre", "décembre"]}

EN = {
    "title": {"uk": "Written statement of employment particulars",
              "eu": "Statement of the essential terms of employment",
              "se": "Statement of the terms of employment",
              "no": "Written employment contract",
              "dk": "Statement of the terms of employment",
              "fi": "Statement of the principal terms of work",
              "us": "Offer of employment",
              "ca": "Employment statement",
              "on": "Employment information",
              "au": "Statement of employment terms",
              "ie": "Statement of terms of employment",
              "be": "Information on the employment relationship", "nl": "Statement of the terms of employment",
              "at": "Statement of the terms of employment (Dienstzettel)",
              "es": "Information on the essential terms of the employment contract",
              "it": "Information on the employment relationship",
              "pl": "Information on the terms of employment"},
    "basis": {"uk": "Given under section 1 of the Employment Rights Act 1996.",
              "eu": "The essential aspects of the employment relationship listed in Article 4 of Directive (EU) 2019/1152.",
              "se": "Information on the terms of employment under section 6 c of the Swedish Employment Protection "
                    "Act (lagen (1982:80) om anställningsskydd).",
              "no": "The written employment contract under sections 14-5 and 14-6 of the Norwegian Working Environment "
                    "Act (arbeidsmiljøloven).",
              "dk": "Information on the terms of employment under section 3 of the Danish Act on Employment Statements "
                    "(lov nr. 501 af 16. maj 2023 om ansættelsesbeviser og visse arbejdsvilkår).",
              "fi": "Given under chapter 2, section 4 of the Finnish Employment Contracts Act (työsopimuslaki 55/2001).",
              "us": "This letter sets out the terms on which we offer you employment.",
              "ca": "Given under section 253.2 of the Canada Labour Code and section 3.1 of the Canada Labour "
                    "Standards Regulations.",
              "on": "Given under section 1.2 of Ontario Regulation 285/01 under the Employment Standards Act, 2000.",
              "au": "The terms of employment, given with the Fair Work Information Statement (Fair Work Act 2009 s 125).",
              "ie": "Given under sections 3 and 3A of the Terms of Employment (Information) Act 1994. The core terms of "
                    "section 3(1A) are due within five days of the start, the rest within one month.",
              "be": "Information under articles 4 to 6 of the Belgian law of 7 October 2022 transposing Directive (EU) "
                    "2019/1152.",
              "nl": "Given under article 7:655 of the Dutch Civil Code (Burgerlijk Wetboek).",
              "at": "Given under section 2 of the Austrian Employment Contract Law Adaptation Act (AVRAG).",
              "es": "Information under article 8.5 of the Spanish Workers' Statute and article 3 of Real Decreto "
                    "723/2026 of 9 September.",
              "it": "Information under article 1 of the Italian decreto legislativo 26 maggio 1997, n. 152.",
              "pl": "Information under article 29 § 3 of the Polish Labour Code (Kodeks pracy), with the terms of the "
                    "contract under article 29 § 1."},
    "given": "Date of this statement: %s.", "as_at": "The particulars are given as at this date.",
    "given_us": "Date of this letter: %s.",
    "heads": {"parties": "The parties", "place": "Place of work", "job": "Job title and duties",
              "start": "Start date", "term": "Type and length of employment",
              "agency": "User undertakings (agency work)", "probation": "Probation", "training": "Training",
              "leave": "Paid leave", "other_leave": "Other paid leave", "termination": "Ending the employment",
              "pay": "Pay", "hours": "Working hours", "breaks": "Breaks",
              "special_hours": "Special working-time arrangement",
              "overtime": "Shift changes and work beyond agreed hours", "collective": "Collective agreements",
              "social": "Social security", "sickness": "Sickness and sick pay", "pension": "Pensions",
              "benefits": "Other benefits", "disciplinary": "Disciplinary and grievance procedures",
              "insurer": "Pension and accident insurance", "qualifications": "Qualifications",
              "deductions": "Mandatory deductions", "expenses": "Work-related expenses",
              "contact": "Employer contact", "classification": "Overtime classification",
              "conditions": "Conditions of this offer", "super": "Superannuation", "award": "Award or agreement",
              "statements": "Information statements", "abroad": "Work abroad", "sign": "Signatures",
              "minimum_wage": "Average hourly rate of pay", "tips": "Tips, gratuities and service charges",
              "grading": "Grading", "on_call": "On-call contract",
              "algorithms": "Automated decision-making and monitoring systems",
              "equality": "Equality plan and protocol against harassment",
              "changes": "Changes to the terms", "rules": "Work regulations"},
    "law_heads": {"uk": {"leave": "Holidays and holiday pay"},
                  "us": {"term": "Employment relationship", "leave": "Paid time off", "sign": "Signatures"},
                  "ca": {"term": "Term of employment", "probation": "Probationary period",
                         "training": "Required training", "hours": "Hours of work and overtime",
                         "pay": "Wages and pay days"},
                  "on": {"place": "Where the work is", "pay": "Wages and pay days", "hours": "Hours of work"},
                  "au": {"term": "Type of employment", "leave": "Leave", "termination": "Notice of termination"},
                  "ie": {"leave": "Paid leave", "sickness": "Sick leave and sick pay", "social": "Social insurance",
                         "termination": "Notice"}},
    "employer": "Employer", "worker": "Worker", "employee": "Employee",
    "operating": "operating as %s", "dba": "doing business as %s",
    "various": "The worker is employed at various places", "free": "The worker is free to decide where to work",
    "seat": "The employer's registered place of business: %s.",
    "starts": "The employment begins on %s.", "starts_us": "Your employment begins on %s.",
    "continuous": "The worker's period of continuous employment began on %s.",
    "permanent": "Permanent: the employment continues until further notice.",
    "permanent_probation": "Permanent: the employment continues until further notice, beginning with the "
                           "probationary period below.",
    "fixed": "Fixed term: from %s to %s.", "fixed_kind": "Fixed term (%s): from %s to %s.",
    "expected": "Fixed term%s: from %s, expected to last %s.", "basis_temp": "Reason for the fixed term: %s.",
    "at_will": "Your employment is at will: you or the Company may end it at any time, with or without cause or "
               "notice. Nothing in this letter is a promise of employment for any period.",
    "au_type": {"full-time": "Full-time employment, ongoing.", "part-time": "Part-time employment, ongoing.",
                "casual": "Casual employment (Fair Work Act 2009 s 15A)."},
    "na": "Not applicable: %s.",
    "na_reason": {"agency": "the worker is not a temporary agency worker",
                  "probation": "there is no probationary period",
                  "training": "the employer provides no training entitlement",
                  "collective": "no collective agreement governs this employment",
                  "social": "the employer pays no social contributions itself and provides no further cover",
                  "other_leave": "there is no other paid leave",
                  "special_hours": "no special working-time arrangement is agreed",
                  "overtime": "no shift changes or work beyond the agreed hours are arranged",
                  "award": "no modern award or enterprise agreement covers this employment",
                  "conditions": "the offer has no conditions",
                  "grading": "no general pay or job classification applies",
                  "tips": "the employer receives no tips, gratuities or mandatory charges",
                  "other": "there are no terms on this"},
    "agency": "The worker is placed with: %s.",
    "probation": "%s from the start of the employment.", "conditions": "Conditions: %s",
    "unit": {"month": ("month", "months"), "week": ("week", "weeks")},
    "basic": "Basic pay: %s", "element": "%s: %s", "paid": "Paid: %s.", "method": "Method of payment: %s.",
    "overtime_rate": "Overtime rate: %s", "other_pay": "Other pay is paid: %s",
    "per": {"hour": "an hour", "week": "a week", "month": "a month", "year": "a year", "fortnight": "a fortnight"},
    "standard": "Normal working time: %s", "overtime": "Overtime: %s", "shifts": "Shift changes: %s",
    "schedule_notice": "Advance notice of working times: %s",
    "variable": "The work schedule is variable.", "guaranteed": "Guaranteed paid hours: %s",
    "extra_pay": "Pay for hours beyond those guaranteed: %s",
    "reference": "Reference hours and days within which work may be required: %s",
    "notice": "Minimum notice before a work assignment: %s",
    "cancellation": "Deadline for cancelling an assignment: %s",
    "countries": "Country: %s", "period": "Period abroad: %s to %s (%s)",
    "weeks": ("week", "weeks"), "days": ("day", "days"),
    "currency": "Currency of pay while abroad: %s", "abroad_benefits": "Benefits in cash or kind: %s",
    "repatriation": "Return home: %s", "host_pay": "Pay under the host country's law: %s",
    "allowances": "Allowances for the posting and travel, board and lodging: %s",
    "website": "The host country's official website on posting: %s",
    "certificates": "Certificates for the posting: %s",
    "insurer_pension": "Pension insurance: %s", "insurer_accident": "Accident and occupational disease insurance: %s",
    "contact_address": "Address: %s", "contact_phone": "Telephone: %s", "contact_names": "Contact: %s",
    "per_day": "Hours the employer reasonably expects the employee to work per normal working day: %s",
    "per_week": "Hours the employer reasonably expects the employee to work per normal working week: %s",
    "schedule": "Working schedule: %s", "breaks_line": "Rest breaks: %s", "rest_days": "Regular days off: %s",
    "reference_period": "Pay reference period (National Minimum Wage Act 2000): %s",
    "minimum_wage_text": "Under section 23 of the National Minimum Wage Act 2000 the employee may ask the employer for a "
                         "written statement of their average hourly rate of pay for any pay reference period.",
    "on_call_no": "No: this is not an on-call contract.", "on_call_yes": "Yes: this is an on-call contract.",
    "pension_no": "The worker does not take part in a pension scheme.", "pension_yes": "Pension scheme: %s",
    "agency_no": "No: this is not a temporary agency or payroll contract.",
    "agency_nl": "Temporary agency contract (BW 7:690); the user undertaking: %s.",
    "insurer_social": "Social insurance institution: %s", "insurer_bv": "Employee provision fund (BV-Kasse): %s",
    "col": {"name": "Collective agreement: %s", "parties": "Signed by: %s", "code": "Code: %s",
            "published": "Published: %s", "validity": "Period of validity: %s", "copy": "Where to read it: %s"},
    "group": "Grade or professional group: %s", "contract": "Contract concluded on %s.",
    "hours_basis": "Working time basis: %s", "norm": "Daily and weekly norm of working time: %s",
    "housing": "Housing: %s", "social_insurance": "Social insurance while abroad: %s",
    "disc": {"rules": "Disciplinary rules: %s", "procedure": "Disciplinary and dismissal procedure: %s",
             "appeal_to": "Appeals against a disciplinary or dismissal decision go to: %s",
             "grievance_to": "Grievances go to: %s", "steps": "Further steps: %s"},
    "flsa_nonexempt": "This position is non-exempt under the Fair Labor Standards Act: hours worked over 40 in a "
                      "workweek are paid at one and one-half times the regular rate (29 U.S.C. 207(a)(1)).",
    "flsa_exempt": "This position is exempt from overtime under the Fair Labor Standards Act (29 U.S.C. 213(a)(1)%s).",
    "fwis": "A copy of the Fair Work Information Statement is given with this statement (Fair Work Act 2009 s 125).",
    "ceis": "A copy of the Casual Employment Information Statement is given with this statement (s 125B).",
    "ftcis": "A copy of the Fixed Term Contract Information Statement is given with this statement (s 333K).",
    "ny": {"head": "Notice of pay rate and pay day (New York Labor Law § 195(1))",
           "rate": "Rate of pay and basis: %s", "overtime_rate": "Overtime rate of pay: %s",
           "allowances": "Allowances claimed as part of the minimum wage: %s", "payday": "Regular pay day: %s",
           "legal_name": "Employer's name: %s", "dba": "Doing business as: %s",
           "physical_address": "Physical address of the main office or principal place of business: %s",
           "mailing_address": "Mailing address: %s", "phone": "Employer's telephone: %s",
           "language": "Primary language the employee identified: %s",
           "ack": "Acknowledgment: I received this notice of my pay rate and pay day on the date below, and I "
                  "identified my primary language to my employer as written above."},
    "ca_notice": {"head": "Notice to employee (California Labor Code § 2810.5)",
                  "rate": "Rate or rates of pay and basis, with overtime rates: %s",
                  "allowances": "Allowances claimed as part of the minimum wage: %s",
                  "payday": "Regular payday: %s", "legal_name": "Employer's name: %s",
                  "dba": "Doing business as: %s",
                  "physical_address": "Physical address of the main office or principal place of business: %s",
                  "mailing_address": "Mailing address: %s", "phone": "Employer's telephone: %s",
                  "comp_carrier": "Workers' compensation insurance carrier (name, address, telephone): %s",
                  "sick_leave": "Paid sick leave: %s",
                  "disaster": "Federal or state emergency or disaster declaration for the county of work, issued "
                              "within 30 days before the first day of work: %s"},
    "none": "None",
    "sign_employer": "For the employer", "sign_worker": "Received by the worker", "sign_date": "Date",
    "law_sign": {"us": ("For the Company", "Accepted by"), "ca": ("For the employer", "Received by the employee"),
                 "on": ("For the employer", "Received by the employee"),
                 "au": ("For the employer", "Received by the employee"),
                 "no": ("For the employer", "Employee"),
                 "ie": ("For the employer", "Received by the employee")},
    "law_words": {"ie": {"worker": "Employee",
                         "various": "The employee is employed at various places",
                         "free": "The employee is free to decide where to work",
                         # s. 3(1)(fa) and (m): a registered employment agreement or an employment regulation
                         # order is named with any collective agreement, and where to get a copy
                         "na_reason": {"agency": "the employee is not a temporary agency worker",
                                       "collective": "no collective agreement, registered employment agreement or "
                                                     "employment regulation order applies to this employment"}}},
}

SV = {
    "title": {k: "Anställningsbevis" for k in LAWS},
    "basis": {"uk": "Skriftlig information enligt section 1 i Employment Rights Act 1996.",
              "eu": "Information om anställningsförhållandets väsentliga delar enligt artikel 4 i direktiv "
                    "(EU) 2019/1152.",
              "se": "Information om anställningsvillkoren enligt 6 c § lagen (1982:80) om anställningsskydd."},
    "given": "Datum för anställningsbeviset: %s.", "as_at": "Uppgifterna gäller per detta datum.",
    "heads": {"parties": "Parter", "place": "Arbetsplats", "job": "Arbetsuppgifter och befattning",
              "start": "Tillträdesdag", "term": "Anställningsform", "agency": "Kundföretag (uthyrning)",
              "probation": "Provanställning", "training": "Utbildning", "leave": "Semester",
              "termination": "Uppsägning och anställningens upphörande", "pay": "Lön", "hours": "Arbetstid",
              "collective": "Kollektivavtal", "social": "Social trygghet", "sickness": "Sjukdom och sjuklön",
              "pension": "Pension", "benefits": "Övriga förmåner", "abroad": "Arbete utomlands",
              "sign": "Underskrifter"},
    "law_heads": {},
    "employer": "Arbetsgivare", "worker": "Arbetstagare",
    "various": "Arbetet utförs på olika platser", "free": "Arbetstagaren får själv bestämma sin arbetsplats",
    "seat": "Arbetsgivarens säte och adress: %s.",
    "starts": "Anställningen tillträds den %s.",
    "continuous": "Den sammanhängande anställningstiden räknas från den %s.",
    "permanent": "Tillsvidareanställning.",
    "permanent_probation": "Tillsvidareanställning som inleds med en provanställning, se nedan.",
    "fixed": "Tidsbegränsad anställning från den %s till och med den %s.",
    "fixed_kind": "Tidsbegränsad anställning (%s) från den %s till och med den %s.",
    "expected": "Tidsbegränsad anställning%s från den %s. Anställningen upphör %s.",
    "basis_temp": "Skäl till tidsbegränsningen: %s.",
    "na": "Ej tillämpligt: %s.",
    "na_reason": {"agency": "arbetstagaren hyrs inte ut av ett bemanningsföretag",
                  "probation": "anställningen inleds inte med provanställning",
                  "training": "arbetsgivaren tillhandahåller ingen rätt till utbildning",
                  "collective": "inget kollektivavtal gäller för anställningen",
                  "social": "arbetsgivaren betalar inga sociala avgifter själv och ger inget ytterligare skydd",
                  "other": "det finns inga villkor om detta"},
    "agency": "Arbetstagaren hyrs ut till: %s.",
    "probation": "Provanställning i %s från tillträdesdagen.", "conditions": "Villkor: %s",
    "unit": {"month": ("månad", "månader"), "week": ("vecka", "veckor")},
    "basic": "Begynnelselön: %s", "element": "%s: %s", "paid": "Utbetalning: %s.",
    "method": "Betalningssätt: %s.",
    "per": {"hour": "per timme", "week": "per vecka", "month": "per månad", "year": "per år"},
    "standard": "Normal arbetstid: %s", "overtime": "Övertid och mertid: %s", "shifts": "Skiftbyte: %s",
    "schedule_notice": "Besked om arbetstidens förläggning: %s",
    "variable": "Arbetstiden är varierande.", "guaranteed": "Garanterade betalda timmar: %s",
    "extra_pay": "Ersättning för timmar utöver de garanterade: %s",
    "reference": "Referenstimmar och referensdagar då arbete kan krävas: %s",
    "notice": "Minsta tidsfrist för besked före ett arbetspass: %s",
    "cancellation": "Sista tidpunkt för att ställa in ett arbetspass: %s",
    "countries": "Land: %s", "period": "Tid utomlands: %s till och med %s (%s)",
    "weeks": ("vecka", "veckor"), "days": ("dag", "dagar"),
    "currency": "Valuta för lönen under tiden utomlands: %s",
    "abroad_benefits": "Kontantersättningar och naturaförmåner: %s", "repatriation": "Hemresa: %s",
    "host_pay": "Ersättning och villkor enligt värdlandets lag: %s",
    "allowances": "Ersättning för utstationeringen och för resa, kost och logi: %s",
    "website": "Värdlandets officiella webbplats om utstationering: %s",
    "certificates": "Intyg för utstationeringen: %s",
    "sign_employer": "För arbetsgivaren", "sign_worker": "Mottaget av arbetstagaren", "sign_date": "Ort och datum",
    "law_sign": {},
}

NB = {
    "title": {"no": "Arbeidsavtale"},
    "basis": {"no": "Skriftlig arbeidsavtale etter arbeidsmiljøloven §§ 14-5 og 14-6."},
    "given": "Avtalen er datert %s.",
    "heads": {"parties": "Partene", "place": "Arbeidssted", "job": "Stilling og arbeidsoppgaver",
              "start": "Tiltredelse", "term": "Ansettelsesform", "probation": "Prøvetid",
              "leave": "Ferie og annet betalt fravær", "termination": "Oppsigelse og opphør", "pay": "Lønn",
              "hours": "Arbeidstid", "breaks": "Pauser", "special_hours": "Særlig arbeidstidsordning",
              "overtime": "Vaktendringer og arbeid utover avtalt arbeidstid", "collective": "Tariffavtaler",
              "agency": "Innleier (utleie fra bemanningsforetak)", "training": "Kompetanseutvikling",
              "social": "Sosial trygghet", "sickness": "Sykdom", "pension": "Pensjon",
              "benefits": "Andre ytelser", "abroad": "Arbeid i utlandet", "sign": "Underskrifter"},
    "law_heads": {},
    "employer": "Arbeidsgiver", "worker": "Arbeidstaker",
    "various": "Arbeidstakeren arbeider på forskjellige steder",
    "free": "Arbeidstakeren kan fritt bestemme sitt arbeidssted",
    "seat": "Arbeidsgiverens forretningsadresse: %s.",
    "starts": "Arbeidsforholdet begynner %s.",
    "permanent": "Fast ansettelse.",
    "permanent_probation": "Fast ansettelse med prøvetid, se nedenfor.",
    "fixed": "Midlertidig ansettelse fra %s til og med %s.",
    "fixed_kind": "Midlertidig ansettelse (%s) fra %s til og med %s.",
    "expected": "Midlertidig ansettelse%s fra %s, forventet varighet: %s.",
    "basis_temp": "Grunnlaget for den midlertidige ansettelsen: %s (arbeidsmiljøloven § 14-9).",
    "na": "Ikke aktuelt: %s.",
    "na_reason": {"agency": "arbeidstakeren leies ikke ut fra bemanningsforetak",
                  "probation": "det er ikke avtalt prøvetid",
                  "training": "arbeidsgiveren tilbyr ingen særskilt rett til kompetanseutvikling",
                  "collective": "ingen tariffavtale regulerer arbeidsforholdet",
                  "social": "arbeidsgiveren gir ingen ytelser til sosial trygghet utover de lovpålagte",
                  "special_hours": "det er ikke avtalt særlig arbeidstidsordning",
                  "overtime": "det er ikke avtalt vaktendringer eller arbeid utover avtalt arbeidstid",
                  "other": "det er ikke avtalt noe om dette"},
    "agency": "Arbeidstakeren leies ut til: %s.",
    "probation": "Prøvetid på %s fra tiltredelsen.", "conditions": "Vilkår: %s",
    "unit": {"month": ("måned", "måneder"), "week": ("uke", "uker")},
    "basic": "Lønn ved tiltredelse: %s", "element": "%s: %s", "paid": "Utbetaling: %s.",
    "method": "Utbetalingsmåte: %s.",
    "per": {"hour": "per time", "week": "per uke", "month": "per måned", "year": "per år"},
    "standard": "Avtalt arbeidstid: %s", "overtime": "Arbeid utover avtalt arbeidstid: %s",
    "shifts": "Vaktendringer: %s", "schedule_notice": "Varsel om arbeidsplan: %s",
    "variable": "Arbeidstiden varierer.", "guaranteed": "Garanterte betalte timer: %s",
    "extra_pay": "Betaling for timer utover de garanterte: %s",
    "reference": "Tidsrom (timer og dager) da arbeid kan kreves: %s",
    "notice": "Minste varsel før et arbeidsoppdrag: %s",
    "cancellation": "Frist for å avlyse et arbeidsoppdrag: %s",
    "countries": "Land: %s", "period": "Varighet i utlandet: %s til og med %s (%s)",
    "weeks": ("uke", "uker"), "days": ("dag", "dager"),
    "currency": "Valuta lønnen utbetales i: %s",
    "abroad_benefits": "Kontant- og naturalytelser knyttet til utenlandsarbeidet: %s",
    "repatriation": "Vilkår for hjemreise, herunder utgiftsdekning: %s",
    "host_pay": "Lønn etter vertslandets regler: %s",
    "allowances": "Ytelser knyttet til utsendelsen og dekning av reise, kost og losji: %s",
    "website": "Vertslandets offisielle nettsted om utsending: %s",
    "certificates": "Attester for utsendelsen: %s",
    "sign_employer": "For arbeidsgiver", "sign_worker": "Arbeidstaker", "sign_date": "Sted og dato",
    "law_sign": {},
}

DA = {
    "title": {"dk": "Ansættelsesbevis"},
    "basis": {"dk": "Oplysning om ansættelsesvilkårene efter § 3 i lov om ansættelsesbeviser og visse "
                    "arbejdsvilkår (lov nr. 501 af 16. maj 2023)."},
    "given": "Ansættelsesbeviset er udstedt %s.",
    "heads": {"parties": "Parterne", "place": "Arbejdssted", "job": "Stilling og arbejdsopgaver",
              "start": "Tiltrædelse", "term": "Ansættelsens varighed", "agency": "Brugervirksomhed (vikararbejde)",
              "probation": "Prøvetid", "leave": "Ferie og fravær med løn", "termination": "Opsigelse",
              "pay": "Løn", "hours": "Arbejdstid", "training": "Uddannelse",
              "collective": "Kollektive overenskomster", "social": "Social sikring", "sickness": "Sygdom",
              "pension": "Pension", "benefits": "Øvrige goder", "abroad": "Arbejde i udlandet",
              "sign": "Underskrifter"},
    "law_heads": {},
    "employer": "Arbejdsgiver", "worker": "Lønmodtager",
    "various": "Lønmodtageren er beskæftiget på forskellige steder",
    "free": "Lønmodtageren kan frit bestemme sit arbejdssted",
    "seat": "Arbejdsgiverens hovedsæde og adresse: %s.",
    "starts": "Ansættelsesforholdet begynder %s.",
    "permanent": "Tidsubestemt ansættelse.",
    "permanent_probation": "Tidsubestemt ansættelse, der begynder med en prøvetid, se nedenfor.",
    "fixed": "Tidsbegrænset ansættelse fra %s til og med %s.",
    "fixed_kind": "Tidsbegrænset ansættelse (%s) fra %s til og med %s.",
    "expected": "Tidsbegrænset ansættelse%s fra %s, forventet varighed: %s.",
    "basis_temp": "Baggrund for tidsbegrænsningen: %s.",
    "na": "Ikke relevant: %s.",
    "na_reason": {"agency": "lønmodtageren er ikke vikaransat",
                  "probation": "der er ikke aftalt prøvetid",
                  "training": "arbejdsgiveren tilbyder ingen ret til uddannelse",
                  "collective": "ingen kollektiv overenskomst eller aftale regulerer arbejdsforholdet",
                  "social": "arbejdsgiveren yder ingen social sikring ud over de lovpligtige bidrag",
                  "other": "der er ikke aftalt noget herom"},
    "agency": "Lønmodtageren udsendes til: %s.",
    "probation": "Prøvetid på %s fra tiltrædelsen.", "conditions": "Vilkår: %s",
    "unit": {"month": ("måned", "måneder"), "week": ("uge", "uger")},
    "basic": "Løn ved ansættelsens begyndelse: %s", "element": "%s: %s", "paid": "Udbetalingstermin: %s.",
    "method": "Udbetalingsmåde: %s.",
    "per": {"hour": "pr. time", "week": "pr. uge", "month": "pr. måned", "year": "pr. år"},
    "standard": "Normal arbejdstid: %s", "overtime": "Overarbejde og betaling herfor: %s",
    "shifts": "Vagtændringer: %s", "schedule_notice": "Varsel om tidsplanen for arbejdet: %s",
    "variable": "Tidsplanen for arbejdet er variabel.", "guaranteed": "Garanterede betalte arbejdstimer: %s",
    "extra_pay": "Betaling for arbejde ud over de garanterede timer: %s",
    "reference": "Referencetimer og -dage, hvor der kan pålægges arbejde: %s",
    "notice": "Minimumsvarsel før en arbejdsopgave: %s",
    "cancellation": "Frist for annullering af en arbejdsopgave: %s",
    "countries": "Land: %s", "period": "Arbejde i udlandet: %s til og med %s (%s)",
    "weeks": ("uge", "uger"), "days": ("dag", "dage"),
    "currency": "Valuta, som lønnen udbetales i: %s",
    "abroad_benefits": "Ydelser i kontanter eller naturalier: %s",
    "repatriation": "Tilbagevenden til hjemlandet: %s",
    "host_pay": "Løn efter værtslandets regler: %s",
    "allowances": "Ydelser ved udstationeringen og godtgørelse af rejse, kost og logi: %s",
    "website": "Værtslandets officielle websted om udstationering: %s",
    "certificates": "Attester i forbindelse med udstationeringen: %s",
    "sign_employer": "For arbejdsgiveren", "sign_worker": "Modtaget af lønmodtageren", "sign_date": "Dato",
    "law_sign": {},
}

FI = {
    "title": {"fi": "Selvitys työnteon keskeisistä ehdoista"},
    "basis": {"fi": "Työsopimuslain (55/2001) 2 luvun 4 §:n mukainen selvitys."},
    "given": "Selvitys on annettu %s.",
    "heads": {"parties": "Sopijapuolet", "start": "Työnteon alkaminen", "term": "Työsopimuksen kesto",
              "probation": "Koeaika", "place": "Työntekopaikka", "job": "Työtehtävät", "pay": "Palkka",
              "hours": "Työaika", "agency": "Käyttäjäyritys (vuokratyö)", "training": "Koulutus",
              "leave": "Vuosiloma", "termination": "Irtisanomisaika", "collective": "Työehtosopimus",
              "insurer": "Eläke- ja tapaturmavakuutus", "social": "Sosiaaliturva", "sickness": "Sairausajan palkka",
              "pension": "Eläke", "benefits": "Muut edut", "abroad": "Ulkomaantyö", "sign": "Allekirjoitukset"},
    "law_heads": {},
    "employer": "Työnantaja", "worker": "Työntekijä",
    "various": "Työntekijällä ei ole pääasiallista kiinteää työntekopaikkaa, ja hän työskentelee eri työkohteissa",
    "free": "Työntekijä voi itse määrittää työntekopaikkansa",
    "seat": "Työnantajan liikepaikka: %s.",
    "starts": "Työnteko alkaa %s.",
    "permanent": "Toistaiseksi voimassa oleva työsopimus.",
    "permanent_probation": "Toistaiseksi voimassa oleva työsopimus, jonka alussa on koeaika, ks. alla.",
    "fixed": "Määräaikainen työsopimus %s–%s.",
    "fixed_kind": "Määräaikainen työsopimus (%s) %s–%s.",
    "expected": "Määräaikainen työsopimus%s %s alkaen, arvioitu päättymisaika: %s.",
    "basis_temp": "Määräaikaisuuden peruste: %s.",
    "na": "Ei sovelleta: %s.",
    "na_reason": {"agency": "kyse ei ole vuokratyöstä",
                  "probation": "koeajasta ei ole sovittu",
                  "training": "työnantaja ei tarjoa koulutusta",
                  "collective": "työhön ei sovelleta työehtosopimusta",
                  "social": "työnantaja ei järjestä lakisääteisen lisäksi muuta sosiaaliturvaa",
                  "other": "tästä ei ole sovittu"},
    "agency": "Käyttäjäyritys: %s.",
    "probation": "Koeaika %s työnteon alkamisesta.", "conditions": "Ehdot: %s",
    "unit": {"month": ("kuukausi", "kuukautta"), "week": ("viikko", "viikkoa")},
    "basic": "Palkka: %s", "element": "%s: %s", "paid": "Palkanmaksukausi: %s.", "method": "Maksutapa: %s.",
    "per": {"hour": "tunnilta", "week": "viikossa", "month": "kuukaudessa", "year": "vuodessa"},
    "standard": "Säännöllinen työaika: %s", "overtime": "Lisä- ja ylityö: %s", "shifts": "Vuoronvaihdot: %s",
    "schedule_notice": "Työvuoroluettelon ilmoittaminen: %s",
    "variable": "Työntekijä noudattaa vaihtelevaa työaikaa.",
    "guaranteed": "Missä tilanteissa ja missä määrin työvoiman tarvetta syntyy: %s",
    "extra_pay": "Korvaus sovitun työajan ylittävästä työstä: %s",
    "reference": "Viikonpäivät ja kellonajat, joina työtä voidaan teettää ilman erillistä suostumusta "
                 "(työaikalaki 30 a §): %s",
    "notice": "Työvuoroista ilmoittaminen: %s", "cancellation": "Työvuoron peruminen: %s",
    "countries": "Maa: %s", "period": "Ulkomaantyön kesto: %s–%s (%s)",
    "weeks": ("viikko", "viikkoa"), "days": ("päivä", "päivää"),
    "currency": "Rahapalkan valuutta: %s",
    "abroad_benefits": "Ulkomailla maksettavat rahalliset korvaukset ja luontoisedut: %s",
    "repatriation": "Kotiuttamisen ehdot: %s",
    "host_pay": "Vastaanottavan valtion lainsäädännön mukainen palkka: %s",
    "allowances": "Lähettämisestä maksettavat lisät sekä matka-, majoitus- ja ruokailukulujen korvaukset: %s",
    "website": "Vastaanottavan valtion virallinen verkkosivusto: %s",
    "certificates": "Lähettämiseen liittyvät todistukset: %s",
    "insurer_pension": "Työeläkevakuutus: %s", "insurer_accident": "Työtapaturma- ja ammattitautivakuutus: %s",
    "sign_employer": "Työnantajan puolesta", "sign_worker": "Vastaanottanut työntekijä",
    "sign_date": "Paikka ja päiväys",
    "law_sign": {},
}

FR = {
    "title": {"ca": "Déclaration d'emploi", "on": "Renseignements sur l'emploi",
              "be": "Informations sur la relation de travail"},
    "basis": {"ca": "Déclaration remise en application de l'article 253.2 du Code canadien du travail et de "
                    "l'article 3.1 du Règlement du Canada sur les normes du travail.",
              "on": "Renseignements remis en application de l'article 1.2 du Règlement de l'Ontario 285/01 pris en "
                    "vertu de la Loi de 2000 sur les normes d'emploi.",
              "be": "Informations sur les principaux aspects de la relation de travail données en application des "
                    "articles 4 à 6 de la loi du 7 octobre 2022 transposant partiellement la directive (UE) 2019/1152."},
    "given": "Date de la présente déclaration : %s.",
    "heads": {"parties": "Les parties", "place": "Lieu de travail habituel", "job": "Poste et fonctions",
              "start": "Début de l'emploi", "term": "Durée de l'emploi", "probation": "Période de probation",
              "qualifications": "Compétences nécessaires", "training": "Formation requise",
              "hours": "Heures de travail et heures supplémentaires", "pay": "Salaire et jours de paie",
              "deductions": "Retenues obligatoires", "expenses": "Dépenses liées au travail",
              "contact": "Coordonnées de l'employeur", "leave": "Congés payés", "termination": "Fin de l'emploi",
              "collective": "Conventions collectives", "benefits": "Autres avantages",
              "abroad": "Travail à l'étranger", "sign": "Signatures"},
    "law_heads": {"on": {"place": "Lieu de travail", "hours": "Heures de travail"},
                  "be": {"place": "Lieu de travail", "job": "Fonction", "start": "Date de début",
                         "term": "Durée de la relation de travail", "pay": "Rémunération et avantages extra-légaux",
                         "probation": "Période d'essai", "hours": "Horaire de travail", "training": "Formation",
                         "leave": "Vacances annuelles", "termination": "Fin de la relation de travail",
                         "collective": "Conventions collectives et commission paritaire",
                         "social": "Institution de sécurité sociale", "abroad": "Travail à l'étranger"}},
    "law_words": {"be": {"worker": "Travailleur", "given": "Date du présent document : %s.",
                         "starts": "La relation de travail commence le %s.",
                         "permanent": "Contrat de travail à durée indéterminée.",
                         "permanent_probation": "Contrat de travail à durée indéterminée, avec la période d'essai "
                                                "ci-dessous.",
                         "fixed": "Contrat de travail à durée déterminée du %s au %s.",
                         "fixed_kind": "Contrat de travail à durée déterminée (%s) du %s au %s.",
                         "basic": "Rémunération de base : %s", "standard": "Régime de travail : %s",
                         "paid": "Périodicité de paiement : %s.",
                         "seat": "Siège de l'employeur : %s.", "various": "Le travailleur est occupé en divers lieux",
                         "free": "Le travailleur est libre de choisir son lieu de travail",
                         "sign_worker": "Reçu par le travailleur",
                         "na_reason": {"probation": "pas de période d'essai (l'article 67 de la loi du 3 juillet 1978 "
                                                    "est abrogé depuis le 1er janvier 2014)",
                                       "training": "l'employeur n'offre pas de droit à la formation",
                                       "other": "aucune disposition à ce sujet"}}},
    "employer": "Employeur", "worker": "Employé", "operating": "faisant affaire sous le nom de %s",
    "various": "L'employé travaille à divers endroits", "free": "L'employé choisit lui-même son lieu de travail",
    "seat": "Adresse de l'employeur : %s.",
    "starts": "L'emploi commence le %s.",
    "permanent": "Emploi à durée indéterminée.",
    "permanent_probation": "Emploi à durée indéterminée, qui commence par la période de probation ci-dessous.",
    "fixed": "Emploi à durée déterminée du %s au %s.",
    "fixed_kind": "Emploi à durée déterminée (%s) du %s au %s.",
    "expected": "Emploi à durée déterminée%s à compter du %s, durée prévue : %s.",
    "basis_temp": "Motif de la durée déterminée : %s.",
    "na": "Sans objet : %s.",
    "na_reason": {"probation": "aucune période de probation", "training": "aucune formation n'est requise pour le poste",
                  "other": "aucune disposition à ce sujet"},
    "probation": "Période de probation de %s à compter du début de l'emploi.", "conditions": "Conditions : %s",
    "unit": {"month": ("mois", "mois"), "week": ("semaine", "semaines")},
    "basic": "Salaire : %s", "element": "%s : %s", "paid": "Jours de paie : %s.", "method": "Mode de paiement : %s.",
    "overtime_rate": "Taux des heures supplémentaires : %s",
    "other_pay": "Versement des autres formes de rémunération : %s",
    "per": {"hour": "l'heure", "week": "par semaine", "month": "par mois", "year": "par année"},
    "standard": "Heures normales : %s", "overtime": "Heures supplémentaires : %s",
    "schedule": "Horaire : %s", "breaks_line": "Intervalles de repos : %s", "rest_days": "Jours d'arrêt réguliers : %s",
    "variable": "L'horaire de travail est variable.", "guaranteed": "Nombre d'heures du régime de travail : %s",
    "reference": "Plage journalière et jours de la semaine où des prestations peuvent être fixées : %s",
    "notice": "Communication de l'horaire : %s",
    "shifts": "Changements de quart : %s", "schedule_notice": "Préavis d'horaire : %s",
    "contact_address": "Adresse : %s", "contact_phone": "Téléphone : %s", "contact_names": "Personnes-ressources : %s",
    "countries": "Pays : %s", "period": "Période à l'étranger : du %s au %s (%s)",
    "weeks": ("semaine", "semaines"), "days": ("jour", "jours"),
    "currency": "Devise du salaire à l'étranger : %s", "abroad_benefits": "Avantages en espèces ou en nature : %s",
    "repatriation": "Retour au pays : %s",
    "sign_employer": "Pour l'employeur", "sign_worker": "Reçu par l'employé", "sign_date": "Date",
    "law_sign": {},
}
NL = {
    "title": {"nl": "Opgave van de arbeidsvoorwaarden", "be": "Informatie over de arbeidsrelatie"},
    "basis": {"nl": "Schriftelijke opgave op grond van artikel 7:655 van het Burgerlijk Wetboek.",
              "be": "Informatie over de belangrijkste aspecten van de arbeidsrelatie op grond van de artikelen 4 tot "
                    "6 van de wet van 7 oktober 2022 houdende gedeeltelijke omzetting van Richtlijn (EU) 2019/1152."},
    "given": "Datum van deze opgave: %s.",
    "heads": {"parties": "Partijen", "place": "Plaats van de arbeid", "job": "Functie en aard van de arbeid",
              "start": "Datum van indiensttreding", "term": "Duur van de arbeidsovereenkomst",
              "leave": "Vakantie en ander betaald verlof", "termination": "Opzegging en einde van de arbeidsovereenkomst",
              "pay": "Loon", "hours": "Arbeidsduur", "pension": "Pensioenregeling",
              "collective": "Collectieve arbeidsovereenkomst", "agency": "Uitzend- of payrollovereenkomst",
              "on_call": "Oproepovereenkomst", "probation": "Proeftijd", "training": "Scholing",
              "social": "Sociale zekerheid", "sickness": "Ziekte", "benefits": "Overige voorzieningen",
              "abroad": "Arbeid buiten Nederland", "sign": "Ondertekening"},
    "law_heads": {"be": {"place": "Plaats van het werk", "job": "Functie", "start": "Aanvangsdatum",
                         "term": "Duur van de arbeidsrelatie", "pay": "Loon en extralegale voordelen",
                         "hours": "Arbeidstijd en uurrooster", "training": "Opleiding", "leave": "Jaarlijkse vakantie",
                         "termination": "Beëindiging van de arbeidsrelatie",
                         "collective": "Collectieve arbeidsovereenkomsten en paritair comité",
                         "social": "Socialezekerheidsinstelling", "abroad": "Werk in het buitenland"}},
    "law_words": {"be": {"given": "Datum van dit document: %s.", "starts": "De arbeidsrelatie begint op %s.",
                         "permanent": "Arbeidsovereenkomst voor onbepaalde duur.",
                         "permanent_probation": "Arbeidsovereenkomst voor onbepaalde duur, met een proeftijd (zie hieronder).",
                         "fixed": "Arbeidsovereenkomst voor een bepaalde duur van %s tot en met %s.",
                         "fixed_kind": "Arbeidsovereenkomst voor een bepaalde duur (%s) van %s tot en met %s.",
                         "standard": "Arbeidsregeling: %s",
                         # art. 4 § 2 9° a) to d), in the words of the Dutch text of the law
                         "variable": "Het uurrooster is variabel.",
                         "guaranteed": "Aantal uren van de arbeidsregeling: %s",
                         "extra_pay": "Overuren en meeruren: %s",
                         "reference": "Dagelijks tijdvak en dagen waarop prestaties kunnen worden vastgesteld: %s",
                         "notice": "Mededeling van het werkrooster: %s",
                         "basis_temp": "Reden voor de bepaalde duur: %s.",
                         "na_reason": {"probation": "er is geen proeftijd (artikel 67 van de wet van 3 juli 1978 is "
                                                    "sinds 1 januari 2014 opgeheven)",
                                       "training": "de werkgever biedt geen recht op opleiding aan",
                                       "other": "hierover is niets afgesproken"}}},
    "employer": "Werkgever", "worker": "Werknemer",
    "various": "De werknemer verricht zijn arbeid op verschillende plaatsen",
    "free": "De werknemer is vrij zijn werkplek te bepalen", "seat": "Zetel van de werkgever: %s.",
    "starts": "De arbeidsovereenkomst gaat in op %s.",
    "permanent": "Arbeidsovereenkomst voor onbepaalde tijd.",
    "permanent_probation": "Arbeidsovereenkomst voor onbepaalde tijd, met een proeftijd (zie hieronder).",
    "fixed": "Arbeidsovereenkomst voor bepaalde tijd van %s tot en met %s.",
    "fixed_kind": "Arbeidsovereenkomst voor bepaalde tijd (%s) van %s tot en met %s.",
    "expected": "Arbeidsovereenkomst voor bepaalde tijd%s vanaf %s, verwachte duur: %s.",
    "basis_temp": "Reden voor de bepaalde tijd: %s.",
    "na": "Niet van toepassing: %s.",
    "na_reason": {"agency": "de werknemer werkt niet via een uitzendbureau",
                  "probation": "er is geen proeftijd overeengekomen",
                  "training": "de werkgever biedt geen recht op scholing",
                  "collective": "er is geen collectieve arbeidsovereenkomst van toepassing",
                  "social": "de werkgever biedt geen bescherming op het gebied van sociale zekerheid naast de wettelijke",
                  "other": "hierover is niets afgesproken"},
    "agency": "De werknemer werkt bij: %s.",
    "agency_no": "Nee: dit is geen uitzend- of payrollovereenkomst.",
    "agency_nl": "Uitzendovereenkomst (artikel 7:690 BW); inlenende onderneming: %s.",
    "on_call_no": "Nee: dit is geen oproepovereenkomst.",
    "on_call_yes": "Ja: dit is een oproepovereenkomst (artikel 7:628a BW).",
    "pension_no": "De werknemer neemt niet deel aan een pensioenregeling.",
    "pension_yes": "De werknemer neemt deel aan een pensioenregeling: %s",
    "probation": "Proeftijd van %s vanaf de datum van indiensttreding.", "conditions": "Voorwaarden: %s",
    "unit": {"month": ("maand", "maanden"), "week": ("week", "weken")},
    "basic": "Aanvangsloon: %s", "element": "%s: %s", "paid": "Betaling: %s.", "method": "Wijze van betaling: %s.",
    "overtime_rate": "Loon voor overwerk: %s", "other_pay": "Overige looncomponenten: %s",
    "per": {"hour": "per uur", "week": "per week", "month": "per maand", "year": "per jaar"},
    "standard": "Normale arbeidsduur: %s", "overtime": "Arbeid buiten de normale arbeidsduur: %s",
    "shifts": "Wisselen van diensten: %s", "schedule_notice": "Bekendmaking van het rooster: %s",
    "schedule": "Uurrooster: %s", "breaks_line": "Rusttijden: %s", "rest_days": "Vaste rustdagen: %s",
    "variable": "De tijdstippen waarop de arbeid wordt verricht zijn variabel.",
    "guaranteed": "Gewaarborgde betaalde uren: %s", "extra_pay": "Loon voor uren boven de gewaarborgde uren: %s",
    "reference": "Dagen en uren waarop arbeid kan worden verlangd: %s",
    "notice": "Minimale termijn voor een oproep: %s", "cancellation": "Termijn voor het afzeggen van een oproep: %s",
    "countries": "Land: %s", "period": "Periode in het buitenland: %s tot en met %s (%s)",
    "weeks": ("week", "weken"), "days": ("dag", "dagen"),
    "currency": "Valuta waarin het loon wordt betaald: %s", "abroad_benefits": "Vergoedingen in geld of in natura: %s",
    "repatriation": "Terugkeer: %s", "housing": "Huisvesting: %s", "social_insurance": "Sociale verzekering: %s",
    "host_pay": "Loon volgens het recht van het ontvangende land: %s",
    "allowances": "Vergoedingen voor de detachering en voor reis-, verblijfs- en huisvestingskosten: %s",
    "website": "Officiële website van het ontvangende land over detachering: %s",
    "certificates": "Verklaringen voor de detachering: %s",
    "sign_employer": "Voor de werkgever", "sign_worker": "Ontvangen door de werknemer", "sign_date": "Datum",
    "law_sign": {},
}

DE = {
    "title": {"at": "Dienstzettel"},
    "basis": {"at": "Schriftliche Aufzeichnung der wesentlichen Rechte und Pflichten aus dem Arbeitsvertrag nach § 2 "
                    "Arbeitsvertragsrechts-Anpassungsgesetz (AVRAG)."},
    "given": "Ausgestellt am %s.",
    "heads": {"parties": "Vertragsparteien", "start": "Beginn des Arbeitsverhältnisses",
              "term": "Dauer des Arbeitsverhältnisses", "termination": "Kündigung", "place": "Arbeitsort",
              "grading": "Einstufung", "job": "Verwendung und Tätigkeit", "pay": "Entgelt", "leave": "Urlaub",
              "hours": "Arbeitszeit", "collective": "Kollektivvertrag und Betriebsvereinbarungen",
              "insurer": "Sozialversicherung und Betriebliche Vorsorgekasse", "probation": "Probezeit",
              "training": "Fortbildung", "abroad": "Tätigkeit im Ausland", "sickness": "Krankenstand",
              "pension": "Betriebspension", "benefits": "Sonstige Leistungen", "agency": "Beschäftigerbetrieb",
              "social": "Sozialversicherung", "sign": "Unterschriften"},
    "law_heads": {},
    "employer": "Arbeitgeber", "worker": "Arbeitnehmer",
    "various": "Der Arbeitnehmer ist an wechselnden Arbeitsorten tätig",
    "free": "Der Arbeitnehmer kann seinen Arbeitsort frei wählen", "seat": "Sitz des Unternehmens: %s.",
    "starts": "Das Arbeitsverhältnis beginnt am %s.",
    "permanent": "Unbefristetes Arbeitsverhältnis.",
    "permanent_probation": "Unbefristetes Arbeitsverhältnis mit Probezeit (siehe unten).",
    "fixed": "Befristetes Arbeitsverhältnis vom %s bis %s.",
    "fixed_kind": "Befristetes Arbeitsverhältnis (%s) vom %s bis %s.",
    "expected": "Befristetes Arbeitsverhältnis%s ab %s, voraussichtliche Dauer: %s.",
    "basis_temp": "Grund der Befristung: %s.",
    "na": "Entfällt: %s.",
    "na_reason": {"probation": "es ist keine Probezeit vereinbart",
                  "training": "der Arbeitgeber stellt keine Fortbildung bereit",
                  "collective": "auf das Arbeitsverhältnis ist kein Kollektivvertrag anzuwenden",
                  "grading": "es gibt keine Einstufung in ein generelles Schema",
                  "other": "dazu ist nichts vereinbart"},
    "probation": "Probezeit von %s ab Beginn des Arbeitsverhältnisses.", "conditions": "Bedingungen: %s",
    "unit": {"month": ("Monat", "Monaten"), "week": ("Woche", "Wochen")},
    "basic": "Grundgehalt: %s", "element": "%s: %s", "paid": "Fälligkeit: %s.", "method": "Art der Auszahlung: %s.",
    "overtime_rate": "Vergütung von Überstunden: %s", "other_pay": "Weitere Entgeltbestandteile: %s",
    "per": {"hour": "pro Stunde", "week": "pro Woche", "month": "brutto pro Monat", "year": "pro Jahr"},
    "standard": "Normalarbeitszeit: %s", "overtime": "Überstunden: %s", "shifts": "Änderung von Schichtplänen: %s",
    "schedule_notice": "Bekanntgabe der Lage der Arbeitszeit: %s", "schedule": "Lage der Arbeitszeit: %s",
    "breaks_line": "Ruhepausen: %s", "rest_days": "Wöchentliche Ruhe: %s",
    "variable": "Die Lage der Arbeitszeit ist variabel.", "guaranteed": "Garantierte bezahlte Stunden: %s",
    "extra_pay": "Entgelt für zusätzliche Stunden: %s",
    "reference": "Referenzstunden und -tage, an denen gearbeitet werden kann: %s",
    "notice": "Mindestankündigungsfrist: %s", "cancellation": "Frist für die Absage eines Arbeitseinsatzes: %s",
    "insurer_social": "Träger der Sozialversicherung: %s", "insurer_bv": "Betriebliche Vorsorgekasse: %s",
    "countries": "Staat: %s", "period": "Dauer der Auslandstätigkeit: %s bis %s (%s)",
    "weeks": ("Woche", "Wochen"), "days": ("Tag", "Tage"),
    "currency": "Währung des Entgelts: %s",
    "abroad_benefits": "Zusätzliche Vergütung für die Auslandstätigkeit: %s",
    "repatriation": "Rückführung nach Österreich: %s",
    "host_pay": "Entgelt nach dem Recht des Staates der Arbeitsleistung: %s", "allowances": "Aufwandersatz: %s",
    "website": "Website des Staates nach Art. 5 Abs. 2 der Richtlinie 2014/67/EU: %s",
    "certificates": "Bescheinigungen für die Entsendung: %s",
    "sign_employer": "Für den Arbeitgeber", "sign_worker": "Erhalten vom Arbeitnehmer", "sign_date": "Datum",
    "law_sign": {},
}
# Wave 9. Spanish in the words of Real Decreto 723/2026 art. 3.2 (persona trabajadora, domicilio social, grupo
# profesional, jornada ordinaria, periodo de prueba, convenio colectivo), Italian in those of D.Lgs. 152/1997 art. 1
# (datore di lavoro, luogo di lavoro, inquadramento, periodo di prova, preavviso, retribuzione), Polish in those of
# Kodeks pracy art. 29 (rodzaj pracy, miejsce wykonywania pracy, wymiar czasu pracy, dzień rozpoczęcia pracy).
ES = {
    "title": {"es": "Información sobre los elementos esenciales del contrato de trabajo"},
    "basis": {"es": "Información que la empresa facilita por escrito a la persona trabajadora conforme al artículo 8.5 "
                    "del Estatuto de los Trabajadores y al artículo 3 del Real Decreto 723/2026, de 9 de septiembre."},
    "given": "Fecha del presente documento: %s.",
    "heads": {"parties": "Partes", "start": "Fecha de comienzo", "term": "Duración del contrato",
              "place": "Domicilio social y centro de trabajo", "job": "Puesto de trabajo y grupo profesional",
              "pay": "Salario", "hours": "Jornada de trabajo", "leave": "Vacaciones", "probation": "Periodo de prueba",
              "training": "Formación", "agency": "Empresa usuaria (empresa de trabajo temporal)",
              "algorithms": "Sistemas algorítmicos o automatizados de toma de decisiones",
              "equality": "Plan de igualdad, conciliación y protocolo frente al acoso",
              "termination": "Extinción del contrato y preaviso", "collective": "Convenio colectivo",
              "social": "Seguridad Social", "changes": "Modificación de las condiciones",
              "sickness": "Incapacidad temporal", "pension": "Plan de pensiones", "benefits": "Otros beneficios",
              "abroad": "Trabajo en el extranjero", "sign": "Firmas"},
    "law_heads": {},
    "employer": "Empresa", "worker": "Persona trabajadora",
    "various": "La persona trabajadora presta sus servicios en diferentes centros de trabajo",
    "free": "La persona trabajadora determina libremente su lugar de prestación de servicios",
    "seat": "Domicilio social de la empresa: %s.", "workplace": "Centro de trabajo habitual: %s",
    "group": "Grupo profesional: %s",
    "starts": "La relación laboral comienza el %s.",
    "permanent": "Contrato de trabajo por tiempo indefinido.",
    "permanent_probation": "Contrato de trabajo por tiempo indefinido, con el periodo de prueba indicado más abajo.",
    "fixed": "Contrato de duración determinada del %s al %s.",
    "fixed_kind": "Contrato de duración determinada (%s) del %s al %s.",
    "expected": "Contrato de duración determinada%s desde el %s; duración previsible: %s.",
    "basis_temp": "Causa de la contratación temporal y circunstancias que la justifican: %s.",
    "na": "No procede: %s.",
    "na_reason": {"agency": "la persona trabajadora no está cedida por una empresa de trabajo temporal",
                  "probation": "no se ha concertado periodo de prueba",
                  "training": "la empresa no proporciona más formación que la exigida por la ley",
                  "collective": "ningún convenio colectivo es aplicable a la relación laboral",
                  "algorithms": "la empresa no utiliza sistemas de este tipo",
                  "other": "no hay nada pactado al respecto"},
    "agency": "Empresa usuaria: %s.",
    "probation": "Periodo de prueba de %s desde el comienzo de la relación laboral.", "conditions": "Condiciones: %s",
    "unit": {"month": ("mes", "meses"), "week": ("semana", "semanas")},
    "basic": "Salario base: %s", "element": "%s: %s", "paid": "Periodicidad de pago: %s.",
    "method": "Método de pago: %s.", "overtime_rate": "Retribución de las horas extraordinarias: %s",
    "other_pay": "Conceptos salariales variables: %s",
    "per": {"hour": "brutos por hora", "week": "brutos por semana", "month": "brutos al mes", "year": "brutos al año"},
    "standard": "Jornada ordinaria: %s", "overtime": "Horas extraordinarias: %s",
    "shifts": "Modificación de la jornada y cambios de turno: %s",
    "schedule": "Distribución horaria: %s", "breaks_line": "Descansos: %s", "rest_days": "Descanso semanal: %s",
    "schedule_notice": "Comunicación del horario: %s",
    "variable": "La jornada se distribuye de forma irregular a lo largo del año.",
    "guaranteed": "Horas garantizadas: %s", "extra_pay": "Retribución de las horas adicionales: %s",
    "reference": "Horas y días de referencia en los que la empresa puede exigir la prestación: %s",
    "notice": "Preaviso mínimo antes del comienzo de la tarea: %s", "cancellation": "Plazo para cancelar la tarea: %s",
    "countries": "País: %s", "period": "Duración del trabajo en el extranjero: del %s al %s (%s)",
    "weeks": ("semana", "semanas"), "days": ("día", "días"),
    "currency": "Moneda en que se pagará el salario: %s",
    "abroad_benefits": "Retribuciones en dinero o en especie, dietas y compensaciones por gastos: %s",
    "repatriation": "Repatriación: %s",
    "host_pay": "Retribución con arreglo a la legislación del Estado de acogida: %s",
    "allowances": "Complemento por desplazamiento y reembolso de los gastos de viaje, alojamiento y manutención: %s",
    "website": "Portal web oficial del Estado de acogida sobre desplazamiento: %s",
    "certificates": "Certificados del desplazamiento: %s",
    "col": {"name": "Convenio colectivo aplicable: %s", "code": "Código de convenio: %s", "published": "Publicación: %s",
            "validity": "Vigencia: %s", "parties": "Partes firmantes: %s", "copy": "Consulta del texto: %s"},
    "sign_employer": "Por la empresa", "sign_worker": "Recibido por la persona trabajadora", "sign_date": "Fecha",
    "law_sign": {},
}

IT = {
    "title": {"it": "Informazioni sul rapporto di lavoro"},
    "basis": {"it": "Informazioni comunicate al lavoratore ai sensi dell'articolo 1 del decreto legislativo 26 maggio "
                    "1997, n. 152."},
    "given": "Data del presente documento: %s.",
    "heads": {"parties": "Parti", "place": "Luogo di lavoro", "job": "Inquadramento e mansioni",
              "start": "Data di inizio del rapporto di lavoro", "term": "Tipologia del rapporto di lavoro",
              "agency": "Imprese utilizzatrici (somministrazione di lavoro)", "probation": "Periodo di prova",
              "training": "Formazione", "leave": "Ferie e altri congedi retribuiti",
              "termination": "Preavviso e recesso", "pay": "Retribuzione", "hours": "Orario di lavoro",
              "collective": "Contratto collettivo applicato", "social": "Enti previdenziali e assicurativi",
              "algorithms": "Sistemi decisionali o di monitoraggio automatizzati", "sickness": "Malattia",
              "pension": "Previdenza complementare", "benefits": "Altri benefici", "abroad": "Lavoro all'estero",
              "sign": "Firme"},
    "law_heads": {},
    "employer": "Datore di lavoro", "worker": "Lavoratore",
    "various": "Il lavoratore è occupato in luoghi diversi",
    "free": "Il lavoratore è libero di determinare il proprio luogo di lavoro",
    "seat": "Sede del datore di lavoro: %s.", "group": "Inquadramento, livello e qualifica: %s",
    "starts": "Il rapporto di lavoro ha inizio il %s.",
    "permanent": "Rapporto di lavoro subordinato a tempo indeterminato.",
    "permanent_probation": "Rapporto di lavoro subordinato a tempo indeterminato, con il periodo di prova indicato di "
                           "seguito.",
    "fixed": "Rapporto di lavoro a tempo determinato dal %s al %s.",
    "fixed_kind": "Rapporto di lavoro a tempo determinato (%s) dal %s al %s.",
    "expected": "Rapporto di lavoro a tempo determinato%s dal %s; durata prevista: %s.",
    "basis_temp": "Ragione del termine: %s.",
    "na": "Non applicabile: %s.",
    "na_reason": {"agency": "il lavoratore non dipende da un'agenzia di somministrazione di lavoro",
                  "probation": "non è previsto un periodo di prova",
                  "training": "il datore di lavoro non eroga formazione oltre a quella obbligatoria per legge",
                  "collective": "al rapporto di lavoro non si applica alcun contratto collettivo",
                  "algorithms": "il datore di lavoro non utilizza sistemi decisionali o di monitoraggio automatizzati",
                  "other": "nulla è stato pattuito al riguardo"},
    "agency": "Impresa utilizzatrice: %s.",
    "probation": "Periodo di prova di %s dall'inizio del rapporto di lavoro.", "conditions": "Condizioni: %s",
    "unit": {"month": ("mese", "mesi"), "week": ("settimana", "settimane")},
    "basic": "Retribuzione iniziale: %s", "element": "%s: %s", "paid": "Periodo di pagamento: %s.",
    "method": "Modalità di pagamento: %s.", "overtime_rate": "Retribuzione del lavoro straordinario: %s",
    "other_pay": "Altri elementi della retribuzione: %s",
    "per": {"hour": "lordi all'ora", "week": "lordi alla settimana", "month": "lordi al mese", "year": "lordi all'anno"},
    "standard": "Orario normale di lavoro: %s", "overtime": "Lavoro straordinario: %s",
    "shifts": "Cambiamenti di turno: %s",
    "schedule": "Programmazione dell'orario: %s", "breaks_line": "Pause: %s", "rest_days": "Riposo settimanale: %s",
    "schedule_notice": "Comunicazione dei turni: %s",
    "variable": "Il rapporto di lavoro non prevede un orario normale di lavoro programmato.",
    "guaranteed": "Ore retribuite garantite: %s",
    "extra_pay": "Retribuzione per il lavoro prestato in aggiunta alle ore garantite: %s",
    "reference": "Ore e giorni di riferimento in cui il lavoratore è tenuto a svolgere la prestazione: %s",
    "notice": "Periodo minimo di preavviso prima dell'inizio della prestazione: %s",
    "cancellation": "Termine entro cui il datore di lavoro può annullare l'incarico: %s",
    "countries": "Paese: %s", "period": "Durata prevista del lavoro all'estero: dal %s al %s (%s)",
    "weeks": ("settimana", "settimane"), "days": ("giorno", "giorni"),
    "currency": "Valuta in cui è corrisposta la retribuzione: %s",
    "abroad_benefits": "Prestazioni ulteriori in denaro o in natura: %s", "repatriation": "Rimpatrio: %s",
    "host_pay": "Retribuzione secondo il diritto dello Stato membro ospitante: %s",
    "allowances": "Indennità per il distacco e rimborso delle spese di viaggio, vitto e alloggio: %s",
    "website": "Sito internet istituzionale dello Stato membro ospitante sul distacco: %s",
    "certificates": "Certificati per il distacco: %s",
    "col": {"name": "Contratto collettivo applicato: %s", "parties": "Parti che lo hanno sottoscritto: %s",
            "code": "Codice alfanumerico unico (CNEL): %s", "published": "Pubblicazione: %s", "validity": "Durata: %s",
            "copy": "Consultazione del testo: %s"},
    "sign_employer": "Per il datore di lavoro", "sign_worker": "Ricevuto dal lavoratore", "sign_date": "Data",
    "law_sign": {},
}

PL = {
    "title": {"pl": "Informacja o warunkach zatrudnienia"},
    "basis": {"pl": "Informacja przekazana pracownikowi na podstawie art. 29 § 3 Kodeksu pracy; warunki umowy o pracę "
                    "określone zgodnie z art. 29 § 1 Kodeksu pracy przywołano w punktach 1–7."},
    "given": "Informację sporządzono dnia %s.",
    "heads": {"parties": "Strony umowy", "term": "Rodzaj umowy", "job": "Rodzaj pracy",
              "place": "Miejsce wykonywania pracy", "pay": "Wynagrodzenie", "hours": "Czas pracy",
              "start": "Dzień rozpoczęcia pracy", "probation": "Okres próbny", "leave": "Urlop",
              "termination": "Rozwiązanie stosunku pracy", "training": "Szkolenia",
              "collective": "Układ zbiorowy pracy", "rules": "Regulamin pracy", "social": "Ubezpieczenia społeczne",
              "agency": "Pracodawca użytkownik (praca tymczasowa)", "sickness": "Choroba",
              "pension": "Pracownicze plany kapitałowe", "benefits": "Inne świadczenia", "abroad": "Praca za granicą",
              "sign": "Podpisy"},
    "law_heads": {},
    "employer": "Pracodawca", "worker": "Pracownik",
    "various": "Pracownik wykonuje pracę w kilku miejscach",
    "free": "Pracownik sam określa miejsce wykonywania pracy",
    "seat": "Adres siedziby pracodawcy: %s.", "contract": "Umowa o pracę zawarta dnia %s.",
    "starts": "Dzień rozpoczęcia pracy: %s.",
    "permanent": "Umowa o pracę na czas nieokreślony.",
    "permanent_probation": "Umowa o pracę na okres próbny (art. 25 § 2 Kodeksu pracy); czas jej trwania podano "
                           "w punkcie „Okres próbny”.",
    "fixed": "Umowa o pracę na czas określony od %s do %s.",
    "fixed_kind": "Umowa o pracę na czas określony (%s) od %s do %s.",
    "expected": "Umowa o pracę na czas określony%s od %s; przewidywany czas trwania: %s.",
    "basis_temp": "Obiektywne przyczyny uzasadniające zawarcie umowy: %s.",
    "na": "Nie dotyczy: %s.",
    "na_reason": {"agency": "pracownik nie jest pracownikiem tymczasowym",
                  "probation": "umowa nie jest umową na okres próbny",
                  "training": "pracodawca nie zapewnia szkoleń innych niż wymagane przepisami",
                  "collective": "pracownik nie jest objęty układem zbiorowym pracy ani innym porozumieniem zbiorowym",
                  "social": "pracownik sam dokonuje wyboru instytucji zabezpieczenia społecznego",
                  "other": "strony nie poczyniły ustaleń w tym zakresie"},
    "agency": "Pracodawca użytkownik: %s.",
    "probation": "Okres próbny: %s od dnia rozpoczęcia pracy.", "conditions": "Warunki: %s",
    # one, two to four, five and more: 1 miesiąc, 3 miesiące, 6 miesięcy
    "unit": {"month": ("miesiąc", "miesiące", "miesięcy"), "week": ("tydzień", "tygodnie", "tygodni")},
    "basic": "Wynagrodzenie zasadnicze: %s", "element": "%s: %s", "paid": "Wypłata wynagrodzenia: %s.",
    "method": "Sposób wypłaty: %s.",
    "overtime_rate": "Wynagrodzenie za pracę w godzinach nadliczbowych: %s",
    "other_pay": "Inne składniki wynagrodzenia oraz świadczenia pieniężne lub rzeczowe: %s",
    "per": {"hour": "brutto za godzinę", "week": "brutto tygodniowo", "month": "brutto miesięcznie",
            "year": "brutto rocznie"},
    "hours_basis": "Wymiar czasu pracy: %s", "norm": "Dobowa i tygodniowa norma czasu pracy: %s",
    "standard": "Dobowy i tygodniowy wymiar czasu pracy: %s",
    "overtime": "Praca w godzinach nadliczbowych i rekompensata za nią: %s",
    "shifts": "Przechodzenie ze zmiany na zmianę: %s",
    "schedule": "Rozkład czasu pracy: %s", "breaks_line": "Przerwy w pracy: %s",
    "rest_days": "Odpoczynek dobowy i tygodniowy: %s", "schedule_notice": "Ogłaszanie rozkładu czasu pracy: %s",
    "variable": "Rozkład czasu pracy jest zmienny.", "guaranteed": "Gwarantowana liczba płatnych godzin: %s",
    "extra_pay": "Wynagrodzenie za godziny ponad gwarantowane: %s",
    "reference": "Godziny i dni, w których praca może być wymagana: %s",
    "notice": "Minimalny termin uprzedzenia o pracy: %s", "cancellation": "Termin odwołania pracy: %s",
    "countries": "Państwo: %s", "period": "Przewidywany czas pracy za granicą: od %s do %s (%s)",
    "weeks": ("tydzień", "tygodnie", "tygodni"), "days": ("dzień", "dni", "dni"),
    "currency": "Waluta, w której będzie wypłacane wynagrodzenie: %s",
    "abroad_benefits": "Świadczenia pieniężne lub rzeczowe związane z pracą za granicą: %s",
    "repatriation": "Powrót do kraju: %s",
    "host_pay": "Wynagrodzenie zgodnie z prawem państwa przyjmującego: %s",
    "allowances": "Dodatki z tytułu delegowania oraz zwrot kosztów podróży, wyżywienia i zakwaterowania: %s",
    "website": "Oficjalna strona internetowa państwa przyjmującego: %s",
    "certificates": "Zaświadczenia związane z delegowaniem: %s",
    "col": {"name": "Układ zbiorowy pracy lub porozumienie zbiorowe: %s", "parties": "Strony: %s", "code": "Numer: %s",
            "published": "Rejestracja: %s", "validity": "Okres obowiązywania: %s", "copy": "Miejsce udostępnienia: %s"},
    "sign_employer": "Za pracodawcę", "sign_worker": "Otrzymał(a) pracownik", "sign_date": "Data",
    "law_sign": {},
}
WORDS = {"en": EN, "sv": SV, "nb": NB, "da": DA, "fi": FI, "fr": FR, "nl": NL, "de": DE, "es": ES, "it": IT, "pl": PL}
REQUIRED = ("employer", "worker", "place", "job", "start", "pay", "hours")
REQUIRED_LAW = {
    "eu": ("leave", "termination"), "se": ("leave", "termination", "social_security"),
    "uk": ("leave", "termination", "disciplinary"), "no": ("leave", "termination", "breaks"),
    "dk": ("leave", "termination"), "fi": ("leave", "termination", "insurance"),
    "us": ("flsa",), "ca": ("qualifications", "deductions", "expenses"), "on": ("contact",),
    "au": ("leave", "termination"),
    "be": ("leave", "termination", "social_security"), "nl": ("leave", "termination"),
    "at": ("leave", "termination", "insurance"), "ie": ("leave", "termination", "sickness", "pension"),
    "es": ("leave", "termination", "social_security", "equality", "changes"),
    "it": ("leave", "termination", "social_security"), "pl": ("leave", "termination", "rules"),
}
# Items a law always answers, yes or no: the spec must say, and false is an answer (BW 7:655 (1) j and o).
ANSWERED = {"nl": ("pension", "on_call")}


def lang_of(spec, law=None):
    raw = str(spec.get("language") or "").lower()
    if raw:
        return next((v for k, v in (("sv", "sv"), ("nb", "nb"), ("no", "nb"), ("nn", "nb"), ("da", "da"),
                                     ("fi", "fi"), ("fr", "fr"), ("nl", "nl"), ("de", "de"), ("es", "es"),
                                     ("it", "it"), ("pl", "pl")) if raw.startswith(k)), "en")
    if law == "be":
        return {"nl": "nl"}.get(belgian_region(spec), "fr")
    return LAWS.get(law or "", {}).get("lang", "en")


def belgian_region(spec):
    """The region whose language decree governs (Flemish decree of 19 July 1973 art. 2 and 5: an operating seat in
    the Dutch language area writes in Dutch; French Community decree of 30 June 1982 art. 1 and 2: French), read
    from the workplace's or the employer's bpost postcode: 1000-1299 Brussels-Capital, 1300-1499 and 4000-7999
    Wallonia (4700-4799 holds the German-speaking area), 1500-3999 and 8000-9999 Flanders."""
    import re as _re
    for text in (spec.get("place") if isinstance(spec.get("place"), str) else "",
                 (spec.get("employer") or {}).get("address", "")):
        m = _re.search(r"(?<!\d)([1-9]\d{3})(?!\d)", str(text or ""))
        if m:
            n = int(m.group(1))
            if 1000 <= n <= 1299:
                return "brussels"
            if 4700 <= n <= 4799:
                return "german"
            return "nl" if 1500 <= n <= 3999 or 8000 <= n <= 9999 else "fr"
    return ""


def law_of(spec):
    law = str(spec.get("law") or "").lower()
    if law in LAWS:
        return law
    lang = lang_of(spec)
    return {"sv": "se", "nb": "no", "da": "dk", "fi": "fi", "fr": "ca", "nl": "nl", "es": "es", "it": "it",
            "pl": "pl"}.get(lang, "eu")


def locale_of(spec):
    law = law_of(spec)
    lang = lang_of(spec, law)
    return LAW_LOCALE.get((law, lang)) or LOCALE.get(lang) or EN_LOCALE.get(law, "en-GB")


def words(spec):
    """The phrases of the statement's language, English filling any the language lacks."""
    law = law_of(spec)
    lang = lang_of(spec, law)
    base = WORDS[lang]
    out = dict(EN, **base)
    for k in ("heads", "na_reason", "per", "unit", "col"):
        out[k] = dict(EN[k], **base.get(k, {}))
    # A market's own words where the language is shared (Belgian French and Dutch, Irish English).
    for k, v in base.get("law_words", {}).get(law, {}).items():
        out[k] = dict(out[k], **v) if isinstance(v, dict) else v
    return out


def sentence(text):
    text = str(text).strip()
    return text if text.endswith((".", "!", "?", ":")) else text + "."


def date(value, loc):
    """A statement's dates: the CLDR long form in North America (October 9, 2026; 9 octobre 2026), else the
    locale's numeric form (letter.py)."""
    try:
        d = dt.date.fromisoformat(str(value).strip())
    except ValueError:
        return str(value)
    if loc in ("en-US", "en-CA"):
        return "%s %d, %d" % (MONTHS["en"][d.month - 1], d.day, d.year)
    if loc == "fr-CA":
        return "%d %s %d" % (d.day, MONTHS["fr"][d.month - 1], d.year)
    return letter.date(value, loc)


SYMBOL = {("en-US", "USD"): "$", ("en-CA", "CAD"): "$", ("fr-CA", "CAD"): "$", ("en-AU", "AUD"): "$",
          ("en-IE", "EUR"): "€", ("es-ES", "EUR"): "€", ("it-IT", "EUR"): "€", ("pl-PL", "PLN"): "zł"}


def plural(n, forms):
    """The form of a unit for a number: one and many, or Polish's three (1 miesiąc, 3 miesiące, 6 miesięcy)."""
    n = int(n)
    if n == 1:
        return forms[0]
    if len(forms) > 2 and not (2 <= n % 10 <= 4 and not 12 <= n % 100 <= 14):
        return forms[2]
    return forms[1]


def money(amount, currency, loc):
    """A whole salary without decimals (48 500 SEK), a rate with them (GBP 13.00, $28.50, 28,50 $)."""
    a = Decimal(str(amount))
    n = letter.number(a, loc) if a == a.to_integral_value() and a >= 100 else letter.money(a, loc)
    sym = SYMBOL.get((loc, str(currency).upper()))
    if loc in ("sv-SE", "nb-NO", "da-DK", "fi-FI", "fr-CA", "fr-BE", "es-ES", "it-IT", "pl-PL"):
        return "%s %s" % (n, sym or currency)
    if loc in ("nl-NL", "nl-BE", "de-AT"):
        return "%s %s" % (currency, letter.money(a, loc))      # EUR 3.450,00: an amount of money with its cents
    return "%s%s" % (sym, n) if sym else "%s %s" % (currency, n)


def party_line(e, w, law):
    name = e.get("name")
    if e.get("operating_name"):
        name = "%s, %s" % (name, (w["dba"] if law == "us" and "dba" in w else w["operating"]) % e["operating_name"])
    return ", ".join(x for x in (name, e.get("number"), e.get("address"), e.get("phone")) if x)


def body(item, spec, w, loc, law):
    """The lines under one heading."""
    d = lambda v: date(v, loc)  # noqa: E731
    na = lambda why=None: [w["na"] % (why or w["na_reason"].get(item, w["na_reason"]["other"]))]  # noqa: E731
    person = w["employee"] if law in ("us", "ca", "on", "au") and "employee" in w and lang_of(spec, law) == "en" \
        else w["worker"]
    if item == "parties":
        e, k = spec["employer"], spec["worker"]
        wrk = ", ".join(x for x in (k.get("name"), k.get("address")) if x)
        form = "%s : %s." if lang_of(spec, law) == "fr" else "%s: %s."
        # The employer's further particulars, as written, under the employer's own line.
        more = [sentence(x) for x in letter.further_lines(e)]
        return [form % (w["employer"], party_line(e, w, law))] + more + [form % (person, wrk)]
    if item == "place":
        p = spec["place"]
        if isinstance(p, dict):
            line = w["free"] if p.get("free") else w["various"]
            out = [line + (", " + p["note"].rstrip(".") if p.get("note") else "") + "."]
            return out + [w["seat"] % spec["employer"].get("address", "").rstrip(".")]
        if law == "at":       # AVRAG § 2 (2) 6: the usual place of work and the company's seat
            return [sentence(p), w["seat"] % spec["employer"].get("address", "").rstrip(".")]
        if law == "es":       # Real Decreto 723/2026 art. 3.2 c): the registered address and the usual workplace
            return [w["workplace"] % sentence(p), w["seat"] % spec["employer"].get("address", "").rstrip(".")]
        return [sentence(p)]
    if item == "job":
        j = spec["job"]
        if isinstance(j, dict):
            return [sentence(j["title"])] + ([sentence(j["description"])] if j.get("description") else []) + \
                ([w["group"] % sentence(j["group"])] if j.get("group") else [])
        return [sentence(j)]
    if item == "start":
        out = [(w["starts_us"] if law == "us" else w["starts"]) % d(spec["start"])]
        if law == "uk":
            out.append(w["continuous"] % d(spec.get("continuous_from") or spec["start"]))
        return out
    if item == "term":
        t = spec.get("term") or {"type": "permanent"}
        kind = str(t.get("type", "permanent")).lower()
        if law == "us" and kind in ("at-will", "at will", "permanent", "open-ended", "indefinite"):
            out = [w["at_will"]]
        elif law == "au" and kind in w["au_type"]:
            out = [w["au_type"][kind]]
        elif kind in ("permanent", "open-ended", "indefinite", "ongoing"):
            out = [w["permanent_probation"] if spec.get("probation") else w["permanent"]]
        elif t.get("end"):
            out = [w["fixed_kind"] % (t["kind"], d(spec["start"]), d(t["end"])) if t.get("kind")
                   else w["fixed"] % (d(spec["start"]), d(t["end"]))]
        else:
            k = " (%s)" % t["kind"] if t.get("kind") else ""
            out = [w["expected"] % (k, d(spec["start"]), str(t.get("expected", "")).rstrip("."))]
        if t.get("basis"):
            out.append(w["basis_temp"] % str(t["basis"]).rstrip("."))
        if law == "au" and t.get("renewal"):       # s 333E(1)(b), (c): how many times, and the latest end
            r = t["renewal"]
            times = {1: "once", 2: "twice"}.get(int(r.get("times", 1)), "%s times" % r.get("times"))
            out.append("This fixed term may be renewed or extended %s, to end no later than %s." % (times, d(r["latest_end"])))
        if law == "pl" and spec.get("contract_date"):       # art. 29 § 1: the date the contract was concluded
            out.insert(0, w["contract"] % d(spec["contract_date"]))
        return out + ([sentence(t["note"])] if t.get("note") else [])
    if item == "agency":
        a = spec.get("agency")
        if law == "nl":       # BW 7:655 (1) m and p: whether it is an agency or payroll contract, and the user
            if a and a.get("user_undertakings"):
                return [w["agency_nl"] % ", ".join(a["user_undertakings"])]
            return [sentence(a["text"])] if a and a.get("text") else [w["agency_no"]]
        return [w["agency"] % ", ".join(a["user_undertakings"])] if a and a.get("user_undertakings") else na()
    if item == "on_call":    # BW 7:655 (1) o: whether it is an on-call contract
        v = spec.get("on_call")
        return [sentence(v)] if isinstance(v, str) and v.strip() else [w["on_call_yes"] if v else w["on_call_no"]]
    if item == "pension" and law == "nl":     # BW 7:655 (1) j: whether the worker joins a pension scheme
        v = spec.get("pension")
        return [w["pension_yes"] % sentence(v)] if isinstance(v, str) and v.strip() else \
            [w["pension_yes"] % sentence(w["na_reason"]["other"])] if v is True else [w["pension_no"]]
    if item == "minimum_wage":
        return [w["minimum_wage_text"]]
    if item == "probation":
        p = spec.get("probation")
        if not p:
            return na()
        if isinstance(p, str):
            return [sentence(p)]
        n, unit = (p["months"], "month") if p.get("months") else (p["weeks"], "week")
        length = "%s %s" % (n, plural(n, w["unit"][unit]))
        line = w["probation"] % length
        line = line[0].upper() + line[1:]
        return [line] + ([w["conditions"] % sentence(p["conditions"])] if p.get("conditions") else [])
    if item == "pay":
        p = spec["pay"]
        if isinstance(p, str):
            return [sentence(p)]
        out = [w["basic"] % ("%s %s" % (money(p["amount"], p["currency"], loc), w["per"].get(p.get("per"), p.get("per", ""))))
               .strip() + "."]
        for c in p.get("components") or []:
            value = c.get("text") or "%s %s" % (money(c["amount"], c.get("currency", p["currency"]), loc),
                                                w["per"].get(c.get("per"), c.get("per", "")))
            out.append(w["element"] % (c["name"], sentence(value.strip())))
        if p.get("overtime_rate"):
            out.append(w["overtime_rate"] % sentence(p["overtime_rate"]))
        out.append(w["paid"] % str(p["paid"]).rstrip("."))
        if p.get("other_pay"):
            out.append(w["other_pay"] % sentence(p["other_pay"]))
        out.append(w["method"] % str(p["method"]).rstrip("."))
        if p.get("reference_period"):
            out.append(w["reference_period"] % sentence(p["reference_period"]))
        return out
    if item == "hours":
        h = spec["hours"]
        if isinstance(h, str):
            return [sentence(h)]
        variable = h.get("pattern") == "variable"
        keys = ("guaranteed", "extra_pay", "reference", "notice", "cancellation") if variable else ("standard",)
        if not variable and law != "no":       # Norway gives overtime and shift changes under (m), their own item
            keys += ("overtime", "shifts")
        out = [w["variable"]] if variable else []
        out += [w[k] % sentence(h[src]) for k, src in (("hours_basis", "basis"), ("norm", "norm")) if h.get(src)]
        out += [w[k] % sentence(h[k]) for k in ("per_day", "per_week") if h.get(k)]
        out += [w[k] % sentence(h[k]) for k in keys if h.get(k)]
        out += [w[k] % sentence(h[src]) for k, src in (("schedule", "schedule"), ("breaks_line", "breaks"),
                                                       ("rest_days", "rest_days")) if h.get(src)]
        if h.get("schedule_notice"):
            out.append(w["schedule_notice"] % sentence(h["schedule_notice"]))
        return out
    if item == "overtime":
        h = spec.get("hours") if isinstance(spec.get("hours"), dict) else {}
        out = [w[k] % sentence(h[k]) for k in ("shifts", "overtime") if h.get(k)]
        return out or na()
    if item == "insurer":
        ins = spec.get("insurance") or {}
        if isinstance(ins, str):
            return [sentence(ins)]
        if law == "at":       # AVRAG § 2 (2) 13: the social insurance institution and the BV-Kasse, with addresses
            return [w["insurer_social"] % sentence(ins.get("social_insurer", "")),
                    w["insurer_bv"] % sentence(ins.get("bv_kasse", ""))]
        return [w["insurer_pension"] % sentence(ins.get("pension", "")),
                w["insurer_accident"] % sentence(ins.get("accident", ""))]
    if item == "contact":
        c = spec.get("contact") or {}
        names = c.get("names") or []
        out = [w["contact_address"] % sentence(c.get("address", spec["employer"].get("address", ""))),
               w["contact_phone"] % sentence(c.get("phone", spec["employer"].get("phone", "")))]
        return out + ([w["contact_names"] % sentence(", ".join(names if isinstance(names, list) else [names]))]
                      if names else [])
    if item == "classification":
        f = spec.get("flsa") or {}
        if str(f.get("status", "")).lower().replace(" ", "-") == "exempt":
            ex = f.get("exemption")
            return [w["flsa_exempt"] % (", %s exemption, 29 CFR part 541" % ex if ex else "; 29 CFR part 541")]
        return [w["flsa_nonexempt"]]
    if item == "statements":
        t = str((spec.get("term") or {}).get("type", "")).lower()
        out = [w["fwis"]]
        if t == "casual":
            out.append(w["ceis"])
        if t in ("fixed", "fixed-term", "fixed term"):
            out.append(w["ftcis"])
        return out
    if item == "disciplinary":
        dsc = spec.get("disciplinary")
        if isinstance(dsc, str):
            return [sentence(dsc)]
        return [w["disc"][k] % sentence(dsc[k]) for k in ("rules", "procedure", "appeal_to", "grievance_to", "steps")
                if dsc.get(k)]
    if item == "abroad":
        a = spec["abroad"]
        frm, to = dt.date.fromisoformat(a["from"]), dt.date.fromisoformat(a["to"])
        days = (to - frm).days + 1
        span = "%d %s" % (days // 7, plural(days // 7, w["weeks"])) if days % 7 == 0 \
            else "%d %s" % (days, plural(days, w["days"]))
        out = [w["countries"] % ", ".join(a["countries"]) + ".", w["period"] % (d(a["from"]), d(a["to"]), span) + ".",
               w["currency"] % a["currency"] + ".",
               w["abroad_benefits"] % sentence(a.get("benefits") or w["na_reason"]["other"]),
               w["repatriation"] % sentence(a["repatriation"])]
        if a.get("certificates"):
            out.append(w["certificates"] % sentence(a["certificates"]))
        out += [w[k] % sentence(a[k]) for k in ("housing", "social_insurance") if a.get(k)]   # BW 7:655 (1) k
        posted = a.get("posted") or {}
        out += [w[k] % sentence(posted[k]) for k in ("host_pay", "allowances", "website") if posted.get(k)]
        return out
    key = {"social": "social_security"}.get(item, item)
    value = spec.get(key)
    if not value:
        return na()
    if item == "collective" and isinstance(value, dict):
        # Spain's art. 3.2 o) and Italy's q), q-bis): the agreement with what identifies it, one line each.
        return [w["col"][k] % sentence(value[k]) for k in ("name", "parties", "code", "published", "validity", "copy")
                if value.get(k)]
    return [sentence(value)]


def state_notice(spec, w, loc):
    """A US state's pay notice at hiring: New York Labor Law 195(1); California Labor Code 2810.5 (not for an
    employee exempt from overtime, 2810.5(c))."""
    state = str(spec.get("work_state") or "").upper()
    n = spec.get("state_notice") or {}
    exempt = str((spec.get("flsa") or {}).get("status", "")).lower() == "exempt"
    if state not in ("NY", "CA") or (state == "CA" and exempt):
        return None, []
    t = w["ny"] if state == "NY" else w["ca_notice"]
    p, e = spec["pay"], spec["employer"]
    rate = "%s %s" % (money(p["amount"], p["currency"], loc), w["per"].get(p.get("per"), p.get("per", "")))
    if state == "CA" and p.get("overtime_rate"):
        rate += "; overtime %s" % p["overtime_rate"]
    values = {"rate": rate.strip(), "overtime_rate": p.get("overtime_rate"), "allowances": n.get("allowances") or w["none"],
              "payday": n.get("payday") or p.get("paid"), "legal_name": e.get("name"),
              "dba": e.get("operating_name") or w["none"], "physical_address": n.get("physical_address") or e.get("address"),
              "mailing_address": n.get("mailing_address") or "the same as the physical address",
              "phone": e.get("phone"), "language": n.get("primary_language"), "comp_carrier": n.get("comp_carrier"),
              "sick_leave": n.get("sick_leave"), "disaster": n.get("disaster")}
    keys = ["rate", "overtime_rate", "allowances", "payday", "legal_name", "dba", "physical_address",
            "mailing_address", "phone", "language"] if state == "NY" else \
        ["rate", "allowances", "payday", "legal_name", "dba", "physical_address", "mailing_address", "phone",
         "comp_carrier", "sick_leave", "disaster"]
    if state == "NY" and exempt:
        keys.remove("overtime_rate")
    lines = [t[k] % sentence(values[k]) for k in keys if values.get(k)]
    if state == "NY":
        lines.append(t["ack"])
    return t["head"], lines


def missing_from(spec, law):
    need = list(REQUIRED) + list(REQUIRED_LAW.get(law, ()))
    out = [k for k in need + ["given"] if not spec.get(k)]
    out += ["%s (true or false: the statement says whether)" % k for k in ANSWERED.get(law, ()) if k not in spec]
    if law in ("nl", "at", "be") and not (spec.get("worker") or {}).get("address"):
        out.append("worker.address (%s)" % {"nl": "BW 7:655 (1) a: the parties' names and homes",
                                            "at": "AVRAG § 2 (2) 2: the worker's name and address",
                                            "be": "art. 4 § 2 1°: the parties' identity"}[law])
    if law == "at" and isinstance(spec.get("insurance"), dict):
        out += ["insurance.%s (AVRAG § 2 (2) 13)" % k for k in ("social_insurer", "bv_kasse")
                if not spec["insurance"].get(k)]
    if law in ("es", "it", "pl") and not (spec.get("employer") or {}).get("address"):
        out.append("employer.address (%s)" % {"es": "Real Decreto 723/2026 art. 3.2 c): el domicilio social",
                                              "it": "D.Lgs. 152/1997 art. 1 c. 1 c): la sede o il domicilio",
                                              "pl": "Kodeks pracy art. 29 § 1: adres siedziby pracodawcy"}[law])
    if law == "es" and not (isinstance(spec.get("job"), dict) and spec["job"].get("group")):
        out.append("job.group (Real Decreto 723/2026 art. 3.2 e): the professional group or category)")
    if law == "pl":
        if not spec.get("contract_date"):
            out.append("contract_date (Kodeks pracy art. 29 § 1: the date the contract was concluded)")
        if not (isinstance(spec.get("hours"), dict) and spec["hours"].get("basis")):
            out.append("hours.basis (Kodeks pracy art. 29 § 1 pkt 4: wymiar czasu pracy, full time or the fraction)")
    if law == "ie":
        h, p = spec.get("hours") if isinstance(spec.get("hours"), dict) else {}, \
            spec.get("pay") if isinstance(spec.get("pay"), dict) else {}
        out += ["hours.%s (s. 3(1A)(e): the hours expected per normal working %s)" % (k, k[4:])
                for k in ("per_day", "per_week") if not h.get(k)]
        if not p.get("reference_period"):
            out.append("pay.reference_period (s. 3(1A)(d): the pay reference period for the National Minimum Wage Act)")
    if law == "se" and "social_security" in out:
        out[out.index("social_security")] = "social_security (LAS 6 c § 12: that employer contributions are paid to the state)"
    if law == "uk" and "disciplinary" in out:
        out[out.index("disciplinary")] = "disciplinary (ERA s.3: the disciplinary rules and procedure and to whom the worker appeals or brings a grievance)"
    if law == "fi" and isinstance(spec.get("insurance"), dict):
        out += ["insurance.%s" % k for k in ("pension", "accident") if not spec["insurance"].get(k)]
    if law in ("no", "fi", "es") and str((spec.get("term") or {}).get("type", "")).lower() in ("fixed", "fixed-term") \
            and not (spec.get("term") or {}).get("basis"):
        out.append("term.basis (%s)" % {"no": "arbeidsmiljøloven § 14-6 (1) e: the basis for the temporary hire",
                                        "fi": "työsopimuslaki 2:4 § 3 kohta: määräaikaisuuden peruste",
                                        "es": "Real Decreto 723/2026 art. 3.2 d): the cause that allows the temporary "
                                              "contract and the circumstances that justify it"}[law])
    if law == "ca" and isinstance(spec.get("pay"), dict) and not spec["pay"].get("overtime_rate"):
        out.append("pay.overtime_rate (CLSR 3.1 (j): the rate of overtime pay)")
    if law == "us":
        state = str(spec.get("work_state") or "").upper()
        n = spec.get("state_notice") or {}
        exempt = str((spec.get("flsa") or {}).get("status", "")).lower() == "exempt"
        if state == "NY":
            out += ["state_notice.%s" % k for k in ("primary_language",) if not n.get(k)]
            if not exempt and not (spec.get("pay") or {}).get("overtime_rate"):
                out.append("pay.overtime_rate (New York Labor Law 195(1)(c): the overtime rate for a non-exempt employee)")
        if state == "CA" and not exempt:
            out += ["state_notice.%s" % k for k in ("comp_carrier", "sick_leave", "disaster") if not n.get(k)]
    if spec.get("abroad"):
        out += ["abroad.%s" % k for k in ("countries", "from", "to", "currency", "repatriation")
                if not spec["abroad"].get(k)]
    return out


def items_for(spec, law):
    """The headings of this statement, in order: the law's list, then what the spec gives beyond it."""
    items = list(LAWS[law]["order"])
    for extra in EXTRA:
        key = "social_security" if extra == "social" else extra
        if extra not in items and spec.get(key):
            items.insert(items.index("collective") if "collective" in items and extra != "social" else len(items), extra)
    if law == "ie" and spec.get("tips"):      # s. 3(1A)(f), where the Payment of Wages Act 1991 ss. 4B-4E apply
        items.insert(items.index("hours") + 1, "tips")
    if spec.get("abroad"):
        items.append("abroad")
    return items


def not_printed(spec, law):
    """Keys the data file gives that this law's statement has no heading for. Each is an error that names the
    key, never a silent drop: the term goes in "further" instead."""
    every = {i for entry in LAWS.values() for i in entry["order"]} | set(EXTRA)
    key_of = {"social": "social_security", "insurer": "insurance", "classification": "flsa"}
    items = items_for(spec, law)
    out = []
    for item in sorted(every - set(items)):
        key = key_of.get(item, item)
        if key in ("flsa", "insurance") and key in [key_of.get(i, i) for i in items]:
            continue
        if key == "overtime":
            continue                           # Norway's heading reads hours.overtime; no key of its own
        if spec.get(key) not in (None, "", [], {}, False):
            out.append('"%s" has no heading in a statement under "law": "%s"' % (key, law))
    for key, laws in ONE_LAW.items():
        if spec.get(key) not in (None, "", [], {}, False) and law not in laws:
            out.append('"%s" is read under "law": "%s" only' % (key, '" or "'.join(laws)))
    return out


def lines(spec):
    """The statement as (style, text) pairs."""
    law, loc = law_of(spec), locale_of(spec)
    w = words(spec)
    title = w["title"].get(law) or EN["title"][law]
    basis = w["basis"].get(law) or EN["basis"][law]
    given = (w["given_us"] if law == "us" else w["given"]) % date(spec["given"], loc)
    out = [("title", title), ("para", basis), ("para", given)]
    if law == "us":
        out.insert(1, ("para", "Dear %s," % spec["worker"]["name"]))
    if law == "uk":
        out[-1] = ("para", out[-1][1] + " " + w["as_at"])
    items = items_for(spec, law)
    heads = dict(w["heads"], **w["law_heads"].get(law, {}))
    n = 0
    for item in items:
        n += 1
        out.append(("item", "%d. %s" % (n, heads[item])))
        out += [("para", t) for t in body(item, spec, w, loc, law)]
    if law == "us":
        head, notice = state_notice(spec, w, loc)
        if head:
            n += 1
            out.append(("item", "%d. %s" % (n, head)))
            out += [("para", t) for t in notice]
    further = letter.further_lines({"further": spec.get("further")})
    if further:
        # Terms the data file gives that no item of the law's list holds: under a last heading, as written.
        n += 1
        out.append(("item", "%d. %s" % (n, FURTHER_HEAD.get(lang_of(spec, law), FURTHER_HEAD["en"]))))
        out += [("para", sentence(t)) for t in further]
    out.append(("item", heads["sign"]))
    sign_employer, sign_worker = w["law_sign"].get(law) or (w["sign_employer"], w["sign_worker"])
    signatory = spec["employer"].get("signatory") or spec["employer"]["name"]
    out.append(("sign", "%s|%s" % (sign_employer, signatory)))
    out.append(("sign", "%s|%s" % (sign_worker, spec["worker"]["name"])))
    return out


def write_docx(spec, out):
    from docx import Document
    from docx.oxml.ns import qn
    from docx.shared import Mm, Pt
    law = law_of(spec)
    missing = missing_from(spec, law)
    if missing:
        raise SystemExit("the spec needs %s" % ", ".join(missing))
    loc = locale_of(spec)
    doc = Document()
    sec = doc.sections[0]
    # A4 (ISO 216), or US Letter in the United States and Canada, with one-inch margins there.
    if letter.paper(loc) == "Letter":
        sec.page_width, sec.page_height = Mm(215.9), Mm(279.4)
        sec.left_margin = sec.right_margin = sec.top_margin = sec.bottom_margin = Mm(25.4)
    else:
        sec.page_width, sec.page_height = Mm(210), Mm(297)
        sec.left_margin = sec.right_margin = Mm(25)
        sec.top_margin = sec.bottom_margin = Mm(20)
    for style in doc.styles:
        if style.type == 1 and style.font is not None:
            style.font.name = FONT
            rpr = style.element.get_or_add_rPr()
            fonts = rpr.find(qn("w:rFonts"))
            if fonts is not None:
                for attr in ("w:ascii", "w:hAnsi", "w:eastAsia", "w:cs"):
                    fonts.set(qn(attr), FONT)
    doc.styles["Normal"].font.size = Pt(11)
    parts = lines(spec)
    doc.core_properties.title = "%s, %s" % (parts[0][1], spec["worker"]["name"])
    doc.core_properties.language = loc
    doc.core_properties.author = spec["employer"]["name"]
    w = words(spec)
    for i, (style, text) in enumerate(parts):
        # A section's lines stay on one page: no last line of an item alone at the head of the next page.
        same_next = i + 1 < len(parts) and parts[i + 1][0] == style
        if style in ("title", "item"):
            # A heading stays with the text under it, never alone at the foot of a page.
            doc.add_heading(text, level=1 if style == "title" else 2).paragraph_format.keep_with_next = True
        elif style == "para":
            p = doc.add_paragraph(text)
            p.paragraph_format.space_after = Pt(4)
            p.paragraph_format.keep_with_next = same_next
        else:
            role, name = text.split("|", 1)
            p = doc.add_paragraph()
            p.paragraph_format.space_before = Pt(28)
            p.paragraph_format.keep_together = True
            p.paragraph_format.keep_with_next = same_next
            p.add_run("_" * 34 + "\n")
            p.add_run(name + "\n").bold = True
            p.add_run(role + "\n")
            p.add_run(w["sign_date"] + (" : " if lang_of(spec, law) == "fr" else ": ") + "____________")
    doc.save(out)


def warnings_for(spec, law):
    out = []
    if law == "us" and str(spec.get("work_state") or "").upper() == "MT":
        out.append("Montana: the Wrongful Discharge from Employment Act (Mont. Code Ann. 39-2-904) may require good "
                   "cause for a discharge after the probationary period, so an at-will sentence may not hold there "
                   "(not proved against the current code). Ask the employer.")
    if law == "uk" and str(spec.get("start") or "") >= "2027-01-01":
        out.append("a start on or after 1 January 2027: the statement of the right to join a trade union planned "
                   "under the Employment Rights Act 2025 may be in force by then; check gov.uk before giving the "
                   "statement (not checked on 2026-10-20)")
    if law == "au":
        out.append("attach the Fair Work Ombudsman's current information statements (fairwork.gov.au); this file "
                   "names them, it does not contain them")
    if law == "be":
        region, lang = belgian_region(spec), lang_of(spec, law)
        if region == "nl" and lang != "nl":
            out.append("the workplace is in the Dutch language area: the Flemish decree of 19 July 1973 asks for Dutch "
                       "(art. 5), with a further version in another language only beside it")
        if region == "fr" and lang != "fr":
            out.append("the workplace is in the French language area: the decree of 30 June 1982 asks for French")
        if region == "brussels":
            out.append("Brussels-Capital: write in Dutch or French by the worker's language")
        if region == "german":
            out.append("the German-speaking area writes in German; this library writes the statement in French or "
                       "Dutch only, so check with the employer")
        if spec.get("probation"):
            out.append("Belgium abolished the trial period for ordinary employment contracts on 1 January 2014; only "
                       "student and temporary agency contracts keep one (first three days)")
    if law == "es":
        try:
            late = dt.date.fromisoformat(str(spec["given"])) > dt.date.fromisoformat(str(spec["start"]))
        except ValueError:
            late = False
        if late:
            out.append("Real Decreto 723/2026 art. 7.1 asks for this information before the employment begins; this "
                       "statement is dated after the start")
    if law == "it" and isinstance(spec.get("collective"), dict) and not spec["collective"].get("code"):
        out.append("a private employer gives the single alphanumeric code CNEL assigns to the national collective "
                   "agreement (D.Lgs. 152/1997 art. 1 c. 1 q-bis)); the files do not give it: say so in your reply")
    if law == "pl":
        out.append("this file repeats the contract's terms and gives the information of Kodeks pracy art. 29 § 3; "
                   "the employment contract itself is concluded in writing (art. 29 § 2)")
    if law == "us" and str(spec.get("work_state") or "").upper() == "NY":
        out.append("New York Labor Law 195(1) asks for the notice in English and in the employee's primary language; "
                   "the New York State Department of Labor publishes its own notice forms in other languages")
    return out


def main(argv):
    if len(argv) != 3:
        print(__doc__.split("\n\n")[1])
        return 2
    spec = json.loads(Path(argv[1]).read_text())
    out = Path(argv[2])
    if out.suffix.lower() != ".docx":
        raise SystemExit("output must end in .docx")
    # Nothing given is dropped: an unknown key, a value of the wrong shape or an item this law's list has no
    # heading for stops the build here.
    spec_guard.guard(spec, HERE.parent / "spec.fields.json", "statement's data file")
    spec_guard.output_guard(out, __file__, "statement")
    # The company's own particulars, written once in the person's folder: what the data file leaves out.
    company.apply(spec, argv[1], "employment-statement")
    lost = not_printed(spec, law_of(spec))
    if lost:
        raise SystemExit("the statement's data file holds what this statement has no heading for; nothing was "
                         "built:\n  - %s\nWrite each term as a line of \"further\" (printed under a last heading, "
                         "before the signatures), or take the key out and say in your reply what was left off."
                         % "\n  - ".join(lost))
    write_docx(spec, out)
    law = law_of(spec)
    print(json.dumps({"file": str(out), "language": locale_of(spec), "law": law,
                      "paper": letter.paper(locale_of(spec)),
                      "fixed_term": str((spec.get("term") or {}).get("type", "permanent")) not in
                      ("permanent", "at-will", "full-time", "part-time", "casual"),
                      "abroad": bool(spec.get("abroad")), "warnings": warnings_for(spec, law)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
