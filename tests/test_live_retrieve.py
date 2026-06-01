# Tests for live poewiki retrieval.

from __future__ import annotations

import json
from unittest.mock import patch

from poe_agent.generator.answer import _chunks_to_citations
from poe_agent.retriever.ingest import chunk_text
from poe_agent.retriever.live import fetch_page_chunks, retrieve_live_for_query
from poe_agent.retriever.wiki_client import search_wiki_titles


def test_search_wiki_titles_parses_hits():
    payload = {
        "query": {
            "search": [
                {"title": "Poison", "snippet": "..."},
                {"title": "Ignite", "snippet": "..."},
            ]
        }
    }

    with patch("poe_agent.retriever.wiki_client.httpx.Client") as mock_client:
        mock_client.return_value.__enter__.return_value.get.return_value.json.return_value = payload
        mock_client.return_value.__enter__.return_value.get.return_value.raise_for_status = lambda: None
        hits = search_wiki_titles("poison damage", limit=5)

    assert hits == [("Poison", "Poison"), ("Ignite", "Ignite")]


def test_fetch_page_chunks_uses_cache(tmp_path, monkeypatch):
    cache_dir = tmp_path / "live_cache"
    cache_dir.mkdir()
    cache_file = cache_dir / "Poison.json"
    cache_file.write_text(
        json.dumps(
            {
                "title": "Poison",
                "path": "Poison",
                "text": "Poison is a damage over time ailment.",
                "wiki_url": "https://www.poewiki.net/wiki/Poison",
                "fetched_at": 9_999_999_999.0,
            }
        ),
        encoding="utf-8",
    )

    monkeypatch.setenv("POE_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("LIVE_WIKI_CACHE_TTL_HOURS", "24")
    from poe_agent.harness.config import get_settings

    get_settings.cache_clear()
    settings = get_settings()

    with patch("poe_agent.retriever.live.fetch_page_text") as mock_fetch:
        chunks = fetch_page_chunks("Poison", "Poison", settings)
        mock_fetch.assert_not_called()

    assert len(chunks) >= 1
    assert chunks[0].metadata["wiki_url"] == "https://www.poewiki.net/wiki/Poison"
    assert chunks[0].metadata["source"] == "live"
    get_settings.cache_clear()


def test_retrieve_live_for_query_end_to_end(monkeypatch):
    monkeypatch.setenv("RETRIEVAL_MODE", "live")
    monkeypatch.setenv("LIVE_WIKI_MAX_PAGES", "1")
    from poe_agent.harness.config import get_settings

    get_settings.cache_clear()

    html = "<p>Poison deals chaos damage over time.</p>"
    search_hits = [("Poison", "Poison")]

    with (
        patch("poe_agent.retriever.live.search_wiki_titles", return_value=search_hits),
        patch(
            "poe_agent.retriever.live.fetch_page_text",
            return_value=("Poison deals chaos damage over time.", "https://www.poewiki.net/wiki/Poison"),
        ),
        patch("poe_agent.retriever.live.rerank") as mock_rerank,
    ):
        from poe_agent.retriever.models import RetrievedChunk

        def _fake_rerank(query, candidates, top_n=None):
            return [
                RetrievedChunk(
                    chunk_id=candidates[0].chunk_id,
                    text=candidates[0].text,
                    metadata=candidates[0].metadata,
                    score=0.91,
                )
            ]

        mock_rerank.side_effect = _fake_rerank
        results, debug = retrieve_live_for_query("how does poison work")

    assert len(results) == 1
    assert results[0].metadata["wiki_url"] == "https://www.poewiki.net/wiki/Poison"
    assert "how does poison work" in debug.fused_search_queries
    assert debug.chunks_returned == 1
    citations = _chunks_to_citations(results)
    assert citations[0]["url"] == "https://www.poewiki.net/wiki/Poison"
    assert "poison" in citations[0]["title"].lower()
    get_settings.cache_clear()


def test_chunk_text_live_metadata():
    chunks = chunk_text("word " * 400, "Poison", "https://www.poewiki.net/wiki/Poison")
    assert chunks[0].metadata["wiki_url"].endswith("/wiki/Poison")


def test_multi_search_dedupes_titles(monkeypatch):
    monkeypatch.setenv("LIVE_WIKI_MAX_SEARCH_QUERIES", "4")
    from poe_agent.harness.config import get_settings

    get_settings.cache_clear()

    def _fake_search(query: str, limit: int = 8):
        if "powers" in query.casefold():
            return [("Ruthless mode", "Ruthless_mode")]
        return [("Buff", "Buff")]

    with patch("poe_agent.retriever.live.search_wiki_titles", side_effect=_fake_search):
        from poe_agent.retriever.live import _merge_search_hits

        hits = _merge_search_hits(
            ["What are Pantheon powers?", "Pantheon"],
            get_settings(),
        )
        paths = {h.path for h in hits}
        assert "Ruthless_mode" in paths
        assert "Buff" in paths
        assert len(paths) >= 2

    get_settings.cache_clear()


def test_pantheon_title_probe_beats_ruthless(monkeypatch):
    user_q = "What are Pantheon powers?"
    verbose = "Pantheon powers Path of Exile mechanics"
    monkeypatch.setenv("LIVE_WIKI_MAX_PAGES", "5")
    monkeypatch.setenv("LIVE_WIKI_TITLE_PROBE", "true")
    monkeypatch.setenv("LIVE_WIKI_TITLE_OVERLAP_FILTER", "true")
    from poe_agent.harness.config import get_settings

    get_settings.cache_clear()

    pantheon_text = (
        "The Pantheon is a system of divine powers granted by the gods. "
        "Major gods and minor gods offer Pantheon powers to characters."
    )
    ruthless_text = "Pantheon powers are disabled in Ruthless mode."

    def _fake_search(query: str, limit: int = 8):
        return [("Ruthless mode", "Ruthless_mode"), ("Buff", "Buff")]

    def _fake_fetch(title: str, path: str | None = None):
        if "Pantheon" in title and "Ruthless" not in title:
            return pantheon_text, "https://www.poewiki.net/wiki/Pantheon"
        return ruthless_text, f"https://www.poewiki.net/wiki/{path or title}"

    with (
        patch("poe_agent.retriever.live.search_wiki_titles", side_effect=_fake_search),
        patch("poe_agent.retriever.live.fetch_page_text", side_effect=_fake_fetch),
        patch("poe_agent.retriever.live.rerank") as mock_rerank,
    ):
        from poe_agent.retriever.models import RetrievedChunk

        def _fake_rerank(query, candidates, top_n=None):
            return sorted(
                [
                    RetrievedChunk(c.chunk_id, c.text, c.metadata, 0.5 + i * 0.01)
                    for i, c in enumerate(candidates)
                ],
                key=lambda x: x.metadata.get("page_title", ""),
                reverse=True,
            )

        mock_rerank.side_effect = _fake_rerank
        results, debug = retrieve_live_for_query(verbose, user_question=user_q)

    assert results
    assert user_q in debug.fused_search_queries
    assert debug.pages_fetched
    top_title = results[0].metadata.get("page_title", "")
    assert top_title == "Pantheon"
    get_settings.cache_clear()


def test_retrieval_gate_title_mismatch(monkeypatch):
    monkeypatch.setenv("RETRIEVAL_REFINE_ENABLED", "true")
    from poe_agent.harness.config import get_settings
    from poe_agent.retriever.gate import retrieval_needs_refine
    from poe_agent.retriever.models import RetrievedChunk

    get_settings.cache_clear()
    chunks = [
        RetrievedChunk("1", "x", {"page_title": "Ruthless mode"}, 0.5),
    ]
    needs, reason = retrieval_needs_refine(chunks, "What are Pantheon powers?")
    assert needs is True
    assert reason == "title_mismatch"
    get_settings.cache_clear()
