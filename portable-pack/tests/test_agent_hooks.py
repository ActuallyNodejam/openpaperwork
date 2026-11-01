"""The pack check at the end of a turn in Codex, Gemini CLI, Cursor CLI and dsh.

hooks/pack_agents.py turns each agent's hook input into what hooks/pack_stop.py decides on, and prints the
answer in that agent's own form. The inputs are in tests/hook-inputs/, one file for each agent and event;
tests/hook-inputs/README.md says which were recorded from a real run and which follow the maker's docs.

Run from the repository root: python3 -m unittest portable-pack/tests/test_agent_hooks.py
The invoice test needs pdftotext (poppler).
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path

PACK = Path(__file__).resolve().parent.parent
HOOKS = PACK / "hooks"
INPUTS = Path(__file__).resolve().parent / "hook-inputs"
sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(HOOKS))
from test_stop_hook import ORDER, hand_made_pdf  # noqa: E402
import pack_agents  # noqa: E402
import pack_stop  # noqa: E402

# Agent -> the event that starts a turn, the event that ends it, the field that names the folder.
AGENTS = {
    "codex": ("UserPromptSubmit", "Stop"),
    "gemini": ("BeforeAgent", "AfterAgent"),
    "cursor": ("beforeSubmitPrompt", "stop"),
    "dsh": ("UserPromptSubmit", "Stop"),
}
# A check that always fails, with one FAIL line.
RED = 'echo "FAIL POSTER-X the poster is not right"\nexit 1\n'


def sample(agent, event):
    return json.loads((INPUTS / ("%s-%s.json" % (agent, event))).read_text())


class Turn:
    """One agent in one folder: a copy of the two hook files beside one pack whose check is always red."""

    def __init__(self, agent, hooks=None):
        self.agent = agent
        self.start, self.end = AGENTS[agent]
        self.chat = Path(tempfile.mkdtemp()) / "My files"
        self.chat.mkdir()
        self.data = Path(tempfile.mkdtemp())
        if hooks is None:
            plugin = Path(tempfile.mkdtemp())
            shutil.copytree(HOOKS, plugin / "hooks")
            pack = plugin / "skills" / "poster"
            pack.mkdir(parents=True)
            (pack / "pack.json").write_text(json.dumps({"hands_back": ["*.pdf"], "check": "sh {here}/check.sh {file}"}))
            (pack / "check.sh").write_text(RED)
            hooks = plugin / "hooks"
        self.hook = hooks / "pack_agents.py"

    def send(self, event, **fields):
        data = sample(self.agent, event)
        if "cwd" in data:
            data["cwd"] = str(self.chat)
        if "workspace_roots" in data:
            data["workspace_roots"] = [str(self.chat)]
        data["transcript_path"] = "" if self.agent == "dsh" else None
        data.update(fields)
        p = subprocess.run([sys.executable, str(self.hook), self.agent], input=json.dumps(data),
                           capture_output=True, text=True, env={**os.environ, "CLAUDE_PLUGIN_DATA": str(self.data)})
        assert p.returncode == 0 and not p.stderr, p.stderr
        return json.loads(p.stdout) if p.stdout.strip() else None

    def prompt(self, text="Make the poster."):
        out = self.send(self.start, prompt=text)
        time.sleep(0.03)
        return out

    def write(self, name="poster.pdf"):
        (self.chat / name).write_text("poster %f\n" % time.time())
        time.sleep(0.02)

    def stop(self, **fields):
        return self.bounce(self.send(self.end, **fields))

    def bounce(self, out):
        """The text that goes back to the agent, or None when the turn may end."""
        if self.agent == "cursor":
            return (out or {}).get("followup_message")
        if self.agent == "gemini":
            return out["reason"] if out["decision"] == "deny" else None
        return out["reason"] if out and out.get("decision") == "block" else None


def every_agent(test):
    """Run a test once for each agent, each in its own folder."""
    def run(self):
        for agent in AGENTS:
            with self.subTest(agent=agent):
                test(self, Turn(agent))
    run.__name__ = test.__name__
    return run


class EveryAgent(unittest.TestCase):
    @every_agent
    def test_a_red_check_goes_back_to_the_agent_in_its_own_form(self, turn):
        turn.prompt()
        turn.write()
        out = turn.send(turn.end)
        want = {"codex": "block", "dsh": "block", "gemini": "deny"}.get(turn.agent)
        if want:
            self.assertEqual(out["decision"], want)
            self.assertEqual(sorted(out), ["decision", "reason"])
        else:
            self.assertEqual(sorted(out), ["followup_message"])
        text = turn.bounce(out)
        self.assertIn("try 1 of 3", text)
        self.assertIn("poster (poster.pdf): FAIL POSTER-X", text)

    @every_agent
    def test_a_turn_that_made_no_file_ends_with_the_agents_own_quiet_answer(self, turn):
        quiet = {"codex": None, "dsh": None, "gemini": {"decision": "allow"}, "cursor": {}}
        start = {"codex": None, "dsh": None, "gemini": {"decision": "allow"}, "cursor": {"continue": True}}
        self.assertEqual(turn.prompt(), start[turn.agent])
        self.assertEqual(turn.send(turn.end), quiet[turn.agent])

    @every_agent
    def test_without_a_turn_start_nothing_is_judged(self, turn):
        turn.write()
        self.assertIsNone(turn.stop())

    @every_agent
    def test_a_file_from_before_the_turn_stays_the_persons(self, turn):
        turn.write()
        turn.prompt()
        self.assertIsNone(turn.stop())

    @every_agent
    def test_nothing_changed_after_a_bounce_ends_it(self, turn):
        turn.prompt()
        turn.write()
        self.assertIsNotNone(turn.stop())
        # dsh always says stop_hook_active false, Cursor counts loops: neither is needed.
        self.assertIsNone(turn.stop())

    @every_agent
    def test_three_bounces_at_most(self, turn):
        turn.prompt()
        tries = []
        for _ in range(4):
            turn.write()
            tries.append(turn.stop())
        self.assertEqual([t is not None for t in tries], [True, True, True, False])
        self.assertIn("last try (3 of 3)", tries[2])

    @every_agent
    def test_the_bounce_coming_back_as_a_prompt_is_the_same_turn(self, turn):
        turn.prompt()
        tries = []
        for _ in range(4):
            turn.write()
            text = turn.stop()
            tries.append(text)
            if text:
                turn.prompt(text)
        self.assertEqual([t is not None for t in tries], [True, True, True, False])

    @every_agent
    def test_the_persons_next_request_is_a_new_turn(self, turn):
        turn.prompt()
        for _ in range(3):
            turn.write()
            turn.stop()
        turn.prompt("Now make it wider.")
        turn.write()
        self.assertIn("try 1 of 3", turn.stop())

    @every_agent
    def test_a_file_named_only_in_the_transcript_is_found(self, turn):
        if turn.agent == "dsh":
            return  # dsh hands a hook no transcript
        turn.prompt()
        deep = turn.chat / "out" / "2026" / "fall"
        deep.mkdir(parents=True)
        (deep / "poster.pdf").write_text("poster\n")
        transcript = turn.data / "transcript.any"
        transcript.write_text(json.dumps({"whatever": [{"shape": "it has", "cmd": "python3 make.py out/2026/fall/poster.pdf"}]}))
        self.assertIsNone(turn.stop())
        self.assertIn("poster (out/2026/fall/poster.pdf): FAIL", turn.stop(transcript_path=str(transcript)))


class TheReply(unittest.TestCase):
    """A reply that ends in a question is waiting for the person. Codex and Gemini CLI hand the reply to the
    hook, Cursor hands it to afterAgentResponse; dsh hands it to no hook."""

    def test_codex_and_gemini_are_not_sent_back_on_a_question(self):
        for agent, field in (("codex", "last_assistant_message"), ("gemini", "prompt_response")):
            with self.subTest(agent=agent):
                turn = Turn(agent)
                turn.prompt()
                turn.write()
                self.assertIsNone(turn.stop(**{field: "Which size should the poster be?"}))
                self.assertIsNotNone(turn.stop(**{field: "Done."}))

    def test_cursor_is_not_sent_back_on_a_question(self):
        turn = Turn("cursor")
        turn.prompt()
        turn.write()
        self.assertEqual(turn.send("afterAgentResponse", text="Which size should the poster be?"), {})
        self.assertIsNone(turn.stop())
        turn.send("afterAgentResponse", text="Done.")
        self.assertIsNotNone(turn.stop())

    def test_cursor_only_judges_a_turn_that_completed(self):
        turn = Turn("cursor")
        turn.prompt()
        turn.write()
        self.assertIsNone(turn.stop(status="aborted"))
        self.assertIsNone(turn.stop(status="error"))
        self.assertIsNotNone(turn.stop(status="completed"))

    def test_deepseek_harness_keeps_its_notes_in_the_folder(self):
        """Its sandbox keeps nothing else from one hook to the next; a dot folder is never taken for a file."""
        turn = Turn("dsh")
        turn.prompt()
        turn.write()
        self.assertIsNotNone(turn.stop())
        self.assertEqual(sorted(p.name[:5] for p in (turn.chat / ".openpaperwork").iterdir()), ["stop-", "turn-"])
        self.assertEqual(list(turn.data.iterdir()), [])
        for agent in ("codex", "gemini", "cursor"):
            other = Turn(agent)
            other.prompt()
            self.assertFalse((other.chat / ".openpaperwork").exists())

    def test_deepseek_harness_cannot_tell_a_question(self):
        turn = Turn("dsh")
        self.assertNotIn("last_assistant_message", sample("dsh", "Stop"))
        turn.prompt()
        turn.write()
        self.assertIsNotNone(turn.stop())


class TheInputs(unittest.TestCase):
    def test_every_input_carries_what_the_adapter_reads(self):
        for agent, events in pack_agents.EVENTS.items():
            for event, kind in events.items():
                with self.subTest(agent=agent, event=event):
                    data = sample(agent, event)
                    self.assertEqual(data["hook_event_name"], event)
                    self.assertIn("conversation_id" if agent == "cursor" else "session_id", data)
                    self.assertIn("workspace_roots" if agent == "cursor" else "cwd", data)
                    if kind == "prompt":
                        self.assertIsInstance(data["prompt"], str)
        self.assertIsInstance(sample("codex", "Stop")["last_assistant_message"], str)
        self.assertIsInstance(sample("gemini", "AfterAgent")["prompt_response"], str)
        self.assertIsInstance(sample("cursor", "afterAgentResponse")["text"], str)
        self.assertEqual(sample("cursor", "stop")["status"], "completed")

    def test_both_bounce_texts_begin_the_way_the_adapter_knows_them(self):
        for count in (1, pack_stop.MAX_BOUNCES):
            self.assertTrue(pack_stop.bounce_text(count, ["x"]).startswith(pack_agents.OURS))

    def test_inside_the_app_no_adapter_judges_the_turn(self):
        import contextlib
        import io
        judged, real, stdin = [], pack_agents.handle, sys.stdin
        pack_agents.handle = lambda *args: judged.append(args) or "x"
        os.environ[pack_stop.APP_ENV] = "1"
        try:
            for agent in AGENTS:
                for event in pack_agents.EVENTS[agent]:
                    with self.subTest(agent=agent, event=event):
                        sys.stdin, out = io.StringIO(json.dumps({"hook_event_name": event})), io.StringIO()
                        with contextlib.redirect_stdout(out):
                            self.assertEqual(pack_agents.main(["pack_agents.py", agent, event]), 0)
                        self.assertNotIn("reason", out.getvalue())
                        self.assertNotIn("followup_message", out.getvalue())
        finally:
            pack_agents.handle, sys.stdin = real, stdin
            del os.environ[pack_stop.APP_ENV]
        self.assertEqual(judged, [])
        # Outside the app the same call does judge.
        pack_agents.handle = lambda *args: judged.append(args)
        try:
            agent = next(iter(AGENTS))
            event = next(iter(pack_agents.EVENTS[agent]))
            sys.stdin = io.StringIO(json.dumps({"hook_event_name": event}))
            with contextlib.redirect_stdout(io.StringIO()):
                pack_agents.main(["pack_agents.py", agent, event])
        finally:
            pack_agents.handle, sys.stdin = real, stdin
        self.assertEqual(len(judged), 1)

    def test_a_broken_input_never_keeps_a_turn_open(self):
        for agent in AGENTS:
            with self.subTest(agent=agent):
                p = subprocess.run([sys.executable, str(HOOKS / "pack_agents.py"), agent], input="not json",
                                   capture_output=True, text=True)
                self.assertEqual(p.returncode, 0)
                out = json.loads(p.stdout) if p.stdout.strip() else {}
                self.assertNotIn("reason", out)
                self.assertNotIn("followup_message", out)


@unittest.skipUnless(shutil.which("pdftotext"), "the invoice check reads PDFs with pdftotext")
class TheInvoice(unittest.TestCase):
    """The real pack: a hand-made invoice PDF fails the e-invoice check and goes back, in every agent."""

    def test_a_hand_made_invoice_goes_back(self):
        for agent in AGENTS:
            with self.subTest(agent=agent):
                turn = Turn(agent, hooks=HOOKS)
                shutil.copy(ORDER, turn.chat / "order.json")
                turn.prompt("Make the invoice.")
                hand_made_pdf(turn.chat / "invoice.pdf")
                text = turn.stop()
                self.assertIn("try 1 of 3", text)
                self.assertIn("e-invoice (invoice.pdf): FAIL ", text)


class Routed(unittest.TestCase):
    """The prompt-time hint and the net under it, in the plugin as it is built, on each agent's recorded input."""

    ASK = "Make the invoice for this job from notes.txt, ready to send."

    def turn(self, agent):
        return Turn(agent, hooks=HOOKS)

    def test_the_hint_goes_to_the_agents_whose_prompt_hook_can_add_to_a_turn(self):
        line = "If this ask is for an invoice, load the e-invoice skill before writing anything"
        for agent, event in (("codex", "UserPromptSubmit"), ("dsh", "UserPromptSubmit"), ("gemini", "BeforeAgent")):
            out = self.turn(agent).prompt(self.ASK)
            self.assertEqual(out["hookSpecificOutput"]["hookEventName"], event, agent)
            self.assertTrue(out["hookSpecificOutput"]["additionalContext"].startswith(line), agent)
            self.assertEqual(sorted(out), ["decision", "hookSpecificOutput"] if agent == "gemini" else ["hookSpecificOutput"])
        self.assertEqual(self.turn("gemini").prompt(self.ASK)["decision"], "allow")
        # Cursor's prompt hook can only let a prompt through or stop it.
        self.assertEqual(self.turn("cursor").prompt(self.ASK), {"continue": True})

    def test_an_ordinary_ask_and_a_bounce_that_comes_back_get_no_hint(self):
        for agent in AGENTS:
            quiet = pack_agents.QUIET.get(agent, {}).get("prompt")
            self.assertEqual(self.turn(agent).prompt("List the files in this folder."), quiet, agent)
            self.assertEqual(self.turn(agent).prompt("A pack check is not clean (try 1 of 3):\n\ne-invoice "
                                                     "(invoice.pdf): FAIL EINV-VAT-LABEL"), quiet, agent)

    def test_inside_the_app_no_hint_comes_from_the_hook(self):
        turn = self.turn("codex")
        data = dict(sample("codex", "UserPromptSubmit"), cwd=str(turn.chat), prompt=self.ASK)
        p = subprocess.run([sys.executable, str(turn.hook), "codex"], input=json.dumps(data), capture_output=True,
                           text=True, env={**os.environ, "CLAUDE_PLUGIN_DATA": str(turn.data), "OPENPAPERWORK_APP": "1"})
        self.assertEqual((p.returncode, p.stdout.strip()), (0, ""))

    def test_a_file_made_without_the_pack_goes_back_once_in_every_agent(self):
        for agent in AGENTS:
            with self.subTest(agent=agent):
                turn = self.turn(agent)
                turn.prompt(self.ASK)
                turn.write("invoice.md")
                extra = {"status": "completed"} if agent == "cursor" else {}
                text = turn.stop(**extra)
                self.assertIn("This was asked as an invoice; the e-invoice skill makes and checks that.", text)
                self.assertIsNone(turn.stop(**extra))

    def test_no_net_when_the_ask_named_nothing_or_the_pack_left_its_evidence(self):
        turn = self.turn("codex")
        turn.prompt("Summarise notes.txt in five bullets.")
        turn.write("summary.md")
        self.assertIsNone(turn.stop())
        turn = self.turn("gemini")
        turn.prompt(self.ASK)
        shutil.copy(ORDER, turn.chat / "order.json")
        turn.write("invoice.md")
        self.assertIsNone(turn.stop())


if __name__ == "__main__":
    unittest.main()
