# ROLE: generator — build grounded answers from retrieved wiki chunks.

from __future__ import annotations

from poe_agent.harness.config import get_effective_provider_mode, get_settings
from poe_agent.harness.providers import get_llm_provider, get_provider_model_id
from poe_agent.harness.trace import traced_generate
from poe_agent.evaluator.context import format_evidence_context
from poe_agent.retriever.models import RetrievedChunk

SYSTEM_PROMPT = """You are a Path of Exile 1 mechanics assistant.
Answer ONLY using the provided wiki excerpts. If the context is insufficient, say so.
Do not mention Path of Exile 2 unless the context explicitly covers it.
Include specific mechanic details when present in the context.
Keep answers concise (2-5 sentences) for beginners."""


def get_answer_system_prompt() -> str:
    return SYSTEM_PROMPT


def _chunks_to_citations(chunks: list[RetrievedChunk]) -> list[dict]:
    seen: set[str] = set()
    citations: list[dict] = []
    for ch in chunks:
        title = str(ch.metadata.get("page_title", "Wiki"))
        url = str(ch.metadata.get("wiki_url", ""))
        key = url or title
        if key in seen:
            continue
        seen.add(key)
        citations.append(
            {
                "title": title,
                "url": url,
                "snippet": ch.text[:280],
            }
        )
    return citations


def generate_answer_with_meta(
    question: str,
    chunks: list[RetrievedChunk],
    history: list[dict[str, str]] | None = None,
    summary: str = "",
) -> tuple[str, list[dict], dict[str, int]]:
    if not chunks:
        mode = get_settings().retrieval_mode.lower()
        if mode in ("live", "hybrid"):
            msg = "No poewiki pages matched this question. Try rephrasing or a more specific mechanic term."
        else:
            msg = "No wiki content indexed yet. Run `poe-ingest` or set RETRIEVAL_MODE=live."
        return (msg, [], {"prompt_tokens": 0, "completion_tokens": 0})

    mode = get_effective_provider_mode()
    context = format_evidence_context(chunks)
    history_block = ""
    if summary or history:
        from poe_agent.harness.session_memory import format_generation_context

        history_block = format_generation_context(summary or "", history or [])
    if history_block:
        user_prompt = f"""Prior conversation (for follow-up context; still answer from wiki excerpts):
{history_block}

Current question: {question}

Wiki excerpts:
{context}

Answer the current question using only the excerpts above. Use prior conversation only to resolve references (e.g. \"it\", \"that skill\")."""
    else:
        user_prompt = f"""Question: {question}

Wiki excerpts:
{context}

Answer the question using only the excerpts above."""

    llm = get_llm_provider()
    result = traced_generate(
        "answer",
        llm,
        SYSTEM_PROMPT,
        user_prompt,
        provider_name=mode,
        model_id=get_provider_model_id(mode),
    )
    return result.text, _chunks_to_citations(chunks), result.token_counts


def generate_answer(
    question: str,
    chunks: list[RetrievedChunk],
    history: list[dict[str, str]] | None = None,
    summary: str = "",
) -> tuple[str, list[dict]]:
    answer, citations, _ = generate_answer_with_meta(
        question, chunks, history=history, summary=summary
    )
    return answer, citations
