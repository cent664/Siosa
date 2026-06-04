# ROLE: orchestrator — shared graph state definition.

from __future__ import annotations

from typing import Annotated, TypedDict

from langgraph.graph.message import add_messages


class AgentState(TypedDict, total=False):
    query: str
    plan: list[dict]
    messages: Annotated[list, add_messages]
    retrieved_chunks: list
    answer: str
    citations: list[dict]
    tool_calls: list[dict]
    token_counts: dict
    refine_round: int
    refine_queries: list[str]
    retrieval_refined: bool
    retrieval_gate_reason: str
    timing_ms: dict[str, float]
