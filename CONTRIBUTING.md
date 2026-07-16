# Contributing

## Laptop / second machine

See [docs/LAPTOP_SETUP.md](docs/LAPTOP_SETUP.md). Regenerate the local handoff bundle with `.\scripts\export_transfer.ps1` (creates gitignored `transfer/`).

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

- **Visitors** — [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) → `docs/architecture.html` (no env vars, deploy steps, or localhost).
- **Planned** — [`docs/PLANNED.md`](docs/PLANNED.md) → `docs/planned.html` (open decisions / future work).
- **Developers** — [`docs/ARCHITECTURE_DEVELOPER.md`](docs/ARCHITECTURE_DEVELOPER.md) → appended to `README.md` after [`docs/README_HEADER.md`](docs/README_HEADER.md).

After editing architecture, planned, changelog, or `README_HEADER.md`, run `python scripts/sync_docs.py`. Interactive pipeline: visitor copy in `docs/assets/pipeline-config.json`; technical copy in `docs/assets/pipeline-config-developer.json` (referenced from `ARCHITECTURE_DEVELOPER.md`).

## Code conventions

- Tag new modules with `# ROLE: ...` (harness, retriever, etc.).
- Run `ruff check src tests` and `pytest tests/` before committing.
