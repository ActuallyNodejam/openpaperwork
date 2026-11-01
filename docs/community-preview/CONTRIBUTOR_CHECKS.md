# Checks for contributions

Two workflows in `.github/workflows` cover the library. `ci.yml` runs the library tests, the case
protocol, the pack-check end state, the portable pack tests and the planted faults.
`community-checks.yml` runs the case protocol and checks that every commit is signed off (DCO). Both
run on an ephemeral GitHub-hosted runner and need no model, provider key, deployment token or
customer material. A green result means those checks passed, not that OpenPaperwork completed a real
task correctly.

## Choose the evidence for the change

| Change | Useful check | What it does not prove |
| --- | --- | --- |
| Case protocol or case structure | File-task protocol tests | A model's answer quality |
| A pack, a rule or a check | Library tests, planted faults and the portable pack tests | That a model uses the pack well |
| A document, sheet or deck workflow | First output, revision, native checks and rendered review | General reliability from one task |

For a manual protocol check, run from `standards`:

```sh
python3 -m unittest -v test_protocol.py
```

Use Python 3.10 or newer. The command uses the standard library. The other test commands are
listed in `.github/workflows/ci.yml`.
Run selected checks in an isolated development environment and report failures
or commands not run. A screenshot can establish layout; it cannot establish
that spreadsheet formulas recalculate correctly.

## What CI covers

CI and the community checks cover the library: `skills`, `standards`, `plugins` and
`portable-pack`. They do not run a model, so they do not cover a real agent run. Maintainers
review the focused evidence for such a change. Do not treat a missing or skipped check as a
passing product check.

The checkout does not persist its token, and workflow permissions are read-only.
There is no `pull_request_target`, publishing job, paid agent review, shared
runner or reference to repository secrets. Fork pull requests never receive
model credentials.

## Helper workflows

`.github/workflows` also holds two maintainer helpers, `pr-standards` and `close-waiting`. They run
no model.

- `pr-standards` uses `pull_request_target` to label and comment on fork pull
  requests. It checks out nothing, runs no pull request code and uses no
  secrets. It reads only the description and the template on the default branch.
  Do not add a checkout or a secret to it.
- `close-waiting.yml` runs on a schedule. It closes a pull request that still does not follow the
  template 72 hours after `pr-standards` commented on it, and an issue labelled `needs:repro` after
  3 days with no activity. Maintainers and team members are never closed. It checks out nothing,
  runs no pull request code and uses no secrets.

See GitHub's [secure use guidance](https://docs.github.com/en/actions/reference/security/secure-use)
for permission and untrusted-code boundaries.
