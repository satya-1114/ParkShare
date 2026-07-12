"""AI-specific exceptions raised by the watsonx.ai client and AI services."""


class AIServiceUnavailableError(Exception):
    """Raised when the watsonx.ai API cannot be reached or returns a non-2xx
    response. Callers must degrade gracefully when this is raised."""


class AIInvalidOutputError(Exception):
    """Raised when the model response cannot be parsed into the expected JSON
    structure. Callers must fall back to deterministic logic."""
