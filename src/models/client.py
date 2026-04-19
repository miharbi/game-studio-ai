"""LLM client wrapper using litellm.

Provides streaming and non-streaming chat with any litellm-supported provider.
"""
from __future__ import annotations

from typing import Generator

try:
    import litellm  # type: ignore[import]

    litellm.set_verbose = False  # type: ignore[attr-defined]
except ImportError as exc:
    raise ImportError("litellm not installed. Run: pip install litellm") from exc


class LLMClient:
    """Provider-agnostic LLM client via litellm."""

    def __init__(self, model: str) -> None:
        self.model = model

    def chat(
        self,
        messages: list[dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 4096,
    ) -> str:
        """Non-streaming chat. Returns full response as string."""
        response = litellm.completion(
            model=self.model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        return response.choices[0].message.content or ""

    def stream(
        self,
        messages: list[dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 4096,
    ) -> Generator[str, None, None]:
        """Streaming chat. Yields text chunks as they arrive."""
        response = litellm.completion(
            model=self.model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            stream=True,
        )
        for chunk in response:
            delta = chunk.choices[0].delta
            content: str = getattr(delta, "content", None) or ""
            if content:
                yield content
