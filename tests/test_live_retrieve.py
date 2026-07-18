# Tests for live poewiki retrieval.

from __future__ import annotations

import json
from unittest.mock import patch

from poe_agent.generator.answer import _chunks_to_citations
from poe_agent.retriever.ingest import chunk_text
from poe_agent.retriever.live import diversify_chunks_by_page, fetch_page_chunks, retrieve_live_for_query
from poe_agent.retriever.models import RetrievedChunk
from poe_agent.retriever.wiki_client import html_to_text, search_wiki_titles


def test_search_wiki_titles_parses_hits():
    payload = {
        "query": {
            "search": [
                {"title": "Poison", "snippet": "..."},
                {"title": "Ignite", "snippet": "..."},
            ]
        }
    }

    with patch("poe_agent.retriever.wiki_client._api_get", return_value=payload):
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
                "text": "Poison is a damage over time ailment. " * 20,
                "wiki_url": "https://www.poewiki.net/wiki/Poison",
                "links": [],
                "links_version": 3,
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

    with patch("poe_agent.retriever.live.fetch_page_payload") as mock_fetch:
        chunks, links = fetch_page_chunks("Poison", "Poison", settings)
        mock_fetch.assert_not_called()

    assert len(chunks) >= 1
    assert chunks[0].metadata["wiki_url"] == "https://www.poewiki.net/wiki/Poison"
    assert chunks[0].metadata["source"] == "live"
    assert links == []
    get_settings.cache_clear()


def test_retrieve_live_for_query_end_to_end(monkeypatch):
    monkeypatch.setenv("RETRIEVAL_MODE", "live")
    monkeypatch.setenv("LIVE_WIKI_MAX_PAGES", "1")
    monkeypatch.setenv("LIVE_WIKI_LINK_EXPAND", "false")
    from poe_agent.harness.config import get_settings

    get_settings.cache_clear()

    search_hits = [("Poison", "Poison")]

    with (
        patch("poe_agent.retriever.live.search_wiki_titles", return_value=search_hits),
        patch(
            "poe_agent.retriever.live.fetch_page_payload",
            return_value=("Poison deals chaos damage over time.", "https://www.poewiki.net/wiki/Poison", []),
        ),
        patch("poe_agent.retriever.live.rerank") as mock_rerank,
    ):
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


def test_rank_search_hits_prefers_mechanic_titles(monkeypatch):
    from poe_agent.retriever.live import _PageHit, _rank_search_hits_by_title

    hits = [
        _PageHit("Skill", "Skill", "search", "long question"),
        _PageHit("Ignite", "Ignite", "search", "ignite"),
        _PageHit("List of unique gloves", "List_of_unique_gloves", "search", "long question"),
        _PageHit("Righteous Fire", "Righteous_Fire", "search", "righteous fire"),
    ]
    ranked = _rank_search_hits_by_title(
        hits,
        "What is the difference between ignite and righteous fire?",
    )
    titles = [h.title for h in ranked]
    assert titles[0] in ("Ignite", "Righteous Fire")
    assert titles[1] in ("Ignite", "Righteous Fire")
    assert titles[-1] in ("Skill", "List of unique gloves")


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

        hits, errors = _merge_search_hits(
            ["What are Pantheon powers?", "Pantheon"],
            get_settings(),
        )
        paths = {h.path for h in hits}
        assert "Ruthless_mode" in paths
        assert "Buff" in paths
        assert len(paths) >= 2
        assert errors == []

    get_settings.cache_clear()


def test_pantheon_title_probe_beats_ruthless(monkeypatch):
    user_q = "What are Pantheon powers?"
    verbose = "Pantheon powers Path of Exile mechanics"
    monkeypatch.setenv("LIVE_WIKI_MAX_PAGES", "5")
    monkeypatch.setenv("LIVE_WIKI_TITLE_PROBE", "true")
    monkeypatch.setenv("LIVE_WIKI_TITLE_OVERLAP_FILTER", "true")
    monkeypatch.setenv("LIVE_WIKI_LINK_EXPAND", "false")
    from poe_agent.harness.config import get_settings

    get_settings.cache_clear()

    pantheon_text = (
        "The Pantheon is a system of divine powers granted by the gods. "
        "Major gods and minor gods offer Pantheon powers to characters."
    )
    ruthless_text = "Pantheon powers are disabled in Ruthless mode."

    def _fake_search(query: str, limit: int = 8):
        return [("Ruthless mode", "Ruthless_mode"), ("Buff", "Buff")]

    def _fake_fetch(title: str, path: str | None = None, **kwargs):
        if "Pantheon" in title and "Ruthless" not in title:
            return pantheon_text, "https://www.poewiki.net/wiki/Pantheon", []
        return ruthless_text, f"https://www.poewiki.net/wiki/{path or title}", []

    with (
        patch("poe_agent.retriever.live.search_wiki_titles", side_effect=_fake_search),
        patch("poe_agent.retriever.live.fetch_page_payload", side_effect=_fake_fetch),
        patch("poe_agent.retriever.live.rerank") as mock_rerank,
    ):
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

    get_settings.cache_clear()
    chunks = [
        RetrievedChunk("1", "x", {"page_title": "Ruthless mode"}, 0.5),
    ]
    needs, reason = retrieval_needs_refine(chunks, "What are Pantheon powers?")
    assert needs is True
    assert reason == "title_mismatch"
    get_settings.cache_clear()


def test_diversify_chunks_by_page():
    chunks = [
        RetrievedChunk("a1", "t1", {"page_title": "Pantheon", "wiki_url": "u1"}, 0.9),
        RetrievedChunk("a2", "t2", {"page_title": "Pantheon", "wiki_url": "u1"}, 0.8),
        RetrievedChunk("a3", "t3", {"page_title": "Pantheon", "wiki_url": "u1"}, 0.7),
        RetrievedChunk("b1", "t4", {"page_title": "Shakari", "wiki_url": "u2"}, 0.6),
    ]
    out = diversify_chunks_by_page(chunks, top_n=3, max_per_page=2)
    assert len(out) == 3
    assert sum(1 for c in out if c.metadata["wiki_url"] == "u1") == 2
    assert any(c.metadata["wiki_url"] == "u2" for c in out)


def test_followup_rewrite_adds_prior_title():
    from poe_agent.retriever.followup import (
        is_topic_continuation,
        rewrite_followup_question,
    )

    out = rewrite_followup_question("list all of them", ["Pantheon"])
    assert "Pantheon" in out
    assert rewrite_followup_question("What are Pantheon powers?", ["Pantheon"]) == (
        "What are Pantheon powers?"
    )
    # New topic must not bake in Pantheon
    assert rewrite_followup_question("How does poison damage scale?", ["Pantheon"]) == (
        "How does poison damage scale?"
    )
    assert is_topic_continuation("list all of them", ["Pantheon"]) is True
    assert is_topic_continuation(
        "How does poison damage scale?",
        ["Pantheon"],
        prior_questions=["What are Pantheon powers?"],
    ) is False


def test_structure_aware_tables_keep_cells():
    html = """
    <div>
      <table>
        <tr><th>God</th><th>Power</th></tr>
        <tr><td>Shakari</td><td>Chaos</td></tr>
      </table>
    </div>
    """
    text = html_to_text(html, structure_aware=True)
    assert "Shakari" in text
    assert "Chaos" in text


def test_fetch_payload_follows_redirects():
    """Pantheon redirects to The Pantheon — parse must use redirects=1."""
    redirect_html = (
        '<div class="mw-parser-output"><div class="redirectMsg">'
        '<p>Redirect to:</p><ul class="redirectText">'
        '<li><a href="/wiki/The_Pantheon">The Pantheon</a></li></ul></div></div>'
    )
    real_html = (
        "<div class='mw-parser-output'><p>"
        + ("The Pantheon grants divine powers. " * 40)
        + "</p>"
        '<table class="wikitable"><tr><td><a href="/wiki/Shakari">Shakari</a></td></tr></table>'
        "</div>"
    )

    def _api(params: dict):
        if params.get("action") == "parse":
            assert params.get("redirects") == "1"
            return {"parse": {"title": "The Pantheon", "text": real_html}}
        raise AssertionError(params)

    with patch("poe_agent.retriever.wiki_client._api_get", side_effect=_api):
        from poe_agent.retriever.wiki_client import fetch_page_payload

        text, url, links = fetch_page_payload("Pantheon", "Pantheon", structure_aware=True)
    assert "divine powers" in text
    assert "The_Pantheon" in url or "The Pantheon" in url.replace("_", " ")
    assert "Shakari" in links
    assert not text.lstrip().lower().startswith("redirect to")
    # Stub HTML alone must not be accepted as content
    with patch(
        "poe_agent.retriever.wiki_client._api_get",
        return_value={"parse": {"title": "Pantheon", "text": redirect_html}},
    ):
        try:
            fetch_page_payload("Pantheon", "Pantheon")
            raise AssertionError("expected redirect stub to raise")
        except RuntimeError as exc:
            assert "redirect" in str(exc).lower()


def test_extract_prefers_table_links_over_nav():
    from poe_agent.retriever.wiki_client import extract_wiki_link_titles

    html = """
    <div>
      <table class="navbox"><tr><td><a href="/wiki/Useless_Nav">Useless Nav</a></td></tr></table>
      <p><a href="/wiki/Early_Body">Early Body</a></p>
      <table class="wikitable">
        <tr><td><a href="/wiki/Shakari">Shakari</a></td>
            <td><a href="/wiki/Brine_King">Brine King</a></td></tr>
      </table>
      <p><a href="/wiki/Later_Body">Later Body</a></p>
    </div>
    """
    links = extract_wiki_link_titles(html, max_links=10, prefer_table_links=True)
    assert "Useless Nav" not in links  # navbox stripped
    assert links[0] in ("Shakari", "Brine King")
    assert "Shakari" in links and "Brine King" in links
    # Table links before remaining body links
    assert links.index("Shakari") < links.index("Early Body") or links.index("Brine King") < links.index(
        "Early Body"
    )


def test_enumerate_expands_more_table_links(tmp_path, monkeypatch):
    monkeypatch.setenv("POE_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("LIVE_WIKI_MAX_PAGES", "1")
    monkeypatch.setenv("LIVE_WIKI_LINK_EXPAND", "true")
    monkeypatch.setenv("LIVE_WIKI_LINK_EXPAND_MAX", "1")
    monkeypatch.setenv("LIVE_WIKI_LINK_EXPAND_ENUMERATE_MAX", "3")
    monkeypatch.setenv("LIVE_WIKI_TITLE_PROBE", "false")
    from poe_agent.harness.config import get_settings

    get_settings.cache_clear()

    def _fake_search(query: str, limit: int = 8):
        return [("Pantheon", "Pantheon")]

    def _fake_fetch(title: str, path: str | None = None, **kwargs):
        if title == "Pantheon" or path == "Pantheon":
            return (
                "Pantheon index",
                "https://www.poewiki.net/wiki/Pantheon",
                ["Shakari", "Brine King", "Arakaali", "Noise Page"],
            )
        return (f"{title} page", f"https://www.poewiki.net/wiki/{path or title}", [])

    with (
        patch("poe_agent.retriever.live.search_wiki_titles", side_effect=_fake_search),
        patch("poe_agent.retriever.live.fetch_page_payload", side_effect=_fake_fetch),
        patch("poe_agent.retriever.live.rerank") as mock_rerank,
    ):
        def _fake_rerank(query, candidates, top_n=None):
            return [
                RetrievedChunk(c.chunk_id, c.text, c.metadata, float(i))
                for i, c in enumerate(reversed(candidates))
            ]

        mock_rerank.side_effect = _fake_rerank
        _results, debug = retrieve_live_for_query(
            "list all of them",
            user_question="list all of them",
            extra_title_probes=["Pantheon"],
        )

    titles = {r.get("title") for r in debug.pages_fetched}
    assert "Pantheon" in titles
    # Enumerate max 3 extras (not capped at LINK_EXPAND_MAX=1)
    assert len([t for t in titles if t != "Pantheon"]) == 3
    assert "Shakari" in titles
    get_settings.cache_clear()
