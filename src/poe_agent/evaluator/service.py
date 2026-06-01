# ROLE: evaluator — /evaluate endpoint orchestration.

from __future__ import annotations

import json
import time
import uuid
from pathlib import Path

from poe_agent.evaluator.judges import judge_extraction, judge_faithfulness, judge_relevance
from poe_agent.evaluator.metrics import retrieval_precision, retrieval_recall, titles_from_chunks
from poe_agent.harness.api.schemas import EvaluateRequest, EvaluateResponse
from poe_agent.harness.config import get_settings
from poe_agent.harness.api.query_service import handle_query
from poe_agent.retriever.pipeline import retrieve_for_query


def run_evaluation(body: EvaluateRequest) -> EvaluateResponse:
    run_id = str(uuid.uuid4())
    start = time.perf_counter()

    question = body.question
    if body.answer:
        answer = body.answer
        chunks, _source, _debug = retrieve_for_query(question)
    else:
        qr = handle_query(question)
        answer = qr.answer
        chunks, _source, _debug = retrieve_for_query(question)

    retrieved_titles = titles_from_chunks(chunks)
    context = "\n".join(c.text[:500] for c in chunks)

    metrics = {
        "retrieval_precision": retrieval_precision(retrieved_titles, body.expected_pages),
        "retrieval_recall": retrieval_recall(retrieved_titles, body.expected_pages),
        "relevance": judge_relevance(question, answer),
        "faithfulness": judge_faithfulness(answer, context),
        "extraction": judge_extraction(answer, body.gold_answer or ""),
        "latency_ms": round((time.perf_counter() - start) * 1000, 2),
        "retrieved_titles": retrieved_titles,
    }

    _log_eval(run_id, question, metrics)
    return EvaluateResponse(run_id=run_id, metrics=metrics)


def _log_eval(run_id: str, question: str, metrics: dict) -> None:
    settings = get_settings()
    settings.eval_dir.mkdir(parents=True, exist_ok=True)
    path = settings.eval_dir / "eval_runs.jsonl"
    row = {"run_id": run_id, "question": question, "metrics": metrics}
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(row, default=str) + "\n")


def run_gold_set_eval() -> list[dict]:
    gold_path = Path(__file__).resolve().parent.parent / "knowledge" / "eval" / "gold.jsonl"
    results = []
    with open(gold_path, encoding="utf-8") as f:
        for line in f:
            row = json.loads(line)
            req = EvaluateRequest(
                question=row["question"],
                expected_pages=row.get("expected_pages", []),
                gold_answer=row.get("gold_answer"),
            )
            resp = run_evaluation(req)
            results.append({"id": row["id"], "metrics": resp.metrics})
    return results
