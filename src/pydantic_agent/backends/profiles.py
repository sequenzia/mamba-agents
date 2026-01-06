"""Model profiles for various providers."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class ModelProfile:
    """Profile defining model capabilities and settings.

    Attributes:
        name: Model identifier.
        provider: Provider name (openai, anthropic, ollama, etc.).
        context_window: Maximum context window size.
        max_output_tokens: Maximum output tokens.
        supports_tools: Whether the model supports tool calling.
        supports_vision: Whether the model supports images.
        supports_streaming: Whether streaming is supported.
        default_temperature: Default temperature setting.
        cost_per_1k_input: Cost per 1000 input tokens (USD).
        cost_per_1k_output: Cost per 1000 output tokens (USD).
        extra: Additional provider-specific settings.
    """

    name: str
    provider: str
    context_window: int
    max_output_tokens: int
    supports_tools: bool = True
    supports_vision: bool = False
    supports_streaming: bool = True
    default_temperature: float = 0.7
    cost_per_1k_input: float | None = None
    cost_per_1k_output: float | None = None
    extra: dict[str, Any] = field(default_factory=dict)


# Built-in profiles for common models
PROFILES: dict[str, ModelProfile] = {
    # OpenAI models
    "gpt-4o": ModelProfile(
        name="gpt-4o",
        provider="openai",
        context_window=128000,
        max_output_tokens=16384,
        supports_tools=True,
        supports_vision=True,
        cost_per_1k_input=0.005,
        cost_per_1k_output=0.015,
    ),
    "gpt-4o-mini": ModelProfile(
        name="gpt-4o-mini",
        provider="openai",
        context_window=128000,
        max_output_tokens=16384,
        supports_tools=True,
        supports_vision=True,
        cost_per_1k_input=0.00015,
        cost_per_1k_output=0.0006,
    ),
    "gpt-4-turbo": ModelProfile(
        name="gpt-4-turbo",
        provider="openai",
        context_window=128000,
        max_output_tokens=4096,
        supports_tools=True,
        supports_vision=True,
        cost_per_1k_input=0.01,
        cost_per_1k_output=0.03,
    ),
    "gpt-3.5-turbo": ModelProfile(
        name="gpt-3.5-turbo",
        provider="openai",
        context_window=16385,
        max_output_tokens=4096,
        supports_tools=True,
        supports_vision=False,
        cost_per_1k_input=0.0005,
        cost_per_1k_output=0.0015,
    ),
    # Anthropic models
    "claude-3-5-sonnet-latest": ModelProfile(
        name="claude-3-5-sonnet-latest",
        provider="anthropic",
        context_window=200000,
        max_output_tokens=8192,
        supports_tools=True,
        supports_vision=True,
        cost_per_1k_input=0.003,
        cost_per_1k_output=0.015,
    ),
    "claude-3-opus-latest": ModelProfile(
        name="claude-3-opus-latest",
        provider="anthropic",
        context_window=200000,
        max_output_tokens=4096,
        supports_tools=True,
        supports_vision=True,
        cost_per_1k_input=0.015,
        cost_per_1k_output=0.075,
    ),
    "claude-3-haiku-20240307": ModelProfile(
        name="claude-3-haiku-20240307",
        provider="anthropic",
        context_window=200000,
        max_output_tokens=4096,
        supports_tools=True,
        supports_vision=True,
        cost_per_1k_input=0.00025,
        cost_per_1k_output=0.00125,
    ),
    # Local/Open-source defaults (Ollama, vLLM, etc.)
    "llama3.2": ModelProfile(
        name="llama3.2",
        provider="ollama",
        context_window=131072,
        max_output_tokens=4096,
        supports_tools=True,
        supports_vision=False,
    ),
    "llama3.2-vision": ModelProfile(
        name="llama3.2-vision",
        provider="ollama",
        context_window=131072,
        max_output_tokens=4096,
        supports_tools=True,
        supports_vision=True,
    ),
    "mistral": ModelProfile(
        name="mistral",
        provider="ollama",
        context_window=32768,
        max_output_tokens=4096,
        supports_tools=False,
        supports_vision=False,
    ),
    "codellama": ModelProfile(
        name="codellama",
        provider="ollama",
        context_window=16384,
        max_output_tokens=4096,
        supports_tools=False,
        supports_vision=False,
    ),
    "qwen2.5-coder": ModelProfile(
        name="qwen2.5-coder",
        provider="ollama",
        context_window=32768,
        max_output_tokens=8192,
        supports_tools=True,
        supports_vision=False,
    ),
    # Generic fallback for unknown models
    "default": ModelProfile(
        name="default",
        provider="unknown",
        context_window=8192,
        max_output_tokens=2048,
        supports_tools=False,
        supports_vision=False,
    ),
}


def get_profile(model_name: str) -> ModelProfile:
    """Get a profile for a model.

    Args:
        model_name: Model name or identifier.

    Returns:
        ModelProfile for the model, or default profile if unknown.
    """
    # Exact match
    if model_name in PROFILES:
        return PROFILES[model_name]

    # Check for partial matches (e.g., "gpt-4o-2024-05-13" matches "gpt-4o")
    for profile_name, profile in PROFILES.items():
        if model_name.startswith(profile_name):
            return profile

    # Return default profile for unknown models
    return PROFILES["default"]


def register_profile(profile: ModelProfile) -> None:
    """Register a custom model profile.

    Args:
        profile: The profile to register.
    """
    PROFILES[profile.name] = profile


def list_profiles() -> list[str]:
    """List all registered profile names.

    Returns:
        List of profile names.
    """
    return list(PROFILES.keys())


def get_profiles_by_provider(provider: str) -> list[ModelProfile]:
    """Get all profiles for a specific provider.

    Args:
        provider: Provider name (e.g., "openai", "ollama").

    Returns:
        List of profiles for that provider.
    """
    return [p for p in PROFILES.values() if p.provider == provider]
