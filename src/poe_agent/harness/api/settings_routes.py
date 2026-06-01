# ROLE: harness — runtime provider settings for UI toggle.

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from poe_agent.harness.api.schemas import (
    ProviderModeInfo,
    ProviderSettingsRequest,
    ProviderSettingsResponse,
)
from poe_agent.harness.config import (
    default_judge_for_answer_mode,
    get_effective_judge_provider,
    get_effective_provider_mode,
    get_provider_mode_source,
    get_settings,
    list_available_provider_modes,
    set_runtime_judge_provider,
    set_runtime_provider_mode,
)
from poe_agent.harness.provider_health import (
    judge_provider_hint,
    judge_provider_reachable,
    ollama_reachable,
)

router = APIRouter(prefix="/settings", tags=["settings"])


def _build_provider_response(mode: str, source: str) -> ProviderSettingsResponse:
    settings = get_settings()
    modes = [
        ProviderModeInfo(
            id=m["id"],
            label=m["label"],
            available=m["available"] == "true",
        )
        for m in list_available_provider_modes()
    ]
    return ProviderSettingsResponse(
        mode=mode,
        source=source,
        available_modes=modes,
        judge_provider=get_effective_judge_provider(),
        judge_reachable=judge_provider_reachable(settings),
        judge_hint=judge_provider_hint(settings),
    )


@router.get("/provider", response_model=ProviderSettingsResponse)
def get_provider() -> ProviderSettingsResponse:
    return _build_provider_response(
        get_effective_provider_mode(),
        get_provider_mode_source(),
    )


@router.post("/provider", response_model=ProviderSettingsResponse)
def set_provider(body: ProviderSettingsRequest) -> ProviderSettingsResponse:
    mode = body.mode.lower()
    settings = get_settings()

    if mode == "ollama" and not ollama_reachable(settings):
        raise HTTPException(
            status_code=503,
            detail="Ollama is not reachable. Start Ollama or use stub mode.",
        )
    if mode == "claude" and not settings.anthropic_api_key:
        raise HTTPException(
            status_code=400,
            detail="ANTHROPIC_API_KEY not set. Add it to .env (console.anthropic.com).",
        )
    if mode == "gpt4" and not settings.openai_api_key:
        raise HTTPException(
            status_code=400,
            detail="OPENAI_API_KEY not set. Add it to .env (platform.openai.com).",
        )

    set_runtime_provider_mode(mode)
    if mode in ("claude", "gpt4", "ollama"):
        set_runtime_judge_provider(default_judge_for_answer_mode(mode))
    else:
        set_runtime_judge_provider(None)

    return _build_provider_response(mode, "runtime")
