# Tests for shared judge/answer evidence context.

from __future__ import annotations

from poe_agent.evaluator.context import format_evidence_context
from poe_agent.evaluator.judges import judge_prompt_adherence
from poe_agent.evaluator.inline import chunks_from_score_payload, run_inline_quality
from poe_agent.generator.answer import get_answer_system_prompt
from poe_agent.retriever.models import RetrievedChunk


def test_format_evidence_context_includes_title_and_text():
    chunks = [
        RetrievedChunk(
            "1",
            "Scion unlock details here " * 50,
            {"page_title": "Scion", "wiki_url": "https://www.poewiki.net/wiki/Scion"},
            0.9,
        ),
    ]
    ctx = format_evidence_context(chunks)
    assert "[1] Scion" in ctx
    assert "unlock" in ctx
    assert len(ctx) <= 1200 + 80


def test_judge_prompt_adherence_user_prompt_includes_wiki_excerpts(monkeypatch):
    from unittest.mock import patch

    from poe_agent.harness.trace import LLMResult

    from poe_agent.harness.config import get_settings

    monkeypatch.setenv("JUDGE_PROVIDER", "stub")
    get_settings.cache_clear()
    evidence = "[1] Scion (https://www.poewiki.net/wiki/Scion)\nFreedom achievement unlocks Scion."
    with patch("poe_agent.evaluator.judges.traced_generate") as mock_gen:
        mock_gen.return_value = LLMResult(
            call_id="t",
            purpose="judge_prompt_adherence",
            provider_name="stub",
            model_id="stub",
            system_prompt="",
            user_prompt="",
            text='{"score": 5, "reason": "ok"}',
            latency_ms=1.0,
            token_counts={},
        )
        judge_prompt_adherence("Answer text.", get_answer_system_prompt(), evidence)
        user_prompt = mock_gen.call_args[0][3]
        assert "Wiki excerpts:" in user_prompt
        assert "Freedom achievement" in user_prompt


def test_chunks_from_score_payload():
    rows = [{"page_title": "Scion", "wiki_url": "http://x", "text": "body"}]
    chunks = chunks_from_score_payload(rows)
    assert len(chunks) == 1
    assert chunks[0].metadata["page_title"] == "Scion"


def test_run_inline_quality_stub_skips():
    scores, latencies = run_inline_quality("q", "(Stub mode — x)", [])
    assert scores.notes.get("skipped")
    assert latencies == {}
