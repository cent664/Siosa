# ROLE: retriever — live poewiki search, fetch, and in-memory retrieval.

from __future__ import annotations

import json
import re
import time
from dataclasses import dataclass
from pathlib import Path

from poe_agent.harness.config import Settings, get_settings
from poe_agent.retriever.ingest import chunk_text
from poe_agent.retriever.models import ChunkRecord, RetrievedChunk
from poe_agent.retriever.query_fusion import (
    build_search_queries,
    extract_topic_terms,
    title_probe_candidates,
)
from poe_agent.retriever.rerank import rerank
from poe_agent.retriever.retrieval_debug import RetrievalDebugInfo
from poe_agent.retriever.wiki_client import WIKI_BASE, fetch_page_text, polite_delay, search_wiki_titles


@dataclass
class _PageHit:
    title: str
    path: str
    fetch_reason: str
    search_query: str = ""


def _cache_path(settings: Settings, path: str) -> Path:
    return settings.live_cache_dir / f"{path}.json"


def _read_cache(settings: Settings, path: str, ttl_hours: float) -> tuple[str, str] | None:
    cache_file = _cache_path(settings, path)
    if not cache_file.is_file():
        return None
    try:
        row = json.loads(cache_file.read_text(encoding="utf-8"))
        fetched_at = float(row.get("fetched_at", 0))
        if (time.time() - fetched_at) > ttl_hours * 3600:
            return None
        text = row.get("text", "")
        url = row.get("wiki_url", "")
        if text and url:
            return text, url
    except (json.JSONDecodeError, OSError, ValueError):
        return None
    return None


def _write_cache(settings: Settings, path: str, title: str, text: str, url: str) -> None:
    settings.live_cache_dir.mkdir(parents=True, exist_ok=True)
    cache_file = _cache_path(settings, path)
    cache_file.write_text(
        json.dumps(
            {
                "title": title,
                "path": path,
                "text": text,
                "wiki_url": url,
                "fetched_at": time.time(),
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )


def fetch_page_chunks(
    title: str,
    path: str,
    settings: Settings | None = None,
    *,
    fetch_reason: str = "search",
    search_query: str = "",
) -> list[ChunkRecord]:
    s = settings or get_settings()
    cached = _read_cache(s, path, s.live_wiki_cache_ttl_hours)
    if cached:
        text, url = cached
    else:
        text, url = fetch_page_text(title, path)
        _write_cache(s, path, title, text, url)
        polite_delay()

    if not text.strip():
        return []

    chunks = chunk_text(text, title, url)
    for ch in chunks:
        ch.metadata["source"] = "live"
        ch.metadata["retrieval"] = "live"
        ch.metadata["fetch_reason"] = fetch_reason
        if search_query:
            ch.metadata["search_query"] = search_query
    return chunks


def _merge_search_hits(
    search_queries: list[str],
    settings: Settings,
) -> list[_PageHit]:
    by_path: dict[str, _PageHit] = {}
    order: list[str] = []

    for sq in search_queries:
        try:
            hits = search_wiki_titles(sq, limit=settings.live_wiki_search_limit)
        except Exception:
            continue
        for title, path in hits:
            if path not in by_path:
                by_path[path] = _PageHit(title, path, "search", sq)
                order.append(path)

    return [by_path[p] for p in order]


def _prepend_title_probes(
    pages: list[_PageHit],
    user_question: str,
    settings: Settings,
) -> list[_PageHit]:
    if not settings.live_wiki_title_probe:
        return pages

    existing = {p.path for p in pages}
    probed: list[_PageHit] = []
    for candidate in title_probe_candidates(user_question):
        path = candidate.replace(" ", "_")
        if path in existing:
            continue
        probed.append(_PageHit(candidate, path, "title_probe", ""))
        existing.add(path)

    return probed + pages


def _title_overlap_score(page_title: str, topic_terms: list[str]) -> float:
    if not topic_terms:
        return 1.0
    title_tokens = set(re.findall(r"[a-z0-9]+", page_title.lower()))
    if not title_tokens:
        return 0.0
    for term in topic_terms:
        term_tokens = set(re.findall(r"[a-z0-9]+", term.lower()))
        if term_tokens and term_tokens & title_tokens:
            return 1.0
    return 0.0


def _apply_title_overlap_penalty(
    chunks: list[RetrievedChunk],
    user_question: str,
    settings: Settings,
) -> list[RetrievedChunk]:
    if not settings.live_wiki_title_overlap_filter:
        return chunks
    terms = extract_topic_terms(user_question)
    if not terms:
        return chunks

    adjusted: list[RetrievedChunk] = []
    for ch in chunks:
        title = str(ch.metadata.get("page_title", ""))
        overlap = _title_overlap_score(title, terms)
        penalty = 0.0 if overlap >= 1.0 else -2.0
        adjusted.append(
            RetrievedChunk(
                chunk_id=ch.chunk_id,
                text=ch.text,
                metadata=ch.metadata,
                score=ch.score + penalty,
            )
        )
    return sorted(adjusted, key=lambda c: c.score, reverse=True)


def _page_hit_to_debug_row(hit: _PageHit, fetch_ok: bool) -> dict:
    return {
        "title": hit.title,
        "path": hit.path,
        "wiki_url": f"{WIKI_BASE}/{hit.path}",
        "fetch_reason": hit.fetch_reason,
        "search_query": hit.search_query,
        "fetch_ok": fetch_ok,
    }


def _collect_pages_from_hits(
    pages: list[_PageHit],
    settings: Settings,
) -> tuple[list[ChunkRecord], list[dict]]:
    all_chunks: list[ChunkRecord] = []
    page_rows: list[dict] = []
    for hit in pages[: settings.live_wiki_max_pages]:
        try:
            chunks = fetch_page_chunks(
                hit.title,
                hit.path,
                settings,
                fetch_reason=hit.fetch_reason,
                search_query=hit.search_query,
            )
            page_rows.append(_page_hit_to_debug_row(hit, bool(chunks)))
            all_chunks.extend(chunks)
        except Exception:
            page_rows.append(_page_hit_to_debug_row(hit, False))
    return all_chunks, page_rows


def _records_to_retrieved(records: list[ChunkRecord], default_score: float = 0.5) -> list[RetrievedChunk]:
    return [
        RetrievedChunk(
            chunk_id=r.chunk_id,
            text=r.text,
            metadata=dict(r.metadata),
            score=default_score,
        )
        for r in records
    ]


def retrieve_live_for_query(
    query: str,
    user_question: str | None = None,
    extra_search_queries: list[str] | None = None,
) -> tuple[list[RetrievedChunk], RetrievalDebugInfo]:
    settings = get_settings()
    user_q = (user_question or query).strip()
    search_queries = build_search_queries(user_q, subtask_query=query, extra_queries=extra_search_queries)
    probes = (
        title_probe_candidates(user_q) if settings.live_wiki_title_probe else []
    )

    debug = RetrievalDebugInfo(
        subtask_query=query,
        user_question=user_q,
        fused_search_queries=search_queries,
        title_probe_candidates=probes,
    )

    pages = _merge_search_hits(search_queries, settings)
    pages = _prepend_title_probes(pages, user_q, settings)
    if not pages:
        return [], debug

    records, debug.pages_fetched = _collect_pages_from_hits(pages, settings)
    if not records:
        return [], debug

    candidates = _records_to_retrieved(records)
    try:
        ranked = rerank(user_q, candidates)
    except Exception:
        ranked = candidates[: settings.rerank_top_n]

    ranked = _apply_title_overlap_penalty(ranked, user_q, settings)
    result = ranked[: settings.rerank_top_n]
    debug.chunks_returned = len(result)
    return result, debug
