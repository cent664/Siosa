from poe_agent.evaluator.context import format_evidence_context
from poe_agent.evaluator.inline import score_to_normalized
from poe_agent.retriever.models import RetrievedChunk


def test_score_to_normalized():
    assert score_to_normalized(5.0) == 1.0
    assert score_to_normalized(3.0) == 0.6
    assert score_to_normalized(None) is None
    assert score_to_normalized(6.0) == 1.0
    assert score_to_normalized(0.0) == 0.0


def test_format_evidence_context_preview():
    chunks = [
        RetrievedChunk(
            chunk_id="a",
            text="Poison damage scales with modifiers.",
            metadata={"page_title": "Poison"},
            score=0.9,
        )
    ]
    preview = format_evidence_context(chunks)
    assert "[1] Poison" in preview
    assert "Poison damage" in preview
