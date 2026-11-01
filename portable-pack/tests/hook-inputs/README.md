# The hook inputs the tests run on

One file for each agent and event that `hooks/pack_agents.py` reads. A test fills in its own folder and
transcript before it sends one to the hook; everything else is as the agent sent it or as its maker
documents it. The paths of the machine they were recorded on are replaced with `/home/person`.

| Files | Where they come from |
| --- | --- |
| `codex-UserPromptSubmit.json`, `codex-Stop.json` | Recorded from a real run of Codex 0.154.0 (`codex exec`, GPT-5.6-Terra) on 2026-10-10 |
| `gemini-BeforeAgent.json`, `gemini-AfterAgent.json` | Recorded from a real run of Gemini CLI 0.63.0 (`gemini -p`) on 2026-10-10 |
| `dsh-UserPromptSubmit.json`, `dsh-Stop.json` | Recorded from dsh 0.1.6-alpha.2 (`dsh --profile headless`, its Claude Code hook bridge) on 2026-10-10, in a run against a scripted stand-in for the model: the harness and the hook were real, the model was not |
| `cursor-beforeSubmitPrompt.json`, `cursor-afterAgentResponse.json`, `cursor-stop.json` | Not recorded. Written from Cursor's documented hook input (cursor.com/docs/hooks, read 2026-10-10); no signed-in Cursor CLI was there to record one |

To record one yourself, set `OPENPAPERWORK_HOOK_LOG` to a folder before you start the agent: the hook
then keeps every input and its answer there, one line each in `<agent>.jsonl`.
