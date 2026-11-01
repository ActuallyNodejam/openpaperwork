"""The plugin's setup hook: what it tells the agent, and the Python the Stop hook's check runs with.

Run from the repository root: python3 -m unittest portable-pack/tests/test_first_use.py
"""
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

HOOKS = Path(__file__).resolve().parents[1] / "hooks"
sys.path.insert(0, str(HOOKS))
import pack_stop


class SetupHook(unittest.TestCase):
    def context(self, data, root):
        env = dict(os.environ, CLAUDE_PLUGIN_DATA=str(data), CLAUDE_PLUGIN_ROOT=str(root))
        out = subprocess.run([sys.executable, str(HOOKS / "first_use.py")], capture_output=True, text=True,
                             env=env, timeout=60).stdout
        return json.loads(out)["hookSpecificOutput"]["additionalContext"]

    def test_a_failed_setup_never_names_its_python(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d) / "plugin"
            (root / ".claude-plugin").mkdir(parents=True)
            (root / ".claude-plugin" / "plugin.json").write_text(json.dumps({"version": "9.9.9"}))
            (root / "requirements.txt").write_text("no-such-package-openpaperwork==0\n")
            line = self.context(Path(d) / "data", root)
            self.assertTrue(line.startswith("OpenPaperwork plugin, from its own setup hook: "), line)
            self.assertIn("did not finish", line)
            self.assertNotIn("venv", line)
            self.assertIn("python3", line)

    def test_a_finished_setup_says_whose_python_and_why(self):
        with tempfile.TemporaryDirectory() as d:
            root, data = Path(d) / "plugin", Path(d) / "data"
            (root / ".claude-plugin").mkdir(parents=True)
            (root / ".claude-plugin" / "plugin.json").write_text(json.dumps({"version": "9.9.9"}))
            data.mkdir()
            (data / ".setup-9.9.9").write_text("done\n")
            line = self.context(data, root)
            self.assertIn(str(data / "venv" / "bin" / "python"), line)
            self.assertIn("need those packages", line)


class CheckPython(unittest.TestCase):
    def test_a_venv_without_the_marker_stays_off_path(self):
        with tempfile.TemporaryDirectory() as d:
            (Path(d) / "venv" / "bin").mkdir(parents=True)
            with mock.patch.dict(os.environ, {"CLAUDE_PLUGIN_DATA": d}):
                self.assertNotIn(str(Path(d) / "venv" / "bin"), pack_stop.plugin_env()["PATH"])
                (Path(d) / ".setup-0.1.0").write_text("done\n")
                self.assertTrue(pack_stop.plugin_env()["PATH"].startswith(str(Path(d) / "venv" / "bin")))


if __name__ == "__main__":
    unittest.main()
