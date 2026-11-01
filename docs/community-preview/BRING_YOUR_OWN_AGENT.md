# Bring your own agent

OpenPaperwork has no agent of its own. The packs are Agent Skills. The agent you already use reads
them, builds the file and runs the pack's check on it. Claude, ChatGPT, Cursor and Antigravity are the
ones we have tried, and any agent that reads Agent Skills can use them.

## The apps

| Agent | How it gets the packs | Run for real |
| --- | --- | --- |
| Claude (the desktop app) | Customize > Plugins > Add marketplace, then `ActuallyNodejam/openpaperwork`. Claude Code takes the same marketplace: `/plugin marketplace add ActuallyNodejam/openpaperwork` | Not run yet in the Claude app. Claude Code ran it on 2026-10-09 (below) |
| ChatGPT (the desktop app, in Work mode, which runs Codex) | `npx skills add ActuallyNodejam/openpaperwork` in the project folder writes the skills to `.agents/skills`, which it reads | 2026-11-01, a free account: found the e-invoice skill itself, made the Swedish sample invoice from `notes.txt`, ran the pack check itself, clean, 49 rules, 4 min 34 s |
| Cursor | The same `npx skills add` command | 2026-11-01, `cursor-agent`, the same task: clean, 49 rules, 153 s |
| Antigravity (Google's) | The same `npx skills add` command | 2026-11-01, the Antigravity app on Gemini 3.8 Flash, the same task: clean, 49 rules, about 5.5 min |

Antigravity replaced Gemini CLI for Google AI Pro, Ultra and free users on 18 June 2026 and keeps Agent
Skills.

The three runs were made on a Mac, with only the skills in the folder's `.agents/skills`. No hook was
set up, and none ran. The agents ran the pack check because the skill's text asks them to; nothing in
the route forces it. If an agent skips the check, run it yourself or ask for it. Claude Code, Codex and Gemini CLI
have a hook that runs it, described below.

## Agents you run in Terminal

| Agent | Install | Sign in once, in Terminal |
| --- | --- | --- |
| Claude Code | `curl -fsSL https://claude.ai/install.sh \| bash` | `claude` |
| Codex | `npm install -g @openai/codex` | `codex login` |
| Gemini CLI | `npm install -g @google/gemini-cli` | A Gemini API key, saved as `GEMINI_API_KEY=…` in `~/.gemini/.env` |
| Cursor CLI | `curl https://cursor.com/install -fsS \| bash` | `cursor-agent login` |

Gemini CLI takes a Gemini API key here rather than its Google sign-in: Google's
[Gemini CLI FAQ](https://geminicli.com/docs/resources/faq/) warns that the Google sign-in used through
third-party software can get an account suspended.

Each install command is the maker's own; check it against the maker's page before you run it.

## Accounts and terms

Each agent signs in and bills through its own account, your plan or your API key, under its maker's
terms. OpenPaperwork never sees, stores or shares those credentials.

## The check when you use an agent on its own

An agent gets the packs as skills, and a skill can only ask the agent to run its check. Claude Code,
Codex, Gemini CLI and Cursor CLI also have a hook at the end of a turn that can send the agent back to
work, so the [portable pack](PORTABLE_PACK.md) carries the same rule for them: a check runs over the
files the turn made, and a fail goes back to the agent in the same chat, three tries at most, never when
the reply ends in a question, and not again when the agent changed nothing.

| Agent | At the end of a turn | Where the hook lives | Run for real |
| --- | --- | --- | --- |
| Claude Code | A check runs by itself (its `Stop` hook) | Inside each plugin | 2026-10-09, the finance plugin |
| Codex | A check runs by itself (its `Stop` hook), once you have trusted the hook: start `codex`, type `/hooks` | `~/.codex/hooks.json`, written by `install.sh` | 2026-10-10, Codex 0.154.0: six fails went back, the agent rebuilt the file, the turn ended on a clean check |
| Gemini CLI | A check runs by itself (its `AfterAgent` hook), in a folder Gemini CLI trusts | `~/.gemini/settings.json`, written by `install.sh` | 2026-10-10, Gemini CLI 0.63.0: six fails went back and the agent went on with them; the key's daily quota ended the run before the file was rebuilt |
| Cursor CLI | Built from Cursor's documented `stop` hook, not run: until it has run, count on the agent running the check on the pack's instruction | `~/.cursor/hooks.json`, written only by `install.py --agents cursor` | The hook has not run. Without it, `cursor-agent` ran the check on the skill's instruction on 2026-11-01 |
| Claude app, ChatGPT app, Antigravity | No hook is proven: the agent runs the check on the skill's instruction | | The ChatGPT app and Antigravity did so on 2026-11-01. The Claude app has not been run |
| Copilot, Kiro, VS Code | No hook is carried: the agent runs the check on the pack's instruction | | |

`python3 portable-pack/install.py doctor` says, agent by agent, whether the skills, the plugin, the
hook and the hint are in place, and what to run when one is not.

Besides a fail, three things go back to the agent once a turn and never a second time: a check's
question (a `WARN` line: the agent answers it in the reply or acts on it), a check that could run no
rule (the file is neither passed nor failed, and the reply says so), and a file the turn made beside the
pack instead of in your folder.

## The hint when the ask arrives

A skill is chosen from a list the agent is given, and that list is short of room: with many skills
installed a pack may stand in it as a bare name, without its description. So the portable pack does not
leave the choice to the list alone. When an ask names a kind of file a pack makes, in any of eleven
languages (an invoice, a Rechnung, a faktura; minutes, a protokoll, an acta; a quotation, a devis, an
offert), one line is added to the turn before the agent starts: "If this ask is for an invoice, load the
e-invoice skill before writing anything: it lays the file out and checks it. Hand back a file, not text
in the chat." The line is conditional, so a word that meant something else costs one ignored line; words
that are ordinary words elsewhere (brief, list, carta, quote) count only with a second sign. It is
worked out by a table (`hooks/routes.json`, built from the `asks` list in each pack's `pack.json`), with
no model call and no network, and an ask that names no such file gets nothing.

In Claude Code the list's room can also be raised: its own variable `SLASH_COMMAND_TOOL_CHAR_BUDGET` (in
the environment, or under `env` in `~/.claude/settings.json`) sets it in characters, and at `30000` every
pack's whole description stood in the list on the machine we tried it on (2026-10-10, Claude Code
2.1.292). The price is a longer list at the start of every chat. `install.py doctor` says which you have.

Under it is a net at the end of the turn: when the ask named a kind of file, the turn handed back a
file, and the pack for it neither was loaded nor left its own order file in the folder, the agent is
sent back once to load the pack and build the file with its script, keeping every fact it wrote.

| Agent | When the ask arrives | What the maker documents |
| --- | --- | --- |
| Claude Code | The hint comes by itself, from each plugin (`UserPromptSubmit`) | The hook's `additionalContext` is added to the turn |
| Codex | The hint comes by itself, from the hook `install.sh` writes, once you have trusted it | `UserPromptSubmit`: "`additionalContext` text is added as extra developer context". The Codex desktop app runs a plugin's hooks only when you installed the plugin by hand, and shows a "Review hooks" dialog first |
| Gemini CLI | The hint comes by itself, from the hook `install.sh` writes, in a folder Gemini CLI trusts | `BeforeAgent`: `additionalContext` is "appended to the prompt for this turn only" |
| Cursor CLI | No hint. The net at the end of the turn is built with the hook, not run | `beforeSubmitPrompt` returns only `continue` and a message for the person: it cannot add to a turn |
| Copilot, Kiro, VS Code | No hint: the skill's own name and description are all the agent has | |
| ChatGPT app, Antigravity, Claude app | No hint is carried or tried: the skill's own name and description are all the agent has. The ChatGPT app found the e-invoice skill itself on 2026-11-01 | |

What each maker documents, read on 2026-10-10:

- **Codex** ([Hooks](https://learn.chatgpt.com/docs/hooks), and the `Stop` schemas in its repository at
  `rust-v0.154.0`): a `Stop` hook that prints `{"decision":"block","reason":…}` makes Codex go on with the
  reason as a new prompt. It receives the folder, the session, the last reply and whether the turn was
  already continued; the transcript's format is not promised. Codex skips a hook until you have reviewed
  and trusted it, and a hook in a folder loads only when the folder is trusted.
- **Gemini CLI** ([Hooks reference](https://geminicli.com/docs/hooks/reference/), `docs/hooks/` at
  `v0.63.0`): an `AfterAgent` hook that prints `{"decision":"deny","reason":…}` rejects the reply and sends
  the reason to the agent as a new prompt. It receives the folder, the session, the prompt and the reply.
  Hooks run only in a trusted folder; headless, set `GEMINI_CLI_TRUST_WORKSPACE=true` before it starts,
  because `--skip-trust` is read after the settings are.
- **Cursor CLI** ([Hooks](https://cursor.com/docs/hooks), the
  [CLI changelog](https://cursor.com/docs/cli/changelog) for January 2026 and v2026.08.11): a `stop` hook
  that prints `{"followup_message":…}` has Cursor send that text as the next message, five times at most
  unless `loop_limit` says otherwise. The reply reaches a hook only through `afterAgentResponse`.

No agent hands a hook the list of files a turn changed. The turn's files are the files in the folder,
one level down at most, that changed since the agent's own prompt hook fired, plus any the transcript
names; a file you had before the turn stays yours.

## Another agent

Any agent that reads Agent Skills can use the packs. Put the skills in its skills folder, with
`npx skills add ActuallyNodejam/openpaperwork` or as [Use the packs in your agent](PORTABLE_PACK.md)
says, and ask for a file. If you run one for real, say what happened in an issue or a pull request
([Contributing](../../CONTRIBUTING.md)).
