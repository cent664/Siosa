# ROLE: harness — map LLM/provider failures to HTTP errors for /query.

from __future__ import annotations

import logging

import httpx
from fastapi import HTTPException

logger = logging.getLogger(__name__)


def _safe_api_message(exc: BaseException) -> str:
    """Extract a short user-safe message without leaking secrets."""
    text = str(exc).strip()
    if len(text) > 400:
        text = text[:397] + "..."
    return text or type(exc).__name__


def map_query_exception(exc: BaseException) -> HTTPException:
    """Convert provider/network errors into 502 with readable detail."""
    if isinstance(exc, HTTPException):
        return exc

    logger.exception("Query pipeline failed")

    if isinstance(exc, httpx.HTTPError):
        return HTTPException(
            status_code=502,
            detail=(
                "Network error talking to an LLM service. "
                f"Check API keys and provider settings. ({_safe_api_message(exc)})"
            ),
        )

    if isinstance(exc, ValueError):
        return HTTPException(status_code=502, detail=_safe_api_message(exc))

    try:
        import anthropic

        if isinstance(exc, anthropic.APIError):
            status = getattr(exc, "status_code", None)
            prefix = f"Anthropic API error ({status})" if status else "Anthropic API error"
            return HTTPException(status_code=502, detail=f"{prefix}: {_safe_api_message(exc)}")
    except ImportError:
        pass

    try:
        import openai

        if isinstance(exc, openai.APIError):
            return HTTPException(
                status_code=502,
                detail=f"OpenAI API error: {_safe_api_message(exc)}",
            )
    except ImportError:
        pass

    return HTTPException(
        status_code=502,
        detail=f"Query failed: {_safe_api_message(exc)}",
    )
