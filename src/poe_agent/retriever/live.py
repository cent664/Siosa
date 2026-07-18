# ROLE: retriever — live poewiki search, fetch, and in-memory retrieval.

from __future__ import annotations

import json
import re
import time
from dataclasses import dataclass
from pathlib import Path

from poe_agent.harness.config import Settings, get_settings
from poe_agent.retriever.followup import rewrite_followup_question
from poe_agent.retriever.ingest import chunk_text
from poe_agent.retriever.models import ChunkRecord, RetrievedChunk
from poe_agent.retriever.query_fusion import (
    build_search_queries,
    retrieval_focus_terms,
    title_probe_candidates,
)
from poe_agent.retriever.rerank import rerank
from poe_agent.retriever.retrieval_debug import RetrievalDebugInfo
from poe_agent.retriever.wiki_client import (
    WIKI_BASE,
    fetch_page_payload,
    parallel_map,
    search_wiki_titles,
)


@dataclass
class _PageHit:
    title: str
    path: str
    fetch_reason: str
    search_query: str = ""


def _cache_path(settings: Settings, path: str) -> Path:
    # Windows-safe: avoid path separators in filenames
    safe = path.replace("/", "_").replace("\\", "_")
    return settings.live_cache_dir / f"{safe}.json"


LINKS_CACHE_VERSION = 3  # redirects=1 + reject redirect stubs


def _read_cache(
    settings: Settings, path: str, ttl_hours: float
) -> tuple[str, str, list[str]] | None:
    cache_file = _cache_path(settings, path)
    if not cache_file.is_file():
        return None
    try:
        row = json.loads(cache_file.read_text(encoding="utf-8"))
        fetched_at = float(row.get("fetched_at", 0))
        if (time.time() - fetched_at) > ttl_hours * 3600:
            return None
        # Force re-fetch when link-harvest / redirect handling changes.
        if int(row.get("links_version", 0)) < LINKS_CACHE_VERSION:
            return None
        text = row.get("text", "")
        url = row.get("wiki_url", "")
        links = [str(x) for x in (row.get("links") or []) if str(x).strip()]
        # Stale redirect stubs / tiny test caches are not real wiki pages.
        if not text or len(text) < 400 or text.lstrip().lower().startswith("redirect to"):
            return None
        if text and url:
            return text, url, links
    except (json.JSONDecodeError, OSError, ValueError):
        return None
    return None


def _write_cache(
    settings: Settings,
    path: str,
    title: str,
    text: str,
    url: str,
    links: list[str] | None = None,
) -> None:
    settings.live_cache_dir.mkdir(parents=True, exist_ok=True)
    cache_file = _cache_path(settings, path)
    cache_file.write_text(
        json.dumps(
            {
                "title": title,
                "path": path,
                "text": text,
                "wiki_url": url,
                "links": links or [],
                "links_version": LINKS_CACHE_VERSION,
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
) -> tuple[list[ChunkRecord], list[str]]:
    """Fetch/chunk a page; also return outgoing wiki titles when available."""
    s = settings or get_settings()
    links: list[str] = []
    cached = _read_cache(s, path, s.live_wiki_cache_ttl_hours)
    if cached:
        text, url, links = cached
    else:
        text, url, links = fetch_page_payload(
            title,
            path,
            use_extracts=s.live_wiki_use_extracts,
            structure_aware=s.live_wiki_structure_aware,
            link_harvest_max=s.live_wiki_link_harvest_max,
            prefer_table_links=s.live_wiki_prefer_table_links,
        )
        _write_cache(s, path, title, text, url, links)

    if not text.strip():
        return [], links

    chunks = chunk_text(text, title, url)
    for ch in chunks:
        ch.metadata["source"] = "live"
        ch.metadata["retrieval"] = "live"
        ch.metadata["fetch_reason"] = fetch_reason
        if search_query:
            ch.metadata["search_query"] = search_query
    return chunks, links


def _merge_search_hits(
    search_queries: list[str],
    settings: Settings,
) -> tuple[list[_PageHit], list[str]]:
    by_path: dict[str, _PageHit] = {}
    order: list[str] = []
    errors: list[str] = []

    def _one(sq: str) -> tuple[str, list[tuple[str, str]], str | None]:
        try:
            return sq, search_wiki_titles(sq, limit=settings.live_wiki_search_limit), None
        except Exception as exc:
            return sq, [], f"{sq}: {exc}"

    results = parallel_map(
        _one,
        search_queries,
        max_workers=settings.live_wiki_search_concurrency,
    )
    for sq, hits, err in results:
        if err:
            errors.append(err)
        for title, path in hits:
            if path not in by_path:
                by_path[path] = _PageHit(title, path, "search", sq)
                order.append(path)

    return [by_path[p] for p in order], errors


def _title_relevance_score(page_title: str, focus_terms: list[str]) -> float:
    """Fraction of focus-term tokens present in the page title (0–1)."""
    if not focus_terms:
        return 0.0
    title_tokens = set(re.findall(r"[a-z0-9]+", page_title.lower()))
    if not title_tokens:
        return 0.0
    best = 0.0
    for term in focus_terms:
        term_tokens = set(re.findall(r"[a-z0-9]+", term.lower()))
        if not term_tokens:
            continue
        overlap = len(term_tokens & title_tokens) / len(term_tokens)
        best = max(best, overlap)
    return best


def _link_relevance_score(link_title: str, question: str) -> float:
    focus = retrieval_focus_terms(question)
    if focus:
        return _title_relevance_score(link_title, focus)
    # Follow-ups like “list all of them” often have weak focus — prefer short entity titles.
    tokens = re.findall(r"[a-z0-9]+", link_title.lower())
    if not tokens:
        return 0.0
    # Mild preference for concise proper-looking titles
    return 0.35 if len(tokens) <= 4 else 0.1


def _rank_search_hits_by_title(
    pages: list[_PageHit],
    user_question: str,
) -> list[_PageHit]:
    focus = retrieval_focus_terms(user_question)
    if not focus:
        return pages
    probes = [p for p in pages if p.fetch_reason in ("title_probe", "prior", "link_expand")]
    search_hits = [p for p in pages if p.fetch_reason == "search"]
    other = [p for p in pages if p not in probes and p not in search_hits]
    ranked = sorted(
        search_hits,
        key=lambda h: (_title_relevance_score(h.title, focus), h.title.lower()),
        reverse=True,
    )
    # Search hits first so the page budget is not eaten by speculative probes.
    return ranked + probes + other


def _prepend_title_probes(
    pages: list[_PageHit],
    user_question: str,
    settings: Settings,
    extra_titles: list[str] | None = None,
    *,
    reason: str = "title_probe",
) -> list[_PageHit]:
    if not settings.live_wiki_title_probe and not extra_titles:
        return pages

    existing = {p.path for p in pages}
    probed: list[_PageHit] = []
    candidates: list[str] = []
    if settings.live_wiki_title_probe:
        candidates.extend(title_probe_candidates(user_question))
    for title in extra_titles or []:
        t = title.strip()
        if t and t.casefold() not in {c.casefold() for c in candidates}:
            candidates.insert(0, t)
    for candidate in candidates:
        path = candidate.replace(" ", "_")
        if path in existing:
            continue
        fetch_reason = reason if reason != "title_probe" else (
            "prior" if extra_titles and any(candidate.casefold() == t.strip().casefold() for t in (extra_titles or [])) else "title_probe"
        )
        # Mark prior citation titles explicitly
        if extra_titles and any(candidate.casefold() == t.strip().casefold() for t in extra_titles):
            fetch_reason = "prior"
        probed.append(_PageHit(candidate, path, fetch_reason, ""))
        existing.add(path)

    return probed + pages


def _title_overlap_score(page_title: str, focus_terms: list[str]) -> float:
    if not focus_terms:
        return 1.0
    return 1.0 if _title_relevance_score(page_title, focus_terms) >= 0.5 else 0.0


def _apply_title_overlap_penalty(
    chunks: list[RetrievedChunk],
    user_question: str,
    settings: Settings,
) -> list[RetrievedChunk]:
    if not settings.live_wiki_title_overlap_filter:
        return chunks
    terms = retrieval_focus_terms(user_question)
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


def diversify_chunks_by_page(
    chunks: list[RetrievedChunk],
    *,
    top_n: int,
    max_per_page: int,
) -> list[RetrievedChunk]:
    """
    Keep score order but cap how many passages come from one wiki page.
    Rule of thumb: 1–2 chunks/page avoids near-duplicate previews wasting the top-N budget.
    """
    if top_n <= 0 or not chunks:
        return []
    if max_per_page <= 0:
        return chunks[:top_n]

    selected: list[RetrievedChunk] = []
    per_page: dict[str, int] = {}
    deferred: list[RetrievedChunk] = []

    for ch in chunks:
        key = str(ch.metadata.get("wiki_url") or ch.metadata.get("page_title") or ch.chunk_id)
        count = per_page.get(key, 0)
        if count < max_per_page:
            selected.append(ch)
            per_page[key] = count + 1
            if len(selected) >= top_n:
                return selected
        else:
            deferred.append(ch)

    for ch in deferred:
        if len(selected) >= top_n:
            break
        selected.append(ch)
    return selected


def _page_hit_to_debug_row(
    hit: _PageHit,
    fetch_ok: bool,
    *,
    fetch_error: str = "",
) -> dict:
    row = {
        "title": hit.title,
        "path": hit.path,
        "wiki_url": f"{WIKI_BASE}/{hit.path}",
        "fetch_reason": hit.fetch_reason,
        "search_query": hit.search_query,
        "fetch_ok": fetch_ok,
    }
    if fetch_error:
        row["fetch_error"] = fetch_error[:300]
    return row


def _collect_pages_from_hits(
    pages: list[_PageHit],
    settings: Settings,
    *,
    max_pages: int | None = None,
) -> tuple[list[ChunkRecord], list[dict], dict[str, list[str]]]:
    limit = settings.live_wiki_max_pages if max_pages is None else max_pages
    selected = pages[:limit]
    link_map: dict[str, list[str]] = {}

    def _one(hit: _PageHit) -> tuple[_PageHit, list[ChunkRecord], list[str], bool, str]:
        try:
            chunks, links = fetch_page_chunks(
                hit.title,
                hit.path,
                settings,
                fetch_reason=hit.fetch_reason,
                search_query=hit.search_query,
            )
            if not chunks:
                return hit, [], links, False, "empty page text"
            return hit, chunks, links, True, ""
        except Exception as exc:
            return hit, [], [], False, str(exc)

    results = parallel_map(
        _one,
        selected,
        max_workers=settings.live_wiki_fetch_concurrency,
    )
    all_chunks: list[ChunkRecord] = []
    page_rows: list[dict] = []
    for hit, chunks, links, ok, err in results:
        page_rows.append(_page_hit_to_debug_row(hit, ok, fetch_error=err))
        all_chunks.extend(chunks)
        if links:
            link_map[hit.path] = links
    return all_chunks, page_rows, link_map


def _select_link_expand_hits(
    link_map: dict[str, list[str]],
    user_question: str,
    existing_paths: set[str],
    settings: Settings,
    *,
    seed_paths: set[str] | None = None,
) -> list[_PageHit]:
    if not settings.live_wiki_link_expand:
        return []
    from poe_agent.retriever.followup import looks_like_enumerate

    # Prefer links from prior / title-probe pages (index pages like Pantheon).
    seed_paths = seed_paths or set(link_map.keys())
    enumerate_mode = looks_like_enumerate(user_question)
    expand_max = (
        settings.live_wiki_link_expand_enumerate_max
        if enumerate_mode
        else settings.live_wiki_link_expand_max
    )

    scored: list[tuple[float, int, str, str]] = []
    seen: set[str] = set(existing_paths)
    for path, links in link_map.items():
        if path not in seed_paths:
            continue
        # links are already table-first when prefer_table_links harvested them
        for rank, title in enumerate(links):
            link_path = title.replace(" ", "_")
            if link_path in seen:
                continue
            rel = _link_relevance_score(title, user_question)
            tokens = re.findall(r"[a-z0-9]+", title.lower())
            # Enumerate: strongly prefer early (table) short entity titles.
            if enumerate_mode:
                table_bonus = 2.0 if rank < 40 else 0.0
                short_bonus = 0.5 if 1 <= len(tokens) <= 4 else 0.0
                score = rel + table_bonus + short_bonus
            else:
                # Mild preference for earlier (table-first) links
                score = rel + (0.15 if rank < 20 else 0.0)
            scored.append((score, rank, title, link_path))
            seen.add(link_path)

    scored.sort(key=lambda x: (x[0], -x[1]), reverse=True)
    picks = scored[:expand_max]
    return [_PageHit(title, path, "link_expand", "") for _, _, title, path in picks]


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
    extra_title_probes: list[str] | None = None,
) -> tuple[list[RetrievedChunk], RetrievalDebugInfo]:
    settings = get_settings()
    prior_titles = [t.strip() for t in (extra_title_probes or []) if t and t.strip()]
    raw_q = (user_question or query).strip()
    user_q = (
        rewrite_followup_question(raw_q, prior_titles)
        if settings.live_wiki_followup_rewrite
        else raw_q
    )

    prefer_prior = bool(settings.live_wiki_prefer_prior_pages and prior_titles)
    search_queries = build_search_queries(
        user_q,
        subtask_query=query if query.strip().casefold() != raw_q.casefold() else user_q,
        extra_queries=extra_search_queries,
    )
    # Only lean the search when we are continuing the same topic (priors already gated upstream).
    if prefer_prior and prior_titles and len(search_queries) > 2:
        search_queries = search_queries[:2]

    probes = list(title_probe_candidates(user_q)) if settings.live_wiki_title_probe else []
    for title in prior_titles:
        if title.casefold() not in {p.casefold() for p in probes}:
            probes.insert(0, title)

    debug = RetrievalDebugInfo(
        subtask_query=query,
        user_question=user_q,
        fused_search_queries=search_queries,
        title_probe_candidates=probes,
    )

    probe_pages = _prepend_title_probes(
        [],
        user_q,
        settings,
        extra_titles=prior_titles or None,
    )
    search_hits, search_errors = _merge_search_hits(search_queries, settings)
    debug.search_errors = search_errors

    # Prefer wiki search hits for the fetch budget; probes fill gaps.
    pages: list[_PageHit] = []
    existing: set[str] = set()
    for hit in search_hits:
        if hit.path not in existing:
            pages.append(hit)
            existing.add(hit.path)
    for hit in probe_pages:
        if hit.path not in existing:
            pages.append(hit)
            existing.add(hit.path)

    pages = _rank_search_hits_by_title(pages, user_q)
    if not pages:
        return [], debug

    seed_paths = {p.path for p in pages if p.fetch_reason in ("prior", "title_probe")}
    records, page_rows, link_map = _collect_pages_from_hits(pages, settings)
    debug.pages_fetched = page_rows

    expand_hits = _select_link_expand_hits(
        link_map,
        user_q,
        existing_paths={p.path for p in pages},
        settings=settings,
        seed_paths=seed_paths or set(link_map.keys()),
    )
    if expand_hits:
        more_records, more_rows, _ = _collect_pages_from_hits(
            expand_hits,
            settings,
            max_pages=len(expand_hits),
        )
        records.extend(more_records)
        debug.pages_fetched.extend(more_rows)

    if not records:
        return [], debug

    candidates = _records_to_retrieved(records)
    try:
        ranked = rerank(user_q, candidates)
    except Exception:
        ranked = candidates[: settings.rerank_top_n]

    ranked = _apply_title_overlap_penalty(ranked, user_q, settings)
    if settings.live_wiki_chunk_diversity:
        result = diversify_chunks_by_page(
            ranked,
            top_n=settings.rerank_top_n,
            max_per_page=settings.live_wiki_max_chunks_per_page,
        )
    else:
        result = ranked[: settings.rerank_top_n]
    debug.chunks_returned = len(result)
    return result, debug
