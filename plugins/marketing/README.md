# OpenPaperwork Marketing

business decks handed back as a PDF, built to consulting structure, with an editable PowerPoint file with native charts and tables when asked, and fair and event posters made from a folder's own words and marks, each with its check.

| Pack | What it is for |
| --- | --- |
| `skills/business-deck` | Business deck, slides or presentation as a PDF, PowerPoint on ask |
| `skills/social-poster` | Trade-fair or event poster, Instagram square or story, thank-you or save-the-date card, and the caption, from a brand's own logo, photos and words |
| `skills/_checks`, `skills/_shared` | The check modules and shared code these packs import; not skills |

## Workflows

Start one by typing its command in Claude Code in the folder that holds your files, alone or with one
line after it. It runs in one go and hands back the file, then says what is still open for you.

| Workflow, started by its command | What you get | What to give it |
| --- | --- | --- |
| `/openpaperwork-marketing:deck` | A deck as PDF, and PowerPoint when you want it | Drop the material, or write one line: a board update for the third quarter |
| `/openpaperwork-marketing:poster` | A fair or event poster as PNG and PDF from your own logo, photos and words | Drop the logo and photos, or write one line: a poster for the Ystad Summer Fair, Stortorget, Ystad, 8 August 2026 |

Install it in Claude Code with `/plugin install openpaperwork-marketing@openpaperwork` after
`/plugin marketplace add`, or start Claude Code with `claude --plugin-dir` pointing at this folder.
Codex, Cursor, Copilot, Kiro and VS Code read `plugin.json` here (Agent Plugins 1.0.0). It needs
Python 3.10 or later with `pip install -r requirements.txt`; in Claude Code the plugin sets that
up itself, once, at the first session start. A clean run ends with `pack check clean`.

Every file here is a copy of `skills/` in the OpenPaperwork repository, built by
`python3 scripts/build-portable-pack.py`; change the source there, never here.
