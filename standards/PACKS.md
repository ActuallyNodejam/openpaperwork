# Guideline packs

A pack is a guideline set under `guidelines/<issuer>/<version>/`, the scripts
in `checks/` that verify its rules, the tasks that cite it, and the starter
files a skill ships so the layout is decided before the model writes a word.
Sources and their licences are in [SOURCES.md](SOURCES.md).

### Finance

| Pack | Guideline set | Checks | Starter files |
| --- | --- | --- | --- |
| EU invoices | `cen-en16931/2017`, `factur-x/1.0`, `kosit-xrechnung/3.0` | `einvoice.py` (parties, lines, VAT breakdown, totals; Mustang EN 16931 validator), `einvoice_page.py` (the page; `EINV-FACTURX` the XML inside the PDF, `EINV-PDFA` veraPDF, `EINV-KOSIT` the KoSIT validator) | `e-invoice/scripts/einvoice_create.py`, `e-invoice/templates/invoice-spec.json` |
| Nordic invoices (Norway, Denmark, Finland) | `no-bokforingsforskriften/2026`, `dk-momsbekendtgorelsen/2026`, `fi-arvonlisaverolaki/2026`, `peppol-bis-billing/3.0`, `finvoice/3.0` | `einvoice_country.py` (`NO-SELLER`, `NO-CONTENT`, `DK-INVOICE`, `FI-INVOICE`, `FI-PAYMENT`: org.nr. with MVA and Foretaksregisteret, delivery time and place, VAT in NOK, CVR, Y-tunnus, viitenumero and bank barcode), `credit_note_check.py` on the UBL credit note, `EINV-PEPPOL` (the official Peppol BIS 3.0 rules with NO-R and DK-R), `EINV-FINVOICE` (the Finvoice 3.0 schema) | `e-invoice/templates/no-faktura-spec.json`, `no-kreditnota`, `dk-faktura`, `dk-kreditnota`, `fi-lasku`, `fi-hyvityslasku`, `fi-finvoice`; Peppol UBL or Finvoice beside the page from `e-invoice/page/build_page.py` |
| English-speaking invoices (UK, Australia, Canada, US) | `uk-vat-notice-700-21/2024`, `au-gst-tax-invoice/2019`, `ca-gst-hst-itc/2026`, `us-sales-tax-invoice/2026`, `peppol-bis-billing/3.0` | `einvoice_country.py` (`UK-VAT-INVOICE`, `AU-TAX-INVOICE`, `CA-GST-HST`, `US-SALES-TAX`), `EINV-PEPPOL` for the UK's UBL | `e-invoice/templates/uk-vat-invoice-spec.json`, `uk-credit-note`, `au-tax-invoice`, `au-adjustment-note`, `ca-invoice`, `ca-facture`, `ca-credit-note`, `us-invoice`, `us-credit-memo`; Letter paper in Canada and the US |
| Belgian, Dutch, Austrian and Irish invoices | `be-royal-decree-no-1/2026`, `nl-wet-ob/2026`, `at-ustg/2026`, `ie-vat-invoice/2026`, `peppol-bis-billing/3.0`, `si-ubl/2.0`, `ebinterface/6.1` | `einvoice_country.py` (`BE-INVOICE`, `NL-INVOICE`, `AT-INVOICE`, `IE-VAT-INVOICE`: the enterprise number and structured communication (modulus 97), the btw-id and KvK number, the UID-Nummer's check digit and the recipient's UID over 10 000 euros, the Irish VAT number, the reverse-charge mention each law fixes or leaves open), `credit_note_check.py` on the UBL credit note, `EINV-PEPPOL` (release 3.0.21 with NL-R), `EINV-SI-UBL` (the NLCIUS rules), `EINV-EBINTERFACE` (the ebInterface 6.1 schema) | `e-invoice/templates/be-factuur-spec.json`, `be-facture`, `be-creditnota`, `nl-factuur`, `nl-creditnota`, `nl-si-ubl`, `at-rechnung`, `at-rechnungskorrektur`, `at-ebinterface`, `ie-vat-invoice`, `ie-credit-note`; Peppol UBL, SI-UBL or ebInterface beside the page from `e-invoice/page/build_page.py` |
| Spanish, Italian and Polish invoices | `es-reglamento-facturacion/2026`, `it-dpr-633/2026`, `pl-ustawa-vat/2026`, `facturae/3.2.2`, `fatturapa/1.2.3`, `ksef-fa/3` | `einvoice_country.py` (`ES-INVOICE`, `IT-INVOICE`, `PL-INVOICE`: the NIF and the series, a rectifying invoice's own series; the partita IVA or codice fiscale, the annotation in place of the tax; the NIP, the tax in złoty, a correcting invoice's KSeF number; the reverse-charge and split-payment words each law fixes), `EINV-FACTURAE`, `EINV-FATTURAPA`, `EINV-KSEF` (each state's own schema) | `e-invoice/templates/es-factura-spec.json`, `es-factura-rectificativa`, `it-fattura`, `it-nota-di-credito`, `pl-faktura`, `pl-faktura-korygujaca`; Facturae (unsigned), FatturaPA or FA(3) beside the page from `e-invoice/page/build_page.py`, none of them sent |
| French invoices | `fr-cgi-invoice/2026-09`, `fnfe-france-rfe/1.4.0` | `fr_invoice_check.py` (`FR-SELLER`, `FR-BUYER`, `FR-PAYMENT`, `FR-MENTIONS`: SIREN, legal form, capital, RCS, the buyer's SIREN, penalties, the 40 euro indemnity, discount, nature of the operation, VAT on debits, delivery address, Autoliquidation), `EINV-FR-CTC` (the KoSIT validator with the FNFE-MPE BR-FR rules) | `e-invoice/templates/facture-spec.json`, `facture-avoir-spec.json`; the Factur-X PDF from `e-invoice/page/build_page.py` |
| A company's own particulars on its invoice | `invoice-company-particulars/2026-10` | `einvoice_particulars.py`, run as `einvoice_page.py` `EINV-PARTICULARS`: the register and number, the seat, the legal form, the share capital and liquidation by the seller's own company statute (France, Belgium, the Netherlands, Spain, Italy, Sweden, Norway, Denmark, Australia; the registered name in the UK, Ireland and Canada; nothing where the statute names letters only: Germany, Austria, Poland, Finland). A missing one fails, one the order lists as `unknown` warns, one the person's files give and the page drops fails | every `e-invoice/templates/*-spec.json`; `e-invoice/page/build_page.py` prints nothing for a particular declared unknown and warns |
| Money as printed | `printed-money/2026-10` | `money_check.py`: `EINV-SUMS` (an invoice page adds up as printed, for every country), `TRADE-SUMS` (a quotation, an order confirmation and a pro forma invoice, with the purchase order's own calculator), `EINV-RATE` and `TRADE-RATE` (a VAT rate is one the seller's country has; a rate written as a fraction fails) | `skills/_checks/tax_rates.json`: 15 countries, each with its source and the day it was read |
| Annual accounts | `arsredovisningslagen/1995-1554`, `eu-accounting-directive/2013-34`, `bfn-k2/2016-10` | `annual_accounts_check.py` (the `ANNUAL-` rules: the parts in their order, each part on a page of its own, the unit, last year's figures, every sum, the balance, the year's result alike in every statement, the changes in equity, the disposition, the notes, the signatures) | `skills/annual-accounts/templates/annual-report-cleaning.spec.json`, `arsredovisning-konsult.spec.json`, built by `annual_create.py` |

### Sales

| Pack | Guideline set | Checks | Starter files |
| --- | --- | --- | --- |
| Trade documents | `oasis-ubl/2.1`, `icc-incoterms/2020`, `letter-layouts/2026-10`, `din-5008/2020`, `eu-company-law/2017-1132`, `company-mentions/2026-10`, `trade-locales/2026-10` | `purchase_order_check.py` (`TRADE-PO-` rules; `TRADE-LANG`, every label in the document's language; `TRADE-WINDOW`, the address in the envelope window of the country the document is sent from, as its invoice and letter have it; `TRADE-BLOCK`, the information block on the text's right edge or before a window on the right), `letter_check.py` (`LETTER-DIN5008` where the sender's country has no layout of its own, `LETTER-COMPANY`), `locale_floor.py` (paper, dates, numbers for PDF, Word and Excel) | `trade-documents/scripts/trade_create.py`, `templates/*.spec.json` (Swedish, Danish, Norwegian, Finnish, US, Canadian English and French, Australian, Dutch, Belgian Dutch and French, Austrian, Irish, Spanish, Italian, Polish), `skills/_checks/trade_words.json` |

### Legal

| Pack | Guideline set | Checks | Starter files |
| --- | --- | --- | --- |
| Agreements | `common-paper/2026-10`, `mike-workflows/ce62e6a2d3f4`, `gdpr/2016-679`, `house-drafting/1` | `legal_check.py` (drafting: parties, date, terms, cross-references, law, signatures, NDA elements, GDPR Art. 28(3); review: one verdict per checklist item, quotes found in their document, no verdict on the whole; redline: tracked changes, the original untouched) | `contract-drafting/scripts/agreement_create.py`, `review_create.py`, `redline_create.py`, `templates/*.json`, `standards/`, `checklists/` |

### HR

| Pack | Guideline set | Checks | Starter files |
| --- | --- | --- | --- |
| Employment statements | `eu-working-conditions/2019-1152`, `uk-employment-rights-act/1996`, `anstallningsskyddslagen/1982-80`, `arbeidsmiljoloven/2024-07`, `ansaettelsesbevisloven/2023-501`, `tyosopimuslaki/2001-55`, `canada-labour-code/2026`, `ontario-esa/2025-07`, `us-employment-offer/2026-10`, `fair-work-act/2009`, `be-working-conditions/2022-10-07`, `bw-7-655/2026-07`, `avrag/2024-03`, `ie-terms-of-employment/2022-12`, `es-working-conditions/2026-09`, `it-dlgs-152-1997/2026-06`, `kodeks-pracy/2026-08` | `employment_check.py` (`EMPLOY-ITEMS`, `-DATES`, `-PROBATION`, `-PAY`, `-ABROAD` per law; `-LANG`, `-REFERENCE`; Norway `-NO-TEMP`, `-NO-HOURS`; Finland `-FI-TEMP`; the US `-US-ATWILL`, `-US-FLSA`, `-US-STATE`, `-US-WORDING`; Australia `-AU-STATEMENTS`; Ireland `-IE-CORE`; the Netherlands and Ireland `-SIGNED`; Belgium `-BE-LANG`; Spain and Italy `-AGREEMENT`; Poland `-PL-CONTRACT`), `locale_floor.py` (`LOCALE-PAPER`) | `employment-statement/scripts/statement_create.py`, `templates/*.spec.json` (UK, EU, Sweden, Norway, Denmark, Finland, Canada in English and French, Ontario, Australia, New York and California offer letters, Belgium in Dutch and French, the Netherlands, Austria, Ireland, Spain, Italy, Poland) |

### Operations

| Pack | Guideline set | Checks | Starter files |
| --- | --- | --- | --- |
| Business letters | `din-5008/2020`, `letter-layouts/2026-10`, `eu-company-law/2017-1132`, `company-mentions/2026-10`, `es-company-law/2026`, `it-codice-civile/2026`, `pl-ksh/2026` | `letter_check.py` (DIN 5008 or the envelope window, the postal address, the date, the salutation and closing, one language, a Finnish letter's page numbers, the parts, company details) | `business-letter/scripts/letter_create.py`, `window_letter.py`, templates for DE/SE, NO, DK, FI, US, UK, CA (en, fr), AU, BE (nl, fr), NL, AT, IE, ES, IT, PL |
| Meeting minutes | `roberts-rules/1915`, `aktiebolagslagen/2005-551`, `aksjeloven/1997-44`, `selskabsloven/2025-331`, `osakeyhtiolaki/2006-624`, `uk-companies-act/2006`, `dgcl/title-8`, `cbca/1985-c44`, `au-corporations-act/2001`, `be-companies-code/2019`, `bw-2/2026-07`, `at-company-law/2026`, `ie-companies-act/2014`, `es-company-law/2026`, `it-codice-civile/2026`, `pl-ksh/2026` | `minutes_check.py` (head, officers, motions, times, signatures and contents per statute, one language) | `meeting-minutes/scripts/minutes_create.py`, twenty-nine templates |

### Marketing

| Pack | Guideline set | Checks | Starter files |
| --- | --- | --- | --- |
| Business decks | `business-deck/2026-10` | `business_deck.py` (the `BDECK-` rules: a message as every title, one exhibit a page, the storyline, next steps, sources, no placeholder, the chart head, direct labels, honest charts, a chart that earns its place, one highlight, tables as tall as their rows, text fit, fill, words, type, contrast, the grid, the file's accessibility basics, and a rule each for a 2x2 matrix, a figure, a quote and an appendix with backup pages; every bound read from the deck's density preset; a PDF is read from the description its builder writes into it and measured on its printed pages) | `business-deck/scripts/deck_build.py`, `business-deck/scripts/deck_html.py`, `business-deck/templates/board-update.deck.json`, `business-deck/templates/proposal.deck.json`, `business-deck/look.json`, `business-deck/density.json` |
| Fair poster | None: its own fixed layout, no published standard | `skills/social-poster/check.py` (the canvas, every slot inside the page and filled, the right marks, the colour asked for, the loop closed, house fonts only, the PDF really printed), run by the skill in the turn; the pack declares no `check` in its `pack.json`, so the app's own pack check does not run it | `skills/social-poster/poster.html`, `agenda.html`, built by `poster.py`, `agenda.py` |

### Engineering

| Pack | Guideline set | Checks | Starter files |
| --- | --- | --- | --- |
| Requirements specifications | `nasa-seh/sp-2016-6105-rev2`, `iso-iec-directives-2/2021` | `requirements_check.py` (`REQ-ID`, `REQ-VERB`, `REQ-ONE`, `REQ-VAGUE`, `REQ-NEGATIVE`, `REQ-TBD`, `REQ-VERIFY`) | `skills/requirements-spec/templates/requirements.spec.json`, `kravspecifikation.spec.json`, built by `requirements_create.py` |
| SI units | `bipm-si/9-v4.01`, `nist-sp811/2008` | `requirements_check.py` (`UNITS-SPACE`, `UNITS-SYMBOL`), run with the requirements pack | None: a rule set the requirements pack carries |

### Academic

| Pack | Guideline set | Checks | Starter files |
| --- | --- | --- | --- |
| Grant proposals | `ec-horizon-europe/ria-ia-5.1` | `proposal.py` (A4 and margins, 11 point text, spacing, section order) and a 40 page limit | `docx/templates/horizon-europe-partb.spec.json` |
| Academic writing | `apa/7`, `ieee/2025-03-28`, `nlm-citing-medicine/2`, `icmje/2026-01`, `utrgv/2024-08-13`, `ieee-conference/1.8b`, `acm-sigconf/2.20` | `refcheck.py`, `papercheck.py` | `academic-references`, `literature-search` and `paper` skills |

### Formats

| Pack | Guideline set | Checks | Starter files |
| --- | --- | --- | --- |
| Decks with a brand kit | `openpaperwork/0.3.0` KIT rules | `brandkit.py` (ratio, fonts, palette, words, minimum size, footer, title, bounds, nothing decorative) | `powerpoint/scripts/pptx_from_kit.py` |
| Every file | `every-file/1.1.0`, inherited by every Office task | `floor.py` (fonts, overflow, contrast, formulas, title and alternative text, text hidden behind a picture), `pdfua.py` (PDF/UA-1 through veraPDF) | title defaults in the create scripts, `office_properties.py`, `docx/templates/standard.docx`, `powerpoint/templates/standard-16x9.pptx` |
| Every builder and page | `house-honest/1`, house rules and defect checks | `spec_guard.py` in `skills/_shared/` (an unknown key and a value of another shape stop the build by name; nothing given is left off the page; an output path inside the library's own folder is refused), `company.py` and `company_check.py` (`company.json`, a company's particulars written once: every builder fills its sender from it, and a page that says something else fails), `letter.py` in `skills/_shared/` (`own_address`: a company's own address is written one way in the footer of its letter, its invoice and its trade document), `thin_pages.py` (no heading with nothing under it, a letter with a body, an address a postman can deliver to), `notes_floor.py` (a question, never a fail: the hard tokens the person's notes hold and the page does not, a token the page changes, a figure the page carries and the notes do not), `packcheck.py` (a rule about fit, a window or fill ends with what may change and never invites changing a fact) | `spec.fields.json` in each pack: every key its builder reads, and the place for a fact with no field of its own; `skills/_shared/company.fields.json` |
| Spreadsheets | `uk-analysis-function/2021`, `fast-standard/02c` | `sheet_check.py` (`SHEET-MERGED`, `SHEET-HIDDEN`, `SHEET-EMPTY`, `SHEET-HEADINGS`, `SHEET-NUMBERS`, `SHEET-LINKS`, `SHEET-VOLATILE`, `SHEET-HARDCODED`; a customer's own form is exempt from the merged, headings and hard-coded rules) | `skills/xlsx/scripts/xlsx_create.py` |

## Known limits

LibreOffice cannot export an accessible PDF from a spreadsheet, leaves slide
content untagged and drops chart alternative text. `checks/pdfua.py` leaves
those findings out and says so, and `floor.py` checks alternative text in the
file itself. The validators (veraPDF, Mustang) are separate tools run from
containers; a criterion that needs one is skipped when it is absent.

The invoice pack covers the EN 16931 semantic model in the Cross Industry
Invoice syntax, handed back as a Factur-X / ZUGFeRD 2 PDF/A-3 with the XML
inside, with the French mentions for a French seller and XRechnung for a German
public buyer; Peppol BIS Billing 3.0 in UBL for Norway (EHF), Denmark, Finland, the UK,
Belgium, the Netherlands, Austria and Ireland, SI-UBL 2.0 for the Netherlands, ebInterface 6.1
for Austria, Finvoice 3.0 for Finland, and the page alone for Australia, Canada and the
United States, where EN 16931 does not apply (the US has no invoice standard; its
page is conventions, and says so). Danish OIOUBL 2.1, Peppol PINT (Australia and New
Zealand, and the Peppol network's coming PINT profiles), XRechnung in UBL, the
Factur-X EXTENDED and EXTENDED-CTC-FR profiles, self-billing and the French e-reporting
flows are not covered yet, and nothing here sends an invoice through a French
plateforme agréée or the Peppol network. The Peppol rules are fetched and run untouched,
never copied (OpenPeppol allows no redistribution). The
validators (KoSIT, veraPDF, Mustang) run as separate programs; a criterion that
needs one is skipped when it is absent.
