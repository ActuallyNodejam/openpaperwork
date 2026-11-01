# OpenPaperwork

Instructions for coding agents working in this repository. Claude Code, Codex,
Cursor, Antigravity and other agents read this file; people can read it too.

OpenPaperwork is a library of document standards that rides the agent the person
already has: they point the agent at a folder, ask in chat, and get editable Word, Excel,
PowerPoint, PDF and HTML files back, each checked against the published rules. This
repository is that library: the packs, the checks, the plugins and the doors that install
them, with no account and no agent of its own. A good change makes finished file work
better for someone who is not technical.

## Set up OpenPaperwork

When someone asks you to set up OpenPaperwork, do these steps and report what passed,
what failed and the exact versions used.

1. Check for Python 3.10 or later. Install it only after the person agrees.
2. From the repository root, link the packs and set their Python up:
   `sh portable-pack/install.sh`, then `sh portable-pack/doctor.sh --fix`. Run the doctor
   again until it prints `Ready`. Show the person any line it prints for `sudo` and let them
   run it.
3. Check which agent the person uses: the Claude app or Claude Code, the ChatGPT app or Codex,
   Cursor, Antigravity. Each signs in on the person's own account, in its own app; never sign
   in for them. See
   [docs/community-preview/BRING_YOUR_OWN_AGENT.md](docs/community-preview/BRING_YOUR_OWN_AGENT.md).
4. Optional: prove one file task with `standards` (below).

Never ask for an API key in chat, and never write a key into a file in this
repository. Stop and ask before anything that costs money.

## Where things live

| Area | Purpose |
| --- | --- |
| `skills` | How the agent makes and revises Word, Excel, PowerPoint, PDF and HTML files, and the pack checks (`skills/_checks`) |
| `standards` | The library's standards: guidelines, invented cases and scripted checks |
| `plugins`, `portable-pack` | The packs built for installing: one plugin per department, and the whole library as one; built from `skills` by `scripts/build-portable-pack.py`, never edited by hand |
| `docs/community-preview` | Philosophy, agents, standards and contribution guidance |
| `scripts` | The pack builds, starter templates and the merge check |

## Checks

- Library: `python3 -m unittest -v standards/test_library.py`.
- Case protocol: `python3 -m unittest -v test_protocol.py` from `standards`.
- The pack checks' end state: `python3 -m unittest -v skills/_checks/tests/test_end_state.py`.
- Portable pack: `python3 -m unittest discover -s portable-pack/tests -p "test_*.py"`.
- Everything a maintainer runs before a merge: `sh scripts/merge-check.sh .` (needs `uv`).

After changing anything in `skills`, rebuild the packs with
`python3 scripts/build-portable-pack.py` and commit `plugins` and `portable-pack` with it.
Run the checks closest to your change and say which ones you did not run.

## Prove a file task

```sh
python3 standards/run.py prepare brief-001 /absolute/path/new-run
# run OpenPaperwork on new-run/task only, save the result under new-run/first/
python3 standards/run.py revision /absolute/path/new-run
python3 standards/run.py check /absolute/path/new-run first
python3 standards/run.py check /absolute/path/new-run revision
```

The agent doing the task must not see this repository, the checker or the
revision request. A passing check is not acceptance; a person still reviews the
rendered file. Details: [standards/README.md](standards/README.md).

## Rules

- One purpose per pull request. Say what the person asked, what they got before
  and after, and what friction remains. See [CONTRIBUTING.md](CONTRIBUTING.md).
- Use invented or redistributable files. No credentials, customer files or
  private logs in code, fixtures, issues or pull requests.
- Anything copied from another project adds its notice to `THIRD_PARTY.md` and
  `licenses/` in the same change.
- Credits for the projects we build on stay in `THIRD_PARTY.md` and
  `docs/community-preview/CREDITS.md`.
- No telemetry, automatic updates or hosted sharing turned on by default.
- This tree has no agent of its own; do not add one. The library rides the agent the person
  already has.
- Never add a sign-in for an agent. Each agent signs in on its own, on the person's own account.
- Account sign-in, hosted services, team coordination, connections and built-in registrations stay out of this tree.
