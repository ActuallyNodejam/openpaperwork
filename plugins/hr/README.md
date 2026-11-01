# OpenPaperwork HR

the written terms of employment for the EU, the UK, Ireland, Sweden, Norway, Denmark, Finland, Belgium, the Netherlands, Austria, Spain, Italy, Poland, Canada, Ontario and Australia, and a US offer letter, with a check of every item the law asks for; not legal advice.

| Pack | What it is for |
| --- | --- |
| `skills/employment-statement` | Written terms of employment for a new hire, as Word |
| `skills/_checks`, `skills/_shared` | The check modules and shared code these packs import; not skills |

## Workflows

Start one by typing its command in Claude Code in the folder that holds your files, alone or with one
line after it. It runs in one go and hands back the file, then says what is still open for you.

| Workflow, started by its command | What you get | What to give it |
| --- | --- | --- |
| `/openpaperwork-hr:employment-terms` | Written terms of employment in Word with everything the law asks for | Write one line: Sam Lee starts on 1 March as a designer in Leeds, 3,400 pounds a month |

Install it in Claude Code with `/plugin install openpaperwork-hr@openpaperwork` after
`/plugin marketplace add`, or start Claude Code with `claude --plugin-dir` pointing at this folder.
Codex, Cursor, Copilot, Kiro and VS Code read `plugin.json` here (Agent Plugins 1.0.0). It needs
Python 3.10 or later with `pip install -r requirements.txt`; in Claude Code the plugin sets that
up itself, once, at the first session start. A clean run ends with `pack check clean`.

Every file here is a copy of `skills/` in the OpenPaperwork repository, built by
`python3 scripts/build-portable-pack.py`; change the source there, never here.
