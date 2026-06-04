# ROLE: harness — on-demand quality scoring for /score.

from __future__ import annotations

import time
import uuid

from poe_agent.evaluator.inline import chunks_from_score_payload, run_inline_quality
from poe_agent.harness.api.schemas import ScoreRequest, ScoreResponse


def handle_score(body: ScoreRequest) -> ScoreResponse:
    chunks = chunks_from_score_payload([c.model_dump() for c in body.chunks])
    t0 = time.perf_counter()
    quality, judge_latencies = run_inline_quality(body.question, body.answer, chunks)
    evaluation_ms = round((time.perf_counter() - t0) * 1000, 2)
    timing_ms = {"evaluation": evaluation_ms, **{f"judge_{k}": v for k, v in judge_latencies.items()}}
    return ScoreResponse(
        run_id=str(uuid.uuid4()),
        quality_scores=quality,
        timing_ms=timing_ms,
    )
