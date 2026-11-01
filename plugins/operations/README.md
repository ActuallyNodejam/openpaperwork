# OpenPaperwork Operations

business letters for Germany and Sweden (DIN 5008), Norway, Denmark, Finland, the US, the UK, Canada, Australia, Belgium, the Netherlands, Austria, Ireland, Spain, Italy and Poland, meeting minutes and company board and general-meeting minutes for the same countries except Germany, and decisions read out of a WhatsApp export.

| Pack | What it is for |
| --- | --- |
| `skills/business-letter` | Any business letter (Brief, brev, lettre, carta) as PDF or Word, laid out for the sender's country (DIN 5008 and more), the address the way the post reads it |
| `skills/diagram` | A diagram as PDF, SVG and PNG |
| `skills/meeting-minutes` | Minutes of any meeting (Protokoll, protokoll, notulen, procès-verbal) as Word |
| `skills/whatsapp-export` | Read a WhatsApp chat the person exported (Export chat, .txt or .zip with media) to pull out decisions, dates, people and files |
| `skills/_checks`, `skills/_shared` | The check modules and shared code these packs import; not skills |

## Workflows

Start one by typing its command in Claude Code in the folder that holds your files, alone or with one
line after it. It runs in one go and hands back the file, then says what is still open for you.

| Workflow, started by its command | What you get | What to give it |
| --- | --- | --- |
| `/openpaperwork-operations:letter` | A business letter as PDF or Word, laid out for the sender's country | Say what the letter says and to whom, or drop your draft, or write one line: a thank-you letter to Example Ltd, Storgatan 12, 211 34 Malmö |
| `/openpaperwork-operations:diagram` | A diagram as PDF, SVG and PNG: a flow, an org chart, a timeline or a plan | Write one line: our order flow from request to invoice |
| `/openpaperwork-operations:minutes` | Minutes in Word with what the law asks to record for the meeting | Drop your notes from the meeting |

Install it in Claude Code with `/plugin install openpaperwork-operations@openpaperwork` after
`/plugin marketplace add`, or start Claude Code with `claude --plugin-dir` pointing at this folder.
Codex, Cursor, Copilot, Kiro and VS Code read `plugin.json` here (Agent Plugins 1.0.0). It needs
Python 3.10 or later with `pip install -r requirements.txt`; in Claude Code the plugin sets that
up itself, once, at the first session start. A clean run ends with `pack check clean`.

Every file here is a copy of `skills/` in the OpenPaperwork repository, built by
`python3 scripts/build-portable-pack.py`; change the source there, never here.
