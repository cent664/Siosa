# Tests for retriever module.

from __future__ import annotations

import json

from poe_agent.retriever.hybrid import reciprocal_rank_fusion
from poe_agent.retriever.ingest import chunk_text
from poe_agent.retriever.models import RetrievedChunk
from poe_agent.retriever.sparse import _tokenize


def test_chunk_text_produces_multiple_chunks():
    text = "word " * 500
    chunks = chunk_text(text, "Poison", "https://www.poewiki.net/wiki/Poison")
    assert len(chunks) >= 2
    assert chunks[0].metadata["page_title"] == "Poison"
    assert chunks[0].metadata["game"] == "poe1"


def test_tokenize_lowercase():
    tokens = _tokenize("Increased Poison Damage 10%")
    assert "poison" in tokens
    assert "damage" in tokens


def test_rrf_merges_lists():
    a = [
        RetrievedChunk("1", "a", {"page_title": "Poison"}, 0.9),
        RetrievedChunk("2", "b", {"page_title": "Ignite"}, 0.5),
    ]
    b = [
        RetrievedChunk("2", "b", {"page_title": "Ignite"}, 0.8),
        RetrievedChunk("3", "c", {"page_title": "Bleed"}, 0.4),
    ]
    fused = reciprocal_rank_fusion([a, b])
    ids = [c.chunk_id for c in fused]
    assert ids[0] == "2"
    assert set(ids) == {"1", "2", "3"}


def test_load_chunks_from_fixture(tmp_path, monkeypatch):
    chunks_dir = tmp_path / "chunks"
    chunks_dir.mkdir()
    row = {
        "chunk_id": "abc",
        "text": "Poison is a damage over time ailment.",
        "metadata": {"page_title": "Poison", "wiki_url": "https://x", "game": "poe1"},
    }
    (chunks_dir / "chunks.jsonl").write_text(json.dumps(row) + "\n", encoding="utf-8")

    monkeypatch.setenv("POE_DATA_DIR", str(tmp_path))
    from poe_agent.harness.config import get_settings

    get_settings.cache_clear()

    from poe_agent.retriever.ingest import load_chunks

    loaded = load_chunks()
    assert len(loaded) == 1
    assert loaded[0].metadata["page_title"] == "Poison"
    get_settings.cache_clear()
