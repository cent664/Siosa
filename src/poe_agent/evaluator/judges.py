# ROLE: evaluator — LLM-as-judge for relevance, faithfulness, verbosity, adherence.

from __future__ import annotations

import re

from poe_agent.evaluator.context import JUDGE_CONTEXT_MAX_CHARS, truncate_for_judge
from poe_agent.harness.config import get_settings
from poe_agent.harness.providers import get_judge_llm_provider, get_provider_model_id
from poe_agent.harness.trace import traced_generate

RELEVANCE_PROMPT = """Rate 1-5 whether the answer addresses the question.
5 = materially answers the question; 4 = mostly addresses with minor gaps.
Do not penalize brevity if the core question is answered.
1 = does not address the question.
Reply with JSON only: {"score": N, "reason": "..."}"""

FAITHFULNESS_PROMPT = """Rate 1-5 whether every claim in the answer is supported by the wiki excerpts.
5 = fully supported, 1 = unsupported claims present.
Reply with JSON only: {"score": N, "reason": "..."}"""

VERBOSITY_PROMPT = """Rate 1-5 whether the answer length is appropriate for a beginner (ideal: 2-5 sentences).
5 = concise and complete, 1 = far too long or far too short.
Reply with JSON only: {"score": N, "reason": "..."}"""

ADHERENCE_PROMPT = """Rate 1-5 whether the answer follows the system rules given the wiki excerpts.
- Uses only provided wiki excerpts (no invented mechanics beyond excerpts)
- Path of Exile 1 focus
5 = fully adheres, 1 = clear violations (e.g. cites facts not in excerpts).
Reply with JSON only: {"score": N, "reason": "..."}"""

CONTEXT_PRECISION_PROMPT = """Rate 1-5 the precision of retrieved wiki excerpts for answering the question.
5 = almost all retrieved chunks are relevant; 1 = mostly irrelevant noise.
Reply with JSON only: {"score": N, "reason": "..."}"""

CONTEXT_RECALL_PROMPT = """Rate 1-5 the recall of retrieved wiki excerpts for answering the question.
5 = retrieval contains the key facts needed; 1 = critical information is missing.
Reply with JSON only: {"score": N, "reason": "..."}"""


def _parse_score(raw: str, default: float = 3.0) -> tuple[float, str]:
    import json

    reason = ""
    try:
        match = re.search(r"\{.*\}", raw, re.DOTALL)
        if match:
            data = json.loads(match.group())
            reason = str(data.get("reason", ""))
            return float(data.get("score", default)), reason
    except (json.JSONDecodeError, ValueError, TypeError):
        pass
    return default, reason


def _judge(purpose: str, system: str, user: str) -> dict:
    settings = get_settings()
    judge_mode = settings.judge_provider.lower()
    llm = get_judge_llm_provider()
    result = traced_generate(
        purpose,
        llm,
        system,
        user,
        provider_name=judge_mode,
        model_id=get_provider_model_id(judge_mode),
    )
    score, reason = _parse_score(result.text)
    return {
        "score": score,
        "reason": reason,
        "raw": result.text,
        "tokens": result.token_counts,
        "latency_ms": result.latency_ms,
    }


def judge_relevance(question: str, answer: str) -> dict:
    return _judge(
        "judge_relevance",
        RELEVANCE_PROMPT,
        f"Question: {question}\nAnswer: {answer}",
    )


def judge_faithfulness(answer: str, context: str) -> dict:
    ctx = truncate_for_judge(context, JUDGE_CONTEXT_MAX_CHARS)
    return _judge(
        "judge_faithfulness",
        FAITHFULNESS_PROMPT,
        f"Wiki excerpts:\n{ctx}\n\nAnswer:\n{answer}",
    )


def judge_verbosity(answer: str) -> dict:
    return _judge("judge_verbosity", VERBOSITY_PROMPT, f"Answer:\n{answer}")


def judge_prompt_adherence(answer: str, system_prompt: str, evidence: str) -> dict:
    ctx = truncate_for_judge(evidence, JUDGE_CONTEXT_MAX_CHARS)
    return _judge(
        "judge_prompt_adherence",
        ADHERENCE_PROMPT,
        f"System rules:\n{system_prompt}\n\nWiki excerpts:\n{ctx}\n\nAnswer:\n{answer}",
    )


def judge_context_precision(question: str, evidence: str) -> dict:
    ctx = truncate_for_judge(evidence, JUDGE_CONTEXT_MAX_CHARS)
    return _judge(
        "judge_context_precision",
        CONTEXT_PRECISION_PROMPT,
        f"Question: {question}\n\nRetrieved excerpts:\n{ctx}",
    )


def judge_context_recall(question: str, evidence: str) -> dict:
    ctx = truncate_for_judge(evidence, JUDGE_CONTEXT_MAX_CHARS)
    return _judge(
        "judge_context_recall",
        CONTEXT_RECALL_PROMPT,
        f"Question: {question}\n\nRetrieved excerpts:\n{ctx}",
    )


def judge_extraction(answer: str, gold: str) -> dict:
    if not gold:
        return {"score": None, "reason": "no gold answer"}
    gold_tokens = set(gold.lower().split())
    answer_tokens = set(answer.lower().split())
    overlap = len(gold_tokens & answer_tokens) / max(len(gold_tokens), 1)
    return {"score": round(overlap, 3), "reason": "token overlap with gold"}
