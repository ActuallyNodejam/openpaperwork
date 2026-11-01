# Use the packs in your agent

OpenPaperwork's packs are the rules and scripts that make a file come out
right. They work on their own inside Claude, ChatGPT, Cursor and Antigravity,
and in Claude Code, Codex, Gemini CLI and Copilot, for people who already use
those agents.

The library ships as one marketplace with a plugin per department, so you
install only the work you do, or everything at once:

| Plugin | Packs | For |
| --- | --- | --- |
| `openpaperwork-finance` | `e-invoice`, `annual-accounts` | EN 16931 e-invoices and credit notes as Factur-X / ZUGFeRD PDFs: France (facture, facture d'avoir, the reform's mentions), Germany (ZUGFeRD, XRechnung); Peppol BIS 3 invoices and credit notes for Norway (EHF), Denmark, Finland (and Finvoice), the UK, Belgium (Dutch, French and German), the Netherlands (and SI-UBL 2.0), Austria (and ebInterface) and Ireland; the national files of Spain (Facturae 3.2.2, unsigned), Italy (FatturaPA) and Poland (the KSeF structure FA(3)), each beside its page and none of them sent; tax invoices for Australia, Canada (English and French) and the US; on each, the particulars the seller's own company statute puts on an invoice, with a missing one failing the check; annual accounts (Sweden, K2) |
| `openpaperwork-sales` | `trade-documents` | Quotations, order confirmations, delivery notes, pro forma invoices, purchase orders: Sweden, Denmark, Norway, Finland, Germany, Austria, the Netherlands, Belgium (Dutch and French), Spain, Italy, Poland, the UK, Ireland, the US, Canada (English and French), Australia, each with the company details its own law asks for |
| `openpaperwork-legal` | `contract-drafting` | An NDA, a DPA or a cloud service agreement on Common Paper's standard terms, a review of the other side's agreement, their Word file back with tracked changes |
| `openpaperwork-hr` | `employment-statement` | The written terms of employment (EU, UK, Sweden, Norway, Denmark, Finland, Belgium in Dutch and French, the Netherlands, Austria, Ireland, Spain, Italy, Poland, Canada, Ontario, Australia; a US offer letter) |
| `openpaperwork-operations` | `business-letter`, `meeting-minutes`, `whatsapp-export` | Letters and minutes: business letters for Germany and Sweden (DIN 5008), Norway, Denmark, Finland, the US, the UK, Canada (English and French), Australia, Belgium (Dutch and French), the Netherlands, Austria, Ireland, Spain, Italy and Poland; meeting minutes and company board and general-meeting minutes for Sweden, Norway, Denmark, Finland, the UK, the US, Canada, Australia, Belgium, the Netherlands, Austria, Ireland, Spain, Italy and Poland; WhatsApp chats read into decisions, dates and files |
| `openpaperwork-marketing` | `business-deck`, `social-poster` | Business decks as a PDF, with an editable PowerPoint file when asked; fair and event posters |
| `openpaperwork-engineering` | `requirements-spec` | Requirements specifications with SI units |
| `openpaperwork-academic` | `academic-references`, `literature-search`, `paper`, `zotero-library` | APA 7, IEEE and Vancouver references; literature search; IEEE and ACM papers; a Zotero library |
| `openpaperwork-formats` | `docx`, `xlsx`, `powerpoint`, `pdf`, `every-file`, `brand-kit-deck` | Word, Excel, PowerPoint and PDF, decks from a brand kit, and the floor every Office file should pass |
| `openpaperwork` | all of them | The whole library, in [`portable-pack/`](../../portable-pack) |

The department plugins are in [`plugins/`](../../plugins). Each one carries
copies of the check modules (`skills/_checks`) and shared code (`skills/_shared`)
its packs import, so it works installed on its own. Where each rule comes from,
rule by rule: [Why standards](STANDARDS.md#where-each-pack-stands).

## Before you start

`sh portable-pack/doctor.sh` says which of these this machine has; `--fix` does the first two.

1. Have Python 3.10 or later. In a virtual environment (`python3 -m venv .venv && . .venv/bin/activate`;
   current Debian, Ubuntu and Homebrew Pythons refuse a plain install), run
   `pip install -r portable-pack/requirements.txt` (each plugin carries the same `requirements.txt`),
   and start your agent from that shell.
2. For printed pages (invoices, trade documents), run `playwright install chromium` once. On Linux also
   run `sudo .venv/bin/playwright install-deps chromium`, which adds the libraries the browser needs.
3. The checks read PDFs with `pdftotext` from poppler (`brew install poppler` on a Mac, `sudo apt install poppler-utils` on Linux).
4. Have LibreOffice installed if you make spreadsheets.
5. The paper pack builds with a TeX engine: have `tectonic` on your PATH.
6. The poster pack recolours its picture with `ffmpeg` (`brew install ffmpeg`, `sudo apt install ffmpeg`)
   and prints with the same Chromium as step 2.

## Claude and Claude Code

In the Claude desktop app, open Customize > Plugins, choose Add marketplace and
enter `ActuallyNodejam/openpaperwork`. Then install `openpaperwork`, the whole
library, or only the departments you work in.

From inside Claude Code, add the marketplace once and install the library:

```text
/plugin marketplace add ActuallyNodejam/openpaperwork
/plugin install openpaperwork
```

For one department only, install its plugin instead, for example
`openpaperwork-finance`. Or start it on a clone with
`claude --plugin-dir /path/to/portable-pack`. The skills and,
in the formats plugin, the checks tool load together.

## Codex, Cursor, Copilot, Kiro and VS Code

Each plugin folder has a `plugin.json` in the Agent Plugins 1.0.0 format
([agent-plugins.org](https://agent-plugins.org)), with its skills in `skills/`
and, in the formats and everything plugins, the checks tool in `mcp.json`.
Agents that read Agent Plugins install a plugin folder the way they install
any other.

## ChatGPT, Cursor and Antigravity

These read skills from the project folder's `.agents/skills`. In the folder you
work in, run:

```bash
npx skills add ActuallyNodejam/openpaperwork
```

On 2026-11-01 the ChatGPT desktop app (Work mode, which runs Codex, on a free
account), `cursor-agent` and the Antigravity app each made the Swedish sample
invoice this way, and each ran the pack check and ended clean, 49 rules. No hook
was set up. They ran the check because the skill asks them to.

## Codex, Gemini CLI and Cursor CLI from a clone

All three read skills from `~/.agents/skills`. Run the install script once:

```bash
sh /path/to/portable-pack/install.sh
```

It links every pack there, with the check modules (`_checks`) and the shared
letter (`_shared`) the packs import. `npx skills add` installs the same two
folders beside the packs, from the small `SKILL.md` each carries for that. With Codex installed it also adds the checks tool with
`codex mcp add`; `--no-mcp` skips that.

For Codex and Gemini CLI, where they are on the machine, it also writes the pack
check as a hook at the end of a turn, into `~/.codex/hooks.json` and
`~/.gemini/settings.json`. It prints each change first, keeps a copy of a file
before it changes it for the first time (`hooks.json.before-openpaperwork`),
and touches only its own entries. `--dry-run` prints the changes and makes none,
`--no-hooks` links the packs only, `--project DIR` does all of it for one folder
instead of your home folder. The hook for Cursor CLI is built from Cursor's
documented format and has not run with a model yet, so it is added only when
you name it: `python3 portable-pack/install.py --agents cursor`.

```bash
python3 /path/to/portable-pack/install.py doctor      # what is in place, agent by agent
python3 /path/to/portable-pack/install.py uninstall   # the links and the hooks out again
```

Two things the makers ask of you. Codex runs a hook only after you have trusted
it: start `codex`, type `/hooks`, and trust the two OpenPaperwork hooks.
Gemini CLI runs hooks only in a folder it trusts.

## Then

Ask for a file as you usually do. The agent reads the skill, builds the file
with the pack's script and runs the check beside it. A clean run prints
`pack check clean`; a fail names the rule and the evidence, and the skill
tells the agent to fix it and run the check again, three times at most.

Three invoice rules compare the page with a case's own expected facts, so
outside a case they say SKIP, not FAIL.

## What to expect

The agent decides for itself whether to read the skill and whether to run the
check, and its list of skills is short of room: with many skills installed a pack
may stand in it as a bare name. So in Claude Code, Codex and Gemini CLI a hint
comes with the ask: when it names a kind of file a pack makes (an invoice,
minutes, a quotation, in eleven languages), one line says which skill to load,
worked out from the ask's words by a table, with no model call. Cursor CLI's
prompt hook cannot add to a turn, so it gets none. Agent by agent:
[Bring your own agent](BRING_YOUR_OWN_AGENT.md#the-hint-when-the-ask-arrives).

In Claude Code a check runs anyway: each plugin's Stop hook
(`hooks/hooks.json`) runs the pack check over the files the turn wrote and, when
one fails, sends the failing lines back so the agent fixes the file, three
times a turn at most, never when the reply ends on a question. Codex and
Gemini CLI get the same from the hook `install.sh` writes. In Cursor CLI the
hook is built and has not run with a model yet. The Claude, ChatGPT and
Antigravity apps, Copilot, Kiro and VS Code have no hook we have shown working:
there the agent runs the check on the skill's instruction, and nothing stops it
handing over a file that fails. Agent by agent:
[Bring your own agent](BRING_YOUR_OWN_AGENT.md#the-check-when-you-use-an-agent-on-its-own).

2026-10-10: Codex 0.154.0 (GPT-5.6-Terra, its sandbox off) with the finance
plugin's packs and the hook installed in one folder, told to run a hand-made
starter and hand the file over: the starter's PDF failed six rules, the Stop
hook sent them back, the agent rebuilt the page with the pack's builder and the
turn ended on a clean check. Inside Codex's own sandbox the page builder cannot
print (the sandbox stops the Chromium it prints with), so there the fails come
back three times and the agent names what is left.

2026-10-10: Gemini CLI 0.63.0 (Gemini 3.8 Flash on a free-tier key) with the
same folder and task: the AfterAgent hook sent the six fails back, Gemini CLI
went on with them and loaded the invoice pack, and the key's daily quota ran out
before the agent had rebuilt the file. The fail going back is seen in a real
run; the turn ending on a clean check is not.

2026-10-09: the finance plugin in Claude Code, told to make an invoice with a
hand-made starter: the starter's PDF failed six rules, the Stop hook sent them
back, the agent rebuilt the page with the pack's builder and finished on a clean
check, 34 rules passed.

2026-10-09: the finance plugin alone, copied out of this repository and
loaded in Claude Code with `--plugin-dir`, made an invoice from the e-invoice
pack's sample order in six turns; its pack check passed, 33 rules, with the
three case-truth rules and the veraPDF rule skipped.

2026-11-01: the Swedish sample invoice from `notes.txt`, made on a Mac with
only the skills in the folder's `.agents/skills`: the ChatGPT desktop app in
Work mode (4 min 34 s, free account), `cursor-agent` (153 s) and the Antigravity
app on Gemini 3.8 Flash (about 5.5 min). Each found and ran the pack check on
its own and ended on a clean check, 49 rules. No hook ran, so the route does not
force the check.

## Where the files come from

Every plugin is built from `skills/` by `python3 scripts/build-portable-pack.py`,
and `--check` fails when a copy has drifted from its source. Change a pack in
`skills/`, never in a plugin.

## Not in the plugins yet

The PDF/UA rule of the floor needs veraPDF. A single pack copied out on its
own, without its plugin's `skills/_checks`, cannot run its check.
