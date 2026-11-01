#!/usr/bin/env python3
"""Run the pack checks from a shell when the openpaperwork-checks tool is not available.

Usage: check_file.py FILE [--kit KIT.json] [--slides N]
"""
import runpy
import sys
from pathlib import Path

server = Path(__file__).resolve().parents[3] / 'mcp' / 'server.py'
sys.argv = [str(server), '--check'] + sys.argv[1:]
runpy.run_path(str(server), run_name='__main__')
