"""Tests for the real IBM watsonx.ai client wiring and failure handling.

These tests never touch the network. They verify:
  - Region configuration points at the Frankfurt (eu-de) ML endpoint.
  - Missing WATSONX_API_KEY surfaces a clean AIServiceUnavailableError
    (not a raw exception / no secret leakage).
  - IAM auth failure and non-200 generation responses raise
    AIServiceUnavailableError.
  - Malformed generation payloads raise AIInvalidOutputError.
  - The generation request targets the configured region URL.

No real IBM credentials or quota are consumed.
"""
import types

import httpx
import pytest
from pydantic import SecretStr

from app.ai import client as watsonx_client
from app.ai.exceptions import AIInvalidOutputError, AIServiceUnavailableError
from app.core.config import settings


class _FakeResponse:
    def __init__(self, status_code: int, json_body=None):
        self.status_code = status_code
        self._json = json_body if json_body is not None else {}

    def json(self):
        return self._json


class _FakeAsyncClient:
    """Minimal async context manager that returns a queued response for post()."""

    def __init__(self, response=None, raise_transport=False):
        self._response = response
        self._raise_transport = raise_transport
        self.last_url = None
        self.last_kwargs = None

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False

    async def post(self, url, **kwargs):
        self.last_url = url
        self.last_kwargs = kwargs
        if self._raise_transport:
            raise httpx.ConnectError("boom")
        return self._response


@pytest.fixture(autouse=True)
def _reset_token_cache():
    """Ensure each test starts with a cold IAM token cache."""
    watsonx_client._cached_token = None
    watsonx_client._token_expiry = 0.0
    yield
    watsonx_client._cached_token = None
    watsonx_client._token_expiry = 0.0


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

def test_watsonx_url_targets_frankfurt_region():
    """Default region endpoint must be eu-de (Frankfurt), matching the runtime."""
    assert settings.WATSONX_URL == "https://eu-de.ml.cloud.ibm.com"


def test_watsonx_model_id_is_configurable_and_set():
    assert settings.WATSONX_MODEL_ID  # non-empty; overridable via env


# ---------------------------------------------------------------------------
# Missing / invalid credentials
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_missing_api_key_raises_service_unavailable(monkeypatch):
    monkeypatch.setattr(watsonx_client.settings, "WATSONX_API_KEY", SecretStr(""), raising=False)
    with pytest.raises(AIServiceUnavailableError):
        await watsonx_client._fetch_iam_token()


@pytest.mark.asyncio
async def test_iam_non_200_raises_service_unavailable(monkeypatch):
    monkeypatch.setattr(watsonx_client.settings, "WATSONX_API_KEY", SecretStr("dummy"), raising=False)
    fake = _FakeAsyncClient(response=_FakeResponse(401, {"errorMessage": "bad key"}))
    monkeypatch.setattr(watsonx_client.httpx, "AsyncClient", lambda *a, **k: fake)
    with pytest.raises(AIServiceUnavailableError):
        await watsonx_client._fetch_iam_token()


@pytest.mark.asyncio
async def test_iam_network_error_raises_service_unavailable(monkeypatch):
    monkeypatch.setattr(watsonx_client.settings, "WATSONX_API_KEY", SecretStr("dummy"), raising=False)
    fake = _FakeAsyncClient(raise_transport=True)
    monkeypatch.setattr(watsonx_client.httpx, "AsyncClient", lambda *a, **k: fake)
    with pytest.raises(AIServiceUnavailableError):
        await watsonx_client._fetch_iam_token()


# ---------------------------------------------------------------------------
# generate()
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_generate_uses_region_url_and_returns_text(monkeypatch):
    async def _fake_token():
        return "fake-token"

    monkeypatch.setattr(watsonx_client, "_get_token", _fake_token)
    fake = _FakeAsyncClient(
        response=_FakeResponse(
            200,
            {"choices": [{"message": {"content": '{"ok": true}'}}]},
        )
    )
    monkeypatch.setattr(watsonx_client.httpx, "AsyncClient", lambda *a, **k: fake)

    out = await watsonx_client.generate("hello")
    assert out == '{"ok": true}'
    assert fake.last_url.startswith(settings.WATSONX_URL.rstrip("/"))
    assert "eu-de" in fake.last_url
    assert fake.last_url.endswith("/ml/v1/text/chat")


@pytest.mark.asyncio
async def test_generate_non_200_raises_service_unavailable(monkeypatch):
    async def _fake_token():
        return "fake-token"

    monkeypatch.setattr(watsonx_client, "_get_token", _fake_token)
    fake = _FakeAsyncClient(response=_FakeResponse(429, {"error": "rate limited"}))
    monkeypatch.setattr(watsonx_client.httpx, "AsyncClient", lambda *a, **k: fake)

    with pytest.raises(AIServiceUnavailableError):
        await watsonx_client.generate("hello")


@pytest.mark.asyncio
async def test_generate_malformed_body_raises_invalid_output(monkeypatch):
    async def _fake_token():
        return "fake-token"

    monkeypatch.setattr(watsonx_client, "_get_token", _fake_token)
    fake = _FakeAsyncClient(response=_FakeResponse(200, {"unexpected": "shape"}))
    monkeypatch.setattr(watsonx_client.httpx, "AsyncClient", lambda *a, **k: fake)

    with pytest.raises(AIInvalidOutputError):
        await watsonx_client.generate("hello")


@pytest.mark.asyncio
async def test_generate_network_error_raises_service_unavailable(monkeypatch):
    async def _fake_token():
        return "fake-token"

    monkeypatch.setattr(watsonx_client, "_get_token", _fake_token)
    fake = _FakeAsyncClient(raise_transport=True)
    monkeypatch.setattr(watsonx_client.httpx, "AsyncClient", lambda *a, **k: fake)

    with pytest.raises(AIServiceUnavailableError):
        await watsonx_client.generate("hello")
