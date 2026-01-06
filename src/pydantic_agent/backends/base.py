"""Abstract backend interface."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import AsyncIterator


@dataclass
class ModelResponse:
    """Response from a model backend.

    Attributes:
        content: The generated content.
        tool_calls: Any tool calls requested.
        usage: Token usage information.
        model: Model that generated the response.
        finish_reason: Reason for completion.
    """

    content: str
    tool_calls: list[dict[str, Any]] | None = None
    usage: dict[str, int] | None = None
    model: str | None = None
    finish_reason: str | None = None


@dataclass
class StreamChunk:
    """A chunk from a streaming response.

    Attributes:
        content: Partial content.
        tool_calls: Partial tool call data.
        is_final: Whether this is the final chunk.
        usage: Token usage (only in final chunk).
    """

    content: str = ""
    tool_calls: list[dict[str, Any]] | None = None
    is_final: bool = False
    usage: dict[str, int] | None = None


class ModelBackend(ABC):
    """Abstract base class for model backends.

    Implementations provide connection to various model providers
    (OpenAI, Anthropic, local models, etc.).
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Get the backend name."""
        ...

    @property
    @abstractmethod
    def model(self) -> str:
        """Get the current model identifier."""
        ...

    @abstractmethod
    async def complete(
        self,
        messages: list[dict[str, Any]],
        *,
        tools: list[dict[str, Any]] | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
        **kwargs: Any,
    ) -> ModelResponse:
        """Generate a completion.

        Args:
            messages: Conversation messages.
            tools: Available tools.
            temperature: Sampling temperature.
            max_tokens: Maximum tokens to generate.
            **kwargs: Additional provider-specific options.

        Returns:
            ModelResponse with generation results.
        """
        ...

    @abstractmethod
    async def stream(
        self,
        messages: list[dict[str, Any]],
        *,
        tools: list[dict[str, Any]] | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
        **kwargs: Any,
    ) -> AsyncIterator[StreamChunk]:
        """Generate a streaming completion.

        Args:
            messages: Conversation messages.
            tools: Available tools.
            temperature: Sampling temperature.
            max_tokens: Maximum tokens to generate.
            **kwargs: Additional provider-specific options.

        Yields:
            StreamChunk objects with partial content.
        """
        ...

    @abstractmethod
    async def health_check(self) -> bool:
        """Check if the backend is healthy.

        Returns:
            True if the backend is reachable and working.
        """
        ...

    async def close(self) -> None:
        """Close any open connections.

        Override this method to clean up resources.
        """
        pass
