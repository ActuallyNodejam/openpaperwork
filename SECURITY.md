# Reporting a security issue

For a suspected vulnerability, use the reporting contact and instructions in
[Nodejam's security policy](https://nodejam.com/security#reporting).
The current published [security.txt](https://nodejam.com/.well-known/security.txt)
lists [hello@nodejam.com](mailto:hello@nodejam.com).

Include the affected file or pack, the release or commit, reproduction
steps and expected versus observed behavior. Use synthetic data where possible.
Do not put credentials, customer files or vulnerability details in a public
issue or pull request.

Ordinary bugs and contribution ideas belong in repository issues.

## What the library does and does not do

OpenPaperwork is files: guidelines, starters and Python scripts. It runs inside
the agent you already use, with that agent's permissions, and is not a sandbox.
Nothing of ours listens on a port or sends telemetry; the plugin's check server
talks to your agent over stdio only.

- `npx skills add` only copies files.
- The Claude plugin adds three hooks, each a script in `portable-pack/hooks`: a
  first-session setup of its own Python packages and a Chromium for rendering, a
  hint when a request names a kind of file, and the pack check after a turn
  writes files.
- Some packs reach the network when used: the paper pack fetches its TeX engine
  from a pinned release checked by hash, reference checks look DOIs up in
  Crossref, literature search asks OpenAlex and PubMed, and the official
  e-invoice validators download only if you install them.

Run your agent inside a container or a virtual machine when you need isolation.
