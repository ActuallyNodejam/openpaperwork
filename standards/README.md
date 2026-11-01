# The library's standards

What every pack is held to: the guidelines with their sources, invented cases, and the scripted
checks that read a finished file. Every case can be rerun.

| Path | What it holds |
| --- | --- |
| `guidelines/<issuer>/<version>/guidelines.json` | The rules in plain sentences, each with an id, tied to a named source, version and licence |
| `checks/` | Scripts that read a finished file and decide each rule: `check(rule_id, path, case, stage)` returns pass or fail with the evidence |
| `cases/<sector>/<occupation>/<task>/` | An invented task: the request, one later change, the input files, and the facts a correct file contains |
| `catalogue.json` | Every case with its id, version, format and path |
| `run.py` | Prepares a case for a run and checks what came back |

[PACKS.md](PACKS.md) lists each guideline set with its check and its starter. Every source and
its licence is in [SOURCES.md](SOURCES.md). Sectors are NAICS 2022 sectors and occupations are
O*NET-SOC 2019 codes; each case lists criteria that cite rules as `<issuer>/<version>#<ID>`.

Python 3.10+ and the standard library are enough for the commands below. The checker reads
supplied files offline; it never calls a model, installs software or uploads anything. Running an
agent is a separate step.

A clean check means the file meets the rules taken from a named source and version. It is not
legal compliance or certification, and a few small cases say nothing about work in general.

## Prepare a case

From this directory, give a new directory outside the source checkout:

```sh
python3 run.py prepare brief-001 /absolute/path/to/new-run
```

This creates `task/request.md` and `task/inputs/`, plus separate `first/` and
`revision/` output folders and `run.json`. Give the agent only `task/` as its
working context and the requested output destination. It must not see this
repository, the checker, the review questions, the revision request or earlier answers.
Preparation is a file convenience, not a sandbox; whoever runs the case enforces
that boundary with the runner they chose.

Run the agent, keep the full transcript and the output under `first/`, and record the model and
tool versions, the product commit, elapsed time, retries and interruptions in `run.json`. Unknown
values stay null, never zero.

```sh
python3 run.py revision /absolute/path/to/new-run
```

This freezes the first file's hash and then reveals `task/revision.md`.
Continue the same conversation, using the first output as
input and saving the revised file under `revision/`. Never overwrite the
first file. The checker detects a changed frozen first output.

## Check what came back

```sh
python3 run.py check /absolute/path/to/new-run first
python3 run.py check /absolute/path/to/new-run revision
```

Reports are saved under `reports/`. Mechanical checks cover required files,
OOXML package parsing, editable text, required deck length, and the explicit
spreadsheet table, totals and formula presence. A valid package is not proof
that a particular application renders it correctly. Formula caches are checked
but do not establish live recalculation or formula correctness.

Each report includes the case's factual and visual review questions. Render
the file with a named engine and version and keep the page images. For a
spreadsheet, recalculate it and change an input in a working copy.
Record observations, page or cell references and evidence paths. Judge meaning, not exact wording.
A failed factual requirement is never averaged into a pass on looks.

The script always leaves overall acceptance at `needs_review` when the mechanical
checks pass. A named reviewer separately records a decision and its
evidence in `review-first.json` / `review-revision.json` following
`review.template.json`. A reviewer can be wrong; keep the method and any disagreement.
A checker cannot certify its own output.

Exit codes are 0 for mechanical checks passed, 1 for failed checks and 2 for
invalid invocation or input. A zero exit code is **not overall acceptance**.

## Say what happened

Report the first attempt and the revision separately. Keep failures, every retry, source versions,
input and output hashes and any repair done by hand. Use null for what was not measured. A
comparison states the case versions, tools and repeat counts on both sides. This folder holds
standards, cases and checks; it carries no results table and makes no claim about any agent or model.

Templates the packs use belong in `skills/`; expected answers belong here. A new institution's or
country's requirement names its exact source, scope and version.
