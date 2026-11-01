# Releasing

A release is a tag and notes a maintainer writes. Nothing ships on its own, and nothing
binary ships at all: the repository is the library.

1. The main line is green in CI.
2. `NODEJAM_VERSION` holds the new version, and the plugin versions in
   `.claude-plugin/marketplace.json` are raised if a pack changed.
3. Tag and push: `git tag v$(cat NODEJAM_VERSION) && git push origin v$(cat NODEJAM_VERSION)`.
4. A maintainer writes the release notes so they say what a person can now do, and credits
   contributors (`gh release create` or the Releases page).

A pack change is on the main line once it is
merged, and its plugin version is raised in the same change.
