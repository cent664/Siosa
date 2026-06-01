# ROLE: harness — request-scoped LLM call tracing for /query responses.

from __future__ import annotations

import time
import uuid
from contextvars import ContextVar
from dataclasses import dataclass, field
from typing import Any

from poe_agent.harness.providers.base import LLMProvider

_llm_calls: ContextVar[list[dict[str, Any]]] = ContextVar("llm_calls", default=[])


@dataclass
class LLMResult:
    text: str
    token_counts: dict[str, int]
    latency_ms: float
    system_prompt: str
    user_prompt: str
    model_id: str
    provider_name: str
    purpose: str
    call_id: str = field(default_factory=lambda: str(uuid.uuid4()))

    def to_trace_dict(self) -> dict[str, Any]:
        return {
            "call_id": self.call_id,
            "purpose": self.purpose,
            "provider": self.provider_name,
            "model": self.model_id,
            "system_prompt": self.system_prompt,
            "user_prompt": self.user_prompt,
            "response": self.text,
            "latency_ms": self.latency_ms,
            "token_counts": self.token_counts,
        }


def reset_llm_calls() -> None:
    _llm_calls.set([])


def get_llm_calls() -> list[dict[str, Any]]:
    return list(_llm_calls.get())


def traced_generate(
    purpose: str,
    provider: LLMProvider,
    system: str,
    user: str,
    *,
    provider_name: str,
    model_id: str,
) -> LLMResult:
    start = time.perf_counter()
    text, tokens = provider.generate(system, user)
    latency_ms = round((time.perf_counter() - start) * 1000, 2)
    result = LLMResult(
        text=text,
        token_counts=tokens,
        latency_ms=latency_ms,
        system_prompt=system,
        user_prompt=user,
        model_id=model_id,
        provider_name=provider_name,
        purpose=purpose,
    )
    calls = _llm_calls.get()
    calls.append(result.to_trace_dict())
    _llm_calls.set(calls)
    return result
