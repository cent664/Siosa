# Tests for QueryResponse trace and quality score schemas.

from poe_agent.harness.api.schemas import (
    LLMCallTrace,
    QualityScores,
    QueryResponse,
    QueryTrace,
)


def test_query_response_includes_trace_and_scores():
    resp = QueryResponse(
        answer="test",
        citations=[],
        run_id="abc",
        trace=QueryTrace(
            pipeline="linear_rag",
            timing_ms={"retrieval": 10.0, "total": 50.0},
            llm_calls=[
                LLMCallTrace(
                    call_id="1",
                    purpose="answer",
                    provider="claude",
                    model="claude-sonnet-4-6",
                    system_prompt="sys",
                    user_prompt="user",
                    response="out",
                    latency_ms=100.0,
                )
            ],
        ),
        quality_scores=QualityScores(
            context_precision=0.8,
            context_recall=0.6,
            faithfulness=4.0,
            relevance=5.0,
            prompt_adherence=5.0,
        ),
    )
    d = resp.model_dump()
    assert d["trace"]["pipeline"] == "linear_rag"
    assert len(d["trace"]["llm_calls"]) == 1
    assert d["quality_scores"]["faithfulness"] == 4.0
