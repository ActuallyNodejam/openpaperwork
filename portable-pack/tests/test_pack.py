"""The portable pack: copies in step with their sources, the check from a shell, the same check over MCP.

Run from the repository root: python3 -m unittest portable-pack/tests/test_pack.py
Needs python-pptx.
"""
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

PACK = Path(__file__).resolve().parent.parent
ROOT = PACK.parent
KIT = {"brand": "Example", "slide_ratio": "16:9", "fonts": {"heading": "Arial", "body": "Georgia"},
       "palette": ["#0B1F3A", "#F2B705", "#FFFFFF", "#5A6B7B"],
       "limits": {"max_words_per_slide": 40, "max_body_paragraphs": 4, "min_font_pt": 18}, "footer": "Example footer"}
SLIDES = {"properties": {"title": "Example deck"}, "slides": [
    {"role": "title", "title": "First title", "subtitle": "First subtitle"},
    {"role": "content", "title": "Second title", "bullets": ["Second one", "Second two"]}]}


class PortablePack(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = Path(tempfile.mkdtemp())
        (cls.tmp / "kit.json").write_text(json.dumps(KIT))
        (cls.tmp / "slides.json").write_text(json.dumps(SLIDES))
        cls.deck = cls.tmp / "deck.pptx"
        p = subprocess.run([sys.executable, str(PACK / "skills/brand-kit-deck/scripts/pptx_from_kit.py"),
                            str(cls.tmp / "kit.json"), str(cls.tmp / "slides.json"), str(cls.deck)], capture_output=True, text=True)
        assert p.returncode == 0, p.stdout + p.stderr

    def test_copies_are_in_step_with_their_sources(self):
        p = subprocess.run([sys.executable, str(ROOT / "scripts/build-portable-pack.py"), "--check"], capture_output=True, text=True)
        self.assertEqual(p.returncode, 0, p.stdout)

    def test_shell_check_passes_a_deck_built_from_the_kit(self):
        p = subprocess.run([sys.executable, str(PACK / "skills/brand-kit-deck/scripts/check_file.py"), str(self.deck),
                            "--kit", str(self.tmp / "kit.json"), "--slides", "2"], capture_output=True, text=True)
        out = json.loads(p.stdout)
        self.assertTrue(out["ok"], out.get("failed"))
        self.assertEqual(p.returncode, 0)

    def test_shell_check_fails_on_a_wrong_slide_count(self):
        p = subprocess.run([sys.executable, str(PACK / "skills/every-file/scripts/check_file.py"), str(self.deck),
                            "--kit", str(self.tmp / "kit.json"), "--slides", "5"], capture_output=True, text=True)
        self.assertEqual(p.returncode, 1)
        self.assertEqual(json.loads(p.stdout)["failed"], ["KIT-COUNT"])

    def test_mcp_server_lists_and_runs_the_same_check(self):
        msgs = [{"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {"protocolVersion": "2025-06-18", "capabilities": {}}},
                {"jsonrpc": "2.0", "method": "notifications/initialized"},
                {"jsonrpc": "2.0", "id": 2, "method": "tools/list"},
                {"jsonrpc": "2.0", "id": 3, "method": "tools/call", "params": {"name": "check_file", "arguments": {"path": str(self.deck)}}}]
        p = subprocess.run([sys.executable, str(PACK / "mcp/server.py")], input="\n".join(json.dumps(m) for m in msgs) + "\n",
                           capture_output=True, text=True)
        replies = [json.loads(line) for line in p.stdout.splitlines()]
        self.assertEqual([r["id"] for r in replies], [1, 2, 3])
        self.assertEqual(replies[1]["result"]["tools"][0]["name"], "check_file")
        self.assertTrue(json.loads(replies[2]["result"]["content"][0]["text"])["ok"])


if __name__ == "__main__":
    unittest.main()
