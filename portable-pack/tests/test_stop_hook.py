"""The Stop hook: a red pack check over a file the turn wrote blocks the stop, three times a turn at most.

Run from the repository root: python3 -m unittest portable-pack/tests/test_stop_hook.py
The invoice tests need pdftotext (poppler).
"""
import json
import os
import shlex
import shutil
import subprocess
import sys
import tempfile
import time
import unittest
from datetime import datetime, timezone
from pathlib import Path

PACK = Path(__file__).resolve().parent.parent
HOOK = PACK / "hooks" / "pack_stop.py"
ORDER = PACK / "skills" / "e-invoice" / "templates" / "uk-vat-invoice-spec.json"
# A one-page PDF of plain text: an invoice made by hand, not by the pack's page builder.
TEXT = b"BT /F1 11 Tf 50 780 Td (INVOICE INV-2026-0207 Total 4480.00 GBP) Tj ET"
OBJS = [b"<< /Type /Catalog /Pages 2 0 R >>", b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] /Contents 4 0 R "
        b"/Resources << /Font << /F1 5 0 R >> >> >>",
        b"<< /Length %d >>\nstream\n%s\nendstream" % (len(TEXT), TEXT),
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>"]


def hand_made_pdf(path):
    pdf, offs = b"%PDF-1.4\n", []
    for i, obj in enumerate(OBJS, 1):
        offs.append(len(pdf))
        pdf += b"%d 0 obj\n%s\nendobj\n" % (i, obj)
    xref = len(pdf)
    pdf += b"xref\n0 %d\n0000000000 65535 f \n" % (len(OBJS) + 1) + b"".join(b"%010d 00000 n \n" % o for o in offs)
    pdf += b"trailer\n<< /Size %d /Root 1 0 R >>\nstartxref\n%d\n%%%%EOF\n" % (len(OBJS) + 1, xref)
    Path(path).write_bytes(pdf)


@unittest.skipUnless(shutil.which("pdftotext"), "the invoice check reads PDFs with pdftotext")
class StopHook(unittest.TestCase):
    def setUp(self):
        self.dir = Path(tempfile.mkdtemp())
        self.data = Path(tempfile.mkdtemp())
        shutil.copy(ORDER, self.dir / "order.json")
        now = datetime.now(timezone.utc) .isoformat().replace("+00:00", "Z")
        time.sleep(0.05)
        hand_made_pdf(self.dir / "invoice.pdf")
        lines = [{"type": "user", "timestamp": now, "message": {"role": "user", "content": "Make the invoice."}},
                 {"type": "assistant", "timestamp": now, "message": {"role": "assistant", "content": [
                     {"type": "tool_use", "name": "Write", "input": {"file_path": str(self.dir / "invoice.pdf")}}]}}]
        self.transcript = self.dir / "transcript.jsonl"
        self.transcript.write_text("".join(json.dumps(line) + "\n" for line in lines))

    def stop(self, reply="Done.", active=False):
        data = {"session_id": "test", "transcript_path": str(self.transcript), "cwd": str(self.dir),
                "stop_hook_active": active, "last_assistant_message": reply, "hook_event_name": "Stop"}
        p = subprocess.run([sys.executable, str(HOOK)], input=json.dumps(data), capture_output=True, text=True,
                           env={**os.environ, "CLAUDE_PLUGIN_DATA": str(self.data)})
        self.assertEqual(p.returncode, 0, p.stderr)
        return json.loads(p.stdout) if p.stdout.strip() else None

    def test_a_red_check_blocks_the_stop_with_its_fail_lines(self):
        out = self.stop()
        self.assertEqual(out["decision"], "block")
        self.assertIn("try 1 of 3", out["reason"])
        self.assertIn("e-invoice (invoice.pdf): FAIL ", out["reason"])

    def loads(self, skill):
        """The turn's transcript with a Skill call that loads the pack, as Claude Code records one."""
        lines = [json.loads(line) for line in self.transcript.read_text().splitlines()]
        lines[1]["message"]["content"].insert(0, {"type": "tool_use", "name": "Skill", "input": {"skill": skill}})
        self.transcript.write_text("".join(json.dumps(line) + "\n" for line in lines))

    def test_a_file_no_pack_claims_or_loaded_is_left_alone(self):
        (self.dir / "order.json").unlink()
        out = self.stop()          # at most the net, said once: no check read the file
        self.assertNotIn("FAIL ", (out or {}).get("reason", ""))

    def test_a_pack_the_turn_loaded_checks_its_files_without_its_evidence(self):
        (self.dir / "order.json").unlink()
        self.loads("openpaperwork-finance:e-invoice")
        out = self.stop()
        self.assertEqual(out["decision"], "block")
        self.assertIn("e-invoice (invoice.pdf): FAIL ", out["reason"])
        # The command to run again is the one the hook ran: no claim asked of a pack the turn loaded.
        self.assertNotIn("--if-claimed", out["reason"].rstrip().splitlines()[-1])

    def test_a_command_loads_the_pack_it_names(self):
        (self.dir / "order.json").unlink()
        self.loads("openpaperwork-finance:invoice")            # headless: the command is the Skill call
        self.assertIn("e-invoice (invoice.pdf): FAIL ", self.stop()["reason"])

    def test_a_command_typed_in_the_chat_loads_the_pack_it_names(self):
        (self.dir / "order.json").unlink()
        lines = [json.loads(line) for line in self.transcript.read_text().splitlines()]
        typed = dict(lines[0], message={"role": "user", "content": (
            "<command-message>openpaperwork-finance:invoice</command-message>\n"
            "<command-name>/openpaperwork-finance:invoice</command-name>\n<command-args>for the March work</command-args>")})
        lines.insert(1, typed)
        self.transcript.write_text("".join(json.dumps(line) + "\n" for line in lines))
        self.assertIn("e-invoice (invoice.pdf): FAIL ", self.stop()["reason"])

    def test_a_command_alone_starts_the_turn_and_a_file_the_person_brought_stays_theirs(self):
        (self.dir / "order.json").unlink()
        lines = [json.loads(line) for line in self.transcript.read_text().splitlines()]
        lines[0]["message"]["content"] = ("<command-message>openpaperwork-finance:invoice</command-message>\n"
                                          "<command-name>/openpaperwork-finance:invoice</command-name>")
        lines[1]["message"]["content"] = [{"type": "tool_use", "name": "Read",
                                           "input": {"file_path": str(self.dir / "invoice.pdf")}}]
        self.transcript.write_text("".join(json.dumps(line) + "\n" for line in lines))
        theirs = time.time() - 3600                            # in the folder before the person sent the command
        os.utime(self.dir / "invoice.pdf", (theirs, theirs))
        self.assertNotIn("FAIL ", (self.stop() or {}).get("reason", ""))

    def test_a_path_that_ends_like_a_command_loads_nothing(self):
        (self.dir / "order.json").unlink()
        lines = [json.loads(line) for line in self.transcript.read_text().splitlines()]
        lines[0]["message"]["content"] = "Use what is in ~/Documents/invoice/march.txt"
        self.transcript.write_text("".join(json.dumps(line) + "\n" for line in lines))
        self.assertNotIn("FAIL ", (self.stop() or {}).get("reason", ""))

    def test_a_folder_named_like_a_pack_does_not_load_it(self):
        (self.dir / "order.json").unlink()
        lines = [json.loads(line) for line in self.transcript.read_text().splitlines()]
        lines[1]["message"]["content"].insert(0, {"type": "tool_use", "name": "Read",
                                                  "input": {"file_path": "/home/person/e-invoice/notes.txt"}})
        self.transcript.write_text("".join(json.dumps(line) + "\n" for line in lines))
        self.assertNotIn("FAIL ", (self.stop() or {}).get("reason", ""))

    def test_the_bounce_ends_on_the_exact_command_to_run_again(self):
        tail = self.stop()["reason"].rstrip().splitlines()[-2:]
        self.assertEqual(tail[0], "Run the check again with exactly:")
        pdf = str(self.dir / "invoice.pdf")
        self.assertTrue(tail[1].startswith("cd %s && " % shlex.quote(str(self.dir))), tail[1])
        self.assertIn("packcheck.py", tail[1])
        self.assertTrue(tail[1].endswith("%s --if-claimed --in %s" % (shlex.quote(pdf), shlex.quote(str(self.dir)))), tail[1])
        # The command is the hook's own: run as printed, it fails the same way.
        again = subprocess.run(["sh", "-c", tail[1]], capture_output=True, text=True)
        self.assertNotEqual(again.returncode, 0)
        self.assertIn("FAIL ", again.stdout + again.stderr)

    def test_inside_the_app_the_hook_stands_down(self):
        data = {"session_id": "test", "transcript_path": str(self.transcript), "cwd": str(self.dir),
                "stop_hook_active": False, "last_assistant_message": "Done.", "hook_event_name": "Stop"}
        p = subprocess.run([sys.executable, str(HOOK)], input=json.dumps(data), capture_output=True, text=True,
                           env={**os.environ, "CLAUDE_PLUGIN_DATA": str(self.data), "OPENPAPERWORK_APP": "1"})
        self.assertEqual((p.returncode, p.stdout.strip()), (0, ""))

    def test_a_reply_that_asks_is_not_blocked(self):
        self.assertIsNone(self.stop("Which VAT number should the invoice carry?"))

    def test_nothing_changed_after_a_bounce_ends_it(self):
        self.assertIsNotNone(self.stop())
        self.assertIsNone(self.stop(active=True))

    def test_three_bounces_at_most(self):
        tries = []
        for _ in range(4):
            os.utime(self.dir / "invoice.pdf")
            time.sleep(0.02)
            tries.append(self.stop(active=bool(tries)))
        self.assertEqual([t is not None for t in tries], [True, True, True, False])
        self.assertIn("last try (3 of 3)", tries[2]["reason"])


# One FAIL line a run, with what the run was given before the hook's own --if-claimed.
POSTER_CHECK = ('out="FAIL POSTER-X"\nfor a; do [ "$a" = "--if-claimed" ] && break; out="$out [$a]"; done\n'
                'echo "$out"\nexit 1\n')


class WholeReply(unittest.TestCase):
    """The person reads only the agent's last message: after a question or a bounce, that message is the whole
    reply again (a real run, 2026-10-13, handed back only its answer to the check)."""

    def test_a_question_and_a_bounce_both_ask_for_the_whole_reply(self):
        sys.path.insert(0, str(HOOK.parent))
        import pack_stop
        said = pack_stop.once_text("/tmp/chat", asks=["meeting-minutes (m.docx): WARN NOTES-FLOOR «11.15»"])
        self.assertTrue(said.endswith(pack_stop.WHOLE_REPLY), said)
        self.assertIn(pack_stop.WHOLE_REPLY, pack_stop.bounce_text(1, ["FAIL X"]))
        self.assertEqual(pack_stop.once_text("/tmp/chat"), "", "nothing to say stays nothing")


class FolderCheck(unittest.TestCase):
    """A check that names {folder} runs once for each folder the turn's files sit in, not once for each file
    (a poster folder holds a PNG and a PDF for every size)."""

    def runs(self, check, names):
        """The pack's lines in the bounce: a copy of the hook beside one pack, and a turn that wrote `names`."""
        plugin, chat = Path(tempfile.mkdtemp()), Path(tempfile.mkdtemp()) / "My files"
        (plugin / "hooks").mkdir()
        shutil.copy(HOOK, plugin / "hooks" / "pack_stop.py")
        pack = plugin / "skills" / "poster"
        pack.mkdir(parents=True)
        (pack / "pack.json").write_text(json.dumps({"hands_back": ["*.png", "*.pdf"], "check": check}))
        (pack / "check.sh").write_text(POSTER_CHECK)
        now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        time.sleep(0.05)
        for name in names:
            (chat / name).parent.mkdir(parents=True, exist_ok=True)
            (chat / name).write_text("poster\n")
        lines = [{"type": "user", "timestamp": now, "message": {"role": "user", "content": "Make the posters."}},
                 {"type": "assistant", "timestamp": now, "message": {"role": "assistant", "content": [
                     {"type": "tool_use", "name": "Write", "input": {"file_path": str(chat / name)}}
                     for name in names]}}]
        transcript = plugin / "transcript.jsonl"
        transcript.write_text("".join(json.dumps(line) + "\n" for line in lines))
        data = {"session_id": "test", "transcript_path": str(transcript), "cwd": str(chat),
                "stop_hook_active": False, "last_assistant_message": "Done.", "hook_event_name": "Stop"}
        p = subprocess.run([sys.executable, str(plugin / "hooks" / "pack_stop.py")], input=json.dumps(data),
                           capture_output=True, text=True, env={**os.environ, "CLAUDE_PLUGIN_DATA": str(plugin)})
        self.assertEqual(p.returncode, 0, p.stderr)
        reason = json.loads(p.stdout)["reason"]
        return chat, [line for line in reason.splitlines() if line.startswith("poster (")]

    def test_two_files_in_one_folder_are_one_run(self):
        chat, lines = self.runs("sh {here}/check.sh {folder}", ["Fall 2026/a2.png", "Fall 2026/a2.pdf"])
        self.assertEqual(lines, ["poster (Fall 2026/): FAIL POSTER-X [%s]" % (chat / "Fall 2026")])

    def test_two_folders_are_two_runs_in_the_order_they_appear(self):
        chat, lines = self.runs("sh {here}/check.sh {folder}",
                                ["Spring 2027/a2.png", "Fall 2026/a2.png", "Fall 2026/a2.pdf"])
        self.assertEqual(lines, ["poster (Spring 2027/): FAIL POSTER-X [%s]" % (chat / "Spring 2027"),
                                 "poster (Fall 2026/): FAIL POSTER-X [%s]" % (chat / "Fall 2026")])

    def test_a_file_check_still_runs_once_for_each_file(self):
        chat, lines = self.runs("sh {here}/check.sh {file}", ["Fall 2026/a2.png", "Fall 2026/a2.pdf"])
        self.assertEqual(lines, ["poster (Fall 2026/a2.png): FAIL POSTER-X [%s]" % (chat / "Fall 2026" / "a2.png"),
                                 "poster (Fall 2026/a2.pdf): FAIL POSTER-X [%s]" % (chat / "Fall 2026" / "a2.pdf")])

    def test_file_and_folder_together_run_once_for_each_file_with_its_folder(self):
        chat, lines = self.runs("sh {here}/check.sh {file} {folder}", ["Fall 2026/a2.png", "Spring 2027/a2.png"])
        self.assertEqual(lines, [
            "poster (Fall 2026/a2.png): FAIL POSTER-X [%s] [%s]" % (chat / "Fall 2026" / "a2.png", chat / "Fall 2026"),
            "poster (Spring 2027/a2.png): FAIL POSTER-X [%s] [%s]" % (chat / "Spring 2027" / "a2.png",
                                                                      chat / "Spring 2027")])


ASK = "WARN MEMO-ASK          the notes hold a phone number and the page does not: 08-555 01 00"


class SaidOnce(unittest.TestCase):
    """The bounce path's two faults (a deck's real run, 2026-10-10), and what goes back to the agent once a
    turn and never again: a check's WARN lines, a check that could run no rule, a file built beside the plugin."""

    def setUp(self):
        # The plugin in a folder of its own, so "beside the plugin" holds nothing but what a test puts there.
        self.plugin, self.chat = Path(tempfile.mkdtemp()) / "plugin", Path(tempfile.mkdtemp()) / "My files"
        (self.plugin / "hooks").mkdir(parents=True)
        shutil.copy(HOOK, self.plugin / "hooks" / "pack_stop.py")
        self.pack = self.plugin / "skills" / "memo"
        self.pack.mkdir(parents=True)
        (self.pack / "pack.json").write_text(json.dumps({"hands_back": ["*.txt"], "check": "sh {here}/check.sh {file}"}))
        self.chat.mkdir()
        now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        time.sleep(0.05)
        (self.chat / "memo.txt").write_text("memo\n")
        lines = [{"type": "user", "timestamp": now, "message": {"role": "user", "content": "Write the memo."}},
                 {"type": "assistant", "timestamp": now, "message": {"role": "assistant", "content": [
                     {"type": "tool_use", "name": "Write", "input": {"file_path": str(self.chat / "memo.txt")}}]}}]
        self.transcript = self.plugin / "transcript.jsonl"
        self.transcript.write_text("".join(json.dumps(line) + "\n" for line in lines))

    def check(self, script):
        (self.pack / "check.sh").write_text(script)

    def stop(self, active=False, reply="Done."):
        data = {"session_id": "test", "transcript_path": str(self.transcript), "cwd": str(self.chat),
                "stop_hook_active": active, "last_assistant_message": reply, "hook_event_name": "Stop"}
        p = subprocess.run([sys.executable, str(self.plugin / "hooks" / "pack_stop.py")], input=json.dumps(data),
                           capture_output=True, text=True, env={**os.environ, "CLAUDE_PLUGIN_DATA": str(self.plugin)})
        self.assertEqual(p.returncode, 0, p.stderr)
        return json.loads(p.stdout)["reason"] if p.stdout.strip() else None

    def test_a_fail_behind_many_skip_lines_is_not_cut_away(self):
        skips = "".join('echo "SKIP MEMO-RULE-%d       could not check: the validator is not installed on this '
                        'machine"\n' % at for at in range(60))
        self.check(skips + 'echo "FAIL MEMO-TITLE no title"\necho "1 of 2 rules failed"\nexit 1\n')
        reason = self.stop()
        self.assertIn("try 1 of 3", reason)
        self.assertIn("memo (memo.txt): FAIL MEMO-TITLE no title", reason)
        self.assertNotIn("SKIP ", reason)

    def test_a_warn_on_a_clean_run_goes_back_once_and_never_again(self):
        self.check('echo "%s"\necho "pack check clean: 3 rules passed"\nexit 0\n' % ASK)
        reason = self.stop()
        self.assertTrue(reason.startswith("A pack check has a question before the turn ends (asked once, not again):"))
        self.assertIn("memo (memo.txt): " + ASK, reason)
        self.assertNotIn("not clean", reason)
        self.assertNotIn("try 1 of 3", reason)
        # The check still asks; the agent has answered, and is not asked a second time, whatever it changed.
        self.assertIsNone(self.stop(active=True))
        os.utime(self.chat / "memo.txt")
        self.assertIsNone(self.stop(active=True))

    def test_a_warn_rides_with_the_first_bounce_and_a_fail_keeps_its_three(self):
        self.check('echo "%s"\necho "FAIL MEMO-TITLE no title"\nexit 1\n' % ASK)
        tries = []
        for _ in range(4):
            os.utime(self.chat / "memo.txt")
            time.sleep(0.02)
            tries.append(self.stop(active=bool(tries)))
        self.assertEqual([t is not None for t in tries], [True, True, True, False])
        self.assertEqual(["WARN MEMO-ASK" in t for t in tries[:3]], [True, False, False])
        self.assertTrue(tries[0].startswith("A pack check is not clean (try 1 of 3):"))
        self.assertLess(tries[0].index("FAIL MEMO-TITLE"), tries[0].index("A pack check has a question"))
        self.assertIn("last try (3 of 3)", tries[2])

    def test_a_check_that_ran_no_rule_is_said_once_and_is_not_a_bounce(self):
        self.check('echo "SKIP MEMO-A could not check: No module named docx"\n'
                   'echo "pack check not checked: none of the 1 rules could run on memo.txt (MEMO-A could not '
                   'check: No module named docx)."\nexit 3\n')
        reason = self.stop()
        self.assertTrue(reason.startswith("A pack check could not run, so a file is not checked (said once, not again):"))
        self.assertIn("memo (memo.txt): pack check not checked: none of the 1 rules could run on memo.txt", reason)
        self.assertIn("Do not call the file checked", reason)
        self.assertNotIn("try 1 of 3", reason)
        self.assertIsNone(self.stop(active=True))
        # An older check's "clean: 0 rules passed" on exit 0 is not what this is about, and a check that broke
        # before it said anything still says nothing.
        self.check('echo "Traceback (most recent call last):" >&2\nexit 1\n')
        os.utime(self.chat / "memo.txt")
        self.assertIsNone(self.stop(active=True))

    def test_a_pack_whose_rules_do_not_apply_has_nothing_to_say(self):
        # The plugin's own packcheck.py with a pack that carries its own rules: none applies to the file.
        (self.plugin / "skills" / "_checks").mkdir()
        for name in ("packcheck.py", "end_state.py"):
            shutil.copy(PACK / "skills" / "_checks" / name, self.plugin / "skills" / "_checks" / name)
        # Words enough that the end state lets the file through to the pack's rules.
        (self.chat / "memo.txt").write_text("A memo with real words in it, more than a title.\n")
        (self.pack / "pack.json").write_text(json.dumps({
            "hands_back": ["*.txt"], "check": "%s {here}/../_checks/packcheck.py memo {file}" % shlex.quote(sys.executable),
            "rules": ["MEMO-A", "MEMO-B"], "modules": {"MEMO": "memo_check"}}))
        (self.pack / "memo_check.py").write_text(
            'def check(rule, output, case, stage):\n    return False, "not measured: no reference list, so not a report"\n')
        p = subprocess.run([sys.executable, str(self.plugin / "skills" / "_checks" / "packcheck.py"), "memo",
                            str(self.chat / "memo.txt")], capture_output=True, text=True)
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        self.assertTrue(p.stdout.strip().splitlines()[-1].startswith(
            "pack check not applicable: none of the 2 rules applies to memo.txt (MEMO-A not measured:"), p.stdout)
        self.assertNotIn("clean", p.stdout)
        self.assertIsNone(self.stop())
        # The same pack when its rules could not run: that is said, once.
        (self.pack / "memo_check.py").write_text(
            'def check(rule, output, case, stage):\n    return False, "could not read the file"\n')
        self.assertIn("pack check not checked: none of the 2 rules could run on memo.txt", self.stop())
        self.assertIsNone(self.stop(active=True))

    def test_the_real_pack_check_fails_a_file_that_is_not_the_kind_it_says(self):
        # The plugin's own packcheck.py on a file that is no Word file: red before any rule (the end state), never
        # "not checked" and never clean. "Not checked" itself is held by the memo pack test above.
        (self.chat / "minutes.docx").write_text("not a Word file\n")
        p = subprocess.run([sys.executable, str(PACK / "skills" / "_checks" / "packcheck.py"), "meeting-minutes",
                            str(self.chat / "minutes.docx")], capture_output=True, text=True)
        self.assertEqual(p.returncode, 1, p.stdout + p.stderr)
        self.assertIn("FAIL OUTPUT-UNOPENABLE", p.stdout)
        self.assertNotIn("not checked", p.stdout)
        self.assertNotIn("pack check clean", p.stdout)

    def test_a_file_built_beside_the_plugin_is_said_once_with_the_persons_folder(self):
        self.check("exit 0\n")
        old = self.pack / "template.txt"
        old.write_text("the pack's own\n")
        os.utime(old, (time.time() - 3600, time.time() - 3600))
        self.assertIsNone(self.stop())
        (self.pack / "out").mkdir()
        (self.pack / "out" / "letter.txt").write_text("built where the script is\n")
        (self.plugin.parent / "beside-the-plugin.txt").write_text("and one beside the plugin's folder\n")
        reason = self.stop()
        self.assertTrue(reason.startswith("A pack check found a file this turn made outside the person's folder"))
        self.assertIn(str(self.pack / "out" / "letter.txt"), reason)
        self.assertIn(str(self.plugin.parent / "beside-the-plugin.txt"), reason)
        self.assertIn("the person works in %s" % self.chat, reason)
        self.assertNotIn("template.txt", reason)
        self.assertIsNone(self.stop(active=True))

    def test_a_file_also_put_in_the_persons_folder_is_handed_back(self):
        self.check("exit 0\n")
        (self.pack / "memo.txt").write_text("built here, then copied to the person's folder\n")
        self.assertIsNone(self.stop())


class Net(unittest.TestCase):
    """The net under the prompt-time hint, in the plugin as it is built: an ask that named a kind of file, a
    file handed back, and the pack for it neither loaded nor used, sends the agent back once."""

    ASK = "Schreib bitte die Rechnung für Beispiel Druck GmbH, die Angaben stehen in notes.txt."

    def setUp(self):
        self.chat, self.data = Path(tempfile.mkdtemp()) / "My files", Path(tempfile.mkdtemp())
        self.chat.mkdir()
        (self.chat / "notes.txt").write_text("Beispiel Druck GmbH, 12 Stunden Satz zu 85 EUR\n")
        os.utime(self.chat / "notes.txt", (time.time() - 3600, time.time() - 3600))
        self.now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        time.sleep(0.05)

    def turn(self, ask, wrote=(), calls=()):
        """A recorded turn as Claude Code writes it: the ask, the tool calls, and the files they made."""
        blocks = [{"type": "tool_use", "name": name, "input": data} for name, data in calls]
        for name in wrote:
            (self.chat / name).write_text("Rechnung RE-2026-1093, Summe 1.020,00 EUR\n")
            blocks.append({"type": "tool_use", "name": "Write", "input": {"file_path": str(self.chat / name)}})
        lines = [{"type": "user", "timestamp": self.now, "message": {"role": "user", "content": ask}},
                 {"type": "assistant", "timestamp": self.now, "message": {"role": "assistant", "content": blocks}}]
        (self.data / "transcript.jsonl").write_text("".join(json.dumps(line) + "\n" for line in lines))

    def stop(self, active=False, reply="Die Rechnung liegt in Rechnung.txt."):
        data = {"session_id": "net", "transcript_path": str(self.data / "transcript.jsonl"), "cwd": str(self.chat),
                "stop_hook_active": active, "last_assistant_message": reply, "hook_event_name": "Stop",
                "permission_mode": "default"}
        p = subprocess.run([sys.executable, str(HOOK)], input=json.dumps(data), capture_output=True, text=True,
                           env={**os.environ, "CLAUDE_PLUGIN_DATA": str(self.data), "OPENPAPERWORK_APP": ""})
        self.assertEqual(p.returncode, 0, p.stderr)
        return json.loads(p.stdout)["reason"] if p.stdout.strip() else None

    def test_a_file_made_without_the_pack_it_was_asked_as_goes_back_once(self):
        self.turn(self.ASK, wrote=["Rechnung.txt"])
        reason = self.stop()
        self.assertTrue(reason.startswith("A pack check found no file made with the pack this ask is for (said once"))
        self.assertIn("This was asked as an invoice; the e-invoice skill makes and checks that. Load it and build the "
                      "file with its script; keep every fact you already wrote.", reason)
        self.assertNotIn("try 1 of 3", reason)
        # Never a second time, whatever the agent then did.
        self.assertIsNone(self.stop(active=True))
        os.utime(self.chat / "Rechnung.txt")
        self.assertIsNone(self.stop(active=True))

    def test_never_when_the_pack_was_loaded(self):
        for call in (("Skill", {"skill": "openpaperwork:e-invoice"}), ("Skill", {"skill": "e-invoice"}),
                     ("Read", {"file_path": "/home/person/.claude/plugins/op/skills/e-invoice/SKILL.md"})):
            self.turn(self.ASK, wrote=["Rechnung.txt"], calls=[call])
            self.assertIsNone(self.stop(), call)

    def test_never_when_the_pack_left_its_own_evidence_in_the_folder(self):
        shutil.copy(ORDER, self.chat / "order.json")
        self.turn(self.ASK, wrote=["Rechnung.txt"])
        self.assertIsNone(self.stop())

    def test_never_when_the_ask_named_no_kind_of_file(self):
        self.turn("Fass notes.txt in fünf Punkten zusammen.", wrote=["Zusammenfassung.txt"])
        self.assertIsNone(self.stop())

    def test_never_when_the_turn_handed_back_no_file_or_ends_on_a_question(self):
        self.turn("Welcher Steuersatz gilt für diese Rechnung?")
        self.assertIsNone(self.stop(reply="Für diese Leistung gelten 19 %."))
        self.turn(self.ASK, wrote=["Rechnung.txt"])
        self.assertIsNone(self.stop(reply="Soll die Rechnung auf Deutsch oder Englisch sein?"))

    def test_inside_the_app_the_net_stands_down_with_the_rest_of_the_hook(self):
        self.turn(self.ASK, wrote=["Rechnung.txt"])
        data = {"session_id": "net", "transcript_path": str(self.data / "transcript.jsonl"), "cwd": str(self.chat),
                "stop_hook_active": False, "last_assistant_message": "Fertig.", "hook_event_name": "Stop"}
        p = subprocess.run([sys.executable, str(HOOK)], input=json.dumps(data), capture_output=True, text=True,
                           env={**os.environ, "CLAUDE_PLUGIN_DATA": str(self.data), "OPENPAPERWORK_APP": "1"})
        self.assertEqual((p.returncode, p.stdout.strip()), (0, ""))


if __name__ == "__main__":
    unittest.main()
