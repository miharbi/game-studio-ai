"""LLM client wrapper using litellm.

Provides streaming and non-streaming chat with any litellm-supported provider.
Includes timeout and retry with exponential backoff for transient errors.
"""
from __future__ import annotations

import time
from typing import Generator

try:
    import litellm  # type: ignore[import]

    litellm.set_verbose = False  # type: ignore[attr-defined]
except ImportError as exc:
    raise ImportError("litellm not installed. Run: pip install litellm") from exc

# Retry config
_MAX_RETRIES: int = 3
_BASE_BACKOFF: float = 2.0  # seconds
_RETRYABLE_EXCEPTIONS = (
    litellm.RateLimitError,
    litellm.APIConnectionError,
    litellm.Timeout,
)


class LLMClient:
    """Provider-agnostic LLM client via litellm."""

    def __init__(self, model: str, timeout: float = 120.0) -> None:
        self.model = model
        self.timeout = timeout

    def chat(
        self,
        messages: list[dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 4096,
    ) -> str:
        """Non-streaming chat. Returns full response as string."""
        last_exc: Exception | None = None
        for attempt in range(_MAX_RETRIES):
            try:
                response = litellm.completion(
                    model=self.model,
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    timeout=self.timeout,
                )
                return response.choices[0].message.content or ""
            except _RETRYABLE_EXCEPTIONS as exc:
                last_exc = exc
                if attempt < _MAX_RETRIES - 1:
                    time.sleep(_BASE_BACKOFF ** (attempt + 1))
        raise last_exc  # type: ignore[misc]

    def stream(
        self,
        messages: list[dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 4096,
    ) -> Generator[str, None, None]:
        """Streaming chat. Yields text chunks as they arrive."""
        last_exc: Exception | None = None
        for attempt in range(_MAX_RETRIES):
            try:
                response = litellm.completion(
                    model=self.model,
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    stream=True,
                    timeout=self.timeout,
                )
                for chunk in response:
                    delta = chunk.choices[0].delta
                    content: str = getattr(delta, "content", None) or ""
                    if content:
                        yield content
                return  # stream completed successfully
            except _RETRYABLE_EXCEPTIONS as exc:
                last_exc = exc
                if attempt < _MAX_RETRIES - 1:
                    time.sleep(_BASE_BACKOFF ** (attempt + 1))
        raise last_exc  # type: ignore[misc]
