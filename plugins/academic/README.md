# OpenPaperwork Academic

IEEE and ACM papers, reference lists in APA 7, IEEE and Vancouver style with their check, literature search and a Zotero library (the paper pack needs a TeX engine, tectonic, on PATH).

| Pack | What it is for |
| --- | --- |
| `skills/academic-references` | Citations and reference lists in APA 7 (default), IEEE or Vancouver |
| `skills/literature-search` | Find and read real research papers and back claims with them |
| `skills/paper` | Research paper, article, or conference or journal submission as a finished PDF in IEEE, ACM or the person's template; every reference looked up, never from memory |
| `skills/zotero-library` | Read the person's own Zotero library on this computer |
| `skills/_checks`, `skills/_shared` | The check modules and shared code these packs import; not skills |

## Workflows

Start one by typing its command in Claude Code in the folder that holds your files, alone or with one
line after it. It runs in one go and hands back the file, then says what is still open for you.

| Workflow, started by its command | What you get | What to give it |
| --- | --- | --- |
| `/openpaperwork-academic:references` | A reference list as a Word file in APA 7, IEEE or Vancouver, every entry checked | Drop the document or the list and say which style |
| `/openpaperwork-academic:paper` | A research paper as PDF in IEEE, ACM or your template, every reference looked up | Drop your draft and notes |

Install it in Claude Code with `/plugin install openpaperwork-academic@openpaperwork` after
`/plugin marketplace add`, or start Claude Code with `claude --plugin-dir` pointing at this folder.
Codex, Cursor, Copilot, Kiro and VS Code read `plugin.json` here (Agent Plugins 1.0.0). It needs
Python 3.10 or later with `pip install -r requirements.txt`; in Claude Code the plugin sets that
up itself, once, at the first session start. A clean run ends with `pack check clean`.

Every file here is a copy of `skills/` in the OpenPaperwork repository, built by
`python3 scripts/build-portable-pack.py`; change the source there, never here.
