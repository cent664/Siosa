# ROLE: orchestrator — LangGraph StateGraph wiring planner → executor → generator.

from __future__ import annotations

from typing import Any

from langgraph.graph import END, StateGraph

from poe_agent.executor.node import execute_refine_retrieval, execute_subtasks, merge_retrieved_chunks
from poe_agent.executor.tools import synthesize_answer
from poe_agent.harness.config import get_settings
from poe_agent.harness.logging import RunLog
from poe_agent.orchestrator.state import AgentState
from poe_agent.planner.node import plan_subtasks
from poe_agent.planner.refine import refine_search_queries
from poe_agent.retriever.gate import retrieval_needs_refine


def _plan_node(state: AgentState) -> AgentState:
    subtasks = plan_subtasks(state["query"])
    return {"plan": subtasks, "refine_round": state.get("refine_round", 0)}


def _execute_node(state: AgentState) -> AgentState:
    chunks, tool_log = execute_subtasks(state["query"], state.get("plan", []))
    return {
        "retrieved_chunks": chunks,
        "tool_calls": tool_log,
    }


def _gate_node(state: AgentState) -> AgentState:
    chunks = state.get("retrieved_chunks", [])
    needs, reason = retrieval_needs_refine(chunks, state["query"])
    return {"retrieval_gate_reason": reason if needs else ""}


def _route_after_gate(state: AgentState) -> str:
    settings = get_settings()
    if not settings.retrieval_refine_enabled:
        return "generate"
    if state.get("refine_round", 0) >= settings.retrieval_max_refine_rounds:
        return "generate"
    chunks = state.get("retrieved_chunks", [])
    needs, _ = retrieval_needs_refine(chunks, state["query"])
    return "refine" if needs else "generate"


def _refine_node(state: AgentState) -> AgentState:
    queries = refine_search_queries(state["query"], state.get("retrieved_chunks", []))
    return {
        "refine_queries": queries,
        "refine_round": state.get("refine_round", 0) + 1,
    }


def _refine_execute_node(state: AgentState) -> AgentState:
    new_chunks, tool_log = execute_refine_retrieval(
        state["query"],
        state.get("refine_queries", []),
    )
    merged = merge_retrieved_chunks(state.get("retrieved_chunks", []), new_chunks)
    prior_log = list(state.get("tool_calls", []))
    prior_log.extend(tool_log)
    return {
        "retrieved_chunks": merged,
        "tool_calls": prior_log,
        "retrieval_refined": True,
    }


def _generate_node(state: AgentState) -> AgentState:
    chunks = state.get("retrieved_chunks", [])
    answer, citations, tokens = synthesize_answer(state["query"], chunks)
    return {
        "answer": answer,
        "citations": citations,
        "token_counts": tokens,
    }


def build_graph():
    graph = StateGraph(AgentState)
    graph.add_node("plan", _plan_node)
    graph.add_node("execute", _execute_node)
    graph.add_node("gate", _gate_node)
    graph.add_node("refine", _refine_node)
    graph.add_node("refine_execute", _refine_execute_node)
    graph.add_node("generate", _generate_node)

    graph.set_entry_point("plan")
    graph.add_edge("plan", "execute")
    graph.add_edge("execute", "gate")
    graph.add_conditional_edges("gate", _route_after_gate, {"refine": "refine", "generate": "generate"})
    graph.add_edge("refine", "refine_execute")
    graph.add_edge("refine_execute", "generate")
    graph.add_edge("generate", END)
    return graph.compile()


_compiled_graph = None


def get_graph():
    global _compiled_graph
    if _compiled_graph is None:
        _compiled_graph = build_graph()
    return _compiled_graph


def run_agent_graph(question: str, run: RunLog | None = None) -> dict[str, Any]:
    graph = get_graph()
    result = graph.invoke({"query": question, "refine_round": 0})
    if run is not None:
        run.tool_calls = result.get("tool_calls", [])
        chunks = result.get("retrieved_chunks", [])
        run.retrieved_chunks = [
            {
                "page_title": c.metadata.get("page_title"),
                "wiki_url": c.metadata.get("wiki_url"),
                "score": getattr(c, "score", None),
                "text_preview": c.text[:200] if hasattr(c, "text") else "",
            }
            for c in chunks
        ]
        run.extra["plan"] = result.get("plan", [])
        run.extra["raw_chunks"] = chunks
        settings = get_settings()
        run.extra["retrieval_source"] = settings.retrieval_mode.lower()
        run.extra["retrieval_mode"] = settings.retrieval_mode.lower()
        run.extra["retrieval_config"] = {
            "max_pages": settings.live_wiki_max_pages,
            "max_search_queries": settings.live_wiki_max_search_queries,
            "search_limit": settings.live_wiki_search_limit,
            "title_probe": settings.live_wiki_title_probe,
            "title_overlap_filter": settings.live_wiki_title_overlap_filter,
            "rerank_top_n": settings.rerank_top_n,
        }
        run.extra["retrieval_refined"] = result.get("retrieval_refined", False)
        run.extra["refine_queries"] = result.get("refine_queries", [])
        run.extra["retrieval_gate_reason"] = result.get("retrieval_gate_reason", "")
        run.output_answer = result.get("answer", "")
        run.citations = result.get("citations", [])
        run.token_counts = result.get("token_counts", {})
    return {
        "answer": result.get("answer", ""),
        "citations": result.get("citations", []),
    }
