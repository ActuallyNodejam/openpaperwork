#!/usr/bin/env python3
"""A drafting check for a written statement of the terms of employment as a Word file. It reads
whether each particular is there, never whether a term is fair, usual or allowed; that is for the
employer, the worker and their advisers. Its sources, restated in our own words:

  Directive (EU) 2019/1152 on transparent and predictable working conditions, Art. 4(2) (a)-(o),
  4(3), 5(1), 7 and 8 (EUR-Lex CELEX 32019L1152, reused under Commission Decision 2011/833/EU);
  Employment Rights Act 1996 sections 1 to 3, UK (legislation.gov.uk, Open Government Licence v3.0);
  lagen (1982:80) om anställningsskydd 6, 6 c and 6 d §§, Sweden (outside copyright, URL 9 §);
  arbeidsmiljøloven §§ 14-5 to 14-7, 14-9 and 15-6, Norway, as in force from 1 July 2024 (outside
  copyright, åndsverkloven § 14);
  lov nr. 501 af 16. maj 2023 om ansættelsesbeviser og visse arbejdsvilkår §§ 3, 4 and 6, Denmark
  (outside copyright, ophavsretsloven § 9);
  työsopimuslaki (55/2001) 1 luku 4 § and 2 luku 4 §, Finland (outside copyright, tekijänoikeuslaki 9 §);
  Canada Labour Code s. 253.2 and Canada Labour Standards Regulations s. 3.1 (Reproduction of Federal
  Law Order); Ontario Regulation 285/01 s. 1.2 under the Employment Standards Act, 2000 (© King's
  Printer for Ontario, 2024);
  for a US offer letter, the Fair Labor Standards Act (29 U.S.C. 207(a)(1), 213(a)(1); 29 CFR part 541),
  New York Labor Law § 195(1) (read on nysenate.gov), California Labor Code § 2810.5 (read through the Labor
  Commissioner's own notice template, DLSE-NTE rev. 11/2023) and Mont. Code Ann. 39-2-904;
  Fair Work Act 2009 (Cth) ss. 125, 125B, 323, 333E and 333K, Australia (cited; nothing copied);
  the Belgian law of 7 October 2022 arts. 4 to 6 (Justel), with the loi du 3 juillet 1978 art. 67
  (repealed 2014) and 127 for probation and the language decrees of 19 July 1973 (Flemish Community)
  and 30 June 1982 (French Community); Burgerlijk Wetboek 7:655 and 7:652, the Netherlands
  (wetten.overheid.nl); AVRAG § 2 as amended by BGBl. I Nr. 11/2024 with ABGB § 1158 (2) and AngG
  § 19 (2), Austria (RIS); the Terms of Employment (Information) Act 1994 ss. 3, 3A, 4 and 6D as
  amended by S.I. No. 686 of 2022, Ireland (irishstatutebook.ie, Oireachtas PSI Licence). All
  restated in our own words.
  Wave 9. Spain: Real Decreto 723/2026 of 9 September arts. 2 to 4, 6 and 7, in force 5 October 2026 (it
  transposes the Directive, develops Estatuto de los Trabajadores art. 8.5 and repealed Real Decreto
  1659/1998), with ET art. 14 for probation (BOE consolidated texts, informative only; Ley de Propiedad
  Intelectual art. 13 and the BOE reuse conditions of 27 June 2024). Italy: decreto legislativo 26 maggio
  1997, n. 152 arts. 1 and 2 as in force from 28 June 2026 (rewritten by D.Lgs. 104/2022, comma 5-bis by
  D.L. 48/2023, letter q-bis by D.L. 62/2026), with D.Lgs. 104/2022 art. 7 for probation (Normattiva; legge
  633/1941 art. 5). Poland: Kodeks pracy arts. 25, 29 and 29(1), ISAP consolidated text of 18 August 2026
  (ustawa o prawie autorskim i prawach pokrewnych art. 4 pkt 1). Restated in our own words.

  EMPLOY-ITEMS      Every particular the statement's law lists is there or marked not applicable;
                    the ones the law always asks for can never be marked so.
  EMPLOY-DATES      The start date is given; a fixed term ends after it starts; the statement is
                    dated within the time its law gives; an Australian fixed term over two years
                    is flagged (s 333E), and so is an option to renew or extend used more than
                    once, or one that runs past two years or gives no latest end (s 333E(1)(b), (c)).
  EMPLOY-PROBATION  A probationary period states its length; one over the law's limit is flagged
                    (six months under Art. 8(1), LAS 6 §, aml. § 15-6, lov 501 § 6, TSL 1:4 §), as is
                    one too long for a fixed term (half in Norway and Finland, a quarter in Denmark).
  EMPLOY-PAY        Pay states the amount, how often it is paid and how; in Australia at least monthly.
  EMPLOY-ABROAD     Work abroad over the law's threshold names the country, the period, the
                    currency, the benefits and the return home, given before departure.
  EMPLOY-LANG       Every heading is in the statement's own language.
  EMPLOY-REFERENCE  A particular the law will not let a statement give by pointing to a law or an
                    agreement states the term itself (aml. § 14-6 (2), lov 501 § 3 stk. 4, TSL 2:4 §
                    4 mom., Art. 4(3), ERA s.2(2) and (3)).
  EMPLOY-NO-TEMP    A Norwegian temporary hire gives its expected length and its basis (§ 14-6 (1) e).
  EMPLOY-NO-HOURS   A Norwegian contract gives the length and placing of the daily and weekly hours and
                    the length of the breaks (§ 14-6 (1) j and k).
  EMPLOY-FI-TEMP    A Finnish fixed term gives its end or expected end and its ground (2:4 § 3 kohta).
  EMPLOY-US-ATWILL  A US offer says the employment is at will or for a set term; at will in Montana is
                    flagged (39-2-904).
  EMPLOY-US-FLSA    The offer states the FLSA classification; a non-exempt one says overtime is paid at
                    one and one-half times the regular rate; an exempt one paid by the hour is flagged.
  EMPLOY-US-STATE   Work in New York or California: the state's pay notice items are there.
  EMPLOY-US-WORDING The letter never says a federal law requires it.
  EMPLOY-AU-STATEMENTS  The Fair Work Information Statement is given (s 125), and the casual (s 125B) or
                    fixed term (s 333K) statement where it applies.
  EMPLOY-IE-CORE    An Irish statement gives the five-day core terms of s. 3(1A): both full names, the
                    employer's address, the hours expected per normal day and per normal week, the pay
                    with its pay reference period, and the overtime terms.
  EMPLOY-SIGNED     A Dutch opgave is signed by the employer (BW 7:655 (3)); an Irish statement is
                    signed and dated by or for the employer (s. 3(4), s. 3A).
  EMPLOY-BE-LANG    A Belgian statement is in the language of the region its workplace is in: Dutch in
                    Flanders, French in Wallonia, either in Brussels.
  EMPLOY-AGREEMENT  The collective agreement is identified the way the law asks: in Spain by its code, the
                    bulletin and date it was published in and its period of validity (Real Decreto 723/2026
                    art. 3.2 o)); in Italy by the parties that signed it and, for a private employer, the
                    CNEL code of the national agreement (D.Lgs. 152/1997 art. 1 c. 1 q) and q-bis)).
  EMPLOY-PL-CONTRACT  A Polish statement repeats the contract's own terms of Kodeks pracy art. 29 § 1 as
                    terms, never as pointers: the type of contract and the date it was concluded, the kind
                    and the place of work, the pay, the working time basis (wymiar czasu pracy), the first day.

Spain, Italy and Poland let a statement give some items by naming the law or the collective agreement that
sets them (RD 723/2026 art. 3.3; D.Lgs. 152/1997 art. 1 c. 5-bis; Kodeks pracy art. 29 § 3(1), provisions of
law only). The check accepts such a pointer for those items, pay included in Spain and Italy, and for no other.

Belgium's art. 5 (training, annual holiday, ending the relationship, collective agreements and the joint
committee, the social security institution) binds this document only for a worker outside the work rules act
of 8 April 1965; for everyone else the work rules carry those items. The statement therefore gives each one
or points to the work rules (arbeidsreglement, règlement de travail), and the check accepts either.

The check never works out a notice period, a number of holiday days, a minimum wage or an overtime
rate. With a statement spec beside the file (skills/employment-statement) it also compares names,
dates and amounts with the spec; without one it reads the statement's own headings.
check(rule_id, path, case, stage) -> (passed, evidence); passed is None when the rule does not apply.
"""
import datetime as dt
import html
import json
import re
import sys
import zipfile
from decimal import Decimal, InvalidOperation
from pathlib import Path

# item, the words its heading starts with per language, and where each law asks for it
ITEMS = [
    ("parties", {'en': ('the parties', 'parties', 'employer and worker', 'employer and employee'), 'sv': ('parter', 'parterna', 'arbetsgivare och arbetstagare'), 'nb': ('partene', 'parter'), 'da': ('parterne', 'parter'), 'fi': ('sopijapuolet', 'osapuolet'), 'fr': ('les parties', 'parties'), 'nl': ('partijen',), 'de': ('vertragsparteien', 'arbeitgeber und arbeitnehmer')},
     {'eu': 'Art. 4(2)(a)', 'se': 'LAS 6 c § 1', 'uk': 'ERA s.1(3)(a)', 'no': 'aml. § 14-6 (1) a', 'dk': 'lov 501 § 3, stk. 2, nr. 1', 'fi': 'TSL 2:4 § 3 mom. 1', 'us': "the offer's parties", 'ca': 'CLSR 3.1(a)', 'on': 'O. Reg. 285/01 s. 1.2 (2) 1', 'au': "the employment's parties", 'be': 'loi du 7 octobre 2022 art. 4 § 2 1°', 'nl': 'BW 7:655 (1) a', 'at': 'AVRAG § 2 (2) 1, 2', 'ie': 's. 3(1A)(a), (b)'}),
    ("place", {'en': ('place of work', 'places of work', 'workplace', 'place of employment', 'where the work is'), 'sv': ('arbetsplats', 'arbetsort'), 'nb': ('arbeidssted', 'arbeidsplass'), 'da': ('arbejdssted',), 'fi': ('työntekopaikka', 'työpaikka'), 'fr': ('lieu de travail',), 'nl': ('plaats van de arbeid', 'plaats van het werk', 'werkplek'), 'de': ('arbeitsort', 'dienstort', 'einsatzort')},
     {'eu': 'Art. 4(2)(b)', 'se': 'LAS 6 c § 1', 'uk': 'ERA s.1(4)(h)', 'no': 'aml. § 14-6 (1) b', 'dk': 'lov 501 § 3, stk. 2, nr. 2', 'fi': 'TSL 2:4 § 3 mom. 5', 'us': 'the place of work', 'ca': 'CLSR 3.1(c)', 'on': 'O. Reg. 285/01 s. 1.2 (2) 3', 'au': 'the place of work', 'be': 'art. 4 § 2 2°', 'nl': 'BW 7:655 (1) b', 'at': 'AVRAG § 2 (2) 6', 'ie': 's. 3(1A)(g)'}),
    ("job", {'en': ('job title', 'job', 'title and duties', 'position', 'role', 'duties'), 'sv': ('arbetsuppgifter', 'befattning', 'yrkesbenämning', 'tjänstetitel'), 'nb': ('stilling', 'arbeidsoppgaver'), 'da': ('stilling', 'arbejdsopgaver'), 'fi': ('työtehtävät', 'tehtävät'), 'fr': ('poste', 'fonctions', 'fonction'), 'nl': ('functie', 'functie en aard van de arbeid'), 'de': ('verwendung und tätigkeit', 'verwendung', 'tätigkeit')},
     {'eu': 'Art. 4(2)(c)', 'se': 'LAS 6 c § 2', 'uk': 'ERA s.1(4)(f)', 'no': 'aml. § 14-6 (1) c', 'dk': 'lov 501 § 3, stk. 2, nr. 3', 'fi': 'TSL 2:4 § 3 mom. 6', 'us': 'the position', 'ca': 'CLSR 3.1(b)', 'on': 'the job', 'au': 'the position', 'be': 'art. 4 § 2 3°', 'nl': 'BW 7:655 (1) c', 'at': 'AVRAG § 2 (2) 8', 'ie': 's. 3(1A)(h)'}),
    ("start", {'en': ('start date', 'start of employment', 'date of commencement', 'commencement', 'date employment began', 'employment began'), 'sv': ('tillträdesdag', 'tillträde', 'anställningens början', 'startdatum'), 'nb': ('tiltredelse', 'tiltredelsesdato', 'arbeidsforholdets begynnelse'), 'da': ('tiltrædelse', 'tiltrædelsesdato', 'ansættelsens begyndelse'), 'fi': ('työnteon alkaminen', 'työn alkaminen', 'alkamisajankohta'), 'fr': ("début de l'emploi", 'date du début', 'date de début'), 'nl': ('datum van indiensttreding', 'indiensttreding', 'aanvangsdatum'), 'de': ('beginn des arbeitsverhältnisses', 'eintritt')},
     {'eu': 'Art. 4(2)(d)', 'se': 'LAS 6 c § 1', 'uk': 'ERA s.1(3)(b)', 'no': 'aml. § 14-6 (1) d', 'dk': 'lov 501 § 3, stk. 2, nr. 4', 'fi': 'TSL 2:4 § 3 mom. 2', 'us': 'the start date', 'ca': 'CLSR 3.1(d)', 'on': 'the start date', 'au': 'the start date', 'be': 'art. 4 § 2 4°', 'nl': 'BW 7:655 (1) d', 'at': 'AVRAG § 2 (2) 3', 'ie': 's. 3(1A)(i)'}),
    ("term", {'en': ('type and length', 'type of employment', 'length of employment', 'duration of employment', 'term of employment', 'form of employment', 'fixed term', 'fixed-term', 'permanent', 'employment relationship'), 'sv': ('anställningsform', 'anställningens längd', 'anställningstid'), 'nb': ('ansettelsesform', 'varighet'), 'da': ('ansættelsens varighed', 'ansættelsesform'), 'fi': ('työsopimuksen kesto', 'sopimuksen kesto'), 'fr': ("durée de l'emploi", 'durée', 'durée de la relation de travail'), 'nl': ('duur van de arbeidsovereenkomst', 'duur van de arbeidsrelatie'), 'de': ('dauer des arbeitsverhältnisses', 'befristung')},
     {'eu': 'Art. 4(2)(e)', 'se': 'LAS 6 c § 3', 'uk': 'ERA s.1(4)(g)', 'no': 'aml. § 14-6 (1) e', 'dk': 'lov 501 § 3, stk. 2, nr. 5', 'fi': 'TSL 2:4 § 3 mom. 3', 'us': 'at-will or a set term', 'ca': 'CLSR 3.1(e)', 'au': 'the type of employment', 'be': 'art. 4 § 2 5°', 'nl': 'BW 7:655 (1) e, n', 'at': 'AVRAG § 2 (2) 4', 'ie': 's. 3(1A)(c)'}),
    ("agency", {'en': ('user undertaking', 'agency work', 'temporary agency'), 'sv': ('kundföretag', 'uthyrning', 'bemanning'), 'nb': ('innleier',), 'da': ('brugervirksomhed',), 'fi': ('käyttäjäyritys',), 'nl': ('uitzend- of payrollovereenkomst', 'uitzendovereenkomst'), 'de': ('beschäftigerbetrieb',)},
     {'eu': 'Art. 4(2)(f)', 'se': 'LAS 6 c § 8', 'no': 'aml. § 14-6 (1) o', 'dk': 'lov 501 § 3, stk. 2, nr. 6', 'fi': 'TSL 2:4 § 3 mom. 10', 'nl': 'BW 7:655 (1) m, p', 'ie': 's. 3(1)(o)'}),
    ("probation", {'en': ('probation', 'probationary period', 'trial period'), 'sv': ('provanställning', 'prövotid'), 'nb': ('prøvetid',), 'da': ('prøvetid',), 'fi': ('koeaika',), 'fr': ('période de probation', 'probation', "période d'essai"), 'nl': ('proeftijd',), 'de': ('probezeit',)},
     {'eu': 'Art. 4(2)(g)', 'se': 'LAS 6 c § 3 c', 'uk': 'ERA s.1(4)(ga)', 'no': 'aml. § 14-6 (1) f', 'dk': 'lov 501 § 3, stk. 2, nr. 7', 'fi': 'TSL 2:4 § 3 mom. 4', 'ca': 'CLSR 3.1(f)', 'au': 'probation', 'be': 'art. 4 § 2 7°', 'nl': 'BW 7:655 (1) q', 'at': 'AVRAG § 2 (2) 14', 'ie': 's. 3(1A)(k)'}),
    ("training", {'en': ('training', 'required training'), 'sv': ('utbildning', 'kompetensutveckling'), 'nb': ('kompetanseutvikling', 'opplæring'), 'da': ('uddannelse',), 'fi': ('koulutus',), 'fr': ('formation requise', 'formation'), 'nl': ('scholing', 'opleiding'), 'de': ('fortbildung',)},
     {'eu': 'Art. 4(2)(h)', 'se': 'LAS 6 c § 9', 'uk': 'ERA s.1(4)(l)-(n)', 'no': 'aml. § 14-6 (1) p', 'dk': 'lov 501 § 3, stk. 2, nr. 13', 'fi': 'TSL 2:4 § 3 mom. 11', 'ca': 'CLSR 3.1(h)', 'be': 'art. 5 1°', 'nl': 'BW 7:655 (1) r', 'at': 'AVRAG § 2 (2) 15', 'ie': 's. 3(1)(n)'}),
    ("other_leave", {"en": ("other paid leave",)}, {"uk": "ERA s.1(4)(d)(iia)"}),
    ("leave", {'en': ('paid leave', 'annual leave', 'holidays', 'holiday', 'leave', 'paid time off'), 'sv': ('betald semester', 'semester'), 'nb': ('ferie',), 'da': ('ferie',), 'fi': ('vuosiloma',), 'fr': ('congés payés', 'congés', 'vacances annuelles'), 'nl': ('vakantie en ander betaald verlof', 'jaarlijkse vakantie', 'vakantie'), 'de': ('urlaub', 'erholungsurlaub')},
     {'eu': 'Art. 4(2)(i)', 'se': 'LAS 6 c § 10', 'uk': 'ERA s.1(4)(d)(i)', 'no': 'aml. § 14-6 (1) g', 'dk': 'lov 501 § 3, stk. 2, nr. 8', 'fi': 'TSL 2:4 § 3 mom. 12', 'au': 'leave under the National Employment Standards', 'be': 'art. 5 2°', 'nl': 'BW 7:655 (1) f', 'at': 'AVRAG § 2 (2) 10', 'ie': 's. 3(1)(j)'}),
    ("termination", {'en': ('ending the employment', 'ending employment', 'termination', 'notice of termination', 'notice periods', 'notice'), 'sv': ('uppsägning', 'anställningens upphörande', 'avslut'), 'nb': ('oppsigelse',), 'da': ('opsigelse',), 'fi': ('irtisanomisaika', 'irtisanominen'), 'fr': ("fin de l'emploi", 'fin de la relation de travail'), 'nl': ('opzegging', 'beëindiging van de arbeidsrelatie', 'einde van de arbeidsovereenkomst'), 'de': ('kündigung', 'beendigung')},
     {'eu': 'Art. 4(2)(j)', 'se': 'LAS 6 c § 3 a and 11', 'uk': 'ERA s.1(4)(e)', 'no': 'aml. § 14-6 (1) h', 'dk': 'lov 501 § 3, stk. 2, nr. 9', 'fi': 'TSL 2:4 § 3 mom. 13', 'au': 'notice under the National Employment Standards', 'be': 'art. 5 3°', 'nl': 'BW 7:655 (1) g', 'at': 'AVRAG § 2 (2) 5', 'ie': 's. 3(1)(l)'}),
    ("pay", {'en': ('pay', 'remuneration', 'salary', 'wages', 'wage'), 'sv': ('lön', 'löneförmåner'), 'nb': ('lønn',), 'da': ('løn',), 'fi': ('palkka',), 'fr': ('salaire', 'rémunération'), 'nl': ('loon', 'salaris'), 'de': ('entgelt', 'gehalt', 'lohn')},
     {'eu': 'Art. 4(2)(k)', 'se': 'LAS 6 c § 4', 'uk': 'ERA s.1(4)(a), (b)', 'no': 'aml. § 14-6 (1) i', 'dk': 'lov 501 § 3, stk. 2, nr. 10', 'fi': 'TSL 2:4 § 3 mom. 7', 'us': 'the pay', 'ca': 'CLSR 3.1(j), (k)', 'on': 'O. Reg. 285/01 s. 1.2 (2) 4, 5', 'au': 'Fair Work Act 2009 s 323', 'be': 'art. 4 § 2 6°', 'nl': 'BW 7:655 (1) h', 'at': 'AVRAG § 2 (2) 9', 'ie': 's. 3(1A)(d); s. 3(1)(h)'}),
    ("breaks", {"en": ("breaks",), "nb": ("pauser",)}, {"no": "aml. § 14-6 (1) k"}),
    ("special_hours", {"en": ("special working-time",), "nb": ("særlig arbeidstidsordning",)}, {"no": "aml. § 14-6 (1) l"}),
    ("overtime", {"en": ("shift changes and work beyond",), "nb": ("vaktendringer",)}, {"no": "aml. § 14-6 (1) m"}),
    ("hours", {'en': ('working hours', 'hours of work', 'working time', 'hours'), 'sv': ('arbetstid', 'arbetstider'), 'nb': ('arbeidstid',), 'da': ('arbejdstid',), 'fi': ('työaika',), 'fr': ('heures de travail', 'horaire de travail', 'horaire'), 'nl': ('arbeidsduur', 'arbeidstijd', 'uurrooster'), 'de': ('arbeitszeit', 'normalarbeitszeit')},
     {'eu': 'Art. 4(2)(l), (m)', 'se': 'LAS 6 c § 5-7', 'uk': 'ERA s.1(4)(c)', 'no': 'aml. § 14-6 (1) j', 'dk': 'lov 501 § 3, stk. 2, nr. 11, 12', 'fi': 'TSL 2:4 § 3 mom. 8, 9', 'us': 'the hours', 'ca': 'CLSR 3.1(i)', 'on': 'O. Reg. 285/01 s. 1.2 (2) 6', 'au': 'the hours', 'be': 'art. 4 § 2 8°, 9°', 'nl': 'BW 7:655 (1) i', 'at': 'AVRAG § 2 (2) 11', 'ie': 's. 3(1A)(e), (j)'}),
    ("collective", {'en': ('collective agreement', 'collective agreements'), 'sv': ('kollektivavtal',), 'nb': ('tariffavtale', 'tariffavtaler'), 'da': ('kollektive overenskomster', 'kollektiv overenskomst'), 'fi': ('työehtosopimus',), 'fr': ('conventions collectives', 'convention collective'), 'nl': ('collectieve arbeidsovereenkomst', 'collectieve arbeidsovereenkomsten', 'cao'), 'de': ('kollektivvertrag', 'betriebsvereinbarung')},
     {'eu': 'Art. 4(2)(n)', 'se': 'LAS 6 c § 13', 'uk': 'ERA s.1(4)(j)', 'no': 'aml. § 14-6 (1) n', 'dk': 'lov 501 § 3, stk. 2, nr. 14', 'fi': 'TSL 2:4 § 3 mom. 14', 'be': 'art. 5 4°', 'nl': 'BW 7:655 (1) l', 'at': 'AVRAG § 2 (2) 12', 'ie': 's. 3(1)(fa), (m)'}),
    ("social", {'en': ('social security', 'social protection', 'social insurance'), 'sv': ('social trygghet', 'socialförsäkring', 'arbetsgivaravgifter'), 'nb': ('sosial trygghet',), 'da': ('social sikring',), 'fi': ('sosiaaliturva',), 'nl': ('sociale zekerheid', 'socialezekerheidsinstelling'), 'fr': ('institution de sécurité sociale', 'sécurité sociale')},
     {'eu': 'Art. 4(2)(o)', 'se': 'LAS 6 c § 12', 'no': 'aml. § 14-6 (1) q', 'dk': 'lov 501 § 3, stk. 2, nr. 15', 'be': 'art. 5 5°', 'nl': 'BW 7:655 (1) s', 'ie': 's. 3(1)(q)'}),
    ("insurer", {'en': ('pension and accident insurance',), 'fi': ('eläke- ja tapaturmavakuutus', 'vakuutuslaitos'), 'de': ('sozialversicherung und betriebliche vorsorgekasse', 'betriebliche vorsorgekasse', 'sozialversicherung')},
     {'fi': 'TSL 2:4 § 3 mom. 15', 'at': 'AVRAG § 2 (2) 13'}),
    ("qualifications", {"en": ("qualifications",), "fr": ("compétences nécessaires", "compétences")}, {"ca": "CLSR 3.1(g)"}),
    ("deductions", {"en": ("mandatory deductions", "deductions"), "fr": ("retenues obligatoires", "retenues")},
     {"ca": "CLSR 3.1(l)"}),
    ("expenses", {"en": ("work-related expenses", "expenses"), "fr": ("dépenses liées au travail", "dépenses")},
     {"ca": "CLSR 3.1(m)"}),
    ("contact", {"en": ("employer contact", "contact"), "fr": ("coordonnées de l'employeur", "coordonnées")},
     {"on": "O. Reg. 285/01 s. 1.2 (2) 2"}),
    ("classification", {"en": ("overtime classification", "flsa classification", "classification")},
     {"us": "29 U.S.C. 207(a)(1), 213(a)(1)"}),
    ("conditions", {"en": ("conditions of this offer", "conditions")}, {}),
    ("super", {"en": ("superannuation",)}, {"au": "Superannuation Guarantee"}),
    ("award", {"en": ("award or agreement", "award", "enterprise agreement")}, {"au": "award coverage"}),
    ("statements", {"en": ("information statements", "fair work information statement")},
     {"au": "Fair Work Act 2009 ss 125, 125B, 333K"}),
    ("disciplinary", {"en": ("disciplinary and grievance", "disciplinary", "grievance")}, {"uk": "ERA s.3(1)"}),
    ("state_notice", {"en": ("notice of pay rate", "notice to employee")}, {"us": "NY Lab. Law 195(1); Cal. Lab. Code 2810.5"}),
    ("sickness", {'en': ('sickness', 'sick pay', 'incapacity', 'sick leave'), 'sv': ('sjukdom', 'sjuklön'), 'nb': ('sykdom',), 'da': ('sygdom',), 'fi': ('sairausajan palkka',), 'nl': ('ziekte',), 'de': ('krankenstand',)}, {'uk': 'ERA s.1(4)(d)(ii)', 'ie': 's. 3(1)(k)(i)'}),
    ("pension", {'en': ('pensions', 'pension'), 'sv': ('tjänstepension', 'pension'), 'nb': ('pensjon',), 'da': ('pension',), 'fi': ('eläke',), 'nl': ('pensioenregeling', 'pensioen'), 'de': ('betriebspension', 'pensionskasse')}, {'uk': 'ERA s.1(4)(d)(iii)', 'nl': 'BW 7:655 (1) j', 'ie': 's. 3(1)(k)(ii)'}),
    ("benefits", {'en': ('other benefits',), 'sv': ('övriga förmåner',), 'nb': ('andre ytelser',), 'da': ('øvrige goder',), 'fi': ('muut edut',), 'fr': ('autres avantages',), 'nl': ('overige voorzieningen',), 'de': ('sonstige leistungen',)}, {'uk': 'ERA s.1(4)(da)'}),
    ("abroad", {'en': ('work abroad', 'working abroad', 'work outside'), 'sv': ('arbete utomlands', 'utlandstjänstgöring'), 'nb': ('arbeid i utlandet',), 'da': ('arbejde i udlandet',), 'fi': ('ulkomaantyö',), 'fr': ("travail à l'étranger",), 'nl': ('arbeid buiten nederland', 'werk in het buitenland'), 'de': ('tätigkeit im ausland', 'auslandstätigkeit')},
     {'eu': 'Art. 7(1)', 'se': 'LAS 6 d §', 'uk': 'ERA s.1(4)(k)', 'no': 'aml. § 14-7', 'dk': 'lov 501 § 4', 'fi': 'TSL 2:4 § 3 mom. 16', 'be': 'art. 6', 'nl': 'BW 7:655 (1) k', 'at': 'AVRAG § 2 (3)', 'ie': 's. 4'}),
    ("on_call", {"en": ("on-call contract",), "nl": ("oproepovereenkomst",)}, {"nl": "BW 7:655 (1) o"}),
    ("grading", {"en": ("grading",), "de": ("einstufung",)}, {"at": "AVRAG § 2 (2) 7"}),
    ("minimum_wage", {"en": ("average hourly rate of pay", "average hourly rate")}, {"ie": "s. 3(1)(ga)"}),
    ("tips", {"en": ("tips, gratuities and service charges", "tips")}, {"ie": "s. 3(1A)(f)"}),
    ("_sign", {'en': ('signatures', 'signature', 'signed', 'for the employer'), 'sv': ('underskrifter', 'underskrift', 'för arbetsgivaren'), 'nb': ('underskrifter', 'underskrift'), 'da': ('underskrifter', 'underskrift'), 'fi': ('allekirjoitukset',), 'fr': ('signatures',), 'nl': ('ondertekening', 'handtekeningen'), 'de': ('unterschriften', 'unterschrift')}, {}),
]
# Wave 9: the Spanish, Italian and Polish headings, where each law asks for the item, and four items of
# their own: automated decision systems (Spain k, Italy s), the equality plan and the harassment protocol
# (Spain l, m), how the terms may be changed (Spain q) and Poland's work regulations (art. 29 § 3 pkt 1 m).
ES_, IT_, PL_ = "RD 723/2026 art. 3.2 ", "D.Lgs. 152/1997 art. 1 c. 1 ", "KP art. 29 "
_W9 = {
    "parties": ({"es": ("partes", "las partes"), "it": ("parti", "le parti"), "pl": ("strony umowy", "strony")},
                {"es": ES_ + "a)", "it": IT_ + "a), c)", "pl": PL_ + "§ 1"}),
    "place": ({"es": ("domicilio social y centro de trabajo", "centro de trabajo", "lugar de trabajo"),
               "it": ("luogo di lavoro",), "pl": ("miejsce wykonywania pracy", "miejsca wykonywania pracy", "miejsce pracy")},
              {"es": ES_ + "c)", "it": IT_ + "b)", "pl": PL_ + "§ 1 pkt 2; § 3 pkt 1 g)"}),
    "job": ({"es": ("puesto de trabajo", "grupo profesional", "contenido de la prestación"),
             "it": ("inquadramento", "mansioni", "qualifica"), "pl": ("rodzaj pracy", "stanowisko")},
            {"es": ES_ + "d), e)", "it": IT_ + "d)", "pl": PL_ + "§ 1 pkt 1"}),
    "start": ({"es": ("fecha de comienzo", "fecha de inicio", "comienzo de la relación laboral"),
               "it": ("data di inizio", "inizio del rapporto"), "pl": ("dzień rozpoczęcia pracy", "rozpoczęcie pracy")},
              {"es": ES_ + "b)", "it": IT_ + "e)", "pl": PL_ + "§ 1 pkt 5"}),
    "term": ({"es": ("duración del contrato", "tipo de contrato", "modalidad de contrato"),
              "it": ("tipologia del rapporto", "tipologia di rapporto", "durata del rapporto"),
              "pl": ("rodzaj umowy", "czas trwania umowy")},
             {"es": ES_ + "b), d)", "it": IT_ + "f)", "pl": PL_ + "§ 1 and pkt 6, 7"}),
    "agency": ({"es": ("empresa usuaria", "empresa de trabajo temporal"),
                "it": ("imprese utilizzatrici", "impresa utilizzatrice", "somministrazione"),
                "pl": ("pracodawca użytkownik",)},
               {"es": ES_ + "j)", "it": IT_ + "g)"}),
    "probation": ({"es": ("periodo de prueba", "período de prueba"), "it": ("periodo di prova",), "pl": ("okres próbny",)},
                  {"es": ES_ + "h)", "it": IT_ + "h)", "pl": PL_ + "§ 1 pkt 6; art. 25 § 2"}),
    "training": ({"es": ("formación",), "it": ("formazione",), "pl": ("szkolenia", "szkolenie")},
                 {"es": ES_ + "i)", "it": IT_ + "i)", "pl": PL_ + "§ 3 pkt 1 k)"}),
    "leave": ({"es": ("vacaciones",), "it": ("ferie", "congedi"), "pl": ("urlop", "urlopy", "płatny urlop")},
              {"es": ES_ + "g) 4.º", "it": IT_ + "l)", "pl": PL_ + "§ 3 pkt 1 i)"}),
    "termination": ({"es": ("extinción del contrato", "extinción", "preaviso"), "it": ("preavviso", "recesso"),
                     "pl": ("rozwiązanie stosunku pracy", "wypowiedzenie", "okresy wypowiedzenia")},
                    {"es": ES_ + "n)", "it": IT_ + "m)", "pl": PL_ + "§ 3 pkt 1 j)"}),
    "pay": ({"es": ("salario", "retribución"), "it": ("retribuzione", "compenso"), "pl": ("wynagrodzenie",)},
            {"es": ES_ + "f)", "it": IT_ + "n)", "pl": PL_ + "§ 1 pkt 3; § 3 pkt 1 h)"}),
    "hours": ({"es": ("jornada de trabajo", "jornada", "tiempo de trabajo"), "it": ("orario di lavoro", "orario"),
               "pl": ("czas pracy", "wymiar czasu pracy")},
              {"es": ES_ + "g) 1.º-3.º, 5.º", "it": IT_ + "o), p)", "pl": PL_ + "§ 1 pkt 4; § 3 pkt 1 a)-f)"}),
    "collective": ({"es": ("convenio colectivo", "convenios colectivos"),
                    "it": ("contratto collettivo", "contratti collettivi", "ccnl"),
                    "pl": ("układ zbiorowy", "układy zbiorowe", "porozumienie zbiorowe")},
                   {"es": ES_ + "o)", "it": IT_ + "q), q-bis)", "pl": PL_ + "§ 3 pkt 1 l)"}),
    "social": ({"es": ("seguridad social",), "it": ("enti previdenziali", "previdenza e assicurazione", "sicurezza sociale"),
                "pl": ("ubezpieczenia społeczne", "zabezpieczenie społeczne")},
               {"es": ES_ + "p)", "it": IT_ + "r)", "pl": PL_ + "§ 3 pkt 2"}),
    "algorithms": ({"en": ("automated decision",), "es": ("sistemas algorítmicos", "sistemas automatizados"),
                    "it": ("sistemi decisionali", "sistemi di monitoraggio", "sistemi automatizzati")},
                   {"es": ES_ + "k)", "it": IT_ + "s), art. 1-bis"}),
    "equality": ({"en": ("equality plan",), "es": ("plan de igualdad", "igualdad")}, {"es": ES_ + "l), m)"}),
    "changes": ({"en": ("changes to the terms",), "es": ("modificación de las condiciones", "modificaciones")},
                {"es": ES_ + "q)"}),
    "rules": ({"en": ("work regulations",), "pl": ("regulamin pracy", "organizacja pracy")}, {"pl": PL_ + "§ 3 pkt 1 m)"}),
    "sickness": ({"es": ("incapacidad temporal",), "it": ("malattia",), "pl": ("choroba",)}, {}),
    "pension": ({"es": ("plan de pensiones",), "it": ("previdenza complementare",), "pl": ("pracownicze plany kapitałowe",)}, {}),
    "benefits": ({"es": ("otros beneficios",), "it": ("altri benefici",), "pl": ("inne świadczenia",)}, {}),
    "abroad": ({"es": ("trabajo en el extranjero", "prestación de servicios en el extranjero"),
                "it": ("lavoro all'estero", "prestazioni di lavoro all'estero"),
                "pl": ("praca za granicą", "praca poza granicami kraju")},
               {"es": "RD 723/2026 art. 4", "it": "D.Lgs. 152/1997 art. 2", "pl": "KP art. 29(1) § 2"}),
    "_sign": ({"es": ("firmas", "firma"), "it": ("firme", "firma"), "pl": ("podpisy", "podpis")}, {}),
}
_KNOWN = {item: (labels, refs) for item, labels, refs in ITEMS}
for _item, (_labels, _refs) in _W9.items():
    if _item in _KNOWN:
        _KNOWN[_item][0].update(_labels)
        _KNOWN[_item][1].update(_refs)
    else:
        ITEMS.insert(len(ITEMS) - 1, (_item, _labels, _refs))        # before the signatures
LABELS = {item: tuple(x for v in labels.values() for x in v) for item, labels, _ in ITEMS}
LABELS_BY_LANG = {item: labels for item, labels, _ in ITEMS}
REFS = {item: refs for item, _, refs in ITEMS}
NAME = {"parties": "the parties", "place": "the place of work", "job": "the job title or description",
        "start": "the start date", "term": "the type and length of the employment",
        "agency": "the user undertakings (agency work)", "probation": "the probationary period",
        "training": "training", "leave": "paid leave", "other_leave": "other paid leave",
        "termination": "how the employment ends, with notice", "pay": "pay", "hours": "working hours",
        "breaks": "the breaks", "special_hours": "a special working-time arrangement",
        "overtime": "shift changes and work beyond the agreed hours", "collective": "collective agreements",
        "social": "social security", "sickness": "sickness and sick pay", "pension": "pensions",
        "benefits": "other benefits", "abroad": "work abroad", "disciplinary": "the disciplinary and grievance note",
        "insurer": "the pension and accident insurers", "qualifications": "the qualifications",
        "deductions": "the mandatory deductions", "expenses": "how work-related expenses are claimed",
        "contact": "the employer's contact details", "classification": "the FLSA classification",
        "super": "superannuation", "award": "the award or agreement", "statements": "the information statements",
        "conditions": "the offer's conditions", "state_notice": "the state pay notice",
        "on_call": "whether it is an on-call contract", "grading": "the classification in a pay scheme",
        "minimum_wage": "the note on asking for the average hourly rate (National Minimum Wage Act 2000 s. 23)",
        "tips": "the policy on tips and service charges",
        "algorithms": "automated decision or monitoring systems",
        "equality": "the equality plan and the protocol against harassment",
        "changes": "how the terms may be changed", "rules": "the work regulations"}
EU = ["parties", "place", "job", "start", "term", "agency", "probation", "training", "leave", "termination",
      "pay", "hours", "collective", "social"]
WANT = {
    "eu": EU, "se": EU,
    "uk": ["parties", "start", "job", "place", "term", "probation", "pay", "hours", "leave", "other_leave", "sickness",
           "pension", "benefits", "termination", "collective", "training", "disciplinary"],
    "no": ["parties", "place", "job", "start", "term", "probation", "leave", "termination", "pay", "hours", "breaks",
           "special_hours", "overtime", "collective", "agency", "training", "social"],
    "dk": ["parties", "place", "job", "start", "term", "agency", "probation", "leave", "termination", "pay", "hours",
           "training", "collective", "social"],
    "fi": ["parties", "start", "term", "probation", "place", "job", "pay", "hours", "agency", "training", "leave",
           "termination", "collective", "insurer"],
    "us": ["parties", "job", "start", "place", "term", "classification", "pay", "hours"],
    "ca": ["parties", "job", "place", "start", "term", "probation", "qualifications", "training", "hours", "pay",
           "deductions", "expenses"],
    "on": ["parties", "contact", "place", "pay", "hours"],
    "au": ["parties", "job", "place", "start", "term", "pay", "hours", "leave", "termination", "statements"],
    "be": ["parties", "place", "job", "start", "term", "pay", "probation", "hours", "training", "leave", "termination",
           "collective", "social"],
    "nl": ["parties", "place", "job", "start", "term", "leave", "termination", "pay", "hours", "pension", "collective",
           "agency", "on_call", "probation", "training", "social"],
    "at": ["parties", "start", "term", "termination", "place", "grading", "job", "pay", "leave", "hours", "collective",
           "insurer", "probation", "training"],
    "ie": ["parties", "place", "job", "start", "term", "probation", "pay", "hours", "leave", "sickness", "pension",
           "termination", "collective", "training", "agency", "social", "minimum_wage"],
    # Real Decreto 723/2026 art. 3.2 a) to q)
    "es": ["parties", "start", "term", "place", "job", "pay", "hours", "leave", "probation", "training", "agency",
           "algorithms", "equality", "termination", "collective", "social", "changes"],
    # D.Lgs. 152/1997 art. 1 c. 1 a) to s)
    "it": ["parties", "place", "job", "start", "term", "agency", "probation", "training", "leave", "termination", "pay",
           "hours", "collective", "social", "algorithms"],
    # Kodeks pracy art. 29 § 1 (the contract's own terms), then § 3 pkt 1 a) to m) and pkt 2
    "pl": ["parties", "term", "job", "place", "pay", "hours", "start", "probation", "leave", "termination", "training",
           "collective", "rules", "social"],
}
MUST = {
    "eu": {"parties", "place", "job", "start", "leave", "termination", "pay", "hours"},
    "se": {"parties", "place", "job", "start", "term", "leave", "termination", "pay", "hours", "social"},
    "uk": {"parties", "start", "job", "place", "pay", "hours", "leave", "termination", "disciplinary"},
    "no": {"parties", "place", "job", "start", "term", "leave", "termination", "pay", "hours", "breaks"},
    "dk": {"parties", "place", "job", "start", "term", "leave", "termination", "pay", "hours"},
    "fi": {"parties", "start", "term", "place", "job", "pay", "hours", "leave", "termination", "insurer"},
    "us": {"parties", "job", "start", "term", "classification", "pay"},
    "ca": {"parties", "job", "place", "start", "term", "qualifications", "hours", "pay", "deductions", "expenses"},
    "on": {"parties", "contact", "place", "pay", "hours"},
    "au": {"parties", "job", "start", "term", "pay", "hours", "statements"},
    "be": {"parties", "place", "job", "start", "pay", "hours", "leave", "termination", "social"},
    # BW 7:655 (1) j, m, n and o ask whether: the answer is no, never "not applicable"
    "nl": {"parties", "place", "job", "start", "term", "leave", "termination", "pay", "hours", "pension", "agency",
           "on_call"},
    "at": {"parties", "start", "termination", "place", "job", "pay", "leave", "hours", "insurer"},
    "ie": {"parties", "place", "job", "start", "pay", "hours", "leave", "sickness", "pension", "termination",
           "minimum_wage"},
    # art. 3.2 l) asks for the harassment protocol whatever the company's size; p) and q) always have an answer
    "es": {"parties", "start", "place", "job", "pay", "hours", "leave", "equality", "termination", "social", "changes"},
    "it": {"parties", "place", "job", "start", "term", "leave", "termination", "pay", "hours", "social"},
    # § 3 pkt 2 falls away only when the worker picks the institution; pkt 1 m) is answered by the work regulations
    "pl": {"parties", "term", "job", "place", "pay", "hours", "start", "leave", "termination", "rules"},
}
LAW_NAME = {"eu": "Directive (EU) 2019/1152 Art. 4(2)", "se": "LAS 6 c §", "uk": "ERA ss.1 and 3",
            "no": "arbeidsmiljøloven § 14-6", "dk": "lov 501 af 16. maj 2023 § 3", "fi": "työsopimuslaki 2:4 §",
            "us": "the offer letter's terms", "ca": "CLSR s. 3.1", "on": "O. Reg. 285/01 s. 1.2",
            "au": "the Fair Work Act 2009 items", "be": "the law of 7 October 2022 arts. 4 and 5",
            "nl": "BW 7:655 lid 1", "at": "AVRAG § 2 (2)", "ie": "the Terms of Employment (Information) Act 1994 s. 3",
            "es": "Real Decreto 723/2026 art. 3.2", "it": "decreto legislativo 152/1997 art. 1",
            "pl": "Kodeks pracy art. 29 § 1 and § 3"}
# Items a statement may give by pointing to a law, a regulation or a collective agreement; the rest it states.
REFERABLE = {
    "eu": {"probation", "training", "leave", "termination", "pay", "hours", "social"},          # Art. 4(3): (g)-(l), (o)
    "no": {"leave", "termination", "pay", "hours", "breaks", "overtime", "training", "social"},  # § 14-6 (2): g-k, m, p, q
    "dk": {"probation", "leave", "termination", "pay", "hours", "training", "social"},  # § 3 stk. 4: all but 1-6, 12, 14
    "fi": {"probation", "pay", "hours", "training", "leave", "termination", "collective", "insurer"},  # 4, 7, 8, 11-15
    "uk": {"sickness", "other_leave", "pension", "training", "termination"},          # ERA s.2(2), (3)
    "be": {"pay", "hours", "training", "leave", "termination", "collective"},          # art. 4 § 2 6°, 8°; art. 5
    "nl": {"leave", "termination", "pay", "hours", "probation", "training", "social"},  # BW 7:655 (2): f-i, k, q-s
    # AVRAG § 2 (5): Z 5, 6, 9 (never the basic pay, which EMPLOY-PAY reads as an amount), 10, 11, 14, 15
    "at": {"termination", "place", "pay", "leave", "hours", "probation", "training"},
    "ie": {"pay", "hours", "probation", "leave", "sickness", "pension", "termination", "training", "social"},  # s. 3(3)
    "es": {"pay", "hours", "leave", "probation", "training", "termination", "social"},   # art. 3.3: f) 1.º, g) 1.º-4.º, h), i), n), p)
    "it": {"probation", "training", "leave", "termination", "pay", "hours", "social"},   # c. 5-bis: h), i), l), m), n), o), r)
    # art. 29 § 3(1): § 3 pkt 1 a)-f), h)-k) and pkt 2, by naming provisions of law; the § 1 terms are never pointers
    "pl": {"hours", "leave", "termination", "training", "social"},
}
POINTER = re.compile(r"^(see|refer to|as set out in|according to|in accordance with|se\b|jf\.?|i henhold til|"
                     r"ifølge|følger av|følger|katso|ks\.|voir|selon|conformément à|zie\b|volgens|conform\b|"
                     r"overeenkomstig|siehe|gemäß|laut\b|"
                     r"véase|ver\b|según|conforme a|de acuerdo con|de conformidad con|con arreglo a|se aplican?\b|"
                     r"(?:lo|los|las|la|el) (?:establecid|dispuest|previst|fijad)\w* (?:en|por)\b|"
                     r"vedi\b|si veda|secondo\b|ai sensi d|come previsto d|come da\b|si rinvia a|in base a|si applican?o?\b|"
                     r"zob\.|zgodnie z|na podstawie|według|stosuje się)", re.I)
# What a pointer must name to count in Spain, Italy and Poland: a law, a decree, an article or an agreement.
SOURCE = re.compile(r"convenio|estatuto de los trabajadores|real decreto|\bley\b|artículo|\bart\.|contratto collettivo|"
                    r"\bccnl\b|legge|decreto|codice civile|kodeks|ustaw|rozporządzeni|regulamin|układ", re.I)
W9 = ("es", "it", "pl")


def points(text):
    """A section that gives its item by naming the law or the agreement that sets it."""
    t = norm(text)
    return bool(POINTER.match(t) and SOURCE.search(t))
NA_STRICT = ("not applicable", "n/a", "ej tillämpligt", "inte tillämpligt", "ej aktuellt", "ikke aktuelt",
             "ikke relevant", "ikke relevant", "ei sovelleta", "sans objet", "niet van toepassing", "entfällt",
             "nicht anwendbar", "no procede", "no aplicable", "no aplica", "non applicabile", "non previsto",
             "nie dotyczy")
FIXED = ("fixed term", "fixed-term", "temporary", "tidsbegränsad", "visstid", "vikariat", "säsongsarbete", "seasonal",
         "midlertidig", "tidsbegrænset", "määräaikainen", "durée déterminée", "bepaalde tijd", "bepaalde duur",
         "befristet", "duración determinada", "temporal", "tempo determinato", "a termine", "czas określony",
         "okres próbny")
PERMANENT = ("permanent", "until further notice", "open-ended", "indefinite", "tillsvidare", "tills vidare",
             "fast ansettelse", "tidsubestemt", "toistaiseksi", "durée indéterminée", "ongoing", "at will",
             "onbepaalde tijd", "onbepaalde duur", "unbefristet", "tiempo indefinido", "indefinido",
             "tempo indeterminato", "czas nieokreślony")
SE_KINDS = ("särskild visstidsanställning", "vikariat", "säsongsarbete", "special fixed-term", "substitute", "seasonal")
EXPECTED = ("expected", "beräknas", "förutsättning", "until the return", "until the end of", "tills", "upphör när",
            "forventet", "arvioitu", "durée prévue", "verwachte duur", "voraussichtliche dauer",
            "duración previsible", "duración prevista", "durata prevista", "przewidywany")
GIVEN = ("date of this statement", "this statement is dated", "statement given on", "statement date",
         "date of this letter", "datum för anställningsbeviset", "anställningsbeviset utfärdat", "utfärdat den",
         "lämnat den", "avtalen er datert", "ansættelsesbeviset er udstedt", "selvitys on annettu",
         "date de la présente déclaration", "date du présent document", "datum van deze opgave",
         "datum van dit document", "ausgestellt am", "fecha del presente documento", "fecha de este documento",
         "data del presente documento", "informację sporządzono")
FREQUENCY = ("monthly", "weekly", "fortnightly", "four-weekly", "biweekly", "every", "each month", "each week",
             "per month", "a month", "per week", "a week", "per hour", "an hour", "per year", "a year", "annually",
             "månadsvis", "veckovis", "varje månad", "varje vecka", "varannan vecka", "per månad", "i månaden",
             "per vecka", "per timme", "per år", "hver måned", "per måned", "per uke", "per time", "månedsvis",
             "pr. måned", "pr. time", "pr. uge", "bagud", "kuukausi", "kuukaudessa", "tunnilta", "viikoittain",
             "kahden viikon", "un jeudi sur deux", "toutes les deux semaines", "par mois", "par semaine",
             "l'heure", "aux deux semaines", "chaque", "maandelijks", "per maand", "per week", "per uur",
             "wekelijks", "monatlich", "pro monat", "pro stunde", "pro woche", "mensuellement", "periodicité",
             "mensual", "al mes", "cada mes", "por hora", "semanal", "quincenal", "al año", "mensile", "mensilmente",
             "al mese", "all'ora", "settimanale", "all'anno", "ogni mese", "miesięcznie", "raz w miesiącu",
             "za godzinę", "tygodniowo", "rocznie")
METHOD = ("bank transfer", "credit transfer", "transfer", "paid into", "bank account", "account", "bacs", "cash",
          "cheque", "check", "direct deposit", "electronic funds transfer", "insättning", "bankkonto", "lönekonto",
          "konto", "överföring", "kontant", "overføring", "overførsel", "nemkonto", "tilisiirto", "pankkitili",
          "dépôt direct", "virement", "compte", "overmaking", "overschrijving", "bankrekening", "überweisung",
          "gehaltskonto", "transferencia", "cuenta bancaria", "cuenta", "efectivo", "bonifico", "conto corrente",
          "conto", "contanti", "assegno", "przelew", "rachunek", "konto", "gotówk")
CURRENCY = re.compile(r"[£€$]|\b(sek|eur|gbp|usd|nok|dkk|cad|aud|chf|pln|kr|kronor|kroner|euros?|pounds?|dollars?|zł|"
                      r"złotych|złote)\b", re.I)
VARIABLE = re.compile(r"\b(schedule|hours|work pattern|arbetstiden?)\s+(is|are|är|will be)\s+(variable|varierande|"
                      r"unpredictable)|\bvariable (schedule|hours|work pattern)|varierande arbetstid|\bunpredictable|"
                      r"oförutsägbar|zero[- ]hours|arbeidstiden varierer|tidsplanen for arbejdet er variabel|"
                      r"vaihtelevaa työaikaa|arbeid wordt verricht zijn variabel|uurrooster is variabel|"
                      r"l'horaire de travail est variable|lage der arbeitszeit ist variabel|"
                      r"distribuye de forma irregular|distribución irregular de la jornada|"
                      r"non prevede un orario normale di lavoro programmato|rozkład czasu pracy jest zmienny")
PAY_CURRENCY = re.compile(r"\b(currency|valuta|valuutta|devise|moneda|waluta|walucie|waluty)\b[^.;]*?(%s)|\b(paid|pay|salary|wages|betalas|utbetalas|lön|lönen)\b"
                          r"[^.;]{0,40}?\b(in|i)\s+(?:\w+\s+)?(%s)" % ((CURRENCY.pattern,) * 2), re.I)
COUNTRIES = ("germany", "tyskland", "poland", "polen", "norway", "norge", "denmark", "danmark", "finland", "france",
             "frankrike", "netherlands", "nederländerna", "belgium", "belgien", "spain", "spanien", "italy",
             "italien", "austria", "österrike", "estonia", "estland", "latvia", "lettland", "lithuania", "litauen",
             "ireland", "irland", "united kingdom", "storbritannien", "sweden", "sverige", "czechia", "tjeckien",
             "portugal", "switzerland", "schweiz", "iceland", "island", "united states", "usa", "canada", "kanada",
             "china", "kina", "india", "indien", "japan", "brazil", "brasilien", "south africa", "sydafrika",
             "saksa", "ruotsi", "norja", "tanska", "viro", "sverige", "tyskland", "duitsland", "frankrijk",
             "belgië", "nederland", "oostenrijk", "ierland", "spanje", "deutschland", "frankreich", "belgien",
             "niederlande", "österreich", "irland", "ungarn", "tschechien", "slowakei", "allemagne", "pays-bas",
             "belgique", "autriche", "irlande", "espagne", "italie", "pologne", "alemania", "francia", "italia",
             "polonia", "países bajos", "bélgica", "reino unido", "estados unidos", "germania", "spagna", "paesi bassi",
             "belgio", "regno unito", "svizzera", "stati uniti", "niemcy", "niemczech", "francja", "francji", "hiszpania",
             "hiszpanii", "włochy", "włoszech", "czechy", "czechach", "holandia", "holandii")
MONTHS = {"january": 1, "februari": 2, "february": 2, "march": 3, "mars": 3, "april": 4, "may": 5, "maj": 5,
          "june": 6, "juni": 6, "july": 7, "juli": 7, "august": 8, "augusti": 8, "september": 9, "october": 10,
          "oktober": 10, "november": 11, "december": 12, "januari": 1, "januar": 1, "februar": 2, "marts": 3,
          "mai": 5, "desember": 12, "janvier": 1, "février": 2, "avril": 4, "juin": 6, "juillet": 7, "août": 8,
          "septembre": 9, "octobre": 10, "novembre": 11, "décembre": 12, "maart": 3, "mei": 5, "augustus": 8,
          "jänner": 1, "märz": 3, "dezember": 12}
NUMBERS = {"one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7, "eight": 8, "nine": 9,
           "ten": 10, "eleven": 11, "twelve": 12, "en": 1, "ett": 1, "två": 2, "tre": 3, "fyra": 4, "fem": 5,
           "sex": 6, "sju": 7, "åtta": 8, "nio": 9, "tio": 10, "elva": 11, "tolv": 12, "seks": 6, "fire": 4,
           "to": 2, "kuusi": 6, "neljä": 4, "kolme": 3, "kaksi": 2, "yksi": 1, "deux": 2, "trois": 3, "quatre": 4,
           "twee": 2, "drie": 3, "zes": 6, "één": 1, "ein": 1, "einen": 1, "einem": 1, "zwei": 2, "drei": 3,
           "sechs": 6}
MONTHS.update({"enero": 1, "febrero": 2, "marzo": 3, "abril": 4, "mayo": 5, "junio": 6, "julio": 7, "agosto": 8,
               "septiembre": 9, "setiembre": 9, "octubre": 10, "noviembre": 11, "diciembre": 12,
               "gennaio": 1, "febbraio": 2, "aprile": 4, "maggio": 5, "giugno": 6, "luglio": 7, "settembre": 9,
               "ottobre": 10, "dicembre": 12,
               "stycznia": 1, "lutego": 2, "marca": 3, "kwietnia": 4, "maja": 5, "czerwca": 6, "lipca": 7,
               "sierpnia": 8, "września": 9, "października": 10, "listopada": 11, "grudnia": 12})
NUMBERS.update({"un": 1, "uno": 1, "una": 1, "dos": 2, "tres": 3, "cuatro": 4, "cinco": 5, "seis": 6,
                "due": 2, "quattro": 4, "cinque": 5, "sei": 6,
                "jeden": 1, "dwa": 2, "trzy": 3, "cztery": 4, "pięć": 5, "sześć": 6})
MONTH_RX = "|".join(sorted(MONTHS, key=len, reverse=True))
DATES = [
    (re.compile(r"\b(\d{4})-(\d{1,2})-(\d{1,2})\b"), "ymd"),
    (re.compile(r"\b(\d{1,2})/(\d{1,2})/(\d{4})\b"), "dmy"),
    (re.compile(r"(?<![\d.])(\d{1,2})\.(\d{1,2})\.(\d{4})\b"), "dmy"),
    (re.compile(r"(?<![\d-])(\d{1,2})-(\d{1,2})-(\d{4})\b"), "dmy"),           # Dutch 01-12-2026
    # 9 October 2026, 9. oktober 2026, 9 de octubre de 2026, 9 października 2026
    (re.compile(r"\b(\d{1,2})(?:st|nd|rd|th|:e|:a|er|\.)?\s+(?:de\s+)?(%s)\s+(?:de\s+)?(\d{4})\b" % MONTH_RX, re.I), "dMy"),
    (re.compile(r"\b(%s)\s+(\d{1,2})(?:st|nd|rd|th)?,?\s+(\d{4})\b" % MONTH_RX, re.I), "Mdy"),
]
LENGTH = re.compile(r"\b(\d+|%s)[\s-]*(months?|månader|månad|måneder|måned|kuukautta|kuukausi|kuukauden|mois|"
                    r"maanden|maand|monaten|monate|monat|meses|mesi|mese|mes|miesięcy|miesiące|miesiąca|miesiąc|"
                    r"weeks?|veckor|vecka|uker|uke|uger|uge|viikkoa|viikko|semaines?|weken|wochen|woche|"
                    r"semanas?|settimane|settimana|tygodnie|tygodni|tygodnia|tydzień|"
                    r"days?|dagar|dager|dage|dagen|dag|päivää|päivä|jours?|tagen|tage|tag|días?|giorni|giorno|dni|"
                    r"dzień)\b" % "|".join(NUMBERS), re.I)
LANG_OF_LOCALE = {"sv": "sv", "nb": "nb", "no": "nb", "nn": "nb", "da": "da", "fi": "fi", "fr": "fr", "en": "en",
                  "nl": "nl", "de": "de", "es": "es", "it": "it", "pl": "pl"}


def norm(s):
    return re.sub(r"\s+", " ", str(s).replace(" ", " ").replace(" ", " ")).strip().lower()


def paragraphs(path):
    """(style, text) for every paragraph with text, table cells included, in reading order."""
    with zipfile.ZipFile(path) as z:
        xml = z.read("word/document.xml").decode("utf-8", "replace")
    out = []
    for p in re.findall(r"<w:p[ >].*?</w:p>", xml, re.S):
        style = re.search(r'<w:pStyle w:val="([^"]+)"', p)
        text = re.sub(r"<w:(br|tab|cr)\b[^>]*/>", " ", p)
        text = re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", "", text))).strip()
        if text:
            out.append((style.group(1) if style else "", text))
    return out


def doc_language(path):
    try:
        with zipfile.ZipFile(path) as z:
            core = z.read("docProps/core.xml").decode("utf-8", "replace")
    except (KeyError, zipfile.BadZipFile):
        return None
    m = re.search(r"<dc:language>([^<]+)</dc:language>", core)
    return m.group(1) if m else None


def strip_number(s):
    return re.sub(r"^(?:§\s*)?(?:\(?(?:\d{1,2}|[a-o])[.)]|\d{1,2})\s+", "", s)


def label_of(text, lang=None):
    s = strip_number(norm(text))
    best = None
    for item, labels, _ in ITEMS:
        pool = labels.get(lang, ()) if lang else LABELS[item]
        for lab in pool:
            if re.match(r"%s(?:s|es)?\b" % re.escape(lab), s) and (best is None or len(lab) > best[1]):
                best = (item, len(lab))
    return best[0] if best else None


def sections(paras):
    """item -> the text under its heading. A heading is a heading-styled paragraph, or a short one that is
    not a sentence and has no value after a colon (a table's label cell), starting with one of the item's
    words."""
    secs, cur = {}, None
    for style, text in paras:
        styled = bool(re.match(r"(heading|rubrik|title|otsikko|overskrift)", style, re.I))
        s = strip_number(norm(text))
        bare = len(s) <= 60 and not re.search(r":\s*\S", s) and not s.endswith((".", ";"))
        item = label_of(text) if (styled or bare) else None
        if item and item != cur:
            cur = item
            secs.setdefault(item, [])
            continue
        if item and styled:
            continue
        if styled and not item:
            cur = None
            continue
        if cur:
            secs[cur].append(text)
    for item, _, _ in ITEMS:      # "Pay: GBP 13.00 an hour" in a statement with no headings
        if item in secs or item == "_sign":
            continue
        rx = re.compile(r"^(%s)(?:s|es)?\s*[:–—-]\s*(\S.*)$" % "|".join(map(re.escape, LABELS[item])))
        for _, text in paras:
            m = rx.match(strip_number(norm(text)))
            if m:
                secs[item] = [text.split(":", 1)[-1].strip() if ":" in text else m.group(2)]
                break
    return {k: " ".join(v).strip() for k, v in secs.items() if k != "_sign"}


def dates_in(text):
    found = []
    for rx, kind in DATES:
        for m in rx.finditer(text):
            a, b, c = m.groups()
            try:
                if kind == "ymd":
                    d = dt.date(int(a), int(b), int(c))
                elif kind == "dmy":
                    d = dt.date(int(c), int(b), int(a))
                elif kind == "dMy":
                    d = dt.date(int(c), MONTHS[b.lower()], int(a))
                else:
                    d = dt.date(int(c), MONTHS[a.lower()], int(b))
            except (ValueError, KeyError):
                continue
            found.append((m.start(), d))
    return [d for _, d in sorted(found)]


def iso(value):
    try:
        return dt.date.fromisoformat(str(value).strip())
    except ValueError:
        return None


def add_months(d, n):
    y, m = divmod(d.month - 1 + n, 12)
    y, m = d.year + y, m + 1
    for day in (d.day, 30, 29, 28):
        try:
            return dt.date(y, m, day)
        except ValueError:
            continue


def length_in(text):
    """(number, unit) of the first length the text gives: unit is month, week or day."""
    m = LENGTH.search(norm(text))
    if not m:
        return None
    n = m.group(1)
    n = int(n) if n.isdigit() else NUMBERS[n.lower()]
    u = m.group(2).lower()
    unit = "month" if u.startswith(("month", "månad", "måned", "kuukau", "mois", "maand", "monat", "mes", "miesi")) else \
        "week" if u.startswith(("week", "veck", "uke", "uge", "uger", "viikko", "semaine", "wek", "woch", "seman",
                                "settiman", "tygod", "tydzie")) else "day"
    return n, unit


def as_days(length, start=None):
    n, unit = length
    if unit == "day":
        return n
    if unit == "week":
        return n * 7
    if start:
        return (add_months(start, n) - start).days
    return round(n * 30.44)


def amounts_in(text):
    """Every amount the text gives, read both ways where a point could group thousands (38.500 in Danish)."""
    out = set()
    for grouped in (False, True):
        t = re.sub(r"(?<=\d)[\s  ,'’](?=\d{3}\b)", "", text)
        if grouped:
            t = re.sub(r"(?<=\d)\.(?=\d{3}\b)", "", t)
        t = re.sub(r"(?<=\d),(?=\d{1,2}\b)", ".", t)
        for n in re.findall(r"\d+(?:\.\d+)?", t):
            try:
                out.add(Decimal(n))
            except InvalidOperation:
                pass
    return out


def na(text):
    return norm(text).startswith(NA_STRICT)


def spec_beside(path):
    for p in sorted(Path(path).parent.glob("*.json")):
        try:
            data = json.loads(p.read_text())
        except (ValueError, OSError):
            continue
        if isinstance(data, dict) and isinstance(data.get("employer"), dict) and isinstance(data.get("worker"), dict):
            return data
    return None


def law_of(spec, flat):
    if spec:
        law = str(spec.get("law") or "").lower()
        if law in WANT:
            return law
        lang = str(spec.get("language", "")).lower()
        return {"sv": "se", "nb": "no", "no": "no", "da": "dk", "fi": "fi", "fr": "ca", "nl": "nl", "es": "es",
                "it": "it", "pl": "pl"}.get(lang[:2], "eu")
    for words, law in (("employment rights act", "uk"), ("1982:80", "se"), ("anställningsskydd", "se"),
                       ("employment protection act", "se"), ("arbeidsmiljøloven", "no"),
                       ("ansættelsesbeviser", "dk"), ("työsopimuslain", "fi"), ("työsopimuslaki", "fi"),
                       ("canada labour code", "ca"), ("code canadien du travail", "ca"),
                       ("ontario regulation 285/01", "on"), ("règlement de l'ontario 285/01", "on"),
                       ("fair work act 2009", "au"), ("fair labor standards act", "us"), ("at will", "us"),
                       ("terms of employment (information) act", "ie"), ("7:655", "nl"), ("avrag", "at"),
                       ("dienstzettel", "at"), ("loi du 7 octobre 2022", "be"), ("wet van 7 oktober 2022", "be"),
                       ("real decreto 723/2026", "es"), ("estatuto de los trabajadores", "es"),
                       ("decreto legislativo 26 maggio 1997", "it"), ("d.lgs. 152/1997", "it"),
                       ("kodeksu pracy", "pl"), ("kodeks pracy", "pl")):
        if words in flat:
            return law
    return "eu"


def ref(item, law):
    r = REFS.get(item, {})
    if law == "se" and item in REFS and "eu" in r:
        return "%s; Art. %s" % (r.get("se", ""), r["eu"].replace("Art. ", "")) if r.get("se") else r["eu"]
    return r.get(law) or r.get("eu") or ""


def given_date(spec, paras):
    if spec and spec.get("given"):
        return iso(spec["given"])
    for _, text in paras:
        if any(g in norm(text) for g in GIVEN):
            found = dates_in(text)
            if found:
                return found[0]
    return None


def term_dates(spec, secs):
    """(start, end, fixed) from the spec, else from the statement's start and term sections."""
    if spec:
        term = spec.get("term") or {}
        fixed = str(term.get("type", "")).lower() in ("fixed", "fixed-term", "fixed term", "temporary")
        return iso(spec.get("start")), iso(term.get("end")) if fixed else None, fixed
    starts = dates_in(secs.get("start", ""))
    start = starts[0] if starts else None
    t = norm(secs.get("term", ""))
    fixed = any(w in t for w in FIXED) and not any(w in t for w in PERMANENT)
    ends = [d for d in dates_in(secs.get("term", "")) if d != start]
    return start, (ends[-1] if fixed and ends else None), fixed


def us_state(spec, flat):
    if spec and spec.get("work_state"):
        return str(spec["work_state"]).upper()
    if "new york labor law" in flat:
        return "NY"
    if "california labor code" in flat:
        return "CA"
    return ""


def exempt_of(spec, flat):
    if spec and isinstance(spec.get("flsa"), dict):
        return str(spec["flsa"].get("status", "")).lower() == "exempt"
    return "is exempt" in flat or "exempt from overtime" in flat


# Deadlines: the number of calendar days after the start the statement may be dated (None: by the start).
DEADLINE = {"eu": (7, "Art. 5(1)"), "se": (7, "LAS 6 c § third paragraph"),
            "no": (7, "arbeidsmiljøloven § 14-5 (2)"), "dk": (7, "lov 501 § 3, stk. 1"),
            "fi": (7, "työsopimuslaki 2:4 § 4 mom."), "ca": (30, "Canada Labour Code s. 253.2(1)"),
            "uk": (0, "ERA s.1(2)(b)"), "on": (0, "O. Reg. 285/01 s. 1.2 (1)"),
            "be": (0, "the Belgian law of 7 October 2022 art. 4 § 1"),
            "nl": (7, "BW 7:655 (3), for items a to e, h, i and q"),
            "at": (7, "AVRAG § 2 (1) (without delay; at the latest the seven days of Art. 5(1) of Directive (EU) "
                      "2019/1152, which it transposes)"),
            "ie": (5, "the Terms of Employment (Information) Act 1994 s. 3(1A), for the core terms"),
            # Spain: before the employment begins (it was two months under Real Decreto 1659/1998)
            "es": (0, "Real Decreto 723/2026 art. 7.1"),
            "it": (7, "D.Lgs. 152/1997 art. 1 c. 3 (what the contract or the hiring notice did not give; letters g), "
                      "i), l), m), q), q-bis) and r) may follow within one month)"),
            "pl": (7, "Kodeks pracy art. 29 § 3 pkt 1 (from the day the worker is admitted to work; the social "
                      "insurance institution of pkt 2 within 30 days)")}
def au_renewal(term, raw, start):
    """Fair Work Act 2009 s 333E(1)(b) and (c): an option to renew or extend a fixed term may be used once, and
    the term with it may not pass two years, unless an exception in s 333F applies. The statement says how many
    times and the latest end ("may be renewed or extended once, to end no later than ...")."""
    bad = []
    if re.search(r"\btwice\b|more than once|\b(two|three|four|\d+) (renewals|extensions|times)\b|rolling", term):
        bad.append("a fixed term that may be renewed or extended more than once: Fair Work Act 2009 s 333E(1)(c) "
                   "allows one renewal or extension unless an exception in s 333F applies; ask the employer which")
    elif not re.search(r"\bonce\b|\bone (renewal|extension)\b", term):
        bad.append("a fixed term that may be renewed or extended says neither how many times nor that it is once: "
                   "Fair Work Act 2009 s 333E(1)(c) allows one; write it")
    latest = max(dates_in(raw)) if "no later than" in term and dates_in(raw) else None
    if latest is None:
        bad.append("a fixed term that may be renewed or extended gives no latest end (\"to end no later than\"): "
                   "Fair Work Act 2009 s 333E(1)(b) keeps it within two years; write the date")
    elif start and latest > add_months(start, 24):
        bad.append("a fixed term that may be renewed or extended to %s runs more than two years from %s: Fair Work "
                   "Act 2009 s 333E(1)(b), unless an exception in s 333F applies; ask the employer which"
                   % (latest, start))
    return bad


def national_probation(law, length, days, start, end, fixed, text=""):
    """The wave 8 and wave 9 countries' own limits, which differ from the Directive's six months; None when
    within them. text: the probation section, where a Spanish statement names the agreement that sets a longer one."""
    what = "%s %s%s" % (length[0], length[1], "" if length[0] == 1 else "s")
    months = length[0] if length[1] == "month" else days / 30.44
    if law == "es":
        # ET art. 14.1: the collective agreement sets the limits; without one, six months for técnicos titulados
        # and two for the others (three in a company under 25 workers), and one month in a temporary contract of
        # six months or less.
        agreed = bool(re.search(r"convenio colectivo", text))
        if fixed and start and end and end < add_months(start, 6) and months > 1.01 and not agreed:
            return ("a probation of %s in a temporary contract of six months or less: Estatuto de los Trabajadores "
                    "art. 14.1 allows one month unless the collective agreement says otherwise; name the agreement "
                    "that does, or shorten it" % what)
        # Without a collective agreement: six months for a técnico titulado, two for the others, three for the
        # others in a company of under twenty-five workers. The statement says which applies, or it is held to two.
        titulado = bool(re.search(r"t[eé]cnicos? titulad", text))
        small = bool(re.search(r"menos de (veinticinco|25) (personas )?trabajador", text))
        limit, who = (6, "a técnico titulado") if titulado else (3, "a worker who is not a técnico titulado in a "
                                                                      "company of under twenty-five workers") \
            if small else (2, "a worker who is not a técnico titulado")
        if months > limit + 0.01 and not agreed:
            return ("a probation of %s is longer than the %s months Estatuto de los Trabajadores art. 14.1 allows %s "
                    "where no collective agreement sets the limit; say in the probation that the worker is a técnico "
                    "titulado (six months) or that the company has under twenty-five workers (three), or name the "
                    "convenio colectivo that sets a longer one (Real Decreto 723/2026 art. 3.2 h) 1.º)"
                    % (what, limit, who))
        return None
    if law == "it":
        if months > 6.01:
            return ("a probation of %s is longer than the six months D.Lgs. 104/2022 art. 7 c. 1 allows; a collective "
                    "agreement can only shorten it" % what)
        if fixed and start and end:
            # art. 7 c. 2: days of actual work, counted here at five a week and twenty a month
            work = length[0] * {"day": 1, "week": 5, "month": 20}[length[1]]
            if end < add_months(start, 6) and work > 15:
                return ("a probation of %s in a fixed term of six months or less: D.Lgs. 104/2022 art. 7 c. 2 allows "
                        "one day of actual work per fifteen calendar days, two days at least and fifteen at most "
                        "(a more favourable collective agreement prevails)" % what)
            if add_months(start, 6) <= end < add_months(start, 12) - dt.timedelta(days=1) and work > 30:
                return ("a probation of %s in a fixed term of more than six and less than twelve months: D.Lgs. "
                        "104/2022 art. 7 c. 2 allows thirty days of actual work at most" % what)
        return None
    if law == "pl":
        if months > 3.01:
            return ("a trial period of %s is longer than the 3 months Kodeks pracy art. 25 § 2 allows (one month "
                    "before a fixed-term contract shorter than 6 months and two before one of 6 to under 12 months, "
                    "§ 2(2), each once longer by a month where the kind of work calls for it, § 2(3))" % what)
        return None
    if law == "be":
        return ("a trial period of %s: Belgium has had no trial period for an ordinary employment contract since "
                "1 January 2014 (loi du 3 juillet 1978 art. 67, repealed by the law of 26 December 2013); a student "
                "contract's first three days (art. 127) and temporary agency work are the exceptions, so check the "
                "contract with the employer" % what)
    if law == "at" and (days > 31 or (length[1] == "month" and length[0] > 1)):
        return ("a probation of %s: Austria allows at most one month (ABGB § 1158 (2); AngG § 19 (2)); check it with "
                "the employer" % what)
    if law == "nl":
        months = (length[0] if length[1] == "month" else days / 30.44)
        if fixed and start and end:
            term = (end - start).days + 1
            if end < add_months(start, 6) or term <= (add_months(start, 6) - start).days:
                return ("a fixed term of %d days with a probation: BW 7:652 (6)(a) allows none in a contract of six "
                        "months or less" % term) if days else None
            limit = 1 if end < add_months(start, 24) - dt.timedelta(days=1) else 2
            where = "BW 7:652 (4)(a), a fixed term under two years" if limit == 1 else "BW 7:652 (4)(b)"
        elif fixed:
            limit, where = 1, "BW 7:652 (5), a fixed term with no calendar end date"
        else:
            limit, where = 2, "BW 7:652 (3), a contract for an indefinite time"
        if months > limit + 0.01:
            return "a probation of %s is longer than the %d month%s %s allows%s" % (
                what, limit, "" if limit == 1 else "s", where,
                "; only a collective agreement may set a longer one (BW 7:652 (7))" if limit == 1 else "")
    if law == "ie" and (days > 184 or (length[1] == "month" and length[0] > 6)):
        if length[1] == "month" and length[0] <= 12 or days <= 366:
            return ("a probation of %s is longer than six months: s. 6D(3) allows up to twelve only exceptionally "
                    "and in the employee's interest; check that with the employer" % what)
        return "a probation of %s is longer than the twelve months s. 6D allows at most" % what
    return None


PROBATION_LIMIT = {"eu": (6, None, "Art. 8(1) of Directive (EU) 2019/1152"), "se": (6, None, "LAS 6 §"),
                   "no": (6, 2, "arbeidsmiljøloven § 15-6 (3)"), "dk": (6, 4, "lov 501 § 6"),
                   "fi": (6, 2, "työsopimuslaki 1 luku 4 §")}
ABROAD_LIMIT = {"uk": "month", "fi": "month_inclusive", "at": "month", "ie": "month_inclusive"}


# Belgium: the items of art. 5, which the work rules carry for a worker under the act of 8 April 1965.
BE_ART5 = ("training", "leave", "termination", "collective", "social")
BE_WORK_RULES = re.compile(r"règlement de travail|arbeidsreglement")


def be_region(spec, text=""):
    """A Belgian workplace's language region from its bpost postcode: 1000-1299 Brussels-Capital, 1300-1499 and
    4000-7999 Wallonia (the German-speaking area within 4700-4799), 1500-3999 and 8000-9999 Flanders."""
    pool = []
    if spec:
        pool += [spec.get("place") if isinstance(spec.get("place"), str) else "",
                 (spec.get("employer") or {}).get("address", "")]
    pool.append(text)
    for t in pool:
        m = re.search(r"(?<!\d)([1-9]\d{3})(?!\d)\s+\w", str(t or ""))
        if m:
            n = int(m.group(1))
            if 1000 <= n <= 1299:
                return "brussels"
            if 4700 <= n <= 4799:
                return "german"
            return "nl" if 1500 <= n <= 3999 or 8000 <= n <= 9999 else "fr"
    return ""


def check(rule_id, path, case, stage):
    path = Path(path)
    if path.suffix.lower() != ".docx":
        return None, "an employment statement is checked as a Word file"
    paras = paragraphs(path)
    flat = norm(" ".join(t for _, t in paras))
    truth = case.get("truth") or {}
    spec = spec_beside(path) or (truth if isinstance(truth.get("employer"), dict) else None)
    law = law_of(spec, flat)
    secs = sections(paras)

    if rule_id == "EMPLOY-ITEMS":
        missing, never = [], []
        for item in WANT[law]:
            body = secs.get(item, "")
            if not body.strip():
                missing.append("%s [%s]" % (NAME[item], ref(item, law)))
            elif item in MUST[law] and na(body):
                never.append("%s is marked not applicable, but %s always applies" % (NAME[item], ref(item, law)))
        bad = []
        if missing:
            bad.append("missing, or not marked not applicable: %s" % "; ".join(missing))
            if law == "be" and any(not secs.get(item, "").strip() for item in BE_ART5):
                bad.append("art. 5 binds this document for a worker outside the work rules act of 8 April 1965; for "
                           "anyone else give the item or point to the work rules (arbeidsreglement, règlement de "
                           "travail)")
        bad += never
        h = norm(secs.get("hours", ""))
        if h and not na(h) and law in ("eu", "se", "uk", "dk", "fi", "no", "be", "nl", "at", "ie") + W9:
            pattern = str(((spec or {}).get("hours") or {}).get("pattern", "")).lower() \
                if spec and isinstance(spec.get("hours"), dict) else ""
            variable = pattern == "variable" or (not spec and bool(VARIABLE.search(h)))
            if variable and law == "uk":
                pass  # ERA s.1(4)(c)(iii) asks only whether and how the hours vary
            elif variable and law == "fi":
                if not any(w in h for w in ("työvoiman tarve", "tilanteissa")) or "30 a" not in h:
                    bad.append("a variable working time gives when and how much work is needed and the days and "
                               "hours work may be ordered without consent (TSL 2:4 § 3 mom. 9)")
            elif variable and law == "pl":
                pass  # Kodeks pracy art. 29 § 3 sets no particulars for a variable schedule
            elif variable:
                lack = [what for what, words_ in (
                    ("the guaranteed paid hours", ("guaranteed", "garanter", "gewaarborgd", "garantiert",
                                                   "nombre d'heures", "aantal uren", "garantit")),
                    ("the reference hours and days", ("reference", "referens", "tidsrom", "dagen en uren", "tijdvak",
                                                      "plage", "referenz", "referencia", "riferimento")),
                    ("the minimum notice before work", ("notice", "besked", "tidsfrist", "varsel", "termijn",
                                                        "meegedeeld", "mededeling", "communication",
                                                        "ankündigung", "preaviso", "preavviso")))
                    # Spain's g) 5.º asks for the reference hours and days and the notice, not for guaranteed hours
                    if not any(w in h for w in words_) and not (law == "es" and what.startswith("the guaranteed"))]
                if lack:
                    bad.append("a variable schedule gives %s (%s)" % (", ".join(lack), {
                        "dk": "lov 501 § 3, stk. 2, nr. 12", "no": "aml. § 14-6 (1) j", "be": "art. 4 § 2 9°",
                        "nl": "BW 7:655 (1) i 2°", "ie": "s. 3(1)(p)", "es": "Real Decreto 723/2026 art. 3.2 g) 5.º",
                        "it": "D.Lgs. 152/1997 art. 1 c. 1 p)"}.get(law, "Art. 4(2)(m)")))
            elif law in W9 and points(h):
                pass  # the working time given by naming the law or the agreement that sets it
            elif not re.search(r"\d+(?:[.,]\d+)?\s*(hours?|timmar|timer|tim\b|tuntia|h\b|heures|uur|stunden|std\b|"
                               r"horas?|ore\b|godzin)|full[- ]time|heltid|jornada completa|tiempo completo|tempo pieno|"
                               r"pełny etat|pełnym wymiarze", h):
                bad.append("the length of the normal working day or week is not given [%s]" % ref("hours", law))
            if law == "se" and not any(w in h for w in ("besked", "notice", "varsel", "tidsfrist")):
                bad.append("the minimum notice of the working schedule is not given (LAS 6 c § 7)")
            if law == "uk" and not variable and not (re.search(r"monday|tuesday|wednesday|thursday|friday|saturday|sunday", h)
                                                     or "days" in h):
                bad.append("the days of the week the worker works are not given (ERA s.1(4)(c)(ii))")
        if law == "be" and h and not na(h) and not VARIABLE.search(h) and not re.search(
                r"(horaire|uurrooster)[^.;]*(règlement de travail|arbeidsreglement)|"
                r"(règlement de travail|arbeidsreglement)[^.;]*(horaire|uurrooster)", h):
            # art. 4 § 2 8° a): the start and end of the regular day, the breaks and the regular days off
            lack = [what for what, rx in (
                ("when the regular day starts and ends", r"\d{1,2}\s*(?:h|u|uur|:|\.)\s*\d{2}"),
                ("the rest breaks", r"repos|pause|rusttijd|middagpauze"),
                ("the regular days off", r"jours d'arrêt|rustdag|samedi|dimanche|zaterdag|zondag"))
                if not re.search(rx, h)]
            if lack:
                bad.append("a fixed schedule gives %s, or points to the work rules (art. 4 § 2 8° a))" % ", ".join(lack))
        if law == "at":
            ins = norm(secs.get("insurer", ""))
            if ins and not na(ins):
                lack = [w for w, keys in (("the social insurance institution", ("sozialversicherung", "gesundheitskasse",
                                                                                "versicherungsanstalt")),
                                          ("the BV-Kasse", ("vorsorgekasse", "bv-kasse"))) if not any(k in ins for k in keys)]
                if lack:
                    bad.append("%s is not named (AVRAG § 2 (2) 13)" % " and ".join(lack))
            col = norm(secs.get("collective", ""))
            if col and not na(col) and not re.search(r"aufl(?:ie|ag)|einsicht|einsehbar|zugänglich|intranet", col):
                bad.append("the collective agreements are named but not where in the business they can be read "
                           "(AVRAG § 2 (2) 12)")
            if "sitz" not in norm(secs.get("place", "")):
                bad.append("the company's seat is not given with the place of work (AVRAG § 2 (2) 6)")
        if law == "be":
            # Art. 5 binds this document for a worker outside the work rules act of 8 April 1965; for the
            # others the work rules carry its items, so a section that points there is complete.
            col = norm(secs.get("collective", ""))
            if col and not na(col) and not BE_WORK_RULES.search(col) and not re.search(r"paritai|\b(pc|cp)\s*\d", col):
                bad.append("the collective agreements name neither the joint committee (commission paritaire / "
                           "paritair comité) they were made in nor the work rules that do (art. 5 4°)")
            soc = norm(secs.get("social", ""))
            if soc and not BE_WORK_RULES.search(soc) and not re.search(
                    r"onss|rsz|sécurité sociale|sociale zekerheid", soc):
                bad.append("the social security institution that collects the contributions is not named, nor the "
                           "work rules that name it (art. 5 5°)")
        if law == "es":
            j = norm(secs.get("job", ""))
            if j and not re.search(r"grupo profesional|categoría", j):
                bad.append("the job names no professional group or category (Real Decreto 723/2026 art. 3.2 e))")
            if h and not na(h) and not points(h) and not VARIABLE.search(h):
                lack = [what for what, rx in (("daily", r"diari|al día|por día"), ("weekly", r"semanal|a la semana|por semana"),
                                              ("annual", r"anual|al año|por año")) if not re.search(rx, h)]
                if lack:
                    bad.append("the working time gives no %s length; art. 3.2 g) 1.º asks for the daily, the weekly "
                               "and the annual working time, or a precise reference to the agreement that sets them "
                               "(art. 3.3)" % " or ".join(lack))
            eq = norm(secs.get("equality", ""))
            if eq and not na(eq) and "acoso" not in eq:
                bad.append("nothing on the protocol against sexual harassment and harassment on grounds of sex, which "
                           "art. 3.2 l) asks for whatever the company's size")
            soc = norm(secs.get("social", ""))
            if soc and not na(soc) and not points(soc) and not re.search(
                    r"mutua|entidad gestora|instituto nacional de la seguridad social|\binss\b|colaboradora", soc):
                bad.append("the Social Security section names neither the managing body nor the mutual that covers the "
                           "contingencies (art. 3.2 p))")
            if term_dates(spec, secs)[2] and not re.search(r"causa|circunstancias|sustituci", norm(secs.get("term", ""))):
                bad.append("a temporary contract names the cause that allows it, the circumstances that justify it and "
                           "their link to its length (art. 3.2 d))")
        if law == "it":
            soc = norm(secs.get("social", ""))
            if soc and not na(soc) and not points(soc) and not re.search(r"\binps\b|\binail\b|istituto nazionale|"
                                                                           r"\bent[ei]\b|\bcassa\b|\bfondo\b", soc):
                bad.append("the bodies that receive the social security and insurance contributions are not named "
                           "(D.Lgs. 152/1997 art. 1 c. 1 r))")
        if law == "pl":
            r_ = norm(secs.get("rules", ""))
            if r_ and not na(r_):
                without = re.search(r"nie ustalił regulaminu|nie ma regulaminu|brak regulaminu|nie obowiązuje regulamin", r_)
                if without:
                    lack = [what for what, rx in (("when, where and how often pay is paid", r"wypłac|wypłat|termin"),
                                                  ("the night time", r"por[aęy] nocn"),
                                                  ("how arrival and presence at work are confirmed", r"potwierdzani|obecnoś"),
                                                  ("how an absence is excused", r"usprawiedliwi")) if not re.search(rx, r_)]
                    if lack:
                        bad.append("the employer has no work regulations and the statement does not give %s "
                                   "(Kodeks pracy art. 29 § 3 pkt 1 m))" % "; ".join(lack))
                elif "regulamin" not in r_:
                    bad.append("the statement says neither that work regulations (regulamin pracy) apply nor what "
                               "art. 29 § 3 pkt 1 m) asks for without them")
            if h and not na(h) and not points(h):
                lack = [what for what, rx in (("the daily and weekly norm of working time", r"norm"),
                                              ("the breaks", r"przerw"), ("the daily and weekly rest", r"odpoczyn"))
                        if not re.search(rx, h)]
                if lack:
                    bad.append("the working time lacks %s, or the provisions that set them (Kodeks pracy art. 29 § 3 "
                               "pkt 1 a) to d), § 3(1))" % "; ".join(lack))
        if law == "ie":
            mw = norm(secs.get("minimum_wage", ""))
            if mw and not na(mw) and not ("section 23" in mw or "average hourly rate" in mw):
                bad.append("the statement does not say the employee may ask for their average hourly rate "
                           "(s. 3(1)(ga), National Minimum Wage Act 2000 s. 23)")
        s = norm(secs.get("social", ""))
        if law == "se" and s and not na(s) and not any(w in s for w in (
                "arbetsgivaravgift", "social security contributions", "employer contributions",
                "employer's contributions", "social contributions")):
            bad.append("the statement does not say that employer contributions are paid to the state (LAS 6 c § 12)")
        if law == "fi":
            ins = norm(secs.get("insurer", ""))
            if ins and not na(ins):
                lack = [w for w, keys in (("the pension insurer", ("eläke", "pension")),
                                          ("the accident insurer", ("tapaturma", "accident"))) if not any(k in ins for k in keys)]
                if lack:
                    bad.append("%s is not named (TSL 2:4 § 3 mom. 15)" % " and ".join(lack))
        if law == "ca":
            if not re.search(r"overtime|heures supplémentaires", norm(secs.get("hours", ""))):
                bad.append("the hours give no rules on overtime (CLSR 3.1(i))")
            if not re.search(r"overtime|heures supplémentaires", norm(secs.get("pay", ""))):
                bad.append("the pay gives no overtime rate (CLSR 3.1(j))")
        if law == "uk":
            dsc = norm(secs.get("disciplinary", ""))
            if dsc and not na(dsc) and not ("disciplin" in dsc and "grievance" in dsc):
                bad.append("the note names the disciplinary rules or procedure and to whom a grievance goes (ERA s.3(1))")
        if spec:
            p = norm(secs.get("parties", ""))
            for who in (spec["employer"].get("name"), spec["worker"].get("name")):
                if who and norm(who) not in p:
                    bad.append("%s is not named under the parties" % who)
            if law in ("se", "dk", "fi", "nl", "at"):
                for who in ("employer", "worker"):
                    addr = spec[who].get("address")
                    if addr and norm(addr) not in p:
                        bad.append("the %s's address is not given (%s)" % (who, ref("parties", law)))
            if law in W9:
                addr = spec["employer"].get("address")
                if addr and norm(addr) not in p and norm(addr) not in norm(secs.get("place", "")):
                    bad.append("the employer's registered address is not given (%s)" % {
                        "es": "Real Decreto 723/2026 art. 3.2 c): el domicilio social",
                        "it": "D.Lgs. 152/1997 art. 1 c. 1 c): la sede o il domicilio",
                        "pl": "Kodeks pracy art. 29 § 1: adres siedziby pracodawcy"}[law])
            title = (spec.get("job") or {}).get("title") if isinstance(spec.get("job"), dict) else spec.get("job")
            if title and "job" in WANT[law] and norm(title) not in norm(secs.get("job", "")):
                bad.append("the job title %r is not under the job" % title)
            users = (spec.get("agency") or {}).get("user_undertakings") if isinstance(spec.get("agency"), dict) else None
            for u in users or []:
                if norm(u) not in norm(secs.get("agency", "")):
                    bad.append("the user undertaking %s is not named [%s]" % (u, ref("agency", law)))
            if law == "on":
                op = spec["employer"].get("operating_name")
                if op and norm(op) not in p:
                    bad.append("the operating name %s is not given (O. Reg. 285/01 s. 1.2 (2) 1)" % op)
        if bad:
            return False, "; ".join(bad)
        return True, "all %d particulars %s lists are there or marked not applicable" % (len(WANT[law]), LAW_NAME[law])

    if rule_id == "EMPLOY-DATES":
        bad = []
        start, end, fixed = term_dates(spec, secs)
        shown = dates_in(secs.get("start", ""))
        if law == "on" and not shown:
            shown = dates_in(" ".join(t for _, t in paras))
        if not shown:
            bad.append("no start date under the start of the employment [%s]" % ref("start", law))
        elif spec and start and start not in shown:
            bad.append("the start date %s from the spec is not the one given" % start.isoformat())
        start = start or (shown[0] if shown else None)
        if law == "uk" and "continu" not in norm(secs.get("start", "")):
            bad.append("the date continuous employment began is not given (ERA s.1(3)(c))")
        term = norm(secs.get("term", ""))
        if fixed:
            if end is None and not any(w in term for w in EXPECTED):
                bad.append("a fixed-term contract gives no end date or expected duration [%s]" % ref("term", law))
            if end and start and end <= start:
                bad.append("the end date %s is not after the start date %s" % (end.isoformat(), start.isoformat()))
            if spec and end and end not in dates_in(secs.get("term", "")):
                bad.append("the end date %s from the spec is not the one given" % end.isoformat())
            if law == "se" and not any(k in term for k in SE_KINDS):
                bad.append("a fixed-term statement says whether it is särskild visstidsanställning, vikariat or "
                           "säsongsarbete (LAS 6 c § 3 b)")
            if law == "au" and start and end and end > add_months(start, 24):
                bad.append("a fixed term from %s to %s runs more than two years: Fair Work Act 2009 s 333E limits a "
                           "fixed term to two years unless an exception in s 333F applies; ask the employer which"
                           % (start, end))
            if law == "au" and re.search(r"renew|extend|extension|rolling", term):
                bad.extend(au_renewal(term, secs.get("term", ""), start))
        given = given_date(spec, paras)
        state = us_state(spec, flat) if law == "us" else ""
        if given and start:
            days, where = DEADLINE.get(law, (None, None))
            if law == "no" and fixed and end and (end - start).days < 31:
                days, where = 0, "arbeidsmiljøloven § 14-5 (3), a hire shorter than a month"
            if law == "us" and state in ("NY", "CA"):
                days, where = 0, {"NY": "New York Labor Law 195(1), at the time of hiring",
                                  "CA": "California Labor Code 2810.5, at the time of hiring"}[state]
            if days == 0 and given > start:
                bad.append("the statement is dated %s, after the employment began on %s; %s asks for it %s%s" % (
                    given, start, where, "before the employment begins" if law == "es" else "by the first day",
                    " (s.2(4) lets pensions, collective agreements, training and the s.3 note follow within two "
                    "months)" if law == "uk" else
                    " or, when that is not practicable, as soon after as reasonably possible; say why"
                    if law == "on" else ""))
            elif days and given > start + dt.timedelta(days=days):
                bad.append("the statement is dated %s, more than %d calendar days after the start on %s; %s asks "
                           "for it by then" % (given, days, start, where))
        if bad:
            return False, "; ".join(bad)
        return True, "start %s%s%s" % (start, ", fixed term to %s" % end if fixed and end else
                                       ", fixed term" if fixed else "", ", statement dated %s" % given if given else "")

    if rule_id == "EMPLOY-PROBATION":
        text = secs.get("probation")
        p = (spec or {}).get("probation") if spec else None
        if spec and not p:
            return None, "no probationary period"
        if not spec and (text is None or norm(text).startswith(NA_STRICT + ("none", "ingen", "no probation"))):
            return None, "no probationary period in the statement"
        if not text or na(text):
            return False, "the spec has a probationary period the statement does not give [%s]" % ref("probation", law)
        length = length_in(text)
        start, end, fixed = term_dates(spec, secs)
        if length is None:
            ds = dates_in(text)
            if len(ds) >= 2:
                length = ((ds[-1] - ds[0]).days + 1, "day")
        if spec and isinstance(p, dict):
            want = (p.get("months"), "month") if p.get("months") else (p.get("weeks"), "week") if p.get("weeks") else None
            if want and want[0] and length and (int(want[0]), want[1]) != length:
                return False, "the statement gives %s %ss of probation, the spec %s %ss" % (
                    length[0], length[1], want[0], want[1])
            length = length or want
        if not length:
            return False, "the probationary period gives no length [%s]" % ref("probation", law)
        days = as_days(length, start)
        verdict = national_probation(law, length, days, start, end, fixed, norm(text))
        if verdict:
            return False, verdict
        over = length[0] > 6 if length[1] == "month" else length[0] > 26 if length[1] == "week" else days > 184
        what = "%s %s%s" % (length[0], length[1], "" if length[0] == 1 else "s")
        limit = PROBATION_LIMIT.get(law)
        if over and limit:
            if law in ("eu", "se"):
                return False, ("a probation of %s is longer than six months: Art. 8(1) of Directive (EU) 2019/1152 sets "
                               "six months as the general limit%s, and Art. 8(3) lets a member state allow longer only in "
                               "exceptional cases; check that one applies or shorten it" % (
                                   what, " (LAS 6 §: at most six months)" if law == "se" else ""))
            return False, "a probation of %s is longer than the six months %s allows; check it with the employer" % (
                what, limit[2])
        if fixed and start and end:
            term_days = (end - start).days + 1
            share = limit[1] if limit else None
            if share and days > term_days / share:
                return False, ("the probation of %s is longer than %s of the fixed term of %d days, the most %s allows"
                               % (what, "half" if share == 2 else "a quarter", term_days, limit[2]))
            if days >= term_days:
                return False, ("the probation of %s covers the whole fixed term; Art. 8(2) asks it to be in proportion to "
                               "the length of the contract" % what)
        return True, "probation of %s, its length stated [%s]" % (what, ref("probation", law))

    if rule_id == "EMPLOY-PAY":
        text = secs.get("pay", "")
        if not text.strip():
            return False, "no pay section [%s]" % ref("pay", law)
        t = norm(text)
        bad = []
        if law in ("es", "it") and points(t):
            return True, "pay given by naming the law or the collective agreement that sets it [%s]" % {
                "es": "Real Decreto 723/2026 art. 3.3", "it": "D.Lgs. 152/1997 art. 1 c. 5-bis"}[law]
        if na(text):
            bad.append("pay is marked not applicable")
        if not (re.search(r"\d", text) and CURRENCY.search(text)):
            bad.append("no amount with its currency")
        # Poland: art. 29 § 1 pkt 3 asks for the pay and its components; when and how it is paid is for the work
        # regulations, or for § 3 pkt 1 m) without them.
        if law != "pl" and not any(w in t for w in FREQUENCY):
            bad.append("not how often it is paid")
        if law not in ("on", "pl") and not any(w in t for w in METHOD):
            bad.append("not how it is paid (bank transfer, cash)")
        if law == "au" and re.search(r"quarterly|every (two|three|six) months|annually|yearly in arrears", t):
            bad.append("pay is paid less often than monthly; Fair Work Act 2009 s 323(1)(c) asks for at least monthly")
        pay = (spec or {}).get("pay") if spec else None
        if isinstance(pay, dict):
            have = amounts_in(text)
            try:
                if pay.get("amount") is not None and Decimal(str(pay["amount"])) not in have:
                    bad.append("the amount %s from the spec is not given" % pay["amount"])
            except InvalidOperation:
                pass
            for c in pay.get("components") or []:
                if c.get("name") and norm(c["name"]) not in t:
                    bad.append("%s is not set out separately" % c["name"])
        if bad:
            return False, "pay: %s [%s]" % ("; ".join(bad), ref("pay", law))
        if law == "pl":
            return True, "pay states the amount and its components [%s]" % ref("pay", law)
        return True, "pay states the amount, how often%s [%s]" % (" and how it is paid" if law != "on" else "",
                                                                 ref("pay", law))

    if rule_id == "EMPLOY-ABROAD":
        if law in ("us", "ca", "on", "au"):
            return None, "the statement's law sets no work-abroad particulars"
        text = secs.get("abroad")
        a = (spec or {}).get("abroad") if spec else None
        if not a and (not text or norm(text).startswith(NA_STRICT + ("none", "ingen", "inget", "no work abroad"))):
            return None, "no work abroad in the statement"
        if a and not text:
            return False, "the spec sends the worker abroad but the statement has no work-abroad section [%s]" % ref(
                "abroad", law)
        t = norm(text)
        frm, to = (iso(a.get("from")), iso(a.get("to"))) if isinstance(a, dict) else (None, None)
        ds = dates_in(text)
        if not (frm and to) and len(ds) >= 2:
            frm, to = ds[0], ds[-1]
        if frm and to:
            days = (to - frm).days + 1
        else:
            length = length_in(text) or ((int(a["weeks"]), "week") if isinstance(a, dict) and a.get("weeks") else None)
            days = as_days(length) if length else None
        if days is None:
            return False, "the work abroad gives no period [%s]" % ref("abroad", law)
        month = (add_months(frm, 1) - frm).days if frm else 31
        if law in ("uk", "at") and days <= month:
            return None, "work abroad of %d days: one month or less, which %s leaves out" % (
                days, "AVRAG § 2 (3)" if law == "at" else "ERA s.1(4)(k)")
        if law in ("fi", "ie") and days < month:
            return None, "work abroad of %d days: less than a month, which %s leaves out" % (
                days, "s. 4(1)" if law == "ie" else "TSL 2:4 § 3 mom. 16")
        # Italy: a posting in a transnational provision of services is informed whatever its length (art. 2 c. 1);
        # the four weeks are for a mission (c. 2).
        posted = law == "it" and isinstance(a, dict) and bool(a.get("posted"))
        if law not in ("uk", "fi", "at", "ie") and days <= 28 and not posted:
            return None, ("work abroad of %d days: four consecutive weeks or less, which %s leaves out" % (
                days, {"no": "aml. § 14-7", "dk": "lov 501 § 4", "be": "art. 6", "nl": "BW 7:655 (1) k",
                       "es": "Real Decreto 723/2026 art. 4.3", "it": "D.Lgs. 152/1997 art. 2 c. 2",
                       "pl": "Kodeks pracy art. 29(1) § 2"}.get(
                    law, "Art. 7(4) (unless the member state provides otherwise)")))
        lack = []
        countries = (a.get("countries") or []) if isinstance(a, dict) else []
        if countries:
            lack += ["the country %s" % c for c in countries if norm(c) not in t]
        elif not (any(re.search(r"\b%s\b" % c, t) for c in COUNTRIES)
                  or re.search(r"\b(country|countries|land|länder|maa|pays|país|países|paese|paesi|państwo|państwa)\s*:\s*\S", t)):
            lack.append("the country")
        cur = (a.get("currency") if isinstance(a, dict) else None)
        if not PAY_CURRENCY.search(t):
            lack.append("the currency of pay")
        elif cur and not re.search(r"\b%s\b" % re.escape(norm(cur)), t):
            lack.append("the currency of pay %s from the spec" % cur)
        if not any(w in t for w in ("benefit", "allowance", "förmån", "ersättning", "traktamente", "in kind", "ytelse",
                                    "ydelse", "luontoisedu", "korvaus", "avantage", "vergoeding", "voordelen",
                                    "vergütung", "zulage", "aufwandersatz", "retribuciones", "dietas", "compensaci",
                                    "prestazioni", "indennità", "świadcze")):
            lack.append("the benefits in cash or kind (or that there are none)")
        if not any(w in t for w in ("return", "repatriat", "travel home", "hemresa", "återresa", "resa hem", "hjemreise",
                                    "tilbagevenden", "kotiuttami", "retour", "terugkeer", "rückführung",
                                    "heimreise", "rapatriement", "repatriaci", "rimpatrio", "powr")):
            lack.append("whether the return home is paid, and on what terms")
        if law == "nl":                     # BW 7:655 (1) k: housing and the social insurance
            if "huisvesting" not in t and "housing" not in t:
                lack.append("the housing")
            if not re.search(r"sociale verzekering|social insurance|sociale zekerheid", t):
                lack.append("whether Dutch social insurance law applies or which bodies carry it out")
        if law == "dk" and "attest" not in t:
            lack.append("whether the certificates for the posting are arranged (lov 501 § 4, stk. 1, nr. 5)")
        given = given_date(spec, paras)
        if given and frm and given > frm:
            lack.append("a statement dated before departure (it is dated %s, departure %s)" % (given, frm))
        if lack:
            return False, "work abroad of %d days lacks %s [%s]" % (days, "; ".join(lack), ref("abroad", law))
        return True, "work abroad of %d days names the country, period, currency, benefits and return [%s]" % (
            days, ref("abroad", law))

    if rule_id == "EMPLOY-LANG":
        tag = doc_language(path) or (spec or {}).get("language") or ""
        lang = LANG_OF_LOCALE.get(str(tag).lower()[:2])
        if not lang:
            return None, "the statement names no language"
        other = []
        for style, text in paras:
            if not re.match(r"(heading|rubrik|title)", style, re.I) or style.lower().startswith("title"):
                continue
            if label_of(text, lang):
                continue
            found = label_of(text)
            if found and found != "_sign":
                other.append(text)
        if other:
            return False, "headings not in the statement's language (%s): %s" % (tag, "; ".join(other[:5]))
        return True, "every heading is in %s" % tag

    if rule_id == "EMPLOY-REFERENCE":
        allowed = REFERABLE.get(law)
        if allowed is None:
            return None, "the statement's law sets no rule on giving terms by reference"
        bad = [NAME[item] for item, body in secs.items()
               if item in WANT[law] and item not in allowed and body and POINTER.match(norm(body))
               and not (law == "be" and item in BE_ART5 and BE_WORK_RULES.search(norm(body)))]
        if bad:
            return False, ("%s only point elsewhere; %s lets a statement refer to a law or an agreement only for "
                           "other particulars, so state these" % ("; ".join(bad), {
                               "eu": "Art. 4(3)", "no": "arbeidsmiljøloven § 14-6 (2)", "dk": "lov 501 § 3, stk. 4",
                               "fi": "työsopimuslaki 2:4 § 4 mom.", "uk": "ERA s.2(2) and (3)",
                               "be": "the law of 7 October 2022 (art. 4 § 2 6° and 8°, art. 5; the work rules for "
                                     "art. 5's items)",
                               "nl": "BW 7:655 (2)", "at": "AVRAG § 2 (5)",
                               "ie": "s. 3(3) of the Terms of Employment (Information) Act 1994",
                               "es": "Real Decreto 723/2026 art. 3.3 (letters f) 1.º, g) 1.º to 4.º, h), i), n) and p))",
                               "it": "D.Lgs. 152/1997 art. 1 c. 5-bis (letters h), i), l), m), n), o) and r))",
                               "pl": "Kodeks pracy art. 29 § 3(1) (§ 3 pkt 1 a) to f), h) to k) and pkt 2, by naming "
                                     "provisions of law)"}[law]))
        return True, "the particulars that must be stated are stated, not referred"

    if rule_id == "EMPLOY-NO-TEMP" or rule_id == "EMPLOY-FI-TEMP":
        want_law = "no" if rule_id == "EMPLOY-NO-TEMP" else "fi"
        if law != want_law:
            return None, "not a %s statement" % ("Norwegian" if want_law == "no" else "Finnish")
        start, end, fixed = term_dates(spec, secs)
        if not fixed:
            return None, "a permanent employment"
        t = norm(secs.get("term", ""))
        lack = []
        if not end and not any(w in t for w in EXPECTED):
            lack.append("the expected length")
        words_ = ("grunnlag", "§ 14-9", "vikar", "midlertidig karakter", "praksis", "arbeidsmarkedstiltak", "idrett") \
            if want_law == "no" else ("peruste", "pitkäaikaistyöt", "1 luvun 3 a")
        if not any(w in t for w in words_):
            lack.append("the basis for the fixed term" if want_law == "no" else "the ground for the fixed term (peruste)")
        if lack:
            return False, "the fixed term lacks %s [%s]" % (" and ".join(lack), ref("term", law))
        return True, "the fixed term gives its length and its basis [%s]" % ref("term", law)

    if rule_id == "EMPLOY-NO-HOURS":
        if law != "no":
            return None, "not a Norwegian contract"
        h, b = norm(secs.get("hours", "")), norm(secs.get("breaks", ""))
        lack = []
        variable = bool(VARIABLE.search(h))
        if not variable:
            if not re.search(r"\d+(?:[.,]\d+)?\s*timer?\b[^.;]*\b(uke|uken|veke)", h):
                lack.append("the weekly hours")
            if not (re.search(r"\b(dag|dagen|daglig)\b", h) or re.search(r"(mandag|tirsdag|onsdag|torsdag|fredag|lørdag|søndag)", h)):
                lack.append("the daily hours or the days")
            if not re.search(r"\b(kl\.?\s*)?\d{1,2}[.:]\d{2}\b", h):
                lack.append("when in the day the work is placed")
        if not b or na(b) or not re.search(r"\d", b):
            lack.append("the length of the breaks (§ 14-6 (1) k)")
        if lack:
            return False, "working time lacks %s (arbeidsmiljøloven § 14-6 (1) j, k)" % "; ".join(lack)
        return True, "daily and weekly hours, their placing and the breaks are given (§ 14-6 (1) j, k)"

    if rule_id == "EMPLOY-US-ATWILL":
        if law != "us":
            return None, "not a US offer"
        t = norm(secs.get("term", ""))
        state = us_state(spec, flat)
        at_will = "at will" in t or "at-will" in t
        if not at_will and not (any(w in t for w in FIXED) and dates_in(secs.get("term", ""))):
            return False, "the offer does not say whether the employment is at will or for a set term"
        if at_will and state == "MT":
            return False, ("an at-will offer for work in Montana: Mont. Code Ann. 39-2-904 may require good cause for a "
                           "discharge after the probationary period (not proved against the current code); ask the "
                           "employer how to word it")
        return True, "the offer says the employment is %s" % ("at will" if at_will else "for a set term")

    if rule_id == "EMPLOY-US-FLSA":
        if law != "us":
            return None, "not a US offer"
        c = norm(secs.get("classification", ""))
        if not c:
            return False, "the offer gives no Fair Labor Standards Act classification (exempt or non-exempt)"
        if "non-exempt" in c or "nonexempt" in c:
            if not (re.search(r"one and one-half|1\.5|time and a half|one and a half", c) and "40" in c):
                return False, ("a non-exempt position: say that hours over 40 in a workweek are paid at one and one-half "
                               "times the regular rate (29 U.S.C. 207(a)(1))")
            return True, "non-exempt, with the overtime rule stated (29 U.S.C. 207(a)(1))"
        if "exempt" in c:
            per = str(((spec or {}).get("pay") or {}).get("per", "")) if spec else ""
            if per == "hour" or re.search(r"\ban hour\b|per hour", norm(secs.get("pay", ""))):
                return False, ("an exempt position paid by the hour: most exemptions need pay on a salary basis "
                               "(29 CFR 541.600); the computer employee exemption allows an hourly rate (541.400(b)); "
                               "check which applies with the employer")
            return True, "exempt, with the exemption named (29 U.S.C. 213(a)(1))"
        return False, "the classification says neither exempt nor non-exempt"

    if rule_id == "EMPLOY-US-STATE":
        if law != "us":
            return None, "not a US offer"
        state = us_state(spec, flat)
        exempt = exempt_of(spec, flat)
        if state not in ("NY", "CA"):
            return None, "no New York or California pay notice applies"
        if state == "CA" and exempt:
            return None, "California Labor Code 2810.5(c) leaves out an employee exempt from overtime"
        t = norm(secs.get("state_notice", ""))
        if not t:
            return False, "work in %s: the offer has no %s" % (state, "notice of pay rate and pay day (NY Labor Law 195(1))"
                                                              if state == "NY" else "notice to employee (Cal. Labor Code 2810.5)")
        want = [("the rate of pay and its basis", "of pay and basis"), ("the allowances claimed", "allowances"),
                ("the regular pay day", "pay day" if state == "NY" else "payday"), ("the employer's name", "employer's name"),
                ("any doing-business-as name", "doing business as"), ("the physical address", "physical address"),
                ("the mailing address", "mailing address"), ("the telephone number", "telephone")]
        if state == "NY":
            if not exempt:
                want.append(("the overtime rate (195(1)(c))", "overtime rate"))
            want += [("the employee's primary language", "primary language"), ("the signed acknowledgment", "acknowledgment")]
        else:
            want += [("the workers' compensation carrier", "workers' compensation"), ("paid sick leave", "sick leave"),
                     ("any emergency or disaster declaration", "disaster declaration")]
        def given(key):
            if key == "acknowledgment":
                return key in t
            return bool(re.search(r"%s[^:]*:\s*[^\s.]" % re.escape(key), t))
        lack = [what for what, key in want if not given(key)]
        if lack:
            return False, "the %s notice lacks %s [%s]" % (state, "; ".join(lack), "NY Labor Law 195(1)" if state == "NY"
                                                          else "Cal. Labor Code 2810.5(a)(1)")
        return True, "the %s pay notice items are there" % state

    if rule_id == "EMPLOY-US-WORDING":
        if law != "us":
            return None, "not a US offer"
        m = re.search(r"(federal law|fair labor standards act|flsa|u\.s\. law)[^.]{0,40}\b(requires|require|mandates)\b"
                      r"[^.]{0,60}\b(letter|statement|offer|written|notice)", flat)
        if m:
            return False, ("the letter says %r; no federal law asks for a written offer or statement, so cite the state "
                           "law that does, or say nothing" % m.group(0))
        return True, "the letter claims no federal written-statement duty"

    if rule_id == "EMPLOY-IE-CORE":
        if law != "ie":
            return None, "not an Irish statement"
        lack = []
        p = norm(secs.get("parties", ""))
        if spec:
            lack += ["the full name %s" % who for who in (spec["employer"].get("name"), spec["worker"].get("name"))
                     if who and norm(who) not in p]
            addr = spec["employer"].get("address")
            if addr and norm(addr) not in p:
                lack.append("the employer's address")
        h = norm(secs.get("hours", ""))
        if not re.search(r"(per|a) normal working day[^.;]*\d|\d[\d.,]*\s*hours?\s*(a|per) day", h):
            lack.append("the hours expected per normal working day")
        if not re.search(r"(per|a) normal working week[^.;]*\d|\d[\d.,]*\s*hours?\s*(a|per) week", h):
            lack.append("the hours expected per normal working week")
        if "overtime" not in h and "overtime" not in norm(secs.get("pay", "")):
            lack.append("the terms on overtime (s. 3(1A)(j))")
        if "pay reference period" not in norm(secs.get("pay", "")):
            lack.append("the pay reference period for the National Minimum Wage Act 2000 (s. 3(1A)(d))")
        if lack:
            return False, "the five-day core statement lacks %s (s. 3(1A))" % "; ".join(lack)
        return True, "the core terms of s. 3(1A) are there"

    if rule_id == "EMPLOY-SIGNED":
        if law not in ("nl", "ie"):
            return None, "the statement's law does not ask for the employer's signature"
        signs = ("voor de werkgever", "namens de werkgever", "for the employer", "on behalf of the employer",
                 "signed for the employer")
        # The signature block: the paragraphs from the signatures heading on, or those with a signature line.
        block, on = [], False
        for style, text in paras:
            if re.match(r"(heading|title)", style, re.I):
                on = label_of(text) == "_sign"
                continue
            if on or "____" in text:
                block.append(text)
        if not any(w in norm(" ".join(block)) for w in signs):
            return False, "no signature block for the employer (%s)" % (
                "BW 7:655 (3): the employer signs the opgave" if law == "nl" else "s. 3(4) and s. 3A(a): signed and "
                "dated by or on behalf of the employer")
        if law == "ie" and not given_date(spec, paras):
            return False, "the statement is not dated (s. 3(4), s. 3A(a))"
        return True, "the employer signs%s" % (" and dates" if law == "ie" else "")

    if rule_id == "EMPLOY-BE-LANG":
        if law != "be":
            return None, "not a Belgian statement"
        region = be_region(spec, " ".join([secs.get("place", ""), secs.get("parties", "")]))
        lang = LANG_OF_LOCALE.get(str(doc_language(path) or (spec or {}).get("language") or "").lower()[:2])
        if not region:
            return None, "no Belgian postcode in the workplace or the parties"
        if region == "german":
            return None, "the German-speaking area: the statement's language is for the employer to confirm"
        want = {"nl": {"nl"}, "fr": {"fr"}, "brussels": {"nl", "fr"}}[region]
        if lang not in want:
            return False, ("the workplace is in %s, which writes in %s (%s); the statement is in %s" % (
                {"nl": "the Dutch language area", "fr": "the French language area", "brussels": "Brussels-Capital"}[region],
                " or ".join(sorted({"nl": "Dutch", "fr": "French"}[x] for x in want)),
                {"nl": "Flemish decree of 19 July 1973 art. 5", "fr": "decree of 30 June 1982 art. 2",
                 "brussels": "Dutch or French by the worker's language"}[region], lang or "no named language"))
        return True, "the statement is in the region's language (%s)" % lang

    if rule_id == "EMPLOY-AGREEMENT":
        if law not in ("es", "it"):
            return None, "the statement's law does not say how a collective agreement is identified"
        body = secs.get("collective", "")
        c = norm(body)
        if not c or na(body):
            return None, "no collective agreement applies"
        if law == "es":
            lack = [what for what, found in (
                ("its code (código de convenio)", re.search(r"código\D{0,40}\d{6,}", c)),
                ("the official bulletin and the date it was published", re.search(
                    r"\b(boe|bop|bocm|boja|dogc|dog|doe|bopv|boletín|diario oficial|diari oficial)\b", c) and dates_in(body)),
                ("its period of validity, or that it applies beyond its term (ultraactividad)",
                 re.search(r"vigencia|vigente|ultraactividad", c))) if not found]
            if lack:
                return False, ("the collective agreement is named without %s (Real Decreto 723/2026 art. 3.2 o))"
                               % "; ".join(lack))
            return True, "the collective agreement gives its code, where and when it was published and its validity"
        lack = []
        if not re.search(r"sottoscritt|firmatari|stipulat", c):
            lack.append("the parties that signed it (art. 1 c. 1 q))")
        public = re.search(r"pubblica amministrazione|amministrazione pubblica|datore di lavoro pubblico", flat)
        if not public and not re.search(r"codice\b.{0,80}?\b(?=\w*\d)(?=\w*[a-z])\w{3,}\b", c):
            lack.append("the single alphanumeric code CNEL gives the national agreement, which a private employer "
                        "states (art. 1 c. 1 q-bis))")
        if lack:
            return False, "the collective agreement is named without %s (D.Lgs. 152/1997)" % "; ".join(lack)
        return True, "the collective agreement names its signatories%s" % ("" if public else " and its CNEL code")

    if rule_id == "EMPLOY-PL-CONTRACT":
        if law != "pl":
            return None, "not a Polish statement"
        lack = []
        t = norm(secs.get("term", ""))
        if not re.search(r"okres próbny|czas określony|czas nieokreślony", t):
            lack.append("the type of contract: for a trial period, a fixed term or an indefinite time (art. 25 § 1)")
        made = iso(spec.get("contract_date")) if spec and spec.get("contract_date") else None
        if "zawart" not in t or not dates_in(secs.get("term", "")) or (made and made not in dates_in(secs.get("term", ""))):
            lack.append("the date the contract was concluded")
        # "Dobowy i tygodniowy wymiar czasu pracy" is the § 3 information, not the contract's full time or fraction
        if not re.search(r"etat|pełnym wymiarze|(?<!tygodniowy )wymiar czasu pracy", norm(secs.get("hours", ""))):
            lack.append("the working time basis, wymiar czasu pracy: full time or the fraction (pkt 4)")
        only = [NAME[item] for item in ("job", "place", "pay", "start", "term") if points(secs.get(item, ""))]
        if only:
            lack.append("%s as a term of the contract, not as a pointer to a provision" % ", ".join(only))
        if lack:
            return False, "the contract's own terms (Kodeks pracy art. 29 § 1) lack %s" % "; ".join(lack)
        return True, "the contract's own terms of art. 29 § 1 are stated"

    if rule_id == "EMPLOY-AU-STATEMENTS":
        if law != "au":
            return None, "not an Australian statement"
        t = norm(secs.get("statements", "")) or flat
        kind = str(((spec or {}).get("term") or {}).get("type", "")).lower() if spec else ""
        casual = kind == "casual" or (not spec and "casual employment" in flat)
        fixed = kind in ("fixed", "fixed-term", "fixed term") or (not spec and "fixed-term employment" in flat)
        lack = []
        if "fair work information statement" not in t:
            lack.append("the Fair Work Information Statement (s 125)")
        if casual and "casual employment information statement" not in t:
            lack.append("the Casual Employment Information Statement (s 125B)")
        if fixed and "fixed term contract information statement" not in t:
            lack.append("the Fixed Term Contract Information Statement (s 333K)")
        if lack:
            return False, "the statement does not say the employee gets %s" % " and ".join(lack)
        return True, "the information statements the employment needs are named"

    return None, "unknown rule"


RULES = ("EMPLOY-ITEMS", "EMPLOY-DATES", "EMPLOY-PROBATION", "EMPLOY-PAY", "EMPLOY-ABROAD", "EMPLOY-LANG",
         "EMPLOY-REFERENCE", "EMPLOY-NO-TEMP", "EMPLOY-NO-HOURS", "EMPLOY-FI-TEMP", "EMPLOY-US-ATWILL",
         "EMPLOY-US-FLSA", "EMPLOY-US-STATE", "EMPLOY-US-WORDING", "EMPLOY-AU-STATEMENTS", "EMPLOY-IE-CORE",
         "EMPLOY-SIGNED", "EMPLOY-BE-LANG", "EMPLOY-AGREEMENT", "EMPLOY-PL-CONTRACT")

if __name__ == "__main__":
    for rule in RULES:
        print(rule, check(rule, sys.argv[1], {}, "first"))
