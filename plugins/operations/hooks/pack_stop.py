#!/usr/bin/env python3
"""Claude Code Stop hook: a turn may not end while a pack's check is red over a file it wrote.

The rule: every pack in this plugin that declares a `check` and what it
`hands_back` in its pack.json looks at the files of its own kind that this turn made in the agent's
folder, runs its check with `--if-claimed --in <folder>` (a pack checks only files its own evidence,
`recognises`, says are its), and keeps only the check's own FAIL lines. A pack the turn loaded (a Skill
call naming it or one of this plugin's commands that loads it, a command typed in the chat, or a read of its
SKILL.md) checks the files of its kind with no claim: a reference list or a paper
printed some other way leaves no evidence, and its pack must still read it. When one is red the stop is
blocked with those lines, so the agent fixes the file and tries again: three times a turn at most,
never when the reply ends on a question, and not again once the agent changes nothing after a bounce.

Three things are said to the agent ONCE a turn, never a second time and never as a loop: a check's WARN
lines (a question it must answer in the reply or act on), a check that could run no rule at all (its
"pack check not checked:" line: the file is neither passed nor failed, and the reply says so), and a file
of a pack's kind that the turn made in or beside this plugin instead of in the person's folder. They ride
with a bounce when there is one, and go alone when nothing fails.

And a net under the prompt-time hint (pack_route.py), once a turn: when the ask named a kind of file a
pack here makes, the turn handed back a file, and that pack neither was loaded nor left its own evidence
in the folder, the agent is sent back with "This was asked as an invoice; the e-invoice skill makes and
checks that. Load it and build the file with its script; keep every fact you already wrote." Never a
second time, never when the pack was loaded or used, never when the ask named nothing.

In the check command `{here}` is the pack's folder and `{file}` one of those files: the check runs once
for each file. A check that judges a whole folder names `{folder}` and no `{file}`, and runs once for
each folder those files sit in. With both it runs once for each file, and `{folder}` is that file's folder.

Claude Code runs it from hooks/hooks.json with the Stop input on stdin (session_id, transcript_path,
cwd, stop_hook_active, last_assistant_message). Codex, Gemini CLI, Cursor CLI and dsh reach
the same rule, decide(), through pack_agents.py beside this file. Standard library only.
"""
import json
import os
import re
import shlex
import subprocess
import sys
import tempfile
import time
from datetime import datetime
from pathlib import Path

MAX_BOUNCES = 3
HERE = Path(__file__).resolve().parent
SKILLS = HERE.parent / "skills"
# How packcheck.py's last line begins when no rule could run: not a pass, not a fault in the file.
NOT_CHECKED = "pack check not checked:"
# What one check may send back, in characters, cut only after its lines are put in order.
CUT = 2000
# How every text this hook sends begins: pack_agents.py tells a bounce that comes back as a prompt by it.
OURS = "A pack check "
# Letters of any language: "Budget-Växjö.xlsx" is one name, not ".xlsx".
PATHISH = re.compile(r"[\w./-]*\.(?:docx|xlsx|pptx|pdf|html|htm|md|csv|tex|txt|xml)\b", re.I)
PATH_TOOLS = {"Write", "Edit", "MultiEdit", "Read", "NotebookEdit"}
PATH_KEYS = ("file_path", "path", "filePath", "notebook_path")
# The kinds of file a person is handed: what the net looks for when it asks whether the turn made a file.
HANDED = ("*.docx", "*.xlsx", "*.pptx", "*.pdf", "*.html", "*.htm", "*.md", "*.txt", "*.odt", "*.rtf")

try:  # the table of what people call each kind of file, beside this file
    import pack_route
except Exception:  # without it there is no net, and the check goes on as before
    pack_route = None


# --- The packs ----------------------------------------------------------------------------------------

def declaration(skill, directory):
    try:
        spec = json.loads((directory / "pack.json").read_text())
    except (OSError, ValueError):
        return None
    if not spec.get("check") or not spec.get("hands_back"):
        return None
    return {"skill": skill, "directory": directory, "check": spec["check"], "hands_back": spec["hands_back"]}


def installed(root):
    """Every pack in the plugin's skills folder and one level under it; the first of a name wins."""
    found = []

    def dirs(folder):
        try:
            return sorted(p for p in folder.iterdir() if p.is_dir())
        except OSError:
            return []

    for entry in dirs(root) + [sub for group in dirs(root) for sub in dirs(group)]:
        pack = declaration(entry.name, entry)
        if pack and not any(other["skill"] == pack["skill"] for other in found):
            found.append(pack)
    return found


def matches(name, kind):
    return name.lower().endswith(kind.lstrip("*").lower())


# --- The turn -----------------------------------------------------------------------------------------

def millis(stamp):
    try:
        return datetime.fromisoformat(str(stamp).replace("Z", "+00:00")).timestamp() * 1000
    except ValueError:
        return 0


# A command the person typed, as Claude Code records it: <command-name>/plugin:command</command-name> and its words.
COMMAND_LINE = re.compile(r"<command-name>\s*([^<]*?)\s*</command-name>(?:\s*<command-args>(.*?)</command-args>)?", re.S)


def prompt_text(entry):
    """The person's own words in a transcript line, or None for tool results, hook feedback and meta. A command
    they typed counts, as its name and words: headless Claude Code records nothing else for a turn started by
    /plugin:command, and with no start every file in the folder read as the turn's own (timed run c21, 2026-10-25:
    the check sent the agent to retitle the person's own template)."""
    if entry.get("type") != "user" or entry.get("isMeta") or entry.get("isSidechain"):
        return None
    content = (entry.get("message") or {}).get("content")
    if isinstance(content, str):
        text = content
    elif isinstance(content, list):
        if any(isinstance(b, dict) and b.get("type") == "tool_result" for b in content):
            return None
        text = "\n".join(b.get("text", "") for b in content if isinstance(b, dict) and b.get("type") == "text")
    else:
        return None
    if text.lstrip().startswith("<command-"):
        m = COMMAND_LINE.search(text)
        return " ".join(x.strip() for x in m.groups() if x and x.strip()) if m else None
    if not text.strip() or text.lstrip().startswith(("Stop hook feedback", "<local-command")):
        return None
    return text


def read_turn(transcript):
    """When the turn and the chat began, the paths the turn named, and the last reply's text."""
    entries = []
    try:
        with open(transcript, encoding="utf-8") as fh:
            for line in fh:
                try:
                    entries.append(json.loads(line))
                except ValueError:
                    continue
    except (OSError, TypeError):
        return 0, 0, [], ""
    began = first = 0
    start = 0
    for i, entry in enumerate(entries):
        if prompt_text(entry) is not None:
            at = millis(entry.get("timestamp"))
            began, start = at or began, i
            first = first or at
    written, reply = [], ""

    def add(value):
        if isinstance(value, str) and value and value not in written:
            written.append(value)

    for entry in entries[start:]:
        content = (entry.get("message") or {}).get("content")
        if not isinstance(content, list):
            continue
        for block in content:
            if not isinstance(block, dict):
                continue
            if block.get("type") == "tool_use":
                data = block.get("input") or {}
                if block.get("name") in PATH_TOOLS:
                    for key in PATH_KEYS:
                        add(data.get(key))
                if block.get("name") == "Bash":
                    for token in PATHISH.findall(str(data.get("command", ""))):
                        add(token)
            elif block.get("type") == "tool_result":
                out = block.get("content")
                if isinstance(out, list):
                    out = "\n".join(b.get("text", "") for b in out if isinstance(b, dict))
                for token in PATHISH.findall(str(out or ""))[:200]:
                    add(token)
            elif block.get("type") == "text" and entry.get("type") == "assistant":
                reply = block.get("text", "")
    return began, first, written, reply


def ask_and_uses(transcript):
    """The person's last ask in a Claude Code transcript, and what every tool of the chat was called with
    (one string a call): the net reads the first for the kind of file, the second for a pack that was loaded."""
    ask, uses = "", []
    try:
        with open(transcript, encoding="utf-8") as fh:
            for line in fh:
                try:
                    entry = json.loads(line)
                except ValueError:
                    continue
                text = prompt_text(entry)
                if text is not None:
                    ask = text
                content = (entry.get("message") or {}).get("content") if isinstance(entry, dict) else None
                for block in content if isinstance(content, list) else []:
                    if isinstance(block, dict) and block.get("type") == "tool_use":
                        uses.append(json.dumps(block.get("input") or {})[:4000])
    except (OSError, TypeError):
        return "", None
    return ask, uses


def turn_uses(transcript, began):
    """What this turn's tool calls were called with, one string a call, and the person's own words (a command
    typed in the chat comes in them, not as a tool call)."""
    uses = []
    try:
        with open(transcript, encoding="utf-8") as fh:
            for line in fh:
                try:
                    entry = json.loads(line)
                except ValueError:
                    continue
                if not isinstance(entry, dict) or millis(entry.get("timestamp")) < (began or 0):
                    continue
                content = (entry.get("message") or {}).get("content")
                # A command typed in the chat is a user line of its own (<command-name>/plugin:command</command-name>),
                # which prompt_text() leaves out as not the person's own words.
                if entry.get("type") == "user" and isinstance(content, str):
                    uses.append(content[:4000])
                for block in content if isinstance(content, list) else []:
                    if isinstance(block, dict) and block.get("type") == "tool_use":
                        uses.append(json.dumps(block.get("input") or {})[:4000])
    except (OSError, TypeError):
        return []
    return uses


def command_packs():
    """The pack each of this plugin's commands loads, by the command's name: its body says "Load the <pack>
    skill" (build-portable-pack.py writes every command that way)."""
    found = {}
    for path in sorted((HERE.parent / "commands").glob("*.md")):
        try:
            m = re.search(r"Load the (\S+) skill", path.read_text(errors="ignore"))
        except OSError:
            continue
        if m:
            found[path.stem] = m.group(1)
    return found


def loaded_packs(uses):
    """The packs this turn loaded: a Skill call by name, bare or with its plugin, a command of this plugin (run
    as a Skill call, or typed as /plugin:command), or a read of its SKILL.md. Headless Claude Code records the
    command as the Skill call and the agent may never load the pack after it (timed run c19, 2026-10-25). A
    folder of the same name elsewhere ("/paper/" or "~/Documents/references/" in a path) is not one."""
    found = set()
    for pack in installed(SKILLS):
        skill = pack["skill"]
        marks = ('"skill": "%s"' % skill, ':%s"' % skill, "/%s/SKILL.md" % skill)
        if any(mark in use for use in uses or [] for mark in marks):
            found.add(skill)
    for name, skill in command_packs().items():
        typed = re.compile(r"(?:^|[\s>])/(?:[\w-]+:)?%s(?![\w/.-])" % re.escape(name))
        if any('"skill": "%s"' % name in use or ':%s"' % name in use or typed.search(use) for use in uses or []):
            found.add(skill)
    return found


def routed(ask):
    """The packs an ask names, as [skill, kind, whether it has a check]; none for a command or our own text."""
    if not pack_route or not ask or not pack_route.an_ask(ask):
        return []
    return [[route["skill"], names[0], bool(route.get("checks"))] for route, names in pack_route.asked(ask)]


def made(file, chat, began, first):
    """The turn made this file: it is in the folder, changed since the person last sent, and was not
    there before the chat began. A file the person brought stays theirs."""
    try:
        inside = Path(file).resolve().relative_to(Path(chat).resolve())
    except ValueError:
        return False
    if not str(inside) or str(inside) == ".":
        return False
    if not began:
        return True
    try:
        stat = os.stat(file)
    except OSError:
        return False
    if stat.st_mtime * 1000 < began:
        return False
    birth = getattr(stat, "st_birthtime", 0) * 1000
    return not (birth > 0 and first > 0 and birth < first)


def evidence_files(folder, kind, depth=2):
    found = []
    try:
        entries = sorted(Path(folder).iterdir())
    except OSError:
        return found
    for entry in entries:
        if entry.is_dir():
            if depth > 1 and not entry.name.startswith("."):
                found.extend(evidence_files(entry, kind, depth - 1))
        elif matches(entry.name, kind):
            found.append(str(entry))
    return found


def files_for(pack, chat, written, began, first):
    files = []
    for raw in written:
        full = raw if os.path.isabs(raw) else os.path.join(chat, raw)
        if any(matches(raw, k) for k in pack["hands_back"]) and full not in files and os.path.isfile(full):
            if made(full, chat, began, first):
                files.append(full)
    # A script that saves a file never names it in the shell line that runs it.
    if began:
        for kind in pack["hands_back"]:
            for f in evidence_files(chat, kind):
                if f not in files and not os.path.basename(f).startswith("~$") and made(f, chat, began, first):
                    files.append(f)
    return [os.path.normpath(f) for f in files]


def claims(directory, chat):
    """Whether a pack's own evidence for its files is in the person's folder (`recognises` in its pack.json):
    the order file its builder reads. A pack that names no evidence cannot be told, and counts as there."""
    try:
        rule = json.loads((Path(directory) / "pack.json").read_text()).get("recognises")
    except (OSError, ValueError, AttributeError):
        return True
    if not isinstance(rule, dict) or not rule.get("file"):
        return True
    if rule.get("also") and evidence_files(chat, rule["also"]):
        return True
    has, without = rule.get("has") or [], rule.get("without") or []
    for file in evidence_files(chat, rule["file"]):
        if not has and not without:
            return True
        try:
            data = json.loads(Path(file).read_text())
        except (OSError, ValueError):
            continue
        if isinstance(data, dict) and all(k in data for k in has) and not any(k in data for k in without):
            return True
    return False


def handed_back(chat, written, began, first):
    """The files the turn made in the person's folder that a person is handed, whatever made them."""
    return files_for({"hands_back": HANDED}, chat, written, began, first)


def net_text(chat, written, began, first, asked, uses, loaded=()):
    """What goes back, once, when the ask named a kind of file and the turn made its file without the pack.

    asked is routed()'s list for the turn's ask; uses is what the chat's tools were called with, or None
    where an agent's transcript cannot be read that way. Nothing when the ask named no pack that is here,
    when one of the packs it named was loaded (its name or folder in a tool call) or left its evidence in the
    folder, or when the turn handed back no file."""
    here = [entry for entry in asked or [] if (SKILLS / str(entry[0]) / "pack.json").is_file()]
    if not here or not began:
        return ""
    for skill, _, _ in here:
        marks = ('"%s"' % skill, ':%s"' % skill, "/%s/" % skill)
        if skill in loaded or any(mark in use for use in uses or [] for mark in marks) or claims(SKILLS / skill, chat):
            return ""
    if not handed_back(chat, written, began, first):
        return ""
    skill, kind, checks = here[0]
    return "\n".join([
        OURS + "found no file made with the pack this ask is for (said once, not again):", "",
        "This was asked as %s; the %s skill %s that. Load it and build the file with its script; keep every fact "
        "you already wrote. If what was asked for is not %s after all, leave the file as it is and say so."
        % (kind, skill, "makes and checks" if checks else "makes", kind)])


def check_command(pack, file, chat, claim=True):
    """The pack's check for this file, as one shell command with every path quoted. With claim, the check
    reads the file only when the pack's evidence says it is its own; a pack the turn loaded needs none."""
    return (pack["check"].replace("{here}", shlex.quote(str(pack["directory"])))
            .replace("{file}", shlex.quote(file)).replace("{folder}", shlex.quote(os.path.dirname(file)))
            + (" --if-claimed" if claim else "") + " --in " + shlex.quote(chat))


def sorted_out(text, code):
    """A check's output as (FAIL lines, WARN lines, the line that says nothing was checked).

    What the agent must act on comes first and the cut comes after: the FAIL lines, then the WARN lines, then
    the rest is dropped. Cut first, a FAIL behind forty SKIP lines fell outside the first 2,000 characters and
    the turn ended as if clean (a deck's real run, 2026-10-10). Only the check's own FAIL lines make a pack
    red, and only on a run that did not exit 0; a check that broke before it said anything says nothing."""
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    fails = [line for line in lines if "FAIL " in line] if code != 0 else []
    warns = [line for line in lines if line.startswith("WARN ")]
    unchecked = [] if fails else [line for line in lines if line.startswith(NOT_CHECKED)][:1]
    kept = "\n".join(fails + warns + unchecked)[:CUT].split("\n") if fails or warns or unchecked else []
    return kept[:len(fails)], kept[len(fails):len(fails) + len(warns)], kept[len(fails) + len(warns):]


def plugin_env():
    """The plugin's Python on PATH and its Chromium, when first_use.py finished setting them up in
    CLAUDE_PLUGIN_DATA (its .setup-<version> marker). A venv a failed setup left behind has no packages."""
    env = dict(os.environ)
    data = os.environ.get("CLAUDE_PLUGIN_DATA")
    if data:
        venv_bin = Path(data) / "venv" / "bin"
        if venv_bin.is_dir() and any(Path(data).glob(".setup-*")):
            env["PATH"] = str(venv_bin) + os.pathsep + env.get("PATH", "")
            env.setdefault("PLAYWRIGHT_BROWSERS_PATH", str(Path(data) / "ms-playwright"))
    return env


def run_check(pack, file, chat, claim=True):
    command = check_command(pack, file, chat, claim)
    try:
        done = subprocess.run(["sh", "-c", command], cwd=os.path.dirname(file), capture_output=True,
                              text=True, timeout=180, env=plugin_env())
    except (OSError, subprocess.TimeoutExpired):
        return [], [], []
    return sorted_out(done.stdout + "\n" + done.stderr, done.returncode)


def strays(chat, began):
    """Files of a pack's kind that the turn made in this plugin's folder, or beside it, and not in the
    person's folder: built where the script lives, they are never handed back (seen in real runs
    on 2026-10-10: the reply named a path the person would not look in)."""
    if not began:
        return []
    plugin, person = HERE.parent, Path(chat).resolve()
    # A person working on the plugin itself, or with the plugin inside their folder, has no "beside".
    if plugin == person or plugin in person.parents or person in plugin.parents:
        return []
    kinds = {kind.lstrip("*").lower() for pack in installed(SKILLS) for kind in pack["hands_back"]}
    found = []

    def look(path):
        if not any(path.name.lower().endswith(kind) for kind in kinds) or path.name.startswith("~$"):
            return
        try:
            fresh = path.stat().st_mtime * 1000 >= began
        except OSError:
            return
        # The same name in the person's folder: the agent built it here and then put it where it belongs.
        if fresh and not (person / path.name).exists():
            found.append(str(path))

    for base, dirs, files in os.walk(plugin):
        dirs[:] = [d for d in dirs if d not in ("__pycache__", "node_modules", ".git")]
        if len(Path(base).relative_to(plugin).parts) >= 5:
            dirs[:] = []
        for name in sorted(files):
            look(Path(base) / name)
    try:
        for entry in sorted(plugin.parent.iterdir()):
            if entry.is_file():
                look(entry)
    except OSError:
        pass
    return found[:5]


def findings(chat, written, began, first, loaded=()):
    """The turn's files against every pack's check: the FAIL lines (six a pack), each checked file's time,
    the commands to run again, and what is said once (the WARN lines, three a pack, and the checks that
    could run no rule). A pack in loaded checks its kind of file with no claim."""
    lines, checked, commands, asks, blind = [], {}, [], [], []
    for pack in installed(SKILLS):
        red, folders = [], []
        claim = pack["skill"] not in loaded
        # A check that names {folder} and no {file} judges a folder as a whole (a poster folder holds a PNG
        # and a PDF for every size): one run for each folder, on its first file, in the order they appear.
        whole = "{folder}" in pack["check"] and "{file}" not in pack["check"]
        for file in files_for(pack, chat, written, began, first):
            checked[file] = os.stat(file).st_mtime
            folder = os.path.dirname(file)
            if whole and folder in folders:
                continue
            folders.append(folder)
            name = os.path.relpath(folder, chat) + "/" if whole else os.path.relpath(file, chat)
            fails, warns, unchecked = run_check(pack, file, chat, claim)
            red += ["%s (%s): %s" % (pack["skill"], name, line) for line in fails]
            asks += ["%s (%s): %s" % (pack["skill"], name, line) for line in warns[:3]]
            blind += ["%s (%s): %s" % (pack["skill"], name, line) for line in unchecked]
            # The command as the hook ran it, from the folder it ran in: an agent told only to "run the check
            # again" spends its turn looking for the script (Gemini CLI, 2026-10-10).
            if fails:
                commands.append("cd %s && %s" % (shlex.quote(folder), check_command(pack, file, chat, claim)))
        lines += red[:6]
    return lines, checked, commands[:6], {"asks": asks[:9], "blind": blind[:6]}


# The person reads only the agent's last message, never this text: an answer to it alone hands back no reply (a
# real run, 2026-10-13: "The check flagged 11.15 ..." was all the person got, with no file and no summary).
# The reply names the file and what is still open, never what the file holds (the brief's acceptance 3): "what it
# holds" here had the agent retell the page after a bounce, and "answer each one" gave the replies a section of
# answers to the check (timed command runs c02, c03, c06, c07, 2026-10-25).
WHOLE_REPLY = ("The person reads only the message you write next, not this one and not your earlier reply: write "
               "the whole reply again, the file and where it is, then what is still open for them, one short line "
               "each, with the answer folded in. Never retell what the file holds, and say nothing about this check "
               "or its questions.")


def bounce_text(count, lines, commands=()):
    last = count >= MAX_BOUNCES
    return "\n".join([
        ("A pack check is still not clean, and this is the last try (%d of %d):" if last
         else "A pack check is not clean (try %d of %d):") % (count, MAX_BOUNCES),
        "", *lines, "",
        ("Fix what you can, then finish and name plainly in the reply what is still red." if last
         else "Fix these, run the check again, then finish. Anything you cannot fix, name in the reply.")
        + " " + WHOLE_REPLY,
        # The text ends on the exact command for each failing pack and file, so nothing has to be searched for.
        *(["", "Run the check again with exactly:" if len(commands) == 1 else "Run the checks again with exactly:",
           *commands] if commands else []),
    ])


def once_text(chat, asks=(), blind=(), stray=()):
    """What is said once a turn, each part under its own first line."""
    parts = []
    if asks:
        parts.append("\n".join([
            OURS + "has a question before the turn ends (asked once, not again):", "", *asks, "",
            "Change the file if the answer is that the file is wrong; otherwise name the point in the reply as "
            "one of what is still open for the person, in plain words. Never change a fact to make a question "
            "go away."]))
    if blind:
        parts.append("\n".join([
            OURS + "could not run, so a file is not checked (said once, not again):", "", *blind, "",
            "This is not a fault in the file and there is nothing to fix in it. Do not call the file checked: "
            "say in the reply that the check could not run and why."]))
    if stray:
        parts.append("\n".join([
            OURS + "found a file this turn made outside the person's folder (said once, not again):", "",
            *stray, "",
            "A file there is not handed back: the person works in %s and will not look anywhere else. Put the "
            "file in that folder and name it there in the reply." % chat]))
    if parts:
        parts.append(WHOLE_REPLY)
    return "\n\n".join(parts)


# --- State, keyed by session ------------------------------------------------------------------------

def state_path(session):
    base = os.environ.get("CLAUDE_PLUGIN_DATA") or os.path.join(tempfile.gettempdir(), "openpaperwork-stop")
    os.makedirs(base, exist_ok=True)
    return os.path.join(base, "stop-%s.json" % re.sub(r"[^\w-]", "_", session or "none"))


def decide(chat, session, began, first, written, reply, active, asked=None, uses=None, loaded=None):
    """What goes back to the agent at this stop: the bounce text, or None when the turn may end.

    chat is the agent's folder, began and first when the turn and the chat began (ms), written the paths
    the turn named, reply its last words, active whether this stop follows a bounce; asked the packs the
    turn's ask named (routed()) and uses what the chat's tools were called with, for the net; loaded the packs
    this turn loaded (loaded_packs()), whose checks need no claim."""
    # A reply that ends on a question is waiting for the person, not finished.
    if re.search(r"\?\s*$", (reply or "").strip()):
        return None
    path = state_path(session)
    try:
        state = json.loads(Path(path).read_text())
    except (OSError, ValueError):
        state = {}
    if state.get("turn") != began:
        state = {"turn": began, "bounces": 0, "checked": {}}
    # The net under the hint, once a turn and before any check: a file made without the pack it was asked as
    # is rebuilt with the pack, and the checks then read that file.
    if asked and not state.get("routed"):
        text = net_text(chat, written, began, first, asked, uses, loaded or ())
        if text:
            state.update(routed=True, at=time.time())
            Path(path).write_text(json.dumps(state))
            return text
    spent = state["bounces"] >= MAX_BOUNCES
    if spent and state.get("said"):
        return None
    lines, checked, commands, once = findings(chat, written, began, first, loaded or ())
    # An agent that changes nothing after a red check has made its call; asking again changes nothing.
    if spent or (active and state["checked"] and checked == state["checked"]):
        lines = []
    # Said once a turn: with the first bounce there is, or alone when nothing fails. Never a second time.
    said = "" if state.get("said") else once_text(chat, once["asks"], once["blind"], strays(chat, began))
    if not lines and not said:
        return None
    if lines:
        state["bounces"] += 1
        state["checked"] = checked
    if said:
        state["said"] = True
    state["at"] = time.time()
    Path(path).write_text(json.dumps(state))
    return "\n\n".join(part for part in (bounce_text(state["bounces"], lines, commands) if lines else "", said)
                       if part)


# Set by an app that starts the agent and runs its own pack check at the end of a turn, so a hook the person
# installed for that agent (install.py) stands down there, and nobody is sent back twice for one fault.
APP_ENV = "OPENPAPERWORK_APP"


def main():
    if os.environ.get(APP_ENV):
        return 0
    try:
        data = json.load(sys.stdin)
    except ValueError:
        return 0
    chat = data.get("cwd") or os.getcwd()
    began, first, written, reply = read_turn(data.get("transcript_path"))
    ask, uses = ask_and_uses(data.get("transcript_path"))
    text = decide(chat, data.get("session_id"), began, first, written,
                  data.get("last_assistant_message") or reply or "", data.get("stop_hook_active"),
                  routed(ask), uses, loaded_packs(turn_uses(data.get("transcript_path"), began)))
    if text:
        print(json.dumps({"decision": "block", "reason": text}))
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as exc:  # a hook that breaks must never keep a turn open
        print("openpaperwork pack check hook: %s" % exc, file=sys.stderr)
        sys.exit(0)
