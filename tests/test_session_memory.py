# Tests for session conversation memory and history search hints.

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from poe_agent.harness.config import Settings
from poe_agent.harness.session_memory import (
    append_turn,
    ensure_session,
    format_generation_context,
    history_search_hints,
    load_all_turns,
    load_prompt_history,
    load_recent_turns,
    normalize_session_id,
)
from poe_agent.generator.answer import generate_answer_with_meta
from poe_agent.retriever.models import RetrievedChunk


def test_normalize_session_id():
    assert normalize_session_id(None) is None
    assert normalize_session_id("not-a-uuid") is None
    sid = "550e8400-e29b-41d4-a716-446655440000"
    assert normalize_session_id(sid) == sid


def test_ensure_and_append_turns(tmp_path: Path):
    settings = Settings(
        session_memory_enabled=True,
        session_memory_summary_enabled=False,
        poe_data_dir=tmp_path,
    )
    sid = ensure_session(None, settings=settings)
    assert normalize_session_id(sid)
    append_turn(sid, "What is ignite?", "Ignite is a DoT.", settings=settings)
    append_turn(sid, "Does RF count as ignite?", "No.", settings=settings)
    turns = load_all_turns(sid, settings=settings)
    assert len(turns) == 2
    assert turns[0]["question"] == "What is ignite?"
    assert turns[1]["answer"] == "No."


def test_recent_window_does_not_delete_older(tmp_path: Path):
    settings = Settings(
        session_memory_enabled=True,
        session_memory_recent_turns=2,
        session_memory_summary_enabled=False,
        poe_data_dir=tmp_path,
    )
    sid = ensure_session(None, settings=settings)
    for i in range(4):
        append_turn(sid, f"q{i}", f"a{i}", settings=settings)
    assert len(load_all_turns(sid, settings=settings)) == 4
    recent = load_recent_turns(sid, settings=settings)
    assert [t["question"] for t in recent] == ["q2", "q3"]


def test_history_search_hints_includes_prior_topic():
    history = [
        {"question": "What are Pantheon powers?", "answer": "Soul of the Brine King..."},
        {"question": "How do I unlock them?", "answer": "..."},
    ]
    hints = history_search_hints(history)
    joined = " ".join(hints).lower()
    assert "pantheon" in joined


def test_history_page_titles_from_citations():
    from poe_agent.harness.session_memory import continuity_retrieval_context, history_page_titles

    history = [
        {
            "question": "What are Pantheon powers?",
            "answer": "...",
            "citations": [
                {"title": "Pantheon", "url": "https://www.poewiki.net/wiki/Pantheon"},
                {"title": "Soul of the Brine King", "url": "https://www.poewiki.net/wiki/Soul_of_the_Brine_King"},
            ],
        }
    ]
    titles = history_page_titles(history)
    assert "Pantheon" in titles
    assert any("Brine" in t for t in titles)
    hints = history_search_hints(history)
    assert "Pantheon" in hints

    # Same-topic follow-up keeps continuity; new topic clears prior probes/hints
    cont_titles, cont_hints = continuity_retrieval_context("list all of them", history)
    assert "Pantheon" in cont_titles
    assert cont_hints
    fresh_titles, fresh_hints = continuity_retrieval_context(
        "How does poison damage scale?",
        history,
    )
    assert fresh_titles == []
    assert fresh_hints == []


def test_append_turn_persists_citations(tmp_path: Path):
    settings = Settings(
        session_memory_enabled=True,
        session_memory_summary_enabled=False,
        poe_data_dir=tmp_path,
    )
    sid = ensure_session(None, settings=settings)
    append_turn(
        sid,
        "What are Pantheon powers?",
        "Answer",
        settings=settings,
        citations=[{"title": "Pantheon", "url": "https://example.com/Pantheon"}],
    )
    recent = load_recent_turns(sid, settings=settings)
    assert recent[0]["citations"][0]["title"] == "Pantheon"


def test_disabled_memory_noop(tmp_path: Path):
    settings = Settings(session_memory_enabled=False, poe_data_dir=tmp_path)
    sid = ensure_session(None, settings=settings)
    append_turn(sid, "q", "a", settings=settings)
    assert load_recent_turns(sid, settings=settings) == []


def test_format_generation_context_includes_summary():
    block = format_generation_context(
        "Talked about Pantheon.",
        [{"question": "Q1", "answer": "A1"}],
    )
    assert "Summary of earlier conversation" in block
    assert "Pantheon" in block
    assert "Q1" in block


def test_load_prompt_history_returns_summary(tmp_path: Path):
    settings = Settings(
        session_memory_enabled=True,
        session_memory_recent_turns=1,
        session_memory_summary_enabled=True,
        poe_data_dir=tmp_path,
    )
    sid = ensure_session(None, settings=settings)

    class FakeLLM:
        def generate(self, system: str, user: str) -> tuple[str, dict[str, int]]:
            return "Summary about pantheon.", {}

    with patch("poe_agent.harness.providers.get_llm_provider", return_value=FakeLLM()):
        append_turn(sid, "What are Pantheon powers?", "A1", settings=settings)
        append_turn(sid, "And Soul of Tukohama?", "A2", settings=settings)
    summary, recent = load_prompt_history(sid, settings=settings)
    assert "pantheon" in summary.lower()
    assert len(recent) == 1
    assert recent[0]["question"] == "And Soul of Tukohama?"


def test_generate_includes_history_in_prompt():
    chunk = RetrievedChunk(
        chunk_id="c1",
        text="Ignite deals fire damage over time.",
        score=1.0,
        metadata={"page_title": "Ignite", "wiki_url": "https://example.com"},
    )

    class FakeLLM:
        def generate(self, system: str, user: str) -> tuple[str, dict[str, int]]:
            assert "Prior conversation" in user
            assert "What is ignite?" in user
            assert "Current question" in user
            return "Follow-up answer.", {"prompt_tokens": 1, "completion_tokens": 1}

    with (
        patch("poe_agent.generator.answer.get_llm_provider", return_value=FakeLLM()),
        patch("poe_agent.generator.answer.get_effective_provider_mode", return_value="claude"),
        patch("poe_agent.generator.answer.get_provider_model_id", return_value="test"),
        patch("poe_agent.generator.answer.traced_generate") as traced,
    ):
        def _traced(purpose, llm, system, user, provider_name, model_id):
            text, tokens = llm.generate(system, user)

            class R:
                pass

            r = R()
            r.text = text
            r.token_counts = tokens
            return r

        traced.side_effect = _traced
        answer, citations, _ = generate_answer_with_meta(
            "Does that stack?",
            [chunk],
            history=[{"question": "What is ignite?", "answer": "A DoT."}],
        )
    assert answer == "Follow-up answer."
    assert citations
