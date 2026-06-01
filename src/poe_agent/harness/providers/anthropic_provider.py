# ROLE: harness — Anthropic API (Claude) LLM provider.

from __future__ import annotations

from poe_agent.harness.config import Settings, get_settings
from poe_agent.harness.providers.base import LLMProvider


class AnthropicLLMProvider(LLMProvider):
    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()
        if not self.settings.anthropic_api_key:
            raise ValueError("ANTHROPIC_API_KEY is not set")

    def generate(self, system: str, user: str) -> tuple[str, dict[str, int]]:
        import anthropic

        client = anthropic.Anthropic(api_key=self.settings.anthropic_api_key)
        message = client.messages.create(
            model=self.settings.anthropic_model,
            max_tokens=1024,
            system=system,
            messages=[{"role": "user", "content": user}],
        )
        text = ""
        for block in message.content:
            if block.type == "text":
                text += block.text
        usage = message.usage
        return text, {
            "prompt_tokens": int(usage.input_tokens),
            "completion_tokens": int(usage.output_tokens),
        }
