# OpenPaperwork Legal

an NDA, a DPA or a cloud service agreement drafted on Common Paper's standard terms, and the other side's agreement reviewed and handed back with tracked changes, each with a drafting check; not legal advice.

| Pack | What it is for |
| --- | --- |
| `skills/contract-drafting` | Agreements in Word |
| `skills/_checks`, `skills/_shared` | The check modules and shared code these packs import; not skills |

## Workflows

Start one by typing its command in Claude Code in the folder that holds your files, alone or with one
line after it. It runs in one go and hands back the file, then says what is still open for you.

| Workflow, started by its command | What you get | What to give it |
| --- | --- | --- |
| `/openpaperwork-legal:draft-agreement` | An NDA, DPA or cloud service agreement in Word on Common Paper's terms | Write one line: a mutual NDA with Example Ltd, Storgatan 12, 211 34 Malmö, under English law |
| `/openpaperwork-legal:review-agreement` | The other side's agreement back in Word with tracked changes | Drop their agreement and say which side you are on |

Install it in Claude Code with `/plugin install openpaperwork-legal@openpaperwork` after
`/plugin marketplace add`, or start Claude Code with `claude --plugin-dir` pointing at this folder.
Codex, Cursor, Copilot, Kiro and VS Code read `plugin.json` here (Agent Plugins 1.0.0). It needs
Python 3.10 or later with `pip install -r requirements.txt`; in Claude Code the plugin sets that
up itself, once, at the first session start. A clean run ends with `pack check clean`.

Every file here is a copy of `skills/` in the OpenPaperwork repository, built by
`python3 scripts/build-portable-pack.py`; change the source there, never here.
