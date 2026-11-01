"""The installer: the packs linked, the hook written into each agent's own file, a doctor that only reads.

Every test runs install.py with HOME set to an empty folder and a PATH that holds only sh, python3 and
dirname, so no agent on this machine is seen and nothing on it is read or changed.
Run from the repository root: python3 -m unittest portable-pack/tests/test_install.py
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

PACK = Path(__file__).resolve().parent.parent
INSTALL = PACK / "install.py"
INPUTS = Path(__file__).resolve().parent / "hook-inputs"
ALL = "codex,gemini,cursor"


class Installer(unittest.TestCase):
    def setUp(self):
        self.home = Path(tempfile.mkdtemp())
        tools = Path(tempfile.mkdtemp())
        for tool in ("sh", "dirname"):
            os.symlink(shutil.which(tool), tools / tool)
        os.symlink(sys.executable, tools / "python3")
        self.env = {"HOME": str(self.home), "PATH": str(tools)}

    def run_it(self, *args, script=None):
        command = ["sh", str(script)] if script else [sys.executable, str(INSTALL)]
        p = subprocess.run([*command, *args], capture_output=True, text=True, env=self.env)
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        return p.stdout

    def doctor(self, *args):
        report = json.loads(self.run_it("doctor", "--json", *args))
        return {a["id"]: {r["part"]: r["state"] for r in a["rows"]} for a in report}

    def commands(self, path, cursor=False):
        hooks = json.loads(Path(path).read_text())["hooks"]
        return {event: [h["command"] for item in items for h in ([item] if cursor else item["hooks"])]
                for event, items in hooks.items()}

    def test_install_links_the_packs_and_writes_each_agents_own_hook_file(self):
        out = self.run_it("--agents", ALL, "--no-mcp")
        links = sorted(p.name for p in (self.home / ".agents/skills").iterdir())
        self.assertEqual(links, sorted(p.name for p in (PACK / "skills").iterdir() if p.is_dir()))
        self.assertTrue((self.home / ".agents/skills/e-invoice/SKILL.md").is_file())
        adapter = str(PACK / "hooks/pack_agents.py")
        codex = self.commands(self.home / ".codex/hooks.json")
        self.assertEqual(sorted(codex), ["Stop", "UserPromptSubmit"])
        self.assertEqual(codex["Stop"], ["python3 %s codex Stop || true" % adapter])
        gemini = json.loads((self.home / ".gemini/settings.json").read_text())["hooks"]
        self.assertEqual(sorted(gemini), ["AfterAgent", "BeforeAgent"])
        self.assertEqual(gemini["AfterAgent"][0]["hooks"][0]["timeout"], 600000)
        cursor = json.loads((self.home / ".cursor/hooks.json").read_text())
        self.assertEqual(cursor["version"], 1)
        self.assertEqual(sorted(cursor["hooks"]), ["afterAgentResponse", "beforeSubmitPrompt", "stop"])
        self.assertEqual(cursor["hooks"]["stop"][0]["loop_limit"], 3)
        self.assertIn("trusted", out)
        self.assertIn("not yet run for real", out)

    def test_what_was_there_stays_and_a_copy_is_kept(self):
        (self.home / ".codex").mkdir()
        theirs = {"hooks": {"Stop": [{"hooks": [{"type": "command", "command": "sh ~/mine.sh"}]}],
                            "PreToolUse": [{"matcher": "Bash", "hooks": [{"type": "command", "command": "sh ~/guard.sh"}]}]}}
        (self.home / ".codex/hooks.json").write_text(json.dumps(theirs))
        (self.home / ".gemini").mkdir()
        (self.home / ".gemini/settings.json").write_text(json.dumps({"security": {"auth": {"selectedType": "gemini-api-key"}}}))
        self.run_it("--agents", ALL, "--no-mcp")
        self.run_it("--agents", ALL, "--no-mcp")
        codex = self.commands(self.home / ".codex/hooks.json")
        self.assertEqual(codex["Stop"][0], "sh ~/mine.sh")
        self.assertEqual(len(codex["Stop"]), 2)
        self.assertEqual(codex["PreToolUse"], ["sh ~/guard.sh"])
        self.assertEqual(json.loads((self.home / ".codex/hooks.json.before-openpaperwork").read_text()), theirs)
        gemini = json.loads((self.home / ".gemini/settings.json").read_text())
        self.assertEqual(gemini["security"]["auth"]["selectedType"], "gemini-api-key")
        self.assertEqual(len(gemini["hooks"]["AfterAgent"]), 1)
        self.assertIn("Nothing to change", self.run_it("--agents", ALL, "--no-mcp"))

    def test_a_dry_run_changes_nothing(self):
        out = self.run_it("--agents", ALL, "--no-mcp", "--dry-run")
        self.assertIn("create %s" % (self.home / ".codex/hooks.json"), out)
        self.assertIn("nothing was changed", out)
        self.assertEqual(list(self.home.iterdir()), [])

    def test_a_file_that_is_not_plain_json_is_left_alone(self):
        (self.home / ".gemini").mkdir()
        text = '{\n  // my comment\n  "theme": "dark"\n}\n'
        (self.home / ".gemini/settings.json").write_text(text)
        out = self.run_it("--agents", "gemini", "--no-mcp")
        self.assertEqual((self.home / ".gemini/settings.json").read_text(), text)
        self.assertIn("left as it is", out)
        self.assertEqual(self.doctor()["gemini"]["hook"], "invalid")

    def test_the_doctor_says_what_is_in_place_and_only_reads(self):
        before = self.doctor()
        self.assertEqual(list(self.home.iterdir()), [])
        for agent in ("codex", "gemini", "cursor"):
            self.assertEqual(before[agent]["skills"], "missing")
            self.assertEqual(before[agent]["hook"], "missing")
            self.assertEqual(before[agent]["plugin"], "none")
        self.assertEqual(before["claude"], {"skills": "missing", "plugin": "missing", "hook": "missing", "hint": "missing"})
        # The hint at the start of a turn rides in the same hook: missing with it, there with it.
        self.assertEqual({agent: before[agent]["hint"] for agent in ("codex", "gemini")},
                         {"codex": "missing", "gemini": "missing"})
        self.run_it("--agents", ALL, "--no-mcp")
        after = self.doctor()
        for agent in ("codex", "gemini", "cursor"):
            self.assertEqual(after[agent]["skills"], "ok")
            self.assertEqual(after[agent]["hook"], "ok")
        self.assertEqual({agent: after[agent]["hint"] for agent in ("codex", "gemini")},
                         {"codex": "ok", "gemini": "ok"})
        # Cursor CLI's prompt hook cannot add to a turn: the doctor says so, before and after.
        self.assertEqual((before["cursor"]["hint"], after["cursor"]["hint"]), ("none", "none"))
        self.assertIn("Cursor CLI's prompt hook cannot add to a turn", self.run_it("doctor"))
        self.run_it("uninstall", "--agents", ALL, "--no-mcp")
        gone = self.doctor()
        self.assertEqual({agent: gone[agent]["hint"] for agent in ("codex", "gemini")},
                         {"codex": "missing", "gemini": "missing"})
        self.run_it("--agents", ALL, "--no-mcp")
        self.assertEqual(after["codex"]["mcp"], "missing")
        text = self.run_it("doctor")
        self.assertIn("trusted", text)
        self.assertIn("not yet run for real", text)

    def test_the_doctor_knows_a_hook_that_runs_another_copy(self):
        self.run_it("--agents", "codex", "--no-mcp")
        path = self.home / ".codex/hooks.json"
        path.write_text(path.read_text().replace(str(PACK), "/somewhere/else/portable-pack"))
        self.assertEqual(self.doctor()["codex"]["hook"], "stale")
        self.run_it("--agents", "codex", "--no-mcp")
        self.assertEqual(self.doctor()["codex"]["hook"], "ok")
        self.assertEqual(len(self.commands(path)["Stop"]), 1)

    def test_a_claude_code_plugin_is_seen(self):
        (self.home / ".claude/plugins").mkdir(parents=True)
        (self.home / ".claude/plugins/installed_plugins.json").write_text(json.dumps(
            {"version": 2, "plugins": {"openpaperwork-finance@openpaperwork": [{"scope": "user"}]}}))
        self.assertEqual(self.doctor()["claude"], {"skills": "ok", "plugin": "ok", "hook": "ok", "hint": "ok", "list": "none"})
        self.assertIn("SLASH_COMMAND_TOOL_CHAR_BUDGET", self.run_it("doctor"))
        # The room for the skill list, raised in Claude Code's own settings, is seen; nothing is written.
        (self.home / ".claude/settings.json").write_text(json.dumps({"env": {"SLASH_COMMAND_TOOL_CHAR_BUDGET": "30000"}}))
        self.assertEqual(self.doctor()["claude"]["list"], "ok")
        self.assertEqual(json.loads((self.home / ".claude/settings.json").read_text()),
                         {"env": {"SLASH_COMMAND_TOOL_CHAR_BUDGET": "30000"}})

    def test_uninstall_takes_out_ours_and_only_ours(self):
        (self.home / ".cursor").mkdir()
        (self.home / ".cursor/hooks.json").write_text(json.dumps({"version": 1, "hooks": {"stop": [{"command": "./mine.sh"}]}}))
        self.run_it("--agents", ALL, "--no-mcp")
        self.run_it("uninstall", "--no-mcp")
        self.assertEqual(json.loads((self.home / ".cursor/hooks.json").read_text()),
                         {"version": 1, "hooks": {"stop": [{"command": "./mine.sh"}]}})
        self.assertEqual(json.loads((self.home / ".codex/hooks.json").read_text()), {"hooks": {}})
        self.assertEqual(list((self.home / ".agents/skills").iterdir()), [])
        after = self.doctor()
        self.assertEqual([after[a]["hook"] for a in ("codex", "gemini", "cursor")], ["missing"] * 3)

    def test_a_folder_gets_its_own_hooks_and_the_home_none(self):
        work = Path(tempfile.mkdtemp())
        out = self.run_it("--project", str(work), "--agents", ALL)
        self.assertEqual(list(self.home.iterdir()), [])
        self.assertTrue((work / ".agents/skills/e-invoice/SKILL.md").is_file())
        self.assertTrue((work / ".codex/hooks.json").is_file())
        self.assertTrue((work / ".gemini/settings.json").is_file())
        self.assertTrue((work / ".cursor/hooks.json").is_file())
        state = self.doctor("--project", str(work))
        self.assertEqual([state[a]["hook"] for a in ("codex", "gemini", "cursor")], ["ok", "ok", "ok"])

    def test_no_agent_is_picked_unless_it_is_here_and_its_hook_has_run(self):
        self.run_it("--no-mcp")
        self.assertFalse((self.home / ".codex").exists())
        for folder in (".codex", ".gemini", ".cursor"):
            (self.home / folder).mkdir()
        self.run_it("--no-mcp")
        self.assertTrue((self.home / ".codex/hooks.json").is_file())
        self.assertTrue((self.home / ".gemini/settings.json").is_file())
        self.assertFalse((self.home / ".cursor/hooks.json").exists())

    def test_a_hook_whose_pack_is_gone_never_blocks(self):
        """python exits 2 for a file that is not there, and to these agents exit 2 means block or go on."""
        self.run_it("--agents", ALL, "--no-mcp")
        command = self.commands(self.home / ".codex/hooks.json")["Stop"][0].replace(str(PACK), "/gone/portable-pack")
        p = subprocess.run(["sh", "-c", command], input="{}", capture_output=True, text=True, env=dict(os.environ))
        self.assertEqual((p.returncode, p.stdout), (0, ""))

    def test_no_hooks_links_the_packs_only(self):
        (self.home / ".codex").mkdir()
        self.run_it("--no-mcp", "--no-hooks")
        self.assertTrue((self.home / ".agents/skills/e-invoice").is_symlink())
        self.assertFalse((self.home / ".codex/hooks.json").exists())

    def test_the_two_shell_scripts_still_install(self):
        for name in ("install.sh", "install-codex.sh"):
            with self.subTest(script=name):
                self.run_it("--no-mcp", script=PACK / name)
                self.assertTrue((self.home / ".agents/skills/e-invoice").is_symlink())
                self.assertTrue((self.home / ".agents/skills/_checks").is_symlink())

    def test_the_command_a_hook_file_holds_runs(self):
        self.run_it("--agents", ALL, "--no-mcp")
        sample = (INPUTS / "codex-Stop.json").read_text()
        command = self.commands(self.home / ".codex/hooks.json")["Stop"][0]
        p = subprocess.run(["sh", "-c", command], input=sample, capture_output=True, text=True,
                           env={**os.environ, "CLAUDE_PLUGIN_DATA": tempfile.mkdtemp()})
        self.assertEqual((p.returncode, p.stdout, p.stderr), (0, "", ""))


if __name__ == "__main__":
    unittest.main()
