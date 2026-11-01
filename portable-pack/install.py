#!/usr/bin/env python3
"""Put the packs, the hint at the start of a turn and the pack check at its end into the agents on this machine.

  python3 install.py                  for every agent found here: link the packs, add the hook
  python3 install.py --dry-run        print every change, make none
  python3 install.py --project DIR    the same into one folder: DIR/.agents/skills, DIR/.codex/hooks.json, ...
  python3 install.py doctor           agent by agent: are the skills, the plugin and the hook in place
  python3 install.py uninstall        take the links and the hooks out again

  --agents codex,gemini,cursor        only these (an agent whose hook has not run for real is never picked
                                      on its own: name it)
  --no-hooks                          link the packs only
  --no-mcp                            do not add the floor check to Codex as an MCP tool
  --pack DIR                          install a department plugin (plugins/finance) instead of this folder

Where each hook goes is the maker's own documented place (links in docs/community-preview/BRING_YOUR_OWN_AGENT.md):

  Codex              ~/.codex/hooks.json ($CODEX_HOME), or DIR/.codex/hooks.json. Codex runs a hook only
                     after you have trusted it once: start codex and type /hooks.
  Gemini CLI         ~/.gemini/settings.json, or DIR/.gemini/settings.json. Gemini CLI runs hooks only in a
                     folder it trusts.
  Cursor CLI         ~/.cursor/hooks.json, or DIR/.cursor/hooks.json
                     Its sandbox has to be able to read this pack's folder: the home folder is, /tmp is not.
  Claude Code        nothing here: its hooks come inside the plugin (/plugin install)

One hook file does both jobs for these agents (hooks/pack_agents.py). On the event that starts a turn it
notes the start and, when the ask names a kind of file a pack makes, adds one line that says which skill to
load (hooks/pack_route.py): Codex and Gemini CLI take that line; Cursor CLI's prompt hook
can only let a prompt through or stop it, so Cursor gets no hint. On the event that ends a turn it runs the
pack check. Installing, listing and removing the hook covers both, and doctor has a row for each.

The shape is REA's installer (github.com/morluto/rea, MIT; see licenses/rea-mit.txt): one table of agents
with the folder that says an agent is on this machine and the file its settings live in, every change
printed before it is made, a copy of a file kept before it is first changed, only our own entries touched,
and a doctor that reads and never writes. Standard library only.
"""
import argparse
import json
import os
import shlex
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ADAPTER = "hooks/pack_agents.py"            # a hook entry is ours when its command runs this file
ROUTER, TABLE = "hooks/pack_route.py", "hooks/routes.json"   # the hint the adapter gives when a turn starts
# Claude Code's own variable for the room its skill list gets, in characters. With many skills installed the
# list is cut to its default room and a pack stands in it as a bare name, without its description.
LIST_ROOM = "SLASH_COMMAND_TOOL_CHAR_BUDGET"
PROMPT_EVENT = {"codex": "UserPromptSubmit", "gemini": "BeforeAgent", "dsh": "UserPromptSubmit"}
MCP = "openpaperwork-checks"
ROW = "openpaperwork-pack-check"         # our row in a dsh patch
BRIDGE = "@deepseek-ai/dsh-hooks-claude-code"
KEPT = ".before-openpaperwork"
# Cursor CLI's hook is built from the maker's documented format and has not run for real on our side.
# The installer adds it only when it is named with --agents.
NOT_RUN = ("cursor",)


def agents(home, env):
    """The one table: what says the agent is here, and where its hooks live for a person and for a folder."""
    def folder(variable, default):
        return Path(env.get(variable) or home / default)
    codex = folder("CODEX_HOME", ".codex")
    return [
        {"id": "claude", "name": "Claude Code", "bin": "claude", "marker": folder("CLAUDE_CONFIG_DIR", ".claude")},
        {"id": "codex", "name": "Codex", "bin": "codex", "marker": codex,
         "user": codex / "hooks.json", "project": ".codex/hooks.json"},
        {"id": "gemini", "name": "Gemini CLI", "bin": "gemini", "marker": home / ".gemini",
         "user": home / ".gemini" / "settings.json", "project": ".gemini/settings.json"},
        {"id": "cursor", "name": "Cursor CLI", "bin": "cursor-agent", "marker": home / ".cursor",
         "user": home / ".cursor" / "hooks.json", "project": ".cursor/hooks.json"},
    ]


# --- What a hook file holds --------------------------------------------------------------------------

def entries(agent, pack):
    """Our hook entries in the agent's own form: event -> the list that goes under it."""
    def run(event):
        # "|| true": python exits 2 when the file is gone, and to these agents 2 means block or go on.
        return "python3 %s %s %s || true" % (shlex.quote(str(pack / ADAPTER)), agent, event)
    if agent == "gemini":  # timeouts in milliseconds
        return {"BeforeAgent": [{"hooks": [{"name": "openpaperwork-turn-start", "type": "command",
                                            "command": run("BeforeAgent"), "timeout": 30000}]}],
                "AfterAgent": [{"hooks": [{"name": "openpaperwork-pack-check", "type": "command",
                                           "command": run("AfterAgent"), "timeout": 600000}]}]}
    if agent == "cursor":
        return {"beforeSubmitPrompt": [{"command": run("beforeSubmitPrompt"), "timeout": 30}],
                "afterAgentResponse": [{"command": run("afterAgentResponse"), "timeout": 30}],
                "stop": [{"command": run("stop"), "timeout": 600, "loop_limit": 3}]}
    # Codex, and Claude Code's form for the dsh bridge: timeouts in seconds.
    return {"UserPromptSubmit": [{"hooks": [{"type": "command", "command": run("UserPromptSubmit"), "timeout": 30}]}],
            "Stop": [{"hooks": [{"type": "command", "command": run("Stop"), "timeout": 600}]}]}


def ours(handler):
    return isinstance(handler, dict) and ADAPTER in str(handler.get("command", "")).replace("\\", "/")


def without_ours(agent, hooks):
    """The hooks map with our entries taken out; everything else as it was."""
    out = {}
    for event, items in hooks.items():
        if not isinstance(items, list):
            out[event] = items
            continue
        kept = []
        for item in items:
            if agent == "cursor":
                if not ours(item):
                    kept.append(item)
            elif isinstance(item, dict) and isinstance(item.get("hooks"), list) and any(ours(h) for h in item["hooks"]):
                rest = [h for h in item["hooks"] if not ours(h)]
                if rest:
                    kept.append({**item, "hooks": rest})
            else:
                kept.append(item)
        if kept or not items:
            out[event] = kept
    return out


def with_ours(agent, data, pack):
    hooks = without_ours(agent, data.get("hooks") if isinstance(data.get("hooks"), dict) else {})
    for event, items in entries(agent, pack).items():
        hooks[event] = list(hooks.get(event) or []) + items
    out = dict(data)
    if agent == "cursor":
        out.setdefault("version", 1)
    out["hooks"] = hooks
    return out


def state_of(agent, data, pack):
    """ok when our entries are there and run this pack's adapter, stale when they run another copy."""
    hooks = data.get("hooks") if isinstance(data, dict) and isinstance(data.get("hooks"), dict) else {}
    want = entries(agent, pack)
    found = [h for items in hooks.values() if isinstance(items, list) for item in items
             for h in ([item] if agent == "cursor" else (item.get("hooks") or []) if isinstance(item, dict) else [])
             if ours(h)]
    if not found:
        return "missing"
    for event, items in want.items():
        commands = [h.get("command") for item in items for h in ([item] if agent == "cursor" else item["hooks"])]
        have = [h.get("command") for h in found]
        if any(c not in have for c in commands):
            return "stale"
    return "ok"


# --- Files -------------------------------------------------------------------------------------------

def read_json(path):
    """(data, None), ({}, None) for no file, or (None, why) when the file is there and is not plain JSON."""
    try:
        text = Path(path).read_text(encoding="utf-8")
    except FileNotFoundError:
        return {}, None
    except OSError as exc:
        return None, str(exc)
    if not text.strip():
        return {}, None
    try:
        data = json.loads(text)
    except ValueError as exc:
        return None, "not plain JSON (%s)" % exc
    return (data, None) if isinstance(data, dict) else (None, "not a JSON object")


def write(path, text, plan, dry):
    path = Path(path)
    new = not path.exists()
    if not new and path.read_text(encoding="utf-8") == text:
        return
    plan.append("%s %s" % ("create" if new else "change", path) + ("" if new else " (a copy stays in %s%s)" % (path.name, KEPT)))
    if dry:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    kept = path.with_name(path.name + KEPT)
    if not new and not kept.exists():
        shutil.copy2(path, kept)
    tmp = path.with_name(path.name + ".tmp-openpaperwork")
    tmp.write_text(text, encoding="utf-8")
    os.replace(tmp, path)


def dump(data):
    return json.dumps(data, indent=2, ensure_ascii=False) + "\n"


# --- dsh: a patch that mounts its Claude Code hook bridge --------------------------------

def patch_rows(text):
    """A patch file as (comment lines, list), or None when it holds YAML we will not rewrite."""
    lines = text.splitlines()
    comments = [line for line in lines if line.lstrip().startswith("#")]
    body = "\n".join(line for line in lines if line.strip() and not line.lstrip().startswith("#")).strip()
    if not body:
        return comments, []
    try:
        rows = json.loads(body)
    except ValueError:
        return None
    return (comments, rows) if isinstance(rows, list) else None


def patch_without_ours(rows):
    out = []
    for row in rows:
        if isinstance(row, dict) and isinstance(row.get("insert"), list):
            rest = [r for r in row["insert"] if not (isinstance(r, dict) and r.get("id") == ROW)]
            if len(rest) != len(row["insert"]):
                if rest:
                    out.append({**row, "insert": rest})
                continue
        out.append(row)
    return out


def patch_has_ours(rows, hooks_file):
    for row in rows:
        for r in (row.get("insert") or []) if isinstance(row, dict) and isinstance(row.get("insert"), list) else []:
            if isinstance(r, dict) and r.get("id") == ROW:
                return "ok" if (r.get("config") or {}).get("configPath") == str(hooks_file) else "stale"
    return "missing"


def dsh_files(agent, project):
    """(the hooks file the bridge reads, the patch that mounts it, the patch to fall back on)."""
    if project:
        base = Path(project) / ".dsh"
        return base / "openpaperwork-hooks.json", base / "openpaperwork.patch.yml", None
    base = agent["marker"]
    return base / "openpaperwork-hooks.json", agent["user"], base / "openpaperwork.patch.yml"


def dsh_row(hooks_file, pack):
    return {"id": ROW, "name": BRIDGE, "config": {"configPath": str(hooks_file), "pluginRoot": str(pack)}}


def install_dsh(agent, pack, project, plan, notes, dry):
    hooks_file, patch, spare = dsh_files(agent, project)
    write(hooks_file, dump({"hooks": entries("dsh", pack)}), plan, dry)
    row = dsh_row(hooks_file, pack)
    notes.append("dsh: this hook has run in the harness itself (0.1.6-alpha.2) against a scripted "
                 "stand-in for the model, and not yet with a model. Its sandbox must be able to read %s (the home "
                 "folder is, /tmp is not), and it keeps the turn's notes in .openpaperwork/ in the folder you "
                 "work in." % pack)
    start = "dsh <profile> --patch %s" % shlex.quote(str(spare or patch))
    if project:
        write(patch, dump([{"insert": [row]}]), plan, dry)
        notes.append("dsh reads no hooks from a folder by itself. Start it with the patch: %s" % start)
        return
    parsed = patch_rows(patch.read_text(encoding="utf-8")) if patch.exists() else ([], [])
    if parsed is None:
        write(spare, dump([{"insert": [row]}]), plan, dry)
        notes.append("%s holds YAML this installer does not rewrite. Start dsh with the patch "
                     "instead: %s" % (patch, start))
        return
    comments, rows = parsed
    text = "".join(line + "\n" for line in comments) + dump(patch_without_ours(rows) + [{"insert": [row]}])
    write(patch, text, plan, dry)


def uninstall_dsh(agent, project, plan, dry):
    hooks_file, patch, spare = dsh_files(agent, project)
    for extra in (hooks_file, spare, patch if project else None):
        if extra and Path(extra).exists():
            plan.append("remove %s" % extra)
            if not dry:
                Path(extra).unlink()
    if project or not patch.exists():
        return
    parsed = patch_rows(patch.read_text(encoding="utf-8"))
    if parsed and patch_has_ours(parsed[1], hooks_file) != "missing":
        write(patch, "".join(line + "\n" for line in parsed[0]) + dump(patch_without_ours(parsed[1])), plan, dry)


# --- Skills ------------------------------------------------------------------------------------------

def skill_folders(pack):
    return sorted(p for p in (pack / "skills").iterdir() if p.is_dir())


def skills_root(home, env, project):
    return Path(project) / ".agents" / "skills" if project else home / ".agents" / "skills"


def link_skills(pack, root, plan, notes, dry):
    for source in skill_folders(pack):
        link = root / source.name
        if link.is_symlink():
            if Path(os.path.realpath(link)) == source.resolve():
                continue
        elif link.exists():
            notes.append("%s is a folder of your own, not a link: left as it is" % link)
            continue
        plan.append("link %s -> %s" % (link, source))
        if dry:
            continue
        root.mkdir(parents=True, exist_ok=True)
        if link.is_symlink():
            link.unlink()
        link.symlink_to(source, target_is_directory=True)


def unlink_skills(pack, root, plan, dry):
    for source in skill_folders(pack):
        link = root / source.name
        if link.is_symlink() and Path(os.path.realpath(link)) == source.resolve():
            plan.append("remove the link %s" % link)
            if not dry:
                link.unlink()


def skills_state(pack, root):
    folders = skill_folders(pack)
    here = [s for s in folders if (root / s.name).is_symlink()
            and Path(os.path.realpath(root / s.name)) == s.resolve()]
    elsewhere = [s for s in folders if (root / s.name).exists() and s not in here]
    if len(here) == len(folders):
        return "ok", "%d folders linked in %s" % (len(here), root)
    if here or elsewhere:
        return "stale", "%d of %d folders in %s come from this pack, %d from somewhere else" % (
            len(here), len(folders), root, len(elsewhere))
    return "missing", "nothing of this pack in %s" % root


# --- The three commands ------------------------------------------------------------------------------

def found(agent):
    return bool(shutil.which(agent["bin"])) or agent["marker"].is_dir()


def chosen(table, names):
    """The agents to give a hook: the named ones, or every agent found here whose hook has run for real."""
    hookable = [a for a in table if "user" in a]
    if names:
        unknown = [n for n in names if n not in [a["id"] for a in hookable]]
        if unknown:
            raise SystemExit("unknown agent: %s (codex, gemini, cursor)" % ", ".join(unknown))
        return [a for a in hookable if a["id"] in names]
    return [a for a in hookable if found(a) and a["id"] not in NOT_RUN]


def hook_file(agent, project):
    return Path(project) / agent["project"] if project else agent["user"]


def install(args, home, env):
    pack, project, dry = args.pack, args.project, args.dry_run
    plan, notes = [], []
    link_skills(pack, skills_root(home, env, project), plan, notes, dry)
    table = agents(home, env)
    if not args.no_hooks:
        for agent in chosen(table, args.agents):
            path = hook_file(agent, project)
            data, why = read_json(path)
            if data is None:
                notes.append("%s: %s is %s; left as it is. Add this by hand:\n%s" % (
                    agent["name"], path, why, dump({"hooks": entries(agent["id"], pack)})))
                continue
            write(path, dump(with_ours(agent["id"], data, pack)), plan, dry)
            if agent["id"] == "codex":
                notes.append("Codex runs a hook only after you have trusted it: start codex, type /hooks and "
                             "trust the two OpenPaperwork hooks. In a folder, Codex must also trust the folder.")
            if agent["id"] == "gemini":
                notes.append("Gemini CLI runs hooks only in a folder it trusts. Headless, start it with "
                             "GEMINI_CLI_TRUST_WORKSPACE=true set; its --skip-trust flag comes too late for hooks.")
            if agent["id"] in NOT_RUN:
                notes.append("%s: this hook follows the maker's documented format and has not yet run for real "
                             "on our side." % agent["name"])
    mcp = None
    if not args.no_mcp and not project and (pack / "mcp" / "server.py").is_file() and shutil.which("codex"):
        mcp = ["codex", "mcp", "add", MCP, "--", "python3", str(pack / "mcp" / "server.py")]
        plan.append("run " + " ".join(shlex.quote(part) for part in mcp))
    print("\n".join(plan) if plan else "Nothing to change: everything is in place.")
    if mcp and not dry:
        subprocess.run(mcp, check=False)
    for note in notes:
        print("\n" + note)
    if dry:
        print("\nDry run: nothing was changed.")
    else:
        print("\nDone. python3 %s doctor shows what is in place." % shlex.quote(str(HERE / "install.py")))
    return 0


def uninstall(args, home, env):
    pack, project, dry = args.pack, args.project, args.dry_run
    plan = []
    unlink_skills(pack, skills_root(home, env, project), plan, dry)
    table = agents(home, env)
    names = args.agents or [a["id"] for a in table if "user" in a]
    for agent in chosen(table, names):
        if agent["id"] == "dsh":
            uninstall_dsh(agent, project, plan, dry)
            continue
        path = hook_file(agent, project)
        data, why = read_json(path)
        if data and state_of(agent["id"], data, pack) != "missing":
            out = dict(data)
            out["hooks"] = without_ours(agent["id"], data["hooks"])
            write(path, dump(out), plan, dry)
    if not args.no_mcp and not project and shutil.which("codex"):
        plan.append("run codex mcp remove %s" % MCP)
        if not dry:
            subprocess.run(["codex", "mcp", "remove", MCP], check=False)
    print("\n".join(plan) if plan else "Nothing of ours was there.")
    if dry:
        print("\nDry run: nothing was changed.")
    return 0


def version(agent):
    path = shutil.which(agent["bin"])
    if not path:
        return None
    try:
        out = subprocess.run([path, "--version"], capture_output=True, text=True, timeout=20)
        return (out.stdout or out.stderr).strip().splitlines()[0][:60]
    except (OSError, subprocess.SubprocessError, IndexError):
        return "on PATH"


def examine(args, home, env):
    """Every agent with its rows: part, state (ok, missing, stale, invalid, manual, none), detail, fix."""
    pack, project = args.pack, args.project
    me = ("python3 %s" % shlex.quote(str(HERE / "install.py"))
          + (" --pack %s" % shlex.quote(str(pack)) if pack != HERE else "")
          + (" --project %s" % shlex.quote(str(project)) if project else ""))
    skills = skills_state(pack, skills_root(home, env, project))
    report = []
    for agent in agents(home, env):
        rows = []
        ident = agent["id"]
        if ident == "claude":
            listed = read_json(agent["marker"] / "plugins" / "installed_plugins.json")[0] or {}
            names = sorted(n for n in (listed.get("plugins") or {}) if "openpaperwork" in n)
            fix = "in Claude Code: /plugin marketplace add ActuallyNodejam/openpaperwork, then /plugin install openpaperwork"
            if names:
                rows.append(("skills", "ok", "come with the plugin", None))
                rows.append(("plugin", "ok", ", ".join(names), None))
                rows.append(("hook", "ok", "comes with the plugin (hooks/hooks.json)", None))
                rows.append(("hint", "ok", "comes with the plugin (hooks/hooks.json, on UserPromptSubmit)", None))
                settings = read_json(agent["marker"] / "settings.json")[0] or {}
                room = env.get(LIST_ROOM) or (settings.get("env") or {}).get(LIST_ROOM)
                if room:
                    rows.append(("list", "ok", "%s is %s: room for the packs' descriptions in the skill list" % (LIST_ROOM, room), None))
                else:
                    rows.append(("list", "none", "the skill list has its default room: with many skills installed a "
                                 "pack stands in it as a bare name, and the hint is what names the skill", "to give "
                                 "the list more room, set \"env\": {\"%s\": \"30000\"} in %s (a longer list at the "
                                 "start of every chat)" % (LIST_ROOM, agent["marker"] / "settings.json")))
            else:
                rows.append(("skills", "missing", "come with the plugin", None))
                rows.append(("plugin", "missing", "no OpenPaperwork plugin is installed", fix))
                rows.append(("hook", "missing", "comes with the plugin", None))
                rows.append(("hint", "missing", "comes with the plugin", None))
        else:
            rows.append(("skills", skills[0], skills[1], None if skills[0] == "ok" else me))
            rows.append(("plugin", "none", "not needed: this agent takes the packs as skills", None))
            fix = "%s --agents %s" % (me, ident)
            if ident == "dsh":
                hooks_file, patch, spare = dsh_files(agent, project)
                parsed = patch_rows(patch.read_text(encoding="utf-8")) if patch.exists() else ([], [])
                state = patch_has_ours(parsed[1], hooks_file) if parsed else "missing"
                if state != "missing" and not hooks_file.exists():
                    state = "stale"
                start = "start it with: dsh <profile> --patch %s" % shlex.quote(str(patch if project else spare))
                if project and state == "ok":
                    rows.append(("hook", "manual", "the patch is written; dsh reads none from a folder by itself", start))
                elif state == "missing" and spare and spare.exists():
                    rows.append(("hook", "manual", "%s holds YAML this installer does not rewrite" % patch, start))
                else:
                    rows.append(("hook", state, "%s; run against a scripted stand-in for the model, not yet with "
                                 "a model" % patch, None if state == "ok" else fix))
            else:
                path = hook_file(agent, project)
                data, why = read_json(path)
                if data is None:
                    rows.append(("hook", "invalid", "%s is %s" % (path, why), "add the hook by hand; %s --dry-run prints it" % me))
                else:
                    state = state_of(ident, data, pack)
                    detail = str(path)
                    if state == "ok" and ident == "codex":
                        detail += "; Codex runs it only once you have trusted it (start codex, /hooks)"
                    if ident == "gemini" and state == "ok":
                        detail += "; Gemini CLI runs it only in a folder it trusts"
                    if ident in NOT_RUN:
                        detail += "; built from the maker's documented format, not yet run for real on our side"
                    rows.append(("hook", state, detail, None if state == "ok" else fix))
            # The hint rides in the same hook file, on the event that starts a turn.
            state = rows[-1][1]
            if ident == "cursor":
                rows.append(("hint", "none", "Cursor CLI's prompt hook cannot add to a turn: no hint at the start, "
                             "the net at the end of the turn runs with the hook", None))
            elif not (pack / ROUTER).is_file() or not (pack / TABLE).is_file():
                rows.append(("hint", "missing", "this pack folder has no %s or no %s" % (ROUTER, TABLE),
                             "build the plugins again: python3 scripts/build-portable-pack.py"))
            else:
                rows.append(("hint", state, "which skill makes the kind of file an ask names, given by the hook "
                             "above on %s" % PROMPT_EVENT[ident], None if state in ("ok", "manual") else fix))
            if ident == "codex" and not project:
                try:
                    registered = ("[mcp_servers.%s]" % MCP) in (agent["marker"] / "config.toml").read_text(encoding="utf-8")
                except OSError:
                    registered = False
                rows.append(("mcp", "ok" if registered else "missing", "the floor check as the tool %s" % MCP,
                             None if registered else me))
        report.append({"id": ident, "name": agent["name"], "found": found(agent), "version": version(agent),
                       "rows": [{"part": p, "state": s, "detail": d, "fix": f} for p, s, d, f in rows]})
    return report


def doctor(args, home, env):
    report = examine(args, home, env)
    if args.json:
        print(json.dumps(report, indent=2))
        return 0
    for agent in report:
        if not agent["found"]:
            print("%-17s not on this machine" % agent["name"])
            continue
        print("%-17s %s" % (agent["name"], agent["version"] or "its folder is here, the command is not on PATH"))
        for row in agent["rows"]:
            print("  %-7s %-8s %s" % (row["part"], "-" if row["state"] == "none" else row["state"], row["detail"]))
            if row["fix"]:
                print("  %-7s %-8s fix: %s" % ("", "", row["fix"]))
    print("\nIn Claude Code a fail goes back to the agent through the plugin; in the others through the hook above.\n"
          "Where a hook is missing, the pack's own instruction asks the agent to run the check.\n"
          "The hint is one line at the start of a turn that names the skill for the kind of file asked for.")
    return 0


def main(argv):
    parser = argparse.ArgumentParser(prog="install.py", description=__doc__.split("\n\n")[0],
                                     formatter_class=argparse.RawDescriptionHelpFormatter,
                                     epilog="\n\n".join(__doc__.split("\n\n")[1:]))
    parser.add_argument("command", nargs="?", default="install", choices=["install", "doctor", "uninstall"])
    parser.add_argument("--agents", type=lambda text: [part for part in text.replace(" ", "").split(",") if part and part != "all"] or
                        ["codex", "gemini", "cursor", "dsh"], default=None)
    parser.add_argument("--project", type=lambda text: Path(text).resolve(), default=None)
    parser.add_argument("--pack", type=lambda text: Path(text).resolve(), default=HERE)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--no-hooks", action="store_true")
    parser.add_argument("--no-mcp", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    if not (args.pack / "skills").is_dir() or not (args.pack / ADAPTER).is_file():
        raise SystemExit("%s is not a pack folder: it has no skills/ and %s" % (args.pack, ADAPTER))
    if args.project and not args.project.is_dir():
        raise SystemExit("%s is not a folder" % args.project)
    env = os.environ
    home = Path(env.get("HOME") or Path.home())
    return {"install": install, "doctor": doctor, "uninstall": uninstall}[args.command](args, home, env)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
