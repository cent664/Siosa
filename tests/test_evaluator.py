# Tests for evaluator module.

import pytest

from poe_agent.evaluator.judges import judge_extraction
from poe_agent.evaluator.metrics import retrieval_precision, retrieval_recall


def test_retrieval_precision_and_recall():
    retrieved = ["Poison", "Ignite", "Flask"]
    expected = ["Poison", "Damage over time"]
    p = retrieval_precision(retrieved, expected)
    r = retrieval_recall(retrieved, expected)
    assert p == pytest.approx(1 / 3, rel=1e-3)
    assert r == 0.5


def test_judge_extraction_overlap():
    result = judge_extraction(
        "Poison is a damage over time ailment that scales with modifiers.",
        "Poison is a damage over time ailment.",
    )
    assert result["score"] is not None
    assert result["score"] > 0.3


def test_judge_extraction_no_gold():
    result = judge_extraction("any answer", "")
    assert result["score"] is None

