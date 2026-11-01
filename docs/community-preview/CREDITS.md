# Foundations and references

The existing [third-party inventory](../../THIRD_PARTY.md), root LICENSE and
the notices in the repository remain authoritative for copied components. This page does
not replace those notices or clear the repository for release.

The agent foundation and every imported component are credited at their
recorded versions in the inventory. Community presentation takes cues from
[OpenWork](https://github.com/different-ai/openwork); focused contribution
guidance from [OpenDesign](https://github.com/nexu-io/open-design).

The standalone preview follows design ideas described by
[effective-html](https://github.com/plannotator/effective-html), including
subject-specific composition, readable labels and useful interaction. No
third-party skill, source code, font or image was copied into this preview.
The illustrations are authored here using the existing OpenPaperwork palette.

The README and its social preview take presentation ideas only from the README
header of [alphaXiv OpenResearch](https://github.com/alphaXiv/OpenResearch), the
README layout of [OpenWork](https://github.com/different-ai/openwork) and the hero
of [nodejam.com](https://nodejam.com). No text, code or image was copied from them;
the pictures are renders of this library's own outputs.

The case design references [GDPval](https://openai.com/index/gdpval/),
[SpreadsheetBench](https://github.com/RUCKBReasoning/SpreadsheetBench),
[PresentBench](https://github.com/PresentBench/PresentBench) and
[OfficeBench](https://github.com/zlwang-cs/OfficeBench). These are methodological
references; none of their datasets or results are included. Dataset rights must
be checked separately from repository-code licenses before any later reuse.

Cases are filed by sector using the
[North American Industry Classification System 2022](https://www.census.gov/naics/)
(U.S. Census Bureau) and by occupation using the
[O*NET-SOC 2019 taxonomy](https://www.onetcenter.org/taxonomy.html). This page and
the case files include information from the O*NET 31.0 Database by the U.S.
Department of Labor, Employment and Training Administration (USDOL/ETA). Used
under the [CC BY 4.0 license](https://creativecommons.org/licenses/by/4.0/).
Occupation codes and titles are unchanged in case.json; folder names shorten the
titles, and USDOL/ETA has not approved, endorsed or tested these modifications.
O*NET® is a trademark of USDOL/ETA.

The academic guideline pack carries the APA 7 and IEEE styles from the
[Citation Style Language styles repository](https://github.com/citation-style-language/styles)
(CC BY-SA 3.0, recorded in the [third-party inventory](../../THIRD_PARTY.md)).
Its rules paraphrase the *Publication Manual of the American Psychological
Association* (7th ed., 2020), the [APA Style](https://apastyle.apa.org/) pages
and the IEEE Reference Guide (version 11.29.2023); none of their text is copied
and neither organization endorses the pack. Thesis rules paraphrase the
University of Texas Rio Grande Valley Graduate College
[Thesis Formatting Guide](https://www.utrgv.edu/graduate/_files/documents/thesis-formatting-guide.pdf),
updated August 13, 2024; the guide is cited, not copied. The literature-search
and paper skills adapt the research skills in alphaXiv's
[OpenResearch](https://github.com/alphaXiv/openresearch-cli) (MIT); what was
taken is recorded in the [third-party inventory](../../THIRD_PARTY.md). Papers
are found through the open [OpenAlex](https://openalex.org/),
[PubMed](https://pubmed.ncbi.nlm.nih.gov/), [arXiv](https://arxiv.org/) and
[Crossref](https://www.crossref.org/) services; thank you to arXiv for use of
its open access interoperability. Paper layouts use the IEEEtran class by
Michael Shell, which the TeX engine supplies, and the acmart class by Boris
Veytsman, version 2.20 shipped unmodified beside the ACM starter (both LaTeX
Project Public License).

The e-invoice skill writes EN 16931 invoices in the UN/CEFACT Cross Industry
Invoice syntax used by Factur-X and ZUGFeRD. Its generator is written here from
the published semantic model; no standard text or third-party code is copied.
The library's checks validate its output with the
[Mustang project](https://github.com/ZUGFeRD/mustangproject) validator
(Apache-2.0), run as a separate, optional tool.

The trade paperwork pack takes its field lists from the
[OASIS Universal Business Language 2.1](https://docs.oasis-open.org/ubl/os-UBL-2.1/UBL-2.1.html)
document types and its delivery-term rule from how
[Incoterms 2020](https://iccwbo.org/business-solutions/incoterms-rules/incoterms-2020/) terms are written.
Incoterms is a trademark of the International Chamber of Commerce. Neither text is
copied and neither body endorses the pack.

The synthetic task material in this branch was created for this pack. It uses
invented organizations and people and contains no customer source material.
Its intended redistribution notice is alongside the cases; release approval
and the wider repository audit remain pending.

## Skills

- The WhatsApp export reader ports [whatsapp-chat-parser](https://github.com/Pustur/whatsapp-chat-parser) (MIT),
  with its notice in `THIRD_PARTY.md` and `licenses/`.

## README pictures

- The direction sketch is drawn with [rough.js](https://github.com/rough-stuff/rough) (MIT), the hand-drawn
  look Excalidraw uses. Only the picture is in this repository, not the library.
