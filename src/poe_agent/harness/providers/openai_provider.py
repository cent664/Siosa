# ROLE: harness — OpenAI API (GPT-4) LLM provider.

from __future__ import annotations

from poe_agent.harness.config import Settings, get_settings
from poe_agent.harness.providers.base import LLMProvider


class OpenAILLMProvider(LLMProvider):
    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()
        if not self.settings.openai_api_key:
            raise ValueError("OPENAI_API_KEY is not set")

    def generate(self, system: str, user: str) -> tuple[str, dict[str, int]]:
        from openai import OpenAI

        client = OpenAI(api_key=self.settings.openai_api_key)
        response = client.chat.completions.create(
            model=self.settings.openai_model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            max_tokens=1024,
        )
        text = response.choices[0].message.content or ""
        usage = response.usage
        return text, {
            "prompt_tokens": int(usage.prompt_tokens or 0),
            "completion_tokens": int(usage.completion_tokens or 0),
        }
