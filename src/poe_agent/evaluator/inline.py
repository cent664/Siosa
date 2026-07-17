# ROLE: evaluator — inline quality scores on every /query response.

from __future__ import annotations

from poe_agent.evaluator.context import format_evidence_context, truncate_for_judge
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


def chunks_from_score_payload(chunks: list[dict]) -> list[RetrievedChunk]:
    """Rebuild RetrievedChunk list from /score request body."""
    out: list[RetrievedChunk] = []
    for i, row in enumerate(chunks):
        text = str(row.get("text", ""))
        if not text.strip():
            continue
        out.append(
            RetrievedChunk(
                chunk_id=str(row.get("chunk_id", f"score-{i}")),
                text=text,
                metadata={
                    "page_title": row.get("page_title", "Wiki"),
                    "wiki_url": row.get("wiki_url", ""),
                },
                score=float(row["score"]) if row.get("score") is not None else 0.0,
            )
        )
    return out


def run_inline_quality(
    question: str,
    answer: str,
    chunks: list[RetrievedChunk],
) -> tuple[QualityScores, dict[str, float]]:
    """Run five judges; return scores and per-judge latency_ms."""
    evidence = truncate_for_judge(format_evidence_context(chunks))
    judge_latencies: dict[str, float] = {}

    ctx_prec = judge_context_precision(question, evidence)
    judge_latencies["context_precision"] = ctx_prec.get("latency_ms", 0.0)

    ctx_rec = judge_context_recall(question, evidence)
    judge_latencies["context_recall"] = ctx_rec.get("latency_ms", 0.0)

    faith = judge_faithfulness(answer, evidence)
    judge_latencies["faithfulness"] = faith.get("latency_ms", 0.0)

    rel = judge_relevance(question, answer)
    judge_latencies["relevance"] = rel.get("latency_ms", 0.0)

    adh = judge_prompt_adherence(answer, get_answer_system_prompt(), evidence)
    judge_latencies["prompt_adherence"] = adh.get("latency_ms", 0.0)

    return (
        QualityScores(
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
        ),
        judge_latencies,
    )


def should_run_inline_eval() -> bool:
    return get_settings().inline_eval
