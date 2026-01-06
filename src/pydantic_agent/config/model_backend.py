"""Model backend configuration."""

from __future__ import annotations

from pydantic import BaseModel, Field, SecretStr


class ModelBackendSettings(BaseModel):
    """Configuration for the model backend connection.

    This configuration defines how to connect to an OpenAI-compatible API endpoint,
    which can be a local LLM server (Ollama, vLLM, llama.cpp) or a remote service.

    Attributes:
        base_url: Base URL for the OpenAI-compatible API endpoint.
        api_key: Optional API key for authenticated endpoints.
        model: Model identifier to use for requests.
        timeout: Request timeout in seconds.
        max_retries: Maximum retry attempts for failed requests.
        temperature: Sampling temperature for generation.
        max_tokens: Maximum tokens to generate (None for model default).
    """

    base_url: str = Field(
        default="http://localhost:11434/v1",
        description="Base URL for the OpenAI-compatible API endpoint",
    )
    api_key: SecretStr | None = Field(
        default=None,
        description="API key for authenticated endpoints",
    )
    model: str = Field(
        default="llama3.2",
        description="Model identifier to use",
    )
    timeout: float = Field(
        default=30.0,
        gt=0,
        description="Request timeout in seconds",
    )
    max_retries: int = Field(
        default=3,
        ge=0,
        description="Maximum retry attempts for failed requests",
    )
    temperature: float = Field(
        default=0.7,
        ge=0.0,
        le=2.0,
        description="Sampling temperature for generation",
    )
    max_tokens: int | None = Field(
        default=None,
        gt=0,
        description="Maximum tokens to generate",
    )

    def get_headers(self) -> dict[str, str]:
        """Get HTTP headers for API requests.

        Returns:
            Dictionary of headers including Authorization if API key is set.
        """
        headers: dict[str, str] = {}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key.get_secret_value()}"
        return headers
