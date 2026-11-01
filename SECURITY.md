# Reporting a security issue

For a suspected vulnerability, use the reporting contact and instructions in
[Nodejam's security policy](https://nodejam.com/security#reporting).
The current published [security.txt](https://nodejam.com/.well-known/security.txt)
lists [hello@nodejam.com](mailto:hello@nodejam.com).

Include the affected component, source revision or app version, reproduction
steps and expected versus observed behavior. Use synthetic data where possible.
Do not put credentials, customer files or vulnerability details in a public
issue or pull request.

Ordinary bugs and contribution ideas belong in repository issues.

## What the app does not promise

The agent is not sandboxed. The permission prompts keep a person aware of what
the agent does and are not a security boundary. Run the app inside a container
or a virtual machine when isolation is needed.
