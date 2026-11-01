#!/bin/sh
# Load the packs into Codex, Gemini CLI and Cursor CLI: all three read skills from
# ~/.agents/skills, so the packs are linked there. The check modules (_checks) and the shared letter
# (_shared) are linked beside them because the packs import them; neither has a SKILL.md, so no agent
# lists them as a skill. With Codex installed, the floor check is also registered as an MCP tool (skip
# with --no-mcp). For Codex and Gemini CLI, where they are on this machine, the pack
# check is added as a hook at the end of a turn (skip with --no-hooks; see what would change with --dry-run).
# All of it is install.py beside this file: python3 install.py doctor says what is in place,
# python3 install.py uninstall takes it out again.
set -e
PACK=$(cd "$(dirname "$0")" && pwd)
exec python3 "$PACK/install.py" install "$@"
