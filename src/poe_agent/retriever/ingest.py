# ROLE: retriever — fetch wiki pages, clean, chunk, and write JSONL corpus.

from __future__ import annotations

import json
import uuid
from pathlib import Path

import yaml

from poe_agent.harness.config import get_settings
from poe_agent.retriever.models import ChunkRecord
from poe_agent.retriever.wiki_client import fetch_page_text, polite_delay

CHUNK_CHARS = 1800
CHUNK_OVERLAP = 200


def _package_seed_path() -> Path:
    return Path(__file__).resolve().parent.parent / "knowledge" / "seed_pages.yaml"


def chunk_text(text: str, page_title: str, wiki_url: str, section: str = "") -> list[ChunkRecord]:
    chunks: list[ChunkRecord] = []
    start = 0
    while start < len(text):
        end = start + CHUNK_CHARS
        piece = text[start:end].strip()
        if piece:
            chunks.append(
                ChunkRecord(
                    chunk_id=str(uuid.uuid4()),
                    text=piece,
                    metadata={
                        "page_title": page_title,
                        "wiki_url": wiki_url,
                        "section": section,
                        "game": "poe1",
                        "source": "ingest",
                    },
                )
            )
        start = end - CHUNK_OVERLAP
        if end >= len(text):
            break
    return chunks


def run_ingest() -> Path:
    settings = get_settings()
    settings.raw_dir.mkdir(parents=True, exist_ok=True)
    settings.chunks_dir.mkdir(parents=True, exist_ok=True)

    with open(_package_seed_path(), encoding="utf-8") as f:
        seed = yaml.safe_load(f)

    all_chunks: list[ChunkRecord] = []
    for page in seed["pages"]:
        title = page["title"]
        path = page["path"]
        print(f"Fetching {title}...")
        try:
            text, url = fetch_page_text(title, path)
        except Exception as exc:
            print(f"  skip {title}: {exc}")
            continue
        raw_path = settings.raw_dir / f"{path}.txt"
        raw_path.write_text(text, encoding="utf-8")
        page_chunks = chunk_text(text, title, url)
        all_chunks.extend(page_chunks)
        polite_delay()

    out = settings.chunks_dir / "chunks.jsonl"
    with open(out, "w", encoding="utf-8") as f:
        for ch in all_chunks:
            f.write(
                json.dumps(
                    {"chunk_id": ch.chunk_id, "text": ch.text, "metadata": ch.metadata},
                    ensure_ascii=False,
                )
                + "\n"
            )
    print(f"Wrote {len(all_chunks)} chunks to {out}")
    return out


def load_chunks() -> list[ChunkRecord]:
    path = get_settings().chunks_dir / "chunks.jsonl"
    if not path.exists():
        return []
    records: list[ChunkRecord] = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            row = json.loads(line)
            records.append(
                ChunkRecord(chunk_id=row["chunk_id"], text=row["text"], metadata=row["metadata"])
            )
    return records


def main() -> None:
    run_ingest()
    from poe_agent.retriever.embed import build_index

    build_index()


if __name__ == "__main__":
    main()
