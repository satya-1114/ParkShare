"""Async HTTP client for IBM watsonx.ai text generation.

IAM token lifecycle
-------------------
IBM Cloud IAM tokens are valid for 1 hour (3600 s). This module caches the
last retrieved token in module-level state and refreshes it when it is within
60 s of expiry. The cache is per-process (in-memory); a fresh token is fetched
on first call after a cold start.

Credentials must be supplied via environment variables — they are never logged.
"""

import asyncio
import logging
import time
from typing import Optional

import httpx

from app.ai.exceptions import AIInvalidOutputError, AIServiceUnavailableError
from app.ai.logging import sanitize_message
from app.core.config import settings

log = logging.getLogger(__name__)

_IAM_TOKEN_URL = "https://iam.cloud.ibm.com/identity/token"
_CHAT_PATH = "/ml/v1/text/chat"
_API_VERSION = "2023-05-29"
_TOKEN_SAFETY_MARGIN_SECONDS = 60  # refresh the token this many seconds before it expires
_IAM_TOKEN_TTL_SECONDS = 3600      # IBM IAM tokens are valid for 1 hour

# In-memory token cache — module level, reset on restart.
_cached_token: Optional[str] = None
_token_expiry: float = 0.0          # monotonic clock seconds
_token_lock = asyncio.Lock()


async def _fetch_iam_token() -> str:
    """Retrieve a fresh IAM bearer token from IBM Cloud.

    Raises :class:`AIServiceUnavailableError` on network or auth failure.
    Never logs the API key.
    """
    api_key = settings.WATSONX_API_KEY.get_secret_value()
    if not api_key:
        raise AIServiceUnavailableError("WATSONX_API_KEY is not configured")

    log.info("Watsonx IAM stage: request started")
    async with httpx.AsyncClient(timeout=settings.WATSONX_TIMEOUT_SECONDS) as client:
        try:
            resp = await client.post(
                _IAM_TOKEN_URL,
                data={
                    "grant_type": "urn:ibm:params:oauth:grant-type:apikey",
                    "apikey": api_key,
                },
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )
        except httpx.TransportError as exc:
            log.error(
                "Watsonx IAM stage: transport error | message=%s",
                sanitize_message(exc),
            )
            raise AIServiceUnavailableError(f"IAM token request failed: {exc}") from exc

    log.info("Watsonx IAM stage: HTTP status=%s", resp.status_code)
    if resp.status_code != 200:
        log.error(
            "Watsonx IAM stage: non-200 response | status=%s | body=%s",
            resp.status_code,
            sanitize_message(getattr(resp, "text", "")),
        )
        raise AIServiceUnavailableError(
            f"IAM token endpoint returned HTTP {resp.status_code}"
        )

    body = resp.json()
    token = body.get("access_token")
    if not token:
        raise AIServiceUnavailableError("IAM response did not contain access_token")
    log.info("Watsonx IAM stage: token acquired")
    return str(token)


async def _get_token() -> str:
    """Return a valid IAM token, refreshing from IBM Cloud when necessary."""
    global _cached_token, _token_expiry  # noqa: PLW0603

    if _cached_token and time.monotonic() < _token_expiry - _TOKEN_SAFETY_MARGIN_SECONDS:
        return _cached_token

    async with _token_lock:
        # Double-check after acquiring lock (another coroutine may have refreshed).
        if _cached_token and time.monotonic() < _token_expiry - _TOKEN_SAFETY_MARGIN_SECONDS:
            return _cached_token

        token = await _fetch_iam_token()
        _cached_token = token
        _token_expiry = time.monotonic() + _IAM_TOKEN_TTL_SECONDS
        return token


async def generate(prompt: str) -> str:
    """Send *prompt* to the configured Granite model and return generated text.

    Raises
    ------
    AIServiceUnavailableError
        If the watsonx endpoint cannot be reached or returns a non-2xx status.
    AIInvalidOutputError
        If the response body does not contain the expected ``results`` field.
    """
    token = await _get_token()

    url = f"{settings.WATSONX_URL.rstrip('/')}{_CHAT_PATH}"
    payload = {
        "model_id": settings.WATSONX_MODEL_ID,
        "project_id": settings.WATSONX_PROJECT_ID,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": settings.WATSONX_MAX_NEW_TOKENS,
        "temperature": 0.1,
    }

    log.info("Watsonx generation stage: request started | endpoint_path=%s", _CHAT_PATH)
    async with httpx.AsyncClient(timeout=settings.WATSONX_TIMEOUT_SECONDS) as client:
        try:
            resp = await client.post(
                url,
                json=payload,
                headers={"Authorization": f"Bearer {token}"},
                params={"version": _API_VERSION},
            )
        except httpx.TransportError as exc:
            log.error(
                "Watsonx generation stage: transport error | endpoint_path=%s | message=%s",
                _CHAT_PATH,
                sanitize_message(exc),
            )
            raise AIServiceUnavailableError(f"watsonx request failed: {exc}") from exc

    log.info(
        "Watsonx generation stage: HTTP status=%s | endpoint_path=%s",
        resp.status_code,
        _CHAT_PATH,
    )
    if resp.status_code != 200:
        log.error(
            "Watsonx generation stage: non-200 response | endpoint_path=%s | status=%s | body=%s",
            _CHAT_PATH,
            resp.status_code,
            sanitize_message(getattr(resp, "text", "")),
        )
        raise AIServiceUnavailableError(
            f"watsonx returned HTTP {resp.status_code}"
        )

    body = resp.json()
    try:
        return str(body["choices"][0]["message"]["content"])
    except (KeyError, IndexError, TypeError) as exc:
        raise AIInvalidOutputError(f"Unexpected watsonx response shape: {exc}") from exc
