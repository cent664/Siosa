# Contributing

## Changelog (required)

Any **user-visible** or **architectural** change must update the changelog:

1. Add an entry to [`docs/CHANGELOG.md`](docs/CHANGELOG.md) (newest first), **or** run:

   ```powershell
   python scripts/add_changelog_entry.py "Short title" "What changed and why."
   ```

   Use bullet lines like `- Label — what changed` (em dash). Avoid `- **Label:**` — the HTML sync formats labels automatically.

2. Regenerate HTML and README:

   ```powershell
   python scripts/sync_docs.py
   ```

Source of truth: `docs/CHANGELOG.md`. Do not edit `docs/changelog.html` by hand.

## Architecture docs

Edit [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) only, then run `python scripts/sync_docs.py` to refresh `README.md` and `docs/architecture.html`.

## Code conventions

- Tag new modules with `# ROLE: ...` (harness, retriever, etc.).
- Run `ruff check src tests` and `pytest tests/` before committing.
