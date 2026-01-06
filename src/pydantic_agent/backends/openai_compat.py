"""OpenAI-compatible backend adapter.

Supports OpenAI API and compatible APIs like:
- Ollama
- vLLM
- llama.cpp
- LM Studio
- LocalAI
"""

from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING, Any

import httpx

from pydantic_agent.backends.base import ModelBackend, ModelResponse, StreamChunk
from pydantic_agent.backends.profiles import ModelProfile, get_profile
from pydantic_agent.errors.exceptions import (
    AuthenticationError,
    ModelBackendError,
    RateLimitError,
)

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

    from pydantic import SecretStr

logger = logging.getLogger(__name__)


class OpenAICompatibleBackend(ModelBackend):
    """Backend for OpenAI-compatible APIs.

    Works with any API that follows the OpenAI chat completions format.
    Automatically handles differences between providers.
    """

    def __init__(
        self,
        model: str,
        *,
        base_url: str = "https://api.openai.com/v1",
        api_key: SecretStr | str | None = None,
        timeout: float = 60.0,
        profile: ModelProfile | None = None,
    ) -> None:
        """Initialize the backend.

        Args:
            model: Model identifier.
            base_url: API base URL.
            api_key: API key for authentication.
            timeout: Request timeout in seconds.
            profile: Custom model profile.
        """
        self._model = model
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout
        self._profile = profile or get_profile(model)

        # Handle SecretStr
        if api_key is not None:
            self._api_key = (
                api_key.get_secret_value()
                if hasattr(api_key, "get_secret_value")
                else str(api_key)
            )
        else:
            self._api_key = None

        self._client = httpx.AsyncClient(
            base_url=self._base_url,
            timeout=timeout,
            headers=self._build_headers(),
        )

    def _build_headers(self) -> dict[str, str]:
        """Build request headers."""
        headers = {"Content-Type": "application/json"}
        if self._api_key:
            headers["Authorization"] = f"Bearer {self._api_key}"
        return headers

    @property
    def name(self) -> str:
        """Get backend name."""
        return "openai_compatible"

    @property
    def model(self) -> str:
        """Get model identifier."""
        return self._model

    @property
    def profile(self) -> ModelProfile:
        """Get model profile."""
        return self._profile

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
            **kwargs: Additional options.

        Returns:
            ModelResponse with generation results.

        Raises:
            ModelBackendError: On API error.
            RateLimitError: On rate limit.
            AuthenticationError: On auth failure.
        """
        payload = self._build_payload(
            messages=messages,
            tools=tools,
            temperature=temperature,
            max_tokens=max_tokens,
            stream=False,
            **kwargs,
        )

        try:
            response = await self._client.post("/chat/completions", json=payload)
            self._check_response(response)
            data = response.json()
            return self._parse_response(data)

        except httpx.HTTPStatusError as e:
            self._handle_http_error(e)
            raise  # Never reached, but satisfies type checker

        except httpx.RequestError as e:
            raise ModelBackendError(
                f"Request failed: {e}",
                model=self._model,
                retryable=True,
                cause=e,
            ) from e

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
            **kwargs: Additional options.

        Yields:
            StreamChunk objects with partial content.
        """
        payload = self._build_payload(
            messages=messages,
            tools=tools,
            temperature=temperature,
            max_tokens=max_tokens,
            stream=True,
            **kwargs,
        )

        try:
            async with self._client.stream(
                "POST", "/chat/completions", json=payload
            ) as response:
                self._check_response(response)

                async for line in response.aiter_lines():
                    if not line or line.startswith(":"):
                        continue

                    if line.startswith("data: "):
                        data_str = line[6:]
                        if data_str.strip() == "[DONE]":
                            yield StreamChunk(is_final=True)
                            break

                        try:
                            data = json.loads(data_str)
                            chunk = self._parse_stream_chunk(data)
                            if chunk:
                                yield chunk
                        except json.JSONDecodeError:
                            logger.warning("Failed to parse stream chunk: %s", line)

        except httpx.HTTPStatusError as e:
            self._handle_http_error(e)

        except httpx.RequestError as e:
            raise ModelBackendError(
                f"Stream request failed: {e}",
                model=self._model,
                retryable=True,
                cause=e,
            ) from e

    async def health_check(self) -> bool:
        """Check if the backend is healthy.

        Returns:
            True if reachable.
        """
        try:
            # Try to list models (common endpoint)
            response = await self._client.get("/models")
            return response.status_code in (200, 401, 403)  # Even auth error means reachable
        except httpx.RequestError:
            return False

    async def close(self) -> None:
        """Close the HTTP client."""
        await self._client.aclose()

    def _build_payload(
        self,
        messages: list[dict[str, Any]],
        *,
        tools: list[dict[str, Any]] | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
        stream: bool = False,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Build the API request payload."""
        payload: dict[str, Any] = {
            "model": self._model,
            "messages": messages,
            "stream": stream,
        }

        if temperature is not None:
            payload["temperature"] = temperature
        elif self._profile.default_temperature is not None:
            payload["temperature"] = self._profile.default_temperature

        if max_tokens is not None:
            payload["max_tokens"] = max_tokens

        if tools and self._profile.supports_tools:
            payload["tools"] = tools

        # Add any additional kwargs
        payload.update(kwargs)

        return payload

    def _check_response(self, response: httpx.Response) -> None:
        """Check response for errors."""
        if response.status_code >= 400:
            response.raise_for_status()

    def _handle_http_error(self, error: httpx.HTTPStatusError) -> None:
        """Handle HTTP errors with appropriate exceptions."""
        status = error.response.status_code
        try:
            body = error.response.json()
            message = body.get("error", {}).get("message", str(error))
        except (json.JSONDecodeError, KeyError):
            message = str(error)

        if status == 401:
            raise AuthenticationError(
                f"Authentication failed: {message}",
                cause=error,
            )

        if status == 429:
            retry_after = error.response.headers.get("Retry-After")
            raise RateLimitError(
                f"Rate limit exceeded: {message}",
                model=self._model,
                retry_after=float(retry_after) if retry_after else None,
            )

        retryable = status >= 500 or status == 429
        raise ModelBackendError(
            f"API error ({status}): {message}",
            model=self._model,
            status_code=status,
            response_body=message,
            retryable=retryable,
            cause=error,
        )

    def _parse_response(self, data: dict[str, Any]) -> ModelResponse:
        """Parse API response into ModelResponse."""
        choice = data.get("choices", [{}])[0]
        message = choice.get("message", {})

        # Parse tool calls if present
        tool_calls = None
        if "tool_calls" in message:
            tool_calls = message["tool_calls"]

        # Parse usage
        usage = None
        if "usage" in data:
            usage = {
                "input_tokens": data["usage"].get("prompt_tokens", 0),
                "output_tokens": data["usage"].get("completion_tokens", 0),
                "total_tokens": data["usage"].get("total_tokens", 0),
            }

        return ModelResponse(
            content=message.get("content", ""),
            tool_calls=tool_calls,
            usage=usage,
            model=data.get("model", self._model),
            finish_reason=choice.get("finish_reason"),
        )

    def _parse_stream_chunk(self, data: dict[str, Any]) -> StreamChunk | None:
        """Parse a streaming chunk."""
        choices = data.get("choices", [])
        if not choices:
            return None

        choice = choices[0]
        delta = choice.get("delta", {})

        content = delta.get("content", "")
        tool_calls = delta.get("tool_calls")
        finish_reason = choice.get("finish_reason")

        # Check for usage in stream (some providers include it)
        usage = None
        if "usage" in data:
            usage = {
                "input_tokens": data["usage"].get("prompt_tokens", 0),
                "output_tokens": data["usage"].get("completion_tokens", 0),
            }

        return StreamChunk(
            content=content,
            tool_calls=tool_calls,
            is_final=finish_reason is not None,
            usage=usage,
        )


def create_ollama_backend(
    model: str,
    *,
    base_url: str = "http://localhost:11434/v1",
    **kwargs: Any,
) -> OpenAICompatibleBackend:
    """Create a backend configured for Ollama.

    Args:
        model: Model name (e.g., "llama3.2", "mistral").
        base_url: Ollama API URL.
        **kwargs: Additional backend options.

    Returns:
        Configured OpenAICompatibleBackend.
    """
    return OpenAICompatibleBackend(
        model=model,
        base_url=base_url,
        api_key=None,  # Ollama doesn't require auth by default
        **kwargs,
    )


def create_vllm_backend(
    model: str,
    *,
    base_url: str = "http://localhost:8000/v1",
    api_key: str | None = None,
    **kwargs: Any,
) -> OpenAICompatibleBackend:
    """Create a backend configured for vLLM.

    Args:
        model: Model name.
        base_url: vLLM API URL.
        api_key: API key if required.
        **kwargs: Additional backend options.

    Returns:
        Configured OpenAICompatibleBackend.
    """
    return OpenAICompatibleBackend(
        model=model,
        base_url=base_url,
        api_key=api_key,
        **kwargs,
    )


def create_lmstudio_backend(
    model: str = "local-model",
    *,
    base_url: str = "http://localhost:1234/v1",
    **kwargs: Any,
) -> OpenAICompatibleBackend:
    """Create a backend configured for LM Studio.

    Args:
        model: Model identifier (can be any name).
        base_url: LM Studio API URL.
        **kwargs: Additional backend options.

    Returns:
        Configured OpenAICompatibleBackend.
    """
    return OpenAICompatibleBackend(
        model=model,
        base_url=base_url,
        api_key=None,
        **kwargs,
    )
