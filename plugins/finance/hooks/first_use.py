#!/usr/bin/env python3
"""Claude Code SessionStart hook: the plugin sets its own Python up, once, into the plugin's data folder.

Claude Code hands every hook CLAUDE_PLUGIN_DATA, this plugin's persistent data folder under the
person's home, kept across updates, and hands it to hook commands only (plugins-reference, "Plugin
data directory"; claude-mem's plugin installs its own dependencies at session start the same way).
The first session after an install or an update makes a virtual environment there, installs
requirements.txt into it and downloads Playwright's Chromium beside it, then writes a version
marker (.setup-<version>). Every later session finds the marker and returns in a few milliseconds.

The Stop hook's check (pack_stop.py) puts this Python on PATH, and the context line below tells the
agent to run the packs' own scripts with the same interpreter, so a run needs no clone, no pip and
no doctor by hand. Poppler is a system tool: when it is missing the line carries the doctor's one
sudo line and installs nothing. Standard library only. Never raises: a broken setup is one context
line, and the next session tries again."""
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

MAX_SECONDS = 540  # hooks.json gives this hook 600; keep the rest for the reply


def run(cmd, env=None):
    return subprocess.run(cmd, capture_output=True, text=True, timeout=MAX_SECONDS,
                          env=dict(os.environ, **(env or {})))


def poppler_line():
    if shutil.which("pdftotext"):
        return ""
    if sys.platform == "darwin":
        return " pdftotext is missing: brew install poppler."
    return " pdftotext is missing: sudo apt install poppler-utils (dnf install poppler-utils on Fedora)."


def bake_browsers_path(venv, browsers):
    """One .pth so any script on this venv finds the Chromium beside it, with no env set."""
    for site in venv.glob("lib/python3.*/site-packages"):
        (site / "zzz-openpaperwork-browsers.pth").write_text(
            'import os; os.environ.setdefault("PLAYWRIGHT_BROWSERS_PATH", %r)\n' % str(browsers),
            encoding="utf-8")
        return


# Said as the plugin's own report, with the reason: a bare "run with this Python" read to the Claude app as an
# instruction planted in a tool result, and it went on without it (Claude app run of 2026-11-01).
SOURCE = "OpenPaperwork plugin, from its own setup hook: "


def tell(line):
    print(json.dumps({"hookSpecificOutput": {"hookEventName": "SessionStart", "additionalContext": SOURCE + line}}))


def say(py, note):
    tell("this plugin installed the packs' Python packages and its own Chromium into " + str(py) + ". The packs'"
         " scripts need those packages, so run them with that interpreter." + note)


def not_ready(why):
    # Never point at the plugin's Python here: it is not ready, and the Stop hook's check leaves it alone too.
    tell("its first-time setup did not finish (" + why + "), so its own Python is not ready. Run the packs'"
         " scripts with python3; the next session tries the setup again." + poppler_line())


def main():
    data, root = os.environ.get("CLAUDE_PLUGIN_DATA"), os.environ.get("CLAUDE_PLUGIN_ROOT")
    if not data or not root:
        return  # not a Claude Code plugin run: the other agents' installers do this job
    data, root = Path(data), Path(root)
    try:
        version = json.loads((root / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8"))["version"]
    except Exception:
        version = "0"
    marker, venv = data / (".setup-" + version), data / "venv"
    py, browsers = venv / "bin" / "python", data / "ms-playwright"
    if marker.exists():
        say(py, poppler_line())
        return
    steps = []
    if not (venv / "pyvenv.cfg").exists():
        steps.append([sys.executable, "-m", "venv", str(venv)])
    steps.append([str(py), "-m", "pip", "install", "--quiet", "--no-input", "-r", str(root / "requirements.txt")])
    steps.append([str(py), "-m", "playwright", "install", "chromium"])
    for step in steps:
        try:
            done = run(step, {"PLAYWRIGHT_BROWSERS_PATH": str(browsers)})
            if done.returncode != 0:
                why = ((done.stderr or done.stdout).strip().splitlines() or ["?"])[-1][:200]
                not_ready(why)
                return
        except Exception as err:
            not_ready(str(err)[:200])
            return
    bake_browsers_path(venv, browsers)
    marker.write_text("requirements.txt and Chromium for " + version + "\n", encoding="utf-8")
    say(py, poppler_line())


if __name__ == "__main__":
    try:
        main()
    except Exception:
        pass  # a hook never blocks the session on its own setup
