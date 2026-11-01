# House conventions, and what was tried for sources

Five academic rules are checked as house conventions rather than as APA or IEEE conformance, because
no official source could be read for them today:

| Rule | Guideline | What was tried | Status |
| --- | --- | --- | --- |
| PAPER-FONTS | ieee-conference/1.8b | https://apastyle.apa.org/style-grammar-guidelines/paper-format/student-papers (wrong body for it, fetched as the nearest APA page) | HTTP 200, no readable text returned |
| PAPER-CITE-COVER | ieee-conference/1.8b | web search for the IEEE author center template and its PDF guide | only third-party templates surfaced, none read |
| PAPER-REF-RECORD | ieee-conference/1.8b | none; a reference made up from memory is the failure it stops (agent run 8, 2026-10-14) | the registries' own records (Crossref, OpenAlex, arXiv) |
| PAPER-CLAIM-CITE | ieee-conference/1.8b | none; an uncited claim about other models ("models like GPT-3.5 ... often violate") is the failure it stops (agent run 8, 2026-10-14) | academic citation practice: a claim about others' work names its source |
| APA-NO-INTRO | apa/7 | the APA student-paper page above | HTTP 200, no readable text returned |
| APA-REFS-NEW-PAGE | apa/7 | same page, plus a search for the APA reference-list page | third-party checklists only, none read |
| APA-REF-CITED | apa/7 | same | same |

To make these sourced, the pages to read are apastyle.apa.org (paper format and reference list) and
the IEEE author center conference template with its PDF guide; the fetch above returned no text, so
the next attempt should use a route that returns the page body, and only then is a citation written.
