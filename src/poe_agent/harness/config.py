# ROLE: harness — central configuration from environment variables.

from functools import lru_cache
from pathlib import Path
from typing import Self

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_runtime_provider_mode: str | None = None
_runtime_judge_provider: str | None = None

_VALID_ANSWER_MODES = frozenset({"claude", "gpt4", "bedrock"})
_VALID_JUDGE_MODES = frozenset({"claude", "gpt4", "bedrock"})


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    poe_provider_mode: str = "claude"  # claude | gpt4 | bedrock
    poe_api_host: str = "127.0.0.1"
    poe_api_port: int = 8000
    poe_api_base_url: str = "http://127.0.0.1:8000"
    anthropic_api_key: str = ""
    anthropic_model: str = "claude-sonnet-4-6"
    openai_api_key: str = ""
    openai_model: str = "gpt-4o"
    judge_provider: str = "claude"  # claude | gpt4 | bedrock
    inline_eval: bool = False
    deployment_profile: str = ""  # set DEPLOYMENT_PROFILE=production on Railway
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    retrieval_top_k: int = 8
    hybrid_rrf_k: int = 60
    # Rule of thumb: 8–12 passages is a common RAG default; raise if answers miss list details.
    rerank_top_n: int = 8
    retrieval_mode: str = "live"  # local | live | hybrid
    live_wiki_max_pages: int = 6
    live_wiki_search_limit: int = 8
    live_wiki_max_search_queries: int = 4
    live_wiki_title_probe: bool = True
    live_wiki_max_title_probes: int = 4
    live_wiki_title_overlap_filter: bool = True
    live_wiki_cache_ttl_hours: float = 24.0
    # Performance (toggle off to undo)
    live_wiki_search_concurrency: int = 4
    live_wiki_fetch_concurrency: int = 4
    live_wiki_use_extracts: bool = False  # faster plain text; loses tables — keep off if structure_aware
    live_wiki_structure_aware: bool = True
    live_wiki_chunk_diversity: bool = True
    live_wiki_max_chunks_per_page: int = 2
    live_wiki_link_expand: bool = True
    live_wiki_link_expand_max: int = 3
    # Rule of thumb: enumerate follow-ups need more hops from the index table (gods, uniques, …).
    live_wiki_link_expand_enumerate_max: int = 10
    live_wiki_link_harvest_max: int = 120
    live_wiki_prefer_table_links: bool = True
    live_wiki_prefer_prior_pages: bool = True
    live_wiki_followup_rewrite: bool = True
    live_wiki_request_delay_sec: float = 0.15
    rerank_warm_on_startup: bool = True
    live_fallback_min_score: float = 0.25
    planner_max_retrieve_subtasks: int = 4
    retrieval_refine_enabled: bool = False
    retrieval_refine_min_score: float = -1.0
    retrieval_max_refine_rounds: int = 1
    rate_limit_enabled: bool = False
    rate_limit_asks_per_day: int = 20
    operator_analytics_enabled: bool = True
    operator_dashboard_key: str = ""
    session_memory_enabled: bool = True
    session_memory_recent_turns: int = 8
    session_memory_summary_enabled: bool = True
    # Deprecated alias — prefer session_memory_recent_turns
    session_memory_max_turns: int = 8
    poe_data_dir: Path = Path("data")
    poe_chroma_dir: Path = Path("data/chroma")
    aws_region: str = "us-east-1"
    bedrock_model_id: str = "anthropic.claude-3-haiku-20240307-v1:0"
    bedrock_embedding_model: str = "amazon.titan-embed-text-v2:0"
    s3_bucket: str = ""
    s3_prefix: str = "poe-wiki-agent/"
    log_level: str = "INFO"
    transcribe_provider: str = "openai"  # local | openai
    transcribe_model: str = ""  # default: base (local) or whisper-1 (openai)

    @property
    def raw_dir(self) -> Path:
        return self.poe_data_dir / "raw"

    @property
    def chunks_dir(self) -> Path:
        return self.poe_data_dir / "chunks"

    @property
    def live_cache_dir(self) -> Path:
        return self.poe_data_dir / "live_cache"

    @property
    def eval_dir(self) -> Path:
        return self.poe_data_dir / "eval"

    @property
    def rate_limit_db_path(self) -> Path:
        return self.poe_data_dir / "rate_limit.sqlite"

    @property
    def operator_analytics_db_path(self) -> Path:
        return self.poe_data_dir / "operator_analytics.sqlite"

    @property
    def session_memory_db_path(self) -> Path:
        return self.poe_data_dir / "session_memory.sqlite"

    @model_validator(mode="after")
    def apply_deployment_profile(self) -> Self:
        if self.deployment_profile.lower().strip() != "production":
            return self
        if self.judge_provider.lower() not in ("claude", "gpt4"):
            object.__setattr__(self, "judge_provider", "claude")
        if self.poe_provider_mode.lower() not in ("claude", "gpt4", "bedrock"):
            object.__setattr__(self, "poe_provider_mode", "claude")
        object.__setattr__(self, "inline_eval", False)
        # Docker image has no faster-whisper; voice uses OpenAI when keys are set.
        object.__setattr__(self, "transcribe_provider", "openai")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()


def get_effective_provider_mode() -> str:
    """Runtime UI override takes precedence over .env POE_PROVIDER_MODE."""
    if _runtime_provider_mode is not None:
        return _runtime_provider_mode.lower()
    return get_settings().poe_provider_mode.lower()


def set_runtime_provider_mode(mode: str | None) -> None:
    global _runtime_provider_mode
    if mode is None:
        _runtime_provider_mode = None
        return
    normalized = mode.lower().strip()
    if normalized not in _VALID_ANSWER_MODES:
        raise ValueError(f"Invalid provider mode: {mode}")
    _runtime_provider_mode = normalized


def get_provider_mode_source() -> str:
    return "runtime" if _runtime_provider_mode is not None else "env"


def get_effective_judge_provider() -> str:
    """Runtime judge override, else env JUDGE_PROVIDER."""
    if _runtime_judge_provider is not None:
        return _runtime_judge_provider.lower()
    return get_settings().judge_provider.lower()


def set_runtime_judge_provider(mode: str | None) -> None:
    global _runtime_judge_provider
    if mode is None:
        _runtime_judge_provider = None
        return
    normalized = mode.lower().strip()
    if normalized not in _VALID_JUDGE_MODES:
        raise ValueError(f"Invalid judge provider: {mode}")
    _runtime_judge_provider = normalized


def default_judge_for_answer_mode(answer_mode: str) -> str:
    """Pick a judge backend that matches cloud answer providers."""
    if answer_mode == "claude":
        return "claude"
    if answer_mode == "gpt4":
        return "gpt4"
    return get_settings().judge_provider.lower()


def short_model_label(model_id: str) -> str:
    """Short display name for provider dropdown (e.g. claude-sonnet-4-6 → Sonnet 4.6)."""
    mid = (model_id or "").strip()
    if not mid:
        return "Claude"
    low = mid.lower()
    if low.startswith("claude-"):
        tail = mid[7:]
        parts = tail.split("-")
        family = parts[0].capitalize() if parts else "Claude"
        if len(parts) > 1:
            version = ".".join(parts[1:])
            return f"{family} {version}"
        return family
    if low.startswith("gpt"):
        if "-" in mid:
            family, version = mid.split("-", 1)
            return f"{family.upper()}-{version}"
        return mid.upper()
    return mid


def list_available_provider_modes() -> list[dict[str, str]]:
    """Modes the UI may offer, with availability hints."""
    s = get_settings()
    return [
        {
            "id": "claude",
            "label": short_model_label(s.anthropic_model),
            "available": "true" if s.anthropic_api_key else "false",
        },
        {
            "id": "gpt4",
            "label": short_model_label(s.openai_model),
            "available": "true" if s.openai_api_key else "false",
        },
    ]


def provider_missing_key_message(mode: str | None = None) -> str:
    """Human-readable error when the selected provider has no API key."""
    m = (mode or get_effective_provider_mode()).lower()
    s = get_settings()
    if m == "claude" and not s.anthropic_api_key:
        return "ANTHROPIC_API_KEY not set. Add it to .env (console.anthropic.com)."
    if m == "gpt4" and not s.openai_api_key:
        return "OPENAI_API_KEY not set. Add it to .env (platform.openai.com)."
    if m == "bedrock":
        return ""
    return ""


def _is_local_deployment(settings: Settings) -> bool:
    host = settings.poe_api_host.lower().strip()
    if host in ("127.0.0.1", "localhost", "::1"):
        return True
    base = settings.poe_api_base_url.lower()
    return "127.0.0.1" in base or "localhost" in base


def deployment_hint(settings: Settings | None = None) -> str:
    """Actionable hint when production defaults are not active (deployed hosts only)."""
    s = settings or get_settings()
    if s.deployment_profile.lower().strip() == "production":
        return ""
    if _is_local_deployment(s):
        return ""
    if s.inline_eval:
        return (
            "On Railway set DEPLOYMENT_PROFILE=production "
            "(or INLINE_EVAL=false). "
            "Add ANTHROPIC_API_KEY and POE_PROVIDER_MODE=claude for cloud answers."
        )
    return ""


def operator_analytics_active(settings: Settings | None = None) -> bool:
    """Operator visit/Ask logging; controlled by OPERATOR_ANALYTICS_ENABLED."""
    s = settings or get_settings()
    return bool(s.operator_analytics_enabled)
