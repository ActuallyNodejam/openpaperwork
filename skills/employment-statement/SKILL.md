---
name: employment-statement
description: "Written terms of employment for a new hire, as Word: UK statement of particulars, anställningsbevis, US offer letter and more countries. Not legal advice."
version: 0.4.0
license: Apache-2.0
platforms: [linux, macos, windows]
metadata:
  domain: hr
  version: "0.4.0"
workflows:
  - id: "employment-terms"
    arguments: "employment terms"
    icon: "file-text"
    menu: "Anställningsbevis"
    menu_en: "Employment terms"
    gives: "Skriftliga anställningsvillkor i Word med allt lagen kräver"
    gives_en: "Written terms of employment in Word with everything the law asks for"
    takes: "Skriv en rad: Sara Lind börjar 1 mars som designer i Malmö, 42 000 kr i månaden"
    takes_en: "Write one line: Sam Lee starts on 1 March as a designer in Leeds, 3,400 pounds a month"
---

# Employment statement

Use this when an employer asks for the written terms a new worker gets. It records what the
employer and the worker agreed; it is not a new contract (in Norway the written employment
contract itself is what the law asks for, and both sign it).

A drafting check, not legal advice: it reads whether each particular is there, never whether a term is fair, usual or allowed.

## How to make one

1. Read what the person gave you: the offer, their notes, the job ad. Ask nothing they already say.
2. Pick the law with `"law"` and the language with `"language"`:

| Law | Country and document | Language | Paper | Template |
| --- | --- | --- | --- | --- |
| `uk` | United Kingdom, written statement of particulars | `en` | A4 | `statement-uk.spec.json` |
| `se` | Sweden, anställningsbevis | `sv` | A4 | `anstallningsbevis.spec.json` |
| `no` | Norway, arbeidsavtale | `nb` | A4 | `arbeidsavtale.spec.json` |
| `dk` | Denmark, ansættelsesbevis | `da` | A4 | `ansaettelsesbevis.spec.json` |
| `fi` | Finland, selvitys työnteon keskeisistä ehdoista | `fi` | A4 | `selvitys-tyoehdoista.spec.json` |
| `eu` | another EU country, Directive (EU) 2019/1152 | `en` | A4 | `statement-eu.spec.json` |
| `ca` | Canada, federally regulated employer: employment statement | `en` or `fr` | Letter | `employment-statement-ca.spec.json`, `declaration-emploi.spec.json` |
| `on` | Ontario, employment information for a new employee | `en` or `fr` | Letter | `employment-information-on.spec.json` |
| `au` | Australia, statement of employment terms | `en` | A4 | `statement-au.spec.json` |
| `us` | United States, offer letter | `en` | Letter | `offer-letter-ny.spec.json`, `offer-letter-ca.spec.json` |
| `be` | Belgium, informatie over de arbeidsrelatie / informations sur la relation de travail | `nl` or `fr`, by region | A4 | `informatie-be-nl.spec.json`, `informations-be-fr.spec.json` |
| `nl` | Netherlands, opgave van de arbeidsvoorwaarden | `nl` | A4 | `opgave-nl.spec.json` |
| `at` | Austria, Dienstzettel | `de` | A4 | `dienstzettel-at.spec.json` |
| `ie` | Ireland, statement of terms of employment | `en` | A4 | `statement-ie.spec.json` |
| `es` | Spain, información sobre los elementos esenciales del contrato de trabajo | `es` | A4 | `informacion-es.spec.json` |
| `it` | Italy, informazioni sul rapporto di lavoro | `it` | A4 | `informazioni-it.spec.json` |
| `pl` | Poland, informacja o warunkach zatrudnienia | `pl` | A4 | `informacja-pl.spec.json` |

   An employer in Canada follows the Canada Labour Code only when it is federally regulated
   (banks, airlines, trucking across a provincial border, telecoms); any other employer in Ontario
   uses `on`. Ask when the notes do not say. A Belgian statement is written in the language of the
   region the workplace is in, read from its postcode: Dutch in Flanders, French in Wallonia, either
   in Brussels by the worker's language; leave `language` out and the script picks it.
3. Write a small spec file (JSON) from the template.
4. Ask for what only the employer can give when the notes leave it out: the pay and how it is paid,
   the hours, the paid leave, the notice, and the country's own items below. Never fill one in yourself.
   A country's note is one of them: the UK disciplinary rules and the person a grievance goes to come
   from the notes, never a stock line such as "procedures are in place, ask HR".
5. Build the statement:

```bash
python3 <skill folder>/scripts/statement_create.py spec.json statement.docx
```

6. Run the pack check and fix what it names:
   `python3 <skill folder>/../_checks/packcheck.py employment-statement <your output>`

## Nothing given is left off

`statement_create.py` stops before anything is laid out when the spec holds a key it has no field
for, a value of another shape, or an item the chosen law's list has no heading for (`breaks` under
`uk`), and names the key. `spec.fields.json` beside this file lists every key. A term with no field
of its own goes in `further`, one line each, printed under a last heading before the signatures; a
particular of the employer (its registered office, a second number) in `employer.further`, printed
with the parties. Never leave a fact out to make the error go away: put it where the message says,
or say in your reply what the page does not carry.

The check fails a heading with nothing under it (EMPLOY-EMPTY, a house rule).

Run the check with `--in` and the working folder. It then reads the person's own files there and
asks, once and never as a fail (NOTES-FLOOR): which e-mail addresses, numbers, dates and amounts the
notes hold and the page does not, which of them the page carries changed. Answer the question once:
put each on the page as the notes have it, or say in your reply why it does not belong there. Never
change one to shorten the list.

Work in the working folder, the folder the person is working in: write the data file there, run the
script from there by its full path (`<skill folder>` is the folder this file is in) and give the
output a path there. The builder refuses an output path inside the library's own folder, where the
person never looks; hand back the path in the working folder.

Look for `company.json` in the working folder first: it holds the company's own particulars, written
once (name, address, VAT and register numbers, registered office, share capital, bank account). The
builder fills from it what the data file leaves out of the sender, stops when the two disagree, and
the check fails a page whose sender disagrees with it (COMPANY-FILE). When the folder has none and
the person gives their company's particulars, write it once: `python3 <skill folder>/../_shared/company.py
make company.json name="..." country=.. street="..." postcode=.. city=.. vat_id=..
register_number=..`; it says which particulars that country's company law still wants. One the files
do not give is declared with `unknown=<key>`, never made up.

## What the statement holds

| Particular | EU Art. 4(2) | Sweden LAS 6 c § | UK ERA | Norway aml. § 14-6 (1) | Denmark lov 501 § 3 stk. 2 | Finland TSL 2:4 § |
| --- | --- | --- | --- | --- | --- | --- |
| The parties (Sweden, Denmark, Finland: with addresses) | (a) | 1 | s.1(3)(a) | a | 1 | 1 |
| Place of work, or that it varies, and the employer's address | (b) | 1 | s.1(4)(h) | b | 2 | 5 |
| Job title or a short description of the work | (c) | 2 | s.1(4)(f) | c | 3 | 6 |
| Start date (UK: also when continuous employment began) | (d) | 1 | s.1(3)(b), (c) | d | 4 | 2 |
| Permanent or fixed term; a fixed term's end or expected length (Norway and Finland: its basis) | (e) | 3 | s.1(4)(g) | e | 5 | 3 |
| User undertakings, for an agency worker | (f) | 8 | | o | 6 | 10 |
| Probation: length and conditions | (g) | 3 c | s.1(4)(ga) | f | 7 | 4 |
| Training the employer provides | (h) | 9 | s.1(4)(l)-(n) | p | 13 | 11 |
| Paid leave (UK: also other paid leave, s.1(4)(d)(iia)) | (i) | 10 | s.1(4)(d)(i) | g | 8 | 12 |
| Ending the employment: form and notice | (j) | 3 a, 11 | s.1(4)(e) | h | 9 | 13 |
| Pay: the amount, other elements separately, how often and how it is paid | (k) | 4 | s.1(4)(a), (b) | i | 10 | 7 |
| Hours, or for a variable schedule the guaranteed hours, reference hours and notice | (l), (m) | 5-7 | s.1(4)(c) | j, m | 11, 12 | 8, 9 |
| Breaks; a special working-time arrangement | | | | k, l | | |
| Collective agreements | (n) | 13 | s.1(4)(j) | n | 14 | 14 |
| Social security; Finland: the pension and accident insurers | (o) | 12 | | q | 15 | 15 |
| Sickness, pensions, other benefits | | | s.1(4)(d)(ii), (iii), (da) | | | |
| Disciplinary rules and procedure, appeals and grievances | | | s.3(1) | | | |
| Work abroad: country, period, currency, benefits, return home | Art. 7(1) | 6 d § | s.1(4)(k) | § 14-7 | § 4 | 16 |

Belgium, the Netherlands, Austria and Ireland, each from its own law:

| Particular | Belgium, law of 7 October 2022 | Netherlands, BW 7:655 (1) | Austria, AVRAG § 2 (2) | Ireland, 1994 Act s. 3 |
| --- | --- | --- | --- | --- |
| The parties (Netherlands, Austria: with addresses; Ireland: full names and the employer's address) | art. 4 § 2 1° | a | 1, 2 | (1A)(a), (b) |
| Place of work, or that it varies (Austria: with the company's seat) | 2° | b | 6 | (1A)(g) |
| Job, grade or a short description (Austria: also the grading in a pay scheme, 7) | 3° | c | 8 | (1A)(h) |
| Start date | 4° | d | 3 | (1A)(i) |
| A fixed term's end or expected length (Netherlands: also whether it is open-ended) | 5° | e, n | 4 | (1A)(c) |
| Pay: the basic amount, other elements separately, how often and how it is paid | 6° | h | 9 | (1A)(d); (1)(h) |
| Probation: length and conditions | 7° | q | 14 | (1A)(k) |
| Hours: a fixed schedule's day, breaks and days off, or a variable one's hours, window and notice | 8°, 9° | i | 11 | (1A)(e), (j); (1)(p) |
| Training the employer provides | art. 5 1° | r | 15 | (1)(n) |
| Paid leave | art. 5 2° | f | 10 | (1)(j) |
| Ending the employment: procedure and notice | art. 5 3° | g | 5 | (1)(l) |
| Collective agreements (Belgium: the joint committee; Austria: where they can be read; Ireland: also a registered employment agreement or employment regulation order) | art. 5 4° | l | 12 | (1)(fa), (m) |
| Social security institution (Austria: the social insurance institution and the BV-Kasse, with addresses) | art. 5 5° | s | 13 | (1)(q) |
| Whether the worker joins a pension scheme; whether it is an agency, payroll or on-call contract | | j, m, o, p | | (1)(k)(ii), (o) |
| Sick leave and sick pay; the note on asking for the average hourly rate; the tips policy | | | | (1)(k)(i), (ga); (1A)(f) |
| Work abroad: country, period, currency, benefits, return home (Netherlands: also housing and social insurance) | art. 6 | k | § 2 (3) | s. 4 |

- **United Kingdom**: Statutory Sick Pay is paid from the first full day of sickness absence, with no
  lower earnings limit, at the weekly rate or 80% of average weekly earnings if lower (from 6 April
  2026, Employment Rights Act 2025 ss. 10 and 11; https://www.business.gov.uk/campaign/employment-changes/employers/statutory-sick-pay/).
  Dated note, 2026-10-20: a written statement of the right to join a trade union, given with the
  statement of particulars, is planned from 1 January 2027 (Employment Rights Act 2025; government
  response of 25 September 2026, regulations due in November 2026). It is not in force today, so the
  starter does not carry it; the builder warns for a start on or after 1 January 2027.
- **Belgium**: the document is due by the first day of work (art. 4 § 1). Art. 5 binds it only for a
  worker outside the work rules act of 8 April 1965; for everyone else the work rules carry those
  items, so give each one or write that it is in the work rules (arbeidsreglement, règlement de
  travail). There is no trial period in an ordinary contract since 1 January 2014; a student
  contract's first three days and agency work are the exceptions.
- **Netherlands**: items a to e, h, i and q within a week of the start, the rest within a month
  (7:655 (3)); the employer signs the opgave, and an electronic one needs the worker's consent and a
  qualified signature. Whether there is a pension scheme, an agency or payroll contract and an
  on-call contract is always answered, yes or no. Probation: none in a contract of six months or
  less, one month in a fixed term under two years, two months otherwise (7:652).
- **Austria**: the Dienstzettel is due without delay after the start (§ 2 (1)). The basic pay is an
  amount in figures, never a reference (§ 2 (5)). Probation is at most one month (ABGB § 1158 (2),
  AngG § 19 (2)).
- **Ireland**: the core terms of s. 3(1A) within five days of the start, the rest within one month
  (s. 3(1)); the statement is signed and dated by or for the employer (s. 3(4), s. 3A). Give the hours
  expected per normal working day and week and the pay reference period under the National Minimum
  Wage Act 2000. Probation is at most six months, twelve only exceptionally (s. 6D).

Spain, Italy and Poland, each from its own law:

| Particular | Spain, Real Decreto 723/2026 art. 3.2 | Italy, D.Lgs. 152/1997 art. 1 c. 1 | Poland, Kodeks pracy art. 29 |
| --- | --- | --- | --- |
| The parties, with the employer's registered address | a), c) | a), c) | § 1 |
| Place of work, or that it varies or is the worker's to choose | c) | b) | § 1 pkt 2; § 3 pkt 1 g) |
| The work: a description (Spain: with the professional group; Italy: or the grade, level and qualification) | d), e) | d) | § 1 pkt 1 |
| Start date | b) | e) | § 1 pkt 5 |
| The kind of contract; a fixed term's end or expected length (Spain: its cause; Poland: the date the contract was concluded) | b), d) | f) | § 1, pkt 6, 7 |
| Pay: the base amount and each other element separately (Spain, Italy: how often and how it is paid) | f) | n) | § 1 pkt 3; § 3 pkt 1 h) |
| Working time (Spain: daily, weekly and annual; Poland: the basis, the norm, the breaks, the rest, overtime) | g) 1.º-3.º, 5.º | o), p) | § 1 pkt 4; § 3 pkt 1 a)-f) |
| Paid leave | g) 4.º | l) | § 3 pkt 1 i) |
| Probation: length and conditions | h) | h) | § 1 pkt 6 |
| Training the employer provides | i) | i) | § 3 pkt 1 k) |
| User undertaking, for an agency worker | j) | g) | |
| Automated decision or monitoring systems | k) | s) | |
| The equality plan, work-life measures and the protocol against harassment; LGTBI measures | l), m) | | |
| Ending the employment: procedure and notice | n) | m) | § 3 pkt 1 j) |
| The collective agreement (Spain: its code, bulletin, date and validity; Italy: its signatories and CNEL code) | o) | q), q-bis) | § 3 pkt 1 l) |
| Social security: the bodies that receive the contributions and any further cover | p) | r) | § 3 pkt 2 |
| How the terms may be changed | q) | | |
| Work regulations, or the pay day, the night time and the attendance rules without them | | | § 3 pkt 1 m) |
| Work abroad over four consecutive weeks: country, period, currency, benefits, return home | art. 4 | art. 2 | art. 29(1) § 2 |

- **Spain**: Real Decreto 723/2026 of 9 September transposes the Directive and has been in force since
  5 October 2026; it repealed Real Decreto 1659/1998, whose list was shorter and whose time was two months.
  The information is now due before the employment begins (art. 7.1), for any employment of more than four
  weeks (art. 2.2), on paper or electronically (art. 6). The base pay and its supplements, the working time,
  the holidays, the probation, the training, the ending and the Social Security item may be given by a precise
  reference to the law or the collective agreement (art. 3.3); nothing else may. The protocol against sexual
  harassment is asked for whatever the company's size (art. 3.2 l)). Probation: the collective agreement sets
  the limit; without one, six months for técnicos titulados, two for others, one in a temporary contract of six
  months or less (Estatuto de los Trabajadores art. 14.1).
- **Italy**: the contract or the hiring notice is handed over before work starts (art. 1 c. 2); what they do
  not give follows in writing within seven days, and letters g), i), l), m), q), q-bis) and r) within a month
  (c. 3). Letters h), i), l), m), n), o) and r) may be given by naming the law or the collective agreement
  (c. 5-bis). A private employer gives the single alphanumeric code CNEL assigns to the national agreement
  (q-bis), added by D.L. 62/2026; the date it took effect is not proved against Normattiva, so ask for the code and say it may not yet be required). Probation is at most six months; in a fixed term one day of actual work per
  fifteen calendar days, at most fifteen days up to six months and thirty days under twelve (D.Lgs. 104/2022
  art. 7). A posting abroad is informed whatever its length, a mission over four consecutive weeks (art. 2).
- **Poland**: the employment contract itself is concluded in writing and states the terms of art. 29 § 1; this
  file repeats them and gives the information of § 3, due within 7 days of admission to work (the social
  insurance institution within 30). The information of § 3 pkt 1 a) to f), h) to k) and pkt 2 may name the
  provisions of law instead (§ 3(1)); the contract's own terms may not. A trial-period contract runs at most
  3 months, 1 or 2 before a short fixed term (art. 25 § 2, § 2(2)).

Outside Europe:

- **Canada (federal)**: the Canada Labour Standards Regulations s. 3.1 (a) to (m): the parties, the
  job and its duties, the address of the ordinary place of work, the start date, the term, any
  probation, the qualifications, any required training, the hours with how they are counted and the
  overtime rules, the wage and the overtime rate, how often pay days and other pay come, the
  mandatory deductions, and how work-related expenses are claimed. Due within the first 30 days
  (Canada Labour Code s. 253.2(1)). In French: déclaration d'emploi.
- **Ontario**: O. Reg. 285/01 s. 1.2 (2), for an employer with 25 or more employees: the legal and
  any operating name, an address, a telephone number and a contact name, where the work will be,
  the starting wage, the pay period and pay day, and the expected hours. Due before the first day,
  or as soon after as reasonably possible. Give the Ministry's ESA poster within 30 days as well
  (Employment Standards Act, 2000 s. 2(5) and (7)).
- **Australia**: no law lists the contents of a contract. The statement says the type of employment
  (full-time, part-time, casual, fixed term), the award or agreement, the pay and how often it is
  paid (at least monthly, Fair Work Act 2009 s 323), the hours, the leave and notice the National
  Employment Standards give, and superannuation. It names the information statements the employee
  gets: the Fair Work Information Statement (s 125), and the Casual Employment Information
  Statement (s 125B) or the Fixed Term Contract Information Statement (s 333K). Download the current
  ones from fairwork.gov.au and attach them; this pack does not copy them. A fixed term with an option to
  renew or extend sets `term.renewal` (`times`, `latest_end`): s 333E allows one renewal and two years in
  all unless an exception in s 333F applies, and the check holds the statement to that.
- **United States**: no federal law asks for a written offer or statement; never say one does. The
  letter states at-will employment (or a set term), the Fair Labor Standards Act classification
  (non-exempt: overtime at one and one-half times the regular rate over 40 hours, 29 U.S.C.
  207(a)(1); exempt: name the exemption), the pay rate and basis, the pay days and the hours. Where
  the work is in New York (Labor Law § 195(1)) or California (Labor Code § 2810.5, non-exempt
  employees) the pay notice items follow in their own section; set `work_state` and
  `state_notice`. New York wants the notice in the employee's primary language too; the state
  Department of Labor publishes its forms in other languages. In Montana the Wrongful Discharge from
  Employment Act (Mont. Code Ann. 39-2-904) may require good cause after the probationary period, so an
  at-will sentence may not hold; this is not proved against the current code: ask the employer.

A particular that does not apply is written "Not applicable" with the reason (in the document's
language), never left out. The statement is due by the seventh calendar day of work in the EU,
Sweden, Norway (immediately for less than a month), Denmark and Finland (Art. 5(1), LAS 6 c §,
aml. § 14-5, lov 501 § 3, TSL 2:4 § 4 mom.), by the first day in the UK (ERA s.1(2)) and Belgium,
within a week in the Netherlands and Austria, within five days in Ireland, before the employment
begins in Spain, within seven days in Italy and Poland, within 30 days
under the Canada Labour Code, before the first day in Ontario and at hiring in New York and
California, and before departure for work abroad over the law's threshold.

## Never work these out

A notice period, a number of holiday days, a minimum wage or an overtime rate turns on the worker's
age, service and hours, on the award or collective agreement and on the state or province. Write
what the employer gives you, or point to the law that sets it where the law lets you: "the notice
section 86 of the Employment Rights Act 1996 sets out", "oppsigelsesfristene i arbeidsmiljøloven
§ 15-3", "opsigelsesvarslerne følger funktionærlovens § 2". Never compute one. Some particulars
can never be given by pointing elsewhere: the parties, the place, the work, the start, the term, the
probation and the collective agreement in Norway; numbers 1 to 6, 12 and 14 in Denmark; the parties,
dates, place and work in Finland; items a to e, j and l to p in the Netherlands (7:655 (2)); the
parties, dates, grading, work, basic pay, collective agreements and insurers in Austria (§ 2 (5)); the
parties, place, work, dates and expected hours in Ireland (s. 3(3)); everything but pay, working time,
holidays, probation, training, ending and Social Security in Spain (art. 3.3); everything but letters h), i),
l), m), n), o) and r) in Italy (c. 5-bis); the contract's own terms in Poland.

When a collective agreement or award applies, name it and who made it; never restate its terms.

## What the check reads

| Rule | What it reads |
| --- | --- |
| EMPLOY-ITEMS | Every particular the statement's law lists is there or marked not applicable; the ones the law always asks for never are; the country's own details (Swedish employer contributions, the Finnish insurers, the Canadian overtime rules and rate, the UK disciplinary note, a Belgian fixed schedule's day, breaks and days off and the joint committee, the Austrian insurers, seat and where the collective agreements can be read, the Irish average-hourly-rate note, Spain's professional group, daily, weekly and annual working time, harassment protocol, Social Security body and a temporary contract's cause, Italy's contribution bodies, Poland's work regulations and working-time norm, breaks and rest) |
| EMPLOY-DATES | The start date; a fixed term ends after it starts; the statement is dated within the law's time (the first day in Belgium, a week in the Netherlands and Austria, five days in Ireland, before the start in Spain, seven days in Italy and Poland); an Australian fixed term over two years is flagged (s 333E) |
| EMPLOY-PROBATION | The probation states its length. Over six months it is flagged (Art. 8(1), LAS 6 §, aml. § 15-6, lov 501 § 6, TSL 1:4 §); in a fixed term over half of it in Norway and Finland, a quarter in Denmark. Belgium: any trial period is flagged (abolished 2014); the Netherlands: BW 7:652's none, one or two months; Austria: over one month; Ireland: over six months (s. 6D); Spain: over two months, or three in a company of under twenty-five workers, or six for a técnico titulado, as the statement says which, or one in a short temporary contract, unless it names the convenio colectivo that sets it (ET art. 14.1); Italy: over six months, or the fixed-term days of D.Lgs. 104/2022 art. 7; Poland: over three months (art. 25 § 2) |
| EMPLOY-PAY | The amount with its currency, how often and how it is paid; in Australia at least monthly. Spain and Italy: or a reference to the law or agreement that sets it; Poland: the amount and its components |
| EMPLOY-ABROAD | Work abroad over the threshold: the country, the period, the currency, the benefits, the return home (Denmark: the certificates), given before departure |
| EMPLOY-LANG | Every heading is in the statement's language |
| EMPLOY-REFERENCE | A particular the law will not let a statement give by pointing to a law or agreement states the term itself (Belgium: art. 5's items may point to the work rules) |
| EMPLOY-NO-TEMP, EMPLOY-FI-TEMP | A Norwegian or Finnish fixed term gives its length and its basis; in Finland since 1 June 2026 the basis may be that the term was made without a justified reason (TSL 1:3 § and 2:4 § as amended by 412/2026) |
| EMPLOY-NO-HOURS | Norway: the daily and weekly hours, when they fall, and the breaks |
| EMPLOY-US-ATWILL, -FLSA, -STATE, -WORDING | A US offer: at will or a set term (Montana flagged), the FLSA classification with its overtime rule, the New York or California notice items, and no claim of a federal duty |
| EMPLOY-AU-STATEMENTS | The information statements an Australian employee gets are named |
| EMPLOY-IE-CORE | Ireland's five-day core terms (s. 3(1A)): both full names, the employer's address, the hours expected per normal day and week, the overtime terms, the pay reference period |
| EMPLOY-SIGNED | A Dutch opgave is signed by the employer (BW 7:655 (3)); an Irish statement is signed and dated by or for the employer (s. 3(4), s. 3A) |
| EMPLOY-BE-LANG | A Belgian statement is in its region's language: Dutch in Flanders (decree of 19 July 1973), French in Wallonia (decree of 30 June 1982), either in Brussels |
| EMPLOY-AGREEMENT | The collective agreement is identified: in Spain by its code, the bulletin and date it was published in and its validity (art. 3.2 o)); in Italy by its signatories and, for a private employer, its CNEL code (art. 1 c. 1 q), q-bis)) |
| EMPLOY-PL-CONTRACT | A Polish statement repeats the contract's own terms (art. 29 § 1) as terms, never as pointers: the type of contract and the date it was concluded, the work, the place, the pay, the working time basis, the first day |
| LOCALE-PAPER | A4, or US Letter in the United States and Canada |

## Say what passed, not more

Tell the person which checks the statement passed and against which source. Never call it lawful,
compliant or approved, never call a term unlawful, and give no legal advice; suggest the employer
checks anything the check flags with an adviser.

## Sources

The official text of each law, as in force on 2026-10-20:

| Where | Law | Official text |
| --- | --- | --- |
| EU | Directive (EU) 2019/1152, Arts. 4, 5, 7, 8 | https://eur-lex.europa.eu/eli/dir/2019/1152/oj |
| United Kingdom | Employment Rights Act 1996, ss. 1 to 7B | https://www.legislation.gov.uk/ukpga/1996/18/part/I |
| Sweden | Lag (1982:80) om anställningsskydd, 6 c to 6 g §§ | https://www.riksdagen.se/sv/dokument-och-lagar/dokument/svensk-forfattningssamling/lag-198280-om-anstallningsskydd_sfs-1982-80/ |
| Norway | Arbeidsmiljøloven, §§ 14-5 to 14-6 and 15-6 | https://lovdata.no/lov/2005-06-17-62 |
| Denmark | Ansættelsesbevisloven (lov nr. 501 af 2023) | https://www.retsinformation.dk/eli/lta/2023/501 |
| Finland | Työsopimuslaki 55/2001, 2:4 §, as amended by 412/2026 | https://www.finlex.fi/fi/lainsaadanto/2001/55 |
| Canada | Canada Labour Code s. 253.2; Canada Labour Standards Regulations s. 3.1 | https://laws-lois.justice.gc.ca/eng/acts/L-2/section-253.2.html, https://laws-lois.justice.gc.ca/eng/regulations/C.R.C.,_c._986/ |
| Ontario | Employment Standards Act, 2000, O. Reg. 477/24 | https://www.ontario.ca/laws/regulation/r24477 |
| Australia | Fair Work Act 2009, ss. 125, 125B, 333E, 333K | https://www.legislation.gov.au/C2009A00028/latest/text |
| United States | 29 CFR part 541; New York Labor Law § 195; California Labor Code § 2810.5 | https://www.ecfr.gov/current/title-29/subtitle-B/chapter-V/subchapter-C/part-541, https://www.nysenate.gov/legislation/laws/LAB/195, https://leginfo.legislature.ca.gov/faces/codes_displaySection.xhtml?lawCode=LAB&sectionNum=2810.5 |
| Belgium | Loi du 7 octobre 2022 / Wet van 7 oktober 2022 | https://www.ejustice.just.fgov.be/eli/loi/2022/10/07/2022206298/justel |
| Netherlands | Burgerlijk Wetboek Boek 7, arts. 652 and 655 | https://wetten.overheid.nl/BWBR0005290 |
| Austria | AVRAG § 2 (Dienstzettel) | https://www.ris.bka.gv.at/eli/bgbl/1993/459/P2/NOR40260833 |
| Ireland | Terms of Employment (Information) Act 1994, revised | https://revisedacts.lawreform.ie/eli/1994/act/5/revised/en/html |
| Spain | Real Decreto 723/2026 (BOE-A-2026-19200); Estatuto de los Trabajadores arts. 8.5 and 14 | https://www.boe.es/buscar/act.php?id=BOE-A-2026-19200 |
| Italy | D.lgs. 26 maggio 1997, n. 152, as amended by d.lgs. 104/2022 | https://www.normattiva.it/uri-res/N2Ls?urn:nir:stato:decreto.legislativo:1997-05-26;152 |
| Poland | Kodeks pracy, art. 29 § 3 | https://isap.sejm.gov.pl/isap.nsf/DocDetails.xsp?id=WDU19740240141 |
