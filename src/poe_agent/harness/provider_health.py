# ROLE: harness — reachability checks for answer and judge providers.

from __future__ import annotations

from poe_agent.harness.config import Settings, get_settings, get_effective_judge_provider


def judge_provider_reachable(settings: Settings | None = None) -> bool:
    s = settings or get_settings()
    mode = get_effective_judge_provider()
    if mode == "claude":
        return bool(s.anthropic_api_key)
    if mode == "gpt4":
        return bool(s.openai_api_key)
    if mode == "bedrock":
        return True
    return True


def judge_provider_hint(settings: Settings | None = None) -> str:
    s = settings or get_settings()
    if not s.inline_eval:
        return ""
    mode = get_effective_judge_provider()
    if mode == "claude" and not s.anthropic_api_key:
        return "JUDGE_PROVIDER=claude requires ANTHROPIC_API_KEY in .env."
    if mode == "gpt4" and not s.openai_api_key:
        return "JUDGE_PROVIDER=gpt4 requires OPENAI_API_KEY in .env."
    return ""
