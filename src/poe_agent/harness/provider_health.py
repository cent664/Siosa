# ROLE: harness — reachability checks for answer and judge providers.

from __future__ import annotations

import httpx

from poe_agent.harness.config import Settings, get_settings


def ollama_reachable(settings: Settings | None = None) -> bool:
    s = settings or get_settings()
    try:
        with httpx.Client(timeout=3.0) as client:
            resp = client.get(f"{s.ollama_base_url.rstrip('/')}/api/tags")
            return resp.status_code == 200
    except httpx.HTTPError:
        return False


def judge_provider_reachable(settings: Settings | None = None) -> bool:
    from poe_agent.harness.config import get_effective_judge_provider

    s = settings or get_settings()
    mode = get_effective_judge_provider()
    if mode == "ollama":
        return ollama_reachable(s)
    if mode == "claude":
        return bool(s.anthropic_api_key)
    if mode == "gpt4":
        return bool(s.openai_api_key)
    if mode == "bedrock":
        return True
    return True


def judge_provider_hint(settings: Settings | None = None) -> str:
    from poe_agent.harness.config import get_effective_judge_provider

    s = settings or get_settings()
    if not s.inline_eval:
        return ""
    mode = get_effective_judge_provider()
    if mode == "ollama":
        if not s.enable_ollama:
            return ""
        if not ollama_reachable(s):
            return "Judges use Ollama but it is not reachable. Start Ollama or set JUDGE_PROVIDER=claude|gpt4 in .env."
    if mode == "claude" and not s.anthropic_api_key:
        return "JUDGE_PROVIDER=claude requires ANTHROPIC_API_KEY in .env."
    if mode == "gpt4" and not s.openai_api_key:
        return "JUDGE_PROVIDER=gpt4 requires OPENAI_API_KEY in .env."
    return ""
