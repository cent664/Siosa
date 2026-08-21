# ROLE: harness — LLM and embedding provider adapters (Claude / GPT-4 only).

from __future__ import annotations

from poe_agent.harness.config import Settings, get_effective_provider_mode, get_settings
from poe_agent.harness.providers.base import EmbeddingProvider, LLMProvider


class LocalEmbeddingProvider(EmbeddingProvider):
    """sentence-transformers embeddings for local/hybrid index mode (not used on live default)."""

    _model = None

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()

    def _get_model(self):
        if LocalEmbeddingProvider._model is None:
            from sentence_transformers import SentenceTransformer

            LocalEmbeddingProvider._model = SentenceTransformer(self.settings.embedding_model)
        return LocalEmbeddingProvider._model

    def embed(self, texts: list[str]) -> list[list[float]]:
        model = self._get_model()
        vectors = model.encode(texts, show_progress_bar=False)
        return [v.tolist() for v in vectors]


def _resolve_provider(mode: str, settings: Settings) -> LLMProvider:
    if mode == "claude":
        if not settings.anthropic_api_key:
            raise ValueError(
                "ANTHROPIC_API_KEY not set. Add it to .env (console.anthropic.com)."
            )
        from poe_agent.harness.providers.anthropic_provider import AnthropicLLMProvider

        return AnthropicLLMProvider(settings)
    if mode == "gpt4":
        if not settings.openai_api_key:
            raise ValueError(
                "OPENAI_API_KEY not set. Add it to .env (platform.openai.com)."
            )
        from poe_agent.harness.providers.openai_provider import OpenAILLMProvider

        return OpenAILLMProvider(settings)
    raise ValueError(f"Unknown provider mode {mode!r}. Use claude or gpt4.")


def get_provider_model_id(mode: str | None = None) -> str:
    s = get_settings()
    mode = mode or get_effective_provider_mode()
    if mode == "claude":
        return s.anthropic_model
    if mode == "gpt4":
        return s.openai_model
    return mode


def get_llm_provider(settings: Settings | None = None) -> LLMProvider:
    s = settings or get_settings()
    return _resolve_provider(get_effective_provider_mode(), s)


def get_judge_llm_provider(settings: Settings | None = None) -> LLMProvider:
    from poe_agent.harness.config import get_effective_judge_provider

    s = settings or get_settings()
    return _resolve_provider(get_effective_judge_provider(), s)


def get_embedding_provider(settings: Settings | None = None) -> EmbeddingProvider:
    return LocalEmbeddingProvider(settings or get_settings())
