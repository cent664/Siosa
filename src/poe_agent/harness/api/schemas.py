# ROLE: harness — request/response contracts for the API.

from typing import Any

from pydantic import BaseModel, Field


class Citation(BaseModel):
    title: str
    url: str
    snippet: str = ""


class LLMCallTrace(BaseModel):
    call_id: str
    purpose: str
    provider: str
    model: str
    system_prompt: str
    user_prompt: str
    response: str
    latency_ms: float
    token_counts: dict[str, int] = Field(default_factory=dict)


class QualityScores(BaseModel):
    context_precision: float | None = None
    context_recall: float | None = None
    faithfulness: float | None = None
    relevance: float | None = None
    prompt_adherence: float | None = None
    notes: dict[str, str] = Field(default_factory=dict)


class QueryTrace(BaseModel):
    pipeline: str = ""
    retrieval_source: str = ""
    retrieval_mode: str = ""
    retrieval_config: dict[str, Any] = Field(default_factory=dict)
    retrieval_refined: bool = False
    refine_queries: list[str] = Field(default_factory=list)
    retrieval_gate_reason: str = ""
    plan: list[dict[str, Any]] = Field(default_factory=list)
    tool_calls: list[dict[str, Any]] = Field(default_factory=list)
    retrieved_chunks: list[dict[str, Any]] = Field(default_factory=list)
    timing_ms: dict[str, float] = Field(default_factory=dict)
    llm_calls: list[LLMCallTrace] = Field(default_factory=list)


class QueryRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=2000)


class QueryResponse(BaseModel):
    answer: str
    citations: list[Citation]
    run_id: str
    mode: str = "stub"
    retrieved_count: int = 0
    trace: QueryTrace = Field(default_factory=QueryTrace)
    quality_scores: QualityScores = Field(default_factory=QualityScores)


class HealthResponse(BaseModel):
    status: str
    provider_mode: str
    chroma_ready: bool
    chunk_count: int = 0
    retrieval_mode: str = "local"
    live_retrieval_hint: str = ""
    judge_provider: str = "ollama"
    judge_reachable: bool = True
    judge_hint: str = ""


class EvaluateRequest(BaseModel):
    question: str
    answer: str | None = None
    expected_pages: list[str] = Field(default_factory=list)
    gold_answer: str | None = None


class EvaluateResponse(BaseModel):
    run_id: str
    metrics: dict[str, Any]


class ProviderModeInfo(BaseModel):
    id: str
    label: str
    available: bool


class ProviderSettingsResponse(BaseModel):
    mode: str
    source: str
    available_modes: list[ProviderModeInfo] = Field(default_factory=list)
    judge_provider: str = "ollama"
    judge_reachable: bool = True
    judge_hint: str = ""


class ProviderSettingsRequest(BaseModel):
    mode: str = Field(..., pattern="^(stub|ollama|claude|gpt4)$")


class TranscribeResponse(BaseModel):
    text: str
