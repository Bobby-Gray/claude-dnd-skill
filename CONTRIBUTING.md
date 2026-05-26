# Contributing to claude-dnd-skill

Thanks for your interest in contributing — pull requests are welcome. A few practical notes below.

## License of contributions

By submitting a pull request, you agree that your contribution is licensed under the [GNU Affero General Public License v3.0 or later](LICENSE), the same license as the rest of the project.

You retain copyright on your own contributions. AGPL-3.0-or-later applies forward from your contribution onward; the combined work remains licensed under AGPL-3.0-or-later.

## What's most useful to contribute

- **Bug fixes** on the display companion, dice mechanics, session-flow scripts, or anything in `scripts/`
- **i18n / language packs** for SFX triggers — see `display/audio.py` for the existing pattern. #32 added Chinese; more languages are very welcome
- **Atmospheric extensions** like the optional dice server (#30) — anything that improves the in-person table experience without compromising the persistent-state model
- **Performance and cleanup** in the Python helper modules

## Process

1. For substantive changes, open an issue first — gives a chance to align on scope before code is written
2. Small bug fixes or doc improvements can go straight to a PR
3. Write a clear PR description that explains the *why*, not just the *what*
4. There's no CI; the maintainer reviews PRs manually
5. The maintainer may apply minor hardening on top of merged PRs (e.g. tightening defaults, adding SRI on CDN-loaded assets) — these are documented as separate follow-up commits in the same release, never as edits to your work

## Questions

Open an issue or comment on an existing PR. The maintainer reads everything.
