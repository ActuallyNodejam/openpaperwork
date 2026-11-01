# OpenPaperwork Formats

Word, Excel, PowerPoint and PDF files, decks from a brand kit, and the floor every document, workbook and deck should pass (no cut-off text, no formula errors), with the same check as an MCP tool.

| Pack | What it is for |
| --- | --- |
| `skills/docx` | Word .docx files |
| `skills/every-file` | The floor every Word, Excel or PowerPoint file must pass before it is delivered, whatever the task |
| `skills/pdf` | PDF files |
| `skills/powerpoint` | Read or change an existing .pptx, or fill a company's own .pptx template |
| `skills/xlsx` | Excel .xlsx workbooks and CSVs |
| `skills/brand-kit-deck` | Build or revise a PowerPoint deck that follows a brand kit (fonts, palette, limits, footer), for example a kit.json file |
| `skills/_checks`, `skills/_shared` | The check modules and shared code these packs import; not skills |

## Workflows

Start one by typing its command in Claude Code in the folder that holds your files, alone or with one
line after it. It runs in one go and hands back the file, then says what is still open for you.

| Workflow, started by its command | What you get | What to give it |
| --- | --- | --- |
| `/openpaperwork-formats:fill-template` | Your own Word template filled in, its layout kept | Drop the template and what goes in it |
| `/openpaperwork-formats:brand-deck` | A PowerPoint deck that follows your brand kit | Drop the brand kit and your material |

Install it in Claude Code with `/plugin install openpaperwork-formats@openpaperwork` after
`/plugin marketplace add`, or start Claude Code with `claude --plugin-dir` pointing at this folder.
Codex, Cursor, Copilot, Kiro and VS Code read `plugin.json` here (Agent Plugins 1.0.0). It needs
Python 3.10 or later with `pip install -r requirements.txt`; in Claude Code the plugin sets that
up itself, once, at the first session start. A clean run ends with `pack check clean`.

Every file here is a copy of `skills/` in the OpenPaperwork repository, built by
`python3 scripts/build-portable-pack.py`; change the source there, never here.
