# OpenPaperwork Finance

invoices and credit notes with the file each country takes (Factur-X / ZUGFeRD and XRechnung for Germany and France; Peppol BIS 3 for Norway, Denmark, Finland, the UK, Belgium, the Netherlands (or SI-UBL), Austria (or ebInterface) and Ireland; Facturae for Spain, FatturaPA for Italy, the KSeF invoice for Poland), tax invoices for Australia, Canada and the US, and a smaller Swedish company's annual report (K2), each with its scripted check.

| Pack | What it is for |
| --- | --- |
| `skills/annual-accounts` | Annual report (årsredovisning) of a smaller Swedish company under K2, as Word |
| `skills/e-invoice` | Any invoice or credit note (Rechnung, facture, faktura, factura) as PDF plus the XML its country takes |
| `skills/_checks`, `skills/_shared` | The check modules and shared code these packs import; not skills |

## Workflows

Start one by typing its command in Claude Code in the folder that holds your files, alone or with one
line after it. It runs in one go and hands back the file, then says what is still open for you.

| Workflow, started by its command | What you get | What to give it |
| --- | --- | --- |
| `/openpaperwork-finance:annual-report` | A K2 annual report in Word, added up and checked | Drop the trial balance or last year's annual report |
| `/openpaperwork-finance:invoice` | An invoice as PDF with the XML file the customer's country takes | Drop the order or your notes, or write one line: 12 hours of consulting at 85 euros an hour for Example Ltd, Storgatan 12, 211 34 Malmö |
| `/openpaperwork-finance:credit-note` | A credit note against an invoice, as PDF with its XML | Drop the invoice and say what to credit |

Install it in Claude Code with `/plugin install openpaperwork-finance@openpaperwork` after
`/plugin marketplace add`, or start Claude Code with `claude --plugin-dir` pointing at this folder.
Codex, Cursor, Copilot, Kiro and VS Code read `plugin.json` here (Agent Plugins 1.0.0). It needs
Python 3.10 or later with `pip install -r requirements.txt`; in Claude Code the plugin sets that
up itself, once, at the first session start. A clean run ends with `pack check clean`.

Every file here is a copy of `skills/` in the OpenPaperwork repository, built by
`python3 scripts/build-portable-pack.py`; change the source there, never here.
