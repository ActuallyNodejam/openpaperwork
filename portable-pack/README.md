# OpenPaperwork packs for your agent

The whole OpenPaperwork library as one plugin, `openpaperwork`, for the Claude app, Claude
Code, Codex, Cursor, Antigravity and other agents that read skills. Each pack is a skill with its scripts; a pack that makes a file has a check
script beside it that runs on the finished file and names what fails. To install one department only
(finance, sales, legal, HR, operations, marketing, engineering, academic or
formats), use its plugin in [`../plugins`](../plugins).

| Department | Packs |
| --- | --- |
| Finance | `e-invoice`: EN 16931 e-invoices and credit notes, Factur-X / ZUGFeRD and XRechnung for Germany and France, Peppol BIS 3 for Norway (EHF), Denmark, Finland (and Finvoice) and the UK, tax invoices for Australia, Canada and the US; `annual-accounts`: the K2 annual report of a smaller Swedish company, not accounting advice |
| Sales | `trade-documents`: quotations, order confirmations, delivery notes, pro forma invoices and purchase orders for Sweden, Norway, Denmark, Finland, Germany, the UK, the US, Canada and Australia |
| Legal | `contract-drafting`: an NDA, a DPA or a cloud service agreement on Common Paper's standard terms, a review item by item, their Word file back with tracked changes; not legal advice |
| HR | `employment-statement`: the written terms of employment for the EU, the UK, Sweden, Norway, Denmark, Finland, Canada, Ontario and Australia, and a US offer letter; not legal advice |
| Operations | `business-letter`: letters for Germany and Sweden (DIN 5008), Norway, Denmark, Finland, the US, the UK, Canada and Australia; `meeting-minutes`: minutes on Robert's Rules and company board and general-meeting minutes for the same countries; `whatsapp-export` |
| Marketing | `html-deck`: business decks as HTML and PDF; `social-poster`: fair and event posters |
| Engineering | `requirements-spec`: ids, shall and SI units |
| Academic | `academic-references`: APA 7, IEEE and Vancouver; `literature-search`; `paper`: IEEE and ACM papers, with `tectonic` on PATH; `zotero-library` |
| Formats | `docx`, `xlsx`, `powerpoint`, `pdf`; `every-file`: the floor every Word, Excel or PowerPoint file should pass; `brand-kit-deck`: a deck from a brand kit file |

| Part | What it is |
| --- | --- |
| `skills/_checks`, `skills/_shared` | The check modules and the shared code the packs import; not skills |
| `skills/_checks/packcheck.py`, `skills/*/scripts/check_file.py` | The checks, run from a shell |
| `mcp/server.py` | Optional. The floor check as one MCP tool, `check_file` |
| `hooks/hooks.json`, `hooks/pack_stop.py` | In Claude Code a check runs at the end of a turn: a Stop hook runs the pack check over the files the turn wrote, and a fail goes back to the agent, three times at most |
| `hooks/first_use.py` | In Claude Code the plugin's own Python, set up once at the first session start: requirements.txt and Chromium into the plugin's data folder (CLAUDE_PLUGIN_DATA), skipped when the version marker matches |
| `hooks/pack_agents.py` | The same rule for Codex, Gemini CLI and Cursor CLI, in each one's own hook format |
| `hooks/pack_route.py`, `hooks/routes.json` | A hint when the ask arrives: when it names a kind of file a pack here makes (an invoice, minutes, a quotation, in eleven languages), one line says which skill to load. The table is built from the `asks` list in each pack's `pack.json` |
| `.claude-plugin/plugin.json`, `plugin.json`, `mcp.json` | The Claude Code and Agent Plugins 1.0.0 manifests |
| `install.sh`, `install.py` | Links every pack into `~/.agents/skills` and writes the hook into the agents found on the machine; `install.py doctor` says what is in place, `install.py uninstall` takes it out |

## Where a check runs by itself

| Agent | At the end of a turn | Run for real |
| --- | --- | --- |
| Claude Code | A check runs by itself, from the plugin | 2026-10-09 |
| Codex | A check runs by itself after `install.sh`, once you have trusted the hook with `/hooks` | 2026-10-10, Codex 0.154.0: the fails went back and the turn ended on a clean check |
| Gemini CLI | A check runs by itself after `install.sh`, in a folder Gemini CLI trusts | 2026-10-10, Gemini CLI 0.63.0: the fails went back; the key's daily quota ended the run before the file was rebuilt |
| Cursor CLI | The hook is built from Cursor's documented format and has not run; `install.py --agents cursor` adds it. Until it has run, the agent runs the check on the pack's instruction | Not run |
| Copilot, Kiro, VS Code | The agent runs the check on the pack's instruction | |

A fail goes back to the agent in the same chat, three tries at most. Said once a turn and never again:
a check's question (a `WARN` line, which the agent answers in its reply or acts on), a check that could
run no rule (the file is then neither passed nor failed, and the reply says so) and a file the turn made
beside the pack instead of in your folder.

Inside the OpenPaperwork app these hooks stand down. The app runs the pack check itself at the end of a
turn, and it tells the agent it starts by setting `OPENPAPERWORK_APP=1`; a hook that sees it does nothing,
so a fault goes back to the agent once and not twice.

What each maker's hook can and
cannot do: [Bring your own agent](../docs/community-preview/BRING_YOUR_OWN_AGENT.md#the-check-when-you-use-an-agent-on-its-own).

## Where the hint comes by itself

An agent's list of skills is short of room, and a pack may stand in it as a bare name. So when an ask
names a kind of file a pack makes, one line is added to the turn: "If this ask is for an invoice, load
the e-invoice skill before writing anything: it lays the file out and checks it. Hand back a file, not
text in the chat." It is worked out from the ask's words by a table, with no model call and no network,
and an ask that names no such file gets nothing. If the file is then made without the pack all the
same, the agent is sent back once to build it with the pack.

| Agent | When the ask arrives |
| --- | --- |
| Claude Code | The hint comes by itself, from the plugin (`UserPromptSubmit`) |
| Codex | The hint comes by itself after `install.sh`, once you have trusted the hook with `/hooks`. The Codex desktop app runs a plugin's hooks only when you installed the plugin by hand, and shows a "Review hooks" dialog first |
| Gemini CLI | The hint comes by itself after `install.sh`, in a folder Gemini CLI trusts (`BeforeAgent`) |
| Cursor CLI | No hint: Cursor's prompt hook can let a prompt through or stop it, and cannot add to a turn. The send-back at the end of the turn is built with the hook |
| Copilot, Kiro, VS Code | No hint: the skill's own description is all the agent has |
| The OpenPaperwork app | The app adds the line itself for whichever agent it starts, and an installed hook stands down there (the app sets `OPENPAPERWORK_APP`), so it comes once |

How to load it: [docs/community-preview/PORTABLE_PACK.md](../docs/community-preview/PORTABLE_PACK.md).

It needs Python 3.10 or later with `pip install -r requirements.txt`, and
LibreOffice for recalculating workbooks.

## What is not here

The PDF/UA rule of the floor needs veraPDF.

## Where the files come from

Everything under `skills/` except the every-file and brand-kit-deck skill files,
and `mcp/checks/`, are copies of files elsewhere in this repository, so the
folder works when copied out on its own. `python3 scripts/build-portable-pack.py`
refreshes them and the department plugins, and `--check` fails when a copy has
drifted.

## Credits

The slide overflow estimate, the dark-on-dark rule, the hidden-text rule and
the formula issue types in `mcp/checks/floor.py` are ported from OfficeCLI
(Apache-2.0, Copyright 2026 OfficeCLI). See `NOTICE` and
`licenses/officecli-apache-2.0.txt`.
