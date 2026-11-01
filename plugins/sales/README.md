# OpenPaperwork Sales

quotations, order confirmations, delivery notes, pro forma invoices and purchase orders for Sweden, Norway, Denmark, Finland, Germany, Austria, the Netherlands, Belgium, France, Spain, Italy, Poland, the UK, Ireland, the US, Canada and Australia, each with the company details its own law asks for and a scripted check.

| Pack | What it is for |
| --- | --- |
| `skills/trade-documents` | Quote, offer, order confirmation, delivery note, pro forma or purchase order (Angebot, offert, devis, presupuesto) as Word, Excel or PDF, sums done by script |
| `skills/_checks`, `skills/_shared` | The check modules and shared code these packs import; not skills |

## Workflows

Start one by typing its command in Claude Code in the folder that holds your files, alone or with one
line after it. It runs in one go and hands back the file, then says what is still open for you.

| Workflow, started by its command | What you get | What to give it |
| --- | --- | --- |
| `/openpaperwork-sales:quotation` | A quotation in Word or PDF, the sums done by script | Drop the request or your price list, or write one line: 40 chairs at 289 kr a chair for Example Ltd, Storgatan 12, 211 34 Malmö |
| `/openpaperwork-sales:order-confirmation` | An order confirmation in Word or PDF with what you have agreed | Drop the order or the quotation |
| `/openpaperwork-sales:delivery-note` | A delivery note to put in the parcel | Drop the order and say what ships |
| `/openpaperwork-sales:proforma-invoice` | A pro forma invoice for prepayment or customs | Drop the quotation or the order |
| `/openpaperwork-sales:purchase-order` | A purchase order to your supplier | Drop the supplier's quote, or write one line: 200 boxes at 1,150 kr a box from Example Ltd, Storgatan 12, 211 34 Malmö |

Install it in Claude Code with `/plugin install openpaperwork-sales@openpaperwork` after
`/plugin marketplace add`, or start Claude Code with `claude --plugin-dir` pointing at this folder.
Codex, Cursor, Copilot, Kiro and VS Code read `plugin.json` here (Agent Plugins 1.0.0). It needs
Python 3.10 or later with `pip install -r requirements.txt`; in Claude Code the plugin sets that
up itself, once, at the first session start. A clean run ends with `pack check clean`.

Every file here is a copy of `skills/` in the OpenPaperwork repository, built by
`python3 scripts/build-portable-pack.py`; change the source there, never here.
