# ROLE: harness — central configuration from environment variables.

from functools import lru_cache
from pathlib import Path
from typing import Self

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_runtime_provider_mode: str | None = None
_runtime_judge_provider: str | None = None


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    poe_provider_mode: str = "stub"  # stub | ollama | claude | gpt4 | bedrock
    poe_api_host: str = "127.0.0.1"
    poe_api_port: int = 8000
    poe_api_base_url: str = "http://127.0.0.1:8000"
    ollama_base_url: str = "http://127.0.0.1:11434"
    ollama_model: str = "llama3.2"
    anthropic_api_key: str = ""
    anthropic_model: str = "claude-sonnet-4-6"
    openai_api_key: str = ""
    openai_model: str = "gpt-4o"
    judge_provider: str = "ollama"  # provider used for inline quality judges
    inline_eval: bool = True
    enable_ollama: bool = True  # POE_ENABLE_OLLAMA — false on production (Railway)
    deployment_profile: str = ""  # set DEPLOYMENT_PROFILE=production on Railway for booth defaults
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    retrieval_top_k: int = 8
    hybrid_rrf_k: int = 60
    rerank_top_n: int = 5
    retrieval_mode: str = "live"  # local | live | hybrid
    live_wiki_max_pages: int = 5
    live_wiki_search_limit: int = 8
    live_wiki_max_search_queries: int = 4
    live_wiki_title_probe: bool = True
    live_wiki_title_overlap_filter: bool = True
    live_wiki_cache_ttl_hours: float = 24.0
    live_fallback_min_score: float = 0.25
    planner_max_retrieve_subtasks: int = 4
    retrieval_refine_enabled: bool = False
    retrieval_refine_min_score: float = -1.0
    retrieval_max_refine_rounds: int = 1
    poe_data_dir: Path = Path("data")
    poe_chroma_dir: Path = Path("data/chroma")
    aws_region: str = "us-east-1"
    bedrock_model_id: str = "anthropic.claude-3-haiku-20240307-v1:0"
    bedrock_embedding_model: str = "amazon.titan-embed-text-v2:0"
    s3_bucket: str = ""
    s3_prefix: str = "poe-wiki-agent/"
    log_level: str = "INFO"
    transcribe_provider: str = "local"  # local | openai
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

    @model_validator(mode="after")
    def apply_deployment_profile(self) -> Self:
        if self.deployment_profile.lower().strip() != "production":
            return self
        if self.judge_provider.lower() == "ollama":
            object.__setattr__(self, "judge_provider", "claude")
        if self.poe_provider_mode.lower() in ("stub", "ollama") and self.anthropic_api_key:
            object.__setattr__(self, "poe_provider_mode", "claude")
        object.__setattr__(self, "inline_eval", False)
        object.__setattr__(self, "enable_ollama", False)
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
    if normalized not in ("stub", "ollama", "claude", "gpt4", "bedrock"):
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
    if normalized not in ("stub", "ollama", "claude", "gpt4", "bedrock"):
        raise ValueError(f"Invalid judge provider: {mode}")
    _runtime_judge_provider = normalized


def default_judge_for_answer_mode(answer_mode: str) -> str:
    """Pick a judge backend that matches cloud answer providers."""
    if answer_mode == "claude":
        return "claude"
    if answer_mode == "gpt4":
        return "gpt4"
    if answer_mode == "ollama":
        return "ollama"
    return get_settings().judge_provider.lower()


def list_available_provider_modes() -> list[dict[str, str]]:
    """Modes the UI may offer, with availability hints."""
    from poe_agent.harness.provider_health import ollama_reachable

    s = get_settings()
    modes = [
        {"id": "stub", "label": "Stub (excerpts)", "available": "true"},
    ]
    if s.enable_ollama:
        modes.append({
            "id": "ollama",
            "label": "Ollama (local)",
            "available": "true" if ollama_reachable(s) else "false",
        })
    modes.append({
        "id": "claude",
        "label": "Claude (Anthropic API)",
        "available": "true" if s.anthropic_api_key else "false",
    })
    modes.append({
        "id": "gpt4",
        "label": "GPT-4 (OpenAI API)",
        "available": "true" if s.openai_api_key else "false",
    })
    return modes


def deployment_hint(settings: Settings | None = None) -> str:
    """Actionable hint when production booth defaults are not active."""
    s = settings or get_settings()
    if s.deployment_profile.lower().strip() == "production":
        return ""
    if s.inline_eval or s.enable_ollama:
        return (
            "Booth mode not active. On Railway set DEPLOYMENT_PROFILE=production "
            "(or INLINE_EVAL=false and POE_ENABLE_OLLAMA=false). "
            "Add ANTHROPIC_API_KEY and POE_PROVIDER_MODE=claude for cloud answers."
        )
    return ""
