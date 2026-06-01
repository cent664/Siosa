# ROLE: harness — structured JSON logging for every agent run.

from __future__ import annotations

import json
import logging
import sys
import time
import uuid
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Any, Generator

from poe_agent.harness.config import get_settings


def configure_logging() -> None:
    level = getattr(logging, get_settings().log_level.upper(), logging.INFO)
    logging.basicConfig(
        level=level,
        format="%(message)s",
        stream=sys.stdout,
    )


@dataclass
class RunLog:
    run_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    input_query: str = ""
    tool_calls: list[dict[str, Any]] = field(default_factory=list)
    retrieved_chunks: list[dict[str, Any]] = field(default_factory=list)
    output_answer: str = ""
    citations: list[dict[str, Any]] = field(default_factory=list)
    latency_ms: float = 0.0
    token_counts: dict[str, int] = field(default_factory=dict)
    extra: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "input": self.input_query,
            "tool_calls": self.tool_calls,
            "retrieved_chunks": self.retrieved_chunks,
            "output": self.output_answer,
            "citations": self.citations,
            "latency_ms": self.latency_ms,
            "token_counts": self.token_counts,
            "extra": self.extra,
        }

    def emit(self) -> None:
        logging.getLogger("poe_agent.run").info(json.dumps(self.to_dict(), default=str))


@contextmanager
def agent_run(query: str) -> Generator[RunLog, None, None]:
    run = RunLog(input_query=query)
    start = time.perf_counter()
    try:
        yield run
    finally:
        run.latency_ms = round((time.perf_counter() - start) * 1000, 2)
        run.emit()
