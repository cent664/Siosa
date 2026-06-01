#!/usr/bin/env python3
"""Prepend a dated entry to docs/CHANGELOG.md and regenerate HTML.

Prefer multi-line bullet bodies in CHANGELOG.md, e.g.:

  - Web UI — React SPA at /
  - Docs — Updated architecture diagram

Avoid `- **Label:**` — use `- Label —` instead.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CHANGELOG = ROOT / "docs" / "CHANGELOG.md"


def main() -> None:
    parser = argparse.ArgumentParser(description="Add a changelog entry")
    parser.add_argument("title", help="Entry title (after date)")
    parser.add_argument("description", help="Entry body (one paragraph)")
    parser.add_argument("--date", default=date.today().isoformat(), help="YYYY-MM-DD")
    args = parser.parse_args()

    entry = f"## {args.date} — {args.title}\n\n{args.description}\n\n"
    existing = CHANGELOG.read_text(encoding="utf-8") if CHANGELOG.exists() else ""
    CHANGELOG.write_text(entry + existing, encoding="utf-8")
    print(f"Prepended to {CHANGELOG}")

    sync = ROOT / "scripts" / "sync_docs.py"
    if sync.exists():
        subprocess.run([sys.executable, str(sync)], check=True)


if __name__ == "__main__":
    main()
