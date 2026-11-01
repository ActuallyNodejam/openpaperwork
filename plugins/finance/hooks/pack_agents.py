#!/usr/bin/env python3
"""The pack check at the end of a turn, for Codex, Gemini CLI, Cursor CLI and dsh.

The rule is pack_stop.py's, unchanged: a pack's own `check` over the files of its own kind that the turn
made, only its FAIL lines, six a pack, three bounces a turn, never on a reply that ends in a question, no
further bounce when nothing changed. This file is only the adapter: it reads the hook input each agent
sends, hands pack_stop.decide() the same things Claude Code's Stop hook hands it, and prints the answer in
that agent's own form.

  python3 pack_agents.py codex|gemini|cursor|dsh [event]     without one, the input's hook_event_name

What each maker documents (read 2026-10-10; the links are in docs/community-preview/BRING_YOUR_OWN_AGENT.md):

  agent    turn starts          turn ends     sent back with                          the reply
  codex    UserPromptSubmit     Stop          {"decision":"block","reason":…}         last_assistant_message
  gemini   BeforeAgent          AfterAgent    {"decision":"deny","reason":…}          prompt_response
  cursor   beforeSubmitPrompt   stop          {"followup_message":…}                  afterAgentResponse's text
  dsh      UserPromptSubmit     Stop          {"decision":"block","reason":…}         not handed to a hook

At the start of a turn the same hook gives pack_route.py's hint (which skill makes the kind of file the ask
names) to the agents whose prompt event can add to a turn: Codex and dsh take
{"hookSpecificOutput":{"hookEventName":"UserPromptSubmit","additionalContext":…}}, Gemini CLI the same
under BeforeAgent. Cursor CLI's beforeSubmitPrompt can only let a prompt through or stop it, so Cursor
gets no hint; it still gets the net at the end of the turn, like the others.

No agent hands a hook the list of files a turn changed, Codex calls its transcript's format unstable and
dsh gives no transcript at all. So the turn's start is noted by the agent's own prompt hook,
and the turn's files are the folder's files changed since then, as pack_stop.py finds them. A transcript,
where there is one, is read only for more file names to look at. The start is kept where pack_stop.py keeps
its own state; for dsh that is .openpaperwork/ in the folder, the one place its sandbox
keeps. Standard library only.
"""
import json
import os
import re
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import pack_stop  # noqa: E402

# The event under which an agent's prompt hook may add context to the turn; an agent not here cannot.
HINTED = {"codex": "UserPromptSubmit", "gemini": "BeforeAgent", "dsh": "UserPromptSubmit"}

# How every text the hook sends begins: one that comes back as the next prompt is the same turn, not a new one.
OURS = pack_stop.OURS
# Where dsh's notes are kept inside the person's folder.
NOTES = ".openpaperwork"
# Event name -> what it is, per agent.
EVENTS = {
    "codex": {"UserPromptSubmit": "prompt", "Stop": "stop"},
    "gemini": {"BeforeAgent": "prompt", "AfterAgent": "stop"},
    "cursor": {"beforeSubmitPrompt": "prompt", "afterAgentResponse": "reply", "stop": "stop"},
    "dsh": {"UserPromptSubmit": "prompt", "Stop": "stop"},
}
# What an agent is told when the turn may go on or end as it is. Codex and dsh take silence.
QUIET = {
    "gemini": {"prompt": {"decision": "allow"}, "stop": {"decision": "allow"}},
    "cursor": {"prompt": {"continue": True}, "reply": {}, "stop": {}},
}


def session_of(agent, data):
    return "%s-%s" % (agent, data.get("conversation_id" if agent == "cursor" else "session_id") or "none")


def folder_of(agent, data):
    if agent == "cursor":
        roots = data.get("workspace_roots")
        if isinstance(roots, list) and roots and isinstance(roots[0], str):
            return roots[0]
        return os.environ.get("CURSOR_PROJECT_DIR") or os.getcwd()
    return data.get("cwd") or os.getcwd()


def turn_path(session):
    """Where the turn's start is kept, beside pack_stop's own state for the session."""
    return os.path.join(os.path.dirname(pack_stop.state_path(session)),
                        "turn-%s.json" % re.sub(r"[^\w-]", "_", session))


def read_turn(session):
    try:
        turn = json.loads(Path(turn_path(session)).read_text())
    except (OSError, ValueError):
        return {}
    return turn if isinstance(turn, dict) else {}


def named(transcript):
    """File names in the agent's transcript, whatever its format: more files for pack_stop to look at.
    Each one still has to be in the folder and changed since the turn began."""
    if not transcript or not isinstance(transcript, str):
        return []
    try:
        with open(transcript, "rb") as fh:
            fh.seek(0, os.SEEK_END)
            fh.seek(max(0, fh.tell() - 4_000_000))
            text = fh.read().decode("utf-8", "replace")
    except OSError:
        return []
    found = []
    for token in pack_stop.PATHISH.findall(text):
        if token not in found:
            found.append(token)
            if len(found) >= 400:
                break
    return found


def handle(agent, kind, data):
    """The bounce text at a stop that is not clean; None for everything else."""
    if agent == "dsh":
        # dsh runs a hook inside its file sandbox (seen at 0.1.6-alpha.2): /tmp there is the
        # hook's own and gone when it ends, the home folder is read-only. Only the session's folder is
        # kept from one hook to the next, so the turn's notes live there.
        os.environ["CLAUDE_PLUGIN_DATA"] = os.path.join(folder_of(agent, data), NOTES)
    session = session_of(agent, data)
    turn = read_turn(session)
    if kind == "prompt":
        if OURS in str(data.get("prompt") or "")[:600]:
            return None
        now = time.time() * 1000
        # What the ask names is kept for the end of the turn: the net reads it there.
        Path(turn_path(session)).write_text(json.dumps({
            "began": now, "first": turn.get("first") or now, "asked": pack_stop.routed(str(data.get("prompt") or ""))}))
        return None
    if kind == "reply":
        if turn:
            turn["reply"] = str(data.get("text") or "")[-400:]
            Path(turn_path(session)).write_text(json.dumps(turn))
        return None
    # Without a noted start there is nothing to tell this turn's files from the person's own.
    began = turn.get("began")
    if not began or (agent == "cursor" and data.get("status") != "completed"):
        return None
    reply = {"codex": data.get("last_assistant_message"), "gemini": data.get("prompt_response"),
             "cursor": turn.get("reply")}.get(agent) or ""
    # Every stop after a bounce counts as one: dsh never sets stop_hook_active, and
    # pack_stop only compares with a bounce of this same turn.
    # No agent here has a transcript whose tool calls can be read for a pack that was loaded (uses is None):
    # the net tells a pack that was used by the evidence its builder leaves in the folder.
    return pack_stop.decide(folder_of(agent, data), session, began, turn.get("first") or began,
                            named(data.get("transcript_path")), reply, True, turn.get("asked"), None)


def hint(agent, kind, data):
    """The line that says which skill makes the kind of file the ask names, for an agent that can take one."""
    route = pack_stop.pack_route
    if kind != "prompt" or agent not in HINTED or not route:
        return ""
    return route.hint(data.get("prompt"))


def answer(agent, kind, text, context=""):
    if text:
        if agent == "cursor":
            return {"followup_message": text}
        return {"decision": "deny" if agent == "gemini" else "block", "reason": text}
    quiet = QUIET.get(agent, {}).get(kind)
    if context:
        return {**(quiet or {}), "hookSpecificOutput": {"hookEventName": HINTED[agent], "additionalContext": context}}
    return quiet


def main(argv):
    agent = argv[1] if len(argv) > 1 else ""
    if agent not in EVENTS:
        print("usage: pack_agents.py codex|gemini|cursor|dsh [event]  (the hook input on stdin)", file=sys.stderr)
        return 0
    kind, text, data, context = None, None, None, ""
    try:
        data = json.load(sys.stdin)
        event = argv[2] if len(argv) > 2 else data.get("hook_event_name")
        kind = EVENTS[agent].get(event)
        # Inside the OpenPaperwork app the app's own pack check judges the turn and the app gives the hint
        # itself: the agent gets its quiet answer.
        if kind and not os.environ.get(pack_stop.APP_ENV):
            text = handle(agent, kind, data)
            context = hint(agent, kind, data)
    except Exception as exc:  # a hook that breaks must never keep a turn open
        print("openpaperwork pack check hook: %s" % exc, file=sys.stderr)
    out = answer(agent, kind or "stop", text, context)
    if out is not None:
        print(json.dumps(out))
    keep(agent, data, out)
    return 0


def keep(agent, data, out):
    """With OPENPAPERWORK_HOOK_LOG set to a folder, each hook input and its answer are kept there, one
    line each in <agent>.jsonl: what to attach when a hook does not do what this file says."""
    folder = os.environ.get("OPENPAPERWORK_HOOK_LOG")
    if not folder:
        return
    try:
        os.makedirs(folder, exist_ok=True)
        with open(os.path.join(folder, "%s.jsonl" % agent), "a", encoding="utf-8") as fh:
            fh.write(json.dumps({"at": time.time(), "input": data, "answer": out}) + "\n")
    except OSError:
        pass


if __name__ == "__main__":
    sys.exit(main(sys.argv))
