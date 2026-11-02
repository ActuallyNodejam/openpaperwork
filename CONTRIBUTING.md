# Contributing to OpenPaperwork

You do not need to touch any agent to contribute. A standard your country or field uses, a sharper
check, a clearer guideline, a translation or a reproducible bug are all worth bringing.

## The most useful thing: a standard you know

Know your country's invoice, your university's thesis format or a citation style well? Open an
[Add a standard](https://github.com/ActuallyNodejam/openpaperwork/issues/new?template=add-a-standard.yml)
issue with the source first, so two people do not build the same one, then follow
[Add a standard](docs/community-preview/ADD_A_STANDARD.md). Issues labelled `standard` and
`good first issue` are ones we have scoped already.

## Begin with a person's task

Every change to what a file looks like or says should tell this short story:

1. What did the person ask, in their own words?
2. Which public-safe files did they start with?
3. What should they receive, and how can we check it?
4. What happened before and after the change?
5. What still needs a person to fix by hand?

"The pack supports format X" does not finish that story. "A seller in Germany gets an invoice
KoSIT accepts without retyping the buyer's routing ID" does. Use invented data or material you
have permission to redistribute.

## A small first change

Pick one [contribution idea](docs/community-preview/FIRST_CONTRIBUTIONS.md). For a defect, include
the smallest request and input that shows it. For a new pack or a large change, agree the
behaviour in an issue before building it. Keep one purpose per pull request.

## How a change reaches main

Fork the repository, make a branch, and open a pull request. CI runs the library's tests and every
check against its planted faults; no secret and no model is used. A maintainer reviews and
approves it. The maintainers keep this repository in step with their own tree, so an approved
pull request is brought in from there with your commits and your name
kept, and GitHub then shows it merged. Contributors are credited in the release notes.

## Show evidence

Use the checks closest to your change. For file work, preserve the original
output, show the revised output, and report the exact task and product versions.
Include rendered pages when layout matters and the editable file when the
task requires editability. State failures and checks you did not run.

The [file-task protocol](standards/README.md) separates mechanical checks
from factual and visual review. Passing one does not imply passing the others.
Do not give an agent the expected answers when you run a case. No real customer
files, private logs, credentials or paid services are required for these examples.

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
