# Help someone finish their work

You do not need to change the agent engine to contribute. A clearer example,
a better document check, a translation, or a reproducible bug can be valuable.

## Begin with a person's task

Every user-facing change should tell this short story:

1. What did the person ask, in their own words?
2. Which public-safe files did they start with?
3. What should they receive, and how can we check it?
4. What happened before and after the change?
5. What setup, interruption or manual correction is still necessary?

“The agent supports tool X” does not finish that story. “A purchasing assistant
can correct a delivery date without rebuilding the comparison” does.
Use invented data or material you have permission to redistribute.

## A small first change

Pick one [contribution idea](docs/community-preview/FIRST_CONTRIBUTIONS.md).
For a defect, include the smallest reproducible request and input. For a new
workflow or a large product change, agree the intended behavior in an issue
before building it. Keep one purpose per pull request.

The process is straightforward. Forking creates your own copy
on GitHub. A branch isolates a change. A pull request asks the maintainers to
review that change; it does not publish or deploy it. Automated checks and
agent-assisted review provide evidence. A maintainer reviews the evidence and
approves the merge. Contributors are credited in release notes.

## Show evidence

Use the checks closest to your change. For file work, preserve the original
output, show the revised output, and report the exact task and product versions.
Include rendered pages when layout matters and the editable file when the
task requires editability. State failures and checks you did not run.

The [file-task protocol](standards/README.md) separates mechanical checks
from factual and visual review. Passing one does not imply passing the others.
Do not give an agent the expected answers when you run a case. No real customer
files, private logs, credentials or paid services are required for these examples.

Paid model runs require a separately approved budget.

## Sign off your commits

Commit with `git commit -s`. It adds a `Signed-off-by:` line with your name, your word under the
[Developer Certificate of Origin](https://developercertificate.org/) that the change is yours to
give under this repository's Apache 2.0 licence. There is no contributor agreement to sign.

## Copy only what the licence allows

- MIT, Apache-2.0, CC BY, the Open Government Licence and the public domain may be copied, with
  credit in `THIRD_PARTY.md` and the licence under `licenses/`.
- CC BY-SA, CC BY-ND, GPL, AGPL and anything without a licence are read and learnt from, then
  written in your own words. Nothing from them is pasted in.
- Paid standards (ISO, CEN, DIN, IEEE and the like) are cited by clause number and paraphrased.
  Never paste their text, tables or figures.
- No logos or "certified" and "compliant" badges, of standards bodies or of anyone else.

## Before submitting

- Explain the user-visible improvement and remaining friction.
- Include focused validation and exact reproduction steps.
- Preserve required licenses and attribute copied work.
- Keep generated outputs out of code changes unless needed as small fixtures.
- Sign off every commit (`git commit -s`).
- For a fix, link the issue it fixes (`Fixes #123`). A pull request that does not follow the
  template is closed 72 hours after we ask; open it again once it does.
- Say in the pull request whether an AI tool helped, which one and how much.
- Use the [pull request template](.github/pull_request_template.md).

Everyone taking part follows the [code of conduct](CODE_OF_CONDUCT.md).
Translation, documentation and example contributions follow the same respectful
review process. Maintainers may request changes, explain why a contribution
does not fit, or mark an issue for a later release. No response-time promise
is made.
