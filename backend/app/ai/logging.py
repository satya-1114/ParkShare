"""Safe logging helpers for AI service boundaries.

These helpers intentionally log configuration presence and public endpoint/model
metadata only. They never log API key values, IAM bearer tokens, Authorization
headers, or full credential material.
"""
import logging
from typing import Iterable

from app.core.config import settings


def is_watsonx_api_key_configured() -> bool:
    return bool(settings.WATSONX_API_KEY.get_secret_value())


def is_watsonx_project_id_configured() -> bool:
    return bool(settings.WATSONX_PROJECT_ID.strip())


def sanitize_message(message: object, extra_secrets: Iterable[str | None] = ()) -> str:
    """Return a one-line message with known sensitive values redacted."""
    text = str(message).replace("\n", " ").replace("\r", " ")

    secrets = [
        settings.WATSONX_API_KEY.get_secret_value(),
        *[s for s in extra_secrets if s],
    ]
    for secret in secrets:
        if secret:
            text = text.replace(secret, "[REDACTED]")

    if "Authorization" in text or "Bearer " in text:
        text = text.replace("Authorization", "[REDACTED_AUTH_HEADER]")
        text = text.replace("Bearer ", "Bearer [REDACTED]")

    return text[:1000]


def log_ai_fallback(logger: logging.Logger, feature_name: str, exc: BaseException) -> None:
    """Log an AI fallback event with safe, actionable runtime context."""
    logger.warning(
        "AI fallback triggered | feature=%s | exception_class=%s | message=%s | "
        "WATSONX_URL=%s | WATSONX_MODEL_ID=%s | WATSONX_API_KEY_configured=%s | "
        "WATSONX_PROJECT_ID_configured=%s",
        feature_name,
        type(exc).__name__,
        sanitize_message(exc),
        settings.WATSONX_URL,
        settings.WATSONX_MODEL_ID,
        is_watsonx_api_key_configured(),
        is_watsonx_project_id_configured(),
    )