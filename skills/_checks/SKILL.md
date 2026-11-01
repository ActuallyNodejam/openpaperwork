---
name: _checks
description: "Support files for the OpenPaperwork packs: the pack checks (packcheck.py) and the rules they read. Never a task on its own; a pack runs its check from here."
---

# _checks

Support files for the OpenPaperwork packs: the pack checks (packcheck.py) and the rules they read. Never a task on its own; a pack runs its check from here.

`npx skills add` and `portable-pack/install.sh` put this folder beside the packs, where their
scripts look for it (`<skills>/_checks`). Leave it there; nothing in it is a task to start.
