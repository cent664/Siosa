# ROLE: harness — LLM and embedding provider adapters.

from __future__ import annotations

import json

from poe_agent.harness.config import Settings, get_effective_provider_mode, get_settings
from poe_agent.harness.providers.base import EmbeddingProvider, LLMProvider


class StubLLMProvider(LLMProvider):
    def generate(self, system: str, user: str) -> tuple[str, dict[str, int]]:
        return (
            "Pipeline is in stub mode.",
            {"prompt_tokens": 0, "completion_tokens": 0},
        )


class BedrockLLMProvider(LLMProvider):
    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()

    def generate(self, system: str, user: str) -> tuple[str, dict[str, int]]:
        import boto3

        client = boto3.client("bedrock-runtime", region_name=self.settings.aws_region)
        body = {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 1024,
            "system": system,
            "messages": [{"role": "user", "content": user}],
        }
        response = client.invoke_model(
            modelId=self.settings.bedrock_model_id,
            body=json.dumps(body),
            contentType="application/json",
            accept="application/json",
        )
        payload = json.loads(response["body"].read())
        text = ""
        for block in payload.get("content", []):
            if block.get("type") == "text":
                text += block.get("text", "")
        usage = payload.get("usage", {})
        return text, {
            "prompt_tokens": int(usage.get("input_tokens", 0)),
            "completion_tokens": int(usage.get("output_tokens", 0)),
        }


class LocalEmbeddingProvider(EmbeddingProvider):
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


class BedrockEmbeddingProvider(EmbeddingProvider):
    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()

    def embed(self, texts: list[str]) -> list[list[float]]:
        import boto3

        client = boto3.client("bedrock-runtime", region_name=self.settings.aws_region)
        out: list[list[float]] = []
        for text in texts:
            body = json.dumps({"inputText": text})
            response = client.invoke_model(
                modelId=self.settings.bedrock_embedding_model,
                body=body,
                contentType="application/json",
                accept="application/json",
            )
            payload = json.loads(response["body"].read())
            out.append(payload["embedding"])
        return out


def _resolve_provider(mode: str, settings: Settings) -> LLMProvider:
    if mode == "claude":
        from poe_agent.harness.providers.anthropic_provider import AnthropicLLMProvider

        return AnthropicLLMProvider(settings)
    if mode == "gpt4":
        from poe_agent.harness.providers.openai_provider import OpenAILLMProvider

        return OpenAILLMProvider(settings)
    if mode == "bedrock":
        return BedrockLLMProvider(settings)
    return StubLLMProvider()


def get_provider_model_id(mode: str | None = None) -> str:
    s = get_settings()
    mode = mode or get_effective_provider_mode()
    if mode == "claude":
        return s.anthropic_model
    if mode == "gpt4":
        return s.openai_model
    if mode == "bedrock":
        return s.bedrock_model_id
    return "stub"


def get_llm_provider(settings: Settings | None = None) -> LLMProvider:
    s = settings or get_settings()
    return _resolve_provider(get_effective_provider_mode(), s)


def get_judge_llm_provider(settings: Settings | None = None) -> LLMProvider:
    from poe_agent.harness.config import get_effective_judge_provider

    s = settings or get_settings()
    return _resolve_provider(get_effective_judge_provider(), s)


def get_embedding_provider(settings: Settings | None = None) -> EmbeddingProvider:
    s = settings or get_settings()
    if get_effective_provider_mode() == "bedrock":
        return BedrockEmbeddingProvider(s)
    return LocalEmbeddingProvider(s)
