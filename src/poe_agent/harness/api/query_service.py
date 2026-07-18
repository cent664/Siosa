# ROLE: harness — dispatches /query to orchestrator or linear RAG pipeline.

from __future__ import annotations

import time

from poe_agent.evaluator.inline import run_inline_quality, should_run_inline_eval
from poe_agent.harness.api.schemas import (
    Citation,
    LLMCallTrace,
    QualityScores,
    QueryResponse,
    QueryTrace,
)
from poe_agent.evaluator.context import EVIDENCE_CHARS_PER_CHUNK
from poe_agent.harness.config import get_effective_provider_mode, get_settings
from poe_agent.harness.logging import RunLog, agent_run
from poe_agent.harness.trace import get_llm_calls, reset_llm_calls
from poe_agent.orchestrator.graph import run_agent_graph
from poe_agent.retriever.models import RetrievedChunk
from poe_agent.executor.node import merge_retrieved_chunks
from poe_agent.planner.refine import refine_search_queries
from poe_agent.retriever.gate import retrieval_needs_refine
from poe_agent.retriever.pipeline import retrieve_for_query


def _chunks_exist() -> bool:
    return (get_settings().chunks_dir / "chunks.jsonl").exists()


def _retrieval_available() -> bool:
    settings = get_settings()
    if settings.retrieval_mode.lower() in ("live", "hybrid"):
        return True
    return _chunks_exist()


def _use_langgraph() -> bool:
    return _retrieval_available()


def _retrieval_config_snapshot() -> dict:
    s = get_settings()
    return {
        "max_pages": s.live_wiki_max_pages,
        "max_search_queries": s.live_wiki_max_search_queries,
        "search_limit": s.live_wiki_search_limit,
        "title_probe": s.live_wiki_title_probe,
        "max_title_probes": s.live_wiki_max_title_probes,
        "title_overlap_filter": s.live_wiki_title_overlap_filter,
        "rerank_top_n": s.rerank_top_n,
        "search_concurrency": s.live_wiki_search_concurrency,
        "fetch_concurrency": s.live_wiki_fetch_concurrency,
        "structure_aware": s.live_wiki_structure_aware,
        "chunk_diversity": s.live_wiki_chunk_diversity,
        "max_chunks_per_page": s.live_wiki_max_chunks_per_page,
        "link_expand": s.live_wiki_link_expand,
        "link_expand_max": s.live_wiki_link_expand_max,
        "link_expand_enumerate_max": s.live_wiki_link_expand_enumerate_max,
        "link_harvest_max": s.live_wiki_link_harvest_max,
        "prefer_table_links": s.live_wiki_prefer_table_links,
        "prefer_prior_pages": s.live_wiki_prefer_prior_pages,
        "followup_rewrite": s.live_wiki_followup_rewrite,
    }


def _chunk_dicts(chunks: list[RetrievedChunk], *, include_text: bool = False) -> list[dict]:
    rows: list[dict] = []
    for c in chunks:
        row: dict = {
            "chunk_id": c.chunk_id,
            "page_title": c.metadata.get("page_title"),
            "wiki_url": c.metadata.get("wiki_url"),
            "score": c.score,
            "retrieval": c.metadata.get("retrieval"),
            "fetch_reason": c.metadata.get("fetch_reason"),
            "search_query": c.metadata.get("search_query"),
            "text_preview": c.text[:200],
        }
        if include_text:
            row["text"] = c.text[:EVIDENCE_CHARS_PER_CHUNK]
        rows.append(row)
    return rows


def _build_trace(
    pipeline: str,
    run: RunLog,
    timing_ms: dict[str, float],
    plan: list | None = None,
    retrieval_source: str = "",
) -> QueryTrace:
    llm_raw = get_llm_calls()
    settings = get_settings()
    return QueryTrace(
        pipeline=pipeline,
        retrieval_source=retrieval_source or run.extra.get("retrieval_source", ""),
        retrieval_mode=run.extra.get("retrieval_mode", settings.retrieval_mode.lower()),
        retrieval_config=run.extra.get("retrieval_config", _retrieval_config_snapshot()),
        retrieval_refined=bool(run.extra.get("retrieval_refined", False)),
        refine_queries=list(run.extra.get("refine_queries", [])),
        retrieval_gate_reason=str(run.extra.get("retrieval_gate_reason", "")),
        plan=plan or run.extra.get("plan", []),
        tool_calls=run.tool_calls,
        retrieved_chunks=run.retrieved_chunks,
        timing_ms=timing_ms,
        llm_calls=[LLMCallTrace(**c) for c in llm_raw],
    )


def _finalize_response(
    question: str,
    answer: str,
    citations: list,
    run: RunLog,
    mode: str,
    pipeline: str,
    chunks: list[RetrievedChunk],
    timing_ms: dict[str, float],
    plan: list | None = None,
    retrieval_source: str = "",
    session_id: str = "",
) -> QueryResponse:
    run.retrieved_chunks = _chunk_dicts(chunks, include_text=True)
    quality = QualityScores()
    if should_run_inline_eval() and answer:
        t0 = time.perf_counter()
        try:
            quality, _ = run_inline_quality(question, answer, chunks)
        except Exception as exc:
            quality = QualityScores(
                notes={
                    "skipped": "inline evaluation failed",
                    "error": str(exc)[:500],
                },
            )
        timing_ms["evaluation"] = round((time.perf_counter() - t0) * 1000, 2)

    trace = _build_trace(pipeline, run, timing_ms, plan=plan, retrieval_source=retrieval_source)
    run.extra["trace"] = trace.model_dump()
    run.extra["quality_scores"] = quality.model_dump()

    return QueryResponse(
        answer=answer,
        citations=[Citation(**c) if isinstance(c, dict) else c for c in citations],
        run_id=run.run_id,
        mode=mode,
        retrieved_count=len(chunks),
        session_id=session_id,
        trace=trace,
        quality_scores=quality,
    )


def handle_query(question: str, session_id: str | None = None) -> QueryResponse:
    reset_llm_calls()
    mode = get_effective_provider_mode()
    timing: dict[str, float] = {}
    settings = get_settings()

    from poe_agent.harness.config import provider_missing_key_message
    from poe_agent.harness.session_memory import (
        append_turn,
        ensure_session,
        load_prompt_history,
    )

    missing = provider_missing_key_message(mode)
    if missing:
        raise ValueError(missing)

    active_session = ""
    history: list[dict[str, str]] = []
    summary = ""
    if settings.session_memory_enabled:
        active_session = ensure_session(session_id, settings=settings)
        summary, history = load_prompt_history(active_session, settings=settings)

    with agent_run(question) as run:
        if not _retrieval_available():
            run.output_answer = (
                "Retrieval not available. Set RETRIEVAL_MODE=live or run `poe-ingest` for local index."
            )
            return QueryResponse(
                answer=run.output_answer,
                citations=[],
                run_id=run.run_id,
                mode=mode,
                session_id=active_session,
                trace=QueryTrace(pipeline="none", timing_ms=timing),
            )

        if _use_langgraph():
            result = run_agent_graph(
                question, run, history=history, summary=summary
            )
            graph_timing = dict(result.get("timing_ms", {}))
            timing.update(graph_timing)
            chunks = run.extra.get("raw_chunks", [])
            resp = _finalize_response(
                question,
                result["answer"],
                result["citations"],
                run,
                "langgraph",
                "langgraph",
                chunks,
                timing,
                plan=run.extra.get("plan"),
                retrieval_source=run.extra.get("retrieval_source", ""),
                session_id=active_session,
            )
        else:
            resp = _linear_rag(
                question,
                run,
                timing,
                history=history,
                summary=summary,
                session_id=active_session,
            )

        if settings.session_memory_enabled and active_session and resp.answer:
            cites = [
                {"title": c.title if hasattr(c, "title") else c.get("title", ""),
                 "url": c.url if hasattr(c, "url") else c.get("url", "")}
                for c in (resp.citations or [])
            ]
            append_turn(
                active_session,
                question,
                resp.answer,
                settings=settings,
                citations=cites,
            )
        return resp


def _maybe_refine_retrieval(
    question: str,
    chunks: list[RetrievedChunk],
    run: RunLog,
) -> list[RetrievedChunk]:
    settings = get_settings()
    needs, reason = retrieval_needs_refine(chunks, question)
    if not needs or not settings.retrieval_refine_enabled:
        return chunks

    t0 = time.perf_counter()
    refine_q = refine_search_queries(question, chunks)
    extra, _src, debug = retrieve_for_query(
        question,
        user_question=question,
        extra_search_queries=refine_q,
    )
    merged = merge_retrieved_chunks(chunks, extra)
    run.extra["retrieval_refined"] = True
    run.extra["refine_queries"] = refine_q
    run.extra["retrieval_gate_reason"] = reason
    refine_entry: dict = {
        "tool": "wiki_search",
        "query": "refine",
        "refine_queries": refine_q,
        "result_count": len(extra),
    }
    if debug is not None:
        refine_entry["retrieval_debug"] = debug.to_dict()
    run.tool_calls.append(refine_entry)
    run.extra["refine_timing_ms"] = round((time.perf_counter() - t0) * 1000, 2)
    return merged


def _linear_rag(
    question: str,
    run: RunLog,
    timing: dict[str, float],
    history: list[dict[str, str]] | None = None,
    summary: str = "",
    session_id: str = "",
) -> QueryResponse:
    from poe_agent.generator.answer import generate_answer_with_meta
    from poe_agent.harness.session_memory import continuity_retrieval_context

    run.extra["retrieval_mode"] = get_settings().retrieval_mode.lower()
    run.extra["retrieval_config"] = _retrieval_config_snapshot()

    page_titles, hints = continuity_retrieval_context(question, history or [])
    t0 = time.perf_counter()
    chunks, retrieval_source, debug = retrieve_for_query(
        question,
        user_question=question,
        extra_search_queries=hints or None,
        extra_title_probes=page_titles or None,
    )
    timing["retrieval"] = round((time.perf_counter() - t0) * 1000, 2)

    t_ref = time.perf_counter()
    chunks = _maybe_refine_retrieval(question, chunks, run)
    if run.extra.get("retrieval_refined"):
        timing["retrieval_refine"] = round((time.perf_counter() - t_ref) * 1000, 2)

    if not run.extra.get("retrieval_refined"):
        entry: dict = {
            "tool": "wiki_search",
            "query": question,
            "result_count": len(chunks),
            "retrieval_source": retrieval_source,
        }
        if hints:
            entry["history_hints"] = hints
        if debug is not None:
            entry["retrieval_debug"] = debug.to_dict()
        run.tool_calls.append(entry)
    run.extra["raw_chunks"] = chunks
    run.extra["retrieval_source"] = retrieval_source

    t1 = time.perf_counter()
    answer, citations, tokens = generate_answer_with_meta(
        question, chunks, history=history or [], summary=summary
    )
    timing["generation"] = round((time.perf_counter() - t1) * 1000, 2)

    run.output_answer = answer
    run.citations = citations
    run.token_counts = tokens
    pipeline = "linear_rag"
    return _finalize_response(
        question,
        answer,
        citations,
        run,
        get_effective_provider_mode(),
        pipeline,
        chunks,
        timing,
        retrieval_source=retrieval_source,
        session_id=session_id,
    )
