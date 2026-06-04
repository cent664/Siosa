import httpx
from fastapi import HTTPException

from poe_agent.harness.api.errors import map_query_exception


def test_map_httpx_error_to_502():
    exc = httpx.ConnectError("Connection refused")
    http_exc = map_query_exception(exc)
    assert http_exc.status_code == 502
    assert "Network" in http_exc.detail


def test_map_value_error():
    http_exc = map_query_exception(ValueError("ANTHROPIC_API_KEY is not set"))
    assert http_exc.status_code == 502
    assert "ANTHROPIC" in http_exc.detail


def test_passthrough_http_exception():
    original = HTTPException(status_code=400, detail="bad request")
    assert map_query_exception(original) is original
