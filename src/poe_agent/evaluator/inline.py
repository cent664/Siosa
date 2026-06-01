# ROLE: evaluator — inline quality scores on every /query response.

from __future__ import annotations

from poe_agent.evaluator.judges import (
    judge_context_precision,
    judge_context_recall,
    judge_faithfulness,
    judge_prompt_adherence,
    judge_relevance,
)
from poe_agent.generator.answer import get_answer_system_prompt
from poe_agent.harness.api.schemas import QualityScores
from poe_agent.harness.config import get_settings
from poe_agent.retriever.models import RetrievedChunk


def score_to_normalized(score: float | None) -> float | None:
    if score is None:
        return None
    return round(max(0.0, min(5.0, score)) / 5.0, 3)


def format_retrieval_preview(chunks: list[RetrievedChunk]) -> str:
    if not chunks:
        return "(no chunks retrieved)"
    parts: list[str] = []
    for i, c in enumerate(chunks, 1):
        title = c.metadata.get("page_title", "unknown")
        parts.append(f"[{i}] {title}\n{c.text[:400]}")
    return "\n\n".join(parts)


def run_inline_quality(
    question: str,
    answer: str,
    context: str,
    *,
    chunks: list[RetrievedChunk] | None = None,
) -> QualityScores:
    if get_effective_provider_mode_stub_skip(answer):
        return QualityScores(
            notes={"skipped": "stub mode — no LLM answer to judge"},
        )

    retrieval_preview = format_retrieval_preview(chunks) if chunks else context

    ctx_prec = judge_context_precision(question, retrieval_preview)
    ctx_rec = judge_context_recall(question, retrieval_preview)
    faith = judge_faithfulness(answer, context)
    rel = judge_relevance(question, answer)
    adh = judge_prompt_adherence(answer, get_answer_system_prompt())

    return QualityScores(
        context_precision=score_to_normalized(ctx_prec.get("score")),
        context_recall=score_to_normalized(ctx_rec.get("score")),
        faithfulness=faith.get("score"),
        relevance=rel.get("score"),
        prompt_adherence=adh.get("score"),
        notes={
            "context_precision": ctx_prec.get("reason", ""),
            "context_recall": ctx_rec.get("reason", ""),
            "faithfulness": faith.get("reason", ""),
            "relevance": rel.get("reason", ""),
            "prompt_adherence": adh.get("reason", ""),
        },
    )


def get_effective_provider_mode_stub_skip(answer: str) -> bool:
    from poe_agent.harness.config import get_effective_provider_mode

    if get_effective_provider_mode() == "stub":
        return True
    if answer.startswith("(Stub mode"):
        return True
    return False


def should_run_inline_eval() -> bool:
    return get_settings().inline_eval
